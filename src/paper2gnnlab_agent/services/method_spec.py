"""Generate template-friendly method_spec.yaml from GNN paper artifacts."""

from __future__ import annotations

from typing import Any

from paper2gnnlab_agent.models.card import PaperCard
from paper2gnnlab_agent.models.common import Citation, CitedValue
from paper2gnnlab_agent.models.method import (
    AttackSpec,
    DatasetSpec,
    DefenseSpec,
    EvaluationSpec,
    MethodSpec,
    ModelModuleSpec,
    ReproductionPlan,
    TrainingSpec,
)


class MethodSpecService:
    """Convert PaperCard and ReproductionPlan artifacts into MethodSpec."""

    def generate(
        self,
        card: PaperCard,
        reproduction_plan: ReproductionPlan | None = None,
    ) -> MethodSpec:
        """Build a conservative method spec for later experiment scaffolding."""

        return MethodSpec(
            paper_id=card.paper_id,
            task_type=_values(card.task_type),
            graph_type=_values(card.graph_type),
            datasets=[
                DatasetSpec(
                    name=dataset.value,
                    preprocessing=_matching_plan_items(
                        reproduction_plan.data_preparation if reproduction_plan else [],
                        dataset.value,
                    ),
                    citations=dataset.citations,
                )
                for dataset in card.datasets
            ],
            node_types=_values(card.node_types),
            edge_types=_values(card.edge_types),
            model_modules=[
                ModelModuleSpec(
                    name=module.value,
                    role="gnn_module",
                    citations=module.citations,
                )
                for module in card.model_modules
            ],
            losses=_values(card.losses),
            attacks=[
                AttackSpec(name=attack.value, citations=attack.citations)
                for attack in card.attacks
            ],
            defenses=[
                DefenseSpec(name=defense.value, citations=defense.citations)
                for defense in card.defenses
            ],
            metrics=_values(card.metrics),
            baselines=_values(card.baselines),
            training=_build_training(card),
            evaluation=_build_evaluation(card, reproduction_plan),
            missing_details=_build_missing_details(card, reproduction_plan),
            citations=_collect_spec_citations(card),
        )


def dump_method_spec_yaml(spec: MethodSpec) -> str:
    """Serialize MethodSpec to deterministic YAML without external dependencies."""

    return _to_yaml(spec.model_dump(mode="json", exclude_none=True))


def _build_training(card: PaperCard) -> TrainingSpec | None:
    if not card.training_setup:
        return None
    return TrainingSpec(
        citations=_citations_from_values(card.training_setup),
    )


def _build_evaluation(
    card: PaperCard,
    reproduction_plan: ReproductionPlan | None,
) -> EvaluationSpec | None:
    if not card.metrics and not card.evaluation_protocol and not reproduction_plan:
        return None
    return EvaluationSpec(
        protocol="; ".join(_values(card.evaluation_protocol)) or None,
        metrics=_values(card.metrics),
        ablations=[
            item.item
            for item in (reproduction_plan.ablation_studies if reproduction_plan else [])
            if item.status in {"todo", "needs_manual_check"}
        ],
        citations=_citations_from_values(card.metrics + card.evaluation_protocol),
    )


def _build_missing_details(
    card: PaperCard,
    reproduction_plan: ReproductionPlan | None,
) -> list[str]:
    details = _values(card.missing_implementation_details)
    if reproduction_plan:
        for section in [
            reproduction_plan.environment,
            reproduction_plan.training_pipeline,
            reproduction_plan.risks,
            reproduction_plan.missing_details,
        ]:
            for item in section:
                if item.status in {"blocked", "needs_manual_check"}:
                    details.append(item.item)
    return _deduplicate(details)


def _matching_plan_items(items: list[Any], value: str) -> list[str]:
    value_lower = value.lower()
    return [item.item for item in items if value_lower in item.item.lower()]


def _values(values: list[CitedValue]) -> list[str]:
    return [value.value for value in values]


def _collect_spec_citations(card: PaperCard) -> list[Citation]:
    values = [
        *(card.title and [card.title] or []),
        *(card.problem and [card.problem] or []),
        *card.task_type,
        *card.graph_type,
        *card.datasets,
        *card.node_types,
        *card.edge_types,
        *card.model_modules,
        *card.losses,
        *card.attacks,
        *card.defenses,
        *card.metrics,
        *card.baselines,
        *card.training_setup,
        *card.evaluation_protocol,
        *card.main_results,
        *card.limitations,
        *card.reproduction_difficulty.reasons,
        *card.missing_implementation_details,
    ]
    return _citations_from_values(values)


def _citations_from_values(values: list[CitedValue]) -> list[Citation]:
    citations: list[Citation] = []
    seen: set[tuple[str, str]] = set()
    for value in values:
        for citation in value.citations:
            key = (citation.paper_id, citation.chunk_id)
            if key not in seen:
                seen.add(key)
                citations.append(citation)
    return citations


def _deduplicate(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _to_yaml(value: Any, indent: int = 0) -> str:
    lines = _yaml_lines(value, indent)
    return "\n".join(lines) + "\n"


def _yaml_lines(value: Any, indent: int) -> list[str]:
    prefix = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, dict):
                lines.append(f"{prefix}{key}:")
                lines.extend(_yaml_lines(item, indent + 2))
            elif isinstance(item, list):
                if item:
                    lines.append(f"{prefix}{key}:")
                    lines.extend(_yaml_lines(item, indent + 2))
                else:
                    lines.append(f"{prefix}{key}: []")
            else:
                lines.append(f"{prefix}{key}: {_format_scalar(item)}")
        return lines
    if isinstance(value, list):
        if not value:
            return [f"{prefix}[]"]
        lines = []
        for item in value:
            if isinstance(item, dict):
                lines.append(f"{prefix}-")
                lines.extend(_yaml_lines(item, indent + 2))
            elif isinstance(item, list):
                lines.append(f"{prefix}-")
                lines.extend(_yaml_lines(item, indent + 2))
            else:
                lines.append(f"{prefix}- {_format_scalar(item)}")
        return lines
    return [f"{prefix}{_format_scalar(value)}"]


def _format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    text = str(value)
    if not text:
        return '""'
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
