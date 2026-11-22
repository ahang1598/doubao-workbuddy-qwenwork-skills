#!/usr/bin/env python3
"""Publish one template page, recording validation diagnostics and real ACKs.

The injected runner has subprocess.run's signature and returns CompletedProcess.
Local image @paths in XML are resolved from --work-dir, which is the CLI CWD.
--local-cache protects updates to an existing real slide ID with a locked,
optimistic read/compare/write guard (not server-side atomic CAS). It accepts
actual single-page XML or documented XML response envelopes and refreshes the
cache as a deck-bound JSON envelope after a conflict or acknowledged readback.
--recover-readback is a read-only recovery for this script's acknowledged
post-write readback barrier; it verifies the original ACK, payload and registry,
refreshes the actual cache and returns readback_recovered_requires_review.
Unknown updates are reconciled once by exact content readback. --recover-write
repeats that read-only check and restores registration only on a content match.
No unknown write is resent. Source-bound native bleed may consume one exception
retry after an explicit server lint rejection; its readback remains required.
Visual contracts and preflight checks are advisory by default. --strict restores
their blocking behavior and the ACK readback barrier. --no-lint directly skips
local visual checks and server lint; --reason is optional. Default ACK readback
differences remain visible for final review without holding subsequent pages.
--exception-file retains the legacy rejection/evidence binding for strict/debug.
"""
from __future__ import annotations

import argparse
try:
    import fcntl
except ImportError:  # Windows uses the standard library byte-range lock.
    fcntl = None
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import uuid
import xml.etree.ElementTree as ET

MODES = ('fixed_template', 'component_reuse', 'active_rebuild')
RECOVERY = ('写入结果未确认，保留 pending。用相同 presentation/page/mode 和原 XML 加 '
            '--recover-write，只读核对实际内容并由脚本恢复登记；add 身份不明时先回读取得真实 '
            'slide-id。ID 存在不代表内容已写入，不能手改登记、删 pending 或盲重发。')
ACK_READBACK_RECOVERY = ('写入已经业务 ACK 并登记，禁止重复 update/add。请按 pending 的 presentation/slide_id '
                         '使用相同 presentation/page/mode、原 XML 路径加 --recover-readback，只读恢复 actual cache '
                         '并保存证据后解除回读 barrier；Main/Organizer 必须检查最新实际页再继续。')


def _acquire_lock(stream):
    if fcntl is not None:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return
    import msvcrt
    if os.fstat(stream.fileno()).st_size == 0:
        stream.write('0'); stream.flush()
    stream.seek(0)
    try:
        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError as exc:
        raise BlockingIOError(str(exc)) from exc


def _release_lock(stream):
    if fcntl is not None:
        fcntl.flock(stream, fcntl.LOCK_UN)
        return
    import msvcrt
    stream.seek(0)
    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def _atomic_json(path: Path, value: dict) -> None:
    """Replace one complete JSON file, never exposing partially written state."""
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        if sys.platform != "win32":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _text(value) -> str:
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='replace')
    return value or ''


def _run(runner, command, cwd: Path, *, input=None, timeout=180) -> dict:
    """Capture the entire response, including diagnostics carried as JSON strings."""
    result = {'command': command, 'cwd': str(cwd)}
    try:
        proc = runner(command, cwd=str(cwd), input=input, capture_output=True,
                      text=True, timeout=timeout, check=False)
        result.update(returncode=proc.returncode, stdout=_text(proc.stdout),
                      stderr=_text(proc.stderr))
    except (OSError, subprocess.SubprocessError) as exc:
        result.update(returncode=None, exception=str(exc),
                      stdout=_text(getattr(exc, 'stdout', None)),
                      stderr=_text(getattr(exc, 'stderr', None)))
    try:
        try:
            parsed = json.loads(result['stdout'])
            result['json_source'] = 'stdout'
        except ValueError:
            if result['stdout'].lstrip().startswith(('{', '[')):
                raise ValueError('Incomplete stdout JSON; write result remains uncertain')
            parsed = json.loads(result['stderr'])
            if not isinstance(parsed, dict) or parsed.get('ok') is not False:
                raise ValueError('stderr is not an explicit rejection envelope')
            result['json_source'] = 'stderr'
        if not isinstance(parsed, dict):
            raise ValueError('JSON envelope must be an object')
        try:
            other = json.loads(result['stderr'])
        except ValueError:
            other = None
        if (result.get('json_source') == 'stdout' and isinstance(other, dict)
                and type(other.get('ok')) is bool and other != parsed):
            raise ValueError('Conflicting stdout/stderr business envelopes')
        result['json'] = parsed
        details = {}
        for parent, key in [('error', 'message'), ('data', 'issues')]:
            container = parsed.get(parent)
            if isinstance(container, dict) and key in container:
                value = container[key]
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except ValueError:
                        pass
                details[parent + '.' + key] = value
        result['decoded_details'] = details
    except ValueError as exc:
        result['json_error'] = str(exc)
    return result


def _registry(path: Path, presentation: str) -> dict:
    if not path.exists():
        return {'version': 1, 'presentation': presentation, 'pages': []}
    state = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(state, dict) or state.get('version') != 1:
        raise ValueError('登记文件格式损坏或版本不支持，先人工核对恢复。')
    if state.get('presentation') != presentation:
        raise ValueError('presentation 与已有登记不一致；不能将同一 work-dir 用于另一个 deck。')
    if not isinstance(state.get('pages'), list):
        raise ValueError('登记文件 pages 必须为列表。')
    pages, ids = set(), set()
    for row in state['pages']:
        if (not isinstance(row, dict) or type(row.get('page')) is not int or row['page'] < 1
                or row.get('presentation') != presentation or row.get('mode') not in MODES
                or not isinstance(row.get('slide_id'), str) or not row['slide_id'].strip()
                or not isinstance(row.get('xml_sha256'), str)):
            raise ValueError('登记行不完整或 deck 不匹配，先人工核对恢复。')
        if row['page'] in pages or row['slide_id'] in ids:
            raise ValueError('登记文件有重复 page 或 slide_id，先人工核对恢复。')
        pages.add(row['page']); ids.add(row['slide_id'])
    return state


def _actual_snapshot(content: str, presentation: str, target: str) -> dict:
    """Parse one actual page; only documented XML envelope paths are unwrapped.

    Namespace prefixes and attribute order are serialization details. Every
    page attribute, text/tail, note, style and descendant remains in the
    fingerprint. Presentation-level geometry/styles also remain; only deck
    identity, revision and title metadata are excluded. A naked actual slide
    is bound by its exact, server-assigned slide ID; any supplied deck identity
    must also match. This is a read/compare/write guard, never atomic CAS.
    """
    identities = []

    def identity(container, deck_keys=('xml_presentation_id', 'presentation_id'),
                 slide_keys=('slide_id',)):
        for key in deck_keys:
            if key in container:
                identities.append(('presentation', container[key]))
        for key in slide_keys:
            if key in container:
                identities.append(('slide', container[key]))

    if content.lstrip().startswith('{'):
        envelope = json.loads(content)
        if not isinstance(envelope, dict) or envelope.get('ok') is not True:
            raise ValueError('缓存/回读 JSON 必须是成功的 XML 回读 envelope。')
        data = envelope.get('data')
        if not isinstance(data, dict):
            raise ValueError('缓存/回读缺少 data。')
        identity(data)
        if data.get('scope', 'slide') not in ('slide', 'presentation'):
            raise ValueError('缓存/回读 scope 无效。')
        candidates = []
        for key in ('slide', 'xml_presentation'):
            part = data.get(key)
            if isinstance(part, dict):
                identity(part)
                if 'content' in part:
                    candidates.append(part['content'])
        # Some older callers save data.xml rather than the shortcut's content.
        if 'xml' in data:
            candidates.append(data['xml'])
        if len(candidates) != 1 or not isinstance(candidates[0], str):
            raise ValueError('缓存/回读必须包含唯一的 allowlisted XML content。')
        content = candidates[0]
    # Match the existing template XML parsers' DTD/entity rejection policy.
    if re.search(r'<!\s*(DOCTYPE|ENTITY)\b', content, re.I):
        raise ValueError('缓存/回读不支持 DTD/entity 声明。')
    root = ET.fromstring(content)
    local = lambda tag: tag.rsplit('}', 1)[-1]
    kind = local(root.tag)
    if kind not in ('presentation', 'slide'):
        raise ValueError('缓存/回读必须是实际 slide 或 presentation XML。')
    identity(root.attrib)
    if kind == 'presentation' and root.get('id') is not None:
        identities.append(('presentation', root.get('id')))
    slides = [node for node in root.iter() if local(node.tag) == 'slide']
    if len(slides) != 1 or (kind == 'presentation' and slides[0] not in list(root)):
        raise ValueError('缓存/回读必须精确包含一张目标页，禁止多页/嵌套页缓存。')
    slide = slides[0]
    if slide.get('id') != target:
        raise ValueError('缓存/回读的实际 slide id 缺失或与更新目标不一致。')
    identity(slide.attrib)
    for label, value in identities:
        if value != (presentation if label == 'presentation' else target):
            raise ValueError('缓存/回读的 ' + label + ' 与目标不一致，禁止跨 deck/页更新。')

    def name(tag):
        # A single-page get may omit the SML namespace inherited in a full get.
        if tag.startswith('{') and tag[1:].split('}', 1)[0].endswith('/sml/2.0'):
            return local(tag)
        return tag

    def tree(node, *, tail=True):
        return (name(node.tag), sorted((name(k), v) for k, v in node.attrib.items()),
                node.text or '', (node.tail or '') if tail else '',
                [tree(child) for child in node])

    context = {}
    if kind == 'presentation':
        metadata = {'id', 'xml_presentation_id', 'presentation_id', 'revision_id', 'revisionId'}
        attrs = sorted((name(k), v) for k, v in root.attrib.items() if k not in metadata)
        children = [tree(child, tail=False) for child in root
                    if child is not slide and local(child.tag) != 'title']
        if attrs or children:
            context = {'attributes': attrs, 'children': children}
    canonical = json.dumps({'slide': tree(slide, tail=False), 'presentation_context': context},
                           ensure_ascii=False, separators=(',', ':'))
    return {'xml': content, 'fingerprint': hashlib.sha256(canonical.encode('utf-8')).hexdigest()}


def _read_actual(runner, work, report, key, presentation, target, report_path):
    """Read latest under the caller's lock, saving the entire response and XML."""
    path = report_path.with_suffix('.' + key + '.xml')
    command = ['lark-cli', 'slides', '+xml-get', '--presentation', presentation,
               '--slide-id', target, '--output', str(path.relative_to(work)), '--json']
    result = report[key] = _run(runner, command, work)
    result['xml_path'] = str(path)
    try:
        response = result.get('json', {})
        data = response.get('data')
        if (result['returncode'] != 0 or response.get('ok') is not True
                or not isinstance(data, dict) or data.get('xml_presentation_id') != presentation
                or data.get('slide_id') != target or data.get('scope', 'slide') != 'slide'
                or data.get('content_saved') is False):
            raise ValueError('实际页回读未成功或响应 presentation/slide_id 不匹配。')
        if isinstance(data.get('slide'), dict) and data['slide'].get('slide_id', target) != target:
            raise ValueError('实际页回读内层 slide_id 不匹配。')
        snapshot = _actual_snapshot(path.read_text(encoding='utf-8'), presentation, target)
        result['fingerprint'] = snapshot['fingerprint']
        return snapshot
    except (OSError, ValueError, ET.ParseError) as exc:
        result['validation_error'] = str(exc)
        return None


def _refresh_cache(path, snapshot, presentation, target):
    # The envelope keeps deck identity with the actual XML even when its root
    # has no presentation attribute; it is accepted regardless of file suffix.
    _atomic_json(path, {'ok': True, 'data': {'xml_presentation_id': presentation,
                 'scope': 'slide', 'slide_id': target,
                 'slide': {'slide_id': target, 'content': snapshot['xml']}}})


def _payload_comparison(payload, actual):
    """Compare full content, allowing only verified service canonical forms.

    ID remapping applies to identity/reference attributes, never media or data
    literals. An unreferenced note ID and rect presetHandlers=0 may be inserted
    by the service when omitted in the payload. Geometry serialization must
    retain the exact numeric value; there is no rounding/pixel tolerance.
    """
    from decimal import Decimal, InvalidOperation

    def local(value):
        if value.startswith('{') and value[1:].split('}', 1)[0].endswith('/sml/2.0'):
            return value.rsplit('}', 1)[-1]
        return value
    numeric = {'topLeftX', 'topLeftY', 'width', 'height', 'startX', 'startY', 'endX', 'endY', 'rotation'}
    references = {'startShapeId', 'endShapeId', 'sourceId', 'targetId', 'beginShapeId',
                  'shapeId', 'ref', 'refId', 'idref'}
    root_metadata = {'id', 'slide_id', 'xml_presentation_id', 'presentation_id'}

    def difference(path, expected, actual):
        return {'path': path, 'expected': expected, 'actual': actual}

    def children(node, path):
        counts = {}
        for child in node:
            tag = local(child.tag)
            counts[tag] = counts.get(tag, 0) + 1
            yield child, path + '/' + tag + '[' + str(counts[tag]) + ']'

    expected, received = ET.fromstring(payload), ET.fromstring(actual)
    if local(received.tag) == 'presentation':
        slides = [n for n in received if local(n.tag) == 'slide']
        if len(slides) != 1:
            return {'content_matches': False,
                    'first_difference': difference('/presentation/slide', 1, len(slides))}
        received = slides[0]

    def ids(root):
        identities = {}
        def visit(node, path):
            for child, child_path in children(node, path):
                value = child.get('id')
                if value:
                    if value in identities:
                        return difference(child_path + '/@id', 'unique member ID', value)
                    identities[value] = child_path
                found = visit(child, child_path)
                if found:
                    return found
        return identities, visit(root, '/slide')

    expected_ids, expected_invalid = ids(expected)
    actual_ids, actual_invalid = ids(received)
    actual_uses = {}
    for node in received.iter():
        for key, value in node.attrib.items():
            if key != 'id':
                actual_uses[value] = actual_uses.get(value, 0) + 1

    def value(key, raw, identities):
        if key in references or key == 'id':
            if raw in identities:
                return ('member', identities[raw])
        if key in numeric:
            try:
                number = Decimal(raw)
                if number.is_finite():
                    return ('number', number)
            except InvalidOperation:
                pass
        return ('literal', raw)

    def compare(left, right, path, root=False):
        if local(left.tag) != local(right.tag):
            return difference(path + '/name()', local(left.tag), local(right.tag))
        left_attrs = {local(k): v for k, v in left.attrib.items()}
        right_attrs = {local(k): v for k, v in right.attrib.items()}
        if root:
            left_attrs = {k: v for k, v in left_attrs.items() if k not in root_metadata}
            right_attrs = {k: v for k, v in right_attrs.items() if k not in root_metadata}
        # Only insertion is verified. Removing authored IDs/defaults is not.
        if (local(left.tag) == 'note' and 'id' not in left_attrs
                and right_attrs.get('id') and not actual_uses.get(right_attrs['id'])):
            right_attrs.pop('id')
        if (local(left.tag) == 'shape' and left.get('type') == right.get('type') == 'rect'
                and 'presetHandlers' not in left_attrs and right_attrs.get('presetHandlers') == '0'):
            right_attrs.pop('presetHandlers')
        for key in sorted(left_attrs.keys() | right_attrs.keys()):
            if (key not in left_attrs or key not in right_attrs
                    or value(key, left_attrs[key], expected_ids) != value(key, right_attrs[key], actual_ids)):
                return difference(path + '/@' + key, left_attrs.get(key), right_attrs.get(key))
        for field, suffix in [('text', '/text()'), ('tail', '/tail()')]:
            if root and field == 'tail':
                continue
            left_text, right_text = getattr(left, field), getattr(right, field)
            left_text = left_text if left_text and left_text.strip() else ''
            right_text = right_text if right_text and right_text.strip() else ''
            if left_text != right_text:
                return difference(path + suffix, left_text, right_text)
        if len(left) != len(right):
            return difference(path + '/*', len(left), len(right))
        for (left_child, child_path), right_child in zip(children(left, path), right):
            found = compare(left_child, right_child, child_path)
            if found:
                return found

    objects = [n for d in expected if local(d.tag) == 'data' for n in d]
    found = expected_invalid or actual_invalid
    if found is None:
        found = compare(expected, received, '/slide', True)
    if found is None and not objects:
        found = difference('/slide/data/*', 'at least one submitted object', 0)
    return {'content_matches': found is None, 'first_difference': found}


def _payload_matches(payload, actual):
    return _payload_comparison(payload, actual)['content_matches']


def _reconcile_write(pending, *, presentation, page, mode, xml, slide_id,
                     work, record_path, runner, report, report_path):
    """Read-only recovery against the publisher's immutable intent/payload."""
    if (not isinstance(pending, dict) or pending.get('status') != 'pending'
            or pending.get('presentation') != presentation or pending.get('page') != page
            or pending.get('mode') != mode or pending.get('operation') not in ('add', 'update')):
        raise ValueError('只读恢复必须绑定原 pending 的 deck/page/mode。')
    old_path = Path(pending.get('report_path', '')).resolve()
    if old_path.parent != work / 'publish-reports' or old_path.suffix != '.json':
        raise ValueError('恢复报告不属于当前 work-dir。')
    old = json.loads(old_path.read_bytes())
    payload = old_path.with_suffix('.xml')
    raw = payload.read_bytes()
    if (old.get('intent') != pending or str(payload) != pending.get('xml')
            or hashlib.sha256(raw).hexdigest() != pending.get('xml_sha256')
            or str(Path(xml).resolve()) not in (old.get('xml'), str(payload))):
        raise ValueError('原 intent、XML 路径或发送哈希不匹配。')
    target = pending.get('slide_id') or slide_id
    if not isinstance(target, str) or not target.strip() or slide_id not in (None, target):
        raise ValueError('必须绑定实际目标 slide-id；不能凭页号猜测 add 的身份。')
    expected = ['lark-cli', 'slides', '+update-slide' if pending['operation'] == 'update' else '+add-slide',
                '--presentation', presentation]
    expected += ['--slide-id', pending['slide_id'], '--content', '-'] if pending['operation'] == 'update' else ['--slide', '-']
    if pending.get('before_slide_id'):
        expected += ['--before-slide-id', pending['before_slide_id']]
    expected += ['--json']
    if pending.get('exception') or pending.get('no_lint'):
        expected += ['--no-lint']
    if old.get('write', {}).get('command') != expected:
        raise ValueError('原写入命令与 pending 不匹配。')
    report['write_recovery'] = {'original_report_path': str(old_path),
        'original_report_sha256': hashlib.sha256(old_path.read_bytes()).hexdigest(),
        'payload_sha256': pending['xml_sha256'], 'slide_id': target}
    actual = _read_actual(runner, work, report, 'write_recovery_readback', presentation, target, report_path)
    comparison = (_payload_comparison(raw.decode('utf-8'), actual['xml']) if actual is not None
                  else {'content_matches': False, 'first_difference': None})
    report['write_recovery'].update(comparison)
    if not comparison['content_matches']:
        return {'status': 'write_content_unconfirmed', 'error': '实际页面缺少或不匹配本次提交内容；未恢复登记。 ' + RECOVERY,
                'first_difference': comparison['first_difference'],
                'pending_path': str(work / 'published-pages.pending.json')}
    state = _registry(record_path, presentation)
    if any(r['slide_id'] == target and r['page'] != page for r in state['pages']):
        raise ValueError('恢复目标已登记为另一页。')
    row = {k: pending[k] for k in ('page', 'mode', 'source', 'xml_sha256', 'presentation')}
    row['slide_id'] = target
    for key in ('layout_contract', 'chart_contract', 'migration_contract', 'style_card', 'exception', 'source_decorations',
                'validation_policy', 'no_lint', 'reason'):
        if key in pending:
            row[key] = pending[key]
    report['write_recovery']['content_matches'] = True
    report['write_recovery']['actual_fingerprint'] = actual['fingerprint']
    row['content_readback'] = {'report_path': str(report_path), 'fingerprint': actual['fingerprint']}
    state['pages'] = sorted([r for r in state['pages'] if r['page'] != page] + [row], key=lambda r: r['page'])
    _atomic_json(report_path, report)
    _atomic_json(record_path, state)
    if pending.get('local_cache'):
        _refresh_cache(Path(pending['local_cache']), actual, presentation, target)
    return {'status': 'published_recovered_requires_review', 'slide_id': target,
            'registry_path': str(record_path), 'xml_readback_complete': True,
            'content_matches': True, 'requires_review': True}


def _decoration_rejection(response, lint):
    """Allow one retry only when every server error is the reviewed native bleed."""
    error = response.get('error')
    if response.get('ok') is not False or not isinstance(error, dict) or str(error.get('code')) != '4000153':
        return None
    import importlib.util
    spec = importlib.util.spec_from_file_location('publisher_lint_inspect', Path(__file__).resolve().parent.parent / 'lint_inspect.py')
    api = importlib.util.module_from_spec(spec); spec.loader.exec_module(api)
    try:
        inspected = api.Inspector(response)
    except (ValueError, TypeError, AttributeError):
        return None
    reviewed = lint.get('checks', {}).get('source_decoration_review', {})
    members = reviewed.get('reviewed', []) if reviewed.get('ok') else []
    if (not members or inspected.diagnostics or not inspected.reports
            or any(not r['counts_match'] for r in inspected.reports)):
        return None
    errors = [r for r in inspected.rows if r['level'] == 'error']
    if not errors:
        return None
    for row in errors:
        issue = row['issue']
        if row['scope'] != 'slide' or not any(
                issue.get('code') == m['code'] and issue.get('elements') == [m['element_id']]
                and issue.get('canvas') == m['canvas'] and issue.get('bbox') == m['bbox'] for m in members):
            return None
    return members


def _recovery_binding(pending, *, presentation, page, mode, xml, slide_id,
                      local_cache, work, record_path):
    """Authorize only the read barrier backed by this publisher's original ACK.

    This does not reconcile unknown writes or claim the read page matches the
    candidate; the immutable payload and ACK establish which write is recovered.
    """
    if (not isinstance(pending, dict) or pending.get('status') != 'acknowledged_readback_required'
            or pending.get('write_acknowledged') is not True or pending.get('operation') not in ('add', 'update')):
        raise ValueError('只读恢复仅适用于本脚本明确 ACK 的后读 barrier；unknown 写入不得用此入口清除。')
    if (pending.get('presentation') != presentation or type(page) is not int
            or pending.get('page') != page or pending.get('mode') != mode or mode not in MODES):
        raise ValueError('恢复 presentation/page/mode 与原写入不一致。')
    target = pending.get('slide_id')
    if not isinstance(target, str) or not target.strip() or slide_id not in (None, target):
        raise ValueError('恢复 slide-id 与原 ACK 目标不一致。')
    cache_value = pending.get('local_cache')
    if cache_value is None and not (pending.get('exception') or pending.get('no_lint')):
        raise ValueError('原 ACK pending 缺少 local_cache。')
    cache = Path(cache_value).resolve() if cache_value else None
    if local_cache is not None and Path(local_cache).resolve() != cache:
        raise ValueError('恢复 local-cache 与原请求不一致。')
    old_path = Path(pending.get('report_path', '')).resolve()
    if old_path.parent != work / 'publish-reports' or old_path.suffix != '.json':
        raise ValueError('恢复必须绑定当前 work-dir 的原 publisher 报告。')
    old_raw = old_path.read_bytes()
    old = json.loads(old_raw)
    if (not isinstance(old, dict) or old.get('intent') != pending
            or old.get('presentation') != presentation or old.get('page') != page
            or old.get('mode') != mode):
        raise ValueError('恢复 pending 与原报告的写入 intent 不一致。')
    payload = Path(pending.get('xml', '')).resolve()
    if (payload != old_path.with_suffix('.xml')
            or hashlib.sha256(payload.read_bytes()).hexdigest() != pending.get('xml_sha256')):
        raise ValueError('恢复原发送 payload 路径/哈希不一致。')
    if str(Path(xml).resolve()) not in (old.get('xml'), str(payload)):
        raise ValueError('恢复 --xml 必须是原 authored 路径或 pending 保存的原发送 payload。')
    write = old.get('write')
    response = write.get('json') if isinstance(write, dict) else None
    data = response.get('data') if isinstance(response, dict) else None
    expected = ['lark-cli', 'slides', '+update-slide' if pending['operation'] == 'update' else '+add-slide',
                '--presentation', presentation]
    expected += ['--slide-id', target, '--content', '-'] if pending['operation'] == 'update' else ['--slide', '-']
    if pending.get('before_slide_id'):
        expected += ['--before-slide-id', pending['before_slide_id']]
    expected += ['--json']
    if isinstance(pending.get('exception'), dict) or pending.get('no_lint'):
        expected += ['--no-lint']
    if (not isinstance(write, dict) or write.get('returncode') != 0
            or not isinstance(response, dict) or response.get('ok') is not True
            or not isinstance(data, dict) or data.get('slide_id') != target
            or data.get('xml_presentation_id', presentation) != presentation
            or write.get('command') != expected or write.get('cwd') != str(work)
            or json.loads(write.get('stdout', '')) != response):
        raise ValueError('恢复缺少原请求的完整业务 ACK；禁止用未知/错页响应解除 barrier。')
    state = _registry(record_path, presentation)
    row = next((r for r in state['pages'] if r['page'] == page), None)
    if row is None or any(row.get(key) != pending.get(key)
                          for key in ('presentation', 'page', 'mode', 'source', 'slide_id', 'xml_sha256',
                                      'layout_contract', 'chart_contract', 'migration_contract',
                                      'style_card', 'exception', 'no_lint', 'reason')):
        raise ValueError('恢复登记行与原 ACK 请求不一致。')
    return cache, target, {'pending': pending, 'original_report_path': str(old_path),
                           'original_report_sha256': hashlib.sha256(old_raw).hexdigest(),
                           'original_write': write, 'write_acknowledged': True}


def _exception_decision(exception_file, reports: Path, presentation: str,
                        page: int, digest: str, target, before_slide_id=None) -> dict:
    """Validate an explicit decision against a complete prior wrapper rejection.

    This validates the evidence binding, not the visual judgment in ``reason``.
    Historical reports remain immutable; a persisted write intent consumes the
    rejection once, including a rejected or interrupted exception attempt.
    """
    try:
        definition_path = Path(exception_file).resolve()
        definition = json.loads(definition_path.read_text(encoding='utf-8'))
        if not isinstance(definition, dict):
            raise ValueError('例外 JSON 必须为对象。')
        reason = definition.get('reason')
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError('例外 reason 必须说明已核验的具体依据。')

        def local_path(value):
            if not isinstance(value, str) or not value.strip():
                raise ValueError('例外报告/视觉证据路径必须为非空字符串。')
            path = Path(value)
            return (definition_path.parent / path).resolve() if not path.is_absolute() else path.resolve()

        old_path = local_path(definition.get('rejection_report'))
        if old_path.parent != reports or old_path.suffix != '.json':
            raise ValueError('例外必须引用当前 work-dir/publish-reports 下的原始 wrapper 拒绝报告。')
        old_raw = old_path.read_bytes()
        old = json.loads(old_raw)
        if not isinstance(old, dict):
            raise ValueError('例外旧报告格式不完整。')
        intent, preflight, write = (old.get(key) for key in ('intent', 'preflight', 'write'))
        if not all(isinstance(part, dict) for part in (intent, preflight, write)):
            raise ValueError('例外旧报告缺少真实 intent/preflight/write。')
        if (old.get('presentation') != presentation or type(old.get('page')) is not int
                or old['page'] != page or intent.get('presentation') != presentation
                or type(intent.get('page')) is not int or intent['page'] != page):
            raise ValueError('例外只限原 presentation 和 page，不能跨 deck 或页使用。')
        if intent.get('xml_sha256') != digest:
            raise ValueError('例外对应的 XML 已修改；必须重新开启服务端 lint 提交。')
        if intent.get('slide_id') != target:
            raise ValueError('例外写入目标 slide_id 与原拒绝请求不一致。')
        if intent.get('before_slide_id') != before_slide_id:
            raise ValueError('例外插入位置与原拒绝请求不一致。')
        if intent.get('report_path') != str(old_path):
            raise ValueError('例外旧报告与其保存的 intent 路径不一致。')
        payload = Path(intent.get('xml', '')).resolve()
        if payload != old_path.with_suffix('.xml') or hashlib.sha256(payload.read_bytes()).hexdigest() != digest:
            raise ValueError('例外缺少与当前 XML 匹配的原始发送 payload。')
        lint = preflight.get('json')
        if (preflight.get('returncode') != 0 or not isinstance(lint, dict)
                or lint.get('ok') is not True or lint.get('status') != 'ready_to_write'
                or not isinstance(preflight.get('command'), list)
                or '--solo' not in preflight['command']
                or not any(Path(str(arg)).name == 'template_lint_all.py' for arg in preflight['command'])
                or json.loads(preflight.get('stdout', '')) != lint):
            raise ValueError('例外旧报告没有完整、通过的本地预检记录。')
        response = write.get('json')
        error = response.get('error') if isinstance(response, dict) else None
        if (write.get('returncode') is None or not isinstance(error, dict)
                or response.get('ok') is not False or str(error.get('code')) != '4000153'
                or write.get('json_source', 'stdout') not in ('stdout', 'stderr')
                or json.loads(write.get(write.get('json_source', 'stdout'), '')) != response
                or not isinstance(old.get('result'), dict)
                or old['result'].get('status') != 'write_rejected'):
            raise ValueError('例外仅适用于完整业务响应确认的 4000153 拒绝。')
        expected = ['lark-cli', 'slides', '+update-slide' if target else '+add-slide',
                    '--presentation', presentation]
        expected += ['--slide-id', target, '--content', '-'] if target else ['--slide', '-']
        if before_slide_id is not None:
            expected += ['--before-slide-id', before_slide_id]
        expected += ['--json']
        if write.get('command') != expected:
            raise ValueError('例外旧请求必须开启服务端 lint，不能使用 no-lint/预览或其他请求。')
        visuals = definition.get('visual_evidence')
        if isinstance(visuals, str):
            visuals = [visuals]
        if not isinstance(visuals, list) or not visuals:
            raise ValueError('例外必须提供本页实际存在的视觉证据。')
        evidence, hashes = [], {}
        for value in visuals:
            path = local_path(value)
            if path.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp', '.pdf') or not path.is_file():
                raise ValueError('例外视觉证据必须为现存 png/jpg/jpeg/webp/pdf 文件。')
            raw = path.read_bytes()
            if not raw:
                raise ValueError('例外视觉证据为空文件。')
            evidence.append(str(path)); hashes[str(path)] = hashlib.sha256(raw).hexdigest()
        for previous in reports.glob('*.json'):
            document = json.loads(previous.read_text(encoding='utf-8'))
            prior_intent = document.get('intent') if isinstance(document, dict) else None
            decision = prior_intent.get('exception') if isinstance(prior_intent, dict) else None
            if isinstance(decision, dict) and decision.get('rejection_report') == str(old_path):
                raise ValueError('例外拒绝报告已用于一次写入尝试，不能沿用或盲重试；请回读核验。')
        return {'exception_file': str(definition_path), 'rejection_report': str(old_path),
                'rejection_report_sha256': hashlib.sha256(old_raw).hexdigest(),
                'reason': reason.strip(), 'visual_evidence': evidence,
                'visual_evidence_sha256': hashes, 'presentation': presentation,
                'page': page, 'xml_sha256': digest}
    except (OSError, ValueError, TypeError) as exc:
        raise ValueError('单页例外校验失败：' + str(exc)) from exc


def publish(*, presentation: str, xml, page: int, mode: str, work_dir,
            source=None, slide_id=None, runner=None, exception_file=None, local_cache=None,
            validation_policy='advisory', no_lint=False, reason=None,
            recover_readback=False, recover_write=False,
            link=None, layout_manifest=None, layout_contract=None, layout_bindings=None,
            source_decorations=None, source_visual=None, fixed_reflow=None,
            chart_inventory=None, chart_contract=None, chart_bindings=None,
            style_card=None, style_bindings=None, style_font_substitutions=None,
            style_overrides=None, migration_contract=None, migration_bindings=None) -> dict:
    """Return a concise result plus an absolute path to the complete report.

    published-pages.json: {version: 1, presentation, pages: [{page, mode,
    source, xml_sha256, slide_id, presentation}]}. Registration is proof of an
    acknowledged write, not proof of rendered correctness; readback is still required.
    """
    runner = runner or subprocess.run
    work = Path(work_dir).resolve()
    work.mkdir(parents=True, exist_ok=True)
    reports = work / 'publish-reports'
    reports.mkdir(exist_ok=True)
    report_path = reports / ('page-' + str(page) + '-' + uuid.uuid4().hex + '.json')
    record_path = work / 'published-pages.json'
    pending_path = work / 'published-pages.pending.json'
    report = {'presentation': presentation, 'page': page, 'mode': mode,
              'xml': str(Path(xml).resolve()), 'validation_policy': validation_policy,
              'no_lint': no_lint, 'reason': reason}
    strict = validation_policy == 'strict'
    enforce_checks = strict and not no_lint
    if exception_file is not None:
        report['exception_file'] = str(Path(exception_file).resolve())

    def finish(status, error=None, **extra):
        if not strict and extra.get('write_acknowledged') and status in (
                'published_readback_failed', 'published_content_unconfirmed', 'readback_recovery_failed'):
            # ACK/registration is durable; readback is a final-review diagnostic.
            report['post_ack_review'] = {'status': status, 'error': error}
            extra.update(needs_final_review=True, requires_review=False, review_status=status,
                         review_error='写入已确认；实际回读、缓存或内容差异见完整报告，留待最终复核。', published=True)
            extra.pop('pending_path', None)
            status, error = 'published', None
            pending_path.unlink(missing_ok=True)
        if not strict and status in ('published', 'published_recovered_requires_review', 'readback_recovered_requires_review'):
            extra.update(needs_final_review=True, requires_review=False, published=True,
                         next='页面已确认并登记；继续制作后页，诊断和 XML/截图差异集中留待最终复核。')
        if isinstance(extra.get('first_difference'), dict):
            concise = dict(extra['first_difference'])
            for field in ('expected', 'actual'):
                if isinstance(concise.get(field), str) and len(concise[field]) > 200:
                    concise[field] = concise[field][:197] + '...'
                    concise[field + '_truncated'] = True
            extra['first_difference'] = concise
        out = {'ok': status in ('published', 'readback_recovered_requires_review', 'published_recovered_requires_review'), 'status': status,
               'report_path': str(report_path), **extra}
        if 'initial_blank' in report:
            out['initial_blank'] = report['initial_blank']
        if not out['ok'] and extra.get('write_acknowledged'):
            out['recovery_flag'] = '--recover-readback'
            out['next'] = '保留原 pending；原发布命令加 --recover-readback，只回读核对原 ACK 页面，不再写入。'
        elif status in ('write_unknown', 'write_content_unconfirmed', 'recovery_required'):
            out['recovery_flag'] = '--recover-write'
            out['next'] = RECOVERY
        if out.get('first_difference') is not None:
            out['next'] = ('页面已 ACK 并登记；first_difference 和完整 expected/actual 留待最终复核。'
                           '可以继续后页，再集中处理内容或视觉差异。') if out['ok'] else (
                           '保留 pending；先核对 first_difference 和报告中的完整 expected/actual。'
                           '只读恢复不会修复内容差异；差异未解决时不要重复恢复或重发。')
        if error:
            out['error'] = error
        report['result'] = out
        _atomic_json(report_path, report)
        return out

    # Advisory OS lock also prevents two writers racing before pending is created.
    with (work / 'published-pages.lock').open('a+') as lock:
        try:
            _acquire_lock(lock)
        except BlockingIOError:
            return finish('publish_in_progress', '同一 work-dir 正在写页；勿并行发布或自动重试。')
        try:
            if validation_policy not in ('advisory', 'strict') or type(no_lint) is not bool:
                raise ValueError('validation_policy 必须为 advisory/strict，no_lint 必须为布尔值。')
            if reason is not None and not isinstance(reason, str):
                raise ValueError('reason 必须为字符串。')
            if recover_write and recover_readback:
                raise ValueError('recover-write 与 recover-readback 只选一种。')
            if recover_write:
                pending = json.loads(pending_path.read_text(encoding='utf-8'))
                if isinstance(pending, dict) and pending.get('status') == 'acknowledged_readback_required':
                    # Both entrypoints are read-only. Keep the original ACK,
                    # payload and registry validation instead of rejecting a
                    # caller who used the generic recovery flag after an ACK.
                    recover_write, recover_readback = False, True
                    report['recovery_route'] = {'requested': '--recover-write', 'effective': '--recover-readback'}
            if recover_write:
                pending = json.loads(pending_path.read_text(encoding='utf-8'))
                result = _reconcile_write(pending, presentation=presentation, page=page, mode=mode,
                    xml=xml, slide_id=slide_id, work=work, record_path=record_path, runner=runner,
                    report=report, report_path=report_path)
                out = finish(**result)
                if out['ok']:
                    pending_path.unlink()
                return out
            if recover_readback:
                try:
                    pending = json.loads(pending_path.read_text(encoding='utf-8'))
                    cache, target, proof = _recovery_binding(pending, presentation=presentation,
                        page=page, mode=mode, xml=xml, slide_id=slide_id, local_cache=local_cache,
                        work=work, record_path=record_path)
                except (OSError, ValueError, TypeError) as exc:
                    return finish('readback_recovery_refused', str(exc),
                                  pending_path=str(pending_path) if pending_path.exists() else None)
                report['recovery'] = proof
                actual = _read_actual(runner, work, report, 'cas_recovery_readback',
                                      presentation, target, report_path)
                if actual is None:
                    return finish('readback_recovery_failed', ACK_READBACK_RECOVERY,
                                  pending_path=str(pending_path), write_acknowledged=True,
                                  requires_readback=True, requires_review=True)
                try:
                    if pending.get('exception') or pending.get('no_lint'):
                        comparison = report['content_readback'] = _payload_comparison(
                            Path(pending['xml']).read_text(encoding='utf-8'), actual['xml'])
                        if not comparison['content_matches']:
                            return finish('readback_recovery_failed', '实际内容仍不匹配已 ACK 的提交；保留 barrier。',
                                          first_difference=comparison['first_difference'],
                                          pending_path=str(pending_path), write_acknowledged=True, requires_review=True)
                    if cache is not None:
                        _refresh_cache(cache, actual, presentation, target)
                    # Save the original ACK plus new read evidence before
                    # removing this read-only barrier. Original reports stay immutable.
                    out = finish('readback_recovered_requires_review', slide_id=target,
                                 registry_path=str(record_path), write_acknowledged=True,
                                 published=False,
                                 cache_refreshed=cache is not None, xml_readback_complete=True,
                                 requires_review=True,
                                 next='只读恢复已完成；Main/Organizer 检查最新实际页、报告和截图后再继续，不代表候选内容已验收。')
                    pending_path.unlink(missing_ok=True)
                    return out
                except OSError as exc:
                    return finish('readback_recovery_failed', str(exc) + ' ' + ACK_READBACK_RECOVERY,
                                  pending_path=str(pending_path), write_acknowledged=True,
                                  requires_readback=True, requires_review=True)
            if pending_path.exists():
                pending = json.loads(pending_path.read_text(encoding='utf-8'))
                if isinstance(pending, dict) and pending.get('status') == 'acknowledged_readback_required':
                    return finish('recovery_required', ACK_READBACK_RECOVERY,
                                  pending_path=str(pending_path), write_acknowledged=True,
                                  requires_readback=True)
                return finish('recovery_required', RECOVERY, pending_path=str(pending_path))
            if not isinstance(presentation, str) or not presentation.strip():
                raise ValueError('presentation ID 不能为空。')
            if type(page) is not int or page < 1 or mode not in MODES:
                raise ValueError('page 必须为正整数，mode 必须为受支持的页型。')
            state = _registry(record_path, presentation)
            existing = next((row for row in state['pages'] if row['page'] == page), None)
            if existing and slide_id is not None and slide_id != existing['slide_id']:
                raise ValueError('显式 slide-id 与该 page 的已有登记冲突；禁止写向另一页。')
            target = existing['slide_id'] if existing else slide_id
            successor = min((row for row in state['pages'] if row['page'] > page),
                            key=lambda row: row['page'], default=None) if target is None else None
            before_slide_id = successor['slide_id'] if successor else None
            if target is not None:
                if not isinstance(target, str) or not target.strip():
                    raise ValueError('slide-id 不能为空。')
                if any(row['slide_id'] == target and row['page'] != page for row in state['pages']):
                    raise ValueError('slide-id 已登记到另一个 page。')
            cache_path, baseline = None, None
            if local_cache is not None:
                if target is None:
                    raise ValueError('local-cache 只允许明确真实 slide-id 的已有页更新；禁止 add 或 fallback。')
                cache_path = Path(local_cache).resolve()
                baseline = _actual_snapshot(cache_path.read_text(encoding='utf-8'), presentation, target)
                report['cas'] = {'local_cache': str(cache_path), 'atomic': False,
                                 'guard': 'optimistic_read_compare_write',
                                 'baseline_fingerprint': baseline['fingerprint']}
            authored = Path(xml).resolve()
            if cache_path is not None and cache_path == authored:
                raise ValueError('local-cache 必须是独立实际回读基线，不能与 authored XML 使用同一路径。')
            raw = authored.read_bytes()
            text = raw.decode('utf-8')
            root = ET.fromstring(text)
            if root.tag.rsplit('}', 1)[-1] != 'slide' or any(
                    node is not root and node.tag.rsplit('}', 1)[-1] == 'slide'
                    for node in root.iter()):
                raise ValueError('一次只能发布一个完整 slide 根，不能提交整稿或嵌套页。')
            if target and root.get('id') not in (None, target):
                raise ValueError('XML 根 id 与更新目标不一致；请先回读并核对目标页。')
            if any(root.get(key) not in (None, presentation) for key in ('presentation_id', 'xml_presentation_id')):
                raise ValueError('XML 根 presentation ID 与目标 deck 不一致。')
            source_path = Path(source).resolve() if source else None
            if source_path and not source_path.is_file():
                report['source_reference'] = {'ok': False, 'error': 'source XML 不存在：' + str(source_path)}
                if enforce_checks:
                    raise ValueError(report['source_reference']['error'])
                source_path = None
            digest = hashlib.sha256(raw).hexdigest()
            style_record = None
            style_path = Path(style_card).resolve() if style_card else work/'manifest/style-card.json'
            overrides_path = Path(style_overrides).resolve() if style_overrides else work/'manifest/style-overrides.json'
            if not no_lint and (style_card is not None or style_overrides is not None or (link == 'L9' and (style_path.exists() or overrides_path.exists()))):
                try:
                    import importlib.util
                    helper = Path(__file__).with_name('template_style_reference.py')
                    spec = importlib.util.spec_from_file_location('template_style_reference_publish', helper)
                    api = importlib.util.module_from_spec(spec); spec.loader.exec_module(api)
                    card_raw = style_path.read_bytes(); card = json.loads(card_raw)
                    if not isinstance(card, dict):
                        raise ValueError('style-card 必须为 JSON 对象。')
                    bindings_path = Path(style_bindings).resolve() if style_bindings else style_path.with_name(style_path.stem+'.bindings.json')
                    bindings_raw = bindings_path.read_bytes() if bindings_path.exists() else None
                    if style_bindings is not None and bindings_raw is None:
                        raise ValueError('指定的 style-bindings 不存在。')
                    substitutions_path = Path(style_font_substitutions).resolve() if style_font_substitutions else None
                    substitutions_raw = substitutions_path.read_bytes() if substitutions_path else None
                    overrides_raw = overrides_path.read_bytes() if overrides_path.exists() and (link == 'L9' or style_overrides is not None) else None
                    if style_overrides is not None and overrides_raw is None:
                        raise ValueError('指定的 style-overrides 不存在。')
                    report['style_card'] = api.validate_sml_roles(text, card,
                        bindings=json.loads(bindings_raw) if bindings_raw is not None else None,
                        font_substitutions=json.loads(substitutions_raw) if substitutions_raw is not None else None,
                        user_overrides=json.loads(overrides_raw) if overrides_raw is not None else None)
                    style_record = {'path':str(style_path),'sha256':hashlib.sha256(card_raw).hexdigest()}
                    if overrides_raw is not None:
                        style_record.update(user_overrides=str(overrides_path),user_overrides_sha256=hashlib.sha256(overrides_raw).hexdigest())
                    if bindings_raw is not None:
                        style_record.update(bindings=str(bindings_path),bindings_sha256=hashlib.sha256(bindings_raw).hexdigest())
                    if substitutions_raw is not None:
                        style_record.update(font_substitutions=str(substitutions_path),font_substitutions_sha256=hashlib.sha256(substitutions_raw).hexdigest())
                    report['style_card']['source'] = style_record
                except (OSError,ValueError,TypeError,KeyError,ImportError,AttributeError) as exc:
                    report['style_card'] = {'ok':False,'errors':[{'code':'missing_or_invalid_style_card','message':str(exc)}]}
                if enforce_checks and report['style_card'].get('ok') is not True:
                    return finish('style_card_blocked','主标题或绑定文本角色未满足样式卡；完整问题见 report_path，尚未写入。')
            layout_record = None
            manifest_path = Path(layout_manifest).resolve() if layout_manifest else work/'manifest/layouts.json'
            requires_layout = link == 'L3' or layout_contract is not None or layout_manifest is not None or (link is None and not source and manifest_path.exists())
            if requires_layout and not no_lint:
                # Never permit a stale/edited contract to redefine source slots.
                try:
                    import importlib.util
                    helper = Path(__file__).with_name('template_layout_contract.py')
                    spec = importlib.util.spec_from_file_location('template_layout_contract_publish', helper)
                    api = importlib.util.module_from_spec(spec); spec.loader.exec_module(api)
                    contract_path = Path(layout_contract).resolve() if layout_contract else work/f'manifest/layout-contracts/page-{page:02d}.json'
                    manifest_raw = manifest_path.read_bytes(); contract_raw = contract_path.read_bytes()
                    manifest = json.loads(manifest_raw); contract = json.loads(contract_raw)
                    if not isinstance(manifest,dict) or not isinstance(contract,dict):
                        raise ValueError('版式目录和绑定文件必须是 JSON 对象。')
                    bindings_path = Path(layout_bindings).resolve() if layout_bindings else contract_path.with_name(contract_path.stem+'.bindings.json')
                    bindings_raw = bindings_path.read_bytes() if bindings_path.exists() else None
                    if layout_bindings and bindings_raw is None:
                        raise ValueError('指定的 layout-bindings 不存在。')
                    bindings = json.loads(bindings_raw) if bindings_raw is not None else None
                    report['layout_contract'] = api.validate_layout_contract(text,contract,manifest=manifest,bindings=bindings)
                    layout_record = {'path':str(contract_path),'sha256':hashlib.sha256(contract_raw).hexdigest(),
                                     'manifest':str(manifest_path),'manifest_sha256':hashlib.sha256(manifest_raw).hexdigest(),
                                     'layout':contract['layout']['name']}
                    if bindings_raw is not None:
                        layout_record.update(bindings=str(bindings_path),bindings_sha256=hashlib.sha256(bindings_raw).hexdigest())
                    report['layout_contract']['source'] = layout_record
                except (OSError,ValueError,TypeError,KeyError) as exc:
                    report['layout_contract'] = {'ok':False,'errors':[{'code':'missing_or_invalid_contract','message':str(exc)}]}
                if enforce_checks and report['layout_contract'].get('ok') is not True:
                    return finish('layout_contract_blocked','L3 必须绑定真实 layout 与源槽位；完整问题见 report_path，尚未写入。')
            chart_record = None
            if not no_lint and (link == 'L6' or chart_contract is not None or chart_inventory is not None):
                try:
                    import importlib.util
                    helper=Path(__file__).with_name('template_chart_contract.py')
                    spec=importlib.util.spec_from_file_location('template_chart_contract_publish',helper)
                    api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
                    inventory_path=Path(chart_inventory).resolve() if chart_inventory else work/'manifest/native-chart-inventory.json'
                    contract_path=Path(chart_contract).resolve() if chart_contract else work/f'manifest/chart-contracts/page-{page:02d}.json'
                    bindings_path=Path(chart_bindings).resolve() if chart_bindings else contract_path.with_name(contract_path.stem+'.bindings.json')
                    inventory_raw=inventory_path.read_bytes();contract_raw=contract_path.read_bytes()
                    bindings_raw=bindings_path.read_bytes() if bindings_path.exists() else None
                    if chart_bindings and bindings_raw is None:raise ValueError('指定的 chart-bindings 不存在。')
                    inventory=json.loads(inventory_raw);contract=json.loads(contract_raw)
                    report['chart_contract']=api.validate_chart_contract(text,contract,inventory=inventory,
                        bindings=json.loads(bindings_raw) if bindings_raw is not None else None)
                    chart_record={'path':str(contract_path),'sha256':hashlib.sha256(contract_raw).hexdigest(),
                                  'inventory':str(inventory_path),'inventory_sha256':hashlib.sha256(inventory_raw).hexdigest(),
                                  'role':contract.get('role') if isinstance(contract,dict) else None}
                    if bindings_raw is not None:chart_record.update(bindings=str(bindings_path),bindings_sha256=hashlib.sha256(bindings_raw).hexdigest())
                    report['chart_contract']['source']=chart_record
                except (OSError,ValueError,TypeError,KeyError) as exc:
                    report['chart_contract']={'ok':False,'errors':[{'code':'missing_or_invalid_chart_contract','message':str(exc)}]}
                if enforce_checks and report['chart_contract'].get('ok') is not True:
                    return finish('chart_contract_blocked','L6 必须绑定实际源图表配置与本题数据；具体问题和替代建议见 report_path，未写入。')
            migration_record = None
            if not no_lint and (link == 'L8' or migration_contract is not None or migration_bindings is not None):
                try:
                    import importlib.util
                    helper = Path(__file__).with_name('template_migration.py')
                    spec = importlib.util.spec_from_file_location('template_migration_publish', helper)
                    api = importlib.util.module_from_spec(spec); spec.loader.exec_module(api)
                    contract_path = Path(migration_contract).resolve() if migration_contract else work/f'manifest/migration-contracts/page-{page:02d}.json'
                    bindings_path = Path(migration_bindings).resolve() if migration_bindings else contract_path.with_name(contract_path.stem+'.bindings.json')
                    contract_raw = contract_path.read_bytes(); contract = json.loads(contract_raw)
                    bindings_raw = bindings_path.read_bytes() if bindings_path.exists() else None
                    if migration_bindings is not None and bindings_raw is None:
                        raise ValueError('指定的 migration-bindings 不存在。')
                    report['migration_contract'] = api.validate_migration(text, contract,
                        bindings=json.loads(bindings_raw) if bindings_raw is not None else None)
                    migration_record = {'path':str(contract_path),
                        'sha256':hashlib.sha256(contract_raw).hexdigest(),
                        'source':contract['source'].get('path'),
                        'source_sha256':contract['source']['sha256']}
                    if bindings_raw is not None:
                        migration_record.update(bindings=str(bindings_path),
                            bindings_sha256=hashlib.sha256(bindings_raw).hexdigest())
                    report['migration_contract']['source'] = migration_record
                except (OSError, ValueError, TypeError, KeyError, ImportError, AttributeError) as exc:
                    report['migration_contract'] = {'ok':False,
                        'errors':[{'code':'missing_or_invalid_migration_contract','message':str(exc)}]}
                if enforce_checks and report['migration_contract'].get('ok') is not True:
                    return finish('migration_contract_blocked',
                        'L8 先用 template_migration.py compose 直接搬运完整原稿内容，'
                        '把 source-bound contract 保存到 manifest/migration-contracts/page-NN.json；'
                        '当前页事实/表格/数据/原备注未守恒，具体问题见 report_path，未写入。')
            decision = None
            if exception_file is not None and not no_lint:
                decision = _exception_decision(exception_file, reports, presentation, page, digest,
                                               target, before_slide_id)
                report['exception'] = decision
            skill_root = Path(__file__).resolve().parents[2]
            command = [sys.executable, str(Path(__file__).with_name('template_lint_all.py')),
                       '--authored', str(authored), '--skill-root', str(skill_root),
                       '--solo', '--page-role', mode]
            if source_path:
                command += ['--source', str(source_path)]
            if source_decorations is not None:
                command += ['--source-decorations',str(Path(source_decorations).resolve())]
            if source_visual:
                for visual in source_visual:
                    command += ['--source-visual', str(Path(visual).resolve())]
            if fixed_reflow is not None:
                command += ['--fixed-reflow',str(Path(fixed_reflow).resolve())]
            report['preflight'] = ({'skipped': True, 'reason': 'caller --no-lint',
                                    'json': {'ok': True, 'status': 'ready_to_write'},
                                    'returncode': 0} if no_lint else _run(runner, command, work))
            lint = report['preflight'].get('json', {})
            if enforce_checks and (report['preflight']['returncode'] != 0 or lint.get('ok') is not True
                    or lint.get('status') != 'ready_to_write'):
                return finish('preflight_blocked', '预检未达到 ready_to_write；完整预检报告见 report_path，禁止写入。',
                              block_reasons=lint.get('block_reasons', []),
                              next='源装饰出血先看源图，再加 --source-visual 原图路径；保留源几何，不移动后再回滚。')
            if authored.read_bytes() != raw:
                return finish('input_changed', 'XML 在预检期间发生变化；未发送，请重新核对后预检。')
            if page == 1 and target is None and not state['pages']:
                import importlib.util
                spec = importlib.util.spec_from_file_location('publisher_initial_blank', Path(__file__).with_name('initial_blank.py'))
                helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
                lookup = report['initial_blank_readback'] = _run(runner,
                    ['lark-cli', 'slides', '+xml-get', '--presentation', presentation, '--json'], work)
                selected = report['initial_blank'] = helper.initial_blank_target(lookup.get('json'), presentation)
                if selected['status'] == 'wrong_deck':
                    return finish('invalid_input', '首张空页回读返回了另一 deck；未写入。')
                if selected['status'] == 'reused':
                    if root.get('id') not in (None, selected['slide_id']):
                        report['initial_blank'] = {'status': 'authored_id_conflict'}
                    else:
                        target = selected['slide_id']
            if cache_path is not None:
                latest = _read_actual(runner, work, report, 'cas_pre_readback',
                                      presentation, target, report_path)
                if latest is None:
                    return finish('cas_readback_failed', '写入前实际页回读失败；未写入、未生成 pending，请恢复回读。')
                if baseline['fingerprint'] != latest['fingerprint']:
                    _refresh_cache(cache_path, latest, presentation, target)
                    return finish('cas_conflict', '实际目标页已变化；缓存已刷新，未写入。请基于最新实际页重新制作本页。',
                                  cache_refreshed=True)

            # Save the exact payload so a timeout/crash can be reconciled by readback.
            payload_path = report_path.with_suffix('.xml')
            with payload_path.open('xb') as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            command = ['lark-cli', 'slides', '+update-slide' if target else '+add-slide',
                       '--presentation', presentation]
            command += ['--slide-id', target, '--content', '-'] if target else ['--slide', '-']
            if before_slide_id is not None:
                command += ['--before-slide-id', before_slide_id]
            command += ['--json']
            if decision is not None or no_lint:
                command += ['--no-lint']
            intent = {'page': page, 'mode': mode, 'presentation': presentation,
                      'source': str(source_path) if source_path else None,
                      'xml_sha256': digest, 'slide_id': target, 'operation': 'update' if target else 'add',
                      'xml': str(payload_path), 'report_path': str(report_path), 'status': 'pending',
                      'validation_policy': validation_policy}
            if no_lint:
                intent.update(no_lint=True, reason=reason)
            if before_slide_id is not None:
                intent['before_slide_id'] = before_slide_id
            if decision is not None:
                intent['exception'] = decision
            if layout_record is not None:
                intent['layout_contract'] = layout_record
            if chart_record is not None:
                intent['chart_contract'] = chart_record
            if migration_record is not None:
                intent['migration_contract'] = migration_record
            if style_record is not None:
                intent['style_card'] = style_record
            decorations = lint.get('checks', {}).get('source_decoration_review', {})
            if decorations.get('ok') and decorations.get('reviewed'):
                intent['source_decorations'] = decorations
            if cache_path is not None:
                intent['local_cache'] = str(cache_path)
            report['intent'] = intent
            _atomic_json(report_path, report)
            _atomic_json(pending_path, intent)  # before any remote write
            report['write'] = _run(runner, command, work, input=text, timeout=120)
            response = report['write'].get('json', {})
            data = response.get('data')
            if report['write']['returncode'] is not None and decision is None and not no_lint:
                members = _decoration_rejection(response, lint)
                if members:
                    # Keep the normal server rejection immutable. Only this
                    # exact payload may consume its source-bound exception once.
                    finish('write_rejected', '仅已复核的原样源装饰出血被服务端拒绝。')
                    rejection_path = report_path
                    definition_path = rejection_path.with_suffix('.exception.json')
                    _atomic_json(definition_path, {'rejection_report': str(rejection_path),
                        'reason': '服务端全部 error 均为严格源/目标报告中已视觉复核的同一装饰出血。',
                        'visual_evidence': list(members[0]['visual_evidence_sha256'])})
                    decision = _exception_decision(definition_path, reports, presentation, page, digest, target, before_slide_id)
                    report_path = reports / ('page-' + str(page) + '-' + uuid.uuid4().hex + '.json')
                    payload_path = report_path.with_suffix('.xml')
                    with payload_path.open('xb') as stream:
                        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
                    report = {k: v for k, v in report.items() if k not in ('write', 'result', 'intent')}
                    report['source_decoration_retry_of'] = str(rejection_path)
                    report['exception'] = decision
                    intent = {**intent, 'exception': decision, 'xml': str(payload_path), 'report_path': str(report_path)}
                    report['intent'] = intent
                    _atomic_json(report_path, report)
                    _atomic_json(pending_path, intent)
                    command = command + ['--no-lint']
                    report['write'] = _run(runner, command, work, input=text, timeout=120)
                    response = report['write'].get('json', {})
                    data = response.get('data')
            if report['write']['returncode'] is not None and response.get('ok') is False:
                rejection = response.get('error')
                advice = ('视觉规则被服务端拒绝；需要跳过时，原发布命令直接加 --no-lint，'
                          '可选 --reason 记录原因。') if isinstance(rejection, dict) and str(rejection.get('code')) == '4000153' else (
                          '读取完整业务错误并修复后再发布。')
                out = finish('write_rejected', '业务 JSON 明确拒绝写入；未登记。', next=advice)
                pending_path.unlink()
                return out
            returned_id = data.get('slide_id') if isinstance(data, dict) else None
            acknowledged = (report['write']['returncode'] == 0 and response.get('ok') is True
                            and isinstance(returned_id, str) and bool(returned_id.strip())
                            and (not target or returned_id == target)
                            and not any(r['slide_id'] == returned_id and r['page'] != page
                                        for r in state['pages'])
                            and data.get('xml_presentation_id', presentation) == presentation)
            if not acknowledged:
                _atomic_json(report_path, report)
                contradictory_identity = (isinstance(data, dict) and (
                    data.get('slide_id') not in (None, target)
                    or data.get('xml_presentation_id', presentation) != presentation))
                if target and not contradictory_identity:
                    result = _reconcile_write(intent, presentation=presentation, page=page, mode=mode,
                        xml=xml, slide_id=target, work=work, record_path=record_path, runner=runner,
                        report=report, report_path=report_path)
                    out = finish(**result)
                    if out['ok']:
                        pending_path.unlink()
                    return out
                return finish('write_unknown', RECOVERY, pending_path=str(pending_path))
            row = {key: intent[key] for key in ('page', 'mode', 'source', 'xml_sha256', 'presentation')}
            row['slide_id'] = returned_id
            row['validation_policy'] = validation_policy
            if no_lint:
                row.update(no_lint=True, reason=reason)
            if 'source_decorations' in intent:
                row['source_decorations'] = intent['source_decorations']
            if decision is not None:
                row['exception'] = decision
            if layout_record is not None:
                row['layout_contract'] = layout_record
            if chart_record is not None:
                row['chart_contract'] = chart_record
            if migration_record is not None:
                row['migration_contract'] = migration_record
            if style_record is not None:
                row['style_card'] = style_record
            state['pages'] = sorted([r for r in state['pages'] if r['page'] != page] + [row],
                                    key=lambda r: r['page'])
            # Persist the full remote response before registering; any crash retains pending.
            _atomic_json(report_path, report)
            _atomic_json(record_path, state)
            if cache_path is not None or decision is not None or no_lint:
                # ACK and registration are durable before the post-write read.
                # Retain a barrier on read/cache failures so no caller resends.
                intent = {**intent, 'status': 'acknowledged_readback_required',
                          'slide_id': returned_id, 'write_acknowledged': True}
                report['intent'] = intent
                _atomic_json(report_path, report)
                if strict:
                    _atomic_json(pending_path, intent)
                else:
                    pending_path.unlink(missing_ok=True)
                actual = _read_actual(runner, work, report, 'cas_post_readback',
                                      presentation, returned_id, report_path)
                if actual is None:
                    return finish('published_readback_failed', ACK_READBACK_RECOVERY,
                                  slide_id=returned_id, registry_path=str(record_path),
                                  pending_path=str(pending_path), write_acknowledged=True,
                                  requires_readback=True, cache_refreshed=False)
                if decision is not None or no_lint or not strict:
                    comparison = report['content_readback'] = _payload_comparison(text, actual['xml'])
                    if not comparison['content_matches']:
                        return finish('published_content_unconfirmed', '业务 ACK 但实际内容不匹配；保留 barrier，不能继续或重发。',
                                      first_difference=comparison['first_difference'],
                                      pending_path=str(pending_path), slide_id=returned_id, write_acknowledged=True)
                try:
                    if cache_path is not None:
                        _refresh_cache(cache_path, actual, presentation, returned_id)
                except OSError as exc:
                    return finish('published_readback_failed', str(exc) + ' ' + ACK_READBACK_RECOVERY,
                                  slide_id=returned_id, registry_path=str(record_path),
                                  pending_path=str(pending_path), write_acknowledged=True,
                                  requires_readback=True, cache_refreshed=False)
            out = finish('published', slide_id=returned_id, registry_path=str(record_path),
                         requires_readback=True,
                         requires_review=bool(lint.get('checks', {}).get('unexpected_wrapping', {}).get('needs_capacity_review')),
                         review_reasons=['unexpected_wrapping'] if lint.get('checks', {}).get('unexpected_wrapping', {}).get('needs_capacity_review') else [],
                         **({'cache_refreshed': cache_path is not None, 'xml_readback_complete': True,
                             'write_acknowledged': True} if cache_path is not None or decision is not None or no_lint else {}),
                         next='页面已写入并登记；请完整读取 report_path 中 issues，回读 XML 并截图核验。文字容量需要复核时先处理本页，再继续后页。')
            pending_path.unlink(missing_ok=True)
            return out
        except (OSError, ValueError, ET.ParseError) as exc:
            if pending_path.exists():
                return finish('write_unknown', str(exc) + ' ' + RECOVERY,
                              pending_path=str(pending_path))
            return finish('invalid_input', str(exc))
        finally:
            _release_lock(lock)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--presentation', required=True, help='目标演示文稿 ID')
    parser.add_argument('--xml', required=True, help='完整单页 XML 文件')
    parser.add_argument('--page', required=True, type=int)
    parser.add_argument('--mode', required=True, choices=MODES)
    parser.add_argument('--work-dir', required=True, help='登记/报告目录，也是本地图片解析 CWD')
    parser.add_argument('--strict', dest='validation_policy', action='store_const', const='strict', default='advisory',
                        help='可选：启用旧版视觉合同/本地预检阻断和 ACK 后读 barrier；默认仅记录诊断')
    parser.add_argument('--no-lint', action='store_true', help='直接跳过本地视觉预检及服务端 lint；仍要求有效单页 XML 和真实业务 ACK')
    parser.add_argument('--reason', help='可选：记录调用者跳过视觉规则的原因，无需例外 JSON 或证据文件')
    parser.add_argument('--source', help='对应模板源页 XML')
    parser.add_argument('--slide-id', help='首次更新已有页时指定；后续使用登记 ID')
    parser.add_argument('--local-cache', help='可选实际单页XML/回读JSON缓存；只允许已知真实slide-id更新，锁内乐观读-比-写，非服务端原子CAS')
    parser.add_argument('--recover-readback', action='store_true', help='只读恢复本脚本已ACK的后读barrier；绑定同deck/页/原XML，绝不add/update，恢复后仍需Main/Organizer验收')
    parser.add_argument('--recover-write', action='store_true', help='只读恢复未知写入；核对精确payload实际内容，由脚本登记，绝不重发')
    parser.add_argument('--exception-file', help='单页例外 JSON：rejection_report、reason、visual_evidence；必须绑定本页当前 XML 的正常 lint 拒绝')
    parser.add_argument('--link', required=True, choices=[f'L{i}' for i in range(1,10)], help='本题模板链路；L3检查源版式，L6检查原生图表合同')
    parser.add_argument('--layout-manifest', help='L3 layouts.json，默认 work-dir/manifest/layouts.json')
    parser.add_argument('--layout-contract', help='L3 每页槽位绑定 JSON，默认 manifest/layout-contracts/page-NN.json')
    parser.add_argument('--layout-bindings', help='改 ID/多元素共用槽时的显式 binding JSON；稳定槽 ID 可省略')
    parser.add_argument('--source-decorations', help='已视觉核对的原样源装饰出血 JSON，传入严格本地预检')
    parser.add_argument('--source-visual', action='append', help='已核对装饰用途的源页图片；自动记录原样出血；服务端仅同一出血拒绝时允许一次例外')
    parser.add_argument('--fixed-reflow', help='固定页内容组件原区内条目重排JSON；源哈希、groups/member_ids/reason')
    parser.add_argument('--chart-inventory', help='L6完整native-chart-inventory.json，默认work-dir/manifest下')
    parser.add_argument('--chart-contract', help='L6单页源图表/新data绑定，默认manifest/chart-contracts/page-NN.json')
    parser.add_argument('--chart-bindings', help='L6 native chart顺序到源chartID，默认page-NN.bindings.json')
    parser.add_argument('--migration-contract', help='L8原稿内容搬运合同，默认manifest/migration-contracts/page-NN.json；由template_migration.py compose生成')
    parser.add_argument('--migration-bindings', help='明确的源ID/媒体token重新绑定JSON；默认合同旁page-NN.bindings.json')
    parser.add_argument('--style-card', help='可选视觉样式卡；L9默认读取work-dir/manifest/style-card.json，缺省无卡不增加检查')
    parser.add_argument('--style-overrides', help='独立保存的explicit_user文字角色要求；L9默认manifest/style-overrides.json，与卡和实际文字一起核对')
    parser.add_argument('--style-bindings', help='文本角色到实际元素ID列表的JSON，例如main_title；默认样式卡旁同名.bindings.json')
    parser.add_argument('--style-font-substitutions', help='可选缺失字体替换JSON列表；from/to/basis=font_unavailable/reason，保留理由并仅豁免该字体')
    args = parser.parse_args(argv)
    try:
        result = publish(**vars(args))
    except OSError as exc:
        result = {'ok': False, 'status': 'local_io_error', 'error': str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
