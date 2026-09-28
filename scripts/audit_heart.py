import bpy,bmesh,json
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath='/Users/mac/Documents/ECG/public/models/heart-exterior.glb')
for o in bpy.context.scene.objects:
 if o.type!='MESH':continue
 bm=bmesh.new();bm.from_mesh(o.data)
 print(o.name,len(bm.verts),'boundaries',sum(e.is_boundary for e in bm.edges),'nonmanifold',sum(not e.is_manifold for e in bm.edges))
 bm.free()
