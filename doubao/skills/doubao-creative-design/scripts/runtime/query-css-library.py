#!/usr/bin/env python3
"""Metadata search and bounded, anchor-based CSS source retrieval. No model calls."""
import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

def _style_norm(value):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', str(value)).casefold()).strip()


def _style_labels(value):
    # Parent/child paths use '/', including full-width slash after normalization.
    full = '/'.join(part.strip() for part in _style_norm(value).split('/') if part.strip())
    parts = full.split('/') if full else []
    return full, parts, set(parts + ([full] if full else []))


def _affinity_words(affinity):
    _, _, labels = _style_labels(affinity.get('style', ''))
    return labels | {_style_norm(term) for term in affinity.get('terms', []) if _style_norm(term)}


def style_affinity_matches(entry, terms, related, style):
    """Match catalog metadata only; terms must come from Library.query_terms.

    One selected match per parent family, regardless of alias count.
    Related terms are expansion evidence, never exact synonyms.
    'level' describes structural suitability, not evidence strength.
    """
    if isinstance(terms, str):
        raise TypeError('Pass the token list returned by Library.query_terms, not raw query text')
    tokens = list(dict.fromkeys(_style_norm(t) for t in terms if _style_norm(t)))
    explicit = _style_labels(style or '')[0]
    relation = {}
    for source, values in (related or {}).items():
        if isinstance(values, str):
            values = [values]
        relation.setdefault(_style_norm(source), set()).update(_style_norm(v) for v in values)
    selected = {}
    for affinity in entry.get('style_affinities', []):
        canonical, parts, labels = _style_labels(affinity.get('style', ''))
        level = affinity.get('level')
        if not parts or level not in ('strong', 'adaptable'):
            continue
        aliases = _affinity_words(affinity)
        explicit_hit = bool(explicit and explicit in aliases)
        direct = [t for t in tokens if t in aliases]
        pairs = sorted({(t, word) for t in tokens if t not in direct
                        for word in relation.get(t, set()) if word in aliases})
        if not direct and not explicit_hit and not pairs:
            continue
        exact = bool(direct or explicit_hit)
        evidence = list(dict.fromkeys(direct + ([explicit] if explicit_hit else [])))
        if not exact:
            evidence = list(dict.fromkeys(source for source, _ in pairs))
        match = {'style': affinity['style'], 'level': level,
                 'reason': affinity.get('reason', ''), 'matched_terms': evidence}
        # Exact evidence precedes expansion; within that tier strong precedes adaptable.
        key = (0 if exact else 1, 0 if level == 'strong' else 1,
               0 if explicit_hit else 1, canonical)
        candidate = {'key': key, 'match': match, 'exact': exact,
                     'explicit': explicit_hit, 'pairs': [] if exact else pairs}
        family = parts[0]
        previous = selected.get(family)
        if previous is None or key < previous['key']:
            selected[family] = candidate
    chosen = sorted(selected.values(), key=lambda item: item['key'])
    direct_terms = list(dict.fromkeys(t for item in chosen if item['exact']
                                     for t in item['match']['matched_terms'] if t in tokens))
    expansions = [{'from': source, 'term': word}
                  for source, word in sorted({pair for item in chosen for pair in item['pairs']})]
    exact_items = [item for item in chosen if item['exact']]
    priority = min((2 * item['key'][0] + item['key'][1] for item in chosen), default=4)
    score = sum((4 if item['match']['level'] == 'strong' else 2)
                * (1 if item['exact'] else 0.25) for item in chosen)
    return {'style_matches': [item['match'] for item in chosen],
            'related_combinations': list(dict.fromkeys(entry.get('related_combinations', []))),
            'style_score': score, 'style_priority': priority,
            'style_match': any(item['explicit'] for item in chosen),
            'style_stage': 'exact' if exact_items else 'expanded' if chosen else 'weak',
            'matched_terms': direct_terms, 'expanded_matches': expansions}


class BudgetExceeded(ValueError):
    pass

class NodeExtractor(HTMLParser):
    """Exact source slices for a deliberately small, explicit selector grammar."""
    def __init__(self, source, selector):
        super().__init__(convert_charrefs=False)
        match = re.fullmatch(r'([a-zA-Z][\w-]*)(?:\[([\w-]+)(?:=[\"\']?([^\"\']*?)[\"\']?)?\])?', selector)
        if not match:
            raise ValueError('Supported selector: tag, tag[attr], tag[attr="value"]')
        self.tag, self.attr, self.value = match.groups()
        self.source, self.stack, self.matches = source, [], []
        self.offsets = [0]
        for line in source.splitlines(keepends=True): self.offsets.append(self.offsets[-1] + len(line))
    def source_offset(self):
        line, col = self.getpos(); return self.offsets[line-1] + col
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        selected = tag == self.tag and (self.attr is None or self.attr in attrs and (self.value is None or attrs[self.attr] == self.value))
        start = self.source_offset() if selected else None
        if tag in ('area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'):
            if selected: self.matches.append(self.source[start:start+len(self.get_starttag_text())])
        else: self.stack.append((tag, start))
    def handle_startendtag(self, tag, attrs):
        before = len(self.stack); self.handle_starttag(tag, attrs)
        if len(self.stack) > before:
            _, start = self.stack.pop()
            if start is not None: self.matches.append(self.source[start:self.source_offset()+len(self.get_starttag_text())])
    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1][0] != tag:
            raise ValueError('Template must have explicitly balanced tags for exact extraction: ' + tag)
        _, start = self.stack.pop()
        if start is not None: self.matches.append(self.source[start:self.source.index('>', self.source_offset())+1])

class Library:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.base = self.root / 'assets/templates/css'
        self.catalog = json.loads((self.base / 'catalog.json').read_text())
        bindings_path = self.root / 'assets/templates/ref-bindings.json'
        self.bindings = json.loads(bindings_path.read_text()) if bindings_path.exists() else {}
        self.entries = {}
        for entry in self.catalog['entries']:
            if entry['id'] in self.entries:
                raise ValueError('Duplicate catalog ID: ' + entry['id'])
            self.entries[entry['id']] = entry
        self.cache = {}

    def path(self, name, parent=None):
        path = ((parent or self.root) / unquote(name)).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError('Path outside skill: ' + str(path))
        return path

    def target(self, ref):
        if ref in self.entries:
            entry = self.entries[ref]
            doc = self.catalog['documents'][entry['document']]['path']
            return self.path(doc), entry['anchor']
        if '#' not in ref or urlsplit(ref).scheme:
            raise ValueError('Unknown ID; use a catalog ID or skill-relative path#anchor: ' + ref)
        file, anchor = ref.split('#', 1)
        return self.path(file), unquote(anchor)

    def supports_ref_key(self, entry_id, ref_key):
        if not ref_key:
            return True
        category_refs = self.bindings.get('category_refs', {})
        if ref_key not in category_refs:
            raise ValueError('Unknown ref_key: ' + ref_key)
        css = self.bindings.get('css', {})
        return ref_key in css.get('entry_overrides', {}).get(
            entry_id, css.get('default_ref_keys', [])
        )

    @staticmethod
    def container_rank(entry, terms, kind):
        """Favor structural containers for generic card queries without changing explicit requests."""
        if kind and kind != 'shape':
            return 0, ''
        generic_terms = {'卡片', '容器', '面板', '承托', '信息面', '信息区'}
        explicit_rounded_terms = {'圆角', 'rounded', '玻璃', '毛玻璃', '塑料', '透明卡片'}
        term_set = set(terms)
        profile = entry.get('container_profile', '')
        if not term_set.intersection(generic_terms) or term_set.intersection(explicit_rounded_terms):
            return 0, ''
        if profile == 'structural':
            return 2, '泛化容器查询优先结构型轮廓'
        if profile == 'neutral':
            return -2, '泛化容器查询降低中性圆角容器'
        return 0, ''

    @staticmethod
    def intent_rank(entry, terms, kind):
        """Expand broad design-language queries into a deliberately bounded candidate set."""
        if kind:
            return [], 0, ''
        intent_entries = {
            '图文关系': {
                'layout.image-stage', 'layout.staggered-title', 'layout.collage',
                'layout.annotated-figure', 'surface.image-fade',
                'combination.playful-product-editorial',
            },
            '背景氛围': {
                'layout.image-stage',
                'surface.diffuse-field', 'surface.woven-grid', 'surface.light-paper',
                'surface.screen-grain', 'surface.dot-pattern', 'surface.soft-focus-mist',
                'surface.image-fade',
            },
            '质感': {
                'material.plastic', 'material.glass', 'material.paper', 'material.sphere-glass',
                'surface.woven-grid', 'surface.light-paper', 'surface.screen-grain',
                'surface.type-relief', 'surface.metal-bands', 'surface.twisted-cord',
            },
            '装饰': {
                'decoration.edge', 'decoration.shadow', 'decoration.back-sheet',
                'shape.paper-mount', 'shape.binder-clip', 'shape.sparkle',
                'surface.twisted-cord', 'surface.dot-pattern',
            },
            '有趣排版': {
                'layout.image-stage', 'layout.collage', 'layout.route-flow',
                'layout.staggered-title', 'layout.annotated-figure',
            },
            '文字特效': {
                'text.paint', 'text.outline', 'text.arc', 'surface.type-relief',
                'surface.metal-bands', 'surface.neon-edge', 'combination.luminous-sphere',
            },
            '配色': set(),  # Resolved below from the stable ID namespace.
        }
        aliases = {
            '图文关系': {'图文关系', '图文', '图文组合', '图文排版'},
            '背景氛围': {'背景', '氛围', '氛围感', '底图', '底纹'},
            '质感': {'质感', '材质', '表面', '肌理'},
            '装饰': {'装饰', '点缀', '装点'},
            '有趣排版': {'有趣', '创意', '表现力', '趣味', '排版'},
            '文字特效': {'特效', '文字特效', '字效', '标题特效'},
            '配色': {'配色', '颜色', '色彩', '色板'},
        }
        matched_intents = [
            intent for intent, aliases_for_intent in aliases.items()
            if set(terms).intersection(aliases_for_intent)
        ]
        implicit_hits = []
        adjustment = 0
        reasons = []
        for intent in matched_intents:
            applies = entry['id'].startswith(('palette.', 'color.')) if intent == '配色' else entry['id'] in intent_entries[intent]
            if not applies:
                continue
            implicit_hits.append(intent)
            adjustment += 2
            reasons.append('泛化%s查询召回对应视觉能力' % intent)
        return implicit_hits, adjustment, '；'.join(reasons)

    def query_terms(self, query):
        related = {'贴纸': ['手账', '拼贴'], '手账': ['纸本', '拼贴'],
                   '毛玻璃': ['磨砂', '透底'], '纸纹': ['纸张', '纤维']}
        vocabulary = set(related) | {word for words in related.values() for word in words}
        vocabulary.update(('灰蓝', '低饱和', '圆角', '网格', '双栏', '单栏', '窄侧栏'))
        categories = set()
        for entry in self.entries.values():
            categories.update(entry.get('artifact_types', []))
            for value in entry.get('tags', []) + entry.get('style_tags', []):
                vocabulary.update(word for word in re.split(r'[\s/：:／、（）()]+', value)
                                  if re.fullmatch(r'[\u4e00-\u9fff]{2,8}', word))
            # Catalog is the only source of layout affinity vocabulary. Never index reason.
            for affinity in entry.get('style_affinities', []):
                vocabulary.update(_affinity_words(affinity))
        vocabulary.update(categories)
        vocabulary = {_style_norm(word) for word in vocabulary if _style_norm(word)}
        for compound in sorted(vocabulary, key=lambda word: (len(word), word)):
            pieces = sorted(word for word in vocabulary if word != compound and len(word) >= 2 and word in compound)
            if pieces:
                related[compound] = list(dict.fromkeys(related.get(compound, []) + pieces +
                                        [item for word in pieces for item in related.get(word, [])]))
        longest_first = sorted(vocabulary, key=lambda word: (-len(word), word))
        terms, unresolved = [], []
        for raw in re.split(r'[\s，,、]+', _style_norm(query)):
            if not raw:
                continue
            if re.fullmatch(r'[a-z]{1,4}\d+(?:\.\d+)+', raw):
                unresolved.append(raw)
                continue
            if raw in vocabulary or not re.search(r'[\u4e00-\u9fff]', raw):
                terms.append(raw)
                continue
            position, extracted = 0, []
            while position < len(raw):
                found = next((word for word in longest_first if raw.startswith(word, position)), None)
                if found:
                    extracted.append(found)
                    position += len(found)
                else:
                    position += 1
            terms.extend(extracted or [raw])
            if not extracted:
                unresolved.append(raw)
        return list(dict.fromkeys(terms)), categories, related, unresolved

    def search(self, query='', style='', kind=None, limit=5, artifact='', layout_scope='', ref_key=''):
        terms, categories, related, unresolved = self.query_terms(query)
        style = _style_norm(style)
        if not terms and not style and not unresolved:
            raise ValueError('Provide query terms or --style; full-catalog dumping is not the default.')
        # Prevent affinity aliases from being counted again by the legacy text scorer.
        affinity_vocabulary = set()
        for metadata in self.entries.values():
            for affinity in metadata.get('style_affinities', []):
                affinity_vocabulary.update(_affinity_words(affinity))
        rows = []
        for entry in self.entries.values():
            if not self.supports_ref_key(entry['id'], ref_key):
                continue
            if kind and entry['id'].split('.')[0] != kind:
                continue
            if artifact and artifact.strip() not in entry.get('artifact_types', []):
                continue
            if layout_scope and entry.get('layout_scope') != layout_scope:
                continue
            affinity = style_affinity_matches(entry, terms, related, style)
            has_affinities = bool(entry.get('style_affinities'))
            legacy_terms = [t for t in terms if not has_affinities or t not in affinity_vocabulary]
            context = entry.get('candidate_contexts', {})
            fields = {k: entry.get(k, []) for k in ('name', 'tags', 'style_tags', 'effect_type', 'effect_targets')}
            fields['candidate_contexts'] = context
            text = json.dumps(fields, ensure_ascii=False).casefold()
            hits = [term for term in legacy_terms if term in text or term in entry['id'].casefold()]
            effects = [term for term in hits if term not in categories]
            legacy_style_hit = bool(style and style in json.dumps(
                [entry.get('style_tags', []), context], ensure_ascii=False).casefold())
            # Known affinity styles must use structural metadata for entries declaring affinities.
            if has_affinities and style in affinity_vocabulary:
                legacy_style_hit = False
            style_hit = legacy_style_hit or affinity['style_match']
            intent_hits, intent_adjustment, intent_reason = self.intent_rank(entry, legacy_terms, kind)
            expanded = [{'from': term, 'term': word} for term in legacy_terms for word in related.get(term, [])
                        if word in text and word not in hits
                        and (not has_affinities or word not in affinity_vocabulary)]
            affinity_exact = affinity['style_stage'] == 'exact'
            generic = not terms and not style and not unresolved and '通用' in entry.get('style_tags', [])
            if not hits and not intent_hits and not style_hit and not expanded and not affinity['style_matches'] and not generic:
                continue
            row = {k: entry[k] for k in ('id', 'name', 'tags', 'style_tags', 'candidate_contexts',
                                        'artifact_types', 'layout_scope') if k in entry}
            if ref_key:
                row['ref_key'] = ref_key
            rank_adjustment, ranking_reason = self.container_rank(entry, legacy_terms, kind)
            rank_adjustment += intent_adjustment
            strong = bool(effects or style_hit or intent_hits or affinity_exact)
            all_hits = list(dict.fromkeys(hits + affinity['matched_terms']))
            all_expanded = expanded + affinity['expanded_matches']
            row.update(matched_terms=all_hits, implied_intents=intent_hits, style_match=style_hit,
                       style_matches=affinity['style_matches'], related_combinations=affinity['related_combinations'],
                       rank_adjustment=rank_adjustment, expanded_matches=all_expanded,
                       unmatched_terms=[term for term in terms if term not in all_hits] + unresolved,
                       recall_stage='exact' if strong else 'expanded' if all_expanded else 'weak',
                       relevance='effect_match' if strong else 'related_effect' if all_expanded else 'category_only')
            reasons = [reason for reason in (ranking_reason, intent_reason) if reason]
            if reasons:
                row['ranking_reason'] = '；'.join(reasons)
            score = (4 * len(effects) + int(legacy_style_hit) * 4 + rank_adjustment
                     + 0.1 * len(hits) + affinity['style_score'])
            rows.append((row, score, strong, affinity['style_priority'], affinity['expanded_matches']))
        expand = sum(strong for _, _, strong, _, _ in rows) < limit
        candidates = []
        for row, score, strong, priority, affinity_expansions in rows:
            if not strong and row['expanded_matches'] and not expand:
                continue
            if strong:
                # Preserve provenance for any expanded affinity alongside other exact evidence.
                row['expanded_matches'] = affinity_expansions
            candidates.append((row, score, priority))
        stage_order = {'exact': 0, 'expanded': 1, 'weak': 2}
        candidates.sort(key=lambda item: (stage_order[item[0]['recall_stage']], item[2], -item[1], item[0]['id']))
        ordered, used = [], set()
        def families(row):
            matches = row.get('style_matches', [])
            if matches:
                return tuple(sorted({_style_labels(match['style'])[1][0] for match in matches}))
            return tuple(row.get('style_tags', []))
        while candidates:
            first_row, score, priority = candidates[0]
            stage = first_row['recall_stage']
            index = next((i for i, (row, value, rank) in enumerate(candidates)
                          if row['recall_stage'] == stage and rank == priority and value == score
                          and families(row) not in used), 0)
            row, _, _ = candidates.pop(index)
            used.add(families(row))
            ordered.append(row)
        expansions = [dict(from_term=term, related_terms=related[term])
                      for term in terms if expand and term in related]
        return {'candidates': ordered[:limit], 'total': len(ordered), 'has_more': len(ordered) > limit,
                'query_analysis': {'terms': terms, 'unresolved_terms': unresolved, 'expansions': expansions},
                'note': 'Metadata recall only, not visual fit or adoption. Hard category/scope filters remain fixed. '
                        'Affinity levels describe structural suitability, not certification. '
                        'Expanded matches are related effects, not exact synonyms. '
                        'Related combinations are source associations, not guaranteed style matches.'}

    def text(self, path):
        if path not in self.cache:
            self.cache[path] = path.read_text()
        return self.cache[path]

    def section(self, path, anchor):
        text = self.text(path)
        if not anchor:
            return text, 1, len(text.splitlines())
        lines = text.splitlines(keepends=True)
        anchors, headings, counts = [], [], {}
        fence = None
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            marker = re.match(r'(`{3,}|~{3,})', stripped)
            if marker:
                token = marker.group(1)
                if fence is None:
                    fence = token
                elif token[0] == fence[0] and len(token) >= len(fence):
                    fence = None
                continue
            if fence:
                continue
            for found in re.finditer(r'<a\s+(?:id|name)=["\']([^"\']+)["\'][^>]*>', line):
                anchors.append((found.group(1), i))
            heading = re.match(r'^(#{1,6})\s+(.+?)\s*#*\s*$', line)
            if heading:
                slug = re.sub(r'[^\w\- ]', '', heading.group(2).casefold()).replace(' ', '-')
                n = counts.get(slug, 0); counts[slug] = n + 1
                headings.append((slug + ('-' + str(n) if n else ''), i, len(heading.group(1))))
        matches = [i for name, i in anchors if name == anchor]
        if len(matches) > 1:
            raise ValueError('Ambiguous anchor: ' + anchor)
        if matches:
            start = matches[0]
            end = min([i for _, i in anchors if i > start] or [len(lines)])
        else:
            match = next((item for item in headings if item[0] == anchor), None)
            if not match:
                raise ValueError('Missing anchor: ' + str(path) + '#' + anchor)
            _, start, level = match
            end = min([i for _, i, depth in headings if i > start and depth <= level] +
                      [i for _, i in anchors if i > start] or [len(lines)])
        return ''.join(lines[start:end]).rstrip(), start + 1, end

    @staticmethod
    def blocks(content):
        """Keep fenced source whole; never treat example markup as metadata."""
        return list(re.finditer(r"(?ms)^ {0,3}([`]{3,}|[~]{3,})([^\n]*)\n(.*?)^ {0,3}\1(?:(?<=`)`*|(?<=~)~*)[ \t]*(?:\n|$)", content))

    def view(self, content, templates=False):
        omitted = []
        for index, block in reversed(list(enumerate(self.blocks(content), 1))):
            language = block.group(2).strip().lower()
            if language in ('html', 'svg') and not templates:
                omitted.append({'block': index, 'language': language, 'characters': len(block.group(0))})
                content = content[:block.start()] + '[Template block %d omitted; explicitly request --templates if adopting this example.]\n' % index + content[block.end():]
        return content, list(reversed(omitted))

    def design_evidence(self, content):
        # JSON carries layout, font, asset and constraint facts, including future fields.
        # Preserve it whole; only executable/code and markup fences are removed.
        for block in reversed(self.blocks(content)):
            if block.group(2).strip().lower() != 'json':
                content = content[:block.start()] + content[block.end():]
        return content

    def template(self, ref, block=None, selector=None, max_chars=30000):
        if block is None and selector is None:
            raise ValueError('Choose --block, --selector, or --block with --selector')
        if block is not None:
            path, anchor = self.target(ref); source = self.section(path, anchor)[0]
            blocks = self.blocks(source)
            if not 1 <= block <= len(blocks) or blocks[block-1].group(2).strip().lower() not in ('html','svg'):
                raise ValueError('Unknown markup block')
            result = blocks[block-1].group(3)
        else:
            path = self.path(ref); source = self.text(path); result = source
        if selector is not None:
            parser = NodeExtractor(result, selector); parser.feed(result); parser.close()
            if parser.stack or len(parser.matches) != 1:
                raise ValueError('Selector must match exactly one complete node; got ' + str(len(parser.matches)))
            result = parser.matches[0]
        if len(result) > max_chars: raise BudgetExceeded('Selected structure exceeds budget; nothing truncated')
        return {'reference': ref, 'block': block, 'selector': selector, 'content': result,
                'characters': len(result), 'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
                'note': 'Only selected structure returned. Read recipe CSS and declared dependencies separately; this is not rendered validation.'}

    def dependency_ids(self, content):
        # applies_to, examples, alternatives and quoted labels are NOT dependencies.
        ids = []
        keys = ('common', 'dependencies', 'components', 'recipe', 'presets', 'base')
        for block in self.blocks(content):
            if block.group(2).strip().lower() != 'json':
                continue
            try:
                data = json.loads(block.group(3))
            except ValueError:
                continue
            if not isinstance(data, dict):
                continue
            for key in keys:
                value = data.get(key, [])
                values = [value] if isinstance(value, str) else value if isinstance(value, list) else []
                ids.extend(x for x in values if isinstance(x, str))
        return list(dict.fromkeys(ids))

    def describe(self, refs):
        """Bounded verbatim selection evidence, not CSS and not an adoption decision."""
        if not 1 <= len(refs) <= 8:
            raise ValueError('describe accepts 1–8 selected candidate references')
        candidates = []
        vocabulary = {
            'layout': r'布局|构图|阅读|图文|背景|主体|分区|容器|版式',
            'typography': r'字体|字形|字重|标题|正文|英文|数字|family',
            'palette': r'配色|色彩|颜色|色场|色板|#(?:[0-9A-Fa-f]{6})',
            'surface': r'质感|材质|纹理|纸感|光照|渐变|透明|投影',
            'assets': r'素材|摄影|照片|插画|图窗|图片|资产',
            'constraints': r'适用|边界|禁止|不得|必须|条件|安全|只在|保留',
        }
        for ref in dict.fromkeys(refs):
            path, anchor = self.target(ref)
            content, start, end = self.section(path, anchor)
            entry = self.entries.get(ref, next((e for e in self.entries.values() if self.target(e['id']) == (path, anchor)), {}))
            prose = content
            for block in reversed(self.blocks(content)):
                prose = prose[:block.start()] + prose[block.end():]
            groups = {key: [] for key in vocabulary}
            # Structured visual facts are selection evidence too; code and coordinates remain source data.
            for block in self.blocks(content):
                if block.group(2).strip().lower() != 'json':continue
                try:data=json.loads(block.group(3))
                except ValueError:continue
                if not isinstance(data,dict):continue
                for note in data.get('local_review_notes',[]):
                    if isinstance(note,str):
                        if re.search(r'字体|字形|字重|标题',note):groups['typography'].append(note)
                for relation in data.get('relationships',[]):
                    if isinstance(relation,dict) and isinstance(relation.get('detail'),str):
                        groups['layout'].append(str(relation.get('type','关系'))+'：'+relation['detail'])
                for field,group in [('layout','layout'),('palette','palette'),('texture','surface'),('asset_strategy','assets')]:
                    value=data.get(field)
                    if isinstance(value,dict):
                        if field=='palette':groups[group].append('配色：'+'；'.join(str(k)+' '+str(v) for k,v in value.items()))
                        else:
                            for key,value in value.items():
                                if isinstance(value,str) and key not in ('mode','binding','dependency'):
                                    groups[group].append(key+'：'+value)
                for font in data.get('fonts',[]):
                    if isinstance(font,dict):
                        groups['typography'].append('字体候选（依正文校正）：'+str(font.get('usage',''))+' / '+str(font.get('family','')))
                for limit in data.get('limits',[]):
                    if isinstance(limit,str):groups['constraints'].append(limit)
            context = ''
            for line in prose.splitlines():
                line = line.strip()
                if not line or line.startswith(('<', '风格标签', '**产物适用标签', '**适用与状态', '**组合状态', '**状态')):
                    continue
                if line.startswith('#'):
                    context = line.lstrip('# ').strip()
                    continue
                if re.fullmatch(r'[| :\-]+', line):
                    continue
                line = re.sub(r'\[([^]]+)\]\([^)]+\)', r'\1', line)
                line = line.replace('**', '').replace('`', '')
                if line.startswith('|'):
                    cells = [x.strip() for x in line.strip('|').split('|')]
                    if cells[:1] in (['对象'], ['角色'], ['分类'], ['参数'], ['区域'], ['类型'], ['归属类型'], ['项目'], ['文字角色']):
                        continue
                    line = '：'.join(cells)
                for group, pattern in vocabulary.items():
                    if re.search(pattern, line, re.I):
                        groups[group].append(line)
                    elif re.search(pattern, context, re.I):
                        groups[group].append(line)
            priority = {
                'layout': r'^title：|^illustration：|^主体|^构图|^布局|^背景／卡面|^背景与容器|^素材与容器',
                'typography': r'^竖排标题|主词|副词|空间主题|^主标题|^字体候选',
                'palette': r'^配色|^色彩|^色板',
                'surface': r'^css_approximation：|^real_texture_strategy：|^质感|^材质|^渐变|^纸',
                'assets': r'^megaphone：|^图片／装饰素材|^主体|^素材|^摄影|^照片|^图像',
                'constraints': r'安全|净空|字形|长文|内容量|比例|不得|不能|不等于',
            }
            for group,pattern in vocabulary.items():
                groups[group] = sorted(groups[group], key=lambda x: (bool(re.search(r'截图复核|组合状态|已做参考',x)), not bool(re.search(priority[group],x,re.I)), not bool(re.search(pattern,x,re.I))))
            # Whole evidence units only: share the budget across all visual dimensions.
            evidence = {}; seen = set(); budget = 1500
            for pass_index in range(2):
                for group, units in groups.items():
                    unit = next((x for x in units if x not in seen and len(x) <= min(360, budget)), None)
                    if unit is None:
                        continue
                    evidence.setdefault(group, []).append(unit);seen.add(unit);budget -= len(unit)
            source_ref = str(path.relative_to(self.root)) + '#' + anchor
            row = {k: entry[k] for k in ('id','name','style_tags','tags','candidate_contexts','artifact_types','layout_scope','style_affinities','related_combinations') if k in entry}
            row.update(reference=source_ref, selection_evidence=evidence,
                       evidence_is_excerpt=True, more_evidence_available=any(x not in seen for units in groups.values() for x in units),
                       implementation_refs=self.dependency_ids(content),
                       component_names=[self.entries[x].get('name',x) for x in self.dependency_ids(content) if x in self.entries],
                       source_sha256=hashlib.sha256(content.encode()).hexdigest(),
                       implementation_read='get ' + ref + ' --dependencies')
            candidates.append(row)
        return {'candidates': candidates, 'note': 'This result is selection evidence, not a selection decision. Inspect it and record the chosen scope and preserved relationships before requesting get/template in a later call; do not batch dependent implementation reads with first-time describe. For whole designs compare relevant whole combinations/visual relationships at the same scope; atoms are local implementations, not competing whole-design directions. Before atom-only fallback check structural adaptation and concrete conflicts; different sample colors/topics or not-yet-produced assets alone do not justify rejection. Explicit user-selected recipes/local edits or still-valid prior selections may read implementation directly. Compare current Spec/Visual candidates before choosing a direction. Evidence is an excerpt, not a rejection criterion: missing evidence means unknown, not unsupported. Use get --prose to check before rejecting. Not complete implementation. Reference dimensions, identities and sample text are not task requirements. No dependencies or code expanded. Read adopted implementation only after selection; inspect missing design evidence with get --prose.'}

    def get(self, refs, dependencies=False, templates=False, max_chars=30000, read_state=None, prose=False):
        if prose and (dependencies or templates):
            raise ValueError('--prose cannot be combined with --dependencies or --templates')
        if read_state is not None and (not isinstance(read_state, dict) or not isinstance(read_state.get('returned', {}), dict)):
            raise ValueError('Invalid task-local read state')
        if read_state and read_state.get('root') != str(self.root):
            raise ValueError('Read state belongs to another skill root; use a new task-local state')
        known = read_state.get('returned', {}) if read_state else {}
        pending = {};queue = [self.target(ref) for ref in refs]
        if dependencies and any(anchor.startswith(('combination.', 'recipe.')) for _, anchor in queue):
            path = self.base / 'combinations/recipes.md'
            if path.exists() and 'id="combinations.assembly"' in self.text(path):
                queue.append((path, 'combinations.assembly'))
        seen, sections, followups, reused, template_blocks = set(), [], {}, [], []
        total = 0
        while queue:
            path, anchor = queue.pop(0)
            key = (path, anchor)
            if key in seen:
                continue
            seen.add(key)
            original, start, end = self.section(path, anchor)
            relative = str(path.relative_to(self.root))
            source_ref = relative + ('#' + anchor if anchor else '')
            content, omitted = self.view(original, templates)
            if prose:
                content = self.design_evidence(original)
                omitted = []
            for item in omitted:
                template_blocks.append(dict(item, reference=source_ref, read='template ' + source_ref + ' --block ' + str(item['block']), status='structure-decision-required'))
            state_key = source_ref + ('|prose' if prose else '|templates' if templates else '|implementation')
            fingerprint = hashlib.sha256(('view-v2\n' + original).encode()).hexdigest()
            if known.get(state_key) == fingerprint:
                reused.append({'reference': source_ref, 'sha256': fingerprint})
            else:
                total += len(content)
                if total > max_chars:
                    raise BudgetExceeded('Read budget exceeded; no partial implementation returned and no read state updated. Select fewer adopted parts. Sources: ' + ', '.join(x['source'] for x in sections) + ', ' + source_ref)
                sections.append({'source':relative, 'anchor':anchor, 'start_line':start, 'end_line':end, 'content':content})
                pending[state_key] = fingerprint
            if prose:
                continue
            for ref in self.dependency_ids(original):
                if ref in self.entries:
                    target = self.target(ref)
                else:
                    try:
                        self.section(path, ref);target = (path, ref)
                    except ValueError:
                        raise ValueError('Unresolved declared dependency: ' + ref + ' in ' + source_ref)
                if dependencies:
                    queue.append(target)
                else:
                    followups[ref] = {'reference':ref, 'role':'required', 'reason':'declared implementation dependency; use --dependencies'}
            # References in fenced examples, applicability lists and alternative recipes are never followed.
            prose_content = original
            for block in reversed(self.blocks(original)):
                prose_content = prose_content[:block.start()] + prose_content[block.end():]
            for match in re.finditer(r'\[([^]]+)\]\(([^)]+)\)', prose_content):
                label, link = match.groups();parsed = urlsplit(link)
                if parsed.scheme or parsed.netloc:
                    followups[link] = {'reference':link,'reason':'external reference; not fetched'};continue
                target = self.path(parsed.path, path.parent) if parsed.path else path
                fragment = unquote(parsed.fragment)
                ref = str(target.relative_to(self.root)) + ('#' + fragment if fragment else '')
                in_library = target.is_relative_to(self.base)
                contract = self.catalog.get('reading_contracts', {}).get(source_ref, {}).get(link)
                if contract not in (None, 'required', 'optional', 'reference'):
                    raise ValueError('Invalid dependency role: ' + str(contract))
                if contract == 'required' and dependencies:
                    if not fragment or target.suffix != '.md':
                        raise ValueError('Required source must be an anchored document: ' + ref)
                    queue.append((target, fragment))
                else:
                    followups[ref] = {'reference':ref, 'role':contract or 'unclassified',
                        'reason': 'explicit ' + contract if contract else 'unclassified link; determine role before claiming complete implementation',
                        'exists':target.exists()}
            for item in self.catalog.get('template_sources', {}).get(source_ref, []):
                template = self.path(item['reference'])
                previous = followups.get(item['reference'], {})
                selectors = list(dict.fromkeys(previous.get('selectors', []) + item.get('selectors', [])))
                followups[item['reference']] = dict(item, selectors=selectors, role='structure', exists=template.exists(), reason='required when adopting this carrier; read each listed selector')
            for block in self.blocks(original):
                if block.group(2).strip().lower() != 'json':continue
                try:data=json.loads(block.group(3))
                except ValueError:continue
                if isinstance(data,dict) and isinstance(data.get('template'),str):
                    template=self.path(data['template'],path.parent)
                    ref=str(template.relative_to(self.root))
                    # A template can contain unrelated variants. Expose its selector, never load the entire file transitively.
                    previous = followups.get(ref, {})
                    selectors = list(dict.fromkeys(previous.get('selectors', []) + ([data['selector']] if data.get('selector') else [])))
                    followups[ref]={'reference':ref,'selectors':selectors,'role':'structure', 'reason':'required when adopting this carrier; read every selected node with template --selector','exists':template.exists()}
        expanded={str(path.relative_to(self.root))+('#'+anchor if anchor else '') for path,anchor in seen}
        result={'sections':sections,'characters':total,'reused_sections':reused,'template_blocks':template_blocks,
                'follow_ups':[v for k,v in followups.items() if k not in expanded],
                'note':'Resolve template_blocks as adopted structure or unused example before assembly. Use template --block/--selector for selected structure; --templates is explicit whole-section markup reading. follow_ups are not loaded implementations; resolve required and unclassified references for the adopted design. Read state records returned sections, not visual validation.'}
        if read_state is not None:
            read_state.update(root=str(self.root),returned=dict(known,**pending))
        return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    sub = parser.add_subparsers(dest='command', required=True)
    search = sub.add_parser('search');search.add_argument('query', nargs='?', default='')
    search.add_argument('--style', default='');search.add_argument('--kind', choices=['combination','recipe','layout','shape','material','color','decoration','surface','text','palette'])
    search.add_argument('--limit', type=int, default=5)
    search.add_argument('--artifact', default='', help='Strict artifact whitelist filter, e.g. 通知, 邀请函, 社媒长图; entries without metadata are excluded')
    search.add_argument('--layout-scope', default='', choices=['整张单屏','局部模块','完整长页'], help='Layout adoption scope')
    search.add_argument('--ref-key', default='', help='Restrict candidates through assets/templates/ref-bindings.json')
    describe = sub.add_parser('describe');describe.add_argument('refs', nargs='+')
    describe.add_argument('--font-language', default='zh', choices=['zh','en','ko','ja'])
    get = sub.add_parser('get');get.add_argument('refs', nargs='+')
    get.add_argument('--dependencies', action='store_true');get.add_argument('--templates', action='store_true')
    get.add_argument('--max-chars', type=int, default=30000)
    get.add_argument('--prose', action='store_true', help='Design evidence only; no code or recursive dependencies')
    get.add_argument('--read-state', type=Path, help='Optional task-local record of returned sections; reuse only within the same retained task context')
    template = sub.add_parser('template'); template.add_argument('ref')
    template.add_argument('--block', type=int); template.add_argument('--selector')
    template.add_argument('--max-chars', type=int, default=30000)
    args = parser.parse_args()
    try:
        lib = Library(args.root)
        if args.command == 'search':
            if not 1 <= args.limit <= 50:raise ValueError('--limit must be 1–50')
            result = lib.search(args.query, args.style, args.kind, args.limit, args.artifact, args.layout_scope, args.ref_key)
        elif args.command == 'describe':
            result = lib.describe(args.refs)
        elif args.command == 'template':
            if args.max_chars < 1: raise ValueError('--max-chars must be positive')
            result = lib.template(args.ref, args.block, args.selector, args.max_chars)
        else:
            if args.max_chars < 1:raise ValueError('--max-chars must be positive')
            state = json.loads(args.read_state.read_text()) if args.read_state and args.read_state.exists() else {}
            result = lib.get(args.refs, args.dependencies, args.templates, args.max_chars, state if args.read_state else None, args.prose)
            if args.read_state:
                state_path = args.read_state.resolve()
                if state_path.is_relative_to(lib.root):raise ValueError('--read-state must be outside the skill, in the task workspace')
                state_path.parent.mkdir(parents=True,exist_ok=True)
                temporary = state_path.with_name(state_path.name+'.tmp')
                temporary.write_text(json.dumps(state,ensure_ascii=False,indent=2));temporary.replace(state_path)
        if args.command == 'describe':
            from select_fonts import recommend, FontBindingError
            combinations = [row['id'] for row in result['candidates'] if row.get('id', '').startswith('combination.')]
            if combinations:
                result['font_recommendations'] = {}
                result['font_errors'] = []
                result['font_status'] = 'recommendations_only'
                for ref in combinations:
                    roles = {}
                    for role in ('hero','sub','body','meta'):
                        try:
                            fonts = recommend(lib.root, combination=ref, role=role, limit=3,
                                              language=args.font_language)
                        except FontBindingError as error:
                            result['font_errors'].append({'code': error.code, 'combination': ref,
                                'detail': str(error), 'blocked': 'font_selection'})
                            result['font_status'] = 'blocked'
                            roles = {}
                            break
                        roles[role] = {
                            'candidates': [{key: font[key] for key in
                                ('key','display_name','shape','design_note','resource_status','license_status')
                                if key in font} for font in fonts['candidates']],
                            'shortfall': fonts.get('shortfall', 0),
                            'detail_query': {'script':'scripts/runtime/select_fonts.py',
                                'combination':ref, 'role':role,
                                'language':args.font_language, 'limit':3},
                        }
                    result['font_recommendations'][ref] = roles
                result['font_note'] = ('Selection summaries only, not loaded-face or license verification. '
                    'After choosing a design, query only its actual text roles/languages via select_fonts.py '
                    'for full resource details and validate the chosen faces. get returns implementation '
                    'without repeating these recommendations; exact source typography remains authoritative.')
        elif args.command == 'search':
            for entry in result['candidates']:
                if entry['id'].startswith('combination.'):
                    entry['font_query'] = {'script':'scripts/runtime/select_fonts.py',
                        'combination':entry['id'],'role':'hero','language':'set_from_actual_text','limit':10}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0

if __name__ == '__main__':
    sys.exit(main())
