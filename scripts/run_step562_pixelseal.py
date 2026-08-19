from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aipshield.pixelseal_runtime import inspect_pixelseal_runtime
from aipshield.engines.pixelseal_adapter import PixelSealAdapter
from scripts.run_step561_engine_comparison import make_sources, benchmark_engine
from aipshield.attack_lab import default_v01_attack_specs


def main() -> int:
    p = argparse.ArgumentParser(description="Step 5.6.2 real PixelSeal engineering benchmark")
    p.add_argument("--source", help="local facebookresearch/videoseal checkout")
    p.add_argument("--checkpoint", help="local PixelSeal checkpoint.pth")
    p.add_argument("--device", choices=["cpu", "cuda"])
    p.add_argument("--negative-controls", type=int, default=20)
    p.add_argument("--all-five-sources", action="store_true")
    args = p.parse_args()

    outdir = ROOT / "reports" / "step5.6.2"
    outdir.mkdir(parents=True, exist_ok=True)

    if args.source:
        os.environ["AIPSHIELD_PIXELSEAL_SOURCE"] = str(Path(args.source).resolve())
    if args.checkpoint:
        os.environ["AIPSHIELD_PIXELSEAL_CHECKPOINT"] = str(Path(args.checkpoint).resolve())

    status = inspect_pixelseal_runtime(args.source, args.checkpoint, args.device)
    (outdir / "PIXELSEAL-RUNTIME-STATUS.json").write_text(
        json.dumps(status.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if not status.ready:
        (outdir / "PIXELSEAL-BENCHMARK-STATUS.md").write_text(
            "# Step 5.6.2 PixelSeal Benchmark\n\n"
            "**BLOCKED — runtime not ready. No surrogate/fake robustness result was generated.**\n\n"
            + "\n".join(f"- {e}" for e in status.errors)
            + "\n",
            encoding="utf-8",
        )
        print(json.dumps(status.to_dict(), ensure_ascii=False, indent=2))
        return 2

    # Force model construction before the expensive benchmark to fail early and clearly.
    try:
        engine = PixelSealAdapter(
            checkpoint_path=args.checkpoint,
            source_dir=args.source,
            device=args.device,
        )
    except Exception as exc:
        fail = {"runtime": status.to_dict(), "model_load_error": f"{type(exc).__name__}: {exc}"}
        (outdir / "PIXELSEAL-MODEL-LOAD-ERROR.json").write_text(
            json.dumps(fail, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (outdir / "PIXELSEAL-BENCHMARK-STATUS.md").write_text(
            "# Step 5.6.2 PixelSeal Benchmark\n\n"
            "**BLOCKED — the runtime was importable but the real PixelSeal model could not be loaded.**\n\n"
            f"`{type(exc).__name__}: {exc}`\n\n"
            "No surrogate result was used.\n",
            encoding="utf-8",
        )
        print(json.dumps(fail, ensure_ascii=False, indent=2))
        return 3

    del engine
    specs = default_v01_attack_specs()
    real = Path("/mnt/data/0B559232-4B9F-4DD6-BD24-1605B912DE59.jpeg")
    if not real.is_file():
        raise FileNotFoundError(f"benchmark source image missing: {real}")

    with tempfile.TemporaryDirectory(prefix="aips-562-") as td:
        work = Path(td)
        all_sources = make_sources(work / "sources", real)
        sources = all_sources if args.all_five_sources else [all_sources[i] for i in (0, 2, 4)]
        result = benchmark_engine(
            "pixelseal", sources, specs, work, negative_count=args.negative_controls
        )

    serializable = {k: v for k, v in result.items() if k != "rows"}
    payload = {"benchmark": "Step 5.6.2 real PixelSeal engineering gate", "result": serializable}
    (outdir / "pixelseal-benchmark.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    md = [
        "# Step 5.6.2 — Real PixelSeal Engineering Benchmark",
        "",
        f"Backend: `{serializable.get('resolved_engine')}`",
        f"Sources: {serializable.get('source_images')}",
        f"Negative controls: {serializable.get('negative_controls')}",
        f"FPR: {serializable.get('false_positive_rate', 1):.2%}",
        f"Mean PSNR: {serializable.get('mean_psnr', 0):.2f} dB",
        f"Mean SSIM: {serializable.get('mean_ssim', 0):.4f}",
        "",
        "| Attack | Detection | Recovery | BER |",
        "|---|---:|---:|---:|",
    ]
    for spec in specs:
        a = serializable["per_attack"][spec.attack_id]
        md.append(
            f"| {spec.attack_id} | {a['detection_rate']:.0%} | {a['recovery_rate']:.0%} | {a['mean_ber']:.1%} |"
        )
    (outdir / "PIXELSEAL-BENCHMARK-STATUS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
