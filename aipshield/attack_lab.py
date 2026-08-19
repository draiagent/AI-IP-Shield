from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable
import csv
import json
import math
import shutil
import time

import cv2
import numpy as np

from .engines import get_engine
from .registry import FingerprintRegistry
from .verify import verify_image


@dataclass(frozen=True)
class AttackSpec:
    attack_id: str
    name: str
    parameters: dict


@dataclass
class AttackResult:
    attack_id: str
    attack_name: str
    parameters: dict
    input_path: str
    output_path: str
    detected: bool
    registry_match: bool
    recovered_token: str | None
    expected_token: str
    token_exact_match: bool
    ber: float | None
    runtime_ms: float
    evidence_level: str

    def to_dict(self):
        return asdict(self)


def _read(path: str | Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"cannot read image: {path}")
    return img


def _write(path: str | Path, img: np.ndarray, jpeg_quality: int | None = None) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    params = []
    if jpeg_quality is not None:
        params = [cv2.IMWRITE_JPEG_QUALITY, int(jpeg_quality)]
    if not cv2.imwrite(str(path), img, params):
        raise IOError(f"failed to write: {path}")
    return str(path)


def apply_attack(input_path: str | Path, output_path: str | Path, spec: AttackSpec) -> str:
    """Apply a deterministic attack transform for reproducible v0.1 benchmarking."""
    src = Path(input_path)
    dst = Path(output_path)
    attack = spec.name
    p = spec.parameters

    if attack == "copy":
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return str(dst)

    img = _read(src)
    h, w = img.shape[:2]

    if attack == "jpeg":
        q = int(p["quality"])
        if dst.suffix.lower() not in {".jpg", ".jpeg"}:
            dst = dst.with_suffix(".jpg")
        return _write(dst, img, jpeg_quality=q)

    if attack == "resize":
        scale = float(p["scale"])
        nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
        out = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
        return _write(dst, out)

    if attack == "crop":
        frac = float(p["fraction"])
        # Remove the requested total fraction from width and height symmetrically.
        dx = round(w * frac / 2)
        dy = round(h * frac / 2)
        out = img[dy:h-dy, dx:w-dx]
        return _write(dst, out)

    if attack == "rotate":
        degrees = float(p["degrees"])
        M = cv2.getRotationMatrix2D((w / 2, h / 2), degrees, 1.0)
        out = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return _write(dst, out)

    if attack == "screenshot-sim":
        # Simulate a common screen capture path: display-resample, centered padding, JPEG recode.
        scale = float(p.get("scale", 0.90))
        q = int(p.get("quality", 85))
        nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
        rendered = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
        canvas = np.full_like(img, 238)
        x0 = (w - nw) // 2
        y0 = (h - nh) // 2
        canvas[y0:y0+nh, x0:x0+nw] = rendered
        if dst.suffix.lower() not in {".jpg", ".jpeg"}:
            dst = dst.with_suffix(".jpg")
        return _write(dst, canvas, jpeg_quality=q)

    if attack == "conversion":
        # PNG -> JPEG memory encode -> PNG, maintaining geometry but changing coefficients.
        q = int(p.get("quality", 90))
        ok, enc = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, q])
        if not ok:
            raise IOError("jpeg conversion encode failed")
        out = cv2.imdecode(enc, cv2.IMREAD_COLOR)
        return _write(dst, out)

    if attack == "composite-resize-jpeg":
        scale = float(p.get("scale", 0.75))
        q = int(p.get("quality", 60))
        nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
        out = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
        if dst.suffix.lower() not in {".jpg", ".jpeg"}:
            dst = dst.with_suffix(".jpg")
        return _write(dst, out, jpeg_quality=q)

    if attack == "composite-crop-jpeg":
        frac = float(p.get("fraction", 0.10))
        q = int(p.get("quality", 75))
        dx = round(w * frac / 2)
        dy = round(h * frac / 2)
        out = img[dy:h-dy, dx:w-dx]
        if dst.suffix.lower() not in {".jpg", ".jpeg"}:
            dst = dst.with_suffix(".jpg")
        return _write(dst, out, jpeg_quality=q)

    raise ValueError(f"unknown attack: {attack}")


def default_v01_attack_specs() -> list[AttackSpec]:
    return [
        AttackSpec("T01-copy", "copy", {}),
        AttackSpec("T02-screenshot", "screenshot-sim", {"scale": 0.90, "quality": 85}),
        AttackSpec("T03-resize-75", "resize", {"scale": 0.75}),
        AttackSpec("T03-resize-50", "resize", {"scale": 0.50}),
        AttackSpec("T03-crop-10", "crop", {"fraction": 0.10}),
        AttackSpec("T03-crop-20", "crop", {"fraction": 0.20}),
        AttackSpec("T03-rotate-3", "rotate", {"degrees": 3.0}),
        AttackSpec("T04-jpeg-95", "jpeg", {"quality": 95}),
        AttackSpec("T04-jpeg-75", "jpeg", {"quality": 75}),
        AttackSpec("T04-jpeg-60", "jpeg", {"quality": 60}),
        AttackSpec("T05-conversion", "conversion", {"quality": 90}),
        AttackSpec("TC-resize75-jpeg60", "composite-resize-jpeg", {"scale": 0.75, "quality": 60}),
        AttackSpec("TC-crop10-jpeg75", "composite-crop-jpeg", {"fraction": 0.10, "quality": 75}),
    ]


def _ber(engine, attacked_path: str | Path, expected_token: str) -> float | None:
    evaluator = getattr(engine, "bit_error_rate", None)
    if evaluator is None:
        return None
    try:
        return float(evaluator(attacked_path, expected_token))
    except Exception:
        return None


def run_attack_case(
    protected_path: str | Path,
    registry_path: str | Path,
    expected_token: str,
    output_dir: str | Path,
    spec: AttackSpec,
    engine_name: str = "blind-native",
) -> AttackResult:
    output_dir = Path(output_dir)
    suffix = ".jpg" if spec.name in {"jpeg", "screenshot-sim", "composite-resize-jpeg", "composite-crop-jpeg"} else ".png"
    output_path = output_dir / f"{spec.attack_id}{suffix}"
    actual_path = apply_attack(protected_path, output_path, spec)

    t0 = time.perf_counter()
    engine = get_engine(engine_name)
    fast_eval = getattr(engine, "evaluate_token", None)
    if fast_eval is not None:
        token, ber = fast_eval(actual_path, expected_token)
        registry = FingerprintRegistry(registry_path)
        row = registry.get_by_token(token) if token else None
        detected = token is not None
        registry_match = row is not None
        evidence_level = "STRONG" if registry_match else ("WEAK" if detected else "NO_EVIDENCE")
    else:
        v = verify_image(str(actual_path), str(registry_path), engine_name=engine_name)
        token = v.watermark_token
        detected = v.detected
        registry_match = v.registry_match
        evidence_level = v.evidence_level
        ber = _ber(engine, actual_path, expected_token)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    return AttackResult(
        attack_id=spec.attack_id,
        attack_name=spec.name,
        parameters=spec.parameters,
        input_path=str(protected_path),
        output_path=str(actual_path),
        detected=detected,
        registry_match=registry_match,
        recovered_token=token,
        expected_token=expected_token,
        token_exact_match=(token == expected_token),
        ber=ber,
        runtime_ms=round(elapsed_ms, 3),
        evidence_level=evidence_level,
    )


def run_attack_suite(
    protected_path: str | Path,
    registry_path: str | Path,
    expected_token: str,
    output_dir: str | Path,
    specs: Iterable[AttackSpec] | None = None,
    engine_name: str = "blind-native",
) -> list[AttackResult]:
    specs = list(specs or default_v01_attack_specs())
    return [
        run_attack_case(protected_path, registry_path, expected_token, output_dir, s, engine_name)
        for s in specs
    ]


def summarize(results: list[AttackResult]) -> dict:
    total = len(results)
    detected = sum(r.detected for r in results)
    recovered = sum(r.token_exact_match for r in results)
    bers = [r.ber for r in results if r.ber is not None and not math.isnan(r.ber)]
    return {
        "cases": total,
        "detected": detected,
        "detection_rate": detected / total if total else 0.0,
        "token_recovered": recovered,
        "recovery_rate": recovered / total if total else 0.0,
        "mean_ber": sum(bers) / len(bers) if bers else None,
    }


def write_results(results: list[AttackResult], out_json: str | Path, out_csv: str | Path | None = None) -> None:
    out_json = Path(out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {"summary": summarize(results), "results": [r.to_dict() for r in results]}
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if out_csv:
        out_csv = Path(out_csv)
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=[
                "attack_id", "attack_name", "parameters", "detected", "registry_match",
                "token_exact_match", "ber", "runtime_ms", "evidence_level", "output_path",
            ])
            w.writeheader()
            for r in results:
                d = r.to_dict()
                d["parameters"] = json.dumps(d["parameters"], ensure_ascii=False, sort_keys=True)
                w.writerow({k: d[k] for k in w.fieldnames})
