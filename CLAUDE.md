# AI-IP Shield project instructions

Use the project Skill in `.claude/skills/ai-ip-shield/` for asset protection, verification, provenance, source tracing, and Attack Lab work.

Project invariants:

- `blind-native` is the pinned V0.1 image engine.
- `blind-native-pdf` is the pinned V0.1 PDF engine.
- Do not lower release gates to hide regressions.
- Do not claim absolute anti-copy, anti-removal, or anti-training guarantees.
- Missing provenance does not mean fake.
- Never commit private signing keys or raw PII in watermark payloads.

Run `python -m pytest -q` and `python scripts/release_check.py` after changes.
