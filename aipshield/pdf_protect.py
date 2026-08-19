from __future__ import annotations

from pathlib import Path
import tempfile

from .adapters.pdf import render_pdf_pages, rebuild_pdf_from_images
from .engines import get_engine
from .fingerprint import generate_fingerprint
from .registry import FingerprintRegistry
from .models import PDFProtectionResult
from .utils.hash import sha256_file
from .report import write_json_report
from .provenance import sign_sidecar, sign_c2pa


def protect_pdf(
    input_path: str,
    output_path: str,
    registry_path: str,
    engine_name: str = "blind-native-pdf",
    version: int = 1,
    report_path: str | None = None,
    *,
    render_dpi: int = 120,
    page_image_format: str = "jpeg",
    jpeg_quality: int = 90,
    provenance_mode: str = "none",
    signing_private_key: str | None = None,
    signing_public_key: str | None = None,
    c2pa_cert: str | None = None,
    do_not_train: bool = False,
    title: str | None = None,
) -> PDFProtectionResult:
    src = Path(input_path)
    out = Path(output_path)
    if src.suffix.lower() != ".pdf":
        raise ValueError("protect_pdf requires a .pdf input")
    if out.suffix.lower() != ".pdf":
        raise ValueError("protect_pdf requires a .pdf output")
    if src.resolve() == out.resolve():
        raise ValueError("input and output PDF paths must be different")
    if provenance_mode not in {"none", "sidecar", "c2pa"}:
        raise ValueError("provenance_mode must be one of: none, sidecar, c2pa")

    source_sha = sha256_file(src)
    fp = generate_fingerprint(source_sha, version=version)
    engine = get_engine(engine_name)
    provenance = None
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="aips-pdf-protect-", dir=str(out.parent)) as td:
        work = Path(td)
        rendered, info = render_pdf_pages(src, work / "rendered", dpi=render_dpi)
        protected_pages: list[Path] = []
        for i, page in enumerate(rendered, start=1):
            page_out = work / "protected" / f"page-{i:04d}.png"
            page_out.parent.mkdir(parents=True, exist_ok=True)
            engine.embed(page, page_out, fp.watermark_token)
            protected_pages.append(page_out)

        if provenance_mode == "c2pa":
            if not c2pa_cert or not signing_private_key:
                raise ValueError("c2pa provenance requires --c2pa-cert and --signing-key")
            unsigned_pdf = work / "protected-unsigned.pdf"
            rebuild_pdf_from_images(
                protected_pages,
                unsigned_pdf,
                info,
                image_format=page_image_format,
                jpeg_quality=jpeg_quality,
            )
            prov = sign_c2pa(
                unsigned_pdf,
                out,
                cert_path=c2pa_cert,
                private_key_path=signing_private_key,
                title=title or out.name,
                do_not_train=do_not_train,
            )
            provenance = prov.to_dict()
        else:
            rebuild_pdf_from_images(
                protected_pages,
                out,
                info,
                image_format=page_image_format,
                jpeg_quality=jpeg_quality,
            )
            if provenance_mode == "sidecar":
                if not signing_private_key or not signing_public_key:
                    raise ValueError("sidecar provenance requires --signing-key and --public-key")
                prov = sign_sidecar(
                    out,
                    signing_private_key,
                    signing_public_key,
                    asset_id=fp.asset_id,
                    fingerprint_id=fp.fingerprint_id,
                    version=fp.version,
                    title=title or out.name,
                    do_not_train=do_not_train,
                )
                provenance = prov.to_dict()

    protected_sha = sha256_file(out)
    registry = FingerprintRegistry(registry_path)
    registry.add(
        fp=fp,
        source_sha256=source_sha,
        protected_sha256=protected_sha,
        source_path=str(src),
        protected_path=str(out),
        engine=engine.name,
        provenance_backend=(provenance or {}).get("backend"),
        provenance_ref=(provenance or {}).get("manifest_path"),
        signer_key_id=(provenance or {}).get("signer_key_id"),
        provenance_status=(provenance or {}).get("status"),
        asset_type="pdf",
        page_count=info.page_count,
        render_dpi=info.render_dpi,
    )

    result = PDFProtectionResult(
        input_path=str(src),
        output_path=str(out),
        source_sha256=source_sha,
        protected_sha256=protected_sha,
        fingerprint=fp,
        engine=engine.name,
        page_count=info.page_count,
        render_dpi=info.render_dpi,
        page_image_format=page_image_format.lower(),
        rasterized=True,
        provenance=provenance,
    )
    if report_path:
        result.report_path = write_json_report(result.to_dict(), report_path)
    return result
