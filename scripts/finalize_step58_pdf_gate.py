from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'reports'/'step5.8'
files=sorted(out.glob('PDF-GATE-BATCH-*.json'))
if len(files) < 4:
    raise SystemExit(f'need 4 batch reports, found {len(files)}')
batches=[json.loads(p.read_text()) for p in files]
cases=[r for b in batches for r in b['cases']]
if len(cases) != 20:
    raise SystemExit(f'expected 20 PDF cases, got {len(cases)}')

def rate(field): return sum(bool(r[field]) for r in cases)/len(cases)
metrics={
 'exact_pdf_detection_rate':rate('exact_detected'),
 'exact_pdf_all_page_rate':sum(float(r['exact_page_rate']) for r in cases)/len(cases),
 'pdf_to_image_trace_rate':rate('pdf_to_image'),
 'screenshot_trace_rate':rate('screenshot'),
 'print_to_pdf_trace_rate':rate('print_to_pdf'),
 'print_to_pdf_mean_page_detection':sum(float(r['print_to_pdf_page_rate']) for r in cases)/len(cases),
 'single_page_pdf_trace_rate':rate('single_page_pdf'),
 'page_geometry_preservation_rate':rate('geometry_preserved'),
 'negative_pdf_page_fpr':sum(b['metrics']['negative_pdf_page_fpr']*b['documents'] for b in batches)/sum(b['documents'] for b in batches),
 'mixed_source_conflict_detected_rate':sum(bool(b['metrics']['mixed_source_conflict_detected']) for b in batches)/len(batches),
 'mean_protect_seconds':sum(float(r['protect_seconds']) for r in cases)/len(cases),
 'mean_size_ratio':sum(r['protected_bytes']/r['source_bytes'] for r in cases)/len(cases),
 'aggregate_size_ratio':sum(r['protected_bytes'] for r in cases)/sum(r['source_bytes'] for r in cases),
 'mean_source_mb':sum(r['source_bytes'] for r in cases)/len(cases)/1_000_000,
 'mean_protected_mb':sum(r['protected_bytes'] for r in cases)/len(cases)/1_000_000,
 'searchable_text_preserved_rate':sum(r['protected_text_chars']>0 for r in cases)/len(cases),
}
gates={
 'exact_pdf':metrics['exact_pdf_detection_rate']>=1.0 and metrics['exact_pdf_all_page_rate']>=0.99,
 'pdf_to_image':metrics['pdf_to_image_trace_rate']>=0.85,
 'screenshot':metrics['screenshot_trace_rate']>=0.85,
 'print_to_pdf':metrics['print_to_pdf_trace_rate']>=0.85,
 'single_page_pdf':metrics['single_page_pdf_trace_rate']>=0.85,
 'geometry':metrics['page_geometry_preservation_rate']>=1.0,
 'false_positive':metrics['negative_pdf_page_fpr']<0.01,
 'mixed_source':metrics['mixed_source_conflict_detected_rate']>=1.0,
}
result={
 'step':'5.8','decision':'GO_STEP5.8' if all(gates.values()) else 'NO_GO',
 'documents':20,'pages_per_document':5,'protected_pages':100,
 'categories':sorted({r['category'] for r in cases}),
 'engine':'blind-watermark-native-pdf-adaptive','render_dpi':batches[0]['render_dpi'],
 'metrics':metrics,'gates':gates,
 'known_limitation':'V0.1 PDF protection is raster-visual: selectable text, accessibility tags, forms, hyperlinks and some annotations are not preserved.',
 'batch_reports':[p.name for p in files],
 'cases':cases,
}
(out/'PDF-GATE.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
md=['# Step 5.8 - PDF Adapter Final Gate','',f"**Decision:** `{result['decision']}`",'',
    '- Documents: **20**','- Pages per document: **5**','- Protected pages: **100**','- Negative PDF page controls: **20**','',
    '| Gate | Actual | Threshold | Result |','|---|---:|---:|---|',
    f"| Exact protected PDF | {metrics['exact_pdf_detection_rate']:.1%} | 100% | {'PASS' if gates['exact_pdf'] else 'FAIL'} |",
    f"| All protected pages readable | {metrics['exact_pdf_all_page_rate']:.1%} | >=99% | {'PASS' if gates['exact_pdf'] else 'FAIL'} |",
    f"| PDF -> image trace | {metrics['pdf_to_image_trace_rate']:.1%} | >=85% | {'PASS' if gates['pdf_to_image'] else 'FAIL'} |",
    f"| PDF page screenshot trace | {metrics['screenshot_trace_rate']:.1%} | >=85% | {'PASS' if gates['screenshot'] else 'FAIL'} |",
    f"| Print / raster re-export PDF | {metrics['print_to_pdf_trace_rate']:.1%} | >=85% | {'PASS' if gates['print_to_pdf'] else 'FAIL'} |",
    f"| Single-page PDF extraction | {metrics['single_page_pdf_trace_rate']:.1%} | >=85% | {'PASS' if gates['single_page_pdf'] else 'FAIL'} |",
    f"| Page geometry | {metrics['page_geometry_preservation_rate']:.1%} | 100% | {'PASS' if gates['geometry'] else 'FAIL'} |",
    f"| Negative PDF page FPR | {metrics['negative_pdf_page_fpr']:.1%} | <1% | {'PASS' if gates['false_positive'] else 'FAIL'} |",
    f"| Mixed-source PDF detection | {metrics['mixed_source_conflict_detected_rate']:.1%} | 100% | {'PASS' if gates['mixed_source'] else 'FAIL'} |",
    '', '## Engineering metrics','',
    f"- Print-to-PDF mean page detection: **{metrics['print_to_pdf_mean_page_detection']:.1%}**",
    f"- Mean protect time per 5-page PDF: **{metrics['mean_protect_seconds']:.2f}s**",
    f"- Aggregate protected/source size ratio: **{metrics['aggregate_size_ratio']:.1f}x**",
    f"- Mean source PDF size: **{metrics['mean_source_mb']:.2f} MB**",
    f"- Mean protected PDF size: **{metrics['mean_protected_mb']:.2f} MB**",
    f"- Searchable text preserved: **{metrics['searchable_text_preserved_rate']:.1%}**",
    '', '## Known V0.1 limitation','', result['known_limitation'], '',
    '> Passing this gate means the visual watermark/fingerprint survived the defined PDF conversion tests. It is not DRM, a legal ownership judgment, or a claim that PDF structure is preserved.']
(out/'PDF-GATE.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(0 if result['decision']=='GO_STEP5.8' else 4)
