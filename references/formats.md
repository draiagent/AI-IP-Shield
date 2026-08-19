# Format Support

## Supported in V0.1

### JPG / JPEG / PNG

Default engine: `blind-native` via `--engine auto`.

### PDF

Default engine: `blind-native-pdf` via `--engine auto`.

PDF protection is raster-visual:

1. render each page;
2. embed the same document fingerprint on each page;
3. rebuild a protected PDF;
4. verify through per-page consensus.

This improves traceability after screenshot, conversion, Print-to-PDF, and page extraction in the defined test model.

## Not native in V0.1

- PPTX: export a protected visual PDF for V0.1; native PPTX is a later adapter.
- DOCX/XLSX: unsupported.
- Text-only content: no text watermark/dataset-fingerprint implementation yet.
- Audio/video: unsupported.

## PDF limitation

Rasterization does not preserve selectable text, forms, hyperlinks, accessibility tags, or original vector objects.
