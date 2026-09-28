"""Refine the licensed cardiac atlas for physically coherent cutaway rendering.
Creates closed section rims, coherent clipping of attached anatomy, vertex AO,
and surface-conforming conduction curves. Geometry remains atlas-derived.
"""
import bpy,bmesh,math,json,time,heapq
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from pathlib import Path
ROOT=Path('/Users/mac/Documents/ECG/public/models')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'heart-exterior.glb'))
scene=bpy.context.scene
objects=[o for o in scene.objects if o.type=='MESH']
WALL_NAMES=['Right atrium','Left atrium','Right ventricle','Left ventricle']
def is_wall(o):return any(o.name.startswith(n+'.') for n in WALL_NAMES)
# Correct welds at exporter seams, smoothing and shape preservation.
for o in objects:
 bpy.context.view_layer.objects.active=o;o.select_set(True)
 bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
 bm=bmesh.new();bm.from_mesh(o.data)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000025)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
 if len(o.data.vertices)<6000 and o['structureId']!='coronary':
  sub=o.modifiers.new('Anatomical surface refinement','SUBSURF');sub.levels=1;sub.render_levels=1
  bpy.ops.object.modifier_apply(modifier=sub.name)
 for p in o.data.polygons:p.use_smooth=True
 o.select_set(False)
# Keep source materials as identity only; the web renderer provides nuanced PBR.
# In this Blender coordinate system anterior = -Y and superior = +Z.
plane_co=Vector((0,-.68,0));plane_no=Vector((0,-1,-.08)).normalized()
def section(o):
 bm=bmesh.new();bm.from_mesh(o.data)
 result=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=plane_co,plane_no=plane_no,clear_outer=True,clear_inner=False)
 cut=[e for e in bm.edges if e.is_boundary and all(abs((v.co-plane_co).dot(plane_no))<.0003 for v in e.verts)]
 count=len(cut)
 if cut and not is_wall(o):
  filled=bmesh.ops.triangle_fill(bm,edges=cut,use_beauty=True,use_dissolve=False)
  # Flat section normals and a separate warm muscle material; valves retain their own.
  if is_wall(o):
   mat=bpy.data.materials.new('Sectioned myocardium');mat.diffuse_color=(.28,.085,.057,1);o.data.materials.append(mat)
   for f in filled['geom']:
    if isinstance(f,bmesh.types.BMFace):f.material_index=len(o.data.materials)-1;f.smooth=False
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();o.data.update()
 if is_wall(o):
  bpy.context.view_layer.objects.active=o
  mat=bpy.data.materials.new('Sectioned myocardium');mat.diffuse_color=(.28,.085,.057,1);o.data.materials.append(mat)
  solid=o.modifiers.new('Section edge thickness','SOLIDIFY');solid.thickness=.018;solid.offset=-1;solid.use_rim=True;solid.material_offset_rim=1
  bpy.ops.object.modifier_apply(modifier=solid.name)
 return count
# Two exports from independent copies keep the exterior and the cutaway coherent.
original=[]
for o in objects:
 if o['structureId'] in ['ra','la','rv','lv','tricuspid','mitral','coronary','aortic','pulmonary'] or o.name.startswith('Pulmonary trunk'):
  original.append((o,o.data.copy()));section(o)
# Remove empty objects created by slicing anterior-only coronaries.
objects=[o for o in objects if len(o.data.polygons)>0]

def make_bvh(obs):
 verts=[];faces=[]
 for o in obs:
  base=len(verts);verts.extend([v.co.copy() for v in o.data.vertices]);faces.extend([tuple(base+i for i in p.vertices) for p in o.data.polygons])
 return BVHTree.FromPolygons(verts,faces,all_triangles=False)

# The overlay is projected onto the surviving chamber surface, then represented
# as a dense polyline so interpolation cannot cut across a curved wall.
walls=[o for o in objects if is_wall(o)]
trees={o['structureId']:make_bvh([o]) for o in walls}
paths=[
 ('sa','ra',[[-1.28,1.24,.39],[-1.5,.92,.2],[-1.5,.54,.08],[-1.08,.17,-.02],[-.65,.03,.12]],.005,.115),
 ('sa','la',[[-1.1,1.12,.12],[-.65,.88,-.28],[-.22,.76,-.45],[.47,.65,-.53]],.02,.125),
 ('his','rv',[[-.65,.03,.12],[-.39,-.14,.2],[-.1,-.36,.2]],.18,.198),
 ('rbb','rv',[[-.1,-.36,.2],[-.31,-.73,.24],[-.22,-1.09,.22],[.2,-1.62,.24]],.195,.227),
 ('lbb','lv',[[-.1,-.36,.12],[.2,-.58,.1],[.51,-1.04,.1],[.93,-1.66,.04],[1.16,-1.81,.04]],.195,.227),
 ('purkinje','rv',[[.2,-1.62,.24],[-.28,-1.48,.22],[-.78,-1.17,.16],[-1.02,-.8,.09],[-1.16,-.39,.1]],.225,.27),
 ('purkinje','lv',[[1.16,-1.81,.04],[1.58,-1.37,.1],[1.71,-.97,.04],[1.66,-.5,-.02],[1.39,-.16,-.12]],.225,.27),
 ('purkinje','lv',[[1.16,-1.81,.04],[1.28,-1.27,-.28],[1.36,-.77,-.36],[1.12,-.32,-.44]],.23,.27),
]
def browser_to_blender(p):return Vector((p[0],-p[2],p[1]))
def blender_to_browser(p):return [round(p.x,5),round(p.z,5),round(-p.y,5)]
path_result=[]
for id,wall,anchors,start,end in paths:
 obj=next(o for o in walls if o['structureId']==wall);mesh=obj.data;tree=trees[wall]
 kd=KDTree(len(mesh.vertices))
 for v in mesh.vertices:kd.insert(v.co,v.index)
 kd.balance();adj=[{} for v in mesh.vertices]
 for e in mesh.edges:
  a,b=e.vertices;d=(mesh.vertices[a].co-mesh.vertices[b].co).length;adj[a][b]=d;adj[b][a]=d
 targets=[]
 for p in anchors:
  desired=browser_to_blender(p)
  hit,n,face,d=tree.ray_cast(Vector((desired.x,-4,desired.z)),Vector((0,1,0)),8)
  if hit is None:hit,n,face,d=tree.find_nearest(desired)
  targets.append(kd.find(hit)[1])
 indices=[]
 for source,target in zip(targets,targets[1:]):
  distance={source:0};parent={};queue=[(0,source)]
  while queue:
   d,index=heapq.heappop(queue)
   if index==target:break
   if d>distance[index]:continue
   for other,weight in adj[index].items():
    nd=d+weight
    if nd<distance.get(other,float('inf')):distance[other]=nd;parent[other]=index;heapq.heappush(queue,(nd,other))
  if target not in distance:continue
  segment=[target]
  while segment[-1]!=source:segment.append(parent[segment[-1]])
  segment.reverse();indices.extend(segment if not indices else segment[1:])
 pts=[]
 for a,b in zip(indices,indices[1:]):
  va,vb=mesh.vertices[a],mesh.vertices[b];steps=max(1,math.ceil((va.co-vb.co).length/.015))
  for j in range(steps):
   t=j/steps;normal=va.normal.lerp(vb.normal,t).normalized();pts.append(blender_to_browser(va.co.lerp(vb.co,t)+normal*.014))
 if indices:
  v=mesh.vertices[indices[-1]];pts.append(blender_to_browser(v.co+v.normal*.014))
 if len(pts)>1:path_result.append({'id':id,'wall':wall,'points':pts,'start':start,'end':end})
(ROOT/'conduction-surface.json').write_text(json.dumps(path_result,separators=(',',':')))
# Ambient occlusion baked into vertex colors: self-shadowing remains visible
# inside the chambers without a costly real-time postprocessing pipeline.
def bake_ao(obs):
 tree=make_bvh(obs);golden=math.pi*(3-math.sqrt(5));rays=14
 start=time.time();total=0;totalverts=sum(len(o.data.vertices) for o in obs)
 for o in obs:
  mesh=o.data;mesh.update()
  attr=mesh.color_attributes.get('TissueOcclusion') or mesh.color_attributes.new(name='TissueOcclusion',type='FLOAT_COLOR',domain='POINT')
  step=max(1,len(mesh.vertices)//max(90,int(9000*len(mesh.vertices)/totalverts)))
  samples=list(range(0,len(mesh.vertices),step));sampletree=KDTree(len(samples));values=[]
  for index,vi in enumerate(samples):
   v=mesh.vertices[vi];n=v.normal.normalized();axis=Vector((0,0,1)) if abs(n.z)<.9 else Vector((1,0,0));tangent=n.cross(axis).normalized();bitangent=n.cross(tangent).normalized();blocked=0
   for k in range(rays):
    z=math.sqrt(1-(k+.5)/rays);r=math.sqrt(1-z*z);angle=k*golden
    direction=(tangent*(r*math.cos(angle))+bitangent*(r*math.sin(angle))+n*z).normalized()
    hit,normal,face,dist=tree.ray_cast(v.co+n*.004,direction,.55)
    if hit is not None:blocked+=1-.45*min(dist/.55,1)
   ao=max(.32,1-.76*blocked/rays);values.append(ao);sampletree.insert(v.co,index)
  sampletree.balance()
  for v in mesh.vertices:
   nearest=sampletree.find_n(v.co,4);weights=[1/max(d,.002)**2 for _,_,d in nearest];ao=sum(values[i]*w for (_,i,_),w in zip(nearest,weights))/sum(weights)
   attr.data[v.index].color=(ao,ao,ao,1)
  mesh.color_attributes.active_color=attr
  # Explicit node wiring makes COLOR_0 the occlusion attribute for every primitive.
  for mat in mesh.materials:
   mat.use_nodes=True;nodes=mat.node_tree.nodes;bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');color=next((n for n in nodes if n.type=='VERTEX_COLOR'),None) or nodes.new('ShaderNodeVertexColor');color.layer_name='TissueOcclusion';mat.node_tree.links.new(color.outputs['Color'],bs.inputs['Base Color'])
  total+=len(mesh.vertices)
 print('AO',total,'vertices',round(time.time()-start,1),'s',flush=True)

def export(name,obs):
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.select_set(True)
 bpy.ops.export_scene.gltf(filepath=str(ROOT/name),export_format='GLB',use_selection=True,export_extras=True,export_yup=True,export_apply=True,export_all_vertex_colors=False)

bake_ao(objects);export('heart-cutaway-v2.glb',objects)
# Restore the original, unsliced anatomical surfaces.
for o,data in original:o.data=data
objects=[o for o in scene.objects if o.type=='MESH' and len(o.data.polygons)>0]
bake_ao(objects);export('heart-exterior-v2.glb',objects)
print('REFINED_ASSETS_COMPLETE',flush=True)
