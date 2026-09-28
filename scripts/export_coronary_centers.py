"""Sample the attributed atlas coronary centerline, without running embedded scripts."""
from pathlib import Path
import bpy,json
from mathutils import Vector
from mathutils.geometry import interpolate_bezier
bpy.ops.wm.open_mainfile(filepath='/private/tmp/cardiac-atlas/Startup.blend',load_ui=False,use_scripts=False)
o=bpy.data.objects['Right coronary artery'];points=[];origin=Vector((.023,-.025,1.304))
for s in o.data.splines:
 for a,b in zip(s.bezier_points,s.bezier_points[1:]):
  pts=interpolate_bezier(a.co,a.handle_right,b.handle_left,b.co,32)
  for i,p in enumerate(pts):
   center=(o.matrix_world@p-origin)*33
   radius=o.data.bevel_depth*(a.radius+(b.radius-a.radius)*i/31)*33
   points.append([*center,radius])
open(Path(__file__).resolve().parents[1]/'public/models/right-coronary-centers.json','w').write(json.dumps(points,separators=(',',':')))
print('CENTERS',len(points))
