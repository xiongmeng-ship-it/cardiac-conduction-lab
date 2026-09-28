import { useMemo } from 'react';
import { ecgAt, timing, clamp } from '../simulation';
interface Props {progress:number;bpm:number;seek:(p:number)=>void}
export default function ECG({progress,bpm,seek}:Props){
  const {rr}=timing(bpm),w=1000,h=204,left=44,right=970,top=15,bottom=150,baseline=112;
  const x=(p:number)=>left+p*(right-left), y=(v:number)=>baseline-v*70;
  const path=useMemo(()=>Array.from({length:901},(_,i)=>`${i?'L':'M'}${(left+i/900*(right-left)).toFixed(2)},${(baseline-ecgAt(i/900*rr,bpm)*70).toFixed(2)}`).join(' '),[bpm,rr]);
  const {tStart,tEnd}=timing(bpm);
  return <svg className="ecg-svg" viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Illustrative Lead II ECG. Use the cardiac cycle slider to choose a time." onPointerDown={e=>{e.currentTarget.setPointerCapture(e.pointerId);const box=e.currentTarget.getBoundingClientRect();seek(clamp(((e.clientX-box.left)/box.width*w-left)/(right-left)));}} onPointerMove={e=>{if(e.buttons===1){const box=e.currentTarget.getBoundingClientRect();seek(clamp(((e.clientX-box.left)/box.width*w-left)/(right-left)));}}}>
    <defs><clipPath id="elapsed-ecg"><rect x={left} y={0} width={Math.max(0,x(progress)-left)} height={h}/></clipPath><linearGradient id="cursor-glow"><stop stopColor="#caeeb4" stopOpacity="0"/><stop offset="1" stopColor="#caeeb4" stopOpacity=".09"/></linearGradient></defs>
    {Array.from({length:Math.floor(rr/.04)+1},(_,i)=><line key={`v${i}`} x1={x(i*.04/rr)} x2={x(i*.04/rr)} y1={top} y2={bottom} stroke={i%5===0?'#2d3c39':'#1c2a29'} strokeWidth={i%5===0?1:.6}/>)}
    {Array.from({length:10},(_,i)=><line key={`h${i}`} x1={left} x2={right} y1={baseline-(i-2)*14} y2={baseline-(i-2)*14} stroke={(i-2)%5===0?'#2d3c39':'#1c2a29'} strokeWidth={.7}/>)}
    {[0,1].map(v=><text key={v} x="30" y={y(v)+4} textAnchor="end" className="axis-label">{v}</text>)}
    <text x="8" y="14" className="axis-label">mV</text>
    {Array.from({length:Math.floor(rr/.2)+1},(_,i)=><text key={i} x={x(i*.2/rr)} y="171" textAnchor="middle" className="axis-label">{(i*.2).toFixed(1)}</text>)}
    <text x={(left+right)/2} y="196" className="axis-label" textAnchor="middle">Time (s)</text>
    <rect x={Math.max(left,x(progress)-65)} y={top} width={Math.min(65,x(progress)-left)} height={bottom-top} fill="url(#cursor-glow)"/>
    <path d={path} fill="none" stroke="#577065" strokeWidth="2.1" strokeLinejoin="round"/>
    <path d={path} fill="none" stroke="#c7ecb4" strokeWidth="2.5" strokeLinejoin="round" clipPath="url(#elapsed-ecg)"/>
    {[{label:'P',t:.075,v:.16},{label:'QRS',t:.213,v:1.14},{label:'T',t:(tStart+tEnd)/2,v:.31}].map(({label,t,v})=><text key={label} x={x(t/rr)} y={y(v)-13} textAnchor="middle" className="wave-label">{label}</text>)}
    <line x1={x(progress)} x2={x(progress)} y1={top} y2={bottom} stroke="#d5edc1" strokeWidth="1" strokeDasharray="3 4" opacity=".7"/>
    <circle cx={x(progress)} cy={y(ecgAt(progress*rr,bpm))} r="4.3" fill="#e3ffd1" stroke="#243b2c" strokeWidth="3"/>
  </svg>;
}
