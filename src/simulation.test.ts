import test from 'node:test';
import assert from 'node:assert/strict';
import { advanceProgress, ecgAt, motionAt, phaseAt, phases, phaseStep, timing } from './simulation';

test('all supported heart rates have a continuous, positive-duration phase sequence',()=>{
  for(let bpm=40;bpm<=120;bpm++){
    const {rr}=timing(bpm),list=phases(bpm);
    assert.equal(list[0].start,0);assert.equal(list.at(-1)!.end,rr);
    for(let i=0;i<list.length;i++){
      assert.ok(list[i].end>list[i].start,`${bpm}: ${list[i].id}`);
      if(i)assert.equal(list[i-1].end,list[i].start);
      const p=(list[i].start+list[i].end)/2/rr;
      assert.equal(phaseAt(p,bpm).id,list[i].id);
    }
  }
});
test('P, QRS and T map to atrial activation, ventricular activation and electrical recovery',()=>{
  for(const bpm of [40,75,120]){
    const {rr,tStart,tEnd}=timing(bpm);
    assert.equal(phaseAt(.075/rr,bpm).id,'atrial');
    assert.equal(phaseAt(.213/rr,bpm).id,'ventricular');
    assert.equal(phaseAt((tStart+tEnd)/2/rr,bpm).id,'repolarization');
    assert.ok(ecgAt(.213,bpm)>1);assert.ok(ecgAt(.075,bpm)>.1);assert.ok(ecgAt((tStart+tEnd)/2,bpm)>.25);
    assert.equal(ecgAt(rr,bpm),0);assert.ok(Math.abs(ecgAt(.16,bpm))<.001);
  }
});
test('heart-rate changes preserve QRS duration while reducing resting time and QT',()=>{
  const slow=timing(40),fast=timing(120);
  assert.equal(slow.qrsEnd-slow.qrsStart,fast.qrsEnd-fast.qrsStart);
  assert.ok(slow.qt>fast.qt);assert.ok(slow.rr-slow.tEnd>fast.rr-fast.tEnd);
});
test('mechanical contraction follows the corresponding electrical onset',()=>{
  const bpm=75,{rr,qrsStart,tEnd}=timing(bpm);
  assert.equal(motionAt(.025/rr,bpm).atrial,0);
  assert.ok(motionAt(.15/rr,bpm).atrial>.8);
  assert.equal(motionAt(qrsStart/rr,bpm).ventricular,0);
  assert.equal(motionAt(.213/rr,bpm).ventricular,0);
  assert.ok(motionAt(.35/rr,bpm).ventricular>.5);
  assert.ok(motionAt((tEnd-.01)/rr,bpm).ventricular>0);
  assert.equal(motionAt(.75/rr,bpm).ventricular,0);
});
test('playback speed scales elapsed time without altering physiology',()=>{
  assert.ok(Math.abs(advanceProgress(0,.1,75,1)-.125)<1e-10);
  assert.ok(Math.abs(advanceProgress(0,.1,75,.25)-.03125)<1e-10);
  assert.ok(Math.abs(advanceProgress(.95,.08,75,1)-.05)<1e-10);
  assert.equal(advanceProgress(.4,0,75,1),.4);
});
test('phase stepping wraps predictably and endpoint is the resting phase',()=>{
  assert.equal(phaseAt(phaseStep(0,75,-1),75).id,'filling');
  assert.equal(phaseAt(phaseStep(.999,75,1),75).id,'atrial');
  assert.equal(phaseAt(phaseStep(0,75,1),75).id,'delay');
  assert.equal(phaseAt(1,75).id,'filling');
});
