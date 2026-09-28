import { Component, Suspense, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode, RefObject } from 'react';
import { Canvas, useFrame, useLoader, useThree, type ThreeEvent } from '@react-three/fiber';
import { OrbitControls, useGLTF, useProgress } from '@react-three/drei';
import * as THREE from 'three';
import type { OrbitControls as OrbitControlsType } from 'three-stdlib';
import { motionAt, phaseAt, timing, clamp } from '../simulation';
import {addHeartMorphs,deformPoint,setHeartPose} from '../heartMotion';

type V3=[number,number,number];
const selectionColor=new THREE.Color('#f4cb78');
interface Props {progress:number;bpm:number;selected:string;onSelect:(id:string)=>void;cutaway:boolean;showConduction:boolean;showLabels:boolean;resetView:number}
interface SurfacePath {id:string;wall:string;points:V3[];start:number;end:number}
// The atlas is CC BY-SA. The sectioned geometry, baked occlusion and attached
// conduction overlay are generated together by scripts/refine_heart.py.
const tissueShader=`
float hash31(vec3 p){p=fract(p*0.1031);p+=dot(p,p.yzx+33.33);return fract((p.x+p.y)*p.z);}
float tissueNoise(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(mix(hash31(i),hash31(i+vec3(1,0,0)),f.x),mix(hash31(i+vec3(0,1,0)),hash31(i+vec3(1,1,0)),f.x),f.y),mix(mix(hash31(i+vec3(0,0,1)),hash31(i+vec3(1,0,1)),f.x),mix(hash31(i+vec3(0,1,1)),hash31(i+vec3(1,1,1)),f.x),f.y),f.z);}
`;
function tissueMaterial(source:THREE.MeshStandardMaterial,id:string,section:boolean){
 const colors:Record<string,string>={ra:'#883f3b',la:'#90453e',rv:'#8d413b',lv:'#91443d',aorta:'#ad7462',pa:'#867578',svc:'#726774',ivc:'#726774',pv:'#9b6159',coronary:'#b08167',mitral:'#c4aa82',tricuspid:'#c4aa82',aortic:'#c7ad8c',pulmonary:'#c7ad8c'};
 const valve=['aortic','pulmonary','mitral','tricuspid'].includes(id);
 const mat=new THREE.MeshPhysicalMaterial({color:section?'#a96a55':colors[id]??'#8d4940',vertexColors:true,side:THREE.DoubleSide,roughness:valve?.46:.58,metalness:0,clearcoat:valve?.06:.12,clearcoatRoughness:.42,specularIntensity:.35});
 mat.name=source.name;
 mat.userData.baseColor=mat.color.clone();
 mat.onBeforeCompile=shader=>{
  shader.vertexShader='varying vec3 vTissuePosition;\n'+shader.vertexShader;
  shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\nvTissuePosition=position;');
  shader.fragmentShader='varying vec3 vTissuePosition;\n'+tissueShader+shader.fragmentShader;
  shader.fragmentShader=shader.fragmentShader.replace('#include <color_fragment>',`#include <color_fragment>
   float mottling=tissueNoise(vTissuePosition*14.0);
   float grain=tissueNoise(vTissuePosition*130.0);
   diffuseColor.rgb *= .88 + .18*mottling + .08*grain;
  `);
  // Very fine nonperiodic relief. Unlike the old sine bands, this does not
  // resemble printed plastic or change anatomical silhouettes.
  shader.fragmentShader=shader.fragmentShader.replace('#include <normal_fragment_maps>',`#include <normal_fragment_maps>
   float relief=tissueNoise(vTissuePosition*95.0)*.0015;
   vec3 sx=dFdx(vViewPosition),sy=dFdy(vViewPosition);
   vec3 r1=cross(sy,normal),r2=cross(normal,sx);
   float det=dot(sx,r1);
   if(abs(det)>1e-8)normal=normalize(abs(det)*normal-sign(det)*(dFdx(relief)*r1+dFdy(relief)*r2));
  `);
 };
 mat.customProgramCacheKey=()=>`tissue-pbr-v3-${section?'section':'surface'}`;
 return mat;
}
function pick(id:string,onSelect:Props['onSelect']){return {onClick:(e:ThreeEvent<MouseEvent>)=>{e.stopPropagation();if(e.delta<5)onSelect(id);},onPointerOver:(e:ThreeEvent<PointerEvent>)=>{e.stopPropagation();document.body.style.cursor='pointer';},onPointerOut:()=>{document.body.style.cursor='auto';}};}
function Atlas({props,anatomyRef}:{props:Props;anatomyRef:RefObject<THREE.Group|null>}){
 const {scene}=useGLTF(props.cutaway?`${import.meta.env.BASE_URL}models/heart-cutaway-v7.glb`:`${import.meta.env.BASE_URL}models/heart-exterior-v7.glb`);
 const meshes=useMemo(()=>{
  scene.updateMatrixWorld(true);const result:{name:string;id:string;mesh:THREE.Mesh<THREE.BufferGeometry,THREE.MeshPhysicalMaterial>}[]=[];
  scene.traverse(node=>{if(!(node instanceof THREE.Mesh))return;
   let ancestor:THREE.Object3D|null=node;while(ancestor&&!ancestor.userData.structureId)ancestor=ancestor.parent;
   const id=ancestor?.userData.structureId as string;if(!id)return;
   const geometry=addHeartMorphs(node.geometry.clone().applyMatrix4(node.matrixWorld));
   const color=geometry.getAttribute('color');
   if(color){const exponent=['mitral','tricuspid','aortic','pulmonary'].includes(id)?.3:.65;for(let i=0;i<color.count;i++)color.setXYZ(i,Math.pow(color.getX(i),exponent),Math.pow(color.getY(i),exponent),Math.pow(color.getZ(i),exponent));color.needsUpdate=true;}
   const source=(Array.isArray(node.material)?node.material[0]:node.material) as THREE.MeshStandardMaterial;
   const material=tissueMaterial(source,id,source.name.includes('Sectioned'));
   const mesh=new THREE.Mesh(geometry,material);mesh.name=node.name;mesh.userData.structureId=id;mesh.userData.sourceName=ancestor?.userData.sourceName??ancestor?.name;mesh.updateMorphTargets();
   result.push({name:node.name,id,mesh});
  });return result;
 },[scene]);
 useEffect(()=>()=>meshes.forEach(({mesh})=>{mesh.geometry.dispose();mesh.material.dispose();}),[meshes]);
 useFrame(()=>{
  const phase=phaseAt(props.progress,props.bpm),motion=motionAt(props.progress,props.bpm);
  for(const {id,mesh} of meshes){
   setHeartPose(mesh,motion);
   const selected=props.selected===id||(props.selected==='septum'&&String(mesh.userData.sourceName).startsWith('Left ventricle'));
   const active=props.showConduction&&phase.structures.includes(id);
   mesh.material.color.copy(mesh.material.userData.baseColor as THREE.Color);
   if(selected)mesh.material.color.lerp(selectionColor,.55);
   mesh.material.emissive.set(selected?'#efb956':active?'#672818':'#000000');mesh.material.emissiveIntensity=selected?.55:active?.04:0;
  }
 });
 return <group ref={anatomyRef}>{meshes.map(({name,id,mesh})=><primitive key={name} object={mesh} {...pick(id,props.onSelect)} onClick={(e:ThreeEvent<MouseEvent>)=>{e.stopPropagation();if(e.delta>=5)return;const p=e.object.parent!.worldToLocal(e.point.clone());const septum=String(mesh.userData.sourceName).startsWith('Left ventricle')&&p.x<.25&&p.y<.2;props.onSelect(septum?'septum':id);}}/>)}</group>;
}
class SurfaceCurve extends THREE.Curve<THREE.Vector3>{
 constructor(public points:THREE.Vector3[]){super();}
 getPoint(t:number,target=new THREE.Vector3()){const s=clamp(t)*(this.points.length-1),i=Math.min(Math.floor(s),this.points.length-2);return target.copy(this.points[i]).lerp(this.points[i+1],s-i);}
}
function Path({path,props}:{path:SurfacePath;props:Props}){
 const spark=useRef<THREE.Mesh>(null),ref=useRef<THREE.Mesh>(null);
 const {curve,geometry,material}=useMemo(()=>{
  const curve=new SurfaceCurve(path.points.map(p=>new THREE.Vector3(...p)));
  const geometry=addHeartMorphs(new THREE.TubeGeometry(curve,(path.points.length-1)*2,path.id==='sa'?.007:.01,6,false));
  const material=new THREE.MeshStandardMaterial({color:'#a6c7b6',emissive:'#88b4a1',emissiveIntensity:.12,roughness:.75});return {curve,geometry,material};
 },[path]);
 useEffect(()=>()=>{geometry.dispose();material.dispose();},[geometry,material]);
 useFrame(()=>{const t=props.progress*timing(props.bpm).rr,m=motionAt(props.progress,props.bpm),active=t>=path.start&&t<=path.end;if(ref.current)setHeartPose(ref.current,m);const selected=props.selected===path.id;material.emissiveIntensity=selected?1.1:active?.8:.07;material.emissive.set(selected?'#efb956':'#88b4a1');material.color.set(selected?'#ffe0a0':'#8cb8a2');if(spark.current){spark.current.visible=active;spark.current.position.copy(deformPoint(curve.getPoint(clamp((t-path.start)/(path.end-path.start))),m));}});
 return <><mesh ref={ref} geometry={geometry} material={material} onUpdate={mesh=>mesh.updateMorphTargets()} {...pick(path.id,props.onSelect)}/><mesh ref={spark}><sphereGeometry args={[.025,12,12]}/><meshBasicMaterial color="#e2efbc" toneMapped={false}/></mesh></>;
}
function ConductionNode({id,p,props}:{id:string;p:V3;props:Props}){
 const ref=useRef<THREE.Mesh>(null),mat=useRef<THREE.MeshStandardMaterial>(null);
 useFrame(()=>{if(ref.current)ref.current.position.copy(deformPoint(new THREE.Vector3(...p),motionAt(props.progress,props.bpm)));if(mat.current){const selected=props.selected===id;mat.current.emissive.set(selected?'#efb956':'#acbf84');mat.current.emissiveIntensity=selected?1.1:phaseAt(props.progress,props.bpm).structures.includes(id)?.8:.1;}});
 return <mesh ref={ref} {...pick(id,props.onSelect)}><sphereGeometry args={[.039,20,20]}/><meshStandardMaterial ref={mat} color={props.selected===id?'#ddc991':'#a8c9ab'} emissive="#acbf84" roughness={.65}/></mesh>;
}
const modelRotation=new THREE.Euler(0,-.12,-.08);
function Scene(props:Props & {labelElements:RefObject<(HTMLButtonElement|null)[]>}){
 const raw=useLoader(THREE.FileLoader,`${import.meta.env.BASE_URL}models/conduction-surface.json`);
 const paths=useMemo(()=>JSON.parse(raw as string) as SurfacePath[],[raw]);
 const nodes=useMemo(()=>[{id:'sa',p:paths[0].points[0]},{id:'av',p:paths.find(p=>p.id==='his')!.points[0]}],[paths]);
 const labels=useMemo(()=>[nodes[0].p,nodes[1].p,[1.45,-.85,.1] as V3],[nodes]);
 const controls=useRef<OrbitControlsType>(null),anatomyRef=useRef<THREE.Group>(null);
 useEffect(()=>{controls.current?.reset();},[props.resetView]);
 return <><ambientLight intensity={.45}/><hemisphereLight args={['#e0dad4','#241b20',.65]}/><directionalLight position={[-3,5,6]} intensity={2.8} color="#fff1e4"/><directionalLight position={[4,-1,3]} intensity={1.0} color="#bdc9d3"/><directionalLight position={[0,3,-4]} intensity={1.8} color="#dcc4b2"/><group rotation={modelRotation}><Atlas props={props} anatomyRef={anatomyRef}/>{props.cutaway&&props.showConduction&&<group>{paths.map((path,i)=><Path key={i} path={path} props={props}/>)}{nodes.map(n=><ConductionNode key={n.id} {...n} props={props}/>)}</group>}</group><LabelProjector elements={props.labelElements} points={labels} anatomyRef={anatomyRef} props={props}/><OrbitControls ref={controls} enablePan={false} minDistance={5.2} maxDistance={12} minPolarAngle={.35} maxPolarAngle={2.8} target={[0,.4,0]} enableDamping dampingFactor={.08}/></>;
}
const labelData=[{id:'sa',text:'SA node',side:'left'},{id:'av',text:'AV node',side:'left'},{id:'lv',text:'Left ventricle',side:'right'}];
function LabelProjector({elements,points,anatomyRef,props}:{elements:RefObject<(HTMLButtonElement|null)[]>;points:V3[];anatomyRef:RefObject<THREE.Group|null>;props:Props}){
 const {camera,size}=useThree();const matrix=useMemo(()=>new THREE.Matrix4().makeRotationFromEuler(modelRotation),[]);const ray=useMemo(()=>new THREE.Raycaster(),[]);const frame=useRef(0);
 useFrame(()=>{if(++frame.current%3!==0)return;labelData.forEach((label,i)=>{
  const el=elements?.current[i];if(!el)return;
  const world=deformPoint(new THREE.Vector3(...points[i]),motionAt(props.progress,props.bpm)).applyMatrix4(matrix);
  const projected=world.clone().project(camera);
  const distance=camera.position.distanceTo(world);ray.set(camera.position,world.clone().sub(camera.position).normalize());ray.far=distance-.055;
  const hidden=anatomyRef.current&&ray.intersectObject(anatomyRef.current,true).length>0;
  let x=(projected.x+1)*size.width/2;const y=(-projected.y+1)*size.height/2;
  x=label.side==='left'?Math.max(el.offsetWidth+8,Math.min(x,size.width-8)):Math.max(8,Math.min(x,size.width-el.offsetWidth-8));
  el.style.left=`${x}px`;el.style.top=`${y}px`;el.style.visibility=hidden||Math.abs(projected.z)>1?'hidden':'visible';
 });});return null;
}
class SceneBoundary extends Component<{children:ReactNode;onError:()=>void},{error:boolean}>{state={error:false};static getDerivedStateFromError(){return {error:true};}componentDidCatch(){this.props.onError();}render(){return this.state.error?null:this.props.children;}}
export default function Heart(props:Props){
 const [failed,setFailed]=useState(false);const labelElements=useRef<(HTMLButtonElement|null)[]>([]);const loading=useProgress();
 const supported=useMemo(()=>{try{const c=document.createElement('canvas');const gl=c.getContext('webgl2');if(!gl)return false;gl.getExtension('WEBGL_lose_context')?.loseContext();return true;}catch{return false;}},[]);
 if(!supported||failed)return <div className="webgl-fallback"><span>3D VIEW UNAVAILABLE</span><h3>Your ECG lab is still ready.</h3><p>Enable WebGL and reload to explore the anatomical heart. You can continue using the ECG, timeline and anatomy explorer.</p></div>;
 return <div className="anatomical-view"><SceneBoundary onError={()=>setFailed(true)}><Canvas camera={{position:[0,.6,9.1],fov:43}} dpr={[1,1.8]} gl={{antialias:true,alpha:true}} onCreated={({gl})=>{gl.domElement.addEventListener('webglcontextlost',()=>setFailed(true),{once:true});}}><Suspense fallback={null}><Scene {...props} labelElements={labelElements}/></Suspense></Canvas></SceneBoundary>{loading.active&&<div className="atlas-loading">Loading anatomical heart… {Math.round(loading.progress)}%</div>}<div className="anatomy-labels" style={{display:props.showLabels&&props.cutaway&&!loading.active?'block':'none'}}>{labelData.map((l,i)=><button key={l.id} ref={el=>{labelElements.current[i]=el;}} className={`projected-label ${l.side} ${props.selected===l.id?'active':''}`} onClick={()=>props.onSelect(l.id)}>{l.side==='right'&&<span/>}{l.text}{l.side==='left'&&<span/>}</button>)}</div></div>;
}
useGLTF.preload(`${import.meta.env.BASE_URL}models/heart-cutaway-v7.glb`);
useGLTF.preload(`${import.meta.env.BASE_URL}models/heart-exterior-v7.glb`);
