from __future__ import annotations
import argparse, csv, json, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from scripts.run_step563_final_gate import (
    make_golden_set, make_negative, _benchmark_one, _negative_one, _summarize,
    _gate_eval, collision_test, GATES, FPR_MAX
)
from aipshield.attack_lab import default_v01_attack_specs
from aipshield.pixelseal_runtime import inspect_pixelseal_runtime

OUT=ROOT/'reports'/'step5.6.3'
CHUNKS=OUT/'chunks'
GOLDEN=OUT/'golden-set'
NEGROOT=OUT/'negative-set'


def get_or_make_golden(total:int):
    if total % 5:
        raise ValueError('golden image count must be divisible by 5')
    cats=['photo','infographic','text-card','slide','low-texture']
    per=total//5
    expected=[]
    for ci,cat in enumerate(cats):
        for j in range(per):
            idx=ci*per+j
            expected.append((GOLDEN/f'{idx:03d}-{cat}.png',cat))
    if all(p.is_file() for p,_ in expected):
        return expected
    return make_golden_set(GOLDEN,total)


def run_attacks(start:int,count:int,total:int,engine:str):
    CHUNKS.mkdir(parents=True,exist_ok=True); GOLDEN.mkdir(parents=True,exist_ok=True)
    sources=get_or_make_golden(total)
    specs=[{'attack_id':s.attack_id,'name':s.name,'parameters':s.parameters} for s in default_v01_attack_specs()]
    rows=[]; quality=[]; embeds=[]; t0=time.perf_counter()
    work=OUT/f'chunk-work-att-{start:03d}-{start+count-1:03d}'; work.mkdir(parents=True,exist_ok=True)
    for i in range(start,min(total,start+count)):
        p,cat=sources[i]
        r=_benchmark_one((engine,str(p),cat,i,specs,str(work)))
        rows.extend(r['rows']); quality.append([r['psnr'],r['ssim']]); embeds.append(r['embed_ms'])
        print(f'attack source {i+1}/{total} done', flush=True)
    payload={
        'phase':'attacks','engine':engine,'start':start,'count':len(quality),'total':total,
        'elapsed_seconds':time.perf_counter()-t0,'quality':quality,'embed_ms':embeds,'rows':rows
    }
    path=CHUNKS/f'attacks-{start:03d}-{start+len(quality)-1:03d}.json'
    path.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
    print(path)


def run_negatives(start:int,count:int,total:int,engine:str):
    CHUNKS.mkdir(parents=True,exist_ok=True); NEGROOT.mkdir(parents=True,exist_ok=True)
    results=[]; t0=time.perf_counter()
    end=min(total,start+count)
    for i in range(start,end):
        p=NEGROOT/f'neg-{i:04d}.png'
        if not p.is_file(): make_negative(p,i)
        r=_negative_one((engine,str(p))); r['index']=i; results.append(r)
        if (i-start+1)%10==0: print(f'negative {i+1}/{total} done',flush=True)
    payload={'phase':'negatives','engine':engine,'start':start,'count':len(results),'total':total,
             'elapsed_seconds':time.perf_counter()-t0,'results':results}
    path=CHUNKS/f'negatives-{start:04d}-{end-1:04d}.json'
    path.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
    print(path)


def finalize(engine:str,total_golden:int,total_negative:int):
    OUT.mkdir(parents=True,exist_ok=True)
    attack_files=sorted(CHUNKS.glob('attacks-*.json')); neg_files=sorted(CHUNKS.glob('negatives-*.json'))
    rows=[]; quality=[]; embeds=[]; attack_indices=set(); neg_indices=set(); attack_elapsed=0; neg_elapsed=0; fp=0
    for p in attack_files:
        d=json.loads(p.read_text());
        if d.get('engine')!=engine: continue
        rows.extend(d['rows']); quality.extend(d['quality']); embeds.extend(d['embed_ms']); attack_elapsed += d['elapsed_seconds']
        attack_indices.update(r['source_index'] for r in d['rows'] if r['attack_id']=='ORIGINAL')
    for p in neg_files:
        d=json.loads(p.read_text());
        if d.get('engine')!=engine: continue
        neg_elapsed += d['elapsed_seconds']
        for r in d['results']:
            if r['index'] in neg_indices: continue
            neg_indices.add(r['index']); fp += int(r['detected'])
    missing_attack=sorted(set(range(total_golden))-attack_indices)
    missing_neg=sorted(set(range(total_negative))-neg_indices)
    if missing_attack or missing_neg:
        raise SystemExit(f'incomplete chunks: attacks missing={len(missing_attack)}, negatives missing={len(missing_neg)}')
    fpr=fp/total_negative
    per=_summarize(rows); passed,decisions=_gate_eval(per,fpr)
    collision=collision_test(100000)
    runtime=inspect_pixelseal_runtime()
    decision='GO_V0.1_CPU_PRODUCTION' if passed and collision['passed'] else 'NO_GO'
    selected=engine if decision.startswith('GO') else None
    result={
        'step':'5.6.3','mode':'final','dataset_complete':True,'engine_result':{
            'engine_requested':engine,'golden_images':total_golden,'negative_controls':total_negative,
            'false_positive_rate':fpr,'mean_psnr':sum(x[0] for x in quality)/len(quality),
            'mean_ssim':sum(x[1] for x in quality)/len(quality),'mean_embed_ms':sum(embeds)/len(embeds),
            'attack_elapsed_seconds':attack_elapsed,'negative_elapsed_seconds':neg_elapsed,
            'per_attack':per,'gate_decisions':decisions,'passed':passed,
        },
        'fingerprint_collision_test':collision,'pixel_runtime':runtime.to_dict(),
        'pixel_status':'READY_FOR_REAL_GATE' if runtime.ready and runtime.checkpoint_looks_valid else 'BLOCKED_RUNTIME_OR_CHECKPOINT',
        'production_engine':selected,'decision':decision,
        'notes':['Final decision uses 100 golden images and 500 negative controls.',
                 'PixelSeal receives no robustness score without the real official checkpoint.']
    }
    (OUT/'FINAL-GATE.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (OUT/f'{engine}-attack-results.csv').open('w',newline='',encoding='utf-8-sig') as f:
        fields=['source_index','category','attack_id','detected','token_exact_match','ber','runtime_ms']; w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(sorted(rows,key=lambda r:(r['source_index'],r['attack_id'])))
    md=['# Step 5.6.3 — Production Engine Final Gate','',f'**Decision:** `{decision}`',f'**Selected engine:** `{selected or "NONE"}`','',
        f'Golden images: **{total_golden}**',f'Negative controls: **{total_negative}**',f'FPR: **{fpr:.3%}**',
        f'Mean PSNR: **{result["engine_result"]["mean_psnr"]:.2f} dB**',f'Mean SSIM: **{result["engine_result"]["mean_ssim"]:.4f}**','',
        '| Gate | Detection | Min | Recovery | Min | Result |','|---|---:|---:|---:|---:|---|']
    for d in decisions:
        if d['gate']=='FALSE_POSITIVE': continue
        md.append(f'| {d["gate"]} | {d["detection"]:.1%} | {d["detection_min"]:.1%} | {d["recovery"]:.1%} | {d["recovery_min"]:.1%} | {"PASS" if d["passed"] else "FAIL"} |')
    md += ['',f'False-positive gate: **{"PASS" if fpr < FPR_MAX else "FAIL"}** ({fpr:.3%} < {FPR_MAX:.1%})',
           f'Fingerprint collision gate: **{"PASS" if collision["passed"] else "FAIL"}** ({collision["generated"]:,} generated)','',
           '## PixelSeal status','',f'`{result["pixel_status"]}`','']
    if runtime.errors: md += [*(f'- {e}' for e in runtime.errors),'']
    md += ['No surrogate PixelSeal result is used.']
    (OUT/'PRODUCTION-ENGINE-DECISION.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('phase',choices=['attacks','negatives','finalize']); ap.add_argument('--start',type=int,default=0); ap.add_argument('--count',type=int,default=20); ap.add_argument('--golden',type=int,default=100); ap.add_argument('--negative',type=int,default=500); ap.add_argument('--engine',default='blind-native'); a=ap.parse_args()
    if a.phase=='attacks': run_attacks(a.start,a.count,a.golden,a.engine)
    elif a.phase=='negatives': run_negatives(a.start,a.count,a.negative,a.engine)
    else: finalize(a.engine,a.golden,a.negative)

if __name__=='__main__': main()
