"""Rule-based reproduction checklist generation from GNN PaperCards."""

from datetime import UTC, datetime

from paper2gnnlab_agent.models.card import PaperCard
from paper2gnnlab_agent.models.common import Citation, CitedValue
from paper2gnnlab_agent.models.method import ChecklistItem, ReproductionPlan


class ReproductionChecklistService:
    """Build citation-backed GNN reproduction plans from structured PaperCards."""

    def generate(self, card: PaperCard) -> ReproductionPlan:
        """Generate a conservative reproduction checklist for one GNN paper."""

        return ReproductionPlan(
            paper_id=card.paper_id,
            objective=_build_objective(card),
            environment=_build_environment(card),
            data_preparation=_build_data_preparation(card),
            model_implementation=_build_model_implementation(card),
            attack_or_defense_setup=_build_attack_or_defense_setup(card),
            training_pipeline=_build_training_pipeline(card),
            evaluation=_build_evaluation(card),
            ablation_studies=_build_ablation_studies(card),
            risks=_build_risks(card),
            missing_details=_build_missing_details(card),
            estimated_difficulty=card.reproduction_difficulty.level,
            generated_at=datetime.now(UTC),
        )


def _build_objective(card: PaperCard) -> str:
    title = card.title.value if card.title else card.paper_id
    tasks = _join_values(card.task_type) or "the paper's GNN task"
    datasets = _join_values(card.datasets)
    if datasets:
        return f"Reproduce {title} for {tasks} on {datasets}."
    return f"Reproduce {title} for {tasks}."


def _build_environment(card: PaperCard) -> list[ChecklistItem]:
    items = [
        ChecklistItem(
            item=(
                "Create a Python environment with PyTorch and a graph learning stack such as "
                "PyG or DGL."
            ),
            status="needs_manual_check",
            rationale=(
                "PaperCard does not encode exact package versions; confirm versions from the "
                "paper, official code, or artifact appendix before running experiments."
            ),
        ),
        ChecklistItem(
            item="Record CUDA, driver, GPU, CPU, and random seed settings before training.",
            status="needs_manual_check",
            rationale=(
                "Hardware and seed settings often affect GNN reproduction but are not "
                "guaranteed in PaperCard."
            ),
        ),
    ]
    if card.attacks:
        items.append(
            ChecklistItem(
                item="Prepare graph attack tooling needed by the threat model.",
                status="todo",
                rationale="The paper card contains attack-related evidence.",
                citations=_citations_from_values(card.attacks),
            )
        )
    return items


def _build_data_preparation(card: PaperCard) -> list[ChecklistItem]:
    items = [
        ChecklistItem(
            item=f"Acquire and preprocess dataset: {dataset.value}.",
            status="todo",
            rationale="Dataset is extracted from the GNN PaperCard.",
            citations=dataset.citations,
        )
        for dataset in card.datasets
    ]
    if not items:
        items.append(
            ChecklistItem(
                item="Identify datasets, splits, preprocessing, and graph construction details.",
                status="blocked",
                rationale="No dataset evidence was extracted into PaperCard.",
            )
        )

    for graph_type in card.graph_type:
        items.append(
            ChecklistItem(
                item=f"Verify graph setting and construction: {graph_type.value}.",
                status="todo",
                rationale="Graph type affects loaders, message passing, and evaluation protocol.",
                citations=graph_type.citations,
            )
        )
    for node_type in card.node_types:
        items.append(
            ChecklistItem(
                item=f"Check node type handling: {node_type.value}.",
                status="needs_manual_check",
                rationale="Node type semantics may require custom feature processing in GNN code.",
                citations=node_type.citations,
            )
        )
    for edge_type in card.edge_types:
        items.append(
            ChecklistItem(
                item=f"Check edge type handling: {edge_type.value}.",
                status="needs_manual_check",
                rationale="Edge type semantics may require relation-specific message passing.",
                citations=edge_type.citations,
            )
        )
    return items


def _build_model_implementation(card: PaperCard) -> list[ChecklistItem]:
    items = [
        ChecklistItem(
            item=f"Implement or configure model module: {module.value}.",
            status="todo",
            rationale="Model module is extracted from the paper card.",
            citations=module.citations,
        )
        for module in card.model_modules
    ]
    for loss in card.losses:
        items.append(
            ChecklistItem(
                item=f"Implement training loss or objective: {loss.value}.",
                status="todo",
                rationale="Loss term is part of the reproducible method definition.",
                citations=loss.citations,
            )
        )
    if not items:
        items.append(
            ChecklistItem(
                item="Recover model architecture, layers, aggregation rules, and loss terms.",
                status="blocked",
                rationale="No model module or loss evidence was extracted into PaperCard.",
            )
        )
    return items


def _build_attack_or_defense_setup(card: PaperCard) -> list[ChecklistItem]:
    items = [
        ChecklistItem(
            item=f"Recreate attack setting: {attack.value}.",
            status="todo",
            rationale="Attack setup should be reproduced before robustness metrics are compared.",
            citations=attack.citations,
        )
        for attack in card.attacks
    ]
    items.extend(
        ChecklistItem(
            item=f"Recreate defense mechanism: {defense.value}.",
            status="todo",
            rationale="Defense setup should be isolated from base model implementation.",
            citations=defense.citations,
        )
        for defense in card.defenses
    )
    if not items:
        items.append(
            ChecklistItem(
                item=(
                    "Confirm whether the paper uses attacks, defenses, or "
                    "robustness-specific evaluation."
                ),
                status="needs_manual_check",
                rationale=(
                    "No attack or defense evidence was extracted; this may be expected for "
                    "non-robustness papers."
                ),
            )
        )
    return items


def _build_training_pipeline(card: PaperCard) -> list[ChecklistItem]:
    items = [
        ChecklistItem(
            item=f"Recreate training setup: {setup.value}.",
            status="todo",
            rationale="Training setup was extracted from the paper card.",
            citations=setup.citations,
        )
        for setup in card.training_setup
    ]
    if not items:
        items.append(
            ChecklistItem(
                item=(
                    "Find optimizer, learning rate, epochs, batch size, early stopping, "
                    "and seed settings."
                ),
                status="needs_manual_check",
                rationale="Training hyperparameters were not extracted into PaperCard.",
            )
        )
    return items


def _build_evaluation(card: PaperCard) -> list[ChecklistItem]:
    items = [
        ChecklistItem(
            item=f"Compute evaluation metric: {metric.value}.",
            status="todo",
            rationale="Metric is extracted from the GNN PaperCard.",
            citations=metric.citations,
        )
        for metric in card.metrics
    ]
    items.extend(
        ChecklistItem(
            item=f"Compare against baseline: {baseline.value}.",
            status="todo",
            rationale="Baseline should be reproduced or cited as an external reference point.",
            citations=baseline.citations,
        )
        for baseline in card.baselines
    )
    items.extend(
        ChecklistItem(
            item=f"Match evaluation protocol: {protocol.value}.",
            status="todo",
            rationale="Evaluation protocol affects whether reported GNN metrics are comparable.",
            citations=protocol.citations,
        )
        for protocol in card.evaluation_protocol
    )
    if not items:
        items.append(
            ChecklistItem(
                item="Recover metrics, baselines, splits, and evaluation protocol.",
                status="blocked",
                rationale="No evaluation evidence was extracted into PaperCard.",
            )
        )
    return items


def _build_ablation_studies(card: PaperCard) -> list[ChecklistItem]:
    items = [
        ChecklistItem(
            item=f"Use reported result as a sanity target: {result.value}.",
            status="todo",
            rationale="Main result provides a target for reproduction checks.",
            citations=result.citations,
        )
        for result in card.main_results
    ]
    items.append(
        ChecklistItem(
            item=(
                "Identify ablation variants for key GNN modules, losses, attacks, "
                "defenses, and graph inputs."
            ),
            status="needs_manual_check",
            rationale="PaperCard does not currently expose a dedicated ablation schema.",
        )
    )
    return items


def _build_risks(card: PaperCard) -> list[ChecklistItem]:
    items = [
        ChecklistItem(
            item=f"Address reproduction risk: {reason.value}.",
            status="needs_manual_check",
            rationale=(
                "PaperCard estimates reproduction difficulty as "
                f"{card.reproduction_difficulty.level}."
            ),
            citations=reason.citations,
        )
        for reason in card.reproduction_difficulty.reasons
    ]
    for limitation in card.limitations:
        items.append(
            ChecklistItem(
                item=f"Account for limitation: {limitation.value}.",
                status="needs_manual_check",
                rationale="Limitation may affect expected reproduction quality or scope.",
                citations=limitation.citations,
            )
        )
    if not items and card.reproduction_difficulty.level in {"high", "unknown"}:
        items.append(
            ChecklistItem(
                item="Manually audit reproduction risk before coding the experiment.",
                status="needs_manual_check",
                rationale=(
                    "PaperCard estimates difficulty as "
                    f"{card.reproduction_difficulty.level}."
                ),
            )
        )
    return items


def _build_missing_details(card: PaperCard) -> list[ChecklistItem]:
    items = [
        ChecklistItem(
            item=f"Resolve missing implementation detail: {detail.value}.",
            status="blocked",
            rationale="This detail must be clarified before claiming faithful reproduction.",
            citations=detail.citations,
        )
        for detail in card.missing_implementation_details
    ]
    if not items:
        items.append(
            ChecklistItem(
                item=(
                    "Check official code, appendix, and supplementary material for "
                    "unstated implementation details."
                ),
                status="needs_manual_check",
                rationale=(
                    "Even when PaperCard has no missing-detail evidence, GNN reproduction "
                    "often depends on code-level defaults."
                ),
            )
        )
    return items


def _join_values(values: list[CitedValue]) -> str:
    return ", ".join(value.value for value in values)


def _citations_from_values(values: list[CitedValue]) -> list[Citation]:
    citations: list[Citation] = []
    seen: set[tuple[str, str]] = set()
    for value in values:
        for citation in value.citations:
            key = (citation.paper_id, citation.chunk_id)
            if key not in seen:
                seen.add(key)
                citations.append(citation)
    return citations
