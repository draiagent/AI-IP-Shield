from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / ".agents" / "skills" / "ai-ip-shield",
    ROOT / ".claude" / "skills" / "ai-ip-shield",
    ROOT / "aipshield" / "bundled_skill",
]


def sync() -> None:
    for target in TARGETS:
        target.mkdir(parents=True, exist_ok=True)
        (target / "references").mkdir(exist_ok=True)
        (target / "agents").mkdir(exist_ok=True)
        shutil.copy2(ROOT / "SKILL.md", target / "SKILL.md")
        for p in (ROOT / "references").glob("*.md"):
            shutil.copy2(p, target / "references" / p.name)
        shutil.copy2(ROOT / "agents" / "openai.yaml", target / "agents" / "openai.yaml")
    init = ROOT / "aipshield" / "bundled_skill" / "__init__.py"
    if not init.exists():
        init.write_text('"""Bundled AI-IP Shield Agent Skill resources."""\n', encoding="utf-8")


if __name__ == "__main__":
    sync()
    print("Skill copies synchronized")
