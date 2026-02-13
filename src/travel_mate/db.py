from __future__ import annotations

import sqlite3
from pathlib import Path


def connect_sqlite(path: str | Path = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def apply_sqlite_migration(conn: sqlite3.Connection, migration_path: str | Path) -> None:
    sql = Path(migration_path).read_text(encoding="utf-8")
    conn.executescript(sql)
