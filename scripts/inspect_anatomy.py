import bpy, json
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='/private/tmp/cardiac-atlas/Startup.blend',load_ui=False,use_scripts=False)
keywords=['heart','atrium','ventric','mitral','tricus','aort','pulmon','cava','purkin','sinuatr','sinoatr','atriovent','chorda','papillary','coronar','septum','his bundle']
result=[]
for obj in bpy.data.objects:
 if obj.type=='MESH' and any(k in obj.name.lower() for k in keywords):
  coords=[obj.matrix_world@Vector(v) for v in obj.bound_box]
  result.append({'name':obj.name,'vertices':len(obj.data.vertices),'collections':[c.name for c in obj.users_collection],'min':[min(v[i] for v in coords) for i in range(3)],'max':[max(v[i] for v in coords) for i in range(3)],'materials':[m.name for m in obj.data.materials if m]})
with open('/private/tmp/cardiac-anatomy-objects.json','w') as f:json.dump(result,f,indent=2)
print('ANATOMY_OBJECTS',len(result))
