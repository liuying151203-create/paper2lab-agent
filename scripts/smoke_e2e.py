"""Run an end-to-end smoke test over the real Phase 1 service workflow."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from paper2gnnlab_agent.samples import build_minimal_gnn_pdf_bytes  # noqa: E402
from paper2gnnlab_agent.services.papers import build_paper_service  # noqa: E402
from paper2gnnlab_agent.storage.paper_repository import PaperRepository  # noqa: E402
from paper2gnnlab_agent.storage.paths import StoragePaths  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Smoke test data directory. Defaults to a timestamped .tmp/smoke-runs directory.",
    )
    parser.add_argument(
        "--pdf-path",
        type=Path,
        default=Path(".tmp/smoke/minimal_gnn_paper.pdf"),
        help="Where to write the generated sample PDF.",
    )
    parser.add_argument(
        "--question",
        default="What datasets, model modules, metrics, and baselines are used?",
        help="Single-paper QA question.",
    )
    args = parser.parse_args()

    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    data_dir = args.data_dir or Path(".tmp") / "smoke-runs" / run_id
    pdf_path = args.pdf_path
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(build_minimal_gnn_pdf_bytes())

    service = build_paper_service(
        repository=PaperRepository(data_dir / "metadata.sqlite3"),
        paths=_build_paths(data_dir),
    )

    upload = service.upload_pdf("minimal_gnn_paper.pdf", pdf_path.read_bytes())
    parsed = service.parse_pdf(upload.paper_id, force=True)
    chunks = service.generate_chunks(upload.paper_id, force=True, max_chars=900)
    card = service.generate_paper_card(upload.paper_id, force=True)
    qa = service.answer_question(upload.paper_id, question=args.question, top_k=6)
    detail = service.get_paper_detail(upload.paper_id)

    summary = {
        "ok": True,
        "paper_id": upload.paper_id,
        "data_dir": str(data_dir),
        "pdf_path": str(pdf_path),
        "status": detail.status,
        "pages_count": parsed.pages_count,
        "chunks_count": chunks.chunks_count,
        "artifacts": detail.artifacts.model_dump(),
        "card": {
            "task_type": [item.value for item in card.card.task_type],
            "datasets": [item.value for item in card.card.datasets],
            "model_modules": [item.value for item in card.card.model_modules],
            "metrics": [item.value for item in card.card.metrics],
            "baselines": [item.value for item in card.card.baselines],
            "reproduction_difficulty": card.card.reproduction_difficulty.level,
        },
        "qa": {
            "question": qa.question,
            "answer": qa.answer,
            "citations_count": len(qa.citations),
            "unsupported_claims": qa.unsupported_claims,
        },
    }
    _assert_smoke_summary(summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _build_paths(data_dir: Path) -> StoragePaths:
    return StoragePaths(
        data_dir=data_dir,
        papers_dir=data_dir / "papers",
        parsed_dir=data_dir / "parsed",
        cleaned_dir=data_dir / "cleaned",
        chunks_dir=data_dir / "chunks",
        cards_dir=data_dir / "cards",
        specs_dir=data_dir / "specs",
        generated_projects_dir=data_dir / "generated_projects",
        sqlite_path=data_dir / "metadata.sqlite3",
    )


def _assert_smoke_summary(summary: dict[str, object]) -> None:
    artifacts = summary["artifacts"]
    card = summary["card"]
    qa = summary["qa"]
    assert isinstance(artifacts, dict)
    assert isinstance(card, dict)
    assert isinstance(qa, dict)
    assert summary["status"] == "card_ready"
    assert summary["pages_count"] >= 1
    assert summary["chunks_count"] >= 1
    assert artifacts["parsed"] is True
    assert artifacts["cleaned"] is True
    assert artifacts["chunks"] is True
    assert artifacts["paper_card"] is True
    assert "node classification" in card["task_type"]
    assert "Cora" in card["datasets"]
    assert "GCN" in card["model_modules"]
    assert qa["citations_count"] >= 1
    assert qa["unsupported_claims"] == []


if __name__ == "__main__":
    main()
