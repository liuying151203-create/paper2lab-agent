from paper2gnnlab_agent.models.parsed import ParsedPage, ParsedPaper
from paper2gnnlab_agent.parsers.cleaning import TextCleaner, detect_section, is_noise_line


def test_detect_section_normalizes_common_gnn_paper_headings() -> None:
    assert detect_section("1 Introduction") == "introduction"
    assert detect_section("3 Proposed Method") == "method"
    assert detect_section("4 Experimental Setup") == "experiments"
    assert detect_section("References") == "references"


def test_noise_detection_filters_page_furniture_and_reference_items() -> None:
    assert is_noise_line("12")
    assert is_noise_line("Page 3 of 14")
    assert is_noise_line("[12] Kipf and Welling. Semi-supervised classification.")
    assert not is_noise_line("We evaluate the proposed GNN on citation networks.")


def test_cleaner_attaches_sections_and_drops_references() -> None:
    parsed = ParsedPaper(
        paper_id="paper_test",
        parser="fake",
        parsed_at="2026-06-12T00:00:00+08:00",
        pages=[
            ParsedPage(
                page=1,
                text=(
                    "1 Introduction\n"
                    "We study graph neural networks for node classification.\n"
                    "Page 1\n"
                    "2 Method\n"
                    "Our message passing module aggregates neighbor features.\n"
                    "References\n"
                    "[1] A noisy reference item.\n"
                ),
            )
        ],
    )

    paragraphs = TextCleaner().clean(parsed)

    assert [paragraph.section for paragraph in paragraphs] == ["introduction", "method"]
    assert "node classification" in paragraphs[0].text
    assert "message passing" in paragraphs[1].text
    assert all("reference" not in paragraph.text.lower() for paragraph in paragraphs)
