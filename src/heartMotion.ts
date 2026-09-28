import * as THREE from 'three';
import { clamp } from './simulation';
export interface HeartMotion { atrial:number; ventricular:number }
/** One smooth spatial map shared by tissue, vessels, pathways and markers.
 * Morph targets make GPU normals and CPU picking agree with visible geometry.
 */
export function deformPoint(p:THREE.Vector3,m:HeartMotion){
  const smooth=(a:number,b:number,v:number)=>{const t=clamp((v-a)/(b-a));return t*t*(3-2*t);};
  // Use broad transition bands so the stronger squeeze does not create a
  // sharp shear where the atria meet the ventricles.
  const vw=1-smooth(-.8,1.6,p.y),aw=smooth(-1,.45,p.y)*(1-smooth(1.05,2.05,p.y));
  // Accentuate inward wall displacement and upward apex movement. The smaller
  // atrial contraction precedes ventricular contraction via motionAt. This is
  // an illustrative displacement field, not a wall-thickening tissue solver.
  // Share it across anatomy, vessels, labels and picking.
  // Make the beat easier to see at the default camera distance while keeping
  // the upper vessel attachments quiet and the shared deformation continuous.
  const ventricular=m.ventricular*vw*1.65, atrial=m.atrial*aw*1.4;
  const radial=ventricular*.068+atrial*.038;
  const depthCompression=ventricular*.02+atrial*.014;
  return p.set(.2+(p.x-.2)*(1-radial),p.y+ventricular*.12+atrial*.014,-.3+(p.z+.3)*(1-depthCompression));
}
export function addHeartMorphs(geometry:THREE.BufferGeometry){
  const base=geometry.attributes.position;
  geometry.morphAttributes.position=[];geometry.morphAttributes.normal=[];
  const v=new THREE.Vector3();
  for(const motion of [{atrial:1,ventricular:0},{atrial:0,ventricular:1}]){
    const positions=new Float32Array(base.count*3);
    for(let i=0;i<base.count;i++){v.fromBufferAttribute(base,i);deformPoint(v,motion);v.toArray(positions,i*3);}
    const attr=new THREE.BufferAttribute(positions,3);
    const posed=geometry.clone();posed.morphAttributes={};posed.setAttribute('position',attr);posed.computeVertexNormals();
    geometry.morphAttributes.position.push(attr);
    geometry.morphAttributes.normal.push(posed.getAttribute('normal').clone());
    posed.dispose();
  }
  geometry.morphTargetsRelative=false;geometry.computeBoundingSphere();
  return geometry;
}
export function setHeartPose(mesh:THREE.Mesh,m:HeartMotion){
  if(mesh.morphTargetInfluences){mesh.morphTargetInfluences[0]=m.atrial;mesh.morphTargetInfluences[1]=m.ventricular;}
}
