import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_DIR = Path(__file__).resolve().parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "sherlock_history.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target TEXT NOT NULL,
                target_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                total_hits INTEGER NOT NULL,
                results_json TEXT NOT NULL
            )
        """)
        conn.commit()

def save_scan(target: str, target_type: str, results: list) -> int:
    init_db()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scans (target, target_type, created_at, total_hits, results_json)
            VALUES (?, ?, ?, ?, ?)
        """, (target, target_type, now_str, len(results), json.dumps(results, ensure_ascii=False)))
        conn.commit()
        return cursor.lastrowid

def get_all_scans(limit: int = 50) -> list:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, target, target_type, created_at, total_hits
            FROM scans
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def get_scan(scan_id: int) -> dict | None:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scans WHERE id = ?", (scan_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["results"] = json.loads(res["results_json"])
        del res["results_json"]
        return res

def delete_scan(scan_id: int) -> bool:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM scans WHERE id = ?", (scan_id,))
        conn.commit()
        return cursor.rowcount > 0

init_db()
