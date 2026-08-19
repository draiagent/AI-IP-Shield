# CLI Reference

## Contents
- Environment checks
- Protect and verify
- Provenance
- Attack Lab
- Skill installation
- Exit behavior

## Environment checks

```bash
aipshield version
aipshield doctor
```

`doctor` reports core dependencies, optional runtimes, supported formats, and the pinned engines.

## Protect and verify

```bash
aipshield protect input.png protected.png --registry data/registry.sqlite3
aipshield protect input.pdf protected.pdf --registry data/registry.sqlite3

aipshield verify protected.png --registry data/registry.sqlite3
aipshield verify protected.pdf --registry data/registry.sqlite3
```

Useful options:

```text
--engine auto
--version 1
--report PATH
--provenance none|sidecar|c2pa
--do-not-train
--dpi 120
--pdf-image-format jpeg|png
--jpeg-quality 90
```

## Provenance

```bash
aipshield provenance-keygen --private-key signing.pem --public-key signing.pub.pem
aipshield provenance-trust signing.pub.pem --trust-store trust-store.json --label publisher
aipshield provenance-sign asset.png --signing-key signing.pem --public-key signing.pub.pem
aipshield provenance-verify asset.png --backend sidecar --trust-store trust-store.json
aipshield c2pa-status
```

## Attack Lab

```bash
aipshield attack protected.png \
  --registry data/registry.sqlite3 \
  --output-dir reports/attack-artifacts \
  --report-json reports/attack-results.json \
  --report-csv reports/attack-results.csv
```

## Skill installation

Codex repo scope:

```bash
aipshield skill-install --host codex --scope project
```

Claude Code repo scope:

```bash
aipshield skill-install --host claude --scope project
```

Both repo-scoped copies:

```bash
aipshield skill-install --host both --scope project
```

User scope:

```bash
aipshield skill-install --host both --scope user
```

Export a portable Skill ZIP:

```bash
aipshield skill-export --output ai-ip-shield-skill.zip
```

Use `--force` only when intentionally replacing an installed Skill.

## Exit behavior

CLI commands return non-zero when an operation cannot be completed safely. Treat errors as blockers; do not rewrite them as success in an agent response.
