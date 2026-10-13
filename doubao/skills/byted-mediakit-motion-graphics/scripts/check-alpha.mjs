import {spawn} from 'node:child_process';
import {parseArgs} from 'node:util';
import {assert,probe} from './common.mjs';
import {main} from './media-utils.mjs';

export async function check(video,width,height,bounds=null) {
  assert(Number.isSafeInteger(width)&&width>0&&Number.isSafeInteger(height)&&height>0,'Invalid alpha dimensions');
  const meta=probe(video);assert(meta.video.width===width&&meta.video.height===height,'Alpha dimensions mismatch');
  if(bounds) for(const k of ['x','y','width','height'])assert(Number.isFinite(bounds[k]),'Invalid alpha bounds');
  const proc=spawn('ffmpeg',['-nostdin','-v','error','-threads','1','-i',video,'-map',`0:${meta.video.index}`,'-vf','alphaextract,format=gray','-f','rawvideo','-']);
  let stderr='';proc.stderr.on('data',chunk=>{stderr=(stderr+chunk).slice(-16000);});
  const done=new Promise(resolve=>{proc.on('error',error=>resolve({error}));proc.on('close',code=>resolve({code}));});
  let count=0,outside=0,last=null,offset=0,maximum=0,escaped=false;
  const size=width*height;
  try {
    for await(const chunk of proc.stdout) for(const value of chunk) {
      maximum=Math.max(maximum,value);
      if(bounds&&value>2) {const x=offset%width,y=Math.floor(offset/width);if(x<bounds.x-1||y<bounds.y-1||x+1>bounds.x+bounds.width+1||y+1>bounds.y+bounds.height+1)escaped=true;}
      if(++offset===size){count++;outside+=Number(escaped);last=maximum;offset=0;maximum=0;escaped=false;}
    }
    const result=await done;if(result.error)throw result.error;assert(result.code===0,stderr||'Alpha decoding failed');
    assert(offset===0,'Incomplete alpha frame');
    assert(count>0&&last===0&&outside===0,`Alpha violation: frames=${count}, last=${last}, outside=${outside}`);
    return {ok:true,frames:count,lastAlphaMax:last,outsideBoundsFrames:bounds?outside:null,method:'rendered alpha per frame; clipping cannot prove content was not truncated'};
  } finally {if(proc.exitCode===null)proc.kill();await done;}
}
main(import.meta.url,async()=>{const {positionals:p,values:v}=parseArgs({allowPositionals:true,options:{bounds:{type:'string'}}});assert(p.length===3,'Usage: check-alpha.mjs video width height [--bounds JSON]');return check(p[0],Number(p[1]),Number(p[2]),v.bounds?JSON.parse(v.bounds):null);});
