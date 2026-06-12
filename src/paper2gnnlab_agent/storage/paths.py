"""Local filesystem path conventions for paper artifacts."""

from dataclasses import dataclass
from pathlib import Path

from paper2gnnlab_agent.core.config import Settings


@dataclass(frozen=True)
class StoragePaths:
    """Resolved local artifact directories used by the MVP workflow."""

    data_dir: Path
    papers_dir: Path
    parsed_dir: Path
    cleaned_dir: Path
    chunks_dir: Path
    cards_dir: Path
    specs_dir: Path
    generated_projects_dir: Path
    sqlite_path: Path


def build_storage_paths(settings: Settings) -> StoragePaths:
    """Build storage paths from runtime settings without creating files."""

    data_dir = settings.data_dir
    return StoragePaths(
        data_dir=data_dir,
        papers_dir=data_dir / "papers",
        parsed_dir=data_dir / "parsed",
        cleaned_dir=data_dir / "cleaned",
        chunks_dir=data_dir / "chunks",
        cards_dir=data_dir / "cards",
        specs_dir=data_dir / "specs",
        generated_projects_dir=data_dir / "generated_projects",
        sqlite_path=settings.sqlite_path,
    )
