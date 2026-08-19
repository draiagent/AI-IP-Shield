# AI-IP Shield Step 5.6 Attack Lab Benchmark

**Decision: NO-GO**

- Engine: `dct-qim-baseline`
- Protected source images: 20
- Attack cases: 260
- Negative controls: 500
- False positive rate: 0.00%
- Runtime: 17.9s

## Attack Results

| Attack | Detection | Recovery | Mean BER | Gate |
|---|---:|---:|---:|---:|
| T01-copy | 100% | 100% | 0.0% | PASS |
| T02-screenshot | 0% | 0% | 51.8% | FAIL |
| T03-resize-75 | 0% | 0% | 52.3% | FAIL |
| T03-resize-50 | 0% | 0% | 52.9% | FAIL |
| T03-crop-10 | 0% | 0% | 52.3% | FAIL |
| T03-crop-20 | 0% | 0% | 52.4% | FAIL |
| T03-rotate-3 | 0% | 0% | 52.3% | — |
| T04-jpeg-95 | 100% | 100% | 0.0% | PASS |
| T04-jpeg-75 | 100% | 100% | 0.0% | PASS |
| T04-jpeg-60 | 80% | 80% | 5.4% | FAIL |
| T05-conversion | 100% | 100% | 0.0% | PASS |
| TC-resize75-jpeg60 | 0% | 0% | 52.3% | — |
| TC-crop10-jpeg75 | 0% | 0% | 51.9% | — |

## Release Gate

| Gate | Target | Actual | Result |
|---|---:|---:|---|
| T01-copy | 100% | 100.0% | PASS |
| T02-screenshot | 90% | 0.0% | FAIL |
| T03-resize-75 | 95% | 0.0% | FAIL |
| T03-resize-50 | 95% | 0.0% | FAIL |
| T03-crop-10 | 90% | 0.0% | FAIL |
| T03-crop-20 | 90% | 0.0% | FAIL |
| T04-jpeg-95 | 90% | 100.0% | PASS |
| T04-jpeg-75 | 90% | 100.0% | PASS |
| T04-jpeg-60 | 90% | 80.0% | FAIL |
| T05-conversion | 85% | 100.0% | PASS |
| False Positive Rate | < 0.01 | 0.0% | PASS |

## Interpretation

- The baseline survives exact copies and high-quality JPEG/conversion paths better than geometric transforms.
- Resize, crop, rotation and simulated screenshot break block synchronization because the current DCT-QIM extractor assumes the same 8×8 block geometry as the protected image.
- This is a useful failure: Step 5.6 has identified synchronization robustness as the next engineering requirement.
- Do not claim screenshot/crop/resize resistance from this baseline.

## Next Action

Keep the current engine as CPU baseline only. Add a robust engine (PixelSeal/Blind Watermark adapter actually enabled) and/or geometric synchronization layer, then rerun this exact Attack Lab without changing the acceptance targets.

> This is an engineering benchmark, not legal proof or a claim of unbreakable protection.