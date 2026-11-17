#!/usr/bin/env python3
"""Fixed canvas self-check inspired by the supplied shot.py; requires playwright and Pillow."""
import argparse
import io
import json
import os
import sys
from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=128)
def self_contained_svg_uri(url):
 """Accept the inliner's percent-encoded static SVG, never raster/base64 data."""
 import re
 import importlib.util
 import xml.etree.ElementTree as ET
 from urllib.parse import unquote
 match=re.fullmatch(r'data:image/svg\+xml(?:;charset=utf-8)?,(.*)',url,re.I|re.S)
 if not match or not re.search(r'%[0-9a-f]{2}',match[1],re.I) or re.search(r'[\s<>#]|%(?![0-9a-f]{2})',match[1],re.I):return False
 try:
  source=unquote(match[1],encoding='utf-8',errors='strict')
  if re.search(r'<!DOCTYPE|<!ENTITY|<\?xml-stylesheet',source,re.I):return False
  root=ET.fromstring(source);ns='http://www.w3.org/2000/svg'
  if root.tag!='{'+ns+'}svg':return False
  for node in root.iter():
   local=node.tag.rsplit('}',1)[-1]
   if not node.tag.startswith('{'+ns+'}') or local in {'script','foreignObject','set','discard'} or local.startswith('animate'):return False
   for key,value in node.attrib.items():
    name=key.rsplit('}',1)[-1]
    if name.lower().startswith('on') or key=='{http://www.w3.org/XML/1998/namespace}base':return False
    if name in {'href','src'} and not re.fullmatch(r'#[^\s#]+',value):return False
  # Reuse the same CSS dependency parser as the producer, including escaped URLs.
  spec=importlib.util.spec_from_file_location('shot_svg_inliner',Path(__file__).with_name('inline-svg-assets.py'))
  inliner=importlib.util.module_from_spec(spec);spec.loader.exec_module(inliner)
  inliner.validate_css_dependencies(root)
  import tinycss2
  def local_css(tokens,parent=''):
   for token in tokens:
    if token.type=='url' and not token.value.startswith('#'):raise ValueError('Nested data or external SVG CSS resource')
    if token.type=='string' and parent in {'url','image-set','-webkit-image-set'} and not token.value.startswith('#'):raise ValueError('Nonlocal SVG CSS source')
    if token.type=='function':local_css(token.arguments,token.lower_name)
    elif hasattr(token,'content'):local_css(token.content,parent)
  for node in root.iter():
   values=[value for key,value in node.attrib.items() if key.rsplit('}',1)[-1] in inliner.CSS_REFERENCE_ATTRIBUTES]
   if node.tag=='{'+ns+'}style':values.append(node.text or '')
   for value in values:local_css(tinycss2.parse_component_value_list(value))
  return True
 except (ValueError,UnicodeError,ET.ParseError,OSError,ImportError):return False


def chromium_executable(explicit=None):
 """Locate a host Chromium executable without downloading another browser."""
 if explicit:
  candidate=Path(explicit).expanduser()
  if candidate.is_file() and (os.name=='nt' or os.access(candidate,os.X_OK)):return str(candidate)
  raise FileNotFoundError(f'Chromium executable unavailable: {candidate}')
 roots=[Path.home()/'.cache/ms-playwright',Path.home()/'Library/Caches/ms-playwright',Path('/ms-playwright'),Path('/opt/ms-playwright'),Path('/root/.cache/ms-playwright'),Path('/home/user/.cache/ms-playwright')]
 if os.name=='nt':
  local_app_data=os.environ.get('LOCALAPPDATA')
  roots.insert(0,(Path(local_app_data) if local_app_data else Path.home()/'AppData/Local')/'ms-playwright')
 if os.environ.get('PLAYWRIGHT_BROWSERS_PATH'):
  roots.insert(0,Path(os.environ['PLAYWRIGHT_BROWSERS_PATH']).expanduser())
 for root in roots:
  try:
   revisions=sorted([d for d in root.iterdir() if d.is_dir() and d.name.startswith('chromium-')],key=lambda d: d.name,reverse=True)
  except OSError:
   continue
  for revision in revisions:
   for suffix in ('chrome-linux/chrome','chrome-linux64/chrome','chrome-mac/Chromium.app/Contents/MacOS/Chromium','chrome-mac-arm64/Chromium.app/Contents/MacOS/Chromium','chrome-win/chrome.exe'):
    candidate=revision/suffix
    if candidate.is_file() and (os.name=='nt' or os.access(candidate,os.X_OK)):return str(candidate)
 raise FileNotFoundError('未找到 Chromium 可执行文件；通过 PLAYWRIGHT_BROWSERS_PATH 或 --exec-path 指定系统已有安装，不下载其他浏览器。')


def check_runtime(explicit=None):
 """Check the pinned renderer before starting HTML production."""
 from playwright.sync_api import sync_playwright
 from PIL import Image  # noqa: F401 - verify the renderer dependency
 executable=chromium_executable(explicit)
 with sync_playwright() as playwright:
  browser=playwright.chromium.launch(executable_path=executable)
  browser.close()
 return {'status':'ready','chromiumExecutable':executable}

MEASURE = r"""() => {
 const marked=document.querySelectorAll('[data-canvas-root]');
 if(marked.length!==1)throw Error('作品总容器必须有且只有一个 data-canvas-root 标记');
 const root=marked[0];
 if(root===document.body||!document.body.contains(root))throw Error('data-canvas-root 必须标记 body 内的作品总容器');
 const box=e=>{const r=e.getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,bottom:r.bottom+scrollY}};
 const visible=e=>{const s=getComputedStyle(e);return s.display!=='none'&&s.visibility!=='hidden'&&Number(s.opacity)>0&&e.getClientRects().length};
 const roots=[document.documentElement,document.body,root],fixed=roots.map(box),saved=roots.map(e=>e.getAttribute('style'));
 const inlineSizes=roots.map(e=>({width:e.style.width,height:e.style.height}));
 const safes=[...root.querySelectorAll('[data-canvas-bottom-safe-area]')],safe=safes.length===1?safes[0]:null;
 const decoration=e=>e.matches('[data-canvas-decoration="true"][aria-hidden="true"]')
  &&!e.textContent.trim()&&!e.matches('img,svg,canvas,video,table,input,button,a')
  &&!e.querySelector('img,svg,canvas,video,table,input,button,a')
  &&getComputedStyle(e,'::before').content.match(/^(none|normal|""|''|)$/)
  &&getComputedStyle(e,'::after').content.match(/^(none|normal|""|''|)$/);
 function measure(){
  const ownText=e=>[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim());
  const pseudoContent=e=>['::before','::after'].some(p=>!getComputedStyle(e,p).content.match(/^(none|normal|""|''|)$/));
  const r=box(root),leaves=[...root.querySelectorAll('*')].filter(e=>visible(e)
   &&(e!==safe||ownText(e)||pseudoContent(e))
   &&(e.childElementCount===0||ownText(e)||pseudoContent(e)||e.matches('svg,canvas,video,img,table')));
  const ignored=leaves.filter(decoration),content=leaves.filter(e=>!decoration(e));
  const contentBottom=Math.max(r.y,...content.map(e=>box(e).bottom)),s=safe?box(safe):null;
  const overflowElements=content.map(e=>{
   const b=box(e),overflow={};
   for(const [side,amount] of Object.entries({left:r.x-b.x,right:b.x+b.width-r.x-r.width,top:r.y-b.y,bottom:b.bottom-r.bottom}))
    if(amount>.5)overflow[side]=Math.round(amount*100)/100;
   return {tag:e.tagName,id:e.id,classes:e.getAttribute('class')||'',bounds:b,overflow};
  }).filter(e=>Object.keys(e.overflow).length);
  return {overflowElements,height:Math.ceil(Math.max(r.bottom,contentBottom,s?.bottom||0)-r.y),contentBottom,safe:s,ignoredDecorations:ignored.map(e=>({tag:e.tagName,id:e.id,classes:e.className,bounds:box(e)})),bottomElements:content.filter(e=>box(e).bottom>=(s?.y??r.bottom)-.5).map(e=>({tag:e.tagName,id:e.id,classes:e.className,bounds:box(e)}))};
 }
 const final=measure();let natural;
 try{roots.forEach(e=>{e.style.height='auto';e.style.minHeight='0';e.style.maxHeight='none';e.style.overflow='visible'});natural=measure()}
 finally{roots.forEach((e,i)=>saved[i]===null?e.removeAttribute('style'):e.setAttribute('style',saved[i]))}
 const refs=[],invalid=[];
 const check=(url,where)=>{if(!url||url.startsWith('#'))return;refs.push(url);if(!/^https?:\/\//i.test(url))invalid.push({url,where})};
 document.querySelectorAll('img,source,image').forEach(e=>{
 for(const a of ['src','href','xlink:href'])if(e.hasAttribute(a))check(e.getAttribute(a),a);
 if(e.hasAttribute('srcset'))e.getAttribute('srcset').split(',').forEach(v=>check(v.trim().split(/\s+/)[0],'srcset'));
 });
 document.querySelectorAll('[style]').forEach(e=>{for(const m of e.getAttribute('style').matchAll(/url\(\s*['"]?([^'"\)]+)['"]?\s*\)/g))check(m[1].trim(),'css-url')});
 document.querySelectorAll('*').forEach(e=>{for(const pseudo of [null,'::before','::after']){
  const css=getComputedStyle(e,pseudo);
  for(const prop of ['background-image','mask-image','border-image-source','list-style-image','content'])
   for(const m of css.getPropertyValue(prop).matchAll(/url\(\s*['"]?([^'"\)]+)['"]?\s*\)/g))check(m[1].trim(),prop);
 }});
 const declared=safe?.getAttribute('data-canvas-bottom-safe-area')||'';
 const meaningful=e=>!!e.textContent.trim()||!!e.querySelector?.('img,svg,canvas,video,table');
 const collapsed=[];
 root.querySelectorAll('details:not([open])').forEach(e=>{
  if(visible(e)&&[...e.childNodes].some(n=>n.nodeType===3?n.textContent.trim():n.nodeType===1&&n.tagName!=='SUMMARY'&&meaningful(n)))
   collapsed.push({type:'details',id:e.id||null,label:e.querySelector('summary')?.textContent.trim().slice(0,80)||''});
 });
 root.querySelectorAll('[aria-expanded="false"][aria-controls]').forEach(e=>{
  if(!visible(e))return;
  for(const id of e.getAttribute('aria-controls').trim().split(/\s+/)){
   const panel=document.getElementById(id);
   if(panel&&root.contains(panel)&&!visible(panel)&&meaningful(panel))collapsed.push({type:'controlled-panel',id,label:e.textContent.trim().slice(0,80)});
  }
 });
 return {nextScreen:(root.getAttribute('data-canvas-next-screen')||'').trim(),fixed,inlineSizes,final,natural,collapsedContent:collapsed,safeCount:safes.length,safeDeclared:/^[1-9]\d*$/.test(declared)?Number(declared):0,safeVisible:!!safe&&!!visible(safe),safePosition:safe?getComputedStyle(safe).position:null,imageReferences:refs,invalidImageReferences:invalid,brokenImages:[...document.images].filter(e=>!e.complete||!e.naturalWidth).map(e=>e.currentSrc||e.src)};
}"""

TEXT_LAYOUT = r"""() => {
 const root=document.querySelector('[data-canvas-root]'),boxes=[];
 const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
 const box=r=>[r.x,r.y,r.width,r.height];
 for(let node;node=walker.nextNode();){
  const parent=node.parentElement;
  if(!node.data.trim()||!parent||parent.closest('script,style,svg,textarea,select'))continue;
  const range=document.createRange();range.selectNodeContents(node);
  boxes.push([box(parent.getBoundingClientRect()),...Array.from(range.getClientRects(),box)]);
 }
 return boxes;
}"""

TEXT_WRAP = r"""() => {
 const root=document.querySelector('[data-canvas-root]');
 if(!root)throw Error('断行检测缺少作品根节点');
 const semantic='h1,h2,h3,h4,h5,h6,[role="heading"],[data-text-role="title"],[data-text-role="product-name"],[data-text-role="label"]';
 const visible=e=>{
  for(let p=e;p;p=p.parentElement){const s=getComputedStyle(p);if(s.display==='none'||Number(s.opacity)===0)return false;}
  return !['hidden','collapse'].includes(getComputedStyle(e).visibility)&&!!e.getClientRects().length;
 };
 const selector=e=>{
  const parts=[];
  for(let p=e;p&&p!==root;p=p.parentElement){
   if(p.id){parts.unshift('#'+CSS.escape(p.id));return parts.join(' > ');}
   const tag=p.localName;const siblings=[...p.parentElement.children].filter(s=>s.localName===tag);
   parts.unshift(tag+':nth-of-type('+(siblings.indexOf(p)+1)+')');
  }
  return '[data-canvas-root]'+(parts.length?' > '+parts.join(' > '):'');
 };
 const owners=new Map(),walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
 for(let node;node=walker.nextNode();){
  const parent=node.parentElement;
  if(!node.data.trim()||!parent||parent.closest('script,style,svg,textarea,select')||!visible(parent))continue;
  let owner=parent.closest(semantic);
  if(!owner||!root.contains(owner)){
   owner=parent;
   while(owner!==root&&['inline','contents'].includes(getComputedStyle(owner).display))owner=owner.parentElement;
  }
  if(!owner||owner===root)continue;
  if(!owners.has(owner))owners.set(owner,[]);
  owners.get(owner).push(node);
 }
 const segmenter=new Intl.Segmenter('zh',{granularity:'grapheme'}),findings=[],skipped=[];
 let checked=0;
 for(const [owner,nodes] of owners){
  const text=nodes.map(n=>n.data).join('').replace(/\s+/g,' ').trim(),chars=[...segmenter.segment(text.replace(/\s/g,''))];
  if(chars.length<2)continue;
  if(chars.length>(owner.matches(semantic)?200:80)){skipped.push({selector:selector(owner),text,reason:'text-length-limit; visual-review'});continue;}
  const css=getComputedStyle(owner),where=selector(owner),b=owner.getBoundingClientRect();
  const modes=new Set(nodes.map(n=>getComputedStyle(n.parentElement).writingMode));
  const complex=nodes.some(n=>{
   const t=getComputedStyle(n.parentElement);
   if(t.fontSize!==css.fontSize||!['baseline','normal'].includes(t.verticalAlign))return true;
   for(let a=n.parentElement;a;a=a.parentElement){
    const s=getComputedStyle(a);
    if(s.transform!=='none'||s.rotate&&s.rotate!=='none'||s.scale&&s.scale!=='none'||s.columnCount!=='auto'&&s.columnCount!=='1')return true;
   }
   return false;
  });
  if(modes.size>1||!modes.has(css.writingMode)||complex||css.columnCount!=='auto'&&css.columnCount!=='1'){skipped.push({selector:where,text,reason:'mixed-or-multicolumn-layout; visual-review'});continue;}
  if(css.writingMode!=='horizontal-tb'){skipped.push({selector:where,text,reason:'vertical-writing'});continue;}
  // Exempt only the measured text element, never a whole page or ancestor.
  const reason=(owner.getAttribute('data-text-wrap-reason')||'').trim();
  if(owner.getAttribute('data-text-wrap-intent')==='single-character'&&reason){skipped.push({selector:where,text,reason});continue;}
  const lines=[];
  for(const node of nodes){
   for(const part of segmenter.segment(node.data)){
    const range=document.createRange();range.setStart(node,part.index);range.setEnd(node,part.index+part.segment.length);
    const rect=[...range.getClientRects()].find(r=>r.width>.1&&r.height>.1);if(!rect)continue;
    let clipped=false;
    for(let a=node.parentElement;a;a=a.parentElement){
     const st=getComputedStyle(a),ab=a.getBoundingClientRect();
     const clipX=['hidden','clip','scroll','auto'].includes(st.overflowX),clipY=['hidden','clip','scroll','auto'].includes(st.overflowY);
     if(clipX&&((rect.left+rect.right)/2<=ab.left||(rect.left+rect.right)/2>=ab.right)||clipY&&((rect.top+rect.bottom)/2<=ab.top||(rect.top+rect.bottom)/2>=ab.bottom)){clipped=true;break;}
    }
    if(clipped)continue;
    // Baseline/font-size changes within a line must not become new lines.
    let line=lines.find(l=>Math.min(l.bottom,rect.bottom)-Math.max(l.top,rect.top)>Math.min(l.bottom-l.top,rect.height)*.5);
    if(!line){line={top:rect.top,bottom:rect.bottom,parts:[]};lines.push(line);}
    line.top=Math.min(line.top,rect.top);line.bottom=Math.max(line.bottom,rect.bottom);line.parts.push(part.segment);
   }
  }
  lines.sort((a,b)=>a.top-b.top);const rendered=lines.map(l=>l.parts.join('').trim()).filter(Boolean);
  checked++;
  if(rendered.length<2)continue;
  const suspectLines=[];
  rendered.forEach((line,i)=>{
   const content=[...segmenter.segment(line)].map(p=>p.segment).filter(c=>/[\p{L}\p{N}]/u.test(c));
   if(content.length===1&&/\p{Script=Han}/u.test(content[0]))suspectLines.push(i+1);
  });
  if(suspectLines.length)findings.push({selector:where,text,lines:rendered,suspectLines,bounds:{x:b.x+scrollX,y:b.y+scrollY,width:b.width,height:b.height},fontSize:css.fontSize});
 }
 return {checked,findings,skipped,scope:'横排 DOM 标题至多200字、其他文本块至多80字（不计空白）；复杂混排、变换、竖排及超长文本记入skipped，需看预览；不识别图片文字或全部语义断词'};
}
"""

def validate_canvas_source(source):
 """Collect missing/inconsistent fixed sizes before starting a browser."""
 import re
 import tinycss2
 from html.parser import HTMLParser
 class Parser(HTMLParser):
  def __init__(self):
   super().__init__();self.nodes=[];self.stack=[]
  def handle_starttag(self,tag,attrs):
   node={'tag':tag,'attrs':dict(attrs),'parent':self.stack[-1] if self.stack else None}
   self.nodes.append(node)
   if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:self.stack.append(node)
  def handle_endtag(self,tag):
   for i in range(len(self.stack)-1,-1,-1):
    if self.stack[i]['tag']==tag:self.stack=self.stack[:i];break
  def handle_startendtag(self,tag,attrs):
   self.handle_starttag(tag,attrs);self.handle_endtag(tag)
 parser=Parser();parser.feed(source);errors=[]
 def error(node,prop,expected,actual):
  errors.append({'node':node,'property':prop,'expected':expected,'actual':actual,
                 'hint':f'{node} 的 {prop} 应为 {expected}，当前为 {actual or "缺失"}；修正源 HTML 后重试。'})
 def unique(nodes,label):
  if len(nodes)!=1:error(label,'节点数量','1',str(len(nodes)));return None
  return nodes[0]
 html=unique([n for n in parser.nodes if n['tag']=='html'],'html')
 body=unique([n for n in parser.nodes if n['tag']=='body'],'body')
 marked=[n for n in parser.nodes if 'data-canvas-root' in n['attrs']]
 root=unique(marked,'[data-canvas-root]')
 if root is not None:
  ancestor=root['parent']
  while ancestor is not None and ancestor is not body:ancestor=ancestor['parent']
  if body is None or ancestor is not body:
   error('[data-canvas-root]','位置','body 内独立的作品总容器',root['tag'])
 dims={}
 for axis in ('width','height'):
  value=(html['attrs'].get('data-canvas-'+axis) or '') if html else ''
  if not re.fullmatch(r'[0-9]+',value) or int(value)<=0:error('html','data-canvas-'+axis,'十进制正整数',value)
  else:dims[axis]=int(value)
 for label,node in [('html',html),('body',body),('[data-canvas-root]',root)]:
  if node is None:continue
  styles={}
  for d in tinycss2.parse_declaration_list(node['attrs'].get('style') or '',skip_comments=True,skip_whitespace=True):
   if d.type=='declaration' and d.lower_name in ('width','height'):
    previous=styles.get(d.lower_name)
    if previous is None or d.important or not previous.important:styles[d.lower_name]=d
  for axis in ('width','height'):
   declaration=styles.get(axis)
   values=[t for t in declaration.value if t.type not in ('whitespace','comment')] if declaration else []
   actual=tinycss2.serialize(declaration.value).strip() if declaration else ''
   valid=len(values)==1 and values[0].type=='dimension' and values[0].lower_unit=='px' and values[0].value>0
   if not valid or (axis in dims and values[0].value!=dims[axis]):
    error(label,'style.'+axis,str(dims[axis])+'px' if axis in dims else '与画布声明一致的固定 px 值',actual)
 return errors


def run(args):
 source=Path(args.html_file).resolve(strict=True)
 out=Path(args.output).resolve() if args.output else source.parent/'_shots'/(source.stem+'.png')
 if out==source or (out.exists() and out.samefile(source)):raise ValueError('Output must not overwrite HTML source')
 if out.suffix.lower()!='.png':raise ValueError(f'OUTPUT_PATH_INVALID: 输出路径须以 .png 结尾，当前为 {out}；修改 --output，例如 preview.png，无须修改 HTML。')
 out.parent.mkdir(parents=True,exist_ok=True)
 report={'source':str(source),'issues':[],'consoleErrors':[],'resourceErrors':[]}
 def issue(code,hint): report['issues'].append({'code':code,'hint':hint})
 from web_font_check import validate, validate_loaded, validate_font_url
 report['webFontErrors']=validate(source.read_text(encoding='utf-8'))
 report['canvasSpecErrors']=validate_canvas_source(source.read_text(encoding='utf-8'))
 if report['canvasSpecErrors']:issue('CANVAS_SPEC_INVALID','检查 canvasSpecErrors，按节点一次修正全部尺寸声明；未启动浏览器或截图。')
 if report['webFontErrors']:
  issue('INVALID_FONT_RESOURCE','字体地址预检失败；检查 webFontErrors。未截图。')
 if report['issues']:
  report.update(status='needs_review',screenshot=None)
  return report
 from playwright.sync_api import sync_playwright
 from PIL import Image
 with sync_playwright() as p:
  executable=chromium_executable(args.exec_path)
  report['chromiumExecutable']=executable
  browser=p.chromium.launch(executable_path=executable)
  try:
   page=browser.new_page(viewport={'width':800,'height':800},device_scale_factor=1)
   stylesheet_sources={}
   def font_route(route):
    if route.request.resource_type=='font':
     error=validate_font_url(route.request.url)
     if error:
      report['webFontErrors'].append(error);route.abort();return
    route.continue_()
   page.route('**/*',font_route)
   def capture_stylesheet(response):
    if response.request.resource_type=='font':
     error=validate_font_url(response.url)
     if error:report['webFontErrors'].append(error)
    if response.request.resource_type=='stylesheet':
     try:stylesheet_sources[response.url]=response.text()
     except Exception:pass  # CSSOM inspection below still reports inaccessible sources.
   page.on('response',capture_stylesheet)
   page.on('pageerror',lambda e:report['consoleErrors'].append(str(e)))
   page.on('console',lambda m:report['consoleErrors'].append(m.text) if m.type=='error' else None)
   page.on('requestfailed',lambda r:report['resourceErrors'].append({'url':r.url,'error':r.failure}))
   page.on('response',lambda r:report['resourceErrors'].append({'url':r.url,'status':r.status}) if r.status>=400 else None)
   page.goto(source.as_uri(),wait_until='domcontentloaded',timeout=30000)
   dims=page.locator('html').evaluate('(e)=>[e.dataset.canvasWidth,e.dataset.canvasHeight]')
   if any(not x or not x.isdecimal() or int(x)<=0 for x in dims):raise ValueError('Invalid data-canvas-width/height')
   w,h=map(int,dims)
   report['canvas']={'width':w,'height':h}
   page.set_viewport_size({'width':w,'height':min(800,h)})
   page.evaluate("document.documentElement.style.scrollBehavior='auto'")
   for y in range(0,h,600):
    page.evaluate('(y)=>scrollTo(0,y)',y);page.wait_for_timeout(30)
   page.evaluate('scrollTo(0,0)')
   try:page.wait_for_function("()=>document.readyState==='complete'&&(!document.fonts||document.fonts.status==='loaded')&&[...document.images].every(i=>i.complete&&i.naturalWidth>0)",timeout=args.timeout_ms)
   except Exception:issue('RESOURCES_NOT_READY','资源未稳定；检查图片、字体和 resourceErrors，不得声称检查通过。')
   loaded_font_errors=validate_loaded(page,stylesheet_sources)
   report['webFontErrors'].extend(loaded_font_errors)
   if report['webFontErrors']:
    issue('WEB_FONT_CHECK_FAILED','检查字体来源、首选字体声明、字重和加载诊断；未截图。')
    report.update(status='needs_review',screenshot=None)
    return report
   report['fontFaces']=page.evaluate("()=>[...document.fonts].map(f=>({family:f.family,weight:f.weight,style:f.style,status:f.status}))")
   if any(f['status']=='error' for f in report['fontFaces']):issue('FONT_LOAD_FAILED','字体加载失败；检查 CDN/CORS/CSP 和回退后的布局，不得宣称字体加载成功。')
   previous=None;stable=False
   for _ in range(10):
    measured=page.evaluate(MEASURE)
    measured['invalidImageReferences']=[item for item in measured['invalidImageReferences'] if not self_contained_svg_uri(item['url'])]
    signature=json.dumps([measured,page.evaluate(TEXT_LAYOUT)],sort_keys=True)
    if signature==previous:stable=True;break
    previous=signature;page.wait_for_timeout(150)
   report['measurement']=measured
   wrap_ready=stable and not any(i['code'] in {'RESOURCES_NOT_READY','FONT_LOAD_FAILED'} for i in report['issues'])
   report['textWrap']=page.evaluate(TEXT_WRAP) if wrap_ready else {'checked':0,'findings':[],'skipped':[{'selector':'[data-canvas-root]','reason':'resources-or-layout-not-ready; rerender-required'}]}
   report['textWrap']['status']='complete' if wrap_ready else 'not_ready'
   if report['textWrap']['findings']:issue('TEXT_WRAP_REVIEW','发现可疑孤字行，查看 textWrap.findings 的 selector、lines、suspectLines 与位置，并结合本次截图复核。先调整栏宽和图文比例，再按完整词组断行，必要时在可读范围调整字号、字距；不自动缩字、删文案。修正源 HTML 后重新渲染，复查断行、遮挡与溢出。仅确属有意单字强调时，在该文本元素记录 data-text-wrap-intent=single-character 及 data-text-wrap-reason 后复查；不得整页豁免。')
   if measured['collapsedContent']:issue('HTML_CONTENT_COLLAPSED','静态交付须完整展开正文与面板；检查 collapsedContent，修改正式源后重跑，不只在截图副本临时展开。')
   if not stable:issue('LAYOUT_UNSTABLE','布局仍在变化，检查动画或资源加载。')
   if any(r['width']!=f'{w}px' or r['height']!=f'{h}px' for r in measured['inlineSizes']):issue('INLINE_CANVAS_SIZE','三个根节点须分别行内声明与画布属性一致的固定 px 宽高。')
   if any(abs(r['width']-w)>.5 or abs(r['height']-h)>.5 or abs(r['x'])>.5 or abs(r['y'])>.5 for r in measured['fixed']):issue('ROOT_SIZE_MISMATCH','三个根边框盒须位于原点且与声明尺寸一致。')
   if measured['final']['overflowElements'] or measured['final']['height']>h:issue('CONTENT_OVERFLOW','内容超出画布；查看 measurement.final.overflowElements 的元素、方向及越界像素。固定页面须调整排版；只有明确允许自适应高度的长页可参考 natural.height 回填高度，左右越界仍须修正。')
   safe=measured['final']['safe'];declared=measured['safeDeclared']
   continuation_without_safe=bool(measured['nextScreen']) and measured['safeCount']==0
   if not continuation_without_safe and (measured['safeCount']!=1 or not measured['safeVisible'] or measured['safePosition'] in ('absolute','fixed') or not safe or declared<=0 or abs(safe['height']-declared)>.5 or safe['y']<measured['final']['contentBottom']-.5 or safe['bottom']>h+.5):issue('BOTTOM_SAFE_AREA_INVALID','独立页面和末屏需要唯一正常流空白安全区，声明与实际高度一致；连续非末屏仅在根节点声明下一屏 data-canvas-next-screen 时可省略；文字、图片、页码及 fixed 内容仍计入边界。查看 measurement.final.bottomElements，将必要内容移到安全区之前，不能通过换容器或定位方式排除检查。')
   if measured['invalidImageReferences']:issue('IMAGE_SHORTLINK_REQUIRED','图片须使用已准出的 HTTP(S) 地址；仅内嵌脚本生成并核验自包含的百分号编码静态 SVG 可用 data 地址。另与素材清单核对来源。')
   if measured['brokenImages'] or report['resourceErrors'] or report['consoleErrors']:issue('RENDER_ERRORS','读取 consoleErrors、resourceErrors 和 brokenImages 定位源码或资源问题。')
   image=Image.new('RGB',(w,h),'white');slices=[]
   for y in range(0,h,args.slice_height):
    th=min(args.slice_height,h-y)
    tile=Image.open(io.BytesIO(page.screenshot(type='png',full_page=True,clip={'x':0,'y':y,'width':w,'height':th}))).convert('RGB')
    if tile.size!=(w,th):raise ValueError('Tile size mismatch')
    image.paste(tile,(0,y))
    if h>args.slice_height:
     target=out.with_name(f'{out.stem}-{len(slices)+1:03d}.png');tile.save(target);slices.append(str(target))
   image.save(out,format='PNG')
   report.update(status='pass' if not report['issues'] else 'needs_review',screenshot={'path':str(out),'width':w,'height':h},slices=slices,sliceHint='先看主图；主图无法读取时再顺序看分片。')
   return report
  finally:browser.close()

def failure_report(exc,check_runtime=False):
 message=str(exc)
 if check_runtime or isinstance(exc,ImportError) or (isinstance(exc,FileNotFoundError) and 'Chromium' in message):
  code='RUNTIME_UNAVAILABLE';hint='检查 Playwright、Pillow 和 Chromium；由部署端补齐依赖，不在设计任务中下载或切换浏览器。'
 elif isinstance(exc,TimeoutError) or type(exc).__name__=='TimeoutError':
  code='RENDER_TIMEOUT';hint='页面加载或渲染超时；检查资源地址、网络及页面脚本，修复后重跑。'
 elif isinstance(exc,(ValueError,FileNotFoundError)):
  code='INPUT_INVALID';hint='按错误信息修正输入文件、输出路径或参数后重跑；输出文件须为 .png。'
 elif isinstance(exc,PermissionError):
  code='FILE_ACCESS_DENIED';hint='检查输入文件读取权限及输出目录写入权限后重跑。'
 else:
  code='EXECUTION_FAILED';hint='按错误类型和消息定位失败步骤，修复后重跑；不要直接改动作品规避检查。'
 return {'status':'error','screenshot':None,'error':{'code':code,'type':type(exc).__name__,'message':message},'hint':hint+' 本次未完成验证，不能视为检查通过。'}

def main():
 for stream in (sys.stdout,sys.stderr):
  if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8',errors='backslashreplace')
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('html_file',nargs='?');parser.add_argument('-o','--output');parser.add_argument('--exec-path')
 parser.add_argument('--check-runtime',action='store_true',help='只检查 Playwright、Pillow 和 Chromium 是否可用，不读取 HTML 或截图')
 parser.add_argument('--slice-height',type=int,default=3200);parser.add_argument('--timeout-ms',type=int,default=10000)
 args=parser.parse_args()
 if not args.check_runtime and not args.html_file:parser.error('需要 html_file；仅预检时使用 --check-runtime')
 try:
  if args.slice_height<=0 or args.timeout_ms<=0:raise ValueError('Timeout and slice height must be positive')
  if args.check_runtime:result=check_runtime(args.exec_path);code=0
  else:result=run(args);code=0 if result['status']=='pass' else 1
 except Exception as exc:
  result=failure_report(exc,args.check_runtime);code=3
 print(json.dumps(result,ensure_ascii=False,indent=2));return code

if __name__=='__main__':raise SystemExit(main())
