"""Sage-oriented hooks for python-lsp-server."""

from __future__ import annotations

import json
import keyword
import os
import re
from pathlib import Path
from importlib.resources import files as resources_files
from typing import Final
from urllib.parse import unquote, urlparse

from pylsp import hookimpl, lsp

SAGE_MANIFEST_FILE: Final[Path] = Path(
    resources_files("sage_lsp").joinpath("data", "sage_all_symbols.json")
)


def _load_symbol_manifest() -> dict[str, dict[str, str]]:
    env_path = os.environ.get("SAGE_LSP_SYMBOL_MANIFEST")
    manifest_path = Path(env_path) if env_path else SAGE_MANIFEST_FILE
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing Sage symbol manifest at {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_symbols = payload.get("symbols")
    if not isinstance(raw_symbols, list):
        raise TypeError(f"Invalid manifest schema in {manifest_path}: expected symbols list")

    info: dict[str, dict[str, str]] = {}
    for item in raw_symbols:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name:
            continue

        details: dict[str, str] = {}
        help_text = item.get("help")
        signature_text = item.get("signature")
        if isinstance(help_text, str):
            details["help"] = help_text.strip()
        if isinstance(signature_text, str):
            details["signature"] = signature_text.strip()
        info[name] = details

    if not info:
        raise ValueError(f"Manifest at {manifest_path} contains no readable symbols")
    return info


SAGE_SYMBOL_INFO: Final[dict[str, dict[str, str]]] = _load_symbol_manifest()
SAGE_SYMBOLS: Final[tuple[str, ...]] = tuple(sorted(SAGE_SYMBOL_INFO))

SAGE_KEYWORDS: Final[tuple[str, ...]] = tuple(
    sorted(set(keyword.kwlist) | set(SAGE_SYMBOLS))
)

SAGE_HINT_RE: Final[re.Pattern[str]] = re.compile(
    r"""(?x)
    (?:^|[^\w.])(from\s+sageall\s+import|from\s+sage\.all\s+import|import\s+sage|import\s+sageall)\b
    """,
    re.IGNORECASE,
)

SAGE_EXTS: Final[tuple[str, ...]] = (".sage", ".spyx", ".sws", ".sagews")
SAGE_LANG_IDS: Final[tuple[str, ...]] = ("sage", "sagews", "sage3")
IDENT_RE: Final[re.Pattern[str]] = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
SAGE_IMPORT_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*from\s+(?:sage\.all|sageall)\s+import\s+(.+)$",
    re.IGNORECASE,
)


def _has_sage_context(document: object) -> bool:
    language_id = getattr(document, "language_id", None)
    if language_id and str(language_id).lower() in SAGE_LANG_IDS:
        return True

    uri = str(getattr(document, "uri", ""))
    uri_lower = uri.lower()
    if any(uri_lower.endswith(ext) for ext in SAGE_EXTS):
        return True

    parsed = urlparse(uri)
    path = unquote((parsed.path or "").lower())
    if any(path.endswith(ext) for ext in SAGE_EXTS):
        return True

    if path.endswith(".ipynb"):
        source = getattr(document, "source", "")
        if isinstance(source, str) and SAGE_HINT_RE.search(source):
            return True

    return False


def _is_sage_symbol_context(document: object, prefix: str) -> bool:
    if _has_sage_context(document):
        return True
    return _maybe_sage_notebook_context(document, prefix)


def _extract_imported_sage_symbols(document: object) -> set[str]:
    source = getattr(document, "source", "")
    if not isinstance(source, str) or not source.strip():
        return set()

    symbols = set()
    for line in source.splitlines():
        match = SAGE_IMPORT_RE.match(line)
        if not match:
            continue

        imported = match.group(1)
        if imported.strip() == "*":
            return set(SAGE_SYMBOLS)

        for item in imported.split(","):
            name = item.strip()
            if not name or name == "*":
                continue
            if " as " in name:
                name = name.split(" as ", 1)[0].strip()
            symbols.add(name)

    return symbols


def _word_at_position(document: object, position: dict[str, int] | None) -> str | None:
    if position is None:
        return None

    line_index = position.get("line")
    char_index = position.get("character")
    if not isinstance(line_index, int) or not isinstance(char_index, int):
        return None

    source = getattr(document, "source", "")
    if not isinstance(source, str):
        return None

    lines = source.splitlines()
    if line_index < 0 or line_index >= len(lines):
        return None

    line = lines[line_index]
    if char_index < 0:
        return None
    if char_index > len(line):
        char_index = len(line)

    for match in IDENT_RE.finditer(line):
        if match.start() <= char_index <= match.end():
            return match.group(0)

    return None


def _maybe_sage_notebook_context(document: object, prefix: str) -> bool:
    language_id = str(getattr(document, "language_id", "")).lower()
    if language_id not in ("", "python"):
        return False

    uri = str(getattr(document, "uri", ""))
    uri_lower = uri.lower()
    parsed = urlparse(uri)
    path = unquote((parsed.path or "").lower())
    is_ipynb = uri_lower.endswith(".ipynb") or path.endswith(".ipynb")
    if not is_ipynb:
        return False

    source = getattr(document, "source", "")
    if isinstance(source, str):
        if SAGE_HINT_RE.search(source):
            return True

        return any(symbol.startswith(prefix) for symbol in SAGE_SYMBOLS)

    return False


def _extract_prefix(document: object, position: dict[str, int] | None) -> str | None:
    if position is None:
        return None

    line_index = position.get("line")
    char_index = position.get("character")
    if not isinstance(line_index, int) or not isinstance(char_index, int):
        return None

    source = getattr(document, "source", "")
    if not isinstance(source, str):
        return None

    lines = source.splitlines()
    if line_index < 0 or line_index >= len(lines):
        return None

    line = lines[line_index]
    if char_index < 0:
        return None

    before_cursor = line[:char_index]
    match = None
    for found in IDENT_RE.finditer(before_cursor):
        match = found

    if match is None:
        return ""

    return match.group(0)


def _completion_items(
    prefix: str,
    keywords: tuple[str, ...],
    ignore: set[str] | None = None,
) -> list[dict[str, object]]:
    ignore = ignore or set()
    suggestions = []
    for keyword_name in keywords:
        if prefix and not keyword_name.startswith(prefix):
            continue
        if keyword_name in ignore:
            continue

        metadata = SAGE_SYMBOL_INFO.get(keyword_name, {})
        details = metadata.get("help", f"Sage keyword: `{keyword_name}`")
        suggestions.append(
            {
                "label": keyword_name,
                "kind": lsp.CompletionItemKind.Keyword,
                "insertText": keyword_name,
                "documentation": {
                    "kind": "markdown",
                    "value": details,
                },
                "sortText": f"zz_{keyword_name}",
            }
        )

    return suggestions


@hookimpl
def pylsp_settings():
    # This server owns linting end to end: Sage documents lint on their
    # lowered Python with mapped positions (sage_lsp.lint), plain Python
    # documents lint directly through the same hook.  The stock lint
    # plugins would re-lint raw Sage source and re-introduce the noise.
    return {
        "plugins": {
            "pyflakes": {"enabled": False},
            "pycodestyle": {"enabled": False},
            "mccabe": {"enabled": False},
            "autopep8": {"enabled": False},
            "yapf": {"enabled": False},
        }
    }


@hookimpl
def pylsp_lint(config, workspace, document, is_saved):
    from sage_lsp.lint import lint_document

    return lint_document(document)


@hookimpl
def pylsp_completions(config, workspace, document, position, ignored_names):
    del config, workspace

    prefix = _extract_prefix(document, position)
    if prefix is None or not prefix:
        return None

    if _is_sage_symbol_context(document, prefix):
        keywords = SAGE_KEYWORDS
    elif _maybe_sage_notebook_context(document, prefix):
        keywords = SAGE_SYMBOLS
    else:
        return None

    ignore = set(ignored_names or [])
    keywords = tuple(sorted(set(keywords).union(_extract_imported_sage_symbols(document))))
    return _completion_items(prefix, keywords, ignore)


@hookimpl
def pylsp_hover(config, workspace, document, position):
    del config, workspace

    symbol = _word_at_position(document, position)
    if symbol is None:
        return None

    if not _is_sage_symbol_context(document, symbol):
        return None

    metadata = SAGE_SYMBOL_INFO.get(symbol)
    if not metadata:
        return None

    details = metadata.get("help", f"Sage symbol `{symbol}`.")
    signature = metadata.get("signature")
    if signature:
        contents = f"```python\n{signature}\n```\n\n{details}"
    else:
        contents = details

    return {"contents": {"kind": "markdown", "value": contents}}


@hookimpl
def pylsp_signature_help(config, workspace, document, position):
    del config, workspace

    symbol = _word_at_position(document, position)
    if symbol is None:
        return None

    if not _is_sage_symbol_context(document, symbol):
        return None

    metadata = SAGE_SYMBOL_INFO.get(symbol)
    if not metadata:
        return None

    signature = metadata.get("signature")
    if not signature:
        return None

    return {
        "signatures": [
            {
                "label": signature,
                "documentation": {
                    "kind": "markdown",
                    "value": metadata.get("help", f"Sage symbol `{symbol}`."),
                },
                "parameters": [],
            }
        ],
        "activeSignature": 0,
    }
