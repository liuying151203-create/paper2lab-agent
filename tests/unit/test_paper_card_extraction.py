from datetime import UTC, datetime

from paper2gnnlab_agent.models.chunk import Chunk
from paper2gnnlab_agent.models.common import Citation
from paper2gnnlab_agent.services.card_extraction import RuleBasedPaperCardExtractor


def test_rule_based_card_extractor_finds_gnn_fields_with_citations() -> None:
    paper_id = "paper_card123"
    chunks = [
        make_chunk(
            paper_id,
            "chunk_card123_0001",
            1,
            "abstract",
            (
                "We propose a graph neural network for node classification on Cora and "
                "Citeseer. The method uses a GCN encoder with cross-entropy loss."
            ),
        ),
        make_chunk(
            paper_id,
            "chunk_card123_0002",
            2,
            "experiments",
            (
                "We compare against GAT, GraphSAGE, and MLP baselines. Accuracy and F1 "
                "are reported under a train/validation/test split with Adam optimizer, "
                "learning rate 0.01, and 200 epochs. Results outperform prior methods."
            ),
        ),
    ]

    card = RuleBasedPaperCardExtractor().extract(paper_id, chunks)

    assert card.paper_id == paper_id
    assert [item.value for item in card.task_type] == ["node classification"]
    assert [item.value for item in card.datasets] == ["Cora", "Citeseer"]
    assert "GCN" in [item.value for item in card.model_modules]
    assert "accuracy" in [item.value for item in card.metrics]
    assert card.reproduction_difficulty.level == "low"
    assert card.task_type[0].citations[0].paper_id == paper_id
    assert card.task_type[0].citations[0].chunk_id == "chunk_card123_0001"


def make_chunk(
    paper_id: str,
    chunk_id: str,
    index: int,
    section: str,
    text: str,
) -> Chunk:
    citation = Citation(
        paper_id=paper_id,
        chunk_id=chunk_id,
        page=index,
        section=section,
        evidence_text=text[:160],
    )
    return Chunk(
        chunk_id=chunk_id,
        paper_id=paper_id,
        index=index,
        page_start=index,
        page_end=index,
        section=section,
        text=text,
        evidence_text=text[:160],
        token_count=len(text.split()),
        citation=citation,
        created_at=datetime.now(UTC),
    )
