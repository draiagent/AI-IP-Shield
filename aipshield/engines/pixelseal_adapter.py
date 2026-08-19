from __future__ import annotations

import os
from pathlib import Path
import tempfile
from typing import Any

import numpy as np
from PIL import Image

from .base import WatermarkEngine
from ..payload import decode_payload, encode_payload
from ..pixelseal_runtime import add_videoseal_source


class PixelSealAdapter(WatermarkEngine):
    """Meta PixelSeal adapter with explicit runtime and checkpoint boundaries.

    Backends, in priority order:
      1. injected model object (tests/integration)
      2. compatible TorchScript model (``model_path`` / AIPSHIELD_PIXELSEAL_MODEL)
      3. facebookresearch/videoseal + local PixelSeal ``.pth`` checkpoint
      4. facebookresearch/videoseal automatic model-card download

    A local ``.pth`` is *not* treated as TorchScript. Step 5.6.2 fixed that ambiguity.
    """

    capacity_bits = 256
    name = "pixelseal"

    def __init__(
        self,
        model: Any | None = None,
        model_path: str | Path | None = None,
        checkpoint_path: str | Path | None = None,
        source_dir: str | Path | None = None,
        device: str | None = None,
        model_name: str = "pixelseal",
    ):
        try:
            import torch
        except ImportError as exc:
            raise RuntimeError("PixelSeal requires PyTorch") from exc

        self.torch = torch
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.backend: str | None = None
        self.model_name = model_name
        self.checkpoint_path: Path | None = None

        env_model = os.environ.get("AIPSHIELD_PIXELSEAL_MODEL")
        env_ckpt = os.environ.get("AIPSHIELD_PIXELSEAL_CHECKPOINT")
        env_source = os.environ.get("AIPSHIELD_PIXELSEAL_SOURCE")
        model_path = model_path or env_model
        checkpoint_path = checkpoint_path or env_ckpt
        source_dir = source_dir or env_source

        if model is not None:
            self.model = model
            self.backend = "injected"
        else:
            # Explicit TorchScript path only. A .pth checkpoint is handled by videoseal.
            ts_path = Path(model_path).expanduser() if model_path else None
            if ts_path:
                if not ts_path.is_file():
                    raise FileNotFoundError(f"PixelSeal-compatible TorchScript model not found: {ts_path}")
                if ts_path.suffix.lower() == ".pth":
                    raise ValueError(
                        "A .pth file is a VideoSeal/PixelSeal checkpoint, not TorchScript. "
                        "Pass it as checkpoint_path or AIPSHIELD_PIXELSEAL_CHECKPOINT."
                    )
                self.model = torch.jit.load(str(ts_path), map_location=self.device)
                self.backend = "torchscript"
                self.name = f"pixelseal-compatible-torchscript:{ts_path.name}"
            else:
                if source_dir:
                    add_videoseal_source(source_dir)
                try:
                    import videoseal  # type: ignore
                except ImportError as exc:
                    raise RuntimeError(
                        "PixelSeal runtime unavailable. Install facebookresearch/videoseal or point "
                        "AIPSHIELD_PIXELSEAL_SOURCE at a local checkout."
                    ) from exc

                ckpt = Path(checkpoint_path).expanduser().resolve() if checkpoint_path else None
                if ckpt:
                    if not ckpt.is_file():
                        raise FileNotFoundError(f"PixelSeal checkpoint not found: {ckpt}")
                    if ckpt.stat().st_size <= 1024 * 1024:
                        raise RuntimeError(
                            f"PixelSeal checkpoint is too small ({ckpt.stat().st_size} bytes); "
                            "this often means an HTML page or Git-LFS/Xet pointer was downloaded instead of model weights."
                        )
                    self.model = self._load_videoseal_with_local_checkpoint(videoseal, ckpt, model_name)
                    self.checkpoint_path = ckpt
                    self.backend = "videoseal-local-checkpoint"
                    self.name = f"{model_name}:local-checkpoint"
                else:
                    self.model = videoseal.load(model_name)
                    self.backend = "videoseal-auto"
                    self.name = model_name

        if hasattr(self.model, "to"):
            self.model.to(self.device)
        if hasattr(self.model, "eval"):
            self.model.eval()

    @staticmethod
    def _load_videoseal_with_local_checkpoint(videoseal_module, checkpoint: Path, model_name: str):
        """Load a local inference checkpoint using the official model-card architecture.

        The official PixelSeal card contains the architecture. We clone the card into a
        temporary YAML and only replace ``checkpoint_path``. This avoids assuming the
        inference checkpoint itself stores all architecture args.
        """
        package_dir = Path(videoseal_module.__file__).resolve().parent
        card = package_dir / "cards" / f"{model_name}.yaml"
        if not card.is_file():
            raise FileNotFoundError(f"VideoSeal model card not found: {card}")
        lines = card.read_text(encoding="utf-8").splitlines()
        replaced = False
        out: list[str] = []
        for line in lines:
            if line.lstrip().startswith("checkpoint_path:") and not replaced:
                out.append(f"checkpoint_path: {checkpoint.as_posix()}")
                replaced = True
            else:
                out.append(line)
        if not replaced:
            raise RuntimeError(f"checkpoint_path missing from model card: {card}")
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", encoding="utf-8", delete=False) as f:
            f.write("\n".join(out) + "\n")
            patched = Path(f.name)
        try:
            return videoseal_module.load(patched)
        finally:
            patched.unlink(missing_ok=True)

    def _image_tensor(self, path: str | Path):
        arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
        return self.torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).to(self.device)

    def _message_tensor(self, token: str):
        bits = encode_payload(token, total_bits=self.capacity_bits, ecc="conv12")
        return self.torch.tensor(bits, dtype=self.torch.float32, device=self.device).unsqueeze(0)

    @staticmethod
    def _unwrap_embed(output):
        if isinstance(output, dict):
            if "imgs_w" not in output:
                raise RuntimeError(f"PixelSeal embed output missing imgs_w; keys={list(output)}")
            return output["imgs_w"]
        if isinstance(output, (tuple, list)):
            return output[0]
        return output

    @staticmethod
    def _unwrap_detect(output):
        if isinstance(output, dict):
            if "preds" not in output:
                raise RuntimeError(f"PixelSeal detect output missing preds; keys={list(output)}")
            return output["preds"]
        if isinstance(output, (tuple, list)):
            return output[-1]
        return output

    def embed(self, input_path: str | Path, output_path: str | Path, token: str) -> None:
        img = self._image_tensor(input_path)
        msg = self._message_tensor(token)
        with self.torch.no_grad():
            try:
                output = self.model.embed(img, msg, is_video=False)
            except TypeError:
                output = self.model.embed(img, msg)
        watermarked = self._unwrap_embed(output)
        if not self.torch.is_tensor(watermarked) or watermarked.ndim != 4:
            raise RuntimeError("PixelSeal embed output must be a BCHW tensor")
        watermarked = watermarked.detach().clamp(0, 1).cpu()[0]
        arr = (watermarked.permute(1, 2, 0).numpy() * 255.0).round().astype(np.uint8)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(arr).save(output_path, format="PNG")

    def _bit_logits(self, input_path: str | Path):
        img = self._image_tensor(input_path)
        with self.torch.no_grad():
            try:
                output = self.model.detect(img, is_video=False)
            except TypeError:
                output = self.model.detect(img)
        preds = self._unwrap_detect(output)
        if not self.torch.is_tensor(preds):
            preds = self.torch.as_tensor(preds)
        preds = preds.detach().float().cpu()

        # Official VideoSeal/PixelSeal may return either [B,1+K] or [B,1+K,H,W].
        if preds.ndim == 4:
            bit_logits = preds[:, 1:, :, :].mean(dim=(2, 3))
        elif preds.ndim == 2:
            bit_logits = preds[:, 1:]
        else:
            raise RuntimeError(f"unexpected PixelSeal detector output shape: {tuple(preds.shape)}")
        if bit_logits.shape[1] < self.capacity_bits:
            raise RuntimeError(
                f"PixelSeal detector returned {bit_logits.shape[1]} message bits; need {self.capacity_bits}"
            )
        return bit_logits[:, : self.capacity_bits]

    def extract_bits(self, input_path: str | Path) -> list[int]:
        logits = self._bit_logits(input_path)[0]
        return (logits > 0).to(self.torch.uint8).tolist()

    def extract(self, input_path: str | Path) -> str | None:
        try:
            return decode_payload(self.extract_bits(input_path), ecc="conv12")
        except Exception:
            return None

    def evaluate_token(self, input_path: str | Path, expected_token: str) -> tuple[str | None, float]:
        try:
            observed = np.asarray(self.extract_bits(input_path), dtype=np.uint8)
        except Exception:
            return None, 1.0
        expected = np.asarray(
            encode_payload(expected_token, total_bits=self.capacity_bits, ecc="conv12"), dtype=np.uint8
        )
        ber = float(np.mean(observed[: len(expected)] != expected))
        return decode_payload(observed.tolist(), ecc="conv12"), ber

    def bit_error_rate(self, input_path: str | Path, expected_token: str) -> float:
        return self.evaluate_token(input_path, expected_token)[1]
