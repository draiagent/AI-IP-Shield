# Contributing

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts/release_check.py
```

## Pull requests

- Keep changes scoped.
- Add or update tests for behavior changes.
- Do not reduce attack-test thresholds to make a regression pass.
- Do not commit private keys, real recipient PII, or proprietary test assets without permission.
- Engine changes must rerun the corresponding Golden Set before robustness claims change.

## Skill changes

Edit the root `SKILL.md`, `references/`, or `agents/openai.yaml`, then run:

```bash
python scripts/sync_skill.py
python scripts/release_check.py
```

The Codex, Claude Code, and bundled Python copies must remain synchronized.
