#!/usr/bin/env python3
"""Check skill Markdown links and concrete inline knowledge-file references."""
import argparse
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import unquote


def _heading_slug(value):
    """Approximate GitHub Markdown heading IDs, including CJK headings."""
    value = re.sub(r'!?(?:\[([^\]]*)\])\([^)]*\)', r'\1', value)
    value = re.sub(r'`([^`]*)`', r'\1', value)
    value = re.sub(r'<[^>]+>', '', value).strip().lower()
    slug = []
    for char in value:
        category = unicodedata.category(char)
        if char.isspace():
            slug.append('-')
        elif char in '-_' or category[0] in {'L', 'N'} or category == 'Mn':
            slug.append(char)
    return ''.join(slug).strip('-')


def _anchors(path):
    anchors = set()
    counts = {}
    fenced = False
    for line in path.read_text(encoding='utf-8').splitlines():
        if re.match(r'^\s*(`{3,}|~{3,})', line):
            fenced = not fenced
            continue
        if fenced:
            continue
        anchors.update(
            unquote(value)
            for value in re.findall(r'<a\s+[^>]*(?:id|name)=["\']([^"\']+)["\']', line, re.I)
        )
        heading = re.match(r'^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$', line)
        if not heading:
            continue
        base = _heading_slug(heading.group(1))
        if not base:
            continue
        duplicate = counts.get(base, 0)
        anchors.add(base if duplicate == 0 else f'{base}-{duplicate}')
        counts[base] = duplicate + 1
    return anchors


def _split_reference(raw):
    raw = raw.strip()
    if raw.startswith('<') and '>' in raw:
        raw = raw[1:raw.index('>')]
    else:
        raw = raw.split(maxsplit=1)[0]
    target, separator, fragment = raw.partition('#')
    return unquote(target), unquote(fragment) if separator else ''


def check(root):
    errors, checked = [], 0
    files = list(root.rglob('*.md'))
    names = {p.name for p in files}
    anchor_cache = {}

    def validate_anchor(source, line_no, raw, target_path, fragment):
        if not fragment or target_path.suffix.lower() != '.md':
            return
        resolved = target_path.resolve()
        if resolved not in anchor_cache:
            anchor_cache[resolved] = _anchors(resolved)
        if fragment not in anchor_cache[resolved]:
            errors.append({
                'file': str(source.relative_to(root)),
                'line': line_no,
                'target': raw,
                'kind': 'missing_anchor',
            })

    # Task-generated records are not packaged knowledge files.
    generated = {'brief.md', 'prompt-log.md'}
    for p in files:
        text = p.read_text(encoding='utf-8')
        # Fences contain examples, not navigational Markdown links.
        fenced = False
        for line_no, line in enumerate(text.splitlines(), 1):
            if re.match(r'^\s*(`{3,}|~{3,})', line):
                fenced = not fenced
                continue
            if fenced:
                continue
            for raw in re.findall(r'\]\(([^)]+)\)', line):
                target, fragment = _split_reference(raw)
                if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', target):
                    continue
                checked += 1
                target_path = p if not target else p.parent / target
                if not target_path.exists():
                    errors.append({'file': str(p.relative_to(root)), 'line': line_no, 'target': raw, 'kind': 'missing_link'})
                else:
                    validate_anchor(p, line_no, raw, target_path, fragment)
            for raw in re.findall(r'(?<!`)`([^`\n]+)`(?!`)', line):
                target, fragment = _split_reference(raw)
                if any(c in target for c in ' <>*{}|') or target in generated:
                    continue
                if not (target.endswith('.md') or (target.startswith(('references/', 'example/', 'scripts/')) and Path(target).suffix)):
                    continue
                checked += 1
                candidates = [p.parent / target, root / target]
                target_path = next((candidate for candidate in candidates if candidate.exists()), None)
                exists = target_path is not None
                # A unique/shared basename may intentionally be shorthand; still catch nonexistent names.
                if '/' not in target and target in names:
                    exists = True
                if not exists:
                    errors.append({'file': str(p.relative_to(root)), 'line': line_no, 'target': target, 'kind': 'missing_inline_reference'})
                elif target.endswith('.md'):
                    if target_path is None:
                        matches = [candidate for candidate in files if candidate.name == target]
                        if len(matches) == 1:
                            target_path = matches[0]
                    if target_path is not None:
                        validate_anchor(p, line_no, raw, target_path, fragment)
                    elif fragment:
                        errors.append({'file': str(p.relative_to(root)), 'line': line_no, 'target': raw, 'kind': 'ambiguous_inline_reference'})
        if fenced:
            errors.append({'file': str(p.relative_to(root)), 'kind': 'unclosed_code_fence'})
    return {'status': 'fail' if errors else 'pass', 'checked': checked, 'errors': errors,
            'scope': 'Local Markdown file/directory targets, Markdown anchors, and concrete inline knowledge paths; runtime artifact paths are not validated.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', default=str(Path(__file__).resolve().parents[2]))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not (root / 'SKILL.md').is_file():
        parser.error('root must contain SKILL.md')
    report = check(root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(1 if report['errors'] else 0)


if __name__ == '__main__':
    main()
