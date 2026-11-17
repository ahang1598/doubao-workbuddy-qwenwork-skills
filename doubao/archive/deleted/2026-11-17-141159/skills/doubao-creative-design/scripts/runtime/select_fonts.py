#!/usr/bin/env python3
"""Query the shared editorial pool; never install fonts or certify rendered glyphs."""
import argparse
import json
from pathlib import Path
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
ROLES = ('hero', 'sub', 'body', 'meta')
BRUSH_MOODS = {'wild', 'cute', 'fresh'}

class FontBindingError(ValueError):
    def __init__(self, code, combination, detail):
        self.code, self.combination = code, combination
        super().__init__(f'{code}: {combination}: {detail}')

def combination_profile(root, pool, combination):
    entries = load_json(Path(root)/'assets/templates/css/catalog.json')['entries']
    matches = [entry for entry in entries if entry['id'] == combination and combination.startswith('combination.')]
    if len(matches) != 1:
        raise ValueError('UNKNOWN_COMBINATION: ' + combination)
    combinations = pool.get('combinations')
    if not isinstance(combinations, dict) or combination not in combinations:
        raise FontBindingError('FONT_BINDING_MISSING', combination, 'pool.combinations requires an explicit mapping')
    profile = combinations[combination]
    if not isinstance(profile, dict) or not isinstance(profile.get('theme'), str) or profile.get('theme') not in pool['themes']:
        raise FontBindingError('FONT_PROFILE_INVALID', combination, 'invalid combination font mapping')
    lanes = profile.get('language_roles')
    if not isinstance(lanes, dict):
        raise FontBindingError('FONT_PROFILE_INVALID', combination, 'language_roles must be an object')
    for language in ('zh', 'en', 'ko', 'ja'):
        roles = lanes.get(language)
        if not isinstance(roles, dict):
            raise FontBindingError('FONT_ROLE_MISSING', combination, language)
        for role in ROLES:
            keys = roles.get(role)
            if not isinstance(keys, list) or not keys or any(not isinstance(key, str) for key in keys):
                raise FontBindingError('FONT_ROLE_MISSING', combination, f'{combination}/{language}/{role}')
    return profile


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def normalize(value):
    return ''.join(unicodedata.normalize('NFKC', str(value)).casefold().split())

def load_records(root=ROOT):
    records = {}
    for path in sorted((Path(root)/'assets/fonts/catalogs').glob('*.json')):
        for record in load_json(path)['records']:
            if record['id'] in records:
                raise ValueError('Duplicate catalog ID: '+record['id'])
            records[record['id']] = record
    return records

def canonical(value, pool):
    aliases = {normalize(k):normalize(v) for k,v in pool['tag_aliases'].items()}
    return aliases.get(normalize(value), normalize(value))

def resource_status(record, cdn_ids, root):
    if any((Path(root)/p).is_file() for p in record.get('local_paths', [])):
        return 'local_present'
    if record.get('id') in cdn_ids:
        return 'cdn_listed_not_rechecked'
    return 'not_installed' if record else 'unresolved'

def recommend(root=ROOT, theme=None, role='hero', shape=None, tags=None, limit=10,
              available_only=False, combination=None, exclude=None, language='zh',
              platform_only=False):
    root = Path(root)
    pool = load_json(root/'assets/fonts/font-curated-pool.json')
    records = load_records(root)
    if role not in ROLES or not isinstance(limit,int) or limit < 1:
        raise ValueError('Role must be hero/sub/body/meta and limit must be positive')
    language = pool['language_aliases'].get(language.casefold(), language.casefold())
    if language not in ('zh','en','ko','ja'):
        raise ValueError('No curated language lane: '+language+'; inspect catalogs and verify real text')
    combo = combination_profile(root, pool, combination) if combination else None
    if combo and theme and theme != combo['theme']:
        raise ValueError('Explicit theme conflicts with combination font profile')
    resolved = theme or (combo['theme'] if combo else None)
    if resolved and resolved not in pool['themes']:
        raise ValueError('Unknown theme: '+resolved)
    if not resolved and not shape and not tags:
        raise ValueError('Provide theme, combination or traits')
    fonts = {f['key']:f for f in pool['fonts']}
    if len(fonts) != len(pool['fonts']):
        raise ValueError('Duplicate font key')
    wanted = {canonical(t,pool) for t in ([shape] if shape else [])+(tags or [])}
    muyao_intent = 'cute' in wanted and bool(wanted & {'brush', 'soft-brush'})
    excluded = {normalize(x) for x in (exclude or [])+pool['blocked_names']}
    cdn_ids = {x['catalog_id'] for x in load_json(root/'assets/fonts/font-cdn-manifest.json')['files'] if x.get('verified') is True}
    platform = {x['family']:x for x in pool['platform_fonts']}
    ordered = []
    if combo:
        for key in combo['language_roles'][language][role]:
            if key not in fonts:
                raise FontBindingError('FONT_REFERENCE_INVALID', combination, 'unknown font key: '+key)
            font = fonts[key]
            if font.get('catalog_id') and font['catalog_id'] not in records:
                raise FontBindingError('FONT_REFERENCE_INVALID', combination, 'unknown catalog: '+font['catalog_id'])
            if role not in font['roles'] or language not in font['recommendation_languages']:
                raise FontBindingError('FONT_ROLE_INVALID', combination, key+'/'+language+'/'+role)
        ordered.extend((key,'combination_ranked') for key in combo['language_roles'][language][role])
    if resolved:
        ordered.extend((key,'theme_ranked') for key in pool['themes'][resolved]['language_roles'][language][role])
    if wanted:
        ordered.extend((key,'trait_fallback') for key in fonts)
    # Keep Muyao behind other eligible candidates before applying the limit.
    ordered.sort(key=lambda item: item[0] == 'muyao')
    candidates = []
    seen = set()
    for key, source in ordered:
        if key in seen:
            continue
        seen.add(key)
        f = fonts[key]
        if key == 'muyao' and not muyao_intent:
            continue
        if role not in f['roles'] or language not in f['recommendation_languages']:
            continue
        if not wanted.issubset({canonical(t,pool) for t in [f['shape'],*f.get('tags',[])]}):
            continue
        record = records.get(f['catalog_id'], {})
        if f['catalog_id'] and not record:
            raise ValueError('Unresolved catalog ID: '+f['catalog_id'])
        registered = [platform[family] for family in f['platform_families']]
        identities = [key,f['display_name'],f['catalog_id'],record.get('name',''),
                      *f.get('aliases',[]),*f['platform_families']]
        if excluded.intersection(normalize(x) for x in identities):
            continue
        status = resource_status(record,cdn_ids,root)
        if available_only and status not in ('local_present','cdn_listed_not_rechecked'):
            continue
        if platform_only and not registered:
            continue
        license_name = str(record.get('license','')).casefold()
        permissive = record.get('open_source') is True and any(x in license_name for x in ('ofl','apache','ubuntu font license','ufl'))
        candidates.append(dict(rank=len(candidates)+1,selection_source=source,key=key,
            display_name=f['display_name'],catalog_id=f['catalog_id'],catalog_name=record.get('name'),
            catalog_resolution=f['catalog_resolution'],shape=f['shape'],tags=f.get('tags',[]),roles=f['roles'],
            recommendation_languages=f['recommendation_languages'],language=record.get('language'),
            design_note=f['design_note'],resource_status=status,
            platform_status='listed_not_runtime_verified' if registered else 'not_listed',
            registered_faces=registered,license_status='catalog_permissive' if permissive else 'review_required',
            source_platform=record.get('source_platform'),source_url=record.get('source_url'),
            coverage_status='not_tested',face_status='not_tested'))
        if len(candidates) >= limit:
            break
    # Diagnostics explain missing editorial evidence; they never relax the AND filter.
    known_traits = {canonical(t, pool) for f in fonts.values()
                    for t in [f['shape'], *f.get('tags', [])]} | BRUSH_MOODS
    unknown_traits = sorted(wanted - known_traits)
    pending = []
    moods = wanted & BRUSH_MOODS
    if moods and wanted & {'brush', 'soft-brush', 'brush-script', 'brush-kai'}:
        for f in fonts.values():
            traits = {canonical(t, pool) for t in [f['shape'], *f.get('tags', [])]}
            if 'brush' not in traits or role not in f['roles'] or language not in f['recommendation_languages']:
                continue
            if not (wanted - BRUSH_MOODS).issubset(traits):
                continue
            record = records.get(f['catalog_id'], {})
            identities = [f['key'], f['display_name'], f['catalog_id'], record.get('name', ''),
                          *f.get('aliases', []), *f['platform_families']]
            if excluded.intersection(normalize(x) for x in identities):
                continue
            unreviewed = sorted(moods - set(f.get('reviewed_brush_moods', [])))
            if unreviewed:
                pending.append({'key': f['key'], 'traits': unreviewed})
    trait_diagnostics = dict(
        status='unknown_traits' if unknown_traits else ('matches' if candidates else 'no_matches'),
        normalized_traits=sorted(wanted), unknown_traits=unknown_traits,
        unreviewed_brush_traits=pending,
        note='Unreviewed brush moods are metadata gaps, not positive matches or available resources. Never remove requested traits to fill a shortfall.')
    return dict(theme=resolved,theme_label=pool['themes'][resolved]['label'] if resolved else None,
        combination=combination,role=role,language=language,
        selection_policy={'muyao_cute_brush_intent': muyao_intent,
                          'deprioritized_fonts': ['muyao'],
                          'query_role': 'deterministic_query_and_diagnostics',
                          'visual_review_required': True,
                          'availability_scope': 'runtime',
                          'recommendations_are_exhaustive': False},
        requested_traits={'shape':shape,'tags':tags or []},trait_diagnostics=trait_diagnostics,candidates=candidates,
        requested_count=limit,shortfall=max(0,limit-len(candidates)),selection_order=pool['selection_order'],
        note='Recommendation scope is not glyph coverage. Registered styles and resource metadata are not runtime approval. Preserve exact user/recipe constraints; never pad a shortfall with incompatible fonts.',
        next_step='Compare 2–3 suitable candidates with real text. Before formal HTML, verify the target platform, license, actual family/face/weight, glyph coverage and Web loading. If a user-locked font cannot pass, request confirmation before substitution. Record the result in the existing validation and final HTML; do not create standalone font-contract.json unless explicitly required. Keep the existing production format.')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--theme');parser.add_argument('--combination')
    parser.add_argument('--role',choices=ROLES)
    parser.add_argument('--language',default='zh')
    parser.add_argument('--shape');parser.add_argument('--tag',action='append',default=[])
    parser.add_argument('--exclude',action='append',default=[])
    parser.add_argument('--limit',type=int,default=10)
    parser.add_argument('--available-only',action='store_true',help='Local file or historical CDN listing; not actual render readiness')
    parser.add_argument('--platform-only',action='store_true',help='Recorded platform family only; not current runtime verification')
    parser.add_argument('--list-themes',action='store_true')
    parser.add_argument('--list-tags',action='store_true')
    parser.add_argument('--list-platform-fonts',action='store_true')
    args = parser.parse_args()
    try:
        pool = load_json(args.root/'assets/fonts/font-curated-pool.json')
        if args.list_themes:
            result = {k:{'label':v['label'],'keywords':v['keywords']} for k,v in pool['themes'].items()}
        elif args.list_tags:
            result = {'aliases':pool['tag_aliases'],'tags':sorted({t for f in pool['fonts'] for t in f.get('tags',[])})}
        elif args.list_platform_fonts:
            result = {'families':pool['platform_fonts'],'status':'listed_not_runtime_verified'}
        else:
            if not args.role:
                parser.error('--role is required')
            result = recommend(args.root,args.theme,args.role,args.shape,args.tag,args.limit,
                args.available_only,args.combination,args.exclude,args.language,args.platform_only)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    except (ValueError,KeyError,OSError) as error:
        parser.exit(2,json.dumps({'error':str(error)},ensure_ascii=False)+'\n')

if __name__=='__main__':
    raise SystemExit(main())
