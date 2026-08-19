# GitHub Publishing Guide

## Repository contents to publish

Publish the full source repository, including:

- `aipshield/`
- `SKILL.md` and `references/`
- `.agents/skills/ai-ip-shield/`
- `.claude/skills/ai-ip-shield/`
- `AGENTS.md` and `CLAUDE.md`
- tests and validation scripts
- documentation, license, security policy, and release notes

Do not publish:

- private signing keys
- real recipient mappings / PII
- private SQLite registries
- secrets or credentials
- generated attack artifacts unless intentionally chosen as public fixtures

## Release assets

Attach:

- `AI-IP-Shield-v0.1.0-release.zip` — source repository release archive
- `AI-IP-Shield-v0.1.0-source.tar.gz` — source archive
- `ai-ip-shield-skill-v0.1.0.zip` — portable Agent Skill
- `ai_ip_shield-0.1.0-py3-none-any.whl` — Python wheel
- `SHA256SUMS.txt` — release checksums

GitHub itself also creates source-code archives for tagged releases; the project archive above is provided so the exact Step 5.9 release gate can be reproduced independently.

## Suggested tag

`v0.1.0`

## Release gate

Before tagging:

```bash
python -m pytest -q
python scripts/release_check.py
aipshield doctor
```

Build:

```bash
python -m pip wheel . --no-deps -w dist
aipshield skill-export --output releases/ai-ip-shield-skill-v0.1.0.zip
```

For an offline sandbox where build isolation cannot retrieve build requirements, use `--no-build-isolation` only when the declared build backend is already present.

## Post-publish smoke test

After GitHub publication, clone into a clean directory, install the wheel/source, run `aipshield doctor`, install the repo-local Skill, protect one JPG/PNG and one PDF, and immediately verify both. Do not consider the public release complete until that clean-clone smoke test passes.
