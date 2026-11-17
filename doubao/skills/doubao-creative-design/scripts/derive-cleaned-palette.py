#!/usr/bin/env python3
"""Derive selected imported palette roles without modifying source tokens or grayscale templates."""
import argparse
import importlib.util
import hashlib
import json
from pathlib import Path
from cleaned_palette import extract, derive

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id',required=True,help='original palette-0001 or catalog palette.cleaned-palette-0001')
    parser.add_argument('--color',required=True)
    parser.add_argument('--mode',choices=('preserve','exact'),default='preserve')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    identifier=args.id.removeprefix('palette.cleaned-')
    manifest=json.loads((ROOT/'assets/模板库/manifest.json').read_text())
    catalog_id='palette.cleaned-'+identifier
    profile=manifest['palette_profiles'].get(catalog_id)
    if not profile:parser.error('Unknown published palette ID')
    source=(ROOT/profile['file']).resolve()
    if not source.is_relative_to(ROOT/'assets/模板库'):parser.error('Palette path is outside published library')
    spec=importlib.util.spec_from_file_location('template_library', ROOT/'scripts/query-template-library.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        raw=module.TemplateLibrary(ROOT).verified_bytes(profile['file'])
    except (ValueError, OSError) as error:
        parser.error(str(error))
    entry={'path':profile['file'],'name':source.stem}
    colors=extract(raw.decode('utf-8'))
    result=derive(entry['name'],colors,args.color,args.mode,role_override=profile['roles'])
    result.update(source_id=identifier,catalog_id='palette.cleaned-'+identifier,source_path=entry['path'],
                  source_sha256=hashlib.sha256(raw).hexdigest(),
                  adoption_boundary='颜色角色仅供当前Brief选择和绑定，不自动给灰度模板上色，不改变入口裁定的生产路线。')
    value=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(value)
        print(json.dumps({'output':str(args.output),'source_id':identifier,'contrast':result['contrast']},ensure_ascii=False))
    else:print(value,end='')

if __name__=='__main__':main()
