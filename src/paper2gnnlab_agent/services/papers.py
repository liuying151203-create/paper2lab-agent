"""Paper upload, hash reuse, and metadata lookup workflows."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from paper2gnnlab_agent.models.card import PaperCard, PaperCardResponse
from paper2gnnlab_agent.models.chunk import (
    Chunk,
    ChunkListResponse,
    GenerateChunksResponse,
)
from paper2gnnlab_agent.models.cleaned import CleanedPaper, CleanPaperResponse
from paper2gnnlab_agent.models.paper import (
    Paper,
    PaperArtifacts,
    PaperDetailResponse,
    PaperUploadResponse,
)
from paper2gnnlab_agent.models.parsed import ParsedPaper, ParsePaperResponse
from paper2gnnlab_agent.parsers.chunking import TextChunker
from paper2gnnlab_agent.parsers.cleaning import TextCleaner
from paper2gnnlab_agent.parsers.pdf import PdfParser, PdfParsingError, PypdfParser
from paper2gnnlab_agent.services.card_extraction import RuleBasedPaperCardExtractor
from paper2gnnlab_agent.storage.chunk_repository import ChunkRepository
from paper2gnnlab_agent.storage.paper_repository import PaperRepository
from paper2gnnlab_agent.storage.paths import StoragePaths


class PaperNotFoundError(ValueError):
    """Raised when a paper_id cannot be found."""


class InvalidPaperUploadError(ValueError):
    """Raised when an uploaded file is not acceptable for ingestion."""


class PaperIngestionService:
    """Coordinate PDF upload, file hash reuse, and metadata persistence."""

    def __init__(
        self,
        repository: PaperRepository,
        paths: StoragePaths,
        parser: PdfParser | None = None,
        cleaner: TextCleaner | None = None,
        chunk_repository: ChunkRepository | None = None,
        card_extractor: RuleBasedPaperCardExtractor | None = None,
    ) -> None:
        self.repository = repository
        self.paths = paths
        self.parser = parser or PypdfParser()
        self.cleaner = cleaner or TextCleaner()
        self.chunk_repository = chunk_repository or ChunkRepository(repository.sqlite_path)
        self.card_extractor = card_extractor or RuleBasedPaperCardExtractor()

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
            parsed=self._parsed_path(paper_id).exists(),
            cleaned=self._cleaned_path(paper_id).exists(),
            chunks=(self.paths.chunks_dir / f"{paper_id}.jsonl").exists(),
            paper_card=(self.paths.cards_dir / f"{paper_id}.json").exists(),
            method_spec=(self.paths.specs_dir / f"{paper_id}.yaml").exists(),
        )
        return PaperDetailResponse(**paper.model_dump(), artifacts=artifacts)

    def parse_pdf(self, paper_id: str, force: bool = False) -> ParsePaperResponse:
        """Extract page-level PDF text and persist the parsed artifact."""

        paper = self.repository.get_by_id(paper_id)
        if paper is None:
            raise PaperNotFoundError(paper_id)

        parsed_path = self._parsed_path(paper_id)
        if parsed_path.exists() and not force:
            parsed = _read_parsed_paper(parsed_path)
            return ParsePaperResponse(
                paper_id=paper_id,
                status=paper.status,
                pages_count=len(parsed.pages),
                reused=True,
            )

        self.repository.update_status(paper_id, "parsing")
        try:
            pages = self.parser.parse_pages(Path(paper.source_path))
            parsed = ParsedPaper(
                paper_id=paper_id,
                pages=pages,
                parser=self.parser.name,
                parsed_at=datetime.now(UTC),
            )
            self.paths.parsed_dir.mkdir(parents=True, exist_ok=True)
            parsed_path.write_text(
                parsed.model_dump_json(indent=2),
                encoding="utf-8",
            )
            clean_response = self.clean_parsed_text(paper_id=paper_id, force=True)
            return ParsePaperResponse(
                paper_id=paper_id,
                status=clean_response.status,
                pages_count=len(pages),
                reused=False,
            )
        except PdfParsingError as exc:
            self.repository.update_status(paper_id, "failed", error_message=str(exc))
            raise

    def clean_parsed_text(self, paper_id: str, force: bool = False) -> CleanPaperResponse:
        """Clean parsed page text and persist paragraph-level section metadata."""

        paper = self.repository.get_by_id(paper_id)
        if paper is None:
            raise PaperNotFoundError(paper_id)

        parsed_path = self._parsed_path(paper_id)
        if not parsed_path.exists():
            raise ParsedArtifactNotFoundError(paper_id)

        cleaned_path = self._cleaned_path(paper_id)
        if cleaned_path.exists() and not force:
            cleaned = _read_cleaned_paper(cleaned_path)
            return CleanPaperResponse(
                paper_id=paper_id,
                status=paper.status,
                paragraphs_count=len(cleaned.paragraphs),
                sections=_sections_from_cleaned(cleaned),
                reused=True,
            )

        parsed = _read_parsed_paper(parsed_path)
        paragraphs = self.cleaner.clean(parsed)
        cleaned = CleanedPaper(
            paper_id=paper_id,
            paragraphs=paragraphs,
            cleaner=self.cleaner.name,
            cleaned_at=datetime.now(UTC),
        )
        self.paths.cleaned_dir.mkdir(parents=True, exist_ok=True)
        cleaned_path.write_text(
            cleaned.model_dump_json(indent=2),
            encoding="utf-8",
        )
        updated = self.repository.update_status(paper_id, "cleaned")
        return CleanPaperResponse(
            paper_id=paper_id,
            status=updated.status if updated else "cleaned",
            paragraphs_count=len(paragraphs),
            sections=_sections_from_cleaned(cleaned),
            reused=False,
        )

    def generate_chunks(
        self,
        paper_id: str,
        force: bool = False,
        max_chars: int = 1800,
    ) -> GenerateChunksResponse:
        """Generate citation-ready chunks from cleaned paragraph text."""

        paper = self.repository.get_by_id(paper_id)
        if paper is None:
            raise PaperNotFoundError(paper_id)

        chunks_path = self._chunks_path(paper_id)
        if chunks_path.exists() and not force:
            chunks = _read_chunks(chunks_path)
            return GenerateChunksResponse(
                paper_id=paper_id,
                status=paper.status,
                chunks_count=len(chunks),
                reused=True,
            )

        cleaned_path = self._cleaned_path(paper_id)
        if not cleaned_path.exists():
            raise CleanedArtifactNotFoundError(paper_id)

        cleaned = _read_cleaned_paper(cleaned_path)
        chunks = TextChunker(max_chars=max_chars).chunk(paper_id, cleaned.paragraphs)
        self.paths.chunks_dir.mkdir(parents=True, exist_ok=True)
        _write_chunks(chunks_path, chunks)
        self.chunk_repository.replace_for_paper(paper_id, chunks, chunks_path)
        updated = self.repository.update_status(paper_id, "chunked")
        return GenerateChunksResponse(
            paper_id=paper_id,
            status=updated.status if updated else "chunked",
            chunks_count=len(chunks),
            reused=False,
        )

    def list_chunks(
        self,
        paper_id: str,
        section: str | None = None,
        page: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ChunkListResponse:
        """Return chunks with full text loaded from JSONL storage."""

        if self.repository.get_by_id(paper_id) is None:
            raise PaperNotFoundError(paper_id)

        chunks_path = self._chunks_path(paper_id)
        if not chunks_path.exists():
            raise ChunksArtifactNotFoundError(paper_id)

        chunks = _read_chunks(chunks_path)
        filtered = [
            chunk
            for chunk in chunks
            if (section is None or chunk.section == section)
            and (page is None or chunk.page_start <= page <= chunk.page_end)
        ]
        return ChunkListResponse(
            paper_id=paper_id,
            total=len(filtered),
            items=filtered[offset : offset + limit],
        )

    def generate_paper_card(self, paper_id: str, force: bool = False) -> PaperCardResponse:
        """Generate and persist a GNN-specific paper card from chunks."""

        paper = self.repository.get_by_id(paper_id)
        if paper is None:
            raise PaperNotFoundError(paper_id)

        card_path = self._card_path(paper_id)
        if card_path.exists() and not force:
            card = _read_paper_card(card_path)
            return PaperCardResponse(
                paper_id=paper_id,
                status="card_ready",
                card=card,
                reused=True,
            )

        chunks_path = self._chunks_path(paper_id)
        if not chunks_path.exists():
            raise ChunksArtifactNotFoundError(paper_id)

        chunks = _read_chunks(chunks_path)
        card = self.card_extractor.extract(paper_id=paper_id, chunks=chunks)
        self.paths.cards_dir.mkdir(parents=True, exist_ok=True)
        _write_paper_card(card_path, card)
        self.repository.update_status(paper_id, "card_ready")
        return PaperCardResponse(
            paper_id=paper_id,
            status="card_ready",
            card=card,
            reused=False,
        )

    def get_paper_card(self, paper_id: str) -> PaperCardResponse:
        """Read a generated GNN-specific paper card without implicit generation."""

        if self.repository.get_by_id(paper_id) is None:
            raise PaperNotFoundError(paper_id)

        card_path = self._card_path(paper_id)
        if not card_path.exists():
            raise CardArtifactNotFoundError(paper_id)

        return PaperCardResponse(
            paper_id=paper_id,
            status="card_ready",
            card=_read_paper_card(card_path),
            reused=True,
        )

    @staticmethod
    def _validate_pdf(filename: str, content: bytes) -> None:
        if not filename.lower().endswith(".pdf"):
            raise InvalidPaperUploadError("Only PDF files are supported.")
        if not content:
            raise InvalidPaperUploadError("Uploaded PDF is empty.")

    def _parsed_path(self, paper_id: str) -> Path:
        return self.paths.parsed_dir / f"{paper_id}.json"

    def _cleaned_path(self, paper_id: str) -> Path:
        return self.paths.cleaned_dir / f"{paper_id}.json"

    def _chunks_path(self, paper_id: str) -> Path:
        return self.paths.chunks_dir / f"{paper_id}.jsonl"

    def _card_path(self, paper_id: str) -> Path:
        return self.paths.cards_dir / f"{paper_id}.json"


def compute_file_hash(content: bytes) -> str:
    """Return the SHA-256 hex digest for uploaded PDF bytes."""

    return hashlib.sha256(content).hexdigest()


def build_paper_id(file_hash: str) -> str:
    """Build a stable paper_id from the file hash."""

    return f"paper_{file_hash[:12]}"


def build_paper_service(
    repository: PaperRepository,
    paths: StoragePaths,
    parser: PdfParser | None = None,
    cleaner: TextCleaner | None = None,
    chunk_repository: ChunkRepository | None = None,
    card_extractor: RuleBasedPaperCardExtractor | None = None,
) -> PaperIngestionService:
    """Factory used by API dependencies and tests."""

    return PaperIngestionService(
        repository=repository,
        paths=paths,
        parser=parser,
        cleaner=cleaner,
        chunk_repository=chunk_repository,
        card_extractor=card_extractor,
    )


def _next_actions_for_status(status: str) -> list[str]:
    if status == "uploaded":
        return ["parse"]
    if status == "parsed":
        return ["clean"]
    if status in {"cleaned", "chunked"}:
        return ["card"]
    if status == "card_ready":
        return ["qa"]
    return []


def _read_parsed_paper(path: Path) -> ParsedPaper:
    return ParsedPaper.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _read_cleaned_paper(path: Path) -> CleanedPaper:
    return CleanedPaper.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _sections_from_cleaned(cleaned: CleanedPaper) -> list[str]:
    return sorted({paragraph.section for paragraph in cleaned.paragraphs})


def _write_chunks(path: Path, chunks: list[Chunk]) -> None:
    path.write_text(
        "\n".join(chunk.model_dump_json() for chunk in chunks) + ("\n" if chunks else ""),
        encoding="utf-8",
    )


def _read_chunks(path: Path) -> list[Chunk]:
    return [
        Chunk.model_validate(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_paper_card(path: Path, card: PaperCard) -> None:
    path.write_text(card.model_dump_json(indent=2), encoding="utf-8")


def _read_paper_card(path: Path) -> PaperCard:
    return PaperCard.model_validate(json.loads(path.read_text(encoding="utf-8")))


class ParsedArtifactNotFoundError(ValueError):
    """Raised when cleaning is requested before PDF parsing has produced text."""


class CleanedArtifactNotFoundError(ValueError):
    """Raised when chunking is requested before cleaning has produced text."""


class ChunksArtifactNotFoundError(ValueError):
    """Raised when chunks are requested before chunking has produced text."""


class CardArtifactNotFoundError(ValueError):
    """Raised when a paper card is requested before generation."""
