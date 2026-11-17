"""Deterministic role extraction and OKLCH derivation; original CSS stays unchanged."""
import math
import re

VERSION = 'oklch-relative-1.1'

def rgb(hex_color):
    if not isinstance(hex_color,str) or not re.fullmatch(r'#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})',hex_color):
        raise ValueError('需要 #RGB 或 #RRGGBB 色值')
    s = hex_color[1:]
    if len(s) == 3:
        s = ''.join(x * 2 for x in s)
    if not re.fullmatch(r'[0-9a-fA-F]{6}', s):
        raise ValueError('需要 #RGB 或 #RRGGBB 色值')
    return [int(s[i:i+2], 16) / 255 for i in (0, 2, 4)]

def hex_rgb(values):
    return '#' + ''.join(f'{round(max(0, min(1, v)) * 255):02X}' for v in values)

def linear(v):
    return v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4

def gamma(v):
    return 12.92 * v if v <= .0031308 else 1.055 * max(v, 0) ** (1 / 2.4) - .055

def to_lch(color):
    r, g, b = [linear(x) for x in rgb(color)]
    l = (.4122214708*r + .5363325363*g + .0514459929*b) ** (1/3)
    m = (.2119034982*r + .6806995451*g + .1073969566*b) ** (1/3)
    s = (.0883024619*r + .2817188376*g + .6299787005*b) ** (1/3)
    L = .2104542553*l + .7936177850*m - .0040720468*s
    a = 1.9779984951*l - 2.4285922050*m + .4505937099*s
    b = .0259040371*l + .7827717662*m - .8086757660*s
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360

def lch_linear(L, C, H):
    a, b = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
    l, m, s = (L + .3963377774*a + .2158037573*b)**3, (L - .1055613458*a - .0638541728*b)**3, (L - .0894841775*a - 1.2914855480*b)**3
    return [4.0767416621*l - 3.3077115913*m + .2309699292*s,
            -1.2684380046*l + 2.6097574011*m - .3413193965*s,
            -.0041960863*l - .7034186147*m + 1.7076147010*s]

def from_lch(L, C, H):
    L = max(0, min(1, L))
    values = lch_linear(L, C, H)
    if any(v < -1e-7 or v > 1 + 1e-7 for v in values):
        low, high = 0, C
        for _ in range(24):
            middle = (low + high) / 2
            test = lch_linear(L, middle, H)
            if all(-1e-7 <= v <= 1+1e-7 for v in test):
                low = middle
            else:
                high = middle
        values = lch_linear(L, low, H)
    return hex_rgb([gamma(x) for x in values])

def contrast(a, b):
    def luminance(color):
        r, g, b = [linear(v) for v in rgb(color)]
        return .2126*r + .7152*g + .0722*b
    x, y = sorted([luminance(a), luminance(b)])
    return (y + .05) / (x + .05)

def extract(text):
    colors = []
    pattern = r'(--[\w-]+)\s*:\s*(#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3}))(?=\s*(?:;|}|$|/\*))\s*;?\s*(?:/\*([^*]*)\*/)?'
    for match in re.finditer(pattern, text):
        variable, color, label = match.groups()
        try:
            color = hex_rgb(rgb(color))
        except ValueError:
            continue
        label = (label or '').strip()
        if not label:
            label = {'--paper':'页面底色', '--ink':'正文', '--white':'反白文字', '--accent':'强调色', '--accent-soft':'浅强调底', '--muted':'辅助文字', '--rule':'分隔线', '--fine':'次级文字', '--green':'绿色点缀', '--wine':'酒红点缀', '--olive':'环境深色', '--taupe':'卡片中性色', '--ochre':'环境暖色'}.get(variable, variable)
        roles = []
        for role, expression in [('background', r'背景|大底|底色|纸面|留白'), ('text', r'正文|文字|文案|字标|书法|标题'), ('accent', r'强调|点缀|印章|标识'), ('surface', r'卡片|底条|底板|纸张|承载'), ('muted', r'辅助文字|次级|细线|分隔')]:
            if re.search(expression, label): roles.append(role)
        area = re.search(r'area≈([\d.]+)', label)
        colors.append({'variable':variable, 'color':color, 'label':label,
                       'roles':roles, 'evidence':'source-comment' if match.group(3) else 'semantic-variable',
                       'area':float(area.group(1)) if area else None})
    return colors

def select_roles(colors, override=None):
    background_candidates = [c for c in colors if 'background' in c['roles']]
    background = next((c for c in colors if c['variable']=='--paper'), None) or (background_candidates[0] if background_candidates else max(colors, key=lambda c:to_lch(c['color'])[0]))
    chromatic = [c for c in colors if to_lch(c['color'])[1] >= .035]
    anchor = next((c for c in colors if c['variable']=='--accent'), None)
    if not anchor:
        # Prefer a substantial chromatic area; source photo area is not a prescribed page ratio.
        anchor = max(chromatic or colors, key=lambda c:(c['area'] or .01) * min(to_lch(c['color'])[1], .2))
    text_candidates = [c for c in colors if 'text' in c['roles']]
    text = max(text_candidates or colors, key=lambda c:contrast(c['color'], background['color']))
    surfaces = [c for c in colors if c is not background and ('surface' in c['roles'] or 'background' in c['roles'])]
    surface = min(surfaces or [background], key=lambda c:abs(to_lch(c['color'])[0]-to_lch(background['color'])[0]))
    mapping={'background':background['variable'], 'surface':surface['variable'],
             'text':text['variable'], 'accent':anchor['variable']}
    by_variable={c['variable']:c for c in colors}
    if override:
        for role in ['background','surface','text','accent','on_surface']:
            if role in override:
                if override[role] not in by_variable:raise ValueError('角色引用未知变量：'+role)
                mapping[role]=override[role]
        anchor=by_variable[mapping['accent']]
    if mapping['accent']==mapping['background']:
        candidates=[c for c in colors if c['variable']!=mapping['background']]
        if candidates:
            anchor=max(candidates,key=lambda c:contrast(c['color'],by_variable[mapping['background']]['color']))
            mapping['accent']=anchor['variable']
    if 'on_surface' not in mapping:
        mapping['on_surface']=max(colors,key=lambda c:contrast(c['color'],by_variable[mapping['surface']]['color']))['variable']
    return mapping,anchor

def accessible_text(proposed, background, target=4.5):
    if not isinstance(target,(int,float)) or not math.isfinite(target) or target<1 or target>21:
        raise ValueError('对比度目标必须在1到21之间')
    extremes=['#000000','#FFFFFF']
    if max(contrast(c,background) for c in extremes)<target:
        raise ValueError('当前底色无法达到指定对比度')
    if contrast(proposed, background) >= target:
        return proposed
    L, C, H = to_lch(proposed)
    options = [from_lch(i/100, C, H) for i in range(101)]
    allowed = [c for c in options if contrast(c, background) >= target]
    return min(allowed, key=lambda c:abs(to_lch(c)[0]-L)) if allowed else max(extremes,key=lambda c:contrast(c,background))

def derive(name, colors, target='#8A4DB0', mode='preserve', role_override=None):
    if not colors:
        raise ValueError('配色文件中没有有效色值')
    if mode not in ('preserve','exact'):
        raise ValueError('未知换色模式')
    target = hex_rgb(rgb(target))
    mapping, anchor = select_roles(colors,role_override)
    oldL, oldC, oldH = to_lch(anchor['color'])
    newL, newC, newH = to_lch(target)
    neutral_target = newC < .015
    chromatic = [c for c in colors if to_lch(c['color'])[1]>=.018]
    reference = anchor if oldC>=.018 else max(chromatic,key=lambda c:to_lch(c['color'])[1]) if chromatic else None
    delta = newH-to_lch(reference['color'])[2] if reference and not neutral_target else 0
    derived = []
    for c in colors:
        L,C,H = to_lch(c['color'])
        if c['variable']==anchor['variable'] and mode=='exact':
            color = target
        elif C < .018 or (mode=='preserve' and neutral_target):
            color = c['color']
        else:
            # preserve: keep original L/C; exact: shift chromatic relatives while preserving neutrals.
            lightness = L if mode=='preserve' else max(.03,min(.98,L+(newL-oldL)*min(1,C/max(oldC,.01))))
            chroma = C if mode=='preserve' else C*min(2,max(.25,newC/max(oldC,.01)))
            if neutral_target: chroma = 0
            color = from_lch(lightness, chroma, H+delta)
        derived.append({**c, 'color':color})
    values = {c['variable']:c['color'] for c in derived}
    roles = {k:values[v] for k,v in mapping.items()}
    roles['accentSource']=roles['accent']
    # A filled emphasis block is a consumer role; keep source palette tokens intact.
    if mode=='preserve':roles['accent']=accessible_text(roles['accent'],roles['background'],3)
    proposed_text = roles['text']
    roles['text'] = accessible_text(roles['text'], roles['background'])
    roles['onSurface']=accessible_text(roles.pop('on_surface'),roles['surface'])
    roles['onAccent'] = accessible_text(roles['text'], roles['accent'])
    roles['accentBorder']=accessible_text(roles['accent'],roles['background'],3)
    L,C,H = to_lch(roles['text'])
    roles['muted'] = accessible_text(from_lch(L + (.12 if L<.5 else -.12), C*.6,H), roles['background'])
    role_prefix='--theme-'
    while any(c['variable'].startswith(role_prefix) for c in colors):
        role_prefix='--review'+role_prefix[1:]
    css = '/* '+VERSION+'; generated theme; original grayscale template is unchanged */\n:root {\n'
    css += '\n'.join('  '+c['variable']+': '+c['color']+';' for c in derived)
    css += '\n'+'\n'.join('  '+role_prefix+re.sub(r'([A-Z])',lambda m:'-'+m[1].lower(),k)+': '+v+';' for k,v in roles.items())+'\n}\n'
    notes = ['角色来自原文件注释与确定性规则，待人工确认。','来源图色面积仅作证据，不强制作为页面应用比例。','灰度页面保持原样；本面板只展示独立配色体系。']
    if neutral_target: notes.append('目标为近中性色：保留气质模式保持原色；精确主色模式才降低彩色角色色度。')
    if reference and reference is not anchor:notes.append('主色锚点为中性色；色相关系改用彩色角色 '+reference['variable']+' 作为参照。')
    if roles['text']!=proposed_text: notes.append('正文角色已单独修正对比度；原编号变量保留派生值。')
    if role_override:notes.append('已应用逐项复核的角色配置：'+role_override.get('reason',''))
    notes.append('背景、承载面和强调块各自配文字；原色板变量不因消费角色的对比修正而改写。')
    reference_lch=to_lch(reference['color']) if reference else None
    parameters=[]
    for color in colors:
        L,C,H=to_lch(color['color'])
        parameters.append({'variable':color['variable'],'L':round(L,7),'C':round(C,7),
                           'h':round(H,4) if C>=.018 else None,
                           'delta_h':round((H-reference_lch[2]+180)%360-180,4) if C>=.018 and reference_lch else None,
                           'delta_L_from_anchor':round(L-oldL,7),
                           'chroma_ratio_to_reference':round(C/reference_lch[1],7) if reference_lch else None,
                           'neutral_locked':C<.018,'role_evidence':color['evidence']})
    return {'name':name,'algorithm':VERSION,'anchor':anchor['variable'],'mode':mode,
            'original':colors,'derived':derived,'role_mapping':mapping,'role_prefix':role_prefix,'hue_reference':reference['variable'] if reference else None,'roles':roles,
            'formula_parameters':parameters,
            'contrast':{'text':round(contrast(roles['text'],roles['background']),2), 'surface':round(contrast(roles['onSurface'],roles['surface']),2),
                        'accent':round(contrast(roles['onAccent'],roles['accent']),2),'accent_boundary':round(contrast(roles['accentBorder'],roles['background']),2)},
            'css':css,'formula':'保留气质：hᵢ′=h目标+(hᵢ−h主色)，保留各色L/C；超出sRGB时降低C。精确主色模式额外调整彩色角色L/C，中性色保留。正文/按钮文字独立校验对比。','notes':notes}
