"""Unit tests for Sage-context gating in the LSP completion hook."""

from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
import os
from pathlib import Path
from importlib import import_module

import pytest

from sage_lsp.server import (
    SAGE_KEYWORDS,
    _has_sage_context,
    _maybe_sage_notebook_context,
    pylsp_completions,
    pylsp_hover,
    pylsp_signature_help,
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


def test_hover_shows_sage_doc() -> None:
    doc = Doc("file:///tmp/test.sage", "python", "IntegralLattice(")
    result = pylsp_hover(None, None, doc, {"line": 0, "character": 3})
    assert result is not None
    assert "IntegralLattice" in result["contents"]["value"]


def test_manifest_contains_expanded_sage_symbol_surface() -> None:
    assert len(SAGE_KEYWORDS) > 1800


def test_manifest_symbols_surface_in_completions() -> None:
    doc = Doc("file:///tmp/test.sage", "python", "Abel")
    result = pylsp_completions(None, None, doc, {"line": 0, "character": 4}, [])
    assert "AbelianGroup" in _labels(result)


def test_manifest_symbol_drives_hover_and_signature() -> None:
    doc = Doc("file:///tmp/test.sage", "python", "AbelianGroup(")
    hover = pylsp_hover(None, None, doc, {"line": 0, "character": 12})
    assert hover is not None
    assert "AbelianGroup" in hover["contents"]["value"]

    signature = pylsp_signature_help(None, None, doc, {"line": 0, "character": 12})
    assert signature is not None
    signatures = signature["signatures"]
    assert signatures[0]["label"].startswith("AbelianGroup(")


def test_signature_help_shows_known_sage_signature() -> None:
    doc = Doc("file:///tmp/test.sage", "python", "IntegralLattice(")
    result = pylsp_signature_help(None, None, doc, {"line": 0, "character": 3})
    assert result is not None
    signatures = result["signatures"]
    assert len(signatures) == 1
    assert signatures[0]["label"].startswith("IntegralLattice")


def test_import_statement_expands_manifest_symbols_in_scope(tmp_path: Path) -> None:
    doc = Doc(
        "file:///tmp/test.sage",
        "python",
        "from sage.all import AbelianGroup\nAbel",
    )
    result = pylsp_completions(None, None, doc, {"line": 1, "character": 4}, [])
    assert "AbelianGroup" in _labels(result)


def test_custom_manifest_override_is_honored(tmp_path: Path) -> None:
    manifest = tmp_path / "sage_all_symbols.json"
    manifest.write_text(
        json.dumps(
            {
                "symbols": [
                    {
                        "name": "CustomManifestSymbol",
                        "help": "Temporary symbol from test manifest.",
                        "signature": "CustomManifestSymbol(x)",
                    }
                ]
            }
        )
        + "\n"
    )

    previous = os.environ.get("SAGE_LSP_SYMBOL_MANIFEST")
    os.environ["SAGE_LSP_SYMBOL_MANIFEST"] = str(manifest)
    try:
        custom_server = importlib.reload(import_module("sage_lsp.server"))
        assert "CustomManifestSymbol" in custom_server.SAGE_SYMBOLS

        doc = Doc(
            "file:///tmp/test.sage",
            "python",
            "CustomManifestSymbol(",
        )
        result = custom_server.pylsp_completions(
            None,
            None,
            doc,
            {"line": 0, "character": len("CustomManifestSymbol")},
            [],
        )
        assert "CustomManifestSymbol" in _labels(result)

        signature = custom_server.pylsp_signature_help(
            None,
            None,
            doc,
            {"line": 0, "character": len("CustomManifestSymbol")},
        )
        assert signature is not None
        assert signature["signatures"][0]["label"].startswith("CustomManifestSymbol(")
    finally:
        if previous is None:
            os.environ.pop("SAGE_LSP_SYMBOL_MANIFEST", None)
        else:
            os.environ["SAGE_LSP_SYMBOL_MANIFEST"] = previous
        importlib.reload(import_module("sage_lsp.server"))


def test_invalid_symbol_manifest_path_fails_fast(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist-symbols.json"

    previous = os.environ.get("SAGE_LSP_SYMBOL_MANIFEST")
    os.environ["SAGE_LSP_SYMBOL_MANIFEST"] = str(missing)
    try:
        with pytest.raises(FileNotFoundError, match="Missing Sage symbol manifest"):
            importlib.reload(import_module("sage_lsp.server"))
    finally:
        if previous is None:
            os.environ.pop("SAGE_LSP_SYMBOL_MANIFEST", None)
        else:
            os.environ["SAGE_LSP_SYMBOL_MANIFEST"] = previous
        importlib.reload(import_module("sage_lsp.server"))
