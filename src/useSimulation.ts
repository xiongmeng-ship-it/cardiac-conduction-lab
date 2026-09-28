import { useEffect, useRef, useState } from 'react';
import { advanceProgress, clamp, phaseStep } from './simulation';
export function useSimulation() {
  const [progress,setProgress] = useState(.02);
  const [playing,setPlaying] = useState(true);
  const [bpm,setBpm] = useState(75);
  const [speed,setSpeed] = useState(1);
  const last = useRef<number | null>(null);
  useEffect(()=>{
    last.current = null;
    if(!playing) return;
    let frame = 0;
    const animate = (now: number) => {
      if(!document.hidden) {
        if(last.current !== null) setProgress(p=>advanceProgress(p,Math.min((now-last.current!)/1000,.1),bpm,speed));
        last.current=now;
      } else last.current=null;
      frame=requestAnimationFrame(animate);
    };
    const visibility = ()=>{last.current=null;};
    document.addEventListener('visibilitychange',visibility);
    frame=requestAnimationFrame(animate);
    return ()=>{cancelAnimationFrame(frame);document.removeEventListener('visibilitychange',visibility);};
  },[playing,bpm,speed]);
  const seek = (p: number)=>{setPlaying(false);setProgress(clamp(p));};
  return {progress,playing,bpm,speed,setSpeed,setBpm,setPlaying,seek,step:(d:number)=>seek(phaseStep(progress,bpm,d)),reset:()=>{setPlaying(false);setProgress(0);setBpm(75);setSpeed(1);}};
}
