from datetime import UTC, datetime
from typing import Any

from paper2gnnlab_agent.models.chunk import Chunk
from paper2gnnlab_agent.models.common import Citation
from paper2gnnlab_agent.services.evidence import GraphRagEvidenceProvider, search_terms_for_question
from paper2gnnlab_agent.services.papers import build_qa_service_from_settings
from paper2gnnlab_agent.services.qa import ChunkQAService, LlmAnswerComposer


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


def test_chunk_qa_can_compose_answer_with_llm_client() -> None:
    paper_id = "paper_qa123"
    response = ChunkQAService(answer_composer=LlmAnswerComposer(FakeLlmClient())).answer(
        paper_id=paper_id,
        question="What datasets are used?",
        chunks=[
            make_chunk(
                paper_id,
                "chunk_qa123_0001",
                1,
                "experiments",
                "Experiments use Cora and Citeseer for node classification.",
            )
        ],
    )

    assert response.answer == "The paper evaluates on Cora and Citeseer. [1]"
    assert response.evidence_provider == "local_chunks"
    assert response.answer_mode == "llm"
    assert response.citations[0].chunk_id == "chunk_qa123_0001"


def test_chunk_qa_supports_common_chinese_research_questions() -> None:
    paper_id = "paper_qa123"

    response = ChunkQAService().answer(
        paper_id=paper_id,
        question="这篇论文用了哪些数据集和指标？",
        chunks=[
            make_chunk(
                paper_id,
                "chunk_qa123_0001",
                1,
                "experiments",
                "Experiments evaluate ACM and DBLP using Micro-F1 and Macro-F1.",
            )
        ],
    )

    assert response.unsupported_claims == []
    assert response.evidence_provider == "local_chunks"
    assert response.answer_mode == "extractive"
    assert response.citations[0].chunk_id == "chunk_qa123_0001"
    assert "ACM and DBLP" in response.answer


def test_search_terms_for_question_expands_chinese_keywords() -> None:
    terms = search_terms_for_question("模型的攻击和防御指标是什么？")

    assert "model" in terms
    assert "attack" in terms
    assert "defense" in terms
    assert "metrics" in terms


def test_chunk_qa_can_use_custom_evidence_provider() -> None:
    paper_id = "paper_qa123"
    service = ChunkQAService(evidence_provider=FakeEvidenceProvider())

    response = service.answer(
        paper_id=paper_id,
        question="What evidence comes from the adapter?",
        chunks=[
            make_chunk(
                paper_id,
                "chunk_qa123_0001",
                1,
                "method",
                "This local chunk should not be selected by the fake provider.",
            )
        ],
    )

    assert response.unsupported_claims == []
    assert response.citations[0].chunk_id == "external_chunk_1"
    assert "adapter-selected evidence" in response.answer


def test_graphrag_provider_converts_response_to_citations(monkeypatch: Any) -> None:
    provider = GraphRagEvidenceProvider(
        base_url="http://127.0.0.1:9000",
        endpoint="/retrieve",
    )

    def fake_urlopen(request: Any, timeout: float) -> FakeHttpResponse:
        assert request.full_url == "http://127.0.0.1:9000/retrieve"
        assert timeout == 30.0
        return FakeHttpResponse(
            {
                "results": [
                    {
                        "paper_id": "paper_qa123",
                        "chunk_id": "chunk_graph_1",
                        "page": "7",
                        "section": "experiments",
                        "text": "GraphRAG evidence mentions ACM and Micro-F1.",
                    }
                ]
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    citations = provider.retrieve(
        paper_id="paper_qa123",
        question="Which dataset and metric?",
        chunks=[],
        top_k=3,
    )

    assert citations == [
        Citation(
            paper_id="paper_qa123",
            chunk_id="chunk_graph_1",
            page=7,
            section="experiments",
            evidence_text="GraphRAG evidence mentions ACM and Micro-F1.",
        )
    ]


def test_graphrag_provider_falls_back_to_local_chunks(monkeypatch: Any) -> None:
    def failing_urlopen(request: Any, timeout: float) -> FakeHttpResponse:
        raise OSError("GraphRAG service unavailable")

    monkeypatch.setattr("urllib.request.urlopen", failing_urlopen)

    paper_id = "paper_qa123"
    citations = GraphRagEvidenceProvider(
        base_url="http://127.0.0.1:9000",
    ).retrieve(
        paper_id=paper_id,
        question="What datasets are used?",
        chunks=[
            make_chunk(
                paper_id,
                "chunk_qa123_0001",
                1,
                "experiments",
                "Experiments use ACM and DBLP datasets.",
            )
        ],
    )

    assert citations[0].chunk_id == "chunk_qa123_0001"
    assert "ACM and DBLP" in citations[0].evidence_text


def test_build_qa_service_can_configure_graphrag_provider() -> None:
    service = build_qa_service_from_settings(
        model_provider=None,
        model_name=None,
        model_base_url=None,
        api_key=None,
        evidence_provider="graphrag",
        graphrag_base_url="http://127.0.0.1:9000",
    )

    assert isinstance(service.evidence_provider, GraphRagEvidenceProvider)


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


class FakeLlmClient:
    def generate(self, messages: list[dict[str, str]], temperature: float = 0.0) -> str:
        assert temperature == 0.0
        assert "Citation evidence" in messages[1]["content"]
        return "The paper evaluates on Cora and Citeseer. [1]"


class FakeEvidenceProvider:
    def retrieve(
        self,
        paper_id: str,
        question: str,
        chunks: list[Chunk],
        top_k: int = 6,
    ) -> list[Citation]:
        return [
            Citation(
                paper_id=paper_id,
                chunk_id="external_chunk_1",
                page=9,
                section="adapter",
                evidence_text="This is adapter-selected evidence.",
            )
        ]


class FakeHttpResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeHttpResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        import json

        return json.dumps(self.payload).encode("utf-8")
