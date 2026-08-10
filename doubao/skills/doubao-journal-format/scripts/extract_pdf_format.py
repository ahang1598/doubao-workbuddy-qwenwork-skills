#!/usr/bin/env python3
"""
Extract text-first PDF format evidence for DOCX formatting.

This script does not treat PDF as a Word template. It first checks whether the
PDF is a selectable-text format guide, such as author instructions or submission
guidelines. Explicit text rules are the only style rules written to rules JSON.
Coordinate/layout evidence may select the single-column or double-column
fallback variant, but it must not define fonts, sizes, color, spacing, or other
Word style properties.

- evidence JSON for audit/debug;
- optional rules JSON that can be passed to format_docx.py --rules-json.

Tools are optional and are used when available:
- PyMuPDF / fitz: span-level fonts, sizes, colors, flags, coordinates.
- pdfplumber: character/table-line evidence.
- pdftotext: layout text and text-extraction sanity check.
- pdffonts: embedded/substituted font inventory.
- mutool: structural metadata when available.
"""

import argparse
import collections
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys


ROLE_ORDER = [
    'title',
    'author',
    'affiliation',
    'abstract',
    'keywords',
    'heading1',
    'heading2',
    'heading3',
    'body',
    'figure_caption',
    'table_caption',
    'references_heading',
    'reference_item',
    'equation',
    'english_title',
    'english_author',
    'english_affiliation',
    'english_abstract',
    'english_keywords',
]

TEXT_RULE_ROLE_ORDER = [
    'references_heading',
    'reference_item',
    'figure_caption',
    'table_caption',
    'english_keywords',
    'english_abstract',
    'english_title',
    'english_author',
    'english_affiliation',
    'metadata',
    'citation_format',
    'keywords',
    'abstract',
    'heading1',
    'heading2',
    'heading3',
    'title',
    'author',
    'affiliation',
    'body',
]

SIZE_MAP = {
    '初号': 84, '小初': 72, '一号': 52, '小一': 48, '二号': 44, '小二': 36,
    '三号': 32, '小三': 30, '四号': 28, '小四': 24, '五号': 21, '小五': 18,
    '六号': 15, '小六': 13, '七号': 11, '八号': 10,
}

FONT_WORDS = [
    'Times New Roman', 'Arial', 'Calibri', 'Cambria', 'Courier New',
    '宋体', '黑体', '楷体', '仿宋', '微软雅黑', 'SimSun', 'SimHei', 'KaiTi', 'FangSong',
]

FORMAT_GUIDE_MARKERS = [
    '投稿须知', '来稿要求', '投稿指南', '作者指南', '撰稿要求', '写作模板',
    '模板要求', '格式要求', '论文格式', '参考文献格式', '参考文献引用须知',
    'Instructions for Authors', 'Author Guidelines', 'Manuscript Preparation',
]

TEXT_RULE_MARKERS = [
    '正文', '题名', '标题', '摘要', '关键词', '作者', '单位', '图题', '图注',
    '表题', '表注', '参考文献', '三线表', '公式', '上标', '字号', '字体',
    '行距', '悬挂缩进', '首行缩进', 'Times New Roman', '宋体', '黑体',
]

DECORATIVE_WATERMARK_RE = re.compile(
    r'^(样\s*例|示\s*例|样\s*张|sample|draft|watermark|proof|copy)$',
    re.I,
)


def run_cmd(cmd, timeout=30):
    exe = shutil.which(cmd[0])
    if not exe:
        return {'available': False, 'command': cmd, 'output': '', 'error': 'not found'}
    try:
        result = subprocess.run(
            [exe] + cmd[1:],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        return {
            'available': True,
            'command': [exe] + cmd[1:],
            'returncode': result.returncode,
            'output': result.stdout,
            'error': result.stderr,
        }
    except Exception as exc:
        return {'available': True, 'command': [exe] + cmd[1:], 'output': '', 'error': str(exc)}


def safe_import(name):
    try:
        return __import__(name)
    except Exception:
        return None


def normalize_font_name(font):
    font = str(font or '').strip()
    if '+' in font and re.match(r'^[A-Z]{6}\+', font):
        font = font.split('+', 1)[1]
    replacements = {
        'TimesNewRomanPSMT': 'Times New Roman',
        'TimesNewRomanPS-BoldMT': 'Times New Roman',
        'TimesNewRomanPS-ItalicMT': 'Times New Roman',
        'TimesNewRomanPS-BoldItalicMT': 'Times New Roman',
        'TimesNewRoman': 'Times New Roman',
        'SimSun': '宋体',
        'SimSun-ExtB': '宋体',
        'SimHei': '黑体',
        'KaiTi': '楷体',
        'FangSong': '仿宋',
    }
    if font in replacements:
        return replacements[font]
    return font


def font_family(font):
    font = normalize_font_name(font)
    for token in ('-BoldItalic', '-BoldOblique', '-Italic', '-Oblique', '-Bold', ',Bold', ',Italic'):
        font = font.replace(token, '')
    for token in ('BoldItalic', 'BoldOblique', 'Italic', 'Oblique', 'Bold'):
        font = font.replace(token, '')
    return font.strip('- ,') or normalize_font_name(font)


def contains_cjk(text):
    return bool(re.search(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]', text or ''))


def contains_latin(text):
    return bool(re.search(r'[A-Za-z]', text or ''))


def text_kind(text):
    if contains_cjk(text):
        return 'cjk'
    if contains_latin(text):
        return 'latin'
    return 'other'


def is_bold_font(font):
    return bool(re.search(r'(bold|black|heavy|semibold|demibold)', str(font or ''), re.I))


def is_italic_font(font):
    return bool(re.search(r'(italic|oblique)', str(font or ''), re.I))


def color_to_hex(value):
    if value is None:
        return None
    try:
        value = int(value)
    except Exception:
        return None
    return f'{value & 0xFFFFFF:06X}'


def clean_text(text):
    return re.sub(r'\s+', ' ', str(text or '')).strip()


def clean_pdf_text_for_rules(text):
    text = str(text or '').replace('\r', '\n')
    text = re.sub(r'[ \t]+', ' ', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def extract_plain_text_from_pymupdf(pdf_path, max_pages=None):
    fitz = safe_import('fitz')
    if fitz is None:
        return '', {'available': False, 'error': 'PyMuPDF/fitz not importable'}
    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        return '', {'available': True, 'error': str(exc)}
    try:
        limit = min(len(doc), max_pages or len(doc))
        pages = []
        for idx in range(limit):
            pages.append(doc[idx].get_text('text') or '')
        text = clean_pdf_text_for_rules('\n'.join(pages))
        return text, {'available': True, 'page_count': len(doc), 'extracted_pages': limit, 'char_count': len(text)}
    finally:
        doc.close()


def split_rule_sentences(text):
    normalized = clean_pdf_text_for_rules(text)
    parts = re.split(r'(?<=[。！？；;])\s*|\n+', normalized)
    merged = []
    buf = ''
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(part) < 18 and re.match(r'^\d+(?:\.\d+)*\s*\S+', part):
            if buf:
                merged.append(buf.strip())
            buf = part
            continue
        if buf and len(buf) < 80:
            buf = f'{buf} {part}'
        else:
            if buf:
                merged.append(buf.strip())
            buf = part
    if buf:
        merged.append(buf.strip())
    return [item for item in merged if item]


def format_guide_score(text):
    haystack = text or ''
    marker_hits = sum(1 for marker in FORMAT_GUIDE_MARKERS if re.search(re.escape(marker), haystack, re.I))
    rule_hits = sum(1 for marker in TEXT_RULE_MARKERS if re.search(re.escape(marker), haystack, re.I))
    section_hits = len(re.findall(r'\b\d+(?:\.\d+)*\s*(?:来稿要求|插图|照片|表|公式|参考文献|摘要|关键词|题目|作者|单位)', haystack))
    return marker_hits * 3 + min(rule_hits, 12) + section_hits * 2


def normalize_text_for_rules(text):
    return re.sub(r'\s+', '', text or '').lower()


def role_from_text_rule(text):
    if re.search(
        r'^(?:author\s+guidelines|instructions?\s+for\s+authors?|author\s+instructions?|'
        r'manuscript\s+preparation|submission\s+guidelines?)\s*$',
        (text or '').strip(),
        re.I,
    ):
        return None
    normalized = normalize_text_for_rules(text)
    if any(key in normalized for key in ('文章正文', '正文', 'bodytext', 'maintext', 'mainbody')):
        return 'body'
    checks = [
        ('references_heading', ['参考文献标题', 'referencesheading']),
        ('reference_item', ['参考文献格式', '参考文献', 'references', '文献']),
        ('figure_caption', ['图题', '图注', 'figurecaption']),
        ('table_caption', ['表题', '表注', 'tablecaption']),
        ('english_keywords', ['英文关键词', 'englishkeywords']),
        ('english_abstract', ['英文摘要', 'englishabstract']),
        ('english_title', ['英文题名', '英文标题', 'englishtitle']),
        ('english_author', ['英文作者', 'englishauthor']),
        ('english_affiliation', ['英文单位', '英文机构', 'englishaffiliation']),
        ('metadata', ['中图分类号', '文献标志码', '文章编号', 'pacs']),
        ('citation_format', ['引用格式', 'citationformat']),
        ('keywords', ['关键词', '关键字', 'keywords']),
        ('abstract', ['摘要', 'abstract']),
        ('heading1', ['一级标题', '1级标题', 'heading1']),
        ('heading2', ['二级标题', '2级标题', 'heading2']),
        ('heading3', ['三级标题', '3级标题', 'heading3']),
        ('title', ['题名', '标题', '论文题目', '题目', 'title']),
        ('author', ['作者', 'author']),
        ('affiliation', ['单位', '机构', 'affiliation']),
        ('body', ['正文', '文章正文', 'body', 'maintext']),
    ]
    for role, keys in checks:
        if any(key.lower() in normalized for key in keys):
            return role
    return None


def parse_size_from_text_rule(text):
    for name, half_point in SIZE_MAP.items():
        if name in text:
            return str(half_point)
    arabic_size_map = {
        '0': 84, '1': 52, '2': 44, '3': 32, '4': 28,
        '5': 21, '6': 15, '7': 11, '8': 10,
    }
    match = re.search(r'(小)?\s*([1-8])\s*号', text)
    if match:
        small, num = match.groups()
        if small:
            small_map = {'1': 48, '2': 36, '3': 30, '4': 24, '5': 18, '6': 13}
            return str(small_map.get(num, arabic_size_map[num]))
        return str(arabic_size_map[num])
    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:-|–|—)?\s*(?:pt|磅|point(?:s)?(?:\s+font)?)', text, re.I)
    if match:
        return str(int(round(float(match.group(1)) * 2)))
    return None


def parse_fonts_from_text_rule(text):
    fonts = {}
    for font in FONT_WORDS:
        if font.lower() not in text.lower():
            continue
        if re.search(r'(英|西|latin|ascii|hansi)[^。；;，,]{0,12}' + re.escape(font), text, re.I):
            fonts['ascii'] = font
            fonts['hAnsi'] = font
        elif re.search(re.escape(font) + r'[^。；;，,]{0,12}(英|西|latin|ascii|hansi)', text, re.I):
            fonts['ascii'] = font
            fonts['hAnsi'] = font
        elif re.search(r'(中|中文|汉字|eastAsia)[^。；;，,]{0,12}' + re.escape(font), text, re.I):
            fonts['eastAsia'] = font
        elif re.search(re.escape(font) + r'[^。；;，,]{0,12}(中|中文|汉字|eastAsia)', text, re.I):
            fonts['eastAsia'] = font
        elif re.search(r'[A-Za-z]', font):
            fonts.setdefault('ascii', font)
            fonts.setdefault('hAnsi', font)
        else:
            fonts.setdefault('eastAsia', font)
    return fonts


def parse_alignment_from_text_rule(text):
    if re.search(r'居中|居中对齐|align(?:ed|ment)?\s*[:=]?\s*center|center(?:ed)?\s+align', text, re.I):
        return 'center'
    if re.search(r'两端对齐|align(?:ed|ment)?\s*[:=]?\s*justify|justified', text, re.I):
        return 'both'
    if re.search(r'右对齐|居右|align(?:ed|ment)?\s*[:=]?\s*right|right(?:-|\s+)?align(?:ed|ment)?', text, re.I):
        return 'right'
    if re.search(r'左对齐|居左|align(?:ed|ment)?\s*[:=]?\s*left|left(?:-|\s+)?align(?:ed|ment)?', text, re.I):
        return 'left'
    return None


def parse_bold_from_text_rule(text):
    if re.search(r'不加粗|非加粗|not\s+bold', text, re.I):
        return False
    if re.search(r'加粗|bold', text, re.I):
        return True
    return None


def parse_line_spacing_from_text_rule(text):
    match = re.search(r'(?:固定值|exact(?:ly)?)\s*(\d+(?:\.\d+)?)\s*(?:磅|pt)', text, re.I)
    if match:
        return {'line': str(int(round(float(match.group(1)) * 20))), 'lineRule': 'exact'}
    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:倍行距|倍)', text)
    if match:
        return {'line': str(int(round(float(match.group(1)) * 240))), 'lineRule': 'auto'}
    if re.search(r'1\.?5\s*(?:倍行距|倍)|一倍半', text):
        return {'line': '360', 'lineRule': 'auto'}
    if re.search(r'单倍行距|single\s+line', text, re.I):
        return {'line': '240', 'lineRule': 'auto'}
    return {}


def parse_indent_from_text_rule(text):
    if re.search(r'悬挂缩进\s*2\s*(?:字符|字)', text):
        return {'left': '420', 'hanging': '420'}
    match = re.search(r'悬挂缩进\s*(\d+(?:\.\d+)?)\s*(?:磅|pt)', text, re.I)
    if match:
        hanging = str(int(round(float(match.group(1)) * 20)))
        return {'left': hanging, 'hanging': hanging}
    if re.search(r'首行缩进\s*2\s*(?:字符|字)', text):
        return {'firstLine': '420'}
    match = re.search(r'首行缩进\s*(\d+(?:\.\d+)?)\s*(?:磅|pt)', text, re.I)
    if match:
        return {'firstLine': str(int(round(float(match.group(1)) * 20)))}
    return {}


def text_rule_has_format_property(text):
    return bool(
        parse_size_from_text_rule(text)
        or parse_fonts_from_text_rule(text)
        or parse_alignment_from_text_rule(text)
        or parse_bold_from_text_rule(text) is not None
        or parse_line_spacing_from_text_rule(text)
        or parse_indent_from_text_rule(text)
        or re.search(r'三线表|上标|公式.*编号|编号.*公式|图题|表题', text)
    )


def merge_rule_property(current, key, value):
    if isinstance(value, dict) and isinstance(current.get(key), dict):
        current[key].update(value)
    else:
        current[key] = value


def merge_rule_into_role(roles, role, rule):
    current = roles.setdefault(role, {})
    for key, value in (rule or {}).items():
        merge_rule_property(current, key, value)


def merge_visual_supplement_into_text_rules(text_rules, visual_rules):
    merged = json.loads(json.dumps(text_rules or {}, ensure_ascii=False))
    supplement = {}
    # Coarse visual may identify roles and broad alignment only. Typography,
    # emphasis, indentation, and spacing must come from explicit text rules
    # or fallback.
    allowed_visual_keys = {'align'}
    for role, visual_rule in (visual_rules or {}).items():
        current = merged.setdefault(role, {})
        role_supplement = {}
        for key, value in (visual_rule or {}).items():
            if key in ('source', 'confidence'):
                continue
            if key not in allowed_visual_keys:
                continue
            if key not in current and value not in (None, ''):
                current[key] = value
                role_supplement[key] = value
        if role_supplement:
            if not current.get('source'):
                current['source'] = 'pdf_visual_supplement'
            if current.get('source') == 'pdf_visual_supplement':
                current['confidence'] = 'low'
            current.setdefault('visual_supplement', {}).update(role_supplement)
            supplement[role] = role_supplement
    return merged, supplement


def parse_prose_rule_sentence(sentence):
    role = role_from_text_rule(sentence)
    if not role or not text_rule_has_format_property(sentence):
        return None, None
    rule = {'source': 'pdf_text_rules', 'confidence': 'medium'}
    size = parse_size_from_text_rule(sentence)
    fonts = parse_fonts_from_text_rule(sentence)
    align = parse_alignment_from_text_rule(sentence)
    bold = parse_bold_from_text_rule(sentence)
    line_spacing = parse_line_spacing_from_text_rule(sentence)
    indent = parse_indent_from_text_rule(sentence)
    if size:
        rule['size'] = size
    if fonts:
        rule['fonts'] = fonts
    if align:
        rule['align'] = align
    if bold is not None:
        rule['bold'] = bold
    if line_spacing:
        rule['spacing'] = line_spacing
    if indent:
        rule['indent'] = indent
    if role == 'table_caption' and re.search(r'表.*(上方|上面|置于表上)', sentence):
        rule['caption_position'] = 'above'
    if role == 'figure_caption' and re.search(r'图.*(下方|下面|置于图下)', sentence):
        rule['caption_position'] = 'below'
    return role, rule


def add_multi_role_text_rules(sentence, roles, matched):
    if re.search(r'图题.*表题|表题.*图题|图和表|图、表|图表', sentence):
        shared = {'source': 'pdf_text_rules', 'confidence': 'medium'}
        if re.search(r'中英文对照|中、英文对照|Chinese\s+and\s+English', sentence, re.I):
            shared['bilingual'] = True
        if len(shared) > 2:
            for role in ('figure_caption', 'table_caption'):
                merge_rule_into_role(roles, role, shared)
            matched.append({
                'role': 'figure_caption/table_caption',
                'text': sentence[:500],
                'rule': shared,
            })
    if re.search(r'表采用三线表|三线表', sentence):
        merge_rule_into_role(roles, 'table_caption', {'source': 'pdf_text_rules', 'confidence': 'medium'})


def parse_structural_postprocess_rule(sentence):
    text = sentence or ''
    normalized = re.sub(r'\s+', ' ', text).strip()
    clauses = [
        clause.strip()
        for clause in re.split(r'(?<=[。；;])\s*|(?<=[.!?])\s+(?=[A-Z])', text)
        if clause.strip()
    ] or [text]
    structural = {}
    operations = []

    def add_structural(section, key, value):
        structural.setdefault(section, {})[key] = value

    def add_op(op):
        op.setdefault('source', 'explicit_pdf_text_rule')
        op.setdefault('source_text', normalized[:500])
        operations.append(op)

    if re.search(r'(tables?|表(?:格)?)[^。；;]{0,80}(after|following|at\s+the\s+end|参考文献后|文后|置于文后|放在文后)', text, re.I) or re.search(r'(after|following)[^。；;]{0,40}(references?)[^。；;]{0,40}(tables?)', text, re.I):
        add_structural('placement', 'tables_after_references', True)
        add_op({'type': 'move_tables_after_references', 'include_caption': True})
    if re.search(r'(figures?|illustrations?|图(?:片|件)?)[^。；;]{0,80}(after|following|at\s+the\s+end|参考文献后|文后|置于文后|放在文后)', text, re.I) or re.search(r'(after|following)[^。；;]{0,40}(references?)[^。；;]{0,40}(figures?)', text, re.I):
        add_structural('placement', 'figures_after_references', True)
        add_op({'type': 'move_figures_after_references', 'include_caption': True})

    if re.search(r'(citation|reference citation|引用|引文|文献标注|参考文献.*引用)', text, re.I):
        citation_rule = {}
        if re.search(r'(within|in|用|置于)?\s*(parentheses|round brackets|圆括号|圆括弧|小括号)|\(\s*\d+\s*\)', text, re.I):
            citation_rule['marker'] = 'parentheses'
        if re.search(r'italic|italics|斜体', text, re.I):
            citation_rule['italic'] = True
        if re.search(r'superscript|上标', text, re.I):
            citation_rule['superscript'] = True
        if citation_rule.get('marker'):
            structural['citation_format'] = citation_rule
            op = {'type': 'normalize_body_citations', 'to': 'parentheses'}
            if citation_rule.get('italic') is not None:
                op['italic'] = bool(citation_rule.get('italic'))
            if citation_rule.get('superscript') is not None:
                op['superscript'] = bool(citation_rule.get('superscript'))
            add_op(op)

    reference_prefix_clause = next((
        clause for clause in clauses
        if re.search(r'(reference list|bibliography|参考文献(?:列表|条目)?)[^。；;.!?]{0,80}(prefix|number|numbers|numbered|numbering|number style|编号|序号)', clause, re.I)
        and not re.search(r'(citation numbers?|reference citations?|body citations?|正文引用|引文|文献标注)', clause, re.I)
    ), None)
    if reference_prefix_clause:
        style = None
        if re.search(r'round|parentheses|圆括号|小括号|\(\s*1\s*\)', reference_prefix_clause, re.I):
            style = 'round'
        elif re.search(r'square|brackets|方括号|\[\s*1\s*\]', reference_prefix_clause, re.I):
            style = 'square'
        elif re.search(r'plain|bare|arabic\s+(?:number|numbers|numerals?)|阿拉伯数字|^1\s', reference_prefix_clause, re.I):
            style = 'plain'
        if style:
            structural['reference_prefix'] = {'style': style}
            add_op({'type': 'normalize_reference_prefixes', 'style': style, 'renumber': False, 'add_missing': False})

    fig_match = re.search(r'(figure legends?|figure captions?|figures?|图题|图注)[^。；;]{0,80}(?:begin|start|prefix|标为|编号为|写作|采用)[^。；;]{0,40}(Fig\.|Figure|图)\s*\.?\s*1?\s*([:：.]?)', text, re.I)
    if fig_match:
        prefix = fig_match.group(2)
        separator = fig_match.group(3) or ':'
        if prefix.lower().startswith('fig'):
            prefix = 'Fig.' if prefix.lower().startswith('fig.') or prefix.lower() == 'fig' else 'Figure'
        structural['figure_caption'] = {'prefix': prefix, 'separator': separator}
        add_op({'type': 'normalize_figure_captions', 'prefix': prefix, 'separator': separator, 'first_sentence_bold': False})

    if re.search(r'(figure legends?|figure captions?|图题|图注)[^。；;]{0,80}(first sentence|第一句|首句)[^。；;]{0,40}(bold|加粗)', text, re.I):
        structural.setdefault('figure_caption', {})['first_sentence_bold'] = True
        add_op({'type': 'normalize_figure_captions', 'first_sentence_bold': True})
    if re.search(r'(table legends?|table captions?|表题|表注)[^。；;]{0,80}(first sentence|第一句|首句)[^。；;]{0,40}(bold|加粗)', text, re.I):
        structural.setdefault('table_caption', {})['first_sentence_bold'] = True
        add_op({'type': 'normalize_table_captions', 'first_sentence_bold': True})

    table_match = re.search(r'(table legends?|table captions?|tables?|表题|表注)[^。；;]{0,80}(?:begin|start|prefix|标为|编号为|写作|采用)[^。；;]{0,40}(Table|Tab\.|表)\s*\.?\s*1?\s*([:：.]?)', text, re.I)
    if table_match:
        prefix = table_match.group(2)
        separator = table_match.group(3) or ':'
        if prefix.lower().startswith('tab'):
            prefix = 'Table'
        structural['table_caption'] = {'prefix': prefix, 'separator': separator}
        add_op({'type': 'normalize_table_captions', 'prefix': prefix, 'separator': separator, 'first_sentence_bold': False})

    if any(
        re.search(r'(references?|reference list|bibliography|参考文献)[^。；;.!?]{0,80}(sequential|consecutive|按顺序|连续编号|依次编号|顺序编号)', clause, re.I)
        and not re.search(r'(citation numbers?|reference citations?|body citations?|正文引用|引文|文献标注)', clause, re.I)
        for clause in clauses
    ):
        structural.setdefault('reference_prefix', {})['renumber'] = True
        add_op({'type': 'normalize_reference_prefixes', 'style': 'plain_dot', 'renumber': True, 'add_missing': False})

    return structural, operations


def merge_structural_rule(current, update):
    for key, value in (update or {}).items():
        if isinstance(value, dict) and isinstance(current.get(key), dict):
            current[key].update(value)
        else:
            current[key] = value


def merge_postprocess_operation(operations, op):
    if not isinstance(op, dict):
        return
    marker = json.dumps(op, ensure_ascii=False, sort_keys=True)
    existing = {json.dumps(item, ensure_ascii=False, sort_keys=True) for item in operations}
    if marker not in existing:
        operations.append(op)


def extract_text_format_rules(text):
    score = format_guide_score(text)
    sentences = split_rule_sentences(text)
    roles = {}
    matched = []
    structural = {}
    postprocess_operations = []
    for sentence in sentences:
        role, rule = parse_prose_rule_sentence(sentence)
        if role and rule:
            merge_rule_into_role(roles, role, rule)
            matched.append({'role': role, 'text': sentence[:500], 'rule': rule})
        add_multi_role_text_rules(sentence, roles, matched)
        structural_rule, ops = parse_structural_postprocess_rule(sentence)
        if structural_rule:
            merge_structural_rule(structural, structural_rule)
            matched.append({'role': 'postprocess', 'text': sentence[:500], 'rule': structural_rule})
        for op in ops:
            merge_postprocess_operation(postprocess_operations, op)
        if re.search(r'三线表', sentence):
            structural.setdefault('table', {})['border_model'] = 'three_line'
            matched.append({'role': 'table_body', 'text': sentence[:500], 'rule': {'table_border_model': 'three_line'}})
        if re.search(r'公式.*(?:编号|阿拉伯数字)|(?:编号|阿拉伯数字).*公式', sentence):
            structural.setdefault('equation', {})['numbering'] = 'arabic_parentheses_right'
            matched.append({'role': 'equation', 'text': sentence[:500], 'rule': {'numbering': 'arabic_parentheses_right'}})
        if re.search(r'参考文献.*上标|文献号.*上标|引用参考文献.*上标', sentence):
            structural.setdefault('superscript', {})['reference_citation'] = True
            matched.append({'role': 'body', 'text': sentence[:500], 'rule': {'reference_citation_superscript': True}})
        if re.search(r'文献.*(?:按正文中引文出现|先后顺序|出现的先后顺序)', sentence):
            structural.setdefault('reference_numbering', {})['order'] = 'citation_order'
    is_text_guide = (
        (score >= 8 and (len(matched) >= 2 or bool(roles)))
        or bool(roles)
        or bool(postprocess_operations)
    )
    rules_json = {
        '_meta': {
            'source_type': 'text_rules' if is_text_guide else 'pdf_visual_inference',
            'format_source_type': 'text_rules' if is_text_guide else 'pdf_visual_inference',
            'pdf_text_rule_score': score,
            'pdf_text_rule_count': len(matched),
            'pdf_text_rule_route': 'primary_text_rules_first' if is_text_guide else 'visual_inference_primary',
        },
        'roles': roles,
    }
    if structural:
        rules_json['_meta']['structural_rules'] = structural
    if postprocess_operations:
        rules_json['_meta']['postprocess_operations'] = postprocess_operations
        rules_json['postprocess_operations'] = postprocess_operations
    return {
        'is_text_format_guide': is_text_guide,
        'score': score,
        'char_count': len(text or ''),
        'matched_rules': matched[:80],
        'roles': roles,
        'structural_rules': structural,
        'postprocess_operations': postprocess_operations,
        'rules_json': rules_json,
    }


def median(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    return statistics.median(values)


def most_common(values):
    values = [v for v in values if v not in (None, '')]
    if not values:
        return None
    return collections.Counter(values).most_common(1)[0][0]


def half_points(size):
    if size is None:
        return None
    return str(int(round(float(size) * 2)))


def twips(points):
    if points is None:
        return None
    return str(int(round(float(points) * 20)))


def get_pymupdf_evidence(pdf_path, max_pages):
    fitz = safe_import('fitz')
    if fitz is None:
        return {'available': False, 'error': 'PyMuPDF/fitz not importable', 'pages': []}
    pages = []
    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        return {'available': True, 'error': str(exc), 'pages': []}
    try:
        page_count = len(doc)
        limit = min(page_count, max_pages or page_count)
        for page_index in range(limit):
            page = doc[page_index]
            page_dict = page.get_text('dict')
            page_lines = []
            page_spans = []
            for block in page_dict.get('blocks', []):
                if block.get('type') != 0:
                    continue
                for line in block.get('lines', []):
                    spans = []
                    text_parts = []
                    for span in line.get('spans', []):
                        text = clean_text(span.get('text'))
                        if not text:
                            continue
                        item = {
                            'text': text,
                            'text_kind': text_kind(text),
                            'bbox': [round(x, 3) for x in span.get('bbox', [])],
                            'font': normalize_font_name(span.get('font')),
                            'font_family': font_family(span.get('font')),
                            'size': round(float(span.get('size') or 0), 3),
                            'color': color_to_hex(span.get('color')),
                            'flags': span.get('flags'),
                            'bold_inferred': is_bold_font(span.get('font')),
                            'italic_inferred': is_italic_font(span.get('font')),
                        }
                        spans.append(item)
                        page_spans.append(item)
                        text_parts.append(text)
                    if not spans:
                        continue
                    bbox = [
                        min(s['bbox'][0] for s in spans),
                        min(s['bbox'][1] for s in spans),
                        max(s['bbox'][2] for s in spans),
                        max(s['bbox'][3] for s in spans),
                    ]
                    page_lines.append({
                        'text': clean_text(' '.join(text_parts)),
                        'bbox': [round(x, 3) for x in bbox],
                        'font': most_common([s['font_family'] for s in spans]),
                        'size': round(float(median([s['size'] for s in spans]) or 0), 3),
                        'color': most_common([s['color'] for s in spans]),
                        'bold_inferred': any(s['bold_inferred'] for s in spans),
                        'italic_inferred': any(s['italic_inferred'] for s in spans),
                        'span_count': len(spans),
                        'spans': spans,
                    })
            pages.append({
                'index': page_index,
                'width': round(float(page.rect.width), 3),
                'height': round(float(page.rect.height), 3),
                'line_count': len(page_lines),
                'span_count': len(page_spans),
                'lines': page_lines,
                'spans_sample': page_spans[:200],
            })
        return {'available': True, 'page_count': page_count, 'pages': pages}
    finally:
        doc.close()


def get_pdfplumber_evidence(pdf_path, max_pages):
    pdfplumber = safe_import('pdfplumber')
    if pdfplumber is None:
        return {'available': False, 'error': 'pdfplumber not importable'}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages = []
            limit = min(len(pdf.pages), max_pages or len(pdf.pages))
            for i in range(limit):
                page = pdf.pages[i]
                chars = page.chars or []
                pages.append({
                    'index': i,
                    'width': page.width,
                    'height': page.height,
                    'char_count': len(chars),
                    'font_sample': sorted(list({normalize_font_name(c.get('fontname')) for c in chars if c.get('fontname')}))[:50],
                    'size_sample': sorted(list({round(float(c.get('size') or 0), 3) for c in chars if c.get('size')}))[:50],
                    'rect_count': len(page.rects or []),
                    'curve_count': len(page.curves or []),
                    'line_count': len(page.lines or []),
                })
            return {'available': True, 'pages': pages}
    except Exception as exc:
        return {'available': True, 'error': str(exc)}


def get_pdftotext_evidence(pdf_path, max_pages):
    cmd = ['pdftotext', '-layout']
    if max_pages:
        cmd += ['-f', '1', '-l', str(max_pages)]
    cmd += [pdf_path, '-']
    layout = run_cmd(cmd)
    bbox = run_cmd(['pdftotext', '-bbox-layout', '-f', '1', '-l', str(max_pages or 3), pdf_path, '-'])
    return {
        'layout': {
            'available': layout.get('available'),
            'returncode': layout.get('returncode'),
            'error': layout.get('error'),
            'text_sample': (layout.get('output') or '')[:8000],
        },
        'bbox_layout': {
            'available': bbox.get('available'),
            'returncode': bbox.get('returncode'),
            'error': bbox.get('error'),
            'xml_sample': (bbox.get('output') or '')[:8000],
        },
    }


def get_pdffonts_evidence(pdf_path):
    result = run_cmd(['pdffonts', pdf_path])
    lines = (result.get('output') or '').splitlines()
    fonts = []
    for line in lines[2:]:
        parts = line.split()
        if len(parts) < 6:
            continue
        fonts.append({
            'raw': line,
            'name': normalize_font_name(parts[0]),
            'type': parts[1] if len(parts) > 1 else '',
            'encoding': parts[2] if len(parts) > 2 else '',
            'embedded': parts[3] if len(parts) > 3 else '',
            'subset': parts[4] if len(parts) > 4 else '',
        })
    return {
        'available': result.get('available'),
        'returncode': result.get('returncode'),
        'error': result.get('error'),
        'fonts': fonts,
        'raw': (result.get('output') or '')[:8000],
    }


def get_mutool_evidence(pdf_path):
    info = run_cmd(['mutool', 'info', pdf_path])
    return {
        'available': info.get('available'),
        'returncode': info.get('returncode'),
        'error': info.get('error'),
        'info_sample': (info.get('output') or '')[:8000],
    }


def all_lines(pymupdf_evidence):
    lines = []
    for page in (pymupdf_evidence or {}).get('pages', []):
        width = page.get('width') or 0
        height = page.get('height') or 0
        for line in page.get('lines', []):
            item = dict(line)
            item['page'] = page.get('index')
            item['page_width'] = width
            item['page_height'] = height
            for span in item.get('spans') or []:
                span['page'] = page.get('index')
            lines.append(item)
    return lines


def text_width(line):
    bbox = line.get('bbox') or [0, 0, 0, 0]
    return max(0, bbox[2] - bbox[0])


def line_text_length(line):
    return len(re.sub(r'\s+', '', clean_text(line.get('text'))))


def role_span_records(role_lines):
    records = []
    for line in role_lines or []:
        spans = line.get('spans') or []
        if spans:
            records.extend(spans)
        else:
            records.append({
                'text': line.get('text') or '',
                'text_kind': text_kind(line.get('text') or ''),
                'font_family': line.get('font'),
                'size': line.get('size'),
                'color': line.get('color'),
                'bold_inferred': line.get('bold_inferred'),
                'italic_inferred': line.get('italic_inferred'),
            })
    return records


def weighted_common(values):
    counter = collections.Counter()
    for value, weight in values:
        if value in (None, ''):
            continue
        counter[value] += max(1, int(weight or 1))
    return counter.most_common(1)[0][0] if counter else None


def infer_slot_fonts_from_spans(spans, role_lines):
    latin = []
    cjk = []
    other = []
    for span in spans:
        text = clean_text(span.get('text') or '')
        weight = len(re.sub(r'\s+', '', text)) or 1
        family = span.get('font_family') or font_family(span.get('font'))
        kind = span.get('text_kind') or text_kind(text)
        if kind == 'cjk':
            cjk.append((family, weight))
        elif kind == 'latin':
            latin.append((family, weight))
        else:
            other.append((family, weight))
    fallback_font = weighted_common(latin + cjk + other) or most_common([l.get('font') for l in role_lines])
    latin_font = weighted_common(latin) or fallback_font
    cjk_font = weighted_common(cjk)
    if not cjk_font:
        any_cjk = any(contains_cjk(l.get('text') or '') for l in role_lines)
        if any_cjk:
            cjk_font = '宋体'
        else:
            cjk_font = '宋体'
    return {
        'ascii': latin_font,
        'hAnsi': latin_font,
        'eastAsia': cjk_font,
    }


def weighted_property_coverage(spans, prop):
    total = 0
    covered = 0
    for span in spans:
        text = clean_text(span.get('text') or '')
        weight = len(re.sub(r'\s+', '', text)) or 1
        total += weight
        if span.get(prop):
            covered += weight
    return covered / float(total or 1)


def representative_color_from_spans(spans):
    values = []
    total = 0
    for span in spans:
        text = clean_text(span.get('text') or '')
        weight = len(re.sub(r'\s+', '', text)) or 1
        total += weight
        values.append((span.get('color'), weight))
    color = weighted_common(values)
    if not color:
        return None
    color_weight = sum(weight for value, weight in values if value == color)
    if color_weight / float(total or 1) < 0.80:
        return None
    if is_near_black_color(color):
        return '000000'
    return color


def is_near_black_color(color):
    if not color:
        return False
    try:
        value = int(str(color), 16)
    except ValueError:
        return False
    r = (value >> 16) & 0xFF
    g = (value >> 8) & 0xFF
    b = value & 0xFF
    return max(r, g, b) <= 48


def is_decorative_or_watermark_line(line):
    text = clean_text(line.get('text'))
    compact = re.sub(r'\s+', '', text)
    if not compact:
        return True
    size = float(line.get('size') or 0)
    page_width = float(line.get('page_width') or 0)
    page_height = float(line.get('page_height') or 0)
    bbox = line.get('bbox') or [0, 0, 0, 0]
    if DECORATIVE_WATERMARK_RE.match(text) or DECORATIVE_WATERMARK_RE.match(compact):
        return True
    if size >= 40 and line_text_length(line) <= 10:
        return True
    if page_width and page_height and size >= 28:
        line_center_x = (bbox[0] + bbox[2]) / 2.0
        line_center_y = (bbox[1] + bbox[3]) / 2.0
        if (
            abs(line_center_x - page_width / 2.0) < page_width * 0.25
            and page_height * 0.20 < line_center_y < page_height * 0.80
        ):
            return True
    return False


def likely_affiliation_text(text):
    return bool(re.search(
        r'(University|College|School|Department|Institute|Hospital|Laborator|Center|'
        r'大学|学院|医院|科室|研究所|实验室|中心|邮编|北京|上海|广州|China)',
        text or '',
        re.I,
    ))


def likely_author_list_text(text):
    stripped = clean_text(text)
    if not stripped or len(stripped) > 180:
        return False
    if likely_affiliation_text(stripped):
        return False
    if re.search(r'(通信作者|基金项目|Corresponding author|Email|摘要|Abstract|关键词|Key words)', stripped, re.I):
        return False
    chinese_name = r'[\u4e00-\u9fff]{2,4}\s*(?:\d+|[，,、])'
    english_name = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b'
    separator_count = len(re.findall(r'[，,、;；]|\band\b', stripped, re.I))
    marker_count = len(re.findall(r'(?<=[\u4e00-\u9fffA-Za-z])\d+(?=[，,、;；\s]|$)', stripped))
    if separator_count >= 1 and (re.search(chinese_name, stripped) or len(re.findall(english_name, stripped)) >= 2):
        return True
    if marker_count >= 2 and len(re.findall(r'[\u4e00-\u9fff]{2,4}', stripped)) >= 2:
        return True
    if len(re.findall(r'[\u4e00-\u9fff]{2,4}\s*\d?', stripped)) >= 3 and separator_count >= 2:
        return True
    return False


def likely_front_matter_noise(text):
    return bool(re.search(
        r'^(通信作者|基金项目|Corresponding author|基金|收稿日期|DOI|Email)',
        clean_text(text),
        re.I,
    ))


def robust_body_size(lines):
    body_candidates = [
        l for l in lines
        if not is_decorative_or_watermark_line(l) and line_text_length(l) > 40
    ]
    size_counts = collections.Counter(round(float(l.get('size') or 0), 1) for l in body_candidates)
    if size_counts:
        return size_counts.most_common(1)[0][0]
    clean_sizes = [
        float(l.get('size') or 0) for l in lines
        if not is_decorative_or_watermark_line(l) and float(l.get('size') or 0) > 0
    ]
    return median(clean_sizes) or 10


def robust_heading_max_size(lines, body_size):
    sizes = []
    for line in lines:
        if is_decorative_or_watermark_line(line):
            continue
        text = clean_text(line.get('text'))
        if not text or likely_front_matter_noise(text):
            continue
        size = float(line.get('size') or 0)
        if size <= 0 or size > max(36, body_size * 3):
            continue
        sizes.append(size)
    return max(sizes) if sizes else body_size


def infer_alignment(line, page_lines):
    bbox = line.get('bbox') or [0, 0, 0, 0]
    width = line.get('page_width') or 0
    if not width:
        return None
    content_left = min((l.get('bbox') or [0])[0] for l in page_lines if l.get('bbox'))
    content_right = max((l.get('bbox') or [0, 0, 0])[2] for l in page_lines if l.get('bbox'))
    page_center = width / 2
    line_center = (bbox[0] + bbox[2]) / 2
    if abs(line_center - page_center) < max(8, width * 0.015) and text_width(line) < (content_right - content_left) * 0.9:
        return 'center'
    if abs(bbox[0] - content_left) < 8 and abs(bbox[2] - content_right) < 18:
        return 'both'
    if abs(bbox[2] - content_right) < 8 and bbox[0] > content_left + 24:
        return 'right'
    return 'left'


def infer_role(line, page_lines, max_size, body_size, after_references=False, allow_front_matter=True):
    text = clean_text(line.get('text'))
    lower = text.lower()
    page = line.get('page') or 0
    size = float(line.get('size') or 0)
    bbox = line.get('bbox') or [0, 0, 0, 0]
    page_height = line.get('page_height') or 9999

    if is_decorative_or_watermark_line(line):
        return None

    if re.match(r'^(abstract|摘要)\b[:：]?', lower, re.I):
        return 'abstract'
    if re.match(r'^(keywords?|key words|关键词)\b[:：]?', lower, re.I):
        return 'keywords'
    if re.match(r'^(references|reference|参考文献)\s*$', lower, re.I):
        return 'references_heading'
    if after_references and len(text) > 12:
        return 'reference_item'
    if re.match(r'^(fig\.?|figure|图)\s*\d+', lower, re.I):
        return 'figure_caption'
    if re.match(r'^(table|表)\s*\d+', lower, re.I):
        return 'table_caption'
    if re.match(r'^\(?\d+(\.\d+){0,2}\)?\s+\S+', text):
        level = text.split()[0].count('.') + 1
        return f'heading{min(level, 3)}'
    if allow_front_matter:
        if page == 0 and bbox[1] < page_height * 0.20 and size >= body_size + 3 and not likely_front_matter_noise(text):
            return 'title'
        if page == 0 and bbox[1] < page_height * 0.45 and len(text) < 240:
            if likely_affiliation_text(text):
                return 'affiliation'
        if page == 0 and bbox[1] < page_height * 0.40 and size >= body_size - 1 and len(text) < 180:
            if likely_author_list_text(text):
                return 'author'
        if page == 0 and bbox[1] < page_height * 0.55 and likely_front_matter_noise(text):
            return 'metadata'
    if size >= body_size + 1.5 and len(text) < 100:
        return 'heading1'
    return 'body'


def first_page_front_matter_role(line, state, body_size):
    text = clean_text(line.get('text'))
    if not text or is_decorative_or_watermark_line(line):
        return None
    page = line.get('page') or 0
    if page != 0 or state.get('done'):
        return None
    bbox = line.get('bbox') or [0, 0, 0, 0]
    page_height = line.get('page_height') or 9999
    if bbox[1] > page_height * 0.92:
        state['done'] = True
        return None
    if re.match(r'^(关键词|关键字)', text, re.I):
        state['step'] = 'english_title'
        return 'keywords'
    if re.match(r'^(Key\s*words?|Keywords)\b', text, re.I):
        state['done'] = True
        return 'english_keywords'
    if re.match(r'^(【?\s*摘要\s*】?|【?\s*Abstract\s*】?|Abstract\b)', text, re.I):
        if re.match(r'^(【?\s*Abstract\s*】?|Abstract\b)', text, re.I):
            state['step'] = 'english_keywords'
            return 'english_abstract'
        state['step'] = 'chinese_abstract'
        return 'abstract'
    step = state.get('step') or 'title'
    size = float(line.get('size') or 0)
    if step == 'title':
        if size >= body_size + 2 and not likely_front_matter_noise(text):
            state['step'] = 'title_or_author'
            return 'title'
        return None
    if step == 'title_or_author':
        if size >= body_size + 2 and not likely_author_list_text(text):
            return 'title'
        if likely_author_list_text(text) or (len(text) < 180 and not likely_affiliation_text(text) and not likely_front_matter_noise(text)):
            state['step'] = 'affiliation'
            return 'author'
    if step == 'affiliation':
        if likely_affiliation_text(text):
            return 'affiliation'
        if likely_front_matter_noise(text):
            return 'metadata'
        if len(text) < 220 and not re.match(r'^(【?摘要】?|Abstract\b|关键词)', text, re.I):
            return 'metadata'
    if step == 'chinese_abstract':
        if re.match(r'^(关键词|关键字)', text, re.I):
            state['step'] = 'english_title'
            return 'keywords'
        return 'abstract'
    if step == 'english_title':
        if size >= body_size + 2 and contains_latin(text) and not likely_author_list_text(text):
            return 'english_title'
        if likely_author_list_text(text) and contains_latin(text):
            state['step'] = 'english_affiliation'
            return 'english_author'
    if step == 'english_affiliation':
        if likely_affiliation_text(text) and contains_latin(text):
            return 'english_affiliation'
        if re.match(r'^(【?\s*Abstract\s*】?|Abstract\b)', text, re.I):
            state['step'] = 'english_keywords'
            return 'english_abstract'
        if re.match(r'^(Key\s*words?|Keywords)\b', text, re.I):
            state['done'] = True
            return 'english_keywords'
        if len(text) < 260 and contains_latin(text):
            return 'english_affiliation'
    if step == 'english_keywords':
        if re.match(r'^(Key\s*words?|Keywords)\b', text, re.I):
            state['done'] = True
            return 'english_keywords'
        return 'english_abstract'
    return None


def role_rule(role, role_lines, page_lines_by_page):
    if not role_lines:
        return None
    aligns = [
        infer_alignment(l, page_lines_by_page.get(l.get('page'), []))
        for l in role_lines
    ]
    rule = {
        'source': 'pdf_visual_inference',
        'confidence': 'low',
        'visual_granularity': 'role_alignment_only',
    }
    align = most_common(aligns)
    if align:
        rule['align'] = align
    return rule


def infer_roles(lines):
    if not lines:
        return {}, {}
    lines = [l for l in lines if not is_decorative_or_watermark_line(l)]
    if not lines:
        return {}, {}
    body_size = robust_body_size(lines)
    max_size = robust_heading_max_size(lines, body_size)
    page_lines_by_page = collections.defaultdict(list)
    for line in lines:
        page_lines_by_page[line.get('page')].append(line)

    grouped = collections.defaultdict(list)
    after_references = False
    front_state = {'step': 'title', 'done': False}
    for line in sorted(lines, key=lambda x: (x.get('page') or 0, (x.get('bbox') or [0, 0])[1], (x.get('bbox') or [0])[0])):
        role = first_page_front_matter_role(line, front_state, body_size)
        if role is None:
            role = infer_role(
                line,
                page_lines_by_page.get(line.get('page'), []),
                max_size,
                body_size,
                after_references=after_references,
                allow_front_matter=not front_state.get('done'),
            )
        if role is None:
            continue
        grouped[role].append(line)
        if role == 'references_heading':
            after_references = True

    rules = {}
    candidates = {}
    for role in ROLE_ORDER:
        selected = grouped.get(role, [])
        if role == 'body':
            selected = [l for l in selected if len(clean_text(l.get('text'))) > 25]
        if role in ('title', 'author', 'affiliation', 'references_heading'):
            selected = selected[:4]
        if not selected:
            continue
        rule = role_rule(role, selected[:80], page_lines_by_page)
        if rule:
            rules[role] = rule
            candidates[role] = [
                {
                    'page': l.get('page'),
                    'text': clean_text(l.get('text'))[:240],
                    'bbox': l.get('bbox'),
                    'font': l.get('font'),
                    'size': l.get('size'),
                    'bold_inferred': l.get('bold_inferred'),
                }
                for l in selected[:12]
            ]
    return rules, candidates


def pdf_column_candidate_line(line, body_size):
    text = clean_text(line.get('text'))
    compact = re.sub(r'\s+', '', text)
    if len(compact) < 18:
        return False
    if is_decorative_or_watermark_line(line):
        return False
    if likely_front_matter_noise(text) or likely_author_list_text(text) or likely_affiliation_text(text):
        return False
    if re.match(r'^(abstract|摘要|keywords?|key words|关键词|references|参考文献|fig\.?|figure|图|table|表)\b', text, re.I):
        return False
    bbox = line.get('bbox') or []
    if len(bbox) < 4:
        return False
    width = float(line.get('page_width') or 0)
    if not width:
        return False
    line_width = text_width(line)
    if line_width < width * 0.12:
        return False
    line_center = (float(bbox[0]) + float(bbox[2])) / 2.0
    page_center = width / 2.0
    if abs(line_center - page_center) < width * 0.08 and line_width < width * 0.45:
        return False
    size = float(line.get('size') or 0)
    if body_size and size > body_size + 2.0 and len(compact) < 80:
        return False
    return True


def page_column_geometry_vote(page_lines, body_size):
    if len(page_lines) < 18:
        return {
            'vote': 1,
            'confidence': 'low',
            'reason': 'too_few_page_lines',
            'line_count': len(page_lines),
        }
    width = max((line.get('page_width') or 0) for line in page_lines) or 0
    if not width:
        return {'vote': 1, 'confidence': 'low', 'reason': 'missing_page_width'}
    candidate_lines = [line for line in page_lines if pdf_column_candidate_line(line, body_size)]
    if len(candidate_lines) < max(10, len(page_lines) * 0.25):
        return {
            'vote': 1,
            'confidence': 'low',
            'reason': 'too_few_body_like_lines',
            'line_count': len(page_lines),
            'candidate_count': len(candidate_lines),
        }
    page_mid = width / 2.0
    gutter_min = max(18.0, width * 0.045)
    left_band = []
    right_band = []
    crossing_lines = []
    for line in candidate_lines:
        bbox = line.get('bbox') or [0, 0, 0, 0]
        x0 = float(bbox[0])
        x1 = float(bbox[2])
        line_width = x1 - x0
        if x0 < page_mid - gutter_min and x1 > page_mid + gutter_min:
            crossing_lines.append(line)
        elif x0 < page_mid - gutter_min:
            left_band.append(line)
        elif x0 > page_mid + gutter_min * 0.5:
            right_band.append(line)

    left_count = len(left_band)
    right_count = len(right_band)
    crossing_count = len(crossing_lines)
    enough_each_side = (
        left_count >= max(6, len(candidate_lines) * 0.28)
        and right_count >= max(6, len(candidate_lines) * 0.22)
    )
    if not enough_each_side:
        return {
            'vote': 1,
            'confidence': 'low',
            'reason': 'missing_balanced_left_right_body_bands',
            'line_count': len(page_lines),
            'candidate_count': len(candidate_lines),
            'left_band_count': left_count,
            'right_band_count': right_count,
            'crossing_count': crossing_count,
        }

    left_right_edge = median([float((line.get('bbox') or [0, 0, 0])[2]) for line in left_band]) or 0
    right_left_edge = median([float((line.get('bbox') or [0])[0]) for line in right_band]) or 0
    gutter = right_left_edge - left_right_edge
    right_text_widths = [text_width(line) for line in right_band]
    left_text_widths = [text_width(line) for line in left_band]
    right_width_med = median(right_text_widths) or 0
    left_width_med = median(left_text_widths) or 0
    right_cluster = median([float((line.get('bbox') or [0])[0]) for line in right_band]) or 0
    left_cluster = median([float((line.get('bbox') or [0])[0]) for line in left_band]) or 0
    crossing_ratio = crossing_count / float(max(1, len(candidate_lines)))
    if gutter < gutter_min:
        vote = 1
        confidence = 'low'
        reason = 'no_clear_gutter_between_columns'
    elif crossing_ratio > 0.18:
        vote = 1
        confidence = 'low'
        reason = 'many_body_lines_cross_column_boundary'
    elif right_width_med < width * 0.18 or left_width_med < width * 0.18:
        vote = 1
        confidence = 'low'
        reason = 'one_side_text_band_too_narrow'
    elif (right_cluster - left_cluster) < width * 0.30:
        vote = 1
        confidence = 'low'
        reason = 'left_right_clusters_too_close'
    else:
        vote = 2
        confidence = 'medium'
        reason = 'balanced_body_bands_with_clear_gutter'
    return {
        'vote': vote,
        'confidence': confidence,
        'reason': reason,
        'line_count': len(page_lines),
        'candidate_count': len(candidate_lines),
        'left_band_count': left_count,
        'right_band_count': right_count,
        'crossing_count': crossing_count,
        'crossing_ratio': round(crossing_ratio, 3),
        'left_cluster': round(left_cluster, 2),
        'right_cluster': round(right_cluster, 2),
        'gutter': round(gutter, 2),
        'gutter_min': round(gutter_min, 2),
        'left_text_width_median': round(left_width_med, 2),
        'right_text_width_median': round(right_width_med, 2),
    }


def pdf_column_cluster_candidate_line(line, body_size):
    """Looser candidate for cross-page column-start aggregation.

    Page-level detection intentionally uses body-like lines only. Sample-issue
    PDFs often have sparse prose on each page because formulas, figures, tables,
    and captions fragment the text. For fallback column selection we may use
    coordinate evidence from short lines too, but only to find stable left/right
    column starts across pages; these lines never define style properties.
    """
    text = clean_text(line.get('text'))
    compact = re.sub(r'\s+', '', text)
    if len(compact) < 5:
        return False
    if is_decorative_or_watermark_line(line):
        return False
    if likely_front_matter_noise(text):
        return False
    bbox = line.get('bbox') or []
    if len(bbox) < 4:
        return False
    width = float(line.get('page_width') or 0)
    height = float(line.get('page_height') or 0)
    if not width:
        return False
    x0, y0, x1, y1 = [float(v) for v in bbox[:4]]
    line_width = x1 - x0
    if line_width < width * 0.025:
        return False
    if height and (y1 < height * 0.04 or y0 > height * 0.965):
        return False
    size = float(line.get('size') or 0)
    if body_size and size > body_size + 3.0 and len(compact) < 90:
        return False
    return True


def cluster_key(value, step=4.0):
    try:
        return round(round(float(value) / step) * step, 1)
    except Exception:
        return None


def lines_near_x0(lines, x0, tolerance=10.0):
    return [
        line for line in lines
        if abs(float((line.get('bbox') or [0])[0]) - float(x0)) <= tolerance
    ]


def global_column_cluster_vote(page_groups, body_size):
    """Detect stable double-column geometry across sparse sample pages.

    This supplements page voting. It still requires more than left-edge clusters:
    both left/right starts must recur across multiple pages, the gap between the
    left-column right edge and right-column start must be real, and full-width
    crossing text must be rare outside front matter.
    """
    all_candidates = []
    by_page = {}
    for page, page_lines in page_groups.items():
        page_candidates = [
            line for line in page_lines
            if pdf_column_cluster_candidate_line(line, body_size)
        ]
        if page_candidates:
            by_page[page] = page_candidates
            all_candidates.extend(page_candidates)
    if len(all_candidates) < 32:
        return {
            'vote': 1,
            'confidence': 'low',
            'reason': 'too_few_global_column_candidates',
            'candidate_count': len(all_candidates),
        }
    width = median([float(line.get('page_width') or 0) for line in all_candidates]) or 0
    if not width:
        return {'vote': 1, 'confidence': 'low', 'reason': 'missing_page_width'}
    page_mid = width / 2.0
    split_gap = max(12.0, width * 0.025)
    left_lines = []
    right_lines = []
    crossing_lines = []
    for line in all_candidates:
        x0, _, x1, _ = [float(v) for v in (line.get('bbox') or [0, 0, 0, 0])[:4]]
        if x0 < page_mid - split_gap and x1 > page_mid + split_gap:
            crossing_lines.append(line)
        elif x0 < page_mid - split_gap:
            left_lines.append(line)
        elif x0 > page_mid + split_gap * 0.5:
            right_lines.append(line)
    if len(left_lines) < 16 or len(right_lines) < 16:
        return {
            'vote': 1,
            'confidence': 'low',
            'reason': 'missing_global_left_or_right_band',
            'candidate_count': len(all_candidates),
            'left_band_count': len(left_lines),
            'right_band_count': len(right_lines),
            'crossing_count': len(crossing_lines),
        }
    left_clusters = collections.Counter(
        cluster_key((line.get('bbox') or [0])[0]) for line in left_lines
    )
    right_clusters = collections.Counter(
        cluster_key((line.get('bbox') or [0])[0]) for line in right_lines
    )
    left_clusters.pop(None, None)
    right_clusters.pop(None, None)
    if not left_clusters or not right_clusters:
        return {'vote': 1, 'confidence': 'low', 'reason': 'missing_column_start_clusters'}
    left_cluster, left_cluster_count = left_clusters.most_common(1)[0]
    right_cluster, right_cluster_count = right_clusters.most_common(1)[0]
    left_cluster_lines = lines_near_x0(left_lines, left_cluster)
    right_cluster_lines = lines_near_x0(right_lines, right_cluster)
    left_pages = {line.get('page') for line in left_cluster_lines}
    right_pages = {line.get('page') for line in right_cluster_lines}
    pages_with_both = sorted(left_pages & right_pages)
    left_right_edge = median([float((line.get('bbox') or [0, 0, 0])[2]) for line in left_cluster_lines]) or 0
    right_left_edge = median([float((line.get('bbox') or [0])[0]) for line in right_cluster_lines]) or 0
    gutter = right_left_edge - left_right_edge
    crossing_ratio = len(crossing_lines) / float(max(1, len(all_candidates)))
    cluster_distance = right_cluster - left_cluster
    min_cluster_count = max(12, int(len(all_candidates) * 0.035))
    if left_cluster_count < min_cluster_count or right_cluster_count < min_cluster_count:
        vote = 1
        confidence = 'low'
        reason = 'dominant_column_start_cluster_too_small'
    elif len(pages_with_both) < 2:
        vote = 1
        confidence = 'low'
        reason = 'column_start_clusters_not_repeated_across_pages'
    elif cluster_distance < width * 0.30:
        vote = 1
        confidence = 'low'
        reason = 'global_left_right_clusters_too_close'
    elif gutter < split_gap:
        vote = 1
        confidence = 'low'
        reason = 'global_no_clear_gutter_between_columns'
    elif crossing_ratio > 0.22:
        vote = 1
        confidence = 'low'
        reason = 'global_many_lines_cross_column_boundary'
    else:
        vote = 2
        confidence = 'medium' if len(pages_with_both) >= 3 else 'low'
        reason = 'stable_global_left_right_column_starts_with_gutter'
    return {
        'vote': vote,
        'confidence': confidence,
        'reason': reason,
        'candidate_count': len(all_candidates),
        'left_band_count': len(left_lines),
        'right_band_count': len(right_lines),
        'crossing_count': len(crossing_lines),
        'crossing_ratio': round(crossing_ratio, 3),
        'left_cluster': round(left_cluster, 2),
        'right_cluster': round(right_cluster, 2),
        'left_cluster_count': left_cluster_count,
        'right_cluster_count': right_cluster_count,
        'pages_with_both_column_starts': pages_with_both[:12],
        'gutter': round(gutter, 2),
        'gutter_min': round(split_gap, 2),
        'cluster_distance': round(cluster_distance, 2),
    }


def infer_column_count(lines):
    page_groups = collections.defaultdict(list)
    for line in lines or []:
        text = clean_text(line.get('text'))
        if not text or is_decorative_or_watermark_line(line):
            continue
        if len(re.sub(r'\s+', '', text)) < 8:
            continue
        bbox = line.get('bbox') or []
        if len(bbox) < 4:
            continue
        page_groups[line.get('page', 0)].append(line)

    page_votes = []
    details = []
    body_size = robust_body_size(lines or [])
    for page, page_lines in page_groups.items():
        detail = page_column_geometry_vote(page_lines, body_size)
        vote = detail.get('vote', 1)
        page_votes.append(vote)
        detail['page'] = page
        details.append(detail)

    two_col_votes = page_votes.count(2)
    one_col_votes = page_votes.count(1)
    page_vote_columns = 2 if two_col_votes >= max(2, math.ceil(len(page_votes) * 0.60)) else 1
    aggregate_detail = global_column_cluster_vote(page_groups, body_size)
    aggregate_columns = 2 if aggregate_detail.get('vote') == 2 else 1
    columns = 2 if page_vote_columns == 2 or aggregate_columns == 2 else 1
    if not page_votes:
        confidence = 'low'
    elif page_vote_columns == 2:
        confidence = 'medium'
    elif aggregate_columns == 2:
        confidence = aggregate_detail.get('confidence') or 'low'
    elif two_col_votes:
        confidence = 'low'
    else:
        confidence = 'medium'
    return {
        'columns': columns,
        'confidence': confidence,
        'method': 'pdf_body_band_gutter_geometry_with_global_cluster',
        'page_votes': page_votes,
        'two_column_votes': two_col_votes,
        'one_column_votes': one_col_votes,
        'aggregate_vote': aggregate_detail,
        'manual_override_hint': 'Use --body-cols when PDF column detection conflicts with the intended layout.',
        'details': details[:8],
    }


def build_evidence(pdf_path, max_pages):
    plain_text, text_extraction = extract_plain_text_from_pymupdf(pdf_path, max_pages)
    text_rule_evidence = extract_text_format_rules(plain_text)
    pymupdf_evidence = get_pymupdf_evidence(pdf_path, max_pages)
    lines = all_lines(pymupdf_evidence)
    visual_rules, candidates = infer_roles(lines)
    column_detection = infer_column_count(lines)
    base_rules_json = text_rule_evidence.get('rules_json') or {'roles': {}}
    rules_json = {
        '_meta': dict(base_rules_json.get('_meta') or {}),
        'roles': base_rules_json.get('roles') or {},
    }
    rules_json['_meta'].update({
        'source_type': 'text_rules',
        'format_source_type': 'text_rules',
        'original_source_type': 'pdf',
        'non_docx_source_kind': 'pdf',
        'non_docx_text_only_route': True,
        'non_docx_standard_fallback': True,
        'text_rule_source_only': True,
        'visual_style_rules_suppressed': True,
        'pdf_text_rule_route': 'text_rules_only_with_column_fallback',
        'fallback_columns': column_detection.get('columns') or 1,
        'source_column_detection': column_detection,
    })
    if text_rule_evidence.get('is_text_format_guide'):
        source_type = 'text_rules'
        confidence = 'medium'
        warning = (
            'PDF appears to be a selectable-text format guide. Explicit prose rules '
            'are used as style rules; missing properties are filled by the standard fallback. '
            'PDF layout evidence may select single/double-column fallback only. '
            'Recommend a native DOCX template or explicit text formatting instructions when exact Word styles are needed.'
        )
    else:
        source_type = 'text_rules'
        confidence = 'low'
        warning = (
            'PDF has no Word styles.xml, numbering.xml, section XML, or real paragraph styles. '
            'No PDF visual style properties are used; missing formatting is completed with the '
            'standard fallback, using detected columns when available. Recommend a native DOCX template or explicit text formatting instructions.'
        )
    return {
        'version': 1,
        'source_type': source_type,
        'confidence': confidence,
        'source_path': os.path.abspath(pdf_path),
        'warning': warning,
        'plain_text_extraction': text_extraction,
        'text_rule_evidence': text_rule_evidence,
        'tools': {
            'pymupdf': pymupdf_evidence,
            'pdfplumber': get_pdfplumber_evidence(pdf_path, max_pages),
            'pdftotext': get_pdftotext_evidence(pdf_path, max_pages),
            'pdffonts': get_pdffonts_evidence(pdf_path),
            'mutool': get_mutool_evidence(pdf_path),
        },
        'role_candidates': candidates,
        'roles': rules_json.get('roles') or {},
        'visual_roles': visual_rules,
        'column_detection': column_detection,
        'rules_json': rules_json,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description='Extract PDF text rules and fallback column metadata.')
    parser.add_argument('pdf', help='PDF format source')
    parser.add_argument('--out-json', required=True, help='Write full PDF evidence JSON')
    parser.add_argument('--rules-json', help='Write role rules JSON usable with format_docx.py --rules-json')
    parser.add_argument('--max-pages', type=int, default=8, help='Maximum PDF pages to inspect; default 8')
    args = parser.parse_args(argv)

    if not os.path.exists(args.pdf):
        print(f'PDF not found: {args.pdf}', file=sys.stderr)
        return 1

    evidence = build_evidence(args.pdf, args.max_pages)
    with open(args.out_json, 'w', encoding='utf-8') as f:
        json.dump(evidence, f, ensure_ascii=False, indent=2)
    if args.rules_json:
        with open(args.rules_json, 'w', encoding='utf-8') as f:
            json.dump(evidence.get('rules_json') or {'roles': {}}, f, ensure_ascii=False, indent=2)

    role_count = len((evidence.get('roles') or {}))
    print(f'Wrote PDF evidence: {args.out_json}')
    if args.rules_json:
        print(f'Wrote text-first rules JSON: {args.rules_json}')
    print(f'Inferred roles: {role_count}')
    print(f"Detected fallback columns: {(evidence.get('column_detection') or {}).get('columns') or 1}")
    if role_count == 0:
        print(
            'No explicit PDF text-format rules were inferred; downstream formatting should use '
            'the selected standard fallback variant and warn that the source was not DOCX.',
            file=sys.stderr,
        )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
