#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render registered semantic boundaries. Never infer screens from equal-height tiles."""
import argparse,hashlib,html,importlib.util,json,math,tempfile
from pathlib import Path
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--template',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--index-file',type=Path,help='Explicit unpublished index for boundary review');a=p.parse_args();s=a.root.resolve();out=a.output.resolve()
 if out.exists():raise ValueError('Output already exists; choose a new review directory')
 sp=importlib.util.spec_from_file_location('query',s/'scripts/query-template-library.py');q=importlib.util.module_from_spec(sp);sp.loader.exec_module(q);lib=q.TemplateLibrary(s);row=lib.resolve(a.template)
 if len(row)!=1:raise ValueError('Template reference must be unique')
 row=row[0]
 if a.index_file:row['screen_index']=json.loads(a.index_file.read_text())
 screens=lib.screens(row)
 if not screens:raise ValueError('No verified boundaries; equal-height fallback is forbidden')
 idx=row['screen_index'];loc=q.ScreenLocators(lib.verified_text(row['file']))
 for sc in screens:
  z=sc['bounds']
  if z['height']<=0 or abs(z['bottom']-z['y']-z['height'])>0.1:raise ValueError('Invalid screen bounds')
  for sel in sc.get('member_selectors',[]):
   if loc.counts.get(sel)!=1:raise ValueError('Invalid member selector: '+sel)
 out.mkdir(parents=True);sp=importlib.util.spec_from_file_location('shot',s/'scripts/shot.py');shot=importlib.util.module_from_spec(sp);sp.loader.exec_module(shot)
 with tempfile.TemporaryDirectory(prefix='template-render-') as temporary, sync_playwright() as pw:
  source=lib.materialize(row['file'],temporary)
  b=pw.chromium.launch(executable_path=shot.chromium_executable(None));page=b.new_page(viewport=idx['viewport'],device_scale_factor=1)
  errors=[]
  page.on('pageerror',lambda error:errors.append(str(error)))
  page.on('requestfailed',lambda request:errors.append(request.url+' '+str(request.failure)) if request.url.startswith('file:') else None)
  page.goto(source.as_uri(),wait_until='networkidle');page.evaluate('document.fonts.ready')
  if errors:raise ValueError('模板渲染失败：'+'; '.join(errors))
  height=page.evaluate('document.documentElement.scrollHeight');width=idx['viewport']['width'];full=Image.new('RGB',(width,height),'white')
  for y in range(0,height,3000):
   f=out/('tile-'+str(y)+'.png');page.screenshot(path=str(f),full_page=True,clip={'x':0,'y':y,'width':width,'height':min(3000,height-y)});full.paste(Image.open(f).convert('RGB'),(0,y))
  if errors:raise ValueError('模板渲染失败：'+'; '.join(errors))
  b.close()
 full.save(out/'full.png');marked=full.copy();draw=ImageDraw.Draw(marked);cards=[];thumbs=[];export=[]
 for i,sc in enumerate(screens):
  z=sc['bounds'];x=round(z['x']);y=round(z['y']);end=round(z['bottom']);right=round(z['x']+z['width']);crop=full.crop((x,y,right,end));name=sc['id']+'.png';crop.save(out/name);draw.line((x,y,right,y),fill='#e63333',width=3);draw.text((x+4,y+4),str(i+1)+' '+sc['id'],fill='#e63333')
  group=[sc]+[v for v in screens if v['id'] in sc['required_sections']];gname=''
  if len(group)>1:
   gy=round(min(v['bounds']['y'] for v in group));ge=round(max(v['bounds']['bottom'] for v in group));gname=sc['id']+'-with-dependencies.png';full.crop((x,gy,right,ge)).save(out/gname)
  thumb=(Image.open(out/gname).convert('RGB') if gname else crop.copy());thumb.thumbnail((240,1500));thumbs.append((sc['id']+(' + linked' if gname else ''),thumb));export.append({'id':sc['id'],'pixel_bounds':[x,y,right,end],'required_sections':sc['required_sections'],'image':name,'with_dependencies':gname})
  cards.append('<article><h2>'+str(i+1)+' · '+html.escape(sc['title'])+'</h2><p>'+html.escape(sc['id'])+' · y='+str(y)+'–'+str(end)+' · '+str(end-y)+'px</p><p>'+html.escape(sc['boundary_basis'])+'</p><p>关联：'+html.escape(', '.join(sc['required_sections']) or '无登记依赖；未验证独立组件')+'</p>'+('<a href="'+gname+'">查看含关联区的完整图</a>' if gname else '')+'<p>用途：'+html.escape('、'.join(sc['purposes']))+' · 布局：'+html.escape('、'.join(sc['layouts']))+'</p>'+('<p>以下展示本屏与关联区的联合预览，源屏边界仍分开记录。<a href="'+name+'">本屏边界切片</a></p>' if gname else '')+'<a href="'+(gname or name)+'"><img src="'+(gname or name)+'"></a></article>')
 marked.save(out/'boundaries.png');cols=4;rows=math.ceil(len(thumbs)/cols);cellh=max(t.height for _,t in thumbs)+32;board=Image.new('RGB',(cols*260,rows*cellh),'#eeeeee');dr=ImageDraw.Draw(board)
 for i,(name,t) in enumerate(thumbs):x=(i%cols)*260;y=(i//cols)*cellh;dr.text((x+10,y+5),name,fill='black');board.paste(t,(x+10,y+28))
 board.save(out/'board.png');(out/'cuts.json').write_text(json.dumps(export,ensure_ascii=False,indent=2))
 (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>真实分区切屏核对</title><style>body{font:16px/1.6 sans-serif;background:#eee;margin:24px}main{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}article{background:white;padding:16px}img{width:100%;height:auto}h2{font-size:19px}</style><h1>'+html.escape(row['name'])+'</h1><p>按源分区切片，不等高；跨区图片可能在单片中截断，使用时须同时读取所列关联区。切片不等于独立组件。</p><p><a href="boundaries.png">整页边界线</a> · <a href="full.png">完整渲染</a></p><main>'+''.join(cards)+'</main>')
 print(json.dumps({'screens':len(screens),'output':str(out)},ensure_ascii=False))
if __name__=='__main__':main()
