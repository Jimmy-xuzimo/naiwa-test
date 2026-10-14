#!/usr/bin/env python3
"""生成叶片卡片贴图。

上一版画的是 252 根**矩形笔画**，贴到 3.6m 的卡片上就是一片片绿色木板，
远看还行，1080p 一看就露。这里改成真正的叶形：
两端收尖的披针形叶身 + 中脉 + 逐叶色差，沿几条枝铺开，中间留出透光缝隙。
"""
import math, random
from PIL import Image, ImageDraw

S = 1024
rnd = random.Random(20261014)
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
dr = ImageDraw.Draw(img, "RGBA")


def blade(cx, cy, ang, ln, wd, col, vein):
    """披针形叶：沿轴采样宽度 = 半宽·sin(πt)^0.62，两端自然收尖"""
    N = 16
    pts = []
    for sgn in (1, -1):
        rng = range(N + 1) if sgn == 1 else range(N, -1, -1)
        for i in rng:
            t = i / N
            hw = wd * (math.sin(math.pi * t) ** 0.62) * 0.5
            x = -ln * 0.5 + t * ln
            pts.append((x, hw * sgn))
    ca, sa = math.cos(ang), math.sin(ang)
    poly = [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in pts]
    dr.polygon(poly, fill=col)
    # 中脉
    vpts = []
    for i in range(N + 1):
        t = i / N
        x = -ln * 0.5 + t * ln
        vpts.append((cx + x * ca, cy + x * sa))
    dr.line(vpts, fill=vein, width=max(1, int(wd * 0.055)))


def spray(cx, cy, ang, ln, spread=0.62, n=13):
    """从一条枝上发叶"""
    ca, sa = math.cos(ang), math.sin(ang)
    dr.line([(cx, cy), (cx + ln * ca, cy + ln * sa)],
            fill=(58, 74, 34, 255), width=4)
    for i in range(n):
        t = 0.06 + 0.94 * (i / max(1, n - 1))
        bx = cx + ln * t * ca
        by = cy + ln * t * sa
        a = ang + rnd.choice((-1, 1)) * rnd.uniform(0.55, 1.25)
        L = rnd.uniform(96, 178)
        W = L * rnd.uniform(0.30, 0.46)
        g = rnd.uniform(0.72, 1.10)
        col = (int(74 * g), int(126 * g), int(38 * g), 255)
        blade(bx, by, a, L, W, col, (int(46 * g), int(84 * g), int(24 * g), 255))
        # 反向再长一片，显得密
        a2 = a + math.pi * rnd.uniform(0.80, 1.00)
        L2 = L * rnd.uniform(0.62, 0.90)
        g2 = rnd.uniform(0.70, 1.05)
        blade(bx, by, a2, L2, L2 * rnd.uniform(0.28, 0.42),
              (int(64 * g2), int(112 * g2), int(33 * g2), 255),
              (int(40 * g2), int(76 * g2), int(21 * g2), 255))


# 主体：几丛方向不同的枝叶，叠出一个有缝隙的簇
for k in range(7):
    a = k * (2 * math.pi / 7) + rnd.uniform(-0.3, 0.3)
    spray(S / 2 + math.cos(a) * 40, S / 2 + math.sin(a) * 40,
          a, rnd.uniform(230, 330))
# 外围再撒一些散叶，打散轮廓
for k in range(60):
    a = rnd.uniform(0, 2 * math.pi)
    r = rnd.uniform(210, 400)
    L = rnd.uniform(80, 150)
    g = rnd.uniform(0.68, 1.08)
    blade(S / 2 + math.cos(a) * r, S / 2 + math.sin(a) * r,
          a + rnd.uniform(-1.2, 1.2), L, L * rnd.uniform(0.28, 0.44),
          (int(70 * g), int(120 * g), int(36 * g), 255),
          (int(44 * g), int(80 * g), int(22 * g), 255))

img.save("/tmp/scene/leaf.png")
a = img.getchannel("A")
hist = a.histogram()
op = sum(hist[128:]) / (S * S)
print("leaf.png 重画完成：不透明占比 %.1f%%（上一版 34.4%%）" % (op * 100))
