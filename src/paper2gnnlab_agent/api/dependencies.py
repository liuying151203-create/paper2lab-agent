"""FastAPI dependencies for settings, storage paths, repositories, and services."""

from functools import lru_cache

from paper2gnnlab_agent.core.config import Settings, get_settings
from paper2gnnlab_agent.services.papers import PaperIngestionService, build_paper_service
from paper2gnnlab_agent.storage.paper_repository import PaperRepository
from paper2gnnlab_agent.storage.paths import StoragePaths, build_storage_paths


@lru_cache
def get_storage_paths() -> StoragePaths:
    return build_storage_paths(get_settings())


@lru_cache
def get_paper_repository() -> PaperRepository:
    return PaperRepository(get_settings().sqlite_path)


def get_paper_service() -> PaperIngestionService:
    return build_paper_service(repository=get_paper_repository(), paths=get_storage_paths())


def get_app_settings() -> Settings:
    return get_settings()
