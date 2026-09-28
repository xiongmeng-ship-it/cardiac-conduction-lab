"""Repair atlas vessel contacts while preserving the complete vessel tree.

Run after refine_heart.py. The pulmonary network is joined into one continuous
lumen; coronary corrections translate cross-sections using the original atlas
centerline. No anatomical branches are hidden or removed.
"""
from pathlib import Path
import json
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
ROOT = Path(__file__).resolve().parents[1] / 'public/models'
WALLS = {'Right atrium', 'Left atrium', 'Right ventricle', 'Left ventricle'}

def load(filename):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT / filename))
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    for o in objects:
        o.data.transform(o.matrix_world)
        o.matrix_world.identity()
    return objects

def tree(objects):
    verts, faces = [], []
    for o in objects:
        offset = len(verts)
        verts.extend(v.co.copy() for v in o.data.vertices)
        faces.extend(tuple(offset + i for i in p.vertices) for p in o.data.polygons)
    return BVHTree.FromPolygons(verts, faces)

def smoothstep(a, b, x):
    t = min(1., max(0., (x-a)/(b-a)))
    return t*t*(3-2*t)

reference = load('heart-exterior-v2.glb')
epicardium = tree([o for o in reference if o.get('sourceName') in WALLS])
centers = json.loads((ROOT/'right-coronary-centers.json').read_text())
center_tree = KDTree(len(centers)); shifts=[]
for i, point in enumerate(centers):
    p=Vector(point[:3]);radius=point[3];center_tree.insert(p,i)
    origin=Vector((.15,.45,-.7));direction=(p-origin).normalized()
    q,n,_,_=epicardium.ray_cast(origin+direction*6,-direction,6)
    amount=max(0.,(q-p).dot(direction)+radius+.04) if q is not None else 0.
    weight=1-smoothstep(-1.15,-.95,p.z)
    shifts.append(direction*amount*weight)
center_tree.balance()

# Rebuild only the pulmonary junction topology. Filling temporary volumes then
# remeshing their union eliminates the internal pipe walls at bifurcations.
pa=[o for o in reference if o.get('structureId')=='pa']
source_parts=[o['sourceName'] for o in pa];terminals=[]
for o in pa:
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000025)
    remaining={e for e in bm.edges if e.is_boundary}
    while remaining:
        e=remaining.pop();component={e};todo=list(e.verts)
        while todo:
            v=todo.pop()
            for edge in v.link_edges:
                if edge in remaining:
                    remaining.remove(edge);component.add(edge);todo.extend(edge.verts)
        vertices={v for edge in component for v in edge.verts}
        center=sum((v.co for v in vertices),Vector())/len(vertices)
        terminal=(o['sourceName']=='Pulmonary trunk' and center.z<1) or (o['sourceName']=='Left pulmonary artery' and center.x>1) or (o['sourceName']=='Right pulmonary artery' and center.x<-1)
        result=bmesh.ops.holes_fill(bm,edges=list(component),sides=0)
        bm.normal_update()
        if terminal and result['faces']:
            # Normal will be oriented away from the vessel center below.
            n=result['faces'][0].normal.copy()
            average=sum((v.co for v in bm.verts),Vector())/len(bm.verts)
            if n.dot(center-average)<0:n.negate()
            terminals.append((center,n,max((v.co-center).length for v in vertices)))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(o.data);bm.free()
bpy.ops.object.select_all(action='DESELECT')
for o in pa:o.select_set(True)
bpy.context.view_layer.objects.active=pa[0];bpy.ops.object.join()
network=pa[0]
mod=network.modifiers.new('Continuous pulmonary lumen','REMESH');mod.mode='VOXEL';mod.voxel_size=.016;mod.use_smooth_shade=True
bpy.ops.object.modifier_apply(modifier=mod.name)
mod=network.modifiers.new('Junction relaxation','SMOOTH');mod.factor=.6;mod.iterations=4
bpy.ops.object.modifier_apply(modifier=mod.name)
bm=bmesh.new();bm.from_mesh(network.data)
for center,n,radius in terminals:
    # The inlet plane can also cross a distant branch. Split the surface but
    # remove only its local cap, leaving the rest of the vessel tree untouched.
    plane=center-n*.025
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=plane,plane_no=n)
    cap_faces=[f for f in bm.faces if (f.calc_center_median()-plane).dot(n)>-.00001 and (f.calc_center_median()-center).length<radius*1.35]
    bmesh.ops.delete(bm,geom=cap_faces,context='FACES')
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(network.data);bm.free()
# A smooth translation field preserves tube cross-sections and shared branch
# junctions. Unlike nearest-surface projection it cannot flatten a vessel wall.
network.data.update()
network_verts=[v.co.copy() for v in network.data.vertices]
network_faces=[tuple(p.vertices) for p in network.data.polygons]

# Choose a small smooth translation of the proximal pulmonary network, testing
# triangle contacts with both adjacent structures, not only vertex distances.
def warped(p, dx, dy):
    w=smoothstep(.62,.98,p.z)*(1-smoothstep(.25,.8,p.y))*smoothstep(-1,-.5,p.x)
    return p+Vector((dx*w,dy*w,0))
dx,dy=.12,0

for view in ['cutaway','exterior']:
    obs=load(f'heart-{view}-v2.glb')
    original_names={o.get('sourceName') for o in obs}
    # All four source vessel sections remain represented in the connected tree.
    pa=[o for o in obs if o.get('structureId')=='pa'];material=pa[0].data.materials[0]
    mesh=bpy.data.meshes.new('Pulmonary arterial tree');mesh.from_pydata(network_verts,[],network_faces);mesh.materials.append(material)
    network=bpy.data.objects.new('Pulmonary arterial tree',mesh)
    network['structureId']='pa';network['sourceName']='Pulmonary arterial tree';network['sourceParts']=source_parts
    bpy.context.scene.collection.objects.link(network)
    if view=='cutaway':
        bm=bmesh.new();bm.from_mesh(mesh)
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=(0,-.68,0),plane_no=(0,-1,-.08),clear_outer=True)
        bm.to_mesh(mesh);bm.free()
    for v in mesh.vertices:
        v.co=warped(v.co,dx,dy)
    mesh.update()
    for p in mesh.polygons:p.use_smooth=True
    attr=mesh.color_attributes.new(name='TissueOcclusion',type='FLOAT_COLOR',domain='POINT')
    for v in mesh.vertices:attr.data[v.index].color=(.85,.85,.85,1)
    mesh.color_attributes.active_color=attr
    for o in pa:obs.remove(o);bpy.data.objects.remove(o,do_unlink=True)
    obs.append(network)
    for o in obs:
        if o.get('sourceName')=='Left atrium':
            # The atlas appendage tip was inside the pulmonary lumen. Preserve
            # it and its wall topology while moving it to the lateral side.
            for v in o.data.vertices:
                p=v.co
                w=smoothstep(.55,.85,p.z)*(1-smoothstep(-.1,.45,p.y))*smoothstep(-.2,.2,p.x)
                v.co+=Vector((.35,.24,0))*w
            o.data.update()
        elif o.get('sourceName')=='Right coronary artery':
            for v in o.data.vertices:
                # Smooth interpolation of centerline translations preserves
                # cross-section radius instead of flattening vertices onto a wall.
                nearest=center_tree.find_n(v.co,4)
                weights=[1/max(d,.002)**2 for _,_,d in nearest]
                delta=sum((shifts[i]*w for (_,i,_),w in zip(nearest,weights)),Vector())/sum(weights)
                v.co+=delta
            o.data.update()
        elif o.get('structureId')=='ivc':
            # The inlet remains in the right atrium, with clearance from the RV.
            for v in o.data.vertices:
                t=smoothstep(-2.1,-1.35,v.co.z)
                v.co+=Vector((-.18,.20,0))*t
            o.data.update()
    represented=set()
    for o in obs:represented.update(o.get('sourceParts',[o.get('sourceName')]))
    assert original_names==represented,(original_names-represented,represented-original_names)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=str(ROOT/f'heart-{view}-v4.glb'),export_format='GLB',use_selection=True,export_extras=True,export_yup=True,export_apply=True)
    print('STRUCTURES_PRESERVED',view,len(original_names),flush=True)
