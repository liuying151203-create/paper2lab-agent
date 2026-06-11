"""Shared citation-oriented schema primitives."""

from typing import Literal

from pydantic import BaseModel, Field


class SourceOffset(BaseModel):
    """Source text offsets for later evidence reconstruction."""

    page: int
    char_start: int | None = None
    char_end: int | None = None


class Citation(BaseModel):
    """A traceable evidence citation into a paper chunk."""

    paper_id: str
    chunk_id: str
    page: int | None = None
    section: str | None = None
    evidence_text: str


class CitedValue(BaseModel):
    """A structured value with citations and uncertainty."""

    value: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low", "unknown"] = "unknown"
