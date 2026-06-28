# Troubleshooting

## Server not starting

Symptoms:

- no `sage-lsp` process attached in Jupyter logs,
- semantic token requests never arrive.

Checks:

- run the command from the config directly:

```bash
/home/dzack/gitclones/sage-lsp-server/bin/sage-lsp --stdio
```

- confirm `~/.jupyter/jupyter_server_config.d/sage-lsp.json` is valid JSON and points
  to an executable path.

## Sage cells still unhighlighted

- confirm kernel metadata is Sage (`language: "sage"`).
- confirm notebook MIME includes `text/x-sage` (or at least `text/x-python`
  fallback remains in config).
- confirm JupyterLab is not still loading older extension behavior for Sage keyword
  handling.

## Why full Sage symbol resolution is not possible yet

This server does not import Sage internals for symbol tables; it currently uses
regex + keyword heuristics. That keeps startup reliable but leaves edge cases:

- alias/import confusion,
- dynamic symbol creation,
- deep object-typed highlighting.

Use this as a known limitation, and escalate to fuller static parsing only if needed.

## Common command-level checks

```bash
python3 -m pip show sage-lsp
jupyter --paths
python3 scripts/render-config.py --output /tmp/sage-lsp.json
cat /tmp/sage-lsp.json
```

