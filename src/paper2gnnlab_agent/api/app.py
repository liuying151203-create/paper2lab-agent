"""FastAPI entrypoint for the Paper2GNNLab-Agent MVP."""

import uvicorn
from fastapi import FastAPI

from paper2gnnlab_agent import __version__
from paper2gnnlab_agent.core.config import get_settings


def create_app() -> FastAPI:
    """Create the FastAPI app with the current minimal MVP routes."""

    settings = get_settings()
    app = FastAPI(
        title="Paper2GNNLab-Agent",
        description="GNN-focused paper reading and experiment reproduction planning API.",
        version=__version__,
    )

    @app.get("/api/v1/health", tags=["health"])
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "paper2gnnlab-agent",
            "env": settings.env,
            "version": __version__,
        }

    return app


app = create_app()


def main() -> None:
    """Run the API with uvicorn for local development."""

    settings = get_settings()
    uvicorn.run(
        "paper2gnnlab_agent.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.env == "development",
    )


if __name__ == "__main__":
    main()
