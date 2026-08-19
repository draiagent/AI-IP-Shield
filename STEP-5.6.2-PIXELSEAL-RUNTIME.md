# Step 5.6.2 — PixelSeal Runtime Integration

## Goal

Run the **real Meta PixelSeal model** through the same AI-IP Shield Attack Lab used by the baseline engines, without substituting a fake/surrogate model.

## What was implemented

1. `aipshield/pixelseal_runtime.py`
   - runtime preflight
   - local source checkout discovery
   - checkpoint presence/size/SHA-256 inspection
   - Python/PyTorch/CUDA diagnostics
   - Git-LFS/Xet/HTML-pointer guard

2. `PixelSealAdapter` hardening
   - injected-model contract remains supported for unit tests
   - explicit TorchScript path
   - explicit local `.pth` checkpoint path
   - local `facebookresearch/videoseal` source checkout support
   - official model-card architecture + local checkpoint patching
   - official-like `[B,1+K]` and `[B,1+K,H,W]` detector outputs

3. Reproducible commands
   - `python scripts/check_pixelseal.py`
   - `python scripts/run_step562_pixelseal.py`

## Bugs fixed immediately

### Bug 1 — `.pth` could be mistaken for TorchScript

A PixelSeal `.pth` checkpoint is no longer passed to `torch.jit.load`. The adapter now requires `.pth` via `checkpoint_path` / `AIPSHIELD_PIXELSEAL_CHECKPOINT`.

### Bug 2 — local checkpoint lacked architecture-loading path

Inference checkpoints may depend on the model-card architecture. AI-IP Shield now copies the installed/source PixelSeal model card to a temporary YAML and replaces only `checkpoint_path`, then asks the official `videoseal` loader to construct the model.

### Bug 3 — bad downloads could look like checkpoints

Files <= 1 MiB are rejected as suspicious. This catches common cases where an HTML error page or Git-LFS/Xet pointer was saved instead of model weights.

### Bug 4 — pip/runtime packaging is not assumed reliable

AI-IP Shield supports `AIPSHIELD_PIXELSEAL_SOURCE=/path/to/videoseal` so a checked-out upstream repository can be loaded directly, without depending exclusively on a packaged wheel.

## Current sandbox result

The current execution environment has:

- Python 3.13.5
- PyTorch 2.10.0 CPU
- torchvision 0.25.0 CPU
- no CUDA
- no `videoseal` package/source checkout
- no local PixelSeal checkpoint
- outbound runtime download unavailable

Therefore the real PixelSeal Attack Lab is **BLOCKED in this sandbox**.

No robustness number was fabricated or borrowed from a surrogate.

## Runtime environment variables

```bash
export AIPSHIELD_PIXELSEAL_SOURCE=/path/to/facebookresearch/videoseal
export AIPSHIELD_PIXELSEAL_CHECKPOINT=/path/to/pixelseal/checkpoint.pth
```

Then:

```bash
python scripts/check_pixelseal.py \
  --source "$AIPSHIELD_PIXELSEAL_SOURCE" \
  --checkpoint "$AIPSHIELD_PIXELSEAL_CHECKPOINT"

python scripts/run_step562_pixelseal.py \
  --source "$AIPSHIELD_PIXELSEAL_SOURCE" \
  --checkpoint "$AIPSHIELD_PIXELSEAL_CHECKPOINT" \
  --negative-controls 20
```

## Step 5.6.2 Gate

- Adapter/runtime code: **PASS**
- Unit/contract tests: **PASS (11/11)**
- Real PixelSeal checkpoint load: **BLOCKED BY ENVIRONMENT**
- Real PixelSeal Attack Lab: **PENDING**
- Production Engine selection: **PENDING**

The project must not advance to a PixelSeal production claim until the real model passes the same Attack Lab.
