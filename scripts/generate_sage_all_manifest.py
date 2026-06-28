#!/usr/bin/env python3
"""Generate the Sage symbol metadata manifest consumed by the LSP."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from pathlib import Path


SAGE_DUMP_SCRIPT = r'''
import inspect
import json
from textwrap import dedent

import sage.all as sage_all


def _short_doc(value: object) -> str:
    doc = getattr(value, "__doc__", "")
    if not isinstance(doc, str):
        return ""
    for line in doc.splitlines():
        normalized = line.strip()
        if normalized:
            return normalized[:240]
    return ""


def _signature(value: object, name: str) -> str:
    try:
        sig = str(inspect.signature(value))
    except Exception:
        return ""
    if not sig:
        return ""
    if name.endswith("]") and "(" in sig:
        return f"{name}{sig}"
    return f"{name}{sig}"


symbols = []
for name in sorted(dir(sage_all)):
    if not name.isidentifier() or name.startswith("_"):
        continue

    try:
        value = getattr(sage_all, name)
    except Exception:
        continue

    item = {"name": name}
    doc = _short_doc(value)
    if doc:
        item["help"] = doc

    sig = _signature(value, name)
    if sig and sig != f"{name}()":
        item["signature"] = sig

    symbols.append(item)

print(json.dumps({"symbols": symbols}, sort_keys=True))
'''


def _run_sage_python(command: str) -> dict[str, object]:
    argv = shlex.split(command)
    if not argv:
        raise ValueError("--sage-command is empty")

    args = [*argv, "-c", SAGE_DUMP_SCRIPT]
    completed = subprocess.run(
        args,
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sage-command",
        default="sage -python",
        help="Sage-capable command (default: %(default)s).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("src/sage_lsp/data/sage_all_symbols.json"),
        help="Where to write the manifest.",
    )
    args = parser.parse_args()

    payload = _run_sage_python(args.sage_command)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {len(payload.get('symbols', []))} symbols to {args.output}")


if __name__ == "__main__":
    main()
