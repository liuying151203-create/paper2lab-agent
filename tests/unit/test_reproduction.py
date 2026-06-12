from datetime import UTC, datetime

from paper2gnnlab_agent.models.card import PaperCard, ReproductionDifficulty
from paper2gnnlab_agent.models.common import Citation, CitedValue
from paper2gnnlab_agent.services.reproduction import ReproductionChecklistService


def test_reproduction_plan_maps_gnn_card_fields_to_checklist_sections() -> None:
    card = PaperCard(
        paper_id="paper_repro",
        title=make_value("paper_repro", "abstract", "Robust GCN"),
        problem=make_value("paper_repro", "abstract", "robust node classification"),
        task_type=[make_value("paper_repro", "abstract", "node classification")],
        graph_type=[make_value("paper_repro", "method", "homogeneous graph")],
        datasets=[make_value("paper_repro", "experiments", "Cora")],
        model_modules=[make_value("paper_repro", "method", "GCN encoder")],
        losses=[make_value("paper_repro", "method", "cross entropy")],
        attacks=[make_value("paper_repro", "experiments", "PRBCD")],
        defenses=[make_value("paper_repro", "method", "edge purification")],
        metrics=[make_value("paper_repro", "experiments", "accuracy")],
        baselines=[make_value("paper_repro", "experiments", "GAT")],
        training_setup=[make_value("paper_repro", "experiments", "200 epochs")],
        main_results=[make_value("paper_repro", "results", "82.1 accuracy")],
        reproduction_difficulty=ReproductionDifficulty(
            level="high",
            reasons=[make_value("paper_repro", "limitations", "missing hyperparameters")],
        ),
        missing_implementation_details=[
            make_value("paper_repro", "limitations", "attack budget schedule")
        ],
        generated_at=datetime.now(UTC),
    )

    plan = ReproductionChecklistService().generate(card)

    assert plan.paper_id == "paper_repro"
    assert plan.estimated_difficulty == "high"
    assert "Robust GCN" in plan.objective
    assert any("Cora" in item.item for item in plan.data_preparation)
    assert any("GCN encoder" in item.item for item in plan.model_implementation)
    assert any("PRBCD" in item.item for item in plan.attack_or_defense_setup)
    assert any("accuracy" in item.item for item in plan.evaluation)
    assert any("GAT" in item.item for item in plan.evaluation)
    assert any("200 epochs" in item.item for item in plan.training_pipeline)
    assert plan.missing_details[0].status == "blocked"
    assert plan.missing_details[0].citations[0].paper_id == "paper_repro"


def test_reproduction_plan_marks_missing_core_evidence_as_blocked() -> None:
    card = PaperCard(
        paper_id="paper_sparse",
        reproduction_difficulty=ReproductionDifficulty(level="unknown", reasons=[]),
        generated_at=datetime.now(UTC),
    )

    plan = ReproductionChecklistService().generate(card)

    assert plan.data_preparation[0].status == "blocked"
    assert plan.model_implementation[0].status == "blocked"
    assert plan.evaluation[0].status == "blocked"
    assert plan.training_pipeline[0].status == "needs_manual_check"
    assert plan.missing_details[0].status == "needs_manual_check"


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
