from pathlib import Path

from paper2gnnlab_agent.services.papers import (
    PaperIngestionService,
    build_paper_id,
    compute_file_hash,
)
from paper2gnnlab_agent.storage.paper_repository import PaperRepository
from paper2gnnlab_agent.storage.paths import StoragePaths


def test_upload_pdf_creates_metadata_and_reuses_hash(tmp_path: Path) -> None:
    paths = StoragePaths(
        data_dir=tmp_path,
        papers_dir=tmp_path / "papers",
        parsed_dir=tmp_path / "parsed",
        chunks_dir=tmp_path / "chunks",
        cards_dir=tmp_path / "cards",
        specs_dir=tmp_path / "specs",
        generated_projects_dir=tmp_path / "generated_projects",
        sqlite_path=tmp_path / "metadata.sqlite3",
    )
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
    assert detail.artifacts.chunks is False
