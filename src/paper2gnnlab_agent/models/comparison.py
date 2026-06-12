"""Multi-paper comparison schemas."""

from pydantic import BaseModel, Field

from paper2gnnlab_agent.models.common import Citation, CitedValue

DEFAULT_COMPARISON_DIMENSIONS = [
    "task_type",
    "graph_type",
    "datasets",
    "model_modules",
    "attacks",
    "defenses",
    "metrics",
    "baselines",
    "reproduction_difficulty",
]


class PaperComparisonRequest(BaseModel):
    """Request body for comparing generated PaperCards."""

    paper_ids: list[str] = Field(min_length=2)
    dimensions: list[str] = Field(default_factory=lambda: list(DEFAULT_COMPARISON_DIMENSIONS))


class PaperComparisonRow(BaseModel):
    """One paper row in a horizontal comparison."""

    paper_id: str
    values: dict[str, list[CitedValue]] = Field(default_factory=dict)


class PaperComparisonResponse(BaseModel):
    """Citation-backed multi-paper comparison response."""

    dimensions: list[str]
    rows: list[PaperComparisonRow] = Field(default_factory=list)
    summary: str
    citations: list[Citation] = Field(default_factory=list)
