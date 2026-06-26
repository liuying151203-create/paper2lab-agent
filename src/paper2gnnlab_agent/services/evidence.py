"""Evidence retrieval providers for citation-backed QA."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from collections import Counter
from typing import Any, Protocol

from paper2gnnlab_agent.models.chunk import Chunk
from paper2gnnlab_agent.models.common import Citation


class EvidenceProvider(Protocol):
    """Retrieve citation evidence for a paper question."""

    def retrieve(
        self,
        paper_id: str,
        question: str,
        chunks: list[Chunk],
        top_k: int = 6,
    ) -> list[Citation]:
        """Return citation evidence ordered by relevance."""


class LocalChunkEvidenceProvider:
    """Retrieve evidence from already persisted local chunks."""

    name = "local_chunks"

    def retrieve(
        self,
        paper_id: str,
        question: str,
        chunks: list[Chunk],
        top_k: int = 6,
    ) -> list[Citation]:
        query_terms = search_terms_for_question(question)
        if not chunks or not query_terms:
            return []

        ranked = _rank_chunks(chunks, query_terms)
        selected = [chunk for chunk, score in ranked[:top_k] if score > 0]
        return [_citation_for_question(chunk, query_terms) for chunk in selected]


def search_terms_for_question(question: str) -> list[str]:
    """Return normalized searchable terms used by local evidence retrieval."""

    terms = _expand_query_terms(_tokenize(question))
    terms.extend(_chinese_query_expansions(question))
    return _dedupe_terms(terms)


class GraphRagEvidenceProvider:
    """Retrieve evidence from an external GraphRAG service with local fallback."""

    name = "graphrag"

    def __init__(
        self,
        base_url: str,
        endpoint: str = "/qa/ask",
        timeout_seconds: float = 30.0,
        fallback: EvidenceProvider | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        self.timeout_seconds = timeout_seconds
        self.fallback = fallback or LocalChunkEvidenceProvider()

    def retrieve(
        self,
        paper_id: str,
        question: str,
        chunks: list[Chunk],
        top_k: int = 6,
    ) -> list[Citation]:
        try:
            payload = self._request_evidence(
                paper_id=paper_id,
                question=question,
                top_k=top_k,
            )
            citations = _citations_from_graphrag_payload(
                payload=payload,
                paper_id=paper_id,
                top_k=top_k,
            )
        except (OSError, ValueError, urllib.error.URLError):
            citations = []

        if citations:
            return citations
        return self.fallback.retrieve(
            paper_id=paper_id,
            question=question,
            chunks=chunks,
            top_k=top_k,
        )

    def _request_evidence(self, paper_id: str, question: str, top_k: int) -> Any:
        request_body = json.dumps(
            {
                "paper_id": paper_id,
                "question": question,
                "top_k": top_k,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            url=f"{self.base_url}{self.endpoint}",
            data=request_body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))


def _citations_from_graphrag_payload(
    payload: Any,
    paper_id: str,
    top_k: int,
) -> list[Citation]:
    items = _evidence_items(payload)
    citations: list[Citation] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue

        merged = _merge_nested_citation(item)
        evidence_text = _first_text(
            merged,
            keys=("evidence_text", "evidence", "text", "content", "snippet", "quote"),
        )
        if not evidence_text:
            continue

        citations.append(
            Citation(
                paper_id=str(merged.get("paper_id") or paper_id),
                chunk_id=str(merged.get("chunk_id") or f"graphrag_{index:04d}"),
                page=_optional_int(merged.get("page") or merged.get("page_start")),
                section=_optional_str(merged.get("section")),
                evidence_text=_compact(evidence_text)[:500],
            )
        )
        if len(citations) >= top_k:
            break
    return citations


def _evidence_items(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []

    for key in ("citations", "evidence", "evidences", "results", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def _merge_nested_citation(item: dict[str, Any]) -> dict[str, Any]:
    citation = item.get("citation")
    if isinstance(citation, dict):
        return {**citation, **item}
    return item


def _first_text(payload: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


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


def _chinese_query_expansions(question: str) -> list[str]:
    expanded: list[str] = []
    normalized = question.lower()
    for keyword, terms in CHINESE_QUERY_EXPANSIONS.items():
        if keyword in normalized:
            expanded.extend(terms)
    return expanded


def _dedupe_terms(terms: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for term in terms:
        if term in seen:
            continue
        seen.add(term)
        deduped.append(term)
    return deduped


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


CHINESE_QUERY_EXPANSIONS = {
    "数据集": ["dataset", "datasets", "data", "cora", "citeseer", "pubmed", "acm", "dblp", "imdb"],
    "数据": ["dataset", "datasets", "data"],
    "指标": ["metric", "metrics", "accuracy", "f1", "auc", "nmi", "ari", "micro-f1", "macro-f1"],
    "评价": ["evaluation", "metric", "metrics", "accuracy", "f1"],
    "评估": ["evaluation", "metric", "metrics", "accuracy", "f1"],
    "模型": ["model", "gcn", "gat", "han", "magnn", "gtn", "encoder"],
    "方法": ["method", "model", "framework"],
    "任务": ["task", "classification", "clustering", "prediction"],
    "图": ["graph", "heterogeneous", "homogeneous", "network"],
    "节点": ["node", "nodes", "author", "paper", "movie"],
    "边": ["edge", "edges", "relation", "relations"],
    "攻击": ["attack", "attacks", "adversarial", "perturbation"],
    "防御": ["defense", "defenses", "robust", "robustness", "purifier"],
    "基线": ["baseline", "baselines", "compare", "comparison"],
    "对比": ["baseline", "baselines", "compare", "comparison"],
    "训练": ["training", "optimizer", "learning", "epoch", "dropout"],
    "优化器": ["optimizer", "adam", "sgd"],
    "学习率": ["learning", "rate", "lr"],
    "结果": ["result", "results", "performance", "outperform"],
    "限制": ["limitation", "limitations", "future", "overfitting"],
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
