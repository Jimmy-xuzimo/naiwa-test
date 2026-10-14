import bpy, os, sys
out="/tmp/baketest"
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
sc.render.engine='CYCLES'
sc.cycles.device='CPU'
sc.cycles.samples=8
sc.render.bake.margin=8

# 低模：一个方块
bpy.ops.mesh.primitive_cube_add(size=2, location=(0,0,0))
low=bpy.context.object; low.name="LOW"
# 高模：表面有浮雕的方块（用一个细分+位移的球体代表细节源）
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.35, segments=48, ring_count=24, location=(0,0,0))
hi=bpy.context.object; hi.name="HIGH"
bpy.ops.object.shade_smooth()

# 低模 UV
bpy.ops.object.select_all(action='DESELECT')
low.select_set(True); bpy.context.view_layer.objects.active=low
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
bpy.ops.object.mode_set(mode='OBJECT')

# 低模材质 + 目标贴图节点
mat=bpy.data.materials.new("LowMat"); mat.use_nodes=True
nt=mat.node_tree
low.data.materials.append(mat)
def mkimg(name):
    return bpy.data.images.new(name, 512, 512, alpha=False)
img_n=mkimg("NORMAL"); img_a=mkimg("AO")
texn=nt.nodes.new("ShaderNodeTexImage"); texn.image=img_n
texa=nt.nodes.new("ShaderNodeTexImage"); texa.image=img_a
for n in (texn,texa): n.location=(-600,0)

def bake(kind, node):
    for n in nt.nodes: n.select=False
    node.select=True; nt.nodes.active=node
    bpy.ops.object.select_all(action='DESELECT')
    low.select_set(True); hi.select_set(True)
    bpy.context.view_layer.objects.active=low
    op = dict(use_selected_to_active=True, cage_extrusion=0.06, margin=8, use_clear=True)
    if kind=='NORMAL': bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', **op)
    else:              bpy.ops.object.bake(type='AO', **op)
bake('NORMAL', texn)
bake('AO', texa)
img_n.filepath_raw=os.path.join(out,"n.png"); img_n.file_format='PNG'; img_n.save()
img_a.filepath_raw=os.path.join(out,"ao.png"); img_a.file_format='PNG'; img_a.save()
print("BAKE OK")
