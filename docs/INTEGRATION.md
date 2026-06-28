# Integration Guide

## 1) Install server package

```bash
cd ~/gitclones/sage-lsp-server
python3 -m pip install -e .
```

Expected result:

- console script `sage-lsp` becomes available.

## 2) Render jupyter-lsp config

```bash
python3 scripts/render-config.py --output ~/.jupyter/jupyter_server_config.d/sage-lsp.json
```

This writes a concrete config with absolute command path and keeps the template in
`config/jupyter-lsp-sage.json`.
`sage-lsp` keeps backward compatibility with `--stdio` in generated config.

It launches `python-lsp-server` with the plugin entrypoint installed by this package.

Generated example:

```json
{
  "LanguageServerManager": {
    "language_servers": {
      "sage-lsp": {
        "version": 2,
        "argv": [".../sage-lsp-server/bin/sage-lsp", "--stdio", "--check-parent-process"],
        "languages": ["sage"],
        "mime_types": ["text/x-sage", "text/x-python"],
        "display_name": "Sage (local)",
        "requires_documents_on_disk": false
      }
    },
    "autodetect": false
  }
}
```

## 3) Bind Sage kernel metadata

Ensure Sage notebook documents match the language id/mime route:

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

Keep a backup before editing in local workflows.

## 4) Restart and verify

- restart the Jupyter server process;
- open a Sage notebook;
- verify LSP client status shows `sage-lsp` as active;
- trigger completion for identifiers like `IntegralLattice`.

## 5) Legacy extension policy

`jupyterlab-sage-highlighter` is intentionally retained as a no-op shim once
external LSP is active. Do not reintroduce frontend patches there.
