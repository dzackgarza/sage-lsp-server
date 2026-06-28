#!/usr/bin/env python3
"""Render jupyter-lsp config with the local command path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "config" / "jupyter-lsp-sage.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path.home() / ".jupyter" / "jupyter_server_config.d" / "sage-lsp.json",
        help="Destination jupyter-lsp config file.",
    )
    args = parser.parse_args()

    data = json.loads(TEMPLATE.read_text())
    server = data["LanguageServerManager"]["language_servers"]["sage-lsp"]
    server["argv"][0] = str(ROOT / "bin" / "sage-lsp")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2) + "\n")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
