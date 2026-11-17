#!/usr/bin/env python3
"""Match the published library by resource group; read complete, verified files.

The published manifest owns membership, hashes and available metadata; no maintenance sources are required.
Match page names or screen structure; prefer verified page-style tags and a chosen source without weighted scores.
"""
import argparse
from html.parser import HTMLParser
import hashlib
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

GROUPS = ('构图', '容器', '点缀', '文字特效', '配色', '材质', '特效', '蒙版', '背景')
ALIASES = (
    ('双栏', '两栏'), ('单栏', '一栏'), ('双列', '两列'),
    ('居中', '中置'), ('并排', '并列'), ('镂空', '空心'),
    ('投影', '阴影'), ('霓虹', 'neon'), ('故障', 'glitch'),
    ('文件夹', 'folder'), ('网格', 'grid'), ('渐变', 'gradient'),
)


def norm(value):
    return unicodedata.normalize('NFKC', str(value)).casefold().strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ScreenLocators(HTMLParser):
    """Validate published ID or explicit rooted nth-child locators, not arbitrary CSS."""
    VOID = set('area base br col embed hr img input link meta param source track wbr'.split())

    def __init__(self, content):
        super().__init__(convert_charrefs=True)
        self.stack = [{'tag': '', 'path': '', 'children': 0}]
        self.counts = {}
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        parent = self.stack[-1]
        parent['children'] += 1
        path = ('html' if tag == 'html' and not parent['path'] else
                parent['path'] + ' > ' + tag + ':nth-child(' + str(parent['children']) + ')')
        keys = [path]
        ident = dict(attrs).get('id')
        if ident:
            keys.append('#' + ident)
        for key in keys:
            self.counts[key] = self.counts.get(key, 0) + 1
        if tag not in self.VOID:
            self.stack.append({'tag': tag, 'path': path, 'children': 0})

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i]['tag'] == tag:
                del self.stack[i:]
                break


class TemplateLibrary:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.manifest = json.loads((self.root / 'assets/模板库/manifest.json').read_text())
        if self.manifest.get('version') != 2:
            raise ValueError('需要自包含发布 manifest v2')
        self.rows = self.manifest['library_resources']
        self.by_file = {r['file']: r for r in self.rows}
        if len(self.by_file) != len(self.rows):
            raise ValueError('发布索引存在重复路径')
        for row in self.rows:
            missing = self.unavailable_dependencies(row['file'], set())
            row['availability'] = ('blocked' if missing else 'metadata-only'
                if row.get('reference_image_status') == 'missing_from_source_package' else 'candidate')
            row['unavailable_dependencies'] = missing

    def unavailable_dependencies(self, file, visited):
        if file in visited:
            return []
        visited.add(file)
        row = self.by_file.get(file, {})
        missing = [{'resource': file, 'missing': value}
                   for value in row.get('blocked_dependencies', [])]
        for dependency in row.get('dependencies', []):
            missing.extend(self.unavailable_dependencies(dependency, visited))
        return missing

    def verified_bytes(self, relative):
        def checked_path(value):
            if (not isinstance(value, str) or not value
                    or '\x00' in value or '\\' in value
                    or Path(value).is_absolute()
                    or any(part in ('', '.', '..') for part in value.split('/'))):
                raise ValueError('资源路径必须是规范相对路径')
            return self.path(value)

        files = self.manifest['files']
        storage = self.manifest.get('resource_storage', {})
        if not isinstance(files, dict) or not isinstance(storage, dict):
            raise ValueError('files 与 resource_storage 必须是对象')

        def expected_hash(file):
            value = files.get(file)
            if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
                raise ValueError('资源缺少有效发布校验值：' + file)
            return value

        logical_path = checked_path(relative)
        expected = expected_hash(relative)
        if relative not in storage:
            raw = logical_path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError('发布资源校验失败：' + relative)
            return raw

        entry = storage[relative]
        if not isinstance(entry, dict):
            raise ValueError('资源存储记录必须是对象：' + relative)
        bundle = entry.get('bundle')
        bundle_path = checked_path(bundle)
        if (bundle == relative or bundle_path == logical_path
                or bundle in storage
                or Path(bundle).parent != Path(relative).parent
                or bundle_path.parent != logical_path.parent):
            raise ValueError('合集必须是同目录独立物理文件：' + relative)
        bundle_expected = expected_hash(bundle)
        offset, length = entry.get('offset'), entry.get('length')
        if type(offset) is not int or offset < 0 or type(length) is not int or length <= 0:
            raise ValueError('offset须为非负整数，length须为正整数：' + relative)

        # 同一次打开中核验整个合集，再按字节段读取；不缓存、不回退原文件。
        with bundle_path.open('rb') as stream:
            digest = hashlib.sha256()
            size = 0
            while True:
                block = stream.read(1024 * 1024)
                if not block:
                    break
                digest.update(block)
                size += len(block)
            if digest.hexdigest() != bundle_expected:
                raise ValueError('发布合集校验失败：' + bundle)
            if offset > size or length > size - offset:
                raise ValueError('资源字节段越界：' + relative)
            stream.seek(offset)
            raw = stream.read(length)
        if len(raw) != length:
            raise ValueError('资源字节段读取不完整：' + relative)
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('发布资源校验失败：' + relative)
        return raw

    def materialize(self, reference, directory):
        """Extract only the selected resource and dependencies for local rendering."""
        base, _ = self.selection(reference)
        rows = self.resolve(base)
        if len(rows) != 1:
            raise ValueError('渲染资源必须唯一')
        row = rows[0]
        if self.unavailable_dependencies(row['file'], set()):
            raise ValueError('渲染资源依赖不完整')
        target = Path(directory).resolve()
        if target.exists() and (not target.is_dir() or any(target.iterdir())):
            raise ValueError('提取目录须为空目录或新目录')
        # Validate the complete dependency closure before creating any file.
        pending = {}
        def collect(file):
            if file in pending:
                return
            pending[file] = self.verified_bytes(file)
            for dependency in self.by_file.get(file, {}).get('dependencies', []):
                collect(dependency)
        collect(row['file'])
        destinations = {}
        for file, raw in pending.items():
            destination = (target / file).resolve()
            if not destination.is_relative_to(target) or destination == target or destination in destinations:
                raise ValueError('提取路径越界或重复')
            destinations[destination] = raw
        if any(parent in destinations for path in destinations for parent in path.parents):
            raise ValueError('提取路径存在文件与目录冲突')
        for destination, raw in destinations.items():
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
        return target / row['file']

    def verified_text(self, relative):
        return self.verified_bytes(relative).decode('utf-8')

    def path(self, relative):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root / 'assets'):
            raise ValueError('读取路径必须位于模板库内')
        return path

    def resolve(self, reference):
        rows = [r for r in self.rows
                if reference == r['file'] or reference in r['ids']]
        if not rows:
            raise ValueError('未找到资源；使用 match 返回的 reference 或稳定 ID')
        return rows

    def style_summary(self, row):
        profile = row.get('style_profile')
        if not profile:
            return {'primary': '', 'tags': [], 'status': 'unknown', 'evidence_level': 'insufficient'}
        if profile.get('source_sha256') != hashlib.sha256(self.verified_bytes(row['file'])).hexdigest():
            raise ValueError('整页风格索引已过期：' + row['file'])
        self.verified_bytes(row['file'])
        dependencies = profile.get('dependency_sha256', {})
        if set(dependencies) != set(row.get('dependencies', [])):
            raise ValueError('整页风格依赖记录过期：' + row['file'])
        for file, expected in dependencies.items():
            if hashlib.sha256(self.verified_bytes(file)).hexdigest() != expected:
                raise ValueError('整页风格依赖缺失或已变更：' + file)
            self.verified_bytes(file)
        if not set(profile['tags']).issubset(self.manifest.get('style_schema', {}).get('tags', [])):
            raise ValueError('整页风格含未知标签：' + row['file'])
        return {k: profile[k] for k in ('primary', 'tags', 'status', 'evidence_level')}

    def index_status(self, row):
        index = row.get('screen_index', {})
        valid = index.get('status') == 'verified_structure'
        return {'has_screen_index': valid, 'screen_count': len(index.get('screens', [])) if valid else 0,
                'screen_index_status': index.get('status', 'not_indexed'),
                'has_page_style': bool(row.get('style_profile'))}

    def unique_file(self, reference):
        rows = self.resolve(reference)
        if len(rows) != 1:
            raise ValueError('模板范围须使用唯一ID或确切文件路径')
        return rows[0]['file']

    def describe(self, reference):
        base, selection = self.selection(reference)
        rows = self.resolve(base)
        for row in rows:
            self.verified_text(row['file'])
            self.style_summary(row)
        return {'resources': [dict({k:v for k,v in row.items() if k != 'screen_index'}, index_status=self.index_status(row)) for row in rows], 'selection': selection, 'note': '元数据仅来自已发布正文，不补造缺失catalog字段；完整约束与实现必须read。'}

    def catalog(self):
        return {'categories': sorted({r['category'] for r in self.rows if r['group']=='构图'}),
                'groups': list(GROUPS), 'screen_schema': self.manifest.get('screen_schema', {}),
                'indexed_templates': sum(bool(r.get('screen_index')) for r in self.rows),
                'style_schema': self.manifest.get('style_schema', {}),
                'styled_templates': sum(bool(r.get('style_profile')) for r in self.rows)}

    def screens(self, row):
        index = row.get('screen_index')
        if not index:
            return []
        if index.get('status') != 'verified_structure':
            return []
        content = self.verified_text(row['file'])
        if index.get('source_sha256') != hashlib.sha256(self.verified_bytes(row['file'])).hexdigest():
            raise ValueError('屏级索引过期，来源已变更：' + row['file'])
        recorded = index.get('dependency_sha256', {})
        if set(recorded) != set(row.get('dependencies', [])):
            raise ValueError('屏级依赖记录过期：' + row['file'])
        for file, expected in recorded.items():
            self.verified_bytes(file)
            if hashlib.sha256(self.verified_bytes(file)).hexdigest() != expected:
                raise ValueError('屏级依赖已变更：' + file)
        items = index['screens']
        ids = {item['id'] for item in items}
        if len(ids) != len(items):
            raise ValueError('屏级索引存在重复 ID')
        locators = ScreenLocators(content)
        for item in items:
            selectors = [item['selector']] + [s for r in item.get('regions', []) for s in r['selectors']]
            for selector in selectors:
                if locators.counts.get(selector) != 1:
                    raise ValueError('屏定位必须唯一且存在：' + selector)
            if not set(item['required_sections']).issubset(ids):
                raise ValueError('屏级依赖未登记：' + item['id'])
        return items

    def selection(self, reference):
        if '::' not in reference:
            return reference, None
        base, section = reference.rsplit('::', 1)
        rows = self.resolve(base)
        if len(rows) != 1:
            raise ValueError('屏引用须指定唯一模板文件或唯一 ID')
        row = rows[0]
        found = [s for s in self.screens(row) if s['id'] == section]
        if not found:
            raise ValueError('未找到已核验屏：' + section)
        return base, dict(found[0], scope='screen', source_file=row['file'],
            source_sha256=row['screen_index']['source_sha256'],
            note='返回完整来源供读取；仅所选屏及required_sections构成采用范围。不得把整页背景和相邻内容直接裁掉。')

    def match(self, group, query='', category='', limit=10, scope='page', purpose='', layout='', offset=0,
              style=None, style_mode='prefer', template='', prefer_template=''):
        if group not in GROUPS:
            raise ValueError('未知资源类型')
        if not 1 <= limit <= 50 or offset < 0:
            raise ValueError('limit 必须在 1–50 之间，offset不得为负')
        if scope not in ('page', 'screen'):
            raise ValueError('scope须为page或screen')
        category = category.strip()
        categories = self.catalog()['categories']
        if group == '构图' and category not in categories:
            raise ValueError('未知或缺失分类；合法分类：' + '、'.join(categories))
        if (scope == 'screen' or purpose or layout) and group != '构图':
            raise ValueError('屏级条件只用于构图')
        style = [style] if isinstance(style, str) else list(style or [])
        if style_mode not in ('prefer', 'required'):
            raise ValueError('风格模式须为prefer或required')
        if style_mode == 'required' and not style:
            raise ValueError('限定风格时须提供style')
        if set(style) - set(self.manifest.get('style_schema', {}).get('tags', [])):
            raise ValueError('未知风格；请先查看catalog的style_schema')
        if (style or template or prefer_template) and group != '构图':
            raise ValueError('整页风格和模板范围只用于构图')
        source_file = self.unique_file(template) if template else ''
        preferred_file = self.unique_file(prefer_template) if prefer_template else ''
        schema = self.manifest.get('screen_schema', {})
        if purpose and purpose not in schema.get('purposes', []):
            raise ValueError('未知屏用途；请先查看catalog')
        if layout and layout not in schema.get('layouts', []) and layout not in schema.get('layout_parents', {}):
            raise ValueError('未知布局；请先查看catalog')
        words = list(dict.fromkeys(w for w in re.split(r'[\s,，、]+', norm(query)) if w))
        supplied = {word: {term for term in word.split('|') if term} for word in words}
        if any(not terms for terms in supplied.values()):
            raise ValueError('同义词组不能为空')
        alternatives = {word:set(terms) for word,terms in supplied.items()}
        expansions=[]
        for word in words:
            for family in ALIASES:
                if supplied[word].intersection(family):alternatives[word].update(family)
            if alternatives[word]!=supplied[word]:expansions.append({'from':word,'alternatives':sorted(alternatives[word]-supplied[word])})
        pool=[r for r in self.rows if r['group']==group and r['role']!='overview'
              and (group!='构图' or r['category'] in (category,'通用'))]
        if source_file:
            pool=[r for r in pool if r['file']==source_file]
        indexed=sum(self.index_status(r)['has_screen_index'] for r in pool)
        style_eligible=0
        indexed_style_eligible=0
        hits=[]
        for row in pool:
            summary=self.style_summary(row)
            style_match=bool(set(style).intersection(summary['tags'])) and summary['status']!='unknown'
            if style and style_mode=='required' and not style_match:
                continue
            style_eligible+=1
            indexed_style_eligible+=int(self.index_status(row)['has_screen_index'])
            base={k:v for k,v in row.items() if k not in ('screen_index','style_profile')}
            base.update(style_summary=summary,index_status=self.index_status(row),
                ranking={'name_match':True,'style_match':style_match,'same_source':row['file']==preferred_file if preferred_file else False})
            choices=self.screens(row) if scope=='screen' or purpose or layout else [None]
            matching=[]
            for screen in choices:
                if screen:
                    if purpose and purpose not in screen['purposes']:continue
                    allowed=schema.get('layout_parents',{}).get(layout,[layout])
                    if layout and not set(allowed).intersection(screen['layouts']):continue
                    tags=list(screen['layouts'])
                    tags += [parent for parent,children in schema.get('layout_parents',{}).items() if set(children).intersection(tags)]
                    name=norm(' '.join([screen['title'],*screen['purposes'],*tags]))
                else:name=norm(row['name'])
                matched={w:sorted(t for t in alternatives[w] if t in name) for w in words}
                name_match=all(matched.values())
                if not screen and not name_match:
                    search_tags=[norm(tag) for tag in row.get('search_tags', [])]
                    matched={w:sorted(t for t in alternatives[w]
                        if t in name or any(t in tag for tag in search_tags)) for w in words}
                if not all(matched.values()):continue
                base['ranking']['name_match']=name_match
                terms=sorted({t for values in matched.values() for t in values})
                if scope=='screen':
                    hits.append(dict(base,screen=screen,screen_ref=row['ids'][0]+'::'+screen['id'],
                        matched_words=terms,match_type='结构条件' if purpose or layout else '关键词' if words else '目录浏览'))
                elif screen:matching.append(screen['id'])
                else:hits.append(dict(base,matched_words=terms,match_type='关键词' if words else '目录浏览'))
            if scope=='page' and matching:
                hits.append(dict(base,matched_screen_ids=matching,match_type='同屏结构条件',
                    note='表示该模板内这些屏满足条件，不表示整页均满足。'))
        hits.sort(key=lambda r:(int(not r['ranking']['name_match']),int(group=='构图' and r['category']!=category),
            int(bool(style) and not r['ranking']['style_match']),
            int(bool(preferred_file) and not r['ranking']['same_source']),
            r['name'],r['file'],r.get('screen',{}).get('order',0)))
        style_hits=sum(r['ranking']['style_match'] for r in hits)
        empty_reason=('' if hits else 'style_filter_no_match' if style and style_mode=='required' and not style_eligible
            else 'no_screen_index_in_scope' if (scope=='screen' or purpose or layout) and not indexed_style_eligible
            else 'structure_or_keyword_no_match')
        end=offset+limit
        return {'group':group,'category':category if group=='构图' else '通用','scope':scope,
                'query':query,'purpose':purpose,'layout':layout,'words':words,'pool_count':len(pool),
                'style':style,'style_mode':style_mode,'template':template,'prefer_template':prefer_template,
                'total':len(hits),'offset':offset,'has_more':end<len(hits),'next_offset':end if end<len(hits) else None,
                'candidates':hits[offset:end],'expansions':expansions,
                'coverage':{'indexed_templates':indexed,'eligible_templates':len(pool),
                    'styled_templates':sum(bool(r.get('style_profile')) for r in pool)},
                'diagnostics':{'empty_reason':empty_reason,'style_matched_candidates':style_hits,
                    'style_preference_unmet':bool(style and style_mode=='prefer' and hits and not style_hits),
                    'unindexed_templates':sum(not self.index_status(r)['has_screen_index'] for r in pool)},
                'note':'结构条件必须在同一屏成立；满幅为上位布局，满幅场景为精确类型。先满足结构条件，再按同题材、风格命中、同源优先排序；风格默认不排除其他结构候选。风格来源为整页，tentative仅为结构倾向；不保证选型最优。屏索引仅核验结构，未索引模板不代表不适配。采用前describe/read屏引用并遵守跨屏依赖。'}

    def expand_html(self, content, row):
        def inline(match):
            file = html.unescape(match[1])
            if file not in row.get('dependencies', []):
                raise ValueError('HTML样式未登记为依赖：' + file)
            attrs = re.search(r'data-style-attributes="([^"]*)"', match[0])
            attrs = html.unescape(attrs[1]) if attrs else ''
            return '<style' + attrs + '>' + self.verified_text(file) + '</style>'
        return re.sub(r'<link\b[^>]*\bdata-published-style="([^"]+)"[^>]*>', inline, content, flags=re.I)

    def read(self, reference, max_chars=2000000):
        if max_chars < 1:
            raise ValueError('max-chars必须为正整数')
        base, selection = self.selection(reference)
        rows = self.resolve(base)
        if len(rows) != 1:
            return {'variants': rows, 'note': '存在多个完整变体；选择准确reference后read，不自动挑选。'}
        row = rows[0]
        if row.get('blocked_dependencies'):
            raise ValueError('资源依赖尚不完整：' + json.dumps(row['blocked_dependencies'], ensure_ascii=False))
        content = self.verified_text(row['file'])
        if row['file'].endswith('.html'):
            content = self.expand_html(content, row)
        visited = {row['file']}
        dependencies = []
        def collect(file):
            if file in visited:
                return
            visited.add(file)
            dependency = self.by_file.get(file, {})
            if dependency.get('blocked_dependencies'):
                raise ValueError('间接依赖尚不完整：' + file)
            raw = self.verified_bytes(file)
            if Path(file).suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.woff', '.woff2', '.ttf', '.otf', '.ttc'):
                dependencies.append({'file': file, 'sha256': self.manifest['files'][file],
                                     'bytes': len(raw), 'kind': 'binary', 'local_path': str(self.path(file))})
                return
            value = raw.decode('utf-8')
            if file.endswith('.html'):
                value = self.expand_html(value, dependency)
            dependencies.append({'file': file, 'sha256': self.manifest['files'][file], 'content': value})
            for child in dependency.get('dependencies', []):
                collect(child)
        for file in row.get('dependencies', []):
            collect(file)
        self.style_summary(row)
        result = dict({k:v for k,v in row.items() if k != 'screen_index'}, index_status=self.index_status(row), content=content, selection=selection, rule_dependencies=dependencies,
            note='完整HTML恢复共享样式原顺序；规则附已校验依赖。metadata-only只含说明，不代表参考图片存在。样例与素材槽须按任务适配，不能当正式成品。')
        if len(json.dumps(result, ensure_ascii=False)) > max_chars:
            raise ValueError('完整资源与依赖超过max-chars，请提高预算；没有截断输出')
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    commands = parser.add_subparsers(dest='command', required=True)
    match = commands.add_parser('match')
    match.add_argument('query', nargs='?', default='')
    match.add_argument('--group', choices=GROUPS, required=True)
    match.add_argument('--category', default='')
    match.add_argument('--limit', type=int, default=10)
    match.add_argument('--offset', type=int, default=0)
    match.add_argument('--scope', choices=('page','screen'), default='page')
    match.add_argument('--purpose', default='')
    match.add_argument('--layout', default='')
    match.add_argument('--style', action='append', default=[], help='整页风格，可重复；任一命中，默认仅优先')
    match.add_argument('--style-mode', choices=('prefer','required'), default='prefer', help='required仅用于明确限定风格')
    match.add_argument('--template', default='', help='限定唯一模板ID或文件，不把模板名当屏关键词')
    match.add_argument('--prefer-template', default='', help='已选模板ID或文件，仅优先同源，不排除其他来源')
    commands.add_parser('catalog')
    describe = commands.add_parser('describe'); describe.add_argument('reference')
    read = commands.add_parser('read'); read.add_argument('reference')
    read.add_argument('--max-chars', type=int, default=2000000)
    args = parser.parse_args(argv)
    try:
        lib = TemplateLibrary(args.root)
        if args.command == 'catalog':
            result = lib.catalog()
        elif args.command == 'match':
            result = lib.match(**{k: v for k, v in vars(args).items() if k not in ('root', 'command')})
        elif args.command == 'describe':
            result = lib.describe(args.reference)
        else:
            result = lib.read(args.reference, args.max_chars)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
