"""Citation-backed comparison over generated GNN PaperCards."""

from __future__ import annotations

from collections import Counter

from paper2gnnlab_agent.models.card import PaperCard
from paper2gnnlab_agent.models.common import Citation, CitedValue
from paper2gnnlab_agent.models.comparison import (
    DEFAULT_COMPARISON_DIMENSIONS,
    PaperComparisonResponse,
    PaperComparisonRow,
)

SUPPORTED_COMPARISON_DIMENSIONS = {
    "task_type",
    "graph_type",
    "datasets",
    "node_types",
    "edge_types",
    "model_modules",
    "losses",
    "attacks",
    "defenses",
    "metrics",
    "baselines",
    "training_setup",
    "evaluation_protocol",
    "main_results",
    "limitations",
    "missing_implementation_details",
    "reproduction_difficulty",
}


class PaperComparisonService:
    """Compare PaperCards across GNN reproduction dimensions."""

    def compare(
        self,
        cards: list[PaperCard],
        dimensions: list[str] | None = None,
    ) -> PaperComparisonResponse:
        selected_dimensions = _normalize_dimensions(dimensions)
        rows = [
            PaperComparisonRow(
                paper_id=card.paper_id,
                values={
                    dimension: _values_for_dimension(card, dimension)
                    for dimension in selected_dimensions
                },
            )
            for card in cards
        ]
        citations = _dedupe_citations(
            citation
            for row in rows
            for values in row.values.values()
            for value in values
            for citation in value.citations
        )
        return PaperComparisonResponse(
            dimensions=selected_dimensions,
            rows=rows,
            summary=_build_summary(rows, selected_dimensions),
            citations=citations,
        )


def _normalize_dimensions(dimensions: list[str] | None) -> list[str]:
    requested = dimensions or DEFAULT_COMPARISON_DIMENSIONS
    normalized: list[str] = []
    seen: set[str] = set()
    for dimension in requested:
        key = dimension.strip()
        if key not in SUPPORTED_COMPARISON_DIMENSIONS or key in seen:
            continue
        normalized.append(key)
        seen.add(key)
    if not normalized:
        return list(DEFAULT_COMPARISON_DIMENSIONS)
    return normalized


def _values_for_dimension(card: PaperCard, dimension: str) -> list[CitedValue]:
    if dimension == "reproduction_difficulty":
        citations = [
            citation
            for reason in card.reproduction_difficulty.reasons
            for citation in reason.citations
        ]
        return [
            CitedValue(
                value=card.reproduction_difficulty.level,
                citations=citations,
                confidence="unknown",
            )
        ]
    values = getattr(card, dimension)
    return list(values)


def _build_summary(rows: list[PaperComparisonRow], dimensions: list[str]) -> str:
    if not rows:
        return "No PaperCards were available for comparison."

    parts = [f"Compared {len(rows)} papers across {len(dimensions)} dimensions."]
    for dimension in dimensions:
        value_counts = Counter(
            value.value
            for row in rows
            for value in row.values.get(dimension, [])
            if value.value
        )
        if not value_counts:
            continue
        common = [value for value, count in value_counts.items() if count > 1]
        if common:
            parts.append(f"Shared {dimension}: {', '.join(sorted(common))}.")
        else:
            top_values = [value for value, _ in value_counts.most_common(3)]
            parts.append(f"Distinct {dimension}: {', '.join(top_values)}.")
    return " ".join(parts)


def _dedupe_citations(citations: object) -> list[Citation]:
    deduped: list[Citation] = []
    seen: set[tuple[str, str, str]] = set()
    for citation in citations:
        if not isinstance(citation, Citation):
            continue
        key = (citation.paper_id, citation.chunk_id, citation.evidence_text)
        if key in seen:
            continue
        deduped.append(citation)
        seen.add(key)
    return deduped
