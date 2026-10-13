#!/usr/bin/env python3
"""Fixed canvas self-check inspired by the supplied shot.py; requires playwright and Pillow."""
import argparse
import io
import json
import math
import os
from pathlib import Path


def chromium_executable(explicit=None):
 """Use the host's chromium-1169 without downloading another browser."""
 if explicit:
  candidate=Path(explicit).expanduser()
  if candidate.is_file() and os.access(candidate,os.X_OK):return str(candidate)
  raise FileNotFoundError(f'Chromium executable unavailable: {candidate}')
 roots=[Path.home()/'.cache/ms-playwright',Path.home()/'Library/Caches/ms-playwright',Path('/ms-playwright'),Path('/opt/ms-playwright'),Path('/root/.cache/ms-playwright'),Path('/home/user/.cache/ms-playwright')]
 if os.environ.get('PLAYWRIGHT_BROWSERS_PATH'):
  roots.insert(0,Path(os.environ['PLAYWRIGHT_BROWSERS_PATH']).expanduser())
 for root in roots:
  revision=root if root.name=='chromium-1169' else root/'chromium-1169'
  for suffix in ('chrome-linux/chrome','chrome-linux64/chrome','chrome-mac/Chromium.app/Contents/MacOS/Chromium','chrome-mac-arm64/Chromium.app/Contents/MacOS/Chromium','chrome-win/chrome.exe'):
   candidate=revision/suffix
   if candidate.is_file() and os.access(candidate,os.X_OK):return str(candidate)
 raise FileNotFoundError('chromium-1169 未找到；通过 PLAYWRIGHT_BROWSERS_PATH 或 --exec-path 指定系统已有安装，不下载其他浏览器。')

MEASURE = r"""() => {
 const root=document.querySelector('[data-canvas-root]')||document.querySelector('main')||document.body.firstElementChild;
 if(!root)throw Error('Missing artwork root');
 const box=e=>{const r=e.getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,bottom:r.bottom+scrollY}};
 const visible=e=>{const s=getComputedStyle(e);return s.display!=='none'&&s.visibility!=='hidden'&&Number(s.opacity)>0&&e.getClientRects().length};
 const roots=[document.documentElement,document.body,root],fixed=roots.map(box),saved=roots.map(e=>e.getAttribute('style'));
 const safes=[...root.querySelectorAll('[data-canvas-bottom-safe-area]')],safe=safes.length===1?safes[0]:null;
 function measure(){
  const r=box(root),leaves=[...root.querySelectorAll('*')].filter(e=>visible(e)&&e!==safe&&!safe?.contains(e)&&getComputedStyle(e).position!=='fixed'&&(e.childElementCount===0||[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())));
  const contentBottom=Math.max(r.y,...leaves.map(e=>box(e).bottom)),s=safe?box(safe):null;
  return {height:Math.ceil(Math.max(r.bottom,contentBottom,s?.bottom||0)-r.y),contentBottom,safe:s};
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
 return {fixed,final,natural,safeCount:safes.length,safeDeclared:Number(safe?.getAttribute('data-canvas-bottom-safe-area')||0),safeVisible:!!safe&&!!visible(safe),safePosition:safe?getComputedStyle(safe).position:null,imageReferences:refs,invalidImageReferences:invalid,brokenImages:[...document.images].filter(e=>!e.complete||!e.naturalWidth).map(e=>e.currentSrc||e.src)};
}"""

def run(args):
 from playwright.sync_api import sync_playwright
 from PIL import Image
 source=Path(args.html_file).resolve(strict=True)
 out=Path(args.output).resolve() if args.output else source.parent/'_shots'/(source.stem+'.png')
 if out==source or (out.exists() and out.samefile(source)):raise ValueError('Output must not overwrite HTML source')
 if out.suffix.lower()!='.png':raise ValueError('Output must use .png extension')
 out.parent.mkdir(parents=True,exist_ok=True)
 report={'source':str(source),'issues':[],'consoleErrors':[],'resourceErrors':[]}
 def issue(code,hint): report['issues'].append({'code':code,'hint':hint})
 from web_font_check import validate
 report['webFontErrors']=validate(source.read_text(encoding='utf-8'))
 if report['webFontErrors']:issue('WEB_FONT_CONTRACT_INVALID','仅允许 head 内唯一 data-web-fonts 块，逐字使用 resolver 的字体声明；其他视觉样式保持行内。')
 with sync_playwright() as p:
  executable=chromium_executable(args.exec_path)
  report['chromiumExecutable']=executable
  browser=p.chromium.launch(executable_path=executable)
  try:
   page=browser.new_page(viewport={'width':800,'height':800},device_scale_factor=1)
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
   report['fontFaces']=page.evaluate("()=>[...document.fonts].map(f=>({family:f.family,weight:f.weight,style:f.style,status:f.status}))")
   if any(f['status']=='error' for f in report['fontFaces']):issue('FONT_LOAD_FAILED','字体加载失败；检查 CDN/CORS/CSP 和回退后的布局，不得宣称字体加载成功。')
   previous=None;stable=False
   for _ in range(10):
    measured=page.evaluate(MEASURE);signature=json.dumps(measured,sort_keys=True)
    if signature==previous:stable=True;break
    previous=signature;page.wait_for_timeout(150)
   report['measurement']=measured
   if not stable:issue('LAYOUT_UNSTABLE','布局仍在变化，检查动画或资源加载。')
   if any(abs(r['width']-w)>.5 or abs(r['height']-h)>.5 or abs(r['x'])>.5 or abs(r['y'])>.5 for r in measured['fixed']):issue('ROOT_SIZE_MISMATCH','三个根边框盒须位于原点且与声明尺寸一致。')
   if measured['final']['height']>h:issue('CONTENT_OVERFLOW','锁高时重排；未锁高时参考 natural.height 回填四处高度再运行。')
   safe=measured['final']['safe'];minimum=max(24,math.ceil(w*.04),measured['safeDeclared'])
   if measured['safeCount']!=1 or not measured['safeVisible'] or measured['safePosition'] in ('absolute','fixed') or not safe or safe['height']<minimum or safe['y']<measured['final']['contentBottom']-.5 or safe['bottom']>h+.5:issue('BOTTOM_SAFE_AREA_INVALID','末尾需要唯一正常流安全区；检查实际高度、压缩、位置和内容越界。')
   if measured['invalidImageReferences']:issue('IMAGE_SHORTLINK_REQUIRED','图片须静态使用已准出的 HTTP(S) 短链；另与素材清单核对来源。')
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

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('html_file');parser.add_argument('-o','--output');parser.add_argument('--exec-path')
 parser.add_argument('--slice-height',type=int,default=3200);parser.add_argument('--timeout-ms',type=int,default=10000)
 args=parser.parse_args()
 try:
  if args.slice_height<=0 or args.timeout_ms<=0:raise ValueError('Timeout and slice height must be positive')
  result=run(args);code=0 if result['status']=='pass' else 1
 except Exception as exc:
  result={'status':'error','error':{'code':type(exc).__name__,'message':str(exc)},'hint':'检查 Playwright、Pillow、Chromium 和输入文件。执行失败可跳过自检继续交付；记录未验证，不伪造预览。'};code=3
 print(json.dumps(result,ensure_ascii=False,indent=2));return code

if __name__=='__main__':raise SystemExit(main())
