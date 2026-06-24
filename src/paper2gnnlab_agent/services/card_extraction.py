"""Rule-based GNN paper card extraction from citation-ready chunks."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Protocol

from paper2gnnlab_agent.models.card import PaperCard, ReproductionDifficulty
from paper2gnnlab_agent.models.chunk import Chunk
from paper2gnnlab_agent.models.common import Citation, CitedValue
from paper2gnnlab_agent.services.llm import LlmClient, LlmGenerationError


class PaperCardExtractor(Protocol):
    """Build a PaperCard from citation-ready chunks."""

    name: str

    def extract(self, paper_id: str, chunks: list[Chunk]) -> PaperCard:
        """Build a citation-backed paper card."""


class RuleBasedPaperCardExtractor:
    """Extract a conservative GNN-specific paper card without external model calls."""

    name = "rule_based"

    def extract(self, paper_id: str, chunks: list[Chunk]) -> PaperCard:
        """Build a citation-backed paper card from available chunks."""

        return PaperCard(
            paper_id=paper_id,
            title=None,
            problem=_extract_problem(chunks),
            task_type=_extract_keyword_values(chunks, TASK_PATTERNS),
            graph_type=_extract_graph_types(chunks),
            datasets=_extract_dataset_values(chunks),
            node_types=_extract_node_types(chunks),
            edge_types=_extract_edge_types(chunks),
            model_modules=_extract_keyword_values(_ordered_chunks(chunks), MODEL_PATTERNS),
            losses=_extract_keyword_values(chunks, LOSS_PATTERNS),
            attacks=_extract_keyword_values(chunks, ATTACK_PATTERNS),
            defenses=_extract_keyword_values(chunks, DEFENSE_PATTERNS),
            metrics=_extract_keyword_values(chunks, METRIC_PATTERNS),
            baselines=_extract_keyword_values(chunks, BASELINE_PATTERNS),
            training_setup=_extract_training_setup(chunks),
            evaluation_protocol=_extract_keyword_values(chunks, EVALUATION_PATTERNS),
            main_results=_extract_sentences(chunks, RESULT_TERMS, limit=3),
            limitations=_extract_sentences(chunks, LIMITATION_TERMS, limit=3),
            reproduction_difficulty=_estimate_reproduction_difficulty(chunks),
            missing_implementation_details=_extract_missing_details(chunks),
            generated_at=datetime.now(UTC),
        )


class LlmPaperCardExtractor:
    """Use an LLM to produce a structured GNN PaperCard JSON with fallback."""

    name = "llm"

    def __init__(
        self,
        client: LlmClient,
        fallback: PaperCardExtractor | None = None,
        max_chunks: int = 24,
    ) -> None:
        self.client = client
        self.fallback = fallback or RuleBasedPaperCardExtractor()
        self.max_chunks = max_chunks

    def extract(self, paper_id: str, chunks: list[Chunk]) -> PaperCard:
        if not chunks:
            return self.fallback.extract(paper_id=paper_id, chunks=chunks)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are Paper2GNNLab-Agent, a GNN paper reading assistant. "
                    "Extract a structured PaperCard for experiment reproduction. "
                    "Use only the provided chunk evidence. "
                    "Every non-empty factual field must include citations copied from "
                    "the provided evidence. Return only valid JSON."
                ),
            },
            {
                "role": "user",
                "content": _build_card_prompt(paper_id=paper_id, chunks=chunks[: self.max_chunks]),
            },
        ]
        try:
            response = self.client.generate(messages=messages, temperature=0.0)
            return _paper_card_from_llm_json(
                paper_id=paper_id,
                response=response,
                chunks=chunks,
            )
        except (LlmGenerationError, ValueError, TypeError, json.JSONDecodeError):
            return self.fallback.extract(paper_id=paper_id, chunks=chunks)


def _build_card_prompt(paper_id: str, chunks: list[Chunk]) -> str:
    evidence = "\n\n".join(
        (
            f"chunk_id: {chunk.chunk_id}\n"
            f"page: {chunk.page_start}\n"
            f"section: {chunk.section or 'unknown'}\n"
            f"citation: {chunk.citation.model_dump_json()}\n"
            f"text: {chunk.text[:1800]}"
        )
        for chunk in chunks
    )
    schema_hint = {
        "paper_id": paper_id,
        "title": None,
        "problem": None,
        "task_type": [],
        "graph_type": [],
        "datasets": [],
        "node_types": [],
        "edge_types": [],
        "model_modules": [],
        "losses": [],
        "attacks": [],
        "defenses": [],
        "metrics": [],
        "baselines": [],
        "training_setup": [],
        "evaluation_protocol": [],
        "main_results": [],
        "limitations": [],
        "reproduction_difficulty": {"level": "unknown", "reasons": []},
        "missing_implementation_details": [],
    }
    return (
        "Extract a GNN-specific PaperCard JSON.\n"
        "Use CitedValue objects shaped as "
        '{"value": "...", "confidence": "high|medium|low|unknown", "citations": [...]}.\n'
        "Use only citation objects copied from the evidence block.\n"
        "If evidence is missing, leave the field empty or use confidence='unknown'.\n"
        f"JSON shape:\n{json.dumps(schema_hint, ensure_ascii=False, indent=2)}\n\n"
        f"Evidence:\n{evidence}\n\n"
        "Return JSON only, no markdown."
    )


def _paper_card_from_llm_json(
    paper_id: str,
    response: str,
    chunks: list[Chunk],
) -> PaperCard:
    payload = _extract_json_object(response)
    payload["paper_id"] = paper_id
    payload.setdefault("generated_at", datetime.now(UTC).isoformat())
    payload.setdefault("reproduction_difficulty", {"level": "unknown", "reasons": []})
    for field_name in PAPER_CARD_LIST_FIELDS:
        payload.setdefault(field_name, [])

    card = PaperCard.model_validate(payload)
    known_chunk_ids = {chunk.chunk_id for chunk in chunks}
    _drop_unknown_citations(card, known_chunk_ids)
    return card


def _extract_json_object(text: str) -> dict[str, object]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM response did not contain a JSON object.")
    parsed = json.loads(stripped[start : end + 1])
    if not isinstance(parsed, dict):
        raise TypeError("LLM PaperCard response must be a JSON object.")
    return parsed


def _drop_unknown_citations(card: PaperCard, known_chunk_ids: set[str]) -> None:
    values: list[CitedValue] = []
    if card.title:
        values.append(card.title)
    if card.problem:
        values.append(card.problem)
    for field_name in PAPER_CARD_LIST_FIELDS:
        values.extend(getattr(card, field_name))
    values.extend(card.reproduction_difficulty.reasons)
    for value in values:
        value.citations = [
            citation for citation in value.citations if citation.chunk_id in known_chunk_ids
        ]


PAPER_CARD_LIST_FIELDS = [
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


TASK_PATTERNS = {
    "node classification": [r"\bnode classification\b"],
    "node clustering": [r"\bnode clustering\b", r"\bclustering task\b"],
    "graph classification": [r"\bgraph classification\b"],
    "link prediction": [r"\blink prediction\b"],
    "recommendation": [r"\brecommendation\b", r"\brecommender\b"],
    "graph regression": [r"\bgraph regression\b"],
    "anomaly detection": [r"\banomaly detection\b"],
    "robustness evaluation": [r"\brobust(?:ness)?\b", r"\badversarial\b"],
}

GRAPH_PATTERNS = {
    "homogeneous graph": [r"\bhomogeneous graph\b"],
    "heterogeneous graph": [r"\bheterogeneous graph\b", r"\bheterograph\b"],
    "dynamic graph": [r"\bdynamic graph\b", r"\btemporal graph\b"],
    "knowledge graph": [r"\bknowledge graph\b"],
    "bipartite graph": [r"\bbipartite graph\b"],
    "attributed graph": [r"\battributed graph\b"],
}

DATASET_PATTERNS = {
    "ACM": [r"\bACM\b"],
    "DBLP": [r"\bDBLP\b"],
    "IMDB": [r"\bIMDB\b"],
    "Aminer": [r"\bAminer\b", r"\bAMiner\b"],
    "Cora": [r"\bCora\b"],
    "Citeseer": [r"\bCiteSeer\b", r"\bCiteseer\b"],
    "PubMed": [r"\bPubMed\b"],
    "ogbn-arxiv": [r"\bogbn-arxiv\b"],
    "ogbn-products": [r"\bogbn-products\b"],
    "PPI": [r"\bPPI\b"],
    "Reddit": [r"\bReddit\b"],
    "Amazon": [r"\bAmazon\b"],
    "Yelp": [r"\bYelp\b"],
    "MovieLens": [r"\bMovieLens\b"],
    "MUTAG": [r"\bMUTAG\b"],
    "PROTEINS": [r"\bPROTEINS\b"],
    "NCI1": [r"\bNCI1\b"],
}

MODEL_PATTERNS = {
    "RoHe": [r"\bRoHe\b", r"\bRobust Heterogeneous GNN\b"],
    "HAN": [r"\bHAN\b", r"\bHeterogeneous Graph Attention Network\b"],
    "MAGNN": [r"\bMAGNN\b"],
    "GTN": [r"\bGTN\b", r"\bGraph Transformer Network\b"],
    "HGNN": [r"\bHGNNs?\b", r"\bheterogeneous graph neural networks?\b"],
    "attention purifier": [r"\battention puri(?:fi|ﬁ)er\b"],
    "node-level attention": [r"\bnode-level attention\b"],
    "semantic-level attention": [r"\bsemantic-level attention\b"],
    "metapath-based aggregation": [r"\bmetapath-based aggregation\b"],
    "GCN": [r"\bGCN\b", r"\bgraph convolutional network\b"],
    "GAT": [r"\bGAT\b", r"\bgraph attention network\b"],
    "GraphSAGE": [r"\bGraphSAGE\b"],
    "GIN": [r"\bGIN\b", r"\bgraph isomorphism network\b"],
    "R-GCN": [r"\bR-GCN\b", r"\brelational graph convolutional network\b"],
    "HGT": [r"\bHGT\b", r"\bheterogeneous graph transformer\b"],
    "message passing": [r"\bmessage passing\b"],
    "attention": [r"\battention\b"],
}

LOSS_PATTERNS = {
    "cross entropy": [r"\bcross[- ]entropy\b"],
    "negative log likelihood": [r"\bnegative log[- ]likelihood\b", r"\bNLL\b"],
    "contrastive loss": [r"\bcontrastive loss\b"],
    "margin loss": [r"\bmargin loss\b"],
    "regularization": [r"\bregularization\b", r"\bregularizer\b"],
}

ATTACK_PATTERNS = {
    "topology adversarial attack": [r"\btopology adversarial attacks?\b"],
    "adversarial attack": [r"\badversarial attack\b"],
    "poisoning attack": [r"\bpoisoning\b"],
    "evasion attack": [r"\bevasion\b"],
    "structure perturbation": [r"\bstructure perturbation\b", r"\bedge perturbation\b"],
    "feature perturbation": [r"\bfeature perturbation\b"],
}

DEFENSE_PATTERNS = {
    "attention purifier": [r"\battention puri(?:fi|ﬁ)er\b"],
    "transiting probability prior": [r"\btransiting probability\b"],
    "top-T neighbor purification": [r"\btop-?T\b", r"\btop T\b"],
    "adversarial training": [r"\badversarial training\b"],
    "robust aggregation": [r"\brobust aggregation\b"],
    "graph purification": [r"\bgraph purification\b"],
    "certified defense": [r"\bcertified\b", r"\bcertifiable\b"],
}

METRIC_PATTERNS = {
    "accuracy": [r"\baccuracy\b", r"\bACC\b"],
    "Macro-F1": [r"\bMacro-F1\b", r"\bmacro F1\b"],
    "Micro-F1": [r"\bMicro-F1\b", r"\bmicro F1\b"],
    "F1": [r"\bF1\b", r"\bF1-score\b"],
    "AUC": [r"\bAUC\b", r"\bROC-AUC\b"],
    "AP": [r"\baverage precision\b", r"\bAP\b"],
    "MRR": [r"\bMRR\b"],
    "Hits@K": [r"\bHits@\d+\b", r"\bHits@K\b"],
    "NMI": [r"\bNMI\b"],
    "ARI": [r"\bARI\b"],
}

BASELINE_PATTERNS = {
    "HAN": [r"\bHAN\b"],
    "MAGNN": [r"\bMAGNN\b"],
    "GTN": [r"\bGTN\b"],
    "Jaccard": [r"\bJaccard\b"],
    "SimP": [r"\bSimP\b"],
    "GGCL": [r"\bGGCL\b"],
    "ESim": [r"\bESim\b"],
    "metapath2vec": [r"\bmetapath2vec\b"],
    "HERec": [r"\bHERec\b"],
    "GCN": [r"\bGCN\b"],
    "GAT": [r"\bGAT\b"],
    "GraphSAGE": [r"\bGraphSAGE\b"],
    "GIN": [r"\bGIN\b"],
    "MLP": [r"\bMLP\b"],
    "DeepWalk": [r"\bDeepWalk\b"],
    "node2vec": [r"\bnode2vec\b"],
}

EVALUATION_PATTERNS = {
    "transductive setting": [r"\btransductive\b"],
    "inductive setting": [r"\binductive\b"],
    "train/validation/test split": [r"\btrain(?:ing)?/validation/test\b", r"\btrain/val/test\b"],
    "ablation study": [r"\bablation\b"],
}

TRAINING_PATTERNS = {
    "Adam optimizer": [r"\bAdam\b"],
    "SGD optimizer": [r"\bSGD\b"],
    "learning rate": [r"\blearning rate\b", r"\blr\s*[=:]\s*\d"],
    "epochs": [r"\bepochs?\b"],
    "batch size": [r"\bbatch size\b"],
    "dropout": [r"\bdropout\b"],
    "weight decay": [r"\bweight decay\b"],
}

RESULT_TERMS = (
    "outperform",
    "state-of-the-art",
    "state of the art",
    "improve",
    "achieve",
    "result",
    "performance",
)
LIMITATION_TERMS = ("limitation", "future work", "fail", "cannot", "does not", "scalability")


SECTION_PRIORITY = {
    "abstract": 0,
    "introduction": 1,
    "method": 2,
    "background": 3,
    "experiments": 4,
    "results": 5,
    "conclusion": 6,
    "related_work": 7,
    "unknown": 8,
}


def _ordered_chunks(chunks: Iterable[Chunk]) -> list[Chunk]:
    return sorted(
        chunks,
        key=lambda chunk: (SECTION_PRIORITY.get(chunk.section or "unknown", 9), chunk.index),
    )


def _extract_graph_types(chunks: list[Chunk]) -> list[CitedValue]:
    values = _extract_keyword_values(_ordered_chunks(chunks), GRAPH_PATTERNS)
    has_heterogeneous = any(value.value == "heterogeneous graph" for value in values)
    if has_heterogeneous:
        values = [value for value in values if value.value != "homogeneous graph"]
        values = [
            value
            for value in values
            if not (
                value.value == "knowledge graph"
                and re.search(
                    r"\b(such as|applications?|applied to)\b",
                    value.citations[0].evidence_text if value.citations else "",
                    re.IGNORECASE,
                )
            )
        ]
    return values


def _extract_dataset_values(chunks: list[Chunk]) -> list[CitedValue]:
    return _extract_keyword_values(_dataset_ordered_chunks(chunks), DATASET_PATTERNS)


def _dataset_ordered_chunks(chunks: Iterable[Chunk]) -> list[Chunk]:
    priority = {
        "experiments": 0,
        "results": 1,
        "abstract": 2,
        "introduction": 3,
        "method": 4,
        "background": 5,
        "related_work": 6,
        "unknown": 7,
    }
    return sorted(
        chunks,
        key=lambda chunk: (priority.get(chunk.section or "unknown", 8), chunk.index),
    )


def _extract_node_types(chunks: list[Chunk]) -> list[CitedValue]:
    values = _extract_list_after_label(chunks, r"node types?\s*(?:are|include|:)\s*([^.;\n]+)")
    values.extend(
        _extract_list_after_label(
            chunks,
            r"types of nodes(?:,?\s*i\.e\.,?| include|:)\s*([^.;\n]+)",
        )
    )

    for chunk in chunks:
        for match in re.finditer(
            r"(?:consists of|contain(?:s)?|objects?)\s*\{([^{}]+)\}",
            chunk.text,
            re.IGNORECASE,
        ):
            values.extend(_schema_values_from_match(chunk, match.group(1), match.group(0)))
        for match in re.finditer(
            r"types of objects\s*\((.+?)\)\s*(?:,?\s+and|\.)",
            chunk.text,
            re.IGNORECASE,
        ):
            values.extend(_schema_values_from_match(chunk, match.group(1), match.group(0)))
    return _dedupe_values(values)[:16]


def _extract_edge_types(chunks: list[Chunk]) -> list[CitedValue]:
    values = _extract_list_after_label(chunks, r"edge types?\s*(?:are|include|:)\s*([^.;\n]+)")
    for chunk in chunks:
        for match in re.finditer(r"relations?\s*\(([^)]+)\)", chunk.text, re.IGNORECASE):
            relation_text = match.group(1)
            if "between" in relation_text.lower():
                continue
            values.extend(_schema_values_from_match(chunk, relation_text, match.group(0)))
    return _dedupe_values(values)[:16]


def _schema_values_from_match(
    chunk: Chunk,
    raw_values: str,
    evidence_text: str,
) -> list[CitedValue]:
    values: list[CitedValue] = []
    for raw_value in re.split(r",| and |/", raw_values):
        value = re.sub(r"\([A-Za-z0-9_-]+\)", "", raw_value).strip(" .;:{}[]")
        if "(" in value or ")" in value or value == "A-B":
            continue
        if not value:
            continue
        values.append(
            CitedValue(
                value=value,
                citations=[_citation_with_evidence(chunk, evidence_text)],
                confidence="medium",
            )
        )
    return values


def _extract_keyword_values(
    chunks: Iterable[Chunk],
    patterns: dict[str, list[str]],
) -> list[CitedValue]:
    values: list[CitedValue] = []
    seen: set[str] = set()
    for value, regexes in patterns.items():
        citation = _first_matching_citation(chunks, regexes)
        if citation is not None and value.lower() not in seen:
            values.append(CitedValue(value=value, citations=[citation], confidence="medium"))
            seen.add(value.lower())
    return values


def _extract_problem(chunks: list[Chunk]) -> CitedValue | None:
    candidates = [
        chunk
        for chunk in chunks
        if chunk.section in {"abstract", "introduction", "unknown"}
    ] or chunks
    for chunk in candidates:
        sentence = _first_sentence_with(
            chunk.text,
            ("propose", "study", "address", "problem", "challenge", "introduce"),
        )
        if sentence:
            return CitedValue(
                value=sentence,
                citations=[_citation_with_evidence(chunk, sentence)],
                confidence="low",
            )
    return None


def _extract_list_after_label(chunks: Iterable[Chunk], pattern: str) -> list[CitedValue]:
    values: list[CitedValue] = []
    seen: set[str] = set()
    regex = re.compile(pattern, re.IGNORECASE)
    for chunk in chunks:
        match = regex.search(chunk.text)
        if match is None:
            continue
        for raw_value in re.split(r",| and |/", match.group(1)):
            value = raw_value.strip(" .;:()[]")
            if not value or value.lower() in seen:
                continue
            values.append(
                CitedValue(
                    value=value,
                    citations=[_citation_with_evidence(chunk, match.group(0))],
                    confidence="medium",
                )
            )
            seen.add(value.lower())
    return values[:8]


def _extract_training_setup(chunks: list[Chunk]) -> list[CitedValue]:
    values = _extract_keyword_values(chunks, TRAINING_PATTERNS)
    lr_values = _extract_regex_values(chunks, r"\b(?:learning rate|lr)\s*[=:]?\s*([0-9.]+e?-?\d*)")
    epoch_values = _extract_regex_values(chunks, r"\b(\d+)\s+epochs?\b")
    return _dedupe_values([*values, *lr_values, *epoch_values])


def _extract_regex_values(chunks: Iterable[Chunk], pattern: str) -> list[CitedValue]:
    values: list[CitedValue] = []
    regex = re.compile(pattern, re.IGNORECASE)
    for chunk in chunks:
        match = regex.search(chunk.text)
        if match is None:
            continue
        values.append(
            CitedValue(
                value=match.group(0),
                citations=[_citation_with_evidence(chunk, match.group(0))],
                confidence="medium",
            )
        )
    return values


def _extract_sentences(
    chunks: Iterable[Chunk],
    terms: tuple[str, ...],
    limit: int,
) -> list[CitedValue]:
    values: list[CitedValue] = []
    seen: set[str] = set()
    for chunk in chunks:
        sentence = _first_sentence_with(chunk.text, terms)
        if sentence and sentence.lower() not in seen:
            values.append(
                CitedValue(
                    value=sentence,
                    citations=[_citation_with_evidence(chunk, sentence)],
                    confidence="low",
                )
            )
            seen.add(sentence.lower())
        if len(values) >= limit:
            break
    return values


def _extract_missing_details(chunks: list[Chunk]) -> list[CitedValue]:
    missing: list[CitedValue] = []
    anchor = _first_section_citation(chunks, {"method", "experiments", "results"}) or (
        chunks[0].citation if chunks else None
    )
    if not chunks:
        return missing

    checks = [
        ("training hyperparameters are not explicit in available chunks", TRAINING_PATTERNS),
        ("dataset split details are not explicit in available chunks", EVALUATION_PATTERNS),
    ]
    for message, patterns in checks:
        if not _has_any_pattern(chunks, patterns):
            missing.append(
                CitedValue(
                    value=message,
                    citations=[anchor] if anchor is not None else [],
                    confidence="low",
                )
            )
    return missing


def _estimate_reproduction_difficulty(chunks: list[Chunk]) -> ReproductionDifficulty:
    reasons = _extract_missing_details(chunks)
    has_training = _has_any_pattern(chunks, TRAINING_PATTERNS)
    has_dataset = _has_any_pattern(chunks, DATASET_PATTERNS)
    has_model = _has_any_pattern(chunks, MODEL_PATTERNS)

    if not chunks:
        return ReproductionDifficulty(level="unknown", reasons=[])
    if len(reasons) >= 2 or not has_model:
        return ReproductionDifficulty(level="high", reasons=reasons)
    if not has_training or not has_dataset:
        return ReproductionDifficulty(level="medium", reasons=reasons)
    return ReproductionDifficulty(level="low", reasons=reasons)


def _first_matching_citation(chunks: Iterable[Chunk], regexes: list[str]) -> Citation | None:
    compiled = [re.compile(regex, re.IGNORECASE) for regex in regexes]
    for chunk in chunks:
        for regex in compiled:
            match = regex.search(chunk.text)
            if match is not None:
                evidence = _sentence_containing(chunk.text, match.group(0))
                return _citation_with_evidence(chunk, evidence)
    return None


def _first_section_citation(chunks: Iterable[Chunk], sections: set[str]) -> Citation | None:
    for chunk in chunks:
        if chunk.section in sections:
            return chunk.citation
    return None


def _has_any_pattern(chunks: Iterable[Chunk], patterns: dict[str, list[str]]) -> bool:
    return any(
        re.search(regex, chunk.text, re.IGNORECASE)
        for chunk in chunks
        for regexes in patterns.values()
        for regex in regexes
    )


def _first_sentence_with(text: str, terms: tuple[str, ...]) -> str | None:
    for sentence in _sentences(text):
        lowered = sentence.lower()
        if any(term in lowered for term in terms):
            return sentence
    return None


def _sentence_containing(text: str, needle: str) -> str:
    lowered_needle = needle.lower()
    for sentence in _sentences(text):
        if lowered_needle in sentence.lower():
            return sentence
    return needle


def _sentences(text: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
        if sentence.strip()
    ]


def _citation_with_evidence(chunk: Chunk, evidence_text: str) -> Citation:
    evidence = _compact(evidence_text)
    return Citation(
        paper_id=chunk.paper_id,
        chunk_id=chunk.chunk_id,
        page=chunk.page_start,
        section=chunk.section,
        evidence_text=evidence[:300],
    )


def _dedupe_values(values: list[CitedValue]) -> list[CitedValue]:
    deduped: list[CitedValue] = []
    seen: set[str] = set()
    for value in values:
        key = value.value.lower()
        if key in seen:
            continue
        deduped.append(value)
        seen.add(key)
    return deduped


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
