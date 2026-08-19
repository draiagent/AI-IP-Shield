# Step 5.8 - PDF Adapter Final Gate

**Decision:** `GO_STEP5.8`

- Documents: **20**
- Pages per document: **5**
- Protected pages: **100**
- Negative PDF page controls: **20**

| Gate | Actual | Threshold | Result |
|---|---:|---:|---|
| Exact protected PDF | 100.0% | 100% | PASS |
| All protected pages readable | 100.0% | >=99% | PASS |
| PDF -> image trace | 100.0% | >=85% | PASS |
| PDF page screenshot trace | 100.0% | >=85% | PASS |
| Print / raster re-export PDF | 100.0% | >=85% | PASS |
| Single-page PDF extraction | 100.0% | >=85% | PASS |
| Page geometry | 100.0% | 100% | PASS |
| Negative PDF page FPR | 0.0% | <1% | PASS |
| Mixed-source PDF detection | 100.0% | 100% | PASS |

## Engineering metrics

- Print-to-PDF mean page detection: **100.0%**
- Mean protect time per 5-page PDF: **1.25s**
- Aggregate protected/source size ratio: **6.5x**
- Mean source PDF size: **0.11 MB**
- Mean protected PDF size: **0.71 MB**
- Searchable text preserved: **0.0%**

## Known V0.1 limitation

V0.1 PDF protection is raster-visual: selectable text, accessibility tags, forms, hyperlinks and some annotations are not preserved.

> Passing this gate means the visual watermark/fingerprint survived the defined PDF conversion tests. It is not DRM, a legal ownership judgment, or a claim that PDF structure is preserved.
