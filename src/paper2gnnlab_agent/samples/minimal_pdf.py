"""Generate a tiny text-based GNN paper PDF without external dependencies."""

from __future__ import annotations

MINIMAL_GNN_PAPER_LINES = [
    "Paper2GNNLab Minimal GNN Paper",
    "Abstract",
    "We propose a graph neural network for node classification on Cora and Citeseer.",
    "The method uses a GCN encoder with message passing and cross-entropy loss.",
    "1 Introduction",
    "Graph neural networks are widely used for semi-supervised node classification.",
    "2 Method",
    "Our model stacks two GCN layers with dropout and ReLU activation.",
    "The training objective is cross-entropy with Adam optimizer.",
    "3 Experiments",
    "We evaluate on Cora and Citeseer using accuracy and F1 metrics.",
    "Baselines include GAT, GraphSAGE, and MLP.",
    "We use a train validation test split, learning rate 0.01, and 200 epochs.",
    "4 Results",
    "The proposed model improves accuracy over the MLP baseline.",
    "5 Limitations",
    "Hardware details and random seeds are not fully specified.",
]


def build_minimal_gnn_pdf_bytes() -> bytes:
    """Return bytes for a one-page PDF with extractable GNN paper text."""

    content_stream = _build_content_stream(MINIMAL_GNN_PAPER_LINES)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        (
            b"<< /Length "
            + str(len(content_stream)).encode("ascii")
            + b" >>\nstream\n"
            + content_stream
            + b"\nendstream"
        ),
    ]
    return _assemble_pdf(objects)


def _build_content_stream(lines: list[str]) -> bytes:
    commands = ["BT", "/F1 11 Tf", "72 750 Td", "14 TL"]
    for index, line in enumerate(lines):
        if index == 0:
            commands.append(f"({_escape_pdf_text(line)}) Tj")
        else:
            commands.append(f"T* ({_escape_pdf_text(line)}) Tj")
    commands.append("ET")
    return "\n".join(commands).encode("ascii")


def _assemble_pdf(objects: list[bytes]) -> bytes:
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
