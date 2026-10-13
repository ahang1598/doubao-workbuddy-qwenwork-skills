import fs from 'node:fs';
import {runScript} from './script-runtime.mjs';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
export function digest(file) {
  const hash=crypto.createHash('sha256'), buffer=Buffer.alloc(1024*1024), fd=fs.openSync(file,'r');
  try {let n;while((n=fs.readSync(fd,buffer,0,buffer.length,null)))hash.update(buffer.subarray(0,n));}
  finally {fs.closeSync(fd);}
  return hash.digest('hex');
}
export function isMain(url) {
  if(!process.argv[1])return false;
  try{return fs.realpathSync(process.argv[1])===fs.realpathSync(fileURLToPath(url));}
  catch{return false;}
}
export function main(url,fn) {
  if(isMain(url))
    return runScript(fn).then(result=>console.log(JSON.stringify(result))).catch(error=>{console.error(JSON.stringify({ok:false,error:error.message}));process.exitCode=1;});
}
