"""Single-paper citation QA schemas."""

from pydantic import BaseModel, Field

from paper2gnnlab_agent.models.common import Citation


class PaperQARequest(BaseModel):
    paper_id: str
    question: str
    top_k: int = 6


class PaperQAResponse(BaseModel):
    paper_id: str
    question: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
