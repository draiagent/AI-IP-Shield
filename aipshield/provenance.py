from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import shutil
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .utils.hash import sha256_file


SIDECAR_SCHEMA = "https://ai-ip-shield.local/provenance/v1"
SIDECAR_SUFFIX = ".aiprov.json"


@dataclass
class ProvenanceResult:
    backend: str
    status: str
    present: bool
    signature_valid: bool | None
    asset_hash_match: bool | None
    trusted: bool
    signer_key_id: str | None
    manifest_path: str | None
    message: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def canonical_json_bytes(data: dict[str, Any]) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def default_sidecar_path(asset_path: str | Path) -> Path:
    p = Path(asset_path)
    return Path(str(p) + SIDECAR_SUFFIX)


def _public_key_id(public_key: Ed25519PublicKey) -> str:
    der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return "ed25519:" + hashlib.sha256(der).hexdigest()[:32]


def generate_signing_keypair(private_key_path: str | Path, public_key_path: str | Path, *, overwrite: bool = False) -> dict[str, str]:
    priv_path = Path(private_key_path)
    pub_path = Path(public_key_path)
    if not overwrite and (priv_path.exists() or pub_path.exists()):
        raise FileExistsError("signing key path already exists; pass overwrite=True to replace it")
    priv_path.parent.mkdir(parents=True, exist_ok=True)
    pub_path.parent.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    priv_path.write_bytes(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ))
    pub_path.write_bytes(public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ))
    try:
        priv_path.chmod(0o600)
    except OSError:
        pass
    return {
        "private_key": str(priv_path),
        "public_key": str(pub_path),
        "key_id": _public_key_id(public_key),
    }


def load_public_key(public_key_path: str | Path) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(Path(public_key_path).read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise TypeError("AI-IP Shield sidecar provenance requires an Ed25519 public key")
    return key


def load_private_key(private_key_path: str | Path) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(Path(private_key_path).read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError("AI-IP Shield sidecar provenance requires an Ed25519 private key")
    return key


def trust_public_key(public_key_path: str | Path, trust_store_path: str | Path, *, label: str | None = None) -> dict[str, Any]:
    public_key = load_public_key(public_key_path)
    key_id = _public_key_id(public_key)
    store_path = Path(trust_store_path)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    if store_path.exists():
        data = json.loads(store_path.read_text(encoding="utf-8"))
    else:
        data = {"schema": "ai-ip-shield-trust-store/v1", "keys": {}}
    keys = data.setdefault("keys", {})
    keys[key_id] = {
        "label": label or key_id,
        "public_key_pem": Path(public_key_path).read_text(encoding="utf-8"),
        "trusted_at": datetime.now(timezone.utc).isoformat(),
    }
    store_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"trust_store": str(store_path), "key_id": key_id, "label": keys[key_id]["label"]}


def _trusted_key_ids(trust_store_path: str | Path | None) -> set[str]:
    if not trust_store_path:
        return set()
    p = Path(trust_store_path)
    if not p.is_file():
        return set()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set()
    return set((data.get("keys") or {}).keys())


def build_sidecar_manifest(
    asset_path: str | Path,
    *,
    asset_id: str | None = None,
    fingerprint_id: str | None = None,
    version: int | None = None,
    title: str | None = None,
    do_not_train: bool = False,
) -> dict[str, Any]:
    p = Path(asset_path)
    mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    return {
        "schema": SIDECAR_SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "claim_generator": {"name": "AI-IP Shield", "version": "0.1.0"},
        "title": title or p.name,
        "asset": {
            "sha256": sha256_file(p),
            "format": mime,
            "asset_id": asset_id,
            # Do not expose the per-copy fingerprint in visible provenance metadata.
            # A one-way commitment lets a verifier correlate records without leaking the raw ID.
            "fingerprint_commitment": (hashlib.sha256(fingerprint_id.encode("utf-8")).hexdigest() if fingerprint_id else None),
            "version": version,
        },
        "actions": [{"action": "protected", "software": "AI-IP Shield"}],
        "training_policy": {
            "ai_inference": "notAllowed" if do_not_train else "unspecified",
            "ai_generative_training": "notAllowed" if do_not_train else "unspecified",
        },
    }


def sign_sidecar(
    asset_path: str | Path,
    private_key_path: str | Path,
    public_key_path: str | Path,
    *,
    sidecar_path: str | Path | None = None,
    asset_id: str | None = None,
    fingerprint_id: str | None = None,
    version: int | None = None,
    title: str | None = None,
    do_not_train: bool = False,
) -> ProvenanceResult:
    asset = Path(asset_path)
    private_key = load_private_key(private_key_path)
    public_key = load_public_key(public_key_path)
    if private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    ) != public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw):
        raise ValueError("private/public provenance keys do not match")
    manifest = build_sidecar_manifest(
        asset,
        asset_id=asset_id,
        fingerprint_id=fingerprint_id,
        version=version,
        title=title,
        do_not_train=do_not_train,
    )
    signature = private_key.sign(canonical_json_bytes(manifest))
    pub_pem = public_key.public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("utf-8")
    key_id = _public_key_id(public_key)
    envelope = {
        "manifest": manifest,
        "signature": {
            "alg": "Ed25519",
            "key_id": key_id,
            "public_key_pem": pub_pem,
            "value_b64": base64.b64encode(signature).decode("ascii"),
        },
    }
    out = Path(sidecar_path) if sidecar_path else default_sidecar_path(asset)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ProvenanceResult(
        backend="aip-sidecar-ed25519",
        status="SIGNED_UNVERIFIED_TRUST",
        present=True,
        signature_valid=True,
        asset_hash_match=True,
        trusted=False,
        signer_key_id=key_id,
        manifest_path=str(out),
        message="A signed provenance sidecar was created. Trust is established separately by the verifier trust store.",
        details={"training_policy": manifest["training_policy"]},
    )


def verify_sidecar(
    asset_path: str | Path,
    *,
    sidecar_path: str | Path | None = None,
    trust_store_path: str | Path | None = None,
) -> ProvenanceResult:
    asset = Path(asset_path)
    sidecar = Path(sidecar_path) if sidecar_path else default_sidecar_path(asset)
    if not sidecar.is_file():
        return ProvenanceResult(
            backend="aip-sidecar-ed25519", status="MISSING", present=False,
            signature_valid=None, asset_hash_match=None, trusted=False,
            signer_key_id=None, manifest_path=None,
            message="No AI-IP Shield provenance sidecar was found. Missing provenance is not proof of falsity.",
        )
    try:
        envelope = json.loads(sidecar.read_text(encoding="utf-8"))
        manifest = envelope["manifest"]
        sig = envelope["signature"]
        if manifest.get("schema") != SIDECAR_SCHEMA:
            raise ValueError("unsupported provenance sidecar schema")
        public_key = serialization.load_pem_public_key(sig["public_key_pem"].encode("utf-8"))
        if not isinstance(public_key, Ed25519PublicKey):
            raise TypeError("sidecar public key is not Ed25519")
        key_id = _public_key_id(public_key)
        if key_id != sig.get("key_id"):
            raise ValueError("sidecar key_id does not match embedded public key")
        signature = base64.b64decode(sig["value_b64"], validate=True)
        try:
            public_key.verify(signature, canonical_json_bytes(manifest))
            signature_valid = True
        except InvalidSignature:
            signature_valid = False
        expected_hash = (manifest.get("asset") or {}).get("sha256")
        hash_match = bool(expected_hash) and sha256_file(asset) == expected_hash
        trusted = key_id in _trusted_key_ids(trust_store_path)
        if not signature_valid:
            status = "INVALID_SIGNATURE"
            message = "The provenance envelope signature is invalid. Treat this provenance record as untrusted."
        elif not hash_match:
            status = "MODIFIED"
            message = "The provenance signature is valid, but the current asset bytes no longer match the signed asset hash."
        elif trusted:
            status = "VALID_TRUSTED"
            message = "The provenance signature is valid, the asset hash matches, and the signer key is trusted locally."
        else:
            status = "VALID_UNTRUSTED"
            message = "The provenance signature and asset hash are valid, but the signer key is not in the local trust store."
        return ProvenanceResult(
            backend="aip-sidecar-ed25519", status=status, present=True,
            signature_valid=signature_valid, asset_hash_match=hash_match, trusted=trusted,
            signer_key_id=key_id, manifest_path=str(sidecar), message=message,
            details={"training_policy": manifest.get("training_policy"), "title": manifest.get("title")},
        )
    except Exception as exc:
        return ProvenanceResult(
            backend="aip-sidecar-ed25519", status="INVALID", present=True,
            signature_valid=False, asset_hash_match=None, trusted=False,
            signer_key_id=None, manifest_path=str(sidecar),
            message=f"The provenance sidecar could not be validated: {type(exc).__name__}: {exc}",
        )


def build_c2pa_manifest(*, title: str, do_not_train: bool = False) -> dict[str, Any]:
    assertions: list[dict[str, Any]] = [
        {
            "label": "c2pa.actions",
            "data": {
                "actions": [
                    {
                        "action": "c2pa.created",
                        "digitalSourceType": "http://cv.iptc.org/newscodes/digitalsourcetype/digitalCreation",
                    }
                ]
            },
        }
    ]
    if do_not_train:
        assertions.append(
            {
                "label": "cawg.training-mining",
                "data": {
                    "entries": {
                        "cawg.ai_inference": {"use": "notAllowed"},
                        "cawg.ai_generative_training": {"use": "notAllowed"},
                    }
                },
            }
        )
    return {
        "claim_generator_info": [{"name": "AI-IP Shield", "version": "0.1.0"}],
        "title": title,
        "assertions": assertions,
    }


def c2pa_runtime_available() -> bool:
    try:
        import c2pa  # type: ignore  # noqa: F401
        return True
    except Exception:
        return False


def sign_c2pa(
    input_path: str | Path,
    output_path: str | Path,
    *,
    cert_path: str | Path,
    private_key_path: str | Path,
    title: str | None = None,
    do_not_train: bool = False,
    algorithm: str = "PS256",
    ta_url: bytes | None = None,
) -> ProvenanceResult:
    try:
        import c2pa  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "C2PA runtime is unavailable. Install c2pa-python or use provenance_mode='sidecar'."
        ) from exc
    source = Path(input_path)
    dest = Path(output_path)
    manifest = build_c2pa_manifest(title=title or source.name, do_not_train=do_not_train)
    certs = Path(cert_path).read_bytes()
    key = Path(private_key_path).read_bytes()
    # c2pa-python accepts a signing algorithm enum, str, or bytes. Passing the
    # normalized SDK algorithm name avoids coupling this adapter to enum-member
    # availability across c2pa-python versions.
    alg_value = algorithm.lower()
    signer_info = c2pa.C2paSignerInfo(
        alg=alg_value,
        sign_cert=certs,
        private_key=key,
        ta_url=ta_url,
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    with (
        c2pa.Context() as context,
        c2pa.Signer.from_info(signer_info) as signer,
        c2pa.Builder(manifest, context) as builder,
    ):
        builder.sign_file(str(source), str(dest), signer)
    result = verify_c2pa(dest)
    if result.status in {"MISSING", "INVALID", "INVALID_SIGNATURE"}:
        raise RuntimeError(f"C2PA verification failed immediately after signing: {result.message}")
    return result


def verify_c2pa(asset_path: str | Path) -> ProvenanceResult:
    try:
        import c2pa  # type: ignore
    except Exception:
        return ProvenanceResult(
            backend="c2pa", status="RUNTIME_UNAVAILABLE", present=False,
            signature_valid=None, asset_hash_match=None, trusted=False,
            signer_key_id=None, manifest_path=None,
            message="C2PA runtime is not installed, so embedded Content Credentials cannot be inspected here.",
        )
    try:
        # Keep remote fetching off during verification so a local check is deterministic.
        if hasattr(c2pa, "Context") and hasattr(c2pa.Context, "from_dict"):
            context = c2pa.Context.from_dict({"verify": {"remote_manifest_fetch": False}})
        else:
            context = c2pa.Context()
        with context:
            with c2pa.Reader(str(asset_path), context=context) as reader:
                state_obj = reader.get_validation_state() if hasattr(reader, "get_validation_state") else None
                active = reader.get_active_manifest() if hasattr(reader, "get_active_manifest") else None
                results = reader.get_validation_results() if hasattr(reader, "get_validation_results") else None
                embedded = reader.is_embedded() if hasattr(reader, "is_embedded") else bool(active)
        state = str(state_obj) if state_obj is not None else "Unknown"
        state_lower = state.strip().lower()
        if not embedded and not active:
            status = "MISSING"
            sig_valid = None
            trusted = False
            message = "No embedded C2PA manifest was found. Missing provenance is not proof of falsity."
        elif state_lower == "trusted":
            # C2PA ValidationState.Trusted means the manifest is valid AND the
            # active signing credential is trusted by the configured verifier.
            status = "VALID_TRUSTED"
            sig_valid = True
            trusted = True
            message = "The C2PA SDK reports a Trusted validation state: the manifest is valid and the active signature is trusted under the configured trust policy."
        elif state_lower == "valid":
            # C2PA ValidationState.Valid explicitly means validation found no
            # errors, but the active signature is NOT trusted. Do not promote it.
            status = "VALID_UNTRUSTED"
            sig_valid = True
            trusted = False
            message = "The C2PA SDK reports a Valid (not Trusted) state: the manifest validates, but the active signing credential is not trusted by this verifier."
        elif state_lower == "invalid":
            status = "INVALID"
            # Invalid can arise from binding/assertion/signature/trust-related
            # validation errors; do not claim the signature itself is bad unless
            # detailed status codes establish that fact.
            sig_valid = None
            trusted = False
            message = "The C2PA SDK reports an Invalid provenance state. Inspect validation results for the specific failure codes."
        else:
            status = "PRESENT_UNRESOLVED_TRUST"
            sig_valid = None
            trusted = False
            message = "A C2PA manifest is present, but the validation/trust state is not conclusively resolved in this verifier context."
        return ProvenanceResult(
            backend="c2pa", status=status, present=bool(embedded or active),
            signature_valid=sig_valid, asset_hash_match=None, trusted=trusted,
            signer_key_id=None, manifest_path="embedded:c2pa" if (embedded or active) else None,
            message=message,
            details={"validation_state": state, "validation_results": results, "active_manifest": active},
        )
    except Exception as exc:
        return ProvenanceResult(
            backend="c2pa", status="INVALID", present=False,
            signature_valid=False, asset_hash_match=None, trusted=False,
            signer_key_id=None, manifest_path=None,
            message=f"C2PA verification failed: {type(exc).__name__}: {exc}",
        )


def copy_then_sidecar_sign(
    input_path: str | Path,
    output_path: str | Path,
    *,
    private_key_path: str | Path,
    public_key_path: str | Path,
    asset_id: str | None,
    fingerprint_id: str | None,
    version: int | None,
    title: str | None,
    do_not_train: bool,
) -> ProvenanceResult:
    src, dst = Path(input_path), Path(output_path)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() != dst.resolve():
        shutil.copy2(src, dst)
    return sign_sidecar(
        dst, private_key_path, public_key_path,
        asset_id=asset_id, fingerprint_id=fingerprint_id, version=version,
        title=title, do_not_train=do_not_train,
    )
