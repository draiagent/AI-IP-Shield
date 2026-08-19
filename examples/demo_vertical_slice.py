from __future__ import annotations
from pathlib import Path
import argparse
from aipshield.protect import protect_image
from aipshield.verify import verify_image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--workdir", default="demo-output")
    args = ap.parse_args()
    wd = Path(args.workdir)
    wd.mkdir(parents=True, exist_ok=True)
    protected = wd / "protected.png"
    registry = wd / "registry.sqlite3"
    protect_report = wd / "protect-report.json"
    verify_report = wd / "verify-report.json"
    verify_md = wd / "verify-report.md"

    p = protect_image(args.input, str(protected), str(registry), report_path=str(protect_report))
    v = verify_image(str(protected), str(registry), report_json=str(verify_report), report_md=str(verify_md))
    print("PROTECT:", p.to_dict())
    print("VERIFY:", v.to_dict())

if __name__ == "__main__":
    main()
