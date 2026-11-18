#!/usr/bin/env python3
"""
db_manager.py
Database manager for Daily Editorial Aggregator & Analysis Agent.
Manages SQLite storage (editorials.db) with upsert deduplication by URL.
"""

import os
import sys
import json
import sqlite3
from typing import Dict, List, Any, Optional

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "editorials.db")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS editorials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    source TEXT NOT NULL,
    original_title TEXT NOT NULL,
    english_title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    theme TEXT NOT NULL,
    summary TEXT NOT NULL,
    key_bullet_points TEXT NOT NULL,
    scope TEXT NOT NULL,
    impact TEXT NOT NULL,
    other_characteristics TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_editorials_date ON editorials(date);
CREATE INDEX IF NOT EXISTS idx_editorials_source ON editorials(source);
CREATE INDEX IF NOT EXISTS idx_editorials_theme ON editorials(theme);
"""

def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Creates a connection to the SQLite database with row factory enabled."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initializes the database tables and indices."""
    with get_connection(db_path) as conn:
        conn.execute(CREATE_TABLE_SQL)
        conn.executescript(CREATE_INDEX_SQL)
        conn.commit()

def _serialize_field(value: Any) -> str:
    """Helper to convert complex types (dict/list) into formatted JSON strings."""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value) if value is not None else ""

def upsert_editorial(item: Dict[str, Any], db_path: str = DEFAULT_DB_PATH) -> bool:
    """
    Inserts or updates a single editorial based on unique URL.
    Returns True if operation succeeded.
    """
    init_db(db_path)
    
    url = item.get("url", "").strip()
    if not url:
        raise ValueError("Field 'url' is required for deduplication.")
    
    key_bullets = _serialize_field(item.get("key_bullet_points", []))
    impact = _serialize_field(item.get("impact", {}))
    other_char = _serialize_field(item.get("other_characteristics", {}))

    query = """
    INSERT INTO editorials (
        date, source, original_title, english_title, url,
        theme, summary, key_bullet_points, scope, impact,
        other_characteristics, created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(url) DO UPDATE SET
        date = excluded.date,
        source = excluded.source,
        original_title = excluded.original_title,
        english_title = excluded.english_title,
        theme = excluded.theme,
        summary = excluded.summary,
        key_bullet_points = excluded.key_bullet_points,
        scope = excluded.scope,
        impact = excluded.impact,
        other_characteristics = excluded.other_characteristics;
    """

    params = (
        item.get("date", ""),
        item.get("source", ""),
        item.get("original_title", ""),
        item.get("english_title", ""),
        url,
        item.get("theme", "General"),
        item.get("summary", ""),
        key_bullets,
        item.get("scope", "National"),
        impact,
        other_char,
    )

    with get_connection(db_path) as conn:
        conn.execute(query, params)
        conn.commit()
    return True

def upsert_editorials(items: List[Dict[str, Any]], db_path: str = DEFAULT_DB_PATH) -> int:
    """Upserts a list of editorials and returns the count of processed items."""
    count = 0
    for item in items:
        if upsert_editorial(item, db_path):
            count += 1
    return count

def get_all_editorials(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Retrieves all editorials ordered by date descending."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT * FROM editorials ORDER BY date DESC, id DESC;")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_editorials_by_date(target_date: str, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Retrieves editorials for a specific date (YYYY-MM-DD)."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT * FROM editorials WHERE date = ? ORDER BY id DESC;", (target_date,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_available_dates(db_path: str = DEFAULT_DB_PATH) -> List[str]:
    """Retrieves distinct dates available in the database in descending order."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT DISTINCT date FROM editorials ORDER BY date DESC;")
        return [row["date"] for row in cursor.fetchall()]

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python db_manager.py init")
        print("  python db_manager.py insert <file.json>")
        print("  python db_manager.py list")
        print("  python db_manager.py dates")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "init":
        init_db()
        print(f"Database initialized successfully at: {DEFAULT_DB_PATH}")

    elif cmd == "insert":
        if len(sys.argv) < 3:
            print("Error: JSON file path required. e.g. python db_manager.py insert data.json")
            sys.exit(1)
        json_file = sys.argv[2]
        if not os.path.isfile(json_file):
            print(f"Error: File not found: {json_file}")
            sys.exit(1)
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = data if isinstance(data, list) else [data]
        count = upsert_editorials(items)
        print(f"Successfully processed {count} editorial(s) into database.")

    elif cmd == "list":
        rows = get_all_editorials()
        print(f"Total editorials in database: {len(rows)}")
        for r in rows:
            print(f"[{r['date']}] ({r['source']}) {r['english_title']} | URL: {r['url']}")

    elif cmd == "dates":
        dates = get_available_dates()
        print("Available dates:", dates)

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
