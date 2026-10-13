import fs from 'node:fs';
import path from 'node:path';
import {parseArgs} from 'node:util';
import {assert,probe,run,readJSON,writeJSON} from './common.mjs';
import {digest,main} from './media-utils.mjs';
export {digest};
// Detect capabilities, including vendor builds with backported options.
export function frameSyncOptions(help=run('ffmpeg',['-hide_banner','-h','full'])){
  if(/^\s*-fps_mode(?=[\s:\[]|$)/m.test(help))return ['-fps_mode','cfr'];
  if(/^\s*-vsync(?=[\s:\[]|$)/m.test(help))return ['-vsync','1'];
  throw new Error('FFmpeg lacks fps_mode and vsync; cannot enforce constant output frame rate');
}
export function encodingOptions(info,options={}){
  const v=info.video;
  const codec='libx264';
  const crf=options.crf??20,preset=options.preset??'slow';
  assert(Number.isFinite(crf)&&crf>=0&&crf<=51,'crf must be between 0 and 51');
  assert(['medium','slow','slower','veryslow'].includes(preset),'Unsupported encoding preset');
  const pixFmt=['yuv420p','yuv420p10le','yuv422p','yuv422p10le','yuv444p','yuv444p10le'].includes(v.pix_fmt)?v.pix_fmt:'yuv420p';
  return {codec,pixFmt,crf,preset,args:['-c:v',codec,'-preset',preset,'-crf',String(crf),'-pix_fmt',pixFmt]};
}
export function validatePlacement(e,stream,source) {
  const legacy=e.x===undefined&&e.y===undefined;
  assert(legacy||(e.x!==undefined&&e.y!==undefined),'Both placement coordinates are required');
  if(legacy)assert(stream.width===source.width&&stream.height===source.height,'Legacy full-canvas effect dimensions mismatch');
  const x=e.x??0,y=e.y??0;
  assert(Number.isInteger(x)&&Number.isInteger(y)&&x>=0&&y>=0,'Invalid effect placement');
  assert(stream.width===e.width&&stream.height===e.height,'Artifact dimensions differ from manifest');
  assert(x+stream.width<=source.width&&y+stream.height<=source.height,'Effect placement outside source canvas');
  e.x=x;e.y=y;
}
export function loadManifest(file) {
  const base=path.dirname(path.resolve(file)),data=readJSON(file);
  assert(data.schemaVersion===1&&data.complete===true,'Manifest is incomplete or unsupported');
  const source=path.resolve(base,data.sourceVideo);
  const info=probe(source),effects=data.effects;
  assert(Array.isArray(effects)&&effects.length,'No effects');const ids=new Set();
  for(const e of effects){
    assert(typeof e.id==='string'&&!ids.has(e.id),'Duplicate or invalid effect id');ids.add(e.id);
    for(const k of ['startMs','durationMs','fps','layer'])assert(typeof e[k]==='number'&&Number.isFinite(e[k]),`Invalid ${k}`);
    assert(e.startMs>=0&&e.durationMs>0&&e.fps>0&&(e.startMs+e.durationMs)/1000<=info.duration+.001,'Effect timing outside source');
    e.path=path.resolve(base,e.path);assert(digest(e.path)===e.sha256,`Artifact changed: ${e.id}`);
    const meta=probe(e.path),s=meta.video;
    validatePlacement(e,s,info.video);
    assert(s.codec_name==='prores'&&s.profile?.includes('4444')&&s.pix_fmt?.includes('a'),'Expected transparent ProRes 4444 MOV');
    assert(Math.abs(meta.duration-e.durationMs/1000)<=1/e.fps+.001,'Effect duration mismatch');
  }
  return {source,info,effects:effects.sort((a,b)=>a.layer-b.layer||a.startMs-b.startMs||(a.id<b.id?-1:a.id>b.id?1:0))};
}
export function compose(manifest,output,start=0,duration=null,options={}){
  const {source,info,effects}=loadManifest(manifest),length=duration??info.duration-start;
  assert(Number.isFinite(start)&&Number.isFinite(length)&&start>=0&&length>0&&start+length<=info.duration+.001,'Invalid preview range');
  output=path.resolve(output);assert(!fs.existsSync(output)&&output!==source,'Output already exists or equals source; choose a new path');assert(path.extname(output).toLowerCase()==='.mp4','Final output must be .mp4');
  const rate=info.video.r_frame_rate??'0/0',[n,d]=rate.split('/').map(Number);assert(n/d>0&&n/d<=240,'Unsupported source frame rate; normalize source explicitly');
  fs.mkdirSync(path.dirname(output),{recursive:true});
  const args=['-nostdin','-n','-v','warning','-i',source];for(const e of effects)args.push('-i',e.path);
  const filters=[`[0:${info.video.index}]setpts=PTS-STARTPTS[base]`];let previous='base';
  effects.forEach((e,index)=>{const i=index+1,s=(e.startMs/1000).toFixed(6),end=((e.startMs+e.durationMs)/1000).toFixed(6);filters.push(`[${i}:v:0]setpts=PTS-STARTPTS+${s}/TB[fx${i}]`,`[${previous}][fx${i}]overlay=x=${e.x}:y=${e.y}:eof_action=pass:repeatlast=0:format=auto:enable='gte(t,${s})*lt(t,${end})'[v${i}]`);previous=`v${i}`;});
  args.push('-filter_complex_threads','1','-filter_complex',filters.join(';'),'-map',`[${previous}]`,'-map','0:a?');
  const full=start===0&&duration===null;if(!full)args.push('-ss',String(start),'-t',String(length));
  const encoding=encodingOptions(info,options);
  args.push('-r',rate,...frameSyncOptions(),...encoding.args,...(full?['-c:a','copy']:['-c:a','aac','-b:a','192k']),'-movflags','+faststart',output);
  run('ffmpeg',args);
  assert(fs.existsSync(output)&&fs.statSync(output).isFile()&&fs.statSync(output).size>0,'Composition produced no nonempty output');
  const stat=fs.statSync(output);
  const sourceSize=fs.statSync(source).size;
  const report={ok:true,output,outputSize:stat.size,sourceSize,sizeRatio:stat.size/sourceSize,outputMtimeMs:stat.mtimeMs,manifestSha256:digest(manifest),audioMode:full?'copy':'aac-preview',effects:effects.length,encoding:{codec:encoding.codec,pixFmt:encoding.pixFmt,crf:encoding.crf,preset:encoding.preset},validation:'command-success-and-nonempty-file'};
  // Internal completion receipt, not a video quality report or deliverable.
  writeJSON(path.join(path.dirname(path.resolve(manifest)),'export-state.json'),report);
  return report;
}
main(import.meta.url,()=>{const {positionals:p,values:v}=parseArgs({allowPositionals:true,options:{start:{type:'string',default:'0'},duration:{type:'string'},crf:{type:'string'},preset:{type:'string'}}});assert(p.length===2,'Usage: compose.mjs manifest output [--start seconds] [--duration seconds] [--crf number] [--preset slow]');return compose(p[0],p[1],Number(v.start),v.duration===undefined?null:Number(v.duration),{crf:v.crf===undefined?undefined:Number(v.crf),preset:v.preset});});
