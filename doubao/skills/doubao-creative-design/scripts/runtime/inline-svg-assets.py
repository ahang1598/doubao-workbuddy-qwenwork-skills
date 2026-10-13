#!/usr/bin/env python3
"""Embed bundled SVG URLs or editable SVG DOM without printing payloads."""
import argparse
import hashlib
import json
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote, unquote

ASSET_REFERENCE = re.compile(r'asset:([^\s\"\'()<>;&]+)')
SVG_NS = 'http://www.w3.org/2000/svg'
INLINE_REFERENCE = re.compile(r'<!--\s*svg-inline:([^\s<>]+)\s*-->')
ARIA_REFERENCES = {
    'aria-activedescendant', 'aria-controls', 'aria-describedby', 'aria-details',
    'aria-errormessage', 'aria-flowto', 'aria-labelledby', 'aria-owns',
}
CSS_REFERENCE_ATTRIBUTES = {
    'style', 'fill', 'stroke', 'filter', 'clip-path', 'mask', 'cursor',
    'marker', 'marker-start', 'marker-mid', 'marker-end', 'color-profile',
}
ET.register_namespace('', SVG_NS)
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')


def read_svg(relative, asset_root, *, inline_dom=False):
    """Resolve only bundled, self-contained SVG files under asset_root."""
    if not re.fullmatch(r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_.-]+)*\.svg', relative):
        raise ValueError(f'Invalid SVG asset reference: {relative}')
    root = Path(asset_root).resolve()
    source = (root / relative).resolve()
    try:
        source.relative_to(root)
    except ValueError:
        raise ValueError(f'SVG asset escapes asset root: {relative}') from None
    svg = source.read_text(encoding='utf-8')
    element = ET.fromstring(svg)
    if element.tag != f'{{{SVG_NS}}}svg':
        raise ValueError(f'Asset must have an SVG root and namespace: {relative}')
    # The final HTML must not silently retain image/font/style dependencies.
    for node in element.iter():
        for key, value in node.attrib.items():
            if key.rsplit('}', 1)[-1] == 'href' and not value.startswith(('#', 'data:')):
                raise ValueError(f'SVG contains an external href: {relative}')
    if re.search(r'@import\b|<\?xml-stylesheet\b', svg, re.I):
        raise ValueError(f'SVG contains an external stylesheet: {relative}')
    if not inline_dom:
        validate_css_dependencies(element)
    return svg


def validate_css_dependencies(element):
    """Validate a parsed copy; data URI output retains the untouched source."""
    contents = []
    for node in element.iter():
        if node.tag.rsplit('}', 1)[-1] == 'style':
            contents.append(node.text or '')
        for key, value in node.attrib.items():
            if key.rsplit('}', 1)[-1] in CSS_REFERENCE_ATTRIBUTES:
                contents.append(value)
    if not contents:
        return
    try:
        import tinycss2
    except ImportError as error:
        raise ValueError('SVG CSS dependency validation requires tinycss2') from error
    def check(tokens):
        css_urls(tokens, tinycss2)
        for token in tokens:
            if token.type == 'at-keyword' and token.value.lower() == 'import':
                raise ValueError('SVG contains an external stylesheet')
            if hasattr(token, 'content'):
                check(token.content)
            elif token.type == 'function':
                check(token.arguments)
    for content in contents:
        check(tinycss2.parse_component_value_list(content))


def svg_data_uri(relative, asset_root):
    return 'data:image/svg+xml,' + quote(read_svg(relative, asset_root), safe='')


def scope_fragment(value, mapping):
    decoded = unquote(value[1:])
    return '#' + mapping[decoded] if decoded in mapping else value


def css_urls(tokens, tinycss2, mapping=None):
    """Validate CSS tokens and optionally scope decoded local URL references."""
    from tinycss2.serializer import serialize_string_value

    def reference(value):
        if not value.startswith(('#', 'data:')):
            raise ValueError(f'SVG contains an external CSS URL: {value}')
        if mapping is not None and value.startswith('#'):
            return scope_fragment(value, mapping)
        return value

    for token in tokens:
        if token.type == 'error':
            raise ValueError(f'Invalid SVG CSS: {token.message}')
        if token.type == 'url':
            value = reference(token.value)
            if mapping is not None:
                token.value = value
                token.representation = 'url("' + serialize_string_value(value) + '")'
        elif token.type == 'function' and token.lower_name == 'url':
            arguments = [item for item in token.arguments if item.type not in {'whitespace', 'comment'}]
            if len(arguments) != 1 or arguments[0].type != 'string':
                raise ValueError('Unsupported or invalid SVG CSS url() value')
            argument = arguments[0]
            value = reference(argument.value)
            if mapping is not None:
                argument.value = value
                argument.representation = '"' + serialize_string_value(value) + '"'
        elif token.type == 'function':
            css_urls(token.arguments, tinycss2, mapping)
        elif hasattr(token, 'content'):
            css_urls(token.content, tinycss2, mapping)


def css_declarations(content, tinycss2):
    declarations = tinycss2.parse_declaration_list(content, skip_comments=True, skip_whitespace=True)
    for declaration in declarations:
        if declaration.type != 'declaration':
            detail = getattr(declaration, 'message', declaration.type)
            raise ValueError(f'Unsupported or invalid SVG CSS declaration: {detail}')
        if not any(token.type not in {'whitespace', 'comment'} for token in declaration.value):
            if not declaration.name.startswith('--'):
                raise ValueError(f'Empty SVG CSS declaration: {declaration.name}')
        css_urls(declaration.value, tinycss2)
    return declarations


def remove_style(parent, node):
    # ElementTree.remove() also removes the tail; that tail may be real text.
    if node.tail:
        siblings = list(parent)
        index = siblings.index(node)
        if index:
            previous = siblings[index - 1]
            previous.tail = (previous.tail or '') + node.tail
        else:
            parent.text = (parent.text or '') + node.tail
    parent.remove(node)


def materialize_styles(element):
    """Match the original XML tree, materialize static CSS, then remove styles."""
    nodes = list(element.iter())
    parents = {child: parent for parent in nodes for child in parent}
    styles = []
    for node in nodes:
        local_name = node.tag.rsplit('}', 1)[-1]
        if local_name == 'link' and 'stylesheet' in node.get('rel', '').lower().split():
            raise ValueError('Linked SVG stylesheets are unsupported for inline DOM')
        if local_name == 'style':
            styles.append(node)
    has_css = any(key.rsplit('}', 1)[-1] in CSS_REFERENCE_ATTRIBUTES
                  for node in nodes for key in node.attrib)
    if not styles and not has_css:
        return None

    # CSS-free DOM and data-URI mode do not need parser dependencies.
    try:
        import tinycss2
        if styles:
            import cssselect2
    except ImportError as error:
        raise ValueError('Inlining SVG CSS requires tinycss2; <style> also requires cssselect2') from error

    if not styles:
        for node in nodes:
            if node.get('style') is not None:
                css_declarations(node.get('style'), tinycss2)
        return tinycss2

    matcher = cssselect2.Matcher()
    source_order = 0
    for style in styles:
        if style.tag != f'{{{SVG_NS}}}style':
            raise ValueError('Unsupported stylesheet namespace in inline SVG')
        if len(style):
            raise ValueError('SVG <style> must contain CSS text, not child elements')
        attributes = {key.rsplit('}', 1)[-1]: value for key, value in style.attrib.items()}
        if attributes.get('type', '').strip().lower() not in {'', 'text/css'}:
            raise ValueError('Only text/css SVG stylesheets are supported')
        if attributes.get('media', '').strip().lower() not in {'', 'all'}:
            raise ValueError('Conditional SVG stylesheet media is unsupported')
        if any(key in attributes for key in {'disabled', 'scoped', 'alternate', 'href'}):
            raise ValueError('Conditional, scoped, or linked SVG stylesheets are unsupported')
        if attributes.get('title', '').strip():
            raise ValueError('Named/alternate SVG stylesheets are unsupported')
        ancestor = style
        while ancestor is not None:
            if ancestor.tag.rsplit('}', 1)[-1] == 'switch' or any(
                key.rsplit('}', 1)[-1] in {'requiredFeatures', 'requiredExtensions', 'systemLanguage'}
                for key in ancestor.attrib
            ):
                raise ValueError('Conditionally included SVG stylesheets are unsupported')
            ancestor = parents.get(ancestor)

        rules = tinycss2.parse_stylesheet(style.text or '', skip_comments=True, skip_whitespace=True)
        for rule in rules:
            if rule.type == 'at-rule':
                raise ValueError(f'Unsupported SVG CSS at-rule: @{rule.lower_at_keyword}')
            if rule.type != 'qualified-rule':
                detail = getattr(rule, 'message', rule.type)
                raise ValueError(f'Invalid SVG stylesheet: {detail}')
            # A colon outside an attribute selector introduces a pseudo selector.
            # Reject it explicitly, including pseudo selectors cssselect2 never matches.
            if any(token.type == 'literal' and token.value == ':' for token in rule.prelude):
                raise ValueError('SVG CSS pseudo-classes and pseudo-elements are unsupported')
            try:
                selectors = cssselect2.compile_selector_list(rule.prelude)
            except cssselect2.SelectorError as error:
                raise ValueError(f'Unsupported or invalid SVG CSS selector: {error}') from error
            if not selectors:
                raise ValueError('Empty SVG CSS selector')
            declarations = css_declarations(rule.content, tinycss2)
            source_order += 1
            for selector in selectors:
                if selector.pseudo_element is not None:
                    raise ValueError('SVG CSS pseudo-elements are unsupported')
                matcher.add_selector(selector, (source_order, declarations))

    staged = []
    wrappers = list(cssselect2.ElementWrapper.from_xml_root(element).iter_subtree())
    for wrapper in wrappers:
        node = wrapper.etree_element
        # A grouped rule contributes once, using its highest matching specificity.
        matched_rules = {}
        for specificity, _, pseudo, payload in matcher.match(wrapper):
            if pseudo is not None:
                raise ValueError('SVG CSS pseudo-elements are unsupported')
            order, declarations = payload
            previous = matched_rules.get(order)
            if previous is None or specificity > previous[0]:
                matched_rules[order] = (specificity, declarations)
        cascade = []
        for order, (specificity, declarations) in matched_rules.items():
            for index, declaration in enumerate(declarations):
                priority = (int(declaration.important), 0, specificity, order, index)
                cascade.append((priority, declaration))
        inline = node.get('style')
        if inline is not None:
            for index, declaration in enumerate(css_declarations(inline, tinycss2)):
                priority = (int(declaration.important), 1, (0, 0, 0), 0, index)
                cascade.append((priority, declaration))
        if cascade or inline is not None:
            cascade.sort(key=lambda item: item[0])
            # Keep ordered declarations instead of discarding by property name:
            # the browser still handles shorthand/longhand and valid-value fallbacks.
            value = ''.join(tinycss2.serialize([declaration]) for _, declaration in cascade)
            staged.append((node, value))

    # No attributes or siblings changed while selectors were being evaluated.
    for node, value in staged:
        node.set('style', value)
    for style in styles:
        remove_style(parents[style], style)
    return tinycss2


def inline_assets(text, asset_root):
    cache = {}
    count = 0
    inline_count = 0
    used_ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', text))
    prefix = 'vl-svg-' + hashlib.sha256(text.encode()).hexdigest()[:10]

    def get_svg(relative, dom=False):
        key = (relative, dom)
        if key not in cache:
            cache[key] = read_svg(relative, asset_root, inline_dom=dom)
        return cache[key]

    def inline_dom(match):
        nonlocal inline_count
        inline_count += 1
        element = ET.fromstring(get_svg(match.group(1), dom=True))
        original_ids = [node.get('id') for node in element.iter() if node.get('id') is not None]
        if len(original_ids) != len(set(original_ids)):
            raise ValueError('SVG contains duplicate IDs')
        tinycss2 = materialize_styles(element)

        # Scope only after CSS has matched the original IDs/classes/attributes/tree.
        mapping = {}
        for node in element.iter():
            old = node.get('id')
            if old is not None:
                new = f'{prefix}-{inline_count}-{len(mapping)}'
                while new in used_ids:
                    new += '-x'
                mapping[old] = new
                used_ids.add(new)
                node.set('id', new)

        def references(value, fragment=False):
            if fragment and value.startswith('#'):
                return scope_fragment(value, mapping)
            return re.sub(
                r'url\(\s*(["\']?)#([^\s)"\']+)\1\s*\)',
                lambda m: 'url(#' + mapping.get(m.group(2), m.group(2)) + ')',
                value,
                flags=re.I,
            )

        for node in element.iter():
            for key, value in list(node.attrib.items()):
                if key == 'id':
                    continue
                local_name = key.rsplit('}', 1)[-1]
                if local_name in ARIA_REFERENCES:
                    node.set(key, ' '.join(mapping.get(v, v) for v in value.split()))
                elif tinycss2 is not None and local_name in CSS_REFERENCE_ATTRIBUTES:
                    # Token rewriting also handles CSS-escaped fragment IDs and quoted URLs.
                    tokens = tinycss2.parse_component_value_list(value)
                    css_urls(tokens, tinycss2, mapping)
                    node.set(key, tinycss2.serialize(tokens))
                else:
                    node.set(key, references(value, local_name == 'href'))
        return ET.tostring(element, encoding='unicode')

    def replace(match):
        nonlocal count
        count += 1
        # Preserve the original SVG payload, including its own stylesheet.
        return 'data:image/svg+xml,' + quote(get_svg(match.group(1)), safe='')

    result = INLINE_REFERENCE.sub(inline_dom, text)
    result = ASSET_REFERENCE.sub(replace, result)
    if 'asset:' in result or 'svg-inline:' in result:
        raise ValueError('Unresolved SVG reference; use asset:svg/name.svg or an svg-inline comment')
    return result, {'references': count, 'unique_assets': len({key[0] for key in cache}), 'inline_svgs': inline_count}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path, help='Draft HTML or CSS containing short asset references')
    parser.add_argument('--output', required=True, type=Path, help='A separate, self-contained output file')
    parser.add_argument('--asset-root', type=Path, default=Path(__file__).resolve().parents[2] / 'assets',
                        help='Defaults to assets next to this skill; use a task-local copy for custom variants')
    parser.add_argument('--force', action='store_true', help='Replace an existing output, never the input')
    args = parser.parse_args()
    temporary = None
    try:
        if args.input.resolve() == args.output.resolve():
            raise ValueError('Input and output must be different files')
        if args.output.exists() and not args.force:
            raise ValueError('Output exists; choose a new output or explicitly use --force')
        result, summary = inline_assets(args.input.read_text(encoding='utf-8'), args.asset_root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=args.output.parent,
                                         prefix='.inline-svg-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(result)
        os.replace(temporary, args.output)
        print(json.dumps({'status': 'pass', **summary, 'output': str(args.output)}, ensure_ascii=False))
    except (OSError, ValueError, ET.ParseError) as error:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        parser.exit(1, f'inline-svg-assets: {error}\n')


if __name__ == '__main__':
    main()
