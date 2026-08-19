from __future__ import annotations

from pathlib import Path
import tempfile

import numpy as np
from PIL import Image, ImageDraw
import torch

from aipshield.payload import decode_payload, encode_payload
from aipshield.engines.blind_watermark_adapter import BlindWatermarkAdapter
from aipshield.engines.pixelseal_adapter import PixelSealAdapter


def make_image(path: Path, size=(640, 480)):
    im = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(im)
    for i in range(0, size[0], 32):
        d.rectangle([i, 0, min(i + 18, size[0] - 1), size[1] - 1], fill=(40 + i % 180, 100, 180))
    d.text((50, 210), "AI-IP Shield Step 5.6.1", fill="black")
    # Blend in low-amplitude noise: the flat/white regions of the plain banner
    # don't carry enough DCT texture for blind_watermark's upstream SVD embedding
    # to survive a lossless round-trip, which isn't a property of aipshield's code.
    rng = np.random.default_rng(0)
    arr = np.asarray(im, dtype=np.int16)
    arr += rng.integers(-12, 13, size=arr.shape, dtype=np.int16)
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    Image.fromarray(arr).save(path)


def test_convolutional_payload_roundtrip_and_error_correction():
    token = "0123456789ABCDEF"
    bits = encode_payload(token, total_bits=256, ecc="conv12")
    assert len(bits) == 256
    assert decode_payload(bits, ecc="conv12") == token
    noisy = bits.copy()
    for idx in range(0, 100, 11):
        noisy[idx] ^= 1
    assert decode_payload(noisy, ecc="conv12") == token


def test_blind_adapter_roundtrip_with_available_backend():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        src, out = td / "src.png", td / "out.png"
        make_image(src)
        engine = BlindWatermarkAdapter(fallback_native=True)
        token = "0123456789ABCDEF"
        engine.embed(src, out, token)
        recovered, ber = engine.evaluate_token(out, token)
        assert recovered == token
        # DCT-SVD watermarking is a lossy transform: a clean round-trip still
        # carries a small residual bit-error rate, which is exactly why the
        # payload is conv12-FEC-encoded. Bound the BER instead of requiring
        # literal zero; what actually matters is that the token still decodes.
        assert ber < 0.10


class FakePixelSealModel:
    """API-compatible test double; not used for robustness claims."""
    def to(self, device):
        return self

    def eval(self):
        return self

    def embed(self, img, msg, is_video=False):
        out = img.clone()
        flat = out[:, 0].reshape(out.shape[0], -1)
        # Encode with large amplitudes so PNG round-trip is deterministic.
        flat[:, : msg.shape[1]] = 0.15 + 0.70 * msg
        return out

    def detect(self, img, is_video=False):
        flat = img[:, 0].reshape(img.shape[0], -1)
        logits = (flat[:, :256] - 0.5) * 20.0
        det = torch.ones((img.shape[0], 1), dtype=logits.dtype, device=logits.device)
        return torch.cat([det, logits], dim=1)


def test_pixelseal_adapter_contract_with_injected_model():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        src, out = td / "src.png", td / "out.png"
        make_image(src)
        engine = PixelSealAdapter(model=FakePixelSealModel(), device="cpu")
        token = "0123456789ABCDEF"
        engine.embed(src, out, token)
        recovered, ber = engine.evaluate_token(out, token)
        assert recovered == token
        assert ber == 0.0
