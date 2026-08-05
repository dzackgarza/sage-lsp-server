test:
	PYTHONPATH=src pytest -q tests

refresh-sage-manifest:
	python3 scripts/generate_sage_all_manifest.py

# Gates invoked by the machine-wide ai-review-ci git hooks.  The
# package is installed editable in .venv, so running installations
# track the source tree and a push needs no refresh.
test-commit:
	.venv/bin/python -m pytest -q tests

test-push: test-commit
