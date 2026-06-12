"""Single-paper citation-backed QA over local chunks."""

from __future__ import annotations

import re
from collections import Counter

from paper2gnnlab_agent.models.chunk import Chunk
from paper2gnnlab_agent.models.common import Citation
from paper2gnnlab_agent.models.qa import PaperQAResponse
from paper2gnnlab_agent.services.llm import LlmClient, LlmGenerationError


class ChunkQAService:
    """Answer questions by retrieving relevant chunks and citing their evidence."""

    def __init__(self, answer_composer: AnswerComposer | None = None) -> None:
        self.answer_composer = answer_composer or ExtractiveAnswerComposer()

    def answer(
        self,
        paper_id: str,
        question: str,
        chunks: list[Chunk],
        top_k: int = 6,
    ) -> PaperQAResponse:
        query_terms = _expand_query_terms(_tokenize(question))
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

        ranked = _rank_chunks(chunks, query_terms)
        selected = [chunk for chunk, score in ranked[:top_k] if score > 0]
        if not selected:
            return PaperQAResponse(
                paper_id=paper_id,
                question=question,
                answer=(
                    "I could not find enough evidence in this paper's chunks "
                    "to answer the question."
                ),
                unsupported_claims=["No chunk matched the question terms."],
            )

        citations = [_citation_for_question(chunk, query_terms) for chunk in selected]
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


def _rank_chunks(chunks: list[Chunk], query_terms: list[str]) -> list[tuple[Chunk, float]]:
    query_counts = Counter(query_terms)
    ranked: list[tuple[Chunk, float]] = []
    for chunk in chunks:
        chunk_terms = Counter(_tokenize(chunk.text))
        overlap = sum(min(chunk_terms[term], count) for term, count in query_counts.items())
        section_bonus = _section_bonus(chunk.section, query_terms)
        ranked.append((chunk, overlap + section_bonus))
    return sorted(ranked, key=lambda item: (-item[1], item[0].index))


def _citation_for_question(chunk: Chunk, query_terms: list[str]) -> Citation:
    sentence = _best_sentence(chunk.text, query_terms) or chunk.evidence_text
    return Citation(
        paper_id=chunk.paper_id,
        chunk_id=chunk.chunk_id,
        page=chunk.page_start,
        section=chunk.section,
        evidence_text=_compact(sentence)[:300],
    )


def _best_sentence(text: str, query_terms: list[str]) -> str | None:
    best_sentence: str | None = None
    best_score = 0
    query_set = set(query_terms)
    for sentence in _sentences(text):
        sentence_terms = set(_tokenize(sentence))
        score = len(query_set & sentence_terms)
        if score > best_score:
            best_sentence = sentence
            best_score = score
    return best_sentence


def _section_bonus(section: str | None, query_terms: list[str]) -> float:
    if section is None:
        return 0
    section_terms = set(_tokenize(section))
    if section_terms & set(query_terms):
        return 0.5
    return 0


def _sentences(text: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
        if sentence.strip()
    ]


def _tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9@_-]*", text.lower())
        if token not in STOPWORDS and len(token) > 1
    ]


def _expand_query_terms(query_terms: list[str]) -> list[str]:
    expanded = list(query_terms)
    for term in query_terms:
        expanded.extend(QUERY_EXPANSIONS.get(term, []))
    return expanded


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


QUERY_EXPANSIONS = {
    "dataset": ["data", "cora", "citeseer", "pubmed", "ogbn-arxiv", "reddit"],
    "datasets": ["data", "cora", "citeseer", "pubmed", "ogbn-arxiv", "reddit"],
    "metric": ["accuracy", "f1", "auc", "mrr", "hits@k"],
    "metrics": ["accuracy", "f1", "auc", "mrr", "hits@k"],
    "baseline": ["baselines", "compare", "comparison"],
    "baselines": ["baseline", "compare", "comparison"],
    "model": ["gcn", "gat", "graphsage", "gin", "encoder"],
    "task": ["classification", "prediction", "recommendation"],
}


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "paper",
    "that",
    "the",
    "this",
    "to",
    "use",
    "used",
    "uses",
    "what",
    "which",
    "with",
}
