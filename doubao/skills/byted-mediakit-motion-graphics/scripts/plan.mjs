import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const check=(ok,msg)=>{if(!ok)throw Error(msg);};
export const digest=v=>crypto.createHash('sha256').update(typeof v==='string'||Buffer.isBuffer(v)?v:JSON.stringify(v)).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const nonempty=v=>typeof v==='string'&&v.trim().length>0;
export function rect(r,w,h,label='rectangle') {
  check(r&&['x','y','width','height'].every(k=>Number.isFinite(r[k])),`Invalid ${label}`);
  check(r.x>=0&&r.y>=0&&r.width>0&&r.height>0&&r.x+r.width<=w&&r.y+r.height<=h,`${label} outside canvas`);
}
export const intersects=(a,b,m=0)=>a.x<b.x+b.width+m&&a.x+a.width>b.x-m&&a.y<b.y+b.height+m&&a.y+a.height>b.y-m;
export const contains=(a,b)=>b.x>=a.x&&b.y>=a.y&&b.x+b.width<=a.x+a.width&&b.y+b.height<=a.y+a.height;
// Protection regions are in source pixels.
export function validateProtection(bounds,regions,w,h,margin,id){
 check(Array.isArray(regions),'protectedRegions required; record observed regions before generating');
 check(Number.isFinite(margin)&&margin>=0,'Invalid safeMargin');
 for(const region of regions){
  check(nonempty(region.frameId)&&nonempty(region.kind),'Protected region needs reviewed frame/kind');
  rect(region.rect,w,h,'protected region');
  check(!intersects(bounds,region.rect,margin),`Motion bounds overlaps protected region: ${id}/${region.kind}. Move position, reflow content or choose another interval; retain the observed protection region.`);
 }
}
export function density(effects,durationMs,windowMs=30000) {
  check(Number.isFinite(windowMs)&&windowMs>0,'Invalid density window');
  const spans=effects.map(e=>[e.startMs,e.startMs+e.durationMs]).sort((a,b)=>a[0]-b[0]);const merged=[];
  for(const [a,b] of spans){const last=merged.at(-1);if(last&&a<=last[1])last[1]=Math.max(last[1],b);else merged.push([a,b]);}
  const events=spans.flatMap(([a,b])=>[[a,1],[b,-1]]).sort((a,b)=>a[0]-b[0]||a[1]-b[1]);let active=0,maxSimultaneous=0;
  for(const [,delta] of events){active+=delta;maxSimultaneous=Math.max(maxSimultaneous,active);}
  const windows=[];for(let startMs=0;startMs<durationMs;startMs+=windowMs){const endMs=Math.min(durationMs,startMs+windowMs);const coverageMs=merged.reduce((s,[a,b])=>s+Math.max(0,Math.min(b,endMs)-Math.max(a,startMs)),0);windows.push({startMs,endMs,coverageMs,ratio:coverageMs/(endMs-startMs)});}
  const coverageMs=merged.reduce((s,[a,b])=>s+b-a,0);
  return {count:effects.length,eventsPerMinute:effects.length*60000/durationMs,coverageMs,coverageRatio:coverageMs/durationMs,longestContinuousMs:Math.max(0,...merged.map(([a,b])=>b-a)),maxSimultaneous,windows};
}
export function validatePlanData(plan,nodes,style,evidence,c) {
  const {width:w,height:h,duration}=c.videoInfo;
  check(plan.schemaVersion===1&&nodes.schemaVersion===1&&style.schemaVersion===1&&evidence.schemaVersion===1,'Planning schemaVersion must be 1');
  check(Array.isArray(nodes.nodes)&&Array.isArray(plan.effects),'nodes/effects arrays required');
  for(const key of ['referenceReason','fontFamily','motion','palette','layoutLanguage'])check(nonempty(style[key]),`style.${key} must be a non-empty string`);
  check(Number.isFinite(style.minFontSize)&&style.minFontSize>=12,'style.minFontSize must be >=12 source pixels');
  check(style.fontFamily===(c.style.fontFamily??'PingFang SC'),'Style font differs from config');
  const ns=new Map();for(const n of nodes.nodes){check(nonempty(n.id)&&!ns.has(n.id),'Duplicate/invalid node id');check(['key','optional','leave'].includes(n.priority),'Invalid node priority');check(nonempty(n.summary)&&nonempty(n.evidence),'Node summary/evidence required');check(Number.isFinite(n.startMs)&&Number.isFinite(n.endMs)&&n.startMs>=0&&n.endMs>n.startMs&&n.endMs<=duration*1000+1,'Invalid node timing');ns.set(n.id,n);}
  const warnings=[],frames=new Map();
  for(const f of evidence.frames??[]){
    const timeMs=f.actualMs??f.timeMs;
    check(nonempty(f.id)&&!frames.has(f.id)&&Number.isFinite(timeMs)&&timeMs>=0&&timeMs<=duration*1000+1,'Invalid/duplicate evidence frame');
    if(f.actualMs===undefined)check(['reported','requested','interval'].includes(f.timeBasis),'Frame timeBasis required for timeMs');
    frames.set(f.id,{...f,actualMs:timeMs});
  }
  check(frames.size>0,'Frame observation missing');
  check(plan.effects.length===c.effects.length,'Plan/config effect count differs');
  const used=new Set(),ids=new Set();
  for(const p of plan.effects){
    check(nonempty(p.id)&&!ids.has(p.id),'Duplicate plan effect');ids.add(p.id);
    const e=c.effects.find(e=>e.id===p.id),n=ns.get(p.nodeId);check(e&&n,'Missing config effect or content node');used.add(n.id);
    check(n.priority!=='leave','Leave node cannot produce effect');
    check(e.startMs===p.startMs&&e.durationMs===p.durationMs&&e.mode===p.mode,'Plan timing/mode differs from config');
    if(p.startMs<n.startMs||p.startMs+p.durationMs>n.endMs){
      check(nonempty(p.timingReason),`Timing outside node needs timingReason: effect=${p.id}, node=${n.id}; effect startMs=${p.startMs}, endMs=${p.startMs+p.durationMs}, durationMs=${p.durationMs}; node startMs=${n.startMs}, endMs=${n.endMs}; startsEarlyMs=${Math.max(0,n.startMs-p.startMs)}, endsLateMs=${Math.max(0,p.startMs+p.durationMs-n.endMs)}`);
    }
    for(const key of ['intent','valueAdded','selectionReason','visualObservation'])check(nonempty(p[key]),`Missing ${key}: ${p.id}`);
    rect(p.layoutRect,w,h,'layoutRect');rect(p.motionBounds,w,h,'motionBounds');check(contains(p.motionBounds,p.layoutRect),'layoutRect must fit motionBounds');
    check(Number.isFinite(p.safeMargin)&&p.safeMargin>=0,'safeMargin required');
    check(Number.isFinite(p.holdMs)&&p.holdMs>=500&&p.holdMs<=p.durationMs-200,'Invalid holdMs');
    check(Number.isFinite(p.holdStartMs)&&p.holdStartMs>=0&&p.holdStartMs+p.holdMs<=p.durationMs,'Invalid hold interval');
    check(Array.isArray(p.evidenceFrames)&&new Set(p.evidenceFrames).size===p.evidenceFrames.length&&p.evidenceFrames.length>=1,'At least one reviewed frame required');
    const reviewed=p.evidenceFrames.map(id=>{check(frames.has(id),`Unknown frame ${id}`);return frames.get(id);}).sort((a,b)=>a.actualMs-b.actualMs);
    const start=p.startMs,end=start+p.durationMs;
    const intervalViews=reviewed.filter(f=>f.actualMs>=start-50&&f.actualMs<end);
    if(intervalViews.length<3||intervalViews[0].actualMs>start+50||intervalViews.at(-1).actualMs<end-100)warnings.push(`${p.id}: sampled views do not cover the full interval; assess motion and add source views if needed`);
    check(Array.isArray(p.protectedRegions),'protectedRegions array required; [] needs explicit visualObservation');
    for(const region of p.protectedRegions)check(p.evidenceFrames.includes(region.frameId),'Protected region needs reviewed frame/kind');
    validateProtection(p.motionBounds,p.protectedRegions,w,h,p.safeMargin,p.id);
  }
  for(const n of ns.values())if(!used.has(n.id))check(nonempty(n.omissionReason),`Unselected node needs omissionReason: ${n.id}`);
  for(let i=0;i<plan.effects.length;i++)for(let j=i+1;j<plan.effects.length;j++){const a=plan.effects[i],b=plan.effects[j];if(a.startMs<b.startMs+b.durationMs&&a.startMs+a.durationMs>b.startMs)check(!intersects(a.motionBounds,b.motionBounds),`Simultaneous effects overlap: ${a.id}/${b.id}`);}
  return {...density(plan.effects,duration*1000,plan.densityWindowMs??30000),warnings};
}
// Compact on-disk inputs are expanded only in memory for rendering and geometry checks.
export function expandSheets(input) {
  check(input.schemaVersion===2&&Array.isArray(input.sheets),'frames.json requires schemaVersion 2 and sheets');
  const ids=new Set(),frames=[];
  for(const sheet of input.sheets){
    check(typeof sheet.id==='string'&&/^[a-z][a-z0-9-]*$/.test(sheet.id)&&!ids.has(sheet.id),'Invalid/duplicate sheet id');ids.add(sheet.id);
    check(nonempty(sheet.url)||nonempty(sheet.path),'Sheet URL or path required');
    const columns=sheet.columns??4,basis=sheet.timeBasis??'requested';
    check(Number.isInteger(columns)&&columns>0,'Sheet columns must be a positive integer');
    check(['requested','reported','interval','actual'].includes(basis),'Invalid sheet timeBasis');
    check(Array.isArray(sheet.timesMs)&&sheet.timesMs.length>0,'Sheet timesMs required');
    sheet.timesMs.forEach((time,i)=>{
      check(Number.isFinite(time)&&time>=0&&(i===0||time>sheet.timesMs[i-1]),'Sheet timesMs must be finite, nonnegative and increasing');
      frames.push({id:`${sheet.id}:${i+1}`,sheetId:sheet.id,cell:i+1,columns,url:sheet.url,path:sheet.path,...(basis==='actual'?{actualMs:time}:{timeMs:time,timeBasis:basis})});
    });
  }
  return {schemaVersion:1,frames};
}
const expandRect=(r,label)=>{
  check(Array.isArray(r)&&r.length===4&&r.every(Number.isFinite),`${label} must be [x,y,width,height]`);
  const [x,y,width,height]=r;return {x,y,width,height};
};
export function expandEffect(e,evidence) {
  check(Array.isArray(e.views)&&e.views.length>0,'views must name reviewed sheets or sheet:cell references');
  const refs=[];
  for(const ref of e.views){
    check(nonempty(ref),'Invalid view reference');
    const matches=evidence.frames.filter(f=>f.id===ref||f.sheetId===ref);
    check(matches.length>0,`Unknown view ${ref}`);refs.push(...matches.map(f=>f.id));
  }
  check(nonempty(e.reason),'Effect reason required: state content and purpose');
  check(Array.isArray(e.hold)&&e.hold.length===2,'hold must be [startMs,durationMs]');
  check(Array.isArray(e.protectedRegions),'protectedRegions required; use [] only after observation');
  const {plan:ignored,...effect}=e;
  return {...effect,intent:e.reason,valueAdded:e.reason,selectionReason:e.reason,
    evidenceFrames:[...new Set(refs)],layoutRect:expandRect(e.layoutRect,'layoutRect'),motionBounds:expandRect(e.motionBounds,'motionBounds'),
    protectedRegions:e.protectedRegions.map(r=>({...r,rect:expandRect(r.rect,'protected region')})),
    safeMargin:e.safeMargin??20,holdStartMs:e.hold[0],holdMs:e.hold[1]};
}
export function attachPlan(c,base,planPath=path.join(base,'plan.json')) {
  check(c.schemaVersion===2,'plan.json schemaVersion must be 2');
  check(Array.isArray(c.nodes),'plan.nodes required; complete pre-add planning first');
  const evidencePath=path.resolve(base,c.frames??'frames.json'),evidence=expandSheets(read(evidencePath));
  const nodes={schemaVersion:1,nodes:c.nodes},style={...c.style,schemaVersion:1};
  const plan={schemaVersion:1,effects:c.effects.map(e=>expandEffect(e,evidence)),densityWindowMs:c.densityWindowMs};
  const stats=validatePlanData(plan,nodes,style,evidence,c);
  c.planInfo={path:planPath,stats,hash:digest({plan,nodes,style,evidence}),style};
  for(const e of c.effects)e.plan=plan.effects.find(p=>p.id===e.id);
}
export const executionHash=c=>digest({video:c.video,plan:c.planInfo?.hash,fps:c.fps,style:c.style,effects:c.effects.map(e=>({id:e.id,startMs:e.startMs,durationMs:e.durationMs,layer:e.layer,mode:e.mode,props:e.props,project:e.project,canvasMode:e.canvasMode,canvasPadding:e.canvasPadding}))});
