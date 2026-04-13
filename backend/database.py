"""
Database for manual inventory counts
- Uses PostgreSQL when DATABASE_URL is set (Neon.tech, production)
- Falls back to SQLite when DATABASE_URL is not set (local development)
"""

import os
import sqlite3
from typing import Dict, List, Optional, Any
from datetime import datetime

# Определяем режим: PostgreSQL или SQLite
DATABASE_URL = os.environ.get("DATABASE_URL")
USE_SQLITE = not DATABASE_URL

# Путь к SQLite базе
SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")


def get_connection():
    """Get database connection (PostgreSQL or SQLite)"""
    if USE_SQLITE:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row  # Для доступа по имени колонки
        return conn
    else:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(DATABASE_URL)
        return conn


def init_db():
    """Initialize database and create tables"""
    conn = get_connection()
    try:
        if USE_SQLITE:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS manual_counts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id TEXT NOT NULL,
                    store TEXT NOT NULL,
                    found_count INTEGER NOT NULL DEFAULT 0,
                    surplus INTEGER NOT NULL DEFAULT 0,
                    shortage INTEGER NOT NULL DEFAULT 0,
                    defect INTEGER NOT NULL DEFAULT 0,
                    percentage REAL NOT NULL DEFAULT 0,
                    is_manual INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL,
                    UNIQUE(group_id, store)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_manual_counts_group
                ON manual_counts(group_id, store)
            """)
        else:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS manual_counts (
                        id SERIAL PRIMARY KEY,
                        group_id TEXT NOT NULL,
                        store TEXT NOT NULL,
                        found_count INTEGER NOT NULL DEFAULT 0,
                        surplus INTEGER NOT NULL DEFAULT 0,
                        shortage INTEGER NOT NULL DEFAULT 0,
                        defect INTEGER NOT NULL DEFAULT 0,
                        percentage REAL NOT NULL DEFAULT 0,
                        is_manual BOOLEAN NOT NULL DEFAULT TRUE,
                        updated_at TEXT NOT NULL,
                        UNIQUE(group_id, store)
                    )
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_manual_counts_group
                    ON manual_counts(group_id, store)
                """)
        conn.commit()
    finally:
        conn.close()


def upsert_manual_count(
    group_id: str,
    store: str,
    found_count: int,
    total_planned: int,
    surplus: int = 0,
    shortage: int = 0,
    defect: int = 0,
) -> Dict[str, Any]:
    """Insert or update a manual count record."""
    percentage = round((found_count / total_planned * 100), 1) if total_planned > 0 else 0
    now = datetime.now().isoformat()

    conn = get_connection()
    try:
        if USE_SQLITE:
            conn.execute("""
                INSERT INTO manual_counts
                    (group_id, store, found_count, surplus, shortage, defect, percentage, is_manual, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(group_id, store) DO UPDATE SET
                    found_count = excluded.found_count,
                    surplus = excluded.surplus,
                    shortage = excluded.shortage,
                    defect = excluded.defect,
                    percentage = excluded.percentage,
                    updated_at = excluded.updated_at
            """, (group_id, store, found_count, surplus, shortage, defect, percentage, now))
            conn.commit()
        else:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO manual_counts
                        (group_id, store, found_count, surplus, shortage, defect, percentage, is_manual, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, %s)
                    ON CONFLICT(group_id, store) DO UPDATE SET
                        found_count = EXCLUDED.found_count,
                        surplus = EXCLUDED.surplus,
                        shortage = EXCLUDED.shortage,
                        defect = EXCLUDED.defect,
                        percentage = EXCLUDED.percentage,
                        updated_at = EXCLUDED.updated_at
                    RETURNING id
                """, (group_id, store, found_count, surplus, shortage, defect, percentage, now))
            conn.commit()

        return {
            "group_id": group_id,
            "store": store,
            "found_count": found_count,
            "surplus": surplus,
            "shortage": shortage,
            "defect": defect,
            "percentage": percentage,
            "is_manual": True,
            "updated_at": now,
        }
    finally:
        conn.close()


def delete_manual_count(group_id: str, store: str) -> bool:
    """Delete a manual count record. Returns True if deleted."""
    conn = get_connection()
    try:
        if USE_SQLITE:
            cursor = conn.execute(
                "DELETE FROM manual_counts WHERE group_id = ? AND store = ?",
                (group_id, store)
            )
            conn.commit()
            return cursor.rowcount > 0
        else:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM manual_counts WHERE group_id = %s AND store = %s",
                    (group_id, store)
                )
                conn.commit()
                return cur.rowcount > 0
    finally:
        conn.close()


def get_manual_count(group_id: str, store: str) -> Optional[Dict[str, Any]]:
    """Get a single manual count record"""
    conn = get_connection()
    try:
        if USE_SQLITE:
            cursor = conn.execute(
                "SELECT * FROM manual_counts WHERE group_id = ? AND store = ?",
                (group_id, store)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        else:
            from psycopg2.extras import RealDictCursor
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM manual_counts WHERE group_id = %s AND store = %s",
                    (group_id, store)
                )
                row = cur.fetchone()
                return dict(row) if row else None
    finally:
        conn.close()


def get_all_manual_counts() -> List[Dict[str, Any]]:
    """Get all manual count records"""
    conn = get_connection()
    try:
        if USE_SQLITE:
            cursor = conn.execute("SELECT * FROM manual_counts ORDER BY updated_at DESC")
            return [dict(row) for row in cursor.fetchall()]
        else:
            from psycopg2.extras import RealDictCursor
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM manual_counts ORDER BY updated_at DESC")
                return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def merge_with_csv_data(csv_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge CSV data with manual counts."""
    conn = get_connection()
    try:
        if USE_SQLITE:
            cursor = conn.execute("SELECT * FROM manual_counts")
            rows = cursor.fetchall()
        else:
            from psycopg2.extras import RealDictCursor
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM manual_counts")
                rows = cur.fetchall()
        
        manual_lookup = {}
        for row in rows:
            row_dict = dict(row)
            key = (row_dict["group_id"], row_dict["store"])
            manual_lookup[key] = row_dict
    finally:
        conn.close()

    merged = []
    for group in csv_groups:
        group_copy = dict(group)
        key = (group_copy.get("Группа ID", ""), group_copy.get("Магазин", ""))

        if key in manual_lookup:
            manual = manual_lookup[key]
            group_copy["Найдено"] = manual["found_count"]
            group_copy["Излишки"] = manual["surplus"]
            group_copy["Недостачи"] = manual["shortage"]
            group_copy["Брак"] = manual["defect"]
            group_copy["Доля"] = manual["percentage"]
            group_copy["Посчитано групп"] = 1 if manual["percentage"] > 0 else 0
            group_copy["is_manual"] = True
            group_copy["manual_updated_at"] = manual["updated_at"]
        else:
            group_copy["is_manual"] = False
            group_copy["manual_updated_at"] = None

        merged.append(group_copy)

    return merged
