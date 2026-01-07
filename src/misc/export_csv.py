import os
import sqlite3
import csv
from datetime import datetime
from typing import Optional


def export_urls_to_csv(
    db_path: str,
    arxiv_urls: list[str],
    out_dir: str = "data/csv",
    filename: Optional[str] = None,
) -> str:
    """
    导出本次抓取的 arxiv_urls 对应论文到 CSV（最准确）
    """
    os.makedirs(out_dir, exist_ok=True)
    if filename is None:
        filename = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_run.csv"
    out_path = os.path.join(out_dir, filename)

    if not arxiv_urls:
        # 生成空文件也行
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            pass
        return out_path

    placeholders = ",".join(["?"] * len(arxiv_urls))

    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""
            SELECT
                p.title,
                p.abstract,
                p.subject,
                p.publish_time,
                p.updated_at,
                p.arxiv_url,
                p.pdf_views,
                p.kimi_calls,
                GROUP_CONCAT(a.author_name, ', ') AS authors
            FROM papers p
            LEFT JOIN paper_authors a ON a.paper_id = p.id
            WHERE p.arxiv_url IN ({placeholders})
            GROUP BY p.id
            ORDER BY p.updated_at ASC
            """,
            arxiv_urls,
        ).fetchall()

        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "title",
                    "abstract",
                    "authors",
                    "subject",
                    "publish_time",
                    "updated_at",
                    "arxiv_url",
                    "pdf_views",
                    "kimi_calls",
                ]
            )
            for r in rows:
                writer.writerow(
                    [
                        r["title"],
                        r["abstract"],
                        r["authors"],
                        r["subject"],
                        r["publish_time"],
                        r["updated_at"],
                        r["arxiv_url"],
                        r["pdf_views"],
                        r["kimi_calls"],
                    ]
                )

        return out_path
    finally:
        conn.close()
