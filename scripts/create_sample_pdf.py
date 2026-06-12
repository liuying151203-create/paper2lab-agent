"""Create the minimal text-based GNN sample PDF used by smoke tests."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from paper2gnnlab_agent.samples import build_minimal_gnn_pdf_bytes  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".tmp/smoke/minimal_gnn_paper.pdf"),
        help="Output PDF path.",
    )
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(build_minimal_gnn_pdf_bytes())
    print(args.output)


if __name__ == "__main__":
    main()
