"""Unit tests for Sage-context gating in the LSP completion hook."""

from __future__ import annotations

from dataclasses import dataclass

from sage_lsp.server import (
    SAGE_KEYWORDS,
    SAGE_SYMBOLS,
    _has_sage_context,
    _maybe_sage_notebook_context,
    pylsp_completions,
)


@dataclass
class Doc:
    uri: str
    language_id: str | None = None
    source: str = ""


def _labels(result: list[dict[str, object]] | None) -> list[str]:
    if result is None:
        return []
    return [entry["label"] for entry in result]


def test_definite_sage_file() -> None:
    doc = Doc("file:///tmp/test.sage", "python", "Int")
    assert _has_sage_context(doc) is True
    result = pylsp_completions(None, None, doc, {"line": 0, "character": 3}, [])
    assert "IntegralLattice" in _labels(result)


def test_plain_python_file_has_no_sage_completions() -> None:
    doc = Doc("file:///tmp/test.py", "python", "Int")
    assert _has_sage_context(doc) is False
    assert _maybe_sage_notebook_context(doc, "Int") is False
    assert _labels(pylsp_completions(None, None, doc, {"line": 0, "character": 3}, [])) == []


def test_python_notebook_uses_sage_symbols_on_match_prefix() -> None:
    doc = Doc("file:///tmp/test.ipynb", "python", "Int")
    assert _maybe_sage_notebook_context(doc, "Int") is True
    result = pylsp_completions(None, None, doc, {"line": 0, "character": 3}, [])
    assert "IntegralLattice" in _labels(result)
    assert "and" not in _labels(result)


def test_python_notebook_marker_triggers_full_coverage() -> None:
    doc = Doc("file:///tmp/test.ipynb", "python", "from sageall import *\nimp")
    assert _maybe_sage_notebook_context(doc, "imp") is True
    result = pylsp_completions(None, None, doc, {"line": 1, "character": 3}, [])
    assert "import" in _labels(result)
