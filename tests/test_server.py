"""Unit tests for Sage-context gating in the LSP completion hook."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from sage_lsp.server import (
    SAGE_KEYWORDS,
    SAGE_SYMBOLS,
    _extract_imported_sage_symbols,
    _has_sage_context,
    _load_symbol_manifest,
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


def _labels(result: list[dict[str, Any]] | None) -> list[str]:
    if result is None:
        return []
    return [str(entry["label"]) for entry in result]


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


def test_import_star_expands_all_manifest_symbols_in_scope() -> None:
    doc = Doc(
        "file:///tmp/test.sage",
        "python",
        "from sage.all import *\nAbel",
    )
    imported = _extract_imported_sage_symbols(doc)
    assert imported == set(SAGE_SYMBOLS)


@pytest.fixture
def symbol_manifest_env(tmp_path: Path) -> Iterator[Path]:
    """Point SAGE_LSP_SYMBOL_MANIFEST at a tmp manifest for one test."""
    previous = os.environ.get("SAGE_LSP_SYMBOL_MANIFEST")
    manifest = tmp_path / "sage_all_symbols.json"
    os.environ["SAGE_LSP_SYMBOL_MANIFEST"] = str(manifest)
    yield manifest
    if previous is None:
        os.environ.pop("SAGE_LSP_SYMBOL_MANIFEST", None)
    else:
        os.environ["SAGE_LSP_SYMBOL_MANIFEST"] = previous


def test_custom_manifest_override_is_honored(symbol_manifest_env: Path) -> None:
    symbol_manifest_env.write_text(
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

    info = _load_symbol_manifest()

    assert info["CustomManifestSymbol"]["help"] == "Temporary symbol from test manifest."
    assert info["CustomManifestSymbol"]["signature"] == "CustomManifestSymbol(x)"


def test_invalid_symbol_manifest_path_fails_fast(symbol_manifest_env: Path) -> None:
    with pytest.raises(FileNotFoundError):
        _load_symbol_manifest()


def test_invalid_symbol_manifest_schema_fails_fast(symbol_manifest_env: Path) -> None:
    symbol_manifest_env.write_text(json.dumps({"symbols": {"name": "not-a-list"}}))

    with pytest.raises(TypeError):
        _load_symbol_manifest()


def test_manifest_with_no_readable_symbols_fails_fast(symbol_manifest_env: Path) -> None:
    symbol_manifest_env.write_text(json.dumps({"symbols": [123, None, {"help": "no symbol name"}]}))

    with pytest.raises(ValueError):
        _load_symbol_manifest()
