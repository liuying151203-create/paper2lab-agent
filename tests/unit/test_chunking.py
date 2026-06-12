from paper2gnnlab_agent.models.cleaned import CleanedParagraph
from paper2gnnlab_agent.parsers.chunking import TextChunker


def test_chunker_keeps_stable_ids_and_citations() -> None:
    paragraphs = [
        CleanedParagraph(page=1, section="introduction", text="Intro " * 30),
        CleanedParagraph(page=1, section="introduction", text="More intro " * 30),
        CleanedParagraph(page=2, section="method", text="Message passing module " * 30),
    ]

    chunks = TextChunker(max_chars=600).chunk("paper_abc123", paragraphs)

    assert [chunk.chunk_id for chunk in chunks] == [
        "chunk_abc123_0001",
        "chunk_abc123_0002",
    ]
    assert chunks[0].section == "introduction"
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 1
    assert chunks[0].citation.paper_id == "paper_abc123"
    assert chunks[0].citation.chunk_id == "chunk_abc123_0001"
    assert chunks[1].section == "method"
