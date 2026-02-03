import sqlite3
import json
import sys
import argparse
from typing import List, Dict

def query_papers(db_path: str, notified: int = None, limit: int = 100) -> List[Dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        query = "SELECT * FROM papers"
        params = []
        if notified is not None:
            query += " WHERE notified = ?"
            params.append(notified)
        
        query += " ORDER BY publish_time DESC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        
        results = []
        for row in rows:
            d = dict(row)
            # 获取作者
            authors = conn.execute(
                "SELECT author_name FROM paper_authors WHERE paper_id = ? ORDER BY author_order",
                (d['id'],)
            ).fetchall()
            d['authors'] = [a[0] for a in authors]
            results.append(d)
        return results
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Query papers from SQLite for n8n")
    parser.add_argument("--db", default="data/papers.sqlite3", help="Path to sqlite3 database")
    parser.add_argument("--notified", type=int, choices=[0, 1], help="Filter by notified status (0 or 1)")
    parser.add_argument("--limit", type=int, default=10, help="Limit number of results")
    
    args = parser.parse_args()
    
    try:
        papers = query_papers(args.db, notified=args.notified, limit=args.limit)
        print(json.dumps(papers, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
