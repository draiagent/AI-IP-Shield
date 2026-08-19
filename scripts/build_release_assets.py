from __future__ import annotations

import argparse
import hashlib
import shutil
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0"
DIST_NAME = f"AI-IP-Shield-v{VERSION}"
PRIMARY = [
    f"{DIST_NAME}-release.zip",
    f"{DIST_NAME}-source.tar.gz",
    f"ai_ip_shield-{VERSION}-py3-none-any.whl",
    f"ai-ip-shield-skill-v{VERSION}.zip",
]

EXCLUDE_PARTS = {".git", "__pycache__", ".pytest_cache", "dist", "build", "release-assets"}


def iter_release_files():
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDE_PARTS or part.endswith(".egg-info") for part in rel.parts):
            continue
        if path.suffix == ".pyc":
            continue
        yield path, rel


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="release-assets")
    parser.add_argument("--wheel", required=True)
    parser.add_argument("--skill-zip", required=True)
    args = parser.parse_args()

    out = Path(args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    files = list(iter_release_files())

    release_zip = out / PRIMARY[0]
    with zipfile.ZipFile(release_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path, rel in files:
            z.write(path, arcname=str(Path(DIST_NAME) / rel))

    source_tgz = out / PRIMARY[1]
    with tarfile.open(source_tgz, "w:gz") as t:
        for path, rel in files:
            t.add(path, arcname=str(Path(DIST_NAME) / rel), recursive=False)

    wheel_src = Path(args.wheel).resolve()
    wheel_dst = out / PRIMARY[2]
    shutil.copy2(wheel_src, wheel_dst)

    skill_src = Path(args.skill_zip).resolve()
    skill_dst = out / PRIMARY[3]
    shutil.copy2(skill_src, skill_dst)

    checksum = out / "SHA256SUMS.txt"
    checksum.write_text(
        "".join(f"{sha256(out / name)}  {name}\n" for name in PRIMARY),
        encoding="utf-8",
    )
    for name in PRIMARY:
        print(f"{name}: {sha256(out / name)}")
    print(f"SHA256SUMS.txt: {checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
