from __future__ import annotations

import shutil
import sys
from pathlib import Path
from types import SimpleNamespace
import tempfile

from PIL import Image

from aipshield.provenance import sign_c2pa, verify_c2pa


class CM:
    def __enter__(self): return self
    def __exit__(self, *args): return False


class FakeContext(CM):
    @classmethod
    def from_dict(cls, config):
        obj=cls(); obj.config=config; return obj


class FakeSigner(CM):
    @classmethod
    def from_info(cls, info):
        obj=cls(); obj.info=info; return obj


class FakeSignerInfo:
    def __init__(self, alg, sign_cert, private_key, ta_url):
        self.alg=alg; self.sign_cert=sign_cert; self.private_key=private_key; self.ta_url=ta_url


class FakeBuilder(CM):
    last_signer = None
    def __init__(self, manifest, context):
        self.manifest=manifest; self.context=context
    def sign_file(self, source, dest, signer=None):
        FakeBuilder.last_signer = signer
        shutil.copy2(source,dest)
        return b'manifest'


class FakeReaderTrusted(CM):
    def __init__(self, path, context=None): self.path=path
    def get_validation_state(self): return 'Trusted'
    def get_validation_results(self): return {'ok': True}
    def get_active_manifest(self): return {'title': 'fake'}
    def is_embedded(self): return True


class FakeReaderValid(FakeReaderTrusted):
    def get_validation_state(self): return 'Valid'


class FakeReaderInvalid(FakeReaderTrusted):
    def get_validation_state(self): return 'Invalid'
    def get_validation_results(self): return {'activeManifest': {'failure': [{'code': 'assertion.dataHash.mismatch'}]}}


def fake_module(reader_cls):
    return SimpleNamespace(
        Context=FakeContext,
        Signer=FakeSigner,
        C2paSignerInfo=FakeSignerInfo,
        C2paSigningAlg=SimpleNamespace(PS256=3),
        Builder=FakeBuilder,
        Reader=reader_cls,
    )


def test_c2pa_adapter_uses_current_signing_contract(monkeypatch):
    fake=fake_module(FakeReaderTrusted)
    monkeypatch.setitem(sys.modules,'c2pa',fake)
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        src=td/'source.png'; out=td/'signed.png'; cert=td/'cert.pem'; key=td/'key.pem'
        Image.new('RGB',(64,64),'white').save(src)
        cert.write_bytes(b'CERT'); key.write_bytes(b'KEY')
        result=sign_c2pa(src,out,cert_path=cert,private_key_path=key,do_not_train=True)
        assert out.is_file()
        assert result.backend=='c2pa'
        assert result.status=='VALID_TRUSTED'
        assert result.present is True
        # The current c2pa-python C2paSignerInfo accepts string algorithms.
        assert FakeBuilder.last_signer.info.alg == 'ps256'


def test_c2pa_valid_state_is_not_mislabeled_trusted(monkeypatch):
    monkeypatch.setitem(sys.modules,'c2pa',fake_module(FakeReaderValid))
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'asset.jpg'; p.write_bytes(b'x')
        result=verify_c2pa(p)
        assert result.status == 'VALID_UNTRUSTED'
        assert result.signature_valid is True
        assert result.trusted is False


def test_c2pa_invalid_state_does_not_overclaim_bad_signature(monkeypatch):
    monkeypatch.setitem(sys.modules,'c2pa',fake_module(FakeReaderInvalid))
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'asset.jpg'; p.write_bytes(b'x')
        result=verify_c2pa(p)
        assert result.status == 'INVALID'
        assert result.signature_valid is None
        assert result.trusted is False
