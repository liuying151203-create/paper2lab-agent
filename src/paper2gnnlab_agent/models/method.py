"""Method specification and reproduction planning schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from paper2gnnlab_agent.models.common import Citation


class DatasetSpec(BaseModel):
    name: str
    split: str | None = None
    preprocessing: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class ModelModuleSpec(BaseModel):
    name: str
    role: str | None = None
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class AttackSpec(BaseModel):
    name: str
    threat_model: str | None = None
    perturbation_budget: str | None = None
    target: str | None = None
    citations: list[Citation] = Field(default_factory=list)


class DefenseSpec(BaseModel):
    name: str
    strategy: str | None = None
    citations: list[Citation] = Field(default_factory=list)


class TrainingSpec(BaseModel):
    optimizer: str | None = None
    learning_rate: str | None = None
    epochs: str | None = None
    batch_size: str | None = None
    hardware: str | None = None
    citations: list[Citation] = Field(default_factory=list)


class EvaluationSpec(BaseModel):
    protocol: str | None = None
    metrics: list[str] = Field(default_factory=list)
    ablations: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class MethodSpec(BaseModel):
    paper_id: str
    task_type: list[str] = Field(default_factory=list)
    graph_type: list[str] = Field(default_factory=list)
    datasets: list[DatasetSpec] = Field(default_factory=list)
    node_types: list[str] = Field(default_factory=list)
    edge_types: list[str] = Field(default_factory=list)
    model_modules: list[ModelModuleSpec] = Field(default_factory=list)
    losses: list[str] = Field(default_factory=list)
    attacks: list[AttackSpec] = Field(default_factory=list)
    defenses: list[DefenseSpec] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    baselines: list[str] = Field(default_factory=list)
    training: TrainingSpec | None = None
    evaluation: EvaluationSpec | None = None
    missing_details: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class ChecklistItem(BaseModel):
    item: str
    status: Literal["todo", "blocked", "needs_manual_check"] = "todo"
    rationale: str | None = None
    citations: list[Citation] = Field(default_factory=list)


class ReproductionPlan(BaseModel):
    paper_id: str
    objective: str
    environment: list[ChecklistItem] = Field(default_factory=list)
    data_preparation: list[ChecklistItem] = Field(default_factory=list)
    model_implementation: list[ChecklistItem] = Field(default_factory=list)
    attack_or_defense_setup: list[ChecklistItem] = Field(default_factory=list)
    training_pipeline: list[ChecklistItem] = Field(default_factory=list)
    evaluation: list[ChecklistItem] = Field(default_factory=list)
    ablation_studies: list[ChecklistItem] = Field(default_factory=list)
    risks: list[ChecklistItem] = Field(default_factory=list)
    missing_details: list[ChecklistItem] = Field(default_factory=list)
    estimated_difficulty: Literal["low", "medium", "high", "unknown"]
    generated_at: datetime


class GenerateReproductionPlanRequest(BaseModel):
    """Request body for generating a GNN reproduction checklist."""

    force: bool = False


class ReproductionPlanResponse(BaseModel):
    """Response returned after generating or reading a reproduction plan."""

    paper_id: str
    status: Literal["reproduction_plan_ready"]
    plan: ReproductionPlan
    reused: bool = False
