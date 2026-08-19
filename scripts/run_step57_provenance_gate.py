from __future__ import annotations

import json
import shutil
import tempfile
import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aipshield.protect import protect_image
from aipshield.verify import verify_image
from aipshield.provenance import (
    build_c2pa_manifest,
    c2pa_runtime_available,
    default_sidecar_path,
    generate_signing_keypair,
    trust_public_key,
    verify_sidecar,
)

OUT = ROOT / "reports" / "step5.7"


def make_image(path: Path):
    im = Image.new("RGB", (640, 480), "white")
    d = ImageDraw.Draw(im)
    for i in range(0, 640, 40):
        d.rectangle((i, 0, min(i+20,639), 479), fill=(40+i%180, 100, 180))
    d.text((40, 210), "AI-IP Shield Step 5.7 Provenance Gate", fill="black")
    im.save(path)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aips-step57-") as td_s:
        td = Path(td_s)
        src = td / "input.png"
        protected = td / "protected.png"
        db = td / "registry.sqlite3"
        priv = td / "signing.pem"
        pub = td / "signing.pub.pem"
        trust = td / "trust.json"
        make_image(src)
        key = generate_signing_keypair(priv, pub)
        trust_public_key(pub, trust, label="Step 5.7 Gate Signer")
        p = protect_image(
            str(src), str(protected), str(db),
            provenance_mode="sidecar",
            signing_private_key=str(priv),
            signing_public_key=str(pub),
            do_not_train=True,
        )
        v = verify_image(str(protected), str(db), trust_store=str(trust))
        sidecar_data = json.loads(default_sidecar_path(protected).read_text(encoding="utf-8"))

        # Missing provenance must not become an accusation of falsity.
        copied = td / "copied.png"
        shutil.copy2(protected, copied)
        missing = verify_image(str(copied), str(db), trust_store=str(trust))

        # Preserve provenance but modify one pixel; this should become MODIFIED.
        modified = td / "modified.png"
        shutil.copy2(protected, modified)
        shutil.copy2(default_sidecar_path(protected), default_sidecar_path(modified))
        im = Image.open(modified).convert("RGB")
        px = im.load(); r,g,b = px[2,2]; px[2,2] = ((r+1)%256,g,b); im.save(modified)
        modified_v = verify_image(str(modified), str(db), trust_store=str(trust))

        # Tamper the signed manifest itself; signature verification must fail.
        tampered = td / "tampered.png"
        shutil.copy2(protected, tampered)
        shutil.copy2(default_sidecar_path(protected), default_sidecar_path(tampered))
        env = json.loads(default_sidecar_path(tampered).read_text(encoding="utf-8"))
        env["manifest"]["title"] = "tampered"
        default_sidecar_path(tampered).write_text(json.dumps(env), encoding="utf-8")
        tampered_p = verify_sidecar(tampered, trust_store_path=trust)

        c2pa_manifest = build_c2pa_manifest(title="asset.png", do_not_train=True)
        labels = {a["label"] for a in c2pa_manifest["assertions"]}
        training = next(a for a in c2pa_manifest["assertions"] if a["label"] == "cawg.training-mining")

        gates = {
            "key_id_created": bool(key["key_id"]),
            "trusted_provenance": v.evidence_level == "CRYPTOGRAPHICALLY_VERIFIED" and v.provenance_status == "VALID_TRUSTED",
            "do_not_train_sidecar": sidecar_data["manifest"]["training_policy"]["ai_generative_training"] == "notAllowed",
            "privacy_no_raw_fingerprint": "fingerprint_id" not in sidecar_data["manifest"]["asset"] and bool(sidecar_data["manifest"]["asset"].get("fingerprint_commitment")),
            "missing_not_fake": missing.provenance_status == "MISSING" and missing.registry_match and missing.evidence_level == "REGISTERED_EXACT_MATCH",
            "modified_detected": modified_v.provenance_status == "MODIFIED" and modified_v.evidence_level == "STRONG_SOURCE_ASSOCIATION_MODIFIED",
            "manifest_tamper_detected": tampered_p.status == "INVALID_SIGNATURE",
            "c2pa_actions_contract": "c2pa.actions" in labels,
            "c2pa_training_mining_contract": "cawg.training-mining" in labels and training["data"]["entries"]["cawg.ai_generative_training"]["use"] == "notAllowed",
        }
        core_pass = all(gates.values())
        payload = {
            "step": "5.7",
            "decision": "PASS_WITH_C2PA_RUNTIME_PENDING" if core_pass else "NO_GO",
            "provenance_core_gate": "PASS" if core_pass else "FAIL",
            "c2pa_adapter_contract": "PASS",
            "c2pa_native_runtime": "AVAILABLE" if c2pa_runtime_available() else "BLOCKED_NOT_INSTALLED",
            "gates": gates,
            "trusted_verification": v.to_dict(),
            "missing_provenance_verification": missing.to_dict(),
            "modified_verification": modified_v.to_dict(),
            "tampered_provenance": tampered_p.to_dict(),
        }
        (OUT / "PROVENANCE-GATE.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if core_pass else 4


if __name__ == "__main__":
    raise SystemExit(main())
