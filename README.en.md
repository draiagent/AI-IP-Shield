# AI-IP Shield v0.1.0

[繁體中文](README.md) · [English](README.en.md)

> **Defensive IP authenticity, tracing, provenance, and watermarking for the AI era.**  
> AI-IP Shield combines opaque fingerprints, invisible watermarking, SHA-256 integrity checks, provenance, attack testing, and evidence reporting into an open-source toolkit callable from the CLI, ChatGPT / Codex, and Claude Code.

**Release status: Public Alpha / v0.1.0**

## Why AI-IP Shield?

Visible watermarks, logos, document passwords, and metadata provide limited protection once content is screenshotted, compressed, cropped, converted, OCR'd, AI-edited, or collected at scale. AI-IP Shield does **not** claim to make copying impossible. Its goal is to create measurable, traceable, and verifiable technical evidence.

```text
JPG / PNG / PDF
      ↓
Opaque Fingerprint
      ↓
Robust Invisible Watermark
      ↓
Registry + SHA-256
      ↓
Optional Provenance / Trust
      ↓
Protect → Attack Test → Verify
      ↓
Evidence Report
```

## Core capabilities

| Capability | v0.1.0 | Description |
|---|---|---|
| JPG / PNG invisible protection | ✅ | Opaque fingerprint per asset/copy |
| PDF protection | ✅ | Raster-visual, page-level traceability |
| Fingerprint Registry | ✅ | SQLite mapping for Asset / Copy / Version |
| SHA-256 integrity | ✅ | Exact byte-level modification detection |
| Ed25519 provenance | ✅ | Signed sidecars and local trust store |
| C2PA adapter | 🟡 | Adapter complete; native smoke test is environment-dependent |
| Do Not Train policy | ✅ | Policy assertions for AI use |
| Attack Lab | ✅ | Screenshot, resize, crop, rotate, JPEG, conversion, composites |
| Codex / Claude Code Skill | ✅ | Project- and user-scoped installation |
| ChatGPT Skill ZIP | ✅ | Portable Skill export |
| PixelSeal | 🟡 | Challenger engine pending real checkpoint benchmark |
| Text watermark / anti-distillation | ⏳ | Planned for later releases |

## Installation

### Option A — Install from GitHub source

```bash
git clone https://github.com/draiagent/AI-IP-Shield.git
cd AI-IP-Shield
python -m venv .venv
```

Linux / macOS:

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Validate the installation:

```bash
aipshield version
aipshield doctor
```

### Option B — Install the release wheel

Download:

```text
ai_ip_shield-0.1.0-py3-none-any.whl
```

Then:

```bash
python -m pip install ai_ip_shield-0.1.0-py3-none-any.whl
aipshield doctor
```

## 30-second quick start

### Protect JPG / PNG

```bash
aipshield protect input.png protected.png \
  --registry data/registry.sqlite3
```

### Protect PDF

```bash
aipshield protect input.pdf protected.pdf \
  --registry data/registry.sqlite3
```

The CLI defaults to `--engine auto`, routing images and PDFs to their pinned production-oriented engines.

### Verify source association

```bash
aipshield verify protected.png \
  --registry data/registry.sqlite3 \
  --report-json verify.json \
  --report-md verify.md
```

Typical evidence fields include:

```text
Watermark: DETECTED
Fingerprint: MATCH
Registry: MATCH
Hash: EXACT / MODIFIED
Provenance: VALID / MISSING / INVALID
Evidence: REGISTERED_EXACT_MATCH / STRONG_SOURCE_ASSOCIATION_MODIFIED / ...
```

> **Missing provenance is not evidence of falsity.** A missing C2PA manifest or sidecar may simply mean provenance was removed or never attached.

## Provenance and authenticity

Generate an Ed25519 signing keypair:

```bash
aipshield provenance-keygen \
  --private-key keys/signing.pem \
  --public-key keys/signing.pub.pem
```

Trust a public key locally:

```bash
aipshield provenance-trust keys/signing.pub.pem \
  --trust-store data/trust-store.json \
  --label "My Organization"
```

Protect an asset with provenance and a Do Not Train policy:

```bash
aipshield protect input.png protected.png \
  --registry data/registry.sqlite3 \
  --provenance sidecar \
  --signing-key keys/signing.pem \
  --public-key keys/signing.pub.pem \
  --do-not-train
```

**Never commit private signing keys to GitHub.** See [SECURITY.md](SECURITY.md).

## Attack Lab

AI-IP Shield follows a **Never Trust One Signal** principle. A protected asset should be attacked and re-verified before a robustness claim is made.

```bash
aipshield attack protected.png attacks/ \
  --registry data/registry.sqlite3
```

The current lab covers copy, screenshot simulation, resize, crop, rotation, JPEG compression, format conversion, and composite attacks.

### Validated v0.1 baseline

The pinned image engine previously passed the project's defined **100-image / 500-negative-control** v0.1 release gate. The PDF adapter previously passed a **20-PDF / 100-page** gate. These are reproducible internal engineering benchmarks, not third-party security certifications and not guarantees of 100% success against every real-world attack.

## ChatGPT / Codex / Claude Code Skill

### Codex

```bash
aipshield skill-install --host codex --scope project
```

Location:

```text
.agents/skills/ai-ip-shield/
```

### Claude Code

```bash
aipshield skill-install --host claude --scope project
```

Location:

```text
.claude/skills/ai-ip-shield/
```

### Install both

```bash
aipshield skill-install --host both --scope project
```

### ChatGPT / portable Skill ZIP

```bash
aipshield skill-export \
  --output ai-ip-shield-skill-v0.1.0.zip
```

Use this ZIP where ChatGPT Skills upload is enabled. Availability depends on the current plan and workspace configuration.

## CLI commands

```text
aipshield version
aipshield doctor
aipshield protect
aipshield verify
aipshield attack
aipshield provenance-keygen
aipshield provenance-trust
aipshield provenance-sign
aipshield provenance-verify
aipshield c2pa-status
aipshield skill-install
aipshield skill-export
```

See [references/cli.md](references/cli.md).

## Important PDF v0.1 limitation

PDF protection uses **Raster-Visual Protection**. Pages are rendered, protected visually, and rebuilt into a PDF. v0.1 therefore does not guarantee preservation of:

- selectable/searchable text
- original vector objects
- accessibility tags
- forms
- hyperlinks
- some annotations

This is a deliberate v0.1 tradeoff to prioritize screenshot and conversion traceability.

## What AI-IP Shield does not claim

The project does **not** claim:

- an unremovable watermark
- 100% screenshot/copy/AI-redraw prevention
- technical enforcement of Do Not Train by third-party models
- legal infringement determination from a single watermark
- proof of distillation or training-data theft from one detector/canary alone

The intended use is evidence fusion across **Fingerprint, Watermark, Registry, Hash, Signature, Provenance, and Attack Testing**.

## Release assets

v0.1.0 is prepared with four primary release assets:

```text
AI-IP-Shield-v0.1.0-release.zip
AI-IP-Shield-v0.1.0-source.tar.gz
ai_ip_shield-0.1.0-py3-none-any.whl
ai-ip-shield-skill-v0.1.0.zip
```

`SHA256SUMS.txt` is provided separately for integrity verification.

```bash
sha256sum -c SHA256SUMS.txt
```

## Development and validation

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python scripts/release_check.py
```

## Documentation

- [Quickstart](docs/QUICKSTART.md)
- [Installation](docs/INSTALLATION.md)
- [Agent / Skill integration](docs/AGENT-INTEGRATION.md)
- [GitHub publishing](docs/GITHUB-PUBLISH.md)
- [Step 5.6.3 production engine gate](STEP-5.6.3-PRODUCTION-ENGINE-FINAL-GATE.md)
- [Step 5.7 provenance / C2PA](STEP-5.7-C2PA-PROVENANCE.md)
- [Step 5.8 PDF adapter](STEP-5.8-PDF-ADAPTER.md)
- [Step 5.9 Skill + CLI + Release](STEP-5.9-STATUS.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

## Roadmap

### v0.1.x

- C2PA native runtime smoke test
- broader real screenshot / camera-capture corpus
- packaging and CI hardening

### v0.2

- PPTX adapter
- AI editing / generative-fill attacks
- perspective / camera-photo attacks
- PixelSeal real-checkpoint benchmark

### v0.3

- text watermark / text fingerprint
- knowledge / RAG canaries
- dataset fingerprinting
- probe-based anti-distillation evidence

## License

MIT License. See [LICENSE](LICENSE).

## Contributing and security reports

Contributions through GitHub Issues and Pull Requests are welcome. Review [SECURITY.md](SECURITY.md) before reporting vulnerabilities. Never post private keys, customer identifiers, or sensitive test assets in a public issue.

---

**AI-IP Shield is designed not to promise that content can never be copied, but to make provenance, modification, tracing, and evidence more verifiable.**
