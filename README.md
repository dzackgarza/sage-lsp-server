# Sage LSP Server

This repository contains a standalone Sage-aware Language Server Protocol (LSP)
server used for JupyterLab syntax intelligence.

The server is intentionally narrow in scope in this first implementation:
it provides `textDocument/semanticTokens/full` support and a Sage-aware keyword
classification layer so Sage-heavy identifiers can be highlighted in notebook cells.

## Why this repo exists

Earlier attempts to make Sage cells look correct in JupyterLab focused on
overriding JupyterLab codemirror adapters inside a UI extension. That path is
fragile and ends up fighting the frontend integration points.

This repo moves the work to the correct layer:

- keep frontend extensions lean,
- keep keyword/identifier inference in an LSP server,
- keep JupyterLab-to-LSP wiring explicit in one config file.

The previous `jupyterlab-sage-highlighter` extension was reduced to a no-op shim
after the external LSP wiring is in place.

## Repository layout

- `src/sage_lsp/server.py` — LSP implementation and tokenization logic.
- `bin/sage-lsp` — tiny bootstrap entrypoint used by `jupyter-lsp`.
- `scripts/render-config.py` — helper to render JSON config with an absolute
  local `bin/sage-lsp` path.
- `config/jupyter-lsp-sage.json` — templated `jupyter-lsp` config.
- `pyproject.toml` — install metadata and console script.

## Install and register

1. Install editable:

```bash
python3 -m pip install -e .
```

2. Render and install jupyter-lsp config:

```bash
python3 scripts/render-config.py --output ~/.jupyter/jupyter_server_config.d/sage-lsp.json
```

That config points at `bin/sage-lsp --stdio` and registers language id `sage`.

3. Restart JupyterLab and check `Log`/LSP diagnostics for `sage-lsp`.

## Optional kernel metadata alignment

For deterministic attachment of this server to Sage notebooks, the kernel should
identify as Sage language text with MIME type `text/x-sage`.

```bash
python3 - <<'PY'
import json
from pathlib import Path

path = Path.home()/'.local/share/jupyter/kernels/sagemath/kernel.json'
data = json.loads(path.read_text())
data['language'] = 'sage'
data['metadata']['language_info']['name'] = 'sage'
data['metadata']['language_info']['mimetype'] = 'text/x-sage'
path.write_text(json.dumps(data, indent=2) + "\n")
print(path)
PY
```

If you edit this file, restart the notebook server and re-open any active tabs.

## What the server currently does

- Detects Sage documents by:
  - language id (`sage`, `sagews`, `sage3`), and
  - file extension fallback (`.sage`, `.spyx`, `.sws`, `.sagews`).
- Splits source text with a lightweight identifier tokenizer.
- Classifies tokens into a `semanticTokens` legend:
  - keyword-like Sage words
  - function/class-like identifiers
  - constructor-like names
- Returns minimal token modifiers (no style flags yet), letting JupyterLab apply
  theme colors.

## Notes on accuracy and scope

- This server is a practical stopgap for identifier highlighting, not a full
  Sage static-analysis engine.
- It is reliable for keyword/class/function name coloring and common Sage symbols
  like `IntegralLattice`, but it does not replace complete parsing or symbol
  binding.
- JupyterLab themes determine final rendering color; this server only emits semantic
  token types.

## Verification checklist

1. Confirm `jupyter-lsp` uses this config file:
   `~/.jupyter/jupyter_server_config.d/sage-lsp.json`
2. Confirm kernel metadata contains:
   `language: "sage"` and `metadata.language_info.mimetype: "text/x-sage"`.
3. Open a Sage cell containing `IntegralLattice` and check token coloring is
   present from semantic tokens rather than generic code text.

## Companion extension note

The prior frontend extension approach (`jupyterlab-sage-highlighter`) is now a
compatibility shim:

- it loads and no-ops at activation;
- it does not patch LSP internals anymore;
- syntax intelligence should come from `sage-lsp` via `jupyter-lsp`.

## Files to read next

- `docs/ARCHITECTURE.md` for data flow and tokenization assumptions.
- `docs/INTEGRATION.md` for command-by-command setup.
- `docs/TROUBLESHOOTING.md` for common failures and what to inspect.
