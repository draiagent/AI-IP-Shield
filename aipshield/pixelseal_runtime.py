from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from pathlib import Path
import importlib
import os
import sys
from typing import Any


OFFICIAL_PIXELSEAL_CHECKPOINT_URL = "https://dl.fbaipublicfiles.com/videoseal/pixelseal/checkpoint.pth"
OFFICIAL_PIXELSEAL_CARD = "pixelseal"


def file_sha256(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    h = sha256()
    with Path(path).open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _module_version(name: str) -> str | None:
    try:
        mod = importlib.import_module(name)
    except Exception:
        return None
    return getattr(mod, "__version__", None) or "installed"


def add_videoseal_source(source_dir: str | Path | None) -> Path | None:
    """Add a local facebookresearch/videoseal checkout to sys.path.

    Accepts either the repository root or the package directory itself.
    Returns the normalized repository root when found.
    """
    if not source_dir:
        return None
    source = Path(source_dir).expanduser().resolve()
    candidates = [source, source.parent]
    for root in candidates:
        if (root / "videoseal" / "__init__.py").is_file():
            s = str(root)
            if s not in sys.path:
                sys.path.insert(0, s)
            return root
    raise FileNotFoundError(
        f"VideoSeal source directory does not contain videoseal/__init__.py: {source}"
    )


@dataclass
class PixelSealRuntimeStatus:
    python_version: str
    torch_version: str | None
    torchvision_version: str | None
    cuda_available: bool
    device: str
    videoseal_importable: bool
    videoseal_version: str | None
    source_dir: str | None
    checkpoint_path: str | None
    checkpoint_exists: bool
    checkpoint_size_bytes: int | None
    checkpoint_sha256: str | None
    checkpoint_looks_valid: bool
    model_card: str
    ready: bool
    errors: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def inspect_pixelseal_runtime(
    source_dir: str | Path | None = None,
    checkpoint_path: str | Path | None = None,
    device: str | None = None,
) -> PixelSealRuntimeStatus:
    errors: list[str] = []
    warnings: list[str] = []

    source_dir = source_dir or os.environ.get("AIPSHIELD_PIXELSEAL_SOURCE")
    checkpoint_path = checkpoint_path or os.environ.get("AIPSHIELD_PIXELSEAL_CHECKPOINT")

    normalized_source: Path | None = None
    if source_dir:
        try:
            normalized_source = add_videoseal_source(source_dir)
        except Exception as exc:
            errors.append(f"source: {type(exc).__name__}: {exc}")

    torch_version = _module_version("torch")
    torchvision_version = _module_version("torchvision")
    cuda_available = False
    resolved_device = device or "cpu"
    if torch_version:
        try:
            import torch
            cuda_available = bool(torch.cuda.is_available())
            resolved_device = device or ("cuda" if cuda_available else "cpu")
        except Exception as exc:
            errors.append(f"torch: {type(exc).__name__}: {exc}")
    else:
        errors.append("PyTorch is not installed")

    videoseal_importable = False
    videoseal_version = None
    try:
        import videoseal  # type: ignore
        videoseal_importable = True
        videoseal_version = getattr(videoseal, "__version__", None) or "installed"
    except Exception as exc:
        errors.append(f"videoseal: {type(exc).__name__}: {exc}")

    ckpt = Path(checkpoint_path).expanduser().resolve() if checkpoint_path else None
    checkpoint_exists = bool(ckpt and ckpt.is_file())
    checkpoint_size_bytes = ckpt.stat().st_size if checkpoint_exists else None
    checkpoint_sha = file_sha256(ckpt) if checkpoint_exists else None
    checkpoint_looks_valid = bool(checkpoint_exists and checkpoint_size_bytes and checkpoint_size_bytes > 1024 * 1024)
    if ckpt and not checkpoint_exists:
        errors.append(f"checkpoint not found: {ckpt}")
    elif checkpoint_exists and not checkpoint_looks_valid:
        errors.append(
            f"checkpoint is suspiciously small ({checkpoint_size_bytes} bytes); possible HTML/LFS pointer instead of model weights"
        )
    elif not ckpt:
        warnings.append(
            "No local PixelSeal checkpoint configured. videoseal.load('pixelseal') will require network access to download the official checkpoint."
        )

    if sys.version_info[:2] != (3, 10):
        warnings.append(
            f"Current Python is {sys.version_info.major}.{sys.version_info.minor}; Meta's README documents Python 3.10 as its reference environment."
        )
    if not cuda_available:
        warnings.append("CUDA is unavailable; PixelSeal inference will run on CPU and may be slow.")

    # Ready means we have the code runtime plus either a local checkpoint or a path to let
    # videoseal download it. For offline execution, a local checkpoint is mandatory.
    ready = bool(torch_version and videoseal_importable and (checkpoint_looks_valid or not ckpt))

    return PixelSealRuntimeStatus(
        python_version=sys.version.split()[0],
        torch_version=torch_version,
        torchvision_version=torchvision_version,
        cuda_available=cuda_available,
        device=resolved_device,
        videoseal_importable=videoseal_importable,
        videoseal_version=videoseal_version,
        source_dir=str(normalized_source) if normalized_source else None,
        checkpoint_path=str(ckpt) if ckpt else None,
        checkpoint_exists=checkpoint_exists,
        checkpoint_size_bytes=checkpoint_size_bytes,
        checkpoint_sha256=checkpoint_sha,
        checkpoint_looks_valid=checkpoint_looks_valid,
        model_card=OFFICIAL_PIXELSEAL_CARD,
        ready=ready,
        errors=errors,
        warnings=warnings,
    )
