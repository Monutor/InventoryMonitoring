"""
SQLite database for manual inventory counts
"""

import sqlite3
import os
from typing import Dict, List, Optional, Any
from datetime import datetime


# На Render используем persistent disk через переменную окружения
_DATA_DIR = os.environ.get("RENDER_DATA_DIR", os.path.dirname(__file__))
DB_PATH = os.path.join(_DATA_DIR, "inventory.db")


def get_connection() -> sqlite3.Connection:
    """Get database connection with row factory"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Initialize database and create tables"""
    conn = get_connection()
    try:
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
                is_manual BOOLEAN NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL,
                UNIQUE(group_id, store)
            )
        """)
        conn.execute("""
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
    """
    Insert or update a manual count record.
    Auto-calculates percentage from found_count / total_planned.
    """
    percentage = round((found_count / total_planned * 100), 1) if total_planned > 0 else 0
    
    conn = get_connection()
    try:
        cursor = conn.execute("""
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
        """, (
            group_id,
            store,
            found_count,
            surplus,
            shortage,
            defect,
            percentage,
            datetime.now().isoformat(),
        ))
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
            "updated_at": datetime.now().isoformat(),
        }
    finally:
        conn.close()


def delete_manual_count(group_id: str, store: str) -> bool:
    """Delete a manual count record. Returns True if deleted."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM manual_counts WHERE group_id = ? AND store = ?",
            (group_id, store)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_manual_count(group_id: str, store: str) -> Optional[Dict[str, Any]]:
    """Get a single manual count record"""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM manual_counts WHERE group_id = ? AND store = ?",
            (group_id, store)
        ).fetchone()
        
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def get_all_manual_counts() -> List[Dict[str, Any]]:
    """Get all manual count records"""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM manual_counts ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def merge_with_csv_data(csv_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merge CSV data with manual counts.
    For groups that have manual entries, override CSV data with manual data.
    """
    conn = get_connection()
    try:
        # Load all manual counts into a dict for fast lookup
        rows = conn.execute("SELECT * FROM manual_counts").fetchall()
        manual_lookup = {}
        for row in rows:
            key = (row["group_id"], row["store"])
            manual_lookup[key] = dict(row)
    finally:
        conn.close()
    
    merged = []
    for group in csv_groups:
        group_copy = dict(group)
        key = (group_copy.get("Группа ID", ""), group_copy.get("Магазин", ""))
        
        if key in manual_lookup:
            manual = manual_lookup[key]
            # Override with manual data
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
