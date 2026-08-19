from pathlib import Path
import tempfile

import cv2
import numpy as np

from aipshield.attack_lab import AttackSpec, apply_attack
from aipshield.engines.blind_native import BlindWatermarkNativeEngine


def _source(path: Path):
    h, w = 480, 640
    y, x = np.mgrid[0:h, 0:w]
    img = np.stack([
        60 + 160 * x / w,
        80 + 120 * y / h,
        100 + 80 * np.sin((x + y) / 45.0),
    ], axis=-1)
    img = np.clip(img, 0, 255).astype(np.uint8)
    cv2.rectangle(img, (60, 60), (580, 420), (235, 235, 235), 3)
    cv2.putText(img, "AI-IP Shield", (160, 245), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (30, 30, 30), 2, cv2.LINE_AA)
    cv2.imwrite(str(path), img)


def test_geometry_recovery_screenshot_crop_rotate():
    token = "0123456789ABCDEF"
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        src = td / "src.png"
        protected = td / "protected.png"
        _source(src)
        engine = BlindWatermarkNativeEngine()
        engine.embed(src, protected, token)
        specs = [
            AttackSpec("screen", "screenshot-sim", {"scale": 0.90, "quality": 85}),
            AttackSpec("crop10", "crop", {"fraction": 0.10}),
            AttackSpec("crop20", "crop", {"fraction": 0.20}),
            AttackSpec("rotate3", "rotate", {"degrees": 3.0}),
        ]
        for spec in specs:
            out = td / f"{spec.attack_id}.jpg"
            attacked = apply_attack(protected, out, spec)
            recovered, ber = engine.evaluate_token(attacked, token)
            assert recovered == token
            assert ber <= 0.05
