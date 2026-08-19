from __future__ import annotations

import importlib.util
import platform
import sys
from pathlib import Path

from . import __version__


def _module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, AttributeError, ValueError):
        return False


def doctor_report() -> dict:
    dependencies = {
        "numpy": _module("numpy"),
        "cv2": _module("cv2"),
        "PIL": _module("PIL"),
        "cryptography": _module("cryptography"),
        "fitz": _module("fitz"),
    }
    optional = {
        "c2pa_python": _module("c2pa"),
        "torch": _module("torch"),
        "videoseal": _module("videoseal"),
        "blind_watermark": _module("blind_watermark"),
    }
    return {
        "ai_ip_shield_version": __version__,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "cwd": str(Path.cwd()),
        "core_dependencies": dependencies,
        "optional_runtimes": optional,
        "pinned_engines": {"image": "blind-native", "pdf": "blind-native-pdf"},
        "supported_assets_v0_1": ["jpg", "jpeg", "png", "pdf"],
        "core_ready": all(dependencies.values()),
    }
