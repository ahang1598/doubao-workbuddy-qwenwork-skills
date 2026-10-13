import {main} from './media-utils.mjs';
import {measurePage} from './measure.mjs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import puppeteer from 'puppeteer-core';
import {loadConfig,assert,writeJSON,projectHash} from './common.mjs';
import {executionHash} from './plan.mjs';
import {browserPath} from './browser.mjs';
import {parseArgs} from 'node:util';
export async function checkBounds(c,e,{browser:sharedBrowser,executablePath}={}){
  const browser=sharedBrowser??await puppeteer.launch({executablePath:browserPath(executablePath),headless:true,args:['--disable-gpu','--allow-file-access-from-files']});
  let page;
  try{
    page=await browser.newPage();await page.setViewport({width:c.videoInfo.width,height:c.videoInfo.height,deviceScaleFactor:1});
    await page.setRequestInterception(true);page.on('request',r=>{if(/^(file:|data:|about:)/.test(r.url()))r.continue();else r.abort();});
    const errors=[];page.on('pageerror',err=>errors.push(err.message));
    await page.goto(pathToFileURL(path.join(e.project,'index.html')).href,{waitUntil:'load'});await page.evaluate(()=>document.fonts.ready);
    const result=await page.evaluate(({id,fps,plan,minFontSize,fontFamily})=>{
      const tl=window.__timelines?.[id];if(!tl)return {ok:false,failures:['Missing seekable timeline']};
      const failures=new Set();
      const holdText=new Map();
      if(!document.querySelector('#effect-clip'))failures.add('Missing effect container; regenerate project with shellHTML');
      const elements=[...document.querySelectorAll('body *')].filter(el=>!['STYLE','SCRIPT','META','TITLE','LINK'].includes(el.tagName));
      if(!document.fonts.check(`16px "${fontFamily}"`))failures.add('Required font not loaded');
      const first=Math.ceil(plan.holdStartMs*fps/1000),last=Math.ceil((plan.holdStartMs+plan.holdMs)*fps/1000)-1;
      const samples=first<=last?[...new Set([first,Math.round((first+last)/2),last])]:[];
      if(!samples.length)failures.add('No output frame falls within the reading hold');
      let sampled=0;
      for(const frame of samples){
        sampled++;const ms=frame*1000/fps;tl.seek(ms/1000,false);const hold=ms>=plan.holdStartMs&&ms<plan.holdStartMs+plan.holdMs;
        const styles=new Map(),visibility=new Map();
        const style=el=>{if(!styles.has(el))styles.set(el,getComputedStyle(el));return styles.get(el);};
        const visible=el=>{if(!el)return {opacity:1,hidden:false};if(visibility.has(el))return visibility.get(el);const st=style(el),parent=visible(el.parentElement),v={opacity:parent.opacity*Number(st.opacity),hidden:parent.hidden||st.display==='none'||st.visibility==='hidden'};visibility.set(el,v);return v;};
        for(const el of elements){
          const st=style(el),r=el.getBoundingClientRect(),{opacity,hidden}=visible(el);
          const ownText=[...el.childNodes].some(n=>n.nodeType===Node.TEXT_NODE&&n.textContent.trim());
          if(hold&&ownText&&opacity<.95)failures.add(`Text not fully visible during hold: ${el.id||el.tagName}`);
          if(hidden||opacity<.01||r.width===0||r.height===0)continue;
          if(ownText){
            if(parseFloat(st.fontSize)<minFontSize)failures.add(`Text below minimum font size: ${el.id||el.tagName} = ${st.fontSize}, required >= ${minFontSize}px; adapt text styling instead of lowering readability blindly`);
            if(hold){const last=holdText.get(el);if(last!==undefined&&last!==el.textContent)failures.add(`Text changes during reading hold: ${el.id||el.tagName}`);holdText.set(el,el.textContent);}
          }
          if(el.tagName==='IMG'&&!el.naturalWidth)failures.add('Image failed to load');
        }
        if(failures.size>30)break;
      }
      return {ok:failures.size===0,failures:[...failures],sampleTimesMs:samples.slice(0,sampled).map(frame=>frame*1000/fps),sampledFrames:sampled,mode:'sampled',method:'Three reading-hold samples for optional diagnostics; not continuous-motion verification'};
    },{id:e.id,fps:c.fps,plan:e.plan,minFontSize:c.planInfo.style.minFontSize,fontFamily:c.planInfo.style.fontFamily});
    const rectangle=r=>[r.x,r.y,r.width,r.height];
    const warnings=new Set();
    for(const atMs of result.sampleTimesMs??[]){
      const measured=await measurePage(page,{id:e.id,atMs,layoutRect:rectangle(e.plan.layoutRect),motionBounds:rectangle(e.plan.motionBounds),strictLayout:true});
      result.failures.push(...measured.failures.map(message=>`${atMs.toFixed(1)}ms: ${message}`));
      for(const warning of measured.warnings)warnings.add(warning);
    }
    result.warnings=[...warnings];
    result.ok=result.failures.length===0;
    if(errors.length){result.ok=false;result.failures.push(...errors);}
    return {...result,id:e.id,projectHash:projectHash(e.project),executionHash:executionHash(c)};
  }finally{if(page)await page.close();if(!sharedBrowser)await browser.close();}
}
main(import.meta.url,async()=>{
  const {positionals,values}=parseArgs({allowPositionals:true,options:{browser:{type:'string'}}});assert(positionals.length===2,'Usage: bounds-check.mjs plan.json effect-id --browser <path>');const {config:c,base}=loadConfig(positionals[0]);assert(c.planInfo,'Bounds check requires a complete plan.json');const e=c.effects.find(e=>e.id===positionals[1]);assert(e,'Effect id required');const r=await checkBounds(c,e,{executablePath:values.browser});writeJSON(path.join(base,'previews',`${e.id}-bounds.json`),r);if(!r.ok)process.exitCode=1;return r;
});
