from __future__ import annotations

from collections import Counter
from pathlib import Path
import tempfile

from .adapters.pdf import render_pdf_pages
from .engines import get_engine
from .registry import FingerprintRegistry
from .models import PDFPageVerification, PDFVerificationResult
from .utils.hash import sha256_file
from .report import write_json_report, write_markdown_pdf_verification
from .verify import _select_provenance, _fuse_evidence


def verify_pdf(
    input_path: str,
    registry_path: str,
    engine_name: str = "blind-native-pdf",
    report_json: str | None = None,
    report_md: str | None = None,
    *,
    render_dpi: int = 120,
    provenance_mode: str = "auto",
    provenance_sidecar: str | None = None,
    trust_store: str | None = None,
) -> PDFVerificationResult:
    src = Path(input_path)
    if src.suffix.lower() != ".pdf":
        raise ValueError("verify_pdf requires a .pdf input")

    candidate_sha = sha256_file(src)
    engine = get_engine(engine_name)
    registry = FingerprintRegistry(registry_path)
    exact_row = registry.get_by_protected_sha256(candidate_sha)

    page_results: list[PDFPageVerification] = []
    tokens: list[str] = []
    with tempfile.TemporaryDirectory(prefix="aips-pdf-verify-") as td:
        rendered, info = render_pdf_pages(src, td, dpi=render_dpi)
        for i, page in enumerate(rendered, start=1):
            token = engine.extract(page)
            row = registry.get_by_token(token) if token else None
            if token:
                tokens.append(token.upper())
            page_results.append(
                PDFPageVerification(
                    page_number=i,
                    detected=bool(token),
                    watermark_token=token.upper() if token else None,
                    registry_match=bool(row),
                )
            )

    counts = Counter(tokens)
    consensus = counts.most_common(1)[0][0] if counts else None
    distinct_tokens = set(tokens)
    mixed = len(distinct_tokens) > 1
    row = registry.get_by_token(consensus) if consensus else exact_row
    exact = bool(row) and candidate_sha == row.get("protected_sha256")
    provenance = _select_provenance(
        str(src), row,
        provenance_mode=provenance_mode,
        provenance_sidecar=provenance_sidecar,
        trust_store=trust_store,
    )

    pages_detected = sum(1 for r in page_results if r.detected)
    rate = pages_detected / len(page_results) if page_results else 0.0

    if mixed:
        evidence_level = "CONFLICTING_EVIDENCE"
        message = (
            "Different AI-IP Shield watermark tokens were recovered from different PDF pages. "
            "This can indicate a mixed/assembled document and must not be attributed to one source copy."
        )
    elif consensus:
        evidence_level, message = _fuse_evidence(
            token=consensus,
            row=row,
            exact=bool(exact),
            provenance=provenance,
        )
        message += f" Page watermark detection: {pages_detected}/{len(page_results)} ({rate:.1%})."
    elif exact_row:
        evidence_level = "CONFLICTING_EVIDENCE"
        message = (
            "The PDF bytes exactly match a registered protected file, but no page watermark could be recovered. "
            "Treat this as an engine/readability anomaly rather than silently upgrading the result."
        )
    else:
        evidence_level, message = _fuse_evidence(
            token=None,
            row=None,
            exact=False,
            provenance=provenance,
        )
        message += f" Page watermark detection: 0/{len(page_results)}."

    result = PDFVerificationResult(
        input_path=str(src),
        detected=bool(consensus),
        consensus_watermark_token=consensus,
        fingerprint_id=row.get("fingerprint_id") if row else None,
        registry_match=bool(row and consensus),
        exact_protected_hash_match=bool(exact),
        candidate_sha256=candidate_sha,
        source_sha256=row.get("source_sha256") if row else None,
        protected_sha256=row.get("protected_sha256") if row else None,
        engine=engine.name,
        evidence_level=evidence_level,
        message=message,
        page_count=len(page_results),
        pages_detected=pages_detected,
        page_detection_rate=rate,
        mixed_watermark_tokens=mixed,
        page_results=[r.to_dict() for r in page_results],
        render_dpi=render_dpi,
        provenance_backend=provenance.backend if provenance else None,
        provenance_status=provenance.status if provenance else "NOT_CHECKED",
        provenance_present=provenance.present if provenance else False,
        provenance_signature_valid=provenance.signature_valid if provenance else None,
        provenance_asset_hash_match=provenance.asset_hash_match if provenance else None,
        provenance_trusted=provenance.trusted if provenance else False,
        provenance_signer_key_id=provenance.signer_key_id if provenance else None,
        provenance_manifest_path=provenance.manifest_path if provenance else None,
        provenance_message=provenance.message if provenance else None,
    )
    if report_json:
        result.report_path = write_json_report(result.to_dict(), report_json)
    if report_md:
        write_markdown_pdf_verification(result.to_dict(), report_md)
        if not result.report_path:
            result.report_path = str(report_md)
    return result
