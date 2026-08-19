# PixelSeal Setup — Step 5.6.2

AI-IP Shield prefers a reproducible local runtime:

```bash
# reference environment: Python 3.10 is preferred for upstream compatibility
python3.10 -m venv .venv-pixelseal
source .venv-pixelseal/bin/activate

# obtain facebookresearch/videoseal source and install its dependencies
# then place the official PixelSeal checkpoint locally

export AIPSHIELD_PIXELSEAL_SOURCE=/absolute/path/to/videoseal
export AIPSHIELD_PIXELSEAL_CHECKPOINT=/absolute/path/to/pixelseal/checkpoint.pth

python scripts/check_pixelseal.py
python scripts/run_step562_pixelseal.py --negative-controls 20
```

## Why local source is supported

The runtime must not assume that a pip package contains every upstream config/model-card file. `AIPSHIELD_PIXELSEAL_SOURCE` allows AI-IP Shield to use a checked-out upstream source tree directly.

## Checkpoint safety

`check_pixelseal.py` records:

- file size
- SHA-256
- runtime versions
- CUDA state
- source location

A tiny `.pth` file is rejected because it is likely a pointer/error page rather than model weights.

## No-surrogate rule

A fake/injected model is allowed only for API contract tests. It is never accepted as a robustness benchmark or production-engine result.
