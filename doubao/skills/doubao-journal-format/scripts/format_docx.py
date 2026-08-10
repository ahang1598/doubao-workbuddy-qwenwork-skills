#!/usr/bin/env python3
"""
DOCX Journal Format Tool - 期刊排版工具
Apply journal template styles to a target DOCX document while preserving all content.

Features:
- Page setup (margins, paper size, columns)
- Headers & footers replacement
- Normal style font/size/alignment
- Document settings, font table, theme
- Preserves all content: formulas, images, OLE objects, tables
- Chinese/English bilingual font support

Usage:
    python3 format_docx.py --template template.docx --target paper.docx --output output.docx
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import glob
import xml.etree.ElementTree as ET
import zipfile
from functools import lru_cache

# WordprocessingML namespace
W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKG_REL_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'
M_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
WP_NS = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
A_NS = 'http://schemas.openxmlformats.org/drawingml/2006/main'
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
FALLBACK_OOXML_SPEC_PATH = os.path.join(SKILL_DIR, 'assets', 'fallback_ooxml_spec.json')

ROLE_STYLE_IDS = {
    'title': '1title',
    'author': '2author',
    'affiliation': '3affiliation',
    'abstract': '4abstract',
    'keywords': '5keywords',
    'heading1': '6heading1',
    'heading2': '7heading2',
    'heading3': '8heading3',
    'body': '9body',
    'figure_caption': '10figurecaption',
    'table_caption': '11tablecaption',
    'references_heading': '12referencesheading',
    'reference_item': '13referenceitem',
    'equation': '14equation',
    'english_title': '15englishtitle',
    'english_author': '16englishauthor',
    'english_affiliation': '17englishaffiliation',
    'english_abstract': '18englishabstract',
    'english_keywords': '19englishkeywords',
    'metadata': '20metadata',
    'citation_format': '21citationformat',
}

ROLE_DISPLAY_NAMES = {
    'title': '1title',
    'author': '2author',
    'affiliation': '3affiliation',
    'abstract': '4abstract',
    'keywords': '5keywords',
    'heading1': '6heading1',
    'heading2': '7heading2',
    'heading3': '8heading3',
    'body': '9body',
    'figure_caption': '10figurecaption',
    'table_caption': '11tablecaption',
    'references_heading': '12referencesheading',
    'reference_item': '13referenceitem',
    'equation': '14equation',
    'english_title': '15englishtitle',
    'english_author': '16englishauthor',
    'english_affiliation': '17englishaffiliation',
    'english_abstract': '18englishabstract',
    'english_keywords': '19englishkeywords',
    'metadata': '20metadata',
    'citation_format': '21citationformat',
}

TEXT_RULE_PRIORITY = (
    'user_rules > extracted_text_rules > source_column_detection_for_fallback_variant > '
    'bundled_OOXML_fallback > legacy_dictionary_fallback'
)
SOURCE_EVIDENCE_PRIORITIES = {
    'docx_template': (
        'user_rules > template_text_rules > representative_template_direct_format > '
        'template_style_xml > bundled_OOXML_fallback > legacy_dictionary_fallback'
    ),
    'native_docx_template': (
        'user_rules > template_text_rules > representative_template_direct_format > '
        'template_style_xml > bundled_OOXML_fallback > legacy_dictionary_fallback'
    ),
    'converted_docx_template': (
        'user_rules > converted_text_rules > source_column_detection_for_fallback_variant > bundled_OOXML_fallback > legacy_dictionary_fallback'
    ),
    'pdf_visual_inference': (
        'user_rules > extracted_text_rules > pdf_column_detection_for_fallback_variant > bundled_OOXML_fallback > legacy_dictionary_fallback'
    ),
    'pdf_text_visual_hybrid': (
        'user_rules > extracted_pdf_text_rules > pdf_column_detection_for_fallback_variant > bundled_OOXML_fallback > legacy_dictionary_fallback'
    ),
    'text_rules': (
        'user_rules > extracted_text_rules > bundled_OOXML_fallback > legacy_dictionary_fallback'
    ),
    'plain_text_rules': (
        'user_rules > extracted_text_rules > bundled_OOXML_fallback > legacy_dictionary_fallback'
    ),
    'ocr_text_rules': (
        'user_rules > extracted_text_rules > source_column_detection_for_fallback_variant > bundled_OOXML_fallback > legacy_dictionary_fallback'
    ),
    'image_text_rules': (
        'user_rules > extracted_text_rules > source_column_detection_for_fallback_variant > bundled_OOXML_fallback > legacy_dictionary_fallback'
    ),
    'website_text_rules': (
        'user_rules > extracted_text_rules > source_column_detection_for_fallback_variant > bundled_OOXML_fallback > legacy_dictionary_fallback'
    ),
    'screenshot_text_rules': (
        'user_rules > extracted_text_rules > source_column_detection_for_fallback_variant > bundled_OOXML_fallback > legacy_dictionary_fallback'
    ),
    'visual_template': (
        'user_rules > extracted_text_rules > source_column_detection_for_fallback_variant > bundled_OOXML_fallback > legacy_dictionary_fallback'
    ),
    'blank_carrier_template': (
        'user_rules > extracted_text_rules > bundled_OOXML_fallback_materialized_into_blank_carrier > legacy_dictionary_fallback'
    ),
}
LEGACY_WORD_EXTENSIONS = {'.doc', '.dot'}
STYLE_SPEC_VERSION = '1.9'
REFERENCE_NUMBERING_MAP_VERSION = '1.2'
WEAK_EXTERNAL_STYLE_SOURCE_TYPES = {
    'converted_docx_template',
    'pdf_visual_inference',
    'pdf_text_visual_hybrid',
    'ocr_text_rules',
    'image_text_rules',
    'website_text_rules',
    'screenshot_text_rules',
    'text_rules',
    'plain_text_rules',
    'blank_carrier_template',
}
LOW_CONFIDENCE_STYLE_SHELL_SOURCE_TYPES = WEAK_EXTERNAL_STYLE_SOURCE_TYPES | {
    'visual_template',
}
LOW_CONFIDENCE_FORMAT_SOURCE_TYPES = LOW_CONFIDENCE_STYLE_SHELL_SOURCE_TYPES | {
    'visual_template',
    'pdf_visual',
}
OOXML_FALLBACK_SOURCE_TYPES = WEAK_EXTERNAL_STYLE_SOURCE_TYPES | {
    'visual_template',
}
NON_DOCX_TEXT_ONLY_SOURCE_TYPES = {
    'converted_docx_template',
    'pdf_visual_inference',
    'pdf_text_visual_hybrid',
    'visual_template',
    'ocr_text_rules',
    'image_text_rules',
    'website_text_rules',
    'screenshot_text_rules',
    'text_rules',
    'plain_text_rules',
}
WEBSITE_FORMAT_SOURCE_TYPES = {
    'website_text_rules',
}
DOCX_TEXT_RULE_COMPLETION_SOURCE_TYPES = {
    'docx_template',
    'native_docx_template',
}
VISUAL_CENTER_DEFAULT_ROLES = {
    'title', 'english_title',
    'author', 'english_author',
    'affiliation', 'english_affiliation',
}
ABSTRACT_KEYWORD_ROLES = {
    'abstract', 'keywords', 'english_abstract', 'english_keywords',
}
ABSTRACT_KEYWORD_LABEL_PATTERN = (
    r'(?:'
    r'摘\s*要|关键词|关键字|'
    r'Abstract|ABSTRACT|Keywords?|KEYWORDS?|Key\s*words?|KEY\s*WORDS?'
    r')'
)
ABSTRACT_KEYWORD_LABEL_RE = re.compile(
    r'^\s*(?:[\[【〔「『（(]\s*)?(' + ABSTRACT_KEYWORD_LABEL_PATTERN + r')'
    r'(?:\s*[\]】〕」』）)])?\s*(?:[:：]\s*)?',
    re.I,
)

CANONICAL_STYLE_CANDIDATES = {
    'title': ['IOPTitle', 'Titledocument', 'TitleDocument', 'Title'],
    'author': ['Authors', 'Author'],
    'affiliation': ['Affiliation', 'AdressLines', 'AddressLines', 'Affiliations'],
    'abstract': ['Abstract'],
    'keywords': ['KeyWords', 'Keywords', 'Keyword', 'KeyWord'],
    'heading1': ['IOPH1', 'Head1', 'Heading1'],
    'heading2': ['IOPH2', 'Head2', 'Heading2'],
    'heading3': ['IOPH3', 'Head3', 'Heading3'],
    'body': ['Para', 'BodyText', 'BodyTextIndent', 'Normal'],
    'figure_caption': ['FigureCaption', 'CaptionFigure', 'Caption'],
    'table_caption': ['TableCaption', 'CaptionTable', 'TableTitle', 'Caption'],
    'references_heading': ['ReferenceHead', 'ACMRefHead', 'Heading1'],
    'reference_item': ['IOPRefs', 'Bibentry', 'BibEntry', 'References', 'Bibliography'],
    'equation': ['DisplayFormula', 'Equation', 'Formula'],
    'english_title': ['EnglishTitle', 'TitleEnglish'],
    'english_author': ['EnglishAuthors', 'AuthorsEnglish'],
    'english_affiliation': ['EnglishAffiliation', 'AffiliationEnglish'],
    'english_abstract': ['EnglishAbstract', 'AbstractEnglish'],
    'english_keywords': ['EnglishKeywords', 'KeywordsEnglish'],
    'metadata': ['Metadata'],
    'citation_format': ['CitationFormat'],
}

ROLE_EQUIVALENTS = {
    'title': ['english_title'],
    'author': ['english_author'],
    'affiliation': ['english_affiliation'],
    'abstract': ['english_abstract'],
    'keywords': ['english_keywords'],
    'english_title': ['title'],
    'english_author': ['author'],
    'english_affiliation': ['affiliation'],
    'english_abstract': ['abstract'],
    'english_keywords': ['keywords'],
}


def abstract_keyword_label_role(text):
    match = ABSTRACT_KEYWORD_LABEL_RE.match(text or '')
    if not match:
        return None
    label_raw = match.group(1) or ''
    label = re.sub(r'\s+', '', label_raw).lower()
    if label in ('摘要',):
        return 'abstract'
    if label in ('关键词', '关键字'):
        return 'keywords'
    if label == 'abstract':
        return 'english_abstract'
    if label in ('keyword', 'keywords', 'keyword', 'keywords', 'keywords'):
        return 'english_keywords'
    return None


SIZE_MAP = {
    '初号': 84,
    '小初': 72,
    '一号': 52,
    '小一': 48,
    '二号': 44,
    '小二': 36,
    '三号': 32,
    '小三': 30,
    '四号': 28,
    '小四': 24,
    '五号': 21,
    '小五': 18,
    '六号': 15,
    '小六': 13,
    '七号': 11,
    '八号': 10,
}

FONT_WORDS = [
    'Times New Roman', 'Times Roman', 'Arial', 'Calibri',
    '宋体', '黑体', '楷体', '楷体_GB2312', '仿宋', '仿宋_GB2312',
    '微软雅黑', '等线', 'SimSun', 'SimHei', 'KaiTi', 'FangSong',
]

DEFAULT_REFERENCE_HANGING_INDENT = '420'
DEFAULT_REFERENCE_INDENT = {
    'left': DEFAULT_REFERENCE_HANGING_INDENT,
    'hanging': DEFAULT_REFERENCE_HANGING_INDENT,
}

BASE_PARAGRAPH_FALLBACK = {
    'align': 'left',
    'spacing': {'before': '0', 'after': '0', 'line': '240', 'lineRule': 'auto'},
}

LANGUAGE_FALLBACKS = {
    'zh': {
        'title': {
            'fonts': {'eastAsia': '黑体', 'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman'},
            'size': '32', 'bold': True, 'align': 'center',
            'spacing': {'before': '240', 'after': '120', 'line': '360', 'lineRule': 'auto'},
        },
        'author': {
            'fonts': {'eastAsia': '宋体', 'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman'},
            'size': '21', 'align': 'center',
        },
        'affiliation': {
            'fonts': {'eastAsia': '宋体', 'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman'},
            'size': '18', 'align': 'center',
        },
        'abstract': {
            'fonts': {'eastAsia': '宋体', 'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman'},
            'size': '21', 'align': 'both',
        },
        'keywords': {
            'fonts': {'eastAsia': '宋体', 'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman'},
            'size': '21', 'align': 'left',
        },
        'heading1': {
            'fonts': {'eastAsia': '黑体', 'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman'},
            'size': '28', 'bold': True, 'align': 'center',
            'spacing': {'before': '240', 'after': '120', 'line': '360', 'lineRule': 'auto'},
        },
        'heading2': {
            'fonts': {'eastAsia': '黑体', 'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman'},
            'size': '24', 'bold': True, 'align': 'left',
            'spacing': {'before': '180', 'after': '60', 'line': '360', 'lineRule': 'auto'},
        },
        'heading3': {
            'fonts': {'eastAsia': '黑体', 'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman'},
            'size': '21', 'bold': True, 'align': 'left',
            'spacing': {'before': '120', 'after': '60', 'line': '360', 'lineRule': 'auto'},
        },
        'body': {
            'fonts': {'eastAsia': '宋体', 'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman'},
            'size': '21', 'align': 'both', 'indent': {'firstLine': '420'},
            'spacing': {'before': '0', 'after': '0', 'line': '360', 'lineRule': 'auto'},
        },
        'figure_caption': {
            'fonts': {'eastAsia': '宋体', 'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman'},
            'size': '18', 'align': 'center',
        },
        'table_caption': {
            'fonts': {'eastAsia': '宋体', 'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman'},
            'size': '18', 'align': 'center',
        },
        'references_heading': {
            'fonts': {'eastAsia': '黑体', 'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman'},
            'size': '24', 'bold': True, 'align': 'center',
        },
        'reference_item': {
            'fonts': {'eastAsia': '宋体', 'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman'},
            'size': '18', 'align': 'both', 'indent': DEFAULT_REFERENCE_INDENT,
        },
        'english_title': {
            'fonts': {'eastAsia': '宋体', 'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman'},
            'size': '24', 'bold': True, 'align': 'center',
        },
        'english_author': {
            'fonts': {'eastAsia': '宋体', 'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman'},
            'size': '18', 'align': 'center',
        },
        'english_affiliation': {
            'fonts': {'eastAsia': '宋体', 'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman'},
            'size': '18', 'align': 'center',
        },
        'english_abstract': {
            'fonts': {'eastAsia': '宋体', 'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman'},
            'size': '21', 'align': 'both',
        },
        'english_keywords': {
            'fonts': {'eastAsia': '宋体', 'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman'},
            'size': '21', 'align': 'left',
        },
        'metadata': {
            'fonts': {'eastAsia': '宋体', 'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman'},
            'size': '18', 'align': 'left',
        },
        'citation_format': {
            'fonts': {'eastAsia': '宋体', 'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman'},
            'size': '18', 'align': 'left',
        },
        'equation': {
            'fonts': {'eastAsia': '宋体', 'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman'},
            'size': '21', 'align': 'center',
            'spacing': {'before': '0', 'after': '0', 'line': '360', 'lineRule': 'auto'},
        },
    },
    'en': {
        'title': {
            'fonts': {'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman', 'eastAsia': 'SimSun'},
            'size': '32', 'bold': True, 'align': 'center',
        },
        'author': {
            'fonts': {'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman', 'eastAsia': 'SimSun'},
            'size': '24', 'align': 'center',
        },
        'affiliation': {
            'fonts': {'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman', 'eastAsia': 'SimSun'},
            'size': '20', 'align': 'center',
        },
        'abstract': {
            'fonts': {'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman', 'eastAsia': 'SimSun'},
            'size': '21', 'align': 'both',
        },
        'keywords': {
            'fonts': {'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman', 'eastAsia': 'SimSun'},
            'size': '21', 'align': 'left',
        },
        'heading1': {
            'fonts': {'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman', 'eastAsia': 'SimSun'},
            'size': '24', 'bold': True, 'align': 'left',
        },
        'heading2': {
            'fonts': {'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman', 'eastAsia': 'SimSun'},
            'size': '22', 'bold': True, 'align': 'left',
        },
        'heading3': {
            'fonts': {'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman', 'eastAsia': 'SimSun'},
            'size': '20', 'bold': True, 'align': 'left',
        },
        'body': {
            'fonts': {'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman', 'eastAsia': 'SimSun'},
            'size': '24', 'align': 'both',
        },
        'figure_caption': {
            'fonts': {'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman', 'eastAsia': 'SimSun'},
            'size': '18', 'align': 'center',
        },
        'table_caption': {
            'fonts': {'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman', 'eastAsia': 'SimSun'},
            'size': '18', 'align': 'center',
        },
        'references_heading': {
            'fonts': {'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman', 'eastAsia': 'SimSun'},
            'size': '24', 'bold': True, 'align': 'left',
        },
        'reference_item': {
            'fonts': {'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman', 'eastAsia': 'SimSun'},
            'size': '20', 'align': 'left', 'indent': DEFAULT_REFERENCE_INDENT,
        },
        'english_title': {
            'fonts': {'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman', 'eastAsia': 'SimSun'},
            'size': '32', 'bold': True, 'align': 'center',
        },
        'english_author': {
            'fonts': {'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman', 'eastAsia': 'SimSun'},
            'size': '24', 'align': 'center',
        },
        'english_affiliation': {
            'fonts': {'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman', 'eastAsia': 'SimSun'},
            'size': '20', 'align': 'center',
        },
        'english_abstract': {
            'fonts': {'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman', 'eastAsia': 'SimSun'},
            'size': '21', 'align': 'both',
        },
        'english_keywords': {
            'fonts': {'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman', 'eastAsia': 'SimSun'},
            'size': '21', 'align': 'left',
        },
        'metadata': {
            'fonts': {'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman', 'eastAsia': 'SimSun'},
            'size': '20', 'align': 'left',
        },
        'citation_format': {
            'fonts': {'ascii': 'Times New Roman', 'hAnsi': 'Times New Roman', 'eastAsia': 'SimSun'},
            'size': '20', 'align': 'left',
        },
    },
}

DIRECT_RPR_TAGS = {
    'rFonts', 'sz', 'szCs', 'b', 'bCs', 'i', 'iCs', 'color', 'highlight',
    'shd', 'u', 'smallCaps', 'caps', 'strike', 'dstrike', 'kern', 'spacing',
    'position', 'fitText', 'em', 'lang',
}

SUPERSCRIPT_MAP_VERSION = '1.0'
SUPERSCRIPT_MARKER_RE = r'(?:\d{1,2}|[*†‡§])'
EQUATION_LAYOUT_MAP_VERSION = '1.0'
TABLE_FORMAT_MAP_VERSION = '1.1'
TABLE_THREE_LINE_BORDER = {'val': 'single', 'sz': '8', 'space': '0', 'color': '000000'}
TABLE_THREE_LINE_BORDER_THICK = {'val': 'single', 'sz': '12', 'space': '0', 'color': '000000'}
TABLE_THREE_LINE_HEADER_SEPARATOR_BORDER = {'val': 'single', 'sz': '6', 'space': '0', 'color': '000000'}
TABLE_BORDER_NONE = {'val': 'none'}
REFERENCE_ITEM_DEFAULT_INDENT_TWIPS = '420'

DIRECT_PPR_TAGS = {
    'jc', 'spacing', 'ind', 'rPr', 'contextualSpacing', 'keepNext',
    'keepLines', 'widowControl', 'outlineLvl', 'tabs', 'textAlignment',
}

TABLE_PR_FORMAT_TAGS = {
    'tblStyle', 'tblpPr', 'tblOverlap', 'bidiVisual', 'tblStyleRowBandSize',
    'tblStyleColBandSize', 'jc', 'tblCellSpacing', 'tblInd',
    'tblBorders', 'shd', 'tblCellMar', 'tblLook',
}

TABLE_ROW_FORMAT_TAGS = {
    'tblHeader', 'cantSplit', 'trHeight', 'jc', 'hidden', 'tblCellSpacing',
    'cnfStyle', 'divId',
}

TABLE_CELL_FORMAT_TAGS = {
    'tcW', 'tcBorders', 'shd', 'noWrap',
    'tcMar', 'textDirection', 'tcFitText', 'vAlign', 'hideMark',
}

TABLE_CELL_TOPOLOGY_TAGS = {'gridSpan', 'hMerge', 'vMerge'}

# All common OOXML namespaces
ALL_NAMESPACES = {
    'wpc': 'http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas',
    'cx': 'http://schemas.microsoft.com/office/drawing/2014/chartex',
    'cx1': 'http://schemas.microsoft.com/office/drawing/2015/9/8/chartex',
    'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'o': 'urn:schemas-microsoft-com:office:office',
    'r': R_NS,
    'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math',
    'v': 'urn:schemas-microsoft-com:vml',
    'wp14': 'http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'w10': 'urn:schemas-microsoft-com:office:word',
    'w': W_NS,
    'w14': 'http://schemas.microsoft.com/office/word/2010/wordml',
    'w15': 'http://schemas.microsoft.com/office/word/2012/wordml',
    'w16se': 'http://schemas.microsoft.com/office/word/2015/wordml/symex',
    'wpg': 'http://schemas.microsoft.com/office/word/2010/wordprocessingGroup',
    'wpi': 'http://schemas.microsoft.com/office/word/2010/wordprocessingInk',
    'wne': 'http://schemas.microsoft.com/office/word/2006/wordml',
    'wps': 'http://schemas.microsoft.com/office/word/2010/wordprocessingShape',
}

# Register all namespaces to preserve them on output
for prefix, uri in ALL_NAMESPACES.items():
    ET.register_namespace(prefix, uri)


def w(tag):
    """Get fully qualified Word tag."""
    return f'{{{W_NS}}}{tag}'


def r(tag):
    """Get fully qualified Relationship tag."""
    return f'{{{R_NS}}}{tag}'


def pkg_rel(tag):
    """Get fully qualified package relationship tag."""
    return f'{{{PKG_REL_NS}}}{tag}'


def local_name(tag):
    """Return local XML tag name without namespace."""
    return tag.split('}')[-1] if '}' in tag else tag


def is_legacy_word_path(path):
    return os.path.splitext(str(path))[1].lower() in LEGACY_WORD_EXTENSIONS


def legacy_word_warning(path, role):
    ext = os.path.splitext(str(path))[1].lower()
    return (
        f"{role} file is legacy Word {ext}: {path}. "
        "Legacy .doc/.dot is not an OpenXML package and has no directly inspectable "
        "word/styles.xml. Conversion to .docx may flatten styles into direct formatting, "
        "lose template-only definitions, or differ from Microsoft Word's final display. "
        "Convert it to a temporary .docx when possible, treat the converted evidence as "
        "lower confidence, and recommend a native .docx/.dotx source-format file or "
        "explicit text formatting instructions in the final notes. Stop only if conversion and other extraction routes produce "
        "no usable formatting evidence."
    )


def find_word_converter():
    candidates = [
        'soffice',
        'libreoffice',
        '/Applications/LibreOffice.app/Contents/MacOS/soffice',
    ]
    for candidate in candidates:
        if os.path.isabs(candidate):
            if os.path.exists(candidate):
                return candidate
        else:
            found = shutil.which(candidate)
            if found:
                return found
    return None


def convert_legacy_word_to_docx(path, tmpdir, role):
    converter = find_word_converter()
    if not converter:
        raise RuntimeError(
            f"{legacy_word_warning(path, role)} No LibreOffice/soffice converter was found."
        )
    out_dir = os.path.join(tmpdir, f'{role}_legacy_docx')
    os.makedirs(out_dir, exist_ok=True)
    cmd = [
        converter,
        '--headless',
        '--convert-to',
        'docx',
        '--outdir',
        out_dir,
        path,
    ]
    print(f"Converting legacy Word {role} to temporary DOCX with {os.path.basename(converter)}...")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Legacy Word conversion failed for {path}: {result.stderr.strip() or result.stdout.strip()}"
        )
    converted = os.path.join(out_dir, os.path.splitext(os.path.basename(path))[0] + '.docx')
    if not os.path.exists(converted):
        candidates = [
            os.path.join(out_dir, name)
            for name in os.listdir(out_dir)
            if name.lower().endswith('.docx')
        ]
        if len(candidates) == 1:
            converted = candidates[0]
    if not os.path.exists(converted) or not zipfile.is_zipfile(converted):
        raise RuntimeError(f"Legacy Word conversion did not produce a valid DOCX for {path}")
    return converted


def classify_libreoffice_failure(stdout, stderr, returncode):
    combined = f"{stdout or ''}\n{stderr or ''}"
    if returncode == 0:
        return None
    if 'source file could not be loaded' in combined:
        return 'libreoffice_source_load_failed'
    if 'Error: source file could not be loaded' in combined:
        return 'libreoffice_source_load_failed'
    if 'General Error' in combined:
        return 'libreoffice_general_error'
    if 'SfxBaseModel::impl_store' in combined or 'store' in combined.lower():
        return 'libreoffice_export_failed'
    return 'libreoffice_conversion_failed'


def run_libreoffice_compatibility_qa(docx_path, output_dir):
    """Check whether LibreOffice can load the final DOCX and export PDF.

    This is a compatibility gate only. It must never save or normalize the final
    DOCX through LibreOffice, because that can alter OMML, OLE, anchors, fields,
    and Word-specific layout.
    """
    os.makedirs(output_dir, exist_ok=True)
    converter = find_word_converter()
    result = {
        'enabled': True,
        'ok': False,
        'engine': 'libreoffice',
        'mode': 'load_and_pdf_export_only_no_docx_resave',
        'output_dir': os.path.abspath(output_dir),
        'pdf_path': None,
        'converter': converter,
        'failure_kind': None,
        'error': None,
    }
    if not converter:
        result.update({
            'failure_kind': 'soffice_missing',
            'error': 'LibreOffice/soffice converter not found',
        })
        return result
    stem = os.path.splitext(os.path.basename(docx_path))[0]
    with tempfile.TemporaryDirectory(prefix='lo_profile_') as profile_dir:
        cmd = [
            converter,
            f'-env:UserInstallation=file://{profile_dir}',
            '--headless',
            '--invisible',
            '--norestore',
            '--convert-to',
            'pdf',
            '--outdir',
            output_dir,
            docx_path,
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    pdf_path = os.path.join(output_dir, f'{stem}.pdf')
    if not os.path.exists(pdf_path):
        candidates = glob.glob(os.path.join(output_dir, '*.pdf'))
        if len(candidates) == 1:
            pdf_path = candidates[0]
    pdf_ok = os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0
    result.update({
        'ok': proc.returncode == 0 and pdf_ok,
        'returncode': proc.returncode,
        'pdf_path': os.path.abspath(pdf_path) if pdf_ok else None,
        'stdout_tail': (proc.stdout or '')[-2000:],
        'stderr_tail': (proc.stderr or '')[-2000:],
    })
    if not result['ok']:
        result['failure_kind'] = classify_libreoffice_failure(proc.stdout, proc.stderr, proc.returncode)
        result['error'] = 'LibreOffice could not load/export the DOCX to PDF'
    return result


def normalize_word_inputs(template_path, target_path, tmpdir, allow_legacy_word_conversion=True):
    legacy_sources = []
    normalized_template = template_path
    normalized_target = target_path
    for role, path in (('template', template_path), ('target', target_path)):
        if not is_legacy_word_path(path):
            continue
        warning = legacy_word_warning(path, role)
        legacy_sources.append({
            'role': role,
            'path': path,
            'extension': os.path.splitext(path)[1].lower(),
            'message': warning,
            'conversion_allowed': bool(allow_legacy_word_conversion),
            'risk': 'legacy_word_conversion_lower_confidence',
        })
        if not allow_legacy_word_conversion:
            raise RuntimeError(warning)
        converted = convert_legacy_word_to_docx(path, tmpdir, role)
        legacy_sources[-1]['converted_docx'] = converted
        legacy_sources[-1]['conversion_tool'] = find_word_converter()
        if role == 'template':
            normalized_template = converted
        else:
            normalized_target = converted
    return normalized_template, normalized_target, legacy_sources


def extract_docx(docx_path, extract_dir):
    """Extract a DOCX file to a directory."""
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(docx_path, 'r') as z:
        z.extractall(extract_dir)


def repack_docx(extract_dir, output_path):
    """Repack a directory into a valid DOCX file.
    [Content_Types].xml must be first and stored (not compressed).
    """
    content_types = os.path.join(extract_dir, '[Content_Types].xml')
    if not os.path.exists(content_types):
        raise FileNotFoundError('[Content_Types].xml not found')

    normalize_all_relationship_parts(extract_dir)

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add [Content_Types].xml first, stored (no compression)
        zf.write(content_types, '[Content_Types].xml', compress_type=zipfile.ZIP_STORED)

        # Add all other files
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, extract_dir)
                if arcname == '[Content_Types].xml':
                    continue  # already added
                if '.DS_Store' in arcname:
                    continue
                zf.write(full_path, arcname)


def normalize_all_relationship_parts(extract_dir):
    """Normalize every package .rels part before final ZIP packaging."""
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if not file.endswith('.rels'):
                continue
            rels_path = os.path.join(root, file)
            try:
                tree = ET.parse(rels_path)
            except ET.ParseError:
                continue
            write_xml(tree, rels_path)


def sectPr_to_info(sectPr):
    info = {}
    for child in sectPr:
        tag = child.tag.split('}')[-1]
        attrs = {k.split('}')[-1]: v for k, v in child.attrib.items()}
        info[tag] = attrs
    return info


def section_col_count(info):
    cols = (info or {}).get('cols') or {}
    try:
        return int(cols.get('num') or 1)
    except (TypeError, ValueError):
        return 1


def normalize_column_count(value):
    try:
        return 2 if int(value or 1) >= 2 else 1
    except (TypeError, ValueError):
        return 1


def is_website_format_source(source_type):
    return normalize_format_source_type(source_type) in WEBSITE_FORMAT_SOURCE_TYPES


def _metadata_truthy(metadata, keys):
    metadata = metadata or {}
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, bool):
            if value:
                return True
        elif isinstance(value, (int, float)):
            if value:
                return True
        elif isinstance(value, str) and value.strip().lower() in {'1', 'true', 'yes', 'y', 'explicit'}:
            return True
    return False


def _explicit_column_text_mentions_count(value):
    text = str(value or '').lower()
    if not text:
        return False
    explicit_tokens = (
        '单栏', '单列', '一栏', '一列', '双栏', '双列', '两栏', '两列',
        'single column', 'single-column', 'one column', 'one-column',
        'two column', 'two-column', 'double column', 'double-column',
        '2-column', '1-column',
    )
    return any(token in text for token in explicit_tokens)


def _explicit_column_count_from_text(value):
    text = str(value or '').lower()
    if not text:
        return None
    double_tokens = (
        '双栏', '双列', '两栏', '两列',
        'two column', 'two-column', 'double column', 'double-column', '2-column',
    )
    single_tokens = (
        '单栏', '单列', '一栏', '一列',
        'single column', 'single-column', 'one column', 'one-column', '1-column',
    )
    if any(token in text for token in double_tokens):
        return 2
    if any(token in text for token in single_tokens):
        return 1
    return None


def _source_text_marks_explicit_column_source(source_text, explicit_tokens, visual_tokens):
    source_text = str(source_text or '').lower()
    negated_tokens = (
        'not explicitly',
        'does not explicitly',
        'no explicit',
        'without explicit',
        'unspecified',
        'not specified',
        'not stated',
        'does not state',
        '未明确',
        '没有明确',
        '未说明',
        '没有说明',
        '未写明',
        '没有写明',
    )
    if any(token in source_text for token in negated_tokens):
        return False
    return any(token in source_text for token in explicit_tokens) and not any(token in source_text for token in visual_tokens)


def website_has_explicit_column_rule(metadata):
    """Website links default to single-column unless text/user rules state columns."""
    metadata = metadata or {}
    explicit_keys = (
        'explicit_column_rule',
        'column_rule_explicit',
        'fallback_columns_explicit',
        'explicit_fallback_columns',
        'explicit_columns',
        'user_column_rule',
        'website_explicit_column_rule',
    )
    if _metadata_truthy(metadata, explicit_keys):
        return True
    text_keys = (
        'column_rule_text',
        'column_instruction_text',
        'explicit_column_text',
        'website_column_text',
        'user_column_text',
    )
    if any(_explicit_column_text_mentions_count(metadata.get(key)) for key in text_keys):
        return True
    source_keys = (
        'column_source',
        'column_detection_source',
        'fallback_columns_source',
        'source',
        'route',
        'method',
    )
    explicit_source_tokens = ('explicit', 'text_rule', 'text rule', 'website_text_rule', 'website text rule', 'user')
    visual_source_tokens = ('visual', 'geometry', 'render', 'screenshot', 'image', 'capture', 'layout')
    source_text = ' '.join(str(metadata.get(key) or '').lower() for key in source_keys)
    if (
        metadata_fallback_columns(metadata, default=None) is not None
        and _source_text_marks_explicit_column_source(source_text, explicit_source_tokens, visual_source_tokens)
    ):
        return True
    detection = metadata.get('source_column_detection')
    if isinstance(detection, dict):
        if _metadata_truthy(detection, explicit_keys):
            return True
        if any(_explicit_column_text_mentions_count(detection.get(key)) for key in text_keys):
            return True
        if any(_explicit_column_text_mentions_count(detection.get(key)) for key in ('reason', 'source', 'route', 'method')):
            source_text = ' '.join(str(detection.get(key) or '').lower() for key in ('source', 'route', 'method', 'reason'))
            explicit_tokens = explicit_source_tokens + ('instruction', 'prose')
            return _source_text_marks_explicit_column_source(source_text, explicit_tokens, visual_source_tokens)
        source_text = ' '.join(str(detection.get(key) or '').lower() for key in source_keys + ('reason',))
        if (
            metadata_fallback_columns(detection, default=None) is not None
            and _source_text_marks_explicit_column_source(source_text, explicit_source_tokens, visual_source_tokens)
        ):
            return True
    return False


def website_explicit_column_count(metadata):
    metadata = metadata or {}
    explicit_count = metadata_fallback_columns(metadata, default=None)
    if explicit_count is not None and website_has_explicit_column_rule(metadata):
        return explicit_count
    text_keys = (
        'column_rule_text',
        'column_instruction_text',
        'explicit_column_text',
        'website_column_text',
        'user_column_text',
    )
    for key in text_keys:
        count = _explicit_column_count_from_text(metadata.get(key))
        if count is not None:
            return count
    detection = metadata.get('source_column_detection')
    if isinstance(detection, dict):
        explicit_count = metadata_fallback_columns(detection, default=None)
        if explicit_count is not None and website_has_explicit_column_rule({'source_column_detection': detection}):
            return explicit_count
        for key in text_keys:
            count = _explicit_column_count_from_text(detection.get(key))
            if count is not None:
                return count
    return None


def website_explicit_column_resolution(columns):
    return {
        'columns': normalize_column_count(columns),
        'source': 'website_explicit_text_column_rule',
        'reason': 'website/user text explicitly states the manuscript column count',
    }


def website_default_single_column_resolution(source_column_resolution=None, prior_columns=None):
    return {
        'columns': 1,
        'source': 'website_unspecified_default_single',
        'reason': (
            'website link does not explicitly state single-column or double-column; '
            'default to submission-manuscript single-column instead of inferring from publisher/production layout'
        ),
        'ignored_columns': prior_columns,
        'ignored_resolution': source_column_resolution,
    }


def metadata_fallback_columns(metadata, default=None):
    metadata = metadata or {}
    for key in ('fallback_columns', 'columns', 'column_count', 'detected_columns'):
        value = metadata.get(key)
        if value not in (None, ''):
            return normalize_column_count(value)
    column_detection = metadata.get('source_column_detection')
    if isinstance(column_detection, dict):
        for key in ('columns', 'column_count', 'detected_columns', 'fallback_columns'):
            value = column_detection.get(key)
            if value not in (None, ''):
                return normalize_column_count(value)
    return default


def get_sectPr_infos(doc_dir):
    """Extract all section properties, including paragraph-level pPr/sectPr."""
    doc_path = os.path.join(doc_dir, 'word', 'document.xml')
    tree = ET.parse(doc_path)
    root = tree.getroot()
    return [sectPr_to_info(sectPr) for sectPr in root.iter(w('sectPr'))]


def detect_fallback_columns(doc_dir):
    try:
        infos = get_sectPr_infos(doc_dir)
    except Exception:
        return 1
    counts = [section_col_count(info) for info in infos]
    return 2 if any(count >= 2 for count in counts) else 1


def detect_columns_from_source_filename(path):
    if not path:
        return None
    name = os.path.basename(str(path)).lower()
    if any(token in name for token in ('双栏', '双列', 'two-column', 'two column', 'double-column', 'double column')):
        return 2
    if any(token in name for token in ('单栏', '单列', 'single-column', 'single column', 'one-column', 'one column')):
        return 1
    return None


def resolve_fallback_columns_for_source(doc_dir=None, source_metadata=None, default=None,
                                        allow_docx_detection=True):
    """Choose fallback columns from allowed low-confidence evidence only."""
    metadata = source_metadata or {}
    metadata_columns = metadata_fallback_columns(metadata, default=None)
    if metadata_columns is not None:
        return {
            'columns': metadata_columns,
            'source': 'metadata',
            'source_column_detection': metadata.get('source_column_detection'),
        }
    if default is not None:
        return {'columns': normalize_column_count(default), 'source': 'default'}
    if allow_docx_detection and doc_dir:
        try:
            infos = get_sectPr_infos(doc_dir)
            counts = [section_col_count(info) for info in infos]
            if counts:
                return {
                    'columns': 2 if any(count >= 2 for count in counts) else 1,
                    'source': 'converted_docx_sectPr',
                    'section_column_counts': counts,
                }
        except Exception as exc:
            return {
                'columns': 1,
                'source': 'docx_detection_failed',
                'error': str(exc),
            }
    for key in ('format_source_path', 'source_path', 'template_path', 'original_path'):
        filename_columns = detect_columns_from_source_filename(metadata.get(key))
        if filename_columns is not None:
            return {'columns': filename_columns, 'source': f'filename:{key}'}
    return {'columns': 1, 'source': 'fallback_default_single'}


def get_sectPr_info(doc_dir):
    """Backward-compatible single section setup: prefer the final/body section."""
    infos = get_sectPr_infos(doc_dir)
    return infos[-1] if infos else None


def get_header_footer_map(doc_dir):
    """Get header/footer files from document.
    Returns dict: {'header': {'default': 'header1.xml', 'first': 'header2.xml'},
                   'footer': {'default': 'footer1.xml'}}
    """
    rels_path = os.path.join(doc_dir, 'word', '_rels', 'document.xml.rels')
    if not os.path.exists(rels_path):
        return {'header': {}, 'footer': {}}

    tree = ET.parse(rels_path)
    root = tree.getroot()

    result = {'header': {}, 'footer': {}}
    for rel in root:
        rel_type = rel.get('Type', '')
        target = rel.get('Target', '')
        rId = rel.get('Id', '')

        if 'relationships/header' in rel_type:
            # Find type from document.xml sectPr
            result['header'][rId] = target
        elif 'relationships/footer' in rel_type:
            result['footer'][rId] = target

    # Map by type by reading document.xml
    # Use iter() to find ALL sectPr elements (including those inside pPr)
    doc_path = os.path.join(doc_dir, 'word', 'document.xml')
    tree = ET.parse(doc_path)
    root = tree.getroot()

    typed_result = {'header': {}, 'footer': {}}
    for sectPr in root.iter(w('sectPr')):
        for child in sectPr:
            tag = child.tag.split('}')[-1]
            if tag in ('headerReference', 'footerReference'):
                ref_type = child.get(w('type'), 'default')
                ref_id = child.get(r('id'), '')
                kind = 'header' if 'header' in tag.lower() else 'footer'
                if ref_id in result[kind] and ref_type not in typed_result[kind]:
                    typed_result[kind][ref_type] = result[kind][ref_id]

    return typed_result


def get_all_styles(doc_dir):
    """Extract all styles from template styles.xml, indexed by style name.

    Returns dict: {style_name: {
        'type': 'paragraph'|'character'|'table'|'numbering',
        'style_elem': <style_element_xml_string>,
        'name': style_name
    }}
    Also includes docDefaults if present.
    """
    styles_path = os.path.join(doc_dir, 'word', 'styles.xml')
    tree = ET.parse(styles_path)
    root = tree.getroot()

    styles_dict = {}

    # Extract docDefaults
    docDefaults = root.find(w('docDefaults'))
    if docDefaults is not None:
        styles_dict['__docDefaults__'] = {
            'type': 'defaults',
            'xml': ET.tostring(docDefaults, encoding='unicode')
        }

    # Extract all styles
    for style in root.findall(w('style')):
        name_elem = style.find(w('name'))
        if name_elem is None:
            continue
        style_name = name_elem.get(w('val'))
        style_type = style.get(w('type'), 'paragraph')

        styles_dict[style_name] = {
            'type': style_type,
            'xml': ET.tostring(style, encoding='unicode'),
            'name': style_name
        }

    return styles_dict


def _get_next_style_id(root):
    """Find the next available styleId number in target styles.xml."""
    max_num = 0
    for style in root.findall(w('style')):
        sid = style.get(w('styleId'), '')
        # Extract numeric part
        num_str = ''
        for c in sid:
            if c.isdigit():
                num_str += c
        if num_str:
            max_num = max(max_num, int(num_str))
    return max_num + 1


def get_text(elem):
    """Collect visible Word text from an element."""
    parts = []

    def walk(node, in_run=False):
        node_in_run = in_run or node.tag == w('r')
        if node.tag == w('t'):
            parts.append(node.text or '')
        elif node_in_run and node.tag == w('tab'):
            parts.append('\t')
        elif node_in_run and node.tag == w('br'):
            parts.append('\n')
        for child in list(node):
            walk(child, node_in_run)

    walk(elem)
    return ''.join(parts)


def run_text(run):
    return ''.join((t.text or '') for t in run.findall(w('t')))


def is_run_superscript(run):
    rPr = get_direct_child(run, w('rPr'))
    vert = child_by_local_name(rPr, 'vertAlign')
    return vert is not None and vert.get(w('val')) == 'superscript'


def simple_text_run(run):
    t_nodes = run.findall(w('t'))
    if len(t_nodes) != 1:
        return False
    allowed = {'rPr', 't'}
    return all(local_name(child.tag) in allowed for child in run)


def set_text_node_preserve_space(t_node, text):
    t_node.text = text
    xml_space = '{http://www.w3.org/XML/1998/namespace}space'
    if text[:1].isspace() or text[-1:].isspace():
        t_node.set(xml_space, 'preserve')
    elif xml_space in t_node.attrib:
        del t_node.attrib[xml_space]


def set_run_text(run, text):
    t_node = run.find(w('t'))
    if t_node is not None:
        set_text_node_preserve_space(t_node, text)


def make_text_run(text):
    run = ET.Element(w('r'))
    t_node = ET.SubElement(run, w('t'))
    set_text_node_preserve_space(t_node, text)
    return run


def set_run_superscript(run):
    rPr = get_or_add_child(run, w('rPr'), first=True)
    vert = child_by_local_name(rPr, 'vertAlign')
    if vert is None:
        vert = ET.Element(w('vertAlign'))
        rPr.append(vert)
    vert.set(w('val'), 'superscript')


def clear_run_superscript(run):
    rPr = get_direct_child(run, w('rPr'))
    if rPr is None:
        return 0
    removed = remove_children_by_local_name(rPr, {'vertAlign'})
    if len(list(rPr)) == 0:
        run.remove(rPr)
    return removed


def clear_paragraph_superscript(p):
    return sum(clear_run_superscript(run) for run in p.iter(w('r')))


def get_direct_child(parent, tag):
    if parent is None:
        return None
    for child in parent:
        if child.tag == tag:
            return child
    return None


def get_or_add_child(parent, tag, first=False):
    child = get_direct_child(parent, tag)
    if child is None:
        child = ET.Element(tag)
        if first:
            parent.insert(0, child)
        else:
            parent.append(child)
    return child


def iter_body_paragraphs(root, include_tables=False):
    body = root.find(w('body'))
    if body is None:
        return
    for child in body:
        if child.tag == w('p'):
            yield child
        elif include_tables and child.tag == w('tbl'):
            for p in child.iter(w('p')):
                yield p


def paragraph_equation_kinds(p):
    kinds = set()
    for node in p.iter():
        lname = local_name(node.tag)
        if lname in ('oMath', 'oMathPara'):
            kinds.add('omml')
        elif lname in ('object', 'OLEObject', 'control'):
            kinds.add('ole_object')
        elif lname == 'objectEmbed':
            kinds.add('ole_object')
        elif lname == 'imagedata':
            progid = ''.join(
                str(value) for key, value in node.attrib.items()
                if 'ProgID' in key or 'progid' in key.lower()
            )
            if re.search(r'(Equation|MathType|MTExtra|DSMT)', progid, re.I):
                kinds.add('ole_object')
        elif lname in ('drawing', 'pict'):
            if paragraph_has_embedded_object(node):
                kinds.add('ole_object')
            elif looks_like_numbered_graphic_equation_paragraph(p):
                kinds.add('numbered_graphic_equation')
    return sorted(kinds)


def looks_like_numbered_graphic_equation_paragraph(p):
    text = get_text(p).strip()
    if not equation_number_text(text):
        return False
    if re.search(r'^\s*(图|表|Fig\.?|Figure|Table|Tab\.?)\b', text, re.I):
        return False
    if re.search(r'(图\s*\d+|表\s*\d+|Fig\.?\s*\d+|Figure\s+\d+|Table\s+\d+)', text, re.I):
        return False
    visible_without_number = equation_number_text(text)
    remainder = text.replace(visible_without_number, '').strip()
    return len(remainder) <= 20


def paragraph_has_embedded_object(elem):
    for node in elem.iter():
        lname = local_name(node.tag)
        if lname in ('object', 'OLEObject', 'objectEmbed', 'control'):
            return True
        if should_sniff_equation_attributes(node):
            for key, value in node.attrib.items():
                haystack = f'{key} {value}'
                if re.search(r'(Equation|MathType|MTExtra|DSMT|oleObject)', haystack, re.I):
                    return True
    return False


def should_sniff_equation_attributes(node):
    lname = local_name(node.tag)
    if lname in ('pPr', 'rPr', 'tblPr', 'tcPr', 'trPr'):
        return False
    if lname in ('pStyle', 'rStyle', 'tblStyle', 'style', 'basedOn', 'link', 'name'):
        return False
    return True


def paragraph_has_equation(p):
    return bool(paragraph_equation_kinds(p))


def paragraph_is_display_equation(p):
    if not paragraph_has_equation(p):
        return False
    style_id = paragraph_style_id(p)
    if style_id in ('DisplayFormula', 'Equation', 'Formula'):
        return True
    kinds = set(paragraph_equation_kinds(p))
    if 'numbered_graphic_equation' in kinds:
        return True
    text = get_text(p).strip()
    number = equation_number_text(text)
    if number:
        remainder = text.replace(number, '').strip()
        if len(re.sub(r'\s+', '', remainder)) <= 40:
            return True
    if not text:
        return True
    # OMML/OLE display equations often have no prose text; inline equations
    # inside a normal sentence should stay as body text.
    if kinds == {'omml'} and len(re.sub(r'\s+', '', text)) <= 20:
        return True
    return False


def equation_number_text(text):
    stripped = (text or '').strip()
    matches = re.findall(r'[\(（]\s*(?:式\s*)?\d+(?:[.\-]\d+)*\s*[\)）]', stripped)
    return matches[-1] if matches else None


def paragraph_tab_profile(p):
    tokens = []
    allow_graphic_equation = looks_like_numbered_graphic_equation_paragraph(p)
    for child in p:
        if child.tag == w('r'):
            run_has_equation = False
            for node in child:
                lname = local_name(node.tag)
                if lname == 'tab':
                    tokens.append('tab')
                elif lname == 't' and (node.text or ''):
                    if equation_number_text(node.text):
                        tokens.append('number')
                    else:
                        tokens.append('text')
                elif lname in ('oMath', 'oMathPara'):
                    tokens.append('equation')
                    run_has_equation = True
                elif lname in ('object', 'OLEObject', 'objectEmbed', 'drawing', 'pict') and child_contains_equation(node, allow_graphic=allow_graphic_equation):
                    tokens.append('equation')
                    run_has_equation = True
            if not run_has_equation and child_contains_equation(child, allow_graphic=allow_graphic_equation):
                tokens.append('equation')
        elif local_name(child.tag) in ('oMath', 'oMathPara'):
            tokens.append('equation')
        elif child_contains_equation(child, allow_graphic=allow_graphic_equation):
            tokens.append('equation')
    equation_index = next((idx for idx, token in enumerate(tokens) if token == 'equation'), None)
    number_index = next((idx for idx, token in enumerate(tokens) if token == 'number'), None)
    def count_tabs(start, end):
        if start is None or end is None:
            return 0
        lo, hi = sorted((start, end))
        return sum(1 for token in tokens[lo + 1:hi] if token == 'tab')
    return {
        'tokens': tokens,
        'equation_index': equation_index,
        'number_index': number_index,
        'tabs_before_equation': sum(1 for token in tokens[:equation_index or 0] if token == 'tab'),
        'tabs_between_equation_and_number': count_tabs(equation_index, number_index),
        'tabs_after_number': sum(1 for token in tokens[(number_index + 1) if number_index is not None else len(tokens):] if token == 'tab'),
    }


def paragraph_tabs_xml(p):
    pPr = get_direct_child(p, w('pPr'))
    tabs = child_by_local_name(pPr, 'tabs')
    return xml_string(tabs)


def paragraph_style_id(p):
    pPr = get_direct_child(p, w('pPr'))
    pStyle = get_direct_child(pPr, w('pStyle'))
    return pStyle.get(w('val')) if pStyle is not None else None


def set_paragraph_style(p, style_id):
    pPr = get_or_add_child(p, w('pPr'), first=True)
    pStyle = get_direct_child(pPr, w('pStyle'))
    if pStyle is None:
        pStyle = ET.Element(w('pStyle'))
        pPr.insert(0, pStyle)
    pStyle.set(w('val'), style_id)


def classify_paragraph(text, index, in_references=False, english_context=None, citation_context=None):
    english_context = english_context or {}
    citation_context = citation_context or {}
    compact = re.sub(r'\s+', '', text or '')
    stripped = (text or '').strip()
    if not stripped:
        return None
    if is_template_marker(stripped):
        return None
    if looks_like_template_noncontent_metadata_or_note(stripped):
        return 'metadata'
    if looks_like_email_contact_line(stripped) and index <= 12:
        return 'affiliation'
    if re.match(r'^\s*英文题名、作者、单位、摘要、关键词参考下面模式', stripped):
        return None
    if re.fullmatch(r'参考文献[:：]?', compact) or compact in ('References', 'REFERENCE', 'REFERENCES'):
        return 'references_heading'
    if in_references and looks_like_reference_item(stripped):
        return 'reference_item'
    if in_references and not looks_like_reference_zone_noise(stripped):
        return 'reference_item'
    label_role = abstract_keyword_label_role(stripped)
    if label_role:
        return label_role
    if re.match(r'^\s*(文章编号|中图分类号|文献标志码)', stripped):
        return 'metadata'
    if re.match(r'^\s*引用格式', stripped):
        citation_context['open'] = True
        return 'citation_format'
    if citation_context.get('open') and looks_like_citation_format_continuation(stripped):
        return 'citation_format'
    if english_context.get('mode') == 'front_matter':
        role = classify_english_front_matter(stripped, english_context)
        if role:
            return role
    if re.search(r'文章题名|论文题名|论文题目', stripped):
        return 'title'
    if 0 < index <= 8 and looks_like_english_author_line(stripped):
        return 'author'
    if index > 0 and re.match(r'^\s*\d+[\.．]\d+[\.．]\d+\s+', stripped):
        return 'heading3'
    if index > 0 and re.match(r'^\s*\d+[\.．]\d+\s+', stripped):
        return 'heading2'
    if index > 0 and re.match(r'^\s*\d+(?:[\.．]|\s{1,6})\s*\S+', stripped) and looks_like_numbered_heading(stripped):
        return 'heading1'
    if index > 0 and looks_like_plain_heading(stripped):
        return 'heading1'
    if index <= 8 and looks_like_english_title(stripped):
        return 'english_title'
    if index <= 6 and re.search(r'第一作者|作者简介|作者[1-9]?', stripped) and len(stripped) < 180:
        return 'author'
    if index <= 8 and re.search(r'(大学|学院|研究院|实验室|Institute|University|College)', stripped, re.I) and len(stripped) < 220:
        return 'affiliation'
    if re.match(r'^\s*(图\s*\d+(\s|$)|Fig\.?\s*\d+|Figure\s+\d+)', stripped, re.I):
        return 'figure_caption'
    if re.match(r'^\s*(表\s*\d+(\s|$)|Tab\.?\s*\d+|Table\s+\d+)', stripped, re.I):
        return 'table_caption'
    if re.match(r'^\s*\d+[\.．]\d+[\.．]\d+\s+', stripped):
        return 'heading3'
    if re.match(r'^\s*\d+[\.．]\d+\s+', stripped):
        return 'heading2'
    if re.match(r'^\s*\d+(?:[\.．]|\s{1,6})\s*\S+', stripped) and looks_like_numbered_heading(stripped):
        return 'heading1'
    if looks_like_plain_heading(stripped):
        return 'heading1'
    if index == 0 and len(stripped) < 80:
        return 'title'
    if index <= 2 and len(stripped) < 80 and looks_like_author_fallback(stripped):
        return 'author'
    if index <= 5 and len(stripped) < 140 and looks_like_affiliation_fallback(stripped):
        return 'affiliation'
    return 'body'


def looks_like_template_noncontent_metadata_or_note(text):
    stripped = (text or '').strip()
    if not stripped:
        return False
    if re.match(r'^\s*(doi|date\s+of\s+publication|received|revised|accepted|published|copyright)\b', stripped, re.I):
        return True
    if re.match(r'^\s*(出版日期|收稿日期|修回日期|录用日期|发布日期|责任编辑|基金项目|作者简介|通讯作者)\b', stripped):
        return True
    if re.search(r'\bdoi\s*[:：]\s*10\.\d{4,9}/\S+', stripped, re.I):
        return True
    if re.search(r'\b(date\s+of\s+publication|publication date|digital object identifier)\b', stripped, re.I):
        return True
    if re.search(r'\b(copyright|all rights reserved|personal use is permitted)\b', stripped, re.I):
        return True
    if re.search(r'\b(corresponding author|e-mail|email)\b', stripped, re.I) and len(stripped) < 220:
        return True
    return False


def looks_like_email_contact_line(text):
    stripped = (text or '').strip()
    if not stripped or len(stripped) > 220:
        return False
    email_re = r'[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}'
    if not re.search(email_re, stripped, re.I):
        return False
    non_email_text = re.sub(email_re, '', stripped, flags=re.I)
    non_email_text = re.sub(r'[\s,;；，、:：()（）\[\]{}<>/\\|\+\*†‡§0-9.\-]+', '', non_email_text)
    return len(non_email_text) <= 24


def looks_like_numbered_heading(text):
    stripped = (text or '').strip()
    if not re.match(r'^\d+(?:[\.．]|\s+)', stripped):
        return False
    if re.match(r'^\d+[\.．]\d+', stripped):
        return False
    tail = re.sub(r'^\d+(?:[\.．]|\s+)\s*', '', stripped).strip()
    if not tail or len(tail) > 120:
        return False
    if re.search(r'[。！？!?；;:：]$', tail):
        return False
    if re.search(r'[，,。；;：:]{1}', tail) and len(tail) > 60:
        return False
    if re.search(r'\b(is|are|was|were|has|have|can|will|should|that|which|because)\b', tail, re.I) and len(tail.split()) > 8:
        return False
    return bool(re.search(r'[A-Za-z\u4e00-\u9fff]', tail))


def looks_like_plain_heading(text):
    stripped = (text or '').strip()
    if not stripped or len(stripped) > 90:
        return False
    if re.search(r'[。！？!?；;。]$', stripped):
        return False
    if abstract_keyword_label_role(stripped) or re.match(r'^(References?)\b', stripped, re.I):
        return False
    if re.match(r'^(Fig\.?|Figure|Table|Tab\.?)\s*\d+', stripped, re.I):
        return False
    if looks_like_english_author_line(stripped) or looks_like_author_fallback(stripped):
        return False
    common = {
        'introduction', 'conclusion', 'conclusions', 'discussion', 'results',
        'methods', 'methodology', 'experiment', 'experiments', 'related work',
        'background', 'acknowledgements', 'acknowledgments'
    }
    normalized = re.sub(r'\s+', ' ', stripped).lower()
    if normalized in common:
        return True
    words = re.findall(r'[A-Za-z][A-Za-z0-9-]*', stripped)
    if 2 <= len(words) <= 9 and not re.search(r'\b(is|are|was|were|has|have|can|will|should|that|which|because)\b', stripped, re.I):
        capitals = sum(1 for word in words if word[:1].isupper() or word.isupper() or any(ch.isdigit() for ch in word))
        return capitals >= max(1, len(words) - 1)
    return False


def looks_like_author_fallback(text):
    stripped = (text or '').strip()
    if not stripped or looks_like_sentence_body(stripped):
        return False
    if re.search(r'(作者|Author)', stripped, re.I):
        return True
    if re.search(r'\d|[*†‡§]|，|,', stripped) and len(re.findall(r'[A-Za-z\u4e00-\u9fff]+', stripped)) <= 12:
        return True
    return False


def looks_like_affiliation_fallback(text):
    stripped = (text or '').strip()
    if not stripped or looks_like_sentence_body(stripped):
        return False
    return bool(re.search(
        r'(大学|学院|研究院|实验室|中心|系|部|Institute|University|College|School|Laboratory|Department|Center|Faculty|Academy)',
        stripped,
        re.I
    ))


def looks_like_sentence_body(text):
    stripped = (text or '').strip()
    if len(stripped) > 100:
        return True
    if re.search(r'[。！？!?；;]$', stripped):
        return True
    return bool(re.search(
        r'\b(is|are|was|were|has|have|allows?|uses?|shows?|indicates?|can|will|should|that|which|because|therefore|however)\b',
        stripped,
        re.I
    ))


def looks_like_citation_format_continuation(text):
    stripped = (text or '').strip()
    normalized = stripped.replace('\\[', '[').replace('\\]', ']')
    return bool(
        re.search(r'\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?\b', normalized)
        and re.search(r'\[(?:J|M|C|D|P|S|R|N|EB/OL|OL)\]', normalized, re.I)
    )


def is_template_marker(text):
    return bool(re.fullmatch(r'\s*WORD模板\s*', text or '', re.I))


def starts_english_front_matter_block(text):
    return bool(re.match(r'^\s*英文题名、作者、单位、摘要、关键词参考下面模式', text or ''))


def classify_english_front_matter(text, context):
    step = context.get('step', 0)
    if re.fullmatch(r'（?姓全部大写，名首字母大写）?', text):
        return None
    label_role = abstract_keyword_label_role(text)
    if label_role == 'english_abstract':
        context['step'] = max(step, 4)
        return 'english_abstract'
    if label_role == 'english_keywords':
        context['step'] = 5
        return 'english_keywords'
    if step <= 0 and looks_like_english_title(text):
        context['step'] = 1
        return 'english_title'
    if step <= 1 and looks_like_english_author_line(text):
        context['step'] = 2
        return 'english_author'
    if step <= 3 and looks_like_english_affiliation_line(text):
        context['step'] = 3
        return 'english_affiliation'
    return None


def looks_like_english_author_line(text):
    stripped = (text or '').strip()
    if not stripped or len(stripped) > 180:
        return False
    if looks_like_email_contact_line(stripped):
        return False
    if re.match(r'^\s*\d+(?:[\.．]|\s+)\s*\S+', stripped) and looks_like_numbered_heading(stripped):
        return False
    if re.search(r'\b(University|Institute|College|School|Laboratory|Department|China|USA|UK)\b', stripped, re.I):
        return False
    words = re.findall(r'[A-Za-z][A-Za-z-]*', stripped)
    upper_like = sum(1 for word in words if word[:1].isupper() or word.isupper())
    return len(words) >= 2 and upper_like >= max(2, len(words) // 2) and bool(re.search(r'\d|，|,', stripped))


def looks_like_front_matter_author_line(text):
    stripped = (text or '').strip()
    if not stripped or len(stripped) > 180:
        return False
    if looks_like_email_contact_line(stripped):
        return False
    if looks_like_sentence_body(stripped) or looks_like_affiliation_fallback(stripped):
        return False
    if re.match(r'^\s*\d+(?:[\.．]|\s+)\s*\S+', stripped) and looks_like_numbered_heading(stripped):
        return False
    if abstract_keyword_label_role(stripped):
        return False
    if re.search(r'(作者|Author)', stripped, re.I):
        return True
    if looks_like_english_author_line(stripped):
        return True
    latin_words = re.findall(r'[A-Za-z][A-Za-z-]*', stripped)
    cjk_chars = re.findall(r'[\u4e00-\u9fff]', stripped)
    separators = bool(re.search(r'[，,、;；]', stripped))
    if separators and latin_words:
        upper_like = sum(1 for word in latin_words if word[:1].isupper() or word.isupper())
        return upper_like >= max(2, len(latin_words) // 2)
    if separators and 2 <= len(cjk_chars) <= 40:
        return True
    if re.search(r'\d|[*†‡§]', stripped) and (latin_words or cjk_chars) and len(latin_words) + len(cjk_chars) <= 24:
        return True
    return False


def looks_like_english_affiliation_line(text):
    stripped = (text or '').strip()
    return bool(re.search(
        r'\b(University|Institute|College|School|Laboratory|Department|Academy|Faculty|China|USA|UK)\b',
        stripped,
        re.I
    ))


def looks_like_english_title(text):
    stripped = (text or '').strip()
    if not stripped or len(stripped) > 160:
        return False
    if re.search(r'[。！？!?；;]$', stripped):
        return False
    if ':' in stripped:
        return False
    if not re.search(r'[A-Za-z]', stripped):
        return False
    if abstract_keyword_label_role(stripped):
        return False
    if re.search(r'\b(is|are|was|were|has|have|allows?|uses?|shows?|indicates?|can|will|should|that|which|because)\b', stripped, re.I):
        return False
    word_count = len(re.findall(r'[A-Za-z][A-Za-z-]*', stripped))
    return 4 <= word_count <= 20 and not re.search(r'\b(University|Institute|College|School|Laboratory|Department)\b', stripped, re.I)


def looks_like_reference_item(text):
    stripped = (text or '').strip()
    if re.match(r'^\s*(\[\d+\]|［\d+］|\d+[\.\)]\s*)', stripped):
        return True
    if re.search(r'\[(?:J|M|C|D|P|S|R|N|EB/OL|OL)\]', stripped, re.I):
        return True
    if re.search(r'\b(?:IEEE|ACM|arXiv|PMLR|Journal|Proceedings|Press|University|Transactions)\b', stripped):
        return True
    if re.search(r'\b(19|20)\d{2}\b', stripped) and re.search(r'[A-Z][A-Z][A-Z]+', stripped):
        return True
    return False


def looks_like_reference_zone_noise(text):
    stripped = (text or '').strip()
    if not stripped:
        return True
    if looks_like_reference_instruction_noise(stripped):
        return True
    if re.fullmatch(r'(例|示例|Example|Examples)[:：]?', stripped, re.I):
        return True
    if re.search(r'(责任编辑|收稿日期|基金项目|作者简介)', stripped):
        return True
    return False


def looks_like_reference_instruction_noise(text):
    stripped = (text or '').strip()
    if re.match(r'^\s*(引用格式|著录格式|期刊与书.*格式为)', stripped, re.I):
        return True
    return bool(re.search(
        r'(参考文献应|引用期刊条数|不要缺少|'
        r'作者1|作者2|著者1|著者2|起始页|终止页|出版地|出版时间)',
        stripped,
        re.I
    ))


def is_template_front_matter_noise(text):
    return bool(re.search(
        r'^(WORD模板|文章编号|中图分类号|文献标志码|引用格式|英文题名、作者|'
        r'姓全部大写|在线查询分类号)',
        text,
        re.I
    )) or bool(re.search(r'\bet\s+al\.', text, re.I))


REPRESENTATIVE_RUN_MIN_COVERAGE = 0.80
REPRESENTATIVE_LOCAL_EMPHASIS_MIN_COVERAGE = 0.90
REPRESENTATIVE_RUN_MIN_ABSOLUTE_CHARS = 8
LOCAL_EMPHASIS_RPR_TAGS = {
    'b', 'bCs', 'i', 'iCs', 'u', 'color', 'highlight', 'shd', 'vertAlign',
    'strike', 'dstrike', 'em', 'position', 'vanish', 'caps', 'smallCaps',
}


def run_effective_text_length(run):
    text = run_text(run)
    if not text:
        return 0
    compact = re.sub(r'\s+', '', text)
    if not compact:
        return 0
    return len(compact)


def rpr_property_key(child):
    name = local_name(child.tag)
    attrs = tuple(sorted((local_name(key), value) for key, value in child.attrib.items()))
    return name, attrs


def rpr_property_is_promotable(name, covered, total_text_length):
    if total_text_length <= 0:
        return False
    threshold = (
        REPRESENTATIVE_LOCAL_EMPHASIS_MIN_COVERAGE
        if name in LOCAL_EMPHASIS_RPR_TAGS
        else REPRESENTATIVE_RUN_MIN_COVERAGE
    )
    if covered / float(total_text_length) < threshold:
        return False
    return covered >= min(REPRESENTATIVE_RUN_MIN_ABSOLUTE_CHARS, total_text_length)


def representative_run_rpr(p):
    """Infer whole-paragraph run properties by coverage, never by first formatted run."""
    total_text_length = 0
    buckets = {}
    exemplars = {}
    for child in p:
        if child.tag != w('r'):
            continue
        text_length = run_effective_text_length(child)
        if not text_length:
            continue
        total_text_length += text_length
        rPr = get_direct_child(child, w('rPr'))
        if rPr is None:
            continue
        seen_in_run = set()
        for prop in list(rPr):
            name, attrs = rpr_property_key(prop)
            key = (name, attrs)
            if key in seen_in_run:
                continue
            seen_in_run.add(key)
            buckets[key] = buckets.get(key, 0) + text_length
            exemplars.setdefault(key, prop)
    if total_text_length <= 0 or not buckets:
        return None

    kept = []
    for key, covered in buckets.items():
        name = key[0]
        if rpr_property_is_promotable(name, covered, total_text_length):
            kept.append((name, key, covered))
    if not kept:
        return None

    rPr = ET.Element(w('rPr'))
    for _name, key, _covered in sorted(kept, key=lambda item: item[0]):
        rPr.append(clone_element(exemplars[key]))
    return rPr if len(list(rPr)) else None


def paragraph_signature(p):
    pPr = get_direct_child(p, w('pPr'))
    rPr = get_direct_child(pPr, w('rPr'))
    run_rpr = rPr if rPr is not None else representative_run_rpr(p)
    return {
        'pPr': ET.tostring(pPr, encoding='unicode') if pPr is not None else '',
        'rPr': ET.tostring(run_rpr, encoding='unicode') if run_rpr is not None else '',
    }


def style_identity_key(value):
    return re.sub(r'[^a-z0-9]+', '', value or '', flags=re.I).lower()


def style_identity_values(style_id, style_name=''):
    values = []
    for value in (style_id, style_name):
        key = style_identity_key(value)
        if key and key not in values:
            values.append(key)
    return values


def style_identity_has_any(values, tokens):
    return any(token in value for value in values for token in tokens)


def role_from_style_identity(style_id, style_name='', text=''):
    values = style_identity_values(style_id, style_name)
    if not values:
        return None
    joined = ' '.join(values)
    if re.fullmatch(r'\s*(references|reference|bibliography|参考文献)\s*:?\s*', text or '', re.I):
        if style_identity_has_any(values, ('referencehead', 'refhead', 'referencesheading', 'bibliographyheading', 'heading', 'head')):
            return 'references_heading'
    if style_identity_has_any(values, ('tablecaption', 'captiontable', 'tabletitle', 'tabcaption')):
        return 'table_caption'
    if style_identity_has_any(values, ('figurecaption', 'captionfigure', 'figcaption', 'figuretitle', 'figtitle')):
        return 'figure_caption'
    if any(
        value.endswith('h1') or value.endswith('head1') or value.endswith('heading1')
        or value.startswith('h1')
        for value in values
    ) or re.search(r'(^|[^a-z0-9])(h1|head1|heading1|headinglevel1|sectionhead1)($|[^a-z0-9])', joined):
        return 'heading1'
    if any(
        value.endswith('h2') or value.endswith('head2') or value.endswith('heading2')
        or value.startswith('h2')
        for value in values
    ) or re.search(r'(^|[^a-z0-9])(h2|head2|heading2|headinglevel2|sectionhead2)($|[^a-z0-9])', joined):
        return 'heading2'
    if any(
        value.endswith('h3') or value.endswith('head3') or value.endswith('heading3')
        or value.startswith('h3')
        for value in values
    ) or re.search(r'(^|[^a-z0-9])(h3|head3|heading3|headinglevel3|sectionhead3)($|[^a-z0-9])', joined):
        return 'heading3'
    if style_identity_has_any(values, ('referencehead', 'refhead', 'referencesheading', 'bibliographyheading')):
        return 'references_heading'
    if style_identity_has_any(values, ('bibentry', 'bibliographyentry', 'referenceitem', 'refsitem', 'referencesitem')):
        return 'reference_item'
    if (
        style_identity_has_any(values, ('bibliography', 'references', 'reference', 'refs'))
        and not style_identity_has_any(values, ('head', 'heading', 'title'))
    ):
        return 'reference_item'
    if style_identity_has_any(values, ('displayformula', 'displayequation', 'equation', 'formula')):
        return 'equation'
    if style_identity_has_any(values, ('englishtitle', 'titleenglish')):
        return 'english_title'
    if style_identity_has_any(values, ('englishauthors', 'englishauthor', 'authorsenglish', 'authorenglish')):
        return 'english_author'
    if style_identity_has_any(values, ('englishaffiliation', 'englishaffiliations', 'affiliationenglish')):
        return 'english_affiliation'
    if style_identity_has_any(values, ('englishabstract', 'abstractenglish')):
        return 'english_abstract'
    if style_identity_has_any(values, ('englishkeywords', 'englishkeyword', 'keywordsenglish')):
        return 'english_keywords'
    if style_identity_has_any(values, ('keywords', 'keyword', 'key words', 'keywd')):
        return 'keywords'
    if style_identity_has_any(values, ('abstract',)):
        return 'abstract'
    if style_identity_has_any(values, ('affiliation', 'affiliations', 'addresslines', 'adresslines', 'institute', 'institution')):
        return 'affiliation'
    if style_identity_has_any(values, ('authors', 'author')):
        return 'author'
    if (
        style_identity_has_any(values, ('articletitle', 'papertitle', 'manuscripttitle', 'documenttitle', 'journaltitle', 'title'))
        and not style_identity_has_any(values, ('subtitle', 'runningtitle', 'shorttitle', 'tabletitle', 'figuretitle', 'figtitle'))
    ):
        return 'title'
    if style_identity_has_any(values, ('metadata', 'classification', 'citationformat')):
        return 'metadata' if 'citationformat' not in joined else 'citation_format'
    if style_identity_has_any(values, ('bodytext', 'bodyparagraph', 'normalparagraph')):
        return 'body'
    if any(value in ('para', 'body', 'normal') for value in values):
        return 'body'
    return None


def role_from_template_pstyle(style_id, text='', styles_by_id=None):
    if not style_id:
        return None
    style_elem = (styles_by_id or {}).get(style_id)
    style_name = style_display_name(style_elem) if style_elem is not None else ''
    mapping = {
        'IOPTitle': 'title',
        'Titledocument': 'title',
        'TitleDocument': 'title',
        'Title': 'title',
        'Authors': 'author',
        'Author': 'author',
        'Affiliation': 'affiliation',
        'AdressLines': 'affiliation',
        'AddressLines': 'affiliation',
        'Affiliations': 'affiliation',
        'Abstract': 'abstract',
        'KeyWords': 'keywords',
        'Keyword': 'keywords',
        'KeyWord': 'keywords',
        'IOPH1': 'heading1',
        'IOPH2': 'heading2',
        'IOPH3': 'heading3',
        'Head1': 'heading1',
        'Head2': 'heading2',
        'Head3': 'heading3',
        'Heading1': 'heading1',
        'Heading2': 'heading2',
        'Heading3': 'heading3',
        'Para': 'body',
        'BodyText': 'body',
        'BodyTextIndent': 'body',
        'FigureCaption': 'figure_caption',
        'CaptionFigure': 'figure_caption',
        'TableCaption': 'table_caption',
        'CaptionTable': 'table_caption',
        'IOPRefs': 'reference_item',
        'References': 'reference_item',
        'Bibliography': 'reference_item',
        'Bibentry': 'reference_item',
        'BibEntry': 'reference_item',
        'DisplayFormula': 'equation',
        'Equation': 'equation',
        'Formula': 'equation',
        'Keywords': 'keywords',
        'EnglishTitle': 'english_title',
        'TitleEnglish': 'english_title',
        'EnglishAuthors': 'english_author',
        'AuthorsEnglish': 'english_author',
        'EnglishAffiliation': 'english_affiliation',
        'AffiliationEnglish': 'english_affiliation',
        'EnglishAbstract': 'english_abstract',
        'AbstractEnglish': 'english_abstract',
        'EnglishKeywords': 'english_keywords',
        'KeywordsEnglish': 'english_keywords',
        'Metadata': 'metadata',
        'CitationFormat': 'citation_format',
    }
    if style_id in ('Heading1', 'Head1') and re.fullmatch(r'\s*References\s*', text or '', re.I):
        return 'references_heading'
    if style_id in ('ReferenceHead', 'ACMRefHead'):
        return 'references_heading'
    if style_id in mapping:
        return mapping[style_id]
    return role_from_style_identity(style_id, style_name, text)


def collect_role_source_styles(doc_dir):
    """Find likely template paragraph roles from the template body."""
    doc_path = os.path.join(doc_dir, 'word', 'document.xml')
    tree = ET.parse(doc_path)
    root = tree.getroot()
    styles_by_id = {}
    styles_path = os.path.join(doc_dir, 'word', 'styles.xml')
    if os.path.exists(styles_path):
        styles_by_id = build_style_id_index(ET.parse(styles_path).getroot())
    role_sources = {}
    in_references = False
    body_zone_open = False
    english_context = {'mode': None, 'step': 0}
    citation_context = {'open': False}
    visible_index = 0
    for p in iter_body_paragraphs(root):
        text = get_text(p).strip()
        is_equation = paragraph_is_display_equation(p)
        if not text and not is_equation:
            continue
        if is_equation:
            role = 'equation'
            p_style_id = paragraph_style_id(p)
        else:
            p_style_id = paragraph_style_id(p)
            role = role_from_template_pstyle(p_style_id, text, styles_by_id=styles_by_id) or classify_paragraph(
                text, visible_index, in_references, english_context, citation_context
            )
        if starts_english_front_matter_block(text):
            english_context = {'mode': 'front_matter', 'step': 0}
            citation_context['open'] = False
            visible_index += 1
            continue
        rule_role = role_from_rule_text(text)
        if rule_role == 'body':
            body_zone_open = True
            visible_index += 1
            continue
        if is_template_front_matter_noise(text) and role not in ('metadata', 'citation_format'):
            visible_index += 1
            continue
        if role == 'references_heading':
            in_references = True
        if role == 'reference_item' and looks_like_reference_instruction_noise(text):
            visible_index += 1
            continue
        if role == 'body' and not body_zone_open:
            visible_index += 1
            continue
        if role == 'body' and (rule_role or looks_like_template_instruction(text)):
            visible_index += 1
            continue
        if role and not role_source_candidate_is_usable(role, text, p_style_id):
            visible_index += 1
            continue
        if role and role not in role_sources:
            role_sources[role] = {
                'style_id': paragraph_style_id(p),
                'signature': paragraph_signature(p),
                'sample': text[:80],
            }
        visible_index += 1
    choose_body_source_fallback(role_sources, doc_dir)
    choose_reference_item_source_fallback(role_sources, doc_dir)
    return role_sources


def collect_first_paragraph_by_style_id(doc_dir):
    """Collect first top-level body paragraph sample/signature for each pStyle."""
    doc_path = os.path.join(doc_dir, 'word', 'document.xml')
    tree = ET.parse(doc_path)
    root = tree.getroot()
    by_style_id = {}
    for p in iter_body_paragraphs(root):
        text = get_text(p).strip()
        if not text and not paragraph_is_display_equation(p):
            continue
        style_id = paragraph_style_id(p)
        if not style_id or style_id in by_style_id:
            continue
        by_style_id[style_id] = {
            'style_id': style_id,
            'signature': paragraph_signature(p),
            'sample': text[:80],
        }
    return by_style_id


def detect_template_language(doc_dir):
    doc_path = os.path.join(doc_dir, 'word', 'document.xml')
    tree = ET.parse(doc_path)
    root = tree.getroot()
    sample = []
    for p in iter_body_paragraphs(root):
        text = get_text(p).strip()
        if text:
            sample.append(text)
        if len(''.join(sample)) > 3000:
            break
    text = ''.join(sample)
    cjk_count = len(re.findall(r'[\u4e00-\u9fff]', text))
    latin_count = len(re.findall(r'[A-Za-z]', text))
    return 'zh' if cjk_count >= max(20, latin_count * 0.2) else 'en'


def infer_rule_language_from_rules(rules):
    blob_parts = []
    for role, rule in (rules or {}).items():
        blob_parts.append(str(role))
        blob_parts.append(json.dumps(rule or {}, ensure_ascii=False, sort_keys=True))
    blob = ''.join(blob_parts)
    cjk_count = len(re.findall(r'[\u4e00-\u9fff]', blob))
    return 'zh' if cjk_count else None


def infer_target_language(doc_dir):
    doc_path = os.path.join(doc_dir, 'word', 'document.xml')
    try:
        tree = ET.parse(doc_path)
    except Exception:
        return None
    root = tree.getroot()
    sample = []
    for p in iter_body_paragraphs(root, include_tables=True):
        text = get_text(p).strip()
        if text:
            sample.append(text)
        if len(''.join(sample)) > 3000:
            break
    text = ''.join(sample)
    cjk_count = len(re.findall(r'[\u4e00-\u9fff]', text))
    latin_count = len(re.findall(r'[A-Za-z]', text))
    if cjk_count >= 5 and cjk_count >= latin_count * 0.2:
        return 'zh'
    if latin_count >= 5:
        return 'en'
    return None


def choose_fallback_language(template_dir, text_rules=None, source_type=None, target_dir=None):
    source_type = normalize_format_source_type(source_type)
    rule_language = infer_rule_language_from_rules(text_rules)
    if rule_language:
        return rule_language
    if source_type in LOW_CONFIDENCE_STYLE_SHELL_SOURCE_TYPES and target_dir:
        target_language = infer_target_language(target_dir)
        if target_language:
            return target_language
    detected = detect_template_language(template_dir)
    if (
        source_type in LOW_CONFIDENCE_STYLE_SHELL_SOURCE_TYPES
        and detected == 'en'
        and not any(get_text(p).strip() for p in iter_body_paragraphs(ET.parse(os.path.join(template_dir, 'word', 'document.xml')).getroot()))
    ):
        return 'zh'
    return detected


def template_has_meaningful_format_text(doc_dir):
    doc_path = os.path.join(doc_dir, 'word', 'document.xml')
    try:
        tree = ET.parse(doc_path)
    except Exception:
        return False
    root = tree.getroot()
    meaningful = 0
    for p in iter_body_paragraphs(root, include_tables=True):
        text = get_text(p).strip()
        if text:
            meaningful += len(text)
        if paragraph_is_display_equation(p):
            meaningful += 20
        if meaningful >= 20:
            return True
    return False


def is_blank_carrier_template_source(template_dir, source_type=None, text_rules=None):
    source_type = normalize_format_source_type(source_type)
    if source_type == 'blank_carrier_template':
        return True
    if source_type not in ('docx_template', 'native_docx_template', '', None):
        return False
    if text_rules:
        return not template_has_meaningful_format_text(template_dir)
    return False


def looks_like_template_instruction(text):
    if role_from_rule_text(text):
        return True
    return bool(re.search(
        r'(WORD模板|文章编号|中图分类号|文献标志码|引用格式|参考下面|姓全部大写|'
        r'在线查询|大小为|文字大小|应标明|基本要求|号|字体|字号|Times\s+New\s+Roman|'
        r'宋体|黑体|楷体|居中|三线制|模式)',
        text,
        re.I
    ))


def text_has_explicit_format_property(text):
    """Return true only when the text states formatting, not generic placeholder prose."""
    if not text:
        return False
    return bool(
        parse_size_from_text(text)
        or parse_fonts_from_text(text)
        or parse_alignment_from_text(text)
        or parse_bold_from_text(text) is not None
        or parse_line_spacing_from_text(text)
        or parse_spacing_before_after_from_text(text)
        or parse_indent_from_text(text)
    )


def parse_global_manuscript_format_rule(text):
    """Parse source prose that states manuscript-wide formatting without naming a role."""
    stripped = (text or '').strip()
    if not stripped:
        return {}
    rule = {}
    spacing = parse_line_spacing_from_text(stripped)
    if spacing and re.search(
        r'\b(contributions?|manuscripts?|papers?|articles?|submissions?|text|稿件|全文|论文)\b',
        stripped,
        re.I,
    ):
        rule['spacing'] = spacing
    fonts = parse_fonts_from_text(stripped)
    if fonts and re.search(
        r'\b(contributions?|manuscripts?|papers?|articles?|submissions?|text|written|稿件|全文|论文)\b',
        stripped,
        re.I,
    ):
        rule['fonts'] = fonts
    return rule


def merge_rule_into_role(rules, role, rule, source='template_text_rules', format_text=''):
    if role not in ROLE_STYLE_IDS or not rule:
        return
    clean_rule = dict(rule)
    clean_rule['source'] = source
    clean_rule['confidence'] = clean_rule.get('confidence') or 'explicit'
    if format_text:
        clean_rule['_format_text'] = format_text
    current = rules.setdefault(role, {})
    for key, value in clean_rule.items():
        if isinstance(value, dict) and isinstance(current.get(key), dict):
            current[key].update(value)
        else:
            current[key] = value


def apply_global_manuscript_rule(rules, rule, source='template_text_rules', format_text=''):
    """Apply manuscript-wide text rules only to manuscript content roles."""
    if not rule:
        return
    target_roles = (
        'abstract', 'english_abstract', 'body', 'reference_item',
        'figure_caption', 'table_caption', 'equation',
    )
    for role in target_roles:
        merge_rule_into_role(rules, role, rule, source=source, format_text=format_text)


def looks_like_explicit_format_or_operation_instruction(text):
    stripped = (text or '').strip()
    if not stripped:
        return False
    if looks_like_non_format_instruction_text(stripped):
        return True
    if looks_like_generic_format_instruction(stripped):
        return True
    if role_from_rule_text(stripped) and text_has_explicit_format_property(stripped):
        return True
    if re.fullmatch(
        r'文章正文是?[^\n。；;]{0,30}(?:宋体|黑体|楷体|Times\s+New\s+Roman)[^\n。；;]{0,20}',
        stripped,
        re.I,
    ):
        return True
    return bool(re.search(
        r'(WORD模板|文章编号|中图分类号|文献标志码|引用格式|参考下面|姓全部大写|'
        r'在线查询|大小为|文字大小|应标明|基本要求|三线制|模式)',
        stripped,
        re.I,
    ))


def looks_like_generic_format_instruction(text):
    stripped = (text or '').strip()
    if not stripped:
        return False
    if not text_has_explicit_format_property(stripped):
        return False
    return bool(re.search(
        r'\b(please\s+use|use\s+(?:a|an)?|should\s+be|must\s+be|set\s+in|'
        r'type\s+in|typed\s+in|formatted\s+in|font\s+size|point\s+font|'
        r'roman\s+font|serif(?:s)?|line\s+spacing|spacing|indent|'
        r'double[-\s]?spaced|single[-\s]?spaced)\b',
        stripped,
        re.I,
    ))


def looks_like_body_placeholder_sample(text):
    stripped = re.sub(r'\s+', ' ', (text or '').strip())
    if not stripped:
        return False
    if looks_like_explicit_format_or_operation_instruction(stripped):
        return False
    return bool(re.search(
        r'^(?:enter|insert|type|paste|write)\s+(?:your\s+)?(?:text|manuscript|body|content)\s+here\.?$|'
        r'^(?:your\s+)?(?:text|manuscript|body|content)\s+(?:goes\s+)?here\.?$|'
        r'^lorem\s+ipsum\b|^sample\s+(?:body\s+)?text\.?$',
        stripped,
        re.I,
    ))


def body_source_candidate_is_usable(text, style_id=None):
    stripped = (text or '').strip()
    if not stripped:
        return False
    if looks_like_explicit_format_or_operation_instruction(stripped):
        return False
    if len(stripped) >= 80 and not looks_like_template_instruction(stripped):
        return True
    if looks_like_body_placeholder_sample(stripped):
        return True
    if style_id in BODY_LIKE_STYLE_IDS and not looks_like_template_instruction(stripped):
        return True
    return False


def role_source_candidate_is_usable(role, text, style_id=None):
    stripped = (text or '').strip()
    if not stripped and role != 'equation':
        return False
    if looks_like_template_noncontent_metadata_or_note(stripped):
        return role in ('metadata', 'citation_format')
    if role in (
        'title', 'author', 'affiliation', 'english_title',
        'english_author', 'english_affiliation', 'abstract',
        'english_abstract', 'keywords', 'english_keywords',
    ) and looks_like_explicit_format_or_operation_instruction(stripped):
        return False
    if role == 'body':
        return body_source_candidate_is_usable(stripped, style_id)
    if role == 'reference_item':
        return not looks_like_reference_instruction_noise(stripped)
    if role in ('figure_caption', 'table_caption'):
        return not looks_like_template_instruction(stripped)
    return True


def choose_body_source_fallback(role_sources, doc_dir):
    if 'body' in role_sources:
        return
    doc_path = os.path.join(doc_dir, 'word', 'document.xml')
    tree = ET.parse(doc_path)
    root = tree.getroot()
    in_references = False
    english_context = {'mode': None, 'step': 0}
    citation_context = {'open': False}
    visible_index = 0
    for p in iter_body_paragraphs(root):
        text = get_text(p).strip()
        is_equation = paragraph_is_display_equation(p)
        if not text and not is_equation:
            continue
        if starts_english_front_matter_block(text):
            english_context = {'mode': 'front_matter', 'step': 0}
            citation_context['open'] = False
            visible_index += 1
            continue
        role = classify_paragraph(text, visible_index, in_references, english_context, citation_context)
        if role == 'references_heading':
            in_references = True
        style_id = paragraph_style_id(p)
        if role in (None, 'body') and body_source_candidate_is_usable(text, style_id):
            role_sources['body'] = {
                'style_id': style_id,
                'signature': paragraph_signature(p),
                'sample': text[:80],
            }
            return
        visible_index += 1


def choose_reference_item_source_fallback(role_sources, doc_dir):
    if 'reference_item' in role_sources:
        return
    doc_path = os.path.join(doc_dir, 'word', 'document.xml')
    tree = ET.parse(doc_path)
    root = tree.getroot()
    in_references = False
    examples_open = False
    first_candidate = None
    visible_index = 0
    for p in iter_body_paragraphs(root):
        text = get_text(p).strip()
        is_equation = paragraph_is_display_equation(p)
        if not text and not is_equation:
            continue
        role = classify_paragraph(text, visible_index, in_references)
        if role == 'references_heading':
            in_references = True
            visible_index += 1
            continue
        if in_references and re.fullmatch(r'(例|示例|Example|Examples)[:：]?', text, re.I):
            examples_open = True
            visible_index += 1
            continue
        if in_references and looks_like_reference_item(text) and not looks_like_reference_instruction_noise(text):
            candidate = {
                'style_id': paragraph_style_id(p),
                'signature': paragraph_signature(p),
                'sample': text[:80],
            }
            if examples_open:
                role_sources['reference_item'] = candidate
                return
            if first_candidate is None:
                first_candidate = candidate
        visible_index += 1
    if first_candidate is not None:
        role_sources['reference_item'] = first_candidate


def reference_numbering_match(text):
    raw = text or ''
    stripped = raw.lstrip()
    leading_len = len(raw) - len(stripped)
    match = re.match(r'^(?:\[(\d{1,3})\]|［(\d{1,3})］|(\d{1,3})[\.．、]\s*|(\d{1,3})\)\s*)', stripped)
    if not match:
        return None
    number = next((group for group in match.groups() if group), None)
    if not number:
        return None
    marker = match.group(0)
    if marker.startswith('［'):
        pattern = 'fullwidth_bracket'
    elif marker.startswith('['):
        pattern = 'bracket'
    elif ')' in marker:
        pattern = 'paren'
    elif '．' in marker:
        pattern = 'fullwidth_dot'
    elif '、' in marker:
        pattern = 'ideographic_comma'
    else:
        pattern = 'dot'
    return {
        'number': int(number),
        'marker': marker,
        'pattern': pattern,
        'prefix_len': leading_len + len(match.group(0)),
        'leading_len': leading_len,
    }


def format_reference_number(number, pattern):
    pattern = pattern or 'bracket'
    if pattern == 'fullwidth_bracket':
        return f'［{number}］ '
    if pattern == 'paren':
        return f'{number}) '
    if pattern == 'fullwidth_dot':
        return f'{number}．'
    if pattern == 'ideographic_comma':
        return f'{number}、'
    if pattern == 'dot':
        return f'{number}. '
    return f'[{number}] '


def reference_auto_numbering_from_styles(doc_dir):
    styles_path = os.path.join(doc_dir, 'word', 'styles.xml')
    if not os.path.exists(styles_path):
        return []
    root = ET.parse(styles_path).getroot()
    styles_by_id = build_style_id_index(root)
    doc_defaults = get_doc_defaults(root)
    examples = []
    reference_style_ids = []
    used_styles = collect_first_paragraph_by_style_id(doc_dir)
    for style_id in CANONICAL_STYLE_CANDIDATES.get('reference_item', []):
        if style_id in styles_by_id and style_id in used_styles and style_id not in reference_style_ids:
            reference_style_ids.append(style_id)
    for style_id in sorted(used_styles):
        if style_id in reference_style_ids:
            continue
        if style_id in styles_by_id and role_from_template_pstyle(style_id, styles_by_id=styles_by_id) == 'reference_item':
            reference_style_ids.append(style_id)
    for style_id in CANONICAL_STYLE_CANDIDATES.get('reference_item', []):
        if style_id in styles_by_id and style_id not in reference_style_ids:
            reference_style_ids.append(style_id)
    for style_id, style in styles_by_id.items():
        if style_id in reference_style_ids:
            continue
        if role_from_template_pstyle(style_id, styles_by_id=styles_by_id) == 'reference_item':
            reference_style_ids.append(style_id)
    for style_id in reference_style_ids:
        style = styles_by_id.get(style_id)
        if style is None:
            continue
        style = flatten_template_style(style, styles_by_id, doc_defaults=doc_defaults)
        pPr = get_direct_child(style, w('pPr'))
        numPr = child_by_local_name(pPr, 'numPr')
        num_id = child_attrs(numPr, 'numId').get('val') if numPr is not None else None
        if num_id is None:
            continue
        examples.append({
            'source': 'style',
            'style_id': style_id,
            'numId': num_id,
            'ilvl': child_attrs(numPr, 'ilvl').get('val') or '0',
        })
    return examples


def is_reference_auto_numbering_paragraph(role, style_id, text):
    if style_id in CANONICAL_STYLE_CANDIDATES.get('reference_item', []):
        return True
    if role != 'reference_item':
        return False
    return looks_like_reference_item(text) and not looks_like_reference_instruction_noise(text)


def extract_reference_numbering_map(doc_dir):
    doc_path = os.path.join(doc_dir, 'word', 'document.xml')
    tree = ET.parse(doc_path)
    root = tree.getroot()
    in_references = False
    english_context = {'mode': None, 'step': 0}
    citation_context = {'open': False}
    visible_index = 0
    examples = []
    counts = {}
    auto_numbering_examples = reference_auto_numbering_from_styles(doc_dir)
    auto_numbering_counts = {}
    for example in auto_numbering_examples:
        key = f'{example.get("numId")}:{example.get("ilvl") or "0"}'
        auto_numbering_counts[key] = auto_numbering_counts.get(key, 0) + 1
    for p in iter_body_paragraphs(root):
        text = get_text(p).strip()
        is_equation = paragraph_is_display_equation(p)
        if not text and not is_equation:
            continue
        if starts_english_front_matter_block(text):
            english_context = {'mode': 'front_matter', 'step': 0}
            citation_context['open'] = False
            visible_index += 1
            continue
        role = (
            role_from_template_pstyle(paragraph_style_id(p), text)
            or classify_paragraph(text, visible_index, in_references, english_context, citation_context)
        )
        if role == 'references_heading':
            in_references = True
            visible_index += 1
            continue
        if role == 'reference_item' and not looks_like_reference_instruction_noise(text):
            match = reference_numbering_match(text)
            if match:
                pattern = match['pattern']
                counts[pattern] = counts.get(pattern, 0) + 1
                examples.append({
                    'paragraph_index': visible_index,
                    'pattern': pattern,
                    'marker': match['marker'],
                    'text': text[:160],
                })
            elif not auto_numbering_examples and is_reference_auto_numbering_paragraph(role, paragraph_style_id(p), text):
                pPr = get_direct_child(p, w('pPr'))
                numPr = child_by_local_name(pPr, 'numPr')
                num_id = child_attrs(numPr, 'numId').get('val') if numPr is not None else None
                ilvl = child_attrs(numPr, 'ilvl').get('val') if numPr is not None else None
                if num_id is not None:
                    key = f'{num_id}:{ilvl or "0"}'
                    auto_numbering_counts[key] = auto_numbering_counts.get(key, 0) + 1
                    auto_numbering_examples.append({
                        'paragraph_index': visible_index,
                        'numId': num_id,
                        'ilvl': ilvl or '0',
                        'style_id': paragraph_style_id(p),
                        'text': text[:160],
                    })
        visible_index += 1
    pattern = None
    if counts:
        pattern = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)[0][0]
    mode = 'visible_text' if pattern else ('word_auto' if auto_numbering_examples else 'none')
    return {
        'version': REFERENCE_NUMBERING_MAP_VERSION,
        'enabled': mode in ('visible_text', 'word_auto'),
        'mode': mode,
        'pattern': pattern,
        'counts': counts,
        'examples': examples[:40],
        'word_auto_enabled': mode == 'word_auto',
        'auto_numbering_counts': auto_numbering_counts,
        'auto_numbering_examples': auto_numbering_examples[:40],
        'policy': (
            'If template reference numbers are visible text prefixes, repair visible target prefixes. '
            'If template reference numbers are Word automatic numbering, keep/migrate numbering definitions. '
            'Never add numbers to body citations, headings, formulas, captions, or paragraphs outside the reference zone.'
        ),
        'warning_if_disabled': (
            'Template did not provide explicit reference-list numbering evidence; '
            'missing reference numbers are not invented.'
        ),
    }


def empty_reference_numbering_map(reason='non_docx_text_only_route'):
    return {
        'version': REFERENCE_NUMBERING_MAP_VERSION,
        'enabled': False,
        'mode': 'none',
        'pattern': None,
        'counts': {},
        'examples': [],
        'word_auto_enabled': False,
        'auto_numbering_counts': {},
        'auto_numbering_examples': [],
        'policy': 'Reference numbering evidence was not taken from a non-DOCX carrier.',
        'warning_if_disabled': reason,
    }


def fallback_reference_numbering_map(pattern='bracket', reason='non_docx_standard_reference_numbering_fallback'):
    return {
        'version': REFERENCE_NUMBERING_MAP_VERSION,
        'enabled': True,
        'mode': 'visible_text',
        'pattern': pattern or 'bracket',
        'counts': {pattern or 'bracket': 1},
        'examples': [],
        'word_auto_enabled': False,
        'auto_numbering_counts': {},
        'auto_numbering_examples': [],
        'source': 'standard_fallback',
        'policy': (
            'Standard fallback may repair visible reference-list prefixes only for paragraphs '
            'already mapped as reference_item. Never add numbers to body citations, headings, '
            'formulas, captions, URLs, or paragraphs outside the reference zone.'
        ),
        'warning_if_disabled': reason,
    }


def reference_numbering_map_from_rules_metadata(metadata):
    if not isinstance(metadata, dict):
        return None
    ref = metadata.get('reference_numbering')
    if not isinstance(ref, dict):
        structural = metadata.get('structural_rules')
        if isinstance(structural, dict):
            ref = structural.get('reference_numbering')
    if not isinstance(ref, dict):
        return None
    if ref.get('enabled') is False:
        return empty_reference_numbering_map('reference_numbering_disabled_by_rules')
    pattern = ref.get('pattern') or ref.get('style') or ref.get('prefix_style') or 'bracket'
    pattern_map = {
        'square': 'bracket',
        'square_brackets': 'bracket',
        'brackets': 'bracket',
        'round': 'paren',
        'parentheses': 'paren',
        'plain': 'dot',
        'bare': 'dot',
        'plain_dot': 'dot',
        'dot': 'dot',
        'fullwidth_bracket': 'fullwidth_bracket',
        'fullwidth_dot': 'fullwidth_dot',
        'ideographic_comma': 'ideographic_comma',
    }
    return fallback_reference_numbering_map(
        pattern_map.get(str(pattern), str(pattern)),
        reason='reference_numbering_from_explicit_rules',
    )


def write_reference_numbering_map(reference_numbering_map, path):
    if not path:
        return
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(reference_numbering_map, f, ensure_ascii=False, indent=2)
    print(f"  Wrote reference numbering map: {path}")


def load_reference_numbering_map(path):
    if not path:
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def reference_numbering_uses_visible_text(reference_numbering_map):
    if not reference_numbering_map:
        return False
    return (
        reference_numbering_map.get('mode') == 'visible_text'
        or bool(reference_numbering_map.get('pattern'))
    )


def reference_numbering_uses_word_auto(reference_numbering_map):
    if not reference_numbering_map:
        return False
    return (
        reference_numbering_map.get('mode') == 'word_auto'
        or bool(reference_numbering_map.get('word_auto_enabled'))
    )


def looks_like_numberless_reference_item(text):
    stripped = (text or '').strip()
    if not stripped or reference_numbering_match(stripped):
        return False
    if looks_like_reference_zone_noise(stripped):
        return False
    if re.match(r'^\s*(参考文献|References?)\s*[:：]?$', stripped, re.I):
        return False
    if re.match(r'^\s*\d+(?:[\.．]|\s{1,6})\s+\S+', stripped) and looks_like_numbered_heading(stripped):
        return False
    return looks_like_reference_item(stripped) and looks_like_reference_item_start(stripped)


def looks_like_reference_item_start(text):
    stripped = (text or '').strip()
    if re.match(r'^(https?://|doi[:：]|DOI[:：]|Available\s+at\b)', stripped, re.I):
        return False
    if re.search(r'\[(?:J|M|C|D|P|S|R|N|EB/OL|OL)\]', stripped, re.I):
        return True
    if re.search(r'\b(19|20)\d{2}\b', stripped) and re.search(
        r'\b(?:IEEE|ACM|arXiv|PMLR|Journal|Proceedings|Press|Transactions)\b',
        stripped,
    ):
        return True
    head = re.split(r'[\.．。]', stripped, maxsplit=1)[0]
    if len(head) > 140:
        return False
    if re.search(r'[，,、;；]', head) and re.search(r'[A-Za-z\u4e00-\u9fff]', head):
        return True
    if re.match(r'^[A-Z][A-Za-z-]+(?:\s+[A-Z][A-Za-z-]+){0,3}\b', head):
        return True
    if re.match(r'^[\u4e00-\u9fff]{2,4}(?:[，,、;；]\s*[\u4e00-\u9fff]{2,4}){0,12}$', head):
        return True
    return False


def first_content_insert_index(p):
    for idx, child in enumerate(list(p)):
        if child.tag == w('pPr'):
            continue
        return idx
    return len(list(p))


def prepend_reference_number(p, number, pattern):
    p.insert(first_content_insert_index(p), make_text_run(format_reference_number(number, pattern)))


def clear_reference_paragraph_numbering(p):
    pPr = get_direct_child(p, w('pPr'))
    if pPr is None:
        return 0
    return remove_children_by_local_name(pPr, {'numPr'})


def first_text_node_with_offset(p):
    offset = 0
    for node in p.iter():
        if node.tag == w('t'):
            return node, offset
        if node.tag == w('tab'):
            offset += 1
        elif node.tag == w('br'):
            offset += 1
    return None, offset


def replace_reference_number_prefix(p, existing, number, pattern):
    replacement = format_reference_number(number, pattern)
    text_node, leading_offset = first_text_node_with_offset(p)
    if text_node is None:
        prepend_reference_number(p, number, pattern)
        return True
    prefix_len = existing.get('prefix_len', 0)
    text = text_node.text or ''
    remove_from_text = max(0, prefix_len - leading_offset)
    if remove_from_text <= len(text):
        set_text_node_preserve_space(text_node, replacement + text[remove_from_text:].lstrip())
        return True
    # Complex/split prefix fallback: clear visible text prefix by prepending the
    # correct marker and leave later audit to catch the unusual run structure.
    prepend_reference_number(p, number, pattern)
    return False


def apply_reference_numbering_map_to_document(target_dir, reference_numbering_map, role_map):
    stats = {
        'enabled': bool((reference_numbering_map or {}).get('enabled')),
        'mode': (reference_numbering_map or {}).get('mode'),
        'pattern': (reference_numbering_map or {}).get('pattern'),
        'reference_items': 0,
        'already_numbered': 0,
        'added': 0,
        'renumbered': 0,
        'paragraph_numPr_removed': 0,
        'skipped_uncertain': 0,
        'added_examples': [],
        'renumbered_examples': [],
    }
    doc_path = os.path.join(target_dir, 'word', 'document.xml')
    if not role_map:
        return stats
    if reference_numbering_uses_word_auto(reference_numbering_map):
        stats['reference_items'] = sum(1 for item in role_map if item.get('role') == 'reference_item')
        stats['word_auto_preserved'] = True
        print(
            "  Reference numbering repair: template uses Word automatic numbering; "
            "preserved migrated reference_item numPr instead of adding visible prefixes"
        )
        return stats
    if not reference_numbering_uses_visible_text(reference_numbering_map):
        stats['skipped_uncertain'] = sum(1 for item in role_map if item.get('role') == 'reference_item')
        print("  Reference numbering map empty; skipped missing reference-number repair")
        return stats
    tree = ET.parse(doc_path)
    root = tree.getroot()
    paragraphs = []
    visible_index = 0
    for p in iter_body_paragraphs(root):
        text = get_text(p).strip()
        is_equation = paragraph_is_display_equation(p)
        if not text and not is_equation:
            continue
        if starts_english_front_matter_block(text) or is_template_marker(text):
            continue
        paragraphs.append((visible_index, p))
        visible_index += 1
    paragraph_by_index = {idx: p for idx, p in paragraphs}
    next_number = 1
    pattern = reference_numbering_map.get('pattern') or 'bracket'
    reference_items = [
        item for item in sorted(role_map, key=lambda it: it.get('index', -1))
        if item.get('role') == 'reference_item'
    ]
    for item in reference_items:
        idx = item.get('index')
        p = paragraph_by_index.get(idx)
        if p is None:
            continue
        text = get_text(p).strip()
        stats['reference_items'] += 1
        stats['paragraph_numPr_removed'] += clear_reference_paragraph_numbering(p)
        existing = reference_numbering_match(text)
        if existing:
            if existing['number'] == next_number and existing['pattern'] == pattern:
                stats['already_numbered'] += 1
            else:
                replace_reference_number_prefix(p, existing, next_number, pattern)
                stats['renumbered'] += 1
                if len(stats['renumbered_examples']) < 20:
                    stats['renumbered_examples'].append({
                        'paragraph_index': idx,
                        'old_number': existing['number'],
                        'new_number': next_number,
                        'text': text[:160],
                    })
            next_number += 1
            continue
        if not looks_like_numberless_reference_item(text):
            stats['skipped_uncertain'] += 1
            continue
        prepend_reference_number(p, next_number, pattern)
        stats['added'] += 1
        if len(stats['added_examples']) < 20:
            stats['added_examples'].append({
                'paragraph_index': idx,
                'number': next_number,
                'text': text[:160],
            })
        next_number += 1
    if stats['added'] or stats['renumbered'] or stats['paragraph_numPr_removed']:
        write_xml(tree, doc_path)
    print(
        "  Reference numbering repair: "
        f"added={stats['added']}, renumbered={stats['renumbered']}, "
        f"already_numbered={stats['already_numbered']}, "
        f"paragraph_numPr_removed={stats['paragraph_numPr_removed']}, "
        f"skipped_uncertain={stats['skipped_uncertain']}"
    )
    return stats


def extract_superscript_map(doc_dir):
    doc_path = os.path.join(doc_dir, 'word', 'document.xml')
    tree = ET.parse(doc_path)
    root = tree.getroot()
    patterns = {
        'author_markers': {},
        'affiliation_markers': {},
        'body_citation_markers': {},
    }
    examples = []
    in_references = False
    english_context = {'mode': None, 'step': 0}
    citation_context = {'open': False}
    visible_index = 0
    for p in iter_body_paragraphs(root):
        text = get_text(p).strip()
        if not text:
            continue
        if starts_english_front_matter_block(text):
            english_context = {'mode': 'front_matter', 'step': 0}
            citation_context['open'] = False
            continue
        role = (
            role_from_template_pstyle(paragraph_style_id(p), text)
            or classify_paragraph(text, visible_index, in_references, english_context, citation_context)
            or 'body'
        )
        if role == 'references_heading':
            in_references = True
        for run in p.iter(w('r')):
            marker = run_text(run).strip()
            if not marker or not is_run_superscript(run):
                continue
            marker_key = None
            if role in ('author', 'english_author') and re.fullmatch(SUPERSCRIPT_MARKER_RE, marker):
                marker_key = 'author_markers'
            elif role in ('affiliation', 'english_affiliation') and re.fullmatch(SUPERSCRIPT_MARKER_RE, marker):
                marker_key = 'affiliation_markers'
            elif role == 'body' and looks_like_superscript_reference_citation(marker):
                marker_key = 'body_citation_markers'
            if marker_key:
                patterns[marker_key][marker] = patterns[marker_key].get(marker, 0) + 1
                examples.append({
                    'paragraph_index': visible_index,
                    'role': role,
                    'marker': marker,
                    'text': text[:160],
                })
        visible_index += 1
    author_affiliation_enabled = bool(patterns['author_markers'] or patterns['affiliation_markers'])
    reference_citation_enabled = bool(patterns['body_citation_markers'])
    return {
        'version': SUPERSCRIPT_MAP_VERSION,
        'enabled': author_affiliation_enabled or reference_citation_enabled,
        'categories': {
            'author_affiliation': {
                'enabled': author_affiliation_enabled,
                'evidence': sorted(set(patterns['author_markers']) | set(patterns['affiliation_markers'])),
            },
            'reference_citation': {
                'enabled': reference_citation_enabled,
                'evidence': sorted(patterns['body_citation_markers']),
                'warning_if_disabled': (
                    'Template did not provide explicit body reference-citation superscript evidence; '
                    'target reference citations are preserved unchanged.'
                ),
            },
        },
        'patterns': {key: sorted(value) for key, value in patterns.items()},
        'counts': patterns,
        'examples': examples[:80],
        'policy': (
            'Apply superscript only to matching small markers in compatible roles; '
            'never make an entire author/affiliation paragraph superscript.'
        ),
    }


def empty_superscript_map(reason='non_docx_text_only_route'):
    return {
        'version': SUPERSCRIPT_MAP_VERSION,
        'enabled': False,
        'reason': reason,
        'categories': {
            'author_affiliation': {'enabled': False, 'patterns': {}, 'examples': []},
            'reference_citation': {'enabled': False, 'patterns': {}, 'examples': []},
        },
        'patterns': {},
        'counts': {},
        'examples': [],
        'policy': 'Superscript evidence was not taken from a non-DOCX carrier.',
    }


def looks_like_superscript_reference_citation(text):
    stripped = (text or '').strip()
    return bool(
        re.fullmatch(r'(?:\[\d+(?:[-,，]\d+)*\]|\(\d+(?:[-,，]\d+)*\)|\^\d+(?:[-,，]\d+)*)', stripped)
    )


def write_superscript_map(superscript_map, path):
    if not path:
        return
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(superscript_map, f, ensure_ascii=False, indent=2)
    print(f"  Wrote superscript map: {path}")


def load_superscript_map(path):
    if not path:
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_equation_layout_map(doc_dir):
    doc_path = os.path.join(doc_dir, 'word', 'document.xml')
    tree = ET.parse(doc_path)
    root = tree.getroot()
    samples = []
    for idx, p in enumerate(iter_body_paragraphs(root, include_tables=True)):
        equation_kinds = paragraph_equation_kinds(p)
        if not equation_kinds:
            continue
        text = get_text(p)
        profile = paragraph_tab_profile(p)
        tabs_xml = paragraph_tabs_xml(p)
        has_number = equation_number_text(text) is not None or profile.get('number_index') is not None
        is_display = paragraph_is_display_equation(p)
        has_paragraph_layout_evidence = bool(
            tabs_xml or paragraph_alignment(p) or paragraph_style_id(p)
        )
        has_tab_run_evidence = bool(
            profile.get('tabs_before_equation') or
            profile.get('tabs_between_equation_and_number') or
            profile.get('tabs_after_number')
        )
        if has_tab_run_evidence or (is_display and has_paragraph_layout_evidence):
            samples.append({
                'paragraph_index': idx,
                'has_number': has_number,
                'number_text': equation_number_text(text),
                'equation_kinds': equation_kinds,
                'tabs_xml': tabs_xml,
                'tab_stops': summarize_tabs_xml(tabs_xml),
                'profile': profile,
                'paragraph_alignment': paragraph_alignment(p),
                'source_style_id': paragraph_style_id(p),
                'text': text[:160],
            })
    numbered = next((sample for sample in samples if sample.get('has_number')), None)
    unnumbered = next((sample for sample in samples if not sample.get('has_number')), None)
    return {
        'version': EQUATION_LAYOUT_MAP_VERSION,
        'enabled': bool(numbered or unnumbered),
        'numbered_equation': numbered,
        'unnumbered_equation': unnumbered,
        'samples': samples[:30],
        'policy': (
            'Apply paragraph tab stops and tab-run layout to target equation paragraphs; '
            'do not modify OMML equation content.'
        ),
    }


def fallback_equation_layout_map(reason='non_docx_text_only_route'):
    return {
        'version': EQUATION_LAYOUT_MAP_VERSION,
        'enabled': False,
        'numbered_equation': None,
        'unnumbered_equation': None,
        'samples': [],
        'fallback_expected': True,
        'reason': reason,
        'policy': (
            'Equation layout evidence was not taken from a non-DOCX carrier; '
            'target numbered display equations should use computed section/column fallback tabs.'
        ),
    }


def summarize_tabs_xml(tabs_xml):
    if not tabs_xml:
        return []
    try:
        tabs = ET.fromstring(tabs_xml)
    except ET.ParseError:
        return []
    return [attrs_without_ns(tab) for tab in tabs if local_name(tab.tag) == 'tab']


def paragraph_alignment(p):
    pPr = get_direct_child(p, w('pPr'))
    jc = child_by_local_name(pPr, 'jc')
    return jc.get(w('val')) if jc is not None else None


def write_equation_layout_map(equation_layout_map, path):
    if not path:
        return
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(equation_layout_map, f, ensure_ascii=False, indent=2)
    print(f"  Wrote equation layout map: {path}")


def load_equation_layout_map(path):
    if not path:
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def iter_body_tables(root):
    body = root.find(w('body'))
    if body is None:
        return
    for tbl in body.iter(w('tbl')):
        yield tbl


def direct_table_rows(tbl):
    return [child for child in tbl if child.tag == w('tr')]


def direct_row_cells(tr):
    return [child for child in tr if child.tag == w('tc')]


def first_nonempty_paragraph_in_table_part(elem):
    for p in elem.iter(w('p')):
        if get_text(p).strip():
            return p
    return None


def table_part_signature(elem):
    p = first_nonempty_paragraph_in_table_part(elem)
    if p is None:
        return {'pPr': '', 'rPr': ''}
    return paragraph_signature(p)


def table_row_profile(tr, role):
    cells = direct_row_cells(tr)
    first_cell = cells[0] if cells else None
    trPr = get_direct_child(tr, w('trPr'))
    tcPr = get_direct_child(first_cell, w('tcPr')) if first_cell is not None else None
    return {
        'role': role,
        'trPr_xml': xml_string(trPr),
        'tcPr_xml': xml_string(tcPr),
        'paragraph_signature': table_part_signature(tr),
        'summary': {
            'row': summarize_row_pr(trPr),
            'first_cell': summarize_cell_pr(tcPr),
        },
        'cell_profiles': [
            {
                'index': idx,
                'tcPr_xml': xml_string(get_direct_child(cell, w('tcPr'))),
                'summary': summarize_cell_pr(get_direct_child(cell, w('tcPr'))),
                'sample': get_text(cell).strip()[:80],
            }
            for idx, cell in enumerate(cells)
        ],
        'sample': get_text(tr).strip()[:160],
    }


def classify_table_kind(tbl):
    rows = direct_table_rows(tbl)
    text = get_text(tbl).strip()
    if len(rows) <= 1:
        return 'single_row'
    if re.search(r'(作者|Author|单位|Affiliation)', text, re.I) and len(text) < 800:
        return 'front_matter_table'
    return 'data_table'


def table_profile(tbl, index):
    rows = direct_table_rows(tbl)
    tblPr = get_direct_child(tbl, w('tblPr'))
    profiles = {}
    if rows:
        profiles['header'] = table_row_profile(rows[0], 'header')
        body_row = rows[1] if len(rows) > 2 else rows[-1]
        profiles['body'] = table_row_profile(body_row, 'body')
        profiles['footer'] = table_row_profile(rows[-1], 'footer')
    profile = {
        'index': index,
        'kind': classify_table_kind(tbl),
        'rows': len(rows),
        'cols': max((len(direct_row_cells(row)) for row in rows), default=0),
        'chars': len(get_text(tbl).strip()),
        'tblPr_xml': xml_string(tblPr),
        'tblGrid_xml': xml_string(get_direct_child(tbl, w('tblGrid'))),
        'summary': summarize_table_pr(tblPr),
        'row_profiles': profiles,
        'sample': get_text(tbl).strip()[:200],
    }
    profile['format_strength'] = table_format_strength(profile)
    profile['weak_format'] = profile['format_strength'] < 8
    return profile


def count_border_edges(border_summary):
    if not border_summary:
        return 0
    count = 0
    for attrs in border_summary.values():
        val = (attrs or {}).get('val')
        if val and val not in ('nil', 'none'):
            count += 1
    return count


def table_format_strength(profile):
    """Score only formatting evidence, not table text volume."""
    summary = profile.get('summary') or {}
    strength = 0
    strength += count_border_edges(summary.get('borders')) * 3
    if summary.get('style'):
        strength += 2
    if summary.get('shading'):
        strength += 1
    if summary.get('cell_margins'):
        strength += 1
    if summary.get('alignment'):
        strength += 1
    for row_profile in (profile.get('row_profiles') or {}).values():
        row_summary = (row_profile.get('summary') or {})
        if (row_summary.get('row') or {}).get('is_header'):
            strength += 1
        strength += count_border_edges(((row_summary.get('first_cell') or {}).get('borders'))) * 2
        if (row_summary.get('first_cell') or {}).get('shading'):
            strength += 1
        for cell_profile in row_profile.get('cell_profiles') or []:
            cell_summary = cell_profile.get('summary') or {}
            strength += count_border_edges(cell_summary.get('borders'))
            if cell_summary.get('shading'):
                strength += 1
    return strength


def table_profile_score(profile):
    score = 0.0
    score += profile.get('format_strength', 0) * 20.0
    score += min(profile.get('chars', 0) / 40.0, 40.0)
    score += min(profile.get('rows', 0), 10) * 5.0
    score += min(profile.get('cols', 0), 8) * 3.0
    borders = ((profile.get('summary') or {}).get('borders') or {})
    score += len(borders) * 8.0
    for row_profile in (profile.get('row_profiles') or {}).values():
        cell_borders = (((row_profile.get('summary') or {}).get('first_cell') or {}).get('borders') or {})
        score += len(cell_borders) * 3.0
        for cell_profile in row_profile.get('cell_profiles') or []:
            score += len(((cell_profile.get('summary') or {}).get('borders') or {})) * 1.0
    if profile.get('kind') == 'data_table':
        score += 25.0
    if profile.get('kind') == 'front_matter_table':
        score -= 30.0
    if profile.get('weak_format') and len(profile.get('row_profiles') or {}) <= 1:
        score -= 25.0
    return score


def border_xml(side, attrs=None):
    attrs = attrs or TABLE_THREE_LINE_BORDER
    elem = ET.Element(w(side))
    for key, value in attrs.items():
        elem.set(w(key), str(value))
    return xml_string(elem)


def border_container_xml(container_name, sides):
    elem = ET.Element(w(container_name))
    for side, attrs in sides.items():
        try:
            elem.append(ET.fromstring(border_xml(side, attrs)))
        except ET.ParseError:
            continue
    return xml_string(elem)


def table_pr_xml_from_borders(borders):
    tblPr = ET.Element(w('tblPr'))
    tblBorders = ET.fromstring(border_container_xml('tblBorders', borders))
    tblPr.append(tblBorders)
    return xml_string(tblPr)


def tc_pr_xml_from_borders(borders):
    tcPr = ET.Element(w('tcPr'))
    tcBorders = ET.fromstring(border_container_xml('tcBorders', borders))
    tcPr.append(tcBorders)
    return xml_string(tcPr)


def three_line_table_profile(language='en', reason='fallback', columns=1):
    ooxml_table = fallback_ooxml_table_spec(language=language, columns=columns)
    if ooxml_table:
        tbl_pr_xml = ooxml_table.get('tblPr_xml') or ''
        header_tc_pr_xml = ooxml_table.get('header_tcPr_xml') or ''
        body_tc_pr_xml = ooxml_table.get('body_tcPr_xml') or ''
        footer_tc_pr_xml = ooxml_table.get('footer_tcPr_xml') or ''
        header_separator_border = ooxml_table.get('header_separator_border') or TABLE_THREE_LINE_HEADER_SEPARATOR_BORDER
        return {
            'index': -1,
            'kind': 'fallback_three_line_table',
            'language': language,
            'fallback': True,
            'fallback_source': 'assets/fallback_ooxml_spec.json',
            'fallback_variant': fallback_variant_key(language, columns),
            'fallback_reason': reason,
            'rows': 3,
            'cols': 3,
            'chars': 0,
            'tblPr_xml': tbl_pr_xml,
            'tblGrid_xml': '',
            'summary': summarize_table_pr(xml_child_from_text(tbl_pr_xml)),
            'multi_header_separator': ooxml_table.get('multi_header_separator', True),
            'header_separator_border': header_separator_border,
            'row_profiles': {
                'header': {
                    'role': 'header',
                    'format_tags': ['tcBorders', 'vAlign', 'shd', 'tcMar'],
                    'trPr_xml': '',
                    'tcPr_xml': header_tc_pr_xml,
                    'paragraph_signature': {'pPr': '', 'rPr': ''},
                    'summary': {'row': {}, 'first_cell': summarize_cell_pr(xml_child_from_text(header_tc_pr_xml))},
                    'cell_profiles': [],
                    'sample': '',
                },
                'body': {
                    'role': 'body',
                    'format_tags': ['tcBorders', 'vAlign', 'shd', 'tcMar'],
                    'trPr_xml': '',
                    'tcPr_xml': body_tc_pr_xml,
                    'paragraph_signature': {'pPr': '', 'rPr': ''},
                    'summary': {'row': {}, 'first_cell': summarize_cell_pr(xml_child_from_text(body_tc_pr_xml))},
                    'cell_profiles': [],
                    'sample': '',
                },
                'footer': {
                    'role': 'footer',
                    'format_tags': ['tcBorders', 'vAlign', 'shd', 'tcMar'],
                    'trPr_xml': '',
                    'tcPr_xml': footer_tc_pr_xml,
                    'paragraph_signature': {'pPr': '', 'rPr': ''},
                    'summary': {'row': {}, 'first_cell': summarize_cell_pr(xml_child_from_text(footer_tc_pr_xml))},
                    'cell_profiles': [],
                    'sample': '',
                },
            },
            'sample': '',
            'format_strength': 18,
            'weak_format': False,
        }
    top_bottom = {
        'top': TABLE_THREE_LINE_BORDER_THICK,
        'bottom': TABLE_THREE_LINE_BORDER_THICK,
    }
    none_sides = {
        'left': TABLE_BORDER_NONE,
        'right': TABLE_BORDER_NONE,
        'insideH': TABLE_BORDER_NONE,
        'insideV': TABLE_BORDER_NONE,
    }
    header_cell = {
        'top': TABLE_THREE_LINE_BORDER_THICK,
        'left': TABLE_BORDER_NONE,
        'right': TABLE_BORDER_NONE,
        'bottom': TABLE_THREE_LINE_BORDER,
    }
    body_cell = {
        'top': TABLE_BORDER_NONE,
        'left': TABLE_BORDER_NONE,
        'right': TABLE_BORDER_NONE,
        'bottom': TABLE_BORDER_NONE,
    }
    footer_cell = {
        'top': TABLE_BORDER_NONE,
        'left': TABLE_BORDER_NONE,
        'right': TABLE_BORDER_NONE,
        'bottom': TABLE_THREE_LINE_BORDER_THICK,
    }
    table_borders = dict(top_bottom)
    table_borders.update(none_sides)
    profile = {
        'index': -1,
        'kind': 'fallback_three_line_table',
        'language': language,
        'fallback': True,
        'fallback_reason': reason,
        'rows': 3,
        'cols': 3,
        'chars': 0,
        'tblPr_xml': table_pr_xml_from_borders(table_borders),
        'tblGrid_xml': '',
        'summary': {
            'borders': table_borders,
            'raw_children': ['tblBorders'],
        },
        'multi_header_separator': True,
        'header_separator_border': TABLE_THREE_LINE_HEADER_SEPARATOR_BORDER,
        'row_profiles': {
            'header': {
                'role': 'header',
                'format_tags': ['tcBorders'],
                'trPr_xml': '',
                'tcPr_xml': tc_pr_xml_from_borders(header_cell),
                'paragraph_signature': {'pPr': '', 'rPr': ''},
                'summary': {'row': {}, 'first_cell': {'borders': header_cell}},
                'cell_profiles': [],
                'sample': '',
            },
            'body': {
                'role': 'body',
                'format_tags': ['tcBorders'],
                'trPr_xml': '',
                'tcPr_xml': tc_pr_xml_from_borders(body_cell),
                'paragraph_signature': {'pPr': '', 'rPr': ''},
                'summary': {'row': {}, 'first_cell': {'borders': body_cell}},
                'cell_profiles': [],
                'sample': '',
            },
            'footer': {
                'role': 'footer',
                'format_tags': ['tcBorders'],
                'trPr_xml': '',
                'tcPr_xml': tc_pr_xml_from_borders(footer_cell),
                'paragraph_signature': {'pPr': '', 'rPr': ''},
                'summary': {'row': {}, 'first_cell': {'borders': footer_cell}},
                'cell_profiles': [],
                'sample': '',
            },
        },
        'sample': '',
        'format_strength': 18,
        'weak_format': False,
    }
    return profile


def should_use_three_line_table_fallback(profiles, representative):
    if not profiles or representative is None:
        return True
    if representative.get('format_strength', 0) < 8:
        return True
    return False


def extract_table_format_map(doc_dir):
    doc_path = os.path.join(doc_dir, 'word', 'document.xml')
    tree = ET.parse(doc_path)
    root = tree.getroot()
    language = detect_template_language(doc_dir)
    columns = detect_fallback_columns(doc_dir)
    profiles = [table_profile(tbl, idx) for idx, tbl in enumerate(iter_body_tables(root))]
    if not profiles:
        fallback = three_line_table_profile(language, reason='no_template_table', columns=columns)
        return {
            'version': TABLE_FORMAT_MAP_VERSION,
            'enabled': True,
            'fallback_applied': True,
            'fallback_kind': 'three_line_table',
            'fallback_reason': 'no_template_table',
            'fallback_source': fallback.get('fallback_source'),
            'fallback_variant': fallback.get('fallback_variant'),
            'tables': [],
            'representative_table': fallback,
            'table_styles': {},
            'candidate_scores': [],
            'policy': (
                'Template has no usable body table XML. Apply a conservative academic '
                'three-line table fallback for Chinese and English templates: top rule, '
                'header bottom rule, bottom rule, and no vertical/internal grid lines. '
                'Do not rewrite cell text, formulas, drawings, media, width, or merge topology.'
            ),
        }
    scored = sorted(
        ((table_profile_score(profile), profile) for profile in profiles),
        key=lambda item: (item[0], item[1].get('rows', 0), item[1].get('cols', 0)),
        reverse=True
    )
    representative = scored[0][1]
    fallback_applied = False
    fallback_reason = None
    if should_use_three_line_table_fallback(profiles, representative):
        fallback_reason = 'weak_template_table_evidence'
        representative = three_line_table_profile(language, reason=fallback_reason, columns=columns)
        fallback_applied = True
    style_xml_by_id = get_table_style_xml_by_id(doc_dir)
    return {
        'version': TABLE_FORMAT_MAP_VERSION,
        'enabled': True,
        'fallback_applied': fallback_applied,
        'fallback_kind': 'three_line_table' if fallback_applied else None,
        'fallback_reason': fallback_reason,
        'fallback_source': representative.get('fallback_source') if fallback_applied else None,
        'fallback_variant': representative.get('fallback_variant') if fallback_applied else None,
        'representative_table': representative,
        'tables': profiles[:40],
        'table_styles': style_xml_by_id,
        'candidate_scores': [
            {
                'index': profile['index'],
                'kind': profile['kind'],
                'rows': profile['rows'],
                'cols': profile['cols'],
                'chars': profile['chars'],
                'score': round(score, 2),
                'format_strength': profile.get('format_strength'),
                'weak_format': profile.get('weak_format'),
            }
            for score, profile in scored[:40]
        ],
        'policy': (
            'Apply table body XML formatting directly: tblPr/tblBorders, row properties, '
            'cell properties/tcBorders, and table-internal paragraph/run properties. '
            'Do not rewrite cell text, formulas, drawings, media, or merge topology.'
        ),
    }


def fallback_table_format_map(language='en', columns=1, reason='non_docx_text_only_route'):
    fallback = three_line_table_profile(language, reason=reason, columns=columns)
    return {
        'version': TABLE_FORMAT_MAP_VERSION,
        'enabled': True,
        'fallback_applied': True,
        'fallback_kind': 'three_line_table',
        'fallback_reason': reason,
        'fallback_source': fallback.get('fallback_source'),
        'fallback_variant': fallback.get('fallback_variant'),
        'tables': [],
        'representative_table': fallback,
        'table_styles': {},
        'candidate_scores': [],
        'policy': (
            'Table formatting evidence was not taken from a non-DOCX carrier. '
            'Apply the selected bundled three-line table fallback while preserving target table content.'
        ),
    }


def get_table_style_xml_by_id(doc_dir):
    styles_path = os.path.join(doc_dir, 'word', 'styles.xml')
    if not os.path.exists(styles_path):
        return {}
    tree = ET.parse(styles_path)
    root = tree.getroot()
    styles = {}
    for style in root.findall(w('style')):
        if style.get(w('type')) != 'table':
            continue
        style_id = style.get(w('styleId'))
        if style_id:
            styles[style_id] = xml_string(style)
    return styles


def write_table_format_map(table_format_map, path):
    if not path:
        return
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(table_format_map, f, ensure_ascii=False, indent=2)
    print(f"  Wrote table format map: {path}")


def load_table_format_map(path):
    if not path:
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def replace_format_children(parent, source_xml, names):
    if parent is None:
        return 0
    try:
        source = ET.fromstring(source_xml) if source_xml else None
    except ET.ParseError:
        return 0
    before = len(list(parent))
    remove_children_by_local_name(parent, names)
    if source is not None:
        for child in source:
            if local_name(child.tag) in names:
                parent.append(clone_element(child))
    return 1 if len(list(parent)) != before or source is not None else 0


def table_width_element_from_xml(source_xml):
    try:
        source = ET.fromstring(source_xml) if source_xml else None
    except ET.ParseError:
        return None
    return child_by_local_name(source, 'tblW') if source is not None else None


def table_layout_element_from_xml(source_xml):
    try:
        source = ET.fromstring(source_xml) if source_xml else None
    except ET.ParseError:
        return None
    return child_by_local_name(source, 'tblLayout') if source is not None else None


def table_width_is_explicit(tblW):
    if tblW is None:
        return False
    width_type = tblW.get(w('type'))
    width_value = tblW.get(w('w'))
    if width_type in ('pct', 'dxa') and width_value not in (None, '', '0'):
        return True
    return False


def replace_single_child_by_local_name(parent, child):
    if parent is None or child is None:
        return 0
    lname = local_name(child.tag)
    before = xml_string(child_by_local_name(parent, lname))
    remove_children_by_local_name(parent, {lname})
    parent.append(clone_element(child))
    after = xml_string(child_by_local_name(parent, lname))
    return 1 if before != after else 0


def apply_table_width_policy(tblPr, profile, preserve_table_width=True, stats=None):
    stats = stats if stats is not None else {}
    tblW = table_width_element_from_xml(profile.get('tblPr_xml') if profile else '')
    tblLayout = table_layout_element_from_xml(profile.get('tblPr_xml') if profile else '')
    if tblW is None:
        stats['width_missing_in_template'] = stats.get('width_missing_in_template', 0) + 1
        return 0
    explicit = table_width_is_explicit(tblW)
    if preserve_table_width and not explicit:
        stats['width_preserved_auto_template'] = stats.get('width_preserved_auto_template', 0) + 1
        return 0
    if preserve_table_width and tblLayout is not None and tblLayout.get(w('type')) == 'autofit' and not explicit:
        stats['layout_preserved_autofit_template'] = stats.get('layout_preserved_autofit_template', 0) + 1
        return 0
    changed = 0
    changed += replace_single_child_by_local_name(tblPr, tblW)
    stats['width_overridden'] = stats.get('width_overridden', 0) + 1
    if tblLayout is not None:
        changed += replace_single_child_by_local_name(tblPr, tblLayout)
        stats['layout_overridden'] = stats.get('layout_overridden', 0) + 1
    return changed


def apply_table_part_paragraph_signature(elem, signature):
    if not signature:
        return 0
    changed = 0
    pPr_xml = signature.get('pPr')
    rPr_xml = signature.get('rPr')
    for p in elem.iter(w('p')):
        if not get_text(p).strip():
            continue
        if pPr_xml:
            pPr = get_or_add_child(p, w('pPr'), first=True)
            changed += replace_format_children(
                pPr, pPr_xml,
                DIRECT_PPR_TAGS | {'pBdr', 'shd', 'framePr', 'snapToGrid'}
            )
        if rPr_xml:
            for run in p.iter(w('r')):
                if not run_text(run).strip():
                    continue
                rPr = get_or_add_child(run, w('rPr'), first=True)
                changed += replace_format_children(rPr, rPr_xml, DIRECT_RPR_TAGS | {'vertAlign', 'vanish', 'bdr'})
    return changed


def apply_table_row_profile(tr, row_profile):
    if tr is None or not row_profile:
        return 0
    changed = 0
    trPr = get_or_add_child(tr, w('trPr'), first=True)
    changed += replace_format_children(trPr, row_profile.get('trPr_xml'), TABLE_ROW_FORMAT_TAGS)
    cell_format_tags = set(row_profile.get('format_tags') or TABLE_CELL_FORMAT_TAGS)
    cell_profiles = row_profile.get('cell_profiles') or []
    default_tcPr_xml = row_profile.get('tcPr_xml')
    for idx, tc in enumerate(direct_row_cells(tr)):
        tcPr = get_or_add_child(tc, w('tcPr'), first=True)
        cell_profile = cell_profiles[idx] if idx < len(cell_profiles) else {}
        tcPr_xml = cell_profile.get('tcPr_xml') or default_tcPr_xml
        changed += replace_format_children(tcPr, tcPr_xml, cell_format_tags)
    changed += apply_table_part_paragraph_signature(tr, row_profile.get('paragraph_signature'))
    return changed


def set_border_attrs(border_elem, attrs):
    before = dict(border_elem.attrib)
    for key in list(border_elem.attrib):
        del border_elem.attrib[key]
    for key, value in (attrs or {}).items():
        border_elem.set(w(key), str(value))
    return 1 if before != dict(border_elem.attrib) else 0


def set_tc_border(tc, side, attrs):
    tcPr = get_or_add_child(tc, w('tcPr'), first=True)
    tcBorders = get_or_add_child(tcPr, w('tcBorders'))
    border = child_by_local_name(tcBorders, side)
    if border is None:
        border = ET.Element(w(side))
        tcBorders.append(border)
    return set_border_attrs(border, attrs)


def row_text_for_header_inference(tr):
    return ' '.join(get_text(tc).strip() for tc in direct_row_cells(tr) if get_text(tc).strip())


def cell_grid_span(tc):
    tcPr = get_direct_child(tc, w('tcPr'))
    grid_span = child_by_local_name(tcPr, 'gridSpan')
    try:
        return max(1, int(grid_span.get(w('val')) or 1)) if grid_span is not None else 1
    except (TypeError, ValueError):
        return 1


def cell_has_vertical_merge(tc):
    tcPr = get_direct_child(tc, w('tcPr'))
    return child_by_local_name(tcPr, 'vMerge') is not None


def row_effective_column_count(tr):
    return sum(cell_grid_span(tc) for tc in direct_row_cells(tr))


def row_has_merge_topology(tr):
    return any(cell_grid_span(tc) > 1 or cell_has_vertical_merge(tc) for tc in direct_row_cells(tr))


def row_cell_texts(tr):
    return [get_text(tc).strip() for tc in direct_row_cells(tr)]


def text_looks_numeric_data(text):
    compact = re.sub(r'\s+', '', text or '')
    if not compact:
        return False
    if re.fullmatch(r'[+-]?\d+(?:\.\d+)?%?', compact):
        return True
    if re.fullmatch(r'[+-]?\d+(?:\.\d+)?(?:±|~|-|—|–|至|到)[+-]?\d+(?:\.\d+)?%?', compact):
        return True
    if re.fullmatch(r'[×xX√/\\-]+', compact):
        return True
    return False


def row_feature_for_header_inference(row, max_cols):
    texts = row_cell_texts(row)
    nonempty = [text for text in texts if text]
    cell_count = max(1, len(texts))
    avg_cell_len = sum(len(text) for text in nonempty) / max(1, len(nonempty))
    numeric_cells = sum(1 for text in nonempty if text_looks_numeric_data(text))
    numeric_ratio = numeric_cells / float(max(1, len(nonempty)))
    text = ' '.join(nonempty)
    labelish_re = re.compile(
        r'^(Top\s*\d+|Acc(?:uracy)?|Precision|Recall|F1|AP|mAP|P@\\d+|R@\\d+|'
        r'准确率|精确率|召回率|分类方法|姿态维度|目标|指标|方法|维度|类别|模型|数据集|'
        r'均值|标准差|Mean|Std\\.?|Dataset|Method|Metric|Category|Dimension)$',
        re.I,
    )
    labelish_cells = sum(1 for text in nonempty if labelish_re.match(text.strip()))
    has_sentence_punct = bool(re.search(r'[。；;.!?？]', text))
    return {
        'text': text,
        'nonempty_cells': len(nonempty),
        'cell_count': cell_count,
        'effective_cols': row_effective_column_count(row),
        'max_cols': max_cols,
        'avg_cell_len': avg_cell_len,
        'numeric_cells': numeric_cells,
        'numeric_ratio': numeric_ratio,
        'labelish_cells': labelish_cells,
        'labelish_ratio': labelish_cells / float(max(1, len(nonempty))),
        'has_merge_topology': row_has_merge_topology(row),
        'has_spanning_group_cell': any(cell_grid_span(tc) > 1 for tc in direct_row_cells(row)),
        'raw_cell_count_below_grid': cell_count < max_cols,
        'has_sentence_punct': has_sentence_punct,
        'is_short_label_row': bool(nonempty) and avg_cell_len <= 18 and not has_sentence_punct,
        'is_data_like': (
            numeric_cells >= 2
            or numeric_ratio >= 0.5
            or (numeric_cells >= 1 and avg_cell_len > 18)
        ),
    }


def infer_three_line_header_row_info(rows):
    if len(rows) <= 1:
        return {
            'count': 1 if rows else 0,
            'features': [],
            'reason': 'single_or_empty_table',
        }
    max_cols = max(row_effective_column_count(row) for row in rows) or 1
    features = [row_feature_for_header_inference(row, max_cols) for row in rows[: min(4, len(rows))]]
    header_count = 1
    reasons = []
    for idx, feature in enumerate(features):
        if idx == 0:
            reasons.append('first_row_header')
            continue
        if idx >= len(rows) - 1:
            break
        if not feature['text']:
            continue
        prev = features[idx - 1] if idx - 1 < len(features) else {}
        next_feature = features[idx + 1] if idx + 1 < len(features) else {}
        merge_continuation = bool(prev.get('has_merge_topology') or feature['has_merge_topology'])
        grouped_header_continuation = (
            feature['is_short_label_row']
            and (
                merge_continuation
                or prev.get('has_spanning_group_cell')
                or prev.get('raw_cell_count_below_grid')
            )
            and (
                not next_feature
                or next_feature.get('is_data_like')
                or next_feature.get('avg_cell_len', 99) > feature.get('avg_cell_len', 0)
            )
        )
        likely_subheader = (
            feature['is_short_label_row']
            and (
                merge_continuation
                or feature['labelish_ratio'] >= 0.5
                or (next_feature and next_feature.get('is_data_like') and feature['numeric_cells'] == 0)
                or grouped_header_continuation
            )
        )
        if likely_subheader:
            header_count = idx + 1
            reasons.append(
                f'row_{idx}_subheader'
                + ('_grouped' if grouped_header_continuation else '')
            )
            continue
        if feature['is_data_like']:
            reasons.append(f'row_{idx}_data_like_stop')
            break
        break
    header_count = max(1, min(header_count, len(rows) - 1))
    return {
        'count': header_count,
        'features': features,
        'reason': ','.join(reasons) or 'default_first_row',
    }


def infer_three_line_header_row_count(rows):
    return infer_three_line_header_row_info(rows).get('count', 0)


def enforce_three_line_table_cell_borders(tbl, stats=None, profile=None):
    """Make fallback three-line tables render in Word by using cell borders.

    Table-level tblBorders are kept as a coarse backup, but Word often renders
    the stable three-line model from cell borders: first row top, last header
    row bottom, and final row bottom.
    """
    stats = stats if stats is not None else {}
    rows = direct_table_rows(tbl)
    if not rows:
        return 0
    changed = 0
    header_info = infer_three_line_header_row_info(rows)
    header_rows = header_info.get('count') or 1
    header_bottom_index = max(0, header_rows - 1)
    separator_enabled = True if profile is None else profile.get('multi_header_separator', True)
    separator_border = (profile or {}).get('header_separator_border') or TABLE_THREE_LINE_HEADER_SEPARATOR_BORDER
    for row_idx, row in enumerate(rows):
        for tc in direct_row_cells(row):
            for side in ('left', 'right', 'insideH', 'insideV', 'top', 'bottom'):
                changed += set_tc_border(tc, side, TABLE_BORDER_NONE)
            if row_idx == 0:
                changed += set_tc_border(tc, 'top', TABLE_THREE_LINE_BORDER_THICK)
            if separator_enabled and header_rows > 1 and row_idx < header_bottom_index:
                changed += set_tc_border(tc, 'bottom', separator_border)
            if separator_enabled and header_rows > 1 and 0 < row_idx <= header_bottom_index:
                changed += set_tc_border(tc, 'top', separator_border)
            if row_idx == header_bottom_index:
                changed += set_tc_border(tc, 'bottom', TABLE_THREE_LINE_BORDER)
            if row_idx == header_bottom_index + 1 and row_idx < len(rows) - 1:
                changed += set_tc_border(tc, 'top', TABLE_THREE_LINE_BORDER)
            if row_idx == len(rows) - 1:
                changed += set_tc_border(tc, 'bottom', TABLE_THREE_LINE_BORDER_THICK)
    stats['three_line_cell_border_enforced'] = stats.get('three_line_cell_border_enforced', 0) + 1
    stats.setdefault('three_line_header_rows', []).append(header_rows)
    stats.setdefault('three_line_header_inference', []).append({
        'header_rows': header_rows,
        'reason': header_info.get('reason'),
        'features': header_info.get('features'),
    })
    if separator_enabled and header_rows > 1:
        stats['three_line_multi_header_separator_enforced'] = stats.get('three_line_multi_header_separator_enforced', 0) + 1
    return changed


def apply_table_profile_to_table(tbl, profile, preserve_table_width=True, stats=None):
    if tbl is None or not profile:
        return 0
    changed = 0
    tblPr = get_or_add_child(tbl, w('tblPr'), first=True)
    changed += replace_format_children(tblPr, profile.get('tblPr_xml'), TABLE_PR_FORMAT_TAGS)
    changed += apply_table_width_policy(
        tblPr, profile,
        preserve_table_width=preserve_table_width,
        stats=stats,
    )
    rows = direct_table_rows(tbl)
    row_profiles = profile.get('row_profiles') or {}
    if rows and row_profiles.get('header'):
        changed += apply_table_row_profile(rows[0], row_profiles['header'])
    if row_profiles.get('body'):
        body_rows = rows[1:-1] if len(rows) > 2 else rows[1:]
        for row in body_rows:
            changed += apply_table_row_profile(row, row_profiles['body'])
    if len(rows) > 1 and row_profiles.get('footer'):
        changed += apply_table_row_profile(rows[-1], row_profiles['footer'])
    if profile.get('kind') == 'fallback_three_line_table':
        changed += enforce_three_line_table_cell_borders(tbl, stats=stats, profile=profile)
    return changed


def select_table_profile_for_target(index, profiles, representative, target_count=None, stats=None):
    stats = stats if stats is not None else {}
    if not profiles:
        return representative
    target_count = target_count if target_count is not None else len(profiles)
    profile = profiles[index] if index < len(profiles) else None
    if len(profiles) != target_count:
        stats['representative_reuse_count'] = stats.get('representative_reuse_count', 0) + 1
        if profile is not None and representative is not None and profile.get('index') != representative.get('index'):
            stats.setdefault('index_profile_bypassed', []).append({
                'target_table': index,
                'template_table': profile.get('index'),
                'template_format_strength': profile.get('format_strength'),
                'representative_table': representative.get('index'),
                'reason': 'template_target_count_mismatch',
            })
        return representative
    if profile is not None:
        rep_strength = (representative or {}).get('format_strength', 0)
        profile_strength = profile.get('format_strength', 0)
        if representative is not None and profile.get('index') != representative.get('index') and profile_strength < max(8, rep_strength * 0.35):
            stats['weak_profile_bypassed_count'] = stats.get('weak_profile_bypassed_count', 0) + 1
            stats.setdefault('index_profile_bypassed', []).append({
                'target_table': index,
                'template_table': profile.get('index'),
                'template_format_strength': profile_strength,
                'representative_table': representative.get('index'),
                'representative_format_strength': rep_strength,
                'reason': 'weak_template_table_format',
            })
            return representative
        return profile
    return representative


def install_table_styles_from_map(target_dir, table_format_map):
    table_styles = (table_format_map or {}).get('table_styles') or {}
    if not table_styles:
        return 0
    styles_path = os.path.join(target_dir, 'word', 'styles.xml')
    if not os.path.exists(styles_path):
        return 0
    tree = ET.parse(styles_path)
    root = tree.getroot()
    existing = {
        style.get(w('styleId')): style
        for style in root.findall(w('style'))
        if style.get(w('styleId'))
    }
    installed = 0
    for style_id, style_xml in table_styles.items():
        try:
            style_elem = ET.fromstring(style_xml)
        except ET.ParseError:
            continue
        old = existing.get(style_id)
        if old is not None:
            root.remove(old)
        root.append(style_elem)
        installed += 1
    if installed:
        write_xml(tree, styles_path)
    return installed


def apply_table_format_map_to_document(target_dir, table_format_map, preserve_table_width=True):
    stats = {
        'target_tables': 0,
        'applied': 0,
        'changed_nodes': 0,
        'skipped_no_template_table': 0,
        'preserve_table_width': preserve_table_width,
        'width_preserved_auto_template': 0,
        'width_overridden': 0,
    }
    doc_path = os.path.join(target_dir, 'word', 'document.xml')
    tree = ET.parse(doc_path)
    root = tree.getroot()
    target_tables = list(iter_body_tables(root))
    stats['target_tables'] = len(target_tables)
    if not table_format_map or not table_format_map.get('enabled'):
        stats['skipped_no_template_table'] = len(target_tables)
        print("  Table format map empty; skipped table body formatting")
        return stats
    if table_format_map.get('fallback_applied'):
        stats['fallback_applied'] = True
        stats['fallback_kind'] = table_format_map.get('fallback_kind')
        stats['fallback_reason'] = table_format_map.get('fallback_reason')
    stats['installed_table_styles'] = install_table_styles_from_map(target_dir, table_format_map)
    profiles = table_format_map.get('tables') or []
    representative = table_format_map.get('representative_table')
    if len(profiles) != len(target_tables) and target_tables:
        if table_format_map.get('fallback_applied'):
            print(
                "  WARNING: template table XML evidence missing or weak; "
                "using conservative academic three-line table fallback"
            )
        else:
            print(
                "  WARNING: template/target table counts differ; "
                "using the strongest representative template table format to avoid weak/placeholder table leakage"
            )
    for idx, tbl in enumerate(target_tables):
        profile = select_table_profile_for_target(
            idx, profiles, representative,
            target_count=len(target_tables),
            stats=stats,
        )
        changed = apply_table_profile_to_table(
            tbl, profile,
            preserve_table_width=preserve_table_width,
            stats=stats,
        )
        if changed:
            stats['applied'] += 1
            stats['changed_nodes'] += changed
    write_xml(tree, doc_path)
    print(f"  Applied table body formatting: {stats}")
    return stats


def superscript_patterns_enabled(superscript_map):
    if not superscript_map or not superscript_map.get('enabled'):
        return False
    patterns = superscript_map.get('patterns') or {}
    return any(patterns.get(key) for key in patterns)


def superscript_category_enabled(superscript_map, category):
    categories = superscript_map.get('categories') or {}
    if category in categories:
        return bool(categories.get(category, {}).get('enabled'))
    patterns = superscript_map.get('patterns') or {}
    if category == 'author_affiliation':
        return bool(patterns.get('author_markers') or patterns.get('affiliation_markers'))
    if category == 'reference_citation':
        return bool(patterns.get('body_citation_markers'))
    return False


def apply_superscript_map_to_document(target_dir, superscript_map, role_map):
    if not superscript_patterns_enabled(superscript_map):
        print("  Superscript map empty; skipped run-level superscript application")
        return {'cleared': 0, 'applied': 0, 'skipped_complex_runs': 0}
    doc_path = os.path.join(target_dir, 'word', 'document.xml')
    tree = ET.parse(doc_path)
    root = tree.getroot()
    role_by_index = {int(item['index']): item.get('role') for item in role_map}
    stats = {
        'cleared': 0,
        'applied': 0,
        'skipped_complex_runs': 0,
        'reference_citations_preserved': 0,
        'reference_citation_rule_missing': not superscript_category_enabled(superscript_map, 'reference_citation'),
    }
    visible_index = 0
    for p in iter_body_paragraphs(root):
        text = get_text(p).strip()
        if not text:
            continue
        if starts_english_front_matter_block(text) or is_template_marker(text):
            continue
        role = role_by_index.get(visible_index, 'body')
        if role in ('author', 'english_author', 'affiliation', 'english_affiliation'):
            stats['cleared'] += clear_paragraph_superscript(p)
        role_patterns = superscript_patterns_for_role(superscript_map, role)
        body_citation_re = reference_citation_regex_from_map(superscript_map) if role == 'body' else None
        if role == 'body' and body_citation_re is None:
            stats['reference_citations_preserved'] += count_reference_citation_like_text(text)
        if role_patterns or body_citation_re is not None:
            applied, skipped = apply_superscript_patterns_to_paragraph(
                p, role_patterns, marker_re=body_citation_re
            )
            stats['applied'] += applied
            stats['skipped_complex_runs'] += skipped
        visible_index += 1
    write_xml(tree, doc_path)
    print(f"  Applied run-level superscript: {stats}")
    return stats


def apply_equation_layout_map_to_document(target_dir, equation_layout_map):
    stats = {
        'equation_paragraphs': 0,
        'inline_equation_paragraphs': 0,
        'applied': 0,
        'fallback_applied': 0,
        'skipped_no_template_layout': 0,
        'by_kind': {},
        'computed_fallback_by_width': {},
    }
    doc_path = os.path.join(target_dir, 'word', 'document.xml')
    tree = ET.parse(doc_path)
    root = tree.getroot()
    numbered_layout = (equation_layout_map or {}).get('numbered_equation')
    unnumbered_layout = (equation_layout_map or {}).get('unnumbered_equation')
    sect_infos = [sectPr_to_info(sectPr) for sectPr in root.iter(w('sectPr'))]
    fallback_layout_cache = {}
    if not equation_layout_map or not equation_layout_map.get('enabled'):
        print("  Equation layout map empty; using computed section/column fallback for numbered display equations")
    body = root.find(w('body'))
    section_index = 0
    current_info = sect_infos[section_index] if sect_infos else {}
    if body is not None:
        for child in body:
            paragraph_nodes = []
            if child.tag == w('p'):
                paragraph_nodes.append(child)
            elif child.tag == w('tbl'):
                paragraph_nodes.extend(child.iter(w('p')))
            for p in paragraph_nodes:
                equation_kinds = paragraph_equation_kinds(p)
                if not equation_kinds:
                    continue
                if not paragraph_is_display_equation(p):
                    stats['inline_equation_paragraphs'] += 1
                    continue
                stats['equation_paragraphs'] += 1
                for kind in equation_kinds:
                    stats['by_kind'][kind] = stats['by_kind'].get(kind, 0) + 1
                has_number = equation_number_text(get_text(p)) is not None
                used_fallback = False
                if has_number:
                    if layout_has_numbered_tab_evidence(numbered_layout):
                        layout = numbered_layout
                    else:
                        width_key = str(section_text_width_twips(current_info) or '')
                        layout = fallback_layout_cache.get(width_key)
                        if layout is None:
                            layout = computed_numbered_equation_layout_for_section(current_info)
                            fallback_layout_cache[width_key] = layout
                        used_fallback = True
                else:
                    layout = unnumbered_layout or numbered_layout
                if not layout:
                    stats['skipped_no_template_layout'] += 1
                    continue
                preserve_number_separator = False
                if apply_equation_layout_to_paragraph(p, layout, preserve_number_separator=preserve_number_separator):
                    stats['applied'] += 1
                    if used_fallback:
                        stats['fallback_applied'] += 1
                        width = layout.get('text_width_twips')
                        if width:
                            record = stats['computed_fallback_by_width'].setdefault(width, {
                                'count': 0,
                                'tab_stops': layout.get('tab_stops'),
                                'source': layout.get('source'),
                                'column_count': layout.get('column_count'),
                            })
                            record['count'] += 1
            if child.tag == w('p'):
                pPr = get_direct_child(child, w('pPr'))
                if get_direct_child(pPr, w('sectPr')) is not None:
                    section_index += 1
                    if section_index < len(sect_infos):
                        current_info = sect_infos[section_index]
    if fallback_layout_cache:
        stats['computed_fallback'] = [
            {
                'text_width_twips': layout.get('text_width_twips'),
                'column_count': layout.get('column_count'),
                'tab_stops': layout.get('tab_stops'),
                'source': layout.get('source'),
            }
            for layout in fallback_layout_cache.values()
            if layout
        ]
    write_xml(tree, doc_path)
    print(f"  Applied equation tab layout: {stats}")
    return stats


def layout_has_numbered_tab_evidence(layout):
    if not layout:
        return False
    profile = layout.get('profile') or {}
    return bool(
        layout.get('tabs_xml') or
        profile.get('tabs_before_equation') or
        profile.get('tabs_between_equation_and_number') or
        profile.get('tabs_after_number') or
        layout.get('tab_stops')
    )


def computed_numbered_equation_layout_for_section(sect_info):
    text_width = section_text_width_twips(sect_info or {})
    if not text_width:
        return None
    center_pos = max(1, int(round(text_width / 2.0)))
    right_pos = max(center_pos + 1, int(text_width))
    tabs = ET.Element(w('tabs'))
    center = ET.SubElement(tabs, w('tab'))
    center.set(w('val'), 'center')
    center.set(w('pos'), str(center_pos))
    right = ET.SubElement(tabs, w('tab'))
    right.set(w('val'), 'right')
    right.set(w('pos'), str(right_pos))
    return {
        'paragraph_index': None,
        'has_number': True,
        'number_text': None,
        'equation_kinds': [],
        'tabs_xml': xml_string(tabs),
        'tab_stops': [
            {'val': 'center', 'pos': str(center_pos)},
            {'val': 'right', 'pos': str(right_pos)},
        ],
        'profile': {
            'tokens': ['tab', 'equation', 'tab', 'number'],
            'equation_index': 1,
            'number_index': 3,
            'tabs_before_equation': 1,
            'tabs_between_equation_and_number': 1,
            'tabs_after_number': 0,
        },
        'paragraph_alignment': 'left',
        'source': 'computed_section_column_width_fallback',
        'text_width_twips': str(text_width),
        'column_count': section_col_count(sect_info or {}),
    }


def section_text_width_twips(sect_info):
    pg_sz = (sect_info or {}).get('pgSz') or {}
    pg_mar = (sect_info or {}).get('pgMar') or {}
    try:
        page_width = int(pg_sz.get('w') or 12240)
        left = int(pg_mar.get('left') or 1440)
        right = int(pg_mar.get('right') or 1440)
        gutter = int(pg_mar.get('gutter') or 0)
    except (TypeError, ValueError):
        return None
    text_width = page_width - left - right - gutter
    cols = (sect_info or {}).get('cols') or {}
    try:
        col_count = int(cols.get('num') or 1)
        col_space = int(cols.get('space') or 720)
    except (TypeError, ValueError):
        col_count = 1
        col_space = 720
    if col_count > 1:
        text_width = int((text_width - ((col_count - 1) * col_space)) / col_count)
    return max(text_width, 1440)


def section_page_text_width_twips(sect_info):
    pg_sz = (sect_info or {}).get('pgSz') or {}
    pg_mar = (sect_info or {}).get('pgMar') or {}
    try:
        page_width = int(pg_sz.get('w') or 12240)
        left = int(pg_mar.get('left') or 1440)
        right = int(pg_mar.get('right') or 1440)
        gutter = int(pg_mar.get('gutter') or 0)
    except (TypeError, ValueError):
        return 9360
    return max(page_width - left - right - gutter, 1440)


EMU_PER_TWIP = 635
MIN_AUTO_FIT_OBJECT_EMU = 457200  # 0.5 inch; leave small icons/logos alone.


def twips_to_emu(value):
    return int(round(value * EMU_PER_TWIP))


def int_attr(elem, attr):
    if elem is None:
        return None
    value = elem.get(attr)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def active_column_width_twips(sect_info):
    if section_col_count(sect_info) <= 1:
        return None
    width = section_text_width_twips(sect_info)
    return max(1440, int(width * 0.98)) if width else None


def scale_drawing_extents_to_width(drawing, max_width_emu, stats):
    changed = 0
    for frame in drawing:
        if local_name(frame.tag) not in ('inline', 'anchor'):
            continue
        extent = child_by_local_name(frame, 'extent')
        old_cx = int_attr(extent, 'cx')
        old_cy = int_attr(extent, 'cy')
        if not old_cx or old_cx <= max_width_emu or old_cx < MIN_AUTO_FIT_OBJECT_EMU:
            continue
        ratio = max_width_emu / float(old_cx)
        new_cx = int(max_width_emu)
        new_cy = int(round(old_cy * ratio)) if old_cy else old_cy
        extent.set('cx', str(new_cx))
        if new_cy:
            extent.set('cy', str(new_cy))
        for ext in frame.iter():
            if local_name(ext.tag) != 'ext':
                continue
            ext_cx = int_attr(ext, 'cx')
            ext_cy = int_attr(ext, 'cy')
            if not ext_cx:
                continue
            if ext_cx == old_cx or ext_cx > max_width_emu:
                ext.set('cx', str(new_cx))
                if ext_cy:
                    ext.set('cy', str(int(round(ext_cy * ratio))))
        stats['drawings_scaled'] = stats.get('drawings_scaled', 0) + 1
        stats['max_original_width_emu'] = max(stats.get('max_original_width_emu', 0), old_cx)
        changed += 1
    return changed


def fit_table_width_to_column(tbl, max_width_twips, stats):
    changed = 0
    tblPr = get_or_add_child(tbl, w('tblPr'), first=True)
    tblW = child_by_local_name(tblPr, 'tblW')
    if tblW is None:
        tblW = ET.Element(w('tblW'))
        tblPr.insert(0, tblW)
    width_type = tblW.get(w('type'))
    width_value = int_attr(tblW, w('w'))

    tblGrid = child_by_local_name(tbl, 'tblGrid')
    grid_cols = []
    if tblGrid is not None:
        for grid_col in tblGrid:
            if local_name(grid_col.tag) == 'gridCol':
                grid_cols.append(grid_col)
    grid_widths = [int_attr(col, w('w')) for col in grid_cols]
    explicit_grid_sum = sum(width for width in grid_widths if width)

    needs_fit = False
    if width_type == 'dxa' and width_value and width_value > max_width_twips:
        needs_fit = True
    if width_type == 'pct' and width_value and width_value > 5000:
        needs_fit = True
    if explicit_grid_sum and explicit_grid_sum > max_width_twips:
        needs_fit = True
    if not needs_fit:
        return changed

    tblW.set(w('type'), 'dxa')
    tblW.set(w('w'), str(max_width_twips))
    changed += 1

    if explicit_grid_sum and grid_cols:
        ratio = max_width_twips / float(explicit_grid_sum)
        for col in grid_cols:
            width = int_attr(col, w('w'))
            if width:
                col.set(w('w'), str(max(1, int(round(width * ratio)))))
        changed += 1

    for tr in tbl.findall(w('tr')):
        cells = direct_row_cells(tr)
        widths = []
        for tc in cells:
            tcPr = get_direct_child(tc, w('tcPr'))
            tcW = child_by_local_name(tcPr, 'tcW')
            if tcW is not None and tcW.get(w('type')) == 'dxa':
                widths.append((tcW, int_attr(tcW, w('w'))))
        total = sum(width for _, width in widths if width)
        if total and total > max_width_twips:
            ratio = max_width_twips / float(total)
            for tcW, width in widths:
                if width:
                    tcW.set(w('w'), str(max(1, int(round(width * ratio)))))
            changed += 1

    stats['tables_fitted'] = stats.get('tables_fitted', 0) + 1
    stats['max_original_table_width_twips'] = max(
        stats.get('max_original_table_width_twips', 0),
        explicit_grid_sum or width_value or 0,
    )
    return changed


def fit_wide_objects_to_columns(target_dir):
    """Constrain wide drawings/tables to the active column width in multicol sections."""
    doc_path = os.path.join(target_dir, 'word', 'document.xml')
    tree = ET.parse(doc_path)
    root = tree.getroot()
    body = root.find(w('body'))
    if body is None:
        return {'enabled': False, 'reason': 'target_has_no_body'}

    sectPrs = list(root.iter(w('sectPr')))
    sect_infos = [sectPr_to_info(sectPr) for sectPr in sectPrs]
    if not any(section_col_count(info) > 1 for info in sect_infos):
        return {'enabled': False, 'reason': 'no_multicolumn_sections'}

    stats = {
        'enabled': True,
        'multicolumn_sections': sum(1 for info in sect_infos if section_col_count(info) > 1),
        'drawings_scaled': 0,
        'tables_fitted': 0,
        'paragraphs_checked': 0,
        'tables_checked': 0,
    }
    changed = 0
    section_index = 0
    current_info = sect_infos[section_index] if sect_infos else {}

    for child in list(body):
        max_width_twips = active_column_width_twips(current_info)
        if max_width_twips:
            max_width_emu = twips_to_emu(max_width_twips)
            if child.tag == w('p'):
                stats['paragraphs_checked'] += 1
                for drawing in child.iter(w('drawing')):
                    changed += scale_drawing_extents_to_width(drawing, max_width_emu, stats)
            elif child.tag == w('tbl'):
                stats['tables_checked'] += 1
                changed += fit_table_width_to_column(child, max_width_twips, stats)

        if child.tag == w('p'):
            pPr = get_direct_child(child, w('pPr'))
            if get_direct_child(pPr, w('sectPr')) is not None:
                section_index += 1
                if section_index < len(sect_infos):
                    current_info = sect_infos[section_index]

    stats['changed'] = changed
    if changed:
        write_xml(tree, doc_path)
        print(f"  Fitted wide objects to multicolumn column width: {stats}")
    else:
        print("  Column object fit: no oversized drawings/tables found in multicolumn sections")
    return stats


def load_paragraph_style_spacing_map(doc_dir):
    """Return styleId -> direct paragraph spacing attrs from styles.xml."""
    styles_path = os.path.join(doc_dir, 'word', 'styles.xml')
    if not os.path.exists(styles_path):
        return {}
    try:
        tree = ET.parse(styles_path)
    except ET.ParseError:
        return {}
    root = tree.getroot()
    result = {}
    for style in root.findall(w('style')):
        if style.get(w('type')) != 'paragraph':
            continue
        style_id = style.get(w('styleId'))
        if not style_id:
            continue
        pPr = get_direct_child(style, w('pPr'))
        spacing = child_by_local_name(pPr, 'spacing')
        if spacing is not None:
            result[style_id] = attrs_without_ns(spacing)
    return result


def paragraph_high_inline_content_kinds(p):
    """Detect content that can be clipped by exact/fixed paragraph line spacing."""
    kinds = set()
    for node in p.iter():
        lname = local_name(node.tag)
        if lname in ('drawing', 'pict'):
            kinds.add(lname)
        elif lname in ('object', 'OLEObject', 'objectEmbed', 'control'):
            kinds.add('ole_object')
        elif lname in ('oMath', 'oMathPara'):
            kinds.add('omml')
        elif node.tag.startswith(f'{{{M_NS}}}'):
            kinds.add('omml')
    return sorted(kinds)


def effective_paragraph_spacing_attrs(p, style_spacing_map):
    pPr = get_direct_child(p, w('pPr'))
    direct_spacing = child_by_local_name(pPr, 'spacing')
    if direct_spacing is not None:
        return attrs_without_ns(direct_spacing), 'direct'
    style_id = paragraph_style_id(p)
    if style_id and style_spacing_map.get(style_id):
        return dict(style_spacing_map[style_id]), f'style:{style_id}'
    return {}, None


def spacing_is_exact_fixed(spacing_attrs):
    if not spacing_attrs:
        return False
    rule = (spacing_attrs.get('lineRule') or '').lower()
    return rule == 'exact'


def set_high_inline_safe_line_spacing(p, current_spacing):
    """Override only the line rule so high inline objects can expand vertically."""
    pPr = get_or_add_child(p, w('pPr'), first=True)
    spacing = child_by_local_name(pPr, 'spacing')
    if spacing is None:
        spacing = ET.Element(w('spacing'))
        pPr.append(spacing)
    for key in ('before', 'after', 'beforeLines', 'afterLines', 'line'):
        value = current_spacing.get(key)
        if value not in (None, '') and spacing.get(w(key)) is None:
            spacing.set(w(key), value)
    if spacing.get(w('line')) is None:
        spacing.set(w('line'), current_spacing.get('line') or '360')
    spacing.set(w('lineRule'), 'auto')


def protect_high_inline_content_line_spacing(target_dir):
    """Relax exact line spacing only on paragraphs with images/OLE/OMML content.

    Body styles can legitimately use fixed/exact line spacing for normal text,
    but Word clips tall inline drawings, MathType/OLE objects, and display math
    when those paragraphs inherit exact line height. This pass runs after all
    style/conformance cleanup so its direct paragraph override is intentional.
    """
    doc_path = os.path.join(target_dir, 'word', 'document.xml')
    stats = {
        'enabled': True,
        'paragraphs_checked': 0,
        'high_inline_paragraphs': 0,
        'paragraphs_changed': 0,
        'content_kind_counts': {},
        'examples': [],
    }
    if not os.path.exists(doc_path):
        stats['enabled'] = False
        stats['reason'] = 'document_xml_missing'
        return stats
    tree = ET.parse(doc_path)
    root = tree.getroot()
    style_spacing_map = load_paragraph_style_spacing_map(target_dir)
    changed = False
    for idx, p in enumerate(root.iter(w('p')), start=1):
        stats['paragraphs_checked'] += 1
        kinds = paragraph_high_inline_content_kinds(p)
        if not kinds:
            continue
        stats['high_inline_paragraphs'] += 1
        for kind in kinds:
            stats['content_kind_counts'][kind] = stats['content_kind_counts'].get(kind, 0) + 1
        spacing_attrs, source = effective_paragraph_spacing_attrs(p, style_spacing_map)
        if not spacing_is_exact_fixed(spacing_attrs):
            continue
        set_high_inline_safe_line_spacing(p, spacing_attrs)
        stats['paragraphs_changed'] += 1
        changed = True
        if len(stats['examples']) < 12:
            stats['examples'].append({
                'paragraph_index': idx,
                'style_id': paragraph_style_id(p),
                'spacing_source': source,
                'old_spacing': spacing_attrs,
                'new_lineRule': 'auto',
                'content_kinds': kinds,
                'text': get_text(p).strip()[:120],
            })
    if changed:
        write_xml(tree, doc_path)
        print(f"  Protected high inline content from exact line spacing: {stats}")
    else:
        print("  High inline content line spacing guard: no exact-spacing risks found")
    return stats


def apply_equation_layout_to_paragraph(p, layout, preserve_number_separator=False):
    changed = False
    tabs_xml = layout.get('tabs_xml')
    if tabs_xml:
        try:
            tabs = ET.fromstring(tabs_xml)
            pPr = get_or_add_child(p, w('pPr'), first=True)
            remove_children_by_local_name(pPr, {'tabs'})
            pPr.append(tabs)
            changed = True
        except ET.ParseError:
            pass
    else:
        # Template formulas may be centered by paragraph style/alignment rather
        # than tab stops. In that case remove stale target tab stops.
        pPr = get_direct_child(p, w('pPr'))
        if remove_children_by_local_name(pPr, {'tabs'}):
            changed = True
    alignment = layout.get('paragraph_alignment')
    if alignment:
        pPr = get_or_add_child(p, w('pPr'), first=True)
        remove_children_by_local_name(pPr, {'jc'})
        jc = ET.Element(w('jc'))
        jc.set(w('val'), alignment)
        pPr.append(jc)
        changed = True
    profile = layout.get('profile') or {}
    desired_between = int(profile.get('tabs_between_equation_and_number') or 0)
    desired_before = int(profile.get('tabs_before_equation') or 0)
    changed = sync_tabs_before_first_equation(p, desired_before) or changed
    if equation_number_text(get_text(p)) and not preserve_number_separator:
        changed = sync_tabs_between_equation_and_number(p, desired_between) or changed
    return changed


def make_tab_run():
    run = ET.Element(w('r'))
    ET.SubElement(run, w('tab'))
    return run


def direct_paragraph_children(p):
    return list(p)


def is_pure_tab_run(child):
    if child.tag != w('r'):
        return False
    ignorable = {'rPr', 'lastRenderedPageBreak'}
    meaningful = [node for node in child if local_name(node.tag) not in ignorable]
    return bool(meaningful) and all(local_name(node.tag) == 'tab' for node in meaningful)


def run_child_is_equation_anchor(node, allow_graphic=False):
    lname = local_name(node.tag)
    if lname in ('oMath', 'oMathPara', 'object', 'OLEObject', 'objectEmbed', 'control'):
        return True
    if lname in ('drawing', 'pict'):
        return paragraph_has_embedded_object(node) or allow_graphic
    if should_sniff_equation_attributes(node):
        for key, value in node.attrib.items():
            haystack = f'{key} {value}'
            if re.search(r'(Equation|MathType|MTExtra|DSMT|oleObject)', haystack, re.I):
                return True
    return False


def equation_anchor_child_index_in_run(run, allow_graphic=False):
    for idx, node in enumerate(list(run)):
        if run_child_is_equation_anchor(node, allow_graphic=allow_graphic):
            return idx
        if child_contains_equation(node, allow_graphic=allow_graphic):
            return idx
    return None


def number_child_index_in_run(run):
    for idx, node in enumerate(list(run)):
        if local_name(node.tag) == 't' and equation_number_text(node.text or ''):
            return idx
    return None


def tab_child_indexes(run, start=0, end=None):
    children = list(run)
    if end is None:
        end = len(children)
    return [
        idx for idx in range(max(0, start), min(end, len(children)))
        if local_name(children[idx].tag) == 'tab'
    ]


def remove_run_tab_children(run, indexes):
    changed = False
    for idx in sorted(indexes, reverse=True):
        children = list(run)
        if 0 <= idx < len(children) and local_name(children[idx].tag) == 'tab':
            run.remove(children[idx])
            changed = True
    return changed


def insert_tab_child(run, index):
    run.insert(index, ET.Element(w('tab')))


def child_contains_equation(child, allow_graphic=False):
    for node in child.iter():
        lname = local_name(node.tag)
        if lname in ('oMath', 'oMathPara', 'object', 'OLEObject', 'objectEmbed', 'control'):
            return True
        if lname in ('drawing', 'pict'):
            if paragraph_has_embedded_object(node) or allow_graphic:
                return True
        if should_sniff_equation_attributes(node):
            for key, value in node.attrib.items():
                haystack = f'{key} {value}'
                if re.search(r'(Equation|MathType|MTExtra|DSMT|oleObject)', haystack, re.I):
                    return True
    return False


def child_contains_equation_number(child):
    return equation_number_text(get_text(child)) is not None


def sync_tabs_before_first_equation(p, desired):
    children = direct_paragraph_children(p)
    allow_graphic = looks_like_numbered_graphic_equation_paragraph(p)
    eq_idx = next((i for i, child in enumerate(children) if child_contains_equation(child, allow_graphic=allow_graphic)), None)
    if eq_idx is None:
        return False
    eq_child = children[eq_idx]
    internal_tab_indexes = []
    if eq_child.tag == w('r'):
        anchor_idx = equation_anchor_child_index_in_run(eq_child, allow_graphic=allow_graphic)
        if anchor_idx is not None:
            internal_tab_indexes = tab_child_indexes(eq_child, end=anchor_idx)
    tab_indexes = []
    j = eq_idx - 1
    while j >= 0 and is_pure_tab_run(children[j]):
        tab_indexes.append(j)
        j -= 1
    tab_indexes = sorted(tab_indexes)
    changed = False
    while len(tab_indexes) + len(internal_tab_indexes) > desired:
        if tab_indexes:
            remove_idx = tab_indexes.pop(0)
            p.remove(children[remove_idx])
            children = direct_paragraph_children(p)
            eq_idx = next((i for i, child in enumerate(children) if child_contains_equation(child, allow_graphic=allow_graphic)), None)
            eq_child = children[eq_idx] if eq_idx is not None else None
            tab_indexes = [idx - 1 for idx in tab_indexes]
        elif eq_child is not None and internal_tab_indexes:
            remove_run_tab_children(eq_child, [internal_tab_indexes.pop()])
        changed = True
    while len(tab_indexes) + len(internal_tab_indexes) < desired:
        p.insert(eq_idx, make_tab_run())
        eq_idx += 1
        tab_indexes.append(eq_idx - 1)
        changed = True
    return changed


def sync_tabs_between_equation_and_number(p, desired):
    children = direct_paragraph_children(p)
    allow_graphic = looks_like_numbered_graphic_equation_paragraph(p)
    eq_idx = next((i for i, child in enumerate(children) if child_contains_equation(child, allow_graphic=allow_graphic)), None)
    num_idx = next((i for i, child in enumerate(children) if child_contains_equation_number(child)), None)
    if eq_idx is None or num_idx is None:
        return False
    if eq_idx == num_idx and children[eq_idx].tag == w('r'):
        run = children[eq_idx]
        anchor_idx = equation_anchor_child_index_in_run(run, allow_graphic=allow_graphic)
        number_idx = number_child_index_in_run(run)
        if anchor_idx is None or number_idx is None or number_idx <= anchor_idx:
            return False
        tab_indexes = tab_child_indexes(run, start=anchor_idx + 1, end=number_idx)
        changed = False
        while len(tab_indexes) > desired:
            remove_run_tab_children(run, [tab_indexes.pop()])
            tab_indexes = tab_child_indexes(run, start=anchor_idx + 1, end=number_child_index_in_run(run))
            changed = True
        while len(tab_indexes) < desired:
            number_idx = number_child_index_in_run(run)
            insert_tab_child(run, number_idx)
            tab_indexes.append(number_idx)
            changed = True
        return changed
    if num_idx <= eq_idx:
        return False
    tab_indexes = [
        idx for idx in range(eq_idx + 1, num_idx)
        if is_pure_tab_run(children[idx])
    ]
    changed = False
    while len(tab_indexes) > desired:
        remove_idx = tab_indexes.pop()
        p.remove(children[remove_idx])
        children = direct_paragraph_children(p)
        num_idx = next((i for i, child in enumerate(children) if child_contains_equation_number(child)), None)
        tab_indexes = [idx for idx in tab_indexes if idx < num_idx]
        changed = True
    while len(tab_indexes) < desired:
        p.insert(num_idx, make_tab_run())
        num_idx += 1
        tab_indexes.append(num_idx - 1)
        changed = True
    return changed


def superscript_patterns_for_role(superscript_map, role):
    patterns = superscript_map.get('patterns') or {}
    markers = []
    if role in ('author', 'english_author'):
        if superscript_category_enabled(superscript_map, 'author_affiliation'):
            markers.extend(patterns.get('author_markers') or [])
    elif role in ('affiliation', 'english_affiliation'):
        if superscript_category_enabled(superscript_map, 'author_affiliation'):
            markers.extend(patterns.get('affiliation_markers') or [])
    elif role == 'body':
        if superscript_category_enabled(superscript_map, 'reference_citation'):
            markers.extend(patterns.get('body_citation_markers') or [])
    return sorted(set(markers), key=len, reverse=True)


def reference_citation_regex_from_map(superscript_map):
    if not superscript_category_enabled(superscript_map, 'reference_citation'):
        return None
    markers = (superscript_map.get('patterns') or {}).get('body_citation_markers') or []
    parts = []
    if any(re.fullmatch(r'\[\d+(?:[-,，]\d+)*\]', marker) for marker in markers):
        parts.append(r'\[\d+(?:[-,，]\d+)*\]')
    if any(re.fullmatch(r'\(\d+(?:[-,，]\d+)*\)', marker) for marker in markers):
        parts.append(r'\(\d+(?:[-,，]\d+)*\)')
    if any(re.fullmatch(r'\^\d+(?:[-,，]\d+)*', marker) for marker in markers):
        parts.append(r'\^\d+(?:[-,，]\d+)*')
    if not parts:
        return None
    return re.compile('|'.join(parts))


def count_reference_citation_like_text(text):
    return len(re.findall(r'(?:\[\d+(?:[-,，]\d+)*\]|\(\d+(?:[-,，]\d+)*\))', text or ''))


def apply_superscript_patterns_to_paragraph(p, markers, marker_re=None):
    if not markers and marker_re is None:
        return 0, 0
    marker_re = marker_re or re.compile('|'.join(re.escape(marker) for marker in markers))
    applied = 0
    skipped = 0
    for run in list(p):
        if run.tag != w('r') or is_run_superscript(run):
            continue
        text = run_text(run)
        if not text or not marker_re.search(text):
            continue
        if not simple_text_run(run):
            skipped += 1
            continue
        pieces = split_text_by_marker(text, marker_re, markers)
        if len(pieces) <= 1:
            continue
        idx = list(p).index(run)
        p.remove(run)
        for offset, (piece_text, make_super) in enumerate(pieces):
            new_run = clone_element(run)
            set_run_text(new_run, piece_text)
            if make_super:
                set_run_superscript(new_run)
                applied += 1
            p.insert(idx + offset, new_run)
    return applied, skipped


def split_text_by_marker(text, marker_re, markers):
    pieces = []
    pos = 0
    for match in marker_re.finditer(text):
        start, end = match.span()
        marker = text[start:end]
        if not safe_superscript_marker_context(text, start, end, marker, markers):
            continue
        if start > pos:
            pieces.append((text[pos:start], False))
        pieces.append((text[start:end], True))
        pos = end
    if pos < len(text):
        pieces.append((text[pos:], False))
    return [(piece, flag) for piece, flag in pieces if piece]


def safe_superscript_marker_context(text, start, end, marker, markers):
    before = text[start - 1] if start > 0 else ''
    after = text[end] if end < len(text) else ''
    if marker.startswith('[') or marker.startswith('('):
        return True
    if re.fullmatch(r'[*†‡§]', marker):
        return bool(before and re.search(r'[A-Za-z\u4e00-\u9fff)]', before))
    if re.fullmatch(r'\d{1,2}', marker):
        if before and re.search(r'[A-Za-z\u4e00-\u9fff)]', before):
            if not after or re.search(r'[\s,，;；、)]', after):
                return True
        return False
    return marker in markers


def build_style_id_index(styles_root):
    return {
        style.get(w('styleId')): style
        for style in styles_root.findall(w('style'))
        if style.get(w('styleId'))
    }


def get_doc_defaults(styles_root):
    defaults = styles_root.find(w('docDefaults'))
    pPr = None
    rPr = None
    if defaults is not None:
        pPr_default = get_direct_child(defaults, w('pPrDefault'))
        rPr_default = get_direct_child(defaults, w('rPrDefault'))
        pPr = get_direct_child(pPr_default, w('pPr'))
        rPr = get_direct_child(rPr_default, w('rPr'))
    return pPr, rPr


def style_exists(template_by_id, style_id):
    return style_id if style_id in template_by_id else None


def find_canonical_style_id(role, template_by_id):
    for style_id in CANONICAL_STYLE_CANDIDATES.get(role, []):
        if style_id in template_by_id:
            return style_id
    for style_id in sorted(template_by_id):
        if role_from_template_pstyle(style_id, styles_by_id=template_by_id) == role:
            return style_id
    return None


def find_used_canonical_style_id(role, template_by_id, style_paragraph_sources):
    for style_id in CANONICAL_STYLE_CANDIDATES.get(role, []):
        if style_id in template_by_id and style_id in style_paragraph_sources:
            return style_id
    for style_id in sorted(style_paragraph_sources):
        if style_id in template_by_id and role_from_template_pstyle(style_id, styles_by_id=template_by_id) == role:
            return style_id
    return None


def should_trust_unused_canonical_style(role, canonical_id):
    if not canonical_id:
        return False
    # Body-like styles are often shipped as unused sample styles while real
    # template body paragraphs use Normal + docDefaults/direct formatting.
    if role == 'body':
        return False
    if role == 'abstract' and canonical_id in ('Heading1', 'Heading2', 'Heading3'):
        return False
    return True


def style_display_name(style_elem):
    name_elem = get_direct_child(style_elem, w('name'))
    return name_elem.get(w('val')) if name_elem is not None else None


def clone_element(elem):
    return ET.fromstring(ET.tostring(elem, encoding='unicode'))


def xml_string(elem):
    return ET.tostring(elem, encoding='unicode') if elem is not None else ''


def xml_to_element(text):
    return ET.fromstring(text) if text else None


@lru_cache(maxsize=1)
def load_fallback_ooxml_spec():
    try:
        with open(FALLBACK_OOXML_SPEC_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def fallback_variant_key(language='en', columns=1):
    lang = 'zh' if language == 'zh' else 'en'
    col = 'double' if int(columns or 1) >= 2 else 'single'
    return f'{lang}_{col}'


def fallback_variant_from_context(language='en', columns=1):
    spec = load_fallback_ooxml_spec()
    variants = spec.get('variants') or {}
    key = fallback_variant_key(language, columns)
    return variants.get(key) or variants.get(f'{language}_single') or variants.get('en_single') or {}


def role_ooxml_fallback(role, language='en', columns=1):
    variant = fallback_variant_from_context(language=language, columns=columns)
    return ((variant.get('roles') or {}).get(role)) or {}


def fallback_ooxml_table_spec(language='en', columns=1):
    variant = fallback_variant_from_context(language=language, columns=columns)
    return ((variant.get('tables') or {}).get('three_line')) or {}


def fallback_ooxml_normal_spec(language='en', columns=1):
    variant = fallback_variant_from_context(language=language, columns=columns)
    return variant.get('normal') or {}


def fallback_ooxml_doc_defaults_spec(language='en', columns=1):
    variant = fallback_variant_from_context(language=language, columns=columns)
    return variant.get('docDefaults') or {}


def variant_body_ooxml_fallback(language='en', columns=1):
    return role_ooxml_fallback('body', language=language, columns=columns)


def fallback_section_infos(language='en', columns=1):
    variant = fallback_variant_from_context(language=language, columns=columns)
    section_xml = ((variant.get('sections') or {}).get('sectPr_xml')) or []
    infos = []
    for xml_text in section_xml:
        elem = xml_child_from_text(xml_text)
        if elem is None:
            continue
        infos.append(sectPr_to_info(elem))
    if infos and int(columns or 1) < 2:
        return [infos[-1]]
    return infos


def fallback_front_body_section_infos(language='en', columns=1):
    infos = fallback_section_infos(language=language, columns=columns)
    if int(columns or 1) < 2 or len(infos) < 2:
        return infos
    single = next((info for info in infos if section_col_count(info) <= 1), infos[0])
    body = next((info for info in reversed(infos) if section_col_count(info) >= 2), infos[-1])
    return [single, body]


def xml_child_from_text(xml_text):
    try:
        return ET.fromstring(xml_text) if xml_text else None
    except ET.ParseError:
        return None


def merge_ooxml_children_by_name(target, source_xml, skip_names=None, override_names=None):
    """Merge a full pPr/rPr/tblPr/tcPr XML fragment into a same-kind container."""
    if target is None:
        return []
    source = xml_child_from_text(source_xml)
    if source is None:
        return []
    skip_names = set(skip_names or [])
    override_names = set(override_names or [])
    applied = []
    for src_child in source:
        name = local_name(src_child.tag)
        if name in skip_names:
            continue
        existing = child_by_local_name(target, name)
        if existing is None or name in override_names:
            if existing is not None:
                target.remove(existing)
            target.append(clone_element(src_child))
            applied.append(name)
    return applied


def attrs_without_ns(elem):
    if elem is None:
        return {}
    return {local_name(k): v for k, v in elem.attrib.items()}


def child_attrs(parent, name):
    return attrs_without_ns(child_by_local_name(parent, name))


def bool_prop(parent, name):
    child = child_by_local_name(parent, name)
    if child is None:
        return None
    val = child.get(w('val'))
    if val is None:
        return True
    return val not in ('0', 'false', 'False', 'off')


def summarize_rpr(rPr):
    """Structured summary of Word font/character settings. rPr_xml remains source of truth."""
    if rPr is None:
        return {}
    return {
        'fonts': child_attrs(rPr, 'rFonts'),
        'size': child_attrs(rPr, 'sz').get('val'),
        'size_cs': child_attrs(rPr, 'szCs').get('val'),
        'bold': bool_prop(rPr, 'b'),
        'bold_cs': bool_prop(rPr, 'bCs'),
        'italic': bool_prop(rPr, 'i'),
        'italic_cs': bool_prop(rPr, 'iCs'),
        'color': child_attrs(rPr, 'color'),
        'highlight': child_attrs(rPr, 'highlight').get('val'),
        'underline': child_attrs(rPr, 'u'),
        'emphasis': child_attrs(rPr, 'em').get('val'),
        'strike': bool_prop(rPr, 'strike'),
        'double_strike': bool_prop(rPr, 'dstrike'),
        'small_caps': bool_prop(rPr, 'smallCaps'),
        'all_caps': bool_prop(rPr, 'caps'),
        'superscript_subscript': child_attrs(rPr, 'vertAlign').get('val'),
        'hidden': bool_prop(rPr, 'vanish'),
        'character_spacing': child_attrs(rPr, 'spacing'),
        'position': child_attrs(rPr, 'position').get('val'),
        'scale': child_attrs(rPr, 'w').get('val'),
        'kerning': child_attrs(rPr, 'kern').get('val'),
        'shading': child_attrs(rPr, 'shd'),
        'border': child_attrs(rPr, 'bdr'),
        'language': child_attrs(rPr, 'lang'),
        'raw_children': [local_name(child.tag) for child in rPr],
    }


def summarize_ppr(pPr):
    """Structured summary of Word paragraph settings. pPr_xml remains source of truth."""
    if pPr is None:
        return {}
    tabs = child_by_local_name(pPr, 'tabs')
    pBdr = child_by_local_name(pPr, 'pBdr')
    return {
        'style': child_attrs(pPr, 'pStyle').get('val'),
        'alignment': child_attrs(pPr, 'jc').get('val'),
        'outline_level': child_attrs(pPr, 'outlineLvl').get('val'),
        'bidi': bool_prop(pPr, 'bidi'),
        'text_direction': child_attrs(pPr, 'textDirection').get('val'),
        'indent': child_attrs(pPr, 'ind'),
        'spacing': child_attrs(pPr, 'spacing'),
        'contextual_spacing': bool_prop(pPr, 'contextualSpacing'),
        'mirror_indents': bool_prop(pPr, 'mirrorIndents'),
        'suppress_auto_hyphens': bool_prop(pPr, 'suppressAutoHyphens'),
        'keep_next': bool_prop(pPr, 'keepNext'),
        'keep_lines': bool_prop(pPr, 'keepLines'),
        'page_break_before': bool_prop(pPr, 'pageBreakBefore'),
        'widow_control': bool_prop(pPr, 'widowControl'),
        'suppress_line_numbers': bool_prop(pPr, 'suppressLineNumbers'),
        'tabs': [attrs_without_ns(tab) for tab in tabs] if tabs is not None else [],
        'numbering': {
            'numId': child_attrs(child_by_local_name(pPr, 'numPr'), 'numId').get('val'),
            'ilvl': child_attrs(child_by_local_name(pPr, 'numPr'), 'ilvl').get('val'),
        } if child_by_local_name(pPr, 'numPr') is not None else {},
        'paragraph_borders': {
            local_name(child.tag): attrs_without_ns(child)
            for child in pBdr
        } if pBdr is not None else {},
        'shading': child_attrs(pPr, 'shd'),
        'frame': child_attrs(pPr, 'framePr'),
        'text_alignment': child_attrs(pPr, 'textAlignment').get('val'),
        'snap_to_grid': bool_prop(pPr, 'snapToGrid'),
        'nested_run_properties': summarize_rpr(child_by_local_name(pPr, 'rPr')),
        'raw_children': [local_name(child.tag) for child in pPr],
    }


def summarize_border_container(container):
    if container is None:
        return {}
    return {
        local_name(child.tag): attrs_without_ns(child)
        for child in container
    }


def summarize_table_pr(tblPr):
    if tblPr is None:
        return {}
    return {
        'style': child_attrs(tblPr, 'tblStyle').get('val'),
        'width': child_attrs(tblPr, 'tblW'),
        'alignment': child_attrs(tblPr, 'jc').get('val'),
        'indent': child_attrs(tblPr, 'tblInd'),
        'cell_spacing': child_attrs(tblPr, 'tblCellSpacing'),
        'layout': child_attrs(tblPr, 'tblLayout'),
        'look': child_attrs(tblPr, 'tblLook'),
        'shading': child_attrs(tblPr, 'shd'),
        'cell_margins': {
            local_name(child.tag): attrs_without_ns(child)
            for child in (child_by_local_name(tblPr, 'tblCellMar') or [])
        },
        'borders': summarize_border_container(child_by_local_name(tblPr, 'tblBorders')),
        'raw_children': [local_name(child.tag) for child in tblPr],
    }


def summarize_row_pr(trPr):
    if trPr is None:
        return {}
    return {
        'is_header': child_by_local_name(trPr, 'tblHeader') is not None,
        'cant_split': child_by_local_name(trPr, 'cantSplit') is not None,
        'height': child_attrs(trPr, 'trHeight'),
        'alignment': child_attrs(trPr, 'jc').get('val'),
        'cell_spacing': child_attrs(trPr, 'tblCellSpacing'),
        'raw_children': [local_name(child.tag) for child in trPr],
    }


def summarize_cell_pr(tcPr):
    if tcPr is None:
        return {}
    return {
        'width': child_attrs(tcPr, 'tcW'),
        'grid_span': child_attrs(tcPr, 'gridSpan').get('val'),
        'v_merge': child_attrs(tcPr, 'vMerge').get('val'),
        'h_merge': child_attrs(tcPr, 'hMerge').get('val'),
        'vertical_alignment': child_attrs(tcPr, 'vAlign').get('val'),
        'text_direction': child_attrs(tcPr, 'textDirection').get('val'),
        'shading': child_attrs(tcPr, 'shd'),
        'margins': {
            local_name(child.tag): attrs_without_ns(child)
            for child in (child_by_local_name(tcPr, 'tcMar') or [])
        },
        'borders': summarize_border_container(child_by_local_name(tcPr, 'tcBorders')),
        'raw_children': [local_name(child.tag) for child in tcPr],
    }


def child_by_local_name(parent, name):
    if parent is None:
        return None
    for child in parent:
        if local_name(child.tag) == name:
            return child
    return None


def based_on_id(style_elem):
    based = child_by_local_name(style_elem, 'basedOn')
    return based.get(w('val')) if based is not None else None


def style_chain(style_elem, styles_by_id):
    """Return inherited styles from base to leaf."""
    chain = []
    seen = set()
    current = style_elem
    while current is not None:
        sid = current.get(w('styleId'))
        if sid in seen:
            break
        seen.add(sid)
        chain.append(current)
        parent_id = based_on_id(current)
        current = styles_by_id.get(parent_id) if parent_id else None
    return list(reversed(chain))


def style_chain_ids(style_elem, styles_by_id):
    return [
        item.get(w('styleId'))
        for item in style_chain(style_elem, styles_by_id)
        if item.get(w('styleId'))
    ]


def merge_property_container(base, override, skip_names=None):
    """Merge pPr/rPr children by local-name, preserving existing full style props."""
    skip_names = skip_names or set()
    if override is None:
        return base
    if base is None:
        base = ET.Element(override.tag)
    for child in override:
        name = local_name(child.tag)
        if name in skip_names:
            continue
        existing = child_by_local_name(base, name)
        if existing is not None:
            base.remove(existing)
        base.append(clone_element(child))
    return base


def flatten_template_style(source_style, template_by_id, doc_defaults=None):
    """Copy a template style and materialize basedOn pPr/rPr into the style itself."""
    role_style = clone_element(source_style)
    pPr_effective = None
    rPr_effective = None
    if doc_defaults:
        default_pPr, default_rPr = doc_defaults
        pPr_effective = merge_property_container(
            pPr_effective, default_pPr, skip_names={'pStyle', 'sectPr'}
        )
        rPr_effective = merge_property_container(rPr_effective, default_rPr)
    for item in style_chain(source_style, template_by_id):
        pPr_effective = merge_property_container(
            pPr_effective, get_direct_child(item, w('pPr')), skip_names={'pStyle', 'sectPr'}
        )
        rPr_effective = merge_property_container(
            rPr_effective, get_direct_child(item, w('rPr'))
        )

    remove_children_by_local_name(role_style, {'pPr', 'rPr'})
    if pPr_effective is not None and (len(list(pPr_effective)) or pPr_effective.attrib):
        role_style.append(pPr_effective)
    if rPr_effective is not None and (len(list(rPr_effective)) or rPr_effective.attrib):
        role_style.append(rPr_effective)
    return role_style


def default_paragraph_style(template_root, template_by_id):
    for style in template_root.findall(w('style')):
        if style.get(w('type')) == 'paragraph' and style.get(w('default')) == '1':
            return style
    return template_by_id.get('Normal')


def flatten_default_paragraph_style(template_root, template_by_id, doc_defaults=None):
    default_style = default_paragraph_style(template_root, template_by_id)
    if default_style is None:
        return None
    return flatten_template_style(default_style, template_by_id, doc_defaults=doc_defaults)


def paragraph_format_from_source_is_trustworthy(role, source):
    if not source:
        return False
    sample = source.get('sample') or ''
    if not sample:
        return False
    if role != 'body':
        if looks_like_role_label_instruction_or_example(role, sample):
            return False
        if looks_like_explicit_format_or_operation_instruction(sample):
            return False
        if looks_like_template_instruction(sample) and not source_signature_has_meaningful_paragraph_format(source):
            return False
        return True
    if looks_like_explicit_format_or_operation_instruction(sample):
        return False
    if looks_like_body_placeholder_sample(sample):
        return True
    style_id = source.get('style_id')
    if len(sample) < 80 and looks_like_template_instruction(sample):
        return False
    if style_id in BODY_LIKE_STYLE_IDS and not looks_like_template_instruction(sample):
        return True
    return True


def looks_like_role_label_instruction_or_example(role, text):
    stripped = (text or '').strip()
    if not stripped:
        return False
    if role in ('abstract', 'keywords', 'english_abstract', 'english_keywords'):
        if abstract_keyword_label_role(stripped):
            return bool(re.search(
                r'(字数|范围|一般|包括|应该|应|关键词|关键字|词与词|分号|如[:：]|例如|sample|example|should|must)',
                stripped,
                re.I,
            ))
    return False


def source_signature_has_meaningful_paragraph_format(source):
    sig = (source or {}).get('signature') or {}
    ppr_xml = sig.get('pPr')
    if not ppr_xml:
        return False
    try:
        pPr = ET.fromstring(ppr_xml)
    except ET.ParseError:
        return False
    spacing = child_by_local_name(pPr, 'spacing')
    if spacing is not None:
        line = spacing.get(w('line'))
        before = spacing.get(w('before'))
        after = spacing.get(w('after'))
        if line not in (None, '', '0'):
            return True
        if before not in (None, '', '0') or after not in (None, '', '0'):
            return True
    ind = child_by_local_name(pPr, 'ind')
    if ind is not None:
        for key in ('firstLine', 'firstLineChars', 'hanging', 'left', 'start'):
            if ind.get(w(key)) not in (None, '', '0'):
                return True
    for name in ('jc', 'tabs', 'pBdr', 'shd', 'framePr', 'keepNext', 'keepLines', 'pageBreakBefore'):
        if child_by_local_name(pPr, name) is not None:
            return True
    return False


def strip_untrustworthy_paragraph_format(pPr):
    removed = {}
    if pPr is None:
        return removed
    for name in ('spacing', 'ind', 'jc', 'tabs', 'contextualSpacing', 'keepNext', 'keepLines', 'pageBreakBefore', 'widowControl'):
        child = child_by_local_name(pPr, name)
        if child is not None:
            removed[name] = attrs_without_ns(child)
            pPr.remove(child)
    return removed


def lock_existing_spacing_rule(style_elem, rule):
    pPr = get_direct_child(style_elem, w('pPr'))
    spacing = child_by_local_name(pPr, 'spacing')
    if spacing is None:
        return rule
    if spacing.get(w('line')) == '0':
        return rule
    locked = dict(rule or {})
    spacing_rule = dict(locked.get('spacing') or {})
    for key in ('before', 'after', 'line', 'lineRule', 'beforeLines', 'afterLines'):
        value = spacing.get(w(key))
        if value is not None:
            spacing_rule[key] = value
    if spacing_rule:
        locked['spacing'] = spacing_rule
    return locked


def build_role_style_element(role, source_style, template_by_id, source, text_rules=None,
                             doc_defaults=None, language='en', default_style_elem=None,
                             fallback_columns=1):
    text_rules = text_rules or {}
    style_id = ROLE_STYLE_IDS[role]
    source_type = normalize_format_source_type((source or {}).get('format_source_type') or (source or {}).get('source_type'))
    force_clean_shell = bool((source or {}).get('force_clean_shell')) or source_type in WEAK_EXTERNAL_STYLE_SOURCE_TYPES
    if force_clean_shell:
        role_style = clean_role_style_shell()
    elif source_style is not None:
        role_style = flatten_template_style(source_style, template_by_id, doc_defaults=doc_defaults)
    elif role == 'body' and (source or {}).get('style_id') is None and default_style_elem is not None:
        role_style = clone_element(default_style_elem)
    else:
        role_style = clean_role_style_shell()
        if doc_defaults and not text_rules.get(role):
            default_pPr, default_rPr = doc_defaults
            if default_pPr is not None and get_direct_child(role_style, w('pPr')) is None:
                role_style.append(clone_element(default_pPr))
            if default_rPr is not None and get_direct_child(role_style, w('rPr')) is None:
                role_style.append(clone_element(default_rPr))

    role_style.set(w('styleId'), style_id)
    role_style.set(w('type'), 'paragraph')
    strip_unstable_style_links(role_style)
    scrub_role_inherited_pollution(role_style, role)
    name_elem = get_direct_child(role_style, w('name'))
    if name_elem is None:
        name_elem = ET.Element(w('name'))
        role_style.insert(0, name_elem)
    name_elem.set(w('val'), ROLE_DISPLAY_NAMES[role])

    if source:
        sig = source.get('signature', {})
        if sig.get('pPr') and not force_clean_shell:
            pPr_src = ET.fromstring(sig['pPr'])
            remove_children_by_local_name(pPr_src, {'pStyle', 'sectPr'})
            if not paragraph_format_from_source_is_trustworthy(role, source):
                removed = strip_untrustworthy_paragraph_format(pPr_src)
                if removed:
                    source['untrusted_paragraph_format_removed'] = removed
            if len(list(pPr_src)) or pPr_src.attrib:
                pPr = get_or_add_child(role_style, w('pPr'))
                merge_property_container(pPr, pPr_src, skip_names={'pStyle', 'sectPr'})
        if sig.get('rPr') and not force_clean_shell:
            rPr = get_or_add_child(role_style, w('rPr'))
            merge_property_container(rPr, ET.fromstring(sig['rPr']))

    rule = text_rules.get(role)
    apply_rule_to_style(role_style, rule)
    scrub_role_inherited_pollution(role_style, role)
    if paragraph_format_from_source_is_trustworthy(role, source):
        rule = lock_existing_spacing_rule(role_style, rule)
    sanitized = sanitize_unspecified_visual_properties(
        role_style,
        role,
        rule,
        source_type=source_type,
        remove_emphasis=source_type in WEAK_EXTERNAL_STYLE_SOURCE_TYPES,
    )
    if source is not None and sanitized:
        source['unspecified_visual_properties_sanitized'] = sanitized
    fallback_applied = apply_granular_fallback_to_style(
        role_style, role, language, rule,
        source_type=source_type,
        columns=fallback_columns,
        source=source,
    )
    reference_indent_fix = ensure_reference_item_indent_guard(role_style, role)
    if reference_indent_fix:
        fallback_applied.setdefault('paragraph', {}).setdefault('indent_guard', reference_indent_fix)
    if not (rule or {}).get('fonts'):
        normalize_theme_font_conflicts_in_style(role_style)
    removed_hint_colors = scrub_template_hint_colors(role_style, role, source, locked_rule=rule)
    if source is not None and removed_hint_colors:
        source['template_hint_colors_removed'] = removed_hint_colors
    return role_style, fallback_applied


def clean_role_style_shell():
    style = ET.Element(w('style'))
    style.set(w('type'), 'paragraph')
    style.append(ET.Element(w('pPr')))
    style.append(ET.Element(w('rPr')))
    return style


def ensure_reference_item_indent_guard(style_elem, role, create_default=False):
    if role != 'reference_item':
        return {}
    pPr = get_or_add_child(style_elem, w('pPr'))
    if child_by_local_name(pPr, 'numPr') is not None:
        return {}
    ind = child_by_local_name(pPr, 'ind')
    if ind is None:
        if not create_default:
            return {}
        ind = ET.Element(w('ind'))
        ind.set(w('left'), REFERENCE_ITEM_DEFAULT_INDENT_TWIPS)
        ind.set(w('hanging'), REFERENCE_ITEM_DEFAULT_INDENT_TWIPS)
        pPr.append(ind)
        return {
            'created_default_visible_text_indent': {
                'left': REFERENCE_ITEM_DEFAULT_INDENT_TWIPS,
                'hanging': REFERENCE_ITEM_DEFAULT_INDENT_TWIPS,
            }
        }
    return ensure_hanging_indent_has_left(ind)


def ensure_hanging_indent_has_left(ind):
    hanging = ind.get(w('hanging'))
    if hanging in (None, '', '0'):
        return {}
    changed = {}
    left = ind.get(w('left'))
    if left in (None, ''):
        ind.set(w('left'), str(hanging))
        changed['left'] = str(hanging)
        return changed
    try:
        hanging_val = int(str(hanging))
        left_val = int(str(left))
    except (TypeError, ValueError):
        return changed
    if left_val < hanging_val:
        ind.set(w('left'), str(hanging_val))
        changed['left'] = str(hanging_val)
    return changed


TEMPLATE_HINT_COLOR_VALUES = {'FF0000', 'FF6600', '0000FF', '0070C0', '00B0F0'}
TEMPLATE_HINT_COLOR_ROLES = {
    'abstract', 'keywords', 'metadata', 'citation_format',
    'reference_item', 'body',
}
UNSPECIFIED_VISUAL_RPR_TAGS = {
    'color', 'u', 'highlight', 'shd', 'smallCaps', 'caps', 'strike',
    'dstrike', 'em', 'bdr', 'emboss', 'imprint', 'outline', 'shadow',
}
LOCAL_EMPHASIS_RPR_TAGS = {'b', 'bCs', 'i', 'iCs'}
UNSPECIFIED_VISUAL_PPR_TAGS = {'pBdr', 'shd', 'framePr'}


def source_text_has_template_hint_color_context(source):
    sample = (source or {}).get('sample') or ''
    return bool(re.search(
        r'(点击在线查询|分号隔开|引用格式|期刊引用格式|专著引用格式|学位论文引用格式|'
        r'专利引用格式|标准引用格式|网上电子公告引用格式|突出体现|一般应包括|'
        r'提示|示例|例：|WORD模板)',
        sample,
        re.I
    ))


def scrub_template_hint_colors(style_elem, role, source=None, locked_rule=None):
    """Remove template instruction/placeholder colors from authoritative style XML."""
    locked_rule = locked_rule or {}
    if locked_rule.get('color'):
        return []
    if role not in TEMPLATE_HINT_COLOR_ROLES and not source_text_has_template_hint_color_context(source):
        return []
    removed = []
    for rPr in (
        get_direct_child(style_elem, w('rPr')),
        get_direct_child(get_direct_child(style_elem, w('pPr')), w('rPr')),
    ):
        if rPr is None:
            continue
        for color in list(rPr):
            if local_name(color.tag) != 'color':
                continue
            val = (color.get(w('val')) or '').upper()
            if val in TEMPLATE_HINT_COLOR_VALUES or source_text_has_template_hint_color_context(source):
                removed.append({'role': role, 'val': val or None})
                rPr.remove(color)
    return removed


def sanitize_unspecified_visual_properties(style_elem, role, locked_rule=None, source_type=None, remove_emphasis=False):
    """Remove display-only residue not explicitly supplied by the evidence contract."""
    locked_rule = locked_rule or {}
    source_type = normalize_format_source_type(source_type)
    is_low_confidence_shell = source_type in LOW_CONFIDENCE_STYLE_SHELL_SOURCE_TYPES
    removed = []
    if not is_low_confidence_shell:
        return removed

    locked_rpr = set()
    if locked_rule.get('color'):
        locked_rpr.add('color')
    if 'underline' in locked_rule or 'u' in locked_rule:
        locked_rpr.add('u')
    if 'bold' in locked_rule:
        locked_rpr.update({'b', 'bCs'})
    if 'italic' in locked_rule or 'italic_inferred' in locked_rule:
        locked_rpr.update({'i', 'iCs'})

    for rPr in (
        get_direct_child(style_elem, w('rPr')),
        get_direct_child(get_direct_child(style_elem, w('pPr')), w('rPr')),
    ):
        if rPr is None:
            continue
        for child in list(rPr):
            name = local_name(child.tag)
            if name in UNSPECIFIED_VISUAL_RPR_TAGS and name not in locked_rpr:
                removed.append({'surface': 'rPr', 'tag': name})
                rPr.remove(child)
            elif remove_emphasis and name in LOCAL_EMPHASIS_RPR_TAGS and name not in locked_rpr:
                removed.append({'surface': 'rPr', 'tag': name})
                rPr.remove(child)

    pPr = get_direct_child(style_elem, w('pPr'))
    if pPr is not None:
        for child in list(pPr):
            name = local_name(child.tag)
            if name in UNSPECIFIED_VISUAL_PPR_TAGS:
                removed.append({'surface': 'pPr', 'tag': name})
                pPr.remove(child)
    return removed


def scrub_role_inherited_pollution(style_elem, role):
    pPr = get_direct_child(style_elem, w('pPr'))
    rPr = get_direct_child(style_elem, w('rPr'))
    pPr_rPr = get_direct_child(pPr, w('rPr'))
    if role in ('author', 'affiliation', 'english_author', 'english_affiliation'):
        remove_children_by_local_name(rPr, {'vertAlign'})
        remove_children_by_local_name(pPr_rPr, {'vertAlign'})
    if role not in ('title', 'heading1', 'heading2', 'heading3', 'references_heading'):
        remove_children_by_local_name(pPr, {'outlineLvl', 'keepNext', 'keepLines', 'pageBreakBefore'})
    if role in ('author', 'affiliation', 'english_author', 'english_affiliation', 'body'):
        normalize_false_bold(rPr)
        normalize_false_bold(pPr_rPr)


def normalize_false_bold(rPr):
    if rPr is None:
        return
    for name in ('b', 'bCs'):
        child = child_by_local_name(rPr, name)
        if child is not None and child.get(w('val')) in ('0', 'false', 'False', 'off'):
            rPr.remove(child)


def normalize_theme_font_conflicts_in_style(style_elem):
    for rPr in (
        get_direct_child(style_elem, w('rPr')),
        get_direct_child(get_direct_child(style_elem, w('pPr')), w('rPr')),
    ):
        normalize_theme_font_conflicts(rPr)


def normalize_theme_font_conflicts(rPr):
    rFonts = child_by_local_name(rPr, 'rFonts')
    if rFonts is None:
        return
    for theme, specific in (
        ('asciiTheme', 'ascii'),
        ('hAnsiTheme', 'hAnsi'),
        ('eastAsiaTheme', 'eastAsia'),
        ('cstheme', 'cs'),
    ):
        if rFonts.get(w(theme)) is not None and rFonts.get(w(specific)) is not None:
            del rFonts.attrib[w(specific)]


BODY_LIKE_STYLE_IDS = {'Para', 'BodyText', 'BodyTextIndent', 'Normal'}


def is_weak_front_matter_source(role, source):
    if role not in ROLE_EQUIVALENTS:
        return False
    if not source:
        return True
    style_id = source.get('style_id')
    if style_id in BODY_LIKE_STYLE_IDS:
        return True
    route = source.get('source_route')
    return route in ('fallback', 'unused_canonical_style_id') and style_id in (None, 'Normal')


def is_stronger_equivalent_source(source):
    if not source:
        return False
    style_id = source.get('style_id')
    return bool(style_id and style_id not in BODY_LIKE_STYLE_IDS)


def resolve_role_source(role, role_sources):
    if role in role_sources:
        exact = role_sources[role]
        if is_weak_front_matter_source(role, exact):
            for equivalent in ROLE_EQUIVALENTS.get(role, []):
                equivalent_source = role_sources.get(equivalent)
                if is_stronger_equivalent_source(equivalent_source):
                    return (
                        equivalent_source,
                        equivalent,
                        'cross_language_equivalent_over_weak_exact',
                    )
        return exact, role, 'exact'
    for equivalent in ROLE_EQUIVALENTS.get(role, []):
        if equivalent in role_sources:
            return role_sources[equivalent], equivalent, 'cross_language_equivalent'
    if 'body' in role_sources:
        return role_sources['body'], 'body', 'body_fallback'
    return None, None, 'missing'


def resolve_role_style_id(role, role_style_ids):
    if role in role_style_ids:
        return role, role_style_ids[role], 'exact'
    for equivalent in ROLE_EQUIVALENTS.get(role or '', []):
        if equivalent in role_style_ids:
            return equivalent, role_style_ids[equivalent], 'cross_language_equivalent'
    if 'body' in role_style_ids:
        return 'body', role_style_ids['body'], 'body_fallback'
    return None, None, 'missing'


def evidence_priority_for_source(source_type):
    normalized = normalize_format_source_type(source_type)
    return SOURCE_EVIDENCE_PRIORITIES.get(normalized) or SOURCE_EVIDENCE_PRIORITIES['docx_template']


def build_style_spec(template_dir, text_rules=None, source_metadata=None, target_dir=None):
    """Create an intermediate style spec independent of any target document."""
    text_rules = text_rules or {}
    source_metadata = dict(source_metadata or {})
    source_type = normalize_format_source_type(source_metadata.get('source_type') or source_metadata.get('format_source_type') or 'docx_template')
    template_styles_path = os.path.join(template_dir, 'word', 'styles.xml')
    template_tree = ET.parse(template_styles_path)
    template_root = template_tree.getroot()
    template_by_id = build_style_id_index(template_root)
    doc_defaults = get_doc_defaults(template_root)
    default_style_elem = flatten_default_paragraph_style(
        template_root, template_by_id, doc_defaults=doc_defaults
    )
    template_language = source_metadata.get('fallback_language') or choose_fallback_language(
        template_dir,
        text_rules=text_rules,
        source_type=source_type,
        target_dir=target_dir,
    )
    source_column_resolution = resolve_fallback_columns_for_source(
        template_dir,
        source_metadata,
        allow_docx_detection=(
            source_type in NON_DOCX_TEXT_ONLY_SOURCE_TYPES
            or source_type in LOW_CONFIDENCE_FORMAT_SOURCE_TYPES
        ),
    )
    website_explicit_columns = website_explicit_column_count(source_metadata) if is_website_format_source(source_type) else None
    if website_explicit_columns is not None:
        source_column_resolution = website_explicit_column_resolution(website_explicit_columns)
    if (
        is_website_format_source(source_type)
        and website_explicit_columns is None
        and source_metadata.get('body_cols') is None
        and source_metadata.get('body_columns') is None
        and not website_has_explicit_column_rule(source_metadata)
    ):
        source_column_resolution = website_default_single_column_resolution(
            source_column_resolution,
            prior_columns=source_column_resolution.get('columns'),
        )
    if source_type in NON_DOCX_TEXT_ONLY_SOURCE_TYPES:
        fallback_columns = source_column_resolution['columns']
    else:
        source_columns_hint = metadata_fallback_columns(source_metadata)
        if source_columns_hint is not None:
            fallback_columns = source_columns_hint
        else:
            fallback_columns = normalize_column_count(detect_fallback_columns(template_dir) if template_dir else 1)
    detected_sources = collect_role_source_styles(template_dir)
    style_paragraph_sources = collect_first_paragraph_by_style_id(template_dir)
    role_sources = {}
    for role in ROLE_STYLE_IDS:
        canonical_id = find_used_canonical_style_id(role, template_by_id, style_paragraph_sources)
        if canonical_id and not role_source_candidate_is_usable(
            role,
            (style_paragraph_sources.get(canonical_id) or {}).get('sample', ''),
            canonical_id,
        ):
            canonical_id = None
        if canonical_id:
            style_source = style_paragraph_sources.get(canonical_id, {})
            detected = detected_sources.get(role, {})
            role_sources[role] = {
                'style_id': canonical_id,
                'signature': style_source.get('signature') or detected.get('signature', {}),
                'sample': style_source.get('sample') or detected.get('sample', ''),
                'source_route': 'used_canonical_style_id',
            }
        elif role in detected_sources:
            role_sources[role] = dict(detected_sources[role])
            role_sources[role]['source_route'] = 'detected_paragraph'
        else:
            unused_canonical_id = find_canonical_style_id(role, template_by_id)
            if should_trust_unused_canonical_style(role, unused_canonical_id):
                role_sources[role] = {
                    'style_id': unused_canonical_id,
                    'signature': {},
                    'sample': '',
                    'source_route': 'unused_canonical_style_id',
                }

    # Abstract body should not inherit Heading1 just because the "Abstract"
    # label is a heading. If no dedicated abstract body style exists, use body.
    if role_sources.get('abstract', {}).get('style_id') in ('Heading1', 'Heading2', 'Heading3'):
        body_source = role_sources.get('body') or {}
        role_sources['abstract'] = {
            'style_id': body_source.get('style_id') or find_canonical_style_id('body', template_by_id),
            'signature': detected_sources.get('abstract', {}).get('signature', {}),
            'sample': detected_sources.get('abstract', {}).get('sample', ''),
            'source_route': 'abstract_body_from_body_style',
        }

    spec = {
        'version': STYLE_SPEC_VERSION,
        'priority': evidence_priority_for_source(source_type),
        '_meta': {
            'source_type': source_type,
            'fallback_language': template_language,
            'fallback_columns': fallback_columns,
            'fallback_column_resolution': source_column_resolution,
            'source_confidence': source_metadata.get('source_confidence') or (
                'lower' if source_type in LOW_CONFIDENCE_FORMAT_SOURCE_TYPES else 'normal'
            ),
            'evidence_priority': evidence_priority_for_source(source_type),
            'unified_evidence_route': True,
            'legacy_word_sources': source_metadata.get('legacy_word_sources') or [],
            'notes': source_metadata.get('notes') or [],
        },
        'roles': {},
    }

    for role, style_id in ROLE_STYLE_IDS.items():
        source, source_role, source_resolution = resolve_role_source(role, role_sources)
        source = dict(source or {})
        source['source_type'] = source_type
        source['format_source_type'] = source_type
        if source_type in WEAK_EXTERNAL_STYLE_SOURCE_TYPES:
            source['force_clean_shell'] = True
        source_style = template_by_id.get(source.get('style_id')) if source else None
        role_style, fallback_applied = build_role_style_element(
            role, source_style, template_by_id, source, text_rules,
            doc_defaults=doc_defaults, language=template_language,
            default_style_elem=default_style_elem,
            fallback_columns=fallback_columns,
        )
        pPr = get_direct_child(role_style, w('pPr'))
        rPr = get_direct_child(role_style, w('rPr'))
        spec['roles'][role] = {
            'style_id': style_id,
            'display_name': ROLE_DISPLAY_NAMES[role],
            'type': 'paragraph',
            'based_on': None,
            'next': style_id,
            'font': summarize_rpr(rPr),
            'paragraph': summarize_ppr(pPr),
            'pPr_xml': xml_string(pPr),
            'rPr_xml': xml_string(rPr),
            'style_xml': xml_string(role_style),
            'text_rule': text_rules.get(role, {}),
            'fallback_language': template_language,
            'fallback_columns': fallback_columns,
            'format_source_type': source_type,
            'granular_fallback_applied': fallback_applied,
            'source_sample': source.get('sample') if source else '',
            'source_style_id': source.get('style_id') if source else None,
            'source_style_chain': style_chain_ids(source_style, template_by_id) if source_style is not None else [],
            'source_style_name': style_display_name(source_style),
            'source_role': source_role,
            'source_resolution': source_resolution,
            'source_route': source.get('source_route') if source else 'fallback',
            'source_paragraph_format_trusted': paragraph_format_from_source_is_trustworthy(role, source),
            'untrusted_paragraph_format_removed': source.get('untrusted_paragraph_format_removed') if source else {},
            'template_hint_colors_removed': source.get('template_hint_colors_removed') if source else [],
            'unspecified_visual_properties_sanitized': source.get('unspecified_visual_properties_sanitized') if source else [],
            'coverage_note': 'style_xml is authoritative; structured fields are for audit/model routing.',
        }
    return spec


def write_style_spec(spec, path):
    if not path:
        return
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
    print(f"  Wrote style spec: {path}")


def build_format_report(style_spec=None, superscript_map=None, superscript_stats=None,
                        role_map=None, numbering_audit=None,
                        equation_layout_map=None, equation_layout_stats=None,
                        table_format_map=None, table_format_stats=None,
                        reference_numbering_map=None, reference_numbering_stats=None,
                        section_structure_stats=None, column_object_fit_stats=None,
                        high_inline_line_spacing_stats=None,
                        abstract_keyword_label_stats=None, metadata_layout_stats=None,
                        legacy_word_sources=None,
                        qa_report=None, format_conformance_stats=None,
                        header_footer_watermark_stats=None,
                        explicit_postprocess_stats=None):
    style_spec = style_spec or {}
    roles = style_spec.get('roles') or {}
    fallback_roles = []
    risk_items = []
    format_conformance_stats = format_conformance_stats or {}
    explicit_postprocess_stats = explicit_postprocess_stats or {}
    format_source = ((qa_report or {}).get('format_source') or {})
    if explicit_postprocess_stats.get('enabled'):
        risk_items.append({
            'type': 'explicit_postprocess_enabled',
            'role': 'document',
            'message': (
                'explicit content/structure postprocess operations were applied after style formatting; '
                'confirm moved objects, caption text, citation markers, and reference numbering in Word'
            ),
            'operations': explicit_postprocess_stats.get('operations') or [],
        })
        if not explicit_postprocess_stats.get('ok', True):
            risk_items.append({
                'type': 'explicit_postprocess_failed',
                'role': 'document',
                'message': 'explicit postprocess did not complete successfully',
                'error': explicit_postprocess_stats.get('error'),
            })
        if explicit_postprocess_stats.get('preservation_issues'):
            risk_items.append({
                'type': 'explicit_postprocess_preservation_issue',
                'role': 'document',
                'message': (
                    'explicit postprocess changed document preservation signatures; '
                    'check possible missing text, formulas, images, OLE objects, or tables before delivery'
                ),
                'issues': explicit_postprocess_stats.get('preservation_issues')[:12],
            })
    if format_source.get('non_docx_text_only_route') or format_source.get('non_docx_standard_fallback'):
        risk_items.append({
            'type': 'non_docx_standard_fallback',
            'role': 'document',
            'message': (
                'format source was not a native DOCX template, so it did not provide reliable Word style XML. '
                'Explicit extracted text rules were applied with higher priority than fallback for the properties they stated; '
                'only unstated or unsafe-default properties were completed with the standard fallback variant. '
                'For more accurate extraction, upload a DOCX template/source-format file or directly provide explicit formatting rules as text instructions.'
            ),
            'source_type': format_source.get('type'),
            'fallback_columns': format_source.get('fallback_columns'),
            'source_column_detection': format_source.get('source_column_detection'),
        })
    if format_source.get('website_unspecified_columns_default_single'):
        risk_items.append({
            'type': 'website_format_source_not_full_word_template',
            'role': 'document',
            'message': (
                'website formatting guidance was used as text rules, not as a full Word/OpenXML template. '
                'If the website does not explicitly provide Word font/size/spacing/page XML, the result follows '
                'the stated submission rules plus the standard single-column fallback rather than publisher print layout.'
            ),
            'source_type': format_source.get('type'),
            'fallback_columns': format_source.get('fallback_columns'),
        })
    spacing_normalization = format_source.get('spacing_value_normalization') or {}
    if spacing_normalization.get('repairs'):
        risk_items.append({
            'type': 'ooxml_spacing_value_normalized',
            'role': 'document',
            'message': (
                'invalid OpenXML spacing values such as decimal line spacing were normalized to Word-compatible '
                'integer values so Word does not ignore the requested line spacing'
            ),
            'repairs': spacing_normalization.get('repairs'),
            'examples': spacing_normalization.get('examples', [])[:8],
        })
    rules_diagnostics = format_source.get('rules_schema_diagnostics') or {}
    for warning in (rules_diagnostics.get('warnings') or [])[:12]:
        risk_items.append({
            'type': 'rules_json_schema_warning',
            'role': 'document',
            'message': warning,
            'diagnostics': {
                'valid_roles': rules_diagnostics.get('valid_roles'),
                'invalid_roles': rules_diagnostics.get('invalid_roles'),
                'normalized_fields': rules_diagnostics.get('normalized_fields'),
            },
        })
    for legacy_source in legacy_word_sources or []:
        risk_items.append({
            'type': 'legacy_word_conversion',
            'role': legacy_source.get('role'),
            'message': (
                'legacy .doc/.dot input was converted to temporary .docx before OpenXML extraction; '
                'style definitions and final visual appearance need local Word confirmation. '
                'For more accurate extraction, upload a native .docx/.dotx source-format file or directly provide explicit formatting rules as text instructions'
            ),
            'path': legacy_source.get('path'),
            'extension': legacy_source.get('extension'),
            'converted_docx': legacy_source.get('converted_docx'),
        })
    if format_conformance_stats.get('enabled'):
        if not format_conformance_stats.get('ok'):
            risk_items.append({
                'type': 'format_conformance_unresolved',
                'role': 'document',
                'message': 'some deterministic style/format conformance checks remained unresolved after repair',
                'after': format_conformance_stats.get('after'),
                'missing_styles': (format_conformance_stats.get('style_repairs') or {}).get('missing_styles'),
            })
    cross_language_roles = []
    for role, role_spec in roles.items():
        applied = role_spec.get('granular_fallback_applied') or {}
        if applied:
            fallback_roles.append({
                'role': role,
                'applied': applied,
                'reason': 'template/user rules did not provide every property; missing properties were filled by granular fallback',
            })
        route = role_spec.get('source_route')
        if route in ('fallback', 'unused_canonical_style_id'):
            risk_items.append({
                'type': 'style_source',
                'role': role,
                'message': f"role style source route is {route}; visual confirmation is recommended",
            })
        if not role_spec.get('source_paragraph_format_trusted', True):
            risk_items.append({
                'type': 'paragraph_format_trust',
                'role': role,
                'message': 'source paragraph looked like a format hint or implicit default; fallback may have filled paragraph properties',
            })
        if role == 'reference_item':
            paragraph = role_spec.get('paragraph') or {}
            indent = paragraph.get('indent') or {}
            numbering = paragraph.get('numbering') or {}
            numbering_controls_indent = bool(numbering.get('numId')) or reference_numbering_uses_word_auto(reference_numbering_map)
            has_hanging = any(
                indent.get(key) not in (None, '', '0')
                for key in ('hanging', 'hangingChars')
            )
            has_firstline = any(
                indent.get(key) not in (None, '', '0')
                for key in ('firstLine', 'firstLineChars')
            )
            if not has_hanging and not has_firstline and not numbering_controls_indent:
                risk_items.append({
                    'type': 'reference_item_missing_hanging_indent',
                    'role': 'reference_item',
                    'message': 'reference_item style has no hanging or first-line indentation; bibliography alignment needs visual confirmation',
                    'indent': indent,
                })
            elif (
                not numbering_controls_indent
                and (role_spec.get('granular_fallback_applied') or {}).get('paragraph', {}).get('indent')
            ):
                risk_items.append({
                    'type': 'reference_item_hanging_indent_fallback',
                    'role': 'reference_item',
                    'message': 'reference_item indentation was completed by granular fallback because the template did not expose explicit indentation XML',
                    'indent': indent,
                })
            elif (
                not numbering_controls_indent
                and ((role_spec.get('granular_fallback_applied') or {}).get('paragraph', {}).get('indent_guard'))
            ):
                risk_items.append({
                    'type': 'reference_item_hanging_indent_fallback',
                    'role': 'reference_item',
                    'message': 'reference_item indentation was completed by a visible-text numbering guard because the template did not expose explicit indentation XML',
                    'indent': indent,
                    'indent_guard': (role_spec.get('granular_fallback_applied') or {}).get('paragraph', {}).get('indent_guard'),
                })
        if role_spec.get('template_hint_colors_removed'):
            risk_items.append({
                'type': 'template_hint_color_removed',
                'role': role,
                'message': 'template instruction/placeholder colors were removed from authoritative style XML',
                'removed': role_spec.get('template_hint_colors_removed'),
            })
        source_resolution = role_spec.get('source_resolution')
        if source_resolution in ('cross_language_equivalent', 'cross_language_equivalent_over_weak_exact'):
            cross_language_roles.append({
                'role': role,
                'source_role': role_spec.get('source_role'),
                'source_style_id': role_spec.get('source_style_id'),
                'resolution': source_resolution,
                'message': 'role used a cross-language equivalent template style instead of falling back to body',
            })
        elif source_resolution == 'body_fallback' and role != 'body':
            risk_items.append({
                'type': 'role_style_body_fallback',
                'role': role,
                'message': 'role had no exact or cross-language equivalent template style and fell back to body; visual confirmation is required',
            })
    superscript_stats = superscript_stats or {}
    superscript_map = superscript_map or {}
    categories = superscript_map.get('categories') or {}
    if not (categories.get('reference_citation') or {}).get('enabled'):
        risk_items.append({
            'type': 'reference_citation_superscript',
            'role': 'body',
            'message': 'template did not provide explicit reference-citation superscript evidence; target reference citations were preserved unchanged',
            'preserved_count': superscript_stats.get('reference_citations_preserved', 0),
        })
    numbering_audit = numbering_audit or {}
    if numbering_audit.get('missing_num_ids'):
        risk_items.append({
            'type': 'numbering_definition',
            'role': 'styles',
            'message': 'some style numId references could not be found in template numbering.xml; numbered styles need visual confirmation',
            'missing_num_ids': numbering_audit.get('missing_num_ids'),
        })
    reference_numbering_map = reference_numbering_map or {}
    reference_numbering_stats = reference_numbering_stats or {}
    if reference_numbering_stats.get('word_auto_preserved'):
        risk_items.append({
            'type': 'reference_list_word_auto_numbering',
            'role': 'reference_item',
            'message': 'template reference list uses Word automatic numbering; reference_item numPr was preserved/migrated instead of adding visible text prefixes',
            'reference_items': reference_numbering_stats.get('reference_items', 0),
            'auto_numbering_examples': reference_numbering_map.get('auto_numbering_examples', [])[:5],
        })
    elif not reference_numbering_uses_visible_text(reference_numbering_map) and reference_numbering_stats.get('reference_items', 0):
        risk_items.append({
            'type': 'reference_list_numbering',
            'role': 'reference_item',
            'message': 'template did not provide explicit reference-list numbering evidence; missing reference numbers were not invented',
            'reference_items': reference_numbering_stats.get('reference_items', 0),
        })
    if reference_numbering_stats.get('added'):
        risk_items.append({
            'type': 'reference_list_numbering_repair',
            'role': 'reference_item',
            'message': 'missing reference-list numbers were added according to the template numbering pattern; manual bibliography order confirmation is recommended',
            'added': reference_numbering_stats.get('added', 0),
            'pattern': reference_numbering_stats.get('pattern'),
            'examples': reference_numbering_stats.get('added_examples', [])[:5],
        })
    if reference_numbering_stats.get('skipped_uncertain'):
        risk_items.append({
            'type': 'reference_list_numbering_uncertain',
            'role': 'reference_item',
            'message': 'some reference-zone paragraphs were not numbered because they were uncertain continuations or non-reference text',
            'skipped_uncertain': reference_numbering_stats.get('skipped_uncertain', 0),
        })
    equation_layout_map = equation_layout_map or {}
    equation_layout_stats = equation_layout_stats or {}
    if not equation_layout_map.get('enabled') and equation_layout_stats.get('equation_paragraphs', 0):
        if equation_layout_stats.get('fallback_applied'):
            risk_items.append({
                'type': 'equation_layout_computed_fallback',
                'role': 'body',
                'message': 'template did not provide explicit equation tab-stop layout; numbered equations used computed center/right tab stops from the active section or column width',
                'equation_paragraphs': equation_layout_stats.get('equation_paragraphs', 0),
                'fallback_applied': equation_layout_stats.get('fallback_applied', 0),
                'computed_fallback_by_width': equation_layout_stats.get('computed_fallback_by_width', {}),
                'by_kind': equation_layout_stats.get('by_kind', {}),
            })
        else:
            risk_items.append({
                'type': 'equation_layout',
                'role': 'body',
                'message': 'template did not provide explicit equation tab-stop layout and no numbered display equation fallback was applied; equation layout needs visual confirmation',
                'equation_paragraphs': equation_layout_stats.get('equation_paragraphs', 0),
                'by_kind': equation_layout_stats.get('by_kind', {}),
            })
    if equation_layout_stats.get('by_kind', {}).get('ole_object') or equation_layout_stats.get('by_kind', {}).get('numbered_graphic_equation'):
        risk_items.append({
            'type': 'equation_object_layout',
            'role': 'body',
            'message': 'equation tab layout was applied to equation-like object paragraphs such as MathType/OLE or numbered graphic equations; object content was preserved, but visual confirmation is required',
            'by_kind': equation_layout_stats.get('by_kind', {}),
        })
    table_format_map = table_format_map or {}
    table_format_stats = table_format_stats or {}
    if not table_format_map.get('enabled') and table_format_stats.get('target_tables', 0):
        risk_items.append({
            'type': 'table_body_format',
            'role': 'tables',
            'message': 'template did not provide table XML formatting evidence; target table body formatting was preserved and needs visual confirmation',
            'target_tables': table_format_stats.get('target_tables', 0),
        })
    if table_format_stats.get('target_tables') and table_format_stats.get('target_tables') != len(table_format_map.get('tables') or []):
        risk_items.append({
            'type': 'table_count_mismatch',
            'role': 'tables',
            'message': 'template/target table counts differ; target tables used the strongest representative template table format instead of weak index matching',
            'target_tables': table_format_stats.get('target_tables'),
            'template_tables': len(table_format_map.get('tables') or []),
            'representative_reuse_count': table_format_stats.get('representative_reuse_count', 0),
        })
    if table_format_stats.get('weak_profile_bypassed_count') or table_format_stats.get('index_profile_bypassed'):
        risk_items.append({
            'type': 'table_weak_template_profile_bypassed',
            'role': 'tables',
            'message': 'weak or placeholder template tables were bypassed so they would not remove borders from target tables',
            'bypassed': table_format_stats.get('index_profile_bypassed', [])[:20],
        })
    if table_format_map.get('fallback_applied') or table_format_stats.get('fallback_applied'):
        risk_items.append({
            'type': 'table_three_line_fallback',
            'role': 'tables',
            'message': 'template table XML evidence was missing or weak, so a conservative academic three-line table fallback was applied; visually confirm table borders',
            'fallback_reason': table_format_map.get('fallback_reason') or table_format_stats.get('fallback_reason'),
            'target_tables': table_format_stats.get('target_tables', 0),
        })
    if table_format_stats.get('width_preserved_auto_template'):
        risk_items.append({
            'type': 'table_width_preserved',
            'role': 'tables',
            'message': 'template table width was auto/unspecified, so target table width was preserved to avoid shrinking tables',
            'preserved_tables': table_format_stats.get('width_preserved_auto_template'),
        })
    if table_format_stats.get('width_overridden') and not table_format_stats.get('preserve_table_width'):
        risk_items.append({
            'type': 'table_width_overridden',
            'role': 'tables',
            'message': 'table width override was explicitly allowed; visual confirmation of table widths is required',
            'overridden_tables': table_format_stats.get('width_overridden'),
        })
    section_structure_stats = section_structure_stats or {}
    if section_structure_stats.get('inserted'):
        risk_items.append({
            'type': 'mixed_column_section_inserted',
            'role': 'sections',
            'message': 'mixed-column template structure was detected; a section break was inserted before target body text so front matter and body can use different column counts',
            'front_cols': section_structure_stats.get('front_cols'),
            'body_cols': section_structure_stats.get('body_cols'),
            'body_start_child': section_structure_stats.get('body_start_child'),
            'template_body_index': section_structure_stats.get('template_body_index'),
        })
    elif section_structure_stats.get('reason') in ('target_body_start_not_found', 'template_body_section_not_found'):
        risk_items.append({
            'type': 'mixed_column_section_not_inserted',
            'role': 'sections',
            'message': 'mixed-column template structure may require section breaks, but automatic insertion was skipped because the target body start or template body section was uncertain',
            'reason': section_structure_stats.get('reason'),
        })
    column_object_fit_stats = column_object_fit_stats or {}
    if column_object_fit_stats.get('enabled') and (
        column_object_fit_stats.get('drawings_scaled') or column_object_fit_stats.get('tables_fitted')
    ):
        risk_items.append({
            'type': 'multicolumn_object_width_fit',
            'role': 'images_tables',
            'message': 'wide images/tables in multi-column sections were fitted to the active column width; visually confirm object placement and readability',
            'drawings_scaled': column_object_fit_stats.get('drawings_scaled', 0),
            'tables_fitted': column_object_fit_stats.get('tables_fitted', 0),
        })
    high_inline_line_spacing_stats = high_inline_line_spacing_stats or {}
    if high_inline_line_spacing_stats.get('paragraphs_changed'):
        risk_items.append({
            'type': 'high_inline_content_line_spacing_repair',
            'role': 'images_formulas',
            'message': 'paragraphs containing inline images, OLE/MathType objects, or formulas had fixed exact line spacing relaxed to avoid clipping; visually confirm images/formulas render fully',
            'paragraphs_changed': high_inline_line_spacing_stats.get('paragraphs_changed', 0),
            'content_kind_counts': high_inline_line_spacing_stats.get('content_kind_counts', {}),
            'examples': high_inline_line_spacing_stats.get('examples', [])[:8],
        })
    header_footer_watermark_stats = header_footer_watermark_stats or {}
    if header_footer_watermark_stats.get('paragraphs_removed') or header_footer_watermark_stats.get('drawings_removed'):
        risk_items.append({
            'type': 'header_footer_watermark_cleanup',
            'role': 'headers_footers',
            'message': 'background image watermarks were removed from header/footer parts; visually confirm the watermark is gone and normal header/footer text remains',
            'paragraphs_removed': header_footer_watermark_stats.get('paragraphs_removed', 0),
            'drawings_removed': header_footer_watermark_stats.get('drawings_removed', 0),
            'parts_changed': header_footer_watermark_stats.get('parts_changed', [])[:8],
        })
    abstract_keyword_label_stats = abstract_keyword_label_stats or {}
    metadata_layout_stats = metadata_layout_stats or {}
    if metadata_layout_stats.get('paragraphs_changed'):
        risk_items.append({
            'type': 'metadata_tab_layout_repair',
            'role': 'metadata',
            'message': 'Chinese classification/document-code metadata was normalized to one line with a right tab stop at the body text boundary; visually confirm metadata alignment',
            'paragraphs_changed': metadata_layout_stats.get('paragraphs_changed'),
            'adjacent_pairs_merged': metadata_layout_stats.get('adjacent_pairs_merged'),
            'tab_positions_twips': metadata_layout_stats.get('tab_positions_twips', [])[:5],
        })
    qa_report = qa_report or {}
    libreoffice_compatibility_qa = qa_report.get('libreoffice_compatibility_qa') or {}
    if libreoffice_compatibility_qa.get('enabled') and not libreoffice_compatibility_qa.get('ok'):
        risk_items.append({
            'type': 'libreoffice_compatibility_failed',
            'role': 'document',
            'message': (
                'LibreOffice could not load/export the final DOCX during compatibility QA; '
                'the file was not normalized through LibreOffice to avoid changing Word-specific content'
            ),
            'failure_kind': libreoffice_compatibility_qa.get('failure_kind'),
            'error': libreoffice_compatibility_qa.get('error'),
            'stderr_tail': libreoffice_compatibility_qa.get('stderr_tail'),
        })
    render_qa = qa_report.get('render_qa') or {}
    if render_qa.get('enabled') and not render_qa.get('ok'):
        risk_items.append({
            'type': 'render_qa_failed',
            'role': 'document',
            'message': 'final DOCX render QA did not complete successfully; local Word visual confirmation is required',
            'error': render_qa.get('error'),
            'engine': render_qa.get('engine'),
            'failure_kind': render_qa.get('failure_kind'),
        })
    render_compare_qa = qa_report.get('render_compare_qa') or {}
    if render_compare_qa.get('skipped') and render_compare_qa.get('skip_reason') == 'format_source_text_rules':
        risk_items.append({
            'type': 'render_compare_skipped_text_rules',
            'role': 'document',
            'message': (
                'target-before/final visual comparison was skipped because formatting was driven by '
                'text/OCR rules; local Word visual confirmation is still required'
            ),
            'source_type': render_compare_qa.get('source_type'),
        })
    elif render_compare_qa.get('enabled') and not render_compare_qa.get('ok'):
        risk_items.append({
            'type': 'mandatory_render_compare_failed',
            'role': 'document',
            'message': 'mandatory target-before/final render comparison did not complete; local Word visual confirmation is required',
            'error': render_compare_qa.get('error'),
            'attempted_engines': render_compare_qa.get('attempted_engines', []),
            'failures': render_compare_qa.get('failures', []),
        })
    elif render_compare_qa.get('enabled') and render_compare_qa.get('engine') != 'word':
        risk_items.append({
            'type': 'render_engine_fallback_used',
            'role': 'document',
            'message': 'Microsoft Word render engine was not used for the successful comparison; a lower-priority engine rendered both files',
            'engine': render_compare_qa.get('engine'),
            'attempted_engines': render_compare_qa.get('attempted_engines', []),
        })
    render_comparison = render_compare_qa.get('comparison') or {}
    if render_comparison.get('page_count_changed'):
        risk_items.append({
            'type': 'render_compare_page_count_changed',
            'role': 'document',
            'message': 'render comparison found a page-count change after formatting; pagination needs visual confirmation',
            'before_page_count': render_comparison.get('before_page_count'),
            'final_page_count': render_comparison.get('final_page_count'),
        })
    if render_comparison.get('missing_pages'):
        risk_items.append({
            'type': 'render_compare_missing_pages',
            'role': 'document',
            'message': 'render comparison found missing pages on one side of the comparison',
            'missing_pages': render_comparison.get('missing_pages')[:8],
        })
    if render_comparison.get('dimension_changes'):
        risk_items.append({
            'type': 'render_compare_page_dimension_changed',
            'role': 'document',
            'message': 'render comparison found page image dimension changes; page size/orientation should be checked',
            'dimension_changes': render_comparison.get('dimension_changes')[:8],
        })
    final_audit = qa_report.get('final_audit') or {}
    final_summary = final_audit.get('summary') or {}
    if final_summary.get('direct_run_formatting_runs', 0) > 0:
        risk_items.append({
            'type': 'final_direct_run_formatting_remaining',
            'role': 'document',
            'message': 'final document still contains direct run formatting; visual confirmation is recommended for font/size consistency',
            'count': final_summary.get('direct_run_formatting_runs'),
        })
    if final_summary.get('direct_paragraph_formatting_paragraphs', 0) > 0:
        risk_items.append({
            'type': 'final_direct_paragraph_formatting_remaining',
            'role': 'document',
            'message': 'final document still contains direct paragraph formatting such as spacing, indentation, tabs, borders, or numbering; visual confirmation is recommended',
            'count': final_summary.get('direct_paragraph_formatting_paragraphs'),
        })
    final_tables = final_audit.get('tables') or {}
    if final_tables.get('issue_count', 0) > 0:
        risk_items.append({
            'type': 'final_table_geometry_issues',
            'role': 'tables',
            'message': 'table geometry audit found width, grid, border, or cell-width issues that may affect Word display',
            'count': final_tables.get('issue_count'),
            'examples': (final_tables.get('issues') or [])[:8],
        })
    final_images = final_audit.get('images') or {}
    image_kind_counts = final_images.get('kind_counts') or {}
    if image_kind_counts.get('anchor', 0) > 0:
        risk_items.append({
            'type': 'floating_images_present',
            'role': 'images',
            'message': 'floating/anchored images are present; placement can differ between Word, LibreOffice, and PDF renderers',
            'count': image_kind_counts.get('anchor'),
        })
    header_footer_background_issues = [
        issue for issue in (final_images.get('issues') or [])
        if issue.get('type') == 'header_footer_background_images_present'
    ]
    if header_footer_background_issues:
        risk_items.append({
            'type': 'header_footer_watermark_residue',
            'role': 'headers_footers',
            'message': 'header/footer still contains behind-text or large anchored images that may render as watermarks; visually confirm whether they are intended template content',
            'issues': header_footer_background_issues[:8],
        })
    non_anchor_image_issues = [
        issue for issue in (final_images.get('issues') or [])
        if issue.get('type') not in ('floating_images_present', 'header_footer_background_images_present')
    ]
    fixed_line_issues = [
        issue for issue in non_anchor_image_issues
        if issue.get('type') == 'fixed_line_spacing_high_inline_content'
    ]
    if fixed_line_issues:
        risk_items.append({
            'type': 'fixed_line_spacing_high_inline_content',
            'role': 'images_formulas',
            'message': 'QA found remaining paragraphs where exact fixed line spacing can clip inline images, OLE/MathType objects, or formulas',
            'issues': fixed_line_issues[:8],
        })
    non_anchor_image_issues = [
        issue for issue in non_anchor_image_issues
        if issue.get('type') != 'fixed_line_spacing_high_inline_content'
    ]
    if non_anchor_image_issues:
        risk_items.append({
            'type': 'image_relationship_or_anchor_issue',
            'role': 'images',
            'message': 'image QA found anchor or relationship issues; image placement and visibility need confirmation',
            'issues': non_anchor_image_issues[:8],
        })
    final_fields = final_audit.get('fields') or {}
    if final_fields.get('update_sensitive_field_counts'):
        risk_items.append({
            'type': 'word_fields_need_refresh',
            'role': 'document',
            'message': 'Word fields such as page numbers, TOC, REF/PAGEREF, or caption sequences may need updating after opening in Word',
            'field_types': final_fields.get('update_sensitive_field_counts'),
        })
    final_headings = final_audit.get('headings') or {}
    if final_headings.get('issues'):
        risk_items.append({
            'type': 'heading_hierarchy_or_numbering_issue',
            'role': 'headings',
            'message': 'heading QA found possible hierarchy jumps or numbered paragraphs that may affect headings/TOC',
            'issues': final_headings.get('issues')[:8],
        })
    target_before_audit = qa_report.get('target_before_audit') or {}
    before_summary = target_before_audit.get('summary') or {}
    count_pairs = [
        ('table_count', 'tables', 'table'),
        ('media_count', 'images', 'media/image'),
        ('embedding_count', 'formulas', 'embedded object/OLE'),
        ('drawing_count', 'images', 'drawing'),
        ('field_count', 'document', 'Word field'),
    ]
    for key, role, label in count_pairs:
        before_count = before_summary.get(key)
        after_count = final_summary.get(key)
        if before_count is not None and after_count is not None and after_count < before_count:
            risk_items.append({
                'type': 'qa_object_count_drop',
                'role': role,
                'message': f'{label} count dropped after formatting; preservation must be checked before delivery',
                'metric': key,
                'before': before_count,
                'after': after_count,
            })
    role_counts = {}
    for item in role_map or []:
        role = item.get('role')
        role_counts[role] = role_counts.get(role, 0) + 1
    heading_numbering_conflicts = [
        {
            'index': item.get('index'),
            'role': item.get('role'),
            'manual_prefix': item.get('manual_heading_number_prefix'),
            'style_id': item.get('style_id'),
            'original_style_id': item.get('original_style_id'),
            'text': item.get('text'),
        }
        for item in role_map or []
        if item.get('heading_numbering_conflict_resolved')
    ]
    if heading_numbering_conflicts:
        risk_items.append({
            'type': 'heading_manual_number_auto_number_conflict_resolved',
            'role': 'headings',
            'message': (
                'some target headings already contained manual numbering while the template heading style used '
                'Word automatic numbering; no-number mirror heading styles were used for those paragraphs to avoid duplicate numbers'
            ),
            'count': len(heading_numbering_conflicts),
            'examples': heading_numbering_conflicts[:8],
        })
    return {
        'fallback_roles': fallback_roles,
        'cross_language_roles': cross_language_roles,
        'risk_items': risk_items,
        'superscript': {
            'categories': categories,
            'stats': superscript_stats,
        },
        'numbering': numbering_audit,
        'reference_numbering': {
            'map_enabled': bool(reference_numbering_map.get('enabled')),
            'pattern': reference_numbering_map.get('pattern'),
            'stats': reference_numbering_stats,
        },
        'equation_layout': {
            'map_enabled': bool(equation_layout_map.get('enabled')),
            'numbered_equation': equation_layout_map.get('numbered_equation'),
            'stats': equation_layout_stats,
            'samples': equation_layout_map.get('samples', [])[:10],
        },
        'table_format': {
            'map_enabled': bool(table_format_map.get('enabled')),
            'stats': table_format_stats,
            'representative_table': {
                key: (table_format_map.get('representative_table') or {}).get(key)
                for key in ('index', 'kind', 'rows', 'cols', 'chars', 'format_strength', 'weak_format')
            } if table_format_map.get('representative_table') else None,
        },
        'section_structure': section_structure_stats,
        'high_inline_content_line_spacing': high_inline_line_spacing_stats,
        'abstract_keyword_label_bold': abstract_keyword_label_stats,
        'metadata_tab_layout': metadata_layout_stats,
        'header_footer_watermark_cleanup': header_footer_watermark_stats,
        'format_conformance': format_conformance_stats,
        'qa': qa_report,
        'role_counts': role_counts,
        'heading_numbering_conflicts_resolved': heading_numbering_conflicts,
        'user_note_requirements': [
            'Tell the user only the concrete areas that need special visual confirmation.',
            'Do not list successful style applications or every fallback area.',
            'If reference-citation superscript evidence is missing, tell the user citations were preserved unchanged and should be checked.',
        ],
    }


def write_format_report(report, path):
    if not path:
        return
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  Wrote format report: {path}")


def load_style_spec(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def audit_style_spec_preflight(spec):
    warnings = []
    roles = spec.get('roles', {})
    for role, role_spec in roles.items():
        chain = role_spec.get('source_style_chain') or []
        source_style_id = role_spec.get('source_style_id')
        if source_style_id and chain and chain[-1] != source_style_id:
            warnings.append(
                f"{role} source_style_id={source_style_id!r} does not match the leaf of source_style_chain={chain!r}; "
                "verify semantic style routing did not collapse to a basedOn parent"
            )
    body = roles.get('body', {})
    body_route = body.get('source_route')
    if body_route in ('unused_canonical_style_id', 'canonical_style_id'):
        warnings.append(
            "body style spec uses an unverified canonical style route; "
            "verify real template body paragraphs use that pStyle or regenerate the style spec"
        )
    if body and (not body.get('font') or not body.get('paragraph')):
        warnings.append(
            "body style spec lacks structured font/paragraph summary; "
            "style_xml may be stale or the extractor missed the actual body paragraph signature"
        )
    if body.get('source_style_id') in ('BodyText', 'BodyTextIndent', 'Para') and body_route != 'used_canonical_style_id':
        warnings.append(
            f"body source_style_id={body.get('source_style_id')!r} is not backed by a used canonical route"
        )
    for role, role_spec in roles.items():
        for label, xml_key in (('style/rPr', 'rPr_xml'), ('style/pPr/rPr', 'pPr_xml')):
            elem = xml_to_element(role_spec.get(xml_key))
            rPr = elem if xml_key == 'rPr_xml' else child_by_local_name(elem, 'rPr')
            rFonts = child_by_local_name(rPr, 'rFonts')
            if rfonts_has_theme_specific_conflict(rFonts):
                warnings.append(
                    f"{role} {label} has both theme font and concrete font attributes; "
                    "concrete fonts may override Calibri/Cambria theme fonts"
                )
    if warnings:
        print("  WARNING: style-spec preflight found suspicious role styles:")
        for warning in warnings:
            print(f"    - {warning}")
    return warnings


def style_spec_source_type(spec, explicit_source_type=None):
    meta = (spec or {}).get('_meta') or {}
    return normalize_format_source_type(
        explicit_source_type
        or meta.get('source_type')
        or meta.get('format_source_type')
        or (spec or {}).get('source_type')
        or (spec or {}).get('format_source_type')
    )


def style_spec_fallback_language(spec, target_dir=None):
    roles = (spec or {}).get('roles') or {}
    text_rules = {
        role: role_spec.get('text_rule') or {}
        for role, role_spec in roles.items()
        if isinstance(role_spec, dict)
    }
    return (
        infer_rule_language_from_rules(text_rules)
        or infer_target_language(target_dir)
        or ((spec or {}).get('_meta') or {}).get('fallback_language')
        or next(
            (
                role_spec.get('fallback_language')
                for role_spec in roles.values()
                if isinstance(role_spec, dict) and role_spec.get('fallback_language')
            ),
            None,
        )
        or 'en'
    )


def style_spec_fallback_columns(spec, target_dir=None):
    meta = (spec or {}).get('_meta') or {}
    value = meta.get('fallback_columns')
    if value is None:
        for role_spec in ((spec or {}).get('roles') or {}).values():
            if isinstance(role_spec, dict) and role_spec.get('fallback_columns') is not None:
                value = role_spec.get('fallback_columns')
                break
    if value is None and target_dir:
        value = detect_fallback_columns(target_dir)
    try:
        return 2 if int(value or 1) >= 2 else 1
    except (TypeError, ValueError):
        return 1


def rebuild_low_confidence_role_style(role, role_spec, source_type, language, columns=1):
    style = clean_role_style_shell()
    style.set(w('styleId'), role_spec.get('style_id', ROLE_STYLE_IDS[role]))
    style.set(w('type'), role_spec.get('type', 'paragraph'))
    name_elem = ET.Element(w('name'))
    name_elem.set(w('val'), role_spec.get('display_name', ROLE_DISPLAY_NAMES[role]))
    style.insert(0, name_elem)
    rule = normalize_user_rule(role_spec.get('text_rule') or {})
    apply_rule_to_style(style, rule)
    sanitized = sanitize_unspecified_visual_properties(
        style,
        role,
        rule,
        source_type=source_type,
        remove_emphasis=source_type in WEAK_EXTERNAL_STYLE_SOURCE_TYPES,
    )
    applied = apply_granular_fallback_to_style(
        style, role, language, rule, source_type=source_type, columns=columns
    )
    reference_indent_fix = ensure_reference_item_indent_guard(style, role)
    if reference_indent_fix:
        applied.setdefault('paragraph', {}).setdefault('indent_guard', reference_indent_fix)
    if not rule.get('fonts'):
        normalize_theme_font_conflicts_in_style(style)
    return style, applied, sanitized


def materialize_low_confidence_fallback_in_style_spec(spec, source_type=None, target_dir=None):
    """Repair old/blank-carrier specs so stale Word defaults cannot override fallback."""
    spec = spec or {}
    roles = spec.get('roles') or {}
    effective_source_type = style_spec_source_type(spec, explicit_source_type=source_type)
    if effective_source_type not in WEAK_EXTERNAL_STYLE_SOURCE_TYPES:
        return spec, {}
    language = style_spec_fallback_language(spec, target_dir=target_dir)
    columns = style_spec_fallback_columns(spec, target_dir=target_dir)
    meta = spec.setdefault('_meta', {})
    meta['source_type'] = effective_source_type
    meta['format_source_type'] = effective_source_type
    meta['fallback_language'] = language
    meta['fallback_columns'] = columns
    meta['blank_carrier_fallback_materialized'] = effective_source_type == 'blank_carrier_template'
    repaired = {}
    for role, role_spec in roles.items():
        if role not in ROLE_STYLE_IDS or not isinstance(role_spec, dict):
            continue
        style, applied, sanitized = rebuild_low_confidence_role_style(
            role, role_spec, effective_source_type, language, columns=columns
        )
        pPr = get_direct_child(style, w('pPr'))
        rPr = get_direct_child(style, w('rPr'))
        role_spec['style_id'] = role_spec.get('style_id') or ROLE_STYLE_IDS[role]
        role_spec['display_name'] = role_spec.get('display_name') or ROLE_DISPLAY_NAMES[role]
        role_spec['type'] = 'paragraph'
        role_spec['font'] = summarize_rpr(rPr)
        role_spec['paragraph'] = summarize_ppr(pPr)
        role_spec['pPr_xml'] = xml_string(pPr)
        role_spec['rPr_xml'] = xml_string(rPr)
        role_spec['style_xml'] = xml_string(style)
        role_spec['fallback_language'] = language
        role_spec['fallback_columns'] = columns
        role_spec['format_source_type'] = effective_source_type
        role_spec['source_route'] = role_spec.get('source_route') or 'fallback'
        role_spec['source_paragraph_format_trusted'] = False
        role_spec['granular_fallback_applied'] = applied
        if sanitized:
            role_spec['unspecified_visual_properties_sanitized'] = sanitized
        if applied:
            repaired[role] = applied
    return spec, {
        'source_type': effective_source_type,
        'fallback_language': language,
        'fallback_columns': columns,
        'roles_rebuilt': sorted(repaired),
        'repaired': repaired,
    }


def style_element_from_spec(role, role_spec, strip_reference_numbering=False):
    style_xml = role_spec.get('style_xml')
    if style_xml:
        style = ET.fromstring(style_xml)
    else:
        style = ET.Element(w('style'))
        style.set(w('type'), role_spec.get('type', 'paragraph'))
        pPr = xml_to_element(role_spec.get('pPr_xml'))
        rPr = xml_to_element(role_spec.get('rPr_xml'))
        if pPr is not None:
            style.append(pPr)
        if rPr is not None:
            style.append(rPr)

    style.set(w('styleId'), role_spec.get('style_id', ROLE_STYLE_IDS[role]))
    style.set(w('type'), role_spec.get('type', 'paragraph'))
    strip_unstable_style_links(style)
    name_elem = get_direct_child(style, w('name'))
    if name_elem is None:
        name_elem = ET.Element(w('name'))
        style.insert(0, name_elem)
    name_elem.set(w('val'), role_spec.get('display_name', ROLE_DISPLAY_NAMES[role]))
    scrub_role_inherited_pollution(style, role)
    if role == 'reference_item' and strip_reference_numbering:
        strip_reference_item_style_numbering(style)
    if not (role_spec.get('text_rule') or {}).get('fonts'):
        normalize_theme_font_conflicts_in_style(style)
    source_type = normalize_format_source_type(
        ((role_spec.get('text_rule') or {}).get('source_type'))
        or ((role_spec.get('text_rule') or {}).get('format_source_type'))
        or ((role_spec.get('_meta') or {}).get('source_type'))
        or role_spec.get('format_source_type')
        or role_spec.get('source_type')
    )
    if not source_type:
        source_type = normalize_format_source_type((role_spec.get('source') or {}).get('source_type') if isinstance(role_spec.get('source'), dict) else None)
    sanitize_unspecified_visual_properties(
        style,
        role,
        role_spec.get('text_rule') or {},
        source_type=(source_type or (role_spec.get('source_type') if isinstance(role_spec.get('source_type'), str) else None)),
    )
    normalize_spacing_element_values(style)
    return style


def strip_reference_item_style_numbering(style):
    removed = 0
    for pPr in style.iter(w('pPr')):
        removed += remove_children_by_local_name(pPr, {'numPr'})
    return removed


def install_style_spec(target_dir, spec, template_dir=None, reference_numbering_map=None):
    styles_path = os.path.join(target_dir, 'word', 'styles.xml')
    tree = ET.parse(styles_path)
    root = tree.getroot()
    target_by_id = build_style_id_index(root)
    numbering_audit = {}
    exclude_numbered_roles = set()
    strip_reference_numbering = reference_numbering_uses_visible_text(reference_numbering_map)
    reference_word_auto = reference_numbering_uses_word_auto(reference_numbering_map)
    if strip_reference_numbering:
        exclude_numbered_roles.add('reference_item')
    if template_dir:
        required_num_ids = collect_required_num_ids_from_spec(spec, exclude_roles=exclude_numbered_roles)
        numbering_audit = copy_numbering_definitions(template_dir, target_dir, required_num_ids)
        if required_num_ids:
            print(
                f"  Numbering sync: required numIds={required_num_ids}, "
                f"mapped={numbering_audit.get('num_id_map', {})}, "
                f"missing={numbering_audit.get('missing_num_ids', [])}"
            )
    installed = 0
    for role, role_spec in spec.get('roles', {}).items():
        if role not in ROLE_STYLE_IDS:
            continue
        style = style_element_from_spec(
            role, role_spec,
            strip_reference_numbering=(role == 'reference_item' and strip_reference_numbering),
        )
        if numbering_audit.get('num_id_map'):
            update_style_num_ids(style, numbering_audit['num_id_map'])
        if role == 'reference_item':
            indent_fix = ensure_reference_item_indent_guard(
                style,
                role,
                create_default=(not reference_word_auto),
            )
            if indent_fix:
                role_spec.setdefault('granular_fallback_applied', {}).setdefault('paragraph', {})[
                    'indent_guard'
                ] = indent_fix
                pPr = get_direct_child(style, w('pPr'))
                rPr = get_direct_child(style, w('rPr'))
                role_spec['paragraph'] = summarize_ppr(pPr)
                role_spec['pPr_xml'] = xml_string(pPr)
                role_spec['rPr_xml'] = xml_string(rPr)
                role_spec['style_xml'] = xml_string(style)
        style_id = style.get(w('styleId'))
        old = target_by_id.get(style_id)
        if old is not None:
            idx = list(root).index(old)
            root.remove(old)
            root.insert(idx, style)
        else:
            root.append(style)
        target_by_id[style_id] = style
        installed += 1
    write_xml(tree, styles_path)
    print(f"  Installed {installed} styles from intermediate spec")
    return {
        'role_style_ids': {
            role: role_spec.get('style_id', ROLE_STYLE_IDS[role])
            for role, role_spec in spec.get('roles', {}).items()
            if role in ROLE_STYLE_IDS
        },
        'numbering_audit': numbering_audit,
    }


def ensure_style_child_after_name(style_elem, tag):
    child = get_direct_child(style_elem, tag)
    if child is not None:
        return child
    child = ET.Element(tag)
    children = list(style_elem)
    if tag == w('rPr'):
        pPr = get_direct_child(style_elem, w('pPr'))
        if pPr is not None:
            style_elem.insert(children.index(pPr) + 1, child)
            return child
    insert_at = 0
    name_elem = get_direct_child(style_elem, w('name'))
    if name_elem is not None:
        insert_at = children.index(name_elem) + 1
    style_elem.insert(insert_at, child)
    return child


def ensure_doc_defaults_containers(styles_root):
    doc_defaults = get_direct_child(styles_root, w('docDefaults'))
    if doc_defaults is None:
        doc_defaults = ET.Element(w('docDefaults'))
        styles_root.insert(0, doc_defaults)
    pPr_default = get_or_add_child(doc_defaults, w('pPrDefault'))
    rPr_default = get_or_add_child(doc_defaults, w('rPrDefault'))
    pPr = get_or_add_child(pPr_default, w('pPr'))
    rPr = get_or_add_child(rPr_default, w('rPr'))
    return pPr, rPr


def ensure_normal_style(styles_root, style_by_id):
    normal = style_by_id.get('Normal')
    if normal is None:
        normal = ET.Element(w('style'))
        normal.set(w('type'), 'paragraph')
        normal.set(w('styleId'), 'Normal')
        normal.set(w('default'), '1')
        name_elem = ET.Element(w('name'))
        name_elem.set(w('val'), 'Normal')
        normal.append(name_elem)
        styles_root.append(normal)
        style_by_id['Normal'] = normal
    else:
        normal.set(w('default'), normal.get(w('default')) or '1')
    pPr = ensure_style_child_after_name(normal, w('pPr'))
    rPr = ensure_style_child_after_name(normal, w('rPr'))
    return normal, pPr, rPr


def apply_rule_to_property_containers(pPr, rPr, rule):
    if not rule:
        return
    if pPr is not None:
        if 'align' in rule:
            jc = get_or_add_child(pPr, w('jc'))
            jc.set(w('val'), str(rule['align']))
        if 'spacing' in rule:
            spacing = get_or_add_child(pPr, w('spacing'))
            for key, value in normalize_spacing_rule(rule.get('spacing') or {}).items():
                spacing.set(w(key), str(value))
        if 'indent' in rule:
            ind = get_or_add_child(pPr, w('ind'))
            for key, value in normalize_reference_hanging_indent_rule(rule.get('indent') or {}).items():
                ind.set(w(key), str(value))
    if rPr is not None:
        apply_rule_to_rpr(rPr, rule)


def materialize_blank_carrier_defaults(target_dir, spec, source_type=None):
    source_type = style_spec_source_type(spec, explicit_source_type=source_type)
    if source_type not in WEAK_EXTERNAL_STYLE_SOURCE_TYPES:
        return {}
    language = ((spec or {}).get('_meta') or {}).get('fallback_language') or style_spec_fallback_language(spec, target_dir=target_dir)
    columns = style_spec_fallback_columns(spec, target_dir=target_dir)
    styles_path = os.path.join(target_dir, 'word', 'styles.xml')
    if not os.path.exists(styles_path):
        return {'enabled': False, 'reason': 'styles.xml missing'}
    tree = ET.parse(styles_path)
    root = tree.getroot()
    style_by_id = build_style_id_index(root)
    body_rule = normalize_user_rule(((spec.get('roles') or {}).get('body') or {}).get('text_rule') or {})
    body_lock_rule = fallback_lock_rule_for_source('body', body_rule, source_type=source_type)
    body_ooxml_spec = variant_body_ooxml_fallback(language, columns)
    normal_spec = fallback_ooxml_normal_spec(language=language, columns=columns)
    body_fallback = role_fallback_rule(
        'body',
        language,
        locked_rule=body_lock_rule,
        allow_alignment=True,
    )
    pPr_default, rPr_default = ensure_doc_defaults_containers(root)
    doc_default_ooxml = {
        'paragraph_ooxml': merge_ooxml_children_by_name(
            pPr_default,
            body_ooxml_spec.get('pPr_xml'),
            skip_names={'pStyle', 'sectPr'},
            override_names={'jc', 'spacing', 'ind', 'tabs', 'keepNext', 'keepLines', 'widowControl'},
        ),
        'font_ooxml': merge_ooxml_children_by_name(
            rPr_default,
            body_ooxml_spec.get('rPr_xml'),
            override_names={'rFonts', 'sz', 'szCs', 'b', 'bCs', 'i', 'iCs', 'color', 'lang'},
        ),
    }
    doc_default_applied = {
        'paragraph': ensure_ppr_fallback(pPr_default, body_fallback, override_keys={'align', 'spacing', 'indent'}),
        'font': ensure_rpr_fallback(rPr_default, body_fallback, override_keys={'fonts', 'size'}),
    }
    apply_rule_to_property_containers(pPr_default, rPr_default, body_lock_rule)
    normal_style, normal_pPr, normal_rPr = ensure_normal_style(root, style_by_id)
    normal_ooxml = {
        'paragraph_ooxml': merge_ooxml_children_by_name(
            normal_pPr,
            normal_spec.get('pPr_xml') or body_ooxml_spec.get('pPr_xml'),
            skip_names={'pStyle', 'sectPr'},
            override_names={'jc', 'spacing', 'ind', 'tabs', 'keepNext', 'keepLines', 'widowControl'},
        ),
        'font_ooxml': merge_ooxml_children_by_name(
            normal_rPr,
            normal_spec.get('rPr_xml') or body_ooxml_spec.get('rPr_xml'),
            override_names={'rFonts', 'sz', 'szCs', 'b', 'bCs', 'i', 'iCs', 'color', 'lang'},
        ),
    }
    normal_applied = {
        'paragraph': ensure_ppr_fallback(normal_pPr, body_fallback, override_keys={'align', 'spacing', 'indent'}),
        'font': ensure_rpr_fallback(normal_rPr, body_fallback, override_keys={'fonts', 'size'}),
    }
    apply_rule_to_property_containers(normal_pPr, normal_rPr, body_lock_rule)
    write_xml(tree, styles_path)
    return {
        'enabled': True,
        'source_type': source_type,
        'fallback_language': language,
        'fallback_columns': columns,
        'fallback_source': 'assets/fallback_ooxml_spec.json',
        'fallback_variant': fallback_variant_key(language, columns),
        'body_fallback': body_fallback,
        'docDefaults': {
            'ooxml': doc_default_ooxml,
            'legacy_backup': doc_default_applied,
        },
        'Normal': {
            'ooxml': normal_ooxml,
            'legacy_backup': normal_applied,
        },
    }


HEADING_NUMBERED_ROLES = {'heading1', 'heading2', 'heading3'}


def style_has_numbering(style_elem):
    if style_elem is None:
        return False
    for pPr in style_elem.iter(w('pPr')):
        if child_by_local_name(pPr, 'numPr') is not None:
            return True
    return False


def strip_style_numbering(style_elem):
    removed = 0
    for pPr in style_elem.iter(w('pPr')):
        removed += remove_children_by_local_name(pPr, {'numPr'})
    return removed


def numbered_heading_text_prefix(text):
    stripped = (text or '').strip()
    if not stripped:
        return None
    patterns = [
        r'^(\d+(?:[\.．]\d+)*)(?:[\.．、\)]|\s+)\s*(?=\S)',
        r'^([IVXLCDM]+)(?:[\.．、\)]|\s+)\s*(?=\S)',
        r'^(第[一二三四五六七八九十百千\d]+[章节])\s*(?=\S)',
    ]
    for pattern in patterns:
        match = re.match(pattern, stripped, re.I)
        if match:
            return match.group(0)
    return None


def ensure_heading_no_number_styles(target_dir, role_style_ids):
    """Create no-number mirror styles for numbered heading styles.

    Use these only when the target heading text already contains a manual
    number prefix, e.g. "1 2D Human Pose Estimation".
    """
    styles_path = os.path.join(target_dir, 'word', 'styles.xml')
    if not os.path.exists(styles_path):
        return {}
    tree = ET.parse(styles_path)
    root = tree.getroot()
    target_by_id = build_style_id_index(root)
    no_number_ids = {}
    changed = False
    for role in HEADING_NUMBERED_ROLES:
        style_id = role_style_ids.get(role)
        if not style_id:
            continue
        style = target_by_id.get(style_id)
        if not style_has_numbering(style):
            continue
        no_num_id = f'{style_id}NoNum'
        no_num_style = clone_element(style)
        no_num_style.set(w('styleId'), no_num_id)
        name_elem = get_direct_child(no_num_style, w('name'))
        if name_elem is None:
            name_elem = ET.Element(w('name'))
            no_num_style.insert(0, name_elem)
        name_elem.set(w('val'), f"{ROLE_DISPLAY_NAMES.get(role, style_id)} NoNumber")
        strip_style_numbering(no_num_style)
        old = target_by_id.get(no_num_id)
        if old is not None:
            idx = list(root).index(old)
            root.remove(old)
            root.insert(idx, no_num_style)
        else:
            root.append(no_num_style)
        target_by_id[no_num_id] = no_num_style
        no_number_ids[role] = no_num_id
        changed = True
    if changed:
        write_xml(tree, styles_path)
        print(f"  Created heading no-number mirror styles: {no_number_ids}")
    return no_number_ids


def copy_or_create_role_styles(target_dir, template_dir, role_sources, text_rules=None):
    """Legacy wrapper: build a target-independent style spec, then install it."""
    text_rules = text_rules or {}
    template_styles_path = os.path.join(template_dir, 'word', 'styles.xml')
    target_styles_path = os.path.join(target_dir, 'word', 'styles.xml')
    template_tree = ET.parse(template_styles_path)
    template_root = template_tree.getroot()
    target_tree = ET.parse(target_styles_path)
    target_root = target_tree.getroot()
    template_by_id = build_style_id_index(template_root)
    doc_defaults = get_doc_defaults(template_root)
    template_language = detect_template_language(template_dir)
    target_by_id = build_style_id_index(target_root)
    copied = 0

    for role, style_id in ROLE_STYLE_IDS.items():
        source = role_sources.get(role) or role_sources.get('body')
        source_style = template_by_id.get(source.get('style_id')) if source else None
        role_style, _ = build_role_style_element(
            role, source_style, template_by_id, source, text_rules,
            doc_defaults=doc_defaults, language=template_language
        )

        old = target_by_id.get(style_id)
        if old is not None:
            idx = list(target_root).index(old)
            target_root.remove(old)
            target_root.insert(idx, role_style)
        else:
            target_root.append(role_style)
        target_by_id[style_id] = role_style
        copied += 1

    write_xml(target_tree, target_styles_path)
    print(f"  Installed {copied} role styles")
    return ROLE_STYLE_IDS.copy()


def load_role_map(path):
    if not path:
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    mapping = {}
    for item in data.get('paragraphs', []):
        if 'index' in item and item.get('role'):
            mapping[int(item['index'])] = item['role']
    return mapping


def role_map_warnings(role_map):
    warnings = []
    in_references = False
    for item in role_map:
        text = item.get('text', '')
        role = item.get('role')
        index = item.get('index')
        compact = re.sub(r'\s+', '', text or '')
        if re.fullmatch(r'参考文献[:：]?', compact) or compact.lower() in ('references', 'reference'):
            in_references = True
            if role != 'references_heading':
                warnings.append(
                    f"paragraph {index}: references heading mapped as {role!r}; expected 'references_heading'"
                )
        elif in_references and looks_like_reference_item(text) and role != 'reference_item':
            warnings.append(
                f"paragraph {index}: reference-zone item mapped as {role!r}; expected 'reference_item'"
            )
        if role in ('title', 'author', 'affiliation') and is_template_front_matter_noise(text):
            warnings.append(
                f"paragraph {index}: likely template/front-matter text mapped as {role!r}: {text[:60]!r}"
            )
        label_role = abstract_keyword_label_role(text)
        if label_role in ('abstract', 'english_abstract') and role not in ('abstract', 'english_abstract'):
            warnings.append(
                f"paragraph {index}: explicit abstract paragraph mapped as {role!r}; expected abstract role"
            )
        if label_role in ('keywords', 'english_keywords') and role not in ('keywords', 'english_keywords'):
            warnings.append(
                f"paragraph {index}: explicit keywords paragraph mapped as {role!r}; expected keywords role"
            )
        if re.match(r'^\s*(文章编号|中图分类号|文献标志码)', text) and role != 'metadata':
            warnings.append(
                f"paragraph {index}: explicit metadata paragraph mapped as {role!r}; expected metadata"
            )
        if role == 'title' and re.match(r'^\s*(\[\d+\]|［\d+］|\d+[\.\)]\s*)', text):
            warnings.append(
                f"paragraph {index}: numbered reference-like paragraph mapped as title"
            )
        if role == 'affiliation' and re.match(r'^\s*(中图分类号|文献标志码|引用格式)', text):
            warnings.append(
                f"paragraph {index}: classification/citation metadata mapped as affiliation"
            )
    return warnings


def print_role_map_warnings(role_map):
    warnings = role_map_warnings(role_map)
    if not warnings:
        return
    print("  WARNING: role-map preflight found suspicious mappings:")
    for warning in warnings[:30]:
        print(f"    - {warning}")
    if len(warnings) > 30:
        print(f"    - ... {len(warnings) - 30} more warning(s)")


def front_matter_role_refinements(role_map):
    changes = {}
    if not role_map:
        return changes
    stop_roles = {
        'abstract', 'english_abstract', 'keywords', 'english_keywords',
        'references_heading', 'reference_item',
    }
    title_seen = False
    for pos, item in enumerate(role_map[:20]):
        role = item.get('role')
        text = item.get('text', '')
        if role in ('title', 'english_title'):
            title_seen = True
            title_pos = pos
            continue
        if not title_seen:
            continue
        if pos - title_pos > 8:
            break
        if role in stop_roles:
            break
        next_item = role_map[pos + 1] if pos + 1 < len(role_map) else {}
        next_text = next_item.get('text', '')
        next_role = next_item.get('role')
        prev_item = role_map[pos - 1] if pos > 0 else {}
        prev_index = prev_item.get('index')
        prev_role = (changes.get(prev_index) or {}).get('role') or prev_item.get('role')
        if looks_like_email_contact_line(text) and role not in ('affiliation', 'english_affiliation', 'metadata'):
            changes[item['index']] = {
                'role': 'affiliation',
                'reason': 'front_matter_email_contact_line_not_title_or_author',
            }
        elif role in ('heading1', 'english_title', 'title', 'body') and looks_like_front_matter_author_line(text):
            changes[item['index']] = {
                'role': 'author',
                'reason': 'front_matter_position_author_between_title_and_affiliation_or_abstract',
            }
        elif (
            role in ('body', 'heading1', 'english_title', 'title')
            and prev_role in ('title', 'english_title', 'author')
            and (
                looks_like_affiliation_fallback(text)
                or looks_like_english_affiliation_line(text)
                or next_role in ('abstract', 'english_abstract')
                or re.match(r'^\s*(摘\s*要|Abstract)[:：]?', next_text, re.I)
            )
            and not looks_like_front_matter_author_line(text)
        ):
            changes[item['index']] = {
                'role': 'affiliation',
                'reason': 'front_matter_position_affiliation_between_author_and_abstract',
            }
    return changes


def apply_role_styles_to_document(target_dir, role_style_ids, clean_direct=True,
                                  role_map_out=None, role_map_in=None):
    """Classify target paragraphs by content and bind them to generated role styles."""
    doc_path = os.path.join(target_dir, 'word', 'document.xml')
    tree = ET.parse(doc_path)
    root = tree.getroot()
    heading_no_number_style_ids = ensure_heading_no_number_styles(target_dir, role_style_ids)
    forced_roles = load_role_map(role_map_in)
    if forced_roles:
        print(f"  Loaded role map input: {role_map_in} ({len(forced_roles)} paragraph roles)")
    in_references = False
    english_context = {'mode': None, 'step': 0}
    citation_context = {'open': False}
    visible_index = 0
    assigned = {}
    cleaned = {'paragraphs': 0, 'runs': 0}
    role_map = []
    paragraph_jobs = []

    for p in iter_body_paragraphs(root):
        text = get_text(p).strip()
        is_equation = paragraph_is_display_equation(p)
        if not text and not is_equation:
            continue
        if starts_english_front_matter_block(text):
            english_context = {'mode': 'front_matter', 'step': 0}
            citation_context['open'] = False
            continue
        if is_template_marker(text):
            continue
        if visible_index in forced_roles:
            role = forced_roles[visible_index]
            source = 'input'
            _, resolved_style_id, _ = resolve_role_style_id(role, role_style_ids)
            if resolved_style_id is None:
                raise ValueError(
                    f"role_map input uses unknown role {role!r} at paragraph {visible_index}. "
                    "Fix role_map.json or style_spec.json before formatting. "
                    "The role must have an exact style, a cross-language equivalent style, or body."
                )
        else:
            if role_map_in:
                raise ValueError(
                    f"role_map input is missing paragraph {visible_index}: {text[:80]!r}. "
                    "Locked role-map mode requires every non-empty body paragraph to be mapped."
                )
            role = 'equation' if is_equation else classify_paragraph(
                text, visible_index, in_references, english_context, citation_context
            )
            source = 'auto'
        if role == 'references_heading':
            in_references = True
        mapped_role = role or 'body'
        style_role, style_id, style_resolution = resolve_role_style_id(mapped_role, role_style_ids)
        if style_id is None:
            raise ValueError(
                f"no style is available for role {mapped_role!r} at paragraph {visible_index}; "
                "style_spec.json must include this role, a cross-language equivalent, or body."
            )
        manual_heading_prefix = None
        effective_style_id = style_id
        heading_numbering_conflict = False
        if (
            mapped_role in HEADING_NUMBERED_ROLES
            and style_role in HEADING_NUMBERED_ROLES
            and style_role in heading_no_number_style_ids
        ):
            manual_heading_prefix = numbered_heading_text_prefix(text)
            if manual_heading_prefix:
                effective_style_id = heading_no_number_style_ids[style_role]
                heading_numbering_conflict = True

        role_map.append({
            'index': visible_index,
            'role': mapped_role,
            'style_role': style_role,
            'style_id': effective_style_id,
            'original_style_id': style_id,
            'style_resolution': style_resolution,
            'source': source,
            'text': text[:160],
            'manual_heading_number_prefix': manual_heading_prefix,
            'heading_numbering_conflict_resolved': heading_numbering_conflict,
        })
        paragraph_jobs.append((p, mapped_role, effective_style_id))
        visible_index += 1

    if not role_map_in:
        refinements = front_matter_role_refinements(role_map)
        if refinements:
            print("  Front-matter role refinements:")
            for item_idx, (p, _mapped_role, _style_id) in enumerate(paragraph_jobs):
                visible = role_map[item_idx]['index']
                change = refinements.get(visible)
                if not change:
                    continue
                new_role = change['role']
                style_role, style_id, style_resolution = resolve_role_style_id(new_role, role_style_ids)
                if style_id is None:
                    continue
                old_role = role_map[item_idx]['role']
                manual_heading_prefix = None
                effective_style_id = style_id
                heading_numbering_conflict = False
                if (
                    new_role in HEADING_NUMBERED_ROLES
                    and style_role in HEADING_NUMBERED_ROLES
                    and style_role in heading_no_number_style_ids
                ):
                    manual_heading_prefix = numbered_heading_text_prefix(role_map[item_idx].get('text', ''))
                    if manual_heading_prefix:
                        effective_style_id = heading_no_number_style_ids[style_role]
                        heading_numbering_conflict = True
                role_map[item_idx]['role'] = new_role
                role_map[item_idx]['style_role'] = style_role
                role_map[item_idx]['style_id'] = effective_style_id
                role_map[item_idx]['original_style_id'] = style_id
                role_map[item_idx]['style_resolution'] = style_resolution
                role_map[item_idx]['source'] = 'auto_refined'
                role_map[item_idx]['refine_reason'] = change['reason']
                role_map[item_idx]['manual_heading_number_prefix'] = manual_heading_prefix
                role_map[item_idx]['heading_numbering_conflict_resolved'] = heading_numbering_conflict
                paragraph_jobs[item_idx] = (p, new_role, effective_style_id)
                print(f"    paragraph {visible}: {old_role!r} -> {new_role!r} ({change['reason']})")

    print_role_map_warnings(role_map)

    if role_map_in:
        extra_indexes = sorted(set(forced_roles) - {item['index'] for item in role_map})
        if extra_indexes:
            raise ValueError(
                f"role_map input contains paragraph indexes not found in target: {extra_indexes[:20]}"
            )

    for p, mapped_role, style_id in paragraph_jobs:
        if style_id:
            set_paragraph_style(p, style_id)
            assigned[mapped_role] = assigned.get(mapped_role, 0) + 1
        if clean_direct:
            p_clean, r_clean = clean_direct_formatting(p)
            cleaned['paragraphs'] += p_clean
            cleaned['runs'] += r_clean

    write_xml(tree, doc_path)
    if role_map_out:
        with open(role_map_out, 'w', encoding='utf-8') as f:
            json.dump({'paragraphs': role_map, 'assigned': assigned}, f, ensure_ascii=False, indent=2)
        print(f"  Wrote role map: {role_map_out}")
    print(f"  Role-bound paragraphs: {assigned}")
    if clean_direct:
        print(f"  Cleaned direct formatting: {cleaned}")
    return role_map


def remove_children_by_local_name(parent, names):
    removed = 0
    if parent is None:
        return removed
    for child in list(parent):
        if local_name(child.tag) in names:
            parent.remove(child)
            removed += 1
    return removed


def replace_child_by_local_name(parent, new_child, names):
    remove_children_by_local_name(parent, names)
    parent.append(new_child)


def clean_direct_formatting(p):
    """Remove paragraph/run direct formatting that overrides assigned styles."""
    p_removed = 0
    r_removed = 0
    pPr = get_direct_child(p, w('pPr'))
    if pPr is not None:
        p_removed += remove_children_by_local_name(pPr, DIRECT_PPR_TAGS)

    for run in p.iter(w('r')):
        rPr = get_direct_child(run, w('rPr'))
        if rPr is None:
            continue
        before = len(list(rPr))
        r_removed += remove_children_by_local_name(rPr, DIRECT_RPR_TAGS)
        if len(list(rPr)) == 0 and before > 0:
            run.remove(rPr)

    return p_removed, r_removed


def set_run_bold(run, value):
    rPr = get_or_add_child(run, w('rPr'), first=True)
    remove_children_by_local_name(rPr, {'b', 'bCs'})
    for name in ('b', 'bCs'):
        elem = ET.Element(w(name))
        elem.set(w('val'), '1' if value else '0')
        rPr.append(elem)


def set_run_plain_text(run, text):
    text_nodes = [node for node in run.iter(w('t'))]
    if not text_nodes:
        t = ET.SubElement(run, w('t'))
        t.text = text
        return
    text_nodes[0].text = text
    if text and (text[0].isspace() or text[-1].isspace()):
        text_nodes[0].set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    for extra in text_nodes[1:]:
        extra.text = ''


def apply_abstract_keyword_label_bold_to_paragraph(p):
    text = get_text(p)
    match = ABSTRACT_KEYWORD_LABEL_RE.match(text or '')
    if not match:
        return 0
    label_end = match.end()
    pos = 0
    changed = 0
    for child in list(p):
        if child.tag != w('r'):
            continue
        run = child
        run_txt = run_text(run)
        if not run_txt:
            continue
        start = pos
        end = pos + len(run_txt)
        pos = end
        if start >= label_end:
            set_run_bold(run, False)
            changed += 1
        elif end <= label_end:
            set_run_bold(run, True)
            changed += 1
        else:
            label_part = run_txt[: max(0, label_end - start)]
            content_part = run_txt[max(0, label_end - start):]
            if label_part:
                set_run_plain_text(run, label_part)
                set_run_bold(run, True)
                changed += 1
            if content_part:
                content_run = clone_element(run)
                set_run_plain_text(content_run, content_part)
                set_run_bold(content_run, False)
                p.insert(list(p).index(run) + 1, content_run)
                changed += 1
    return changed


def apply_abstract_keyword_label_bold(target_dir, role_map):
    if not role_map:
        return {'enabled': False, 'reason': 'role_map_empty'}
    role_by_index = {
        int(item['index']): item.get('role')
        for item in role_map
        if item.get('index') is not None
    }
    doc_path = os.path.join(target_dir, 'word', 'document.xml')
    tree = ET.parse(doc_path)
    root = tree.getroot()
    visible_index = 0
    stats = {
        'enabled': True,
        'paragraphs_checked': 0,
        'paragraphs_changed': 0,
        'runs_changed': 0,
    }
    for p in iter_body_paragraphs(root):
        text = get_text(p).strip()
        is_equation = paragraph_is_display_equation(p)
        if not text and not is_equation:
            continue
        role = role_by_index.get(visible_index)
        if role in ABSTRACT_KEYWORD_ROLES:
            stats['paragraphs_checked'] += 1
            changed = apply_abstract_keyword_label_bold_to_paragraph(p)
            if changed:
                stats['paragraphs_changed'] += 1
                stats['runs_changed'] += changed
        visible_index += 1
    if stats['runs_changed']:
        write_xml(tree, doc_path)
    print(f"  Applied abstract/keyword label bolding: {stats}")
    return stats


def should_apply_abstract_keyword_label_defaults(source_type=None):
    return normalize_format_source_type(source_type) in OOXML_FALLBACK_SOURCE_TYPES


def should_apply_chinese_metadata_tab_layout(source_type=None):
    """Apply only when explicit Chinese classification/doc-code labels exist.

    This repair is source-type agnostic: native DOCX templates can also contain
    manually spaced metadata rows that should not remain justified text.
    """
    return True


def should_apply_chinese_metadata_tab_defaults(source_type=None):
    return should_apply_chinese_metadata_tab_layout(source_type)


def extract_chinese_classification_metadata(text):
    raw = (text or '').replace('\u3000', ' ')
    if (
        not re.search(r'中\s*图\s*分\s*类\s*号', raw)
        and not re.search(r'文\s*献\s*标\s*志\s*码', raw)
    ):
        return None

    def clean_value(value):
        return re.sub(r'\s+', ' ', value or '').strip()

    ctc = None
    doc_code = None
    m_ctc = re.search(r'中\s*图\s*分\s*类\s*号\s*[:：]\s*(.*?)(?=\s*文\s*献\s*标\s*志\s*码\s*[:：]|$)', raw, re.S)
    if m_ctc:
        ctc = clean_value(m_ctc.group(1))
    m_doc = re.search(r'文\s*献\s*标\s*志\s*码\s*[:：]\s*(.*)$', raw, re.S)
    if m_doc:
        doc_code = clean_value(m_doc.group(1))
    if ctc is None and doc_code is None:
        return None
    return {
        'classification': f"中图分类号：{ctc or ''}",
        'doc_code': f"文献标志码：{doc_code or ''}",
        'has_classification': ctc is not None,
        'has_doc_code': doc_code is not None,
    }


def paragraph_direct_sectPr(p):
    pPr = get_direct_child(p, w('pPr'))
    return get_direct_child(pPr, w('sectPr')) if pPr is not None else None


def move_direct_sectPr(source_p, target_p):
    source_pPr = get_direct_child(source_p, w('pPr'))
    sectPr = get_direct_child(source_pPr, w('sectPr')) if source_pPr is not None else None
    if sectPr is None:
        return False
    source_pPr.remove(sectPr)
    target_pPr = get_or_add_child(target_p, w('pPr'), first=True)
    remove_children_by_local_name(target_pPr, {'sectPr'})
    target_pPr.append(sectPr)
    return True


def set_paragraph_plain_text_with_tab(p, left_text, right_text):
    pPr = get_direct_child(p, w('pPr'))
    for child in list(p):
        if child is not pPr:
            p.remove(child)
    if pPr is not None and list(p)[:1] != [pPr]:
        p.remove(pPr)
        p.insert(0, pPr)
    p.append(make_text_run(left_text))
    p.append(make_tab_run())
    p.append(make_text_run(right_text))


def apply_metadata_right_tab_to_paragraph(p, tab_pos_twips):
    pPr = get_or_add_child(p, w('pPr'), first=True)
    remove_children_by_local_name(pPr, {'jc', 'tabs'})
    tabs = ET.Element(w('tabs'))
    tab = ET.SubElement(tabs, w('tab'))
    tab.set(w('val'), 'right')
    tab.set(w('pos'), str(int(tab_pos_twips)))
    pPr.append(tabs)
    jc = ET.Element(w('jc'))
    jc.set(w('val'), 'left')
    pPr.append(jc)


def apply_chinese_metadata_tab_layout(target_dir):
    """Normalize Chinese classification/doc-code metadata to left + right-tab layout."""
    doc_path = os.path.join(target_dir, 'word', 'document.xml')
    tree = ET.parse(doc_path)
    root = tree.getroot()
    body = root.find(w('body'))
    if body is None:
        return {'enabled': False, 'reason': 'target_has_no_body'}

    sectPrs = list(root.iter(w('sectPr')))
    sect_infos = [sectPr_to_info(sectPr) for sectPr in sectPrs] or [{}]
    current_info = sect_infos[0] if sect_infos else {}
    section_index = 0
    paragraphs = []
    for child in list(body):
        if child.tag == w('p'):
            paragraphs.append((child, current_info))
        if child.tag == w('p') and paragraph_direct_sectPr(child) is not None:
            section_index += 1
            if section_index < len(sect_infos):
                current_info = sect_infos[section_index]

    stats = {
        'enabled': True,
        'paragraphs_checked': 0,
        'paragraphs_changed': 0,
        'adjacent_pairs_merged': 0,
        'section_breaks_moved': 0,
        'tab_positions_twips': [],
    }
    changed = False
    idx = 0
    while idx < len(paragraphs):
        p, sect_info = paragraphs[idx]
        info = extract_chinese_classification_metadata(get_text(p))
        if not info:
            idx += 1
            continue
        stats['paragraphs_checked'] += 1
        if info.get('has_classification') and not info.get('has_doc_code') and idx + 1 < len(paragraphs):
            next_p, _next_info = paragraphs[idx + 1]
            next_info = extract_chinese_classification_metadata(get_text(next_p))
            if next_info and next_info.get('has_doc_code') and not next_info.get('has_classification'):
                if move_direct_sectPr(next_p, p):
                    stats['section_breaks_moved'] += 1
                body.remove(next_p)
                paragraphs.pop(idx + 1)
                info['doc_code'] = next_info['doc_code']
                info['has_doc_code'] = True
                stats['adjacent_pairs_merged'] += 1
                changed = True
        if info.get('has_classification') and info.get('has_doc_code'):
            tab_pos = section_page_text_width_twips(sect_info)
            set_paragraph_plain_text_with_tab(p, info['classification'], info['doc_code'])
            apply_metadata_right_tab_to_paragraph(p, tab_pos)
            stats['paragraphs_changed'] += 1
            stats['tab_positions_twips'].append(tab_pos)
            changed = True
        idx += 1

    if changed:
        write_xml(tree, doc_path)
    print(f"  Applied Chinese metadata tab layout: {stats}")
    return stats


STYLE_CONFORMANCE_RPR_TAGS = {
    'rFonts', 'sz', 'szCs', 'b', 'bCs', 'i', 'iCs',
    'color', 'u', 'spacing', 'position', 'lang',
}

STYLE_CONFORMANCE_PPR_TAGS = {
    'jc', 'spacing', 'ind', 'contextualSpacing', 'keepNext',
    'keepLines', 'widowControl', 'outlineLvl', 'textAlignment',
    'tabs', 'pBdr', 'shd', 'framePr', 'snapToGrid',
}


def replace_selected_children_from_source(target_parent, source_parent, tag_names):
    if target_parent is None or source_parent is None:
        return 0
    changed = 0
    source_names = {
        local_name(source_child.tag)
        for source_child in source_parent
        if local_name(source_child.tag) in tag_names
    }
    for name in tag_names - source_names:
        changed += remove_children_by_local_name(target_parent, {name})
    for source_child in source_parent:
        name = local_name(source_child.tag)
        if name not in tag_names:
            continue
        current = child_by_local_name(target_parent, name)
        if xml_string(current) == xml_string(source_child):
            continue
        remove_children_by_local_name(target_parent, {name})
        target_parent.append(clone_element(source_child))
        changed += 1
    return changed


def repair_installed_role_styles(target_dir, style_spec):
    stats = {
        'styles_checked': 0,
        'style_repairs': 0,
        'missing_styles': [],
    }
    if not style_spec:
        return stats
    styles_path = os.path.join(target_dir, 'word', 'styles.xml')
    if not os.path.exists(styles_path):
        stats['missing_styles'].append('__styles_xml_missing__')
        return stats
    tree = ET.parse(styles_path)
    root = tree.getroot()
    style_by_id = build_style_id_index(root)
    for role, role_spec in (style_spec.get('roles') or {}).items():
        if role not in ROLE_STYLE_IDS:
            continue
        style_id = role_spec.get('style_id') or ROLE_STYLE_IDS.get(role)
        style_elem = style_by_id.get(style_id)
        stats['styles_checked'] += 1
        if style_elem is None:
            stats['missing_styles'].append(style_id)
            continue
        repairs = 0
        expected_rPr = xml_to_element(role_spec.get('rPr_xml'))
        if expected_rPr is not None:
            target_rPr = get_or_add_child(style_elem, w('rPr'))
            repairs += replace_selected_children_from_source(
                target_rPr, expected_rPr, STYLE_CONFORMANCE_RPR_TAGS
            )
        expected_pPr = xml_to_element(role_spec.get('pPr_xml'))
        if expected_pPr is not None:
            target_pPr = get_or_add_child(style_elem, w('pPr'))
            repairs += replace_selected_children_from_source(
                target_pPr, expected_pPr, STYLE_CONFORMANCE_PPR_TAGS
            )
            expected_pPr_rPr = child_by_local_name(expected_pPr, 'rPr')
            if expected_pPr_rPr is not None:
                target_pPr_rPr = get_or_add_child(target_pPr, w('rPr'))
                repairs += replace_selected_children_from_source(
                    target_pPr_rPr, expected_pPr_rPr, STYLE_CONFORMANCE_RPR_TAGS
                )
            else:
                target_pPr_rPr = child_by_local_name(target_pPr, 'rPr')
                repairs += remove_children_by_local_name(target_pPr_rPr, STYLE_CONFORMANCE_RPR_TAGS)
                if target_pPr_rPr is not None and len(list(target_pPr_rPr)) == 0:
                    target_pPr.remove(target_pPr_rPr)
        if repairs:
            stats['style_repairs'] += repairs
    if stats['style_repairs']:
        write_xml(tree, styles_path)
    return stats


def iter_role_visible_paragraphs(root):
    visible_index = 0
    for p in iter_body_paragraphs(root):
        text = get_text(p).strip()
        is_equation = paragraph_is_display_equation(p)
        if not text and not is_equation:
            continue
        if starts_english_front_matter_block(text):
            continue
        if is_template_marker(text):
            continue
        yield visible_index, p
        visible_index += 1


def paragraph_direct_format_counts(p):
    p_count = 0
    r_count = 0
    pPr = get_direct_child(p, w('pPr'))
    if pPr is not None:
        p_count = sum(1 for child in pPr if local_name(child.tag) in DIRECT_PPR_TAGS)
    for run in p.iter(w('r')):
        rPr = get_direct_child(run, w('rPr'))
        if rPr is not None:
            r_count += sum(1 for child in rPr if local_name(child.tag) in DIRECT_RPR_TAGS)
    return p_count, r_count


def audit_role_paragraph_conformance(root, role_map):
    role_by_index = {int(item['index']): item for item in role_map or [] if 'index' in item}
    result = {
        'paragraphs_checked': 0,
        'style_mismatches': [],
        'direct_ppr_overrides': 0,
        'direct_rpr_overrides': 0,
    }
    for visible_index, p in iter_role_visible_paragraphs(root):
        item = role_by_index.get(visible_index)
        if not item:
            continue
        expected_style_id = item.get('style_id')
        actual_style_id = paragraph_style_id(p)
        result['paragraphs_checked'] += 1
        if expected_style_id and actual_style_id != expected_style_id:
            result['style_mismatches'].append({
                'index': visible_index,
                'expected': expected_style_id,
                'actual': actual_style_id,
                'role': item.get('role'),
                'text': item.get('text', '')[:80],
            })
        p_count, r_count = paragraph_direct_format_counts(p)
        result['direct_ppr_overrides'] += p_count
        result['direct_rpr_overrides'] += r_count
    return result


def enforce_role_format_conformance(target_dir, style_spec, role_map, clean_direct=True):
    """Audit and repair deterministic role/style formatting mismatches.

    This pass runs after role binding and direct-format cleanup, before surfaces
    such as reference numbering and equation tabs intentionally add formatting.
    """
    stats = {
        'enabled': bool(style_spec and role_map),
        'ok': True,
        'style_repairs': {},
        'paragraph_repairs': {
            'style_mismatches_repaired': 0,
            'direct_ppr_removed': 0,
            'direct_rpr_removed': 0,
        },
        'before': {},
        'after': {},
    }
    if not stats['enabled']:
        return stats
    stats['style_repairs'] = repair_installed_role_styles(target_dir, style_spec)
    doc_path = os.path.join(target_dir, 'word', 'document.xml')
    tree = ET.parse(doc_path)
    root = tree.getroot()
    stats['before'] = audit_role_paragraph_conformance(root, role_map)
    role_by_index = {int(item['index']): item for item in role_map or [] if 'index' in item}
    changed = False
    for visible_index, p in iter_role_visible_paragraphs(root):
        item = role_by_index.get(visible_index)
        if not item:
            continue
        expected_style_id = item.get('style_id')
        if expected_style_id and paragraph_style_id(p) != expected_style_id:
            set_paragraph_style(p, expected_style_id)
            stats['paragraph_repairs']['style_mismatches_repaired'] += 1
            changed = True
        if clean_direct:
            p_removed, r_removed = clean_direct_formatting(p)
            if p_removed or r_removed:
                stats['paragraph_repairs']['direct_ppr_removed'] += p_removed
                stats['paragraph_repairs']['direct_rpr_removed'] += r_removed
                changed = True
    if changed:
        write_xml(tree, doc_path)
        tree = ET.parse(doc_path)
        root = tree.getroot()
    stats['after'] = audit_role_paragraph_conformance(root, role_map)
    stats['ok'] = (
        not stats['style_repairs'].get('missing_styles')
        and not stats['after'].get('style_mismatches')
        and (
            not clean_direct
            or (
                stats['after'].get('direct_ppr_overrides', 0) == 0
                and stats['after'].get('direct_rpr_overrides', 0) == 0
            )
        )
    )
    return stats


def normalize_text_for_rules(text):
    return re.sub(r'\s+', '', text or '').lower()


def looks_like_structure_sequence_instruction(text):
    stripped = (text or '').strip()
    if not stripped:
        return False
    return bool(re.search(
        r'(organized|arranged|presented)\s+(?:in\s+the\s+)?sequence|'
        r'(organized|arranged|presented)\s+as\s+follows|'
        r'顺序(?:为|如下)|按(?:以下|下列)?.{0,12}顺序|'
        r'(title,\s*authors?,\s*affiliations?|main\s+references?,\s*tables?,\s*figure\s+legends?)',
        stripped,
        re.I,
    ))


def role_from_rule_text(text):
    if starts_english_front_matter_block(text):
        return None
    if looks_like_structure_sequence_instruction(text):
        return None
    stripped = (text or '').strip()
    prefix_checks = [
        ('abstract', r'^\s*摘\s*要\s*[:：]'),
        ('keywords', r'^\s*(关键词|关键字)\s*[:：]'),
        ('english_abstract', r'^\s*Abstract\s*[:：]'),
        ('english_keywords', r'^\s*(Key\s*words?|Keywords?)\s*[:：]'),
    ]
    for role, pattern in prefix_checks:
        if re.match(pattern, stripped, re.I):
            return role
    normalized = normalize_text_for_rules(text)
    if not normalized:
        return None
    checks = [
        ('references_heading', ['参考文献标题', 'referencesheading']),
        ('reference_item', ['参考文献', 'references', '文献']),
        ('figure_caption', ['图题', '图注', 'figurecaption']),
        ('table_caption', ['表题', '表注', 'tablecaption']),
        ('english_keywords', ['英文关键词', 'englishkeywords']),
        ('english_abstract', ['英文摘要', 'englishabstract']),
        ('english_title', ['英文题名', '英文标题', 'englishtitle']),
        ('english_author', ['英文作者', 'englishauthor']),
        ('english_affiliation', ['英文单位', '英文机构', 'englishaffiliation']),
        ('metadata', ['中图分类号', '文献标志码', '文章编号']),
        ('citation_format', ['引用格式', 'citationformat']),
        ('keywords', ['关键词', '关键字', 'keywords']),
        ('abstract', ['摘要', 'abstract']),
        ('heading1', ['一级标题', '1级标题', 'heading1']),
        ('heading2', ['二级标题', '2级标题', 'heading2']),
        ('heading3', ['三级标题', '3级标题', 'heading3']),
        ('title', ['题名', '标题', '论文题目', 'title']),
        ('author', ['作者', 'author']),
        ('affiliation', ['单位', '机构', 'affiliation']),
        ('body', ['正文', '文章正文', 'body', 'maintext']),
    ]
    for role, keys in checks:
        if any(key.lower() in normalized for key in keys):
            return role
    return None


def text_rule_format_segment(text, role=None):
    """Keep the explicit formatting phrase and avoid long sample prose."""
    stripped = (text or '').strip()
    if not stripped:
        return ''
    role = role or role_from_rule_text(stripped)
    if role in ('abstract', 'keywords', 'english_abstract', 'english_keywords'):
        match = re.match(
            r'^\s*(摘\s*要|关键词|关键字|Abstract|Key\s*words?|Keywords?)\s*[:：]\s*([^。；;\n]{0,80})',
            stripped,
            re.I,
        )
        if match:
            return match.group(2) or stripped[:120]
    if role == 'body':
        match = re.search(r'(文章正文|正文)[^。；;\n]{0,80}', stripped, re.I)
        if match:
            return match.group(0)
    return stripped[:160]


def parse_size_from_text(text):
    for name, half_points in SIZE_MAP.items():
        if name in text:
            return str(half_points)
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


def parse_fonts_from_text(text):
    fonts = {}
    for font in FONT_WORDS:
        if font.lower() in text.lower():
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


def parse_alignment_from_text(text):
    if re.search(r'居中|居中对齐|align(?:ed|ment)?\s*[:=]?\s*center|center(?:ed)?\s+align', text, re.I):
        return 'center'
    if re.search(r'两端对齐|align(?:ed|ment)?\s*[:=]?\s*justify|justified', text, re.I):
        return 'both'
    if re.search(r'右对齐|居右|align(?:ed|ment)?\s*[:=]?\s*right|right(?:-|\s+)?align(?:ed|ment)?', text, re.I):
        return 'right'
    if re.search(r'左对齐|居左|align(?:ed|ment)?\s*[:=]?\s*left|left(?:-|\s+)?align(?:ed|ment)?', text, re.I):
        return 'left'
    return None


def parse_bold_from_text(text):
    if re.search(r'不加粗|非加粗|not\s+bold', text, re.I):
        return False
    if re.search(r'加粗|bold', text, re.I):
        return True
    return None


def parse_line_spacing_from_text(text):
    match = re.search(r'(?:固定值|exact(?:ly)?)\s*(\d+(?:\.\d+)?)\s*(?:磅|pt)', text, re.I)
    if match:
        return {'line': str(int(round(float(match.group(1)) * 20))), 'lineRule': 'exact'}
    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:倍行距|倍)', text)
    if match:
        return {'line': str(int(round(float(match.group(1)) * 240))), 'lineRule': 'auto'}
    if re.search(r'1\.?5\s*(?:倍行距|倍)|一倍半', text):
        return {'line': '360', 'lineRule': 'auto'}
    if re.search(r'double[-\s]?spaced|double\s+line(?:\s+spacing)?|2(?:\.0)?\s*(?:line\s+spacing|spacing)', text, re.I):
        return {'line': '480', 'lineRule': 'auto'}
    if re.search(r'默认单倍行距|默认行距|use\s+default\s+single', text, re.I):
        return {'line': '0', 'lineRule': 'auto'}
    if re.search(r'单倍行距|single[-\s]?spaced|single\s+line', text, re.I):
        return {'line': '240', 'lineRule': 'auto'}
    return {}


def parse_spacing_before_after_from_text(text):
    spacing = {}
    before = re.search(r'(?:段前|before)\s*(\d+(?:\.\d+)?)\s*(?:磅|pt)', text, re.I)
    after = re.search(r'(?:段后|after)\s*(\d+(?:\.\d+)?)\s*(?:磅|pt)', text, re.I)
    if before:
        spacing['before'] = str(int(round(float(before.group(1)) * 20)))
    if after:
        spacing['after'] = str(int(round(float(after.group(1)) * 20)))
    return spacing


def parse_indent_from_text(text):
    if re.search(r'悬挂缩进\s*2\s*(?:字符|字)', text):
        return dict(DEFAULT_REFERENCE_INDENT)
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


def extract_template_text_rules(doc_dir):
    """Extract prose formatting rules from template body text before style import."""
    doc_path = os.path.join(doc_dir, 'word', 'document.xml')
    tree = ET.parse(doc_path)
    root = tree.getroot()
    rules = {}
    for p in iter_body_paragraphs(root):
        text = get_text(p).strip()
        if looks_like_non_format_instruction_text(text):
            continue
        global_rule = parse_global_manuscript_format_rule(text)
        if global_rule:
            apply_global_manuscript_rule(
                rules,
                global_rule,
                source='template_text_rules',
                format_text=text_rule_format_segment(text),
            )
        role = role_from_rule_text(text)
        if not role:
            continue
        format_text = text_rule_format_segment(text, role=role)
        rule = {}
        size = parse_size_from_text(format_text)
        fonts = parse_fonts_from_text(format_text)
        align = parse_alignment_from_text(format_text)
        bold = parse_bold_from_text(format_text)
        line_spacing = parse_line_spacing_from_text(format_text)
        paragraph_spacing = parse_spacing_before_after_from_text(format_text)
        indent = parse_indent_from_text(format_text)
        if size:
            rule['size'] = size
        if fonts:
            rule['fonts'] = fonts
        if align:
            rule['align'] = align
        if bold is not None:
            rule['bold'] = bold
        spacing = {}
        spacing.update(line_spacing)
        spacing.update(paragraph_spacing)
        if spacing:
            rule['spacing'] = spacing
        if indent:
            rule['indent'] = indent
        if rule:
            merge_rule_into_role(
                rules,
                role,
                rule,
                source='template_text_rules',
                format_text=format_text,
            )
    complete_paired_front_matter_text_rules(rules)
    return rules


def complete_paired_front_matter_text_rules(rules):
    """Propagate only font/size between paired abstract and keyword rules."""
    pair_specs = (
        ('abstract', 'keywords'),
        ('english_abstract', 'english_keywords'),
    )
    for source_role, target_role in pair_specs:
        source_rule = rules.get(source_role) or {}
        target_rule = rules.get(target_role) or {}
        if not source_rule:
            continue
        copied = {}
        for key in ('size', 'fonts'):
            if key in source_rule and key not in target_rule:
                copied[key] = dict(source_rule[key]) if isinstance(source_rule[key], dict) else source_rule[key]
        if not copied:
            continue
        current = rules.setdefault(target_role, {})
        current.update(copied)
        current.setdefault('source', 'template_text_rules')
        current.setdefault('confidence', 'explicit')
        current.setdefault('_format_text', f'inherited {",".join(copied)} from {source_role} text rule')


def looks_like_non_format_instruction_text(text):
    stripped = (text or '').strip()
    if not stripped:
        return False
    return bool(re.search(
        r'(right-click|left-click|double-click|click\s+on|select\s+["“]?Edit\s+Alt\s+Text|'
        r'Alt\s+Text|text\s+box(?:es)?|Description\s+text\s+box|Title\s+text\s+box|'
        r'In\s+the\s+["“]?Title["”]?\s+and\s+["“]?Description["”]?|'
        r'automatic\s+page\s+numbering|field\s+functions?|table\s+function|spreadsheets?|'
        r'ORCID|space\s+bar|tab\s+stops?|Do\s+not\s+use|'
        r'for\s+pages\s+other\s+than\s+the\s+first\s+page|start\s+at\s+the\s+top\s+of\s+the\s+page|'
        r'continue\s+in\s+double-column|double-column\s+format|single-column\s+format|'
        r'use\s+the\s+header|use\s+the\s+footer|headers?\s+and\s+footers?|'
        r'page\s+margins?|column\s+width|column\s+spacing|paper\s+size|'
        r'include\s+headers?|include\s+footers?|page\s+numbers?|'
        r'in\s+your\s+submission|your\s+submission|will\s+be\s+added|'
        r'paper\s+submission|manuscript\s+submission|template\s+instructions?|'
        r'place\s+(?:tables?|figures?|images?)|tables?/figures?/images?|'
        r'as\s+close\s+to\s+the\s+reference\s+as\s+possible|'
        r'insert\s+(?:tables?|figures?|images?)|'
        r'position\s+(?:tables?|figures?|images?)|'
        r'caption\s+(?:should|must)|'
        r'figures?\s+and\s+tables?\s+should|tables?\s+and\s+figures?\s+should)',
        stripped,
        re.I
    ))


def merge_text_rules(template_rules, user_rules):
    """User rules override template prose rules."""
    merged = {}
    for role, rule in (template_rules or {}).items():
        merged[role] = dict(rule or {})
    for role, rule in (user_rules or {}).items():
        if role not in ROLE_STYLE_IDS:
            continue
        rule = normalize_user_rule(rule or {})
        current = merged.setdefault(role, {})
        for key, value in (rule or {}).items():
            if isinstance(value, dict) and isinstance(current.get(key), dict):
                current[key].update(value)
            else:
                current[key] = value
    return merged


VISUAL_ONLY_RULE_ALLOWED_KEYS = {
    'align',
    'source',
    'confidence',
    'visual_supplement',
    'visual_granularity',
    'caption_position',
    'bilingual',
}

EXPLICIT_TEXT_RULE_KEYS = {
    'size', 'font_size', 'fontSize', 'fonts', 'font', 'rPr', 'rPr_xml', 'style_xml',
    'bold', 'italic', 'underline', 'color', 'highlight', 'strike', 'caps',
    'smallCaps', 'spacing', 'line_spacing', 'lineSpacing', 'indent', 'ind',
    'indentation', 'align', 'alignment', 'paragraph', 'tabs', 'numbering',
    'outline', 'keepNext', 'keepLines', 'pageBreakBefore', 'caption_position',
    'bilingual',
}
VISUAL_RULE_SOURCE_MARKERS = (
    'visual', 'visual_role_alignment', 'pdf_visual', 'pdf_visual_inference',
    'image_visual', 'screenshot_visual', 'geometry', 'rendered_preview',
)


def rule_is_explicit_text_format(rule):
    source = str((rule or {}).get('source') or '').lower()
    confidence = str((rule or {}).get('confidence') or '').lower()
    if any(marker in source for marker in VISUAL_RULE_SOURCE_MARKERS):
        return False
    has_explicit_field = any(
        key in (rule or {}) and (rule or {}).get(key) not in (None, '', {}, [])
        for key in EXPLICIT_TEXT_RULE_KEYS
    )
    return (
        source in ('user_rules', 'text_rules', 'pdf_text_rules', 'template_text_rules')
        or confidence in ('high', 'explicit', 'locked')
        or has_explicit_field
    )


def normalize_visual_alignment_rule(role, rule):
    rule = dict(rule or {})
    align = str(rule.get('align') or rule.get('alignment') or '').lower()
    if role in VISUAL_CENTER_DEFAULT_ROLES and align in ('both', 'justify', 'justified', 'distribute'):
        rule['align'] = 'center'
        rule['visual_alignment_normalized'] = 'justify_to_center_for_front_matter'
    return rule


def sanitize_visual_only_rules(rules, source_type):
    """For non-DOCX evidence, keep only explicit text rules; visual data may only select fallback columns."""
    source_type = normalize_format_source_type(source_type)
    if source_type not in WEAK_EXTERNAL_STYLE_SOURCE_TYPES:
        return rules or {}
    sanitized = {}
    for role, rule in (rules or {}).items():
        if role not in ROLE_STYLE_IDS:
            continue
        normalized = normalize_user_rule(rule or {})
        if rule_is_explicit_text_format(normalized):
            sanitized[role] = normalized
            continue
        if source_type in NON_DOCX_TEXT_ONLY_SOURCE_TYPES:
            continue
        normalized = normalize_visual_alignment_rule(role, normalized)
        kept = {
            key: value
            for key, value in normalized.items()
            if key in VISUAL_ONLY_RULE_ALLOWED_KEYS
        }
        if kept:
            kept.setdefault('source', normalized.get('source') or 'visual_role_alignment')
            kept.setdefault('confidence', normalized.get('confidence') or 'low')
            sanitized[role] = kept
    return sanitized


def rules_schema_diagnostics(raw_rules, normalized_rules):
    diagnostics = {
        'enabled': bool(raw_rules),
        'valid_roles': [],
        'invalid_roles': [],
        'normalized_fields': {},
        'warnings': [],
    }
    for role, rule in (raw_rules or {}).items():
        if role not in ROLE_STYLE_IDS:
            diagnostics['invalid_roles'].append(role)
            diagnostics['warnings'].append(f'ignored unsupported rules.json role: {role}')
            continue
        diagnostics['valid_roles'].append(role)
        normalized = (normalized_rules or {}).get(role) or {}
        accepted = normalized.get('_ooxml_summary_rule_accepted') or normalized.get('_normalized_from') or []
        if accepted:
            diagnostics['normalized_fields'][role] = sorted(set(accepted))
        useful_keys = {
            key for key, value in normalized.items()
            if key in EXPLICIT_TEXT_RULE_KEYS and value not in (None, '', {}, [])
        }
        if not useful_keys:
            diagnostics['warnings'].append(
                f'rules.json role {role} did not contain recognized formatting keys after normalization'
            )
    return diagnostics


def load_user_rules(path):
    if not path:
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if 'roles' in data:
        data = data['roles']
    return data


def load_rules_metadata(path):
    if not path:
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    metadata = {}
    for key in ('_meta', 'meta', 'metadata'):
        if isinstance(data.get(key), dict):
            metadata.update(data.get(key))
    source_type = (
        data.get('source_type')
        or data.get('sourceType')
        or data.get('evidence_source')
        or data.get('evidenceSource')
    )
    if source_type:
        metadata['source_type'] = source_type
    for key in (
        'fallback_columns',
        'fallback_language',
        'columns',
        'column_count',
        'detected_columns',
        'source_column_detection',
        'explicit_column_rule',
        'column_rule_explicit',
        'fallback_columns_explicit',
        'explicit_fallback_columns',
        'explicit_columns',
        'user_column_rule',
        'website_explicit_column_rule',
        'column_rule_text',
        'column_instruction_text',
        'explicit_column_text',
        'website_column_text',
        'user_column_text',
        'column_source',
        'column_detection_source',
        'fallback_columns_source',
        'column_route',
        'column_method',
        'non_docx_standard_fallback',
        'non_docx_text_only_route',
        'original_source_type',
        'original_extension',
        'format_source_extension',
        'non_docx_source_kind',
        'pdf_text_rule_route',
        'text_rule_source_only',
        'source_text',
        'raw_text',
        'guide_text',
        'website_text',
        'extracted_text',
        'format_text',
    ):
        if key in data:
            metadata[key] = data.get(key)
    for key in ('_meta', 'meta', 'metadata'):
        meta = data.get(key)
        if isinstance(meta, dict):
            for subkey in (
                'fallback_columns',
                'fallback_language',
                'columns',
                'column_count',
                'detected_columns',
                'source_column_detection',
                'explicit_column_rule',
                'column_rule_explicit',
                'fallback_columns_explicit',
                'explicit_fallback_columns',
                'explicit_columns',
                'user_column_rule',
                'website_explicit_column_rule',
                'column_rule_text',
                'column_instruction_text',
                'explicit_column_text',
                'website_column_text',
                'user_column_text',
                'column_source',
                'column_detection_source',
                'fallback_columns_source',
                'column_route',
                'column_method',
                'non_docx_standard_fallback',
                'non_docx_text_only_route',
                'original_source_type',
                'original_extension',
                'format_source_extension',
                'non_docx_source_kind',
                'pdf_text_rule_route',
                'text_rule_source_only',
                'source_text',
                'raw_text',
                'guide_text',
                'website_text',
                'extracted_text',
                'format_text',
            ):
                if subkey in meta:
                    metadata[subkey] = meta.get(subkey)
    return metadata


def split_source_text_sentences(text):
    text = re.sub(r'\s+', ' ', str(text or '')).strip()
    if not text:
        return []
    parts = re.split(r'(?<=[。；;.!?])\s+|\n+', text)
    return [part.strip() for part in parts if part.strip()]


def extract_text_rules_from_source_metadata(metadata, source='metadata_text_rules'):
    """Extract explicit rules from website/PDF/OCR metadata raw text fields."""
    metadata = metadata or {}
    text_values = []
    for key in ('source_text', 'raw_text', 'guide_text', 'website_text', 'extracted_text', 'format_text'):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            text_values.append(value)
    if not text_values:
        return {}
    rules = {}
    for text_value in text_values:
        for sentence in split_source_text_sentences(text_value):
            if looks_like_non_format_instruction_text(sentence):
                continue
            global_rule = parse_global_manuscript_format_rule(sentence)
            if global_rule:
                apply_global_manuscript_rule(
                    rules,
                    global_rule,
                    source=source,
                    format_text=sentence[:240],
                )
            role = role_from_rule_text(sentence)
            if not role:
                continue
            format_text = text_rule_format_segment(sentence, role=role)
            rule = {}
            size = parse_size_from_text(format_text)
            fonts = parse_fonts_from_text(format_text)
            align = parse_alignment_from_text(format_text)
            bold = parse_bold_from_text(format_text)
            spacing = {}
            spacing.update(parse_line_spacing_from_text(format_text))
            spacing.update(parse_spacing_before_after_from_text(format_text))
            indent = parse_indent_from_text(format_text)
            if size:
                rule['size'] = size
            if fonts:
                rule['fonts'] = fonts
            if align:
                rule['align'] = align
            if bold is not None:
                rule['bold'] = bold
            if spacing:
                rule['spacing'] = spacing
            if indent:
                rule['indent'] = indent
            merge_rule_into_role(rules, role, rule, source=source, format_text=format_text)
    complete_paired_front_matter_text_rules(rules)
    return rules


def load_rules_postprocess_operations(path):
    if not path:
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    candidates = []
    for key in ('postprocess_operations', 'postprocess_ops', 'explicit_postprocess_operations'):
        candidates.extend(postprocess_candidates_from_value(data.get(key), source_key=key))
    for meta_key in ('_meta', 'meta', 'metadata'):
        meta = data.get(meta_key)
        if not isinstance(meta, dict):
            continue
        for key in ('postprocess_operations', 'postprocess_ops', 'explicit_postprocess_operations'):
            candidates.extend(postprocess_candidates_from_value(meta.get(key), source_key=f'{meta_key}.{key}'))
        structural = meta.get('structural_rules')
        if isinstance(structural, dict):
            candidates.extend(infer_postprocess_operations_from_structural_rules(structural))
    return normalize_postprocess_operations(candidates)


POSTPROCESS_SHORTHAND_MAP = {
    'tables_after_references': {'type': 'move_tables_after_references', 'include_caption': True},
    'figures_after_references': {'type': 'move_figures_after_references', 'include_caption': True},
    'citation_markers_italic_parentheses': {'type': 'normalize_body_citations', 'to': 'parentheses', 'italic': True},
    'body_citation_markers_italic_parentheses': {'type': 'normalize_body_citations', 'to': 'parentheses', 'italic': True},
    'intext_citation_markers_italic_parentheses': {'type': 'normalize_body_citations', 'to': 'parentheses', 'italic': True},
    'inttext_citation_markers_italic_parentheses': {'type': 'normalize_body_citations', 'to': 'parentheses', 'italic': True},
    'figure_caption_first_sentence_bold': {'type': 'normalize_figure_captions', 'first_sentence_bold': True},
    'table_caption_first_sentence_bold': {'type': 'normalize_table_captions', 'first_sentence_bold': True},
}


def postprocess_candidates_from_value(value, source_key='postprocess_operations'):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        if value.get('type') or value.get('operation'):
            op = dict(value)
            op.setdefault('_config_warning', f'{source_key} should normally be an array; accepted single operation object')
            return [op]
        candidates = []
        for key, enabled in value.items():
            if not enabled:
                continue
            template = POSTPROCESS_SHORTHAND_MAP.get(key)
            if template:
                op = dict(template)
                op['_config_warning'] = (
                    f'{source_key}.{key} used shorthand object form; prefer an operations array with explicit type'
                )
                candidates.append(op)
            else:
                candidates.append({
                    'type': f'unsupported_shorthand:{key}',
                    'enabled': True,
                    '_config_error': f'unrecognized postprocess shorthand {source_key}.{key}',
                })
        return candidates
    return [{
        'type': 'unsupported_postprocess_config',
        'enabled': True,
        '_config_error': f'{source_key} must be an array, object shorthand, or operation object',
    }]


def normalize_postprocess_operations(operations):
    normalized = []
    seen = set()
    supported = {
        'move_tables_after_references',
        'move_figures_after_references',
        'normalize_body_citations',
        'normalize_reference_prefixes',
        'normalize_figure_captions',
        'normalize_table_captions',
    }
    for op in operations or []:
        if not isinstance(op, dict):
            clean = {
                'type': 'unsupported_postprocess_config',
                'enabled': True,
                '_config_error': 'postprocess operation entries must be objects with explicit type',
            }
            key = json.dumps(clean, ensure_ascii=False, sort_keys=True)
            if key not in seen:
                seen.add(key)
                normalized.append(clean)
            continue
        op_type = op.get('type') or op.get('operation')
        if str(op_type or '').startswith('unsupported_') or op_type == 'unsupported_postprocess_config':
            clean = {
                'type': op_type or 'unsupported_postprocess_config',
                'enabled': True,
                '_config_error': op.get('_config_error') or 'unsupported postprocess operation',
            }
            key = json.dumps(clean, ensure_ascii=False, sort_keys=True)
            if key not in seen:
                seen.add(key)
                normalized.append(clean)
            continue
        if op_type not in supported:
            clean = {
                'type': op_type or 'unsupported_postprocess_operation',
                'enabled': True,
                '_config_error': f'unsupported postprocess operation type: {op_type or "missing"}',
            }
            key = json.dumps(clean, ensure_ascii=False, sort_keys=True)
            if key not in seen:
                seen.add(key)
                normalized.append(clean)
            continue
        clean = dict(op)
        clean['type'] = op_type
        clean.setdefault('enabled', True)
        key = json.dumps(clean, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(clean)
    return normalized


def infer_postprocess_operations_from_structural_rules(structural):
    if not isinstance(structural, dict):
        return []
    operations = []
    placement = structural.get('placement') if isinstance(structural.get('placement'), dict) else {}
    if placement.get('tables_after_references'):
        operations.append({
            'type': 'move_tables_after_references',
            'include_caption': True,
            'source': 'explicit_text_structural_rule',
        })
    if placement.get('figures_after_references'):
        operations.append({
            'type': 'move_figures_after_references',
            'include_caption': True,
            'source': 'explicit_text_structural_rule',
        })

    citation = structural.get('citation_format') if isinstance(structural.get('citation_format'), dict) else {}
    if citation.get('marker') in ('parentheses', 'round'):
        op = {
            'type': 'normalize_body_citations',
            'to': 'parentheses',
            'source': 'explicit_text_structural_rule',
        }
        if citation.get('italic') is not None:
            op['italic'] = bool(citation.get('italic'))
        if citation.get('bold') is not None:
            op['bold'] = bool(citation.get('bold'))
        if citation.get('superscript') is not None:
            op['superscript'] = bool(citation.get('superscript'))
        operations.append(op)

    references = structural.get('reference_prefix') if isinstance(structural.get('reference_prefix'), dict) else {}
    if references.get('style'):
        op = {
            'type': 'normalize_reference_prefixes',
            'style': references.get('style'),
            'source': 'explicit_text_structural_rule',
        }
        if references.get('renumber') is not None:
            op['renumber'] = bool(references.get('renumber'))
        if references.get('add_missing') is not None:
            op['add_missing'] = bool(references.get('add_missing'))
        operations.append(op)

    figure = structural.get('figure_caption') if isinstance(structural.get('figure_caption'), dict) else {}
    if figure.get('prefix'):
        operations.append({
            'type': 'normalize_figure_captions',
            'prefix': figure.get('prefix'),
            'separator': figure.get('separator', ':'),
            'first_sentence_bold': bool(figure.get('first_sentence_bold', False)),
            'source': 'explicit_text_structural_rule',
        })
    table = structural.get('table_caption') if isinstance(structural.get('table_caption'), dict) else {}
    if table.get('prefix'):
        operations.append({
            'type': 'normalize_table_captions',
            'prefix': table.get('prefix'),
            'separator': table.get('separator', ':'),
            'first_sentence_bold': bool(table.get('first_sentence_bold', False)),
            'source': 'explicit_text_structural_rule',
        })
    return operations


def write_auto_postprocess_ops(operations, directory):
    operations = normalize_postprocess_operations(operations)
    if not operations:
        return None
    path = os.path.join(directory, 'auto_postprocess_ops.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({
            'enabled': True,
            '_meta': {
                'generated_by': 'format_docx.py',
                'source': 'rules_json_explicit_structural_rules',
                'boundary': 'explicit text/source rules only; never visual-style evidence',
            },
            'operations': operations,
        }, f, ensure_ascii=False, indent=2)
    return path


def value_attr(value):
    if isinstance(value, dict):
        for key in ('val', 'value', '@val', 'w:val'):
            if value.get(key) not in (None, ''):
                return value.get(key)
    return value


def attrs_from_summary_node(node):
    if not isinstance(node, dict):
        return {}
    attrs = {}
    for key, value in node.items():
        if isinstance(value, dict) and any(k in value for k in ('val', 'value', '@val', 'w:val')):
            attrs[key] = value_attr(value)
        elif not isinstance(value, (dict, list)):
            attrs[key] = value
    return attrs


def merge_rule_dict_field(normalized, field, values, source_name=None):
    values = {k: str(v) for k, v in (values or {}).items() if v not in (None, '', {}, [])}
    if not values:
        return
    current = dict(normalized.get(field) or {})
    current.update(values)
    normalized[field] = current
    if source_name:
        normalized.setdefault('_normalized_from', []).append(source_name)


def normalize_size_value(value):
    value = value_attr(value)
    if value in (None, ''):
        return None
    return str(value)


def normalize_spacing_line_value(value, line_rule=None):
    value = value_attr(value)
    if value in (None, ''):
        return None
    text = str(value).strip()
    if not text:
        return None
    lower = text.lower()
    if lower in {'default', '默认', 'default single'}:
        return '0'
    if lower in {'single', 'single-spaced', 'single spaced', '单倍', '单倍行距'}:
        return '240'
    if lower in {'double', 'double-spaced', 'double spaced', '双倍', '双倍行距'}:
        return '480'
    if lower in {'1.5', '1.50', '1.5x', '1.5倍', '一倍半'}:
        return '360'
    if re.fullmatch(r'\d+', text):
        return text
    if re.fullmatch(r'\d+(?:\.\d+)?', text):
        number = float(text)
        if number <= 4 and str(line_rule or '').lower() != 'exact':
            return str(int(round(number * 240)))
        return str(int(round(number)))
    match = re.fullmatch(r'(\d+(?:\.\d+)?)\s*(?:倍|x|line(?:s)?)', lower)
    if match and str(line_rule or '').lower() != 'exact':
        return str(int(round(float(match.group(1)) * 240)))
    match = re.fullmatch(r'(\d+(?:\.\d+)?)\s*(?:pt|磅)', lower)
    if match:
        return str(int(round(float(match.group(1)) * 20)))
    return text


def normalize_spacing_rule(spacing):
    if not isinstance(spacing, dict):
        return {}
    result = {
        str(k): str(value_attr(v))
        for k, v in spacing.items()
        if v not in (None, '', {}, [])
    }
    line_rule = result.get('lineRule')
    if result.get('line') not in (None, ''):
        result['line'] = normalize_spacing_line_value(result.get('line'), line_rule=line_rule)
        if result.get('lineRule') in (None, ''):
            result['lineRule'] = 'auto'
    return result


def normalize_spacing_element_values(root):
    """Repair invalid OOXML spacing values such as w:line="1.5" before writing."""
    repairs = []
    if root is None:
        return repairs
    for spacing in root.iter(w('spacing')):
        old_line = spacing.get(w('line'))
        if old_line in (None, ''):
            continue
        new_line = normalize_spacing_line_value(old_line, line_rule=spacing.get(w('lineRule')))
        if new_line and new_line != old_line:
            spacing.set(w('line'), new_line)
            if spacing.get(w('lineRule')) in (None, ''):
                spacing.set(w('lineRule'), 'auto')
            repairs.append({'old': old_line, 'new': new_line})
    return repairs


def normalize_docx_spacing_values(extract_dir):
    """Normalize invalid paragraph spacing line values across document/style XML parts."""
    stats = {'parts_scanned': 0, 'repairs': 0, 'examples': []}
    word_dir = os.path.join(extract_dir, 'word')
    if not os.path.isdir(word_dir):
        return stats
    for root_dir, dirs, files in os.walk(word_dir):
        for file_name in files:
            if not file_name.endswith('.xml'):
                continue
            path = os.path.join(root_dir, file_name)
            try:
                tree = ET.parse(path)
            except ET.ParseError:
                continue
            stats['parts_scanned'] += 1
            repairs = normalize_spacing_element_values(tree.getroot())
            if not repairs:
                continue
            stats['repairs'] += len(repairs)
            rel_path = os.path.relpath(path, extract_dir)
            for repair in repairs[:5]:
                if len(stats['examples']) < 12:
                    stats['examples'].append({'part': rel_path, **repair})
            write_xml(tree, path)
    if stats['repairs']:
        print(f"  Normalized invalid OOXML spacing values: {stats['repairs']}")
    return stats


def extract_spacing_from_ppr(ppr):
    if not isinstance(ppr, dict):
        return {}
    spacing = ppr.get('spacing')
    if isinstance(spacing, dict):
        result = attrs_from_summary_node(spacing)
    else:
        result = {}
    for key in ('line', 'lineRule', 'before', 'after', 'beforeLines', 'afterLines'):
        if key in ppr and ppr.get(key) not in (None, ''):
            result[key] = value_attr(ppr.get(key))
    return normalize_spacing_rule(result)


def extract_indent_from_ppr(ppr):
    if not isinstance(ppr, dict):
        return {}
    ind = ppr.get('ind') or ppr.get('indent') or ppr.get('indentation')
    result = attrs_from_summary_node(ind) if isinstance(ind, dict) else {}
    for key in ('left', 'right', 'firstLine', 'hanging', 'leftIndent', 'rightIndent', 'firstLineIndent', 'hangingIndent'):
        if key in ppr and ppr.get(key) not in (None, ''):
            result[key] = value_attr(ppr.get(key))
    return result


def extract_align_from_ppr(ppr):
    if not isinstance(ppr, dict):
        return None
    jc = ppr.get('jc') or ppr.get('align') or ppr.get('alignment')
    if isinstance(jc, dict):
        return value_attr(jc)
    return jc


def extract_rpr_rule(rpr):
    if not isinstance(rpr, dict):
        return {}
    rule = {}
    fonts = rpr.get('rFonts') or rpr.get('fonts') or rpr.get('font')
    if isinstance(fonts, dict):
        rule['fonts'] = attrs_from_summary_node(fonts)
    elif fonts:
        rule['fonts'] = {'ascii': fonts, 'hAnsi': fonts, 'eastAsia': fonts}
    size = None
    for key in ('sz', 'size', 'font_size', 'fontSize'):
        if key in rpr:
            size = normalize_size_value(rpr.get(key))
            if size:
                break
    if not size and 'szCs' in rpr:
        size = normalize_size_value(rpr.get('szCs'))
    if size:
        rule['size'] = size
    for key, target in (('b', 'bold'), ('i', 'italic')):
        if key in rpr:
            value = value_attr(rpr.get(key))
            if value in (None, ''):
                rule[target] = True
            elif isinstance(value, bool):
                rule[target] = value
            else:
                rule[target] = str(value).lower() not in ('0', 'false', 'off', 'none')
    color = rpr.get('color')
    if isinstance(color, dict):
        color_val = value_attr(color)
        if color_val:
            rule['color'] = color_val
    elif color:
        rule['color'] = color
    return rule


def normalize_ooxml_summary_rule(normalized):
    summary_sources = []
    candidate_containers = []
    for container_key in ('summary', 'ooxml', 'xml_summary'):
        if isinstance(normalized.get(container_key), dict):
            candidate_containers.append((container_key, normalized.get(container_key)))
    candidate_containers.append(('root', normalized))
    paragraph = normalized.get('paragraph') if isinstance(normalized.get('paragraph'), dict) else {}
    if paragraph:
        candidate_containers.append(('paragraph', paragraph))

    for source_name, container in candidate_containers:
        ppr = container.get('pPr') if isinstance(container, dict) else None
        if isinstance(ppr, dict):
            spacing = extract_spacing_from_ppr(ppr)
            if spacing:
                merge_rule_dict_field(normalized, 'spacing', spacing, f'{source_name}.pPr.spacing')
                summary_sources.append(f'{source_name}.pPr.spacing')
            indent = extract_indent_from_ppr(ppr)
            if indent:
                merge_rule_dict_field(normalized, 'indent', indent, f'{source_name}.pPr.ind')
                summary_sources.append(f'{source_name}.pPr.ind')
            align = extract_align_from_ppr(ppr)
            if align and 'align' not in normalized:
                normalized['align'] = str(align)
                normalized.setdefault('_normalized_from', []).append(f'{source_name}.pPr.jc')
                summary_sources.append(f'{source_name}.pPr.jc')
        rpr = container.get('rPr') if isinstance(container, dict) else None
        if isinstance(rpr, dict):
            rpr_rule = extract_rpr_rule(rpr)
            for key, value in rpr_rule.items():
                if isinstance(value, dict):
                    merge_rule_dict_field(normalized, key, value, f'{source_name}.rPr.{key}')
                elif key not in normalized:
                    normalized[key] = value
                    normalized.setdefault('_normalized_from', []).append(f'{source_name}.rPr.{key}')
                else:
                    normalized[key] = value
                summary_sources.append(f'{source_name}.rPr.{key}')
    if summary_sources:
        normalized['_ooxml_summary_rule_accepted'] = sorted(set(summary_sources))
        normalized.setdefault('source', 'user_rules')
        normalized.setdefault('confidence', 'explicit')
    return normalized


def normalize_user_rule(rule):
    normalized = dict(rule or {})
    normalized = normalize_ooxml_summary_rule(normalized)
    if 'font_size' in normalized and 'size' not in normalized:
        normalized['size'] = normalized['font_size']
    if 'fontSize' in normalized and 'size' not in normalized:
        normalized['size'] = normalized['fontSize']
    if 'font' in normalized and 'fonts' not in normalized:
        font = normalized.get('font')
        if isinstance(font, dict):
            normalized['fonts'] = dict(font)
        elif font:
            normalized['fonts'] = {'ascii': font, 'hAnsi': font, 'eastAsia': font}
    paragraph = normalized.get('paragraph') if isinstance(normalized.get('paragraph'), dict) else {}
    indentation = None
    for key in ('indent', 'ind', 'indentation'):
        if isinstance(normalized.get(key), dict):
            indentation = dict(normalized.get(key))
            break
    for key in ('indent', 'ind', 'indentation'):
        if key in paragraph and isinstance(paragraph.get(key), dict):
            indentation = dict(paragraph.get(key))
            break
    if indentation:
        indent = dict(normalized.get('indent') or {})
        for key, value in indentation.items():
            mapped = {
                'leftIndent': 'left',
                'rightIndent': 'right',
                'firstLineIndent': 'firstLine',
                'hangingIndent': 'hanging',
            }.get(key, key)
            indent[mapped] = value
        indent = normalize_reference_hanging_indent_rule(indent)
        normalized['indent'] = indent
    spacing = None
    if isinstance(normalized.get('spacing'), dict):
        spacing = dict(normalized.get('spacing'))
    for key in ('line_spacing', 'lineSpacing'):
        if isinstance(normalized.get(key), dict):
            spacing = dict(normalized.get(key))
        elif normalized.get(key) not in (None, ''):
            spacing = dict(spacing or {})
            spacing['line'] = str(normalized.get(key))
    if isinstance(paragraph.get('spacing'), dict):
        spacing = dict(paragraph.get('spacing'))
    for key in ('line_spacing', 'lineSpacing'):
        if isinstance(paragraph.get(key), dict):
            spacing = dict(paragraph.get(key))
        elif paragraph.get(key) not in (None, ''):
            spacing = dict(spacing or {})
            spacing['line'] = str(paragraph.get(key))
    if spacing:
        current = dict(normalized.get('spacing') or {})
        current.update(spacing)
        normalized['spacing'] = normalize_spacing_rule(current)
    if 'alignment' in normalized and 'align' not in normalized:
        normalized['align'] = normalized['alignment']
    if 'align' not in normalized and 'alignment' in paragraph:
        normalized['align'] = paragraph['alignment']
    return normalized


def normalize_reference_hanging_indent_rule(indent):
    indent = dict(indent or {})
    hanging = indent.get('hanging') or indent.get('hangingChars')
    if hanging in (None, '', '0'):
        return indent
    if 'left' not in indent and 'leftChars' not in indent:
        indent['left'] = hanging
        return indent
    try:
        hanging_val = int(str(hanging))
        left_val = int(str(indent.get('left') or 0))
    except (TypeError, ValueError):
        return indent
    if left_val < hanging_val:
        indent['left'] = str(hanging_val)
    return indent


def apply_rule_to_rpr(rPr, rule):
    fonts = rule.get('fonts') or {}
    if fonts:
        rFonts = get_or_add_child(rPr, w('rFonts'))
        theme_for = {
            'ascii': 'asciiTheme',
            'hAnsi': 'hAnsiTheme',
            'eastAsia': 'eastAsiaTheme',
            'cs': 'cstheme',
        }
        for key in ('ascii', 'hAnsi', 'eastAsia', 'cs'):
            if key in fonts:
                theme_key = theme_for.get(key)
                if theme_key and rFonts.get(w(theme_key)) is not None:
                    del rFonts.attrib[w(theme_key)]
                rFonts.set(w(key), str(fonts[key]))

    if 'size' in rule:
        size = str(rule['size'])
        remove_children_by_local_name(rPr, {'sz', 'szCs'})
        sz = ET.Element(w('sz'))
        szCs = ET.Element(w('szCs'))
        sz.set(w('val'), size)
        szCs.set(w('val'), size)
        rPr.append(sz)
        rPr.append(szCs)

    if 'bold' in rule:
        remove_children_by_local_name(rPr, {'b', 'bCs'})
        for tag in ('b', 'bCs'):
            elem = ET.Element(w(tag))
            if rule['bold']:
                elem.set(w('val'), '1')
            else:
                elem.set(w('val'), '0')
            rPr.append(elem)

    if 'color' in rule:
        remove_children_by_local_name(rPr, {'color'})
        color = ET.Element(w('color'))
        color.set(w('val'), str(rule['color']).upper())
        rPr.append(color)


def set_attrs_if_missing(elem, attrs, override=False):
    changed = {}
    for key, value in (attrs or {}).items():
        attr = w(key)
        if override or elem.get(attr) is None:
            old = elem.get(attr)
            elem.set(attr, str(value))
            if old != str(value):
                changed[key] = {'old': old, 'new': str(value)} if old is not None else str(value)
    return changed


def set_spacing_attrs_if_missing_or_default(elem, attrs, override=False):
    changed = {}
    current_line = elem.get(w('line'))
    implicit_line_spacing = current_line == '0'
    for key, value in normalize_spacing_rule(attrs or {}).items():
        attr = w(key)
        current = elem.get(attr)
        if override or current is None or (key in ('line', 'lineRule') and implicit_line_spacing):
            elem.set(attr, str(value))
            if current != str(value):
                changed[key] = {'old': current, 'new': str(value)} if current is not None else str(value)
    return changed


def ensure_rpr_fallback(rPr, fallback, override_keys=None):
    applied = {}
    override_keys = set(override_keys or [])
    fonts = fallback.get('fonts') or {}
    if fonts:
        rFonts = get_or_add_child(rPr, w('rFonts'))
        changed = set_font_attrs_if_missing_without_theme_conflict(rFonts, fonts, override=('fonts' in override_keys))
        if changed:
            applied['fonts'] = changed

    if 'size' in fallback:
        size = str(fallback['size'])
        for name in ('sz', 'szCs'):
            elem = get_or_add_child(rPr, w(name))
            old = elem.get(w('val'))
            if old is None or 'size' in override_keys:
                elem.set(w('val'), size)
                if old != size:
                    applied[name] = {'old': old, 'new': size} if old is not None else size

    if 'bold' in fallback:
        for name in ('b', 'bCs'):
            elem = child_by_local_name(rPr, name)
            if elem is None:
                elem = ET.Element(w(name))
                elem.set(w('val'), '1' if fallback['bold'] else '0')
                rPr.append(elem)
                applied[name] = bool(fallback['bold'])
            elif elem.get(w('val')) is None:
                # Empty <w:b/> is an explicit true, not a missing value.
                continue
    return applied


def set_font_attrs_if_missing_without_theme_conflict(rFonts, fonts, override=False):
    changed = {}
    theme_pairs = {
        'ascii': 'asciiTheme',
        'hAnsi': 'hAnsiTheme',
        'eastAsia': 'eastAsiaTheme',
        'cs': 'cstheme',
    }
    for key, value in (fonts or {}).items():
        attr = w(key)
        theme_attr = w(theme_pairs.get(key, ''))
        if rFonts.get(attr) is not None and not override:
            continue
        if theme_pairs.get(key) and rFonts.get(theme_attr) is not None and not override:
            continue
        old = rFonts.get(attr)
        rFonts.set(attr, str(value))
        if old != str(value):
            changed[key] = {'old': old, 'new': str(value)} if old is not None else str(value)
    return changed


def rfonts_has_theme_specific_conflict(rFonts):
    if rFonts is None:
        return False
    pairs = (
        ('asciiTheme', 'ascii'),
        ('hAnsiTheme', 'hAnsi'),
        ('eastAsiaTheme', 'eastAsia'),
        ('cstheme', 'cs'),
    )
    return any(rFonts.get(w(theme)) is not None and rFonts.get(w(specific)) is not None for theme, specific in pairs)


def style_num_ids(style_elem):
    ids = []
    for numId in style_elem.iter(w('numId')):
        val = numId.get(w('val'))
        if val is not None:
            ids.append(val)
    return ids


def update_style_num_ids(style_elem, num_id_map):
    updated = {}
    for numId in style_elem.iter(w('numId')):
        old = numId.get(w('val'))
        if old in num_id_map:
            new = str(num_id_map[old])
            numId.set(w('val'), new)
            updated[old] = new
    return updated


def numbering_child_by_id(root, local, attr_name, attr_value):
    if root is None:
        return None
    for child in root:
        if local_name(child.tag) == local and child.get(w(attr_name)) == str(attr_value):
            return child
    return None


def max_numbering_id(root, local, attr_name):
    max_id = -1
    if root is None:
        return max_id
    for child in root:
        if local_name(child.tag) != local:
            continue
        value = child.get(w(attr_name))
        if value is None:
            continue
        try:
            max_id = max(max_id, int(value))
        except ValueError:
            pass
    return max_id


def ensure_numbering_part(doc_dir):
    word_dir = os.path.join(doc_dir, 'word')
    numbering_path = os.path.join(word_dir, 'numbering.xml')
    if os.path.exists(numbering_path):
        return ET.parse(numbering_path), numbering_path
    root = ET.Element(w('numbering'))
    return ET.ElementTree(root), numbering_path


def collect_required_num_ids_from_spec(spec, exclude_roles=None):
    required = set()
    exclude_roles = set(exclude_roles or [])
    for role, role_spec in (spec.get('roles') or {}).items():
        if role in exclude_roles:
            continue
        for key in ('style_xml', 'pPr_xml'):
            xml = role_spec.get(key)
            if not xml:
                continue
            try:
                elem = ET.fromstring(xml)
            except ET.ParseError:
                continue
            required.update(style_num_ids(elem))
    return sorted(required, key=lambda x: (0, int(x)) if str(x).isdigit() else (1, str(x)))


def ensure_numbering_relationship_and_content_type(doc_dir):
    word_dir = os.path.join(doc_dir, 'word')
    rels_dir = os.path.join(word_dir, '_rels')
    os.makedirs(rels_dir, exist_ok=True)
    rels_path = os.path.join(rels_dir, 'document.xml.rels')
    if os.path.exists(rels_path):
        rels_tree = ET.parse(rels_path)
        rels_root = rels_tree.getroot()
    else:
        rels_root = ET.Element(pkg_rel('Relationships'))
        rels_tree = ET.ElementTree(rels_root)
    ensure_document_relationship(
        rels_root,
        f'{R_NS}/numbering',
        'numbering.xml'
    )
    write_xml(rels_tree, rels_path)

    content_types_path = os.path.join(doc_dir, '[Content_Types].xml')
    if os.path.exists(content_types_path):
        ct_tree = ET.parse(content_types_path)
        ct_root = ct_tree.getroot()
        ct_ns = ct_root.tag.split('}')[0].strip('{') if ct_root.tag.startswith('{') else ''
        override_tag = f'{{{ct_ns}}}Override' if ct_ns else 'Override'
        has_override = any(
            local_name(child.tag) == 'Override'
            and child.get('PartName') == '/word/numbering.xml'
            for child in ct_root
        )
        if not has_override:
            override = ET.Element(override_tag)
            override.set('PartName', '/word/numbering.xml')
            override.set('ContentType', 'application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml')
            ct_root.append(override)
            write_xml(ct_tree, content_types_path)


def copy_numbering_definitions(template_dir, target_dir, required_num_ids):
    if not required_num_ids:
        return {}
    template_numbering_path = os.path.join(template_dir, 'word', 'numbering.xml')
    if not os.path.exists(template_numbering_path):
        return {
            'num_id_map': {},
            'missing_num_ids': list(required_num_ids),
            'copied': [],
            'warning': 'template numbering.xml missing while role styles reference numId',
        }
    template_tree = ET.parse(template_numbering_path)
    template_root = template_tree.getroot()
    target_tree, target_numbering_path = ensure_numbering_part(target_dir)
    target_root = target_tree.getroot()
    next_abstract_id = max_numbering_id(target_root, 'abstractNum', 'abstractNumId') + 1
    next_num_id = max_numbering_id(target_root, 'num', 'numId') + 1
    abstract_map = {}
    num_id_map = {}
    copied = []
    missing = []

    for old_num_id in required_num_ids:
        template_num = numbering_child_by_id(template_root, 'num', 'numId', old_num_id)
        if template_num is None:
            missing.append(old_num_id)
            continue
        old_abs_id = child_attrs(template_num, 'abstractNumId').get('val')
        if old_abs_id is None:
            missing.append(old_num_id)
            continue
        if old_abs_id not in abstract_map:
            template_abs = numbering_child_by_id(template_root, 'abstractNum', 'abstractNumId', old_abs_id)
            if template_abs is None:
                missing.append(old_num_id)
                continue
            new_abs_id = str(next_abstract_id)
            next_abstract_id += 1
            copied_abs = clone_element(template_abs)
            copied_abs.set(w('abstractNumId'), new_abs_id)
            target_root.append(copied_abs)
            abstract_map[old_abs_id] = new_abs_id
        new_num_id = str(next_num_id)
        next_num_id += 1
        copied_num = clone_element(template_num)
        copied_num.set(w('numId'), new_num_id)
        abs_ref = child_by_local_name(copied_num, 'abstractNumId')
        if abs_ref is not None:
            abs_ref.set(w('val'), abstract_map[old_abs_id])
        target_root.append(copied_num)
        num_id_map[str(old_num_id)] = new_num_id
        copied.append({
            'old_numId': str(old_num_id),
            'new_numId': new_num_id,
            'old_abstractNumId': str(old_abs_id),
            'new_abstractNumId': abstract_map[old_abs_id],
        })

    if copied:
        ensure_numbering_relationship_and_content_type(target_dir)
        write_xml(target_tree, target_numbering_path)
    return {
        'num_id_map': num_id_map,
        'missing_num_ids': missing,
        'copied': copied,
    }


def ensure_ppr_fallback(pPr, fallback, override_keys=None):
    applied = {}
    override_keys = set(override_keys or [])
    if 'align' in fallback:
        jc = child_by_local_name(pPr, 'jc')
        if jc is None:
            jc = ET.Element(w('jc'))
            jc.set(w('val'), str(fallback['align']))
            pPr.append(jc)
            applied['align'] = str(fallback['align'])
        elif jc.get(w('val')) is None or 'align' in override_keys:
            old = jc.get(w('val'))
            jc.set(w('val'), str(fallback['align']))
            if old != str(fallback['align']):
                applied['align'] = {'old': old, 'new': str(fallback['align'])} if old is not None else str(fallback['align'])

    spacing_rule = fallback.get('spacing') or {}
    if spacing_rule:
        spacing = get_or_add_child(pPr, w('spacing'))
        changed = set_spacing_attrs_if_missing_or_default(spacing, spacing_rule, override=('spacing' in override_keys))
        if changed:
            applied['spacing'] = changed

    indent_rule = fallback.get('indent') or {}
    if indent_rule:
        indent_rule = normalize_reference_hanging_indent_rule(indent_rule)
        ind = get_or_add_child(pPr, w('ind'))
        changed = set_attrs_if_missing(ind, indent_rule, override=('indent' in override_keys))
        if changed:
            applied['indent'] = changed
    return applied


def role_fallback_rule(role, language, locked_rule=None, allow_alignment=False):
    locked_rule = locked_rule or {}
    fallback = {}
    fallback.update(BASE_PARAGRAPH_FALLBACK)
    fallback.update(LANGUAGE_FALLBACKS.get(language, LANGUAGE_FALLBACKS['en']).get(role, {}))
    if 'spacing' in BASE_PARAGRAPH_FALLBACK or 'spacing' in LANGUAGE_FALLBACKS.get(language, {}).get(role, {}):
        spacing = {}
        spacing.update(BASE_PARAGRAPH_FALLBACK.get('spacing', {}))
        spacing.update(LANGUAGE_FALLBACKS.get(language, {}).get(role, {}).get('spacing', {}))
        fallback['spacing'] = spacing
    for key in ('fonts', 'size', 'bold', 'align', 'indent'):
        if key in locked_rule:
            fallback.pop(key, None)
    # Missing w:jc has a real Word meaning: default left alignment.
    # Only low-confidence visual sources may be normalized back to fallback
    # alignment for roles where the fallback is a safer baseline.
    if not allow_alignment:
        fallback.pop('align', None)
    if 'spacing' in locked_rule and isinstance(fallback.get('spacing'), dict):
        for key in locked_rule.get('spacing') or {}:
            fallback['spacing'].pop(key, None)
        if not fallback['spacing']:
            fallback.pop('spacing', None)
    return fallback


def fallback_lock_rule_for_source(role, rule, source_type=None):
    """Only high-confidence rule properties may block granular fallback.

    PDF/image/website visual evidence is useful for role cues and broad layout,
    but it must not freeze weak sizes, paragraph rhythm, or equation defaults.
    """
    rule = dict(rule or {})
    source_type = normalize_format_source_type(source_type)
    if source_type not in WEAK_EXTERNAL_STYLE_SOURCE_TYPES:
        return rule
    confidence = str(rule.get('confidence') or '').lower()
    source = str(rule.get('source') or '').lower()
    is_explicit_text_rule = (
        source in ('pdf_text_rules', 'text_rules', 'user_rules')
        or confidence in ('high', 'explicit', 'locked')
    )
    if is_explicit_text_rule:
        return rule
    filtered = dict(rule)
    for key in ('size', 'spacing'):
        filtered.pop(key, None)
    if role in ('title', 'heading1', 'heading2', 'heading3', 'body', 'equation'):
        filtered.pop('align', None)
    if role == 'equation':
        filtered.pop('indent', None)
    return filtered


def fallback_override_keys_for_source(role, source_type=None, rule=None):
    source_type = normalize_format_source_type(source_type)
    if source_type in DOCX_TEXT_RULE_COMPLETION_SOURCE_TYPES:
        return set()
    if source_type not in WEAK_EXTERNAL_STYLE_SOURCE_TYPES:
        return set()
    rule = rule or {}
    confidence = str(rule.get('confidence') or '').lower()
    source = str(rule.get('source') or '').lower()
    is_explicit_text_rule = (
        source in ('pdf_text_rules', 'text_rules', 'user_rules')
        or confidence in ('high', 'explicit', 'locked')
    )
    if is_explicit_text_rule:
        return set()
    keys = {'size', 'spacing'}
    if role in ('title', 'heading1', 'heading2', 'heading3', 'body', 'equation'):
        keys.add('align')
    if role == 'equation':
        keys.add('indent')
    return keys


def should_apply_bundled_ooxml_fallback(source_type=None):
    return normalize_format_source_type(source_type) in OOXML_FALLBACK_SOURCE_TYPES


def should_apply_language_dictionary_fallback(source_type=None):
    return normalize_format_source_type(source_type) in OOXML_FALLBACK_SOURCE_TYPES


def rule_is_template_text_rule(rule):
    rule = rule or {}
    source = str(rule.get('source') or '').lower()
    confidence = str(rule.get('confidence') or '').lower()
    return source == 'template_text_rules' or confidence in ('explicit', 'locked')


def style_child_missing_or_default(style_elem, group, child_name):
    parent = get_or_add_child(style_elem, w(group))
    child = child_by_local_name(parent, child_name)
    if child is None:
        return True
    if child_name == 'spacing':
        line = child.get(w('line'))
        return line in (None, '', '0')
    if child_name == 'ind':
        return not any(child.get(w(name)) not in (None, '', '0') for name in ('firstLine', 'firstLineChars', 'hanging', 'left', 'start'))
    if child_name == 'jc':
        return child.get(w('val')) in (None, '')
    if child_name == 'rFonts':
        return not any(
            child.get(w(name)) not in (None, '')
            for name in ('ascii', 'hAnsi', 'eastAsia', 'cs', 'asciiTheme', 'hAnsiTheme', 'eastAsiaTheme', 'cstheme')
        )
    if child_name in ('sz', 'szCs'):
        return child.get(w('val')) in (None, '')
    return False


def docx_text_rule_completion_needed(style_elem, role, rule, source_type=None, source=None):
    source_type = normalize_format_source_type(source_type)
    if source_type not in DOCX_TEXT_RULE_COMPLETION_SOURCE_TYPES:
        return False
    if source and not paragraph_format_from_source_is_trustworthy(role, source):
        return True
    if not rule_is_template_text_rule(rule):
        return False
    if not rule:
        return False
    if 'spacing' not in rule and style_child_missing_or_default(style_elem, 'pPr', 'spacing'):
        return True
    if role in ('body', 'reference_item') and 'indent' not in rule and style_child_missing_or_default(style_elem, 'pPr', 'ind'):
        return True
    if 'fonts' in rule and style_child_missing_or_default(style_elem, 'rPr', 'rFonts'):
        return True
    if 'size' in rule and (
        style_child_missing_or_default(style_elem, 'rPr', 'sz')
        or style_child_missing_or_default(style_elem, 'rPr', 'szCs')
    ):
        return True
    return False


def docx_text_rule_paragraph_only_completion(source_type=None, role=None, source=None, locked_rule=None):
    source_type = normalize_format_source_type(source_type)
    if source_type not in DOCX_TEXT_RULE_COMPLETION_SOURCE_TYPES:
        return False
    sample = (source or {}).get('sample') or ''
    return looks_like_role_label_instruction_or_example(role, sample) and not rule_is_template_text_rule(locked_rule)


def effective_fallback_source_type(source_type=None, role=None, locked_rule=None, style_elem=None, source=None):
    source_type = normalize_format_source_type(source_type)
    if docx_text_rule_completion_needed(style_elem, role, locked_rule, source_type=source_type, source=source):
        return 'text_rules'
    return source_type


def merge_fallback_attrs(target_child, source_child, locked_attrs=None, override=False, default_attr_names=None):
    locked_attrs = set(locked_attrs or [])
    default_attr_names = set(default_attr_names or [])
    changed = []
    if target_child is None or source_child is None:
        return changed
    default_attr_missing = any(target_child.get(w(name)) in (None, '', '0') for name in default_attr_names)
    for attr, value in source_child.attrib.items():
        name = local_name(attr)
        if name in locked_attrs:
            continue
        current = target_child.get(attr)
        if override or current is None or (name in default_attr_names and default_attr_missing):
            target_child.set(attr, value)
            if current != value:
                changed.append(name)
    return changed


def locked_ooxml_attrs_for_child(name, locked_rule):
    locked_rule = locked_rule or {}
    if name == 'spacing':
        return set((locked_rule.get('spacing') or {}).keys())
    if name == 'ind':
        return set(normalize_reference_hanging_indent_rule(locked_rule.get('indent') or {}).keys())
    if name == 'rFonts':
        return set((locked_rule.get('fonts') or {}).keys())
    return set()


def apply_ooxml_fallback_to_style(style_elem, role, language='en', locked_rule=None,
                                  source_type=None, columns=1, source=None):
    """Apply role-level fallback pPr/rPr copied from the bundled OOXML samples."""
    locked_rule = normalize_user_rule(locked_rule or {})
    source_type = effective_fallback_source_type(
        source_type,
        role=role,
        locked_rule=locked_rule,
        style_elem=style_elem,
        source=source,
    )
    if not should_apply_bundled_ooxml_fallback(source_type):
        return {}
    role_spec = role_ooxml_fallback(role, language=language, columns=columns)
    if not role_spec:
        return {}
    override_keys = fallback_override_keys_for_source(role, source_type=source_type, rule=locked_rule)
    # Respect explicit text/user rule channels; fallback fills only what is missing.
    for key in ('fonts', 'size', 'bold', 'align', 'indent'):
        if key in locked_rule:
            override_keys.discard(key)
    if 'spacing' in locked_rule:
        override_keys.discard('spacing')
    applied = {}
    pPr_src = xml_child_from_text(role_spec.get('pPr_xml'))
    rPr_src = xml_child_from_text(role_spec.get('rPr_xml'))
    pPr = get_or_add_child(style_elem, w('pPr'))
    rPr = get_or_add_child(style_elem, w('rPr'))
    if pPr_src is not None:
        for src_child in pPr_src:
            name = local_name(src_child.tag)
            if name in {'pStyle', 'sectPr'}:
                continue
            channel = {
                'jc': 'align',
                'spacing': 'spacing',
                'ind': 'indent',
                'tabs': 'tabs',
            }.get(name, name)
            existing = child_by_local_name(pPr, name)
            if name in ('spacing', 'ind') and existing is not None:
                changed_attrs = merge_fallback_attrs(
                    existing,
                    src_child,
                    locked_attrs=locked_ooxml_attrs_for_child(name, locked_rule),
                    override=channel in override_keys,
                    default_attr_names={'line', 'lineRule'} if name == 'spacing' else set(),
                )
                if changed_attrs:
                    applied.setdefault('paragraph_ooxml_attrs', {})[name] = changed_attrs
                continue
            if channel in locked_rule:
                continue
            should_replace = (
                existing is None
                or channel in override_keys
                or (name == 'spacing' and existing.get(w('line')) == '0')
            )
            if should_replace:
                if existing is not None:
                    pPr.remove(existing)
                pPr.append(clone_element(src_child))
                applied.setdefault('paragraph_ooxml', []).append(name)
    if rPr_src is not None:
        for src_child in rPr_src:
            name = local_name(src_child.tag)
            channel = {
                'rFonts': 'fonts',
                'sz': 'size',
                'szCs': 'size',
                'b': 'bold',
                'bCs': 'bold',
                'i': 'italic',
                'iCs': 'italic',
            }.get(name, name)
            existing = child_by_local_name(rPr, name)
            if name == 'rFonts' and existing is not None:
                changed_attrs = merge_fallback_attrs(
                    existing,
                    src_child,
                    locked_attrs=locked_ooxml_attrs_for_child(name, locked_rule),
                    override=channel in override_keys,
                )
                if changed_attrs:
                    applied.setdefault('font_ooxml_attrs', {})[name] = changed_attrs
                continue
            if channel in locked_rule:
                continue
            should_replace = existing is None or channel in override_keys
            if should_replace:
                if existing is not None:
                    rPr.remove(existing)
                rPr.append(clone_element(src_child))
                applied.setdefault('font_ooxml', []).append(name)
    # Re-apply explicit rules after OOXML fallback so user/prose rules keep priority.
    apply_rule_to_style(style_elem, locked_rule)
    return applied


def apply_granular_fallback_to_style(style_elem, role, language, locked_rule=None,
                                     source_type=None, columns=1, source=None):
    effective_locked_rule = fallback_lock_rule_for_source(role, locked_rule, source_type=source_type)
    paragraph_only_completion = docx_text_rule_paragraph_only_completion(
        source_type=source_type,
        role=role,
        source=source,
        locked_rule=locked_rule,
    )
    if paragraph_only_completion:
        effective_locked_rule = dict(effective_locked_rule or {})
        existing_rPr = get_or_add_child(style_elem, w('rPr'))
        existing_fonts = child_by_local_name(existing_rPr, 'rFonts')
        if 'fonts' not in effective_locked_rule and existing_fonts is not None:
            effective_locked_rule['fonts'] = {
                name: existing_fonts.get(w(name))
                for name in ('ascii', 'hAnsi', 'eastAsia', 'cs', 'asciiTheme', 'hAnsiTheme', 'eastAsiaTheme', 'cstheme')
                if existing_fonts.get(w(name)) is not None
            }
        if 'size' not in effective_locked_rule and (
            child_by_local_name(existing_rPr, 'sz') is not None
            or child_by_local_name(existing_rPr, 'szCs') is not None
        ):
            size_elem = child_by_local_name(existing_rPr, 'sz')
            if size_elem is None:
                size_elem = child_by_local_name(existing_rPr, 'szCs')
            effective_locked_rule['size'] = size_elem.get(w('val')) if size_elem is not None else None
        if 'bold' not in effective_locked_rule and child_by_local_name(existing_rPr, 'b') is not None:
            effective_locked_rule['bold'] = child_by_local_name(existing_rPr, 'b').get(w('val')) not in ('0', 'false', 'False')
    effective_source_type = effective_fallback_source_type(
        source_type,
        role=role,
        locked_rule=locked_rule,
        style_elem=style_elem,
        source=source,
    )
    override_keys = fallback_override_keys_for_source(role, source_type=effective_source_type, rule=locked_rule)
    ooxml_applied = apply_ooxml_fallback_to_style(
        style_elem,
        role,
        language=language,
        locked_rule=effective_locked_rule,
        source_type=source_type,
        columns=columns,
        source=source,
    )
    legacy_override_keys = set(override_keys)
    if paragraph_only_completion:
        legacy_override_keys -= {'fonts', 'size'}
    paragraph_ooxml = set((ooxml_applied or {}).get('paragraph_ooxml') or [])
    paragraph_ooxml_attrs = set(((ooxml_applied or {}).get('paragraph_ooxml_attrs') or {}).keys())
    font_ooxml = set((ooxml_applied or {}).get('font_ooxml') or [])
    font_ooxml_attrs = set(((ooxml_applied or {}).get('font_ooxml_attrs') or {}).keys())
    if 'jc' in paragraph_ooxml:
        legacy_override_keys.discard('align')
    if 'spacing' in paragraph_ooxml or 'spacing' in paragraph_ooxml_attrs:
        legacy_override_keys.discard('spacing')
    if 'ind' in paragraph_ooxml or 'ind' in paragraph_ooxml_attrs:
        legacy_override_keys.discard('indent')
    if 'rFonts' in font_ooxml or 'rFonts' in font_ooxml_attrs:
        legacy_override_keys.discard('fonts')
    if {'sz', 'szCs'} & font_ooxml:
        legacy_override_keys.discard('size')
    fallback = (
        role_fallback_rule(role, language, locked_rule=effective_locked_rule, allow_alignment=('align' in override_keys))
        if should_apply_language_dictionary_fallback(effective_source_type)
        else {}
    )
    pPr = get_or_add_child(style_elem, w('pPr'))
    if role == 'reference_item' and child_by_local_name(pPr, 'numPr') is not None:
        fallback.pop('indent', None)
    rPr = get_or_add_child(style_elem, w('rPr'))
    applied = {}
    p_applied = ensure_ppr_fallback(pPr, fallback, override_keys=legacy_override_keys)
    r_applied = ensure_rpr_fallback(rPr, fallback, override_keys=legacy_override_keys)
    if p_applied:
        applied['paragraph'] = p_applied
    if r_applied:
        applied['font'] = r_applied
    if ooxml_applied:
        applied['ooxml'] = ooxml_applied
    if effective_source_type != normalize_format_source_type(source_type):
        applied['docx_text_rule_property_completion'] = {
            'from_source_type': normalize_format_source_type(source_type),
            'as_source_type': effective_source_type,
            'reason': 'template text rule locked some properties and missing/default properties were completed by granular fallback',
        }
        if paragraph_only_completion:
            applied['docx_text_rule_property_completion']['paragraph_only'] = True
    pPr_rPr = get_direct_child(pPr, w('rPr'))
    if pPr_rPr is not None:
        nested = ensure_rpr_fallback(pPr_rPr, fallback, override_keys=legacy_override_keys)
        if nested:
            applied['paragraph_nested_font'] = nested
    return applied


def apply_rule_to_style(style_elem, rule):
    if not rule:
        return
    pPr = get_or_add_child(style_elem, w('pPr'))
    rPr = get_or_add_child(style_elem, w('rPr'))

    if 'align' in rule:
        jc = get_or_add_child(pPr, w('jc'))
        jc.set(w('val'), rule['align'])

    if 'spacing' in rule:
        spacing = get_or_add_child(pPr, w('spacing'))
        for key, value in normalize_spacing_rule(rule.get('spacing') or {}).items():
            spacing.set(w(key), str(value))

    if 'indent' in rule:
        ind = get_or_add_child(pPr, w('ind'))
        for key, value in normalize_reference_hanging_indent_rule(rule.get('indent') or {}).items():
            ind.set(w(key), str(value))

    apply_rule_to_rpr(rPr, rule)

    # Paragraph styles can also contain pPr/rPr. Mirror locked prose/user
    # rules there so Word does not display stale size/font from the template.
    pPr_rPr = get_direct_child(pPr, w('rPr'))
    if pPr_rPr is not None:
        apply_rule_to_rpr(pPr_rPr, rule)


def strip_unstable_style_links(style_elem):
    """Remove links that often point to template-only styleIds or numbering IDs."""
    remove_children_by_local_name(
        style_elem,
        {'basedOn', 'next', 'link', 'autoRedefine', 'rsid', 'numStyleLink'}
    )


def warn_style_route(style_mode, clean_direct, text_rules, source_type='docx_template'):
    print(f"  Priority locked: {evidence_priority_for_source(source_type)}")
    if style_mode == 'name':
        print("  WARNING: style-mode=name matches w:name only; use only when target style names are known to match the template.")
    else:
        print("  Style route: role binding. Target style names will not be trusted as the formatting bridge.")
    if not clean_direct:
        print("  WARNING: direct formatting cleanup disabled; run/paragraph overrides may still beat the assigned style.")
    if not text_rules:
        print("  WARNING: no template prose/user text rules detected; role styles will fall back to template XML.")


def apply_all_styles(target_dir, styles_dict):
    """Apply all template styles to target document by style name.

    - Styles that exist in both: replace target's style properties
    - Styles only in template: add as new styles to target
    - Styles only in target: preserved as-is
    - Style IDs in target are never changed (no document.xml modifications)
    """
    styles_path = os.path.join(target_dir, 'word', 'styles.xml')
    tree = ET.parse(styles_path)
    root = tree.getroot()

    # Build index of target styles by name
    target_styles = {}
    for style in root.findall(w('style')):
        name_elem = style.find(w('name'))
        if name_elem is not None:
            target_styles[name_elem.get(w('val'))] = style

    applied_count = 0
    added_count = 0

    for style_name, template_info in styles_dict.items():
        if style_name == '__docDefaults__':
            # Handle docDefaults separately
            defaults_elem = ET.fromstring(template_info['xml'])
            old_defaults = root.find(w('docDefaults'))
            if old_defaults is not None:
                root.remove(old_defaults)
            # Insert docDefaults as first child
            root.insert(0, defaults_elem)
            applied_count += 1
            continue

        template_style = ET.fromstring(template_info['xml'])

        if style_name in target_styles:
            # Replace existing style's content (preserve styleId)
            target_style = target_styles[style_name]
            target_sid = target_style.get(w('styleId'))
            target_type = target_style.get(w('type'))

            # Clear all children of target style
            for child in list(target_style):
                target_style.remove(child)

            # Copy all children from template style
            for child in template_style:
                target_style.append(child)

            # Restore original styleId and type
            target_style.set(w('styleId'), target_sid)
            if target_type:
                target_style.set(w('type'), target_type)

            applied_count += 1
        else:
            # Add new style (generate new styleId)
            new_id_num = _get_next_style_id(root)
            template_style.set(w('styleId'), f'Style{new_id_num}')
            root.append(template_style)
            added_count += 1

    print(f"  Applied {applied_count} existing styles, added {added_count} new styles")

    write_xml(tree, styles_path)


def build_sectPr_child(tag, sectPr_info):
    elem = ET.Element(w(tag))
    for k, v in sectPr_info.get(tag, {}).items():
        elem.set(w(k), v)
    return elem


def apply_page_setup_to_sectPr(sectPr, sectPr_info):
    """Apply page geometry to one sectPr while preserving section identity refs."""
    for tag in ['pgSz', 'pgMar', 'cols', 'docGrid']:
        for elem in list(sectPr.findall(w(tag))):
            sectPr.remove(elem)

    insert_idx = 0
    for i, child in enumerate(list(sectPr)):
        tag = local_name(child.tag)
        if tag in ('headerReference', 'footerReference', 'type', 'titlePg'):
            insert_idx = i + 1

    applied = {}
    for tag in ('pgSz', 'pgMar', 'cols', 'docGrid'):
        if tag not in sectPr_info:
            continue
        elem = build_sectPr_child(tag, sectPr_info)
        sectPr.insert(insert_idx, elem)
        insert_idx += 1
        applied[tag] = dict(sectPr_info[tag])
    return applied


def audit_section_setup(root, expected_info=None):
    records = []
    body = root.find(w('body'))
    body_children = list(body) if body is not None else []
    expected_infos = expected_info if isinstance(expected_info, list) else None
    for idx, sectPr in enumerate(root.iter(w('sectPr'))):
        parent_kind = 'body' if sectPr in body_children else 'pPr'
        record = {'index': idx, 'location': parent_kind, 'matches': True, 'values': {}}
        expected = expected_infos[idx] if expected_infos and idx < len(expected_infos) else expected_info
        for tag in ('pgSz', 'pgMar', 'cols', 'docGrid'):
            elem = get_direct_child(sectPr, w(tag))
            value = attrs_without_ns(elem)
            record['values'][tag] = value
            if expected and tag in expected and value != expected.get(tag, {}):
                record['matches'] = False
        records.append(record)
    return records


def select_section_infos_for_target(template_infos, target_count):
    """Map template section geometry to target sections with conservative fallbacks."""
    if not template_infos:
        return []
    if len(template_infos) == target_count:
        print(f"  Section route: {target_count} template section(s) matched by position")
        return template_infos
    if len(template_infos) > 1 and target_count > 1:
        first = template_infos[0]
        body = template_infos[-1]
        print(
            "  WARNING: template/target section counts differ; "
            "using template first section for target first section and template final/body section for the rest"
        )
        return [first] + [body for _ in range(target_count - 1)]
    print("  Section route: using template final/body section for all target sections")
    return [template_infos[-1] for _ in range(target_count)]


def collect_section_profiles(doc_dir, sectPr_infos):
    """Describe each section by nearby content roles and column count."""
    doc_path = os.path.join(doc_dir, 'word', 'document.xml')
    tree = ET.parse(doc_path)
    root = tree.getroot()
    body = root.find(w('body'))
    if body is None:
        return []

    sections = []
    current = {'texts': [], 'roles': [], 'chars': 0}
    visible_index = 0
    in_references = False
    english_context = {}
    citation_context = {}

    def close_section():
        idx = len(sections)
        info = sectPr_infos[idx] if idx < len(sectPr_infos) else (sectPr_infos[-1] if sectPr_infos else {})
        roles = list(current['roles'])
        role_counts = {role: roles.count(role) for role in sorted(set(roles))}
        has_front = any(role in {
            'title', 'author', 'affiliation', 'abstract', 'keywords',
            'english_title', 'english_author', 'english_affiliation',
            'english_abstract', 'english_keywords', 'metadata', 'citation_format'
        } for role in roles)
        has_refs = any(role in {'references_heading', 'reference_item'} for role in roles)
        body_like = sum(role_counts.get(role, 0) for role in (
            'body', 'heading1', 'heading2', 'heading3', 'figure_caption', 'table_caption'
        ))
        if has_refs and body_like <= max(2, role_counts.get('reference_item', 0)):
            kind = 'back'
        elif has_front and body_like <= 3:
            kind = 'front'
        elif body_like:
            kind = 'body'
        elif has_refs:
            kind = 'back'
        else:
            kind = 'unknown'
        sections.append({
            'index': idx,
            'kind': kind,
            'roles': role_counts,
            'chars': current['chars'],
            'cols': section_col_count(info),
            'info': info,
            'sample': ' '.join(current['texts'])[:120],
        })

    for child in body:
        if child.tag == w('p'):
            text = get_text(child).strip()
            if text:
                if starts_english_front_matter_block(text):
                    english_context = {'mode': 'front_matter', 'step': 0}
                role = classify_paragraph(
                    text, visible_index, in_references,
                    english_context=english_context,
                    citation_context=citation_context
                )
                if role:
                    current['roles'].append(role)
                    if role in ('references_heading', 'reference_item'):
                        in_references = True
                current['texts'].append(text)
                current['chars'] += len(text)
                visible_index += 1
        elif child.tag == w('tbl'):
            text = get_text(child).strip()
            if text:
                current['texts'].append(text[:120])
                current['chars'] += len(text)

        sectPr = None
        if child.tag == w('p'):
            pPr = get_direct_child(child, w('pPr'))
            sectPr = get_direct_child(pPr, w('sectPr'))
        if sectPr is not None:
            close_section()
            current = {'texts': [], 'roles': [], 'chars': 0}

    body_sectPr = get_direct_child(body, w('sectPr'))
    if body_sectPr is not None or current['texts'] or not sections:
        close_section()

    return sections


def score_body_section_candidate(profile, preferred_body_cols=None):
    """Score how likely a template section is the representative body layout."""
    roles = profile.get('roles') or {}
    cols = profile.get('cols') or 1
    chars = profile.get('chars') or 0

    body_roles = (
        'body', 'heading1', 'heading2', 'heading3',
        'english_abstract', 'english_keywords',
        'abstract', 'keywords',
        'references_heading', 'reference_item',
    )
    front_roles = (
        'title', 'author', 'affiliation',
        'english_title', 'english_author', 'english_affiliation',
        'metadata', 'citation_format',
    )
    caption_roles = ('figure_caption', 'table_caption')

    score = 0.0
    score += min(chars / 80.0, 55.0)
    score += roles.get('body', 0) * 10.0
    score += sum(roles.get(role, 0) for role in ('heading1', 'heading2', 'heading3')) * 8.0
    score += sum(roles.get(role, 0) for role in ('abstract', 'keywords', 'english_abstract', 'english_keywords')) * 7.0
    score += sum(roles.get(role, 0) for role in ('references_heading', 'reference_item')) * 4.0
    score += sum(roles.get(role, 0) for role in caption_roles) * 1.0

    if preferred_body_cols is not None:
        if cols == preferred_body_cols:
            score += 70.0
        else:
            score -= abs(cols - preferred_body_cols) * 30.0
    else:
        # Most journal body text is one or two columns. Three-column sections in
        # templates are frequently author/affiliation grids or instruction blocks.
        if cols == 2:
            score += 35.0
        elif cols == 1:
            score += 4.0
        elif cols >= 3:
            score -= 28.0 + (cols - 3) * 10.0

    front_count = sum(roles.get(role, 0) for role in front_roles)
    body_count = sum(roles.get(role, 0) for role in body_roles)
    caption_count = sum(roles.get(role, 0) for role in caption_roles)

    score -= front_count * 16.0
    if front_count and body_count <= front_count + 2:
        score -= 45.0
    if chars < 500:
        score -= 28.0
    if chars < 120 and body_count <= 1:
        score -= 35.0
    if caption_count and body_count <= caption_count + 1:
        score -= 25.0

    return score


def select_representative_body_profile(template_profiles, preferred_body_cols=None):
    body_candidates = [profile for profile in template_profiles if profile['kind'] == 'body']
    if not body_candidates:
        return None, []

    scored = [
        (score_body_section_candidate(profile, preferred_body_cols=preferred_body_cols), profile)
        for profile in body_candidates
    ]
    scored.sort(key=lambda item: (item[0], item[1].get('chars') or 0), reverse=True)
    return scored[0][1], scored


def select_section_infos_for_target_profiles(template_profiles, target_profiles, preferred_body_cols=None):
    if not template_profiles:
        return []

    target_count = len(target_profiles)
    if len(template_profiles) == target_count:
        print(f"  Section route: {target_count} template section(s) matched by position")
        return [profile['info'] for profile in template_profiles]

    def first_kind(kind):
        return next((profile for profile in template_profiles if profile['kind'] == kind), None)

    def last_kind(kind):
        return next((profile for profile in reversed(template_profiles) if profile['kind'] == kind), None)

    front_info = (first_kind('front') or template_profiles[0])['info']
    back_info = (last_kind('back') or template_profiles[-1])['info']
    body_profile, body_scores = select_representative_body_profile(
        template_profiles, preferred_body_cols=preferred_body_cols
    )
    body_info = (body_profile or last_kind('body') or template_profiles[-1])['info']

    mapped = []
    route = []
    for target_profile in target_profiles:
        kind = target_profile['kind']
        if kind == 'front':
            info = front_info
            source_kind = 'front'
        elif kind == 'back':
            info = back_info
            source_kind = 'back'
        elif kind == 'body':
            info = body_info
            source_kind = 'body'
        elif target_profile['index'] == 0:
            info = front_info
            source_kind = 'front'
        else:
            info = body_info
            source_kind = 'body'
        mapped.append(info)
        route.append(
            f"target#{target_profile['index']}({kind},cols={target_profile['cols']})"
            f"<=template_{source_kind}(cols={section_col_count(info)})"
        )

    template_seq = ', '.join(
        f"#{p['index']}:{p['kind']}/cols={p['cols']}" for p in template_profiles
    )
    target_seq = ', '.join(
        f"#{p['index']}:{p['kind']}/cols={p['cols']}" for p in target_profiles
    )
    print(
        "  WARNING: template/target section counts differ; "
        "using content-aware section routing instead of repeating the template final section"
    )
    print(f"  Template section profiles: {template_seq}")
    print(f"  Target section profiles: {target_seq}")
    if body_scores:
        score_seq = '; '.join(
            f"#{profile['index']}:cols={profile['cols']},chars={profile['chars']},score={score:.1f}"
            for score, profile in body_scores
        )
        chosen = body_profile['index'] if body_profile else 'none'
        print(f"  Body section candidate scores: {score_seq}; chosen template body=#{chosen}")
        distinct_cols = sorted({profile['cols'] for _, profile in body_scores})
        if len(distinct_cols) > 1:
            print(
                "  WARNING: template has multiple body-like sections with different column counts; "
                "selected representative body section by score. Visually confirm body columns."
            )
    print(f"  Section route: {'; '.join(route)}")
    if any(p['kind'] == 'body' for p in target_profiles) and section_col_count(body_info) <= 1:
        print(
            "  WARNING: no template body section with multi-column cols was found; "
            "body column layout needs visual confirmation"
        )
    return mapped


def first_template_profile_kind(template_profiles, kind):
    return next((profile for profile in template_profiles if profile.get('kind') == kind), None)


def find_target_body_start_child_index(root):
    body = root.find(w('body'))
    if body is None:
        return None
    visible_index = 0
    in_references = False
    english_context = {'mode': None, 'step': 0}
    citation_context = {'open': False}
    seen_front = False
    seen_front_anchor = False
    front_roles = {
        'title', 'author', 'affiliation', 'abstract', 'keywords',
        'english_title', 'english_author', 'english_affiliation',
        'english_abstract', 'english_keywords', 'metadata', 'citation_format',
    }
    body_start_roles = {'heading1', 'heading2', 'heading3', 'body'}
    for child_index, child in enumerate(list(body)):
        if child.tag != w('p'):
            continue
        text = get_text(child).strip()
        if not text:
            continue
        if starts_english_front_matter_block(text):
            english_context = {'mode': 'front_matter', 'step': 0}
            citation_context['open'] = False
            visible_index += 1
            continue
        role = classify_paragraph(
            text, visible_index, in_references,
            english_context=english_context,
            citation_context=citation_context,
        )
        if role in ('references_heading', 'reference_item'):
            in_references = True
        if role in front_roles:
            seen_front = True
            if role in ('abstract', 'keywords', 'english_abstract', 'english_keywords'):
                seen_front_anchor = True
        elif seen_front and role in body_start_roles and (seen_front_anchor or visible_index >= 4):
            return child_index
        visible_index += 1
    return None


def insert_section_break_before_child(body, child_index, section_info):
    if child_index is None or child_index <= 0:
        return False
    previous_paragraph = None
    for child in reversed(list(body)[:child_index]):
        if child.tag == w('p'):
            previous_paragraph = child
            break
    if previous_paragraph is None:
        return False
    pPr = get_or_add_child(previous_paragraph, w('pPr'), first=True)
    remove_children_by_local_name(pPr, {'sectPr'})
    sectPr = ET.Element(w('sectPr'))
    type_info = (section_info or {}).get('type') or {'val': 'continuous'}
    type_elem = ET.Element(w('type'))
    for key, value in type_info.items():
        type_elem.set(w(key), value)
    sectPr.append(type_elem)
    apply_page_setup_to_sectPr(sectPr, section_info or {})
    pPr.append(sectPr)
    return True


def maybe_insert_mixed_column_sections(target_dir, template_dir, template_infos, body_cols=None):
    if not template_dir or not template_infos or len(template_infos) <= 1:
        return {'inserted': 0, 'reason': 'template_has_no_mixed_sections'}
    doc_path = os.path.join(target_dir, 'word', 'document.xml')
    tree = ET.parse(doc_path)
    root = tree.getroot()
    body = root.find(w('body'))
    if body is None:
        return {'inserted': 0, 'reason': 'target_has_no_body'}
    existing_sectPrs = list(root.iter(w('sectPr')))
    if len(existing_sectPrs) != 1:
        return {'inserted': 0, 'reason': 'target_already_has_sections', 'target_sections': len(existing_sectPrs)}

    template_profiles = collect_section_profiles(template_dir, template_infos)
    if len(template_profiles) <= 1:
        return {'inserted': 0, 'reason': 'template_profiles_not_mixed'}
    front_profile = first_template_profile_kind(template_profiles, 'front') or template_profiles[0]
    body_profile, body_scores = select_representative_body_profile(
        template_profiles, preferred_body_cols=body_cols
    )
    if body_profile is None:
        return {'inserted': 0, 'reason': 'template_body_section_not_found'}
    front_cols = section_col_count(front_profile.get('info'))
    body_cols_count = section_col_count(body_profile.get('info'))
    if front_cols == body_cols_count:
        return {
            'inserted': 0,
            'reason': 'template_front_body_columns_match',
            'front_cols': front_cols,
            'body_cols': body_cols_count,
        }
    body_start_child = find_target_body_start_child_index(root)
    if body_start_child is None:
        print(
            "  WARNING: mixed-column template detected, but target body start was not clear; "
            "did not insert section break automatically"
        )
        return {
            'inserted': 0,
            'reason': 'target_body_start_not_found',
            'front_cols': front_cols,
            'body_cols': body_cols_count,
        }
    if not insert_section_break_before_child(body, body_start_child, front_profile.get('info')):
        return {
            'inserted': 0,
            'reason': 'section_break_insert_failed',
            'body_start_child': body_start_child,
        }
    write_xml(tree, doc_path)
    score_seq = '; '.join(
        f"#{profile['index']}:cols={profile['cols']},chars={profile['chars']},score={score:.1f}"
        for score, profile in body_scores
    )
    print(
        "  Inserted mixed-column section break before target body: "
        f"front cols={front_cols}, body cols={body_cols_count}, "
        f"target child index={body_start_child}, template body=#{body_profile['index']}"
    )
    if score_seq:
        print(f"  Mixed-column body section scores: {score_seq}")
    return {
        'inserted': 1,
        'front_cols': front_cols,
        'body_cols': body_cols_count,
        'body_start_child': body_start_child,
        'template_body_index': body_profile.get('index'),
    }


def maybe_insert_fallback_front_body_sections(target_dir, fallback_infos, body_cols=None):
    if not fallback_infos or int(body_cols or 1) < 2 or len(fallback_infos) < 2:
        return {'inserted': 0, 'reason': 'fallback_not_mixed_columns'}
    front_info = next((info for info in fallback_infos if section_col_count(info) <= 1), fallback_infos[0])
    body_info = next((info for info in reversed(fallback_infos) if section_col_count(info) >= 2), fallback_infos[-1])
    front_cols = section_col_count(front_info)
    body_cols_count = section_col_count(body_info)
    if front_cols == body_cols_count or body_cols_count < 2:
        return {
            'inserted': 0,
            'reason': 'fallback_front_body_columns_match',
            'front_cols': front_cols,
            'body_cols': body_cols_count,
        }
    doc_path = os.path.join(target_dir, 'word', 'document.xml')
    tree = ET.parse(doc_path)
    root = tree.getroot()
    body = root.find(w('body'))
    if body is None:
        return {'inserted': 0, 'reason': 'target_has_no_body'}
    existing_sectPrs = list(root.iter(w('sectPr')))
    if len(existing_sectPrs) != 1:
        return {
            'inserted': 0,
            'reason': 'target_already_has_sections',
            'target_sections': len(existing_sectPrs),
        }
    body_start_child = find_target_body_start_child_index(root)
    if body_start_child is None:
        print(
            "  WARNING: fallback double-column layout requested, but target body start was not clear; "
            "did not insert front/body section break automatically"
        )
        return {
            'inserted': 0,
            'reason': 'target_body_start_not_found',
            'front_cols': front_cols,
            'body_cols': body_cols_count,
        }
    if not insert_section_break_before_child(body, body_start_child, front_info):
        return {
            'inserted': 0,
            'reason': 'section_break_insert_failed',
            'body_start_child': body_start_child,
        }
    write_xml(tree, doc_path)
    print(
        "  Inserted fallback front/body section break before target body: "
        f"front cols={front_cols}, body cols={body_cols_count}, "
        f"target child index={body_start_child}"
    )
    return {
        'inserted': 1,
        'source': 'fallback_ooxml_front_body_columns',
        'front_cols': front_cols,
        'body_cols': body_cols_count,
        'body_start_child': body_start_child,
    }


def apply_page_setup(target_dir, sectPr_info, template_dir=None, body_cols=None):
    """Apply page setup to every section, including paragraph-level pPr/sectPr."""
    doc_path = os.path.join(target_dir, 'word', 'document.xml')
    template_infos = sectPr_info if isinstance(sectPr_info, list) else [sectPr_info]
    section_structure_stats = {}
    if template_dir:
        section_structure_stats = maybe_insert_mixed_column_sections(
            target_dir, template_dir, template_infos, body_cols=body_cols
        )
    elif body_cols and int(body_cols or 1) >= 2 and len(template_infos) > 1:
        section_structure_stats = maybe_insert_fallback_front_body_sections(
            target_dir, template_infos, body_cols=body_cols
        )

    tree = ET.parse(doc_path)
    root = tree.getroot()
    body = root.find(w('body'))
    if body is None:
        raise ValueError('document.xml has no w:body')

    sectPrs = list(root.iter(w('sectPr')))
    if not sectPrs:
        sectPrs = [ET.SubElement(body, w('sectPr'))]

    if template_dir and len(template_infos) != len(sectPrs):
        template_profiles = collect_section_profiles(template_dir, template_infos)
        target_profiles = collect_section_profiles(target_dir, [sectPr_to_info(s) for s in sectPrs])
        if len(target_profiles) == len(sectPrs):
            target_infos = select_section_infos_for_target_profiles(
                template_profiles, target_profiles, preferred_body_cols=body_cols
            )
        else:
            print(
                "  WARNING: section profile count did not match target sectPr count; "
                "falling back to conservative positional section routing"
            )
            target_infos = select_section_infos_for_target(template_infos, len(sectPrs))
    elif not template_dir and body_cols and int(body_cols or 1) >= 2 and len(template_infos) > 1 and len(sectPrs) > 1:
        front_info = next((info for info in template_infos if section_col_count(info) <= 1), template_infos[0])
        body_info = next((info for info in reversed(template_infos) if section_col_count(info) >= 2), template_infos[-1])
        target_infos = [front_info] + [body_info for _ in range(len(sectPrs) - 1)]
        print(
            "  Section route: applying fallback single-column front matter "
            f"and {section_col_count(body_info)}-column body sections"
        )
    elif not template_dir and body_cols and int(body_cols or 1) >= 2 and len(template_infos) > 1 and len(sectPrs) == 1:
        front_info = next((info for info in template_infos if section_col_count(info) <= 1), template_infos[0])
        target_infos = [front_info]
        print(
            "  WARNING: fallback double-column body was requested, but no safe body-start split was inserted; "
            "keeping the single-column front section for the one remaining section instead of applying double columns to the whole document"
        )
    else:
        target_infos = select_section_infos_for_target(template_infos, len(sectPrs))

    for sectPr, info in zip(sectPrs, target_infos):
        apply_page_setup_to_sectPr(sectPr, info)

    audit = audit_section_setup(root, expected_info=target_infos)
    bad = [item for item in audit if not item['matches']]
    print(f"  Applied page setup to {len(sectPrs)} section(s)")
    if bad:
        raise ValueError(f"page setup audit failed for section indexes {[item['index'] for item in bad]}")

    write_xml(tree, doc_path)
    return section_structure_stats


def rels_child_tag(rels_root):
    if rels_root.tag.startswith('{'):
        ns = rels_root.tag.split('}')[0].strip('{')
        return f'{{{ns}}}Relationship'
    if rels_root.get('xmlns') == PKG_REL_NS:
        return pkg_rel('Relationship')
    return 'Relationship'


def next_relationship_id(rels_root):
    max_rid = 0
    for rel in rels_root:
        rid = rel.get('Id', '')
        if rid.startswith('rId'):
            try:
                max_rid = max(max_rid, int(rid[3:]))
            except ValueError:
                pass
    return f'rId{max_rid + 1}'


def ensure_document_relationship(rels_root, rel_type, target):
    for rel in rels_root:
        if rel.get('Type') == rel_type and rel.get('Target') == target:
            return rel.get('Id')
    rel = ET.Element(rels_child_tag(rels_root))
    rid = next_relationship_id(rels_root)
    rel.set('Id', rid)
    rel.set('Type', rel_type)
    rel.set('Target', target)
    rels_root.append(rel)
    return rid


def remove_header_footer_refs(sectPr):
    removed = 0
    for child in list(sectPr):
        if local_name(child.tag) in ('headerReference', 'footerReference'):
            sectPr.remove(child)
            removed += 1
    return removed


def insert_header_footer_refs(sectPr, ref_ids):
    insert_idx = 0
    inserted = 0
    order = [
        ('header', 'even'),
        ('header', 'default'),
        ('header', 'first'),
        ('footer', 'even'),
        ('footer', 'default'),
        ('footer', 'first'),
    ]
    for kind, ref_type in order:
        rid = ref_ids.get((kind, ref_type))
        if not rid:
            continue
        tag = w('headerReference') if kind == 'header' else w('footerReference')
        ref = ET.Element(tag)
        ref.set(w('type'), ref_type)
        ref.set(r('id'), rid)
        sectPr.insert(insert_idx, ref)
        insert_idx += 1
        inserted += 1
    if any(key[1] == 'first' for key in ref_ids):
        if get_direct_child(sectPr, w('titlePg')) is None:
            type_elem = get_direct_child(sectPr, w('type'))
            title_pg = ET.Element(w('titlePg'))
            if type_elem is not None:
                sectPr.insert(list(sectPr).index(type_elem), title_pg)
            else:
                sectPr.insert(insert_idx, title_pg)
    return inserted


def iter_header_footer_xml_paths(doc_dir):
    word_dir = os.path.join(doc_dir, 'word')
    if not os.path.isdir(word_dir):
        return []
    paths = []
    for name in os.listdir(word_dir):
        if re.match(r'^(header|footer)\d+\.xml$', name):
            paths.append(os.path.join(word_dir, name))
    return sorted(paths)


def element_has_header_footer_background_anchor(elem):
    for anchor in elem.iter(f'{{{WP_NS}}}anchor'):
        if anchor.get('behindDoc') == '1':
            return True
        extent = anchor.find(f'{{{WP_NS}}}extent')
        if extent is not None:
            try:
                width_in = int(extent.get('cx', '0') or '0') / 914400.0
                height_in = int(extent.get('cy', '0') or '0') / 914400.0
            except Exception:
                width_in = 0
                height_in = 0
            if width_in >= 3.0 and height_in >= 1.0:
                return True
    return False


def paragraph_has_text_or_field(p):
    text = ''.join(t.text or '' for t in p.iter(w('t'))).strip()
    if text:
        return True
    field_tags = {'fldSimple', 'fldChar', 'instrText', 'tab', 'br'}
    return any(local_name(child.tag) in field_tags for child in p.iter())


def paragraph_is_header_footer_background_image_only(p):
    has_drawing = any(local_name(child.tag) in ('drawing', 'pict') for child in p.iter())
    if not has_drawing:
        return False
    if paragraph_has_text_or_field(p):
        return False
    return element_has_header_footer_background_anchor(p)


def remove_header_footer_background_watermarks(doc_dir):
    """Remove inherited header/footer background image watermarks from target package.

    The formatter preserves page content aggressively, but target manuscripts often
    carry proof/sample watermarks as behind-text header images. These are not paper
    content and can survive when the template has no header/footer to replace them.
    """
    stats = {
        'enabled': True,
        'parts_checked': 0,
        'paragraphs_removed': 0,
        'drawings_removed': 0,
        'parts_changed': [],
    }
    for path in iter_header_footer_xml_paths(doc_dir):
        try:
            tree = ET.parse(path)
        except Exception:
            continue
        root = tree.getroot()
        stats['parts_checked'] += 1
        removed_in_part = 0
        drawings_in_part = 0
        for parent in root.iter():
            for child in list(parent):
                if child.tag != w('p'):
                    continue
                if not paragraph_is_header_footer_background_image_only(child):
                    continue
                drawings_in_part += sum(1 for elem in child.iter() if local_name(elem.tag) in ('drawing', 'pict'))
                parent.remove(child)
                removed_in_part += 1
        if removed_in_part:
            write_xml(tree, path)
            stats['paragraphs_removed'] += removed_in_part
            stats['drawings_removed'] += drawings_in_part
            stats['parts_changed'].append(os.path.relpath(path, doc_dir))
    print(f"  Header/footer watermark cleanup: {stats}")
    return stats


def apply_headers_footers(target_dir, template_dir, hf_map):
    """Replace headers and footers in every target section with template refs."""
    target_word = os.path.join(target_dir, 'word')
    template_word = os.path.join(template_dir, 'word')
    target_rels = os.path.join(target_word, '_rels')

    target_doc_path = os.path.join(target_dir, 'word', 'document.xml')
    tree = ET.parse(target_doc_path)
    root = tree.getroot()
    body = root.find(w('body'))
    if body is None:
        raise ValueError('document.xml has no w:body')
    sectPrs = list(root.iter(w('sectPr')))
    if not sectPrs:
        sectPrs = [ET.SubElement(body, w('sectPr'))]

    rels_path = os.path.join(target_rels, 'document.xml.rels')
    rels_tree = ET.parse(rels_path)
    rels_root = rels_tree.getroot()

    media_dir = os.path.join(target_word, 'media')
    os.makedirs(media_dir, exist_ok=True)
    max_img = 0
    for f in os.listdir(media_dir):
        if f.startswith('image'):
            num_str = ''
            for c in f[5:]:
                if c.isdigit():
                    num_str += c
                else:
                    break
            if num_str:
                max_img = max(max_img, int(num_str))

    new_img_num = max_img + 1
    ref_ids = {}

    for kind in ('header', 'footer'):
        for hf_type, template_file in hf_map.get(kind, {}).items():
            template_file_path = os.path.join(template_word, template_file)
            if not os.path.exists(template_file_path):
                continue

            target_file = os.path.basename(template_file)
            rel_type = f'{R_NS}/header' if kind == 'header' else f'{R_NS}/footer'
            ref_ids[(kind, hf_type)] = ensure_document_relationship(
                rels_root, rel_type, target_file
            )

            shutil.copy2(template_file_path, os.path.join(target_word, target_file))

            template_rels_file = template_file + '.rels'
            template_rels_path = os.path.join(template_word, '_rels', template_rels_file)
            target_rels_path_file = os.path.join(target_rels, target_file + '.rels')

            if os.path.exists(template_rels_path):
                hf_rels_tree = ET.parse(template_rels_path)
                hf_rels_root = hf_rels_tree.getroot()

                for rel in hf_rels_root:
                    target_attr = rel.get('Target', '')
                    if target_attr.startswith('media/'):
                        img_file = os.path.basename(target_attr)
                        template_img_path = os.path.join(template_word, 'media', img_file)
                        if os.path.exists(template_img_path):
                            ext = os.path.splitext(img_file)[1]
                            new_img_name = f'image{new_img_num}{ext}'
                            shutil.copy2(template_img_path, os.path.join(media_dir, new_img_name))
                            rel.set('Target', f'media/{new_img_name}')
                            new_img_num += 1

                write_xml(hf_rels_tree, target_rels_path_file)

    removed = 0
    inserted = 0
    for sectPr in sectPrs:
        removed += remove_header_footer_refs(sectPr)
        inserted += insert_header_footer_refs(sectPr, ref_ids)

    print(
        f"  Applied headers/footers to {len(sectPrs)} section(s): "
        f"removed {removed} old refs, inserted {inserted} template refs"
    )

    write_xml(rels_tree, rels_path)
    write_xml(tree, target_doc_path)


def copy_support_files(target_dir, template_dir):
    """Copy supporting files: settings.xml, fontTable.xml, theme1.xml."""
    target_word = os.path.join(target_dir, 'word')
    template_word = os.path.join(template_dir, 'word')

    files_to_copy = ['settings.xml', 'fontTable.xml']
    for f in files_to_copy:
        src = os.path.join(template_word, f)
        dst = os.path.join(target_word, f)
        if os.path.exists(src):
            shutil.copy2(src, dst)

    # Theme
    theme_src = os.path.join(template_word, 'theme', 'theme1.xml')
    theme_dst_dir = os.path.join(target_word, 'theme')
    if os.path.exists(theme_src):
        os.makedirs(theme_dst_dir, exist_ok=True)
        shutil.copy2(theme_src, os.path.join(theme_dst_dir, 'theme1.xml'))


def write_xml(tree, path):
    """Write XML tree with proper declaration."""
    with open(path, 'wb') as f:
        f.write(b"<?xml version='1.0' encoding='UTF-8' standalone='yes'?>\n")
        if is_relationship_part(path, tree.getroot()):
            normalize_relationship_part(tree.getroot())
            ET.register_namespace('', PKG_REL_NS)
            tree.write(f, encoding='UTF-8', xml_declaration=False)
        else:
            tree.write(f, encoding='UTF-8', xml_declaration=False)


def is_relationship_part(path, root):
    """Return true for package relationship parts such as word/_rels/*.rels."""
    if str(path).endswith('.rels'):
        return True
    return root is not None and root.tag == pkg_rel('Relationships')


def normalize_relationship_part(root):
    """Keep .rels parts in the default package relationship namespace.

    LibreOffice can reject otherwise valid DOCX packages when relationship parts
    are serialized as ns0:Relationships/ns0:Relationship.
    """
    if root is None:
        return
    for elem in root.iter():
        name = local_name(elem.tag)
        if name in ('Relationships', 'Relationship'):
            elem.tag = pkg_rel(name)
        if 'xmlns' in elem.attrib and elem.attrib.get('xmlns') == PKG_REL_NS:
            del elem.attrib['xmlns']


def audit_docx_package(docx_path):
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qa_audit.py')
    if not os.path.exists(script_path):
        return {'path': os.path.abspath(docx_path), 'error': 'qa_audit.py not found'}
    with tempfile.NamedTemporaryFile('r+', suffix='.json', delete=False) as tmp:
        audit_path = tmp.name
    try:
        cmd = [sys.executable, script_path, docx_path, '--out-json', audit_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            return {
                'path': os.path.abspath(docx_path),
                'error': result.stderr.strip() or result.stdout.strip() or 'qa audit failed',
            }
        with open(audit_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    finally:
        try:
            os.unlink(audit_path)
        except OSError:
            pass


def run_explicit_postprocess(input_docx, output_docx, ops_json, report_out=None):
    if not ops_json:
        return {'enabled': False, 'skipped': True, 'reason': 'no_explicit_postprocess_json'}
    script_path = os.path.join(SCRIPT_DIR, 'explicit_postprocess.py')
    if not os.path.exists(script_path):
        return {'enabled': False, 'ok': False, 'error': 'explicit_postprocess.py not found'}
    cmd = [
        sys.executable,
        script_path,
        input_docx,
        output_docx,
        '--ops-json',
        ops_json,
    ]
    if report_out:
        cmd.extend(['--report-out', report_out])
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    parsed = None
    if report_out and os.path.exists(report_out):
        try:
            with open(report_out, 'r', encoding='utf-8') as f:
                parsed = json.load(f)
        except (OSError, json.JSONDecodeError):
            parsed = None
    if parsed is None:
        try:
            parsed = json.loads((result.stdout or '').strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError):
            parsed = {}
    parsed['enabled'] = bool(parsed.get('enabled'))
    parsed['ok'] = result.returncode == 0
    parsed['ops_json'] = os.path.abspath(ops_json)
    parsed['report_out'] = os.path.abspath(report_out) if report_out else None
    parsed['stdout_tail'] = (result.stdout or '')[-2000:]
    parsed['stderr_tail'] = (result.stderr or '')[-2000:]
    if result.returncode != 0:
        parsed['error'] = result.stderr.strip() or result.stdout.strip() or 'explicit postprocess failed'
    return parsed


def explicit_postprocess_result_lines(stats):
    lines = []
    for op in (stats or {}).get('operations') or []:
        if not isinstance(op, dict):
            continue
        name = op.get('display_name') or op.get('operation') or 'unknown'
        parts = []
        if op.get('target_scope'):
            parts.append(f'scope={op.get("target_scope")}')
        for key in (
            'moved_groups', 'changed_markers', 'changed_paragraphs', 'changed',
            'added', 'renumbered', 'skipped', 'skipped_complex'
        ):
            if key in op:
                parts.append(f'{key}={op.get(key)}')
        if op.get('warning'):
            parts.append(f'warning={op.get("warning")}')
        for warning in (op.get('warnings') or [])[:5]:
            parts.append(f'warning={warning}')
        if not parts and op.get('skipped'):
            parts.append('skipped=true')
        lines.append(f'{name}: ' + (', '.join(parts) if parts else 'completed'))
    return lines


def print_explicit_postprocess_summary(stats):
    if not stats or not stats.get('enabled'):
        print("Postprocess results: disabled or skipped")
        return
    lines = explicit_postprocess_result_lines(stats)
    print("Postprocess results:")
    if not lines:
        print("  - no operations executed")
    for line in lines:
        print(f"  - {line}")
    for warning in (stats.get('warnings') or [])[:20]:
        print(f"  WARNING: {warning}")


RENDER_ENGINE_PRIORITY = ('word', 'libreoffice')
TEXT_RULE_SOURCE_TYPES = {
    'text_rules',
    'plain_text_rules',
    'ocr_text',
    'ocr_text_rules',
    'image_text',
    'image_text_rules',
    'website_text',
    'website_text_rules',
    'screenshot_text',
    'screenshot_text_rules',
    'converted_docx_template',
    'pdf_visual',
    'pdf_visual_inference',
    'pdf_text_visual_hybrid',
    'visual_template',
}
VISUAL_RULE_SOURCE_TYPES = {
    'docx_template',
    'native_docx_template',
    'converted_docx_template',
    'pdf_visual',
    'pdf_visual_inference',
    'pdf_text_visual_hybrid',
    'visual_template',
}


def run_render_qa(docx_path, output_dir, engine='word'):
    render_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'render_docx.py')
    if not os.path.exists(render_path):
        return {'enabled': False, 'ok': False, 'error': 'render_docx.py not found'}
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        sys.executable,
        render_path,
        docx_path,
        '--output_dir',
        output_dir,
        '--engine',
        engine,
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    pages = []
    if os.path.isdir(output_dir):
        pages = sorted(name for name in os.listdir(output_dir) if re.match(r'page-\d+\.png$', name))
    combined_log = (result.stdout or '') + '\n' + (result.stderr or '')
    failure_kind = None
    if result.returncode != 0 or not pages:
        if engine == 'word' and (
            'Microsoft Word automation via AppleScript is only available' in combined_log
            or 'osascript command is not available' in combined_log
        ):
            failure_kind = 'word_render_unavailable'
        elif engine == 'word':
            failure_kind = 'word_render_failed'
        elif 'source file could not be loaded' in combined_log:
            failure_kind = 'libreoffice_source_load_failed'
        elif 'command not found: soffice' in combined_log or (
            'No such file or directory' in combined_log and 'soffice' in combined_log
        ):
            failure_kind = 'soffice_missing'
        elif 'PDF rasterization requires pdf2image or pdftoppm' in combined_log:
            failure_kind = 'rasterizer_missing'
        elif 'Failed to read PDF page size' in combined_log:
            failure_kind = 'pdfinfo_missing'
        else:
            failure_kind = 'render_failed'
    return {
        'enabled': True,
        'ok': result.returncode == 0 and bool(pages),
        'output_dir': os.path.abspath(output_dir),
        'page_png_count': len(pages),
        'pages': pages[:20],
        'renderer_invocation': 'direct_cloud_toolchain',
        'engine': engine,
        'failure_kind': failure_kind,
        'stdout_tail': (result.stdout or '')[-2000:],
        'stderr_tail': (result.stderr or '')[-2000:],
        'error': None if result.returncode == 0 and pages else 'render failed or produced no page PNGs',
    }


def default_render_qa_dir(output_path):
    base_dir = os.path.dirname(os.path.abspath(output_path)) or os.getcwd()
    stem = os.path.splitext(os.path.basename(output_path))[0]
    return os.path.join(base_dir, f'{stem}_render_qa')


def normalize_format_source_type(value):
    value = str(value or '').strip().lower().replace('-', '_')
    aliases = {
        'ocr': 'ocr_text_rules',
        'ocr_text': 'ocr_text_rules',
        'image': 'image_text_rules',
        'image_text': 'image_text_rules',
        'screenshot': 'screenshot_text_rules',
        'screenshot_text': 'screenshot_text_rules',
        'website': 'website_text_rules',
        'website_text': 'website_text_rules',
        'text': 'text_rules',
        'plain_text': 'plain_text_rules',
        'rules': 'text_rules',
        'pdf': 'text_rules',
        'pdf_visual': 'pdf_visual_inference',
        'pdf_text_visual': 'pdf_text_visual_hybrid',
        'pdf_rules_with_visual_supplement': 'pdf_text_visual_hybrid',
        'docx': 'docx_template',
        'word': 'docx_template',
        'native_docx': 'native_docx_template',
        'doc': 'converted_docx_template',
        'dot': 'converted_docx_template',
        'legacy_doc': 'converted_docx_template',
        'legacy_dot': 'converted_docx_template',
        'converted_doc': 'converted_docx_template',
        'converted_dot': 'converted_docx_template',
        'blank': 'blank_carrier_template',
        'blank_docx': 'blank_carrier_template',
        'blank_template': 'blank_carrier_template',
        'carrier': 'blank_carrier_template',
        'carrier_template': 'blank_carrier_template',
    }
    return aliases.get(value, value)


def should_skip_render_compare_for_source(source_type):
    return normalize_format_source_type(source_type) in TEXT_RULE_SOURCE_TYPES


def skipped_render_compare_qa(source_type, output_dir):
    source_type = normalize_format_source_type(source_type) or 'unspecified'
    return {
        'enabled': False,
        'ok': None,
        'skipped': True,
        'skip_reason': 'format_source_text_rules',
        'source_type': source_type,
        'output_dir': os.path.abspath(output_dir),
        'message': (
            'Target-before/final visual comparison was skipped because the target '
            'format came from text/OCR rules rather than a visual template. '
            'Large expected layout changes would make visual diff misleading.'
        ),
    }


def page_sort_key(name):
    match = re.match(r'page-(\d+)\.png$', name)
    return int(match.group(1)) if match else 10 ** 9


def list_render_pages(render_dir):
    if not os.path.isdir(render_dir):
        return []
    return sorted(
        [name for name in os.listdir(render_dir) if re.match(r'page-\d+\.png$', name)],
        key=page_sort_key,
    )


def png_dimensions(path):
    try:
        with open(path, 'rb') as f:
            header = f.read(24)
        if len(header) >= 24 and header[:8] == b'\x89PNG\r\n\x1a\n':
            width = int.from_bytes(header[16:20], 'big')
            height = int.from_bytes(header[20:24], 'big')
            return [width, height]
    except Exception:
        pass
    return None


def compare_rendered_page_sets(before_dir, final_dir):
    before_pages = list_render_pages(before_dir)
    final_pages = list_render_pages(final_dir)
    max_pages = max(len(before_pages), len(final_pages))
    changed_pages = []
    missing_pages = []
    dimension_changes = []
    for page_no in range(1, max_pages + 1):
        name = f'page-{page_no}.png'
        before_path = os.path.join(before_dir, name)
        final_path = os.path.join(final_dir, name)
        if not os.path.exists(before_path) or not os.path.exists(final_path):
            changed_pages.append(page_no)
            missing_pages.append({
                'page': page_no,
                'before_exists': os.path.exists(before_path),
                'final_exists': os.path.exists(final_path),
            })
            continue
        before_dim = png_dimensions(before_path)
        final_dim = png_dimensions(final_path)
        if before_dim != final_dim:
            dimension_changes.append({
                'page': page_no,
                'before': before_dim,
                'final': final_dim,
            })
        try:
            with open(before_path, 'rb') as f:
                before_bytes = f.read()
            with open(final_path, 'rb') as f:
                final_bytes = f.read()
            if before_bytes != final_bytes:
                changed_pages.append(page_no)
        except Exception:
            changed_pages.append(page_no)
    return {
        'before_page_count': len(before_pages),
        'final_page_count': len(final_pages),
        'changed_pages': changed_pages[:80],
        'changed_page_count': len(changed_pages),
        'missing_pages': missing_pages[:20],
        'dimension_changes': dimension_changes[:20],
        'page_count_changed': len(before_pages) != len(final_pages),
        'comparison_note': (
            'Changed pages are expected after formatting; use this gate to confirm rendering completed, '
            'page counts, page dimensions, and missing pages.'
        ),
    }


def run_render_compare_qa(before_docx_path, final_docx_path, output_dir):
    """Render target-before and final DOCX and compare page PNG sets.

    This gate is mandatory for normal formatting runs. It directly invokes the
    configured cloud render toolchain and records failure as QA risk instead
    of performing environment setup actions.
    """
    before_dir = os.path.join(output_dir, 'target_before')
    final_dir = os.path.join(output_dir, 'final')
    result = {
        'enabled': True,
        'ok': False,
        'output_dir': os.path.abspath(output_dir),
        'before_render': None,
        'final_render': None,
        'comparison': None,
        'engine': None,
        'attempted_engines': [],
        'error': None,
    }
    os.makedirs(output_dir, exist_ok=True)
    failures = []
    for engine in RENDER_ENGINE_PRIORITY:
        engine_output_dir = os.path.join(output_dir, engine)
        before_dir = os.path.join(engine_output_dir, 'target_before')
        final_dir = os.path.join(engine_output_dir, 'final')
        print(f"Rendering target-before DOCX for QA with {engine}: {before_dir}")
        before_render = run_render_qa(before_docx_path, before_dir, engine=engine)
        print(f"Rendering final DOCX for QA with {engine}: {final_dir}")
        final_render = run_render_qa(final_docx_path, final_dir, engine=engine)
        attempt = {
            'engine': engine,
            'before_ok': bool(before_render.get('ok')),
            'final_ok': bool(final_render.get('ok')),
            'before_failure_kind': before_render.get('failure_kind'),
            'final_failure_kind': final_render.get('failure_kind'),
        }
        result['attempted_engines'].append(attempt)
        if before_render.get('ok') and final_render.get('ok'):
            comparison = compare_rendered_page_sets(before_dir, final_dir)
            result['before_render'] = before_render
            result['final_render'] = final_render
            result['comparison'] = comparison
            result['engine'] = engine
            result['ok'] = True
            return result
        if not before_render.get('ok'):
            failures.append({
                'engine': engine,
                'side': 'target_before',
                'failure_kind': before_render.get('failure_kind'),
                'error': before_render.get('error'),
            })
        if not final_render.get('ok'):
            failures.append({
                'engine': engine,
                'side': 'final',
                'failure_kind': final_render.get('failure_kind'),
                'error': final_render.get('error'),
            })
    result['before_render'] = None
    result['final_render'] = None
    result['failures'] = failures
    result['error'] = 'render comparison failed because no render engine could render both DOCX files'
    return result


def format_document(template_path, target_path, output_path,
                    apply_page=True, apply_header=True, apply_style=True, apply_support=True,
                    style_mode='role', clean_direct=True, rules_json=None,
                    style_spec_out=None, style_spec_in=None,
                    role_map_out=None, role_map_in=None,
                    superscript_map_out=None, superscript_map_in=None,
                    equation_layout_map_out=None, equation_layout_map_in=None,
                    table_format_map_out=None, table_format_map_in=None,
                    reference_numbering_map_out=None, reference_numbering_map_in=None,
                    format_report_out=None, body_cols=None, preserve_table_width=True,
                    allow_legacy_word_conversion=True, qa_report_out=None,
                    render_qa_dir=None, format_source_type=None,
                    explicit_postprocess_json=None, explicit_postprocess_report_out=None):
    """Main function: apply template styles to target document.

    Args:
        template_path: Path to template DOCX (journal sample)
        target_path: Path to target DOCX (paper to format)
        output_path: Path for output DOCX
        apply_page: Apply page setup (margins, etc.)
        apply_header: Apply headers/footers
        apply_style: Apply template role/name styles
        apply_support: Apply settings, fontTable, theme
        style_mode: 'role' classifies target content; 'name' matches w:name
        clean_direct: Remove direct paragraph/run formatting that overrides styles
        rules_json: Optional user rule JSON. User rules override template text rules.
        style_spec_out: Optional path for intermediate style spec JSON
        style_spec_in: Optional path to reuse an existing intermediate style spec JSON
        role_map_out: Optional path for target paragraph role mapping JSON
        role_map_in: Optional path to reuse a reviewed target paragraph role mapping JSON
        superscript_map_out: Optional path for template run-level superscript map JSON
        superscript_map_in: Optional path to reuse reviewed superscript map JSON
        equation_layout_map_out: Optional path for template equation tab layout map JSON
        equation_layout_map_in: Optional path to reuse reviewed equation layout map JSON
        table_format_map_out: Optional path for template table body formatting map JSON
        table_format_map_in: Optional path to reuse reviewed table body formatting map JSON
        reference_numbering_map_out: Optional path for template reference-list numbering map JSON
        reference_numbering_map_in: Optional path to reuse reviewed reference-list numbering map JSON
        format_report_out: Optional path for internal formatting report JSON
        body_cols: Optional preferred body column count for section routing
        preserve_table_width: Preserve target table tblW unless template width is explicit
        allow_legacy_word_conversion: Convert .doc/.dot inputs to temporary .docx when possible.
            The flag is kept for compatibility; converted evidence remains lower confidence.
        qa_report_out: Optional path for structural QA report JSON
        render_qa_dir: Optional directory for mandatory target-before/final render comparison QA
        format_source_type: Evidence source for formatting rules. Use text_rules/ocr_text_rules
            to skip misleading target-before/final visual comparison.
        explicit_postprocess_json: Optional explicit opt-in content/structure postprocess operations JSON.
        explicit_postprocess_report_out: Optional path for explicit postprocess report JSON.

    Returns:
        Path to formatted document
    """
    if role_map_in and not style_spec_in and style_mode != 'name':
        raise ValueError(
            "--role-map-in requires --style-spec-in for locked bridge formatting. "
            "Pass both reviewed JSON files so paragraph roles and role styles are both fixed."
        )

    # Create temp directories
    with tempfile.TemporaryDirectory() as tmpdir:
        template_dir = os.path.join(tmpdir, 'template')
        target_dir = os.path.join(tmpdir, 'target')
        template_path, target_path, legacy_word_sources = normalize_word_inputs(
            template_path,
            target_path,
            tmpdir,
            allow_legacy_word_conversion=allow_legacy_word_conversion,
        )
        qa_report = {
            'template_audit': audit_docx_package(template_path),
            'target_before_audit': audit_docx_package(target_path),
        }

        # Extract both documents
        print(f"Extracting template: {template_path}")
        extract_docx(template_path, template_dir)
        print(f"Extracting target: {target_path}")
        extract_docx(target_path, target_dir)

        user_rules = load_user_rules(rules_json)
        rules_metadata = load_rules_metadata(rules_json)
        auto_postprocess_operations = load_rules_postprocess_operations(rules_json)
        auto_postprocess_json = None
        template_legacy_sources = [
            item for item in legacy_word_sources or []
            if item.get('role') == 'template'
        ]
        inferred_source_type = 'converted_docx_template' if template_legacy_sources else 'docx_template'
        effective_format_source_type = normalize_format_source_type(
            format_source_type
            or rules_metadata.get('format_source_type')
            or rules_metadata.get('source_type')
            or inferred_source_type
        )
        fallback_columns_hint = metadata_fallback_columns(rules_metadata, default=body_cols)
        non_docx_text_only_route = effective_format_source_type in NON_DOCX_TEXT_ONLY_SOURCE_TYPES
        raw_user_rules = user_rules
        user_rules = sanitize_visual_only_rules(user_rules, effective_format_source_type)
        rules_diagnostics = rules_schema_diagnostics(raw_user_rules, user_rules)
        visual_rule_sanitized = {}
        for role, raw_rule in (raw_user_rules or {}).items():
            if role not in ROLE_STYLE_IDS:
                continue
            removed = sorted(set((raw_rule or {}).keys()) - set((user_rules.get(role) or {}).keys()))
            if removed:
                visual_rule_sanitized[role] = removed
        template_text_rules = extract_template_text_rules(template_dir)
        metadata_text_rules = extract_text_rules_from_source_metadata(rules_metadata)
        combined_template_text_rules = merge_text_rules(template_text_rules, metadata_text_rules)
        text_rules = merge_text_rules(combined_template_text_rules, user_rules)
        if is_blank_carrier_template_source(
            template_dir,
            source_type=effective_format_source_type,
            text_rules=text_rules,
        ):
            effective_format_source_type = 'blank_carrier_template'
            non_docx_text_only_route = effective_format_source_type in NON_DOCX_TEXT_ONLY_SOURCE_TYPES
            user_rules = sanitize_visual_only_rules(raw_user_rules, effective_format_source_type)
            rules_diagnostics = rules_schema_diagnostics(raw_user_rules, user_rules)
            metadata_text_rules = extract_text_rules_from_source_metadata(rules_metadata)
            combined_template_text_rules = merge_text_rules(template_text_rules, metadata_text_rules)
            text_rules = merge_text_rules(combined_template_text_rules, user_rules)
            visual_rule_sanitized = {}
            for role, raw_rule in (raw_user_rules or {}).items():
                if role not in ROLE_STYLE_IDS:
                    continue
                removed = sorted(set((raw_rule or {}).keys()) - set((user_rules.get(role) or {}).keys()))
                if removed:
                    visual_rule_sanitized[role] = removed
        template_source_paths = [
            item.get('path')
            for item in template_legacy_sources
            if item.get('path')
        ]
        source_column_resolution = resolve_fallback_columns_for_source(
            template_dir,
            {
                **rules_metadata,
                'format_source_path': template_source_paths[0] if template_source_paths else None,
                'legacy_word_sources': template_legacy_sources,
            },
            default=body_cols,
            allow_docx_detection=non_docx_text_only_route or effective_format_source_type in LOW_CONFIDENCE_FORMAT_SOURCE_TYPES,
        )
        website_default_single_columns = False
        website_explicit_columns = website_explicit_column_count(rules_metadata) if is_website_format_source(effective_format_source_type) else None
        if website_explicit_columns is not None and body_cols is None:
            source_column_resolution = website_explicit_column_resolution(website_explicit_columns)
            fallback_columns_hint = source_column_resolution['columns']
        if (
            is_website_format_source(effective_format_source_type)
            and body_cols is None
            and website_explicit_columns is None
            and not website_has_explicit_column_rule(rules_metadata)
        ):
            source_column_resolution = website_default_single_column_resolution(
                source_column_resolution,
                prior_columns=source_column_resolution.get('columns'),
            )
            fallback_columns_hint = 1
            website_default_single_columns = True
        if non_docx_text_only_route and fallback_columns_hint is None:
            fallback_columns_hint = source_column_resolution['columns']
        qa_report['format_source'] = {
            'type': effective_format_source_type,
            'evidence_priority': evidence_priority_for_source(effective_format_source_type),
            'unified_evidence_route': True,
            'rules_metadata': rules_metadata,
            'rules_json': os.path.abspath(rules_json) if rules_json else None,
            'legacy_word_sources': legacy_word_sources,
            'visual_only_rule_sanitized': visual_rule_sanitized,
            'rules_schema_diagnostics': rules_diagnostics,
            'metadata_text_rules_roles': sorted(metadata_text_rules.keys()),
            'blank_carrier_template': effective_format_source_type == 'blank_carrier_template',
            'non_docx_text_only_route': non_docx_text_only_route,
            'fallback_columns': fallback_columns_hint,
            'fallback_column_resolution': source_column_resolution,
            'website_unspecified_columns_default_single': website_default_single_columns,
            'source_column_detection': rules_metadata.get('source_column_detection'),
            'non_docx_standard_fallback': bool(non_docx_text_only_route),
        }
        if auto_postprocess_operations:
            auto_postprocess_json = write_auto_postprocess_ops(auto_postprocess_operations, tmpdir)
            qa_report['format_source']['auto_postprocess_operations'] = auto_postprocess_operations
        superscript_map = load_superscript_map(superscript_map_in)
        if superscript_map is None:
            if non_docx_text_only_route:
                superscript_map = empty_superscript_map()
            else:
                superscript_map = extract_superscript_map(template_dir)
        write_superscript_map(superscript_map, superscript_map_out)
        equation_layout_map = load_equation_layout_map(equation_layout_map_in)
        if equation_layout_map is None:
            if non_docx_text_only_route:
                equation_layout_map = fallback_equation_layout_map()
            else:
                equation_layout_map = extract_equation_layout_map(template_dir)
        write_equation_layout_map(equation_layout_map, equation_layout_map_out)
        table_format_map = load_table_format_map(table_format_map_in)
        if table_format_map is None:
            if non_docx_text_only_route:
                table_language = choose_fallback_language(
                    template_dir,
                    text_rules=text_rules,
                    source_type=effective_format_source_type,
                    target_dir=target_dir,
                )
                table_format_map = fallback_table_format_map(
                    table_language,
                    fallback_columns_hint or 1,
                )
            else:
                table_format_map = extract_table_format_map(template_dir)
        write_table_format_map(table_format_map, table_format_map_out)
        reference_numbering_map = load_reference_numbering_map(reference_numbering_map_in)
        if reference_numbering_map is None:
            if non_docx_text_only_route:
                reference_numbering_map = (
                    reference_numbering_map_from_rules_metadata(rules_metadata)
                    or fallback_reference_numbering_map()
                )
            else:
                reference_numbering_map = extract_reference_numbering_map(template_dir)
        write_reference_numbering_map(reference_numbering_map, reference_numbering_map_out)
        style_spec = None
        role_map = []
        superscript_stats = {}
        explicit_postprocess_stats = {}
        equation_layout_stats = {}
        table_format_stats = {}
        reference_numbering_stats = {}
        section_structure_stats = {}
        column_object_fit_stats = {}
        high_inline_line_spacing_stats = {}
        abstract_keyword_label_stats = {}
        metadata_layout_stats = {}
        header_footer_watermark_stats = {'enabled': False}
        numbering_audit = {}
        format_conformance_stats = {}

        # Extract template info
        if apply_page:
            if non_docx_text_only_route:
                fallback_language_for_page = choose_fallback_language(
                    template_dir,
                    text_rules=text_rules,
                    source_type=effective_format_source_type,
                    target_dir=target_dir,
                )
                fallback_columns_for_page = fallback_columns_hint or 1
                sectPr_infos = fallback_front_body_section_infos(
                    fallback_language_for_page,
                    fallback_columns_for_page,
                )
                if sectPr_infos:
                    print(
                        "Applying standard fallback page setup for non-DOCX text route: "
                        f"{fallback_language_for_page}, columns={fallback_columns_for_page}"
                    )
                    section_structure_stats = apply_page_setup(
                        target_dir, sectPr_infos,
                        template_dir=None,
                        body_cols=fallback_columns_for_page,
                    )
                    qa_report['format_source']['fallback_page_setup'] = {
                        'language': fallback_language_for_page,
                        'columns': fallback_columns_for_page,
                        'variant': fallback_variant_key(fallback_language_for_page, fallback_columns_for_page),
                    }
            else:
                print("Extracting page setup from template...")
                sectPr_infos = get_sectPr_infos(template_dir)
                if sectPr_infos:
                    print(f"  Template sections: {len(sectPr_infos)}")
                    print(f"  Applying page setup primary margins: {sectPr_infos[-1].get('pgMar', {})}")
                    section_structure_stats = apply_page_setup(
                        target_dir, sectPr_infos,
                        template_dir=template_dir,
                        body_cols=body_cols,
                    )

        header_footer_watermark_stats = remove_header_footer_background_watermarks(target_dir)
        if header_footer_watermark_stats.get('paragraphs_removed') or header_footer_watermark_stats.get('drawings_removed'):
            qa_report['format_source']['header_footer_watermark_cleanup'] = header_footer_watermark_stats

        if apply_header and not non_docx_text_only_route:
            print("Extracting headers/footers from template...")
            hf_map = get_header_footer_map(template_dir)
            if hf_map['header'] or hf_map['footer']:
                print(f"  Headers: {list(hf_map['header'].keys())}")
                print(f"  Footers: {list(hf_map['footer'].keys())}")
                apply_headers_footers(target_dir, template_dir, hf_map)
        elif apply_header and non_docx_text_only_route:
            print("Skipping header/footer migration for non-DOCX text route; source headers are low confidence.")
            qa_report['format_source']['headers_footers_skipped'] = 'non_docx_text_only_route'

        if apply_style:
            print("Preparing style route...")
            warn_style_route(style_mode, clean_direct, text_rules, effective_format_source_type)
            if style_mode == 'name':
                print("Extracting all styles from template by w:name...")
                all_styles = get_all_styles(template_dir)
                if all_styles:
                    print(f"  Found {len(all_styles)} style definitions")
                    apply_all_styles(target_dir, all_styles)
                if clean_direct:
                    print("Cleaning direct formatting after name-based style import...")
                role_map = apply_role_styles_to_document(
                    target_dir, {}, clean_direct=clean_direct,
                    role_map_out=role_map_out, role_map_in=role_map_in
                )
                format_conformance_stats = enforce_role_format_conformance(
                    target_dir, style_spec, role_map, clean_direct=clean_direct
                )
                if not format_conformance_stats.get('enabled'):
                    print("  Format conformance QA skipped: no style_spec available in name-based mode")
                if should_apply_abstract_keyword_label_defaults(effective_format_source_type):
                    abstract_keyword_label_stats = apply_abstract_keyword_label_bold(target_dir, role_map)
                reference_numbering_stats = apply_reference_numbering_map_to_document(
                    target_dir, reference_numbering_map, role_map
                )
                table_format_stats = apply_table_format_map_to_document(
                    target_dir, table_format_map,
                    preserve_table_width=preserve_table_width,
                )
                column_object_fit_stats = fit_wide_objects_to_columns(target_dir)
                equation_layout_stats = apply_equation_layout_map_to_document(target_dir, equation_layout_map)
                superscript_stats = apply_superscript_map_to_document(target_dir, superscript_map, role_map)
                if should_apply_chinese_metadata_tab_layout(effective_format_source_type):
                    metadata_layout_stats = apply_chinese_metadata_tab_layout(target_dir)
                high_inline_line_spacing_stats = protect_high_inline_content_line_spacing(target_dir)
            else:
                if style_spec_in:
                    print(f"Loading intermediate style spec: {style_spec_in}")
                    style_spec = load_style_spec(style_spec_in)
                else:
                    print("Building intermediate style spec from template...")
                    style_spec = build_style_spec(
                        template_dir,
                        text_rules=text_rules,
                        source_metadata={
                            'source_type': effective_format_source_type,
                            'source_confidence': 'lower' if template_legacy_sources else 'normal',
                            'fallback_columns': fallback_columns_hint,
                            'fallback_language': rules_metadata.get('fallback_language'),
                            'source_column_detection': rules_metadata.get('source_column_detection'),
                            'fallback_column_resolution': source_column_resolution,
                            'format_source_path': template_source_paths[0] if template_source_paths else None,
                            'non_docx_text_only_route': non_docx_text_only_route,
                            'non_docx_standard_fallback': bool(non_docx_text_only_route),
                            'legacy_word_sources': legacy_word_sources,
                            'notes': [
                                'All usable source formats are fused into this role-based style_spec before target formatting.'
                            ],
                        },
                        target_dir=target_dir,
                    )
                style_spec, fallback_materialized = materialize_low_confidence_fallback_in_style_spec(
                    style_spec,
                    source_type=effective_format_source_type,
                    target_dir=target_dir,
                )
                if fallback_materialized:
                    qa_report['format_source']['fallback_materialized'] = fallback_materialized
                print(f"  Style spec roles: {sorted(style_spec.get('roles', {}).keys())}")
                audit_style_spec_preflight(style_spec)
                write_style_spec(style_spec, style_spec_out)
                install_result = install_style_spec(
                    target_dir, style_spec, template_dir=template_dir,
                    reference_numbering_map=reference_numbering_map,
                )
                blank_defaults = materialize_blank_carrier_defaults(
                    target_dir,
                    style_spec,
                    source_type=effective_format_source_type,
                )
                if blank_defaults:
                    qa_report['format_source']['blank_carrier_defaults'] = blank_defaults
                role_style_ids = install_result['role_style_ids']
                numbering_audit = install_result.get('numbering_audit') or {}
                role_map = apply_role_styles_to_document(
                    target_dir, role_style_ids, clean_direct=clean_direct,
                    role_map_out=role_map_out, role_map_in=role_map_in
                )
                format_conformance_stats = enforce_role_format_conformance(
                    target_dir, style_spec, role_map, clean_direct=clean_direct
                )
                if format_conformance_stats.get('enabled'):
                    repairs = format_conformance_stats.get('paragraph_repairs') or {}
                    style_repairs = (format_conformance_stats.get('style_repairs') or {}).get('style_repairs', 0)
                    print(
                        "  Format conformance QA: "
                        f"ok={format_conformance_stats.get('ok')}, "
                        f"style_repairs={style_repairs}, "
                        f"style_mismatches_repaired={repairs.get('style_mismatches_repaired', 0)}, "
                        f"direct_ppr_removed={repairs.get('direct_ppr_removed', 0)}, "
                        f"direct_rpr_removed={repairs.get('direct_rpr_removed', 0)}"
                    )
                if should_apply_abstract_keyword_label_defaults(effective_format_source_type):
                    abstract_keyword_label_stats = apply_abstract_keyword_label_bold(target_dir, role_map)
                reference_numbering_stats = apply_reference_numbering_map_to_document(
                    target_dir, reference_numbering_map, role_map
                )
                table_format_stats = apply_table_format_map_to_document(
                    target_dir, table_format_map,
                    preserve_table_width=preserve_table_width,
                )
                column_object_fit_stats = fit_wide_objects_to_columns(target_dir)
                equation_layout_stats = apply_equation_layout_map_to_document(target_dir, equation_layout_map)
                superscript_stats = apply_superscript_map_to_document(target_dir, superscript_map, role_map)
                if should_apply_chinese_metadata_tab_layout(effective_format_source_type):
                    metadata_layout_stats = apply_chinese_metadata_tab_layout(target_dir)
                high_inline_line_spacing_stats = protect_high_inline_content_line_spacing(target_dir)

        if apply_support and not non_docx_text_only_route:
            print("Copying support files (settings, fonts, theme)...")
            copy_support_files(target_dir, template_dir)
        elif apply_support and non_docx_text_only_route:
            print("Skipping support file migration for non-DOCX text route; using target package support files.")
            qa_report['format_source']['support_files_skipped'] = 'non_docx_text_only_route'

        spacing_normalization_stats = normalize_docx_spacing_values(target_dir)
        if spacing_normalization_stats.get('repairs'):
            qa_report['format_source']['spacing_value_normalization'] = spacing_normalization_stats

        # Repack
        print(f"Repacking to: {output_path}")
        repack_docx(target_dir, output_path)

        # Verify
        if zipfile.is_zipfile(output_path):
            print(f"✓ Success: {output_path}")
        else:
            raise RuntimeError(f"Failed to create valid DOCX: {output_path}")
        effective_explicit_postprocess_json = explicit_postprocess_json or auto_postprocess_json
        if effective_explicit_postprocess_json:
            print(f"Running explicit text-rule postprocess: {effective_explicit_postprocess_json}")
            explicit_postprocess_stats = run_explicit_postprocess(
                output_path,
                output_path,
                effective_explicit_postprocess_json,
                report_out=explicit_postprocess_report_out,
            )
            if auto_postprocess_json and not explicit_postprocess_json:
                explicit_postprocess_stats['auto_generated_from_rules_json'] = True
            qa_report['explicit_postprocess'] = explicit_postprocess_stats
            print_explicit_postprocess_summary(explicit_postprocess_stats)
            if not explicit_postprocess_stats.get('ok'):
                raise RuntimeError(f"Explicit postprocess failed: {explicit_postprocess_stats.get('error')}")
            if not zipfile.is_zipfile(output_path):
                raise RuntimeError(f"Explicit postprocess produced invalid DOCX: {output_path}")
        qa_report['format_conformance_qa'] = format_conformance_stats
        qa_report['final_audit'] = audit_docx_package(output_path)
        effective_render_qa_dir = render_qa_dir or default_render_qa_dir(output_path)
        lo_compat_dir = os.path.join(effective_render_qa_dir, 'libreoffice_compatibility')
        print(f"Running LibreOffice compatibility QA: {lo_compat_dir}")
        qa_report['libreoffice_compatibility_qa'] = run_libreoffice_compatibility_qa(
            output_path,
            lo_compat_dir,
        )
        if qa_report['libreoffice_compatibility_qa'].get('ok'):
            print("  LibreOffice compatibility QA: load/export succeeded")
        else:
            print(
                "  WARNING: LibreOffice compatibility QA failed: "
                f"{qa_report['libreoffice_compatibility_qa'].get('failure_kind')}"
            )
        if should_skip_render_compare_for_source(effective_format_source_type):
            print(
                "Skipping target-before/final render comparison QA: "
                f"format source is {effective_format_source_type}"
            )
            qa_report['render_compare_qa'] = skipped_render_compare_qa(
                effective_format_source_type,
                effective_render_qa_dir,
            )
            qa_report['render_qa'] = {
                'enabled': False,
                'ok': None,
                'skipped': True,
                'skip_reason': 'format_source_text_rules',
                'source_type': effective_format_source_type,
            }
        else:
            print(f"Running mandatory render comparison QA: {effective_render_qa_dir}")
            qa_report['render_compare_qa'] = run_render_compare_qa(
                target_path,
                output_path,
                effective_render_qa_dir,
            )
            qa_report['render_qa'] = qa_report['render_compare_qa'].get('final_render') or {
                'enabled': True,
                'ok': False,
                'error': 'mandatory render comparison did not produce a final render result',
            }
            if qa_report['render_compare_qa'].get('ok'):
                comparison = qa_report['render_compare_qa'].get('comparison') or {}
                print(
                    "  Render comparison QA pages: "
                    f"before={comparison.get('before_page_count')}, "
                    f"final={comparison.get('final_page_count')}, "
                    f"changed={comparison.get('changed_page_count')}"
                )
            else:
                print(f"  WARNING: mandatory render comparison QA failed: {qa_report['render_compare_qa'].get('error')}")
        if qa_report_out:
            with open(qa_report_out, 'w', encoding='utf-8') as f:
                json.dump(qa_report, f, ensure_ascii=False, indent=2)
            print(f"  Wrote QA report: {qa_report_out}")
        if apply_style:
            report = build_format_report(
                style_spec=style_spec,
                superscript_map=superscript_map,
                superscript_stats=superscript_stats,
                role_map=role_map,
                numbering_audit=numbering_audit,
                equation_layout_map=equation_layout_map,
                equation_layout_stats=equation_layout_stats,
                table_format_map=table_format_map,
                table_format_stats=table_format_stats,
                reference_numbering_map=reference_numbering_map,
                reference_numbering_stats=reference_numbering_stats,
                section_structure_stats=section_structure_stats,
                column_object_fit_stats=column_object_fit_stats,
                high_inline_line_spacing_stats=high_inline_line_spacing_stats,
                abstract_keyword_label_stats=abstract_keyword_label_stats,
                metadata_layout_stats=metadata_layout_stats,
                header_footer_watermark_stats=header_footer_watermark_stats,
                legacy_word_sources=legacy_word_sources,
                qa_report=qa_report,
                format_conformance_stats=format_conformance_stats,
                explicit_postprocess_stats=explicit_postprocess_stats,
            )
            write_format_report(report, format_report_out)

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Apply journal/DOCX template styles to a target document. '
                    'Preserves all content (formulas, images, OLE objects).',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Apply full template formatting
  python3 format_docx.py -t journal_template.docx -i paper.docx -o output.docx

  # Only apply page margins and headers
  python3 format_docx.py -t template.docx -i paper.docx -o out.docx --no-style --no-support

  # Use legacy style-name matching only when target/template names are known to match
  python3 format_docx.py -t template.docx -i paper.docx -o out.docx --style-mode name

  # Write/reuse the intermediate role style specification
  python3 format_docx.py -t template.docx -i paper.docx -o out.docx --style-spec-out style_spec.json
  python3 format_docx.py -t template.docx -i paper.docx -o out.docx --style-spec-in style_spec.json

  # Also write target paragraph role mapping for audit
  python3 format_docx.py -t template.docx -i paper.docx -o out.docx --role-map-out role_map.json

  # Write/reuse run-level superscript marker map
  python3 format_docx.py -t template.docx -i paper.docx -o out.docx --superscript-map-out superscript_map.json
  python3 format_docx.py -t template.docx -i paper.docx -o out.docx --superscript-map-in superscript_map.json

  # Write/reuse equation tab-stop layout map
  python3 format_docx.py -t template.docx -i paper.docx -o out.docx --equation-layout-map-out equation_layout_map.json
  python3 format_docx.py -t template.docx -i paper.docx -o out.docx --equation-layout-map-in equation_layout_map.json

  # Write/reuse table body formatting map
  python3 format_docx.py -t template.docx -i paper.docx -o out.docx --table-format-map-out table_format_map.json
  python3 format_docx.py -t template.docx -i paper.docx -o out.docx --table-format-map-in table_format_map.json

  # Allow template table width to override target widths when explicitly desired
  python3 format_docx.py -t template.docx -i paper.docx -o out.docx --allow-table-width-override

  # Write/reuse reference-list numbering repair map
  python3 format_docx.py -t template.docx -i paper.docx -o out.docx --reference-numbering-map-out reference_numbering_map.json
  python3 format_docx.py -t template.docx -i paper.docx -o out.docx --reference-numbering-map-in reference_numbering_map.json

  # Write internal formatting report for final user notes
  python3 format_docx.py -t template.docx -i paper.docx -o out.docx --format-report-out format_report.json

  # Write structural QA report. Render comparison QA is mandatory and runs even
  # without --render-qa-dir; pass it only to choose the internal QA directory.
  python3 format_docx.py -t template.docx -i paper.docx -o out.docx \
    --qa-report-out qa_report.json --render-qa-dir render_qa

  # When the target format comes from OCR/plain text rules, skip misleading
  # target-before/final visual comparison but still run structural and
  # LibreOffice compatibility QA.
  python3 format_docx.py -t template.docx -i paper.docx -o out.docx \
    --rules-json ocr_rules.json --format-source-type ocr_text_rules

  # Force the representative body section to use a known column count
  python3 format_docx.py -t template.docx -i paper.docx -o out.docx --body-cols 2

  # Optional explicit post-format content/structure edits. Use only when the
  # user clearly asks for these edits.
  python3 format_docx.py -t template.docx -i paper.docx -o out.docx \
    --explicit-postprocess-json postprocess_ops.json \
    --explicit-postprocess-report-out postprocess_report.json

  # Legacy .doc/.dot sources are converted to temporary .docx when possible.
  # Converted evidence is lower confidence and should be mentioned in final notes.
  python3 format_docx.py -t template.doc -i paper.docx -o out.docx

  # Reuse both reviewed intermediate files as locked inputs
  python3 format_docx.py -t template.docx -i paper.docx -o out.docx \
    --style-spec-in style_spec.json --role-map-in role_map.json
        """
    )
    parser.add_argument('-t', '--template', required=True,
                        help='Template DOCX file path (journal sample/style reference)')
    parser.add_argument('-i', '--target', required=True,
                        help='Target DOCX file path (paper to format)')
    parser.add_argument('-o', '--output', required=True,
                        help='Output DOCX file path')
    parser.add_argument('--no-page', action='store_true',
                        help='Skip page setup (margins, paper size)')
    parser.add_argument('--no-header', action='store_true',
                        help='Skip headers and footers replacement')
    parser.add_argument('--no-style', action='store_true',
                        help='Skip style migration, role binding, and direct-format cleanup')
    parser.add_argument('--no-support', action='store_true',
                        help='Skip support files (settings, fontTable, theme)')
    parser.add_argument('--style-mode', choices=('role', 'name'), default='role',
                        help='role=classify content and bind role styles (default); '
                             'name=legacy w:name style matching')
    parser.add_argument('--keep-direct-formatting', action='store_true',
                        help='Do not remove direct paragraph/run formatting overrides')
    parser.add_argument('--rules-json',
                        help='Optional JSON rules. User rules override template prose rules.')
    parser.add_argument('--style-spec-out',
                        help='Write intermediate role style specification JSON')
    parser.add_argument('--style-spec-in',
                        help='Reuse existing intermediate role style specification JSON')
    parser.add_argument('--role-map-out',
                        help='Write target paragraph role mapping JSON')
    parser.add_argument('--role-map-in',
                        help='Reuse reviewed target paragraph role mapping JSON')
    parser.add_argument('--superscript-map-out',
                        help='Write template-derived run-level superscript marker map JSON')
    parser.add_argument('--superscript-map-in',
                        help='Reuse reviewed run-level superscript marker map JSON')
    parser.add_argument('--equation-layout-map-out',
                        help='Write template-derived equation tab-stop layout map JSON')
    parser.add_argument('--equation-layout-map-in',
                        help='Reuse reviewed equation tab-stop layout map JSON')
    parser.add_argument('--table-format-map-out',
                        help='Write template-derived table body formatting map JSON')
    parser.add_argument('--table-format-map-in',
                        help='Reuse reviewed table body formatting map JSON')
    parser.add_argument('--reference-numbering-map-out',
                        help='Write template-derived reference-list numbering repair map JSON')
    parser.add_argument('--reference-numbering-map-in',
                        help='Reuse reviewed reference-list numbering repair map JSON')
    parser.add_argument('--format-report-out',
                        help='Write internal formatting report JSON for user-facing notes')
    parser.add_argument('--qa-report-out',
                        help='Write structural QA audit JSON for template, target-before, and final DOCX')
    parser.add_argument('--render-qa-dir',
                        help='Directory for mandatory target-before/final render comparison QA. '
                        'If omitted, a default <output-stem>_render_qa directory is created. '
                             'Rendered files are internal QA artifacts, not default user deliverables.')
    parser.add_argument('--format-source-type',
                        choices=(
                            'docx_template', 'native_docx_template', 'converted_docx_template',
                            'pdf_visual', 'pdf_visual_inference', 'visual_template',
                            'pdf_text_visual', 'pdf_text_visual_hybrid', 'pdf_rules_with_visual_supplement',
                            'text_rules', 'plain_text_rules', 'ocr_text', 'ocr_text_rules',
                            'image_text', 'image_text_rules', 'website_text', 'website_text_rules',
                            'screenshot_text', 'screenshot_text_rules',
                        ),
                        help='Evidence source for target formatting. Text/OCR/image/website text '
                             'sources skip target-before/final visual comparison QA because large '
                             'expected layout changes make visual diff misleading. DOCX/PDF visual '
                             'sources keep render comparison QA enabled. converted_docx_template '
                             'marks legacy .doc/.dot evidence converted to temporary DOCX with lower '
                             'style-XML confidence.')
    parser.add_argument('--body-cols', '--body-columns', type=int, dest='body_cols',
                        help='Preferred body column count for mixed-section templates')
    parser.add_argument('--explicit-postprocess-json',
                        help='Optional explicit opt-in JSON for post-format content/structure edits. '
                             'Do not use unless the user clearly requested these edits.')
    parser.add_argument('--explicit-postprocess-report-out',
                        help='Write explicit postprocess operation report JSON')
    parser.add_argument('--allow-table-width-override', action='store_true',
                        help='Allow template tblW/tblLayout to override target table width. '
                             'By default target table widths are preserved unless template width is explicit.')
    parser.add_argument('--allow-legacy-word-conversion', action='store_true',
                        help='Compatibility flag. Legacy .doc/.dot inputs are converted to temporary .docx '
                             'when possible before OpenXML extraction; converted evidence is lower confidence.')

    args = parser.parse_args()

    if not os.path.exists(args.template):
        print(f"Error: Template file not found: {args.template}")
        return 1
    if not os.path.exists(args.target):
        print(f"Error: Target file not found: {args.target}")
        return 1

    try:
        format_document(
            args.template, args.target, args.output,
            apply_page=not args.no_page,
            apply_header=not args.no_header,
            apply_style=not args.no_style,
            apply_support=not args.no_support,
            style_mode=args.style_mode,
            clean_direct=not args.keep_direct_formatting,
            rules_json=args.rules_json,
            style_spec_out=args.style_spec_out,
            style_spec_in=args.style_spec_in,
            role_map_out=args.role_map_out,
            role_map_in=args.role_map_in,
            superscript_map_out=args.superscript_map_out,
            superscript_map_in=args.superscript_map_in,
            equation_layout_map_out=args.equation_layout_map_out,
            equation_layout_map_in=args.equation_layout_map_in,
            table_format_map_out=args.table_format_map_out,
            table_format_map_in=args.table_format_map_in,
            reference_numbering_map_out=args.reference_numbering_map_out,
            reference_numbering_map_in=args.reference_numbering_map_in,
            format_report_out=args.format_report_out,
            qa_report_out=args.qa_report_out,
            render_qa_dir=args.render_qa_dir,
            body_cols=args.body_cols,
            preserve_table_width=not args.allow_table_width_override,
            allow_legacy_word_conversion=True,
            format_source_type=args.format_source_type,
            explicit_postprocess_json=args.explicit_postprocess_json,
            explicit_postprocess_report_out=args.explicit_postprocess_report_out,
        )
        return 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
