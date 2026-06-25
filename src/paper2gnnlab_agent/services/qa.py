"""Single-paper citation-backed QA over local chunks."""

from __future__ import annotations

from paper2gnnlab_agent.models.chunk import Chunk
from paper2gnnlab_agent.models.common import Citation
from paper2gnnlab_agent.models.qa import PaperQAResponse
from paper2gnnlab_agent.services.evidence import (
    EvidenceProvider,
    LocalChunkEvidenceProvider,
    search_terms_for_question,
)
from paper2gnnlab_agent.services.llm import LlmClient, LlmGenerationError


class ChunkQAService:
    """Answer questions by retrieving relevant chunks and citing their evidence."""

    def __init__(
        self,
        answer_composer: AnswerComposer | None = None,
        evidence_provider: EvidenceProvider | None = None,
    ) -> None:
        self.answer_composer = answer_composer or ExtractiveAnswerComposer()
        self.evidence_provider = evidence_provider or LocalChunkEvidenceProvider()

    def answer(
        self,
        paper_id: str,
        question: str,
        chunks: list[Chunk],
        top_k: int = 6,
    ) -> PaperQAResponse:
        query_terms = search_terms_for_question(question)
        if not chunks:
            return PaperQAResponse(
                paper_id=paper_id,
                question=question,
                answer=(
                    "No chunks are available for this paper, "
                    "so the question cannot be answered."
                ),
                unsupported_claims=["No chunk evidence is available for this paper."],
            )
        if not query_terms:
            return PaperQAResponse(
                paper_id=paper_id,
                question=question,
                answer="The question does not contain searchable terms.",
                unsupported_claims=["Question has no searchable terms."],
            )

        citations = self.evidence_provider.retrieve(
            paper_id=paper_id,
            question=question,
            chunks=chunks,
            top_k=top_k,
        )
        if not citations:
            return PaperQAResponse(
                paper_id=paper_id,
                question=question,
                answer=(
                    "I could not find enough evidence in this paper's chunks "
                    "to answer the question."
                ),
                unsupported_claims=["No chunk matched the question terms."],
            )

        answer = self.answer_composer.compose(question=question, citations=citations)
        return PaperQAResponse(
            paper_id=paper_id,
            question=question,
            answer=answer,
            citations=citations,
            unsupported_claims=[],
        )


class AnswerComposer:
    """Compose an answer from already selected citation evidence."""

    def compose(self, question: str, citations: list[Citation]) -> str:
        raise NotImplementedError


class ExtractiveAnswerComposer(AnswerComposer):
    """Return a conservative evidence-only answer without model calls."""

    def compose(self, question: str, citations: list[Citation]) -> str:
        evidence_summary = " ".join(
            f"[{index}] {citation.evidence_text}"
            for index, citation in enumerate(citations, start=1)
        )
        return (
            "Based on the retrieved paper chunks, the relevant evidence is: "
            f"{evidence_summary}"
        )


class LlmAnswerComposer(AnswerComposer):
    """Use an LLM to write a concise answer constrained by citation evidence."""

    def __init__(self, client: LlmClient, fallback: AnswerComposer | None = None) -> None:
        self.client = client
        self.fallback = fallback or ExtractiveAnswerComposer()

    def compose(self, question: str, citations: list[Citation]) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are Paper2GNNLab-Agent, a GNN paper reading assistant. "
                    "Answer only using the provided citation evidence. "
                    "Do not introduce paper facts that are not supported by the evidence. "
                    "Write a concise answer for a researcher who wants to reproduce "
                    "GNN experiments. "
                    "When referring to evidence, use bracket markers like [1], [2]."
                ),
            },
            {
                "role": "user",
                "content": _build_qa_prompt(question=question, citations=citations),
            },
        ]
        try:
            return self.client.generate(messages=messages, temperature=0.0)
        except LlmGenerationError:
            return self.fallback.compose(question=question, citations=citations)


def _build_qa_prompt(question: str, citations: list[Citation]) -> str:
    evidence = "\n".join(
        (
            f"[{index}] paper_id={citation.paper_id}; chunk_id={citation.chunk_id}; "
            f"page={citation.page}; section={citation.section or 'unknown'}\n"
            f"{citation.evidence_text}"
        )
        for index, citation in enumerate(citations, start=1)
    )
    return f"Question: {question}\n\nCitation evidence:\n{evidence}\n\nAnswer:"
