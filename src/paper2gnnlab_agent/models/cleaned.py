"""Cleaned paragraph-level text schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class CleanedParagraph(BaseModel):
    """A cleaned paragraph with page and recognized section metadata."""

    page: int
    section: str
    text: str


class CleanedPaper(BaseModel):
    """Cleaned paragraph-level artifact for a parsed paper."""

    paper_id: str
    paragraphs: list[CleanedParagraph] = Field(default_factory=list)
    cleaner: str
    cleaned_at: datetime


class CleanPaperRequest(BaseModel):
    """Request body for triggering text cleaning."""

    force: bool = False


class CleanPaperResponse(BaseModel):
    """Response returned after cleaning or reusing cleaned text."""

    paper_id: str
    status: str
    paragraphs_count: int
    sections: list[str] = Field(default_factory=list)
    reused: bool
