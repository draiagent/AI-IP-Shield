from __future__ import annotations

import json
import sqlite3
from pathlib import Path
import tempfile

import pytest
from PIL import Image, ImageDraw

from aipshield.protect import protect_image
from aipshield.verify import verify_image
from aipshield.provenance import (
    build_c2pa_manifest,
    default_sidecar_path,
    generate_signing_keypair,
    sign_sidecar,
    trust_public_key,
    verify_sidecar,
)
from aipshield.registry import FingerprintRegistry


def make_image(path: Path, size=(512, 512)):
    im = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(im)
    for i in range(0, size[0], 32):
        d.rectangle([i, 0, min(i+15, size[0]-1), size[1]-1], fill=(50+i%180, 100, 180))
    d.text((40, 220), "AI-IP Shield Step 5.7", fill="black")
    im.save(path)


def test_sidecar_signature_trust_and_do_not_train():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        asset = td / "asset.png"
        private = td / "signing.pem"
        public = td / "signing.pub.pem"
        trust = td / "trust.json"
        make_image(asset)
        key = generate_signing_keypair(private, public)
        trust_public_key(public, trust, label="test signer")
        created = sign_sidecar(asset, private, public, do_not_train=True)
        assert created.signer_key_id == key["key_id"]
        result = verify_sidecar(asset, trust_store_path=trust)
        assert result.status == "VALID_TRUSTED"
        assert result.signature_valid is True
        assert result.asset_hash_match is True
        assert result.trusted is True
        data = json.loads(default_sidecar_path(asset).read_text(encoding="utf-8"))
        assert data["manifest"]["training_policy"]["ai_generative_training"] == "notAllowed"


def test_sidecar_detects_asset_modification():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        asset = td / "asset.png"
        private = td / "signing.pem"
        public = td / "signing.pub.pem"
        make_image(asset)
        generate_signing_keypair(private, public)
        sign_sidecar(asset, private, public)
        raw = bytearray(asset.read_bytes())
        raw[-12] ^= 1
        asset.write_bytes(raw)
        result = verify_sidecar(asset)
        assert result.signature_valid is True
        assert result.asset_hash_match is False
        assert result.status == "MODIFIED"


def test_sidecar_detects_manifest_tamper():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        asset = td / "asset.png"
        private = td / "signing.pem"
        public = td / "signing.pub.pem"
        make_image(asset)
        generate_signing_keypair(private, public)
        sign_sidecar(asset, private, public)
        sidecar = default_sidecar_path(asset)
        data = json.loads(sidecar.read_text(encoding="utf-8"))
        data["manifest"]["title"] = "tampered title"
        sidecar.write_text(json.dumps(data), encoding="utf-8")
        result = verify_sidecar(asset)
        assert result.status == "INVALID_SIGNATURE"
        assert result.signature_valid is False


def test_integrated_protect_verify_trusted_provenance():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        src = td / "input.png"
        out = td / "protected.png"
        db = td / "registry.sqlite3"
        private = td / "signing.pem"
        public = td / "signing.pub.pem"
        trust = td / "trust.json"
        make_image(src)
        generate_signing_keypair(private, public)
        trust_public_key(public, trust)
        p = protect_image(
            str(src), str(out), str(db),
            provenance_mode="sidecar",
            signing_private_key=str(private),
            signing_public_key=str(public),
            do_not_train=True,
        )
        assert p.provenance and p.provenance["backend"] == "aip-sidecar-ed25519"
        v = verify_image(str(out), str(db), trust_store=str(trust))
        assert v.detected and v.registry_match and v.exact_protected_hash_match
        assert v.provenance_status == "VALID_TRUSTED"
        assert v.provenance_trusted is True
        assert v.evidence_level == "CRYPTOGRAPHICALLY_VERIFIED"


def test_integrated_protect_verify_untrusted_signer_is_not_promoted_to_trusted():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        src = td / "input.png"
        out = td / "protected.png"
        db = td / "registry.sqlite3"
        private = td / "signing.pem"
        public = td / "signing.pub.pem"
        make_image(src)
        generate_signing_keypair(private, public)
        protect_image(
            str(src), str(out), str(db),
            provenance_mode="sidecar",
            signing_private_key=str(private),
            signing_public_key=str(public),
        )
        v = verify_image(str(out), str(db))
        assert v.provenance_status == "VALID_UNTRUSTED"
        assert v.provenance_trusted is False
        assert v.evidence_level == "SIGNED_SOURCE_MATCH_UNTRUSTED"


def test_c2pa_manifest_has_standard_training_mining_assertion():
    manifest = build_c2pa_manifest(title="asset.png", do_not_train=True)
    labels = {a["label"] for a in manifest["assertions"]}
    assert "c2pa.actions" in labels
    assert "cawg.training-mining" in labels
    training = next(a for a in manifest["assertions"] if a["label"] == "cawg.training-mining")
    assert training["data"]["entries"]["cawg.ai_generative_training"]["use"] == "notAllowed"


def test_registry_migrates_step56_database_without_data_loss():
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "old.sqlite3"
        con = sqlite3.connect(db)
        con.executescript("""
        CREATE TABLE fingerprints (
            watermark_token TEXT PRIMARY KEY,
            fingerprint_id TEXT NOT NULL UNIQUE,
            asset_id TEXT NOT NULL,
            copy_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            source_sha256 TEXT NOT NULL,
            protected_sha256 TEXT NOT NULL,
            source_path TEXT,
            protected_path TEXT,
            engine TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
        );
        INSERT INTO fingerprints VALUES ('ABCDEF0123456789','FP1','A1','C1',1,'s','p','src','dst','blind','now','active');
        """)
        con.commit(); con.close()
        reg = FingerprintRegistry(db)
        row = reg.get_by_token("ABCDEF0123456789")
        assert row is not None and row["fingerprint_id"] == "FP1"
        assert "provenance_backend" in row
        assert row["provenance_backend"] is None
