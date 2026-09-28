import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {addHeartMorphs,deformPoint,setHeartPose} from './heartMotion';
import {motionAt} from './simulation';

test('cardiac deformation does not fold or invert the anatomical volume at any phase',()=>{
 const eps=1e-4;
 for(const bpm of [40,75,120])for(let phase=0;phase<=100;phase++){
  const m=motionAt(phase/100,bpm);
  for(let y=-2.5;y<=2.6;y+=.05){
   const base=deformPoint(new THREE.Vector3(.6,y,.2),m);
   const dx=deformPoint(new THREE.Vector3(.6+eps,y,.2),m).sub(base).multiplyScalar(1/eps);
   const dy=deformPoint(new THREE.Vector3(.6,y+eps,.2),m).sub(base).multiplyScalar(1/eps);
   const dz=deformPoint(new THREE.Vector3(.6,y,.2+eps),m).sub(base).multiplyScalar(1/eps);
   const determinant=dx.dot(dy.clone().cross(dz));
   // The stronger illustrative squeeze allows up to 25% local volume change;
   // a positive, bounded Jacobian guards against folds and collapsed tissue.
   assert.ok(determinant>.75&&determinant<=1.01,`non-invertible or excessive deformation: ${determinant}`);
  }
 }
});
test('rendered morph vertices and picked vertices match the shared heart deformation',()=>{
 const geometry=addHeartMorphs(new THREE.SphereGeometry(1,24,16));
 const mesh=new THREE.Mesh(geometry,new THREE.MeshBasicMaterial());mesh.updateMorphTargets();
 for(const progress of [.1,.2,.3,.45,.6,.8]){
  const m=motionAt(progress,75);setHeartPose(mesh,m);
  for(let i=0;i<geometry.attributes.position.count;i++){
   const expected=deformPoint(new THREE.Vector3().fromBufferAttribute(geometry.attributes.position,i),m);
   const actual=mesh.getVertexPosition(i,new THREE.Vector3());
   assert.ok(actual.distanceTo(expected)<1e-6);
  }
 }
 geometry.dispose();mesh.material.dispose();
});
