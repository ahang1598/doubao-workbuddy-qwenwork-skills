#!/usr/bin/env node
'use strict';
// Read-only HTML QA. Requires Node.js and Playwright with an installed Chromium.
const fs = require('node:fs');
const path = require('node:path');
const {createHash} = require('node:crypto');
const sha256 = data => createHash('sha256').update(data).digest('hex');


function parseArgs(argv) {
  const a = {timeout: 15000, tolerance: 1, root: 'body > main', allowInteraction: false, longPage: false};
  const names = {'--html':'html','--font-contract':'fontContract','--out':'out','--screenshots':'screenshots','--root':'root','--browser':'browser','--timeout':'timeout','--tolerance':'tolerance','--expected-width':'expectedWidth','--expected-height':'expectedHeight'};
  for (let i=0;i<argv.length;i++) {
    const key=argv[i];
    if (key==='--allow-interaction') a.allowInteraction=true;
    else if (key==='--long-page') a.longPage=true;
    else if (key==='--help') a.help=true;
    else if (names[key] && argv[i+1] && !argv[i+1].startsWith('--')) a[names[key]]=argv[++i];
    else throw new Error(`Unknown option or missing value: ${key}`);
  }
  if (a.help) return a;
  if (!a.html || !a.out) throw new Error('--html and --out are required');
  a.timeout=Number(a.timeout); a.tolerance=Number(a.tolerance);
  if (!Number.isFinite(a.timeout)||a.timeout<=0||!Number.isFinite(a.tolerance)||a.tolerance<0) throw new Error('Invalid timeout/tolerance');
  validateExpectedCanvas(a);
  for (const key of ['html','out','fontContract','screenshots','browser']) if(a[key]) a[key]=path.resolve(a[key]);
  if (a.out===a.html || a.out===a.fontContract || fs.existsSync(a.out)) throw new Error('Report must use a new path, distinct from inputs');
  if (a.screenshots && fs.existsSync(a.screenshots)) throw new Error('Screenshot directory must be new');
  return a;
}

function validateExpectedCanvas(a) {
  const keys=['expectedWidth','expectedHeight'];
  if(keys.every(k=>a[k]===undefined))return;
  for(const key of keys) {
    a[key]=Number(a[key]);
    if(!Number.isSafeInteger(a[key])||a[key]<=0)throw new Error('Expected width and height must both be positive integers from the frozen Brief');
  }
}

function readFontContract(filename) {
  if(!filename)return null;
  const contract=JSON.parse(fs.readFileSync(filename,'utf8'));
  const families=contract?.families;
  if(!families||typeof families!=='object'||Array.isArray(families)||!Object.keys(families).length)throw new Error('FONT_CONTRACT: nonempty families object required');
  for(const [family,entry] of Object.entries(families)) {
    if(!family.trim()||!entry||entry.source!=='target_environment'||entry.availability!=='verified')throw new Error(`FONT_CONTRACT: ${family} requires source=target_environment and availability=verified`);
  }
  return families;
}

async function inspectPage(page, a) {
  return page.evaluate(async ({rootSelector,tol,longPage,allowInteraction,timeout})=>{
    const errors=[], warnings=[], elements=[], sections=[], surfaces=[];
    const err=(code,detail)=>errors.push({code,detail});
    const warn=(code,detail)=>warnings.push({code,detail});
    const roots=[...document.querySelectorAll(rootSelector)];
    const root=roots[0];
    if(roots.length!==1) err('CANVAS_ROOT_COUNT',String(roots.length));
    const number=(v)=>Number.parseFloat(v);
    const near=(a,b)=>Number.isFinite(a)&&Math.abs(a-b)<=tol;
    const label=(e)=>e.id||e.getAttribute('data-layer-id')||e.tagName.toLowerCase();
    const box=(r)=>({x:r.x,y:r.y,width:r.width,height:r.height});
    const all=[...document.querySelectorAll('*')];
    const w=document.documentElement.getAttribute('data-canvas-width');
    const h=document.documentElement.getAttribute('data-canvas-height');
    if(!/^[1-9]\d*$/.test(w||'')||!/^[1-9]\d*$/.test(h||'')) err('CANVAS_ATTRIBUTES','Positive integer width/height required');
    const width=Number(w),height=Number(h);
    if(document.doctype?.name!=='html') err('DOCTYPE','HTML doctype required');
    if(!document.querySelector('meta[charset="UTF-8" i]')) err('CHARSET','UTF-8 declaration required');
    for(const e of [document.documentElement,document.body,root].filter(Boolean)) {
      const r=e.getBoundingClientRect(), css=getComputedStyle(e);
      if(!near(r.width,width)||!near(r.height,height)) err('CANVAS_SIZE',`${label(e)}: ${r.width}x${r.height}`);
      if(!/^\d+(?:\.\d+)?px$/.test(e.style.width)||!/^\d+(?:\.\d+)?px$/.test(e.style.height)||!near(number(e.style.width),width)||!near(number(e.style.height),height)) err('INLINE_CANVAS_SIZE',label(e));
      if(css.transform!=='none'||!['1','normal'].includes(css.zoom)) err('CANVAS_TRANSFORM',label(e));
      if(['hidden','clip'].includes(css.overflowX)||['hidden','clip'].includes(css.overflowY)||css.clipPath!=='none'||css.clip!=='auto'||/\b(paint|strict|content)\b/.test(css.contain))err('CANVAS_ROOT_CLIPPING',label(e));
    }
    for(const e of all) {
      const s=e.getAttribute('style')||'';
      if(/(?:backdrop-filter|filter|mix-blend-mode)/i.test(s)) {const cs=getComputedStyle(e);surfaces.push({element:label(e),filter:cs.filter,backdrop_filter:cs.backdropFilter,mix_blend_mode:cs.mixBlendMode,opacity:cs.opacity});}
      if(/@import|@font-face|@media|@keyframes/i.test(s)) err('STYLE_RULE',label(e));
      if(/(?:\d|\.)(?:[sld]?v[whib]|vmin|vmax)\b/i.test(s)) err('VIEWPORT_UNIT',label(e));
      if(!allowInteraction && (e.tagName==='SCRIPT' && !['application/ld+json','application/json'].includes(e.type) || [...e.attributes].some(x=>/^on/i.test(x.name)))) err('SCRIPT_REQUIRES_AUTHORIZATION',label(e));
      if(e.tagName==='IFRAME') warn('EMBEDDED_DOCUMENT_UNCHECKED',label(e));
    }
    const seen=new Set();
    for(const e of all.filter(e=>e.id)) {if(seen.has(e.id))err('DUPLICATE_DOM_ID',e.id);seen.add(e.id);}
    const urls=new Set(),images=[];
    for(const e of all) {
      const css=getComputedStyle(e);
      for(const value of [css.backgroundImage,css.maskImage,css.borderImageSource]) {
        for(const m of value.matchAll(/url\(["']?(.*?)["']?\)/g)) if(m[1]&&!m[1].startsWith('#')) urls.add(m[1]);
      }
      if(e.tagName==='IMG') {
        images.push({element:label(e),url:e.currentSrc||e.src,width:e.naturalWidth,height:e.naturalHeight});
        if(!e.complete||!e.naturalWidth) err('IMAGE_NOT_LOADED',label(e));
      }
      if(e instanceof SVGImageElement) {const u=e.href.baseVal;if(u&&!u.startsWith('#'))urls.add(new URL(u,document.baseURI).href);}
    }
    await Promise.all([...urls].map(url=>new Promise(resolve=>{
      const im=new Image();let finished=false;
      const done=(ok)=>{if(finished)return;finished=true;clearTimeout(timer);if(!ok)err('CSS_OR_SVG_IMAGE_NOT_LOADED',url);resolve();};
      const timer=setTimeout(()=>done(false),timeout);
      im.onload=()=>done(true);im.onerror=()=>done(false);im.src=url;
    })));
    const origin=root?.getBoundingClientRect();
    if(root) {
      for(const e of root.querySelectorAll('img,svg,section,article,div,[data-layer-id]')) {
        const r=e.getBoundingClientRect(),s=getComputedStyle(e);
        if(s.display==='none'||s.visibility==='hidden'||!r.width||!r.height)continue;
        // Local decorative crops are permitted, but never at the canvas roots or for text.
        const decorative=e.closest('[aria-hidden="true"]');
        const localDecoration=decorative&&decorative!==root&&root.contains(decorative);
        if(localDecoration)continue;
        const image=e.tagName==='IMG';
        const visible={left:r.left,right:r.right,top:r.top,bottom:r.bottom};
        for(let p=e.parentElement;p&&root.contains(p);p=p.parentElement) {
          const css=getComputedStyle(p),b=p.getBoundingClientRect();
          const clipX=['hidden','clip','scroll','auto'].includes(css.overflowX);
          const clipY=['hidden','clip','scroll','auto'].includes(css.overflowY);
          if(image&&p!==root) {
            if(clipX){visible.left=Math.max(visible.left,b.left);visible.right=Math.min(visible.right,b.right);}
            if(clipY){visible.top=Math.max(visible.top,b.top);visible.bottom=Math.min(visible.bottom,b.bottom);}
          } else {
            const checked=image?visible:r;
            if(checked.right>checked.left&&checked.bottom>checked.top&&((clipX&&(checked.left<b.left-tol||checked.right>b.right+tol))||(clipY&&(checked.top<b.top-tol||checked.bottom>b.bottom+tol))))err('ELEMENT_CLIPPED',label(e));
          }
        }
        if(visible.right>visible.left&&visible.bottom>visible.top&&(visible.left<origin.left-tol||visible.right>origin.right+tol||visible.top<origin.top-tol||visible.bottom>origin.bottom+tol))err('ELEMENT_OUTSIDE_CANVAS',label(e));
      }
      const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
      const textIssues=new Set();
      const issue=(code,e)=>{const key=code+label(e);if(!textIssues.has(key)){textIssues.add(key);err(code,label(e));}};
      while(walker.nextNode()) {
        const n=walker.currentNode,e=n.parentElement;
        if(!n.textContent.trim()||!e||e.closest('script,style,template'))continue;
        let hidden=false;
        for(let p=e;p && root.contains(p);p=p.parentElement) {
          const s=getComputedStyle(p);
          if(s.display==='none'||s.visibility==='hidden'||number(s.opacity)===0){hidden=true;break;}
        }
        if(hidden){issue('HIDDEN_TEXT',e);continue;}
        const range=document.createRange();range.selectNodeContents(n);
        for(const r of range.getClientRects()) {
          if(r.width===0||r.height===0)continue;
          if(r.left<origin.left-tol||r.right>origin.right+tol||r.top<origin.top-tol||r.bottom>origin.bottom+tol)issue('TEXT_OUTSIDE_CANVAS',e);
          for(let p=e;p&&root.contains(p);p=p.parentElement) {
            const s=getComputedStyle(p),b=p.getBoundingClientRect();
            if(s.clipPath!=='none') {
              const match=s.clipPath.match(/^inset\(([^()]*)\)$/);
              const tokens=match?match[1].trim().split(/\s+/):[];
              let transformed=false;
              for(let q=p;q&&root.contains(q);q=q.parentElement) {
                const qs=getComputedStyle(q);
                if(qs.transform!=='none'||!['1','normal'].includes(qs.zoom)||[qs.translate,qs.rotate,qs.scale].some(v=>v&&v!=='none')){transformed=true;break;}
              }
              if(!transformed&&tokens.length>=1&&tokens.length<=4&&tokens.every(v=>/^-?(?:\d*\.)?\d+(?:px|%)?$/.test(v))) {
                const [t,x=t,u=t,v=x]=tokens;
                const px=(value,size)=>parseFloat(value)*(value.endsWith('%')?size/100:1);
                const clip={top:b.top+px(t,b.height),right:b.right-px(x,b.width),bottom:b.bottom-px(u,b.height),left:b.left+px(v,b.width)};
                if(r.left<clip.left-tol||r.right>clip.right+tol||r.top<clip.top-tol||r.bottom>clip.bottom+tol)issue('TEXT_CLIPPED',p);
              } else issue('TEXT_CLIP_UNVERIFIED',p);
            }
            if(s.clip!=='auto')issue('TEXT_CLIP_UNVERIFIED',p);
            if(s.display==='inline')continue;
            // Range boxes expose line overflow; clipping is checked against every ancestor.
            const paint=/(?:paint|strict|content)/.test(s.contain),clipX=paint||['hidden','clip','scroll','auto'].includes(s.overflowX),clipY=paint||['hidden','clip','scroll','auto'].includes(s.overflowY);
            if((clipX&&(r.left<b.left-tol||r.right>b.right+tol))||(clipY&&(r.top<b.top-tol||r.bottom>b.bottom+tol)))issue('TEXT_CLIPPED',p);
            if(p===e && (r.left<b.left-tol||r.right>b.right+tol||r.top<b.top-tol||r.bottom>b.bottom+tol))issue('TEXT_BOX_OVERFLOW',e);
          }
        }
      }
    }
    if(root) {
      const mapped=[...root.querySelectorAll('*')];
      const mappedIds=new Set();
      for(const [index,e] of mapped.entries()) {
        if(e.closest('script,style,template'))continue;
        const elementId=e.id||e.getAttribute('data-layer-id')||'dom:'+index;
        if(!elementId||mappedIds.has(elementId))continue;
        mappedIds.add(elementId);
        const r=e.getBoundingClientRect(),css=getComputedStyle(e);
        elements.push({element_id:elementId,box:{x:r.x-origin.x,y:r.y-origin.y,width:r.width,height:r.height},z_index:css.zIndex,font_size:number(css.fontSize),font_family:css.fontFamily,text:e.textContent.trim()});
      }
      const sectionNodes=[...root.querySelectorAll('[data-section-id]')].filter(e=>!e.parentElement?.closest('[data-section-id]'));
      if(longPage&&!sectionNodes.length)err('LONG_PAGE_SECTIONS_REQUIRED','Add ordered top-level data-section-id markers');
      let expectedY=0;
      const sectionIds=new Set();
      for(const e of sectionNodes) {
        const sectionId=e.getAttribute('data-section-id'),r=e.getBoundingClientRect();
        const actual={x:r.x-origin.x,y:r.y-origin.y,width:r.width,height:r.height};
        if(!sectionId||sectionIds.has(sectionId))err('LONG_PAGE_SECTION_ID',sectionId||'(empty)');
        sectionIds.add(sectionId);
        const css=getComputedStyle(e);
        if(e.closest('[aria-hidden="true"]')||css.display==='none'||css.visibility==='hidden'||(!e.textContent.trim()&&!e.querySelector('img,svg,video,canvas')))
          err('LONG_PAGE_SECTION_CONTENT',sectionId);
        if(!near(actual.x,0)||!near(actual.width,width))err('LONG_PAGE_SECTION_WIDTH',sectionId);
        if(!near(actual.y,expectedY))err('LONG_PAGE_SECTION_GAP_OR_OVERLAP',sectionId);
        if(actual.height<=0)err('LONG_PAGE_SECTION_HEIGHT',sectionId);
        expectedY=actual.y+actual.height;
        sections.push({section_id:sectionId,box:actual});
      }
      if(sectionNodes.length&&expectedY>height+tol)err('LONG_PAGE_SECTION_SUM',`${expectedY} > ${height}`);
      if(longPage&&sectionNodes.length) {
        const belongs=e=>sectionNodes.some(section=>section===e||section.contains(e));
        const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
        while(walker.nextNode()) {
          const n=walker.currentNode,e=n.parentElement;
          if(n.textContent.trim()&&!e.closest('script,style,template')&&!belongs(e))err('LONG_PAGE_UNMAPPED_CONTENT',label(e));
        }
        for(const e of root.querySelectorAll('img,svg,video,canvas')) {
          if(!e.closest('[aria-hidden="true"]')&&!belongs(e))err('LONG_PAGE_UNMAPPED_CONTENT',label(e));
        }
      }
    }
    return {errors,warnings,canvas:{width,height,box:origin?box(origin):null},elements,sections,images,surfaces};
  },{rootSelector:a.root,tol:a.tolerance,longPage:a.longPage,allowInteraction:a.allowInteraction,timeout:a.timeout});
}

async function actualFonts(page, rootSelector) {
  const session=await page.context().newCDPSession(page);
  try {
    await session.send('DOM.enable');await session.send('CSS.enable');
    const {root}=await session.send('DOM.getDocument',{depth:-1});
    const {nodeIds}=await session.send('DOM.querySelectorAll',{nodeId:root.nodeId,selector:`${rootSelector}, ${rootSelector} *`});
    const fonts=[];
    for(const nodeId of nodeIds) {
      const {node}=await session.send('DOM.describeNode',{nodeId,depth:1});
      if((node.children||[]).some(n=>n.nodeType===3&&n.nodeValue.trim())) {
        const {fonts:used}=await session.send('CSS.getPlatformFontsForNode',{nodeId});
        const {computedStyle}=await session.send('CSS.getComputedStyleForNode',{nodeId});
        const stack=computedStyle.find(s=>s.name==='font-family')?.value||'';
        const attrs={};for(let i=0;i<(node.attributes||[]).length;i+=2)attrs[node.attributes[i]]=node.attributes[i+1];
        fonts.push({nodeId,element:attrs.id||attrs['data-layer-id']||node.localName,font_family:stack,fonts:used});
      }
    }
    return fonts;
  } finally {await session.detach();}
}

async function routeLocalSource(page, filename, allowInteraction) {
  // No listening server: fulfill only this browser's synthetic-origin requests.
  const directory=fs.realpathSync(path.dirname(filename));
  const mime={'.html':'text/html; charset=utf-8','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.svg':'image/svg+xml','.webp':'image/webp','.gif':'image/gif','.woff':'font/woff','.woff2':'font/woff2','.ttf':'font/ttf','.js':'text/javascript','.json':'application/json','.css':'text/css'};
  await page.route('https://html-check.invalid/**',async route=>{
    const request=route.request();
    if(!['GET','HEAD'].includes(request.method())){await route.fulfill({status:405,body:''});return;}
    try {
      const requestPath=decodeURIComponent(new URL(request.url()).pathname);
      const file=fs.realpathSync(path.resolve(directory,'.'+requestPath));
      if(!file.startsWith(directory+path.sep)||!fs.statSync(file).isFile())throw new Error('Out of scope');
      if(request.isNavigationRequest()&&file!==fs.realpathSync(filename))throw new Error('Only the input document may navigate');
      await route.fulfill({status:200,headers:!allowInteraction && request.isNavigationRequest()?{'Content-Security-Policy':"script-src 'none'"}:{},contentType:mime[path.extname(file).toLowerCase()]||'application/octet-stream',body:request.method()==='HEAD'?'':fs.readFileSync(file)});
    }catch {await route.fulfill({status:404,body:''});}
  });
  return `https://html-check.invalid/${encodeURIComponent(path.basename(filename))}`;
}

async function verify(a) {
  validateExpectedCanvas(a);
  const source=fs.readFileSync(a.html,'utf8');
  const fontContract=readFontContract(a.fontContract);
  const report={status:'error',scope:'Browser structural and actual DOM geometry checks; visual review and platform delivery are separate',html:a.html,errors:[],warnings:[],views:[],unverified:['visual quality, subject identity, optical alignment, alpha edges','hosted platform fonts/effects, upload and Item readback']};
  report.source_sha256=sha256(source);
  report.expected_canvas=a.expectedWidth===undefined?null:{width:a.expectedWidth,height:a.expectedHeight};
  report.font_validation={status:'unverified',scope:'Local browser exact family only; not target-platform verification'};
  if(!fontContract)report.unverified.push('Target font matching: no font-contract provided; actualFonts are diagnostic only');
  const {chromium}=require('playwright');
  const browser=await chromium.launch({headless:true,...(a.browser?{executablePath:a.browser}:{})});
  try {
    const context=await browser.newContext({javaScriptEnabled:true,deviceScaleFactor:1});
    const page=await context.newPage();
    page.setDefaultTimeout(a.timeout);
    const sourceURL=await routeLocalSource(page,a.html,a.allowInteraction);
    const failures=[];
    page.on('requestfailed',req=>failures.push({url:req.url(),error:req.failure()?.errorText}));
    page.on('response',res=>{if(res.status()>=400)failures.push({url:res.url(),status:res.status()});});
    if(!/<\/html\s*>/i.test(source)||!/<\/body\s*>/i.test(source)||!/<head[\s>]/i.test(source))report.errors.push({code:'INCOMPLETE_SOURCE',detail:'Explicit document, head, body and closing tags required'});
    if(a.screenshots)fs.mkdirSync(a.screenshots,{recursive:true});
    for(const width of [360,1440]) {
      await page.setViewportSize({width,height:900});
      await page.goto(sourceURL,{waitUntil:'load',timeout:a.timeout});
      await page.evaluate(async timeout=>{await Promise.race([document.fonts.ready,new Promise((_,reject)=>setTimeout(()=>reject(new Error('Font loading timed out')),timeout))]);},a.timeout);
      const view=await inspectPage(page,a);view.viewport={width,height:900};
      if(report.expected_canvas&&(view.canvas.width!==a.expectedWidth||view.canvas.height!==a.expectedHeight))view.errors.push({code:'BRIEF_CANVAS_MISMATCH',detail:{expected:report.expected_canvas,declared:{width:view.canvas.width,height:view.canvas.height}}});
      view.font_validation={status:'unverified'};
      try {
        view.actualFonts=await actualFonts(page,a.root);
        if(fontContract) {
          for(const item of view.actualFonts) {
            const stack=item.font_family.split(',').map(v=>v.trim().replace(/^(['"])(.*)\1$/,'$2'));
            const family=stack[0],used=item.fonts.filter(f=>f.glyphCount>0);
            if(!Object.hasOwn(fontContract,family)||stack.length<2)view.errors.push({code:'FONT_CONTRACT_MISMATCH',detail:item.element});
            if(!used.length)view.errors.push({code:'ACTUAL_FONTS_UNVERIFIED',detail:item.element});
            else if(used.some(f=>f.familyName!==family))view.errors.push({code:'FONT_FAMILY_MISMATCH',detail:{element:item.element,expected:family,actual:used.map(f=>f.familyName)}});
          }
          view.font_validation.status=view.actualFonts.length&&!view.errors.some(e=>/FONT/.test(e.code))?'pass':'fail';
        } else view.warnings.push({code:'FONT_CONTRACT_MISSING',detail:'Actual font names are diagnostic, not verified targets'});
      }catch(e){
        view.warnings.push({code:'ACTUAL_FONTS_UNVERIFIED',detail:e.message});
        report.unverified.push('Actual font diagnostics failed: '+e.message);
        if(fontContract)view.errors.push({code:'ACTUAL_FONTS_UNVERIFIED',detail:e.message});
      }
      await page.evaluate(()=>window.scrollTo(0,document.documentElement.scrollHeight));
      const after=await page.locator(a.root).first().boundingBox();
      if(after&&view.canvas.box&&(Math.abs(after.width-view.canvas.box.width)>a.tolerance||Math.abs(after.height-view.canvas.box.height)>a.tolerance))view.errors.push({code:'SIZE_CHANGED_AFTER_SCROLL'});
      await page.evaluate(()=>window.scrollTo(0,0));
      if(a.screenshots) {view.screenshot=path.join(a.screenshots,`viewport-${width}.png`);await page.screenshot({path:view.screenshot,fullPage:true,timeout:a.timeout});}
      report.views.push(view);
    }
    for(const fail of failures)report.errors.push({code:'RESOURCE_REQUEST_FAILED',detail:fail});
    if(a.allowInteraction)report.unverified.push('Interaction behavior and delayed script changes beyond sampled states');
    const first=report.views[0],second=report.views[1];
    if(first.canvas.box&&second.canvas.box&&['width','height'].some(k=>Math.abs(first.canvas.box[k]-second.canvas.box[k])>a.tolerance))report.errors.push({code:'VIEWPORT_LAYOUT_DRIFT'});
    for(const item of first.elements) {
      const other=second.elements.find(e=>e.element_id===item.element_id);
      if(!other||['x','y','width','height'].some(k=>Math.abs(item.box[k]-other.box[k])>a.tolerance))report.errors.push({code:'VIEWPORT_ELEMENT_DRIFT',detail:item.element_id});
    }
    if(sha256(fs.readFileSync(a.html))!==report.source_sha256)report.errors.push({code:'SOURCE_CHANGED_DURING_VALIDATION'});
    report.status=report.errors.length||report.views.some(v=>v.errors.length)?'fail':'pass';
    if(fontContract)report.font_validation.status=report.views.some(v=>v.font_validation.status==='fail')?'fail':report.views.every(v=>v.font_validation.status==='pass')?'pass':'unverified';
    return report;
  } finally {await browser.close();}
}

async function main() {
  let a;
  try {
    a=parseArgs(process.argv.slice(2));
    if(a.help){console.log('node scripts/maintenance/verify-html.cjs --html <file> --out <new-report.json> [--long-page] [--expected-width <Brief px> --expected-height <Brief px>] [--font-contract <font-contract.json>] [--screenshots <new-dir>] [--root "body > main"] [--browser <Chromium>] [--allow-interaction] [--timeout 15000] [--tolerance 1]');return;}
    const report=await verify(a);
    fs.mkdirSync(path.dirname(a.out),{recursive:true});fs.writeFileSync(a.out,JSON.stringify(report,null,2)+'\n',{flag:'wx'});
    console.log(JSON.stringify({status:report.status,report:a.out,errors:report.errors.length+report.views.reduce((n,v)=>n+v.errors.length,0)}));
    process.exitCode=report.status==='pass'?0:1;
  } catch(e) {console.error(`HTML_CHECK_NOT_COMPLETED: ${e.message}`);process.exitCode=2;}
}
if(require.main===module)main();
module.exports={verify,parseArgs};
