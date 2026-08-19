# Step 5.8 — PDF Adapter Gate

**Decision:** `GO_STEP5.8`

Documents: **5**  
Pages/document: **5**  
Protected pages: **25**

| Gate | Actual | Threshold | Result |
|---|---:|---:|---|
| Exact protected PDF | 100.0% | 100% | PASS |
| PDF → image trace | 100.0% | ≥85% | PASS |
| PDF page screenshot trace | 100.0% | ≥85% | PASS |
| Print / raster re-export PDF | 100.0% | ≥85% | PASS |
| Single-page PDF extraction | 100.0% | ≥85% | PASS |
| Page geometry | 100.0% | 100% | PASS |
| Negative PDF page FPR | 0.0% | <1% | PASS |
| Mixed-source PDF detection | True | True | PASS |

## Engineering metrics

- Print-to-PDF mean page detection: **100.0%**
- Mean protect time/document: **1.23s**
- Mean protected/source size ratio: **92.1×**
- Searchable text preserved: **0.0%**

## V0.1 limitation

V0.1 PDF protection is raster-visual: selectable text, accessibility tags, forms, hyperlinks and some annotations are not preserved.

> The PDF gate validates visual-trace robustness. It does not claim native-structure preservation or DRM behavior.
