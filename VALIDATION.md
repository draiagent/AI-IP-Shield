# Validation

## Automated tests

```text
28 passed
```

Coverage includes:

- fingerprint / payload round-trip
- convolutional ECC recovery
- image watermark adapters
- Step 5.6 geometry recovery
- PixelSeal adapter/runtime contracts
- provenance signature / trust behavior
- C2PA trust-state contract
- PDF protect / verify round-trip
- PDF -> image trace
- Print-to-PDF trace
- PDF sidecar provenance
- mixed-source PDF detection
- encrypted PDF fail-closed behavior

## Step 5.8 formal PDF gate

- 20 PDFs
- 5 pages each
- 100 protected pages
- all Step 5.8 trace gates PASS
- 20 PDF-page negative controls, 0 false positives

See `reports/step5.8/PDF-GATE.md` and `reports/step5.8/PDF-GATE.json`.

## Image-engine regression after PDF decoder extension

100 additional unwatermarked images were checked after adding PDF decode profiles:

- false positives: 0
- FPR: 0%

See `reports/step5.8/IMAGE-ENGINE-NEGATIVE-REGRESSION.json`.

## Native C2PA

Still pending because the current runtime does not contain `c2pa-python`. No surrogate C2PA result is counted as a native embedded Content Credential pass.
