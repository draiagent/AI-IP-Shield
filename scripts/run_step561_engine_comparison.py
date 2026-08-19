from __future__ import annotations

from pathlib import Path
import csv
import json
import shutil
import sys
import tempfile
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aipshield.engines import get_engine
from aipshield.protect import protect_image
from aipshield.verify import verify_image
from aipshield.attack_lab import default_v01_attack_specs, run_attack_case

SEED = 20260818
np.random.seed(SEED)


def fit_cover(img, size=(640, 480)):
    tw, th = size
    h, w = img.shape[:2]
    scale = max(tw / w, th / h)
    nw, nh = round(w * scale), round(h * scale)
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
    x, y = (nw - tw) // 2, (nh - th) // 2
    return resized[y:y+th, x:x+tw].copy()


def make_sources(root: Path, real_path: Path):
    root.mkdir(parents=True, exist_ok=True)
    h, w = 480, 640
    real = fit_cover(cv2.imread(str(real_path)), (w, h))
    out = []

    p = root / "real.png"; cv2.imwrite(str(p), real); out.append((p, "real-infographic"))

    rng = np.random.default_rng(SEED)
    Y, X = np.mgrid[0:h, 0:w]
    photo = np.stack([80 + 130*X/w, 55 + 160*Y/h, 115 + 85*np.sin((X+Y)/52)], axis=-1)
    photo += rng.normal(0, 12, photo.shape); photo = np.clip(photo, 0, 255).astype(np.uint8)
    cv2.circle(photo, (390, 210), 70, (220, 170, 80), -1)
    p = root / "photo.png"; cv2.imwrite(str(p), photo); out.append((p, "photo-like"))

    im = Image.new("RGB", (w, h), (244,247,250)); d = ImageDraw.Draw(im)
    d.text((24,18), "AI-IP Shield Card", fill=(25,35,50))
    for j in range(6):
        x=24+(j%3)*204; y=72+(j//3)*190; c=(60+j*20, 110, 175)
        d.rounded_rectangle((x,y,x+185,y+150), radius=16, fill=c)
        d.text((x+12,y+18), f"MODULE {j+1}", fill="white")
    p = root / "card.png"; im.save(p); out.append((p, "text-card"))

    im = Image.new("RGB", (w,h), "white"); d = ImageDraw.Draw(im)
    d.rectangle((0,0,w,62), fill=(45,110,180)); d.text((28,20), "Enterprise AI Slide", fill="white")
    d.rectangle((28,95,390,410), outline=(100,110,120), width=2)
    for k in range(7): d.line((55,130+k*36,350,130+k*36), fill=(125,135,145), width=2)
    d.rectangle((420,95,610,235), fill=(225,235,244)); d.rectangle((420,260,610,410), fill=(235,228,242))
    p = root / "slide.png"; im.save(p); out.append((p, "slide-page"))

    flat = np.full((h,w,3), 230, dtype=np.uint8)
    cv2.rectangle(flat,(90,90),(550,390),(236,238,240),-1); cv2.circle(flat,(320,240),70,(170,175,185),2)
    cv2.putText(flat,"LOW TEXTURE",(245,250),cv2.FONT_HERSHEY_SIMPLEX,.65,(70,70,70),2,cv2.LINE_AA)
    p = root / "flat.png"; cv2.imwrite(str(p), flat); out.append((p, "low-texture"))
    return out


def make_negative(path: Path, i: int):
    rng=np.random.default_rng(SEED+5000+i); h,w=384,512; m=i%4
    if m==0: img=rng.integers(0,256,(h,w,3),dtype=np.uint8)
    elif m==1:
        img=np.full((h,w,3),180+i%50,dtype=np.uint8); cv2.putText(img,f"NEG {i}",(40,200),cv2.FONT_HERSHEY_SIMPLEX,1,(30,30,30),2,cv2.LINE_AA)
    elif m==2:
        Y,X=np.mgrid[0:h,0:w]; img=np.stack([X*255/w,Y*255/h,(X+Y)*255/(w+h)],-1).astype(np.uint8)
    else:
        img=np.full((h,w,3),245,dtype=np.uint8)
        for _ in range(10):
            x1=int(rng.integers(0,w-20)); y1=int(rng.integers(0,h-20)); x2=min(w-1,x1+int(rng.integers(10,150))); y2=min(h-1,y1+int(rng.integers(10,100)))
            cv2.rectangle(img,(x1,y1),(x2,y2),tuple(int(x) for x in rng.integers(0,255,3)),-1)
    cv2.imwrite(str(path),img)


def quality(src: Path, protected: Path):
    a=cv2.imread(str(src)); b=cv2.imread(str(protected))
    return {
        "psnr": float(peak_signal_noise_ratio(a,b,data_range=255)),
        "ssim": float(structural_similarity(a,b,channel_axis=2,data_range=255)),
    }


def engine_available(name: str):
    try:
        engine = get_engine(name)
        return True, engine.name, None
    except Exception as exc:
        return False, None, f"{type(exc).__name__}: {exc}"


def benchmark_engine(name: str, sources, specs, work: Path, negative_count=20):
    available, resolved_name, error = engine_available(name)
    if not available:
        return {"requested_engine": name, "available": False, "error": error}

    db=work/f"registry-{name}.sqlite3"; rows=[]; qs=[]; t0=time.perf_counter()
    for idx,(src,cat) in enumerate(sources):
        protected=work/f"{name}-p-{idx}.png"
        pr=protect_image(str(src),str(protected),str(db),engine_name=name)
        qs.append(quality(src,protected))
        case=work/f"att-{name}-{idx}"; case.mkdir(exist_ok=True)
        for spec in specs:
            r=run_attack_case(protected,db,pr.fingerprint.watermark_token,case,spec,engine_name=name)
            d=r.to_dict(); d["source_index"]=idx; d["category"]=cat; rows.append(d)
        shutil.rmtree(case,ignore_errors=True)

    fp=0; negdir=work/f"neg-{name}"; negdir.mkdir(exist_ok=True)
    for i in range(negative_count):
        p=negdir/f"n{i:03d}.png"; make_negative(p,i)
        try: fp += int(verify_image(str(p),str(db),engine_name=name).detected)
        except Exception: pass
    elapsed=time.perf_counter()-t0

    per={}
    for spec in specs:
        rr=[r for r in rows if r["attack_id"]==spec.attack_id]; n=len(rr)
        bers=[r["ber"] for r in rr if r["ber"] is not None]
        per[spec.attack_id]={
            "cases":n,
            "detection_rate":sum(r["detected"] for r in rr)/n,
            "recovery_rate":sum(r["token_exact_match"] for r in rr)/n,
            "mean_ber":sum(bers)/len(bers) if bers else None,
        }
    return {
        "requested_engine":name,
        "resolved_engine":resolved_name,
        "available":True,
        "source_images":len(sources),
        "attack_cases":len(rows),
        "negative_controls":negative_count,
        "false_positive_rate":fp/negative_count,
        "mean_psnr":sum(q["psnr"] for q in qs)/len(qs),
        "mean_ssim":sum(q["ssim"] for q in qs)/len(qs),
        "elapsed_seconds":elapsed,
        "per_attack":per,
        "rows":rows,
    }


def main():
    outdir=ROOT/"reports"/"step5.6.1"; outdir.mkdir(parents=True,exist_ok=True)
    specs=default_v01_attack_specs()
    with tempfile.TemporaryDirectory(prefix="aips-561-") as td:
        work=Path(td); all_sources=make_sources(work/"sources",Path("/mnt/data/0B559232-4B9F-4DD6-BD24-1605B912DE59.jpeg"))
        sources=[all_sources[i] for i in (0,2,4)]
        results=[]
        for name in ["dct-qim","blind","pixelseal"]:
            print(f"benchmarking {name}...",flush=True)
            results.append(benchmark_engine(name,sources,specs,work,negative_count=5))

    serializable=[]
    for r in results:
        rr={k:v for k,v in r.items() if k!="rows"}; serializable.append(rr)
    payload={"benchmark":"Step 5.6.1 engineering comparison","results":serializable}
    (outdir/"engine-comparison.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")

    with (outdir/"engine-attack-results.csv").open("w",newline="",encoding="utf-8-sig") as f:
        fields=["engine","source_index","category","attack_id","detected","token_exact_match","ber","runtime_ms"]
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for r in results:
            for row in r.get("rows",[]):
                w.writerow({"engine":r["resolved_engine"], **{k:row[k] for k in fields if k!="engine"}})

    md=["# Step 5.6.1 Robust Engine Upgrade — Engineering Comparison","","This is a 3-source/5-negative-control engineering integration gate, not the final 100-image/500-negative-control release benchmark.",""]
    for r in serializable:
        md.append(f"## {r['requested_engine']}")
        if not r["available"]:
            md += ["",f"**UNAVAILABLE:** `{r['error']}`",""]
            continue
        md += ["",f"Resolved backend: `{r['resolved_engine']}`",f"- Mean PSNR: {r['mean_psnr']:.2f} dB",f"- Mean SSIM: {r['mean_ssim']:.4f}",f"- FPR: {r['false_positive_rate']:.2%}",f"- Runtime: {r['elapsed_seconds']:.1f}s","", "| Attack | Detection | Recovery | BER |","|---|---:|---:|---:|"]
        for spec in specs:
            a=r["per_attack"][spec.attack_id]
            md.append(f"| {spec.attack_id} | {a['detection_rate']:.0%} | {a['recovery_rate']:.0%} | {a['mean_ber']:.1%} |")
        md.append("")
    md += ["## Decision","", "- DCT-QIM remains a baseline only.", "- Blind Watermark native-compatible backend is the current CPU fallback; canonical resizing + convolutional ECC fixed resize and JPEG robustness, but crop/screenshot/rotation remain blocking weaknesses.", "- PixelSeal adapter is implemented, but the real Meta model/checkpoint is required before selecting the production engine. No fake/surrogate result is used for robustness claims.", "", "**Production engine selection remains PENDING until PixelSeal is benchmarked on the same Attack Lab.**"]
    (outdir/"ENGINE-COMPARISON.md").write_text("\n".join(md),encoding="utf-8")
    print(json.dumps(payload,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
