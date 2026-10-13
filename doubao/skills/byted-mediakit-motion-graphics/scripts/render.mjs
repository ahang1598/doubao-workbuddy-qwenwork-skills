import {executionHash} from './plan.mjs';
import fs from 'node:fs';
import path from 'node:path';
import {parseArgs} from 'node:util';
import {browserPath} from './browser.mjs';
import {loadConfig,verifyProject,writeJSON,projectHash,assert,probe} from './common.mjs';
import {main,digest} from './media-utils.mjs';
import {hfAsync,renderConcurrency,renderQueue,runAsync} from './render-runtime.mjs';
import {renderCanvas,localCanvasHTML,CANVAS_VERSION} from './render-canvas.mjs';

// Dependency injection keeps resume/failure tests independent of a browser render.
export async function renderEffects(c,base,{browser,effect,jobs='2'}={},io={}){
  const lock=path.join(base,'.render.lock');
  try {fs.mkdirSync(lock);} catch(error) {
    if(error.code==='EEXIST')throw new Error(`Render already locked: ${lock}; if a previous process was interrupted, confirm it has exited before removing this lock directory`);
    throw error;
  }
  try {
    fs.writeFileSync(path.join(lock,'owner.json'),JSON.stringify({pid:process.pid,startedAt:new Date().toISOString()}));
    return await renderLocked(c,base,{browser,effect,jobs},io);
  } finally {fs.rmSync(lock,{recursive:true,force:true});}
}

async function renderLocked(c,base,{browser,effect,jobs:requestedJobs},io){
  const selected=effect===undefined?null:new Set(effect);
  if(selected)for(const id of selected)assert(c.effects.some(e=>e.id===id),`Unknown effect: ${id}`);
  const manifest=path.join(base,'artifacts.json'),renderDir=path.join(base,'renders');
  const previous=fs.existsSync(manifest)?JSON.parse(fs.readFileSync(manifest,'utf8')):null;
  const jobs=c.effects.map(e=>{
    verifyProject(e,c);
    assert(!fs.readFileSync(path.join(e.project,'index.html'),'utf8').includes('AUTHOR_CUSTOM_EFFECT'),`Author custom effect: ${e.id}`);
    const html=fs.readFileSync(path.join(e.project,'index.html'),'utf8'),canvas=renderCanvas(e,c,html);
    const hash=projectHash(e.project),output=path.join(renderDir,`${e.id}.mov`);
    const old=previous?.schemaVersion===1&&previous.sourceVideo===c.video?previous.effects?.find(item=>item.id===e.id):null;
    let reusable=Boolean(old&&old.projectHash===hash&&old.fps===c.fps&&old.durationMs===e.durationMs&&old.width===canvas.width&&old.height===canvas.height&&old.x===canvas.x&&old.y===canvas.y&&old.canvasVersion===CANVAS_VERSION&&path.resolve(old.path)===output&&fs.existsSync(output));
    if(reusable)reusable=digest(output)===old.sha256;
    const render=selected?selected.has(e.id):!reusable;
    assert(render||reusable,`Missing or stale artifact: ${e.id}; include it with --effect or run without --effect`);
    return {e,hash,output,render,old,canvas,html};
  });
  const pendingJobs=jobs.filter(j=>j.render).sort((a,b)=>b.e.durationMs-a.e.durationMs);
  const scheduling=renderConcurrency(requestedJobs,pendingJobs.length);
  console.error(`Render jobs: ${scheduling.concurrency}; workers=1`);
  const artifacts={schemaVersion:1,complete:pendingJobs.length===0,sourceVideo:c.video,planHash:c.planInfo?.hash,executionHash:executionHash(c),videoInfo:c.videoInfo,effects:jobs.filter(j=>!j.render).map(({e,old})=>({...old,startMs:e.startMs,layer:e.layer,project:e.project}))};
  fs.mkdirSync(renderDir,{recursive:true});
  const save=()=>{const temp=manifest+`.${process.pid}.tmp`;try{writeJSON(temp,artifacts);fs.renameSync(temp,manifest);}finally{if(fs.existsSync(temp))fs.unlinkSync(temp);}};
  save();
  await renderQueue(pendingJobs,scheduling.concurrency,async({e,hash,output,canvas,html})=>{
    const staging=fs.mkdtempSync(path.join(renderDir,`.${e.id}-`));
    const pending=path.join(staging,'effect.mov');
    try{
      console.error(`Rendering ${e.id}`);
      let project=e.project;
      if(canvas.mode==='local') {
        project=path.join(staging,'project');
        fs.cpSync(e.project,project,{recursive:true,filter:p=>p===e.project||!['node_modules','.git','renders','snapshots','.hyperframes'].includes(path.basename(p))});
        fs.writeFileSync(path.join(project,'index.html'),localCanvasHTML(html,canvas,c.videoInfo));
      }
      console.error(`Canvas ${e.id}: ${canvas.width}x${canvas.height} at ${canvas.x},${canvas.y} (${canvas.reason})`);
      const logs=await (io.hf??hfAsync)(project,['render','--format','mov','--fps',String(c.fps),'--workers','1','--output',pending],browser);
      fs.writeFileSync(path.join(renderDir,`${e.id}.log`),logs);
      let meta=await (io.probe??probe)(pending);
      const verify=()=>{
        const v=meta.video;
        assert(v.codec_name==='prores'&&/4444/.test(v.profile)&&/a/.test(v.pix_fmt),'Expected ProRes 4444 with alpha');
        assert(Math.abs(meta.duration-e.durationMs/1000)<=1/c.fps+.001,'Rendered duration mismatch');
        const [rn,rd]=v.avg_frame_rate.split('/').map(Number);assert(Math.abs(rn/rd-c.fps)<.001,'Rendered fps mismatch');
      };
      verify();
      const {width,height}=canvas;
      if(meta.video.width!==width||meta.video.height!==height){
        const scale=meta.video.width/width;
        assert(Number.isInteger(scale)&&scale>1&&meta.video.height===height*scale,`Rendered dimensions ${meta.video.width}x${meta.video.height} differ from plan ${width}x${height}; expected matching dimensions or uniform integer supersampling`);
        const normalized=path.join(staging,'normalized.mov');
        const note=`Normalizing ${scale}x render from ${meta.video.width}x${meta.video.height} to ${width}x${height}, preserving ProRes 4444 alpha`;
        console.error(note);fs.appendFileSync(path.join(renderDir,`${e.id}.log`),`\n${note}\n`);
        await (io.run??runAsync)('ffmpeg',['-nostdin','-n','-v','error','-i',pending,'-map','0:v:0','-an','-vf',`scale=${width}:${height}:flags=lanczos,setsar=1`,'-c:v','prores_ks','-profile:v','4','-pix_fmt','yuva444p10le','-threads','1',normalized]);
        meta=await (io.probe??probe)(normalized);verify();
        assert(meta.video.width===width&&meta.video.height===height,'Normalized dimensions differ from plan');
        fs.renameSync(normalized,pending);
      }
      const v=meta.video;
      const sha256=digest(pending);fs.renameSync(pending,output);
      artifacts.effects.push({id:e.id,path:output,startMs:e.startMs,durationMs:e.durationMs,layer:e.layer,x:canvas.x,y:canvas.y,canvasMode:canvas.mode,canvasVersion:CANVAS_VERSION,width:v.width,height:v.height,fps:c.fps,actualDuration:meta.duration,alphaMode:'transparent',alphaCheck:{status:'not-run',reason:'Alpha-capable format verified; pixel checks optional'},project:e.project,projectHash:hash,sha256});
      save();
    }catch(error){fs.appendFileSync(path.join(renderDir,`${e.id}.log`),'\n'+String(error.stack??error));throw error;}
    finally{fs.rmSync(staging,{recursive:true,force:true});}
  });
  artifacts.effects.sort((a,b)=>c.effects.findIndex(e=>e.id===a.id)-c.effects.findIndex(e=>e.id===b.id));
  artifacts.complete=true;save();
  return {ok:true,manifest,scheduling,rendered:jobs.filter(j=>j.render).map(j=>j.e.id),reused:jobs.filter(j=>!j.render).map(j=>j.e.id)};
}
main(import.meta.url,()=>{
  const {positionals,values}=parseArgs({allowPositionals:true,options:{browser:{type:'string'},effect:{type:'string',multiple:true},jobs:{type:'string',default:'2'}}});
  assert(positionals.length===1,'Usage: render.mjs plan.json --browser <path> [--effect id] [--jobs 1|2|3]');
  const {config:c,base}=loadConfig(positionals[0]);
  assert(c.planInfo,'Complete plan.json is required');
  return renderEffects(c,base,{browser:browserPath(values.browser),effect:values.effect,jobs:values.jobs});
});
