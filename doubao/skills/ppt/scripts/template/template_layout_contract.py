#!/usr/bin/env python3
"""Generate and validate opt-in layout authoring contracts from layouts.json.

No source PPTX/Slides/Office/network operations. All layout metadata lives in
external JSON; the skeleton uses only native SML shape/content/id attributes.

CLI: --manifest layouts.json --layout 'Title and Content' --output contract.json
     --skeleton slide.xml [--free-regions regions.json] [--instance-id page-01]
Validation CLI: --contract contract.json --sml authored.xml [--bindings map.json]

Pure APIs:
  build_layout_contract(manifest, layout_name, free_regions=None, instance_id=None)
  generate_skeleton(contract) -> one empty-content native <slide>
  validate_layout_contract(sml, contract, manifest=None, bindings=None, tolerance=.5)

bindings = {"elements": {"native-id": "slot_id", "data_index:0": "slot_id"},
            "decorative_ids": ["logo-id"]}
Each source slot also exposes sml_font_families: latin, east_asian,
complex_script, scripts (real referenced theme script families), source_language.
The empty skeleton uses the source Latin default. Authored CJK text/spans use
their actual EA or theme script family; the validator checks each visible run.
Han without a Chinese locale cannot distinguish Hans/Hant, so either actual
source family is accepted. Kana/Hangul or source zh-TW/zh-CN locale selects the
specific source script. Missing source metadata stays unresolved, never becomes
a guessed local font. bindings.font_substitutions = {slot_id: {fontFamily,
reason}} is only an explicit unavailable-source-font replacement, not necessary
for legitimate source EA/script inheritance. Source size/alignment checks still
apply to substituted fonts. Visible subtitle text is checked too. Transformed
or unresolved subtitle colors stay warnings rather than treating computed RGB
as renderer proof. Body/obj text needs a separate semantic role contract before
strict typography checks; a bound chart caption is not necessarily body copy.
data_index is a zero-based position among direct <data> children. It supports
authoring XML without IDs; explicit maps also support server-assigned IDs.
One content slot can contain several bound elements. Title slots are required
and exact; other boxes contain their bound content. Footer/date/page slots are
optional. No title-only/blank free region is inferred: supply explicit regions
with name, bbox and optional allowed_kinds. Nontext shapes and lines are ignored;
image logos/backgrounds must be explicitly marked decorative. Text/chart/table
cannot be hidden using a decorative binding. This API is only for a selected
layout contract, never an unconditional whole-deck geometry lock.
"""
from __future__ import annotations

import argparse
import colorsys
from contextlib import ExitStack
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET

SML_NS = 'https://www.larkoffice.com/sml/2.0'
BBOX_KEYS = ('x', 'y', 'width', 'height')
SML_BBOX = ('topLeftX', 'topLeftY', 'width', 'height')
TITLE_ROLES = frozenset({'title', 'ctrTitle'})
KINDS = frozenset({'text', 'chart', 'table', 'img', 'embed'})
ROLE_KINDS = {'title':['text'], 'ctrTitle':['text'], 'subTitle':['text'],
              'body':['text','chart','table','img','embed'], 'obj':['text','chart','table','img','embed'],
              'chart':['chart'], 'tbl':['table'], 'pic':['img'],
              'dgm':['text','img','embed'], 'media':['img'], 'clipArt':['img'],
              'dt':['text'], 'ftr':['text'], 'sldNum':['text']}
TEXT_STYLE_ROLES = TITLE_ROLES | frozenset({'subTitle'})


def local(tag):
    return tag.rsplit('}', 1)[-1]


def fingerprint(data):
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def number(value):
    value = float(value)
    return str(int(value)) if value.is_integer() else repr(value)


def valid_bbox(box):
    return (isinstance(box, dict) and all(isinstance(box.get(k), (int,float)) and
            not isinstance(box[k], bool) and math.isfinite(box[k]) for k in BBOX_KEYS)
            and box['width'] > 0 and box['height'] > 0)


def select_layout(manifest, name, source_file=None):
    candidates = [l for l in manifest.get('layouts', []) if l.get('name') == name and
                  (source_file is None or l.get('source_file') == source_file)]
    if len(candidates) != 1:
        raise ValueError(f'Layout must resolve exactly once: {name!r} ({len(candidates)} matches)')
    return candidates[0]


def _resolved_color(value, theme, cmap, warnings):
    """Resolve supported OOXML color transforms; retain unresolved evidence in JSON."""
    if not value:
        return None
    kind = value.get('type')
    attrs = value.get('attributes', {})
    token = value.get('value')
    if kind == 'schemeClr':
        target = cmap.get(token, token)
        base = theme.get('colors', {}).get(target)
        resolved = _resolved_color(base, theme, {}, warnings) if base else None
        if resolved is None:
            warnings.append(f'Unresolved theme color: {token}')
            return None
        rgb, alpha = resolved
    elif kind in {'srgbClr','sysClr'}:
        raw = attrs.get('lastClr') if kind == 'sysClr' else token
        if not isinstance(raw, str) or not re.fullmatch('[0-9a-fA-F]{6}',raw):
            warnings.append(f'Unsupported {kind} color: {raw}')
            return None
        rgb = [int(raw[i:i+2],16)/255 for i in (0,2,4)]
        alpha = 1.0
    elif kind == 'scrgbClr':
        rgb = [float(attrs.get(c,0))/100000 for c in ('r','g','b')]
        alpha = 1.0
    else:
        warnings.append(f'Unsupported source color: {kind}')
        return None
    for transform in value.get('transforms',[]):
        t = transform.get('type')
        v = float(transform.get('val',0))/100000
        if t == 'tint': rgb = [c+(1-c)*v for c in rgb]
        elif t == 'shade': rgb = [c*v for c in rgb]
        elif t in {'lumMod','lumOff','satMod','satOff','hueMod','hueOff'}:
            h,l,s = colorsys.rgb_to_hls(*rgb)
            if t == 'lumMod': l *= v
            elif t == 'lumOff': l += v
            elif t == 'satMod': s *= v
            elif t == 'satOff': s += v
            elif t == 'hueMod': h *= v
            elif t == 'hueOff': h += float(transform.get('val',0))/21600000
            rgb = list(colorsys.hls_to_rgb(h%1, max(0,min(1,l)), max(0,min(1,s))))
        elif t == 'alpha': alpha = v
        elif t == 'alphaMod': alpha *= v
        elif t == 'alphaOff': alpha += v
        else:
            warnings.append(f'Unsupported color transform: {t}; color kept in contract only')
            return None
    return rgb, max(0,min(1,alpha))


EAST_ASIAN_SCRIPTS = frozenset({'Hans','Hant','Jpan','Hang'})


def _font_families(slot, theme):
    """Resolve only actual source run-font roles and their referenced theme family."""
    style = slot.get('text_style',{}).get('default',{})
    value = lambda key: style.get(key,{}).get('value')
    def resolve(token, script):
        if not isinstance(token,str) or not token.strip(): return None, None
        if not token.startswith('+'): return token, None
        role = 'major' if token.startswith('+mj-') else 'minor' if token.startswith('+mn-') else None
        family = theme.get('fonts',{}).get(role,{}) if role else {}
        return family.get(script) or None, family.get('scripts',{}) if role else None
    latin, _ = resolve(value('font_latin'),'latin')
    east_asian, ea_scripts = resolve(value('font_ea') or value('font_east_asian'),'ea')
    complex_script, cs_scripts = resolve(value('font_cs'),'cs')
    scripts = {k:v for k,v in (ea_scripts or {}).items() if k in EAST_ASIAN_SCRIPTS and v}
    scripts.update({k:v for k,v in (cs_scripts or {}).items() if k not in EAST_ASIAN_SCRIPTS and v})
    return {'latin':latin, 'east_asian':east_asian, 'complex_script':complex_script,
            'scripts':scripts, 'source_language':value('language')}


def _text_attrs(slot, theme, cmap, warnings):
    style = slot.get('text_style',{}).get('default',{})
    value = lambda k: style.get(k,{}).get('value')
    attrs = {'textType':'title' if slot['role'] in TITLE_ROLES else 'caption' if slot['role'] in {'dt','ftr','sldNum'} else 'body'}
    size = value('font_size_pt')
    if size is not None:
        attrs['fontSize'] = number(size)
    # Empty SML scaffolds have no language yet and accept one family. The
    # external font map retains EA/CS/theme-script roles for later visible runs.
    font = _font_families(slot,theme)['latin']
    if value('font_latin') and not font:
        warnings.append(f'Unresolved theme font: {value("font_latin")}')
    if font:
        attrs['fontFamily'] = font
    for prop in ('bold','italic'):
        if value(prop) is not None: attrs[prop] = 'true' if value(prop) else 'false'
    align = {'l':'left','ctr':'center','r':'right','just':'justify','dist':'dist'}.get(value('paragraph_algn'))
    if align: attrs['textAlign'] = align
    anchor = slot.get('text_style',{}).get('body_properties',{}).get('anchor',{}).get('value')
    if anchor in {'t','ctr','b'}: attrs['verticalAlign'] = {'t':'top','ctr':'middle','b':'bottom'}[anchor]
    resolved = _resolved_color(value('color'), theme, cmap, warnings)
    if resolved:
        rgb, alpha = resolved
        channels = ','.join(str(round(max(0,min(1,c))*255)) for c in rgb)
        attrs['color'] = f'rgb({channels})' if alpha == 1 else f'rgba({channels},{number(alpha)})'
    return attrs


def _color_validation(value, theme, cmap):
    """Only untransformed explicit RGB paths justify new subtitle hard checks."""
    if not isinstance(value,dict): return {'mode':'warning','reason':'unresolved_source_color'}
    if value.get('transforms'): return {'mode':'warning','reason':'transformed_source_color'}
    if value.get('type') == 'schemeClr':
        token = value.get('value')
        base = theme.get('colors',{}).get(cmap.get(token,token))
        # A scheme cannot recursively reference itself in a valid clrScheme.
        if not isinstance(base,dict) or base.get('type') == 'schemeClr':
            return {'mode':'warning','reason':'unresolved_source_color'}
        return _color_validation(base,theme,{})
    if value.get('type') == 'srgbClr' and re.fullmatch('[0-9a-fA-F]{6}',str(value.get('value',''))):
        return {'mode':'exact'}
    return {'mode':'warning','reason':'uncertain_source_color'}


def build_layout_contract(manifest, layout_name, *, free_regions=None, instance_id=None):
    """Build deterministic JSON from a schema_version=1 layout manifest, without IO."""
    if manifest.get('schema_version') != 1:
        raise ValueError('Unsupported layout manifest schema_version')
    canvas = manifest.get('canvas_sml',{})
    if not valid_bbox({'x':0,'y':0,**canvas}):
        raise ValueError('Manifest is missing a positive SML canvas')
    layout = select_layout(manifest,layout_name)
    warnings = []
    master = next((m for m in manifest.get('masters',[]) if m.get('source_file') == layout.get('master_file')), {})
    theme = next((t for t in manifest.get('themes',[]) if t.get('source_file') == master.get('theme_file')), {})
    cmap = layout.get('color_map_override') or master.get('color_map',{})
    source_sha = manifest.get('source_sha256')
    if source_sha is not None and not re.fullmatch('[0-9a-fA-F]{64}',source_sha):
        raise ValueError('Invalid source_sha256 in manifest')
    manifest_sha = fingerprint(manifest)
    if source_sha is None: warnings.append('Legacy manifest has no PPTX source hash; source_hash identifies manifest JSON')
    contract = {'schema_version':1, 'contract_type':'template_layout',
                'source_pptx':manifest.get('source_pptx'), 'source_sha256':source_sha,
                'source_hash':{'algorithm':'sha256','kind':'pptx' if source_sha else 'manifest','value':source_sha or manifest_sha},
                'manifest_sha256':manifest_sha, 'canvas_sml':copy.deepcopy(canvas),
                'layout':{k:layout.get(k) for k in ('name','type','source_file','master_file')},
                'instance_id':instance_id, 'slots':[], 'free_area_policy':'explicit_regions_only', 'warnings':warnings}
    for ordinal, slot in enumerate(layout.get('placeholders',[])):
        if not valid_bbox(slot.get('bbox')):
            raise ValueError(f'Unresolved placeholder bbox: {layout_name} role={slot.get("role")} id={slot.get("id")}')
        role = slot['role']
        identity = [layout.get('source_file'),slot.get('id'),slot.get('idx'),role,ordinal,instance_id]
        contract['slots'].append({'slot_id':'lc_'+fingerprint(identity)[:20], 'role':role,
            'source_placeholder_id':slot.get('id'), 'source_placeholder_idx':slot.get('idx'),
            'bbox':copy.deepcopy(slot['bbox']), 'bbox_source':copy.deepcopy(slot.get('bbox_source')),
            'required':role in TITLE_ROLES, 'geometry':'exact' if role in TITLE_ROLES else 'contain',
            'allowed_kinds':ROLE_KINDS.get(role,[]), 'text_style':copy.deepcopy(slot.get('text_style',{})),
            'sml_text_style':_text_attrs(slot,theme,cmap,warnings),
            'sml_font_families':_font_families(slot,theme)})
        if role == 'subTitle':
            contract['slots'][-1]['color_validation'] = _color_validation(
                slot.get('text_style',{}).get('default',{}).get('color',{}).get('value'),theme,cmap)
    for ordinal, region in enumerate(free_regions or []):
        if not isinstance(region.get('name'),str) or not region['name'] or not valid_bbox(region.get('bbox')):
            raise ValueError('Each free region requires a nonempty name and positive finite bbox')
        kinds = region.get('allowed_kinds', sorted(KINDS))
        if not isinstance(kinds,list) or not kinds or not set(kinds) <= KINDS:
            raise ValueError(f'Invalid allowed_kinds for free region {region["name"]}')
        if not _contains({'x':0,'y':0,'width':canvas['width'],'height':canvas['height']},region['bbox'],0):
            raise ValueError(f'Free region outside canvas: {region["name"]}')
        contract['slots'].append({'slot_id':'lc_'+fingerprint([layout.get('source_file'),'free',region['name'],ordinal,instance_id])[:20],
            'role':'free', 'name':region['name'], 'bbox':copy.deepcopy(region['bbox']), 'bbox_source':{'level':'explicit'},
            'required':bool(region.get('required',False)), 'geometry':'contain', 'allowed_kinds':list(kinds),
            'text_style':{}, 'sml_text_style':{'textType':'body'}})
    return contract


def generate_skeleton(contract):
    """Generate exact native text boxes. Replace nontext slot boxes with real content."""
    if contract.get('contract_type') != 'template_layout' or contract.get('schema_version') != 1:
        raise ValueError('Unsupported layout contract')
    root = ET.Element('slide', {'xmlns':SML_NS})
    data = ET.SubElement(root,'data')
    for slot in contract['slots']:
        if not valid_bbox(slot.get('bbox')): raise ValueError(f'Invalid slot bbox: {slot.get("slot_id")}')
        attrs = {'id':slot['slot_id'], 'type':'text'}
        attrs.update({attr:number(slot['bbox'][key]) for key,attr in zip(BBOX_KEYS,SML_BBOX)})
        node = ET.SubElement(data,'shape',attrs)
        content = ET.SubElement(node,'content',slot.get('sml_text_style',{}))
        ET.SubElement(content,'p')
    ET.indent(root,space='  ')
    return ET.tostring(root,encoding='unicode')+'\n'


def _contains(outer, inner, tolerance):
    return (inner['x'] >= outer['x']-tolerance and inner['y'] >= outer['y']-tolerance and
            inner['x']+inner['width'] <= outer['x']+outer['width']+tolerance and
            inner['y']+inner['height'] <= outer['y']+outer['height']+tolerance)


def _element_kind(node):
    tag = local(node.tag)
    if tag in {'chart','table','img','embed'}: return tag
    if tag == 'shape':
        content = next((c for c in node if local(c.tag) == 'content'),None)
        if content is not None and (''.join(content.itertext()).strip() or
                any(local(e.tag) in {'formula','field'} for e in content.iter())): return 'text'
    return None


TITLE_STYLE_KEYS = ('fontSize','fontFamily','color','bold','italic','textAlign','verticalAlign')


def _style_value(key, value):
    """Normalize native spelling without changing a visual role."""
    if value is None: return None
    value=str(value).strip()
    if key == 'fontSize':
        try:
            size=float(value)
            return size if math.isfinite(size) else value
        except ValueError: return value
    if key == 'color':
        if re.fullmatch(r'#[0-9a-fA-F]{6}',value):
            return tuple(int(value[i:i+2],16) for i in (1,3,5))+(1.,)
        match=re.fullmatch(r'rgba?\(([^)]+)\)',value,re.I)
        if match:
            try:
                channels=[float(v.strip()) for v in match.group(1).split(',')]
                if len(channels) == 3: channels.append(1.)
                if len(channels) == 4: return tuple(round(v,6) for v in channels)
            except ValueError: pass
        if value.lower() in {'black','white'}:
            return (0.,0.,0.,1.) if value.lower()=='black' else (255.,255.,255.,1.)
    if key in ('bold','italic'):
        return value.lower() in {'true','1','yes'}
    return value.casefold()


def _visible_title_styles(node):
    """Rendered text fragments plus inherited style; unused defaults do not count."""
    content=next((c for c in node if local(c.tag)=='content'),None)
    if content is None: return []
    styles=[]
    def visit(item,inherited):
        style={**inherited,**{k:item.get(k) for k in TITLE_STYLE_KEYS if item.get(k) is not None}}
        if local(item.tag) == 'strong': style['bold']='true'
        if local(item.tag) in {'em','i'}: style['italic']='true'
        if item.text and item.text.strip(): styles.append({**style,'_text':item.text})
        for child in item:
            visit(child,style)
            if child.tail and child.tail.strip(): styles.append({**style,'_text':child.tail})
    visit(content,{})
    return styles


def _text_script(text, context, language):
    """Use visible characters; Han alone cannot identify simplified/traditional."""
    points = [ord(c) for c in text]
    if any(0x3040 <= c <= 0x30ff or 0x31f0 <= c <= 0x31ff or 0xff66 <= c <= 0xff9d for c in points): return 'Jpan'
    if any(0x1100 <= c <= 0x11ff or 0x3130 <= c <= 0x318f or 0xac00 <= c <= 0xd7af for c in points): return 'Hang'
    if any(0x3100 <= c <= 0x312f for c in points): return 'Hant'
    if any(0x3400 <= c <= 0x4dbf or 0x4e00 <= c <= 0x9fff or 0xf900 <= c <= 0xfaff or 0x20000 <= c <= 0x323af for c in points):
        # Kana/Hangul elsewhere in the same title disambiguates Han-only runs.
        anchor = _text_script(context,'',None) if context != text else 'Han'
        if anchor in {'Jpan','Hang'}: return anchor
        language = (language or '').casefold()
        if language.startswith('ja'): return 'Jpan'
        if language.startswith('ko'): return 'Hang'
        if language.startswith(('zh-tw','zh-hk','zh-mo','zh-hant')): return 'Hant'
        if language.startswith(('zh-cn','zh-sg','zh-hans')): return 'Hans'
        return 'Han'
    # These scripts map to real OOXML theme font keys, never local font choices.
    prefixes = {'ARABIC':'Arab','HEBREW':'Hebr','THAI':'Thai','DEVANAGARI':'Deva',
                'BENGALI':'Beng','GUJARATI':'Gujr','GURMUKHI':'Guru','TAMIL':'Taml',
                'TELUGU':'Telu','KANNADA':'Knda','MALAYALAM':'Mlym','SINHALA':'Sinh',
                'KHMER':'Khmr','LAO':'Laoo','TIBETAN':'Tibt','SYRIAC':'Syrc'}
    for c in text:
        if c.isalpha():
            name = unicodedata.name(c,'')
            for prefix,script in prefixes.items():
                if name.startswith(prefix): return script
            return 'Latn'
    return _text_script(context,'',language) if context and context != text else 'Latn'


def _expected_fonts(text, context, families):
    if text and not any(c.isalpha() for c in text):
        # Common digits/punctuation may keep source Latin even next to CJK.
        # They may also inherit the title's actual source script family.
        _,context_fonts=_expected_fonts(context,context,families) if any(c.isalpha() for c in context) else ('Latn',[families.get('latin')])
        return 'Common',list(dict.fromkeys(f for f in [families.get('latin'),*context_fonts] if f))
    script = _text_script(text,context,families.get('source_language'))
    scripts = families.get('scripts',{})
    if script == 'Latn': candidates = [families.get('latin')]
    elif script in EAST_ASIAN_SCRIPTS or script == 'Han':
        if families.get('east_asian'): candidates = [families['east_asian']]
        elif script == 'Han': candidates = [scripts.get('Hans'),scripts.get('Hant')]
        else: candidates = [scripts.get(script)]
    else: candidates = [families.get('complex_script') or scripts.get(script)]
    return script, list(dict.fromkeys(f for f in candidates if f))


def _check_text_style(node, slot, replacement, selector, fail, warnings):
    """Validate visible placeholder text; source defaults never mask run overrides."""
    title = slot['role'] in TITLE_ROLES
    slot_id = slot['slot_id']
    code = 'title_style_mismatch' if title else 'slot_text_style_mismatch'
    label = 'Title' if title else f'Source {slot["role"]} text'
    visible = _visible_title_styles(node)
    context = ''.join(style['_text'] for style in visible)
    expected_style = dict(slot.get('sml_text_style',{}))
    families = slot.get('sml_font_families') or _font_families(slot,{})
    # Legacy contracts may contain resolved Latin even when raw font is a token.
    if not families.get('latin') and expected_style.get('fontFamily'):
        families = {**families,'latin':expected_style['fontFamily']}
    font_errors = []
    unresolved = set()
    substitution_used = False
    for style in visible:
        script,candidates = _expected_fonts(style['_text'],context,families)
        actual = style.get('fontFamily')
        if any(_style_value('fontFamily',actual) == _style_value('fontFamily',family) for family in candidates):
            continue
        if (isinstance(replacement,dict) and replacement.get('reason') and
                _style_value('fontFamily',actual) == _style_value('fontFamily',replacement.get('fontFamily'))):
            substitution_used = True
        elif candidates:
            font_errors.append({'script':script,'expected':candidates,'actual':actual})
        else: unresolved.add(script)
    if font_errors:
        fail(code,f'{label} font must inherit the source font for its visible script',
             element=selector,slot_id=slot_id,role=slot['role'],property='fontFamily',runs=font_errors,
             expected=list(dict.fromkeys(f for e in font_errors for f in e['expected'])),
             actual=list(dict.fromkeys(e['actual'] for e in font_errors)),
             hint='Use the source Latin/EA/theme-script family. Only unavailable source fonts need a reasoned font_substitutions declaration.')
    if substitution_used:
        warnings.append({'code':'declared_title_font_substitution' if title else 'declared_text_font_substitution',
                         'slot_id':slot_id,**replacement})
    for script in sorted(unresolved):
        warnings.append({'code':'unresolved_source_title_font' if title else 'unresolved_source_text_font',
                         'slot_id':slot_id,'script':script,
                         'message':'Source metadata does not resolve this script family; no machine-local font was guessed.'})
    color_policy = None
    if not title:
        color_policy = slot.get('color_validation')
        if color_policy is None:
            raw_style = slot.get('text_style',{}).get('default',{})
            color_policy = _color_validation(raw_style.get('color',{}).get('value'),{}, {})
        if color_policy.get('mode') != 'exact':
            warnings.append({'code':'uncertain_source_text_color','slot_id':slot_id,
                             'reason':color_policy.get('reason','unresolved_source_color'),
                             'message':'Computed source RGB is advisory; transformed or uncertain colors need renderer evidence.'})
    for key in TITLE_STYLE_KEYS:
        if key == 'fontFamily': continue
        if key not in expected_style: continue
        if key == 'color' and not title and color_policy.get('mode') != 'exact': continue
        expected = _style_value(key,expected_style[key])
        actuals = [style.get(key) for style in visible]
        if any(_style_value(key,value) != expected for value in actuals):
            fail(code,'Title must inherit its source role, not the new-deck default' if title else f'{label} must inherit its resolved source role',
                 element=selector,slot_id=slot_id,role=slot['role'],property=key,expected=expected_style[key],
                 actual=list(dict.fromkeys(actuals)),
                 hint='Keep source title size/color/alignment; shorten the heading to fit. Declare an unavailable-font replacement in bindings.font_substitutions.' if title else 'Keep resolved source size/weight/alignment. Shorten the text to fit; leave optional unknown content empty.')


def validate_layout_contract(sml, contract, *, manifest=None, bindings=None, tolerance=0.5):
    """Validate one selected slide; returns errors, never mutates any input or source."""
    errors = []
    warnings = []
    result = {'ok':False,'errors':errors,'warnings':warnings,'checked_elements':0}
    def fail(code, message, **details):
        errors.append({'code':code,'message':message,**details})
    if not isinstance(tolerance,(int,float)) or not math.isfinite(tolerance) or tolerance < 0:
        fail('invalid_tolerance','Tolerance must be a finite nonnegative pixel value')
        return result
    if (not isinstance(contract,dict) or contract.get('schema_version') != 1 or
            contract.get('contract_type') != 'template_layout'):
        fail('invalid_contract','Unsupported layout contract')
        return result
    layout = contract.get('layout')
    slot_rows = contract.get('slots')
    if not isinstance(layout,dict) or not isinstance(slot_rows,list):
        fail('invalid_contract','Contract requires a layout object and a slots array')
        return result
    for slot in slot_rows:
        if (not isinstance(slot,dict) or not isinstance(slot.get('slot_id'),str) or
                not slot['slot_id'] or not isinstance(slot.get('role'),str) or
                not valid_bbox(slot.get('bbox')) or not isinstance(slot.get('allowed_kinds',[]),list) or
                not isinstance(slot.get('sml_font_families',{}),dict) or
                ('color_validation' in slot and (not isinstance(slot['color_validation'],dict) or
                 slot['color_validation'].get('mode') not in ('exact','warning')))):
            fail('invalid_contract','Each slot requires an ID, role, positive bbox and accepted-kind array')
            return result
    if not layout.get('name') or not layout.get('source_file'):
        fail('invalid_layout','Contract requires a named source layout')
    if manifest is not None:
        try:
            select_layout(manifest,layout.get('name'),layout.get('source_file'))
        except ValueError as error: fail('invalid_layout',str(error))
        if contract.get('manifest_sha256') != fingerprint(manifest):
            fail('manifest_mismatch','Contract does not identify the supplied layout manifest')
        # The manifest fingerprint alone is insufficient: an accidentally edited
        # contract must not redefine a real source title as a wider free region.
        try:
            regions = [{k:slot.get(k) for k in ('name','bbox','allowed_kinds','required')}
                       for slot in contract.get('slots',[]) if slot.get('role') == 'free']
            expected_contract = build_layout_contract(manifest,layout.get('name'),
                free_regions=regions,instance_id=contract.get('instance_id'))
            keys = ('slot_id','role','source_placeholder_id','source_placeholder_idx','bbox',
                    'required','geometry','allowed_kinds','text_style','sml_text_style','sml_font_families')
            # New derived evidence is checked when present; old frozen contracts
            # can still be compared with their original raw source metadata.
            keys += tuple(k for k in ('color_validation',)
                          if any(k in s for s in contract.get('slots',[])))
            source_slots = [{k:s.get(k) for k in keys} for s in expected_contract['slots']]
            actual_slots = [{k:s.get(k) for k in keys} for s in contract.get('slots',[])]
            if source_slots != actual_slots or expected_contract['layout'] != layout:
                fail('source_slot_mismatch','Contract slots or layout differ from the selected source manifest')
        except (ValueError,KeyError,TypeError) as error:
            fail('source_slot_mismatch',f'Cannot resolve contract slots from source manifest: {error}')
    slots = {}
    for slot in contract.get('slots',[]):
        if not slot.get('slot_id') or slot['slot_id'] in slots or not valid_bbox(slot.get('bbox')):
            fail('invalid_contract','Duplicate slot ID or invalid slot bbox')
            continue
        slots[slot['slot_id']] = slot
    try:
        if isinstance(sml,ET.Element): root = sml
        else:
            if re.search(r'<!\s*(DOCTYPE|ENTITY)\b',sml.decode() if isinstance(sml,bytes) else sml,re.I):
                raise ValueError('DTD/entity declarations are unsupported')
            root = ET.fromstring(sml)
    except (ET.ParseError,ValueError,TypeError) as error:
        fail('invalid_sml',str(error))
        return result
    if local(root.tag) != 'slide':
        fail('invalid_sml','Layout validation accepts exactly one <slide>')
        return result
    data = next((c for c in root if local(c.tag)=='data'),None)
    nodes = list(data) if data is not None else []
    binding_data = {} if bindings is None else bindings
    if not isinstance(binding_data,dict):
        fail('invalid_bindings','Bindings must be an object containing element selectors')
        return result
    elements = binding_data.get('elements',{})
    decorative_ids = binding_data.get('decorative_ids',[])
    if (not isinstance(elements,dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in elements.items()) or
            not isinstance(decorative_ids,list) or not all(isinstance(i,str) for i in decorative_ids)):
        fail('invalid_bindings','bindings.elements must map element selectors to slot IDs')
        return result
    decorative = set(decorative_ids)
    substitutions=binding_data.get('font_substitutions',{})
    if not isinstance(substitutions,dict):
        fail('invalid_font_substitution','font_substitutions must be a slot-to-font object')
        return result
    for slot_id,entry in substitutions.items():
        if (slot_id not in slots or not isinstance(entry,dict) or not isinstance(entry.get('fontFamily'),str)
                or not entry['fontFamily'].strip() or not isinstance(entry.get('reason'),str) or not entry['reason'].strip()):
            fail('invalid_font_substitution','Font fallback requires a real slot, replacement family and unavailable-font reason',slot_id=slot_id)
    identities = set()
    seen_selectors = set()
    bound = {key:[] for key in slots}
    for index,node in enumerate(nodes):
        kind = _element_kind(node)
        identifier = node.get('id')
        index_selector = f'data_index:{index}'
        selector = identifier or index_selector
        if identifier:
            if identifier in identities: fail('duplicate_element_id',f'Duplicate native ID: {identifier}',element=selector)
            identities.add(identifier)
        seen_selectors.add(index_selector)
        if identifier: seen_selectors.add(identifier)
        if selector in decorative or index_selector in decorative:
            if kind in {'text','chart','table'}:
                fail('invalid_decorative_binding',f'{kind} content cannot be excluded as decoration',element=selector)
            else: continue
        if kind is None: continue
        slot_id = elements.get(identifier, elements.get(index_selector)) if identifier else elements.get(index_selector)
        if slot_id is None and identifier in slots: slot_id = identifier
        if slot_id not in slots:
            fail('unknown_slot_binding' if slot_id is not None else 'unbound_content',
                 'Bind semantic content to a requested layout slot',element=selector,kind=kind,slot_id=slot_id)
            continue
        slot = slots[slot_id]
        bound[slot_id].append(kind)
        result['checked_elements'] += 1
        if kind not in slot.get('allowed_kinds',[]):
            fail('slot_kind_mismatch',f'{kind} is not accepted by {slot["role"]} slot',element=selector,slot_id=slot_id)
        if slot['role'] in TEXT_STYLE_ROLES and kind == 'text':
            _check_text_style(node,slot,substitutions.get(slot_id),selector,fail,warnings)
        try:
            bbox = {key:float(node.get(attr)) for key,attr in zip(BBOX_KEYS,SML_BBOX)}
        except (TypeError,ValueError): bbox = None
        if not valid_bbox(bbox):
            fail('missing_element_bbox','Bound content needs a positive finite bbox',element=selector,slot_id=slot_id)
            continue
        expected = slot['bbox']
        if slot.get('geometry') == 'exact' and any(abs(bbox[k]-expected[k]) > tolerance for k in BBOX_KEYS):
            fail('title_bbox_mismatch' if slot['role'] in TITLE_ROLES else 'slot_bbox_mismatch',
                 'Bound element must retain the exact source slot bbox',element=selector,slot_id=slot_id,expected=expected,actual=bbox)
        if not _contains(expected,bbox,tolerance):
            fail('outside_slot_bbox','Bound content extends beyond its requested slot',element=selector,slot_id=slot_id,expected=expected,actual=bbox)
        try:
            rotation = float(node.get('rotation','0'))
        except (TypeError,ValueError): rotation = math.nan
        if not math.isfinite(rotation):
            fail('invalid_element_rotation','Element rotation must be finite',element=selector,slot_id=slot_id)
        elif rotation % 360:
            fail('rotated_slot_content','Rotated slot content requires a separate explicit region',element=selector,slot_id=slot_id)
    for selector in elements:
        if selector not in seen_selectors: fail('missing_bound_element','Binding references no authored element',element=selector)
    for slot_id,slot in slots.items():
        if slot.get('required') and not bound[slot_id]:
            fail('missing_title_binding' if slot['role'] in TITLE_ROLES else 'missing_slot_binding',
                 f'Required {slot["role"]} slot has no nonempty authored content',slot_id=slot_id)
        if slot['role'] in TITLE_ROLES and len(bound[slot_id]) > 1:
            fail('multiple_title_bindings','A title slot accepts exactly one text box',slot_id=slot_id)
    result['ok'] = not errors
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--layout')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--skeleton',type=Path)
    parser.add_argument('--free-regions',type=Path)
    parser.add_argument('--instance-id')
    parser.add_argument('--contract',type=Path)
    parser.add_argument('--sml',type=Path)
    parser.add_argument('--bindings',type=Path)
    args = parser.parse_args(argv)
    try:
        read_json = lambda p: json.loads(p.read_text(encoding='utf-8'))
        if args.contract or args.sml:
            if not args.contract or not args.sml: raise ValueError('--contract and --sml are required together')
            result = validate_layout_contract(args.sml.read_text(encoding='utf-8'),read_json(args.contract),
                manifest=read_json(args.manifest) if args.manifest else None,
                bindings=read_json(args.bindings) if args.bindings else None)
            print(json.dumps(result,ensure_ascii=False))
            return 0 if result['ok'] else 1
        if not args.manifest or not args.layout or not args.output:
            raise ValueError('Generation requires --manifest, --layout and --output')
        outputs = [args.output] + ([args.skeleton] if args.skeleton else [])
        if len({p.resolve() for p in outputs}) != len(outputs): raise ValueError('Output paths must be distinct')
        for path in outputs:
            if path.exists() or path.is_symlink(): raise FileExistsError(f'Output already exists: {path}')
        contract = build_layout_contract(read_json(args.manifest),args.layout,
            free_regions=read_json(args.free_regions) if args.free_regions else None,instance_id=args.instance_id)
        encoded = json.dumps(contract,ensure_ascii=False,indent=2)+'\n'
        skeleton = generate_skeleton(contract) if args.skeleton else None
        created = []
        try:
            with ExitStack() as stack:
                streams = []
                for path in outputs:
                    streams.append(stack.enter_context(path.open('x',encoding='utf-8')))
                    created.append(path)
                for stream,payload in zip(streams,[encoded,skeleton]): stream.write(payload)
        except OSError:
            for path in created: path.unlink(missing_ok=True)
            raise
        print(json.dumps({'ok':True,'output':str(args.output.resolve()),'skeleton':str(args.skeleton.resolve()) if args.skeleton else None,'slots':len(contract['slots'])}))
        return 0
    except (OSError,ValueError,KeyError,TypeError) as error:
        print(f'template_layout_contract: {error}',file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
