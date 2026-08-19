from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aipshield.pixelseal_runtime import inspect_pixelseal_runtime, OFFICIAL_PIXELSEAL_CHECKPOINT_URL


def main() -> int:
    p = argparse.ArgumentParser(description="AI-IP Shield PixelSeal runtime preflight")
    p.add_argument("--source", help="Local facebookresearch/videoseal checkout")
    p.add_argument("--checkpoint", help="Local official PixelSeal checkpoint.pth")
    p.add_argument("--device", choices=["cpu", "cuda"])
    p.add_argument("--json-out")
    args = p.parse_args()

    status = inspect_pixelseal_runtime(args.source, args.checkpoint, args.device)
    payload = status.to_dict()
    payload["official_checkpoint_url"] = OFFICIAL_PIXELSEAL_CHECKPOINT_URL
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(text)
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    return 0 if status.ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
