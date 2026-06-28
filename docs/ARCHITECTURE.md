# Architecture

## Runtime model

`jupyter-lsp` invokes this package as a subprocess through:

- `~/.jupyter/jupyter_server_config.d/sage-lsp.json`
- `argv`: `["/home/dzack/gitclones/sage-lsp-server/bin/sage-lsp","--stdio"]`

The flow is:

1. JupyterLab cell edit is proxied through `jupyterlab-lsp` runtime to
   `jupyter-lsp`.
2. `jupyter-lsp` starts the server command from config and establishes LSP stdio.
3. `pygls` receives `textDocument/semanticTokens/full` requests.
4. The server classifies identifiers in the text and returns encoded semantic
   token arrays.

## Tokenization behavior

Current logic is intentionally conservative:

- tokenize using regex: `[A-Za-z_][A-Za-z0-9_]*`
- classify each identifier by simple heuristics:
  - exact match in `SAGE_KEYWORDS` -> token type `keyword`
  - previous token is `class` -> token type `class`
  - previous token is `def`/`async`/`cdef` -> token type `function`
  - `self` -> `parameter`
  - PascalCase -> `class`
  - all-caps -> `type`
  - default -> `variable`
- encode with standard relative-position LSP `SemanticTokens.data`

## Why not LSP patching in the frontend

Frontend patches are brittle for kernel/language routing edge cases. The server-first
route used here avoids manual monkey patches and keeps behavior visible in standard
LSP surfaces.

## Scope limits

- No AST parse.
- No symbol table or type inference.
- No signature docs / completion engine.
- No diagnostic reporting.

The immediate objective is "good enough" keyword and identifier highlighting for
Sage notebooks, while keeping the path compatible with future extension.

