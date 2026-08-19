from __future__ import annotations

from pathlib import Path
import tempfile

import torch

from aipshield.pixelseal_runtime import inspect_pixelseal_runtime
from aipshield.engines.pixelseal_adapter import PixelSealAdapter
from tests.test_step561_engines import FakePixelSealModel, make_image


def test_runtime_rejects_tiny_checkpoint():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "checkpoint.pth"
        p.write_text("version https://git-lfs.github.com/spec/v1\n", encoding="utf-8")
        status = inspect_pixelseal_runtime(checkpoint_path=p)
        assert status.checkpoint_exists
        assert not status.checkpoint_looks_valid
        assert any("suspiciously small" in e for e in status.errors)


def test_adapter_rejects_pth_as_torchscript_model_path():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "checkpoint.pth"
        p.write_bytes(b"x" * 1024)
        try:
            PixelSealAdapter(model_path=p, device="cpu")
        except ValueError as exc:
            assert "checkpoint_path" in str(exc)
        else:
            raise AssertionError(".pth must not be treated as TorchScript")


class FakePixelSealMapModel(FakePixelSealModel):
    """Official-like dict + BCHW detector output contract."""
    def embed(self, img, msg, is_video=False):
        return {"imgs_w": super().embed(img, msg, is_video=is_video)}

    def detect(self, img, is_video=False):
        base = super().detect(img, is_video=is_video)
        return {"preds": base[:, :, None, None].expand(-1, -1, 2, 2)}


def test_pixelseal_adapter_official_like_dict_and_map_contract():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        src, out = td / "src.png", td / "out.png"
        make_image(src)
        engine = PixelSealAdapter(model=FakePixelSealMapModel(), device="cpu")
        token = "0123456789ABCDEF"
        engine.embed(src, out, token)
        recovered, ber = engine.evaluate_token(out, token)
        assert recovered == token
        assert ber == 0.0
