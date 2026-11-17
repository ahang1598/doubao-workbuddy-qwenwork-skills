#!/usr/bin/env python3
"""Prepare explicit page recipes and publish them through the existing publisher.

prepare --plan manifest/authoring-plan.json --work-dir WORK_DIR
run --plan manifest/authoring-plan.json --work-dir WORK_DIR --presentation DECK
run --plan manifest/authoring-plan.json --work-dir WORK_DIR --presentation DECK --start-page 14

Paths in JSON are relative to WORK_DIR. Every page declares page/link/mode and
operation: migration, fill or ready. Migration takes the existing compose API's
source/frame/content_ids/frame_ids/target_region/placements/role_styles/bindings.
Fill takes source/ids/fill_plan and explicit notes (text or paragraph strings).
Ready takes xml and existing per-page publisher contract/binding paths.

Optional values_file and values contain already formatted strings; inline
values override the file. {{key}} substitution applies to fill replacement text
and fill notes. A ready recipe can explicitly set apply_values:true to substitute
native text and notes once; attributes and charts stay unchanged. No calculation,
expression evaluation or custom commands are supported. Migration preserves source text.

Generated output defaults to authoring/slide-NN.xml; output can name another
path inside WORK_DIR. Identical prepared files are reused; different existing
files are kept and reported. Full plan, values and source/recipe bytes are saved
under manifest/authoring-plans. Publisher input source is explicit publish_source
for migration, and defaults to source for fill/ready.

run (also named publish) prepares and publishes sequentially, stopping at the
first unsuccessful page. start_page is an explicit resume cursor. The existing
publisher owns lint, IDs, registration and unknown-ACK recovery; this script
never clears its pending record. A completed run proves acknowledged writes,
not semantic or rendered approval of the deck.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid

from lxml import etree as ET


PUBLISH_PATHS = ('exception_file', 'local_cache', 'layout_manifest', 'layout_contract',
    'layout_bindings', 'source_decorations', 'fixed_reflow', 'chart_inventory',
    'chart_contract', 'chart_bindings', 'migration_contract', 'migration_bindings',
    'style_card', 'style_bindings', 'style_font_substitutions', 'style_overrides')
MODES = {'fixed_template', 'component_reuse', 'active_rebuild'}
PLACEHOLDER = re.compile(r'\{\{([^{}]+)\}\}')
_HELPERS = {}


def _helper(name):
    if name not in _HELPERS:
        path = Path(__file__).with_name(name + '.py')
        spec = importlib.util.spec_from_file_location('authoring_' + name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _HELPERS[name] = module
    return _HELPERS[name]


def _path(value, work):
    if not isinstance(value, (str, Path)) or not str(value):
        raise ValueError('Expected a nonempty input file path')
    path = Path(value).expanduser()
    return (path if path.is_absolute() else work / path).resolve()


def _output(value, work):
    path = _path(value, work)
    try:
        path.relative_to(work)
    except ValueError:
        raise ValueError('Prepared outputs must stay inside work_dir: ' + str(path))
    return path


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def _write_artifacts(artifacts):
    # Check the whole current page before writing any new deliverable.
    for path, raw in artifacts.items():
        if path.exists() and (not path.is_file() or path.read_bytes() != raw):
            raise ValueError('Existing output differs; use a new output/plan version: ' + str(path))
    for path, raw in artifacts.items():
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(raw)


def _artifact(artifacts, path, raw):
    if path in artifacts and artifacts[path] != raw:
        raise ValueError('Different current-page artifacts share an output path: ' + str(path))
    artifacts[path] = raw


def _input(value, work, inputs, suffix):
    path = _path(value, work)
    raw = path.read_bytes()
    inputs.append((path, raw, suffix))
    return path, raw


def _json_input(value, work, inputs):
    if isinstance(value, (str, Path)):
        _, raw = _input(value, work, inputs, '.json')
        return json.loads(raw)
    return copy.deepcopy(value)


def _context(plan, work_dir, start_page):
    work = Path(work_dir).expanduser().resolve()
    if not work.is_dir():
        raise ValueError('work_dir must be an existing directory')
    if type(start_page) is not int or start_page < 1:
        raise ValueError('start_page must be a positive page number')
    if isinstance(plan, (str, Path)):
        raw = _path(plan, work).read_bytes()
        data = json.loads(raw)
    else:
        data = copy.deepcopy(plan)
        raw = _json_bytes(data)
    if not isinstance(data, dict) or not isinstance(data.get('pages'), list) or not data['pages']:
        raise ValueError('Plan must contain a nonempty pages array')
    seen = set()
    for page in data['pages']:
        if not isinstance(page, dict) or type(page.get('page')) is not int or page['page'] < 1:
            raise ValueError('Every page recipe needs a positive page number')
        if page['page'] in seen:
            raise ValueError('Duplicate page recipe: ' + str(page['page']))
        seen.add(page['page'])
        if page.get('mode') not in MODES or page.get('link') not in [f'L{i}' for i in range(1, 10)]:
            raise ValueError('Every page must declare a supported mode and link')
    values = {}
    if data.get('values_file') is not None:
        values = json.loads(_path(data['values_file'], work).read_bytes())
    inline = data.get('values', {})
    if not isinstance(values, dict) or not isinstance(inline, dict):
        raise ValueError('values_file/values must contain a string mapping')
    values = {**values, **inline}
    if any(not isinstance(k, str) or not isinstance(v, str) for k, v in values.items()):
        raise ValueError('Shared values must be explicit already-formatted strings')
    values_raw = _json_bytes(values)
    key = hashlib.sha256(raw + b'\0' + values_raw).hexdigest()
    folder = _output('manifest/authoring-plans/' + key, work)
    snapshot, values_snapshot = folder / 'plan.json', folder / 'values.json'
    _write_artifacts({snapshot: raw, values_snapshot: values_raw})
    return {'work': work, 'folder': folder, 'plan': data, 'values': values,
            'plan_snapshot': str(snapshot), 'values_snapshot': str(values_snapshot),
            'plan_sha256': hashlib.sha256(raw).hexdigest(),
            'pages': sorted((p for p in data['pages'] if p['page'] >= start_page), key=lambda p: p['page'])}


def _substitute(text, values):
    if not isinstance(text, str):
        raise ValueError('Replacement text and notes must be strings')
    def replace(match):
        key = match.group(1).strip()
        if key not in values:
            raise ValueError('Unknown shared value key: ' + key)
        return values[key]
    return PLACEHOLDER.sub(replace, text)


def _root(raw):
    root = ET.fromstring(raw, ET.XMLParser(resolve_entities=False, no_network=True))
    if ET.QName(root).localname != 'slide':
        raise ValueError('Ready/fill XML must contain one slide')
    return root


def _apply_ready_values(raw, values):
    root = _root(raw)
    namespace = ET.QName(root).namespace
    def editable(node):
        if node is None or not isinstance(node.tag, str):
            return False
        path = [ET.QName(item) for item in [node, *node.iterancestors()]
                if isinstance(item.tag, str)]
        if (namespace not in {None, 'https://www.larkoffice.com/sml/2.0'} or
                any(item.namespace != namespace for item in path)):
            return False
        names = [item.localname for item in path]
        if any(name in {'embed', 'svg', 'defs', 'chart'} for name in names):
            return False
        return ('content' in names and
                any(name in {'shape', 'table', 'note'}
                    for name in names[names.index('content') + 1:]))
    for node in root.iter():
        if isinstance(node.tag, str) and node.text and editable(node):
            node.text = _substitute(node.text, values)
        if node.tail and editable(node.getparent()):
            node.tail = _substitute(node.tail, values)
    return ET.tostring(root, encoding='utf-8')


def _with_notes(xml, notes, values):
    paragraphs = [notes] if isinstance(notes, str) else notes
    if not isinstance(paragraphs, list):
        raise ValueError('Fill notes must be text or an explicit paragraph list')
    paragraphs = [_substitute(p, values) for p in paragraphs]
    root = _root(xml.encode('utf-8'))
    for child in list(root):
        if ET.QName(child).localname == 'note':
            root.remove(child)
    namespace = ET.QName(root).namespace
    tag = lambda name: '{' + namespace + '}' + name if namespace else name
    note = ET.SubElement(root, tag('note'))
    content = ET.SubElement(note, tag('content'))
    for text in paragraphs:
        ET.SubElement(content, tag('p')).text = text
    return ET.tostring(root, encoding='utf-8'), paragraphs


def _prepare_page(page, context):
    work = context['work']
    inputs, artifacts = [], {}
    operation, number = page.get('operation'), page['page']
    xml_path = _output(page.get('output', f'authoring/slide-{number:02d}.xml'), work)
    row = {'page': number, 'operation': operation, 'link': page['link'], 'mode': page['mode'],
           'status': 'prepared', 'xml_path': str(xml_path), 'source_snapshots': []}
    if operation == 'migration':
        if 'notes' in page:
            raise ValueError('Migration preserves original notes; new notes are only supported for fill')
        source, _ = _input(page['source'], work, inputs, '.xml')
        frame, _ = _input(page['frame'], work, inputs, '.xml')
        options = {k: _json_input(page[k], work, inputs) for k in
                   ('placements', 'role_styles', 'bindings', 'source_roles', 'explicit_numbering') if k in page}
        api = _helper('template_migration')
        result = api.compose_migration(source, frame, page.get('content_ids'),
            page.get('frame_ids'), page.get('target_region'), **options)
        verdict = api.validate_migration(result['xml'], result['contract'])
        if not verdict['ok']:
            raise ValueError('Composed migration did not preserve source content: ' + json.dumps(verdict['errors']))
        raw = result['xml'].encode('utf-8')
        contract = _output(page.get('migration_contract', f'manifest/migration-contracts/page-{number:02d}.json'), work)
        bindings = _output(page.get('migration_bindings', str(contract.with_name(contract.stem + '.bindings.json'))), work)
        _artifact(artifacts, contract, _json_bytes(result['contract']))
        _artifact(artifacts, bindings, _json_bytes(result['bindings']))
        row.update(migration_contract=str(contract), migration_bindings=str(bindings))
    elif operation == 'fill':
        source, _ = _input(page['source'], work, inputs, '.xml')
        field_plan = _json_input(page['fill_plan'], work, inputs)
        if not isinstance(field_plan, dict):
            raise ValueError('fill_plan must be a complete field-plan object')
        for field in field_plan.get('fields', []):
            if isinstance(field, dict) and field.get('action') == 'replace':
                field['new_text'] = _substitute(field.get('new_text'), context['values'])
        result = _helper('template_reuse').fill_component(source, page['ids'], field_plan)
        if not result['ok']:
            raise ValueError('Incomplete component fill: ' + json.dumps(result.get('missing_fields', []), ensure_ascii=False))
        if 'notes' not in page:
            raise ValueError('Fill page requires explicit notes text/paragraphs')
        raw, paragraphs = _with_notes(result['xml'], page['notes'], context['values'])
        fill_report = xml_path.with_suffix('.fill.json')
        summary = {k: v for k, v in result.items() if k != 'xml'}
        summary.update(notes=paragraphs, xml_sha256=hashlib.sha256(raw).hexdigest())
        _artifact(artifacts, fill_report, _json_bytes(summary))
        row.update(fill_report=str(fill_report), note_paragraph_count=len(paragraphs))
    elif operation == 'ready':
        if 'notes' in page:
            raise ValueError('Ready notes come from its already-authored XML')
        _, raw = _input(page['xml'], work, inputs, '.xml')
        _root(raw)
        if page.get('apply_values') is True:
            raw = _apply_ready_values(raw, context['values'])
            row['values_applied'] = True
    else:
        raise ValueError('Unsupported authoring operation: ' + str(operation))
    if operation != 'migration' and page.get('explicit_numbering') is True:
        numbered=_helper('template_list_layout').explicit_numbering(raw)
        raw=numbered['xml'].encode('utf-8')
        numbering_report=xml_path.with_suffix('.numbering.json')
        _artifact(artifacts,numbering_report,_json_bytes({k:v for k,v in numbered.items() if k!='xml'}))
        row['numbering_report']=str(numbering_report)
    if page.get('text_fit_ids'):
        stage=_output(context['folder']/f'page-{number:02d}.before-text-fit.xml',work)
        if stage == xml_path:
            raise ValueError('Author output cannot use the internal text-fit stage path')
        _write_artifacts({stage:raw})
        fitted=_helper('template_text_fit').prepare_text_containers(stage,page['text_fit_ids'])
        if not fitted['ok']:
            raise ValueError('Text container needs layout adjustment: '+json.dumps(fitted['containers'],ensure_ascii=False))
        raw=fitted['xml'].encode('utf-8')
        text_report=xml_path.with_suffix('.text-fit.json')
        _artifact(artifacts,text_report,_json_bytes({k:v for k,v in fitted.items() if k!='xml'}))
        row['text_fit_report']=str(text_report)
    if row.get('fill_report'):
        report_path=Path(row['fill_report'])
        report=json.loads(artifacts[report_path])
        report['xml_sha256']=hashlib.sha256(raw).hexdigest()
        artifacts[report_path]=_json_bytes(report)
    # Keep fixed publisher flags explicit; arbitrary JSON commands are not used.
    for key in PUBLISH_PATHS:
        if key not in row and page.get(key) is not None:
            row[key] = str(_path(page[key], work))
    if page.get('source_visual') is not None:
        visuals = page['source_visual']
        if isinstance(visuals, str):
            visuals = [visuals]
        if not isinstance(visuals, list) or not visuals:
            raise ValueError('source_visual 必须是源页图片路径或非空路径列表。')
        row['source_visual'] = [str(_path(v, work)) for v in visuals]
    for key in ('no_lint', 'strict', 'reason'):
        if page.get(key) is not None:
            row[key] = page[key]
    publish_source = page.get('publish_source')
    if publish_source is None and operation in {'fill', 'ready'}:
        publish_source = page.get('source')
    if publish_source is not None:
        row['publish_source'] = str(_path(publish_source, work))
    if page.get('slide_id') is not None:
        row['slide_id'] = page['slide_id']
    for path, source_raw, suffix in inputs:
        if path.read_bytes() != source_raw:
            raise ValueError('Source/recipe changed during preparation: ' + str(path))
        digest = hashlib.sha256(source_raw).hexdigest()
        snapshot = _output(context['folder'] / 'sources' / (digest + suffix), work)
        _artifact(artifacts, snapshot, source_raw)
        row['source_snapshots'].append({'path': str(path), 'sha256': digest, 'snapshot': str(snapshot)})
    row['xml_sha256'] = hashlib.sha256(raw).hexdigest()
    prepared_report = context['folder'] / f'page-{number:02d}.json'
    row['prepare_report_path'] = str(prepared_report)
    _artifact(artifacts, xml_path, raw)
    _artifact(artifacts, prepared_report, _json_bytes({'recipe': page, 'prepared': row}))
    _write_artifacts(artifacts)
    return row


def _progress(row):
    print(json.dumps({k: row[k] for k in ('page', 'status')}, ensure_ascii=False), file=sys.stderr, flush=True)


def _result(context, rows, ok, status, next_page=None, error=None):
    result = {'ok': ok, 'status': status, 'next_page': next_page,
              'plan_snapshot': context['plan_snapshot'], 'values_snapshot': context['values_snapshot'],
              'prepared_pages': [r['page'] for r in rows if 'xml_path' in r], 'pages': rows}
    if error is not None:
        result['error'] = str(error)[:500]
    return result


def prepare_plan(plan, work_dir, start_page=1):
    """Prepare each explicit page, stopping on its actual composition error."""
    context = _context(plan, work_dir, start_page)
    rows = []
    for page in context['pages']:
        try:
            row = _prepare_page(page, context)
        except (OSError, ValueError, TypeError, KeyError, ET.XMLSyntaxError) as exc:
            row = {'page': page['page'], 'status': 'prepare_blocked'}
            rows.append(row); _progress(row)
            return _result(context, rows, False, 'prepare_blocked', page['page'], exc)
        rows.append(row); _progress(row)
    return _result(context, rows, True, 'prepared' if rows else 'nothing_to_do')


def _publisher_command(page, row, work, presentation):
    argv = [sys.executable, str(Path(__file__).with_name('template_publish.py')),
            '--presentation', presentation, '--xml', row['xml_path'],
            '--page', str(page['page']), '--link', page['link'], '--mode', page['mode'], '--work-dir', str(work)]
    for key in PUBLISH_PATHS:
        if key in row:
            argv.extend(['--' + key.replace('_', '-'), row[key]])
    for visual in row.get('source_visual', []):
        argv.extend(['--source-visual', visual])
    if row.get('no_lint') is True:
        argv.append('--no-lint')
    if row.get('strict') is True:
        argv.append('--strict')
    if row.get('reason'):
        argv.extend(['--reason', str(row['reason'])])
    for key, flag in [('publish_source', '--source'), ('slide_id', '--slide-id')]:
        if key in row:
            argv.extend([flag, row[key]])
    return argv


def run_plan(plan, work_dir, presentation, start_page=1, runner=None):
    """Run the existing publisher once per page; return the first stop cursor."""
    if not isinstance(presentation, str) or not presentation.strip():
        raise ValueError('presentation must be an explicit deck ID')
    context = _context(plan, work_dir, start_page)
    runner = runner or subprocess.run
    report_dir = _output('authoring-plan-reports/' + uuid.uuid4().hex, context['work'])
    report_dir.mkdir(parents=True)
    rows, published = [], []
    for page in context['pages']:
        try:
            row = _prepare_page(page, context)
        except (OSError, ValueError, TypeError, KeyError, ET.XMLSyntaxError) as exc:
            row = {'page': page['page'], 'status': 'prepare_blocked'}
            rows.append(row); _progress(row)
            result = _result(context, rows, False, 'prepare_blocked', page['page'], exc)
            break
        argv = _publisher_command(page, row, context['work'], presentation)
        execution = {'page': page['page'], 'command': argv, 'cwd': str(context['work'])}
        response = {}
        try:
            process = runner(argv, cwd=str(context['work']), capture_output=True, text=True, check=False)
            execution.update(returncode=process.returncode, stdout=process.stdout, stderr=process.stderr)
            parsed = json.loads(process.stdout)
            if not isinstance(parsed, dict):
                raise ValueError('Publisher response must be a JSON object')
            response = parsed
            success = process.returncode == 0 and response.get('ok') is True and response.get('status') == 'published'
            execution['json'] = response
        except (OSError, subprocess.SubprocessError, ValueError, TypeError) as exc:
            execution['exception'] = str(exc)
            success = False
        execution_path = report_dir / f'page-{page["page"]:02d}.json'
        _write_artifacts({execution_path: _json_bytes(execution)})
        row.update(status=response.get('status', 'publish_process_failed'), execution_report_path=str(execution_path))
        if response.get('report_path'):
            row['publisher_report_path'] = response['report_path']
        rows.append(row); _progress(row)
        if not success:
            result = _result(context, rows, False, row['status'], page['page'],
                             response.get('error', execution.get('exception', 'Publisher did not acknowledge this page')))
            break
        published.append(page['page'])
        if response.get('requires_review') is True:
            remaining = [p['page'] for p in context['pages'] if p['page'] > page['page']]
            result = _result(context, rows, False, 'published_requires_review',
                             min(remaining) if remaining else None,
                             '当前页已写入；先看实际页并处理容量风险。需要修订时原位更新本页，确认后从 next_page 继续。')
            result['review_page'] = page['page']
            break
    else:
        result = _result(context, rows, True, 'published_all' if rows else 'nothing_to_do')
    result['published_pages'] = published
    result['report_path'] = str(report_dir / 'summary.json')
    _write_artifacts({Path(result['report_path']): _json_bytes(result)})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('prepare', 'run', 'publish'):
        entry = commands.add_parser(command)
        entry.add_argument('--plan', required=True)
        entry.add_argument('--work-dir', required=True)
        entry.add_argument('--start-page', type=int, default=1)
        if command != 'prepare':
            entry.add_argument('--presentation', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'prepare':
            result = prepare_plan(args.plan, args.work_dir, args.start_page)
        else:
            result = run_plan(args.plan, args.work_dir, args.presentation, args.start_page)
    except (OSError, ValueError, TypeError, KeyError, ET.XMLSyntaxError) as exc:
        result = {'ok': False, 'status': 'invalid_plan', 'error': str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
