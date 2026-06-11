"""Chunk schema for cleaned, citation-ready paper text."""

from datetime import datetime

from pydantic import BaseModel, Field

from paper2gnnlab_agent.models.common import SourceOffset


class Chunk(BaseModel):
    """A cleaned text chunk with page and section metadata."""

    chunk_id: str
    paper_id: str
    index: int
    page_start: int
    page_end: int
    section: str | None = None
    text: str
    token_count: int | None = None
    source_offsets: list[SourceOffset] = Field(default_factory=list)
    created_at: datetime
