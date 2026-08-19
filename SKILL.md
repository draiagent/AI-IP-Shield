---
name: ai-ip-shield
description: Protects and verifies image and PDF intellectual property with invisible fingerprints, source tracing, integrity checks, provenance, attack testing, and evidence reports. Use when a user asks to watermark, fingerprint, protect, trace, verify, authenticate, detect leaked copies, apply Do Not Train policy signals, or evaluate robustness of JPG, PNG, or PDF assets.
---

# AI-IP Shield

Use the installed `aipshield` CLI for deterministic protection and verification. Do not recreate watermark algorithms ad hoc.

## Scope

V0.1 supports:

- JPG / JPEG / PNG images
- PDF documents in raster-visual protection mode
- opaque per-copy fingerprints and SQLite registry records
- SHA-256 exact-file integrity
- Ed25519 sidecar provenance and local trust stores
- optional C2PA when the native runtime is available
- deterministic T01-T05 attack testing

V0.1 does **not** provide native PPTX protection, structure-preserving PDF protection, guaranteed watermark survival, or anti-distillation detection.

## Core rule

Never claim "unremovable", "100% anti-copy", "100% anti-training", or legal proof of infringement. Report technical evidence and limitations.

## Start every task

1. Identify the asset type and requested outcome: protect, verify, provenance, trace, or attack-test.
2. Run `aipshield doctor` if environment readiness is unknown.
3. Use `--engine auto` unless a benchmark explicitly requires another engine.
4. Keep private signing keys outside the repository and never print key material.
5. After protection, immediately verify the output before reporting success.

## Protect an image or PDF

Run:

```bash
aipshield protect INPUT OUTPUT --registry data/registry.sqlite3 --engine auto
```

For PDF, `auto` routes to the pinned PDF engine. For image, it routes to the pinned image engine.

If provenance is required, prefer local sidecar signing unless C2PA readiness has been confirmed:

```bash
aipshield protect INPUT OUTPUT \
  --registry data/registry.sqlite3 \
  --provenance sidecar \
  --signing-key PRIVATE.pem \
  --public-key PUBLIC.pem \
  --do-not-train
```

Then verify the output. See [references/cli.md](references/cli.md) for full commands.

## Verify an unknown or leaked asset

Run:

```bash
aipshield verify INPUT \
  --registry data/registry.sqlite3 \
  --provenance auto \
  --trust-store trust-store.json \
  --report-json report.json \
  --report-md report.md
```

Interpret signals independently before fusion:

- exact hash match proves byte-for-byte integrity only
- recovered watermark/fingerprint supports source association
- trusted cryptographic provenance supports signer/authenticity claims
- missing provenance is **not** evidence that an asset is fake
- conflicting valid page fingerprints in a PDF mean `CONFLICTING_EVIDENCE`

See [references/evidence.md](references/evidence.md).

## Add provenance

Generate a keypair only when the user wants local signing and no suitable key exists:

```bash
aipshield provenance-keygen \
  --private-key signing.pem \
  --public-key signing.pub.pem
```

Add a public key to a local trust store:

```bash
aipshield provenance-trust signing.pub.pem \
  --trust-store trust-store.json \
  --label publisher
```

Never overwrite an existing private key unless the user explicitly requests rotation. Do not commit private keys.

For C2PA, first run:

```bash
aipshield c2pa-status
```

If unavailable, report the limitation and use sidecar provenance when appropriate. A Do Not Train assertion expresses policy; it does not technically prevent model training.

## Attack-test a protected image

Run:

```bash
aipshield attack PROTECTED_IMAGE \
  --registry data/registry.sqlite3 \
  --output-dir reports/attack-artifacts \
  --report-json reports/attack-results.json \
  --report-csv reports/attack-results.csv
```

Do not lower release thresholds to make a test pass. If robustness regresses, report the failed gate and diagnose the engine or geometry issue. See [references/validation.md](references/validation.md).

## PDF rules

PDF V0.1 is raster-visual protection. It prioritizes visual traceability after conversion, screenshot, Print-to-PDF, or page extraction. It does not preserve selectable text, forms, hyperlinks, accessibility tags, or original vectors.

For encrypted/password-protected PDFs, fail closed rather than claiming protection succeeded. See [references/formats.md](references/formats.md).

## Privacy and security

Embed opaque identifiers only. Do not place names, email addresses, phone numbers, government identifiers, or secrets directly into watermark payloads. Store sensitive mappings in the registry or another controlled system.

Read [references/security.md](references/security.md) before handling signing keys or publishing evidence.

## Completion criteria

A protection task is complete only when:

1. the protected asset exists;
2. the registry record exists;
3. immediate verification recovers the expected fingerprint;
4. requested provenance verifies or its runtime limitation is explicitly reported;
5. the final response names the output path, evidence status, and material limitations.
