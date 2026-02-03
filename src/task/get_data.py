# src/task/get_data.py
import re
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

import requests
import lxml.html as LH


def _to_int(x: str) -> int:
    if not x:
        return 0
    m = re.search(r"\d+", x)
    return int(m.group(0)) if m else 0


def parse_utc_time(s: Optional[str]) -> Optional[str]:
    """
    '2026-01-06 17:59:37 UTC' -> '2026-01-06 17:59:37' (UTC)
    SQLite 用 TEXT 存 ISO-like 时间即可，可排序可比较。
    """
    if not s:
        return None
    s = s.strip()
    try:
        dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S UTC")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def init_db(conn: sqlite3.Connection) -> None:
    """
    初始化/升级数据库结构（幂等）。
    仅保留 papers + paper_authors 两张表。
    """
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA temp_store=MEMORY;")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS papers (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        arxiv_url     TEXT NOT NULL UNIQUE,
        title         TEXT,
        abstract      TEXT,
        subject       TEXT,
        publish_time  TEXT,   -- UTC 'YYYY-MM-DD HH:MM:SS'
        pdf_views     INTEGER NOT NULL DEFAULT 0,
        kimi_calls    INTEGER NOT NULL DEFAULT 0,
        notified      INTEGER NOT NULL DEFAULT 0,
        updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS paper_authors (
        paper_id     INTEGER NOT NULL,
        author_order INTEGER NOT NULL,
        author_name  TEXT NOT NULL,
        PRIMARY KEY (paper_id, author_order),
        FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
    );
    """)

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_papers_publish_time ON papers(publish_time);"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_subject ON papers(subject);")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_papers_updated_at ON papers(updated_at);"
    )
    # 迁移：为旧数据库增加 notified 字段
    try:
        conn.execute("ALTER TABLE papers ADD COLUMN notified INTEGER NOT NULL DEFAULT 0;")
    except sqlite3.OperationalError:
        pass  # 字段已存在

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_papers_notified ON papers(notified);"
    )

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_authors_name ON paper_authors(author_name);"
    )
    conn.commit()


def _upsert_paper(conn: sqlite3.Connection, row: Dict) -> int:
    """
    UPSERT papers，并返回 paper_id。
    如果记录已存在，仅更新动态字段（阅读量等），不重置 notified 状态。
    """
    conn.execute(
        """
    INSERT INTO papers (
        arxiv_url, title, abstract, subject,
        publish_time, pdf_views, kimi_calls, notified, updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, 0, datetime('now'))
    ON CONFLICT(arxiv_url) DO UPDATE SET
        pdf_views = excluded.pdf_views,
        kimi_calls = excluded.kimi_calls,
        updated_at = datetime('now');
    """,
        (
            row["arxiv_url"],
            row.get("title"),
            row.get("abstract"),
            row.get("subject"),
            row.get("publish_time"),
            int(row.get("pdf_views") or 0),
            int(row.get("kimi_calls") or 0),
        ),
    )

    paper_id_row = conn.execute(
        "SELECT id FROM papers WHERE arxiv_url = ?", (row["arxiv_url"],)
    ).fetchone()
    if not paper_id_row:
        raise RuntimeError(f"UPSERT 后未找到 paper_id: {row['arxiv_url']}")
    return int(paper_id_row[0])


def _replace_authors(
    conn: sqlite3.Connection, paper_id: int, authors: List[str]
) -> None:
    """
    替换该 paper 的作者列表（保留顺序）。
    """
    conn.execute("DELETE FROM paper_authors WHERE paper_id = ?", (paper_id,))
    if not authors:
        return
    conn.executemany(
        "INSERT INTO paper_authors (paper_id, author_order, author_name) VALUES (?, ?, ?)",
        [(paper_id, i + 1, name) for i, name in enumerate(authors)],
    )


def _select_main_container(root) -> LH.HtmlElement:
    """
    选包含最多 h2 的 body/div 作为论文列表容器（避免写死 /div[3]）。
    """
    body_divs = root.xpath("/html/body/div")
    if not body_divs:
        raise RuntimeError("HTML 结构异常：/html/body/div 为空")
    return max(body_divs, key=lambda d: len(d.xpath(".//h2")))


def fetch_and_upsert(
    web_url: str,
    db_path: str,
    timeout: int = 30,
) -> List[str]:
    """
    抓取网页并增量写入 sqlite。
    返回：本次抓到并写入的 arxiv_url 列表。
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    r = requests.get(web_url, headers=headers, timeout=timeout)
    r.raise_for_status()
    root = LH.fromstring(r.text)

    container = _select_main_container(root)

    blocks = container.xpath("./div[./h2]")
    if not blocks:
        blocks = container.xpath(".//div[./h2]")

    conn = sqlite3.connect(db_path)
    try:
        init_db(conn)

        arxiv_urls: List[str] = []

        for b in blocks:
            title = (b.xpath("normalize-space(./h2/a[2])") or "").strip()
            if not title:
                continue

            arxiv_data = b.xpath("./h2/a[3]/@data")
            if not arxiv_data:
                continue
            arxiv_url = (arxiv_data[0] or "").strip()
            if not arxiv_url:
                continue

            abstract = (b.xpath("normalize-space(./p[2])") or "").strip() or None
            subject = (b.xpath("normalize-space(./p[3]/span)") or "").strip() or None

            raw_publish_time = (
                b.xpath("normalize-space(./p[4]/span)") or ""
            ).strip() or None
            publish_time = parse_utc_time(raw_publish_time)

            pdf_views = _to_int("".join(b.xpath("./h2/a[3]/sup/text()")))
            kimi_calls = _to_int("".join(b.xpath("./h2/a[5]/sup/text()")))

            author_nodes = b.xpath("./p[1]/a")
            authors = [
                a.text_content().strip()
                for a in author_nodes
                if a.text_content().strip()
            ]

            paper_id = _upsert_paper(
                conn,
                {
                    "arxiv_url": arxiv_url,
                    "title": title,
                    "abstract": abstract,
                    "subject": subject,
                    "publish_time": publish_time,
                    "pdf_views": pdf_views,
                    "kimi_calls": kimi_calls,
                },
            )
            _replace_authors(conn, paper_id, authors)

            arxiv_urls.append(arxiv_url)

        conn.commit()
        return arxiv_urls
    finally:
        conn.close()
