// One task, one browser and one reusable page. Clients may submit independently.
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {parseArgs} from 'node:util';
import puppeteer from 'puppeteer-core';
import {loadConfig,readJSON,assert,projectHash,verifyProject} from './common.mjs';
import {browserPath} from './browser.mjs';
import {measurePage} from './measure.mjs';
import {main} from './media-utils.mjs';

const directory=plan=>path.join(path.dirname(path.resolve(plan)),'.measure-service');
const statePath=plan=>path.join(directory(plan),'state.json');
const reply=(res,code,value)=>{res.writeHead(code,{'Content-Type':'application/json'});res.end(JSON.stringify(value));};

export function measurementSpec(planFile,id,{spec,atMs}={}) {
 const plan=readJSON(planFile),e=spec?readJSON(spec):plan.effects.find(e=>e.id===id);
 assert(e&&e.id===id,'Select a matching effect with --effect');
 return {id:e.id,project:path.resolve(path.dirname(path.resolve(planFile)),e.project??`effects/${e.id}`),durationMs:e.durationMs,
  atMs:atMs??(Array.isArray(e.hold)?e.hold[0]+e.hold[1]/2:NaN),layoutRect:e.layoutRect,motionBounds:e.motionBounds};
}

export async function startMeasurementService(planFile,{browser:executablePath,timeoutMs=30000,idleMs=1800000}={}) {
 const {config:c,base}=loadConfig(planFile,{skipPlan:true});
 executablePath=browserPath(executablePath);
 const dir=directory(planFile);
 try{fs.mkdirSync(dir,{mode:0o700});}catch(error){
  if(error.code==='EEXIST')throw Error('Measurement service directory exists; use status/stop. If stale, confirm its owner and browser have exited before removing .measure-service.');
  throw error;
 }
 fs.writeFileSync(path.join(dir,'owner.json'),JSON.stringify({pid:process.pid}),{mode:0o600});
 const token=crypto.randomUUID();let browser,page,tail=Promise.resolve(),pending=0,completed=0,browserStarts=0,accepting=true,idleTimer,closing;
 let resolveClosed;const closed=new Promise(resolve=>{resolveClosed=resolve;});
 async function resetBrowser(){
  const old=browser;browser=page=undefined;
  if(old){const child=old.process();try{await Promise.race([old.close().catch(()=>{}),new Promise(resolve=>setTimeout(resolve,2000).unref())]);}finally{if(child&&child.exitCode===null)child.kill('SIGKILL');}}
 }
 async function ensurePage(){
  if(!browser?.connected||!page||page.isClosed()){
   await resetBrowser();browser=await puppeteer.launch({executablePath,headless:true,timeout:10000,args:['--disable-gpu','--allow-file-access-from-files']});browserStarts++;
   fs.writeFileSync(path.join(dir,'owner.json'),JSON.stringify({pid:process.pid,browserPid:browser.process()?.pid}),{mode:0o600});
   page=await browser.newPage();await page.setViewport({width:c.videoInfo.width,height:c.videoInfo.height,deviceScaleFactor:1});
   await page.setCacheEnabled(false);page.setDefaultTimeout(timeoutMs);page.setDefaultNavigationTimeout(timeoutMs);
  }
 }
 function validate(spec){
  assert(spec&&/^[a-z][a-z0-9-]{0,63}$/.test(spec.id),'Invalid effect id');
  assert(c.effects.some(e=>e.id===spec.id),'Effect is not in the task plan loaded at service start; restart after adding IDs');
  const project=fs.realpathSync(spec.project);
  assert(project.startsWith(fs.realpathSync(base)+path.sep),'Project must be inside task directory');
  assert(Number.isFinite(spec.durationMs)&&spec.durationMs>=1000,'Invalid durationMs');
  assert(Number.isFinite(spec.atMs)&&spec.atMs>=0&&spec.atMs<spec.durationMs,'Invalid reading time');
  for(const key of ['layoutRect','motionBounds']){
   const r=spec[key];assert(Array.isArray(r)&&r.length===4&&r.every(Number.isFinite)&&r[0]>=0&&r[1]>=0&&r[2]>0&&r[3]>0&&r[0]+r[2]<=c.videoInfo.width&&r[1]+r[3]<=c.videoInfo.height,`Invalid ${key}`);
  }
  verifyProject({...spec,project},c);
  assert(!fs.readFileSync(path.join(project,'index.html'),'utf8').includes('AUTHOR_CUSTOM_EFFECT'),'Author the effect before measuring');
  return {...spec,project,projectHash:projectHash(project)};
 }
 function unchanged(spec,message){
  if(projectHash(spec.project)!==spec.projectHash)throw Object.assign(Error(message),{keepBrowser:true});
 }
 async function measure(spec){
  unchanged(spec,'Project changed while queued; resubmit');
  await ensurePage();const errors=[];const listener=e=>errors.push(e.message);page.on('pageerror',listener);
  try{
   // Clearing the document prevents prior timelines and globals from leaking across jobs.
   await page.goto('about:blank');
   await page.goto(pathToFileURL(path.join(spec.project,'index.html')).href,{waitUntil:'load'});
   const result=await measurePage(page,spec);assert(!errors.length,errors.join('; '));
   unchanged(spec,'Project changed during measurement; resubmit');
   return {id:spec.id,source:'project',...result,projectHash:spec.projectHash,atMs:spec.atMs,layoutRect:spec.layoutRect,motionBounds:spec.motionBounds};
  }finally{page?.off('pageerror',listener);}
 }
 function armIdle(){clearTimeout(idleTimer);if(accepting&&pending===0)idleTimer=setTimeout(()=>void stop(),idleMs).unref();}
 async function stop(){
  if(closing)return closing;
  accepting=false;clearTimeout(idleTimer);
  closing=(async()=>{await tail;await resetBrowser();await new Promise(resolve=>server.close(resolve));fs.rmSync(dir,{recursive:true,force:true});process.off('SIGINT',signal);process.off('SIGTERM',signal);resolveClosed();})();
  return closing;
 }
 const signal=()=>void stop();
 const server=http.createServer(async(req,res)=>{
  if(req.headers.authorization!==`Bearer ${token}`){reply(res,403,{ok:false,error:'Unauthorized'});return;}
  try{
   assert(req.method==='POST'&&req.url==='/','Unsupported request');let body='';
   for await(const chunk of req){body+=chunk;assert(Buffer.byteLength(body)<=65536,'Request too large');}
   const input=JSON.parse(body);
   if(input.action==='status'){reply(res,200,{ok:true,pid:process.pid,pending,completed,browserStarts,accepting});return;}
   if(input.action==='stop'){reply(res,200,{ok:true,draining:true});void stop();return;}
   assert(input.action==='measure'&&accepting,'Service is stopping or action is invalid');
   const spec=validate(input.spec),requestId=crypto.randomUUID();pending++;clearTimeout(idleTimer);
   const task=tail.then(async()=>{
    let timer;
    try{return await Promise.race([measure(spec),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Measurement timed out')),timeoutMs);})]);}
    catch(error){if(!error.keepBrowser)await resetBrowser();return {id:spec.id,ok:false,error:error.message};}
    finally{clearTimeout(timer);}
   });
   // Validation failures are results; every queued job gets its own response and receipt.
   tail=task.then(()=>{pending--;completed++;armIdle();});
   const result={requestId,...await task};
   const outputDir=path.join(base,'measurements');fs.mkdirSync(outputDir,{recursive:true});
   const receipt=path.join(outputDir,`${spec.id}-${requestId}.json`);fs.writeFileSync(receipt,JSON.stringify(result,null,2));
   reply(res,200,{...result,receipt});
  }catch(error){reply(res,400,{ok:false,error:error.message});}
 });
 try{
  await ensurePage();
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
  fs.writeFileSync(statePath(planFile),JSON.stringify({pid:process.pid,port:server.address().port,token}),{mode:0o600});
  process.on('SIGINT',signal);process.on('SIGTERM',signal);armIdle();
  return {stop,closed,status:()=>({pending,completed,browserStarts})};
 }catch(error){await resetBrowser();fs.rmSync(dir,{recursive:true,force:true});throw error;}
}

export async function serviceRequest(planFile,input){
 const state=readJSON(statePath(planFile));assert(Number.isInteger(state.port)&&state.port>0&&state.port<65536,'Invalid service port');
 const response=await fetch(`http://127.0.0.1:${state.port}/`,{method:'POST',headers:{Authorization:`Bearer ${state.token}`,'Content-Type':'application/json'},body:JSON.stringify(input),signal:AbortSignal.timeout(600000)});
 const result=await response.json();if(!response.ok)throw Error(result.error);return result;
}
main(import.meta.url,async()=>{
 const {positionals:[action,plan],values:v}=parseArgs({allowPositionals:true,options:{browser:{type:'string'},effect:{type:'string'},spec:{type:'string'},'at-ms':{type:'string'}}});
 assert(plan&&['serve','submit','status','stop'].includes(action),'Usage: measure-service.mjs serve|submit|status|stop plan.json [--browser path] [--effect id] [--spec effect.json] [--at-ms ms]');
 if(action==='serve'){const service=await startMeasurementService(plan,{browser:v.browser});console.log(JSON.stringify({ok:true,ready:true,pid:process.pid}));await service.closed;return {ok:true,stopped:true};}
 const result=await serviceRequest(plan,action==='submit'?{action:'measure',spec:measurementSpec(plan,v.effect,{spec:v.spec,atMs:v['at-ms']===undefined?undefined:Number(v['at-ms'])})}:{action});
 if(result.ok===false)process.exitCode=1;return result;
});
