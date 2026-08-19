# Model files

Large third-party model weights are intentionally not bundled in this archive.

For PixelSeal, place the official checkpoint somewhere on disk and set:

```bash
export AIPSHIELD_PIXELSEAL_CHECKPOINT=/absolute/path/to/checkpoint.pth
```

The runtime preflight will record the file SHA-256 and reject suspiciously small pointer/error files.
