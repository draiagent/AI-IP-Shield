# Step 5.6.2 Status

## Result

**Engineering integration: PASS**  
**Real PixelSeal robustness benchmark: BLOCKED BY CURRENT SANDBOX**

## Fixed in this step

- `.pth` is no longer misrouted into `torch.jit.load`
- local official checkpoint loading now uses the upstream PixelSeal model card
- local upstream `videoseal` source checkout is supported
- tiny HTML/LFS/Xet pointer-like files are rejected as checkpoints
- runtime diagnostics record Python/PyTorch/CUDA/checkpoint SHA-256
- official-like PixelSeal dict + BCHW detection output is covered by tests

## Verification

- automated tests: **11/11 PASS**
- DCT/Blind regression benchmark: **PASS (script completed)**
- real PixelSeal model: **not available in sandbox**
- fake/surrogate robustness claims: **none**

## Required to finish the production-engine decision

Provide:

1. local `facebookresearch/videoseal` source/runtime
2. official PixelSeal `checkpoint.pth`

Then run:

```bash
python scripts/check_pixelseal.py
python scripts/run_step562_pixelseal.py --negative-controls 20
```
