"""Validate embedded web-font declarations without restricting stylesheet organization."""
import tinycss2
from html.parser import HTMLParser
from resolve_font import load_web_manifest, build_web_font_contract


def validate_loaded(page, stylesheet_sources):
    """Check loaded CSS font faces, including imports and cross-origin sheets."""
    collected = page.evaluate(r'''() => {
      const hrefs=new Set(), seen=new Set();
      function sheet(s){
        if(!s||seen.has(s))return;seen.add(s);
        if(s.href)hrefs.add(s.href);
        try{for(const rule of s.cssRules)
          if(rule.type===CSSRule.IMPORT_RULE)sheet(rule.styleSheet);
        }catch(e){} // Cross-origin text comes from the response collector.
      }
      for(const s of document.styleSheets)sheet(s);
      return {inline:[...document.querySelectorAll('style')].map(s=>s.textContent),hrefs:[...hrefs]};
    }''')
    errors = ['Font stylesheet could not be inspected: ' + href
              for href in collected['hrefs'] if href not in stylesheet_sources]
    errors.extend(check_css(collected['inline'] + list(stylesheet_sources.values())))
    return list(dict.fromkeys(errors))


def tokens(items):
    return [t for t in items if t.type not in ('whitespace', 'comment')]


def faces(css):
    for rule in tinycss2.parse_stylesheet(css, skip_comments=True, skip_whitespace=True):
        if rule.type == 'at-rule' and rule.lower_at_keyword == 'font-face':
            yield rule
        elif rule.type == 'at-rule' and rule.content is not None:
            yield from faces(tinycss2.serialize(rule.content))


def signature(rule):
    if rule.content is None:
        raise ValueError('Missing font declaration')
    properties = {}
    for d in tinycss2.parse_declaration_list(rule.content, skip_comments=True, skip_whitespace=True):
        if d.type != 'declaration' or d.important:
            raise ValueError('Invalid font declaration')
        properties[d.lower_name] = tokens(d.value)
    family = properties.get('font-family', [])
    if len(family) == 1 and family[0].type == 'string':
        family = family[0].value
    elif family and all(t.type == 'ident' for t in family):
        family = ' '.join(t.value for t in family)
    else:
        raise ValueError('Invalid font family')
    urls = []
    expect_url = True
    for t in properties.get('src', []):
        if t.type == 'literal' and t.value == ',' and not expect_url:
            expect_url = True
        elif expect_url and t.type == 'url':
            urls.append(t.value)
            expect_url = False
        elif expect_url and t.type == 'function' and t.lower_name == 'url':
            args = tokens(t.arguments)
            if len(args) != 1 or args[0].type != 'string':
                raise ValueError('Invalid font URL')
            urls.append(args[0].value)
            expect_url = False
        elif not expect_url and t.type == 'function' and t.lower_name in ('format', 'tech'):
            continue
        else:
            raise ValueError('Invalid font source')
    if expect_url or any(not u or any(c.isspace() for c in u) for u in urls):
        raise ValueError('Missing or invalid font URL')
    weight = tinycss2.serialize(properties.get('font-weight', [])).strip().lower() or '400'
    weight = {'normal': '400', 'bold': '700'}.get(weight, weight)
    style = tinycss2.serialize(properties.get('font-style', [])).strip().lower() or 'normal'
    return family, weight, style, tuple(urls)


def check_css(stylesheets):
    try:
        allowed = {signature(rule) for f in load_web_manifest()['families'] for face in f['faces']
                   for rule in faces(build_web_font_contract(f, face)['font_face_css'])}
    except (OSError, ValueError, KeyError, TypeError) as error:
        return [f'Web font manifest validation failed: {error}']
    errors = []
    for css in stylesheets:
        for rule in faces(css):
            try:
                if signature(rule) not in allowed:
                    raise ValueError('Font face outside resolver manifest')
            except ValueError as error:
                errors.append(str(error))
    return errors


def validate(source):
    errors = []

    class Parser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.active = False
            self.blocks = []
            self.css = ''

        def handle_starttag(self, tag, attrs):
            if tag == 'style':
                self.active = True
                self.css = ''

        def handle_data(self, data):
            if self.active: self.css += data

        def handle_endtag(self, tag):
            if tag == 'style' and self.active:
                self.blocks.append(self.css)
                self.active = False

    parser = Parser()
    parser.feed(source)
    if parser.active: errors.append('Unclosed stylesheet')
    errors.extend(check_css(parser.blocks))
    return errors
