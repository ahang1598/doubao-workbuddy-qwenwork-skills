// Pre-layout measurement at an explicit, fully revealed reading state.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {parseArgs} from 'node:util';
import puppeteer from 'puppeteer-core';
import {loadConfig,assert} from './common.mjs';
import {browserPath} from './browser.mjs';
import {main} from './media-utils.mjs';

export async function measurePage(page,{id,atMs,selector='#card',layoutRect,motionBounds,strictLayout=false}) {
 await page.evaluate(()=>document.fonts.ready);
 return page.evaluate(({id,atMs,selector,layoutRect,motionBounds,strictLayout})=>{
  const tl=window.__timelines?.[id];
  if(!tl)throw new Error('Missing seekable timeline');
  tl.seek(atMs/1000,false);
  const root=document.querySelector('#effect-clip')??document.querySelector('#root');
  if(!root)throw new Error('Missing effect root');
  const fonts=[],overflow=[],warnings=new Set();let union=null,textUnion=null;
  const merge=(a,r)=>({left:Math.min(a?.left??Infinity,r.left),top:Math.min(a?.top??Infinity,r.top),right:Math.max(a?.right??-Infinity,r.right),bottom:Math.max(a?.bottom??-Infinity,r.bottom)});
  const rect=r=>r?({x:r.left,y:r.top,width:r.right-r.left,height:r.bottom-r.top}):null;
  const edgeSources={left:[],top:[],right:[],bottom:[]};
  const selectorFor=el=>{
   const parts=[];
   for(let a=el;a;a=a.parentElement){
    if(a.id){parts.unshift(`#${CSS.escape(a.id)}`);break;}
    parts.unshift(`${a.localName}:nth-child(${Array.prototype.indexOf.call(a.parentElement?.children??[],a)+1})`);
   }
   return parts.join(' > ');
  };
  // Track the same geometry used by readingBounds, including tied edge contributors.
  const include=(r,el,kind)=>{
   let source;
   for(const side of Object.keys(edgeSources)){
    const extendsEdge=!union||(['left','top'].includes(side)?r[side]<union[side]:r[side]>union[side]);
    if(extendsEdge||r[side]===union?.[side]){
     source??={element:el.id||el.className?.baseVal||el.className||el.tagName,selector:selectorFor(el),kind,bounds:rect(r)};
     if(extendsEdge)edgeSources[side]=[];
     edgeSources[side].push(source);
    }
   }
   union=merge(union,r);
  };
  const contains=(a,b)=>b.left>=a.left-1&&b.top>=a.top-1&&b.right<=a.right+1&&b.bottom<=a.bottom+1;
  const visible=el=>{let alpha=1;for(let a=el;a;a=a.parentElement){const s=getComputedStyle(a);if(s.display==='none'||s.visibility==='hidden')return 0;alpha*=Number(s.opacity);}return alpha;};
  const painted=s=>!['transparent','rgba(0, 0, 0, 0)'].includes(s.backgroundColor)||s.backgroundImage!=='none'||['Top','Bottom','Left','Right'].some(k=>parseFloat(s[`border${k}Width`])>0);
  const transformed=(box,m)=>{
   const points=[[box.x,box.y],[box.x+box.width,box.y],[box.x,box.y+box.height],[box.x+box.width,box.y+box.height]].map(([x,y])=>new DOMPoint(x,y).matrixTransform(m));
   return {left:Math.min(...points.map(p=>p.x)),top:Math.min(...points.map(p=>p.y)),right:Math.max(...points.map(p=>p.x)),bottom:Math.max(...points.map(p=>p.y))};
  };
  for(const el of root.querySelectorAll('*')){
   if(['STYLE','SCRIPT'].includes(el.tagName)||el.closest('defs,clipPath,mask,symbol,marker,pattern'))continue;
   const st=getComputedStyle(el),alpha=visible(el);
   const ownText=[...el.childNodes].filter(n=>n.nodeType===3&&n.textContent.trim());
   const label=el.id||el.className?.baseVal||el.className||el.tagName;
   if(alpha<.01){if(ownText.length)warnings.add(`Hidden text at reading time: ${label}; choose a fully revealed time or confirm intentional hiding`);continue;}
   const r=el.getBoundingClientRect();
   if(painted(st))include(r,el,'element');
   if(el instanceof SVGGraphicsElement&&!['svg','g','a','switch'].includes(el.localName)){
    const hasFill=st.fill!=='none'&&Number(st.fillOpacity)>0;
    const hasStroke=st.stroke!=='none'&&Number(st.strokeOpacity)>0&&parseFloat(st.strokeWidth)>0;
    if(hasFill||hasStroke||['use','image'].includes(el.localName)){
     const b=el.getBBox(),m=el.getScreenCTM();
     // Include stroke joins conservatively; filters/markers remain author-reserved decoration.
     const pad=hasStroke?parseFloat(st.strokeWidth)/2*(st.strokeLinejoin==='miter'?Math.max(1,parseFloat(st.strokeMiterlimit)||4):1):0;
     if(m&&(b.width>0||b.height>0))include(transformed({x:b.x-pad,y:b.y-pad,width:b.width+2*pad,height:b.height+2*pad},m),el,'svg');
    }
   }
   if(['img','canvas'].includes(el.localName)){
    // Raster alpha is not inferred from the full element box. Author declares local CSS-pixel bounds.
    let b;try{b=JSON.parse(el.getAttribute('data-content-bounds'));}catch{}
    const w=el.offsetWidth,h=el.offsetHeight;
    if(!Array.isArray(b)||b.length!==4||!b.every(Number.isFinite)||b[0]<0||b[1]<0||b[2]<=0||b[3]<=0||b[0]+b[2]>w||b[1]+b[3]>h){
     overflow.push(`Declare data-content-bounds="[x,y,width,height]" in local CSS pixels: ${label}`);
    }else{
     let m=new DOMMatrix(),supported=true;
     for(let a=el;a;a=a.parentElement){const cs=getComputedStyle(a);const t=new DOMMatrix(cs.transform==='none'?undefined:cs.transform);if(!t.is2D||cs.perspective!=='none'||cs.rotate!=='none'||cs.scale!=='none'){supported=false;break;}m=t.scale(Number.parseFloat(cs.zoom)||1).multiply(m);}
     if(!supported)overflow.push(`Use 2D transform on raster bounds: ${label}`);
     else{const outer=transformed({x:0,y:0,width:w,height:h},m),inner=transformed({x:b[0],y:b[1],width:b[2],height:b[3]},m);include({left:inner.left+r.left-outer.left,top:inner.top+r.top-outer.top,right:inner.right+r.left-outer.left,bottom:inner.bottom+r.top-outer.top},el,'raster');}
     warnings.add('Raster content bounds are author-declared, not alpha-pixel verified');
    }
   }
   if(ownText.length){
    let tr=null;
    for(const node of ownText){const range=document.createRange();range.selectNodeContents(node);for(const box of range.getClientRects())tr=merge(tr,box);}
    if(tr){
     include(tr,el,'text');textUnion=merge(textUnion,tr);
     fonts.push({element:label,fontSize:parseFloat(st.fontSize),lineHeight:st.lineHeight,text:ownText.map(n=>n.textContent).join('')});
     if(alpha<.99)warnings.add(`Text not fully opaque: ${label}`);
     if(!el.closest('[data-text-container]')&&(tr.left<r.left-1||tr.right>r.right+1))overflow.push(`Text exceeds its element width: ${label}`);
     for(let a=el;a&&a!==document.body;a=a.parentElement){
      const cs=getComputedStyle(a),ar=a.getBoundingClientRect();
      if((['hidden','clip','scroll','auto'].includes(cs.overflowX)&&(tr.left<ar.left-1||tr.right>ar.right+1))||(['hidden','clip','scroll','auto'].includes(cs.overflowY)&&(tr.top<ar.top-1||tr.bottom>ar.bottom+1)))overflow.push(`Text clipped by ${a.id||a.tagName}: ${label}`);
      if(a!==root&&cs.clipPath!=='none')warnings.add(`Local clip-path on ${a.id||a.tagName}; confirm intentional masking`);
     }
    }
   }
   if(st.boxShadow!=='none'||st.textShadow!=='none'||st.filter!=='none')warnings.add('Reserve additional space for shadows/filters; DOM bounds exclude their painted extent');
  }
  const panel=document.querySelector(selector),container=panel?rect(panel.getBoundingClientRect()):null;
  const motion=motionBounds?{left:motionBounds[0],top:motionBounds[1],right:motionBounds[0]+motionBounds[2],bottom:motionBounds[1]+motionBounds[3]}:null;
  const expected=layoutRect?{left:layoutRect[0],top:layoutRect[1],right:layoutRect[0]+layoutRect[2],bottom:layoutRect[1]+layoutRect[3]}:null;
  let clipMatchesPlan=null;
  if(document.querySelector('#effect-stage')){
   clipMatchesPlan=getComputedStyle(root).clipPath==='none';
  }else if(motion){
   const expectedClip=document.createElement('div');
   expectedClip.style.clipPath=`inset(${motion.top}px ${document.documentElement.clientWidth-motion.right}px ${document.documentElement.clientHeight-motion.bottom}px ${motion.left}px)`;
   document.body.append(expectedClip);clipMatchesPlan=getComputedStyle(root).clipPath===getComputedStyle(expectedClip).clipPath;expectedClip.remove();
  }
  const fitsMotionBounds=motion&&union?contains(motion,union):null, fitsLayout=expected&&union?contains(expected,union):null;
  const diagnose=b=>b&&union?{bounds:rect(b),excessPx:{left:Math.max(0,b.left-union.left),top:Math.max(0,b.top-union.top),right:Math.max(0,union.right-b.right),bottom:Math.max(0,union.bottom-b.bottom)}}:null;
  const boundsDiagnostics={tolerancePx:1,layoutRect:diagnose(expected),motionBounds:diagnose(motion),edgeSources};
  // Check explicitly marked text backplates in local, unrotated CSS pixels.
  const cardDiagnostics=[];
  for(const card of root.querySelectorAll('[data-text-container]')){
   if(visible(card)<.01)continue;
   const ancestors=[];
   for(let a=card;a;a=a.parentElement){
    const cs=getComputedStyle(a);
    if(cs.transform!=='none'||['rotate','scale','translate'].some(k=>cs[k]!=='none')||(parseFloat(cs.zoom)||1)!==1)ancestors.push({el:a,style:a.getAttribute('style'),transform:cs.transform});
   }
   try{
    for(const {el,transform} of ancestors){
     el.style.setProperty('transition','none','important');
     el.style.setProperty('transform',transform==='none'?'none':'matrix(1,0,0,1,0,0)','important');
     for(const property of ['rotate','scale','translate'])el.style.setProperty(property,'none','important');
     el.style.setProperty('zoom','1','important');
    }
    const cs=getComputedStyle(card),box=card.getBoundingClientRect();
    const inset=side=>(parseFloat(cs[`border${side}Width`])||0)+(parseFloat(cs[`padding${side}`])||0);
    const content={left:box.left+inset('Left'),top:box.top+inset('Top'),right:box.right-inset('Right'),bottom:box.bottom-inset('Bottom')};
    let text=null;
    const walker=document.createTreeWalker(card,NodeFilter.SHOW_TEXT);
    for(let node=walker.nextNode();node;node=walker.nextNode()){
     const el=node.parentElement;
     if(!node.textContent.trim()||el.closest('script,style,defs,clipPath,mask,symbol')||visible(el)<.01)continue;
     const range=document.createRange();range.selectNodeContents(node);
     const elementBox=el.getBoundingClientRect();
     for(const r of range.getClientRects())if(r.width>0&&r.height>0){
      text=merge(text,r);
      if(r.left<elementBox.left-1||r.right>elementBox.right+1)overflow.push(`Text exceeds its element width: ${selectorFor(el)}`);
     }
    }
    const excessPx=text?{left:Math.max(0,content.left-text.left),top:Math.max(0,content.top-text.top),right:Math.max(0,text.right-content.right),bottom:Math.max(0,text.bottom-content.bottom)}:null;
    const fits=text?contains(content,text):null;
    const inner={left:box.left+(parseFloat(cs.borderLeftWidth)||0),top:box.top+(parseFloat(cs.borderTopWidth)||0),right:box.right-(parseFloat(cs.borderRightWidth)||0),bottom:box.bottom-(parseFloat(cs.borderBottomWidth)||0)};
    const fitsCard=text?contains(inner,text):null;
    const local=r=>r?{x:r.left-box.left,y:r.top-box.top,width:r.right-r.left,height:r.bottom-r.top}:null;
    const cardSelector=selectorFor(card);
    cardDiagnostics.push({selector:cardSelector,contentBounds:local(content),textBounds:local(text),excessPx,fits,cardInnerBounds:local(inner),fitsCard,tolerancePx:1});
    if(fitsCard===false)overflow.push(`Text exceeds card inner bounds: ${cardSelector}`);
    else if(fits===false)warnings.add(`Text range enters card padding: ${cardSelector}; font metrics are not glyph pixels. Check visual spacing; do not enlarge line-height solely to clear this warning.`);
   }finally{
    for(const {el,style} of ancestors){if(style===null){el.style.cssText='';el.removeAttribute('style');}else el.setAttribute('style',style);}
   }
  }
  const failures=[...new Set(overflow)];
  if(!union||union.right<=union.left||union.bottom<=union.top)failures.push('No visible content at reading time');
  const suggestedLayoutRect=union?[Math.floor(union.left),Math.floor(union.top),Math.ceil(union.right)-Math.floor(union.left),Math.ceil(union.bottom)-Math.floor(union.top)]:null;
  const fitsCanvas=union?contains({left:0,top:0,right:document.documentElement.clientWidth,bottom:document.documentElement.clientHeight},union):null;
  if(fitsCanvas===false)failures.push('Reading content exceeds video canvas; move or reflow content');
  if(fitsLayout===false){
   if(strictLayout)failures.push('Reading content exceeds layoutRect; synchronize planned bounds or fix layout');
   else warnings.add('layoutRect needs synchronization: use suggestedLayoutRect if motionBounds and placement constraints permit. Preserve content screen coordinates; remeasure if wrapping, size or position changes.');
  }
  if(fitsMotionBounds===false)failures.push('Reading content exceeds motionBounds; check stage position and local coordinates');
  if(clipMatchesPlan===false)failures.push('Unexpected outer clipping; regenerate the shell (custom effects require a full-canvas unclipped layer)');
  return {ok:failures.length===0,needsLayoutSync:fitsLayout===false,suggestedLayoutRect,fitsCanvas,failures,sampledStates:1,atMs,container,clipMatchesPlan,fitsMotionBounds,readingBounds:rect(union),textBounds:rect(textUnion),fitsLayout,boundsDiagnostics,cardDiagnostics,fonts,overflow:[...new Set(overflow)],warnings:[...warnings]};
 },{id,atMs,selector,layoutRect,motionBounds,strictLayout});
}

main(import.meta.url,async()=>{
 const {positionals:p,values:v}=parseArgs({allowPositionals:true,options:{browser:{type:'string'},effect:{type:'string'},'at-ms':{type:'string'}}});
 assert(p.length===1,'Usage: measure.mjs plan.json --effect id --browser <path> [--at-ms milliseconds]');
 const {config:c}=loadConfig(p[0],{skipPlan:true});
 const e=c.effects.find(e=>e.id===v.effect);assert(e,'Select an effect with --effect');
 const executablePath=browserPath(v.browser);
 const atMs=v['at-ms']!==undefined?Number(v['at-ms']):Array.isArray(e.hold)?e.hold[0]+e.hold[1]/2:NaN;
 assert(Number.isFinite(atMs)&&atMs>=0&&atMs<e.durationMs,'Provide --at-ms at a fully revealed reading state, or a valid effect hold');
 const project=fs.existsSync(path.join(e.project,'index.html'))?e.project:e.source;
 assert(project&&fs.existsSync(path.join(project,'index.html')),'Author the custom project before measuring');
 let browser;
 try{
  assert(!fs.readFileSync(path.join(project,'index.html'),'utf8').includes('AUTHOR_CUSTOM_EFFECT'),'Author custom effect before measuring');
  browser=await puppeteer.launch({executablePath,headless:true,args:['--disable-gpu','--allow-file-access-from-files']});
  const page=await browser.newPage();await page.setViewport({width:c.videoInfo.width,height:c.videoInfo.height,deviceScaleFactor:1});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto(pathToFileURL(path.join(project,'index.html')).href,{waitUntil:'load'});
  const result=await measurePage(page,{id:e.id,atMs,layoutRect:e.layoutRect,motionBounds:e.motionBounds});
  assert(!errors.length,errors.join('; '));
  if(!result.ok)process.exitCode=1;
  return {id:e.id,source:'project',...result,note:'Reading-state geometry only, not motion bounds. Include entry/exit extrema, rotation, scale, decorations and shadows when planning motionBounds. Project coordinates remain unchanged.'};
 }finally{if(browser)await browser.close();}
});
