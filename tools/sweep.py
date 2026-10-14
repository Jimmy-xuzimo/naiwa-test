#!/usr/bin/env python3
"""定值曝光扫描：渲一组曝光，报均值，并把它们拼成联络表。
用法: sweep.py CAM expo1 expo2 ...   [环境里带 RX RY SPP]
"""
import os, subprocess, sys, re
import numpy as np
from PIL import Image

BL = "/Users/yuyixian/Documents/Qoder/2026-09-13-22-26-38/blender_app/Blender.app/Contents/MacOS/Blender"
SCRIPT = "/tmp/scene_build.py"
CAM = sys.argv[1]; EXPOS = [float(x) for x in sys.argv[2:]]
RX = os.environ.get("RX", "640"); RY = os.environ.get("RY", "360")
SPP = os.environ.get("SPP", "32")


def mean_of(p):
    a = np.asarray(Image.open(p).convert("RGB"), np.float32) / 255
    return float((a @ np.array([.2126, .7152, .0722], np.float32)).mean())


def lum_of(p):
    a = np.asarray(Image.open(p).convert("RGB"), np.float32) / 255
    return a @ np.array([.2126, .7152, .0722], np.float32)


outs = []
for e in EXPOS:
    tag = "sw%+.1f" % e
    env = dict(os.environ)
    env.update({"RX": RX, "RY": RY, "SPP": SPP, "CAM": CAM,
                "TAG": tag, "EXPO": "%.3f" % e})
    p = subprocess.run([BL, "--background", "--factory-startup", "--python", SCRIPT],
                       capture_output=True, text=True, env=env)
    o = p.stdout + p.stderr
    if "Traceback" in o or "Error:" in o:
        print("!!", "\n".join(l for l in o.splitlines() if "Error" in l or "line " in l)[:1200])
        sys.exit(1)
    f = [x for x in os.listdir("/tmp/scene") if x.startswith(tag) and x.endswith(".png")]
    f.sort(key=lambda x: os.path.getmtime("/tmp/scene/" + x))
    path = "/tmp/scene/" + f[-1]
    m = mean_of(path)
    print("  expo %+.2f → mean %.3f  %s" % (e, m, os.path.basename(path)), flush=True)
    outs.append((e, path, m))

# 联络表
ims = [Image.open(p).convert("RGB").resize((int(RX) // 2, int(RY) // 2)) for _, p, _ in outs]
W, H = ims[0].size
sheet = Image.new("RGB", (W * len(ims), H), (20, 20, 20))
for i, im in enumerate(ims):
    sheet.paste(im, (i * W, 0))
sp = "/tmp/scene/contact_%s_%s.png" % (CAM, "_".join("%+.1f" % e for e, _, _ in outs))
sheet.save(sp)
print("联络表 →", sp, " 顺序:", ["%+.1f" % e for e, _, _ in outs])
