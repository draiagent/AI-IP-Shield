from __future__ import annotations

from pathlib import Path
import numpy as np

from .base import WatermarkEngine
from .blind_native import BlindWatermarkNativeEngine
from ..payload import decode_payload, encode_payload, encoded_length


class BlindWatermarkAdapter(WatermarkEngine):
    """Adapter for guofei9987/blind_watermark with a dependency-free fallback.

    The upstream package requires the watermark bit length during extraction. AI-IP
    Shield uses a fixed authenticated payload length, so no per-file wm_shape metadata
    is needed. If the upstream package is unavailable, the adapter falls back to the
    clean-room DWT-DCT-SVD compatibility engine so the benchmark remains executable.
    """

    def __init__(self, password_img: int = 1, password_wm: int = 1, fallback_native: bool = True):
        self.password_img = int(password_img)
        self.password_wm = int(password_wm)
        self.ecc = "conv12"
        self.payload_bits = encoded_length(self.ecc)
        self._native: BlindWatermarkNativeEngine | None = None
        try:
            from blind_watermark import WaterMark  # type: ignore
            self.WaterMark = WaterMark
            self.name = "blind-watermark-upstream"
        except ImportError:
            if not fallback_native:
                raise RuntimeError("blind-watermark is not installed")
            self.WaterMark = None
            self._native = BlindWatermarkNativeEngine(password_img=password_img, password_wm=password_wm)
            self.name = self._native.name

    @property
    def using_upstream(self) -> bool:
        return self.WaterMark is not None

    def embed(self, input_path: str | Path, output_path: str | Path, token: str) -> None:
        if self._native is not None:
            return self._native.embed(input_path, output_path, token)
        bits = encode_payload(token, ecc=self.ecc)
        bwm = self.WaterMark(password_img=self.password_img, password_wm=self.password_wm)
        bwm.read_img(str(input_path))
        bwm.read_wm(np.asarray(bits, dtype=bool), mode="bit")
        bwm.embed(str(output_path))

    def _extract_bits_upstream(self, input_path: str | Path) -> list[int] | None:
        try:
            bwm = self.WaterMark(password_img=self.password_img, password_wm=self.password_wm)
            raw = bwm.extract(str(input_path), wm_shape=self.payload_bits, mode="bit")
            return (np.asarray(raw) >= 0.5).astype(np.uint8).tolist()
        except Exception:
            return None

    def extract(self, input_path: str | Path) -> str | None:
        if self._native is not None:
            return self._native.extract(input_path)
        bits = self._extract_bits_upstream(input_path)
        return decode_payload(bits or [], ecc=self.ecc)

    def evaluate_token(self, input_path: str | Path, expected_token: str) -> tuple[str | None, float]:
        if self._native is not None:
            return self._native.evaluate_token(input_path, expected_token)
        bits = self._extract_bits_upstream(input_path)
        if bits is None:
            return None, 1.0
        expected = np.asarray(encode_payload(expected_token, ecc=self.ecc), dtype=np.uint8)
        observed = np.asarray(bits[:len(expected)], dtype=np.uint8)
        if len(observed) != len(expected):
            return None, 1.0
        return decode_payload(observed.tolist(), ecc=self.ecc), float(np.mean(observed != expected))

    def bit_error_rate(self, input_path: str | Path, expected_token: str) -> float:
        return self.evaluate_token(input_path, expected_token)[1]
