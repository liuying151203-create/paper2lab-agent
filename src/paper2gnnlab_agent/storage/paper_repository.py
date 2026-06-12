"""SQLite repository for paper metadata."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from paper2gnnlab_agent.models.paper import Paper
from paper2gnnlab_agent.storage.sqlite import connect, init_db


class PaperRepository:
    """Persist and load paper metadata from SQLite."""

    def __init__(self, sqlite_path: Path) -> None:
        self.sqlite_path = sqlite_path
        init_db(sqlite_path)

    def get_by_id(self, paper_id: str) -> Paper | None:
        query = "SELECT * FROM papers WHERE paper_id = ?"
        with connect(self.sqlite_path) as connection:
            row = connection.execute(query, (paper_id,)).fetchone()
        return _row_to_paper(row) if row else None

    def get_by_hash(self, file_hash: str) -> Paper | None:
        query = "SELECT * FROM papers WHERE file_hash = ?"
        with connect(self.sqlite_path) as connection:
            row = connection.execute(query, (file_hash,)).fetchone()
        return _row_to_paper(row) if row else None

    def list_recent(self, limit: int = 20) -> list[Paper]:
        """Return recently updated papers for local UI selection."""

        query = """
        SELECT * FROM papers
        ORDER BY updated_at DESC
        LIMIT ?
        """
        with connect(self.sqlite_path) as connection:
            rows = connection.execute(query, (limit,)).fetchall()
        return [_row_to_paper(row) for row in rows]

    def create(self, paper: Paper) -> Paper:
        query = """
        INSERT INTO papers (
            paper_id,
            file_hash,
            filename,
            title,
            authors_json,
            year,
            venue,
            abstract,
            source_path,
            status,
            created_at,
            updated_at,
            error_message
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        values = (
            paper.paper_id,
            paper.file_hash,
            paper.filename,
            paper.title,
            json.dumps(paper.authors, ensure_ascii=True),
            paper.year,
            paper.venue,
            paper.abstract,
            paper.source_path,
            paper.status,
            paper.created_at.isoformat(),
            paper.updated_at.isoformat(),
            paper.error_message,
        )
        with connect(self.sqlite_path) as connection:
            connection.execute(query, values)
        return paper

    def update_status(
        self,
        paper_id: str,
        status: str,
        error_message: str | None = None,
    ) -> Paper | None:
        query = """
        UPDATE papers
        SET status = ?, updated_at = ?, error_message = ?
        WHERE paper_id = ?
        """
        now = datetime.now(UTC).isoformat()
        with connect(self.sqlite_path) as connection:
            connection.execute(query, (status, now, error_message, paper_id))
        return self.get_by_id(paper_id)


def _row_to_paper(row: sqlite3.Row) -> Paper:
    return Paper(
        paper_id=row["paper_id"],
        file_hash=row["file_hash"],
        filename=row["filename"],
        title=row["title"],
        authors=json.loads(row["authors_json"]),
        year=row["year"],
        venue=row["venue"],
        abstract=row["abstract"],
        source_path=row["source_path"],
        status=row["status"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        error_message=row["error_message"],
    )
