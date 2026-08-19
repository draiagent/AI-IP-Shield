from __future__ import annotations
from pathlib import Path
import csv
import json
import random
import shutil
import sys
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aipshield.protect import protect_image
from aipshield.verify import verify_image
from aipshield.attack_lab import default_v01_attack_specs, run_attack_case

SEED = 20260818
random.seed(SEED)
np.random.seed(SEED)


def fit_cover(img: np.ndarray, size=(768, 512)) -> np.ndarray:
    tw, th = size
    h, w = img.shape[:2]
    s = max(tw / w, th / h)
    nw, nh = int(round(w*s)), int(round(h*s))
    r = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
    x = (nw - tw)//2; y=(nh-th)//2
    return r[y:y+th, x:x+tw].copy()


def generate_sources(out_dir: Path, real_image: Path, n_per_class=5):
    out_dir.mkdir(parents=True, exist_ok=True)
    real = cv2.imread(str(real_image))
    if real is None:
        raise RuntimeError(f"real image missing: {real_image}")
    paths=[]
    # 1. Real infographic-derived variants.
    base=fit_cover(real)
    for i in range(n_per_class):
        img=base.copy()
        if i:
            alpha=1.0 + (i-2)*0.02
            beta=(i-2)*2
            img=cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
        p=out_dir/f"real_{i:02d}.png"; cv2.imwrite(str(p),img); paths.append((p,"real-infographic"))
    # 2. Photo-like gradient/noise.
    h,w=512,768
    Y,X=np.mgrid[0:h,0:w]
    for i in range(n_per_class):
        rng=np.random.default_rng(SEED+i)
        ch1=(80+120*X/w + 25*np.sin(Y/27+i)).astype(np.float32)
        ch2=(60+150*Y/h + 20*np.cos(X/41+i)).astype(np.float32)
        ch3=(120+90*np.sin((X+Y)/(60+i*3))).astype(np.float32)
        img=np.stack([ch1,ch2,ch3],axis=-1)
        img += rng.normal(0,12+i*2,img.shape)
        img=np.clip(img,0,255).astype(np.uint8)
        cv2.circle(img,(150+i*90,180+i*25),70+i*5,(220,180,80),-1)
        p=out_dir/f"photo_{i:02d}.png"; cv2.imwrite(str(p),img); paths.append((p,"photo-like"))
    # 3. Text-heavy infographic cards.
    for i in range(n_per_class):
        im=Image.new('RGB',(768,512),(245,248-i*3,250))
        d=ImageDraw.Draw(im)
        for j in range(6):
            x=30+(j%3)*245; y=90+(j//3)*185
            fill=(60+i*18,120+j*10,180-j*12)
            d.rounded_rectangle((x,y,x+215,y+145),radius=18,fill=fill)
            d.text((x+18,y+20),f"AI-IP {i+1}-{j+1}",fill='white')
            d.text((x+18,y+55),"Protect Verify\nAttack Evidence",fill='white')
        d.text((30,25),f"AI-IP Shield Benchmark Card {i+1}",fill=(20,35,50))
        p=out_dir/f"card_{i:02d}.png"; im.save(p); paths.append((p,"text-card"))
    # 4. Low texture / difficult scenes.
    for i in range(n_per_class):
        img=np.full((512,768,3), 220-i*8, dtype=np.uint8)
        cv2.rectangle(img,(80+i*20,100),(680-i*15,410),(225-i*5,230-i*4,235-i*3),-1)
        cv2.circle(img,(384,256),70+i*10,(190+i*6,195+i*4,205+i*2),2)
        cv2.putText(img,f"LOW TEXTURE {i+1}",(240,270),cv2.FONT_HERSHEY_SIMPLEX,0.8,(80,80,80),2,cv2.LINE_AA)
        p=out_dir/f"flat_{i:02d}.png"; cv2.imwrite(str(p),img); paths.append((p,"low-texture"))
    return paths


def generate_negative(path: Path, i: int):
    rng=np.random.default_rng(SEED+1000+i)
    h,w=384,512
    mode=i%5
    if mode==0:
        img=rng.integers(0,256,(h,w,3),dtype=np.uint8)
    elif mode==1:
        base=np.full((h,w,3), 180+(i%50), dtype=np.uint8)
        cv2.putText(base,f"NEG {i}",(40,200),cv2.FONT_HERSHEY_SIMPLEX,1.2,(20,20,20),2,cv2.LINE_AA); img=base
    elif mode==2:
        Y,X=np.mgrid[0:h,0:w]
        img=np.stack([(X*255/w),(Y*255/h),((X+Y)*255/(w+h))],axis=-1).astype(np.uint8)
    elif mode==3:
        img=np.full((h,w,3),255,dtype=np.uint8)
        for _ in range(20):
            x1=int(rng.integers(0,w)); y1=int(rng.integers(0,h)); x2=int(rng.integers(x1,w)); y2=int(rng.integers(y1,h))
            cv2.rectangle(img,(x1,y1),(x2,y2),tuple(int(x) for x in rng.integers(0,255,3)),-1)
    else:
        img=np.full((h,w,3),50,dtype=np.uint8)
        for k in range(0,w,12): cv2.line(img,(k,0),(w-k-1,h-1),(150,150,150),1)
    cv2.imwrite(str(path),img)


def main():
    out=ROOT/'reports'/'step5.6-benchmark'
    if out.exists(): shutil.rmtree(out)
    (out/'sources').mkdir(parents=True)
    (out/'protected').mkdir(parents=True)
    (out/'attacks').mkdir(parents=True)
    (out/'negative').mkdir(parents=True)
    db=out/'registry.sqlite3'
    real=Path('/mnt/data/0B559232-4B9F-4DD6-BD24-1605B912DE59.jpeg')
    sources=generate_sources(out/'sources',real,5)
    specs=default_v01_attack_specs()
    rows=[]
    protected_rows=[]
    t0=time.perf_counter()
    for idx,(src,category) in enumerate(sources):
        protected=out/'protected'/f"p_{idx:02d}.png"
        p=protect_image(str(src),str(protected),str(db))
        protected_rows.append({"source":str(src),"category":category,"protected":str(protected),"token":p.fingerprint.watermark_token,"fingerprint":p.fingerprint.fingerprint_id})
        case_dir=out/'attacks'/f"case_{idx:02d}"
        for spec in specs:
            r=run_attack_case(protected,db,p.fingerprint.watermark_token,case_dir,spec)
            d=r.to_dict(); d['source_index']=idx; d['category']=category; rows.append(d)

    # Negative controls for FPR.
    neg_total=500; neg_detected=0
    for i in range(neg_total):
        p=out/'negative'/f"neg_{i:04d}.png"
        generate_negative(p,i)
        v=verify_image(str(p),str(db))
        neg_detected += int(v.detected)
    elapsed=time.perf_counter()-t0

    # Aggregate by attack.
    per_attack={}
    for spec in specs:
        rr=[r for r in rows if r['attack_id']==spec.attack_id]
        n=len(rr); det=sum(int(r['detected']) for r in rr); rec=sum(int(r['token_exact_match']) for r in rr)
        bers=[r['ber'] for r in rr if r['ber'] is not None]
        per_attack[spec.attack_id]={
            'attack_name':spec.name,'parameters':spec.parameters,'cases':n,
            'detected':det,'detection_rate':det/n if n else 0,
            'recovered':rec,'recovery_rate':rec/n if n else 0,
            'mean_ber':sum(bers)/len(bers) if bers else None,
        }

    # Compare against Step 4 gates.
    gate_targets={
        'T01-copy':1.00,
        'T02-screenshot':0.90,
        'T03-resize-75':0.95,
        'T03-resize-50':0.95,
        'T03-crop-10':0.90,
        'T03-crop-20':0.90,
        'T04-jpeg-95':0.90,
        'T04-jpeg-75':0.90,
        'T04-jpeg-60':0.90,
        'T05-conversion':0.85,
    }
    gates=[]
    for aid,target in gate_targets.items():
        actual=per_attack[aid]['detection_rate']
        gates.append({'gate':aid,'target':target,'actual':actual,'pass':actual>=target})
    fpr=neg_detected/neg_total
    gates.append({'gate':'False Positive Rate','target':'< 0.01','actual':fpr,'pass':fpr<0.01})
    all_pass=all(g['pass'] for g in gates)

    summary={
        'benchmark_type':'Step 5.6 engineering benchmark',
        'engine':'dct-qim-baseline',
        'source_images':len(sources),
        'source_categories':sorted(set(c for _,c in sources)),
        'attack_cases':len(rows),
        'negative_controls':neg_total,
        'false_positive_detected':neg_detected,
        'false_positive_rate':fpr,
        'elapsed_seconds':elapsed,
        'per_attack':per_attack,
        'release_gates':gates,
        'v0_1_gate_pass':all_pass,
        'decision':'GO' if all_pass else 'NO-GO',
        'note':'This benchmark uses 20 mixed real-derived/synthetic sources and 500 negative controls. Step 4 specifies 100 protected source images for the full Golden Test Set; this run is an engineering gate, not the final production validation.'
    }
    (out/'benchmark-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    with (out/'attack-results.csv').open('w',newline='',encoding='utf-8-sig') as f:
        fields=['source_index','category','attack_id','attack_name','parameters','detected','registry_match','token_exact_match','ber','runtime_ms','evidence_level','output_path']
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for r in rows:
            r=r.copy(); r['parameters']=json.dumps(r['parameters'],ensure_ascii=False,sort_keys=True)
            w.writerow({k:r[k] for k in fields})

    md=['# AI-IP Shield Step 5.6 Attack Lab Benchmark','',f"**Decision: {'GO' if all_pass else 'NO-GO'}**",'',f"- Engine: `dct-qim-baseline`",f"- Protected source images: {len(sources)}",f"- Attack cases: {len(rows)}",f"- Negative controls: {neg_total}",f"- False positive rate: {fpr:.2%}",f"- Runtime: {elapsed:.1f}s",'', '## Attack Results','', '| Attack | Detection | Recovery | Mean BER | Gate |','|---|---:|---:|---:|---:|']
    gate_map={g['gate']:g for g in gates}
    for spec in specs:
        a=per_attack[spec.attack_id]; g=gate_map.get(spec.attack_id)
        gate='—' if g is None else ('PASS' if g['pass'] else 'FAIL')
        md.append(f"| {spec.attack_id} | {a['detection_rate']:.0%} | {a['recovery_rate']:.0%} | {a['mean_ber']:.1%} | {gate} |")
    md += ['', '## Release Gate', '', '| Gate | Target | Actual | Result |','|---|---:|---:|---|']
    for g in gates:
        actual=f"{g['actual']:.1%}" if isinstance(g['actual'],float) else str(g['actual'])
        target=f"{g['target']:.0%}" if isinstance(g['target'],float) else str(g['target'])
        md.append(f"| {g['gate']} | {target} | {actual} | {'PASS' if g['pass'] else 'FAIL'} |")
    md += ['', '## Interpretation','', '- The baseline survives exact copies and high-quality JPEG/conversion paths better than geometric transforms.', '- Resize, crop, rotation and simulated screenshot break block synchronization because the current DCT-QIM extractor assumes the same 8×8 block geometry as the protected image.', '- This is a useful failure: Step 5.6 has identified synchronization robustness as the next engineering requirement.', '- Do not claim screenshot/crop/resize resistance from this baseline.', '', '## Next Action','', 'Keep the current engine as CPU baseline only. Add a robust engine (PixelSeal/Blind Watermark adapter actually enabled) and/or geometric synchronization layer, then rerun this exact Attack Lab without changing the acceptance targets.', '', '> This is an engineering benchmark, not legal proof or a claim of unbreakable protection.']
    (out/'ATTACK-LAB-REPORT.md').write_text('\n'.join(md),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
