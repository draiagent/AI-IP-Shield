from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class Fingerprint:
    fingerprint_id: str
    watermark_token: str
    asset_id: str
    copy_id: str
    version: int


@dataclass
class ProtectionResult:
    input_path: str
    output_path: str
    source_sha256: str
    protected_sha256: str
    fingerprint: Fingerprint
    engine: str
    report_path: str | None = None
    provenance: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VerificationResult:
    input_path: str
    detected: bool
    watermark_token: str | None
    fingerprint_id: str | None
    registry_match: bool
    exact_protected_hash_match: bool
    candidate_sha256: str
    source_sha256: str | None
    protected_sha256: str | None
    engine: str
    evidence_level: str
    message: str
    report_path: str | None = None
    provenance_backend: str | None = None
    provenance_status: str = "NOT_CHECKED"
    provenance_present: bool = False
    provenance_signature_valid: bool | None = None
    provenance_asset_hash_match: bool | None = None
    provenance_trusted: bool = False
    provenance_signer_key_id: str | None = None
    provenance_manifest_path: str | None = None
    provenance_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PDFProtectionResult:
    input_path: str
    output_path: str
    source_sha256: str
    protected_sha256: str
    fingerprint: Fingerprint
    engine: str
    page_count: int
    render_dpi: int
    page_image_format: str
    rasterized: bool = True
    report_path: str | None = None
    provenance: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PDFPageVerification:
    page_number: int
    detected: bool
    watermark_token: str | None
    registry_match: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PDFVerificationResult:
    input_path: str
    detected: bool
    consensus_watermark_token: str | None
    fingerprint_id: str | None
    registry_match: bool
    exact_protected_hash_match: bool
    candidate_sha256: str
    source_sha256: str | None
    protected_sha256: str | None
    engine: str
    evidence_level: str
    message: str
    page_count: int
    pages_detected: int
    page_detection_rate: float
    mixed_watermark_tokens: bool
    page_results: list[dict[str, Any]]
    render_dpi: int
    report_path: str | None = None
    provenance_backend: str | None = None
    provenance_status: str = "NOT_CHECKED"
    provenance_present: bool = False
    provenance_signature_valid: bool | None = None
    provenance_asset_hash_match: bool | None = None
    provenance_trusted: bool = False
    provenance_signer_key_id: str | None = None
    provenance_manifest_path: str | None = None
    provenance_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
