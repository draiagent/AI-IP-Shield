from __future__ import annotations
import hashlib
import secrets
import zlib
from .models import Fingerprint

PREFIX = "AIPS"


def _checksum(text: str) -> str:
    return f"{zlib.crc32(text.encode('utf-8')) & 0xFFFF:04X}"


def validate_fingerprint_id(value: str) -> bool:
    try:
        body, checksum = value.rsplit("-", 1)
    except ValueError:
        return False
    return checksum.upper() == _checksum(body)


def generate_fingerprint(source_sha256: str, version: int = 1) -> Fingerprint:
    asset_id = source_sha256[:10].upper()
    copy_id = secrets.token_hex(4).upper()
    nonce = secrets.token_hex(3).upper()
    body = f"{PREFIX}-{asset_id}-{copy_id}-V{version:02d}-{nonce}"
    fingerprint_id = f"{body}-{_checksum(body)}"
    # Watermark payload is a compact 64-bit registry lookup token, not PII.
    watermark_token = hashlib.sha256(fingerprint_id.encode("utf-8")).hexdigest()[:16].upper()
    return Fingerprint(
        fingerprint_id=fingerprint_id,
        watermark_token=watermark_token,
        asset_id=asset_id,
        copy_id=copy_id,
        version=version,
    )
