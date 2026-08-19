from __future__ import annotations
from pathlib import Path
from .engines import get_engine
from .registry import FingerprintRegistry
from .models import VerificationResult
from .utils.hash import sha256_file
from .report import write_json_report, write_markdown_verification
from .provenance import default_sidecar_path, verify_sidecar, verify_c2pa, ProvenanceResult


def _select_provenance(
    input_path: str,
    row: dict | None,
    *,
    provenance_mode: str,
    provenance_sidecar: str | None,
    trust_store: str | None,
) -> ProvenanceResult | None:
    if provenance_mode == "none":
        return None
    if provenance_mode not in {"auto", "sidecar", "c2pa"}:
        raise ValueError("provenance_mode must be one of: auto, none, sidecar, c2pa")
    if provenance_mode == "c2pa":
        return verify_c2pa(input_path)
    if provenance_mode == "sidecar":
        return verify_sidecar(input_path, sidecar_path=provenance_sidecar, trust_store_path=trust_store)

    # auto: use the registered backend when available. If the asset is a copied file,
    # prefer a sidecar adjacent to that copy rather than silently trusting the original path.
    registered_backend = (row or {}).get("provenance_backend")
    if registered_backend == "c2pa":
        return verify_c2pa(input_path)
    if registered_backend == "aip-sidecar-ed25519":
        adjacent = default_sidecar_path(input_path)
        sidecar = Path(provenance_sidecar) if provenance_sidecar else adjacent
        if not sidecar.is_file() and row and Path(input_path).resolve() == Path(row.get("protected_path") or "").resolve():
            reg_ref = row.get("provenance_ref")
            if reg_ref:
                sidecar = Path(reg_ref)
        return verify_sidecar(input_path, sidecar_path=sidecar, trust_store_path=trust_store)

    if provenance_sidecar or default_sidecar_path(input_path).is_file():
        return verify_sidecar(input_path, sidecar_path=provenance_sidecar, trust_store_path=trust_store)
    return None


def _fuse_evidence(
    *,
    token: str | None,
    row: dict | None,
    exact: bool,
    provenance: ProvenanceResult | None,
) -> tuple[str, str]:
    if not token:
        if provenance and provenance.status == "VALID_TRUSTED":
            return "PROVENANCE_VERIFIED", "Trusted cryptographic provenance is valid, but no AI-IP Shield watermark was detected."
        return "NO_EVIDENCE", "No valid AI-IP Shield watermark payload was detected."
    if not row:
        if provenance and provenance.status == "VALID_TRUSTED":
            return "MODERATE", "A valid trusted provenance record exists, but the watermark token is not in this registry."
        return "WEAK", "A structurally valid watermark was detected, but the token is not present in this registry."

    if provenance:
        if provenance.status == "VALID_TRUSTED":
            if exact:
                return "CRYPTOGRAPHICALLY_VERIFIED", "Watermark, registry, exact protected hash, and trusted provenance all agree."
            return "STRONG_SOURCE_ASSOCIATION", "Watermark and registry identify the source copy; trusted provenance is valid for this asset."
        if provenance.status == "VALID_UNTRUSTED":
            if exact:
                return "SIGNED_SOURCE_MATCH_UNTRUSTED", "Watermark and exact registry hash match; the provenance signature is valid but its signer is not trusted locally."
            return "STRONG", "Watermark and registry match; provenance is signed but the signer is not trusted locally."
        if provenance.status == "MODIFIED":
            return "STRONG_SOURCE_ASSOCIATION_MODIFIED", "The watermark identifies a registered source copy, while provenance indicates that the current bytes differ from the signed asset."
        if provenance.status in {"INVALID", "INVALID_SIGNATURE"}:
            return "CONFLICTING_EVIDENCE", "The watermark identifies a registered source copy, but the provenance record is invalid or has an invalid signature."

    if exact:
        return "REGISTERED_EXACT_MATCH", "Watermark token and registry record match; the protected file hash also matches exactly."
    return "STRONG", "Watermark token matches a registry record, but the file bytes differ from the registered protected copy."


def verify_image(
    input_path: str,
    registry_path: str,
    engine_name: str = "blind-native",
    report_json: str | None = None,
    report_md: str | None = None,
    provenance_mode: str = "auto",
    provenance_sidecar: str | None = None,
    trust_store: str | None = None,
) -> VerificationResult:
    engine = get_engine(engine_name)
    candidate_sha = sha256_file(input_path)
    token = engine.extract(input_path)
    registry = FingerprintRegistry(registry_path)
    row = registry.get_by_token(token) if token else None
    exact = bool(row) and candidate_sha == row["protected_sha256"]
    provenance = _select_provenance(
        input_path, row,
        provenance_mode=provenance_mode,
        provenance_sidecar=provenance_sidecar,
        trust_store=trust_store,
    )
    evidence_level, message = _fuse_evidence(token=token, row=row, exact=exact, provenance=provenance)

    result = VerificationResult(
        input_path=input_path,
        detected=bool(token),
        watermark_token=token,
        fingerprint_id=row["fingerprint_id"] if row else None,
        registry_match=bool(row),
        exact_protected_hash_match=bool(exact),
        candidate_sha256=candidate_sha,
        source_sha256=row["source_sha256"] if row else None,
        protected_sha256=row["protected_sha256"] if row else None,
        engine=engine.name,
        evidence_level=evidence_level,
        message=message,
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

    data = result.to_dict()
    if report_json:
        result.report_path = write_json_report(data, report_json)
    if report_md:
        write_markdown_verification(data, report_md)
    return result
