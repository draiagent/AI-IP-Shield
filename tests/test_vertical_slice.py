from __future__ import annotations
from pathlib import Path
import tempfile
from PIL import Image, ImageDraw

from aipshield.fingerprint import generate_fingerprint, validate_fingerprint_id
from aipshield.protect import protect_image
from aipshield.verify import verify_image


def make_image(path: Path, size=(512, 512)):
    im = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(im)
    for i in range(0, size[0], 32):
        d.rectangle([i, 0, min(i+15, size[0]-1), size[1]-1], fill=(50+i%180, 100, 180))
    d.text((40, 220), "AI-IP Shield Vertical Slice", fill="black")
    im.save(path)


def test_fingerprint_shape_and_checksum():
    fp = generate_fingerprint("a" * 64)
    assert validate_fingerprint_id(fp.fingerprint_id)
    assert len(fp.watermark_token) == 16


def test_protect_verify_roundtrip():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        src = td / "input.png"
        out = td / "protected.png"
        db = td / "registry.sqlite3"
        make_image(src)
        p = protect_image(str(src), str(out), str(db))
        v = verify_image(str(out), str(db))
        assert v.detected
        assert v.registry_match
        assert v.fingerprint_id == p.fingerprint.fingerprint_id
        assert v.exact_protected_hash_match


def test_unknown_image_not_detected():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        src = td / "plain.png"
        db = td / "registry.sqlite3"
        make_image(src)
        v = verify_image(str(src), str(db))
        assert not v.detected
        assert not v.registry_match
