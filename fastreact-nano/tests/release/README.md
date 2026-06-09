# Release LLM Gate

Release-only real LLM checks are executed through:

```bash
python3 run_tests.py release-llm
```

This directory documents the release layer and intentionally has no default
pytest-collected tests. The gate reads `~/api_key.txt` at runtime and writes
only non-sensitive timing output.
