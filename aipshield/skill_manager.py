from __future__ import annotations

import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Iterable

SKILL_NAME = "ai-ip-shield"


@dataclass(frozen=True)
class SkillInstallResult:
    host: str
    scope: str
    destination: str
    installed: bool

    def to_dict(self) -> dict:
        return {
            "host": self.host,
            "scope": self.scope,
            "destination": self.destination,
            "installed": self.installed,
        }


def _bundled_root():
    return resources.files("aipshield.bundled_skill")


def _copy_resource_tree(src, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for child in src.iterdir():
        if child.name == "__pycache__" or child.name == "__init__.py":
            continue
        target = dst / child.name
        if child.is_dir():
            _copy_resource_tree(child, target)
        else:
            target.write_bytes(child.read_bytes())


def _destinations(host: str, scope: str, root: Path | None = None) -> Iterable[tuple[str, Path]]:
    root = (root or Path.cwd()).resolve()
    home = Path.home()
    hosts = [host] if host in {"codex", "claude"} else ["codex", "claude"]
    for item in hosts:
        if item == "codex":
            base = root / ".agents" / "skills" if scope == "project" else home / ".agents" / "skills"
        else:
            base = root / ".claude" / "skills" if scope == "project" else home / ".claude" / "skills"
        yield item, base / SKILL_NAME


def install_skill(host: str, scope: str, root: str | None = None, force: bool = False) -> list[SkillInstallResult]:
    if host not in {"codex", "claude", "both"}:
        raise ValueError("host must be codex, claude, or both")
    if scope not in {"project", "user"}:
        raise ValueError("scope must be project or user")
    root_path = Path(root).expanduser() if root else None
    results: list[SkillInstallResult] = []
    for actual_host, dest in _destinations(host, scope, root_path):
        if dest.exists():
            if not force:
                raise FileExistsError(f"skill already exists: {dest}; use --force to replace it")
            shutil.rmtree(dest)
        _copy_resource_tree(_bundled_root(), dest)
        results.append(SkillInstallResult(actual_host, scope, str(dest), True))
    return results


def export_skill_zip(output: str) -> str:
    out = Path(output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aipshield-skill-") as td:
        root = Path(td) / SKILL_NAME
        _copy_resource_tree(_bundled_root(), root)
        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(root.parent).as_posix())
    return str(out)
