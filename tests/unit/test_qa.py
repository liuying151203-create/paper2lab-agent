from datetime import UTC, datetime

from paper2gnnlab_agent.models.chunk import Chunk
from paper2gnnlab_agent.models.common import Citation
from paper2gnnlab_agent.services.qa import ChunkQAService


def test_chunk_qa_returns_citations_for_matching_evidence() -> None:
    paper_id = "paper_qa123"
    chunks = [
        make_chunk(
            paper_id,
            "chunk_qa123_0001",
            1,
            "method",
            "The model uses a GCN encoder with attention for message passing.",
        ),
        make_chunk(
            paper_id,
            "chunk_qa123_0002",
            2,
            "experiments",
            "Experiments evaluate Cora and Citeseer using accuracy and F1.",
        ),
    ]

    response = ChunkQAService().answer(
        paper_id=paper_id,
        question="What datasets and metrics are used?",
        chunks=chunks,
        top_k=2,
    )

    assert response.unsupported_claims == []
    assert response.citations[0].chunk_id == "chunk_qa123_0002"
    assert "Cora" in response.answer
    assert response.citations[0].paper_id == paper_id


def test_chunk_qa_reports_unsupported_when_no_chunk_matches() -> None:
    response = ChunkQAService().answer(
        paper_id="paper_qa123",
        question="What optimizer is used?",
        chunks=[
            make_chunk(
                "paper_qa123",
                "chunk_qa123_0001",
                1,
                "method",
                "The model uses graph convolution layers.",
            )
        ],
    )

    assert response.citations == []
    assert response.unsupported_claims == ["No chunk matched the question terms."]


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
        evidence_text=text,
    )
    return Chunk(
        chunk_id=chunk_id,
        paper_id=paper_id,
        index=index,
        page_start=index,
        page_end=index,
        section=section,
        text=text,
        evidence_text=text,
        token_count=len(text.split()),
        citation=citation,
        created_at=datetime.now(UTC),
    )
