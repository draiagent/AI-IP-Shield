# Step 5.8 - PDF Adapter

## Goal

Extend the proven JPG/PNG protection pipeline to PDF documents while preserving the Step 4 traceability gates.

The V0.1 PDF strategy is **visual-raster protection**:

```text
PDF
  -> render each page
  -> embed the same authenticated Fingerprint token on every page
  -> rebuild PDF at original page geometry
  -> register the protected PDF hash
  -> optional provenance signing
```

This design intentionally prioritizes screenshot / conversion traceability over preservation of native PDF text structure.

## Added

### PDF Adapter

`aipshield/adapters/pdf.py`

- deterministic page rendering with PyMuPDF
- original page-size preservation
- PNG/JPEG page packaging
- Print-to-PDF / raster re-export attack helper
- single-page PDF extraction helper
- encrypted-PDF fail-closed behavior

### Protect PDF

`aipshield/pdf_protect.py`

Each protected PDF receives one document Fingerprint. The same compact watermark token is embedded on every page, allowing a screenshot or extracted page to resolve back to the source PDF copy.

Registry metadata now records:

- asset type
- page count
- render DPI
- provenance backend/status

### Verify PDF

`aipshield/pdf_verify.py`

Verification renders each page and performs page-level extraction. It reports:

- page count
- pages detected
- page detection rate
- consensus watermark token
- fingerprint / registry match
- exact PDF hash match
- provenance status
- mixed-source detection

If different valid watermark tokens appear on different pages, the PDF is reported as `CONFLICTING_EVIDENCE` instead of being attributed to one source copy.

## PDF-specific engine

A bug was found immediately: the image-tuned dual-SVD profile could self-check on a rendered PDF page but lose the token after normal PDF JPEG packaging or another Print-to-PDF cycle.

The image production engine was not modified because that would invalidate the Step 5.6.3 benchmark. Instead a PDF-specific profile was added:

```text
blind-native-pdf
 -> blind-watermark-native-pdf-adaptive
```

The PDF profile prefers a single-singular-value 36/0 embedding profile and retains stronger fallbacks for difficult pages. The base `blind-native` decoder can also recognize these PDF profiles, so a protected PDF page screenshot can still be verified as a normal image.

## CLI routing fix

Another bug was found: the generic CLI originally defaulted to `blind-native`, which meant a PDF supplied to the CLI could bypass the PDF-tuned engine.

The generic `protect` and `verify` commands now default to `--engine auto`:

- image -> `blind-native`
- PDF -> `blind-native-pdf`

Explicit engine selection still overrides auto-routing.

## Formal PDF gate

The one-shot 20-document benchmark exceeded the execution time limit, so the gate was converted to four resumable 5-document batches and then aggregated. No thresholds were lowered.

Formal corpus:

- 20 PDFs
- 5 pages per PDF
- 100 protected pages
- five content categories: text-heavy, image-heavy, table, slide, low-texture
- 20 unprotected PDF-page negative controls

### Results

| Gate | Result |
|---|---:|
| Exact protected PDF | 100% |
| All protected pages readable | 100% |
| PDF -> image trace | 100% |
| PDF-page screenshot trace | 100% |
| Print / raster re-export PDF | 100% |
| Single-page PDF extraction | 100% |
| Page geometry preserved | 100% |
| Negative PDF-page FPR | 0% |
| Mixed-source assembly detected | 100% |

Decision: **`GO_STEP5.8`**

## Performance

With the V0.1 balanced default of 120 DPI / JPEG quality 90:

- mean protection time for a 5-page PDF: about 1.25 seconds in this test environment
- mean source size in the synthetic corpus: about 0.11 MB
- mean protected size: about 0.71 MB
- aggregate output/source size ratio: about 6.5x

Synthetic text PDFs are unusually small before protection, so per-file percentage growth is not a useful production-size predictor.

## Known V0.1 limitation

The protected PDF is rasterized. Therefore V0.1 does **not** preserve:

- selectable/searchable text
- accessibility tags
- forms
- hyperlinks
- all annotations
- original vector structure

This is a deliberate V0.1 tradeoff. A future structure-preserving PDF mode must be tested separately because keeping an extractable text layer changes the piracy threat model.

## Security semantics

A PDF conversion that removes provenance metadata may still retain the visual watermark. Therefore:

```text
C2PA / sidecar missing != fake
Watermark present + registry match = source association
Exact hash + trusted provenance + watermark = strongest evidence
```

Passing Step 5.8 does not mean the PDF cannot be copied or altered. It means the defined visual conversion attacks retained enough signal to trace the tested copies.
