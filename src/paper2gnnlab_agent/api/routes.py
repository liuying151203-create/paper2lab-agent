"""MVP API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from paper2gnnlab_agent import __version__
from paper2gnnlab_agent.api.dependencies import get_app_settings, get_paper_service
from paper2gnnlab_agent.core.config import Settings
from paper2gnnlab_agent.models.paper import PaperDetailResponse, PaperUploadResponse
from paper2gnnlab_agent.services.papers import (
    InvalidPaperUploadError,
    PaperIngestionService,
    PaperNotFoundError,
)

router = APIRouter(prefix="/api/v1")
SettingsDep = Annotated[Settings, Depends(get_app_settings)]
PaperServiceDep = Annotated[PaperIngestionService, Depends(get_paper_service)]
PdfUpload = Annotated[UploadFile, File()]


@router.get("/health", tags=["health"])
def health(settings: SettingsDep) -> dict[str, str]:
    return {
        "status": "ok",
        "service": "paper2gnnlab-agent",
        "env": settings.env,
        "version": __version__,
    }


@router.post(
    "/papers",
    response_model=PaperUploadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["papers"],
)
async def upload_paper(
    file: PdfUpload,
    service: PaperServiceDep,
) -> PaperUploadResponse:
    content = await file.read()
    try:
        return service.upload_pdf(filename=file.filename or "paper.pdf", content=content)
    except InvalidPaperUploadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/papers/{paper_id}", response_model=PaperDetailResponse, tags=["papers"])
def get_paper(
    paper_id: str,
    service: PaperServiceDep,
) -> PaperDetailResponse:
    try:
        return service.get_paper_detail(paper_id)
    except PaperNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found.",
        ) from exc
