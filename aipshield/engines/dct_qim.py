from __future__ import annotations
from pathlib import Path
import binascii
import cv2
import numpy as np
from .base import WatermarkEngine

MAGIC = 0xA17E
MAGIC_BITS = 16
TOKEN_BITS = 64
CRC_BITS = 16
TOTAL_BITS = MAGIC_BITS + TOKEN_BITS + CRC_BITS

class DCTQIMEngine(WatermarkEngine):
    """Dependency-light DCT-QIM baseline used to prove the v0.1 vertical slice.

    This is intentionally an internal baseline engine, not a claim that it is
    equivalent to PixelSeal or the guofei9987 blind-watermark implementation.
    """

    name = "dct-qim-baseline"

    def __init__(self, delta: float = 28.0, repeats: int = 9, seed: int = 20260818):
        self.delta = float(delta)
        self.repeats = int(repeats)
        self.seed = int(seed)

    @staticmethod
    def _int_to_bits(value: int, n: int) -> list[int]:
        return [(value >> (n - 1 - i)) & 1 for i in range(n)]

    @staticmethod
    def _bits_to_int(bits: list[int]) -> int:
        v = 0
        for b in bits:
            v = (v << 1) | int(b)
        return v

    @staticmethod
    def _token_bytes(token: str) -> bytes:
        if len(token) != 16:
            raise ValueError("watermark token must be exactly 16 hex characters")
        try:
            return bytes.fromhex(token)
        except ValueError as e:
            raise ValueError("watermark token must be hexadecimal") from e

    def _payload_bits(self, token: str) -> list[int]:
        token_b = self._token_bytes(token)
        token_int = int.from_bytes(token_b, "big")
        crc = binascii.crc_hqx(token_b, 0xFFFF)
        return (
            self._int_to_bits(MAGIC, MAGIC_BITS)
            + self._int_to_bits(token_int, TOKEN_BITS)
            + self._int_to_bits(crc, CRC_BITS)
        )

    def _block_positions(self, h: int, w: int) -> np.ndarray:
        by, bx = h // 8, w // 8
        total = by * bx
        need = TOTAL_BITS * self.repeats
        if total < need:
            raise ValueError(
                f"image capacity too small: {total} DCT blocks available, {need} required; "
                "use an image of roughly 256x256 or larger"
            )
        idx = np.arange(total)
        rng = np.random.default_rng(self.seed)
        rng.shuffle(idx)
        return idx[:need]

    def embed(self, input_path: str | Path, output_path: str | Path, token: str) -> None:
        img = cv2.imread(str(input_path), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"cannot read image: {input_path}")
        ycc = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb).astype(np.float32)
        y = ycc[:, :, 0]
        h, w = y.shape
        positions = self._block_positions(h, w)
        bits = self._payload_bits(token)
        by, bx = h // 8, w // 8

        # Repeat each payload bit over multiple pseudorandom blocks.
        for i, bit in enumerate(bits):
            for r in range(self.repeats):
                flat = int(positions[i * self.repeats + r])
                yy, xx = divmod(flat, bx)
                y0, x0 = yy * 8, xx * 8
                block = y[y0:y0+8, x0:x0+8].astype(np.float32)
                coeff = cv2.dct(block)
                c = float(coeff[3, 4])
                q = int(np.round(c / self.delta))
                if (q & 1) != bit:
                    # nearest parity-correct quantization point
                    q_up = q + 1
                    q_down = q - 1
                    candidates = [qq for qq in (q_up, q_down) if (qq & 1) == bit]
                    q = min(candidates, key=lambda qq: abs(c - qq * self.delta))
                coeff[3, 4] = q * self.delta
                y[y0:y0+8, x0:x0+8] = cv2.idct(coeff)

        ycc[:, :, 0] = np.clip(y, 0, 255)
        out = cv2.cvtColor(ycc.astype(np.uint8), cv2.COLOR_YCrCb2BGR)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        # PNG is the vertical-slice default to avoid introducing a second lossy transform.
        if not cv2.imwrite(str(output_path), out):
            raise IOError(f"failed to write image: {output_path}")

    def extract_raw_bits(self, input_path: str | Path) -> list[int] | None:
        """Return raw majority-voted payload bits for diagnostics, even if CRC fails."""
        img = cv2.imread(str(input_path), cv2.IMREAD_COLOR)
        if img is None:
            return None
        ycc = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb).astype(np.float32)
        y = ycc[:, :, 0]
        h, w = y.shape
        try:
            positions = self._block_positions(h, w)
        except ValueError:
            return None
        by, bx = h // 8, w // 8
        out_bits: list[int] = []
        for i in range(TOTAL_BITS):
            votes = []
            for r in range(self.repeats):
                flat = int(positions[i * self.repeats + r])
                yy, xx = divmod(flat, bx)
                y0, x0 = yy * 8, xx * 8
                block = y[y0:y0+8, x0:x0+8].astype(np.float32)
                coeff = cv2.dct(block)
                q = int(np.round(float(coeff[3, 4]) / self.delta))
                votes.append(q & 1)
            out_bits.append(1 if sum(votes) > len(votes) / 2 else 0)
        return out_bits

    def decode_raw_bits(self, out_bits: list[int] | None) -> str | None:
        if out_bits is None:
            return None
        magic = self._bits_to_int(out_bits[:MAGIC_BITS])
        if magic != MAGIC:
            return None
        token_int = self._bits_to_int(out_bits[MAGIC_BITS:MAGIC_BITS+TOKEN_BITS])
        crc = self._bits_to_int(out_bits[-CRC_BITS:])
        token_b = token_int.to_bytes(8, "big")
        if binascii.crc_hqx(token_b, 0xFFFF) != crc:
            return None
        return token_b.hex().upper()

    def evaluate_token(self, input_path: str | Path, expected_token: str) -> tuple[str | None, float]:
        observed = self.extract_raw_bits(input_path)
        if observed is None:
            return None, 1.0
        expected = self._payload_bits(expected_token)
        errors = sum(int(a != b) for a, b in zip(observed, expected))
        return self.decode_raw_bits(observed), errors / len(expected)

    def bit_error_rate(self, input_path: str | Path, expected_token: str) -> float:
        return self.evaluate_token(input_path, expected_token)[1]

    def extract(self, input_path: str | Path) -> str | None:
        return self.decode_raw_bits(self.extract_raw_bits(input_path))
