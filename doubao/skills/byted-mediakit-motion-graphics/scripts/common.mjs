import {attachPlan} from './plan.mjs';
import {runScript} from './script-runtime.mjs';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import crypto from 'node:crypto';

export const skillDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const readJSON = p => JSON.parse(fs.readFileSync(p, 'utf8').replace(/^\uFEFF/, ''));
export function writeJSON(p, value) {
  fs.mkdirSync(path.dirname(p), {recursive:true});
  fs.writeFileSync(p, JSON.stringify(value, null, 2)+'\n');
}
export function assert(ok, message) { if (!ok) throw new Error(message); }
export function requireNode(version=process.versions.node) {
  const [major,minor]=version.split('.').map(Number);
  assert(major>22||(major===22&&minor>=12),`Node.js >=22.12.0 required (current: ${version}). Select a supported Node for this task.`);
}
export function nodeEnv(env=process.env) {
  const result={...env};
  const key=process.platform==='win32'?Object.keys(result).find(k=>k.toUpperCase()==='PATH')??'PATH':'PATH';
  result[key]=[path.dirname(process.execPath),result[key]].filter(Boolean).join(path.delimiter);
  return result;
}
export function cli(fn) {
  return runScript(()=>fn(process.argv.slice(2))).catch(e=>{console.error(JSON.stringify({ok:false,error:e.message}));process.exitCode=1;});
}
export function run(bin, args, options={}) {
  const result = spawnSync(bin, args, {encoding:'utf8', maxBuffer:32*1024*1024, ...options});
  if (result.error) throw result.error;
  if (result.status!==0) throw new Error(`${bin} failed (${result.status}): ${((result.stderr||'')+'\n'+(result.stdout||'')).slice(-16000)}`);
  return result.stdout;
}
export function probe(p) {
  const d=JSON.parse(run('ffprobe',['-v','error','-show_streams','-show_format','-of','json',p]));
  const v=d.streams.find(s=>s.codec_type==='video' && !s.disposition?.attached_pic);
  assert(v,`No video stream: ${p}`);
  return {...d,video:v,duration:Number(d.format.duration)};
}
export function number(n,lo,hi,label) {assert(typeof n==='number' && Number.isFinite(n) && n>=lo && n<=hi,`Invalid ${label}`);}
export function loadConfig(file,{skipPlan=false}={}) {
  requireNode();
  assert(file,'Usage: <script> <plan.json>');
  const configPath=path.resolve(file), base=path.dirname(configPath), c=readJSON(configPath);
  assert(c.schemaVersion===2,'plan.json schemaVersion must be 2');
  assert(typeof c.video==='string','video path required');
  c.video=path.resolve(base,c.video); assert(fs.existsSync(c.video),'Video does not exist');
  const media=probe(c.video); c.videoInfo={width:media.video.width,height:media.video.height,duration:media.duration};
  c.fps??=30; assert(Number.isInteger(c.fps) && c.fps>=1 && c.fps<=60,'fps must be integer 1–60');
  c.style??={};
  if(c.theme!==undefined) assert(['notion','cyberpunk','apple','aurora','tiktok'].includes(c.theme),'Unknown theme');
  assert(/^#[0-9a-f]{6}$/i.test(c.style.accentColor??'#F6C453'),'accentColor must be #RRGGBB');
  assert(typeof (c.style.fontFamily??'PingFang SC')==='string' && /^[\p{L}\p{N} _-]{1,64}$/u.test(c.style.fontFamily??'PingFang SC'),'Invalid fontFamily');
  assert(Array.isArray(c.effects) && c.effects.length>0,'effects must not be empty');
  const ids=new Set(), projects=new Set();
  for(const e of c.effects) {
    assert(/^[a-z][a-z0-9-]{0,63}$/.test(e.id) && !ids.has(e.id),'Invalid or duplicate effect id'); ids.add(e.id);
    e.mode??='custom';
    assert(e.mode==='custom',`Use custom mode: ${e.id}`);
    number(e.startMs,0,media.duration*1000,'startMs'); number(e.durationMs,1000,600000,'durationMs');
    assert(e.startMs+e.durationMs<=media.duration*1000+1,'Effect exceeds source duration');
    assert(Math.abs(e.durationMs*c.fps/1000-Math.round(e.durationMs*c.fps/1000))<1e-6,'durationMs must align to output fps');
    e.layer??=0; assert(Number.isInteger(e.layer),'layer must be integer');
    e.project??=`effects/${e.id}`; assert(typeof e.project==='string','project path required'); e.project=path.resolve(base,e.project);
    assert(e.project.startsWith(base+path.sep) && !e.project.startsWith(skillDir+path.sep),'Project must be inside task directory, outside skill');
    assert(!projects.has(e.project),'Project directories must be unique'); projects.add(e.project);
    if(e.source) e.source=path.resolve(base,e.source);
  }
  if(c.subtitles) {c.subtitles=path.resolve(base,c.subtitles);assert(fs.existsSync(c.subtitles),'Subtitles do not exist');}
  if(!skipPlan)attachPlan(c,base,configPath);
  return {config:c,base,configPath};
}
export function projectHash(project) {
  const hash=crypto.createHash('sha256');
  function walk(dir) {
    for(const name of fs.readdirSync(dir).sort()) {
      if(['node_modules','renders','snapshots','.hyperframes','.git','package-lock.json'].includes(name))continue;
      const p=path.join(dir,name),s=fs.lstatSync(p);
      assert(!s.isSymbolicLink(),`Symlinks are not supported in project: ${p}`);
      if(s.isDirectory())walk(p); else {hash.update(path.relative(project,p));hash.update(fs.readFileSync(p));}
    }
  } walk(project); return hash.digest('hex');
}
export function verifyProject(e,c) {
  const html=fs.readFileSync(path.join(e.project,'index.html'),'utf8');
  const attr=name=>html.match(new RegExp(`${name}=["']([^"']+)["']`))?.[1];
  assert(attr('data-composition-id')===e.id,'Composition id must match effect id');
  assert(Number(attr('data-width'))===c.videoInfo.width && Number(attr('data-height'))===c.videoInfo.height,'Composition dimensions mismatch');
  assert(Number(attr('data-duration'))===e.durationMs/1000,'Composition duration mismatch');
  assert(Number(attr('data-fps'))===c.fps,'Composition fps mismatch');
}
export const escapeHTML=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

export function shellHTML(e,c,body,css,timeline) {
  const {width:w,height:h}=c.videoInfo;
  const stage=e.plan?.layoutRect??{x:0,y:0,width:w,height:h};
  const content=`<div id="effect-stage"><div id="effect-content">${body}</div></div>`;
  const constraint=`#effect-clip{clip-path:none;overflow:visible}#effect-stage{position:absolute;left:${stage.x}px;top:${stage.y}px;width:${stage.width}px;height:${stage.height}px;overflow:visible}#effect-content{position:relative;width:100%;height:100%;overflow:visible}`;
  return `<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><title>${escapeHTML(e.id)}</title>
<script src="./vendor/gsap.min.js"></script><style>
@font-face{font-family:'${c.style.fontFamily??'PingFang SC'}';src:local('${c.style.fontFamily??'PingFang SC'}')}
*{box-sizing:border-box}html,body{margin:0;width:${w}px;height:${h}px;background:transparent;color:#fff;font-family:'${c.style.fontFamily??'PingFang SC'}',Arial,sans-serif}
#root{position:relative;width:${w}px;height:${h}px;overflow:hidden;--accent:${c.style.accentColor??'#F6C453'}}
.clip{position:absolute;inset:0}h1,h2,p{margin:0} ${css} ${constraint}
</style></head><body><div id="root" data-composition-id="${e.id}" data-start="0" data-width="${w}" data-height="${h}" data-fps="${c.fps}" data-duration="${e.durationMs/1000}">
<div id="effect-clip" class="clip" data-start="0" data-duration="${e.durationMs/1000}" data-track-index="1">${content}</div></div>
<script>window.__timelines=window.__timelines||{};const tl=gsap.timeline({paused:true});const D=${e.durationMs/1000};${timeline}
window.__timelines["${e.id}"]=tl;</script></body></html>`;
}
