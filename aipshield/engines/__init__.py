from .base import WatermarkEngine
from .dct_qim import DCTQIMEngine


def get_engine(name: str = "blind-native") -> WatermarkEngine:
    key = name.lower().strip()
    if key in {"dct-qim", "dct", "baseline"}:
        return DCTQIMEngine()
    if key in {"blind-watermark", "blind"}:
        from .blind_watermark_adapter import BlindWatermarkAdapter
        return BlindWatermarkAdapter(fallback_native=True)
    if key in {"blind-native", "blind-compatible"}:
        from .blind_native import BlindWatermarkNativeEngine
        return BlindWatermarkNativeEngine()
    if key in {"blind-native-pdf", "blind-pdf"}:
        from .blind_native import BlindWatermarkNativePDFEngine
        return BlindWatermarkNativePDFEngine()
    if key in {"pixelseal", "pixel-seal"}:
        from .pixelseal_adapter import PixelSealAdapter
        return PixelSealAdapter()
    raise ValueError(f"unknown watermark engine: {name}")
