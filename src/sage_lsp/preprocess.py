"""SagePython lowering for LSP documents, with incremental reuse.

The compiler (``dzack_research.preamble.sagepython``) is sage-free:
recognition comes from the tree-sitter-sage grammar and the output is
ordinary Python plus a source map translating positions in both
directions.  Documents are re-lowered incrementally across edits by
retaining the previous result per URI.
"""

from __future__ import annotations

from dzack_research.preamble.sagepython import LoweredSource, lower

_CACHE: dict[str, LoweredSource] = {}


def lowered_for(uri: str, source: str) -> LoweredSource:
    """The lowered form of ``source``, reusing the previous parse for ``uri``."""
    previous = _CACHE.get(uri)
    if previous is not None and previous.source_map.original == source:
        return previous
    result = lower(source, previous=previous)
    _CACHE[uri] = result
    return result


def forget(uri: str) -> None:
    _CACHE.pop(uri, None)
