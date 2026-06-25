"""Explainable quality checks for generated and reviewed PaperCards."""

from __future__ import annotations

from collections.abc import Mapping

from paper2gnnlab_agent.models.card import PaperCard
from paper2gnnlab_agent.models.common import CitedValue
from paper2gnnlab_agent.models.quality import FieldQuality, PaperCardQualityReport

REQUIRED_REPRODUCTION_FIELDS = [
    "task_type",
    "graph_type",
    "datasets",
    "model_modules",
    "metrics",
    "baselines",
]

REVIEW_FIELDS = [
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
]

LOW_TRUST_SECTIONS = {"related_work", "unknown"}


class PaperCardQualityService:
    """Score PaperCards with transparent field-level checks."""

    def evaluate(
        self,
        card: PaperCard,
        golden: Mapping[str, list[str]] | None = None,
    ) -> PaperCardQualityReport:
        golden = golden or {}
        field_reports = [
            _evaluate_field(field_name, getattr(card, field_name), golden.get(field_name, []))
            for field_name in REVIEW_FIELDS
        ]
        required_reports = [
            report for report in field_reports if report.field in REQUIRED_REPRODUCTION_FIELDS
        ]
        completeness = _ratio(
            sum(not report.missing for report in required_reports),
            len(required_reports),
        )
        total_values = sum(report.values_count for report in field_reports)
        total_cited_values = sum(report.cited_values_count for report in field_reports)
        citation_coverage = _ratio(total_cited_values, total_values)
        suspicious_values_count = sum(len(report.suspicious_values) for report in field_reports)

        warnings = _build_warnings(field_reports, completeness, citation_coverage)
        precision_scores = [
            report.precision for report in field_reports if report.precision is not None
        ]
        recall_scores = [report.recall for report in field_reports if report.recall is not None]

        return PaperCardQualityReport(
            paper_id=card.paper_id,
            completeness=completeness,
            citation_coverage=citation_coverage,
            suspicious_values_count=suspicious_values_count,
            fields=field_reports,
            warnings=warnings,
            golden_available=bool(golden),
            macro_precision=_average(precision_scores) if precision_scores else None,
            macro_recall=_average(recall_scores) if recall_scores else None,
        )


def _evaluate_field(
    field_name: str,
    values: list[CitedValue],
    expected_values: list[str],
) -> FieldQuality:
    normalized_values = {_normalize(value.value): value.value for value in values if value.value}
    normalized_expected = {
        _normalize(value): value for value in expected_values if value.strip()
    }
    matched = sorted(
        normalized_expected[key]
        for key in normalized_expected.keys() & normalized_values.keys()
    )
    cited_count = sum(bool(value.citations) for value in values)
    suspicious = [
        value.value
        for value in values
        if _has_suspicious_evidence(value) or not value.citations
    ]

    precision = None
    recall = None
    if normalized_expected:
        precision = _ratio(len(matched), len(normalized_values))
        recall = _ratio(len(matched), len(normalized_expected))

    return FieldQuality(
        field=field_name,
        values_count=len(values),
        cited_values_count=cited_count,
        missing=field_name in REQUIRED_REPRODUCTION_FIELDS and not values,
        citation_coverage=_ratio(cited_count, len(values)),
        suspicious_values=sorted(set(suspicious)),
        expected_values=sorted(normalized_expected.values()),
        matched_expected_values=matched,
        precision=precision,
        recall=recall,
    )


def _has_suspicious_evidence(value: CitedValue) -> bool:
    return any(
        (citation.section or "unknown").lower() in LOW_TRUST_SECTIONS
        for citation in value.citations
    )


def _build_warnings(
    fields: list[FieldQuality],
    completeness: float,
    citation_coverage: float,
) -> list[str]:
    warnings: list[str] = []
    missing = [field.field for field in fields if field.missing]
    if missing:
        warnings.append(f"Missing required reproduction fields: {', '.join(missing)}.")
    if completeness < 1.0:
        warnings.append("PaperCard is incomplete for reproduction planning.")
    if citation_coverage < 1.0:
        warnings.append("Some extracted values have no citation evidence.")
    suspicious_count = sum(len(field.suspicious_values) for field in fields)
    if suspicious_count:
        warnings.append(
            "Some values are supported only by low-trust sections such as related_work "
            "or unknown, or have no citation."
        )
    return warnings


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return round(numerator / denominator, 3)


def _average(values: list[float]) -> float:
    return round(sum(values) / len(values), 3)
