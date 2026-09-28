/** One shared, deterministic teaching timeline. Times are in seconds. */
export interface Phase { id: string; label: string; short: string; wave: string; start: number; end: number; electrical: string; mechanical: string; structures: string[] }
export const clamp = (v: number, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, v));
export function timing(bpm: number) {
  const rr = 60 / clamp(bpm, 40, 120);
  const qrsStart = .18, qrsEnd = .27;
  const qt = Math.min(.4 * Math.sqrt(rr), rr - .22);
  const tEnd = qrsStart + qt, tStart = tEnd - .15;
  return { rr, qrsStart, qrsEnd, qt, tStart, tEnd };
}
export function phases(bpm: number): Phase[] {
  const { rr, qrsStart, qrsEnd, tStart, tEnd } = timing(bpm);
  return [
    { id:'atrial',label:'Atrial depolarization',short:'Atrial activation',wave:'P wave',start:0,end:.13,electrical:'The SA node initiates an impulse that spreads through both atria. Their depolarization produces the P wave.',mechanical:'Atrial contraction follows electrical activation, helping complete ventricular filling.',structures:['sa','ra','la'] },
    { id:'delay',label:'AV nodal delay',short:'AV nodal delay',wave:'PR segment',start:.13,end:qrsStart,electrical:'Conduction slows at the AV node before the impulse enters the His–Purkinje system. The surface ECG is nearly isoelectric.',mechanical:'The atria finish contracting while the ventricles remain relaxed and fill.',structures:['av'] },
    { id:'ventricular',label:'Ventricular depolarization',short:'Ventricular activation',wave:'QRS complex',start:qrsStart,end:qrsEnd,electrical:'The impulse travels through the His bundle, bundle branches and Purkinje network. Rapid ventricular depolarization produces the QRS complex.',mechanical:'Ventricular tension begins to rise after activation. The AV valves close as ventricular pressure increases.',structures:['his','rbb','lbb','purkinje','septum'] },
    { id:'ejection',label:'Ventricular ejection',short:'Ventricular ejection',wave:'ST segment',start:qrsEnd,end:tStart,electrical:'Most ventricular muscle is depolarized. With little net electrical difference, the ST segment stays near baseline.',mechanical:'The ventricles contract and eject blood through the pulmonary and aortic valves.',structures:['rv','lv','aortic','pulmonary'] },
    { id:'repolarization',label:'Ventricular repolarization',short:'Electrical recovery',wave:'T wave',start:tStart,end:tEnd,electrical:'Ventricular cells recover electrically, generating the T wave. Repolarization is distinct from mechanical relaxation.',mechanical:'Contraction subsides toward the end of the T wave; ventricular relaxation follows.',structures:['rv','lv'] },
    { id:'filling',label:'Ventricular filling',short:'Rest & filling',wave:'TP segment',start:tEnd,end:rr,electrical:'The myocardium is electrically at rest before the next SA node impulse. The ECG returns to baseline.',mechanical:'Relaxed ventricles fill through the open mitral and tricuspid valves.',structures:['mitral','tricuspid','ra','la','rv','lv'] },
  ];
}
export function phaseAt(progress: number, bpm: number) {
  const t = clamp(progress) * timing(bpm).rr;
  const list = phases(bpm);
  return list.find(p => t >= p.start && t < p.end) ?? list[list.length - 1];
}
function bump(t: number, start: number, end: number) {
  if (t <= start || t >= end) return 0;
  return Math.sin(Math.PI * (t - start) / (end - start)) ** 2;
}
export function ecgAt(t: number, bpm: number): number {
  const { tStart, tEnd } = timing(bpm);
  const gaussian = (center: number, width: number, height: number) => height * Math.exp(-.5 * ((t-center)/width)**2);
  return .16 * bump(t,.025,.125)
    + (t >= .175 && t <= .275 ? gaussian(.19,.006,-.13)+gaussian(.213,.008,1.14)+gaussian(.241,.009,-.25) : 0)
    + .31 * bump(t,tStart,tEnd);
}
export function motionAt(progress: number, bpm: number) {
  const t = clamp(progress) * timing(bpm).rr;
  const { tEnd } = timing(bpm);
  return { atrial: bump(t,.075,.23), ventricular: bump(t,.225,Math.min(tEnd+.035,timing(bpm).rr)) };
}
export function advanceProgress(progress: number, elapsed: number, bpm: number, speed: number) {
  return (progress + Math.max(0,elapsed) * speed / timing(bpm).rr) % 1;
}
export function phaseStep(progress: number, bpm: number, direction: number) {
  const list = phases(bpm), active = phaseAt(progress,bpm);
  const index = (list.findIndex(p=>p.id===active.id)+direction+list.length)%list.length;
  return (list[index].start + .001) / timing(bpm).rr;
}
