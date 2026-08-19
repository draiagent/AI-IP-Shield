from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "SKILL.md"
MIRRORS = [
    ROOT / ".agents" / "skills" / "ai-ip-shield" / "SKILL.md",
    ROOT / ".claude" / "skills" / "ai-ip-shield" / "SKILL.md",
    ROOT / "aipshield" / "bundled_skill" / "SKILL.md",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    raise SystemExit(1)


text = CANON.read_text(encoding="utf-8")
if not text.startswith("---\n"):
    fail("SKILL.md missing YAML frontmatter")
front = text.split("---", 2)[1]
name = re.search(r"^name:\s*(.+)$", front, flags=re.M)
desc = re.search(r"^description:\s*(.+)$", front, flags=re.M)
if not name or not re.fullmatch(r"[a-z0-9-]{1,64}", name.group(1).strip()):
    fail("invalid Skill name")
if not desc or not (1 <= len(desc.group(1).strip()) <= 1024):
    fail("invalid Skill description")
if len(text.splitlines()) > 500:
    fail("SKILL.md exceeds 500 lines")

canonical_hash = sha(CANON)
for mirror in MIRRORS:
    if not mirror.exists() or sha(mirror) != canonical_hash:
        fail(f"Skill mirror out of sync: {mirror.relative_to(ROOT)}")

for ref in (ROOT / "references").glob("*.md"):
    for base in [ROOT / ".agents" / "skills" / "ai-ip-shield", ROOT / ".claude" / "skills" / "ai-ip-shield", ROOT / "aipshield" / "bundled_skill"]:
        other = base / "references" / ref.name
        if not other.exists() or sha(other) != sha(ref):
            fail(f"reference mirror out of sync: {ref.name}")

# Secret-pattern sanity checks for release tree. This is intentionally conservative.
private_key_marker = "-----BEGIN " + "PRIVATE KEY-----"
for p in ROOT.rglob("*"):
    if not p.is_file() or ".git" in p.parts or "dist" in p.parts or "releases" in p.parts:
        continue
    if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf", ".sqlite3", ".zip", ".pyc"}:
        continue
    try:
        data = p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        continue
    if private_key_marker in data:
        fail(f"private key material found: {p.relative_to(ROOT)}")

print("PASS: release structure, Skill metadata, mirrors, and secret sanity checks")
