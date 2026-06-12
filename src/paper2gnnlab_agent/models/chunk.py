"""Chunk schema for cleaned, citation-ready paper text."""

from datetime import datetime

from pydantic import BaseModel, Field

from paper2gnnlab_agent.models.common import Citation, SourceOffset


class Chunk(BaseModel):
    """A cleaned text chunk with page and section metadata."""

    chunk_id: str
    paper_id: str
    index: int
    page_start: int
    page_end: int
    section: str | None = None
    text: str
    evidence_text: str
    token_count: int | None = None
    source_offsets: list[SourceOffset] = Field(default_factory=list)
    citation: Citation
    created_at: datetime


class GenerateChunksRequest(BaseModel):
    """Request body for generating chunks from cleaned text."""

    force: bool = False
    max_chars: int = 1800


class GenerateChunksResponse(BaseModel):
    """Response returned after chunk generation or reuse."""

    paper_id: str
    status: str
    chunks_count: int
    reused: bool


class ChunkListResponse(BaseModel):
    """Paginated chunk list for API responses."""

    paper_id: str
    total: int
    items: list[Chunk] = Field(default_factory=list)
