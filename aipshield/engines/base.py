from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path

class WatermarkEngine(ABC):
    name: str

    @abstractmethod
    def embed(self, input_path: str | Path, output_path: str | Path, token: str) -> None:
        """Embed a registry token into an image."""

    @abstractmethod
    def extract(self, input_path: str | Path) -> str | None:
        """Return token when a valid watermark is detected, otherwise None."""

    def detect(self, input_path: str | Path) -> bool:
        return self.extract(input_path) is not None
