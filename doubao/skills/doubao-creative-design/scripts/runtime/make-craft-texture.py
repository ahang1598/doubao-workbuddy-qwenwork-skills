#!/usr/bin/env python3
"""Generate deterministic, standalone SVG craft approximations; never overwrite assets."""
import argparse, random, math, html, pathlib, re
KINDS=('crumpled-paper','fiber-edge','paper-curl','crumpled-foil','wax-seal','graph-paper','ruled-paper','gingham','chevron','applique')
def generate(kind,w=600,h=360,seed=17,color='#9bbad2',base='#f8f1df',step=28,strength=.45,text='GORGEOUS',font='Arial',weight=700,outline=None):
 r=random.Random(seed)
 esc=lambda s:html.escape(str(s),quote=True)
 c,b=esc(color),esc(base)
 edge=esc(outline or color)
 defs=f'''<filter id="grain"><feTurbulence baseFrequency=".38" numOctaves="3" seed="{seed}"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="linear" slope="{strength*.24}"/></feComponentTransfer><feBlend in="SourceGraphic" mode="multiply" result="grained"/><feComposite in="grained" in2="SourceGraphic" operator="in"/></filter>
 <filter id="rough" x="-10%" y="-10%" width="120%" height="120%"><feTurbulence baseFrequency=".09" numOctaves="2" seed="{seed}" result="noise"/><feDisplacementMap in="SourceGraphic" in2="noise" scale="3"/></filter>
 <filter id="emboss"><feTurbulence baseFrequency=".025 .04" numOctaves="3" seed="{seed}" result="noise"/><feDiffuseLighting in="noise" surfaceScale="{strength*1.4}" diffuseConstant="1" lighting-color="{c}" result="light"><feDistantLight azimuth="225" elevation="45"/></feDiffuseLighting><feSpecularLighting in="noise" surfaceScale="{strength*1.4}" specularConstant=".18" specularExponent="10" lighting-color="#fff4d4" result="shine"><feDistantLight azimuth="225" elevation="45"/></feSpecularLighting><feComposite in="light" in2="shine" operator="arithmetic" k2="1" k3="1" result="metal"/><feComposite in="metal" in2="SourceGraphic" operator="in"/></filter>
 <linearGradient id="curl" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#80765c"/><stop offset=".48" stop-color="{b}"/><stop offset=".8" stop-color="#fff"/><stop offset="1" stop-color="#c9c1aa"/></linearGradient>
 <radialGradient id="wax"><stop stop-color="{c}"/><stop offset=".68" stop-color="{c}"/><stop offset=".77" stop-color="#72501f"/><stop offset=".87" stop-color="#e7c97e"/><stop offset="1" stop-color="#8a6429"/></radialGradient>'''
 rect=lambda fill,extra='':f'<rect width="{w}" height="{h}" fill="{fill}" {extra}/>'
 body=''
 if kind in ('graph-paper','ruled-paper','gingham','chevron'):
  if kind=='graph-paper': pat=f'<path d="M0 {step}V0H{step}" fill="none" stroke="{c}" stroke-width="1"/>'
  elif kind=='ruled-paper':pat=f'<path d="M0 {step-1}H{step}" stroke="{c}" stroke-width="1"/>'
  elif kind=='gingham':pat=f'<rect width="{step/2}" height="{step}" fill="{c}" opacity=".43"/><rect width="{step}" height="{step/2}" fill="{c}" opacity=".43"/>'
  else:pat=f'<path d="M{-step/2} 0L0 {step/2}L{step/2} 0L{step} {step/2}L{step*1.5} 0" fill="none" stroke="{c}" stroke-width="{step*.25}"/>'
  defs+=f'<pattern id="pattern" width="{step}" height="{step}" patternUnits="userSpaceOnUse">{pat}</pattern>'
  body=rect(b)+rect('url(#pattern)')
  if kind=='gingham':
   defs+=f'<pattern id="weave" width="4" height="4" patternUnits="userSpaceOnUse"><path d="M0 0H4M0 0V4" stroke="#fff" opacity=".3"/><path d="M2 0V4" stroke="#000" opacity=".07"/></pattern>'
   body+=rect('url(#weave)')
 elif kind=='crumpled-paper':
  defs+=f'<filter id="creases"><feTurbulence baseFrequency=".018 .028" numOctaves="3" seed="{seed}" result="n"/><feDiffuseLighting in="n" surfaceScale="{strength*6}" diffuseConstant="1.1" lighting-color="{b}" result="l"><feDistantLight azimuth="225" elevation="60"/></feDiffuseLighting><feComposite in="l" in2="SourceGraphic" operator="in"/></filter>'
  body=rect(b,'filter="url(#creases)"')
  # Triangulated low frequency folds, paired ridges; independent fine grain.
  cols,rows=8,5
  pts=[[(i*w/cols+(r.uniform(-18,18) if 0<i<cols else 0),j*h/rows+(r.uniform(-18,18) if 0<j<rows else 0)) for i in range(cols+1)] for j in range(rows+1)]
  for j in range(rows):
   for i in range(cols):
    a,z,d,e=pts[j][i],pts[j][i+1],pts[j+1][i],pts[j+1][i+1]
    for tri in ((a,z,e),(a,d,e)):
     body+=f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in tri)}" fill="{r.choice(("#675842","#fff"))}" opacity="{r.uniform(.02,.12)*strength:.3f}"/>'
    body+=f'<path d="M{a[0]} {a[1]}L{e[0]} {e[1]}" stroke="#fff" opacity="{strength*.2}" fill="none"/>'
  body=f'<g filter="url(#grain)">{body}</g>'
 elif kind=='crumpled-foil':body=rect(c,'filter="url(#emboss)"')
 elif kind=='fiber-edge':
  pts=[]
  for x,y,dx,dy in ((20,20,1,0),(w-20,20,0,1),(w-20,h-20,-1,0),(20,h-20,0,-1)):
   length=w-40 if dx else h-40
   for i in range(0,int(length),8):pts.append((x+dx*i+r.uniform(-4,4),y+dy*i+r.uniform(-4,4)))
  body=f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in pts)}" fill="{c}" filter="url(#grain)"/>'
  for x,y in pts:
   body+=f'<path d="M{x:.1f} {y:.1f}l{r.uniform(-6,6):.1f} {r.uniform(-6,6):.1f}" stroke="{b}" stroke-width="{r.uniform(.3,.9):.2f}" opacity=".8"/>'
 elif kind=='paper-curl':
  # Folded lower-right corner: missing original corner, inward paper back,
  # separate contact shadow beneath flap. Flap tip faces page interior.
  margin=15;right=w-margin;bottom=h-margin;s=min(w,h)*.27
  ax,ay=right-s,bottom;bx,by=right,bottom-s;tx,ty=right-s*.9,bottom-s*.88
  defs+=f'<filter id="curl-contact" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="{s*.028}"/></filter><linearGradient id="paper-back" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{b}"/><stop offset=".55" stop-color="#fffdf5"/><stop offset=".88" stop-color="#d6d0bf"/><stop offset="1" stop-color="#a9a291"/></linearGradient>'
  flap=f'M{ax} {ay}Q{tx+s*.08} {ty+s*.12} {tx} {ty}Q{bx-s*.26} {by-s*.07} {bx} {by}Q{right-s*.47} {bottom-s*.47} {ax} {ay}Z'
  body=f'<path d="M15 15H{right}V{by}L{ax} {bottom}H15Z" fill="{c}" filter="url(#grain)"/><path d="{flap}" fill="#302819" opacity=".25" transform="translate(-2 5)" filter="url(#curl-contact)"/><path d="{flap}" fill="url(#paper-back)" stroke="#e8e2d3" stroke-width=".65"/>'
 elif kind=='wax-seal':
  rad=min(w,h)*.43;cx=w/2;cy=h/2
  pts=[(cx+math.cos(t)*rad*(1+.045*math.sin(t*7)),cy+math.sin(t)*rad*(1+.045*math.sin(t*7))) for t in [i*math.tau/120 for i in range(120)]]
  body=f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in pts)}" fill="url(#wax)" filter="url(#grain)"/>'
  for offset,stroke in ((2,'#edd093'),(0,'#73501d')):
   body+=f'<circle cx="{cx}" cy="{cy+offset}" r="{rad*.58}" fill="none" stroke="{stroke}" stroke-width="2"/><text x="{cx}" y="{cy+rad*.19+offset}" text-anchor="middle" font-family="serif" font-size="{rad*.6}" fill="{stroke}">{esc(text[:2])}</text>'
 else:
  # SVG dashed outline follows actual glyph contours; no rectangular stitch substitute.
  defs+=f'<pattern id="cloth" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="4" fill="{c}"/><path d="M0 0H4M0 0V4" stroke="#fff" opacity=".25" stroke-width=".6"/><path d="M2 0V4" stroke="#000" opacity=".1" stroke-width=".5"/></pattern>' 
  size=min(h*.64,w/max(len(text),1)*1.32)
  attrs=f'x="{w/2}" y="{h*.68}" text-anchor="middle" font-family="{esc(font)}" font-weight="{weight}" font-size="{size}" stroke-linejoin="round"'
  defs+='<filter id="cloth-inset" x="-5%" y="-5%" width="110%" height="110%"><feComponentTransfer in="SourceAlpha" result="inverse"><feFuncA type="table" tableValues="1 0"/></feComponentTransfer><feOffset in="inverse" dx="0" dy=".8" result="shift"/><feGaussianBlur in="shift" stdDeviation=".55" result="soft"/><feComposite in="soft" in2="SourceAlpha" operator="in" result="inside"/><feFlood flood-color="#302a28" flood-opacity=".22" result="ink"/><feComposite in="ink" in2="inside" operator="in" result="shadow"/><feMerge><feMergeNode in="SourceGraphic"/><feMergeNode in="shadow"/></feMerge></filter>'
  body='' 
  body+=f'<text {attrs} fill="{c}" stroke="{edge}" stroke-width="8" filter="url(#rough)">{esc(text)}</text>'
  body+=f'<text {attrs} fill="url(#cloth)" filter="url(#cloth-inset)">{esc(text)}</text><text {attrs} fill="none" stroke="{b}" stroke-width="2" stroke-dasharray="3 3">{esc(text)}</text>' 
  body+=f'<path d="M{w*.28} {h*.7}q-12 14 2 22t-5 20M{w*.76} {h*.68}q14 12 4 26" fill="none" stroke="{b}" stroke-width=".8"/>'
 return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(kind)}"><defs>{defs}</defs>{body}</svg>'
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('kind',choices=KINDS);p.add_argument('output',type=pathlib.Path)
 for k,v in [('width',600),('height',360),('seed',17),('step',28),('weight',700)]:p.add_argument('--'+k,type=int,default=v)
 p.add_argument('--strength',type=float,default=.45);p.add_argument('--color',default='#9bbad2');p.add_argument('--base',default='#f8f1df');p.add_argument('--text',default='GORGEOUS');p.add_argument('--font',default='Arial');p.add_argument('--outline',default=None)
 a=p.parse_args()
 if not(64<=a.width<=4096 and 64<=a.height<=4096 and 4<=a.step<=256 and 0<=a.strength<=1):p.error('size 64–4096, step 4–256, strength 0–1 required')
 if not all(re.fullmatch(r'#[0-9a-fA-F]{6}',c) for c in (a.color,a.base,a.outline or a.color)):p.error('colors must be #RRGGBB')
 if not 1<=len(a.text)<=40:p.error('text length must be 1–40')
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open('x') as f:f.write(generate(a.kind,a.width,a.height,a.seed,a.color,a.base,a.step,a.strength,a.text,a.font,a.weight,a.outline))
if __name__=='__main__':main()
