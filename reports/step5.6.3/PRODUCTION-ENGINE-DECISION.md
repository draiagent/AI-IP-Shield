# Step 5.6.3 — Production Engine Final Gate

**Decision:** `GO_V0.1_CPU_PRODUCTION`
**Selected engine:** `blind-native`

Golden images: **100**
Negative controls: **500**
FPR: **0.000%**
Mean PSNR: **38.00 dB**
Mean SSIM: **0.9545**

| Gate | Detection | Min | Recovery | Min | Result |
|---|---:|---:|---:|---:|---|
| ORIGINAL | 100.0% | 100.0% | 100.0% | 99.0% | PASS |
| T01-copy | 100.0% | 100.0% | 100.0% | 100.0% | PASS |
| T02-screenshot | 97.0% | 90.0% | 97.0% | 85.0% | PASS |
| T03-resize-75 | 98.0% | 95.0% | 98.0% | 95.0% | PASS |
| T03-resize-50 | 98.0% | 95.0% | 98.0% | 95.0% | PASS |
| T03-crop-10 | 99.0% | 90.0% | 99.0% | 90.0% | PASS |
| T03-crop-20 | 95.0% | 90.0% | 95.0% | 90.0% | PASS |
| T03-rotate-3 | 97.0% | 85.0% | 97.0% | 85.0% | PASS |
| T04-jpeg-95 | 100.0% | 95.0% | 100.0% | 95.0% | PASS |
| T04-jpeg-75 | 99.0% | 95.0% | 99.0% | 95.0% | PASS |
| T04-jpeg-60 | 98.0% | 90.0% | 98.0% | 90.0% | PASS |
| T05-conversion | 99.0% | 85.0% | 99.0% | 80.0% | PASS |
| TC-resize75-jpeg60 | 96.0% | 70.0% | 96.0% | 70.0% | PASS |
| TC-crop10-jpeg75 | 96.0% | 70.0% | 96.0% | 70.0% | PASS |

False-positive gate: **PASS** (0.000% < 1.0%)
Fingerprint collision gate: **PASS** (100,000 generated)

## PixelSeal status

`BLOCKED_RUNTIME_OR_CHECKPOINT`

- videoseal: ModuleNotFoundError: No module named 'videoseal'

No surrogate PixelSeal result is used.
