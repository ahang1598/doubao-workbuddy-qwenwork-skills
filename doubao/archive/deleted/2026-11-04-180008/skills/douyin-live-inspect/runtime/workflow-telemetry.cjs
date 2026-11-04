'use strict';
// One small sidecar per real inspection request. Never stores input, URLs or credentials.
// State is an observation, not a delivery guarantee; missing events remain unknown.
const fs = require('node:fs');
const path = require('node:path');
const {createHash, randomUUID} = require('node:crypto');
const STAGES = new Set(['none','entry','startup','inspection','quality','recap','delivery']);
const REASONS = new Set(['none','OUT_OF_MEMORY', 'OPERATION_FAILED','TASK_FAILED','CONTENT_INSUFFICIENT','NO_CAPTURED_CONTENT',
 'NO_REVIEWED_CONTENT','NO_USABLE_TRANSCRIPT','ASR_RETRY_EXHAUSTED','REVIEW_FAILED','RECAP_FAILED','RECAP_TIMEOUT',
 'HOST_DELIVERY_FAILED','REPORT_NOT_READY','RUNTIME_UNAVAILABLE','SETUP_PENDING','INVALID_INPUT','AUTH_REQUIRED',
 'PERMISSION_DENIED','NETWORK_ERROR','REQUEST_TIMEOUT','WRITE_RESULT_UNKNOWN','CREATE_FAILED','CREATE_UNCERTAIN',
 'STREAM_RETRY_EXHAUSTED','DOUYIN_FETCH_FAILED','DOUYIN_PAGE_UNAVAILABLE','DOUYIN_FLV_UNAVAILABLE',
 'DOUYIN_RESOLVER_UNAVAILABLE','USER_STOP','WATCH_TIMEOUT','HOST_INTERRUPTED','TASK_BINDING_MISMATCH']);
const reason = value => REASONS.has(value) ? value : 'OPERATION_FAILED';
function read(file) {
 const fd=fs.openSync(file,fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW||0) | (fs.constants.O_NONBLOCK||0));
 try {const stat=fs.fstatSync(fd);if(!stat.isFile()||stat.size>256*1024)throw Error('invalid flow state');return JSON.parse(fs.readFileSync(fd,'utf8'));}finally{fs.closeSync(fd);}
}
function summary(s) {
 const tasks=Object.values(s.tasks), all=key=>tasks.length===s.expected && tasks.every(t=>t[key]==='delivered');
 const quality=all('quality'),recap=s.kind==='live' && all('recap');
 const generated=key=>tasks.length===s.expected && tasks.every(t=>t[key+'_generated']===true||['ready','delivered'].includes(t[key]));
 const qualityGenerated=generated('quality'),recapGenerated=s.kind==='live'&&generated('recap');
 const failed=tasks.find(t=>t.inspection==='failed'||t.quality==='failed'||t.recap==='failed');
 const insufficient=tasks.find(t=>t.quality==='insufficient'||t.recap==='insufficient');
 const success=(s.mode!=='lite'||s.lite_success===true) && tasks.length===s.expected && tasks.every(t=>t.inspection==='completed') && quality && (s.kind==='video'||recap);
 const result=success?'success':failed||s.problem?.terminal?'failed':insufficient?'insufficient':'unknown';
 const evidence={...(failed||insufficient||s.problem||tasks.find(t=>t.failure_reason && t.failure_reason!=='none')||{})};
 // An unrelated ready/read/ack must not erase an outstanding report outcome's cause.
 if((failed||insufficient)&&(!evidence.failure_reason||evidence.failure_reason==='none')){
  evidence.failure_stage=failed?.inspection==='failed'?'inspection':(failed||insufficient).quality=== (failed?'failed':'insufficient')?'quality':'recap';
  evidence.failure_reason=insufficient&&!failed?'CONTENT_INSUFFICIENT':evidence.failure_stage==='inspection'?'TASK_FAILED':'HOST_DELIVERY_FAILED';
 }
 const selected=['lite','formal'].includes(s.mode);
 const currentStage=success?'complete':evidence.failure_reason==='HOST_DELIVERY_FAILED'?'delivery':evidence.failure_stage&&evidence.failure_stage!=='none'?evidence.failure_stage:
  !selected?'version_selection':tasks.length<s.expected?'startup':!qualityGenerated?
   (tasks.every(t=>t.inspection==='completed')?'quality':'inspection'):
   s.kind==='live'&&!recapGenerated?'recap':!quality||(s.kind==='live'&&!recap)?'delivery':'finalizing';
 return {product:'douyin-live-inspect',record_type:'workflow',flow_schema:2,flow_id:s.id,flow_started_at:s.started,
  inspection_mode:s.mode,workflow_kind:s.kind==='live'?'live':s.kind==='video'?(s.batch||s.expected>1?'video_batch':'video_single'):'unknown',
  flow_result:result,version_selected:Number(selected),quality_generated:Number(qualityGenerated),recap_generated:Number(recapGenerated),current_stage:currentStage,task_created:Number(tasks.some(t=>t.created)),inspection_completed:Number(tasks.length===s.expected&&tasks.every(t=>t.inspection==='completed')),
  quality_delivered:Number(quality),recap_delivered:Number(recap),expected_tasks:s.expected,
  failure_stage:success?'none':evidence.failure_stage||'none',failure_reason:success?'none':evidence.failure_reason||'none',
  ...(s.uid?{doubao_user_id:s.uid}:{})};
}
async function mutate(change,{env=process.env,emit,strict=false}={}) {
 if(require('./telemetry-reporter.cjs').disabled(env))return;
 if(!env.INSPECT_USAGE_CONTEXT_DIR){if(strict)throw Error('original flow context required');return;}
 let lock,temporary,file,output;
 try {
  const root=fs.realpathSync(env.INSPECT_USAGE_CONTEXT_DIR), context=require('./lite-task-context.cjs').readContext(root);
  if(!context){if(strict)throw Error('original flow context required');return;}
  file=path.join(root,'.workflow-telemetry.json');const lockfile=file+'.lock';
  const until=Date.now()+500;
  while(!lock){try{const fd=fs.openSync(lockfile,'wx',0o600);lock={fd,file:lockfile};}catch(e){if(e.code!=='EEXIST'||Date.now()>until)throw e;await new Promise(r=>setTimeout(r,10));}}
  let state;try{state=read(file);}catch(e){if(e.code!=='ENOENT')throw e;}
  if(state && state.id!==context.task_id)throw Error('flow binding mismatch');
  const previous=state?JSON.stringify(summary(state)):null;
  state=await change(state,context);
  if(!state)return;
  const next=summary(state);
  if(previous!==JSON.stringify(next)){state.revision=(state.revision||0)+1;output={...next,flow_revision:state.revision};}
  temporary=file+'.'+randomUUID();fs.writeFileSync(temporary,JSON.stringify(state),{flag:'wx',mode:0o600});fs.renameSync(temporary,file);
 }catch(e){if(strict)throw e;}finally{if(temporary)try{fs.unlinkSync(temporary);}catch{}if(lock){fs.closeSync(lock.fd);fs.unlinkSync(lock.file);}}
 if(output){try{await (emit||((extra)=>require('./telemetry-reporter.cjs').reportEvent('workflow.snapshot',extra,{toolName:'douyin-live-inspect',env})))(output);}catch{/* no business replay */}}
 return output;
}
async function begin({kind,mode,expected}={},options={}) {
 return mutate(async(s,c)=>{
  if(!s){const uid=(await require('../lite/scripts/telemetry-identity.cjs').resolveIdentity(options.env||process.env)).doubao_user_id;
   s={id:c.task_id,started:Math.floor(Date.now()/1000),kind:'unknown',mode:'unselected',expected:1,tasks:{},uid};}
  if(['live','video'].includes(kind)){if(s.kind!=='unknown'&&s.kind!==kind)throw Error('flow kind mismatch');s.kind=kind;}
  if(['lite','formal'].includes(mode))s.mode=mode;
  if(expected!==undefined){if(!Number.isInteger(expected)||expected<1||expected>100||(s.kind!=='video'&&expected!==1))throw Error('invalid task count');if(Object.keys(s.tasks).length&&s.expected!==expected)throw Error('task count frozen');s.expected=expected;}
  return s;
 },options);
}
function key(identity){
 if(!identity||identity.environment!=='online'||!identity.profile||!identity.account_id||!identity.project_name||!/^\d+$/.test(String(identity.task_id)))throw Error('original task identity required');
 return createHash('sha256').update(JSON.stringify(['online',identity.profile,String(identity.account_id),identity.project_name,String(identity.task_id)])).digest('hex');
}
async function formal(identity,patch,options={}) {
 return mutate(s=>{
  if(!s)return;const id=key(identity);let t=s.tasks[id];
  if(!t&&!patch.created)return s; // Never attach an unrelated existing task by time or device.
  if(!t){if(Object.keys(s.tasks).length>=s.expected)throw Error('unexpected extra task');t=s.tasks[id]={created:true,inspection:'unknown',quality:'none',recap:'none'};}
  s.mode='formal';
  const blocked=s.problem?.failure_stage;
  // Only recovery at the affected stage clears an observed blocker.
  if((patch.created&&['entry','startup'].includes(blocked))||
    (['running','completed'].includes(patch.inspection)&&['entry','startup','inspection'].includes(blocked))||
    (patch.quality==='ready'&&blocked==='quality')||(patch.recap==='ready'&&blocked==='recap')||
    (patch.report_saved===true&&blocked==='delivery'&&!s.problem?.terminal))delete s.problem;
  for(const k of ['inspection','quality','recap'])if(patch[k]!==undefined){
   const allowed=k==='inspection'?['unknown','running','completed','failed']:['none','ready','delivered','insufficient','failed'];
   if(!allowed.includes(patch[k]))throw Error('invalid stage');
   // Re-reading a ready report must not revoke an acknowledged delivery.
   if(!(patch[k]==='ready'&&t[k]==='delivered'))t[k]=patch[k];
   if(k!=='inspection'&&['ready','delivered','insufficient','none'].includes(patch[k]))t[k+'_generated']=['ready','delivered'].includes(patch[k]);
  }
  if(patch.inspection==='running'){t.quality=t.recap='none';t.quality_generated=t.recap_generated=false;}
  // Keep the cause of an unresolved stage when another report is read.
  if(patch.failure_reason || !['failed','insufficient'].includes(t[t.failure_stage])) {
   t.failure_stage=STAGES.has(patch.failure_stage)?patch.failure_stage:'none';t.failure_reason=patch.failure_reason?reason(patch.failure_reason):'none';
  }
  return s;
 },options);
}
async function ack(identity,kind,outcome,options={}) {
 if(!['quality','recap'].includes(kind)||!['delivered','insufficient','failed'].includes(outcome))throw Error('invalid delivery acknowledgement');
 return mutate(s=>{
  if(!s)throw Error('original flow context required');const t=s.tasks[key(identity)];
  if(!t||t.inspection!=='completed'||(kind==='recap'&&s.kind!=='live'))throw Error('task is not ready');
  if(outcome==='delivered'&&!['ready','delivered'].includes(t[kind]))throw Error('report not ready');
  t[kind]=outcome;
  if(outcome==='insufficient')t[kind+'_generated']=false;
  if(outcome!=='delivered' || !['failed','insufficient'].includes(t[t.failure_stage])) {
   t.failure_stage=outcome==='delivered'?'none':kind;t.failure_reason=outcome==='insufficient'?'CONTENT_INSUFFICIENT':outcome==='failed'?'HOST_DELIVERY_FAILED':'none';
  }
  return s;
 },{...options,strict:true});
}
async function problem(stage,code,terminal=false,options={}) {
 return mutate(s=>{
  if(!s||summary(s).flow_result==='success'||(s.problem?.terminal&&!terminal))return s;
  s.problem={failure_stage:STAGES.has(stage)?stage:'entry',failure_reason:reason(code),terminal:!!terminal};return s;
 },options);
}
async function lite(event,options={}) {
 const e=event.extra||{};
 if(!['funnel.snapshot','task.started','task.resumed'].includes(event.command)||e.child_task_id||e.task_type==='live_recap')return;
 return mutate(s=>{
  if(!s||s.id!==e.task_id)return s;
  const order=[e.run_index||0,e.funnel_revision||0],old=s.lite_order||[-1,-1];
  if(order[0]<old[0]||(order[0]===old[0]&&order[1]<=old[1]))return s;
  s.lite_order=order;s.mode='lite';s.lite_success=e.workflow_success===1;s.batch=e.task_type==='video_batch';delete s.problem;
  // Batch snapshot is already an all-children projection; do not count each child again.
  s.expected=1;s.kind=e.task_type==='live_inspection'?'live':'video';
  const convert=v=>v==='ready'?'delivered':v==='failed'?'failed':'none';
  // A failed receipt can acknowledge a content-gap explanation, not a technical failure.
  const recapInsufficient=e.recap_status==='insufficient'||
   (e.recap_status==='blocked'&&e.flow_result==='insufficient'&&e.failure_stage==='recap');
  s.tasks={root:{created:true,inspection:e.quality_ready?'completed':e.flow_result==='failed'?'failed':'unknown',
   quality_generated:e.quality_ready===1,recap_generated:e.recap_status==='ready',
   quality:e.quality_ready?convert(e.quality_delivery):e.flow_result==='insufficient'?'insufficient':'none',
   recap:recapInsufficient?'insufficient':convert(e.recap_delivery),
   failure_stage:STAGES.has(e.failure_stage)?e.failure_stage:'none',failure_reason:reason(e.failure_reason||'none')}};
  if(e.flow_result==='failed')s.problem={terminal:true,failure_stage:STAGES.has(e.failure_stage)?e.failure_stage:'inspection',failure_reason:reason(e.failure_reason)};
  return s;
 },options);
}
async function observeEvent(event,env=process.env){
 if(event.command==='workflow.snapshot')return;
 let extra;try{extra=JSON.parse(event.extra||'{}');}catch{return;}
 if(['funnel.snapshot','task.started','task.resumed'].includes(event.command))return lite({command:event.command,extra},{env});
 if(event.result==='failure'||event.result==='business_rejected'||event.result==='cancelled'){
  const stage=extra.startup_stage?'startup':extra.feature==='live_recap'?'recap':extra.feature==='quality_report'?'quality':'inspection';
  return problem(stage,extra.error_code||'OPERATION_FAILED',event.command==='start'&&extra.startup_outcome==='failed',{env});
 }
}
module.exports={begin,formal,ack,problem,lite,observeEvent,summary,reason};
