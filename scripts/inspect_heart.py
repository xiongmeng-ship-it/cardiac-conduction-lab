import bpy,json
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='/private/tmp/cardiac-atlas/Startup.blend',load_ui=False,use_scripts=False)
result=[]
for obj in bpy.data.objects:
 cols=[c.name for c in obj.users_collection]
 if ('Heart' in cols or any(k in obj.name.lower() for k in ['aorta','vena cava','pulmonary trunk','pulmonary artery','pulmonary vein','coronary','atrioventricular bundle','sinuatrial','sinoatrial','atrioventricular node'])) and not obj.name.endswith('.j'):
  coords=[obj.matrix_world@Vector(v) for v in obj.bound_box]
  result.append({'name':obj.name,'type':obj.type,'modifiers':[(m.name,m.type) for m in obj.modifiers],'min':[min(v[i] for v in coords) for i in range(3)],'max':[max(v[i] for v in coords) for i in range(3)],'materials':[m.name for m in obj.data.materials if m] if hasattr(obj.data,'materials') else []})
with open('/private/tmp/cardiac-heart-objects.json','w') as f:json.dump(result,f,indent=2)
for x in result:print(x['name'],x['type'],x['modifiers'],x['materials'])
