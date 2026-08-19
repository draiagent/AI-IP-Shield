# AI-IP Shield agent instructions

## Project purpose

AI-IP Shield is a defensive intellectual-property protection system for image/PDF fingerprinting, robust watermarking, provenance, verification, and attack testing.

## Skill

For protection, verification, source tracing, provenance, or robustness tasks, use the repo skill at:

`.agents/skills/ai-ip-shield/SKILL.md`

The release sync test requires the root Skill, Codex Skill, Claude Skill, and bundled Python Skill to stay semantically identical.

## Engineering rules

- Keep the V0.1 production image engine pinned to `blind-native` unless the full Step 5.6.3 gate is rerun.
- Keep the V0.1 PDF engine pinned to `blind-native-pdf` unless the Step 5.8 gate is rerun.
- Do not lower acceptance thresholds to make regressions pass.
- Do not claim a watermark is unremovable or that Do Not Train technically blocks model training.
- Missing provenance is not evidence of a fake asset.
- Never commit private signing keys, trust secrets, or recipient PII.
- Prefer opaque fingerprint IDs and controlled registry mappings.

## Validation

After code changes, run:

```bash
python -m pytest -q
python scripts/release_check.py
```

For packaging changes also run:

```bash
python -m pip wheel . --no-deps -w dist
# Offline fallback only when build backend is already installed:
python -m pip wheel . --no-deps --no-build-isolation -w dist
```
