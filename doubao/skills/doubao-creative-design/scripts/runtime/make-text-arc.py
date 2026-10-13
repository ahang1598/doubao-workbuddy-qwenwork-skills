#!/usr/bin/env python3
"""Generate one editable curved-title SVG from the bundled template."""
import argparse
import math
import os
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

NS='http://www.w3.org/2000/svg'
ET.register_namespace('',NS)


def build(text, width=320, height=140, rise=40, baseline=100, inset=24,
          font_size=28, letter_spacing=0, font_family=None):
    values=[width,height,rise,baseline,inset,font_size,letter_spacing]
    if not all(math.isfinite(v) for v in values):
        raise ValueError('Geometry must be finite')
    if width<=0 or height<=0 or font_size<=0 or not 0<=inset<width/2:
        raise ValueError('Invalid size or inset')
    if not 0<=rise<baseline<height or baseline-rise<font_size or baseline+font_size/2>height:
        raise ValueError('Curve must leave room above the text and stay inside the canvas')
    if not text.strip():
        raise ValueError('Text must not be empty')
    root=ET.parse(Path(__file__).resolve().parents[2]/'assets/svg/text-arc.svg').getroot()
    root.set('width',f'{width:g}');root.set('height',f'{height:g}')
    root.set('viewBox',f'0 0 {width:g} {height:g}');root.set('aria-label',text)
    root.find(f'.//{{{NS}}}path').set('d',f'M{inset:g} {baseline:g}Q{width/2:g} {baseline-2*rise:g} {width-inset:g} {baseline:g}')
    node=root.find(f'.//{{{NS}}}text');node.set('font-size',f'{font_size:g}');node.set('letter-spacing',f'{letter_spacing:g}')
    if font_family:node.set('font-family',font_family)
    root.find(f'.//{{{NS}}}textPath').text=text
    return ET.tostring(root,encoding='unicode')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--text',required=True);parser.add_argument('--output',required=True,type=Path)
    for name,default in [('width',320),('height',140),('rise',40),('baseline',100),('inset',24),('font-size',28),('letter-spacing',0)]:
        parser.add_argument('--'+name,type=float,default=default)
    parser.add_argument('--font-family');parser.add_argument('--force',action='store_true')
    args=parser.parse_args();temp=None
    try:
        if args.output.exists() and not args.force:raise ValueError('Output exists; use another name or --force')
        svg=build(args.text,args.width,args.height,args.rise,args.baseline,args.inset,args.font_size,args.letter_spacing,args.font_family)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=args.output.parent,prefix='.text-arc-',delete=False) as stream:
            temp=Path(stream.name);stream.write(svg)
        os.replace(temp,args.output)
        print(f'Wrote editable arc SVG: {args.output}')
    except (OSError,ValueError,ET.ParseError) as error:
        if temp is not None:temp.unlink(missing_ok=True)
        parser.exit(1,f'make-text-arc: {error}\n')


if __name__=='__main__':main()
