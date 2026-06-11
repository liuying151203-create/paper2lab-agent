"""Streamlit MVP shell for Paper2GNNLab-Agent."""

import streamlit as st

from paper2gnnlab_agent import __version__
from paper2gnnlab_agent.core.config import get_settings


def main() -> None:
    """Render the current Streamlit shell without paper-processing features."""

    settings = get_settings()

    st.set_page_config(page_title="Paper2GNNLab-Agent", page_icon="P2G", layout="wide")
    st.title("Paper2GNNLab-Agent")
    st.caption("GNN paper reading and experiment reproduction planning")

    st.info(
        "MVP shell is ready. Paper upload, parsing, GNN paper cards, and citation QA "
        "will be added in Phase 1."
    )

    st.subheader("Runtime")
    st.json(
        {
            "version": __version__,
            "env": settings.env,
            "api_host": settings.api_host,
            "api_port": settings.api_port,
            "data_dir": str(settings.data_dir),
            "sqlite_path": str(settings.sqlite_path),
        }
    )


if __name__ == "__main__":
    main()
