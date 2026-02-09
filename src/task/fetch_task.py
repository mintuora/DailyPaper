import os
import logging
from src.db import DBManager
from src.scraper import ArxivScraper
from src.misc.logger import setup_run_logger
from src.ranking import filter_relevant_by_keywords, get_top_popular
from src.misc.config_loader import get_base_conf, get_task_conf

def run_fetch():
    logger, _ = setup_run_logger(name="DailyPaper.Fetch")
    logger.info("--- 启动获取任务 (Fetch) ---")

    base_conf = get_base_conf()
    task_conf = get_task_conf()
    
    web_url = base_conf.get("web", {}).get("URL") or "https://papers.cool/arxiv/cs+q-bio?show=10000"
    db_path = base_conf.get("db_path", "data/papers.sqlite3")
    top_n = base_conf.get("top_popular_n", 5)
    keywords = task_conf.get("keyword", [])
    if isinstance(keywords, str):
        keywords = [keywords]

    try:
        scraper = ArxivScraper()
        db = DBManager(db_path)
        
        fetched_papers = scraper.fetch_papers(web_url)
        all_urls = [p["arxiv_url"] for p in fetched_papers]
        
        for p in fetched_papers:
            db.upsert_paper(p)
        
        logger.info(f"成功抓取并更新了 {len(fetched_papers)} 篇论文。")

        # 筛选逻辑
        relevant_papers = filter_relevant_by_keywords(db_path, all_urls, keywords)
        relevant_urls = [p["arxiv_url"] for p in relevant_papers]
        
        popular_papers = get_top_popular(db_path, all_urls, top_n)
        popular_urls = [p["arxiv_url"] for p in popular_papers]
        
        # 合并命中结果，去重
        target_urls = list(set(relevant_urls + popular_urls))
        
        if target_urls:
            db.update_status(target_urls, 1) # 标记为待推送
            logger.info(f"筛选完成：命中了 {len(target_urls)} 篇待推送论文 (关键词: {len(relevant_urls)}, 热度: {len(popular_urls)})")
        else:
            logger.info("筛选完成：本次抓取无命中论文。")
            
    except Exception as e:
        logger.error(f"获取任务异常: {e}")
        raise

if __name__ == "__main__":
    run_fetch()
