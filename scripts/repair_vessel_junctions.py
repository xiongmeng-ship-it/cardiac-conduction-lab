"""Restore arch roof, pulmonary root attachment, and posterior contact clearance.
Run with Blender -b --python scripts/repair_vessel_junctions.py. Reads the
licensed original atlas with scripts disabled; preserves v4 source structures.
"""
from pathlib import Path
import json
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]/'public/models'

def load(view):
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.gltf(filepath=str(ROOT/f'heart-{view}-v4.glb'))
 obs=[o for o in bpy.context.scene.objects if o.type=='MESH']
 for o in obs:o.data.transform(o.matrix_world);o.matrix_world.identity()
 return obs

def loops(bm):
 remaining={e for e in bm.edges if e.is_boundary};result=[]
 while remaining:
  first=next(iter(remaining));start=first.verts[0];current=start;edge=first;ordered=[]
  while edge in remaining:
   ordered.append(current);remaining.remove(edge);current=edge.other_vert(current)
   possible=[e for e in current.link_edges if e in remaining]
   if not possible:break
   edge=possible[0]
  result.append(ordered)
 return result

def make_tree(mesh):return BVHTree.FromPolygons([v.co for v in mesh.vertices],[tuple(p.vertices) for p in mesh.polygons])
def smooth(a,b,x):
 t=min(1,max(0,(x-a)/(b-a)));return t*t*(3-2*t)
def colors(mesh,value=.86):
 attr=mesh.color_attributes.get('TissueOcclusion') or mesh.color_attributes.new(name='TissueOcclusion',type='FLOAT_COLOR',domain='POINT')
 for c in attr.data:c.color=(value,value,value,1)
 mesh.color_attributes.active_color=attr

# Recover the roof from the original arch, not a planar lid over the bad crop.
bpy.ops.wm.open_mainfile(filepath='/private/tmp/cardiac-atlas/Startup.blend',load_ui=False,use_scripts=False)
o=bpy.data.objects['Aortic arch'];deps=bpy.context.evaluated_depsgraph_get()
for mod in o.modifiers:
 if mod.type=='SUBSURF':mod.levels=2;mod.render_levels=2
mesh=bpy.data.meshes.new_from_object(o.evaluated_get(deps),depsgraph=deps)
mesh.transform(o.matrix_world)
for v in mesh.vertices:v.co=(v.co-Vector((.023,-.025,1.304)))*33
arch_verts=[v.co.copy() for v in mesh.vertices];arch_faces=[tuple(p.vertices) for p in mesh.polygons]

# Repair in intact space, so both views use exactly the same tissue movement.
obs=load('exterior');pa=next(o for o in obs if o.get('structureId')=='pa')
bm=bmesh.new();bm.from_mesh(pa.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000025)
ring=min(loops(bm),key=lambda vs:(sum((v.co for v in vs),Vector())/len(vs)-Vector((.233,-.767,.818))).length)
center=sum((v.co for v in ring),Vector())/len(ring)
# Extend the vascular wall to surround the semilunar cusp attachments. The
# annulus remains hollow; valve leaflets and their free edges remain intact.
previous=ring
for j in range(1,9):
 t=j/8;offset=Vector((-.065,0,-.09))*t
 new=[bm.verts.new(center+(v.co-center)*(1+.025*t)+offset) for v in ring]
 for i in range(len(ring)):
  k=(i+1)%len(ring);bm.faces.new((previous[i],previous[k],new[k],new[i]))
 previous=new
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(pa.data);bm.free()
pa.data.update();full_pa_verts=[v.co.copy() for v in pa.data.vertices];full_pa_faces=[tuple(p.vertices) for p in pa.data.polygons]
pa_tree=make_tree(pa.data)

def posterior_clearance(p):
 # Restrict to the posterior right-heart/PA contact seen in the user's image;
 # maintain all openings and the atrium's vertex/face connectivity.
 if not (-1.8<p.x<-.65 and .3<p.y<1.3 and .72<p.z<1.5):return p
 for _ in range(3):
  q,n,_,d=pa_tree.find_nearest(p)
  if q is None or d>.32:break
  signed=(p-q).dot(n)
  if signed>=.03:break
  p=p+n*(.03-signed)
 return p

report={}
for view in ['cutaway','exterior']:
 obs=load(view);before={o.get('sourceName') for o in obs}
 arch=next(o for o in obs if o.get('sourceName')=='Aortic arch')
 m=bpy.data.meshes.new('Complete aortic arch');m.from_pydata(arch_verts,[],arch_faces)
 for mat in arch.data.materials:m.materials.append(mat)
 arch.data=m
 # Match v2 source refinement without clipping the arch crown.
 bpy.context.view_layer.objects.active=arch
 sub=arch.modifiers.new('Arch surface refinement','SUBSURF');sub.levels=1;bpy.ops.object.modifier_apply(modifier=sub.name)
 colors(arch.data)
 pa=next(o for o in obs if o.get('structureId')=='pa')
 m=bpy.data.meshes.new('Continuous pulmonary root');m.from_pydata(full_pa_verts,[],full_pa_faces)
 for mat in pa.data.materials:m.materials.append(mat)
 pa.data=m
 if view=='cutaway':
  bm=bmesh.new();bm.from_mesh(m)
  # Section only the anterior wall; the posterior root remains continuous.
  bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=(0,-.68,0),plane_no=(0,-1,-.08),clear_outer=True)
  bm.to_mesh(m);bm.free()
 colors(m)
 moved=0
 for o in obs:
  if o.get('sourceName') in ['Right atrium','Superior vena cava']:
   for v in o.data.vertices:
    p=posterior_clearance(v.co.copy())
    if (p-v.co).length>1e-7:moved+=1;v.co=p
   o.data.update()
  for face in o.data.polygons:face.use_smooth=True
 assert before=={o.get('sourceName') for o in obs}
 tree_pa=make_tree(pa.data);ra=next(o for o in obs if o.get('sourceName')=='Right atrium')
 contacts=tree_pa.overlap(make_tree(ra.data))
 report[view]={'sourceStructures':len(before),'posteriorMovedVertices':moved,'paRaTriangleContacts':len(contacts),'archHeight':max(v.co.z for v in arch.data.vertices)}
 bpy.ops.object.select_all(action='SELECT')
 bpy.ops.export_scene.gltf(filepath=str(ROOT/f'heart-{view}-v5.glb'),export_format='GLB',use_selection=True,export_extras=True,export_yup=True,export_apply=True)
print('REPAIR_REPORT',json.dumps(report),flush=True)
(ROOT/'junction-repair-report.json').write_text(json.dumps(report,indent=2))
