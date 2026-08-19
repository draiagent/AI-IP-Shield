# Validation and Release Gates

## Image gate baseline

The pinned V0.1 image engine was selected only after a 100-image Golden Set, 500 negative controls, and attack testing for copy, screenshot simulation, resize, crop, rotation, JPEG compression, conversion, and composite attacks.

Do not replace the production engine or lower thresholds without rerunning the same gate.

## PDF gate baseline

The V0.1 PDF adapter was validated on 20 PDFs x 5 pages, including PDF-to-image, screenshot simulation, Print-to-PDF, page extraction, geometry preservation, and negative controls.

## Regression workflow

1. Run focused tests for the changed module.
2. Run the full test suite:

```bash
python -m pytest -q
```

3. For engine changes, rerun Step 5.6.3 release gates.
4. For PDF adapter changes, rerun Step 5.8 PDF gates.
5. Do not publish a robustness improvement based only on a hand-picked example.

## Pending coverage

V0.1 does not claim full coverage for physical camera capture, perspective distortion, high-percentage crop, large rotations, AI editing, AI regeneration, or model distillation.
