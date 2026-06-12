"""MVP API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from paper2gnnlab_agent import __version__
from paper2gnnlab_agent.api.dependencies import get_app_settings, get_paper_service
from paper2gnnlab_agent.core.config import Settings
from paper2gnnlab_agent.models.card import (
    GeneratePaperCardRequest,
    PaperCardResponse,
)
from paper2gnnlab_agent.models.chunk import (
    ChunkListResponse,
    GenerateChunksRequest,
    GenerateChunksResponse,
)
from paper2gnnlab_agent.models.cleaned import CleanPaperRequest, CleanPaperResponse
from paper2gnnlab_agent.models.paper import PaperDetailResponse, PaperUploadResponse
from paper2gnnlab_agent.models.parsed import ParsePaperRequest, ParsePaperResponse
from paper2gnnlab_agent.parsers.pdf import PdfParsingError
from paper2gnnlab_agent.services.papers import (
    CardArtifactNotFoundError,
    ChunksArtifactNotFoundError,
    CleanedArtifactNotFoundError,
    InvalidPaperUploadError,
    PaperIngestionService,
    PaperNotFoundError,
    ParsedArtifactNotFoundError,
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


@router.post("/papers/{paper_id}/parse", response_model=ParsePaperResponse, tags=["papers"])
def parse_paper(
    paper_id: str,
    request: ParsePaperRequest,
    service: PaperServiceDep,
) -> ParsePaperResponse:
    try:
        return service.parse_pdf(paper_id=paper_id, force=request.force)
    except PaperNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found.",
        ) from exc
    except PdfParsingError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post("/papers/{paper_id}/clean", response_model=CleanPaperResponse, tags=["papers"])
def clean_paper(
    paper_id: str,
    request: CleanPaperRequest,
    service: PaperServiceDep,
) -> CleanPaperResponse:
    try:
        return service.clean_parsed_text(paper_id=paper_id, force=request.force)
    except PaperNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found.",
        ) from exc
    except ParsedArtifactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Paper must be parsed before cleaning.",
        ) from exc


@router.post("/papers/{paper_id}/chunks", response_model=GenerateChunksResponse, tags=["papers"])
def generate_chunks(
    paper_id: str,
    request: GenerateChunksRequest,
    service: PaperServiceDep,
) -> GenerateChunksResponse:
    try:
        return service.generate_chunks(
            paper_id=paper_id,
            force=request.force,
            max_chars=request.max_chars,
        )
    except PaperNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found.",
        ) from exc
    except CleanedArtifactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Paper must be cleaned before chunking.",
        ) from exc


@router.get("/papers/{paper_id}/chunks", response_model=ChunkListResponse, tags=["papers"])
def list_chunks(
    paper_id: str,
    service: PaperServiceDep,
    section: str | None = None,
    page: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ChunkListResponse:
    try:
        return service.list_chunks(
            paper_id=paper_id,
            section=section,
            page=page,
            limit=limit,
            offset=offset,
        )
    except PaperNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found.",
        ) from exc
    except ChunksArtifactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunks not found.",
        ) from exc


@router.post("/papers/{paper_id}/card", response_model=PaperCardResponse, tags=["papers"])
def generate_paper_card(
    paper_id: str,
    request: GeneratePaperCardRequest,
    service: PaperServiceDep,
) -> PaperCardResponse:
    try:
        return service.generate_paper_card(paper_id=paper_id, force=request.force)
    except PaperNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found.",
        ) from exc
    except ChunksArtifactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Paper must be chunked before card generation.",
        ) from exc


@router.get("/papers/{paper_id}/card", response_model=PaperCardResponse, tags=["papers"])
def get_paper_card(
    paper_id: str,
    service: PaperServiceDep,
) -> PaperCardResponse:
    try:
        return service.get_paper_card(paper_id=paper_id)
    except PaperNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found.",
        ) from exc
    except CardArtifactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not ready.",
        ) from exc
