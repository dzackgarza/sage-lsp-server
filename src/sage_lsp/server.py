"""Sage-aware Language Server Protocol implementation."""

from __future__ import annotations

import keyword
import re
from dataclasses import dataclass
from typing import Final, Iterable
from urllib.parse import urlparse, unquote

from lsprotocol import types as lsp_types
from pygls.lsp.server import LanguageServer

SAGE_TOKEN_TYPES: Final[list[str]] = [
    "keyword",
    "class",
    "function",
    "type",
    "variable",
    "parameter",
    "string",
    "number",
    "comment",
]

SAGE_KEYWORDS: Final[set[str]] = {
    # Python base language (for readability in Sage cells)
    *keyword.kwlist,
    # Sage-specific constructors and common symbols used in arithmetic geometry workflows
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
}

SAGE_EXTS: Final[tuple[str, ...]] = (".sage", ".spyx", ".sws", ".sagews")
SAGE_LANG_IDS: Final[tuple[str, ...]] = ("sage", "sagews", "sage3")
IDENT_RE: Final[re.Pattern[str]] = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@dataclass(frozen=True)
class EncodedSemanticToken:
    line: int
    start: int
    length: int
    token_type: int


def _has_sage_mime_or_extension(document: lsp_types.TextDocumentIdentifier, language_id: str | None) -> bool:
    if language_id and language_id.lower() in SAGE_LANG_IDS:
        return True

    uri = (document.uri or "").lower()
    if any(uri.endswith(ext) for ext in SAGE_EXTS):
        return True
    parsed = urlparse(uri)
    path = unquote(parsed.path.lower())
    if any(path.endswith(ext) for ext in SAGE_EXTS):
        return True

    # The notebook virtual-document URI used by JupyterLab contains the parent notebook
    # path. Matching .py here intentionally does not force Sage scope.
    return False


def _classify_identifier(name: str, previous_token: str | None) -> int:
    if name in SAGE_KEYWORDS:
        return 0

    if name == "self":
        return 5

    if previous_token in {"def", "async", "cdef", "class"}:
        return 1 if previous_token == "class" else 2

    if name[0].isupper() and not name.isupper():
        return 1

    if name.isupper() and len(name) > 1:
        return 3

    return 4


def _encode_tokens(tokens: Iterable[EncodedSemanticToken]) -> list[int]:
    data: list[int] = []
    prev_line = 0
    prev_start = 0

    for token in tokens:
        delta_line = token.line - prev_line
        delta_start = token.start if delta_line else token.start - prev_start

        data.extend(
            [
                delta_line,
                delta_start,
                token.length,
                token.token_type,
                0,
            ]
        )

        prev_line = token.line
        prev_start = token.start

    return data


def _tokenize_code(source: str, previous_token_hint: str | None = None) -> list[EncodedSemanticToken]:
    tokens: list[EncodedSemanticToken] = []
    for line_no, line in enumerate(source.splitlines()):
        prev = previous_token_hint or ""
        for match in IDENT_RE.finditer(line):
            name = match.group(0)
            token_type = _classify_identifier(name, prev)
            start = match.start()
            token = EncodedSemanticToken(line_no, start, len(name), token_type)
            tokens.append(token)
            prev = name
        previous_token_hint = prev

    return tokens


server = LanguageServer("sage-lsp", "0.1.0")


@server.feature(
    lsp_types.TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL,
    lsp_types.SemanticTokensLegend(
        token_types=SAGE_TOKEN_TYPES,
        token_modifiers=[],
    ),
)
def semantic_tokens_full(
    server: LanguageServer, params: lsp_types.SemanticTokensParams
) -> lsp_types.SemanticTokens:
    text_document = server.workspace.get_text_document(params.text_document.uri)
    language_id = getattr(text_document, "language_id", None)
    if not _has_sage_mime_or_extension(text_document, language_id):
        return lsp_types.SemanticTokens(data=[])

    source = getattr(text_document, "source", "")
    raw_tokens = _tokenize_code(source)
    return lsp_types.SemanticTokens(data=_encode_tokens(raw_tokens))


def main() -> None:
    server.start_io()


if __name__ == "__main__":
    main()
