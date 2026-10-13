// Optional diagnostic: rendering never depends on this report.
import fs from 'node:fs';
import path from 'node:path';
import {parseArgs} from 'node:util';
import puppeteer from 'puppeteer-core';
import {main} from './media-utils.mjs';
import {checkBounds} from './bounds-check.mjs';
import {browserPath} from './browser.mjs';
import {loadConfig,verifyProject,writeJSON,assert} from './common.mjs';

main(import.meta.url,async()=>{
 const {positionals,values}=parseArgs({allowPositionals:true,options:{browser:{type:'string'},effect:{type:'string',multiple:true}}});
 assert(positionals.length===1,'Usage: preview.mjs plan.json --browser <path> [--effect id]');
 const {config:c,base}=loadConfig(positionals[0]);
 const executablePath=browserPath(values.browser);
 const selected=new Set(values.effect??c.effects.map(e=>e.id));
 for(const id of selected)assert(c.effects.some(e=>e.id===id),`Unknown effect: ${id}`);
 const report={ok:true,mode:'sampled',effects:[]};let browser;
 try{
  for(const e of c.effects.filter(e=>selected.has(e.id))){
   try{
    verifyProject(e,c);
    assert(!fs.readFileSync(path.join(e.project,'index.html'),'utf8').includes('AUTHOR_CUSTOM_EFFECT'),`Author custom effect: ${e.id}`);
    browser??=await puppeteer.launch({executablePath,headless:true,args:['--disable-gpu','--allow-file-access-from-files']});
    const result=await checkBounds(c,e,{browser});report.effects.push(result);
   }catch(error){report.effects.push({id:e.id,ok:false,error:error.message});}
  }
 }finally{if(browser)await browser.close();}
 report.ok=report.effects.every(e=>e.ok);
 const file=path.join(base,'diagnostics.json');writeJSON(file,report);
 if(!report.ok)process.exitCode=1;
 return {ok:report.ok,checked:report.effects.length,report:file,failures:report.effects.filter(e=>!e.ok)};
});
