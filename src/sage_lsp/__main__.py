"""Entrypoint for launching the Sage-aware `python-lsp-server` process."""

from __future__ import annotations

import os
import sys


def _normalize_argv(argv: list[str]) -> list[str]:
    argv = [arg for arg in argv if arg != "--stdio"]
    if (
        "--check-parent-process" not in argv
        and "--tcp" not in argv
        and "--ws" not in argv
    ):
        argv.append("--check-parent-process")

    return argv


def main(argv: list[str] | None = None) -> None:
    argv = _normalize_argv(sys.argv[1:] if argv is None else argv)
    os.execvp(sys.executable, [sys.executable, "-m", "pylsp", *argv])


if __name__ == "__main__":
    main()
