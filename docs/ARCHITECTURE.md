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
4. The plugin contributes Sage-aware completion suggestions for matching identifiers.

## Completion behavior

Current logic is intentionally conservative:

- detect Sage context by language id (`sage`, `sagews`, `sage3`) and/or file extension
  (`.sage`, `.spyx`, `.sws`, `.sagews`);
- extract token prefix at cursor;
- return completion items from a keyword list when they match the prefix.

## Why not LSP patching in the frontend

Frontend patches are brittle for kernel/language routing edge cases. The server-first
route used here avoids manual monkey patches and keeps behavior visible in standard
LSP surfaces.

## Scope limits

- No AST parse.
- No symbol table or type inference.
- Completion list is curated; this is not a signature engine.
- No diagnostic reporting.
- No semantic token generation.

The immediate objective is practical completion assistance for Sage notebooks while
keeping the path compatible with future extension.
