"""Paper metadata and API response schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

PaperStatus = Literal[
    "uploaded",
    "parsing",
    "parsed",
    "chunked",
    "card_ready",
    "failed",
]


class Paper(BaseModel):
    """Metadata for one uploaded GNN paper."""

    paper_id: str
    file_hash: str
    filename: str
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    abstract: str | None = None
    source_path: str
    status: PaperStatus
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None


class PaperArtifacts(BaseModel):
    """Artifact readiness flags for paper detail responses."""

    chunks: bool = False
    paper_card: bool = False
    method_spec: bool = False


class PaperUploadResponse(BaseModel):
    """Response returned after a PDF upload or hash reuse."""

    paper_id: str
    file_hash: str
    filename: str
    status: PaperStatus
    reused: bool
    next_actions: list[str] = Field(default_factory=list)


class PaperDetailResponse(Paper):
    """Paper metadata enriched with artifact readiness."""

    artifacts: PaperArtifacts = Field(default_factory=PaperArtifacts)
