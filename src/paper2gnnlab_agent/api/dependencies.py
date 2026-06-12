"""FastAPI dependencies for settings, storage paths, repositories, and services."""

from functools import lru_cache

from paper2gnnlab_agent.core.config import Settings, get_settings
from paper2gnnlab_agent.services.papers import (
    PaperIngestionService,
    build_card_extractor_from_settings,
    build_paper_service,
    build_qa_service_from_settings,
)
from paper2gnnlab_agent.storage.paper_repository import PaperRepository
from paper2gnnlab_agent.storage.paths import StoragePaths, build_storage_paths


@lru_cache
def get_storage_paths() -> StoragePaths:
    return build_storage_paths(get_settings())


@lru_cache
def get_paper_repository() -> PaperRepository:
    return PaperRepository(get_settings().sqlite_path)


def get_paper_service() -> PaperIngestionService:
    settings = get_settings()
    return build_paper_service(
        repository=get_paper_repository(),
        paths=get_storage_paths(),
        card_extractor=build_card_extractor_from_settings(
            model_provider=settings.model_provider,
            model_name=settings.model_name,
            model_base_url=settings.model_base_url,
            api_key=settings.api_key,
        ),
        qa_service=build_qa_service_from_settings(
            model_provider=settings.model_provider,
            model_name=settings.model_name,
            model_base_url=settings.model_base_url,
            api_key=settings.api_key,
        ),
    )


def get_app_settings() -> Settings:
    return get_settings()
