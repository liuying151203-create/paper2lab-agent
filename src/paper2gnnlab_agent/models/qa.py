"""Single-paper citation QA schemas."""

from pydantic import BaseModel, Field

from paper2gnnlab_agent.models.common import Citation


class PaperQARequest(BaseModel):
    """Request body for single-paper QA."""

    question: str = Field(min_length=1)
    top_k: int = Field(default=6, ge=1, le=20)


class PaperQAResponse(BaseModel):
    paper_id: str
    question: str
    answer: str
    evidence_provider: str = "unknown"
    answer_mode: str = "unknown"
    citations: list[Citation] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
