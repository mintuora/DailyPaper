import logging
from typing import Dict, List

from src.db.pubmed_db_manager import PubMedDBManager
from src.misc.config_loader import get_base_conf, get_task_conf
from src.misc.logger import setup_run_logger
from src.scraper.pubmed_scraper import PubMedScraper

logger = logging.getLogger("DailyPaper")

DEFAULT_PUBMED_DB_PATH = "data/pubmed_papers.sqlite3"
DEFAULT_PUBMED_QUERY = (
    '(("protein design"[Title/Abstract]) OR '
    '("de novo protein design"[Title/Abstract]) OR '
    '("computational protein design"[Title/Abstract]) OR '
    '("protein engineering"[Title/Abstract]) OR '
    '("protein sequence design"[Title/Abstract]))'
)


def _normalize_keywords(value) -> List[str]:
    if not value:
        return []
    if isinstance(value, str):
        value = [value]
    return [str(v).strip().lower() for v in value if str(v).strip()]


def _filter_by_keywords(papers: List[Dict], keywords: List[str]) -> List[Dict]:
    if not keywords:
        return papers

    out: List[Dict] = []
    for p in papers:
        text = " ".join(
            [
                str(p.get("title") or "").lower(),
                str(p.get("abstract") or "").lower(),
                str(p.get("subject") or "").lower(),
            ]
        )
        if any(k in text for k in keywords):
            out.append(p)
    return out


def run_fetch_pubmed():
    logger, _ = setup_run_logger(name="DailyPaper.Fetch.PubMed")
    logger.info("--- 启动 PubMed 获取任务 (Fetch PubMed) ---")

    base_conf = get_base_conf() or {}
    task_conf = get_task_conf() or {}
    pubmed_conf = base_conf.get("pubmed", {}) or {}

    enabled = bool(pubmed_conf.get("enabled", True))
    if not enabled:
        logger.info("PubMed 抓取已禁用，任务结束。")
        return

    db_path = pubmed_conf.get("db_path", DEFAULT_PUBMED_DB_PATH)
    query = (pubmed_conf.get("query") or DEFAULT_PUBMED_QUERY).strip()
    retmax = int(pubmed_conf.get("retmax", 50))
    days_back = int(pubmed_conf.get("days_back", 1))
    timeout = int(pubmed_conf.get("timeout", 30))

    pubmed_keywords = _normalize_keywords(task_conf.get("pubmed_keyword", []))

    try:
        scraper = PubMedScraper(
            timeout=timeout,
            email=pubmed_conf.get("email"),
            tool=pubmed_conf.get("tool", "DailyPaper"),
            api_key=pubmed_conf.get("api_key"),
        )
        db = PubMedDBManager(db_path)

        fetched_papers = scraper.fetch_papers(query=query, retmax=retmax, days_back=days_back)
        logger.info(f"PubMed 原始抓取结果：{len(fetched_papers)} 篇")

        selected_papers = _filter_by_keywords(fetched_papers, pubmed_keywords)
        logger.info(f"PubMed 关键词筛选后：{len(selected_papers)} 篇")

        all_urls: List[str] = []
        for p in selected_papers:
            db.upsert_paper(p)
            paper_url = p.get("pubmed_url") or p.get("arxiv_url")
            if paper_url:
                all_urls.append(paper_url)

        updated = db.mark_pending(all_urls)
        skipped = len(all_urls) - updated
        logger.info(
            f"PubMed 入库完成：总计 {len(all_urls)} 篇，标记待处理 {updated} 篇，跳过已处理 {skipped} 篇"
        )
    except Exception as e:
        logger.error(f"PubMed 获取任务异常: {e}")
        raise


if __name__ == "__main__":
    run_fetch_pubmed()
