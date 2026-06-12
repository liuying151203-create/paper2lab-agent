"""Parsed page-level text schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class ParsedPage(BaseModel):
    """Text extracted from one PDF page."""

    page: int
    text: str


class ParsedPaper(BaseModel):
    """Page-level parsed text artifact for a paper."""

    paper_id: str
    pages: list[ParsedPage] = Field(default_factory=list)
    parser: str
    parsed_at: datetime


class ParsePaperRequest(BaseModel):
    """Request body for triggering PDF parsing."""

    force: bool = False


class ParsePaperResponse(BaseModel):
    """Response returned after parsing or reusing parsed text."""

    paper_id: str
    status: str
    pages_count: int
    reused: bool
