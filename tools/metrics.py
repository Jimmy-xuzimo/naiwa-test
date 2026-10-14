#!/usr/bin/env python3
"""README 渲染质检：按 blender-photoreal-landscape skill 的质量门禁算指标。
用法: python3 metrics.py a.png [b.png ...]
"""
import sys, numpy as np
from PIL import Image

def stats(p):
    im = Image.open(p).convert("RGB")
    a = np.asarray(im, np.float32) / 255.0
    h, w, _ = a.shape
    lum = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    # 天空判定：上部 1/4 且像素偏亮偏蓝
    top = a[: max(1, h // 4)]
    tl = lum[: max(1, h // 4)]
    gnd = a[h // 2:]
    gl = lum[h // 2:]
    # 逐行均值，找出「天空→地面」那条最陡的跳变行，用来报告地平线位置
    rowm = lum.reshape(h, -1).mean(1)
    d = np.abs(np.diff(rowm))
    hz = int(np.argmax(d)) if d.size else 0
    skyb_r = (top[..., 2].mean() - top[..., 0].mean())
    print(f"{p}")
    print(f"  size        {w}x{h}")
    print(f"  mean        {lum.mean():.3f}   (门禁 0.26~0.52)")
    print(f"  p05/p50/p95 {np.percentile(lum,5):.3f} / {np.percentile(lum,50):.3f} / {np.percentile(lum,95):.3f}")
    print(f"  contrast    {lum.std():.3f}   (门禁 0.22~0.60)")
    print(f"  sky_lum     {tl.mean():.3f}   gnd_lum {gl.mean():.3f}   比值 {tl.mean()/max(1e-6,gl.mean()):.2f}  (需 >1)")
    print(f"  sky B-R     {skyb_r:+.3f}   (需 > +0.010)")
    print(f"  dark%       {(lum<0.06).mean()*100:.1f}   (需 <8)")
    print(f"  blow%       {(lum>0.95).mean()*100:.1f}   (需 <6)")
    g = a[..., 1] - np.maximum(a[..., 0], a[..., 2])
    print(f"  green%      {((a[...,1]>a[...,0]*1.06)&(a[...,1]>a[...,2]*1.10)&(g>0.03)).mean()*100:.1f}   (参考 8~70)")
    print(f"  地平线行    {hz} / {h}  ({hz/h*100:.0f}%)")
    print()

for p in sys.argv[1:]:
    try:
        stats(p)
    except Exception as e:
        print(p, "ERR", e)
