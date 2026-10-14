import bpy, math, os, sys
from mathutils import Vector

OUT="/tmp/gate_build"; os.makedirs(OUT, exist_ok=True)
RES=int(os.environ.get("BAKE_RES","1024"))

def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def cube(w,h,d,x,y,z,bevel=0.0,seg=2,rot=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x,y,z))
    o=bpy.context.object
    o.scale=(w,h,d)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if rot: o.rotation_euler=rot
    if bevel>0:
        m=o.modifiers.new("b","BEVEL")
        m.width=bevel; m.segments=seg
        m.limit_method='ANGLE'; m.angle_limit=math.radians(25)
        bpy.ops.object.modifier_apply(modifier=m.name)
    return o

def cyl(r,d,x,y,z,rot=None,verts=10):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d, vertices=verts, location=(x,y,z))
    o=bpy.context.object
    if rot: o.rotation_euler=rot
    return o

def sph(r,x,y,z,sub=2):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=14, ring_count=8, location=(x,y,z))
    return bpy.context.object

# ══════════════ 高模：带线脚/雕饰/瓦垄 ══════════════
clear()
HI=[]
B=0.035                     # 高模倒角半径

# 台基：三层收分，每层带压边线脚
HI.append(cube(19.4,.34,2.60, 0,.17,0, .05,1))
HI.append(cube(18.9,.06,2.34, 0,.37,0, .02,2))
HI.append(cube(18.6,.30,2.20, 0,.49,0, .05,1))
HI.append(cube(18.1,.06,1.98, 0,.67,0, .02,2))
HI.append(cube(17.8,.26,1.90, 0,.77,0, .05,1))

def hi_pillar(x,top):
    HI.append(cube(1.00,.34,1.00, x,.26,0, B,2))          # 柱础下
    HI.append(cube(1.26,.26,1.26, x,.56,0, B,2))          # 柱础上
    c=sph(.63,x,.86,0); c.scale=(1,.42,1)                 # 覆盆
    HI.append(c)
    h=top-1.05
    HI.append(cube(1.44,h,1.44, x,(top+1.05)/2,0, B,1))   # 柱身
    HI.append(cube(1.60,.17,1.60, x,top*.52,0, .03,2))    # 线脚 1
    HI.append(cube(1.52,.11,1.52, x,top*.56,0, .02,2))    # 线脚 2
    HI.append(cube(1.80,.24,1.80, x,top+.14,0, .04,2))    # 柱头
    HI.append(cyl(.34,.50,x,top+.48,0,verts=12))          # 宝珠座
    HI.append(sph(.20,x,top+.78,0))
    for s in (-1,1):                                      # 抱鼓石
        HI.append(cube(1.34,.24,.40, x,.14,s*1.06, .05,2))
        HI.append(cube(1.12,.62,.26, x,.56,s*1.06, .05,2))
        d=cyl(.52,.20,x,.62,s*1.06,rot=(math.pi/2,0,0),verts=12); HI.append(d)
for x,t in ((-3.2,8.8),(3.2,8.8),(-6.5,7.3),(6.5,7.3)): hi_pillar(x,t)

def hi_beam(w,h,y,x):
    HI.append(cube(w,h,.98, x,y,0, .04,2))                # 额枋
    HI.append(cube(w*.96,h*.30,.10, x,y-h*.30,.50, .01,2))# 下缘凹槽
    HI.append(cube(w+.5,.20,1.34, x,y+h/2+.10,0, .04,2))  # 檐板
    for s in (-1,1):                                      # 雀替
        for z in (.56,-.56):
            HI.append(cube(.20,h*1.5,.16, x+s*(w/2-.20),y-h/2-h*.75,z, .03,2))
            HI.append(cube(.86,h*.28,.16, x+s*(w/2-.52),y-h/2-.14,z, .03,2))
hi_beam(7.6,1.02,7.95,0); hi_beam(3.5,.74,6.55,-5.0); hi_beam(3.5,.74,6.55,5.0)

def hi_dg(x,y):
    for i in range(4):
        s=.30+i*.17
        HI.append(cube(s*2.4,s,s*1.5, x,y+i*.30,0, .022,2))
        HI.append(cube(s*3.0,.05,s*1.2, x,y+i*.30+.15,0, .012,2))
for x in (-3.2,3.2):       hi_dg(x,9.05)
for x in (-6.5,-4.0,4.0,6.5): hi_dg(x,6.75)

def hi_roof(w,d,y,ox=0.0):
    n=int(w/.36)
    for i in range(n):                                    # 瓦垄
        x=ox-w/2+.18+i*(w/n)
        HI.append(cyl(.15,d,x,y+.16,0,rot=(math.pi/2,0,0),verts=8))
        HI.append(cyl(.155,.07,x,y+.16,d/2+.02,rot=(math.pi/2,0,0),verts=8))  # 瓦当
    HI.append(cube(w+.7,.34,.52, ox,y+.36,0, .05,2))      # 正脊
    HI.append(cube(w+.7,.20,.92, ox,y+.16,d/2-.22, .03,2))
    for s in (-1,1):                                      # 鸱吻
        HI.append(cube(.42,.62,.42, ox+s*(w/2+.14),y+.62,0, .04,2))
        HI.append(sph(.14,ox+s*(w/2+.22),y+.56,0))
        c=cyl(.15,.44,ox+s*(w/2+.22),y+.84,0,verts=8); HI.append(c)
    HI.append(cyl(.16,.30,ox,y+.66,0,verts=8))           # 宝顶
    HI.append(sph(.17,ox,y+.92,0))
hi_roof(7.9,1.55,9.55,0.0)
hi_roof(3.9,1.25,7.35,-5.0)
hi_roof(3.9,1.25,7.35,5.0)

HI.append(cube(4.5,1.34,.20, 0,8.45,.55, .03,2))          # 匾额框

for s in (-1,1):                                          # 围栏
    cx=s*15.6
    HI.append(cube(15.6,.20,.92, cx,.16,0, .04,2))
    HI.append(cube(15.0,.86,.60, cx,.66,0, .03,2))
    HI.append(cube(15.6,.15,.82, cx,1.15,0, .04,2))
    for i in range(6):
        x=s*(8.5+i*2.86)
        HI.append(cube(.46,1.34,.46, x,.72,0, .04,2))
        HI.append(cube(.60,.13,.60, x,1.45,0, .03,2))
        f=sph(.20,x,1.66,0); f.scale=(1,1.25,1); HI.append(f)

bpy.ops.object.select_all(action='DESELECT')
for o in HI: o.select_set(True)
bpy.context.view_layer.objects.active=HI[0]
bpy.ops.object.join()
HIGH=bpy.context.object; HIGH.name="HIGH"
print("HIGH tris:", len(HIGH.data.polygons))

# ══════════════ 交付策略：直接上高模 + 自烘焙 AO ══════════════
# 这套校门一共才 2 万面，对现代 GPU 是零成本；而高模自带全部线脚与瓦垄，
# 比「低模 + 法线贴图假装」在剪影上就赢一大截。所以不做高低模对烘，
# 只对高模自身烘一张 AO，把斗拱凹角、雀替下缘、瓦垄缝里的脏影子补上。
bpy.ops.object.select_all(action='DESELECT')
HIGH.select_set(True); bpy.context.view_layer.objects.active=HIGH
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004)
bpy.ops.object.mode_set(mode='OBJECT')

sc=bpy.context.scene
sc.render.engine='CYCLES'
sc.cycles.device='CPU'
sc.cycles.samples=int(os.environ.get("BAKE_SAMPLES","64"))
sc.render.bake.margin=8

mat=bpy.data.materials.new("GateMat"); mat.use_nodes=True
nt=mat.node_tree
HIGH.data.materials.clear()
HIGH.data.materials.append(mat)
iA=bpy.data.images.new("GATE_AO", RES, RES, alpha=False)
tA=nt.nodes.new("ShaderNodeTexImage"); tA.image=iA; tA.location=(-700,0)
for n in nt.nodes: n.select=False
tA.select=True; nt.nodes.active=tA
bpy.ops.object.select_all(action='DESELECT')
HIGH.select_set(True); bpy.context.view_layer.objects.active=HIGH
bpy.ops.object.bake(type='AO', margin=8, use_clear=True)
iA.filepath_raw=os.path.join(OUT,"gate_ao.png"); iA.file_format='PNG'; iA.save()
print("saved ao")

for o in bpy.data.objects: o.select_set(False)
HIGH.select_set(True); bpy.context.view_layer.objects.active=HIGH
bpy.ops.export_scene.gltf(
    filepath=os.path.join(OUT,"gate.glb"),
    export_format='GLB', use_selection=True,
    export_apply=True, export_yup=True, export_texcoords=True, export_normals=True)
print("EXPORTED gate.glb")
print("DONE")
