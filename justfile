test:
	PYTHONPATH=src pytest -q tests

refresh-sage-manifest:
	python3 scripts/generate_sage_all_manifest.py
