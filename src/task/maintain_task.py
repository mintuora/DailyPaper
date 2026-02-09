import os
import yaml
import logging
from src.misc.logger import setup_run_logger

def run_maintain():
    logger, _ = setup_run_logger(name="DailyPaper.Maintain")
    logger.info("--- 启动维护任务 (Maintain) ---")

    with open("config/base.yaml", "r", encoding="utf-8") as f:
        conf = yaml.safe_load(f)
    
    db_path = conf.get("db_path", "data/papers.sqlite3")

    if os.path.exists(db_path):
        logger.info(f"正在删除数据库: {db_path}")
        os.remove(db_path)
        logger.info("数据库已删除。")
    else:
        logger.info("数据库文件不存在，无需删除。")

    log_dir = "log"
    if os.path.exists(log_dir):
        logger.info("正在清理 7 天前的日志文件...")
        pass

if __name__ == "__main__":
    run_maintain()
