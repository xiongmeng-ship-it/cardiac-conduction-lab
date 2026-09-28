"""Close exposed tube ends with short inset anatomical lumen caps.
Keeps every source mesh and branch; only adds faces inside existing boundary loops.
"""
from pathlib import Path
import bpy,bmesh,json
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]/'public/models'
CAP_IDS={'pa','aorta','svc','ivc','pv','coronary'}
MIN_LOOP=20

def loops(bm):
 rem={e for e in bm.edges if e.is_boundary};out=[]
 while rem:
  seed=next(iter(rem));vs=set(seed.verts);todo=list(seed.verts);rem.remove(seed)
  while todo:
   v=todo.pop()
   for e in v.link_edges:
    if e in rem: rem.remove(e);todo.extend(e.verts);vs.update(e.verts)
  # Sort by connectivity so cap quads follow the tube rim.
  ordered=[];start=next(iter(vs));cur=start;prev=None
  while True:
   ordered.append(cur)
   nxt=[e.other_vert(cur) for e in cur.link_edges if e.is_boundary and e.other_vert(cur) in vs and e.other_vert(cur)!=prev]
   nxt=[v for v in nxt if v not in ordered]
   if not nxt:break
   prev,cur=cur,nxt[0]
  if len(ordered)>=MIN_LOOP:out.append(ordered)
 return out

def load(view):
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(ROOT/f'heart-{view}-v5.glb'))
 return [o for o in bpy.context.scene.objects if o.type=='MESH']
report={}
for view in ['cutaway','exterior']:
 obs=load(view);added=[]
 for o in obs:
  if o.get('structureId') not in CAP_IDS:continue
  bm=bmesh.new();bm.from_mesh(o.data);bm.normal_update();loops0=loops(bm)
  mesh_center=sum((v.co for v in bm.verts),Vector())/max(1,len(bm.verts))
  count=0
  for ring in loops0:
   center=sum((v.co for v in ring),Vector())/len(ring);radius=max((v.co-center).length for v in ring)
   if radius<.035:continue
   # Pull the cap into the lumen, so it occludes adjacent meshes without
   # changing the silhouette or cutting away the original vessel wall.
   inward=(mesh_center-center).normalized()
   depth=(.38 if o.get('structureId')=='pa' and center.y<-.4 and center.z>.4 else min(.18,max(.06,radius*.22)))
   inner=[bm.verts.new(v.co+inward*depth) for v in ring]
   for i in range(len(ring)):
    j=(i+1)%len(ring);bm.faces.new((ring[i],ring[j],inner[j],inner[i]))
   edges=[]
   for i in range(len(inner)):
    j=(i+1)%len(inner);e=bm.edges.get((inner[i],inner[j]));
    if e:edges.append(e)
   fill=bmesh.ops.triangle_fill(bm,edges=edges,use_beauty=True)
   for f in fill.get('geom',[]):
    if isinstance(f,bmesh.types.BMFace): f.smooth=True
   count+=1
  if count:
   bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);o.data.update();added.append((o.get('sourceName'),count))
  bm.free()
 report[view]=added
 bpy.ops.object.select_all(action='SELECT')
 bpy.ops.export_scene.gltf(filepath=str(ROOT/f'heart-{view}-v7.glb'),export_format='GLB',use_selection=True,export_extras=True,export_yup=True,export_apply=True)
print(json.dumps(report,indent=2),flush=True)
(ROOT/'open-vessel-cap-report.json').write_text(json.dumps(report,indent=2))
