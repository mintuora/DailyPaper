# src/misc/get_popular.py
import sqlite3
from typing import List, Dict


def get_top_popular(
    db_path: str,
    arxiv_urls: List[str],
    top_n: int = 5,
) -> List[Dict]:
    """
    从本次 arxiv_urls 中，按 (pdf_views + kimi_calls) 排前 N。
    """
    if not arxiv_urls:
        return []

    placeholders = ",".join(["?"] * len(arxiv_urls))

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            f"""
            SELECT arxiv_url, abstract, title, subject, publish_time, pdf_views, kimi_calls
            FROM papers
            WHERE arxiv_url IN ({placeholders})
            ORDER BY (pdf_views + kimi_calls) DESC
            LIMIT ?
            """,
            (*arxiv_urls, int(top_n)),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
