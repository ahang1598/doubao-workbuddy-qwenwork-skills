"""Validate the narrowly scoped HTML web-font exception without network access."""
import re
from html.parser import HTMLParser
from resolve_font import load_web_manifest, build_web_font_contract


def normalized(css):
    # Preserve whitespace within quoted URLs and family names.
    return ''.join(re.findall(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|\S', css))


def validate(source):
    try:
        allowed = {normalized(build_web_font_contract(f, face)['font_face_css'])
                   for f in load_web_manifest()['families'] for face in f['faces']}
    except (OSError, ValueError, KeyError, TypeError) as error:
        return [f'Web font manifest validation failed: {error}']
    errors = []

    class Parser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.head = False
            self.active = False
            self.blocks = []
            self.css = ''

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == 'head': self.head = True
            if tag == 'link' and 'stylesheet' in attrs.get('rel', '').lower().split():
                errors.append('External stylesheets are prohibited')
            if tag == 'style':
                if not self.head or set(attrs) != {'data-web-fonts'}:
                    errors.append('Only <style data-web-fonts> inside head is allowed')
                self.active = True
                self.css = ''

        def handle_data(self, data):
            if self.active: self.css += data

        def handle_endtag(self, tag):
            if tag == 'head': self.head = False
            if tag == 'style' and self.active:
                self.blocks.append(self.css)
                self.active = False

    parser = Parser()
    parser.feed(source)
    if parser.active: errors.append('Unclosed font stylesheet')
    if len(parser.blocks) > 1: errors.append('Only one font stylesheet is allowed')
    seen = set()
    for css in parser.blocks:
        blocks = re.findall(r'@font-face\s*\{[^{}]*\}', css)
        remainder = re.sub(r'@font-face\s*\{[^{}]*\}', '', css)
        if remainder.strip() or not blocks:
            errors.append('Font stylesheet may contain only resolver font-face rules')
        for block in blocks:
            key = normalized(block)
            if key not in allowed: errors.append('Font declaration must exactly match resolver output')
            if key in seen: errors.append('Duplicate font declaration')
            seen.add(key)
    return errors
