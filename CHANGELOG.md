# Changelog

## v0.1.0 — Step 5.6.3

### Added
- formal 100-Golden / 500-negative Production Engine Final Gate
- resumable benchmark chunk runner
- parity-aware crop geometry recovery
- vectorized cyclic phase ranking using encoded MAGIC/VERSION marker
- explicit `blind-native` production engine pin
- real-image regression report

### Changed
- production-facing CLI / protect / verify / Attack Lab defaults now use `blind-native`
- canonical blind-native processing long side set to 480 px after 384 px caused a regression in the exact round-trip BER test
- benchmark/test extras documented in `pyproject.toml`

### Fixed
- screenshot/crop/rotation DWT block synchronization
- 1-pixel crop canvas rounding failure
- phase-search performance bottleneck
- environment-dependent `blind` adapter drift risk
- long benchmark timeout recovery via resumable chunks

### Validation
- 13/13 automated tests pass
- all Step 4 V0.1 gates pass
- FPR 0/500
- fingerprint collisions 0/100,000 generated IDs

## Step 5.7

- Added cryptographic provenance layer using Ed25519 sidecar signatures.
- Added local trust store and trusted/untrusted signer separation.
- Added provenance statuses: VALID_TRUSTED, VALID_UNTRUSTED, MODIFIED, INVALID_SIGNATURE, MISSING.
- Added evidence fusion between watermark, registry, exact hash, and provenance.
- Added `cawg.training-mining` Do Not Train policy support.
- Added optional C2PA signing/Reader adapter based on current c2pa-python API.
- Added C2PA runtime status command.
- Added provenance CLI commands: keygen, trust, sign, verify.
- Added privacy fix: raw per-copy fingerprint is no longer exposed in provenance metadata; only a one-way commitment is stored.
- Added schema migration for Step 5.6 registries.
- Added 9-gate provenance validation and expanded automated tests to 21.


## Step 5.8

### Added
- PyMuPDF PDF adapter and page renderer.
- `protect_pdf()` and `verify_pdf()` pipelines.
- per-page consensus and mixed-source conflict detection.
- PDF registry metadata (`asset_type`, `page_count`, `render_dpi`).
- Print-to-PDF and single-page extraction attack helpers.
- resumable 20-PDF formal gate.
- PDF sidecar-provenance integration.

### Fixed
- PDF CLI routing now uses `--engine auto`, selecting `blind-native-pdf` for PDFs.
- high-white/vector PDF pages no longer rely on the image engine's unstable dual-SVD profile.
- document profile now prefers 36/0 single-SVD embedding with stronger fallbacks.
- mixed PDFs carrying multiple valid tokens no longer collapse to one source attribution.
- encrypted PDFs fail closed instead of producing a partial protected artifact.
- one-shot 20-document gate timeout replaced by resumable batch execution.

### Validation
- 28/28 automated tests pass.
- 20 PDFs x 5 pages = 100 protected pages.
- PDF -> image / screenshot / Print-to-PDF / single-page extraction: 100% trace rate in the formal corpus.
- PDF negative page FPR: 0/20.
- image-engine post-change negative regression: 0/100.

### Known limitation
- V0.1 PDF mode rasterizes pages and does not preserve searchable text, accessibility tags, forms, hyperlinks or original vector structure.

## 0.1.0 - Step 5.9 Release Integration

- Added cross-agent `SKILL.md` with progressive references.
- Added Codex `.agents/skills/ai-ip-shield` and Claude Code `.claude/skills/ai-ip-shield` copies.
- Added `AGENTS.md`, `CLAUDE.md`, and OpenAI `agents/openai.yaml` metadata.
- Added `aipshield version`, `doctor`, `skill-install`, and `skill-export` CLI commands.
- Bundled the Skill inside the Python package for post-install deployment.
- Added public GitHub documentation, CI, release workflow, license, security policy, and contribution guide.
- Added release structure tests and secret sanity checks.
