from datetime import UTC, datetime

from paper2gnnlab_agent.models.card import PaperCard, ReproductionDifficulty
from paper2gnnlab_agent.models.common import Citation, CitedValue
from paper2gnnlab_agent.services.card_quality import PaperCardQualityService


def test_card_quality_reports_completeness_citation_coverage_and_golden_scores() -> None:
    card = PaperCard(
        paper_id="paper_quality",
        task_type=[value("node classification", "experiments")],
        graph_type=[value("heterogeneous graph", "abstract")],
        datasets=[value("ACM", "experiments"), CitedValue(value="DBLP")],
        model_modules=[value("HAN", "abstract")],
        metrics=[value("Macro-F1", "experiments")],
        baselines=[value("GCN", "related_work")],
        reproduction_difficulty=ReproductionDifficulty(level="medium"),
        generated_at=datetime.now(UTC),
    )

    report = PaperCardQualityService().evaluate(
        card,
        golden={
            "datasets": ["ACM", "DBLP", "IMDB"],
            "model_modules": ["HAN"],
        },
    )

    assert report.completeness == 1.0
    assert report.citation_coverage < 1.0
    assert report.golden_available is True
    assert report.suspicious_values_count == 2
    assert report.macro_recall is not None
    assert any(field.field == "datasets" and field.recall == 0.667 for field in report.fields)
    assert report.warnings


def value(text: str, section: str) -> CitedValue:
    return CitedValue(
        value=text,
        citations=[
            Citation(
                paper_id="paper_quality",
                chunk_id=f"chunk_{section}",
                page=1,
                section=section,
                evidence_text=text,
            )
        ],
        confidence="medium",
    )
