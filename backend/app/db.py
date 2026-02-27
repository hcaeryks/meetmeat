import os
import sqlite3
from pathlib import Path

DATABASE_PATH = os.environ.get("DATABASE_PATH", str(Path(__file__).parent.parent / "app.db"))


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    schema_path = Path(__file__).parent / "schema.sql"
    schema_sql = schema_path.read_text()
    conn = get_connection()
    try:
        conn.executescript(schema_sql)
        conn.commit()
        try:
            conn.execute("ALTER TABLE participants ADD COLUMN password_hash TEXT NULL")
            conn.commit()
        except Exception:
            pass
    finally:
        conn.close()
