from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import tempfile
from typing import Iterable

import cv2
import fitz  # PyMuPDF


@dataclass(frozen=True)
class PDFRenderInfo:
    source_path: str
    page_count: int
    render_dpi: int
    page_sizes_points: list[tuple[float, float]]
    metadata: dict
    toc: list

    def to_dict(self) -> dict:
        return asdict(self)


def _open_pdf(path: str | Path) -> fitz.Document:
    p = Path(path)
    if p.suffix.lower() != ".pdf":
        raise ValueError(f"expected a PDF input, got: {p.suffix or '<no extension>'}")
    if not p.is_file():
        raise FileNotFoundError(p)
    try:
        doc = fitz.open(str(p))
    except Exception as exc:
        raise ValueError(f"cannot open PDF: {p}: {exc}") from exc
    if doc.needs_pass:
        doc.close()
        raise ValueError("encrypted/password-protected PDFs are not supported in V0.1")
    if doc.page_count < 1:
        doc.close()
        raise ValueError("PDF contains no pages")
    return doc


def render_pdf_pages(
    input_pdf: str | Path,
    output_dir: str | Path,
    *,
    dpi: int = 144,
    prefix: str = "page",
) -> tuple[list[Path], PDFRenderInfo]:
    if dpi < 72 or dpi > 600:
        raise ValueError("dpi must be between 72 and 600")
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    doc = _open_pdf(input_pdf)
    paths: list[Path] = []
    sizes: list[tuple[float, float]] = []
    scale = float(dpi) / 72.0
    matrix = fitz.Matrix(scale, scale)
    try:
        metadata = dict(doc.metadata or {})
        toc = doc.get_toc(simple=False) or []
        for i, page in enumerate(doc):
            rect = page.rect
            sizes.append((float(rect.width), float(rect.height)))
            pix = page.get_pixmap(matrix=matrix, alpha=False, colorspace=fitz.csRGB)
            p = outdir / f"{prefix}-{i+1:04d}.png"
            pix.save(str(p))
            paths.append(p)
    finally:
        doc.close()
    info = PDFRenderInfo(
        source_path=str(Path(input_pdf)),
        page_count=len(paths),
        render_dpi=int(dpi),
        page_sizes_points=sizes,
        metadata=metadata,
        toc=toc,
    )
    return paths, info


def _encode_page_image(path: Path, *, image_format: str, jpeg_quality: int) -> bytes:
    fmt = image_format.lower()
    if fmt not in {"png", "jpeg", "jpg"}:
        raise ValueError("image_format must be png or jpeg")
    if fmt == "png":
        return path.read_bytes()
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"cannot read rendered page image: {path}")
    quality = max(60, min(100, int(jpeg_quality)))
    ok, data = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise IOError(f"failed to JPEG-encode page image: {path}")
    return data.tobytes()


def rebuild_pdf_from_images(
    page_images: Iterable[str | Path],
    output_pdf: str | Path,
    info: PDFRenderInfo,
    *,
    image_format: str = "jpeg",
    jpeg_quality: int = 95,
) -> str:
    images = [Path(p) for p in page_images]
    if len(images) != info.page_count:
        raise ValueError(f"page image count mismatch: expected {info.page_count}, got {len(images)}")
    out = Path(output_pdf)
    if out.suffix.lower() != ".pdf":
        raise ValueError("PDF adapter output must use a .pdf extension")
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    try:
        for image_path, (width, height) in zip(images, info.page_sizes_points):
            page = doc.new_page(width=width, height=height)
            stream = _encode_page_image(image_path, image_format=image_format, jpeg_quality=jpeg_quality)
            page.insert_image(page.rect, stream=stream, keep_proportion=False, overlay=True)
        safe_metadata = {k: v for k, v in (info.metadata or {}).items() if isinstance(v, str)}
        if safe_metadata:
            try:
                doc.set_metadata(safe_metadata)
            except Exception:
                # Metadata is convenience data, never a security primitive.
                pass
        if info.toc:
            try:
                doc.set_toc(info.toc)
            except Exception:
                # Some PDFs contain outline variants PyMuPDF cannot round-trip.
                pass
        doc.save(str(out), garbage=4, deflate=True, clean=True)
    finally:
        doc.close()
    return str(out)


def raster_roundtrip_pdf(
    input_pdf: str | Path,
    output_pdf: str | Path,
    *,
    dpi: int = 120,
    jpeg_quality: int = 85,
) -> str:
    """Simulate Print-to-PDF / visual re-export, intentionally stripping provenance metadata."""
    with tempfile.TemporaryDirectory(prefix="aips-pdf-roundtrip-") as td:
        pages, info = render_pdf_pages(input_pdf, td, dpi=dpi)
        return rebuild_pdf_from_images(
            pages,
            output_pdf,
            info,
            image_format="jpeg",
            jpeg_quality=jpeg_quality,
        )


def extract_pdf_page(
    input_pdf: str | Path,
    output_pdf: str | Path,
    *,
    page_index: int = 0,
) -> str:
    """Extract one page as a PDF without rasterising again."""
    src = _open_pdf(input_pdf)
    out = Path(output_pdf)
    out.parent.mkdir(parents=True, exist_ok=True)
    if page_index < 0 or page_index >= src.page_count:
        src.close()
        raise IndexError(f"page_index out of range: {page_index}")
    dest = fitz.open()
    try:
        dest.insert_pdf(src, from_page=page_index, to_page=page_index)
        dest.save(str(out), garbage=4, deflate=True, clean=True)
    finally:
        dest.close()
        src.close()
    return str(out)
