"""探针：量出 Nishita 天空在「北向地平线上方 0~3°」处的**线性**颜色，
用来定合成器的 HAZE 色。渲染成 Standard 变换的 PNG（= sRGB 编码的线性值），
再手动 decode 回线性。
"""
import bpy, math, os, numpy as np

SUN_ROT = float(os.environ.get("SKYROT", "-30.9"))     # 度
SUN_ELEV = float(os.environ.get("SKYELEV", "28"))      # 度
STRENGTH = float(os.environ.get("SKYSTR", "0.62"))
TINT = (0.90, 1.00, 1.38)
DUST = float(os.environ.get("DUST", "1.4"))
OUT = "/tmp/scene/_skyprobe.exr"

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 8

w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
nt = w.node_tree
bg = nt.nodes["Background"]
sky = nt.nodes.new("ShaderNodeTexSky")
sky.sky_type = 'NISHITA'
sky.sun_elevation = math.radians(SUN_ELEV)
sky.sun_rotation = math.radians(SUN_ROT)
sky.air_density = 1.0; sky.dust_density = DUST; sky.ozone_density = 1.0
sky.sun_intensity = 0.35
tn = nt.nodes.new("ShaderNodeMixRGB"); tn.blend_type = 'MULTIPLY'
tn.inputs[0].default_value = 1.0
tn.inputs[2].default_value = (TINT[0], TINT[1], TINT[2], 1)
nt.links.new(sky.outputs["Color"], tn.inputs[1])
nt.links.new(tn.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = STRENGTH

# 相机水平朝北（-Y），等距柱状式地看：一帧 90° 竖直摆幅由像素行给出
bpy.ops.object.camera_add(location=(0, 0, 1.7))
cam = bpy.context.object
cam.data.lens = 24.0; cam.data.sensor_width = 36.0
cam.rotation_euler = (math.radians(90), 0, math.radians(180))   # 看向 -Y，水平
sc.camera = cam

sc.view_settings.view_transform = 'Standard'
sc.view_settings.look = 'None'
sc.view_settings.exposure = 0.0
sc.render.resolution_x = 320; sc.render.resolution_y = 180
# 32bit EXR：无 clamp、无色彩管理往返，pixels 就是场景线性辐亮度
sc.render.image_settings.file_format = 'OPEN_EXR'
sc.render.image_settings.color_depth = '32'
sc.render.image_settings.color_mode = 'RGB'
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)

img = bpy.data.images.load(OUT)
img.colorspace_settings.name = 'Non-Color'
W, H = img.size
px = np.array(img.pixels[:], np.float32).reshape(H, W, img.channels)[:, :, :3]   # 行 0 = 底部
# 相机水平：行 y 对应仰角 el = atan( ((y+0.5)/H - 0.5) * 2*tan(halfV) )，halfV 竖半角
half_v = math.atan((36.0 * H / W / 2) / 24.0)
def elev_of(row):
    return math.degrees(math.atan(((row + .5) / H - .5) * 2 * math.tan(half_v)))
def lin(c):
    return c
az_mid = slice(W // 2 - 40, W // 2 + 40)      # 北向正中
print("── 北向天空剖线（真实线性辐亮度） ──")
print(f"{'仰角°':>7s}   {'R':>6s} {'G':>6s} {'B':>6s}    B-R")
for row in range(H):
    el = elev_of(row)
    if not (-1 < el < 22): continue
    m = lin(px[row, az_mid].mean(0))
    if abs(el - round(el * 2) / 2) < 0.12:   # 每 0.5° 打一行
        print(f"{el:7.1f}   {m[0]:6.3f} {m[1]:6.3f} {m[2]:6.3f}   {m[2]-m[0]:+.3f}")
# 地平线带 0~2°
band = [lin(px[r, az_mid].mean(0)) for r in range(H) if 0.3 < elev_of(r) < 2.2]
if band:
    b = np.mean(band, 0)
    print("\n★ 地平线带（0.3~2.2°）均值，线性: (%.4f, %.4f, %.4f)  亮度 %.4f"
          % (b[0], b[1], b[2], b @ np.array([.2126, .7152, .0722])))
    print("   该值 × world_strength 就是合成器里的 HAZE 色（本探针已含 strength=%s）" % STRENGTH)
    print("   sRGB 8bit 参考:", tuple(int(round(v * 255)) for v in np.clip(b, 0, 1) ** (1 / 2.2)))

    # 落盘给主脚本读，别再手抄
    import json
    prof = []
    for row in range(H):
        el = elev_of(row)
        if -1 < el < 30:
            prof.append((round(el, 2), [round(float(v), 4) for v in px[row, az_mid].mean(0)]))
    json.dump({"sun_rot": SUN_ROT, "sun_elev": SUN_ELEV, "strength": STRENGTH,
               "dust": DUST, "tint": TINT,
               "horizon": [round(float(v), 4) for v in b], "profile": prof},
              open("/tmp/scene/_skyprobe.json", "w"), indent=1)
    print("   → 已写 /tmp/scene/_skyprobe.json")
