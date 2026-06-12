from datetime import UTC, datetime

from paper2gnnlab_agent.models.card import PaperCard, ReproductionDifficulty
from paper2gnnlab_agent.models.common import Citation, CitedValue
from paper2gnnlab_agent.models.method import ChecklistItem, ReproductionPlan
from paper2gnnlab_agent.services.method_spec import MethodSpecService, dump_method_spec_yaml


def test_method_spec_maps_card_and_reproduction_plan_to_template_fields() -> None:
    card = PaperCard(
        paper_id="paper_method",
        task_type=[make_value("paper_method", "abstract", "node classification")],
        graph_type=[make_value("paper_method", "method", "homogeneous graph")],
        datasets=[make_value("paper_method", "experiments", "Cora")],
        model_modules=[make_value("paper_method", "method", "GCN encoder")],
        losses=[make_value("paper_method", "method", "cross entropy")],
        attacks=[make_value("paper_method", "experiments", "PRBCD")],
        defenses=[make_value("paper_method", "method", "edge purification")],
        metrics=[make_value("paper_method", "experiments", "accuracy")],
        baselines=[make_value("paper_method", "experiments", "GAT")],
        training_setup=[make_value("paper_method", "experiments", "200 epochs")],
        evaluation_protocol=[make_value("paper_method", "experiments", "fixed split")],
        missing_implementation_details=[make_value("paper_method", "method", "dropout rate")],
        reproduction_difficulty=ReproductionDifficulty(level="medium", reasons=[]),
        generated_at=datetime.now(UTC),
    )
    plan = ReproductionPlan(
        paper_id="paper_method",
        objective="Reproduce a GNN.",
        data_preparation=[
            ChecklistItem(item="Acquire and preprocess dataset: Cora.", status="todo")
        ],
        training_pipeline=[
            ChecklistItem(item="Find optimizer and learning rate.", status="needs_manual_check")
        ],
        ablation_studies=[ChecklistItem(item="Ablate GCN encoder.", status="todo")],
        risks=[],
        missing_details=[
            ChecklistItem(
                item="Resolve missing implementation detail: dropout rate.",
                status="blocked",
            )
        ],
        estimated_difficulty="medium",
        generated_at=datetime.now(UTC),
    )

    spec = MethodSpecService().generate(card=card, reproduction_plan=plan)

    assert spec.paper_id == "paper_method"
    assert spec.task_type == ["node classification"]
    assert spec.datasets[0].name == "Cora"
    assert spec.datasets[0].preprocessing == ["Acquire and preprocess dataset: Cora."]
    assert spec.model_modules[0].name == "GCN encoder"
    assert spec.losses == ["cross entropy"]
    assert spec.attacks[0].name == "PRBCD"
    assert spec.defenses[0].name == "edge purification"
    assert spec.metrics == ["accuracy"]
    assert spec.baselines == ["GAT"]
    assert spec.training is not None
    assert spec.training.citations[0].paper_id == "paper_method"
    assert spec.evaluation is not None
    assert spec.evaluation.protocol == "fixed split"
    assert spec.evaluation.ablations == ["Ablate GCN encoder."]
    assert "dropout rate" in spec.missing_details
    assert "Find optimizer and learning rate." in spec.missing_details


def test_method_spec_yaml_dump_is_deterministic_and_readable() -> None:
    spec = MethodSpecService().generate(
        card=PaperCard(
            paper_id="paper_yaml",
            datasets=[make_value("paper_yaml", "experiments", "Cora")],
            reproduction_difficulty=ReproductionDifficulty(level="low", reasons=[]),
            generated_at=datetime.now(UTC),
        )
    )

    yaml_text = dump_method_spec_yaml(spec)

    assert yaml_text.startswith('paper_id: "paper_yaml"')
    assert 'name: "Cora"' in yaml_text
    assert "datasets:" in yaml_text


def make_value(paper_id: str, section: str, value: str) -> CitedValue:
    return CitedValue(
        value=value,
        confidence="medium",
        citations=[
            Citation(
                paper_id=paper_id,
                chunk_id=f"chunk_{paper_id}_0001",
                page=1,
                section=section,
                evidence_text=f"{value} evidence",
            )
        ],
    )
