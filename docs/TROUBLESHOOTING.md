# Troubleshooting

## Server not starting

Symptoms:

- no `sage-lsp` process attached in Jupyter logs,
- completion requests from this server never arrive.

Checks:

- run the command from the config directly:

```bash
/home/dzack/gitclones/sage-lsp-server/bin/sage-lsp --stdio
```

- confirm `~/.jupyter/jupyter_server_config.d/sage-lsp.json` is valid JSON and points
  to an executable path.

## Sage completions missing

- confirm kernel metadata is Sage (`language: "sage"`).
- confirm notebook MIME includes `text/x-sage` (or at least `text/x-python`
  fallback remains in config).
- confirm `jupyter-lsp` command points at `bin/sage-lsp`.
- check `~/.local/share/jupyter/lsp/lsp.log` (or your server log) for startup
  trace indicating `pylsp` launch.

## Why full Sage highlighting is still limited

This server does not import Sage internals for symbol tables; it currently provides
completion keywords only. That keeps startup reliable but leaves edge cases:

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
