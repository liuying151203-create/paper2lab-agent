from paper2gnnlab_agent.ui.app import main


def test_streamlit_app_entrypoint_is_importable() -> None:
    assert callable(main)
