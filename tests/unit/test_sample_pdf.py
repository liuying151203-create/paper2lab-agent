from pathlib import Path

from paper2gnnlab_agent.parsers.pdf import PypdfParser
from paper2gnnlab_agent.samples import build_minimal_gnn_pdf_bytes


def test_minimal_sample_pdf_is_extractable_by_pypdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "minimal_gnn_paper.pdf"
    pdf_path.write_bytes(build_minimal_gnn_pdf_bytes())

    pages = PypdfParser().parse_pages(pdf_path)

    assert len(pages) == 1
    assert "node classification" in pages[0].text
    assert "Cora" in pages[0].text
    assert "GCN" in pages[0].text
