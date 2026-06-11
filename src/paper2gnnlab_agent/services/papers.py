"""Paper upload, hash reuse, and metadata lookup workflows."""

import hashlib
from datetime import UTC, datetime

from paper2gnnlab_agent.models.paper import (
    Paper,
    PaperArtifacts,
    PaperDetailResponse,
    PaperUploadResponse,
)
from paper2gnnlab_agent.storage.paper_repository import PaperRepository
from paper2gnnlab_agent.storage.paths import StoragePaths


class PaperNotFoundError(ValueError):
    """Raised when a paper_id cannot be found."""


class InvalidPaperUploadError(ValueError):
    """Raised when an uploaded file is not acceptable for ingestion."""


class PaperIngestionService:
    """Coordinate PDF upload, file hash reuse, and metadata persistence."""

    def __init__(self, repository: PaperRepository, paths: StoragePaths) -> None:
        self.repository = repository
        self.paths = paths

    def upload_pdf(self, filename: str, content: bytes) -> PaperUploadResponse:
        """Persist a new PDF or reuse an existing paper by SHA-256 hash."""

        self._validate_pdf(filename, content)
        file_hash = compute_file_hash(content)

        existing = self.repository.get_by_hash(file_hash)
        if existing is not None:
            return PaperUploadResponse(
                paper_id=existing.paper_id,
                file_hash=existing.file_hash,
                filename=existing.filename,
                status=existing.status,
                reused=True,
                next_actions=_next_actions_for_status(existing.status),
            )

        paper_id = build_paper_id(file_hash)
        source_path = self.paths.papers_dir / f"{paper_id}.pdf"
        self.paths.papers_dir.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes(content)

        now = datetime.now(UTC)
        paper = Paper(
            paper_id=paper_id,
            file_hash=file_hash,
            filename=filename,
            source_path=str(source_path),
            status="uploaded",
            created_at=now,
            updated_at=now,
        )
        self.repository.create(paper)

        return PaperUploadResponse(
            paper_id=paper.paper_id,
            file_hash=paper.file_hash,
            filename=paper.filename,
            status=paper.status,
            reused=False,
            next_actions=["parse"],
        )

    def get_paper_detail(self, paper_id: str) -> PaperDetailResponse:
        """Load paper metadata and current local artifact readiness."""

        paper = self.repository.get_by_id(paper_id)
        if paper is None:
            raise PaperNotFoundError(paper_id)

        artifacts = PaperArtifacts(
            chunks=(self.paths.chunks_dir / f"{paper_id}.jsonl").exists(),
            paper_card=(self.paths.cards_dir / f"{paper_id}.json").exists(),
            method_spec=(self.paths.specs_dir / f"{paper_id}.yaml").exists(),
        )
        return PaperDetailResponse(**paper.model_dump(), artifacts=artifacts)

    @staticmethod
    def _validate_pdf(filename: str, content: bytes) -> None:
        if not filename.lower().endswith(".pdf"):
            raise InvalidPaperUploadError("Only PDF files are supported.")
        if not content:
            raise InvalidPaperUploadError("Uploaded PDF is empty.")


def compute_file_hash(content: bytes) -> str:
    """Return the SHA-256 hex digest for uploaded PDF bytes."""

    return hashlib.sha256(content).hexdigest()


def build_paper_id(file_hash: str) -> str:
    """Build a stable paper_id from the file hash."""

    return f"paper_{file_hash[:12]}"


def build_paper_service(repository: PaperRepository, paths: StoragePaths) -> PaperIngestionService:
    """Factory used by API dependencies and tests."""

    return PaperIngestionService(repository=repository, paths=paths)


def _next_actions_for_status(status: str) -> list[str]:
    if status == "uploaded":
        return ["parse"]
    if status in {"parsed", "chunked"}:
        return ["card"]
    return []
