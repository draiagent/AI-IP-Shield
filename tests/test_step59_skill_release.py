from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

from aipshield.doctor import doctor_report
from aipshield.skill_manager import export_skill_zip, install_skill

ROOT = Path(__file__).resolve().parents[1]


def test_skill_frontmatter_and_size():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\n")
    front = text.split("---", 2)[1]
    name = re.search(r"^name:\s*(.+)$", front, re.M).group(1).strip()
    desc = re.search(r"^description:\s*(.+)$", front, re.M).group(1).strip()
    assert re.fullmatch(r"[a-z0-9-]{1,64}", name)
    assert 1 <= len(desc) <= 1024
    assert len(text.splitlines()) < 500


def test_skill_mirrors_are_identical():
    canonical = (ROOT / "SKILL.md").read_bytes()
    for p in [
        ROOT / ".agents/skills/ai-ip-shield/SKILL.md",
        ROOT / ".claude/skills/ai-ip-shield/SKILL.md",
        ROOT / "aipshield/bundled_skill/SKILL.md",
    ]:
        assert p.read_bytes() == canonical


def test_install_skill_codex_and_claude_project(tmp_path):
    results = install_skill("both", "project", str(tmp_path))
    assert len(results) == 2
    assert (tmp_path / ".agents/skills/ai-ip-shield/SKILL.md").is_file()
    assert (tmp_path / ".claude/skills/ai-ip-shield/SKILL.md").is_file()


def test_install_refuses_overwrite_without_force(tmp_path):
    install_skill("codex", "project", str(tmp_path))
    try:
        install_skill("codex", "project", str(tmp_path))
    except FileExistsError:
        pass
    else:
        raise AssertionError("expected FileExistsError")
    install_skill("codex", "project", str(tmp_path), force=True)


def test_export_skill_zip_has_top_level_folder(tmp_path):
    out = tmp_path / "skill.zip"
    export_skill_zip(str(out))
    with zipfile.ZipFile(out) as zf:
        names = set(zf.namelist())
    assert "ai-ip-shield/SKILL.md" in names
    assert "ai-ip-shield/agents/openai.yaml" in names
    assert "ai-ip-shield/references/cli.md" in names


def test_doctor_reports_core_and_pinned_engines():
    report = doctor_report()
    assert report["ai_ip_shield_version"] == "0.1.0"
    assert report["pinned_engines"]["image"] == "blind-native"
    assert report["pinned_engines"]["pdf"] == "blind-native-pdf"
    assert report["core_ready"] is True
