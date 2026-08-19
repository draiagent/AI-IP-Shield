from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def write_json_report(data: dict[str, Any], path: str | Path) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(p)


def write_markdown_verification(data: dict[str, Any], path: str | Path) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AI-IP Shield Verification Report",
        "",
        f"- **Input:** `{data.get('input_path')}`",
        f"- **Engine:** `{data.get('engine')}`",
        f"- **Watermark:** {'DETECTED' if data.get('detected') else 'NOT DETECTED'}",
        f"- **Watermark Token:** `{data.get('watermark_token') or 'N/A'}`",
        f"- **Fingerprint:** `{data.get('fingerprint_id') or 'N/A'}`",
        f"- **Registry Match:** `{data.get('registry_match')}`",
        f"- **Exact Protected Hash Match:** `{data.get('exact_protected_hash_match')}`",
        f"- **Provenance Backend:** `{data.get('provenance_backend') or 'N/A'}`",
        f"- **Provenance Status:** `{data.get('provenance_status')}`",
        f"- **Provenance Signature Valid:** `{data.get('provenance_signature_valid')}`",
        f"- **Provenance Asset Hash Match:** `{data.get('provenance_asset_hash_match')}`",
        f"- **Provenance Trusted:** `{data.get('provenance_trusted')}`",
        f"- **Signer Key ID:** `{data.get('provenance_signer_key_id') or 'N/A'}`",
        f"- **Evidence Level:** **{data.get('evidence_level')}**",
        f"- **Message:** {data.get('message')}",
    ]
    if data.get("provenance_message"):
        lines += [f"- **Provenance Note:** {data.get('provenance_message')}"]
    lines += [
        "",
        "> Missing provenance is not proof of falsity. This report is technical evidence, not a legal conclusion.",
    ]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


def write_markdown_pdf_verification(data: dict[str, Any], path: str | Path) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AI-IP Shield PDF Verification Report",
        "",
        f"- **Input:** `{data.get('input_path')}`",
        f"- **Engine:** `{data.get('engine')}`",
        f"- **Pages:** `{data.get('page_count')}`",
        f"- **Pages Detected:** `{data.get('pages_detected')}`",
        f"- **Page Detection Rate:** `{float(data.get('page_detection_rate') or 0):.1%}`",
        f"- **Consensus Token:** `{data.get('consensus_watermark_token') or 'N/A'}`",
        f"- **Mixed Tokens:** `{data.get('mixed_watermark_tokens')}`",
        f"- **Fingerprint:** `{data.get('fingerprint_id') or 'N/A'}`",
        f"- **Registry Match:** `{data.get('registry_match')}`",
        f"- **Exact Protected Hash Match:** `{data.get('exact_protected_hash_match')}`",
        f"- **Provenance Backend:** `{data.get('provenance_backend') or 'N/A'}`",
        f"- **Provenance Status:** `{data.get('provenance_status')}`",
        f"- **Provenance Trusted:** `{data.get('provenance_trusted')}`",
        f"- **Evidence Level:** **{data.get('evidence_level')}**",
        f"- **Message:** {data.get('message')}",
        "",
        "## Page Results",
        "",
        "| Page | Detected | Registry Match | Token |",
        "|---:|---|---|---|",
    ]
    for r in data.get("page_results") or []:
        lines.append(f"| {r.get('page_number')} | {r.get('detected')} | {r.get('registry_match')} | `{r.get('watermark_token') or 'N/A'}` |")
    lines += [
        "",
        "> Missing provenance is not proof of falsity. PDF V0.1 uses a rasterized visual protection mode and does not preserve selectable text/accessibility structure.",
    ]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)
