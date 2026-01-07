# src/misc/get_relevant.py
import sqlite3
from typing import List, Dict


def _normalize(s: str) -> str:
    return (s or "").lower()


def filter_relevant_by_keywords(
    db_path: str,
    arxiv_urls: List[str],
    keywords: List[str],
) -> List[Dict]:
    """
    从本次 arxiv_urls 对应的 papers 中筛“相关”的（简单关键词命中）。
    返回 dict 列表（可用于邮件渲染）。
    """
    if not arxiv_urls:
        return []
    if not keywords:
        return []

    kw = [k.strip().lower() for k in keywords if k.strip()]
    if not kw:
        return []

    placeholders = ",".join(["?"] * len(arxiv_urls))

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            f"""
            SELECT arxiv_url, title, abstract, subject, publish_time, pdf_views, kimi_calls
            FROM papers
            WHERE arxiv_url IN ({placeholders})
            """,
            arxiv_urls,
        ).fetchall()

        out: List[Dict] = []
        for r in rows:
            text = " ".join(
                [
                    _normalize(r["title"]),
                    _normalize(r["abstract"]),
                    _normalize(r["subject"]),
                ]
            )
            if any(k in text for k in kw):
                out.append(dict(r))
        # 稍微按“热度”排一下，便于邮件阅读
        out.sort(
            key=lambda x: (
                int(x.get("pdf_views") or 0) + int(x.get("kimi_calls") or 0)
            ),
            reverse=True,
        )
        return out
    finally:
        conn.close()
