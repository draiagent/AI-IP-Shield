from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .doctor import doctor_report
from .skill_manager import export_skill_zip, install_skill


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aipshield", description="AI-IP Shield v0.1")
    sub = p.add_subparsers(dest="cmd", required=True)

    protect = sub.add_parser("protect", help="fingerprint and invisibly watermark an image or PDF")
    protect.add_argument("input")
    protect.add_argument("output")
    protect.add_argument("--registry", default="data/registry.sqlite3")
    protect.add_argument("--engine", default="auto", help="auto selects blind-native for images and blind-native-pdf for PDFs")
    protect.add_argument("--version", type=int, default=1)
    protect.add_argument("--report", default=None)
    protect.add_argument("--provenance", choices=["none", "sidecar", "c2pa"], default="none")
    protect.add_argument("--signing-key", default=None, help="Ed25519 key for sidecar or private key for C2PA")
    protect.add_argument("--public-key", default=None, help="Ed25519 public key for sidecar provenance")
    protect.add_argument("--c2pa-cert", default=None, help="C2PA signing certificate chain PEM")
    protect.add_argument("--do-not-train", action="store_true")
    protect.add_argument("--title", default=None)
    protect.add_argument("--dpi", type=int, default=120, help="PDF raster render DPI")
    protect.add_argument("--pdf-image-format", choices=["jpeg", "png"], default="jpeg")
    protect.add_argument("--jpeg-quality", type=int, default=90)

    verify = sub.add_parser("verify", help="verify an image or PDF, resolve fingerprint, and inspect provenance")
    verify.add_argument("input")
    verify.add_argument("--registry", default="data/registry.sqlite3")
    verify.add_argument("--engine", default="auto", help="auto selects blind-native for images and blind-native-pdf for PDFs")
    verify.add_argument("--report-json", default=None)
    verify.add_argument("--report-md", default=None)
    verify.add_argument("--provenance", choices=["auto", "none", "sidecar", "c2pa"], default="auto")
    verify.add_argument("--sidecar", default=None)
    verify.add_argument("--trust-store", default=None)
    verify.add_argument("--dpi", type=int, default=120, help="PDF render DPI used during verification")

    attack = sub.add_parser("attack", help="run the v0.1 deterministic attack suite")
    attack.add_argument("protected")
    attack.add_argument("--registry", default="data/registry.sqlite3")
    attack.add_argument("--engine", default="blind-native")
    attack.add_argument("--output-dir", default="reports/attack-artifacts")
    attack.add_argument("--report-json", default="reports/attack-results.json")
    attack.add_argument("--report-csv", default="reports/attack-results.csv")

    keygen = sub.add_parser("provenance-keygen", help="generate a local Ed25519 provenance signing keypair")
    keygen.add_argument("--private-key", required=True)
    keygen.add_argument("--public-key", required=True)
    keygen.add_argument("--overwrite", action="store_true")

    trust = sub.add_parser("provenance-trust", help="add an Ed25519 public key to a local trust store")
    trust.add_argument("public_key")
    trust.add_argument("--trust-store", required=True)
    trust.add_argument("--label", default=None)

    psign = sub.add_parser("provenance-sign", help="sign a standalone asset with an AI-IP Shield provenance sidecar")
    psign.add_argument("asset")
    psign.add_argument("--signing-key", required=True)
    psign.add_argument("--public-key", required=True)
    psign.add_argument("--sidecar", default=None)
    psign.add_argument("--title", default=None)
    psign.add_argument("--do-not-train", action="store_true")

    pverify = sub.add_parser("provenance-verify", help="verify sidecar or C2PA provenance")
    pverify.add_argument("asset")
    pverify.add_argument("--backend", choices=["sidecar", "c2pa"], default="sidecar")
    pverify.add_argument("--sidecar", default=None)
    pverify.add_argument("--trust-store", default=None)

    sub.add_parser("c2pa-status", help="report whether c2pa-python is available")
    sub.add_parser("version", help="print AI-IP Shield version")
    sub.add_parser("doctor", help="check core dependencies, optional runtimes, and pinned engines")

    sinstall = sub.add_parser("skill-install", help="install the bundled Agent Skill for Codex and/or Claude Code")
    sinstall.add_argument("--host", choices=["codex", "claude", "both"], default="both")
    sinstall.add_argument("--scope", choices=["project", "user"], default="project")
    sinstall.add_argument("--root", default=None, help="project root for project-scoped installation; defaults to CWD")
    sinstall.add_argument("--force", action="store_true")

    sexport = sub.add_parser("skill-export", help="export the bundled Agent Skill as a portable ZIP")
    sexport.add_argument("--output", default="ai-ip-shield-skill.zip")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.cmd == "version":
        payload = {"version": __version__}
    elif args.cmd == "doctor":
        payload = doctor_report()
    elif args.cmd == "skill-install":
        payload = {"installed": [x.to_dict() for x in install_skill(args.host, args.scope, args.root, args.force)]}
    elif args.cmd == "skill-export":
        payload = {"skill_zip": export_skill_zip(args.output)}
    elif args.cmd == "protect":
        if Path(args.input).suffix.lower() == ".pdf":
            from .pdf_protect import protect_pdf
            engine_name = "blind-native-pdf" if args.engine == "auto" else args.engine
            result = protect_pdf(
                args.input, args.output, args.registry, engine_name, args.version, args.report,
                render_dpi=args.dpi, page_image_format=args.pdf_image_format, jpeg_quality=args.jpeg_quality,
                provenance_mode=args.provenance, signing_private_key=args.signing_key,
                signing_public_key=args.public_key, c2pa_cert=args.c2pa_cert,
                do_not_train=args.do_not_train, title=args.title,
            )
        else:
            from .protect import protect_image
            engine_name = "blind-native" if args.engine == "auto" else args.engine
            result = protect_image(
                args.input, args.output, args.registry, engine_name, args.version, args.report,
                provenance_mode=args.provenance, signing_private_key=args.signing_key,
                signing_public_key=args.public_key, c2pa_cert=args.c2pa_cert,
                do_not_train=args.do_not_train, title=args.title,
            )
        payload = result.to_dict()
    elif args.cmd == "verify":
        if Path(args.input).suffix.lower() == ".pdf":
            from .pdf_verify import verify_pdf
            engine_name = "blind-native-pdf" if args.engine == "auto" else args.engine
            result = verify_pdf(
                args.input, args.registry, engine_name, args.report_json, args.report_md,
                render_dpi=args.dpi, provenance_mode=args.provenance,
                provenance_sidecar=args.sidecar, trust_store=args.trust_store,
            )
        else:
            from .verify import verify_image
            engine_name = "blind-native" if args.engine == "auto" else args.engine
            result = verify_image(
                args.input, args.registry, engine_name, args.report_json, args.report_md,
                provenance_mode=args.provenance, provenance_sidecar=args.sidecar,
                trust_store=args.trust_store,
            )
        payload = result.to_dict()
    elif args.cmd == "attack":
        from .attack_lab import run_attack_suite, write_results
        from .registry import FingerprintRegistry
        from .utils.hash import sha256_file
        reg = FingerprintRegistry(args.registry)
        row = reg.get_by_protected_sha256(sha256_file(args.protected))
        if not row:
            raise SystemExit("protected file is not registered; cannot resolve expected token")
        results = run_attack_suite(args.protected, args.registry, row["watermark_token"], args.output_dir, engine_name=args.engine)
        write_results(results, args.report_json, args.report_csv)
        payload = {"cases": len(results), "report_json": args.report_json, "report_csv": args.report_csv}
    else:
        from .provenance import (
            c2pa_runtime_available,
            generate_signing_keypair,
            sign_sidecar,
            trust_public_key,
            verify_c2pa,
            verify_sidecar,
        )
        if args.cmd == "provenance-keygen":
            payload = generate_signing_keypair(args.private_key, args.public_key, overwrite=args.overwrite)
        elif args.cmd == "provenance-trust":
            payload = trust_public_key(args.public_key, args.trust_store, label=args.label)
        elif args.cmd == "provenance-sign":
            payload = sign_sidecar(
                args.asset, args.signing_key, args.public_key,
                sidecar_path=args.sidecar, title=args.title, do_not_train=args.do_not_train,
            ).to_dict()
        elif args.cmd == "provenance-verify":
            if args.backend == "c2pa":
                payload = verify_c2pa(args.asset).to_dict()
            else:
                payload = verify_sidecar(args.asset, sidecar_path=args.sidecar, trust_store_path=args.trust_store).to_dict()
        else:
            payload = {"c2pa_python_available": c2pa_runtime_available()}

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
