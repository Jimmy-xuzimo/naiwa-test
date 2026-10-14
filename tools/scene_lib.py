"""批量建网格的极简几何库。

为什么不用 bpy.ops：每次 primitive_*_add 都会触发一次全场景 depsgraph 更新，
N 个物体就是 O(N²)。上一版 4000 个物体要跑 8 分钟，其中 95% 是建场不在渲染。
这里改成纯 Python 生成顶点/面，按材质归并成 ~20 个网格对象，一次 from_pydata。
"""
import math
from mathutils import Vector, Matrix, Euler

def _tf(verts, mtx=None, loc=(0, 0, 0)):
    lv = Vector(loc)
    if mtx is None:
        return [(v[0] + lv.x, v[1] + lv.y, v[2] + lv.z) for v in verts]
    return [tuple((mtx @ Vector(v)) + lv) for v in verts]

def euler_m(rx=0.0, ry=0.0, rz=0.0):
    return Euler((rx, ry, rz), 'XYZ').to_matrix()

# ── 图元：返回 (verts, faces) ──────────────────────────────
def box(w, d, h, loc=(0, 0, 0), mtx=None):
    x, y, z = w / 2, d / 2, h / 2
    v = [(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z),
         (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
         (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return _tf(v, mtx, loc), f

def plane(sx, sy, loc=(0, 0, 0), mtx=None):
    x, y = sx / 2, sy / 2
    v = [(-x, -y, 0), (x, -y, 0), (x, y, 0), (-x, y, 0)]
    return _tf(v, mtx, loc), [(0, 1, 2, 3)]

PLANE_UV = ((0, 0), (1, 0), (1, 1), (0, 1))

def cyl(r, ln, loc=(0, 0, 0), mtx=None, n=16, axis='Z'):
    if axis == 'X': mtx = (mtx or Matrix.Identity(3)) @ euler_m(0, math.pi / 2, 0)
    if axis == 'Y': mtx = (mtx or Matrix.Identity(3)) @ euler_m(math.pi / 2, 0, 0)
    v, f = [], []
    for h in (-ln / 2, ln / 2):
        for i in range(n):
            a = 2 * math.pi * i / n
            v.append((math.cos(a) * r, math.sin(a) * r, h))
    for i in range(n):
        j = (i + 1) % n
        f.append((i, j, n + j, n + i))
    b, t = 2 * n, 2 * n + 1
    v.append((0, 0, -ln / 2)); v.append((0, 0, ln / 2))
    for i in range(n):
        j = (i + 1) % n
        f.append((b, j, i)); f.append((t, n + i, n + j))
    return _tf(v, mtx, loc), f

def sphere(r, loc=(0, 0, 0), mtx=None, seg=16, rings=8, scale=(1, 1, 1)):
    sx, sy, sz = scale
    v = [(0, 0, r * sz)]
    for j in range(1, rings):
        ph = math.pi * j / rings
        sr, cz = math.sin(ph), math.cos(ph)
        for i in range(seg):
            a = 2 * math.pi * i / seg
            v.append((sr * math.cos(a) * r * sx, sr * math.sin(a) * r * sy, cz * r * sz))
    v.append((0, 0, -r * sz))
    top, bot = 0, len(v) - 1
    f = []
    for i in range(seg):
        f.append((top, 1 + i, 1 + (i + 1) % seg))
    for j in range(rings - 2):
        for i in range(seg):
            i2 = (i + 1) % seg
            f.append((1 + j * seg + i, 1 + j * seg + i2,
                      1 + (j + 1) * seg + i2, 1 + (j + 1) * seg + i))
    base = 1 + (rings - 2) * seg
    for i in range(seg):
        f.append((bot, base + (i + 1) % seg, base + i))
    return _tf(v, mtx, loc), f

def seg(p0, p1, r0, r1, n=12, caps=True):
    """两点之间的锥台（大腿/小腿/手臂/指头都用它）"""
    p0 = Vector(p0); p1 = Vector(p1)
    d = p1 - p0; ln = d.length
    m = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix()
    v, f = [], []
    for r, h in ((r0, -ln / 2), (r1, ln / 2)):
        for i in range(n):
            a = 2 * math.pi * i / n
            v.append((math.cos(a) * r, math.sin(a) * r, h))
    for i in range(n):
        j = (i + 1) % n
        f.append((i, j, n + j, n + i))
    if caps:
        b, t = 2 * n, 2 * n + 1
        v.append((0, 0, -ln / 2)); v.append((0, 0, ln / 2))
        for i in range(n):
            j = (i + 1) % n
            f.append((b, j, i)); f.append((t, n + i, n + j))
    return _tf(v, m, (p0 + p1) / 2), f

# ── 累积器 ────────────────────────────────────────────────
class Group:
    """按材质把图元拼成一个网格。add() 接受 (verts, faces)。"""
    def __init__(self):
        self.v = []; self.f = []; self.sm = []; self.col = []
        self.uvf = []; self.mi = []

    def add(self, prim, color=None, smooth=False, uv=None, mi=0):
        verts, faces = prim
        o = len(self.v)
        self.v.extend(verts)
        for fc in faces:
            self.f.append(tuple(o + i for i in fc))
            self.sm.append(smooth)
            self.col.append(color)
            self.uvf.append(uv)
            self.mi.append(mi)
        return self

    def add_box(self, w, d, h, loc, color=None):
        return self.add(box(w, d, h, loc), color)

    def add_plane(self, sx, sy, loc, mtx=None, color=None):
        return self.add(plane(sx, sy, loc, mtx), color=color, uv=PLANE_UV)

    def add_face(self, verts, faces, color=None, smooth=False, mi=0):
        return self.add((verts, faces), color=color, smooth=smooth, mi=mi)

    def build(self, name, mat, bevel=0.0, seg=2, angle=25.0, col_attr=None,
              collection=None):
        import bpy
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        changed = me.validate(verbose=False)
        if changed or len(me.polygons) != len(self.f):
            # validate 可能删掉退化面 → 逐面属性会错位，宁可报出来
            raise RuntimeError("%s: validate 改动了拓扑 (%d 面 → %d)，"
                               "逐面颜色/平滑标记不可靠" % (name, len(self.f), len(me.polygons)))
        ob = bpy.data.objects.new(name, me)
        (collection or bpy.context.scene.collection).objects.link(ob)
        mats = mat if isinstance(mat, (list, tuple)) else [mat]
        for k in mats:
            ob.data.materials.append(k)
        for i, p in enumerate(me.polygons):
            p.use_smooth = self.sm[i]
            if len(mats) > 1:
                p.material_index = self.mi[i]
        if bevel > 0:
            mm = ob.modifiers.new("b", "BEVEL")
            mm.width = bevel; mm.segments = seg
            mm.limit_method = 'ANGLE'; mm.angle_limit = math.radians(angle)
            mm.harden_normals = False
            bpy.context.view_layer.objects.active = ob
            ob.select_set(True)
            bpy.ops.object.modifier_apply(modifier=mm.name)
        if col_attr and any(c is not None for c in self.col):
            me2 = ob.data
            ca = me2.color_attributes.new(name=col_attr, type='FLOAT_COLOR',
                                          domain='CORNER')
            li = 0
            for fi, p in enumerate(me2.polygons):
                c = self.col[fi] or (1, 1, 1, 1)
                for _ in range(p.loop_total):
                    ca.data[li].color = c; li += 1
        # from_pydata 不建 UV 层；没有 UV 层时 TexImage(FLAT) 会只采 (0,0) 一个像素
        if any(u is not None for u in self.uvf):
            uvl = ob.data.uv_layers.new(name="UVMap")
            li = 0
            for fi, p in enumerate(ob.data.polygons):
                u = self.uvf[fi]
                for j in range(p.loop_total):
                    uvl.data[li].uv = u[j] if u else (0.0, 0.0)
                    li += 1
        return ob
