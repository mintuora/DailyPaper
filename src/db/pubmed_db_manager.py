import logging
import sqlite3
from typing import Dict, List

logger = logging.getLogger("DailyPaper")


class PubMedDBManager:
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
                CREATE TABLE IF NOT EXISTS pubmed_papers (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    pmid          TEXT NOT NULL UNIQUE,
                    pubmed_url    TEXT NOT NULL UNIQUE,
                    doi           TEXT,
                    pdf_url       TEXT,
                    title         TEXT,
                    abstract      TEXT,
                    journal       TEXT,
                    publish_time  TEXT,
                    notified      INTEGER NOT NULL DEFAULT 0,
                    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
                );
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pubmed_authors (
                    paper_id      INTEGER NOT NULL,
                    author_order  INTEGER NOT NULL,
                    author_name   TEXT NOT NULL,
                    PRIMARY KEY (paper_id, author_order),
                    FOREIGN KEY (paper_id) REFERENCES pubmed_papers(id) ON DELETE CASCADE
                );
                """
            )

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_pubmed_papers_publish_time ON pubmed_papers(publish_time);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_pubmed_papers_notified ON pubmed_papers(notified);"
            )
            conn.commit()

    def upsert_paper(self, row: Dict) -> int:
        pmid = (row.get("pmid") or row.get("external_id") or "").strip()
        pubmed_url = (row.get("pubmed_url") or row.get("arxiv_url") or "").strip()
        if not pmid or not pubmed_url:
            raise ValueError("PubMed 入库缺少 pmid 或 pubmed_url")

        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO pubmed_papers (
                    pmid, pubmed_url, doi, pdf_url,
                    title, abstract, journal,
                    publish_time, notified, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, datetime('now'))
                ON CONFLICT(pmid) DO UPDATE SET
                    pubmed_url = excluded.pubmed_url,
                    doi = COALESCE(excluded.doi, pubmed_papers.doi),
                    pdf_url = COALESCE(excluded.pdf_url, pubmed_papers.pdf_url),
                    title = COALESCE(excluded.title, pubmed_papers.title),
                    abstract = COALESCE(excluded.abstract, pubmed_papers.abstract),
                    journal = COALESCE(excluded.journal, pubmed_papers.journal),
                    publish_time = COALESCE(excluded.publish_time, pubmed_papers.publish_time),
                    updated_at = datetime('now');
                """,
                (
                    pmid,
                    pubmed_url,
                    row.get("doi"),
                    row.get("pdf_url"),
                    row.get("title"),
                    row.get("abstract"),
                    row.get("subject"),
                    row.get("publish_time"),
                ),
            )

            paper_id = conn.execute(
                "SELECT id FROM pubmed_papers WHERE pmid = ?",
                (pmid,),
            ).fetchone()[0]

            authors = row.get("authors") or []
            if isinstance(authors, str):
                authors = [a.strip() for a in authors.split(",") if a.strip()]

            conn.execute("DELETE FROM pubmed_authors WHERE paper_id = ?", (paper_id,))
            conn.executemany(
                "INSERT INTO pubmed_authors (paper_id, author_order, author_name) VALUES (?, ?, ?)",
                [(paper_id, i + 1, name) for i, name in enumerate(authors)],
            )

            conn.commit()
            return paper_id

    def mark_pending(self, pubmed_urls: List[str]) -> int:
        urls = [u for u in (pubmed_urls or []) if u]
        if not urls:
            return 0

        with self._get_conn() as conn:
            placeholders = ",".join(["?"] * len(urls))
            cur = conn.execute(
                f"UPDATE pubmed_papers SET notified = 1 WHERE pubmed_url IN ({placeholders}) AND notified != 2",
                (*urls,),
            )
            conn.commit()
            return int(cur.rowcount or 0)

    def update_status(self, pubmed_urls: List[str], status: int):
        urls = [u for u in (pubmed_urls or []) if u]
        if not urls:
            return

        with self._get_conn() as conn:
            placeholders = ",".join(["?"] * len(urls))
            conn.execute(
                f"UPDATE pubmed_papers SET notified = ? WHERE pubmed_url IN ({placeholders})",
                (status, *urls),
            )
            conn.commit()

    def get_pending_papers(self, limit: int = 100) -> List[Dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM pubmed_papers
                WHERE notified = 1
                ORDER BY publish_time DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

            papers: List[Dict] = []
            for row in rows:
                p = dict(row)
                authors = conn.execute(
                    "SELECT author_name FROM pubmed_authors WHERE paper_id = ? ORDER BY author_order",
                    (p["id"],),
                ).fetchall()
                p["authors"] = [a[0] for a in authors]
                papers.append(p)
            return papers
