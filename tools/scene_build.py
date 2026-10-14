"""南传校门报到日 · 写实场景 v2（Cycles 路径追踪）

v1 的四个实测病灶 → 本版对策
  1. 天空辐亮度 2.5~5.8（线性）≈ 太阳灯 → 直射:天光接近阴天，画面平、无影
     → 用 RATIO 显式定直射:天光（晴日 ≈3:1），曝光另由 autoexp.py 定标
  2. 地面只 240m，"地平线"其实是板边（离相机 130m）
     → 铺到 24km，SKY_DEPTH=19000，并补远景树线/城市/丘陵
  3. 雾色凭感觉 → 从 probe_sky.py 实测的**线性**天边色读
  4. 树冠 2.6m 树干 + 2.3m 卡片 = 玩具灌木 → 8~11m 行道树 + 逐棵顶点色

环境变量：RX RY SPP DEV EXPO SUN SKYSTR RATIO SKYD CAM TAG
"""
import bpy, math, os, random, json, sys
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# 依赖同目录的 scene_lib.py；贴图放 PHTEX，产物落 SCENEOUT
import scene_lib as SL

TEX = os.environ.get("PHTEX", "/tmp/ph_tex")      # Poly Haven CC0 贴图目录
OUT = os.environ.get("SCENEOUT", "/tmp/scene")   # 输出目录
os.makedirs(OUT, exist_ok=True)
RES_X = int(os.environ.get("RX", "640")); RES_Y = int(os.environ.get("RY", "360"))
SPP = int(os.environ.get("SPP", "24"))
SKYSTR = float(os.environ.get("SKYSTR", "0.62"))
SKY_ELEV = float(os.environ.get("SKYELEV", "28"))
SKY_ROT = float(os.environ.get("SKYROT", "-30.9"))
RATIO = float(os.environ.get("RATIO", "3.0"))
# 探针在 dust0.9/strength0.62 下测得上半球平均辐亮度 ≈3.3（0~30° 剖面积分估计）
LSKY_AVG = 3.3
SUN_E = float(os.environ.get(
    "SUN", "%.2f" % (RATIO * math.pi * LSKY_AVG * (SKYSTR / 0.62) / math.sin(math.radians(SKY_ELEV)))))
MIST_START, MIST_DEPTH = 100.0, 9000.0

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = os.environ.get("DEV", "CPU")
sc.cycles.samples = SPP
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4
sc.cycles.diffuse_bounces = 3
sc.cycles.glossy_bounces = 3
sc.cycles.transmission_bounces = 4
sc.cycles.transparent_max_bounces = 24        # 叶片卡片是 alpha，射线要穿得过去
sc.render.resolution_x = RES_X; sc.render.resolution_y = RES_Y
sc.render.film_transparent = False
sc.view_settings.view_transform = 'Filmic'
try: sc.view_settings.look = os.environ.get("LOOK", 'Medium High Contrast')
except Exception: pass
sc.view_settings.exposure = float(os.environ.get("EXPO", "0.0"))

# ══════════ 材质 ══════════
def img(slug, suf):
    p = os.path.join(TEX, "%s_%s.jpg" % (slug, suf))
    return bpy.data.images.load(p) if os.path.exists(p) else None

def pbr(name, slug, tint=(1, 1, 1), tile=(1.0, 1.0), rough_mul=1.0,
        spec=0.5, bump_strength=1.0, subsurf=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; bs = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0 / tile[0], 1.0 / tile[1], 1.0 / tile[0])
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    d = img(slug, "diff")
    if d:
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = d
        n.projection = 'BOX'; n.interpolation = 'Smart'
        nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
        mix = nt.nodes.new("ShaderNodeMixRGB"); mix.blend_type = 'MULTIPLY'
        mix.inputs[0].default_value = 1.0
        mix.inputs[2].default_value = (tint[0], tint[1], tint[2], 1)
        nt.links.new(n.outputs["Color"], mix.inputs[1])
        nt.links.new(mix.outputs["Color"], bs.inputs["Base Color"])
    nr = img(slug, "nor")
    if nr:
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = nr; n.projection = 'BOX'
        n.image.colorspace_settings.name = 'Non-Color'
        nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = bump_strength
        nt.links.new(n.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bs.inputs["Normal"])
    rg = img(slug, "rough")
    if rg:
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = rg; n.projection = 'BOX'
        n.image.colorspace_settings.name = 'Non-Color'
        nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
        if rough_mul != 1.0:
            mm = nt.nodes.new("ShaderNodeMath"); mm.operation = 'MULTIPLY'
            mm.inputs[1].default_value = rough_mul
            nt.links.new(n.outputs["Color"], mm.inputs[0])
            nt.links.new(mm.outputs["Value"], bs.inputs["Roughness"])
        else:
            nt.links.new(n.outputs["Color"], bs.inputs["Roughness"])
    else:
        bs.inputs["Roughness"].default_value = 0.6
    try: bs.inputs["Specular IOR Level"].default_value = spec
    except Exception:
        try: bs.inputs["Specular"].default_value = spec
        except Exception: pass
    if subsurf: bs.inputs["Subsurface Weight"].default_value = subsurf
    return m

def flat(name, rgba, rough=0.7, spec=0.35, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = rgba
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    try: b.inputs["Specular IOR Level"].default_value = spec
    except Exception: pass
    return m

M = {}
# tex_audit.py 实测：所有草地 R/G=1.10~1.18（黄橄榄），B/G 只 0.64~0.77
# → 真绿必须靠 tint 把 R 压到 G 之下、把 B 补回来，光调亮度救不了色相
M["pave"] = pbr("pave", "precast_stone_paving", tint=(0.88, 0.92, 1.00), tile=(2.2, 2.2),
                rough_mul=1.15, spec=0.28)
M["granite"] = pbr("granite", "granite_tile_04", tint=(1.00, 0.99, 0.99), tile=(3.6, 3.6),
                   rough_mul=1.05, spec=0.32, bump_strength=1.0)
M["asphalt"] = pbr("asphalt", "asphalt_floor", tint=(0.62, 0.68, 0.82), tile=(6.0, 6.0),
                   rough_mul=1.10, spec=0.30)
M["grass"] = pbr("grass", "grass_path_2", tint=(0.64, 0.86, 0.76), tile=(3.0, 3.0),
                 rough_mul=1.20, spec=0.24, subsurf=0.09)
M["grassfar"] = pbr("grassfar", "grass_ground", tint=(0.72, 0.90, 0.86), tile=(45.0, 45.0),
                    rough_mul=1.15, spec=0.26)
M["tile"] = pbr("tile", "grey_roof_tiles", tint=(0.90, 0.97, 1.06), tile=(1.2, 1.2),
                rough_mul=1.0, spec=0.42)
M["stone"] = pbr("stone", "stone_wall_04", tint=(0.86, 0.88, 0.94), tile=(3.2, 3.2),
                 rough_mul=1.1, spec=0.30)
M["gold"] = flat("gold", (0.72, 0.52, 0.13, 1), 0.32, 0.6, 0.9)
M["wood"] = flat("wood", (0.145, 0.085, 0.050, 1), 0.70, 0.30)
M["steel"] = flat("steel", (0.24, 0.25, 0.27, 1), 0.45, 0.35, 0.75)
M["clothR"] = flat("clothR", (0.30, 0.030, 0.024, 1), 0.88, 0.20)
M["clothB"] = flat("clothB", (0.035, 0.115, 0.30, 1), 0.88, 0.20)
# 参考图（IMG_8537/8538）实测比例色：主体黄 sRGB(214,172,89)、腹部米白、手脚深橄榄
M["skinY"] = flat("skinY", (0.74, 0.47, 0.115, 1), 0.52, 0.34)
M["belly"] = flat("belly", (0.72, 0.66, 0.48, 1), 0.56, 0.34)
M["skinD"] = flat("skinD", (0.24, 0.175, 0.055, 1), 0.62, 0.30)
M["iris"] = flat("iris", (0.30, 0.46, 0.20, 1), 0.25, 0.55)
M["pupil"] = flat("pupil", (0.010, 0.012, 0.008, 1), 0.16, 0.60)
M["concrete"] = flat("concrete", (0.30, 0.30, 0.29, 1), 0.78, 0.26)
M["hill"] = flat("hill", (0.155, 0.170, 0.135, 1), 0.95, 0.15)
M["dtreetop"] = flat("dtreetop", (0.075, 0.100, 0.055, 1), 0.92, 0.18)
M["cityA"] = flat("cityA", (0.185, 0.190, 0.200, 1), 0.62, 0.35)
M["cityB"] = flat("cityB", (0.150, 0.145, 0.135, 1), 0.66, 0.33)
M["cityC"] = flat("cityC", (0.105, 0.110, 0.125, 1), 0.55, 0.42)
M["bluesign"] = flat("bluesign", (0.030, 0.085, 0.22, 1), 0.55, 0.40)

def windows(name, wall=(0.255, 0.250, 0.240, 1), glass=(0.045, 0.062, 0.090, 1)):
    """规则窗格。扫掠幕墙贴图在 ~1km 处空间频率 > 像素间距就会闪，程序化网格不会。"""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(sep.outputs["X"], comb.inputs["X"])
    nt.links.new(sep.outputs["Z"], comb.inputs["Y"])
    comb.inputs["Z"].default_value = 0.5
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / 3.6, 1 / 7.2, 1.0)
    nt.links.new(comb.outputs["Vector"], mp.inputs["Vector"])
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.offset = 0.0; br.inputs['Scale'].default_value = 1.0
    br.inputs['Color1'].default_value = wall
    br.inputs['Color2'].default_value = glass
    br.inputs['Mortar'].default_value = (0.16, 0.16, 0.16, 1)
    try: br.inputs['Mortar Size'].default_value = 0.045
    except Exception: pass
    try: br.inputs['Mortar Smooth'].default_value = 0.0
    except Exception: pass
    nt.links.new(mp.outputs["Vector"], br.inputs["Vector"])
    nt.links.new(br.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.45
    b.inputs["Metallic"].default_value = 0.25
    try: b.inputs["Specular IOR Level"].default_value = 0.5
    except Exception: pass
    return m
M["win"] = windows("win")

# 叶片卡片：alpha 抠图 + 逐棵顶点色
mleaf = bpy.data.materials.new("leaf"); mleaf.use_nodes = True
nt = mleaf.node_tree; bs = nt.nodes["Principled BSDF"]
t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(os.path.join(OUT, "leaf.png"))
nt.links.new(t.outputs["Color"], bs.inputs["Base Color"])
nt.links.new(t.outputs["Alpha"], bs.inputs["Alpha"])
bs.inputs["Roughness"].default_value = 0.78
try: bs.inputs["Specular IOR Level"].default_value = 0.20
except Exception: pass
try: mleaf.blend_method = 'HASHED'
except Exception: pass
at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "TreeTint"
lt = nt.nodes.new("ShaderNodeMixRGB"); lt.blend_type = 'MULTIPLY'
lt.inputs[0].default_value = 1.0
# 叶片贴图不透明处 sRGB(83,137,47)：R/G=0.61、B/G=0.34 —— 和扫描草地一样缺蓝，
# 直出是电子游戏绿；压红补蓝并把整体压暗一档
lt.inputs[2].default_value = (0.66, 0.83, 1.10, 1)
nt.links.new(t.outputs["Color"], lt.inputs[1])
vc = nt.nodes.new("ShaderNodeMixRGB"); vc.blend_type = 'MULTIPLY'
vc.inputs[0].default_value = 1.0
nt.links.new(lt.outputs["Color"], vc.inputs[1])
nt.links.new(at.outputs["Color"], vc.inputs[2])
nt.links.new(vc.outputs["Color"], bs.inputs["Base Color"])

# ══════════ 场景（全部走批量网格） ══════════
GR = {}
def g(k):
    if k not in GR: GR[k] = SL.Group()
    return GR[k]
GATE_Y = -14.0
rnd = random.Random(20261014)

# ── 地面：校园草坪 → 24km 大地面 ──
g("grassfar").add_box(24000, 24000, 0.10, (0, 0, -0.12))
g("grass").add_box(260, 240, 0.10, (-10, -60, -0.06))
g("pave").add_box(46, 32, 0.10, (0, 6, 0.05))
g("pave").add_box(30, 9.0, 0.10, (0, -3, 0.06))
g("pave").add_box(9.0, 150, 0.10, (0, -90, 0.06))
g("asphalt").add_box(120, 7.0, 0.10, (0, -26, 0.04))
g("asphalt").add_box(15, 260, 0.08, (0, -150, 0.05))
for s in (-1, 1):
    g("granite").add_box(0.5, 260, 0.22, (s * 7.8, -150, 0.11))

# ── 校门 ──
def gate():
    A = g("granite"); T = g("tile"); Go = g("gold")
    for i, (w, d, h, y) in enumerate(((19.4, 2.60, .34, .17), (18.6, 2.20, .30, .49),
                                      (17.8, 1.90, .26, .77))):
        A.add_box(w, d, h, (0, GATE_Y, y))
    for x, top in ((-3.2, 8.8), (3.2, 8.8), (-6.5, 7.3), (6.5, 7.3)):
        A.add_box(1.00, 1.00, .34, (x, GATE_Y, .26))
        A.add_box(1.26, 1.26, .26, (x, GATE_Y, .56))
        A.add(SL.sphere(.63, (x, GATE_Y, .86), scale=(1, 1, .42)), smooth=True)
        h = top - 1.05
        A.add_box(1.44, 1.44, h, (x, GATE_Y, (top + 1.05) / 2))
        A.add_box(1.60, 1.60, .17, (x, GATE_Y, top * .52))
        A.add_box(1.52, 1.52, .11, (x, GATE_Y, top * .56))
        A.add_box(1.80, 1.80, .24, (x, GATE_Y, top + .14))
        Go.add(SL.cyl(.34, .50, (x, GATE_Y, top + .48), n=20))
        Go.add(SL.sphere(.20, (x, GATE_Y, top + .78)), smooth=True)
        for s in (-1, 1):
            A.add_box(1.34, .40, .24, (x, GATE_Y + s * 1.06, .14))
            A.add_box(1.12, .26, .62, (x, GATE_Y + s * 1.06, .56))
            A.add(SL.cyl(.52, .20, (x, GATE_Y + s * 1.06, .62), axis='Y', n=24))
    def beam(w, h, y, x):
        A.add_box(w, .98, h, (x, GATE_Y, y))
        A.add_box(w * .96, .10, h * .30, (x, GATE_Y, y - h * .30))
        A.add_box(w + .5, 1.34, .20, (x, GATE_Y, y + h / 2 + .10))
        for s in (-1, 1):
            for zz in (.56, -.56):
                A.add_box(.20, .16, h * 1.5, (x + s * (w / 2 - .20), GATE_Y + zz, y - h / 2 - h * .75))
                A.add_box(.86, .16, h * .28, (x + s * (w / 2 - .52), GATE_Y + zz, y - h / 2 - .14))
    beam(7.6, 1.02, 7.95, 0); beam(3.5, .74, 6.55, -5.0); beam(3.5, .74, 6.55, 5.0)
    def dg(x, y):
        for i in range(4):
            s = .30 + i * .17
            A.add_box(s * 2.4, s * 1.5, s, (x, GATE_Y, y + i * .30))
            A.add_box(s * 3.0, s * 1.2, .05, (x, GATE_Y, y + i * .30 + .15))
    for x in (-3.2, 3.2): dg(x, 9.05)
    for x in (-6.5, -4.0, 4.0, 6.5): dg(x, 6.75)
    def roof(w, d, y, ox=0.0):
        n = int(w / .34)
        for i in range(n):
            x = ox - w / 2 + .17 + i * (w / n)
            T.add(SL.cyl(.145, d, (x, GATE_Y, y + .16), axis='Y', n=16))
            T.add(SL.cyl(.15, .07, (x, GATE_Y + d / 2 + .02, y + .16), axis='Y', n=16))
        T.add_box(w + .7, .52, .34, (ox, GATE_Y, y + .36))
        T.add_box(w + .7, .92, .20, (ox, GATE_Y + d / 2 - .22, y + .16))
        for s in (-1, 1):
            A.add_box(.42, .42, .62, (ox + s * (w / 2 + .14), GATE_Y, y + .62))
            Go.add(SL.sphere(.14, (ox + s * (w / 2 + .22), GATE_Y, y + .56)), smooth=True)
            Go.add(SL.cyl(.15, .44, (ox + s * (w / 2 + .22), GATE_Y, y + .84), n=14))
        Go.add(SL.cyl(.16, .30, (ox, GATE_Y, y + .66), n=14))
        Go.add(SL.sphere(.17, (ox, GATE_Y, y + .92)), smooth=True)
    roof(7.9, 1.55, 9.55); roof(3.9, 1.25, 7.35, -5.0); roof(3.9, 1.25, 7.35, 5.0)
    A.add_box(4.80, 1.60, .22, (0, GATE_Y, 8.45))
    # 匾额贴在主额枋的**正面**（原先放在枋顶，被檐口完全挡住，画面上根本看不见）
    g("bluesign").add_box(4.40, .12, .86, (0, GATE_Y + .56, 8.00))
    A.add_box(4.62, .10, 1.02, (0, GATE_Y + .50, 8.00))
    for x in (-5.0, 5.0):
        g("bluesign").add_box(2.40, .12, .62, (x, GATE_Y + .58, 6.72))
        A.add_box(2.58, .10, .76, (x, GATE_Y + .52, 6.72))
    for s in (-1, 1):
        cx = s * 15.6
        A.add_box(15.6, .92, .20, (cx, GATE_Y, .16))
        A.add_box(15.0, .60, .86, (cx, GATE_Y, .66))
        A.add_box(15.6, .82, .15, (cx, GATE_Y, 1.15))
        for i in range(6):
            x = s * (8.5 + i * 2.86)
            A.add_box(.46, .46, 1.34, (x, GATE_Y, .72))
            A.add_box(.60, .60, .13, (x, GATE_Y, 1.45))
            A.add(SL.sphere(.20, (x, GATE_Y, 1.66), scale=(1, 1, 1.25)), smooth=True)
gate()
g("clothR").add_box(5.9, .10, .90, (0, GATE_Y + .9, 6.72))

# ── 校园中景 ──
def bldg(x, y, w, d, h, mat, floors=True):
    g(mat).add_box(w, d, h, (x, y, h / 2))
    g("concrete").add_box(w + .6, d + .6, .5, (x, y, h + .25))
    if floors:
        for f in range(1, int(h / 3.6)):
            g("concrete").add_box(w + .18, d + .18, .16, (x, y, f * 3.6))
bldg(-118, -268, 74, 20, 21, "win")
bldg(104, -238, 56, 20, 24, "win")
bldg(-152, -330, 68, 18, 19, "win")
bldg(164, -196, 44, 26, 15, "stone")
# 照壁挪到轴线外 + 加瓦顶，否则它就是门洞正中一块没有细节的灰板
g("stone").add_box(9, 3.2, 5.0, (-27, -50, 2.5))
g("tile").add_box(10.2, 4.2, 0.34, (-27, -50, 5.17))
g("tile").add_box(9.6, 3.6, 0.30, (-27, -50, 5.45))
for s in (-1, 1):
    g("stone").add_box(0.7, 3.6, 5.6, (-27 + s * 4.9, -50, 2.8))

# ── 行道树 8~11m ──
TRN = [0]
def tree(x, y, scale=1.0, ncard=36):
    """树干 4m，树冠卡片 2.1~3.2m。
    卡片太大（v1 是 3.6m×缩放，最大到 7m）在 1080p 下就是一片片绿木板，
    必须小块多张，叶形贴图才有意义。"""
    th = 4.0 * scale
    W = g("wood")
    W.add(SL.cyl(.20 * scale, th, (x, y, th / 2), n=10))
    for k in range(3):
        a = k * 2.094 + rnd.uniform(-.4, .4)
        ln = 2.0 * scale
        W.add(SL.cyl(.085 * scale, ln, (x + math.cos(a) * ln * .28,
                                        y + math.sin(a) * ln * .28, th + ln * .32), n=8))
    # 逐棵顶点色：4000 棵同色同形是"假"的第一来源
    lum = rnd.uniform(0.62, 1.20); warm = rnd.uniform(-0.12, 0.12)
    col = (lum * (1 + warm), lum, lum * (1 - warm * 0.9), 1.0)
    L = g("leaf")
    for i in range(ncard):
        k = rnd.uniform(.72, 1.12) * scale
        th_ = rnd.uniform(0, math.pi * 2); ph = rnd.uniform(0, math.pi * .70)
        rad = (0.95 + 1.80 * rnd.random()) * scale
        m = SL.euler_m(rnd.uniform(-.75, .75), rnd.uniform(-.75, .75),
                       th_ + rnd.uniform(-1.0, 1.0))
        L.add_plane(2.9 * k, 2.9 * k,
                    (x + math.cos(th_) * math.sin(ph) * rad,
                     y + math.sin(th_) * math.sin(ph) * rad,
                     th + 0.55 * scale + math.cos(ph) * 2.5 * scale), m, color=col)
    TRN[0] += 1

for i in range(18):
    tree((-1 if i % 2 else 1) * (11.5 + (i % 3) * 1.1) + rnd.uniform(-1.6, 1.6),
         -20 - (i // 2) * 7.2 + rnd.uniform(-2.2, 2.2), rnd.uniform(.95, 1.40))
# 门后成片树林：否则透过门洞看到的是远处一面灰墙（比没楼还假）。
# 尺寸方差必须给足，否则一眼就是"同一棵树复制 40 遍"。
for i in range(26):
    x = rnd.uniform(-52, 52); y = -28 - rnd.uniform(0, 74)
    if abs(x) < 9.0: continue                      # 让开主路
    tree(x, y, rnd.uniform(0.80, 1.80), ncard=30)
for i in range(18):
    tree((-1 if i % 2 else 1) * (25 + (i // 2) % 4 * 6) + rnd.uniform(-3.0, 3.0),
         -32 - (i // 2) * 9.5 + rnd.uniform(-3.0, 3.0), rnd.uniform(1.0, 1.50))
for i in range(8):
    tree((-1 if i % 2 else 1) * (16.5 + (i // 2) * 3.2) + rnd.uniform(-1.4, 1.4),
         8.0 - (i // 2) * 3.0, rnd.uniform(.90, 1.25))

# ── 远景：树线 / 城市 / 丘陵（缺了它们地平线就是一条板边） ──
def ring(n, seed, rmin, rmax, mk, cx=0.0, cy=-260.0):
    rr = random.Random(seed)
    for i in range(n):
        a = rr.uniform(0, math.pi * 2); d = rmin + (rmax - rmin) * math.sqrt(rr.random())
        x = cx + math.cos(a) * d; y = cy + math.sin(a) * d
        if math.hypot(x, y) < 130: continue
        mk(rr, x, y, d)
def _dt(rr, x, y, d):
    r = rr.uniform(4.5, 9.0)          # 球心抬到 r*0.78，球底才落在地面
    g("dtreetop").add(SL.sphere(r, (x, y, r * .78), seg=8, rings=5, scale=(1, 1, .78)),
                      smooth=True)
ring(950, 7001, 150, 1500, _dt)
def _dc(rr, x, y, d):
    w = rr.uniform(60, 130) * (0.7 + d / 2600)
    h = rr.uniform(18, 62) * (0.6 + d / 3000)
    g(rr.choice(("cityA", "cityB", "cityC"))).add_box(w, w * rr.uniform(.6, 1.7), h, (x, y, h / 2))
ring(520, 7002, 1400, 6200, _dc, cy=-300)
def _dh(rr, x, y, d):
    r = rr.uniform(700, 2200); k = 0.22
    g("hill").add(SL.sphere(r, (x, y, r * k), seg=12, rings=6, scale=(1, 1, k)),
                  smooth=True)
ring(14, 7003, 5200, 11000, _dh)

# ── 报到日道具 ──
def tent(x, y, key):
    C = g(key)
    C.add_box(3.0, 3.0, .10, (x, y, 2.42))
    C.add_box(3.0, .06, .34, (x, y - 1.52, 2.16))
    C.add_box(3.0, .06, .34, (x, y + 1.52, 2.16))
    for dx in (-1.4, 1.4):
        for dy in (-1.4, 1.4):
            g("steel").add(SL.cyl(.045, 2.42, (x + dx, y + dy, 1.21), n=8))
for (tx, ty, tc) in ((-9.0, -5.0, "clothR"), (8.5, -3.0, "clothB"), (-13.5, -10.0, "clothB")):
    tent(tx, ty, tc)
for s in (-1, 1):
    for k in range(3):
        x, y = s * 10.5, -8 - k * 14
        g("steel").add(SL.cyl(.09, 5.2, (x, y, 2.6), n=10))
        g("steel").add_box(1.0, .10, .10, (x, y, 5.15))
        g("steel").add_box(.46, .26, .18, (x - s * .46, y, 5.00))

# ── 奶娃：按三张参考图重建 ─────────────────────────────────────────
# 参考图量得（IMG_8538，脚底→头顶 H）：身体最宽 0.537H@z0.52、肩 0.35H@z0.78、
# 头宽 0.226H@z0.92、眼距 0.136H、眼径 0.074H、裆 z0.31。
# 所以**不是一颗蛋**：小头 + 溜肩 + 大肚 + 两条短腿 + 蹼状大脚。
BODY = [(0.250, 0.000), (0.262, 0.090), (0.280, 0.150), (0.305, 0.196),
        (0.340, 0.228), (0.375, 0.246), (0.442, 0.263), (0.521, 0.269),
        (0.600, 0.257), (0.662, 0.235), (0.720, 0.208), (0.760, 0.184),
        (0.795, 0.152), (0.828, 0.137), (0.865, 0.129), (0.900, 0.125),
        (0.930, 0.114), (0.960, 0.089), (0.982, 0.052), (1.000, 0.000)]

def _pw(TAB, t):
    if t <= TAB[0][0]: return TAB[0][1]
    if t >= TAB[-1][0]: return TAB[-1][1]
    for i in range(len(TAB) - 1):
        a, b = TAB[i], TAB[i + 1]
        if t <= b[0]:
            k = (t - a[0]) / max(1e-9, b[0] - a[0])
            k = k * k * (3 - 2 * k)
            return a[1] + (b[1] - a[1]) * k
    return TAB[-1][1]

def body_r(t):  return _pw(BODY, t)
def head_sh(t): return 0.030 * _pw([(0.76, 0.0), (0.92, 1.0)], t)
def belly_b(t): return 0.075 * math.exp(-((t - 0.50) / 0.20) ** 2)

def body_pt(t, a):
    """a=0 正前方(+y)；返回身体表面点（含前腹外凸与前倾小头）"""
    r = body_r(t)
    x = math.sin(a) * r; y = math.cos(a) * r
    h = math.hypot(x, y) or 1e-6
    return x, y + (y / h) * belly_b(t) + head_sh(t)

HX, HY, HS = 2.40, -5.0, 2.05
HM = Matrix.Scale(HS, 3)
def U(prim):
    """把单位空间图元搬到奶娃所在位置（Group.add 第二参是颜色，别直接塞矩阵）"""
    v, f = prim
    return SL._tf(v, HM, (HX, HY, 0)), f

hb = g("skinY"); hd = g("skinD")
N = 96                     # 腹部贴片是按面判定的，角分辨率低了椭圆边会有台阶
TS = [0.250 + (1.0 - 0.250) * i / 78 for i in range(79)]
hv, hf, hmi = [], [], []
for t in TS:
    for i in range(N):
        x, y = body_pt(t, i * 2 * math.pi / N)
        hv.append((x, y, t))
for j in range(len(TS) - 1):
    for i in range(N):
        a = j * N + i; b = j * N + (i + 1) % N
        c = (j + 1) * N + i; d = (j + 1) * N + (i + 1) % N
        hf.append((a, c, b)); hf.append((b, c, d))
        t0 = (TS[j] + TS[j + 1]) / 2
        ang = math.atan2(math.sin(i * 2 * math.pi / N), math.cos(i * 2 * math.pi / N))
        amax = 1.02 * math.sqrt(max(0.0, 1 - ((t0 - 0.52) / 0.215) ** 2))
        mi = 1 if abs(ang) < amax else 0
        hmi.append(mi); hmi.append(mi)
hb.add_face(SL._tf(hv, HM, (HX, HY, 0)), hf, smooth=True)
hb.mi[-len(hmi):] = hmi

# 腿：粗短大腿 → 膝 → 小腿（参考图里腿是很粗的，且短）
for s in (-1, 1):
    hb.add(U(SL.seg((s * .120, .012, .340), (s * .132, .026, .190), .105, .072, 16)), smooth=True)
    hb.add(U(SL.seg((s * .132, .026, .190), (s * .130, .034, .062), .072, .052, 16)), smooth=True)
    hb.add(U(SL.sphere(.076, (s * .132, .026, .188))), smooth=True)
    # 脚：大扁掌 + 4 根张开的长趾（深橄榄）
    hd.add(U(SL.sphere(1.0, (s * .134, .082, .032), scale=(.072, .108, .032))), smooth=True)
    for k in range(4):
        a = (k - 1.5) * 0.28
        hd.add(U(SL.seg((s * .134 + math.sin(a) * .034, .140, .028),
                        (s * .134 + math.sin(a) * .128, .258, .018), .023, .015, 8)), smooth=True)

# 臂：肩→肘→腕，双手在腹前合拢（参考图的标志性姿势）
for s in (-1, 1):
    hb.add(U(SL.seg((s * .148, .030, .770), (s * .250, .122, .568), .076, .056, 14)), smooth=True)
    hb.add(U(SL.seg((s * .250, .122, .568), (s * .098, .300, .470), .056, .045, 14)), smooth=True)
    hb.add(U(SL.sphere(.058, (s * .086, .322, .462))), smooth=True)          # 手掌
    for k in range(4):                                                        # 四指朝上，双手交错合拢
        a = (k - 1.5) * 0.30
        hd.add(U(SL.seg((s * .086 + math.sin(a) * .030, .334, .470),
                        (s * .062 + math.sin(a) * .050, .340, .542), .020, .014, 8)), smooth=True)
    hd.add(U(SL.seg((s * .128, .296, .458), (s * .162, .330, .424), .020, .014, 8)), smooth=True)

# 眼：黄眼球 + 绿虹膜 + 黑瞳，沿头表面法线一层层往外推
for s in (-1, 1):
    ang = s * 0.55
    ex, ey = body_pt(0.902, ang)
    nx, ny = ex, ey - head_sh(0.902)
    nl = math.hypot(nx, ny) or 1e-6; nx, ny = nx / nl, ny / nl
    hb.add(U(SL.sphere(.050, (ex, ey, .902))), smooth=True)
    g("iris").add(U(SL.sphere(.038, (ex + nx * .034, ey + ny * .034, .902))), smooth=True)
    g("pupil").add(U(SL.sphere(.019, (ex + nx * .050, ey + ny * .050, .902))), smooth=True)

# 嘴：一道细横线
mx_, my_ = body_pt(0.840, 0.0)
hd.add(U(SL.sphere(.046, (mx_, my_ + .002, .840), scale=(1, .30, .18))), smooth=True)
print("SCENE BUILT  groups=%d  trees=%d" % (len(GR), TRN[0]))

# ══════════ 落成网格 ══════════
BEV = {"granite": 0.035, "tile": 0.030}
MULTI = {"skinY": ["skinY", "belly"]}      # 身体 + 腹部浅色贴片
MADE = {}
for k, gg in GR.items():
    if k == "leaf":
        mat = mleaf
    elif k in MULTI:
        mat = [M[x] for x in MULTI[k]]
    else:
        mat = M[k]
    MADE[k] = gg.build("M_" + k, mat, bevel=BEV.get(k, 0.0), seg=2,
                       col_attr="TreeTint" if k == "leaf" else None)

# ── 诊断钩子：ONLY=leaf 只显该组；FLAT=leaf 换成洋红自发光 ──
if os.environ.get("ONLY"):
    keep = set(os.environ["ONLY"].split(","))
    for k, o in MADE.items():
        o.hide_render = k not in keep
if os.environ.get("FLAT"):
    for k in os.environ["FLAT"].split(","):
        o = MADE.get(k)
        if not o: continue
        mm = bpy.data.materials.new("dbg_" + k); mm.use_nodes = True
        nb = mm.node_tree.nodes["Principled BSDF"]
        nb.inputs["Base Color"].default_value = (0.85, 0.05, 0.75, 1)
        nb.inputs["Emission Color"].default_value = (0.85, 0.05, 0.75, 1)
        nb.inputs["Emission Strength"].default_value = 1.0
        o.data.materials.clear(); o.data.materials.append(mm)
if os.environ.get("DIAG"):
    for k, o in sorted(MADE.items()):
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        zs = [v.z for v in bb]; xs = [v.x for v in bb]; ys = [v.y for v in bb]
        print("DIAG %-10s v=%6d f=%6d  x[%7.1f,%7.1f] y[%7.1f,%7.1f] z[%6.2f,%6.2f]  col=%s"
              % (k, len(o.data.vertices), len(o.data.polygons),
                 min(xs), max(xs), min(ys), max(ys), min(zs), max(zs),
                 [c.name for c in o.data.color_attributes]))

# ══════════ 天空与太阳 ══════════
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
wnt = w.node_tree; bg = wnt.nodes["Background"]
sky = wnt.nodes.new("ShaderNodeTexSky")
sky.sky_type = 'NISHITA'
sky.sun_elevation = math.radians(SKY_ELEV)
sky.sun_rotation = math.radians(SKY_ROT)
sky.air_density = 1.0; sky.dust_density = 0.9; sky.ozone_density = 1.0
sky.sun_intensity = 0.30
TINT = (0.90, 1.00, 1.38)
tn = wnt.nodes.new("ShaderNodeMixRGB"); tn.blend_type = 'MULTIPLY'
tn.inputs[0].default_value = 1.0; tn.inputs[2].default_value = (TINT[0], TINT[1], TINT[2], 1)
wnt.links.new(sky.outputs["Color"], tn.inputs[1])
wnt.links.new(tn.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = SKYSTR

bpy.ops.object.light_add(type='SUN', location=(40, -10, 34))
sun = bpy.context.object; sun.name = "SUN"
sun.data.energy = SUN_E
sun.data.angle = math.radians(0.53)
SUN_AZ = SKY_ROT + 180.0
sun.rotation_euler = (math.radians(90.0 - SKY_ELEV), 0, math.radians(SUN_AZ))
sun.data.color = (1.0, 0.935, 0.83)

# ══════════ 空气透视 ══════════
vl = sc.view_layers[0]
vl.use_pass_mist = True; vl.use_pass_z = True
sc.world.mist_settings.start = MIST_START
sc.world.mist_settings.depth = MIST_DEPTH
sc.world.mist_settings.falloff = 'LINEAR'
SKY_DEPTH = float(os.environ.get("SKYD", "19000"))
try:
    pj = json.load(open("/tmp/scene/_skyprobe.json"))
    HAZE = tuple(v * (SKYSTR / pj["strength"]) for v in pj["horizon"]) + (1.0,)
    print("HAZE 实测(探针 %.3f):" % pj["strength"], tuple(round(v, 4) for v in HAZE[:3]))
except Exception as e:
    HAZE = (0.30, 0.36, 0.58, 1.0); print("!! 兜底雾色:", e)

# ══════════ 相机 ══════════
CAMS = {
    "hero":   ((4.8, 2.4, 2.20), (0.2, -10.0, 2.4), 30.0),
    "hero2":  ((5.9, 3.4, 2.05), (-0.4, -11.5, 3.4), 30.0),
    "threeq": ((11.5, 1.5, 2.30), (-1.0, GATE_Y, 4.0), 30.0),
    "low":    ((5.0, 2.2, 1.75), (0, GATE_Y, 4.2), 24.0),
    "wide":   ((8.0, 10.6, 5.25), (0, GATE_Y, 0.85), 24.0),
    "mascot": ((2.4, 0.6, 1.20), (2.4, -5.0, 1.02), 62.0),
    "gate":   ((0.0, -2.0, 7.6), (0, GATE_Y, 7.6), 35.0),
}
CAM = os.environ.get("CAM", "hero")
if os.environ.get("ORBIT") is not None:
    # 环绕镜头：绕 (0.6,-9.0) 摆 +-22°，用于出 3~4 秒短片
    f = int(os.environ["ORBIT"]); NF = int(os.environ.get("ORBIT_N", "72"))
    a = math.radians(-22.0 + 44.0 * f / max(1, NF - 1))
    R = 14.0
    loc = (0.6 + math.sin(a) * R, -9.0 + math.cos(a) * R, 2.55)
    tgt = (0.2, -10.5, 3.0); lens = 30.0
    CAM = "orbit%03d" % f
else:
    loc, tgt, lens = CAMS[CAM]
bpy.ops.object.camera_add(location=loc)
cam = bpy.context.object; cam.name = "CAM"
cam.data.lens = lens; cam.data.sensor_width = 36.0
cam.data.clip_start = 0.1; cam.data.clip_end = 60000.0
cam.rotation_euler = (Vector(loc) - Vector(tgt)).to_track_quat('Z', 'Y').to_euler()
if os.environ.get("FSTOP"):
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = (Vector(loc) - Vector(tgt)).length
    cam.data.dof.aperture_fstop = float(os.environ["FSTOP"])
sc.camera = cam

# ══════════ 合成器：Mist × 深度遮罩 ══════════
sc.use_nodes = True
cnt = sc.node_tree
for n in list(cnt.nodes): cnt.nodes.remove(n)
rl = cnt.nodes.new("CompositorNodeRLayers")
comp = cnt.nodes.new("CompositorNodeComposite")
mth = cnt.nodes.new("CompositorNodeMath"); mth.operation = 'LESS_THAN'
mth.inputs[1].default_value = SKY_DEPTH
cnt.links.new(rl.outputs['Depth'], mth.inputs[0])
mul = cnt.nodes.new("CompositorNodeMath"); mul.operation = 'MULTIPLY'
cnt.links.new(rl.outputs['Mist'], mul.inputs[0])
cnt.links.new(mth.outputs[0], mul.inputs[1])
fac = cnt.nodes.new("CompositorNodeMath"); fac.operation = 'MULTIPLY'
fac.inputs[1].default_value = 0.95
cnt.links.new(mul.outputs[0], fac.inputs[0])
try:
    mix = cnt.nodes.new("CompositorNodeMixRGB")
except Exception:
    mix = None
if mix is None:
    mix = cnt.nodes.new("CompositorNodeMix"); mix.data_type = 'RGBA'
mix.blend_type = 'MIX'
mix.inputs[2].default_value = HAZE
cnt.links.new(fac.outputs[0], mix.inputs[0])
cnt.links.new(rl.outputs['Image'], mix.inputs[1])

# ── 后处理：AAA 画面的"游戏感"有一半在调色与镜头效应上 ──
# 合成器在**场景线性**里工作（早于 Filmic），所以阈值 1.0 = 真正的白点
node = mix
if os.environ.get("NOFX") != "1":
    # 1) 色彩分级：阴影偏冷、高光偏暖（lift/gamma/gain）
    #    4.5 里 Lift/Gamma/Gain 各有**两个同名 socket**（float 在前、color 在后），
    #    按名字取会拿到 float 那个并报 "expected a float, not tuple" → 用索引取 color。
    try:
        cb = cnt.nodes.new("CompositorNodeColorBalance")
        cb.correction_method = 'LIFT_GAMMA_GAIN'
        cb.inputs[3].default_value = (0.975, 0.990, 1.030, 1.0)   # Lift  (color)
        cb.inputs[5].default_value = (1.010, 1.000, 0.985, 1.0)   # Gamma (color)
        cb.inputs[7].default_value = (1.045, 1.012, 0.952, 1.0)   # Gain  (color)
        cnt.links.new(node.outputs[0], cb.inputs['Image'])
        node = cb
    except Exception as e:
        print("!! ColorBalance 跳过:", e)
    # 2) 泛光：只在真正过阈值的地方晕开
    try:
        gl = cnt.nodes.new("CompositorNodeGlare")
        gl.glare_type = 'FOG_GLOW'
        gl.quality = 'MEDIUM'
        gl.threshold = 1.15
        gl.size = 8
        gl.mix = -0.80
        cnt.links.new(node.outputs[0], gl.inputs['Image'])
        node = gl
    except Exception as e:
        print("!! Glare 跳过:", e)
    # 3) 暗角：椭圆遮罩大幅模糊 → 当 Mix 的 Fac，往黑里压
    try:
        mk = cnt.nodes.new("CompositorNodeEllipseMask")
        mk.x = 0.5; mk.y = 0.5
        mk.width = float(os.environ.get("VIGW", "1.55"))
        mk.height = float(os.environ.get("VIGH", "1.55"))
        bl = cnt.nodes.new("CompositorNodeBlur")
        bl.size_x = 140; bl.size_y = 140
        cnt.links.new(mk.outputs['Mask'], bl.inputs['Image'])
        one = cnt.nodes.new("CompositorNodeMath"); one.operation = 'SUBTRACT'
        one.inputs[0].default_value = 1.0
        cnt.links.new(bl.outputs['Image'], one.inputs[1])   # 中心 0 → 边缘 1
        m2 = cnt.nodes.new("CompositorNodeMath"); m2.operation = 'MULTIPLY'
        m2.inputs[1].default_value = float(os.environ.get("VIG", "0.16"))
        cnt.links.new(one.outputs[0], m2.inputs[0])
        dk = cnt.nodes.new("CompositorNodeMixRGB"); dk.blend_type = 'MIX'
        dk.inputs[2].default_value = (0, 0, 0, 1)
        cnt.links.new(m2.outputs[0], dk.inputs[0])
        cnt.links.new(node.outputs[0], dk.inputs[1])
        node = dk
    except Exception as e:
        print("!! 暗角跳过:", e)
    # 4) 镜头畸变 + 轻微色散（"这是相机拍的"的强暗示）
    try:
        ld = cnt.nodes.new("CompositorNodeLensdist")
        ld.inputs['Distortion'].default_value = 0.003
        ld.inputs['Dispersion'].default_value = 0.0025
        try: ld.use_fit = True
        except Exception: pass
        cnt.links.new(node.outputs[0], ld.inputs['Image'])
        node = ld
    except Exception as e:
        print("!! Lensdist 跳过:", e)

cnt.links.new(node.outputs[0], comp.inputs['Image'])

TAG = os.environ.get("TAG", "v2")
sc.render.filepath = os.path.join(OUT, "%s_%s_%dx%d_%dspp.png" % (TAG, CAM, RES_X, RES_Y, SPP))
import time
t0 = time.time(); bpy.ops.render.render(write_still=True)
print("RENDER_SECONDS %.1f  (%dx%d %dspp cam=%s skystr=%s sun=%.2f)"
      % (time.time() - t0, RES_X, RES_Y, SPP, CAM, SKYSTR, SUN_E))
