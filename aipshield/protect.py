from __future__ import annotations
from pathlib import Path
import tempfile
from .engines import get_engine
from .fingerprint import generate_fingerprint
from .registry import FingerprintRegistry
from .models import ProtectionResult
from .utils.hash import sha256_file
from .report import write_json_report
from .provenance import sign_sidecar, sign_c2pa

SUPPORTED = {".png", ".jpg", ".jpeg"}


def protect_image(
    input_path: str,
    output_path: str,
    registry_path: str,
    engine_name: str = "blind-native",
    version: int = 1,
    report_path: str | None = None,
    provenance_mode: str = "none",
    signing_private_key: str | None = None,
    signing_public_key: str | None = None,
    c2pa_cert: str | None = None,
    do_not_train: bool = False,
    title: str | None = None,
) -> ProtectionResult:
    src = Path(input_path)
    out = Path(output_path)
    if src.suffix.lower() not in SUPPORTED:
        raise ValueError(f"unsupported image format: {src.suffix}")
    if out.suffix.lower() != ".png":
        raise ValueError("vertical slice requires PNG output for deterministic round-trip")
    if provenance_mode not in {"none", "sidecar", "c2pa"}:
        raise ValueError("provenance_mode must be one of: none, sidecar, c2pa")

    source_sha = sha256_file(src)
    fp = generate_fingerprint(source_sha, version=version)
    engine = get_engine(engine_name)
    provenance = None

    if provenance_mode == "c2pa":
        if not c2pa_cert or not signing_private_key:
            raise ValueError("c2pa provenance requires --c2pa-cert and --signing-key")
        out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix=".png", dir=out.parent, delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            engine.embed(src, tmp_path, fp.watermark_token)
            prov = sign_c2pa(
                tmp_path, out,
                cert_path=c2pa_cert,
                private_key_path=signing_private_key,
                title=title or out.name,
                do_not_train=do_not_train,
            )
            provenance = prov.to_dict()
        finally:
            tmp_path.unlink(missing_ok=True)
    else:
        engine.embed(src, out, fp.watermark_token)
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
    )

    result = ProtectionResult(
        input_path=str(src),
        output_path=str(out),
        source_sha256=source_sha,
        protected_sha256=protected_sha,
        fingerprint=fp,
        engine=engine.name,
        provenance=provenance,
    )
    if report_path:
        result.report_path = write_json_report(result.to_dict(), report_path)
    return result
