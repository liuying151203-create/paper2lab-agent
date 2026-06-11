from pathlib import Path

from fastapi.testclient import TestClient

from paper2gnnlab_agent.api.app import create_app
from paper2gnnlab_agent.api.dependencies import get_paper_service
from paper2gnnlab_agent.services.papers import PaperIngestionService
from paper2gnnlab_agent.storage.paper_repository import PaperRepository
from paper2gnnlab_agent.storage.paths import StoragePaths


def test_api_upload_reuse_and_get_paper(tmp_path: Path) -> None:
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
    service = PaperIngestionService(PaperRepository(paths.sqlite_path), paths)
    app = create_app()
    app.dependency_overrides[get_paper_service] = lambda: service
    client = TestClient(app)

    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    upload = client.post(
        "/api/v1/papers",
        files={"file": ("paper.pdf", b"%PDF-1.4\nminimal test pdf\n", "application/pdf")},
    )
    assert upload.status_code == 201
    payload = upload.json()
    assert payload["reused"] is False
    assert payload["status"] == "uploaded"
    assert payload["next_actions"] == ["parse"]

    reused = client.post(
        "/api/v1/papers",
        files={"file": ("paper-copy.pdf", b"%PDF-1.4\nminimal test pdf\n", "application/pdf")},
    )
    assert reused.status_code == 201
    assert reused.json()["paper_id"] == payload["paper_id"]
    assert reused.json()["reused"] is True

    detail = client.get(f"/api/v1/papers/{payload['paper_id']}")
    assert detail.status_code == 200
    assert detail.json()["artifacts"] == {
        "chunks": False,
        "paper_card": False,
        "method_spec": False,
    }
