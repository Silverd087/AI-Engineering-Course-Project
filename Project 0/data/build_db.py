"""Builds bookstore.db from schema.sql + seed.sql.

Usage:
    python data/build_db.py

Builds in a temp file first, then moves it into place -- some
filesystems (e.g. networked/synced folders) don't play well with
SQLite's journal files when the .db lives directly inside them.
"""
import shutil
import sqlite3
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
DB_PATH = HERE / "bookstore.db"
SCHEMA_PATH = HERE / "schema.sql"
SEED_PATH = HERE / "seed.sql"


def build():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_db = Path(tmp) / "bookstore.db"
        conn = sqlite3.connect(tmp_db)
        try:
            conn.executescript(SCHEMA_PATH.read_text())
            conn.executescript(SEED_PATH.read_text())
            conn.commit()
        finally:
            conn.close()
        shutil.copy(tmp_db, DB_PATH)
    print(f"Built {DB_PATH}")


if __name__ == "__main__":
    build()
