import os
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict

import yaml
from src.task.get_data import fetch_and_upsert
from src.misc.get_relevant import filter_relevant_by_keywords
from src.misc.get_popular import get_top_popular
from src.misc.logger import setup_run_logger


def load_yaml(path: str) -> Dict:
    if not path or not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def count_today_utc(db_path: str, arxiv_urls: List[str]) -> int:
    """
    统计“今天(UTC)”的论文数：publish_time 形如 'YYYY-MM-DD HH:MM:SS'
    只统计本次抓取 arxiv_urls 范围内的。
    """
    if not arxiv_urls:
        return 0

    today = datetime.utcnow().strftime("%Y-%m-%d")
    placeholders = ",".join(["?"] * len(arxiv_urls))

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            f"""
            SELECT COUNT(1)
            FROM papers
            WHERE arxiv_url IN ({placeholders})
              AND publish_time LIKE ?
            """,
            (*arxiv_urls, f"{today}%"),
        ).fetchone()
        return int(row[0] or 0)
    finally:
        conn.close()


def count_yesterday_utc(db_path: str, arxiv_urls: List[str]) -> int:
    """
    统计“昨天(UTC)”的论文数：publish_time 形如 'YYYY-MM-DD HH:MM:SS'
    只统计本次抓取 arxiv_urls 范围内的。
    """
    if not arxiv_urls:
        return 0

    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    placeholders = ",".join(["?"] * len(arxiv_urls))

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            f"""
            SELECT COUNT(1)
            FROM papers
            WHERE arxiv_url IN ({placeholders})
              AND publish_time LIKE ?
            """,
            (*arxiv_urls, f"{yesterday}%"),
        ).fetchone()
        return int(row[0] or 0)
    finally:
        conn.close()


def get_unnotified_urls(db_path: str, arxiv_urls: List[str]) -> List[str]:
    """
    从给定的 arxiv_urls 中筛选出尚未通知过的 (notified=0)
    """
    if not arxiv_urls:
        return []
    placeholders = ",".join(["?"] * len(arxiv_urls))
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            f"SELECT arxiv_url FROM papers WHERE arxiv_url IN ({placeholders}) AND notified = 0",
            arxiv_urls,
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def mark_as_notified(db_path: str, arxiv_urls: List[str]) -> None:
    """
    将指定的 arxiv_urls 标记为已通知 (notified=1)
    """
    if not arxiv_urls:
        return
    placeholders = ",".join(["?"] * len(arxiv_urls))
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            f"UPDATE papers SET notified = 1 WHERE arxiv_url IN ({placeholders})",
            arxiv_urls,
        )
        conn.commit()
    finally:
        conn.close()


def render_mail(
    web_url: str,
    today_count: int,
    relevant: List[Dict],
    popular: List[Dict],
) -> str:
    lines = []
    lines.append("DailyPaper 报告")
    lines.append(f"来源: {web_url}")
    lines.append(f"昨日论文数: {today_count}")
    lines.append("")

    lines.append("== 关键词相关（Relevant） ==")
    if not relevant:
        lines.append("(无)")
    else:
        for i, p in enumerate(relevant, 1):
            lines.append(f"{i}. {p.get('title')}")
            lines.append(f"   arxiv: {p.get('arxiv_url')}")
            lines.append(
                f"   publish: {p.get('publish_time')} | subject: {p.get('subject')}"
            )
            abs_ = (p.get("abstract") or "").strip().replace("\n", " ")
            if abs_:
                lines.append(
                    f"   abstract: {abs_[:40000]}{'...' if len(abs_) > 40000 else ''}"
                )
    lines.append("")

    lines.append("== 热门（Popular Top） ==")
    if not popular:
        lines.append("(无)")
    else:
        for i, p in enumerate(popular, 1):
            heat = int(p.get("pdf_views") or 0) + int(p.get("kimi_calls") or 0)
            lines.append(f"{i}. {p.get('title')}")
            lines.append(f"   arxiv: {p.get('arxiv_url')}")
            lines.append(
                f"   publish: {p.get('publish_time')} | subject: {p.get('subject')}"
            )
            lines.append(
                f"   pdf_views: {p.get('pdf_views')} | kimi_calls: {p.get('kimi_calls')} | heat={heat}"
            )
    lines.append("")

    return "\n".join(lines)


def main():
    logger, log_path = setup_run_logger(log_dir="log")

    # 配置：env > yaml > default
    base_conf = load_yaml(os.getenv("BASE_YAML", "config/base.yaml"))
    task_conf = load_yaml(os.getenv("TASK_YAML", "config/task.yaml"))

    web_url = (
        os.getenv("WEB_URL")
        or base_conf.get("web", {}).get("URL")
        or "https://papers.cool/arxiv/cs+q-bio?show=10000"
    )
    db_path = os.getenv("DB_PATH") or base_conf.get("db_path") or "data/papers.sqlite3"

    top_n = int(os.getenv("TOP_POPULAR_N") or base_conf.get("top_popular_n") or 5)

    keywords = task_conf.get("keyword") or []
    if isinstance(keywords, str):
        keywords = [keywords]

    logger.info("Start run. web_url=%s db_path=%s top_n=%s", web_url, db_path, top_n)

    # 1) 抓取 + 入库
    all_fetched_urls = fetch_and_upsert(web_url=web_url, db_path=db_path)
    logger.info("Fetched & upserted: %d papers", len(all_fetched_urls))

    # 2) 筛选出未通知过的论文，实现去重
    arxiv_urls = get_unnotified_urls(db_path, all_fetched_urls)
    logger.info("New papers (unnotified): %d", len(arxiv_urls))

    if not arxiv_urls:
        logger.info("No new papers to report. Exit.")
        return

    # 3) 统计昨天(UTC)论文数（在本次抓取范围内）
    yesterday_count = count_yesterday_utc(db_path, arxiv_urls)
    logger.info("yesterday count in new set: %d", yesterday_count)

    # 4) relevant / popular
    relevant = filter_relevant_by_keywords(db_path, arxiv_urls, keywords)
    logger.info("Relevant matched: %d", len(relevant))

    popular = get_top_popular(db_path, arxiv_urls, top_n=top_n)
    logger.info("Popular top_n=%d returned: %d", top_n, len(popular))

    body = render_mail(web_url, yesterday_count, relevant, popular)
    logger.info(body)

    logger.info("Run finished. log_file=%s", log_path)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # 这里不依赖 logger（万一 logger 初始化前就炸）
        os.makedirs("log", exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        fallback = os.path.join("log", f"{ts}_crash.log")
        with open(fallback, "w", encoding="utf-8") as f:
            f.write(f"[CRASH] {datetime.utcnow().isoformat()}Z\n{repr(e)}\n")
        raise
