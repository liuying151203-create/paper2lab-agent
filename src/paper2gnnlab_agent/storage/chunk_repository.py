"""SQLite repository for chunk metadata."""

import sqlite3
from datetime import datetime
from pathlib import Path

from paper2gnnlab_agent.models.chunk import Chunk
from paper2gnnlab_agent.models.common import Citation
from paper2gnnlab_agent.storage.sqlite import connect, init_db


class ChunkRepository:
    """Persist and query citation-ready chunk metadata."""

    def __init__(self, sqlite_path: Path) -> None:
        self.sqlite_path = sqlite_path
        init_db(sqlite_path)

    def replace_for_paper(self, paper_id: str, chunks: list[Chunk], text_path: Path) -> None:
        with connect(self.sqlite_path) as connection:
            connection.execute("DELETE FROM chunks WHERE paper_id = ?", (paper_id,))
            connection.executemany(
                """
                INSERT INTO chunks (
                    chunk_id,
                    paper_id,
                    chunk_index,
                    page_start,
                    page_end,
                    section,
                    text_path,
                    evidence_text,
                    token_count,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk.chunk_id,
                        chunk.paper_id,
                        chunk.index,
                        chunk.page_start,
                        chunk.page_end,
                        chunk.section,
                        str(text_path),
                        chunk.evidence_text,
                        chunk.token_count,
                        chunk.created_at.isoformat(),
                    )
                    for chunk in chunks
                ],
            )

    def count_for_paper(self, paper_id: str) -> int:
        with connect(self.sqlite_path) as connection:
            row = connection.execute(
                "SELECT count(*) AS chunk_count FROM chunks WHERE paper_id = ?",
                (paper_id,),
            ).fetchone()
        return int(row["chunk_count"])

    def list_for_paper(
        self,
        paper_id: str,
        section: str | None = None,
        page: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[int, list[Chunk]]:
        where = ["paper_id = ?"]
        values: list[object] = [paper_id]

        if section is not None:
            where.append("section = ?")
            values.append(section)
        if page is not None:
            where.append("page_start <= ? AND page_end >= ?")
            values.extend([page, page])

        where_sql = " AND ".join(where)
        with connect(self.sqlite_path) as connection:
            total = connection.execute(
                f"SELECT count(*) AS chunk_count FROM chunks WHERE {where_sql}",
                values,
            ).fetchone()["chunk_count"]
            rows = connection.execute(
                f"""
                SELECT * FROM chunks
                WHERE {where_sql}
                ORDER BY chunk_index
                LIMIT ? OFFSET ?
                """,
                [*values, limit, offset],
            ).fetchall()

        return int(total), [_row_to_chunk(row) for row in rows]


def _row_to_chunk(row: sqlite3.Row) -> Chunk:
    citation = Citation(
        paper_id=row["paper_id"],
        chunk_id=row["chunk_id"],
        page=row["page_start"],
        section=row["section"],
        evidence_text=row["evidence_text"],
    )
    return Chunk(
        chunk_id=row["chunk_id"],
        paper_id=row["paper_id"],
        index=row["chunk_index"],
        page_start=row["page_start"],
        page_end=row["page_end"],
        section=row["section"],
        text="",
        evidence_text=row["evidence_text"],
        token_count=row["token_count"],
        source_offsets=[],
        citation=citation,
        created_at=datetime.fromisoformat(row["created_at"]),
    )
