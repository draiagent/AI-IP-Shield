from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import time
from pathlib import Path

import cv2
import fitz
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen.canvas import Canvas

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))

from aipshield.adapters.pdf import render_pdf_pages, raster_roundtrip_pdf, extract_pdf_page
from aipshield.attack_lab import AttackSpec, apply_attack
from aipshield.pdf_protect import protect_pdf
from aipshield.pdf_verify import verify_pdf
from aipshield.verify import verify_image

REAL_IMAGE = Path('/mnt/data/0B559232-4B9F-4DD6-BD24-1605B912DE59.jpeg')


def make_pdf(path: Path, category: str, doc_index: int, pages: int = 5) -> Path:
    c = Canvas(str(path), pagesize=landscape(letter))
    w, h = landscape(letter)
    c.setTitle(f"AI-IP Shield Step 5.8 {category} {doc_index}")
    for i in range(pages):
        c.setFont("Helvetica-Bold", 20)
        c.drawString(34, h - 48, f"Step 5.8 PDF Gate — {category} — {doc_index:02d}/{i+1:02d}")
        if category == "text-heavy":
            c.setFont("Helvetica", 9.5)
            for r in range(18):
                c.drawString(42, h - 82 - r * 22, f"{r+1:02d}. AI-IP Shield protects document identity, source tracking, provenance and verification evidence.")
        elif category == "image-heavy" and REAL_IMAGE.is_file():
            c.drawImage(str(REAL_IMAGE), 42, 55, width=w - 84, height=h - 130, preserveAspectRatio=True, anchor='c')
        elif category == "table":
            c.setFont("Helvetica", 9)
            x0, y0, tw, th = 45, 70, w - 90, h - 150
            rows, cols = 12, 6
            for r in range(rows + 1):
                y = y0 + r * th / rows
                c.line(x0, y, x0 + tw, y)
            for col in range(cols + 1):
                x = x0 + col * tw / cols
                c.line(x, y0, x, y0 + th)
            for r in range(rows):
                for col in range(cols):
                    c.drawString(x0 + col * tw / cols + 4, y0 + r * th / rows + 5, f"{doc_index}-{i+1}-{r+1}-{col+1}")
        elif category == "slide":
            colors = [(.12,.45,.68), (.18,.60,.52), (.55,.31,.68), (.80,.42,.20)]
            for k in range(4):
                x = 45 + (k % 2) * (w * .43)
                y = 70 + (k // 2) * (h * .34)
                rr,gg,bb = colors[(k + doc_index + i) % len(colors)]
                c.setFillColorRGB(rr,gg,bb)
                c.roundRect(x, y, w*.36, h*.27, 12, fill=1, stroke=0)
                c.setFillColorRGB(1,1,1)
                c.setFont("Helvetica-Bold", 15)
                c.drawString(x+14, y+h*.20, f"MODULE {k+1}")
                c.setFont("Helvetica", 10)
                c.drawString(x+14, y+h*.13, "Protect / Verify / Evidence")
            c.setFillColorRGB(0,0,0)
        else:  # low-texture
            c.setFillColorRGB(.96,.97,.98)
            c.rect(45, 70, w-90, h-150, fill=1, stroke=0)
            c.setFillColorRGB(.65,.67,.70)
            c.circle(w/2, h/2, 48 + i*3, fill=0, stroke=1)
            c.setFont("Helvetica", 15)
            c.drawCentredString(w/2, h/2-4, f"LOW TEXTURE {doc_index:02d}-{i+1:02d}")
            c.setFillColorRGB(0,0,0)
        c.showPage()
    c.save()
    return path


def page_geometry(pdf: Path):
    d=fitz.open(str(pdf))
    try:
        return [(round(p.rect.width,2), round(p.rect.height,2)) for p in d]
    finally:
        d.close()


def protected_text_chars(pdf: Path) -> int:
    d=fitz.open(str(pdf))
    try:
        return sum(len(p.get_text("text") or "") for p in d)
    finally:
        d.close()


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--docs',type=int,default=20)
    ap.add_argument('--pages',type=int,default=5)
    ap.add_argument('--dpi',type=int,default=120)
    ap.add_argument('--offset',type=int,default=0,help='document index offset for resumable batches')
    args=ap.parse_args()
    if args.docs % 5:
        raise SystemExit('--docs must be divisible by 5')
    outdir=ROOT/'reports'/'step5.8'; outdir.mkdir(parents=True,exist_ok=True)
    categories=['text-heavy','image-heavy','table','slide','low-texture']
    rows=[]; t0=time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='aips-step58-') as td:
        work=Path(td); db=work/'registry.sqlite3'
        sources=[]
        per=args.docs//5
        for ci,cat in enumerate(categories):
            for j in range(per):
                idx=args.offset+ci*per+j
                src=make_pdf(work/f'source-{idx:02d}.pdf',cat,idx+1,args.pages)
                sources.append((idx,cat,src))

        protected_paths=[]
        for idx,cat,src in sources:
            protected=work/f'protected-{idx:02d}.pdf'
            started=time.perf_counter()
            pr=protect_pdf(str(src),str(protected),str(db),render_dpi=args.dpi,jpeg_quality=90)
            protect_seconds=time.perf_counter()-started
            exact=verify_pdf(str(protected),str(db),render_dpi=args.dpi)
            rendered,_=render_pdf_pages(protected,work/f'render-{idx:02d}',dpi=args.dpi)
            page_img=verify_image(str(rendered[0]),str(db))
            shot=work/f'screenshot-{idx:02d}.jpg'
            apply_attack(rendered[0],shot,AttackSpec('T02-screenshot','screenshot-sim',{'scale':0.9,'quality':85}))
            shot_v=verify_image(str(shot),str(db))
            rt=work/f'roundtrip-{idx:02d}.pdf'
            raster_roundtrip_pdf(protected,rt,dpi=100,jpeg_quality=85)
            rt_v=verify_pdf(str(rt),str(db),render_dpi=args.dpi)
            one=work/f'one-{idx:02d}.pdf'
            extract_pdf_page(protected,one,page_index=min(2,args.pages-1))
            one_v=verify_pdf(str(one),str(db),render_dpi=args.dpi)
            row={
                'index':idx,'category':cat,'pages':args.pages,
                'protect_seconds':protect_seconds,
                'exact_detected':exact.detected,'exact_page_rate':exact.page_detection_rate,'exact_hash':exact.exact_protected_hash_match,
                'pdf_to_image':page_img.registry_match,
                'screenshot':shot_v.registry_match,
                'print_to_pdf':rt_v.registry_match,
                'print_to_pdf_page_rate':rt_v.page_detection_rate,
                'single_page_pdf':one_v.registry_match,
                'geometry_preserved':page_geometry(src)==page_geometry(protected),
                'source_text_chars':protected_text_chars(src),
                'protected_text_chars':protected_text_chars(protected),
                'source_bytes':src.stat().st_size,
                'protected_bytes':protected.stat().st_size,
                'fingerprint_id':pr.fingerprint.fingerprint_id,
            }
            rows.append(row)
            protected_paths.append(protected)
            shutil.rmtree(work/f'render-{idx:02d}',ignore_errors=True)
            shot.unlink(missing_ok=True); rt.unlink(missing_ok=True); one.unlink(missing_ok=True)

        # Negative controls: render page 1 of each unprotected PDF and verify as an image.
        negative_detected=0
        for idx,cat,src in sources:
            pages,_=render_pdf_pages(src,work/f'neg-{idx:02d}',dpi=args.dpi)
            nv=verify_image(str(pages[0]),str(db))
            negative_detected += int(nv.detected)
            shutil.rmtree(work/f'neg-{idx:02d}',ignore_errors=True)

        # Mixed-source assembly gate.
        mixed_path=work/'mixed.pdf'
        m=fitz.open(); a=fitz.open(str(protected_paths[0])); b=fitz.open(str(protected_paths[-1]))
        try:
            m.insert_pdf(a,from_page=0,to_page=0); m.insert_pdf(b,from_page=0,to_page=0); m.save(str(mixed_path))
        finally:
            a.close(); b.close(); m.close()
        mixed=verify_pdf(str(mixed_path),str(db),render_dpi=args.dpi)

    def rate(field): return sum(bool(r[field]) for r in rows)/len(rows)
    result={
        'step':'5.8','batch_offset':args.offset,'documents':len(rows),'pages_per_document':args.pages,'protected_pages':len(rows)*args.pages,
        'engine':'blind-watermark-native-pdf-adaptive','render_dpi':args.dpi,
        'metrics':{
            'exact_pdf_detection_rate':rate('exact_detected'),
            'exact_pdf_all_page_rate':sum(r['exact_page_rate'] for r in rows)/len(rows),
            'pdf_to_image_trace_rate':rate('pdf_to_image'),
            'screenshot_trace_rate':rate('screenshot'),
            'print_to_pdf_trace_rate':rate('print_to_pdf'),
            'print_to_pdf_mean_page_detection':sum(r['print_to_pdf_page_rate'] for r in rows)/len(rows),
            'single_page_pdf_trace_rate':rate('single_page_pdf'),
            'page_geometry_preservation_rate':rate('geometry_preserved'),
            'negative_pdf_page_fpr':negative_detected/len(rows),
            'mixed_source_conflict_detected':mixed.mixed_watermark_tokens and mixed.evidence_level=='CONFLICTING_EVIDENCE',
            'mean_protect_seconds':sum(r['protect_seconds'] for r in rows)/len(rows),
            'mean_size_ratio':sum(r['protected_bytes']/r['source_bytes'] for r in rows)/len(rows),
            'searchable_text_preserved_rate':sum(r['protected_text_chars']>0 for r in rows)/len(rows),
        },
        'known_limitation':'V0.1 PDF protection is raster-visual: selectable text, accessibility tags, forms, hyperlinks and some annotations are not preserved.',
        'cases':rows,
    }
    m=result['metrics']
    gates={
        'exact_pdf': m['exact_pdf_detection_rate']>=1.0 and m['exact_pdf_all_page_rate']>=0.99,
        'pdf_to_image':m['pdf_to_image_trace_rate']>=0.85,
        'screenshot':m['screenshot_trace_rate']>=0.85,
        'print_to_pdf':m['print_to_pdf_trace_rate']>=0.85,
        'single_page_pdf':m['single_page_pdf_trace_rate']>=0.85,
        'geometry':m['page_geometry_preservation_rate']>=1.0,
        'false_positive':m['negative_pdf_page_fpr']<0.01,
        'mixed_source':bool(m['mixed_source_conflict_detected']),
    }
    result['gates']=gates; result['decision']='GO_STEP5.8' if all(gates.values()) else 'NO_GO'; result['elapsed_seconds']=time.perf_counter()-t0
    suffix=f'BATCH-{args.offset:02d}'
    (outdir/f'PDF-GATE-{suffix}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    md=['# Step 5.8 — PDF Adapter Gate','',f"**Decision:** `{result['decision']}`",'',f"Documents: **{len(rows)}**  ",f"Pages/document: **{args.pages}**  ",f"Protected pages: **{len(rows)*args.pages}**",'', '| Gate | Actual | Threshold | Result |','|---|---:|---:|---|',
        f"| Exact protected PDF | {m['exact_pdf_detection_rate']:.1%} | 100% | {'PASS' if gates['exact_pdf'] else 'FAIL'} |",
        f"| PDF → image trace | {m['pdf_to_image_trace_rate']:.1%} | ≥85% | {'PASS' if gates['pdf_to_image'] else 'FAIL'} |",
        f"| PDF page screenshot trace | {m['screenshot_trace_rate']:.1%} | ≥85% | {'PASS' if gates['screenshot'] else 'FAIL'} |",
        f"| Print / raster re-export PDF | {m['print_to_pdf_trace_rate']:.1%} | ≥85% | {'PASS' if gates['print_to_pdf'] else 'FAIL'} |",
        f"| Single-page PDF extraction | {m['single_page_pdf_trace_rate']:.1%} | ≥85% | {'PASS' if gates['single_page_pdf'] else 'FAIL'} |",
        f"| Page geometry | {m['page_geometry_preservation_rate']:.1%} | 100% | {'PASS' if gates['geometry'] else 'FAIL'} |",
        f"| Negative PDF page FPR | {m['negative_pdf_page_fpr']:.1%} | <1% | {'PASS' if gates['false_positive'] else 'FAIL'} |",
        f"| Mixed-source PDF detection | {bool(m['mixed_source_conflict_detected'])} | True | {'PASS' if gates['mixed_source'] else 'FAIL'} |",
        '', '## Engineering metrics','',f"- Print-to-PDF mean page detection: **{m['print_to_pdf_mean_page_detection']:.1%}**",f"- Mean protect time/document: **{m['mean_protect_seconds']:.2f}s**",f"- Mean protected/source size ratio: **{m['mean_size_ratio']:.1f}×**",f"- Searchable text preserved: **{m['searchable_text_preserved_rate']:.1%}**",'', '## V0.1 limitation','',result['known_limitation'],'', '> The PDF gate validates visual-trace robustness. It does not claim native-structure preservation or DRM behavior.']
    (outdir/f'PDF-GATE-{suffix}.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['decision']=='GO_STEP5.8' else 4

if __name__=='__main__':
    raise SystemExit(main())
