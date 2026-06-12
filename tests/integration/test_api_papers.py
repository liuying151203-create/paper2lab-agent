from pathlib import Path

from fastapi.testclient import TestClient

from paper2gnnlab_agent.api.app import create_app
from paper2gnnlab_agent.api.dependencies import get_paper_service
from paper2gnnlab_agent.models.parsed import ParsedPage
from paper2gnnlab_agent.services.papers import PaperIngestionService
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
                    "classification on Cora and report accuracy."
                ),
            )
        ]


def test_api_upload_reuse_and_get_paper(tmp_path: Path) -> None:
    paths = StoragePaths(
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
    service = PaperIngestionService(PaperRepository(paths.sqlite_path), paths, parser=FakeParser())
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
        "parsed": False,
        "cleaned": False,
        "chunks": False,
        "paper_card": False,
        "method_spec": False,
    }

    parsed = client.post(f"/api/v1/papers/{payload['paper_id']}/parse", json={"force": False})
    assert parsed.status_code == 200
    assert parsed.json() == {
        "paper_id": payload["paper_id"],
        "status": "cleaned",
        "pages_count": 1,
        "reused": False,
    }

    reused_parse = client.post(f"/api/v1/papers/{payload['paper_id']}/parse", json={"force": False})
    assert reused_parse.status_code == 200
    assert reused_parse.json()["reused"] is True

    clean = client.post(f"/api/v1/papers/{payload['paper_id']}/clean", json={"force": False})
    assert clean.status_code == 200
    assert clean.json()["reused"] is True
    assert clean.json()["paragraphs_count"] == 1

    chunked = client.post(
        f"/api/v1/papers/{payload['paper_id']}/chunks",
        json={"force": False, "max_chars": 200},
    )
    assert chunked.status_code == 200
    assert chunked.json()["status"] == "chunked"
    assert chunked.json()["chunks_count"] == 1

    chunks = client.get(f"/api/v1/papers/{payload['paper_id']}/chunks")
    assert chunks.status_code == 200
    chunks_payload = chunks.json()
    assert chunks_payload["total"] == 1
    assert chunks_payload["items"][0]["paper_id"] == payload["paper_id"]
    assert chunks_payload["items"][0]["citation"]["paper_id"] == payload["paper_id"]

    card = client.post(f"/api/v1/papers/{payload['paper_id']}/card", json={"force": False})
    assert card.status_code == 200
    card_payload = card.json()
    assert card_payload["status"] == "card_ready"
    assert card_payload["reused"] is False
    assert card_payload["card"]["task_type"][0]["value"] == "node classification"
    assert card_payload["card"]["task_type"][0]["citations"][0]["paper_id"] == payload["paper_id"]

    loaded_card = client.get(f"/api/v1/papers/{payload['paper_id']}/card")
    assert loaded_card.status_code == 200
    assert loaded_card.json()["reused"] is True

    reproduction_plan = client.post(
        f"/api/v1/papers/{payload['paper_id']}/reproduction-plan",
        json={"force": False},
    )
    assert reproduction_plan.status_code == 200
    reproduction_payload = reproduction_plan.json()
    assert reproduction_payload["status"] == "reproduction_plan_ready"
    assert reproduction_payload["reused"] is False
    assert reproduction_payload["plan"]["paper_id"] == payload["paper_id"]
    assert reproduction_payload["plan"]["estimated_difficulty"] in {
        "low",
        "medium",
        "high",
        "unknown",
    }
    assert reproduction_payload["plan"]["data_preparation"]
    assert reproduction_payload["plan"]["model_implementation"]
    assert reproduction_payload["plan"]["evaluation"]

    reused_plan = client.post(
        f"/api/v1/papers/{payload['paper_id']}/reproduction-plan",
        json={"force": False},
    )
    assert reused_plan.status_code == 200
    assert reused_plan.json()["reused"] is True

    qa = client.post(
        f"/api/v1/papers/{payload['paper_id']}/qa",
        json={"question": "What task and dataset are used?", "top_k": 3},
    )
    assert qa.status_code == 200
    qa_payload = qa.json()
    assert qa_payload["paper_id"] == payload["paper_id"]
    assert qa_payload["unsupported_claims"] == []
    assert qa_payload["citations"][0]["paper_id"] == payload["paper_id"]

    second_upload = client.post(
        "/api/v1/papers",
        files={"file": ("paper-2.pdf", b"%PDF-1.4\nminimal test pdf 2\n", "application/pdf")},
    )
    assert second_upload.status_code == 201
    second_payload = second_upload.json()
    assert second_payload["paper_id"] != payload["paper_id"]
    assert client.post(
        f"/api/v1/papers/{second_payload['paper_id']}/parse",
        json={"force": False},
    ).status_code == 200
    assert client.post(
        f"/api/v1/papers/{second_payload['paper_id']}/chunks",
        json={"force": False, "max_chars": 200},
    ).status_code == 200
    assert client.post(
        f"/api/v1/papers/{second_payload['paper_id']}/card",
        json={"force": False},
    ).status_code == 200

    comparison = client.post(
        "/api/v1/comparisons",
        json={
            "paper_ids": [payload["paper_id"], second_payload["paper_id"]],
            "dimensions": ["task_type", "datasets", "metrics"],
        },
    )
    assert comparison.status_code == 200
    comparison_payload = comparison.json()
    assert comparison_payload["dimensions"] == ["task_type", "datasets", "metrics"]
    assert len(comparison_payload["rows"]) == 2
    assert comparison_payload["citations"]
    assert "Compared 2 papers" in comparison_payload["summary"]
