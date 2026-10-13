import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {assert,requireNode,skillDir,nodeEnv} from './common.mjs';
import {browserEnv} from './browser.mjs';

export function renderConcurrency(requested='2',count) {
  assert(/^[1-3]$/.test(String(requested)),'--jobs must be 1, 2, or 3');
  return {mode:String(requested),concurrency:Math.min(count,Number(requested))};
}

export async function renderQueue(jobs,concurrency,execute) {
  let next=0,failure;const active=new Set();
  while(next<jobs.length||active.size) {
    while(!failure&&next<jobs.length&&active.size<concurrency) {
      const job=jobs[next++];
      const task=Promise.resolve().then(()=>execute(job)).catch(error=>{failure??={error};}).finally(()=>active.delete(task));
      active.add(task);
    }
    if(active.size)await Promise.race(active);
    else break;
  }
  if(failure)throw failure.error;
}

export function runAsync(bin,args,options={}) {
  return new Promise((resolve,reject)=>{
    const child=spawn(bin,args,{...options,stdio:['ignore','pipe','pipe']});
    let output='',bytes=0,overflow=false;
    const collect=chunk=>{
      bytes+=Buffer.byteLength(chunk);
      if(bytes>32*1024*1024){overflow=true;child.kill();return;}
      output+=chunk;
    };
    child.stdout.setEncoding('utf8');child.stderr.setEncoding('utf8');
    child.stdout.on('data',collect);child.stderr.on('data',collect);
    child.on('error',reject);
    child.on('close',(code,signal)=>{
      if(overflow)reject(new Error(`${bin} output exceeded 32 MiB`));
      else if(code!==0)reject(new Error(`${bin} failed (${signal??code}): ${output.slice(-16000)}`));
      else resolve(output);
    });
  });
}
export function hfAsync(project,args,browser) {
  requireNode();
  const bin=path.join(skillDir,'node_modules/hyperframes/bin/hyperframes.mjs');
  assert(fs.existsSync(bin),'Install dependencies first: npm install --prefix <skill-dir>');
  return runAsync(process.execPath,[bin,...args],{cwd:project,env:{...nodeEnv(browserEnv(browser)),DO_NOT_TRACK:'1',HYPERFRAMES_TELEMETRY_DISABLED:'1'}});
}
