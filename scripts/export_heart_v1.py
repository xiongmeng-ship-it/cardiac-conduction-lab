"""Export only heart anatomy from the attributed Z-Anatomy atlas (CC BY-SA 4.0).
Run in a separate background Blender process; never operates on a live user's scene.
"""
import bpy,bmesh,json,math
from mathutils import Vector,Matrix
from pathlib import Path
bpy.ops.wm.open_mainfile(filepath='/private/tmp/cardiac-atlas/Startup.blend',load_ui=False,use_scripts=False)
root=Path('/Users/mac/Documents/ECG/public/models');root.mkdir(exist_ok=True)
# BodyParts3D coordinates: +X patient's left, -Y anterior, +Z superior.
center=Vector((.023,-.025,1.304));scale=33
map_exact={'Right atrium':'ra','Left atrium':'la','Right ventricle':'rv','Left ventricle':'lv','Pulmonary trunk':'pa','Ascending aorta':'aorta','Aortic arch':'aorta','Superior vena cava':'svc','Inferior vena cava (thoracic part)':'ivc','Bifurcation of pulmonary trunk':'pa'}
selected=[]
for obj in bpy.data.objects:
 if obj.type not in ('MESH','CURVE') or obj.name.endswith('.j'):continue
 name=obj.name.lower();cols=[c.name for c in obj.users_collection];id=map_exact.get(obj.name)
 if not id:
  if 'pulmonary vein' in name:id='pv'
  elif name in ['left pulmonary artery','right pulmonary artery']:id='pa'
  elif 'arch' in name and ('aort' in name):id='aorta'
  elif 'papillary muscle' in name:id='lv' if 'left ventricle' in name else 'rv'
  elif 'leaflet' in name and 'Heart' in cols:
   if 'pulmonary' in name:id='pulmonary'
   elif 'coronary' in name:id='aortic'
   elif 'left atrioventricular' in name:id='mitral'
   elif 'right atrioventricular' in name:id='tricuspid'
  elif '5: Cardiovascular system' in cols and any(k in name for k in ['coronary artery','interventricular branch','circumflex branch','marginal branch','cardiac vein','coronary sinus']):id='coronary'
 if id:selected.append((obj,id))
print('SOURCE_OBJECTS',[(o.name,id) for o,id in selected])
# Store world-space evaluated data before removing the rest of the atlas.
for o,_ in selected:
 for mod in o.modifiers:
  if mod.type=='SUBSURF':mod.levels=2;mod.render_levels=2
 o.hide_viewport=False;o.hide_set(False)
deps=bpy.context.evaluated_depsgraph_get();converted=[]
for source,id in selected:
 evaluated=source.evaluated_get(deps)
 mesh=bpy.data.meshes.new_from_object(evaluated,depsgraph=deps)
 mesh.transform(source.matrix_world)
 for v in mesh.vertices:v.co=(v.co-center)*scale
 # Keep just proximal portions of vessels, not their branches throughout the chest.
 if id in ['ivc','pa','pv','svc','aorta']:
  bm=bmesh.new();bm.from_mesh(mesh)
  for point,normal in [((0,0,-2.2),(0,0,-1)),((0,0,2.65),(0,0,1)),((-2.25,0,0),(-1,0,0)),((2.25,0,0),(1,0,0))]:
   bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=point,plane_no=normal,clear_outer=True,clear_inner=False)
  bm.to_mesh(mesh);bm.free()
 obj=bpy.data.objects.new(source.name,mesh);obj['structureId']=id;obj['sourceName']=source.name;converted.append(obj)
# New isolated scene; leave source data available but not linked.
new_scene=bpy.data.scenes.new('Cardiac Lab — licensed anatomy');bpy.context.window.scene=new_scene
palette={'ra':(.42,.105,.11,1),'la':(.45,.12,.125,1),'rv':(.48,.135,.14,1),'lv':(.48,.14,.14,1),'pa':(.22,.29,.34,1),'pv':(.48,.19,.18,1),'svc':(.19,.25,.31,1),'ivc':(.19,.25,.31,1),'aorta':(.48,.20,.18,1),'aortic':(.64,.49,.34,1),'pulmonary':(.64,.49,.34,1),'mitral':(.61,.45,.31,1),'tricuspid':(.61,.45,.31,1),'coronary':(.45,.16,.15,1)}
mats={}
for id,color in palette.items():
 mat=bpy.data.materials.new('Anatomy_'+id);mat.use_nodes=True;bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=color;bs.inputs['Roughness'].default_value=.48;mats[id]=mat
for o in converted:
 new_scene.collection.objects.link(o);o.data.materials.clear();o.data.materials.append(mats[o['structureId']]);o.select_set(True)
 for p in o.data.polygons:p.use_smooth=True
# Preserve complete heart and a separate surgical window made from actual source meshes.
bpy.ops.export_scene.gltf(filepath=str(root/'heart-exterior.glb'),export_format='GLB',use_selection=True,export_extras=True,export_yup=True,export_apply=True)
for o in converted:
 id=o['structureId'];name=o['sourceName']
 if name in ['Right ventricle','Left ventricle','Right atrium','Left atrium']:
  bm=bmesh.new();bm.from_mesh(o.data)
  # Front wall window. Cut an oblique plane, retaining the posterior chambers and septal anatomy.
  point=(0,-.49,0);normal=(0,-1,-.08)
  result=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=point,plane_no=normal,clear_outer=True,clear_inner=False)
  # Open chambers are intentional; source meshes already contain the anatomical walls.
  bm.to_mesh(o.data);bm.free();o.data.update()
 if id=='coronary':
  bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=(0,-.49,0),plane_no=(0,-1,-.08),clear_outer=True,clear_inner=False);bm.to_mesh(o.data);bm.free()
bpy.ops.export_scene.gltf(filepath=str(root/'heart-cutaway.glb'),export_format='GLB',use_selection=True,export_extras=True,export_yup=True,export_apply=True)
summary=[]
for o in converted:
 if not o.data.vertices:continue
 coords=[v.co for v in o.data.vertices];summary.append({'name':o.name,'id':o['structureId'],'verts':len(coords),'min':[round(min(v[i] for v in coords),3) for i in range(3)],'max':[round(max(v[i] for v in coords),3) for i in range(3)]})
(root/'anatomy-manifest.json').write_text(json.dumps({'source':'Z-Anatomy / BodyParts3D','license':'CC BY-SA 4.0','sourceUrl':'https://github.com/Z-Anatomy/Models-of-human-anatomy','scale':scale,'center':list(center),'objects':summary},indent=2))
print('EXPORTED',len(summary),'objects')
