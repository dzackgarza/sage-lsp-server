"""Sage-oriented hooks for python-lsp-server."""

from __future__ import annotations

import keyword
import re
from typing import Final
from urllib.parse import unquote, urlparse

from pylsp import hookimpl, lsp

SAGE_SYMBOLS: Final[tuple[str, ...]] = tuple(
    sorted(
        {
            "Integer",
            "ZZ",
            "QQ",
            "RR",
            "CC",
            "GF",
            "Matrix",
            "vector",
            "MatrixSpace",
            "VectorSpace",
            "PolynomialRing",
            "Polynomial",
            "SR",
            "sage",
            "var",
            "factor",
            "IntegralLattice",
            "ModularForms",
            "DirichletGroup",
            "EllipticCurve",
            "sageall",
            "identity_matrix",
            "QQbar",
        }
    )
)

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

        suggestions.append(
            {
                "label": keyword_name,
                "kind": lsp.CompletionItemKind.Keyword,
                "insertText": keyword_name,
                "documentation": f"Sage keyword: `{keyword_name}`",
                "sortText": f"zz_{keyword_name}",
            }
        )

    return suggestions


@hookimpl
def pylsp_completions(config, workspace, document, position, ignored_names):
    del config, workspace

    prefix = _extract_prefix(document, position)
    if prefix is None or not prefix:
        return None

    if _has_sage_context(document):
        keywords = SAGE_KEYWORDS
    elif _maybe_sage_notebook_context(document, prefix):
        keywords = SAGE_SYMBOLS
    else:
        return None

    ignore = set(ignored_names or [])
    return _completion_items(prefix, keywords, ignore)
