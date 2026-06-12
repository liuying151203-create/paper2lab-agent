"""Rule-based text cleaning and section recognition for GNN papers."""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from paper2gnnlab_agent.models.cleaned import CleanedParagraph
from paper2gnnlab_agent.models.parsed import ParsedPaper

SECTION_ALIASES = {
    "abstract": "abstract",
    "introduction": "introduction",
    "related work": "related_work",
    "background": "background",
    "preliminaries": "background",
    "method": "method",
    "methods": "method",
    "methodology": "method",
    "approach": "method",
    "model": "method",
    "proposed method": "method",
    "experiments": "experiments",
    "experiment": "experiments",
    "experimental setup": "experiments",
    "evaluation": "experiments",
    "results": "results",
    "analysis": "results",
    "discussion": "discussion",
    "limitations": "limitations",
    "conclusion": "conclusion",
    "conclusions": "conclusion",
    "appendix": "appendix",
    "references": "references",
    "bibliography": "references",
}

SECTION_RE = re.compile(
    r"^(?:(?:\d+|[ivxlcdm]+)(?:\.\d+)*\.?\s+)?"
    r"(?P<title>[A-Z][A-Za-z /\-&]{2,80})\.?$"
)
NOISE_PATTERNS = [
    re.compile(r"^\d+$"),
    re.compile(r"^page\s+\d+(\s+of\s+\d+)?$", re.IGNORECASE),
    re.compile(r"^arxiv:\d{4}\.\d{4,5}", re.IGNORECASE),
    re.compile(r"^preprint\.?\s*$", re.IGNORECASE),
    re.compile(r"^published as a conference paper", re.IGNORECASE),
    re.compile(r"^proceedings of", re.IGNORECASE),
    re.compile(r"^\s*©"),
]


@dataclass(frozen=True)
class TextCleaner:
    """Clean parsed pages and attach coarse paper sections."""

    name: str = "rule_based_v1"

    def clean(self, parsed: ParsedPaper) -> list[CleanedParagraph]:
        paragraphs: list[CleanedParagraph] = []
        current_section = "unknown"

        for page in parsed.pages:
            buffer: list[str] = []
            for raw_line in _iter_normalized_lines(page.text):
                section = detect_section(raw_line)
                if section is not None:
                    _flush(paragraphs, page.page, current_section, buffer)
                    buffer = []
                    current_section = section
                    continue

                if current_section == "references":
                    continue
                if is_noise_line(raw_line):
                    continue

                buffer.append(raw_line)

            _flush(paragraphs, page.page, current_section, buffer)

        return paragraphs


def detect_section(line: str) -> str | None:
    """Return a normalized section name if a line looks like a heading."""

    stripped = line.strip().strip(":")
    lowered = re.sub(r"\s+", " ", stripped.lower())
    lowered = re.sub(r"^(?:\d+|[ivxlcdm]+)(?:\.\d+)*\.?\s+", "", lowered)
    if lowered in SECTION_ALIASES:
        return SECTION_ALIASES[lowered]

    match = SECTION_RE.match(stripped)
    if not match:
        return None

    title = re.sub(r"\s+", " ", match.group("title").lower()).strip()
    return SECTION_ALIASES.get(title)


def is_noise_line(line: str) -> bool:
    """Return true for low-value page furniture or publication metadata."""

    normalized = line.strip()
    if len(normalized) <= 1:
        return True
    if any(pattern.search(normalized) for pattern in NOISE_PATTERNS):
        return True
    if _looks_like_reference_item(normalized):
        return True
    return False


def _iter_normalized_lines(text: str) -> Iterable[str]:
    text = text.replace("-\n", "")
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if line:
            yield line


def _flush(
    paragraphs: list[CleanedParagraph],
    page: int,
    section: str,
    buffer: list[str],
) -> None:
    if not buffer:
        return

    text = re.sub(r"\s+", " ", " ".join(buffer)).strip()
    if len(text) < 20:
        return

    paragraphs.append(CleanedParagraph(page=page, section=section, text=text))


def _looks_like_reference_item(line: str) -> bool:
    return bool(
        re.match(r"^\[\d+\]\s+", line)
        or re.match(r"^\d+\.\s+[A-Z][A-Za-z-]+,\s", line)
        or re.search(r"\bdoi:\s*10\.", line, re.IGNORECASE)
    )
