## Summary

One or two sentences describing what this PR changes and why.

## Linked issue

Closes #<issue_number>. If there isn't one, describe the problem this solves.

## Type of change

- [ ] Bug fix (fixes an issue, no new behavior)
- [ ] New feature (adds behavior)
- [ ] New example rule (adds to `examples/rules/`)
- [ ] Docs / README / runbook
- [ ] Test-only (adds or restructures tests, no production code change)
- [ ] Refactor (no behavior change)
- [ ] CI / tooling / build
- [ ] Breaking change (API / CLI / config / on-disk format)

## Checklist

- [ ] Tests added or updated (`python -m unittest discover -s tests -v`)
- [ ] `python -m pip install -e .` still works
- [ ] If this changes public API (MCP tools, CLI commands, rule schema):
  updated the README / CHANGELOG
- [ ] Zero runtime dependencies — `[project.dependencies]` is not added to
  `pyproject.toml`
- [ ] `pathlib.Path` used (no `os.path`); logs go to stderr (no `print()` in
  `server.py`, `tools.py`, `jsonrpc.py`, or `schemas.py`)
- [ ] For new example rules: `sekha.rules.load_rules` loads the file without
  errors; rule has narrow pattern; severity matches real risk level

## How tested

- OS: Windows / macOS / Linux
- Python: 3.11 / 3.12 / 3.13
- Commands run / results observed

## Notes for reviewer

Anything non-obvious. Edge cases you considered. Trade-offs made.
