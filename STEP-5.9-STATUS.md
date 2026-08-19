# Step 5.9 — Skill + CLI + Release Integration

## Decision

**PASS — `GO_PUBLIC_ALPHA_PACKAGE`**

AI-IP Shield V0.1.0 is packaged as a reproducible Public Alpha source release, Python CLI wheel, and portable Agent Skill. GitHub publication itself is intentionally not performed by this step; this step prepares the repository and release assets for publication.

## Integrated surfaces

### Python CLI

Release commands:

- `aipshield version`
- `aipshield doctor`
- `aipshield protect`
- `aipshield verify`
- `aipshield attack`
- provenance / trust / C2PA status commands
- `aipshield skill-install`
- `aipshield skill-export`

The CLI uses lazy imports for media/provenance-heavy modules, so `version`, `doctor`, and Skill packaging remain diagnosable even in a clean environment before all runtime dependencies are installed.

### OpenAI / Codex Skill

Canonical Skill:

- `SKILL.md`
- `references/*.md`
- `agents/openai.yaml`

Mirrored repo-local Codex Skill:

- `.agents/skills/ai-ip-shield/`

The Python package also embeds the Skill so the installed wheel can deploy it with `aipshield skill-install` or export a portable ZIP with `aipshield skill-export`.

### ChatGPT distribution

The portable ZIP is prepared for upload through ChatGPT's Skills interface on accounts/workspaces where Skills and uploading are enabled. AI-IP Shield does not claim that the local CLI can install directly into the ChatGPT service.

### Claude Code Skill

Mirrored repo-local Skill:

- `.claude/skills/ai-ip-shield/`

Repository-wide invariants are kept in `CLAUDE.md`; task-specific behavior stays in `SKILL.md`.

## Release-safety rules carried forward

- Production image engine remains pinned to `blind-native`.
- Production PDF engine remains pinned to `blind-native-pdf`.
- Release gates are not reduced to hide a regression.
- Missing provenance is not evidence that an asset is fake.
- Do Not Train is a policy signal, not technical prevention of training.
- No absolute anti-copy / anti-removal claim is allowed.
- Opaque identifiers are used in watermark payloads instead of direct PII.
- Private signing keys must not be committed or bundled.

## Step 5.9 validation

- Full automated suite: **34 / 34 PASS**
- Release structure / mirror / secret sanity check: **PASS**
- Main environment `aipshield doctor`: **core_ready = true**
- Clean-wheel lightweight CLI smoke: **PASS**
- Clean-wheel Codex project Skill install: **PASS**
- Clean-wheel Claude Code project Skill install: **PASS**
- Clean-wheel portable Skill export: **PASS**
- Image CLI Protect → Verify smoke: **PASS** (`REGISTERED_EXACT_MATCH`)
- PDF CLI Protect → Verify smoke: **PASS** (`3 / 3` pages detected, `REGISTERED_EXACT_MATCH`)

## Current optional-runtime status

The core V0.1 release does not require the external `blind-watermark` package because the production engines are the pinned native implementations.

Optional/challenger runtimes remain environment-dependent:

- native C2PA runtime: optional / not present in the current sandbox
- PixelSeal / VideoSeal: optional challenger / not present in the current sandbox

Their absence does not invalidate the core V0.1 image/PDF protection release, but AI-IP Shield must not claim their optional capabilities were runtime-tested here.

## Public Alpha boundary

This release means the repository, CLI, Skill packaging, tests, and prior V0.1 image/PDF release gates form a reproducible engineering baseline. It is not third-party security certification, DRM, legal proof, or a guarantee that a determined attacker cannot remove all signals.
