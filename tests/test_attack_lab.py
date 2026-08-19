from pathlib import Path
import tempfile
from PIL import Image, ImageDraw

from aipshield.protect import protect_image
from aipshield.attack_lab import AttackSpec, apply_attack, run_attack_case


def make_image(path: Path, size=(512, 512)):
    im = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(im)
    for i in range(0, size[0], 24):
        d.rectangle([i, 0, min(i+10, size[0]-1), size[1]-1], fill=(60+i%170, 90, 180))
    d.text((40, 220), "AI-IP Shield Attack Lab", fill="black")
    im.save(path)


def test_copy_attack_roundtrip():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        src, protected = td/'src.png', td/'protected.png'
        db = td/'registry.sqlite3'
        make_image(src)
        p = protect_image(str(src), str(protected), str(db))
        r = run_attack_case(protected, db, p.fingerprint.watermark_token, td/'attacks', AttackSpec('T01-copy','copy',{}))
        assert r.detected
        assert r.registry_match
        assert r.token_exact_match
        assert r.ber == 0.0


def test_jpeg_attack_is_reproducible():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        src, protected = td/'src.png', td/'protected.png'
        db = td/'registry.sqlite3'
        make_image(src)
        p = protect_image(str(src), str(protected), str(db))
        spec = AttackSpec('T04-jpeg-95','jpeg',{'quality':95})
        out = apply_attack(protected, td/'attack.jpg', spec)
        assert Path(out).exists()
        r = run_attack_case(protected, db, p.fingerprint.watermark_token, td/'attacks', spec)
        assert r.ber is not None
        assert 0.0 <= r.ber <= 1.0
