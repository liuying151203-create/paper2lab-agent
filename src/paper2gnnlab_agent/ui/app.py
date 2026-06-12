"""Streamlit MVP UI for the single-paper Paper2GNNLab-Agent workflow."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from paper2gnnlab_agent import __version__
from paper2gnnlab_agent.core.config import Settings, get_settings
from paper2gnnlab_agent.models.card import PaperCard
from paper2gnnlab_agent.models.common import Citation, CitedValue
from paper2gnnlab_agent.models.comparison import PaperComparisonResponse
from paper2gnnlab_agent.models.method import ChecklistItem, MethodSpec, ReproductionPlan
from paper2gnnlab_agent.models.paper import PaperDetailResponse
from paper2gnnlab_agent.services.comparison import SUPPORTED_COMPARISON_DIMENSIONS
from paper2gnnlab_agent.services.papers import (
    CardArtifactNotFoundError,
    ChunksArtifactNotFoundError,
    CleanedArtifactNotFoundError,
    InvalidPaperUploadError,
    PaperIngestionService,
    PaperNotFoundError,
    ParsedArtifactNotFoundError,
    build_card_extractor_from_settings,
    build_paper_service,
    build_qa_service_from_settings,
)
from paper2gnnlab_agent.storage.paper_repository import PaperRepository
from paper2gnnlab_agent.storage.paths import build_storage_paths


def main() -> None:
    """Render the Streamlit MVP workbench."""

    st.set_page_config(page_title="Paper2GNNLab-Agent", page_icon="P2G", layout="wide")
    service = get_ui_service()
    settings = get_settings()

    st.title("Paper2GNNLab-Agent")
    st.caption("GNN paper reading and experiment reproduction planning")

    selected_paper_id = render_sidebar(service, settings)
    if selected_paper_id is None:
        st.info("Upload a GNN paper PDF or select a recent paper to start the Phase 1 workflow.")
        render_runtime(settings)
        return

    single_tab, comparison_tab = st.tabs(["Single paper", "Compare papers"])
    with single_tab:
        render_paper_workspace(service, selected_paper_id)
    with comparison_tab:
        render_comparison_workspace(service)


@st.cache_resource
def get_ui_service() -> PaperIngestionService:
    """Build a cached service instance for the Streamlit process."""

    settings = get_settings()
    paths = build_storage_paths(settings)
    repository = PaperRepository(paths.sqlite_path)
    return build_paper_service(
        repository=repository,
        paths=paths,
        card_extractor=build_card_extractor_from_settings(
            model_provider=settings.model_provider,
            model_name=settings.model_name,
            model_base_url=settings.model_base_url,
            api_key=settings.api_key,
        ),
        qa_service=build_qa_service_from_settings(
            model_provider=settings.model_provider,
            model_name=settings.model_name,
            model_base_url=settings.model_base_url,
            api_key=settings.api_key,
        ),
    )


def render_sidebar(service: PaperIngestionService, settings: Settings) -> str | None:
    """Render upload and paper selection controls."""

    with st.sidebar:
        st.header("Paper")
        uploaded = st.file_uploader("Upload GNN paper PDF", type=["pdf"])
        if st.button("Upload", type="primary", disabled=uploaded is None, use_container_width=True):
            if uploaded is not None:
                run_action(
                    lambda: service.upload_pdf(uploaded.name, uploaded.getvalue()),
                    success=lambda response: (
                        set_selected_paper(response.paper_id),
                        st.success(
                            f"{'Reused' if response.reused else 'Uploaded'} {response.paper_id}"
                        ),
                    ),
                )

        recent_papers = service.repository.list_recent(limit=30)
        options = [paper.paper_id for paper in recent_papers]
        current = st.session_state.get("selected_paper_id")
        if options:
            index = options.index(current) if current in options else 0
            selected = st.selectbox(
                "Recent papers",
                options=options,
                index=index,
                format_func=lambda paper_id: _format_paper_option(paper_id, recent_papers),
            )
            set_selected_paper(selected)
        elif current:
            st.text_input("Selected paper", value=current, disabled=True)

        st.divider()
        render_runtime(settings)

    return st.session_state.get("selected_paper_id")


def render_runtime(settings: Settings) -> None:
    """Show local runtime details."""

    st.caption(
        f"v{__version__} | {settings.env} | data: {settings.data_dir} | "
        f"sqlite: {settings.sqlite_path}"
    )
    model_status = (
        "LLM card + QA on" if settings.model_provider and settings.api_key else "rule/extractive"
    )
    st.caption(f"mode: {model_status}")


def render_paper_workspace(service: PaperIngestionService, paper_id: str) -> None:
    """Render the processing pipeline, card view, and QA panel."""

    try:
        detail = service.get_paper_detail(paper_id)
    except PaperNotFoundError:
        st.error("Selected paper no longer exists in metadata storage.")
        return

    render_paper_header(detail)
    render_pipeline(service, paper_id)
    st.divider()

    left, right = st.columns([1.05, 0.95], gap="large")
    with left:
        render_card_panel(service, paper_id)
    with right:
        render_qa_panel(service, paper_id)

    st.divider()
    render_reproduction_plan_panel(service, paper_id)
    st.divider()
    render_method_spec_panel(service, paper_id)


def render_paper_header(detail: PaperDetailResponse) -> None:
    """Render paper metadata and artifact readiness."""

    st.subheader(detail.filename)
    columns = st.columns(5)
    columns[0].metric("Status", detail.status)
    columns[1].metric("Parsed", "yes" if detail.artifacts.parsed else "no")
    columns[2].metric("Cleaned", "yes" if detail.artifacts.cleaned else "no")
    columns[3].metric("Chunks", "yes" if detail.artifacts.chunks else "no")
    columns[4].metric("Card", "yes" if detail.artifacts.paper_card else "no")
    st.code(detail.paper_id, language=None)


def render_pipeline(service: PaperIngestionService, paper_id: str) -> None:
    """Render Phase 1 workflow actions."""

    st.subheader("Workflow")
    force = st.checkbox("Force regenerate artifacts", value=False)
    col_parse, col_chunk, col_card = st.columns(3)

    with col_parse:
        if st.button("Parse and clean PDF", use_container_width=True):
            run_action(
                lambda: service.parse_pdf(paper_id, force=force),
                success=lambda response: st.success(
                    f"Parsed {response.pages_count} pages; status={response.status}"
                ),
            )

    with col_chunk:
        max_chars = st.number_input(
            "Chunk max chars",
            min_value=400,
            max_value=4000,
            value=1800,
            step=100,
        )
        if st.button("Generate chunks", use_container_width=True):
            run_action(
                lambda: service.generate_chunks(paper_id, force=force, max_chars=int(max_chars)),
                success=lambda response: st.success(
                    f"{'Reused' if response.reused else 'Generated'} "
                    f"{response.chunks_count} chunks"
                ),
            )

    with col_card:
        if st.button("Generate PaperCard", use_container_width=True):
            run_action(
                lambda: service.generate_paper_card(paper_id, force=force),
                success=lambda response: st.success(
                    f"{'Reused' if response.reused else 'Generated'} PaperCard"
                ),
            )


def render_card_panel(service: PaperIngestionService, paper_id: str) -> None:
    """Render a generated GNN PaperCard."""

    st.subheader("GNN PaperCard")
    try:
        card = service.get_paper_card(paper_id).card
    except (PaperNotFoundError, ChunksArtifactNotFoundError):
        st.info("Generate a PaperCard after chunking the paper.")
        return
    except Exception as exc:  # noqa: BLE001
        st.warning(f"PaperCard is not ready: {exc}")
        return

    render_card(card)


def render_card(card: PaperCard) -> None:
    """Render core PaperCard fields with citations."""

    if card.problem:
        render_cited_value("Problem", card.problem)

    sections = [
        ("Task type", card.task_type),
        ("Graph type", card.graph_type),
        ("Datasets", card.datasets),
        ("Node types", card.node_types),
        ("Edge types", card.edge_types),
        ("Model modules", card.model_modules),
        ("Losses", card.losses),
        ("Attacks", card.attacks),
        ("Defenses", card.defenses),
        ("Metrics", card.metrics),
        ("Baselines", card.baselines),
        ("Training setup", card.training_setup),
        ("Evaluation protocol", card.evaluation_protocol),
        ("Main results", card.main_results),
        ("Limitations", card.limitations),
        ("Missing implementation details", card.missing_implementation_details),
    ]
    for title, values in sections:
        render_cited_values(title, values)

    st.markdown("**Reproduction difficulty**")
    st.write(card.reproduction_difficulty.level)
    for reason in card.reproduction_difficulty.reasons:
        render_cited_value("Reason", reason)


def render_cited_values(title: str, values: list[CitedValue]) -> None:
    """Render a list of citation-backed values."""

    if not values:
        return
    st.markdown(f"**{title}**")
    for value in values:
        render_cited_value("", value)


def render_cited_value(title: str, value: CitedValue) -> None:
    """Render one citation-backed value."""

    label = f"{title}: {value.value}" if title else value.value
    st.write(label)
    render_citations(value.citations)


def render_qa_panel(service: PaperIngestionService, paper_id: str) -> None:
    """Render citation-backed single-paper QA."""

    st.subheader("Single-paper QA")
    question = st.text_area(
        "Question",
        placeholder="What datasets, metrics, and baselines are used?",
        height=100,
    )
    top_k = st.slider("Top-k chunks", min_value=1, max_value=10, value=6)
    if st.button("Ask", type="primary", use_container_width=True, disabled=not question.strip()):
        run_action(
            lambda: service.answer_question(paper_id, question=question.strip(), top_k=top_k),
            success=lambda response: set_last_qa(response.model_dump()),
        )

    response = st.session_state.get("last_qa")
    if response and response.get("paper_id") == paper_id:
        st.markdown("**Answer**")
        st.write(response["answer"])
        if response["unsupported_claims"]:
            st.warning("; ".join(response["unsupported_claims"]))
        render_citations([Citation.model_validate(item) for item in response["citations"]])


def render_comparison_workspace(service: PaperIngestionService) -> None:
    """Render Phase 2 multi-paper PaperCard comparison."""

    st.subheader("Multi-paper comparison")
    card_ready_papers = [
        paper
        for paper in service.repository.list_recent(limit=100)
        if service.get_paper_detail(paper.paper_id).artifacts.paper_card
    ]
    if len(card_ready_papers) < 2:
        st.info("Generate PaperCards for at least two papers before comparing them.")
        return

    paper_options = [paper.paper_id for paper in card_ready_papers]
    selected_papers = st.multiselect(
        "Papers",
        options=paper_options,
        default=paper_options[:2],
        format_func=lambda paper_id: _format_paper_option(paper_id, card_ready_papers),
    )
    dimensions = st.multiselect(
        "Dimensions",
        options=sorted(SUPPORTED_COMPARISON_DIMENSIONS),
        default=[
            "task_type",
            "datasets",
            "model_modules",
            "metrics",
            "baselines",
            "reproduction_difficulty",
        ],
    )

    if st.button(
        "Compare",
        type="primary",
        disabled=len(selected_papers) < 2,
        use_container_width=True,
    ):
        run_action(
            lambda: service.compare_papers(
                paper_ids=selected_papers,
                dimensions=dimensions,
            ),
            success=lambda response: set_last_comparison(response.model_dump()),
        )

    response_data = st.session_state.get("last_comparison")
    if response_data:
        render_comparison(PaperComparisonResponse.model_validate(response_data))


def render_comparison(response: PaperComparisonResponse) -> None:
    """Render comparison summary, matrix, and citations."""

    st.markdown("**Summary**")
    st.write(response.summary)
    st.dataframe(
        [
            {
                "paper_id": row.paper_id,
                **{
                    dimension: _format_comparison_values(row.values.get(dimension, []))
                    for dimension in response.dimensions
                },
            }
            for row in response.rows
        ],
        use_container_width=True,
        hide_index=True,
    )
    render_citations(response.citations)


def render_reproduction_plan_panel(service: PaperIngestionService, paper_id: str) -> None:
    """Render Phase 2 reproduction checklist generation and review."""

    st.subheader("Reproduction checklist")
    force = st.checkbox("Force regenerate reproduction plan", value=False)
    if st.button("Generate ReproductionPlan", type="primary", use_container_width=True):
        run_action(
            lambda: service.generate_reproduction_plan(paper_id=paper_id, force=force),
            success=lambda response: set_last_reproduction_plan(response.model_dump()),
        )

    response_data = st.session_state.get("last_reproduction_plan")
    if not response_data or response_data.get("paper_id") != paper_id:
        st.info("Generate a PaperCard first, then create a reproduction checklist.")
        return

    render_reproduction_plan(ReproductionPlan.model_validate(response_data["plan"]))


def render_reproduction_plan(plan: ReproductionPlan) -> None:
    """Render a generated reproduction plan as grouped checklist sections."""

    columns = st.columns(3)
    columns[0].metric("Difficulty", plan.estimated_difficulty)
    columns[1].metric("Checklist items", _count_checklist_items(plan))
    columns[2].metric("Generated", plan.generated_at.strftime("%Y-%m-%d %H:%M"))

    st.markdown("**Objective**")
    st.write(plan.objective)

    sections = [
        ("Environment", plan.environment),
        ("Data preparation", plan.data_preparation),
        ("Model implementation", plan.model_implementation),
        ("Attack or defense setup", plan.attack_or_defense_setup),
        ("Training pipeline", plan.training_pipeline),
        ("Evaluation", plan.evaluation),
        ("Ablation studies", plan.ablation_studies),
        ("Risks", plan.risks),
        ("Missing details", plan.missing_details),
    ]
    for title, items in sections:
        render_checklist_section(title, items)


def render_checklist_section(title: str, items: list[ChecklistItem]) -> None:
    """Render one reproduction checklist section."""

    if not items:
        return
    expanded = title in {"Data preparation", "Model implementation"}
    with st.expander(f"{title} ({len(items)})", expanded=expanded):
        for item in items:
            st.markdown(f"**[{item.status}]** {item.item}")
            if item.rationale:
                st.caption(item.rationale)
            render_citations(item.citations)


def render_method_spec_panel(service: PaperIngestionService, paper_id: str) -> None:
    """Render method_spec.yaml generation, preview, and download."""

    st.subheader("method_spec.yaml")
    force = st.checkbox("Force regenerate method_spec.yaml", value=False)
    if st.button("Generate method_spec.yaml", type="primary", use_container_width=True):
        run_action(
            lambda: service.generate_method_spec(paper_id=paper_id, force=force),
            success=lambda response: set_last_method_spec(
                response.model_dump(),
                service.get_method_spec_yaml(paper_id),
            ),
        )

    response_data = st.session_state.get("last_method_spec")
    yaml_text = st.session_state.get("last_method_spec_yaml")
    if not response_data or response_data.get("paper_id") != paper_id or not yaml_text:
        st.info(
            "Generate a PaperCard first, optionally generate a ReproductionPlan, "
            "then export MethodSpec."
        )
        return

    spec = MethodSpec.model_validate(response_data["spec"])
    action = "Reused" if response_data.get("reused") else "Generated"
    st.caption(f"{action} {response_data['yaml_path']}")
    columns = st.columns(4)
    columns[0].metric("Datasets", len(spec.datasets))
    columns[1].metric("Modules", len(spec.model_modules))
    columns[2].metric("Metrics", len(spec.metrics))
    columns[3].metric("Missing details", len(spec.missing_details))
    st.download_button(
        "Download YAML",
        data=yaml_text,
        file_name=f"{paper_id}.yaml",
        mime="application/x-yaml",
        use_container_width=True,
    )
    st.code(yaml_text, language="yaml")


def _count_checklist_items(plan: ReproductionPlan) -> int:
    return sum(
        len(items)
        for items in [
            plan.environment,
            plan.data_preparation,
            plan.model_implementation,
            plan.attack_or_defense_setup,
            plan.training_pipeline,
            plan.evaluation,
            plan.ablation_studies,
            plan.risks,
            plan.missing_details,
        ]
    )


def _format_comparison_values(values: list[CitedValue]) -> str:
    if not values:
        return ""
    return "; ".join(value.value for value in values)


def render_citations(citations: list[Citation]) -> None:
    """Render citations in expandable evidence blocks."""

    if not citations:
        return
    for citation in citations:
        label = (
            f"{citation.chunk_id}"
            f" | page {citation.page if citation.page is not None else '?'}"
            f" | {citation.section or 'unknown'}"
        )
        with st.expander(label):
            st.write(citation.evidence_text)


def run_action(action: Callable[[], object], success: Callable[[object], None]) -> None:
    """Run a service action and surface expected workflow errors."""

    try:
        result = action()
    except InvalidPaperUploadError as exc:
        st.error(str(exc))
    except ParsedArtifactNotFoundError:
        st.error("Parse the PDF before cleaning.")
    except CleanedArtifactNotFoundError:
        st.error("Clean the paper before generating chunks.")
    except ChunksArtifactNotFoundError:
        st.error("Generate chunks before this action.")
    except CardArtifactNotFoundError:
        st.error("Generate PaperCards before this action.")
    except PaperNotFoundError:
        st.error("Paper not found.")
    except Exception as exc:  # noqa: BLE001
        st.exception(exc)
    else:
        success(result)
        st.rerun()


def set_selected_paper(paper_id: str) -> None:
    st.session_state["selected_paper_id"] = paper_id


def set_last_qa(response: dict[str, object]) -> None:
    st.session_state["last_qa"] = response


def set_last_comparison(response: dict[str, object]) -> None:
    st.session_state["last_comparison"] = response


def set_last_reproduction_plan(response: dict[str, object]) -> None:
    st.session_state["last_reproduction_plan"] = response


def set_last_method_spec(response: dict[str, object], yaml_text: str) -> None:
    st.session_state["last_method_spec"] = response
    st.session_state["last_method_spec_yaml"] = yaml_text


def _format_paper_option(paper_id: str, papers: list[object]) -> str:
    for paper in papers:
        if getattr(paper, "paper_id", None) == paper_id:
            return f"{paper.filename} | {paper.status} | {paper.paper_id}"
    return paper_id


if __name__ == "__main__":
    main()
