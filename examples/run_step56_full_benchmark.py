from __future__ import annotations
from pathlib import Path
import csv, json, random, shutil, sys, tempfile, time
import cv2, numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from aipshield.protect import protect_image
from aipshield.verify import verify_image
from aipshield.attack_lab import default_v01_attack_specs, run_attack_case

SEED=20260818
random.seed(SEED); np.random.seed(SEED)


def fit_cover(img, size=(640,480)):
    tw,th=size; h,w=img.shape[:2]; s=max(tw/w,th/h); nw,nh=round(w*s),round(h*s)
    r=cv2.resize(img,(nw,nh),interpolation=cv2.INTER_AREA if s<1 else cv2.INTER_CUBIC)
    x=(nw-tw)//2; y=(nh-th)//2
    return r[y:y+th,x:x+tw].copy()


def make_sources(root: Path, real_path: Path):
    root.mkdir(parents=True,exist_ok=True); out=[]; h,w=480,640
    real=cv2.imread(str(real_path)); base=fit_cover(real,(w,h))
    # 20 real-infographic-derived
    for i in range(20):
        img=base.copy(); alpha=0.94+(i%7)*0.02; beta=(i%5-2)*3
        img=cv2.convertScaleAbs(img,alpha=alpha,beta=beta)
        if i%3==1: img=cv2.GaussianBlur(img,(3,3),0)
        p=root/f"real_{i:02d}.png"; cv2.imwrite(str(p),img); out.append((p,'real-infographic'))
    # 20 photo-like synthetic
    Y,X=np.mgrid[0:h,0:w]
    for i in range(20):
        rng=np.random.default_rng(SEED+i)
        img=np.stack([
            80+130*X/w+25*np.sin(Y/(22+i%5)),
            55+160*Y/h+20*np.cos(X/(37+i%7)),
            115+85*np.sin((X+Y)/(48+i%9))],axis=-1)
        img += rng.normal(0,10+i%6,img.shape); img=np.clip(img,0,255).astype(np.uint8)
        cv2.circle(img,(80+(i*47)%500,80+(i*31)%320),35+i%35,(220,170,80),-1)
        p=root/f"photo_{i:02d}.png"; cv2.imwrite(str(p),img); out.append((p,'photo-like'))
    # 20 text cards
    for i in range(20):
        im=Image.new('RGB',(w,h),(244,247,250)); d=ImageDraw.Draw(im)
        d.text((24,18),f"AI-IP Shield Card {i+1}",fill=(25,35,50))
        for j in range(6):
            x=24+(j%3)*204; y=72+(j//3)*190
            c=(50+(i*9+j*13)%160,90+(j*20)%130,160+(i*5)%80)
            d.rounded_rectangle((x,y,x+185,y+150),radius=16,fill=c)
            d.text((x+12,y+18),f"MODULE {j+1}",fill='white'); d.text((x+12,y+52),"Protect\nVerify\nEvidence",fill='white')
        p=root/f"card_{i:02d}.png"; im.save(p); out.append((p,'text-card'))
    # 20 slide-like pages
    for i in range(20):
        im=Image.new('RGB',(w,h),'white'); d=ImageDraw.Draw(im)
        d.rectangle((0,0,w,62),fill=(30+(i*4)%80,100,150+(i*3)%90)); d.text((28,20),f"Enterprise AI Slide {i+1}",fill='white')
        d.rectangle((28,95,390,410),outline=(100,110,120),width=2); d.rectangle((420,95,610,235),fill=(225,235,244)); d.rectangle((420,260,610,410),fill=(235,228,242))
        for k in range(7): d.line((55,130+k*36,350,130+k*36),fill=(125,135,145),width=2)
        d.text((440,125),"KPI",fill=(20,30,40)); d.text((440,292),"AGENT",fill=(20,30,40))
        p=root/f"slide_{i:02d}.png"; im.save(p); out.append((p,'slide-page'))
    # 20 low texture
    for i in range(20):
        img=np.full((h,w,3),205+(i%8)*5,dtype=np.uint8)
        cv2.rectangle(img,(90,90),(550,390),(218+(i%5)*3,220+(i%5)*3,224+(i%5)*3),-1)
        cv2.circle(img,(320,240),55+i%25,(165,170,180),2)
        cv2.putText(img,f"LOW {i+1}",(265,250),cv2.FONT_HERSHEY_SIMPLEX,0.7,(75,75,75),2,cv2.LINE_AA)
        p=root/f"flat_{i:02d}.png"; cv2.imwrite(str(p),img); out.append((p,'low-texture'))
    return out


def make_negative(path: Path,i:int):
    rng=np.random.default_rng(SEED+5000+i); h,w=384,512; m=i%5
    if m==0: img=rng.integers(0,256,(h,w,3),dtype=np.uint8)
    elif m==1:
        img=np.full((h,w,3),160+i%80,dtype=np.uint8); cv2.putText(img,f"NEGATIVE {i}",(30,200),cv2.FONT_HERSHEY_SIMPLEX,1,(20,20,20),2,cv2.LINE_AA)
    elif m==2:
        Y,X=np.mgrid[0:h,0:w]; img=np.stack([X*255/w,Y*255/h,(X+Y)*255/(w+h)],-1).astype(np.uint8)
    elif m==3:
        img=np.full((h,w,3),245,dtype=np.uint8)
        for _ in range(12):
            x1=int(rng.integers(0,w-20)); y1=int(rng.integers(0,h-20)); x2=min(w-1,x1+int(rng.integers(10,180))); y2=min(h-1,y1+int(rng.integers(10,120)))
            cv2.rectangle(img,(x1,y1),(x2,y2),tuple(int(x) for x in rng.integers(0,255,3)),-1)
    else:
        img=np.full((h,w,3),60,dtype=np.uint8)
        for x in range(0,w,13): cv2.line(img,(x,0),(w-1-x,h-1),(150,150,150),1)
    cv2.imwrite(str(path),img)


def main():
    final=ROOT/'reports'/'step5.6-full'; final.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='aips-step56-') as td:
        work=Path(td); sources=make_sources(work/'sources',Path('/mnt/data/0B559232-4B9F-4DD6-BD24-1605B912DE59.jpeg')); db=work/'registry.sqlite3'; specs=default_v01_attack_specs(); rows=[]
        t0=time.perf_counter()
        for idx,(src,cat) in enumerate(sources):
            protected=work/f'p_{idx:03d}.png'; pr=protect_image(str(src),str(protected),str(db))
            case=work/f'a_{idx:03d}'; case.mkdir()
            for spec in specs:
                r=run_attack_case(protected,db,pr.fingerprint.watermark_token,case,spec)
                d=r.to_dict(); d['source_index']=idx; d['category']=cat; rows.append(d)
                try: Path(r.output_path).unlink()
                except FileNotFoundError: pass
            shutil.rmtree(case,ignore_errors=True); protected.unlink(missing_ok=True)
        neg=500; fp=0
        negdir=work/'neg'; negdir.mkdir()
        for i in range(neg):
            p=negdir/f'n{i:04d}.png'; make_negative(p,i); v=verify_image(str(p),str(db)); fp+=int(v.detected); p.unlink(missing_ok=True)
        elapsed=time.perf_counter()-t0
    per={}
    for spec in specs:
        rr=[r for r in rows if r['attack_id']==spec.attack_id]; n=len(rr); det=sum(r['detected'] for r in rr); rec=sum(r['token_exact_match'] for r in rr); bers=[r['ber'] for r in rr if r['ber'] is not None]
        per[spec.attack_id]={'attack_name':spec.name,'parameters':spec.parameters,'cases':n,'detection_rate':det/n,'recovery_rate':rec/n,'mean_ber':sum(bers)/len(bers)}
    targets={'T01-copy':1.0,'T02-screenshot':0.90,'T03-resize-75':0.95,'T03-resize-50':0.95,'T03-crop-10':0.90,'T03-crop-20':0.90,'T04-jpeg-95':0.90,'T04-jpeg-75':0.90,'T04-jpeg-60':0.90,'T05-conversion':0.85}
    gates=[]
    for aid,t in targets.items():
        a=per[aid]['detection_rate']; gates.append({'gate':aid,'target':t,'actual':a,'pass':a>=t})
    fpr=fp/neg; gates.append({'gate':'False Positive Rate','target':'< 0.01','actual':fpr,'pass':fpr<0.01})
    summary={'benchmark_type':'Step 5.6 full Golden-set candidate','engine':'dct-qim-baseline','source_images':100,'category_counts':{'real-infographic':20,'photo-like':20,'text-card':20,'slide-page':20,'low-texture':20},'attack_cases':len(rows),'negative_controls':neg,'false_positive_detected':fp,'false_positive_rate':fpr,'elapsed_seconds':elapsed,'per_attack':per,'release_gates':gates,'v0_1_gate_pass':all(g['pass'] for g in gates),'decision':'GO' if all(g['pass'] for g in gates) else 'NO-GO','limitations':['Photo-like images are synthetic; real-world external camera/screenshot dataset is still required before production claims.','T02 is a deterministic screenshot simulation, not a physical-device capture corpus.']}
    (final/'benchmark-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    with (final/'attack-results.csv').open('w',newline='',encoding='utf-8-sig') as f:
        fields=['source_index','category','attack_id','attack_name','parameters','detected','registry_match','token_exact_match','ber','runtime_ms','evidence_level']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rows:
            r=r.copy();r['parameters']=json.dumps(r['parameters'],ensure_ascii=False,sort_keys=True);w.writerow({k:r[k] for k in fields})
    md=['# Step 5.6 Full Attack Lab Report','',f"**Decision: {summary['decision']}**",'',f"- 100 protected source images (20 × 5 categories)",f"- {len(rows)} attack cases",f"- 500 negative controls",f"- FPR: {fpr:.2%}",f"- Runtime: {elapsed:.1f}s",'', '## Results','','| Attack | Detection | Recovery | BER | Gate |','|---|---:|---:|---:|---|']
    gm={g['gate']:g for g in gates}
    for spec in specs:
        a=per[spec.attack_id]; g=gm.get(spec.attack_id); gate='—' if not g else ('PASS' if g['pass'] else 'FAIL'); md.append(f"| {spec.attack_id} | {a['detection_rate']:.0%} | {a['recovery_rate']:.0%} | {a['mean_ber']:.1%} | {gate} |")
    md += ['', '## Gate Summary','', '| Gate | Target | Actual | Result |','|---|---:|---:|---|']
    for g in gates:
        target=f"{g['target']:.0%}" if isinstance(g['target'],float) else g['target']; actual=f"{g['actual']:.1%}" if isinstance(g['actual'],float) else str(g['actual']); md.append(f"| {g['gate']} | {target} | {actual} | {'PASS' if g['pass'] else 'FAIL'} |")
    md += ['', '## Engineering Diagnosis','', 'The current baseline is robust to exact copies, JPEG 95/75, and same-geometry JPEG conversion, but it is not geometrically synchronized. Resize, crop, rotation and screenshot-like re-rendering randomize the block locations used by the extractor, producing BER near 50% and no valid payload.', '', '**Conclusion:** retain DCT-QIM as a CPU baseline only. It does **not** satisfy the Step 4 robustness gate.', '', '## Next Engineering Gate','', 'Enable a genuinely robust engine (PixelSeal or the Blind Watermark adapter) and/or introduce geometric synchronization. Rerun the same benchmark without lowering thresholds.']
    (final/'ATTACK-LAB-REPORT.md').write_text('\n'.join(md),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
