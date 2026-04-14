"""
Database module for Inventory Monitor
Currently unused — manual counts feature has been removed.
Kept as a stub in case DB is needed in the future.
"""

import os

DATABASE_URL = os.environ.get("DATABASE_URL")
USE_SQLITE = not DATABASE_URL

SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")


def get_connection():
    """Get database connection (PostgreSQL or SQLite)"""
    if USE_SQLITE:
        import sqlite3
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    else:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        return conn


def init_db():
    """Initialize database and create tables (currently no-op)"""
    # No tables to create — manual_counts table removed.
    pass
