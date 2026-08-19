# Step 5.6.1 Robust Engine Upgrade — Engineering Comparison

This is a 3-source/5-negative-control engineering integration gate, not the final 100-image/500-negative-control release benchmark.

## dct-qim

Resolved backend: `dct-qim-baseline`
- Mean PSNR: 47.36 dB
- Mean SSIM: 0.9883
- FPR: 0.00%
- Runtime: 1.8s

| Attack | Detection | Recovery | BER |
|---|---:|---:|---:|
| T01-copy | 100% | 100% | 0.0% |
| T02-screenshot | 0% | 0% | 46.2% |
| T03-resize-75 | 0% | 0% | 46.2% |
| T03-resize-50 | 0% | 0% | 47.2% |
| T03-crop-10 | 0% | 0% | 45.8% |
| T03-crop-20 | 0% | 0% | 45.1% |
| T03-rotate-3 | 0% | 0% | 46.5% |
| T04-jpeg-95 | 100% | 100% | 0.0% |
| T04-jpeg-75 | 100% | 100% | 0.0% |
| T04-jpeg-60 | 67% | 67% | 2.1% |
| T05-conversion | 100% | 100% | 0.0% |
| TC-resize75-jpeg60 | 0% | 0% | 45.8% |
| TC-crop10-jpeg75 | 0% | 0% | 45.1% |

## blind

Resolved backend: `blind-watermark-native-adaptive`
- Mean PSNR: 36.54 dB
- Mean SSIM: 0.9124
- FPR: 0.00%
- Runtime: 29.1s

| Attack | Detection | Recovery | BER |
|---|---:|---:|---:|
| T01-copy | 100% | 100% | 0.0% |
| T02-screenshot | 100% | 100% | 0.0% |
| T03-resize-75 | 100% | 100% | 0.0% |
| T03-resize-50 | 100% | 100% | 0.0% |
| T03-crop-10 | 100% | 100% | 0.0% |
| T03-crop-20 | 100% | 100% | 0.0% |
| T03-rotate-3 | 100% | 100% | 0.0% |
| T04-jpeg-95 | 100% | 100% | 0.0% |
| T04-jpeg-75 | 100% | 100% | 0.0% |
| T04-jpeg-60 | 100% | 100% | 0.0% |
| T05-conversion | 100% | 100% | 0.0% |
| TC-resize75-jpeg60 | 67% | 67% | 0.8% |
| TC-crop10-jpeg75 | 100% | 100% | 0.0% |

## pixelseal

**UNAVAILABLE:** `RuntimeError: PixelSeal runtime unavailable. Install facebookresearch/videoseal or point AIPSHIELD_PIXELSEAL_SOURCE at a local checkout.`

## Decision

- DCT-QIM remains a baseline only.
- Blind Watermark native-compatible backend is the current CPU fallback; canonical resizing + convolutional ECC fixed resize and JPEG robustness, but crop/screenshot/rotation remain blocking weaknesses.
- PixelSeal adapter is implemented, but the real Meta model/checkpoint is required before selecting the production engine. No fake/surrogate result is used for robustness claims.

**Production engine selection remains PENDING until PixelSeal is benchmarked on the same Attack Lab.**