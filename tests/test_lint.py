"""Behavioral proofs for source-mapped linting on lowered SagePython.

The headline claim (research#296): Sage preparser syntax never produces
false diagnostics, real findings land at their positions in the Sage
source, and Sage globals are never "undefined name" noise.
"""

from __future__ import annotations

from dataclasses import dataclass

from sage_lsp.lint import lint_document
from sage_lsp.preprocess import lowered_for


@dataclass
class Doc:
    uri: str
    language_id: str | None = None
    source: str = ""


def _sage(source: str, uri: str = "file:///cell.sage") -> Doc:
    return Doc(uri, "sage", source)


def test_generator_assignment_produces_no_diagnostics() -> None:
    document = _sage("R.<x0, x1, y0, y1> = PolynomialRing(QQ)\n")

    assert lint_document(document) == []


def test_issue_296_construct_list_is_quiet() -> None:
    document = _sage(
        "R.<x> = QQ[]\n"
        "w = ZZ[pi]\n"
        "b = 123 ^^ 123\n"
        "q = 1/2\n"
        "m = matrix(QQ, [[1, 2], [3, 4]])\n"
    )

    assert lint_document(document) == []


def test_generated_semicolons_never_surface_as_style_findings() -> None:
    document = _sage("R.<x, y> = PolynomialRing(QQ)\n")

    codes = [diagnostic["code"] for diagnostic in lint_document(document)]
    assert "E702" not in codes and codes == []


def test_real_undefined_name_maps_to_its_sage_position() -> None:
    document = _sage("R.<x> = QQ[]\nvalue = undefined_thing\n")

    diagnostics = lint_document(document)
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert "undefined_thing" in diagnostic["message"]
    assert diagnostic["range"]["start"] == {"line": 1, "character": 8}


def test_real_style_finding_in_authored_text_maps_exactly() -> None:
    document = _sage("R.<x> = QQ[]\ny=x\n")

    diagnostics = lint_document(document)
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic["code"] == "E225"
    assert diagnostic["range"]["start"] == {"line": 1, "character": 1}


def test_sage_globals_are_not_undefined_names() -> None:
    document = _sage("value = pi + euler_gamma\nring = PolynomialRing(QQ, 'x')\n")

    assert lint_document(document) == []


def test_plain_python_documents_lint_unlowered() -> None:
    document = Doc("file:///plain.py", "python", "value = missing_name\n")

    diagnostics = lint_document(document)
    assert len(diagnostics) == 1
    assert "missing_name" in diagnostics[0]["message"]
    assert diagnostics[0]["range"]["start"] == {"line": 0, "character": 8}


def test_sage_syntax_error_maps_to_the_broken_line() -> None:
    document = _sage("R.<x> = QQ[]\ndef broken(:\n    pass\n")

    diagnostics = lint_document(document)
    errors = [d for d in diagnostics if d["severity"] == 1]
    assert len(errors) == 1
    assert errors[0]["range"]["start"]["line"] == 1


def test_incremental_cache_reuses_and_refreshes() -> None:
    uri = "file:///incr.sage"
    first = lowered_for(uri, "a = 2^3\n")
    again = lowered_for(uri, "a = 2^3\n")
    assert again is first

    edited = lowered_for(uri, "a = 2^3 + 1\n")
    assert edited is not first
    assert edited.python == "a = Integer(2)**Integer(3) + Integer(1)\n"
