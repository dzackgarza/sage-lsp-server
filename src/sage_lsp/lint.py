"""Diagnostics on lowered SagePython, mapped back to author positions.

This is the preprocessing layer of issue research#296: Sage documents
are compiled to ordinary Python before pyflakes and pycodestyle run, so
``R.<x, y> = PolynomialRing(QQ)`` never produces a syntax error, and
every real finding lands at its position in the Sage source via the
compiler's source map.  Sage globals from the symbol manifest count as
builtins, so ``QQ`` or ``pi`` are never "undefined name" noise.  Style
findings inside compiler-generated text (for example the semicolons in
a lowered generator assignment) describe the compiler's output, not the
author's input, and are dropped.

Plain-Python documents lint directly, unlowered.
"""

from __future__ import annotations

import ast
from typing import Any

import pycodestyle
from pyflakes import checker as pyflakes_checker

import sagepython
import sagepython.research

from sage_lsp.preprocess import lowered_for
from sage_lsp.server import SAGE_SYMBOLS, _has_sage_context

_BUILTINS: tuple[str, ...] = (
    SAGE_SYMBOLS + sagepython.RUNTIME_NAMES + sagepython.research.RUNTIME_NAMES
)

_SOURCE = "sage-lsp"
_ERROR = 1
_WARNING = 2

Diagnostic = dict[str, Any]


def _diagnostic(
    line: int,
    character: int,
    end_character: int,
    message: str,
    code: str,
    severity: int,
) -> Diagnostic:
    return {
        "source": _SOURCE,
        "range": {
            "start": {"line": line, "character": character},
            "end": {"line": line, "character": end_character},
        },
        "message": message,
        "code": code,
        "severity": severity,
    }


class _StyleReport(pycodestyle.BaseReport):
    def __init__(self, options: Any) -> None:
        super().__init__(options)
        self.findings: list[tuple[int, int, str, str]] = []

    def error(
        self, line_number: int, offset: int, text: str, check: Any
    ) -> str | None:
        code = super().error(line_number, offset, text, check)
        if code:
            self.findings.append((line_number, offset, code, text[5:]))
        return code


def _pyflakes_findings(
    python: str, builtins: tuple[str, ...]
) -> tuple[list[tuple[int, int, str]], tuple[int, int, str] | None]:
    """(warnings, syntax_error) from pyflakes over ``python``."""
    try:
        tree = ast.parse(python)
    except SyntaxError as error:  # boundary: the parser reports via raise
        return [], (error.lineno or 1, (error.offset or 1) - 1, error.msg or "invalid syntax")
    results = pyflakes_checker.Checker(tree, builtins=builtins)
    findings = []
    for message in results.messages:
        findings.append(
            (message.lineno, message.col, message.message % message.message_args)
        )
    return findings, None


def _pycodestyle_findings(python: str) -> list[tuple[int, int, str, str]]:
    style = pycodestyle.StyleGuide(reporter=_StyleReport)
    checker = pycodestyle.Checker(
        lines=python.splitlines(keepends=True),
        options=style.options,
        report=_StyleReport(style.options),
    )
    checker.check_all()
    return checker.report.findings


def lint_document(document: Any) -> list[Diagnostic]:
    source = document.source
    if not _has_sage_context(document):
        return _lint_plain(source)
    lowered = lowered_for(document.uri, source)
    source_map = lowered.source_map
    diagnostics: list[Diagnostic] = []

    warnings, syntax_error = _pyflakes_findings(lowered.python, _BUILTINS)
    if syntax_error is not None:
        line, column, message = syntax_error
        original = source_map.original_position(line, column)
        diagnostics.append(
            _diagnostic(
                original[0] - 1,
                original[1],
                original[1] + 1,
                message,
                "syntax",
                _ERROR,
            )
        )
    for line, column, message in warnings:
        original = source_map.original_position(line, column)
        diagnostics.append(
            _diagnostic(
                original[0] - 1,
                original[1],
                original[1] + 1,
                message,
                "pyflakes",
                _WARNING,
            )
        )
    for line, column, code, message in _pycodestyle_findings(lowered.python):
        if not source_map.exact_at_generated(line, column):
            continue  # a finding about compiler-generated text
        original = source_map.original_position(line, column)
        diagnostics.append(
            _diagnostic(
                original[0] - 1,
                original[1],
                original[1] + 1,
                message,
                code,
                _WARNING,
            )
        )
    return diagnostics


def _lint_plain(source: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    warnings, syntax_error = _pyflakes_findings(source, ())
    if syntax_error is not None:
        line, column, message = syntax_error
        diagnostics.append(
            _diagnostic(line - 1, column, column + 1, message, "syntax", _ERROR)
        )
    for line, column, message in warnings:
        diagnostics.append(
            _diagnostic(line - 1, column, column + 1, message, "pyflakes", _WARNING)
        )
    for line, column, code, message in _pycodestyle_findings(source):
        diagnostics.append(
            _diagnostic(line - 1, column, column + 1, message, code, _WARNING)
        )
    return diagnostics
