# Step 5.6.1 — Robust Engine Upgrade

## Goal

Integrate the robust-engine layer without lowering the Step 4 acceptance thresholds.

Target engines:

1. DCT-QIM baseline
2. Blind Watermark family
3. Meta PixelSeal

## Implemented

### 1. Shared authenticated payload

AI-IP Shield no longer sends the raw 64-bit lookup token directly to new engines.
The token is wrapped as:

`MAGIC + VERSION + TOKEN + CRC16`

and then protected by a rate-1/2 convolutional ECC before embedding.

This gives the detector a stronger rule than "some bits were returned": the decoded
payload must also pass structural validation and CRC.

### 2. Blind Watermark adapter fixed

The upstream Blind Watermark API requires the watermark bit length at extraction.
AI-IP Shield now uses a fixed-size authenticated bit payload, so the adapter can supply
the extraction size deterministically.

When the PyPI dependency is unavailable, the project uses a clean-room native
DWT-DCT-SVD compatibility backend. It does not vendor upstream source code.

### 3. Blind native robustness fixes

The first native pass exposed three engineering problems and they were fixed during
Step 5.6.1:

- **Low-texture exact-roundtrip failure** → adaptive strength profiles + post-embed self-check.
- **JPEG/chroma instability** → watermarking moved to the Y/luminance channel.
- **Resize failure** → canonical long-side geometry plus residual-only re-projection.
- **Bit corruption** → convolutional ECC and authenticated payload.

Current engineering result: resize 75/50, JPEG 95/75/60, format conversion and
resize+JPEG recover on the 3-source integration set. Crop, screenshot simulation and
rotation are still blocking weaknesses.

### 4. PixelSeal adapter implemented

`PixelSealAdapter` supports:

- an injected model object for contract tests;
- the official `videoseal.load("pixelseal")` runtime when installed;
- a compatible 256-bit TorchScript model via `AIPSHIELD_PIXELSEAL_MODEL`.

The adapter maps the AI-IP Shield authenticated/ECC payload into a 256-bit message and
converts detector logits back into the registry token.

## Current blocker

The current execution environment does not contain the Meta VideoSeal package or the
PixelSeal checkpoint, and external binary checkpoint installation is unavailable here.
Therefore PixelSeal robustness results are deliberately marked **UNAVAILABLE**, not
simulated.

No production-engine selection is made until the real PixelSeal checkpoint runs the
same Attack Lab.

## Engineering benchmark

See:

- `reports/step5.6.1/ENGINE-COMPARISON.md`
- `reports/step5.6.1/engine-comparison.json`
- `reports/step5.6.1/engine-attack-results.csv`

This is a small integration gate (3 source types + 5 negatives), not the final
100-image + 500-negative-control Release Gate.

## Decision

- **DCT-QIM:** baseline only.
- **Blind native-compatible:** current CPU fallback; improved but not production-ready.
- **PixelSeal:** integration code ready; production decision pending real-model benchmark.

Do not advance to a "robust watermark passed" claim until PixelSeal (or another robust
model) passes the Step 4 crop/screenshot requirements.
