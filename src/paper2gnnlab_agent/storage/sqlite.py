"""SQLite connection and schema initialization."""

import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS papers (
    paper_id TEXT PRIMARY KEY,
    file_hash TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    title TEXT,
    authors_json TEXT NOT NULL DEFAULT '[]',
    year INTEGER,
    venue TEXT,
    abstract TEXT,
    source_path TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_papers_file_hash ON papers(file_hash);
"""


def connect(sqlite_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection and ensure the parent directory exists."""

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(sqlite_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(sqlite_path: Path) -> None:
    """Create MVP metadata tables when they do not exist."""

    with connect(sqlite_path) as connection:
        connection.executescript(SCHEMA_SQL)
