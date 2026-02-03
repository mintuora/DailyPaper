import sqlite3
import sys
import argparse
import json

def mark_as_notified(db_path: str, ids: list) -> int:
    """
    将指定的 ID 标记为已通知 (notified=1)
    """
    if not ids:
        return 0
    
    placeholders = ",".join(["?"] * len(ids))
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            f"UPDATE papers SET notified = 1 WHERE id IN ({placeholders})",
            ids,
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Mark papers as notified in SQLite by ID")
    parser.add_argument("--db", default="data/papers.sqlite3", help="Path to sqlite3 database")
    parser.add_argument("ids", nargs="*", type=int, help="List of paper IDs to mark as notified")
    parser.add_argument("--file", help="Path to a JSON file containing a list of IDs")

    args = parser.parse_args()
    
    ids = args.ids
    if args.file:
        try:
            with open(args.file, "r") as f:
                file_data = json.load(f)
                if isinstance(file_data, list):
                    ids.extend(file_data)
                elif isinstance(file_data, dict) and "ids" in file_data:
                    ids.extend(file_data["ids"])
        except Exception as e:
            print(json.dumps({"error": f"Failed to read file: {str(e)}"}), file=sys.stderr)
            sys.exit(1)

    if not ids:
        print(json.dumps({"status": "ignored", "message": "No IDs provided"}))
        return

    try:
        count = mark_as_notified(args.db, ids)
        print(json.dumps({"status": "success", "marked_count": count}))
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
