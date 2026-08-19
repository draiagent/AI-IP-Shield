from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import multiprocessing as mp
import os
# Prevent nested BLAS/OpenMP oversubscription when release tests spawn workers.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
import random
import shutil
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import cv2
cv2.setNumThreads(1)
import numpy as np
from PIL import Image, ImageDraw
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aipshield.attack_lab import AttackSpec, apply_attack, default_v01_attack_specs
from aipshield.engines import get_engine
from aipshield.fingerprint import generate_fingerprint
from aipshield.pixelseal_runtime import inspect_pixelseal_runtime
from aipshield.utils.hash import sha256_file

SEED = 20260819
REAL_IMAGE = Path('/mnt/data/0B559232-4B9F-4DD6-BD24-1605B912DE59.jpeg')

# Step 4 acceptance thresholds. Detection and recovery are intentionally separated.
GATES = {
    'ORIGINAL': {'detection': 1.00, 'recovery': 0.99},
    'T01-copy': {'detection': 1.00, 'recovery': 1.00},
    'T02-screenshot': {'detection': 0.90, 'recovery': 0.85},
    'T03-resize-75': {'detection': 0.95, 'recovery': 0.95},
    'T03-resize-50': {'detection': 0.95, 'recovery': 0.95},
    'T03-crop-10': {'detection': 0.90, 'recovery': 0.90},
    'T03-crop-20': {'detection': 0.90, 'recovery': 0.90},
    'T03-rotate-3': {'detection': 0.85, 'recovery': 0.85},
    'T04-jpeg-95': {'detection': 0.95, 'recovery': 0.95},
    'T04-jpeg-75': {'detection': 0.95, 'recovery': 0.95},
    'T04-jpeg-60': {'detection': 0.90, 'recovery': 0.90},
    'T05-conversion': {'detection': 0.85, 'recovery': 0.80},
    'TC-resize75-jpeg60': {'detection': 0.70, 'recovery': 0.70},
    'TC-crop10-jpeg75': {'detection': 0.70, 'recovery': 0.70},
}
FPR_MAX = 0.01


def _resize_cover(img: np.ndarray, w: int, h: int) -> np.ndarray:
    ih, iw = img.shape[:2]
    scale = max(w / iw, h / ih)
    nw, nh = max(w, round(iw * scale)), max(h, round(ih * scale))
    r = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
    x0, y0 = (nw - w) // 2, (nh - h) // 2
    return r[y0:y0+h, x0:x0+w].copy()


def _dims(i: int) -> tuple[int, int]:
    # Representative document/image geometries; sizes kept reasonable for release testing.
    options = [(640, 480), (768, 432), (540, 720), (600, 600), (864, 486)]
    return options[i % len(options)]


def make_golden_set(root: Path, n: int = 100) -> list[tuple[Path, str]]:
    if n % 5:
        raise ValueError('golden image count must be divisible by 5')
    root.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    real = cv2.imread(str(REAL_IMAGE)) if REAL_IMAGE.is_file() else None
    out: list[tuple[Path, str]] = []
    per = n // 5
    categories = ['photo', 'infographic', 'text-card', 'slide', 'low-texture']
    for ci, cat in enumerate(categories):
        for j in range(per):
            idx = ci * per + j
            w, h = _dims(idx)
            p = root / f'{idx:03d}-{cat}.png'
            if cat == 'photo':
                Y, X = np.mgrid[0:h, 0:w]
                phase = (j + 1) * 0.31
                img = np.stack([
                    55 + 155 * X / max(w, 1),
                    60 + 145 * Y / max(h, 1),
                    120 + 75 * np.sin((X + Y) / (38 + j % 17) + phase),
                ], axis=-1)
                img += rng.normal(0, 9 + j % 7, img.shape)
                img = np.clip(img, 0, 255).astype(np.uint8)
                cv2.circle(img, (int(w*(.2+.03*(j%10))), int(h*.35)), max(12, min(w,h)//9), (215,160,85), -1)
                cv2.rectangle(img, (int(w*.55), int(h*.55)), (int(w*.88), int(h*.82)), (65,125,175), -1)
            elif cat == 'infographic' and real is not None:
                img = _resize_cover(real, w, h)
                alpha = 0.03 + (j % 5) * 0.01
                overlay = np.zeros_like(img)
                overlay[:, :, j % 3] = 255
                img = cv2.addWeighted(img, 1-alpha, overlay, alpha, 0)
                cv2.putText(img, f'VAR {j+1:02d}', (max(8,w//30), max(28,h//16)), cv2.FONT_HERSHEY_SIMPLEX, .65, (20,20,20), 2, cv2.LINE_AA)
            elif cat == 'text-card':
                im = Image.new('RGB', (w,h), (242,246,249)); d = ImageDraw.Draw(im)
                d.text((max(12,w//30), max(10,h//30)), f'AI-IP Shield / Card {j+1:02d}', fill=(30,40,55))
                cols = 2 if w < h else 3
                rows = 3
                gap = max(8, w//50)
                cellw = (w - gap*(cols+1))//cols
                cellh = (h - max(45,h//8) - gap*(rows+1))//rows
                ybase = max(45,h//8)
                for k in range(cols*rows):
                    x = gap + (k%cols)*(cellw+gap); y = ybase + (k//cols)*(cellh+gap)
                    fill=(45+(17*k+j)%150, 90+(13*j)%120, 135+(11*k)%100)
                    d.rounded_rectangle((x,y,x+cellw,y+cellh), radius=max(5,min(cellw,cellh)//10), fill=fill)
                    d.text((x+8,y+8), f'M{k+1}', fill='white')
                img = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
            elif cat == 'slide':
                img = np.full((h,w,3), 250, dtype=np.uint8)
                head = max(45, h//9); img[:head] = (180-(j%3)*20, 105+(j%4)*15, 45+(j%5)*10)
                cv2.putText(img, f'Enterprise AI Slide {j+1:02d}', (max(10,w//30), int(head*.65)), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 2, cv2.LINE_AA)
                x1=max(10,w//25); y1=head+max(10,h//30); x2=int(w*.61); y2=h-max(12,h//25)
                cv2.rectangle(img,(x1,y1),(x2,y2),(105,110,120),2)
                for k in range(6):
                    yy=y1+20+k*max(18,(y2-y1-30)//7); cv2.line(img,(x1+20,yy),(x2-20,yy),(135,140,150),2)
                cv2.rectangle(img,(int(w*.66),y1),(w-max(12,w//30),int(h*.48)),(226,236,246),-1)
                cv2.rectangle(img,(int(w*.66),int(h*.54)),(w-max(12,w//30),y2),(237,230,244),-1)
            else:  # low texture
                base = 220 + (j % 20)
                img = np.full((h,w,3), base, dtype=np.uint8)
                cv2.rectangle(img,(int(w*.14),int(h*.18)),(int(w*.86),int(h*.82)),(min(252,base+5),)*3,-1)
                cv2.circle(img,(w//2,h//2),max(20,min(w,h)//7),(165+(j%12),)*3,2)
                cv2.putText(img, f'LOW {j+1:02d}', (int(w*.37),int(h*.52)), cv2.FONT_HERSHEY_SIMPLEX,.65,(70,70,70),2,cv2.LINE_AA)
            cv2.imwrite(str(p), img)
            out.append((p, cat))
    return out


def make_negative(path: Path, i: int):
    rng = np.random.default_rng(SEED + 100000 + i)
    w, h = _dims(i)
    mode = i % 5
    if mode == 0:
        img = rng.integers(0, 256, (h,w,3), dtype=np.uint8)
    elif mode == 1:
        Y, X = np.mgrid[0:h,0:w]
        img = np.stack([X*255/max(w,1), Y*255/max(h,1), (X+Y)*255/max(w+h,1)], -1).astype(np.uint8)
    elif mode == 2:
        img = np.full((h,w,3), 230, dtype=np.uint8)
        cv2.putText(img, f'NEGATIVE {i}', (max(10,w//15),h//2), cv2.FONT_HERSHEY_SIMPLEX,.7,(50,50,50),2,cv2.LINE_AA)
    elif mode == 3:
        img = np.full((h,w,3), 248, dtype=np.uint8)
        for _ in range(14):
            x1=int(rng.integers(0,max(1,w-20))); y1=int(rng.integers(0,max(1,h-20)))
            x2=min(w-1,x1+int(rng.integers(10,max(11,w//3)))); y2=min(h-1,y1+int(rng.integers(10,max(11,h//4))))
            cv2.rectangle(img,(x1,y1),(x2,y2),tuple(int(x) for x in rng.integers(0,255,3)),-1)
    else:
        img = rng.integers(180, 250, (h,w,3), dtype=np.uint8)
        img = cv2.GaussianBlur(img,(0,0),sigmaX=5.0)
    cv2.imwrite(str(path),img)


def _token_for(path: Path, idx: int) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    h.update(f'|{idx}|AI-IP-Shield-5.6.3'.encode())
    return h.hexdigest()[:16].upper()


def _quality(a: Path, b: Path) -> tuple[float,float]:
    x=cv2.imread(str(a)); y=cv2.imread(str(b))
    return (
        float(peak_signal_noise_ratio(x,y,data_range=255)),
        float(structural_similarity(x,y,channel_axis=2,data_range=255)),
    )


def _benchmark_one(args):
    engine_name, src_s, category, idx, specs_raw, work_s = args
    src=Path(src_s); work=Path(work_s); engine=get_engine(engine_name)
    token=_token_for(src,idx); protected=work/f'p-{idx:03d}.png'
    t0=time.perf_counter(); engine.embed(src,protected,token); embed_ms=(time.perf_counter()-t0)*1000
    psnr,ssim=_quality(src,protected)
    rows=[]
    # Original verification is an explicit gate.
    t0=time.perf_counter(); tok,ber=engine.evaluate_token(protected,token); runtime=(time.perf_counter()-t0)*1000
    rows.append({'source_index':idx,'category':category,'attack_id':'ORIGINAL','detected':tok is not None,'token_exact_match':tok==token,'ber':ber,'runtime_ms':runtime})
    case_dir=work/f'att-{idx:03d}'; case_dir.mkdir(exist_ok=True)
    for raw in specs_raw:
        spec=AttackSpec(raw['attack_id'],raw['name'],raw['parameters'])
        suffix='.jpg' if spec.name in {'jpeg','screenshot-sim','composite-resize-jpeg','composite-crop-jpeg'} else '.png'
        out=case_dir/f'{spec.attack_id}{suffix}'
        actual=apply_attack(protected,out,spec)
        t0=time.perf_counter(); tok,ber=engine.evaluate_token(actual,token); runtime=(time.perf_counter()-t0)*1000
        rows.append({'source_index':idx,'category':category,'attack_id':spec.attack_id,'detected':tok is not None,'token_exact_match':tok==token,'ber':ber,'runtime_ms':runtime})
    shutil.rmtree(case_dir,ignore_errors=True); protected.unlink(missing_ok=True)
    return {'idx':idx,'category':category,'embed_ms':embed_ms,'psnr':psnr,'ssim':ssim,'rows':rows}


def _negative_one(args):
    engine_name, path_s = args
    engine=get_engine(engine_name)
    t0=time.perf_counter(); token=engine.extract(path_s); runtime=(time.perf_counter()-t0)*1000
    return {'detected':token is not None,'runtime_ms':runtime,'token':token}


def _summarize(rows: list[dict]) -> dict:
    out={}
    for attack_id in GATES:
        rr=[r for r in rows if r['attack_id']==attack_id]
        if not rr: continue
        bers=[float(r['ber']) for r in rr if r.get('ber') is not None and not math.isnan(float(r['ber']))]
        out[attack_id]={
            'cases':len(rr),
            'detection_rate':sum(bool(r['detected']) for r in rr)/len(rr),
            'recovery_rate':sum(bool(r['token_exact_match']) for r in rr)/len(rr),
            'mean_ber':sum(bers)/len(bers) if bers else None,
            'mean_runtime_ms':sum(float(r['runtime_ms']) for r in rr)/len(rr),
        }
    return out


def _gate_eval(per_attack: dict, fpr: float) -> tuple[bool,list[dict]]:
    decisions=[]; ok=True
    for aid,req in GATES.items():
        got=per_attack.get(aid,{})
        d=float(got.get('detection_rate',0)); r=float(got.get('recovery_rate',0))
        passed=d>=req['detection'] and r>=req['recovery']; ok &= passed
        decisions.append({'gate':aid,'passed':passed,'detection':d,'detection_min':req['detection'],'recovery':r,'recovery_min':req['recovery']})
    fp_pass=fpr < FPR_MAX; ok &= fp_pass
    decisions.append({'gate':'FALSE_POSITIVE','passed':fp_pass,'fpr':fpr,'fpr_max_exclusive':FPR_MAX})
    return bool(ok),decisions


def collision_test(n: int = 100000) -> dict:
    seen_id=set(); seen_token=set(); dup_id=dup_token=0
    source='A'*64
    t0=time.perf_counter()
    for _ in range(n):
        fp=generate_fingerprint(source)
        dup_id += int(fp.fingerprint_id in seen_id); dup_token += int(fp.watermark_token in seen_token)
        seen_id.add(fp.fingerprint_id); seen_token.add(fp.watermark_token)
    return {'generated':n,'fingerprint_id_duplicates':dup_id,'watermark_token_duplicates':dup_token,'elapsed_seconds':time.perf_counter()-t0,'passed':dup_id==0 and dup_token==0}


def run_engine(engine_name: str, outdir: Path, golden_n: int, negative_n: int, workers: int) -> dict:
    runroot=outdir/f'work-{engine_name}'; shutil.rmtree(runroot,ignore_errors=True); runroot.mkdir(parents=True)
    sources=make_golden_set(runroot/'golden',golden_n)
    specs=[{'attack_id':s.attack_id,'name':s.name,'parameters':s.parameters} for s in default_v01_attack_specs()]
    tasks=[(engine_name,str(p),cat,i,specs,str(runroot)) for i,(p,cat) in enumerate(sources)]
    rows=[]; quality=[]; embeds=[]; t0=time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as ex:
        futs=[ex.submit(_benchmark_one,t) for t in tasks]
        for fut in as_completed(futs):
            r=fut.result(); rows.extend(r['rows']); quality.append((r['psnr'],r['ssim'])); embeds.append(r['embed_ms'])
    attack_seconds=time.perf_counter()-t0

    negdir=runroot/'negative'; negdir.mkdir(exist_ok=True)
    negpaths=[]
    for i in range(negative_n):
        p=negdir/f'n-{i:04d}.png'; make_negative(p,i); negpaths.append(p)
    t0=time.perf_counter(); neg=[]
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as ex:
        futs=[ex.submit(_negative_one,(engine_name,str(p))) for p in negpaths]
        for fut in as_completed(futs): neg.append(fut.result())
    negative_seconds=time.perf_counter()-t0
    fpr=sum(x['detected'] for x in neg)/negative_n if negative_n else 0.0
    per=_summarize(rows); passed, decisions=_gate_eval(per,fpr)

    with (outdir/f'{engine_name}-attack-results.csv').open('w',newline='',encoding='utf-8-sig') as f:
        fields=['source_index','category','attack_id','detected','token_exact_match','ber','runtime_ms']
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(sorted(rows,key=lambda r:(r['source_index'],r['attack_id'])))
    shutil.rmtree(runroot,ignore_errors=True)
    return {
        'engine_requested':engine_name,
        'golden_images':golden_n,
        'negative_controls':negative_n,
        'workers':workers,
        'false_positive_rate':fpr,
        'mean_psnr':sum(x[0] for x in quality)/len(quality),
        'mean_ssim':sum(x[1] for x in quality)/len(quality),
        'mean_embed_ms':sum(embeds)/len(embeds),
        'attack_elapsed_seconds':attack_seconds,
        'negative_elapsed_seconds':negative_seconds,
        'per_attack':per,
        'gate_decisions':decisions,
        'passed':passed,
    }


def main() -> int:
    ap=argparse.ArgumentParser(description='Step 5.6.3 Production Engine Final Gate')
    ap.add_argument('--golden',type=int,default=100)
    ap.add_argument('--negative',type=int,default=500)
    ap.add_argument('--workers',type=int,default=min(5,os.cpu_count() or 1))
    ap.add_argument('--engine',default='blind-native')
    ap.add_argument('--pixelseal-source')
    ap.add_argument('--pixelseal-checkpoint')
    ap.add_argument('--quick',action='store_true',help='20 golden / 50 negative engineering pre-gate')
    args=ap.parse_args()
    if args.quick:
        args.golden=20; args.negative=50
    if args.golden % 5: raise SystemExit('--golden must be divisible by 5')

    outdir=ROOT/'reports'/'step5.6.3'; outdir.mkdir(parents=True,exist_ok=True)
    runtime=inspect_pixelseal_runtime(args.pixelseal_source,args.pixelseal_checkpoint)
    collision=collision_test(100000)

    engine_result=run_engine(args.engine,outdir,args.golden,args.negative,args.workers)
    # PixelSeal can only be selected after a real-model run of this same gate.
    pixel_status='READY_FOR_REAL_GATE' if runtime.ready and runtime.checkpoint_looks_valid else 'BLOCKED_RUNTIME_OR_CHECKPOINT'
    if args.quick:
        selected = None
        decision = 'ENGINEERING_PASS_NOT_RELEASE' if engine_result['passed'] else 'ENGINEERING_FAIL'
    elif args.engine=='pixelseal' and engine_result['passed']:
        selected='pixelseal'; decision='GO'
    elif args.engine in {'blind','blind-native'} and engine_result['passed']:
        selected='blind'; decision='GO_V0.1_CPU_PRODUCTION'
    else:
        selected=None; decision='NO_GO'

    payload={
        'step':'5.6.3',
        'mode':'quick' if args.quick else 'final',
        'pixel_runtime':runtime.to_dict(),
        'pixel_status':pixel_status,
        'fingerprint_collision_test':collision,
        'engine_result':engine_result,
        'production_engine':selected,
        'decision':decision,
        'notes':[
            'PixelSeal is not credited with any robustness score unless the real checkpoint is loaded and this exact gate is run with --engine pixelseal.',
            'Blind may be selected only for V0.1 CPU production if every Step 4 gate passes on the 100/500 final dataset.',
        ],
    }
    (outdir/'FINAL-GATE.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

    md=['# Step 5.6.3 — Production Engine Final Gate','',f"**Decision:** `{decision}`",f"**Selected engine:** `{selected or 'NONE'}`",'',
        f"Golden images: {engine_result['golden_images']}",f"Negative controls: {engine_result['negative_controls']}",f"FPR: {engine_result['false_positive_rate']:.3%}",f"Mean PSNR: {engine_result['mean_psnr']:.2f} dB",f"Mean SSIM: {engine_result['mean_ssim']:.4f}",'',
        '| Gate | Detection | Min | Recovery | Min | Result |','|---|---:|---:|---:|---:|---|']
    for d in engine_result['gate_decisions']:
        if d['gate']=='FALSE_POSITIVE': continue
        md.append(f"| {d['gate']} | {d['detection']:.1%} | {d['detection_min']:.1%} | {d['recovery']:.1%} | {d['recovery_min']:.1%} | {'PASS' if d['passed'] else 'FAIL'} |")
    md += ['',f"False-positive gate: **{'PASS' if engine_result['false_positive_rate'] < FPR_MAX else 'FAIL'}** ({engine_result['false_positive_rate']:.3%} < {FPR_MAX:.1%})",f"Fingerprint collision gate: **{'PASS' if collision['passed'] else 'FAIL'}** ({collision['generated']:,} generated)",'',
        '## PixelSeal status','',f"`{pixel_status}`",'']
    if runtime.errors: md += [*(f'- {e}' for e in runtime.errors),'']
    md += ['No surrogate PixelSeal result is used. A real PixelSeal checkpoint must pass this exact runner before PixelSeal can replace the V0.1 engine.']
    (outdir/'PRODUCTION-ENGINE-DECISION.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps(payload,ensure_ascii=False,indent=2))
    return 0 if (decision.startswith('GO') or decision.startswith('ENGINEERING_PASS')) else 4


if __name__=='__main__':
    raise SystemExit(main())
