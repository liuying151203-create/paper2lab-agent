from pathlib import Path

from paper2gnnlab_agent.models.card import ReproductionDifficulty
from paper2gnnlab_agent.models.common import CitedValue
from paper2gnnlab_agent.models.parsed import ParsedPage
from paper2gnnlab_agent.services.papers import (
    PaperIngestionService,
    build_paper_id,
    compute_file_hash,
)
from paper2gnnlab_agent.storage.paper_repository import PaperRepository
from paper2gnnlab_agent.storage.paths import StoragePaths


class FakeParser:
    name = "fake"

    def parse_pages(self, pdf_path: Path) -> list[ParsedPage]:
        return [
            ParsedPage(
                page=1,
                text=(
                    f"parsed from {pdf_path.name}. We propose a GCN for node "
                    "classification on Cora."
                ),
            ),
            ParsedPage(
                page=2,
                text=(
                    "Experiments use accuracy with Adam optimizer, learning rate 0.01, "
                    "and 200 epochs."
                ),
            ),
        ]


def make_paths(tmp_path: Path) -> StoragePaths:
    return StoragePaths(
        data_dir=tmp_path,
        papers_dir=tmp_path / "papers",
        parsed_dir=tmp_path / "parsed",
        cleaned_dir=tmp_path / "cleaned",
        chunks_dir=tmp_path / "chunks",
        cards_dir=tmp_path / "cards",
        specs_dir=tmp_path / "specs",
        generated_projects_dir=tmp_path / "generated_projects",
        sqlite_path=tmp_path / "metadata.sqlite3",
    )


def test_upload_pdf_creates_metadata_and_reuses_hash(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    service = PaperIngestionService(
        repository=PaperRepository(paths.sqlite_path),
        paths=paths,
    )
    content = b"%PDF-1.4\nminimal test pdf\n"

    first = service.upload_pdf("gnn-paper.pdf", content)
    second = service.upload_pdf("same-paper.pdf", content)

    file_hash = compute_file_hash(content)
    assert first.paper_id == build_paper_id(file_hash)
    assert first.file_hash == file_hash
    assert first.reused is False
    assert first.next_actions == ["parse"]
    assert (paths.papers_dir / f"{first.paper_id}.pdf").read_bytes() == content

    assert second.paper_id == first.paper_id
    assert second.reused is True
    assert second.filename == "gnn-paper.pdf"

    detail = service.get_paper_detail(first.paper_id)
    assert detail.status == "uploaded"
    assert detail.artifacts.parsed is False
    assert detail.artifacts.cleaned is False
    assert detail.artifacts.chunks is False


def test_parse_pdf_writes_page_text_cleans_text_and_reuses_artifacts(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    service = PaperIngestionService(
        repository=PaperRepository(paths.sqlite_path),
        paths=paths,
        parser=FakeParser(),
    )
    upload = service.upload_pdf("gnn-paper.pdf", b"%PDF-1.4\nminimal test pdf\n")

    parsed = service.parse_pdf(upload.paper_id)
    reused = service.parse_pdf(upload.paper_id)
    cleaned = service.clean_parsed_text(upload.paper_id)
    chunked = service.generate_chunks(upload.paper_id, max_chars=120)
    reused_chunks = service.generate_chunks(upload.paper_id)
    listed_chunks = service.list_chunks(upload.paper_id)
    card = service.generate_paper_card(upload.paper_id)
    reused_card = service.get_paper_card(upload.paper_id)
    qa = service.answer_question(upload.paper_id, "What task and dataset are used?", top_k=2)
    detail = service.get_paper_detail(upload.paper_id)

    assert parsed.status == "cleaned"
    assert parsed.pages_count == 2
    assert parsed.reused is False
    assert reused.reused is True
    assert cleaned.reused is True
    assert chunked.status == "chunked"
    assert chunked.chunks_count >= 1
    assert reused_chunks.reused is True
    assert listed_chunks.total == chunked.chunks_count
    assert listed_chunks.items[0].citation.paper_id == upload.paper_id
    assert card.status == "card_ready"
    assert card.card.task_type[0].value == "node classification"
    assert card.card.task_type[0].citations[0].paper_id == upload.paper_id
    assert reused_card.reused is True
    assert qa.citations
    assert qa.citations[0].paper_id == upload.paper_id
    assert detail.status == "card_ready"
    assert detail.artifacts.parsed is True
    assert detail.artifacts.cleaned is True
    assert detail.artifacts.chunks is True
    assert detail.artifacts.paper_card is True
    assert (paths.parsed_dir / f"{upload.paper_id}.json").exists()
    assert (paths.cleaned_dir / f"{upload.paper_id}.json").exists()
    assert (paths.chunks_dir / f"{upload.paper_id}.jsonl").exists()
    assert (paths.cards_dir / f"{upload.paper_id}.json").exists()


def test_reviewed_paper_card_is_preferred_for_quality_and_downstream(
    tmp_path: Path,
) -> None:
    paths = make_paths(tmp_path)
    service = PaperIngestionService(
        repository=PaperRepository(paths.sqlite_path),
        paths=paths,
        parser=FakeParser(),
    )
    upload = service.upload_pdf("gnn-paper.pdf", b"%PDF-1.4\nminimal test pdf\n")
    service.parse_pdf(upload.paper_id)
    service.generate_chunks(upload.paper_id, max_chars=120)
    original = service.generate_paper_card(upload.paper_id).card
    reviewed = original.model_copy(
        update={
            "datasets": [CitedValue(value="ReviewedSet", confidence="unknown")],
            "reproduction_difficulty": ReproductionDifficulty(level="high"),
        }
    )
    eval_dir = paths.data_dir / "eval"
    eval_dir.mkdir(parents=True, exist_ok=True)
    (eval_dir / f"{upload.paper_id}.golden.json").write_text(
        '{"datasets": ["ReviewedSet"]}',
        encoding="utf-8",
    )

    service.save_reviewed_paper_card(upload.paper_id, reviewed)
    loaded = service.get_paper_card(upload.paper_id).card
    report = service.evaluate_paper_card(upload.paper_id)
    plan = service.generate_reproduction_plan(upload.paper_id, force=True).plan

    assert loaded.datasets[0].value == "ReviewedSet"
    assert report.golden_available is True
    assert any(
        field.field == "datasets" and field.recall == 1.0
        for field in report.fields
    )
    assert any("ReviewedSet" in item.item for item in plan.data_preparation)
