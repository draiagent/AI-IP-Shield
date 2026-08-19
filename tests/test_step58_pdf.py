from __future__ import annotations

from pathlib import Path

import fitz
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen.canvas import Canvas

from aipshield.adapters.pdf import render_pdf_pages, raster_roundtrip_pdf, extract_pdf_page
from aipshield.pdf_protect import protect_pdf
from aipshield.pdf_verify import verify_pdf
from aipshield.verify import verify_image
from aipshield.provenance import generate_signing_keypair, trust_public_key


def make_pdf(path: Path, *, pages: int = 3, seed: int = 1) -> Path:
    c = Canvas(str(path), pagesize=landscape(letter))
    w, h = landscape(letter)
    for i in range(pages):
        c.setFont("Helvetica-Bold", 22)
        c.drawString(36, h - 55, f"AI-IP Shield PDF {seed} / Page {i+1}")
        c.setFont("Helvetica", 11)
        for j in range(10):
            c.drawString(45, h - 95 - j * 22, f"Row {j+1:02d} — fingerprint / watermark / provenance / verification")
        c.setFillColorRGB((seed % 7) / 8, ((i+2) % 7) / 8, ((seed+i+4) % 7) / 8)
        c.rect(w * 0.62, h * 0.25, w * 0.30, h * 0.48, fill=1, stroke=0)
        c.setFillColorRGB(0, 0, 0)
        c.circle(w * 0.78, h * 0.5, 42 + (i * 5), stroke=1, fill=0)
        c.showPage()
    c.setTitle(f"AI-IP Shield test {seed}")
    c.save()
    return path


def test_pdf_protect_verify_and_page_trace(tmp_path: Path):
    src = make_pdf(tmp_path / "source.pdf", pages=3)
    out = tmp_path / "protected.pdf"
    db = tmp_path / "registry.sqlite3"
    r = protect_pdf(str(src), str(out), str(db), render_dpi=120, jpeg_quality=95)
    assert r.page_count == 3
    assert r.rasterized is True
    v = verify_pdf(str(out), str(db), render_dpi=120)
    assert v.detected is True
    assert v.registry_match is True
    assert v.exact_protected_hash_match is True
    assert v.pages_detected == 3
    assert v.page_detection_rate == 1.0

    pages, _ = render_pdf_pages(out, tmp_path / "rendered", dpi=120)
    iv = verify_image(str(pages[0]), str(db))
    assert iv.detected is True
    assert iv.registry_match is True
    assert iv.fingerprint_id == r.fingerprint.fingerprint_id


def test_pdf_roundtrip_and_single_page_survive(tmp_path: Path):
    src = make_pdf(tmp_path / "source.pdf", pages=4, seed=2)
    out = tmp_path / "protected.pdf"
    db = tmp_path / "registry.sqlite3"
    protect_pdf(str(src), str(out), str(db), render_dpi=120, jpeg_quality=95)

    rt = tmp_path / "print-to-pdf.pdf"
    raster_roundtrip_pdf(out, rt, dpi=100, jpeg_quality=85)
    v = verify_pdf(str(rt), str(db), render_dpi=120)
    assert v.detected is True
    assert v.registry_match is True
    assert v.exact_protected_hash_match is False
    assert v.page_detection_rate >= 0.75

    one = tmp_path / "one-page.pdf"
    extract_pdf_page(out, one, page_index=2)
    sv = verify_pdf(str(one), str(db), render_dpi=120)
    assert sv.detected is True
    assert sv.registry_match is True
    assert sv.page_count == 1


def test_pdf_sidecar_provenance_trusted(tmp_path: Path):
    src = make_pdf(tmp_path / "source.pdf", pages=2, seed=3)
    out = tmp_path / "protected.pdf"
    db = tmp_path / "registry.sqlite3"
    priv = tmp_path / "private.pem"
    pub = tmp_path / "public.pem"
    trust = tmp_path / "trust.json"
    generate_signing_keypair(priv, pub)
    trust_public_key(pub, trust, label="test")
    protect_pdf(
        str(src), str(out), str(db), render_dpi=120,
        provenance_mode="sidecar", signing_private_key=str(priv), signing_public_key=str(pub),
        do_not_train=True,
    )
    v = verify_pdf(str(out), str(db), render_dpi=120, trust_store=str(trust))
    assert v.provenance_status == "VALID_TRUSTED"
    assert v.provenance_trusted is True
    assert v.evidence_level == "CRYPTOGRAPHICALLY_VERIFIED"


def test_mixed_pdf_detects_conflicting_page_tokens(tmp_path: Path):
    db = tmp_path / "registry.sqlite3"
    p1 = tmp_path / "p1.pdf"
    p2 = tmp_path / "p2.pdf"
    protect_pdf(str(make_pdf(tmp_path / "s1.pdf", pages=2, seed=11)), str(p1), str(db), render_dpi=120)
    protect_pdf(str(make_pdf(tmp_path / "s2.pdf", pages=2, seed=22)), str(p2), str(db), render_dpi=120)

    mixed = fitz.open()
    d1, d2 = fitz.open(str(p1)), fitz.open(str(p2))
    try:
        mixed.insert_pdf(d1, from_page=0, to_page=0)
        mixed.insert_pdf(d2, from_page=0, to_page=0)
        mixed_path = tmp_path / "mixed.pdf"
        mixed.save(str(mixed_path))
    finally:
        d1.close(); d2.close(); mixed.close()
    v = verify_pdf(str(mixed_path), str(db), render_dpi=120)
    assert v.mixed_watermark_tokens is True
    assert v.evidence_level == "CONFLICTING_EVIDENCE"


def test_encrypted_pdf_fails_closed(tmp_path: Path):
    src = make_pdf(tmp_path / "source.pdf", pages=1, seed=4)
    doc = fitz.open(str(src))
    encrypted = tmp_path / "encrypted.pdf"
    doc.save(
        str(encrypted),
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner",
        user_pw="secret",
        permissions=fitz.PDF_PERM_ACCESSIBILITY,
    )
    doc.close()
    try:
        protect_pdf(str(encrypted), str(tmp_path / "out.pdf"), str(tmp_path / "r.sqlite3"), render_dpi=120)
    except ValueError as exc:
        assert "password-protected" in str(exc)
    else:
        raise AssertionError("encrypted PDF must fail closed")
