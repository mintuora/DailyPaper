import sqlite3
import logging
from typing import List, Dict

logger = logging.getLogger("DailyPaper")


class DBManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")

            conn.execute(
                """
            CREATE TABLE IF NOT EXISTS papers (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                arxiv_url     TEXT NOT NULL UNIQUE,
                title         TEXT,
                abstract      TEXT,
                subject       TEXT,
                publish_time  TEXT,
                pdf_views     INTEGER NOT NULL DEFAULT 0,
                kimi_calls    INTEGER NOT NULL DEFAULT 0,
                notified      INTEGER NOT NULL DEFAULT 0,
                updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
            )

            conn.execute(
                """
            CREATE TABLE IF NOT EXISTS paper_authors (
                paper_id     INTEGER NOT NULL,
                author_order INTEGER NOT NULL,
                author_name  TEXT NOT NULL,
                PRIMARY KEY (paper_id, author_order),
                FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
            );
            """
            )

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_papers_publish_time ON papers(publish_time);"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_notified ON papers(notified);")

            conn.commit()

    def upsert_paper(self, row: Dict) -> int:
        with self._get_conn() as conn:
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

            paper_id = conn.execute(
                "SELECT id FROM papers WHERE arxiv_url = ?", (row["arxiv_url"],)
            ).fetchone()[0]

            if "authors" in row:
                conn.execute("DELETE FROM paper_authors WHERE paper_id = ?", (paper_id,))
                conn.executemany(
                    "INSERT INTO paper_authors (paper_id, author_order, author_name) VALUES (?, ?, ?)",
                    [(paper_id, i + 1, name) for i, name in enumerate(row["authors"])],
                )
            conn.commit()
            return paper_id

    def get_unnotified_papers(self, limit: int = 100) -> List[Dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT p.* FROM papers p
                WHERE p.notified = 1 
                ORDER BY p.publish_time DESC 
                LIMIT ?
            """,
                (limit,),
            ).fetchall()

            papers = []
            for row in rows:
                p = dict(row)
                authors = conn.execute(
                    "SELECT author_name FROM paper_authors WHERE paper_id = ? ORDER BY author_order",
                    (p["id"],),
                ).fetchall()
                p["authors"] = ", ".join([a[0] for a in authors])
                papers.append(p)
            return papers

    def update_status(self, arxiv_urls: List[str], status: int):
        if not arxiv_urls:
            return
        with self._get_conn() as conn:
            placeholders = ",".join(["?"] * len(arxiv_urls))
            conn.execute(
                f"UPDATE papers SET notified = ? WHERE arxiv_url IN ({placeholders})",
                (status, *arxiv_urls),
            )
            conn.commit()

    def mark_pending(self, arxiv_urls: List[str]) -> int:
        if not arxiv_urls:
            return 0
        with self._get_conn() as conn:
            placeholders = ",".join(["?"] * len(arxiv_urls))
            cur = conn.execute(
                f"UPDATE papers SET notified = 1 WHERE arxiv_url IN ({placeholders}) AND notified != 2",
                (*arxiv_urls,),
            )
            conn.commit()
            return int(cur.rowcount or 0)

    def mark_notified(self, arxiv_urls: List[str]):
        self.update_status(arxiv_urls, 2)
