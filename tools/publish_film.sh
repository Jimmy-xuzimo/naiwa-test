#!/bin/bash
# 把 /tmp/scene 的成片转成网页用的资源，放进 assets/film/
# 环绕序列编成往返循环，接缝才是无缝的。
set -e
SC=/tmp/scene
DST="$(cd "$(dirname "$0")/.." && pwd)/assets/film"
mkdir -p "$DST"
PY=/usr/local/bin/python3

pick(){ ls -t "$SC"/$1 2>/dev/null | head -1; }

HERO=$(pick 'final_hero_hero_1920x1080_*.png')
MASC=$(pick 'final_mascot_mascot_1200x1500_*.png')
THRQ=$(pick 'final_quarter_quarter_1920x1080_*.png')
echo "hero=$HERO"; echo "mascot=$MASC"; echo "threeq=$THRQ"

$PY - "$HERO" "$MASC" "$THRQ" "$DST" <<'PYEOF'
import sys, os
from PIL import Image
hero, masc, thrq, dst = sys.argv[1:5]
def conv(src, name, w, q=88):
    im = Image.open(src).convert("RGB")
    if im.width > w:
        im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    im.save(os.path.join(dst, name + ".jpg"), "JPEG", quality=q,
            optimize=True, progressive=True, subsampling=1)
    im.save(os.path.join(dst, name + ".webp"), "WEBP", quality=q, method=6)
    print("  %-14s %5dx%-5d  jpg %6.0f KB  webp %6.0f KB" % (
        name, im.width, im.height,
        os.path.getsize(os.path.join(dst, name + ".jpg")) / 1024,
        os.path.getsize(os.path.join(dst, name + ".webp")) / 1024))
conv(hero, "hero", 1920)
conv(masc, "mascot", 1100)
conv(thrq, "threeq", 1600)
PYEOF

# 环绕：正放 + 倒放拼成无缝循环
cd "$SC"
FIRST=$(ls -t orb_orbit*_960x540_*.png 2>/dev/null | tail -1)
[ -n "$FIRST" ] || { echo "没有环绕帧"; exit 1; }
ffmpeg -y -framerate 24 -pattern_type glob -i 'orb_orbit*_960x540_*.png' \
  -c:v libx264 -pix_fmt yuv420p -crf 16 "$SC/orbit_fwd.mp4" >/dev/null 2>&1
ffmpeg -y -i "$SC/orbit_fwd.mp4" -filter_complex \
  "[0:v]split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1[o]" -map "[o]" \
  -c:v libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart \
  "$DST/orbit.mp4" >/dev/null 2>&1
# 海报帧
LAST=$(ls -t orb_orbit*_960x540_*.png | head -1)
$PY -c "
from PIL import Image; import sys
im=Image.open('$LAST').convert('RGB')
im.save('$DST/orbit.jpg','JPEG',quality=86,optimize=True,progressive=True)
print('  orbit.mp4 %.1f MB' % (__import__('os').path.getsize('$DST/orbit.mp4')/1048576))
"
ls -la "$DST"
