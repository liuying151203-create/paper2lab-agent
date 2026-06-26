"""GNN-specific paper card schema."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from paper2gnnlab_agent.models.common import CitedValue


class ReproductionDifficulty(BaseModel):
    """Estimated reproduction difficulty and evidence-backed reasons."""

    level: Literal["low", "medium", "high", "unknown"]
    reasons: list[CitedValue] = Field(default_factory=list)


class PaperCard(BaseModel):
    """Structured GNN paper card with citation-backed fields."""

    paper_id: str
    extraction_method: Literal["rule_based", "llm", "reviewed", "unknown"] = "unknown"
    extraction_notes: list[str] = Field(default_factory=list)
    title: CitedValue | None = None
    problem: CitedValue | None = None
    task_type: list[CitedValue] = Field(default_factory=list)
    graph_type: list[CitedValue] = Field(default_factory=list)
    datasets: list[CitedValue] = Field(default_factory=list)
    node_types: list[CitedValue] = Field(default_factory=list)
    edge_types: list[CitedValue] = Field(default_factory=list)
    model_modules: list[CitedValue] = Field(default_factory=list)
    losses: list[CitedValue] = Field(default_factory=list)
    attacks: list[CitedValue] = Field(default_factory=list)
    defenses: list[CitedValue] = Field(default_factory=list)
    metrics: list[CitedValue] = Field(default_factory=list)
    baselines: list[CitedValue] = Field(default_factory=list)
    training_setup: list[CitedValue] = Field(default_factory=list)
    evaluation_protocol: list[CitedValue] = Field(default_factory=list)
    main_results: list[CitedValue] = Field(default_factory=list)
    limitations: list[CitedValue] = Field(default_factory=list)
    reproduction_difficulty: ReproductionDifficulty
    missing_implementation_details: list[CitedValue] = Field(default_factory=list)
    generated_at: datetime


class GeneratePaperCardRequest(BaseModel):
    """Request body for generating a GNN-specific paper card."""

    force: bool = False


class PaperCardResponse(BaseModel):
    """Response returned after generating or reading a paper card."""

    paper_id: str
    status: Literal["card_ready"]
    card: PaperCard
    reused: bool = False
