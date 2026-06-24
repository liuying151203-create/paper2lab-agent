from datetime import UTC, datetime

from paper2gnnlab_agent.models.chunk import Chunk
from paper2gnnlab_agent.models.common import Citation
from paper2gnnlab_agent.services.card_extraction import (
    LlmPaperCardExtractor,
    RuleBasedPaperCardExtractor,
)


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


def test_rule_based_card_extractor_handles_han_experiment_evidence() -> None:
    paper_id = "paper_han"
    chunks = [
        make_chunk(
            paper_id,
            "chunk_han_0001",
            1,
            "abstract",
            (
                "In this paper, we first propose Heterogeneous Graph Attention Network "
                "(HAN), a novel heterogeneous graph neural network based on the "
                "hierarchical attention, including node-level attention and "
                "semantic-level attention."
            ),
        ),
        make_chunk(
            paper_id,
            "chunk_han_0002",
            2,
            "introduction",
            (
                "The heterogeneous graph IMDB consists three types of nodes, i.e., actor, "
                "movie, director. Two meta-paths involved in IMDB are Movie-Actor-Movie "
                "and Movie-Director-Movie."
            ),
        ),
        make_chunk(
            paper_id,
            "chunk_han_0003",
            3,
            "experiments",
            (
                "Table 3 reports quantitative results on the node classification task. "
                "Datasets include ACM, DBLP, and IMDB. Metrics are Macro-F1 and Micro-F1. "
                "Baselines include DeepWalk, ESim, metapath2vec, HERec, GCN, and GAT. "
                "Table 4 reports node clustering with NMI and ARI."
            ),
        ),
    ]

    card = RuleBasedPaperCardExtractor().extract(paper_id, chunks)

    assert "heterogeneous graph" in [item.value for item in card.graph_type]
    assert "homogeneous graph" not in [item.value for item in card.graph_type]
    assert "HAN" in [item.value for item in card.model_modules]
    assert {"ACM", "DBLP", "IMDB"}.issubset({item.value for item in card.datasets})
    assert "node clustering" in [item.value for item in card.task_type]
    assert {"actor", "movie", "director"}.issubset({item.value for item in card.node_types})
    assert {"Macro-F1", "Micro-F1", "NMI", "ARI"}.issubset(
        {item.value for item in card.metrics}
    )
    assert {"DeepWalk", "metapath2vec", "HERec"}.issubset(
        {item.value for item in card.baselines}
    )


def test_rule_based_card_extractor_handles_rohe_robustness_evidence() -> None:
    paper_id = "paper_rohe"
    chunks = [
        make_chunk(
            paper_id,
            "chunk_rohe_0001",
            1,
            "abstract",
            (
                "We propose a novel robust HGNN framework RoHe against topology "
                "adversarial attacks by equipping an attention purifier, which can prune "
                "malicious neighbors based on topology and feature."
            ),
        ),
        make_chunk(
            paper_id,
            "chunk_rohe_0002",
            2,
            "introduction",
            (
                "HGNNs, i.e., HAN, MAGNN, and GTN, dramatically decrease under attack. "
                "An example of ACM citation network consists of three types of objects "
                "(Author (A), Paper (P), Subject (S)) and two types of relations "
                "(P-A and P-S)."
            ),
        ),
        make_chunk(
            paper_id,
            "chunk_rohe_0003",
            3,
            "experiments",
            (
                "RoHe is evaluated on three widely used HG datasets: ACM consists of "
                "{Paper (P), Author (A), Subject (S)}, DBLP consists of {Author (A), "
                "Paper (P), Term (T), Conference (C)}, and Aminer consists of "
                "{Paper (P), Author (A), Reference (R)}. We compare with Jaccard, "
                "SimP, and GGCL baselines and report accuracy, Macro-F1, Micro-F1, and AP."
            ),
        ),
    ]

    card = RuleBasedPaperCardExtractor().extract(paper_id, chunks)

    assert {"ACM", "DBLP", "Aminer"}.issubset({item.value for item in card.datasets})
    assert {"RoHe", "HAN", "MAGNN", "GTN", "attention purifier"}.issubset(
        {item.value for item in card.model_modules}
    )
    assert "topology adversarial attack" in [item.value for item in card.attacks]
    assert "attention purifier" in [item.value for item in card.defenses]
    assert {"Jaccard", "SimP", "GGCL"}.issubset({item.value for item in card.baselines})
    assert {"Paper", "Author", "Subject", "Term", "Conference", "Reference"}.issubset(
        {item.value for item in card.node_types}
    )


def test_llm_card_extractor_validates_structured_json_with_citations() -> None:
    paper_id = "paper_card123"
    chunks = [
        make_chunk(
            paper_id,
            "chunk_card123_0001",
            1,
            "abstract",
            "We study node classification on Cora with a GCN model.",
        )
    ]

    card = LlmPaperCardExtractor(FakeCardLlmClient()).extract(paper_id, chunks)

    assert card.paper_id == paper_id
    assert card.task_type[0].value == "node classification"
    assert card.datasets[0].value == "Cora"
    assert card.datasets[0].citations[0].chunk_id == "chunk_card123_0001"


def test_llm_card_extractor_falls_back_on_invalid_json() -> None:
    paper_id = "paper_card123"
    chunks = [
        make_chunk(
            paper_id,
            "chunk_card123_0001",
            1,
            "abstract",
            "We study node classification on Cora with a GCN model.",
        )
    ]

    card = LlmPaperCardExtractor(BrokenCardLlmClient()).extract(paper_id, chunks)

    assert card.task_type[0].value == "node classification"


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


class FakeCardLlmClient:
    def generate(self, messages: list[dict[str, str]], temperature: float = 0.0) -> str:
        assert temperature == 0.0
        assert "Evidence:" in messages[1]["content"]
        return """
        {
          "paper_id": "paper_card123",
          "task_type": [
            {
              "value": "node classification",
              "confidence": "high",
              "citations": [
                {
                  "paper_id": "paper_card123",
                  "chunk_id": "chunk_card123_0001",
                  "page": 1,
                  "section": "abstract",
                  "evidence_text": "We study node classification on Cora with a GCN model."
                }
              ]
            }
          ],
          "datasets": [
            {
              "value": "Cora",
              "confidence": "high",
              "citations": [
                {
                  "paper_id": "paper_card123",
                  "chunk_id": "chunk_card123_0001",
                  "page": 1,
                  "section": "abstract",
                  "evidence_text": "We study node classification on Cora with a GCN model."
                }
              ]
            }
          ],
          "reproduction_difficulty": {"level": "unknown", "reasons": []}
        }
        """


class BrokenCardLlmClient:
    def generate(self, messages: list[dict[str, str]], temperature: float = 0.0) -> str:
        return "not json"
