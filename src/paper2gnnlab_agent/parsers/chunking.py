"""Chunk cleaned paragraphs into citation-ready evidence units."""

from dataclasses import dataclass
from datetime import UTC, datetime

from paper2gnnlab_agent.models.chunk import Chunk
from paper2gnnlab_agent.models.cleaned import CleanedParagraph
from paper2gnnlab_agent.models.common import Citation, SourceOffset


@dataclass(frozen=True)
class TextChunker:
    """Create stable chunks from cleaned paragraphs without crossing sections."""

    max_chars: int = 1800

    def chunk(self, paper_id: str, paragraphs: list[CleanedParagraph]) -> list[Chunk]:
        chunks: list[Chunk] = []
        buffer: list[CleanedParagraph] = []

        for paragraph in paragraphs:
            if not buffer:
                buffer = [paragraph]
                continue

            candidate_text = _join_text([*buffer, paragraph])
            same_section = paragraph.section == buffer[-1].section
            if same_section and len(candidate_text) <= self.max_chars:
                buffer.append(paragraph)
                continue

            chunks.append(_build_chunk(paper_id, len(chunks), buffer))
            buffer = [paragraph]

        if buffer:
            chunks.append(_build_chunk(paper_id, len(chunks), buffer))

        return chunks


def _build_chunk(paper_id: str, index: int, paragraphs: list[CleanedParagraph]) -> Chunk:
    text = _join_text(paragraphs)
    page_start = min(paragraph.page for paragraph in paragraphs)
    page_end = max(paragraph.page for paragraph in paragraphs)
    section = paragraphs[0].section
    chunk_id = f"chunk_{paper_id.removeprefix('paper_')}_{index + 1:04d}"
    evidence_text = text[:500]
    citation = Citation(
        paper_id=paper_id,
        chunk_id=chunk_id,
        page=page_start,
        section=section,
        evidence_text=evidence_text,
    )
    return Chunk(
        chunk_id=chunk_id,
        paper_id=paper_id,
        index=index + 1,
        page_start=page_start,
        page_end=page_end,
        section=section,
        text=text,
        evidence_text=evidence_text,
        token_count=len(text.split()),
        source_offsets=[SourceOffset(page=paragraph.page) for paragraph in paragraphs],
        citation=citation,
        created_at=datetime.now(UTC),
    )


def _join_text(paragraphs: list[CleanedParagraph]) -> str:
    return "\n\n".join(paragraph.text for paragraph in paragraphs)
