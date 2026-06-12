from datetime import UTC, datetime

from paper2gnnlab_agent.models.card import PaperCard, ReproductionDifficulty
from paper2gnnlab_agent.models.common import Citation, CitedValue
from paper2gnnlab_agent.services.comparison import PaperComparisonService


def test_compare_paper_cards_keeps_cited_values_by_dimension() -> None:
    cards = [
        make_card("paper_a", dataset="Cora", model="GCN", metric="accuracy"),
        make_card("paper_b", dataset="Cora", model="GAT", metric="F1"),
    ]

    response = PaperComparisonService().compare(
        cards=cards,
        dimensions=["datasets", "model_modules", "metrics", "reproduction_difficulty"],
    )

    assert response.dimensions == [
        "datasets",
        "model_modules",
        "metrics",
        "reproduction_difficulty",
    ]
    assert len(response.rows) == 2
    assert response.rows[0].values["datasets"][0].value == "Cora"
    assert response.rows[1].values["model_modules"][0].value == "GAT"
    assert response.citations
    assert "Shared datasets: Cora." in response.summary


def test_compare_paper_cards_ignores_unsupported_dimensions() -> None:
    response = PaperComparisonService().compare(
        cards=[make_card("paper_a", dataset="Cora", model="GCN", metric="accuracy")],
        dimensions=["datasets", "not_a_dimension"],
    )

    assert response.dimensions == ["datasets"]


def make_card(paper_id: str, dataset: str, model: str, metric: str) -> PaperCard:
    return PaperCard(
        paper_id=paper_id,
        datasets=[make_value(paper_id, "datasets", dataset)],
        model_modules=[make_value(paper_id, "method", model)],
        metrics=[make_value(paper_id, "experiments", metric)],
        reproduction_difficulty=ReproductionDifficulty(level="medium", reasons=[]),
        generated_at=datetime.now(UTC),
    )


def make_value(paper_id: str, section: str, value: str) -> CitedValue:
    return CitedValue(
        value=value,
        confidence="medium",
        citations=[
            Citation(
                paper_id=paper_id,
                chunk_id=f"chunk_{paper_id.removeprefix('paper_')}_0001",
                page=1,
                section=section,
                evidence_text=f"{value} evidence",
            )
        ],
    )
