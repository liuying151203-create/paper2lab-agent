"""PDF page-level text extraction."""

from pathlib import Path
from typing import Protocol

from pypdf import PdfReader

from paper2gnnlab_agent.models.parsed import ParsedPage


class PdfParsingError(ValueError):
    """Raised when PDF text extraction fails."""


class PdfParser(Protocol):
    """Interface for PDF parsers used by the ingestion workflow."""

    name: str

    def parse_pages(self, pdf_path: Path) -> list[ParsedPage]:
        """Extract page-level text from a PDF path."""


class PypdfParser:
    """Lightweight parser backed by pypdf."""

    name = "pypdf"

    def parse_pages(self, pdf_path: Path) -> list[ParsedPage]:
        try:
            reader = PdfReader(pdf_path)
            return [
                ParsedPage(page=index + 1, text=page.extract_text() or "")
                for index, page in enumerate(reader.pages)
            ]
        except Exception as exc:  # pypdf raises several parser-specific exceptions.
            raise PdfParsingError(f"Failed to parse PDF: {pdf_path}") from exc
