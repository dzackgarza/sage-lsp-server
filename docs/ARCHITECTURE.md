# Architecture

## Runtime model

`jupyter-lsp` invokes this package as a subprocess through:

- `~/.jupyter/jupyter_server_config.d/sage-lsp.json`
- `argv`: `["/home/dzack/gitclones/sage-lsp-server/bin/sage-lsp","--stdio"]`

The flow is:

1. JupyterLab cell edit is proxied through `jupyterlab-lsp` runtime to
   `jupyter-lsp`.
2. `jupyter-lsp` starts the server command from config and establishes LSP stdio.
3. `sage-lsp` runs `python -m pylsp` and loads this package through the
   `pylsp` plugin entrypoint.
4. The plugin contributes Sage-aware completion suggestions for matching identifiers and
   lightweight Sage symbol docs/signatures for hover/signature help.
5. Symbol metadata is loaded from `src/sage_lsp/data/sage_all_symbols.json`, regenerated
   via `scripts/generate_sage_all_manifest.py`.

## Completion behavior

Current logic is intentionally conservative:

- detect Sage context by language id (`sage`, `sagews`, `sage3`) and/or file extension
- (`.sage`, `.spyx`, `.sws`, `.sagews`),
- extract token prefix at cursor;
- if that is not conclusive, treat Python-marked notebook documents (`.ipynb`) as "possibly Sage"
  only when a Sage import marker is present or the typed prefix matches a Sage symbol.
- return completion items from the Sage symbol list or full keyword list when they match the prefix.

## Why not LSP patching in the frontend

Frontend patches are brittle for kernel/language routing edge cases. The server-first
route used here avoids manual monkey patches and keeps behavior visible in standard
LSP surfaces.

## Scope limits

- No AST parse.
- No symbol table or type inference.
- Completion list is derived from the generated `sage.all` export manifest (still a static hint engine,
  not full Sage inference).
- No diagnostic reporting.
- No semantic token generation.

The immediate objective is practical completion assistance for Sage notebooks while
keeping the path compatible with future extension.
