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

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    paper_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    page_start INTEGER NOT NULL,
    page_end INTEGER NOT NULL,
    section TEXT,
    text_path TEXT NOT NULL,
    evidence_text TEXT NOT NULL,
    token_count INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chunks_paper_id ON chunks(paper_id);
CREATE INDEX IF NOT EXISTS idx_chunks_paper_section ON chunks(paper_id, section);
"""


def connect(sqlite_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection and ensure the parent directory exists."""

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(sqlite_path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    return connection


def init_db(sqlite_path: Path) -> None:
    """Create MVP metadata tables when they do not exist."""

    with connect(sqlite_path) as connection:
        connection.executescript(SCHEMA_SQL)
