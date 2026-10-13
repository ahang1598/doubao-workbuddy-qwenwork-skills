"""Load an independent, JSON-serializable rule snapshot; never classify media here."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
RULES_FILE = ROOT / 'assets' / 'rules' / 'rules.md'
SCENARIOS = frozenset({'ecommerce', 'finance', 'automotive'})
ALIASES = {'电商': 'ecommerce', '金融': 'finance', '汽车': 'automotive'}
MODALITIES = frozenset({'speech', 'image'})


def _read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result

    try:
        return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique,
                          parse_constant=lambda value: (_ for _ in ()).throw(
                              ValueError(f'Invalid JSON constant: {value}')))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f'Cannot read rule JSON: {path}: {exc}') from exc


def _validate(rule, seen, custom=False):
    if not isinstance(rule, dict):
        raise ValueError('Each rule must be an object')
    rule = deepcopy(rule)
    for field in ('id', 'name', 'description'):
        if not isinstance(rule.get(field), str) or not rule[field].strip():
            raise ValueError(f'Rule requires nonempty string {field}')
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]*', rule['id']):
        raise ValueError(f'Invalid rule id: {rule["id"]}')
    if rule['id'] in seen:
        raise ValueError(f'Duplicate rule id: {rule["id"]}')
    seen.add(rule['id'])
    for field, allowed in (('scenarios', SCENARIOS), ('modalities', MODALITIES)):
        values = rule.get(field)
        if (not isinstance(values, list) or not values
                or any(not isinstance(v, str) or v not in allowed for v in values)
                or len(values) != len(set(values))):
            raise ValueError(f'{rule["id"]}: {field} must be a nonempty unique list of {sorted(allowed)}')
    rule.setdefault('priority', 'P1')
    if rule['priority'] not in ('P0', 'P1', 'P2'):
        raise ValueError(f'{rule["id"]}: priority must be P0, P1 or P2')
    rule.setdefault('enabled', True)
    if not isinstance(rule['enabled'], bool):
        raise ValueError(f'{rule["id"]}: enabled must be boolean')
    rule.setdefault('kind', 'risk')
    if rule['kind'] not in ('risk', 'visual_router') or (custom and rule['kind'] != 'risk'):
        raise ValueError(f'{rule["id"]}: invalid rule kind')
    if 'examples' in rule and not isinstance(rule['examples'], list):
        raise ValueError(f'{rule["id"]}: examples must be a list')
    if custom:
        # Custom IDs cannot replace another scenario's builtin rules, even when disabled.
        if rule['id'].startswith(('DY_ECOM_', 'FIN_LOCAL_', 'AUTO_LOCAL_')):
            raise ValueError(f'Reserved builtin rule id: {rule["id"]}')
        rule['count_as_risk'] = True
        rule['origin'] = 'custom'
    else:
        if type(rule.get('order')) is not int or rule['order'] < 1:
            raise ValueError(f'{rule["id"]}: builtin order must be a positive integer')
        rule['count_as_risk'] = rule['kind'] == 'risk'
        rule['origin'] = 'builtin'
    return rule


# Stable identities belong to the runtime, not the authored rule document.
RULE_DEFINITIONS = {'通用': [['DY_BASE_001_P0', '内容安全-涉嫌违法违规', 'P0', ['speech', 'image']],
        ['DY_BASE_002_P0', '内容安全-色情低俗', 'P0', ['speech', 'image']],
        ['DY_BASE_003_P0', '内容安全-暴力血腥与危险模仿', 'P0', ['speech', 'image']],
        ['DY_FALSE_001_P1', '虚假宣传-绝对化用语', 'P1', ['speech', 'image']],
        ['DY_FALSE_002_P1', '虚假宣传-虚假功效', 'P1', ['speech', 'image']]],
 '电商': [['DY_ECOM_001_P1', '电商小程序-禁投/禁推品类与高风险商品', 'P1', ['speech', 'image']],
        ['DY_ECOM_004_P1', '直播电商-主播不当承诺', 'P1', ['speech', 'image']]],
 '金融': [['FIN_CORE_001', '投资建议与收益承诺', 'P1', ['speech', 'image']],
        ['FIN_CORE_002', '营销与不当表达', 'P1', ['speech', 'image']],
        ['FIN_CORE_003', '金融业务合规', 'P1', ['speech', 'image']]],
 '汽车': [['AUTO_LOCAL_001', '驾驶辅助的危险能力保证', 'P1', ['speech', 'image']],
        ['AUTO_LOCAL_002', '车辆规格、价格及质保的明确矛盾', 'P1', ['speech', 'image']]]}
BUNDLE_NAMES = {'common': '通用', 'ecommerce': '电商', 'finance': '金融', 'automotive': '汽车'}


def _sections(text, level):
    """Split exact heading levels; reject duplicates instead of silently dropping rules."""
    pattern = re.compile(r'^' + '#' * level + r' ([^\n]+)(?:\n|$)', re.M)
    matches = list(pattern.finditer(text))
    result = {}
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        if title in result:
            raise ValueError(f'Duplicate rule heading: {title}')
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        result[title] = text[match.end():end].strip()
    return text[:matches[0].start()].strip() if matches else text.strip(), result


def _read_builtin():
    text = RULES_FILE.read_text(encoding='utf-8')
    _, groups = _sections(text, 2)
    if set(groups) != {'判定原则', *RULE_DEFINITIONS} or not groups['判定原则']:
        raise ValueError('Rule document requires principles and every builtin group')
    parsed = {}
    for name, definitions in RULE_DEFINITIONS.items():
        introduction, rows = _sections(groups[name], 3)
        if set(rows) != {r[1] for r in definitions} or not all(rows.values()):
            raise ValueError(f'Missing, empty or unknown rule in {name}')
        parsed[name] = (introduction, rows)
    return groups['判定原则'], parsed, hashlib.sha256(text.encode()).hexdigest()


def review_snapshot(snapshot, *, compact=False):
    """Return the immutable model-facing rules without duplicated source views.

    Both views retain the full policy and rule body. The compact argument stays
    compatible with callers; legacy interpretation and evidence requirements
    remain available for frozen snapshots.
    """
    fields = ('id', 'name', 'description', 'modalities', 'priority', 'kind',
              'count_as_risk', 'order', 'full_prompt',
              'interpretation', 'evidence_requirements', 'policy')
    rules = []
    for rule in snapshot['rules']:
        value = {key: deepcopy(rule[key]) for key in fields if key in rule}
        if not value.get('full_prompt'):
            for key in ('conditions', 'exclusions', 'evidence_requirements', 'interpretation'):
                if key in rule:value[key] = deepcopy(rule[key])
        rules.append(value)
    return {'version': snapshot['version'],
            'source_sha256': snapshot.get('source_sha256'),
            'common_rule_ids': deepcopy(snapshot.get('common_rule_ids', [])),
            'policies': deepcopy(snapshot.get('policies', {})),
            'rules': rules}


def load_rules(scenario, custom_path=None):
    """Freeze rules authored in one Markdown file; retain additive custom JSON support."""
    if not isinstance(scenario, str):
        raise ValueError('scenario must be a string')
    scenario = ALIASES.get(scenario, scenario)
    if scenario not in SCENARIOS | {'common'}:
        raise ValueError(f'Unknown scenario: {scenario}')
    principles, groups, source_hash = _read_builtin()
    active, seen = [], set()
    policies = {'common': {'requirements': principles}}
    for bundle in (['common'] if scenario == 'common' else ['common', scenario]):
        name = BUNDLE_NAMES[bundle]
        introduction, rows = groups[name]
        if introduction:
            policies.setdefault(bundle, {})['requirements'] = introduction
        for rule_id, title, priority, modalities in RULE_DEFINITIONS[name]:
            body = rows[title]
            marker = '\n#### 金融内容补充\n'
            base, separator, supplement = body.partition(marker)
            if separator:
                body = base.rstrip()
                if scenario == 'finance':
                    body += marker + supplement
            rule = dict(id=rule_id, name=title, description=title,
                        scenarios=sorted(SCENARIOS) if bundle == 'common' else [bundle],
                        modalities=modalities, priority=priority, order=len(active)+1,
                        full_prompt=body, scope=bundle, policy=bundle)
            if separator and scenario == 'finance':
                # Marker only; supplement text already occurs once in full_prompt.
                rule['active_supplements'] = True
            active.append(_validate(rule, seen))
    if custom_path is not None:
        custom = _read(custom_path)
        if isinstance(custom, dict):
            custom = custom.get('rules')
        if not isinstance(custom, list):
            raise ValueError('Custom JSON must be a rule list or an object with rules list')
        for index, entry in enumerate(custom, len(active)+1):
            rule = _validate(entry, seen, custom=True)
            rule['order'] = index
            if rule['enabled'] and scenario in rule['scenarios']:
                rule['policy'] = 'common'
                active.append(rule)
    canonical = json.dumps({'rules': active, 'policies': policies}, ensure_ascii=False,
                           sort_keys=True, separators=(',', ':'))
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    return {'version': 'markdown-v1-' + digest, 'source_sha256': source_hash,
            'common_rule_ids': [r['id'] for r in active if r.get('scope') == 'common'],
            'policies': policies, 'rules': active}
