# Step 5.6 — Attack Lab

## Purpose

Attack the first vertical slice before adding more features. The benchmark measures whether protected assets remain detectable and traceable after common transformations.

## Implemented attacks

- T01 Copy
- T02 Screenshot simulation
- T03 Resize / Crop / Rotate
- T04 JPEG compression
- T05 Format conversion
- Composite Resize + JPEG
- Composite Crop + JPEG

## Metrics

- Detection Rate
- Token / Fingerprint Recovery Rate
- Bit Error Rate (BER)
- False Positive Rate (FPR)
- Verification runtime

## Acceptance thresholds

The thresholds are inherited from the Step 4 specification and are intentionally **not adjusted to fit the current engine**.

| Gate | Target |
|---|---:|
| Copy | 100% |
| Screenshot | ≥90% |
| Resize ≥50% | ≥95% |
| Crop ≤20% | ≥90% |
| JPEG quality ≥60 | ≥90% |
| Same-geometry conversion | ≥85% |
| FPR | <1% |

## Current result

**NO-GO** for V0.1 robustness claims.

See `reports/step5.6-benchmark/ATTACK-LAB-REPORT.md` for measured results.

## Important interpretation

The failure is not treated as a failed project. It identifies the exact limitation of the current baseline: it lacks robust geometric synchronization. This is the purpose of Attack Lab — discover the weakness before shipping claims.
