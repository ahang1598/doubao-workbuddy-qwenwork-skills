"""Immutable submission bindings for the full-live v2 single-agent loop."""
import copy
import hashlib
from pathlib import Path
import json
import os
import shlex
import sys
import tempfile
import uuid

from runtime import full_live

PROTOCOL = 'lite_review_v2'


def enabled(task):
    return full_live.enabled(task) and task.get('review_protocol') == PROTOCOL


def initialize(conn):
    conn.execute(
        'CREATE TABLE IF NOT EXISTS review_contexts '
        '(id TEXT PRIMARY KEY, session_id TEXT NOT NULL, data TEXT NOT NULL)'
    )


def prepare_input(path, template):
    """Project a bound draft onto pending segments; never overwrite damaged input."""
    path = Path(path)
    state = 'created'
    if path.exists():
        raw = path.read_bytes()
        try:
            value = json.loads(raw.decode('utf-8'))
        except (UnicodeError, ValueError, RecursionError):
            value = None
        items = value.get('segments') if isinstance(value, dict) else None
        bound = (isinstance(value, dict) and value.get('task_id') == template['task_id']
                 and value.get('context_id') == template['context_id']
                 and isinstance(items, list) and all(isinstance(s, dict) for s in items))
        ids = [s.get('segment_id') for s in items] if bound else []
        wanted = [s['segment_id'] for s in template['segments']]
        if bound and all(type(i) is int for i in ids) and len(set(ids)) == len(ids) and set(wanted) <= set(ids):
            draft = {**value, 'segments': [next(s for s in items if s['segment_id'] == sid) for sid in wanted]}
            if draft == value:
                return {'input_path': str(path), 'draft_state': 'preserved'}
            template = draft
            state = 'preserved'
        else:
            # Deterministic recovery path keeps the original intact, including foreign bindings.
            recovered = path.with_name(path.stem.split('.recovery-', 1)[0] + '.recovery-' + hashlib.sha256(raw + path.name.encode()).hexdigest()[:16] + '.json')
            result = prepare_input(recovered, template)
            return {**result, 'draft_state': 'recovered'}
    fd, temporary = tempfile.mkstemp(prefix=path.stem + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(template, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {'input_path': str(path), 'draft_state': state}


def attach(store, conn, batch, result, snapshot):
    initialize(conn)
    speech_only = full_live.speech_only_scope(store._task(conn))
    compact_speech = speech_only and store._task(conn).get('inspection_policy') in {'lite_live_realtime_v1','lite_live_realtime_v2'}
    context_id = batch.get('context_id')
    if not context_id:
        context_id = uuid.uuid4().hex
        context = {
            'batch_id': batch['id'],
            'generation': batch['generation'],
            'rules_version': snapshot['version'],
            'targets': batch['targets'],
            'supplements': {
                str(segment['id']): segment['saved_decisions']
                for segment in result['segments']
                if segment.get('review_kind') == 'visual_supplement'
            },
            'modalities': {rule['id']: rule['modalities'] for rule in snapshot['rules']},
            'compact_speech': compact_speech,
            'speech_can_clear': {str(segment['id']):full_live.speech_can_clear(store._task(conn),segment)
                                 for segment in result['segments']},
        }
        conn.execute(
            'INSERT INTO review_contexts VALUES(?,?,?)',
            (context_id, store.session_id, json.dumps(context)),
        )
        batch['context_id'] = context_id
        from runtime.live_review import save
        save(conn, store.session_id, batch)
    else:
        saved_context = json.loads(conn.execute('SELECT data FROM review_contexts WHERE id=? AND session_id=?',
                                               (context_id, store.session_id)).fetchone()[0])
        compact_speech = saved_context.get('compact_speech', False)

    template = {'task_id': store.task_id, 'context_id': context_id, 'segments': []}
    if batch.get('executor') == 'child':
        template['host_task_id'] = batch.get('host_task_id')
    for segment in result['segments']:
        supplement = segment.get('review_kind') == 'visual_supplement'
        rules = [
            {
                'rule_id': rule['id'],
                'status': None,
                'reason': '',
                'events': [],
                'channels': {
                    channel: (
                        {'status': 'not_checked', 'reason': '画面检测关闭，未检查画面'}
                        if speech_only and channel == 'image'
                        else {'status': None, 'reason': ''}
                    )
                    for channel in (['image'] if supplement else rule['modalities'])
                },
            }
            for rule in snapshot['rules']
            if not supplement or 'image' in rule['modalities']
        ]
        if compact_speech:
            for rule in rules:
                rule.pop('channels')
        template['segments'].append({
            'segment_id': segment['id'],
            'summary': '',
            'images_viewed': [],
            'rules': rules,
        })
        if compact_speech:
            template['segments'][-1].update(reviewed=False, rules=[])
        segment['evidence_contract'] = {
            'inspection_scope': 'speech_only' if speech_only else 'speech_and_image',
            'speech': {
                'status': segment['asr_status'],
                'evidence_ids': [utterance['id'] for utterance in segment.get('subtitles', [])],
                'can_clear': full_live.speech_can_clear(store._task(conn), segment),
                'allowed_decisions': (['hit', 'no_hit', 'insufficient'] if full_live.speech_can_clear(store._task(conn), segment) else ['hit', 'insufficient']),
            },
            'image': {
                'status': segment['frame_status'],
                'evidence_ids': [frame['id'] for frame in segment.get('frames', [])],
                'can_clear_after_viewing': bool(segment.get('frames')) and segment['frame_status'] == 'success',
            },
            'missing_evidence_action': (
                '画面检测已关闭，image 渠道用 not_checked；仅按已取得字幕判定规则顶层结果：命中填 hit，未命中填 no_hit（通过），不得仅因 ASR 状态不完整填 insufficient。'
                if speech_only
                else '保留可判语音结论；依赖缺失证据的条件用 insufficient，不把未采样当作无风险。'
            ),
        }

    if store._task(conn).get('rules_mode') == 'dynamic':
        result['rules_load_contract'] = {
            'command':'rules-load','argv':['rules-load','--task-dir',str(store.root),'--next'], 'task_id':store.task_id,
            'loaded_bundles':store._task(conn).get('loaded_rule_bundles',[]),
            'bindings':[{'segment_id':s['id'],'evidence_revision':s['evidence_revision']} for s in result['segments']],
            'required_fields':['task_id','bundle','segment_id','evidence_revision','reason','evidence_ids','images_viewed'],
            'instruction':'内容需要专项时追加 finance 或 ecommerce，引用本批 evidence_ids。通过 stdin 提交并携带 --next，直接使用返回的下一批合同。'}

    output_path = store.root / 'review-input' / (context_id + '.json')
    output_path.parent.mkdir(mode=0o700, exist_ok=True)
    draft = prepare_input(output_path, template)
    output_path = Path(draft['input_path'])
    batch['input_path'] = str(output_path)
    from runtime.live_review import save
    save(conn, store.session_id, batch)

    submit_argv = [
        sys.executable,
        str(Path(__file__).resolve().parents[1] / 'scripts/live_inspect.py'),
        'review-submit', '--task-dir', str(store.root), '--input-file', str(output_path),
        '--next', '--known-rules-version', snapshot['version'],
    ]
    if store._task(conn).get('review_dispatch_version') == 2:
        submit_argv += ['--dispatcher-id', store._task(conn)['review_dispatch']['owner']]
        submit_argv += ['--request-id', uuid.uuid4().hex]
    # Agent commands use the current Lite root; full argv remains for existing programmatic callers.
    result['submission_contract'] = {
        'protocol': PROTOCOL,
        'template': template,
        'input_path': str(output_path),
        'draft_state': draft['draft_state'],
        'submit_command_argv': submit_argv[2:],
        'submit_argv': submit_argv,
        **({'submit_shell_command': shlex.join(submit_argv)} if os.name != 'nt' else {}),
        'state_argv': ['review-state', '--task-dir', str(store.root), '--context-id', context_id],
        'recovery_instruction': '结果未知时按 state_argv 核对；遵循运行时返回的 next_action，完整读取结果，不修改绑定。',
        'instructions': 'Runtime 已在 input_path 写好分行缩进的合法 JSON 模板；先读取文件，再按 segment_id、rule_id 定位并局部编辑语义字段，保留未修改内容和数组/对象闭合符，不整份压成一行重写，不重建绑定字段。保留 context_id 和 segment_id。编辑完成立即提交；JSON 解析失败按 message、line、column 修复原文件，不臆测为截断或重建全部判定。失败仅重交失败段。',
        'decisions': (['hit', 'no_hit', 'insufficient'] if speech_only and all('speech' in r['modalities'] for r in snapshot['rules'])
                      else ['hit', 'no_hit', 'not_applicable', 'insufficient']),
        'channel_decisions': ['hit', 'no_hit', 'not_applicable', 'insufficient'] + (['not_checked'] if speech_only else []),
        'inspection_scope': 'speech_only' if speech_only else 'speech_and_image',
        'event_template': {
            'evidence_ids': ['从本段 evidence_contract 复制实际ID'],
            'description': '实际图片内容；纯语音事件可省略此字段',
        },
        'event_requirements': (
            'hit 必须有 events，每个事件使用 evidence_ids 数组（不是 evidence_id），只引用本段可用ID；非hit的events为空。'
            + (
                '画面检测关闭：保留模板的 image=not_checked；含 speech 的规则顶层与 speech 渠道同结论，纯画面规则顶层为 not_applicable；no_hit 仅表示字幕范围未命中，不得声称画面已通过。'
                if speech_only
                else '图片命中必须先填写images_viewed并描述实际画面。无图的image渠道不得no_hit，需要视觉才能排除的最终结论用insufficient；语音足够可hit。'
            )
        ),
    }
    if compact_speech:
        for segment in result['segments']:
            segment['evidence_contract'].pop('image')
            segment['evidence_contract'].pop('missing_evidence_action')
            segment['evidence_contract']['speech']['allowed_decisions'] = (['hit','no_hit']
                if segment['evidence_contract']['speech']['can_clear'] else ['hit','insufficient'])
        result['submission_contract'].pop('channel_decisions')
        result['submission_contract'].update(decisions=['hit'],
            event_template={'evidence_ids':['本段真实字幕ID']},
            event_requirements='每个命中项必须提供 events，只引用本段真实 evidence_ids。')
        result['submission_contract']['instructions'] = (
            '一次阅读本批字幕，结合核心规则判断。每段填写简短 summary、reviewed=true，rules 只填写命中项'
            '（rule_id、status=hit、reason、events）；未命中时 rules=[]。命中引用本段真实 evidence_ids。'
            '运行时补齐其余规则和渠道。保留 task_id、context_id、segment_id；允许序列化模型已完成的判断。'
            '写入 input_path 后从当前 Lite 目录用同一 Python 环境执行 submit_command_argv，直接处理返回的 next。'
        )


def expand(store, payload):
    """Look up the exact immutable context, never the most recent assignment."""
    def read_context(conn):
        # Missing contexts are invalid input, not a reason to write during a read.
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='review_contexts'").fetchone():
            return None
        return conn.execute(
            'SELECT data FROM review_contexts WHERE id=? AND session_id=?',
            (payload.get('context_id'), store.session_id),
        ).fetchone()
    value = store._read_with_retry(read_context)
    if not value:
        raise ValueError('stale or missing review context')
    context = json.loads(value[0])
    result = copy.deepcopy(payload)
    result['_source_context'] = result.pop('context_id', None)
    if store.task().get('review_dispatch_version') == 2:
        from runtime.live_review import row
        batch = store._read_with_retry(lambda conn:row(conn, store.session_id, context['batch_id']))
        if batch and batch.get('executor') == 'child':
            if batch.get('host_task_id') != payload.get('host_task_id') or not batch.get('host_task_id'):
                raise ValueError('host task binding mismatch')
    for item in [result]:
        segment_id = str(item.get('segment_id')) if isinstance(item, dict) else ''
        if segment_id not in context['targets']:
            raise ValueError('foreign context segment')
        if context.get('compact_speech'):
            if 'reviewed' in item:
                if item.pop('reviewed') is not True or not isinstance(item.get('summary'), str) or not item['summary'].strip():
                    raise ValueError('explicit review confirmation required')
                hits = item.get('rules')
                if (not isinstance(hits, list) or any(not isinstance(r, dict) or r.get('status') != 'hit' for r in hits)
                        or 'no_hit_rule_ids' in item):
                    raise ValueError('each frozen rule requires one decision')
                ids = [r.get('rule_id') for r in hits]
                if any(not isinstance(rid, str) for rid in ids) or len(set(ids)) != len(ids) or not set(ids) <= context['modalities'].keys():
                    raise ValueError('each frozen rule requires one decision')
                item['rules'] = hits + [
                    {'rule_id': rid, 'status':('no_hit' if context.get('speech_can_clear',{}).get(segment_id,True)
                                              else 'insufficient') if 'speech' in modalities else 'not_applicable',
                     'reason':('已检测字幕未命中' if context.get('speech_can_clear',{}).get(segment_id,True)
                               else '语音证据不足') if 'speech' in modalities else '仅字幕检测', 'events':[]}
                    for rid, modalities in context['modalities'].items() if rid not in ids]
            clear_ids = item.pop('no_hit_rule_ids', [])
            if not isinstance(item.get('rules', []), list) or not isinstance(clear_ids, list) or any(not isinstance(rule_id, str) for rule_id in clear_ids):
                raise ValueError('each frozen rule requires one decision')
            if clear_ids:
                item.setdefault('rules', []).extend({'rule_id': rule_id, 'status': 'no_hit',
                    'reason': '已检测字幕未命中', 'events': []} for rule_id in clear_ids)
            for rule in item.get('rules', []):
                if isinstance(rule, dict) and 'channels' not in rule:
                    rule['channels'] = {
                        channel: ({'status': 'not_checked', 'reason': '画面检测关闭，未检查画面'}
                                  if channel == 'image' else {'status': rule.get('status'), 'reason': rule.get('reason')})
                        for channel in context['modalities'].get(rule.get('rule_id'), [])
                    }
        prior = context.get('supplements', {}).get(segment_id)
        if prior:
            incoming = item.get('rules', [])
            expected = {
                rule_id for rule_id, channels in context['modalities'].items()
                if 'image' in channels
            }
            if (
                not isinstance(incoming, list)
                or len(incoming) != len(expected)
                or {rule.get('rule_id') for rule in incoming if isinstance(rule, dict)} != expected
            ):
                raise ValueError('each frozen rule requires one decision')
            incoming = {rule['rule_id']: rule for rule in incoming}
            merged = []
            for saved in prior:
                updated = incoming.get(saved['rule_id'])
                if updated is None:
                    merged.append(copy.deepcopy(saved))
                    continue
                if not isinstance(updated.get('channels'), dict) or set(updated['channels']) != {'image'}:
                    from runtime.review_errors import ReviewValidationError
                    index = next(
                        index for index, rule in enumerate(item['rules'])
                        if rule.get('rule_id') == saved['rule_id']
                    )
                    raise ReviewValidationError(
                        'each rule channel requires a decision', item['segment_id'],
                        saved['rule_id'], f'rules[{index}].channels'
                    )
                from runtime.review_errors import contextual
                index = next(
                    index for index, rule in enumerate(item['rules'])
                    if rule.get('rule_id') == saved['rule_id']
                )
                if (
                    updated.get('status') not in {'hit', 'no_hit', 'not_applicable', 'insufficient'}
                    or not isinstance(updated.get('reason'), str)
                    or not updated['reason'].strip()
                ):
                    raise contextual(
                        ValueError('invalid semantic decision'), item['segment_id'],
                        saved['rule_id'], index
                    )
                events = updated.get('events', [])
                if (
                    not isinstance(events, list)
                    or (updated['status'] == 'hit' and not events)
                    or (updated['status'] != 'hit' and events)
                ):
                    raise contextual(
                        ValueError('hits require evidence events only'), item['segment_id'],
                        saved['rule_id'], index
                    )
                updated['channels'] = {**copy.deepcopy(saved['channels']), **updated['channels']}
                if saved['status'] == 'hit':
                    if updated['status'] != 'hit':
                        updated['reason'] = saved['reason']
                    updated['status'] = 'hit'
                    updated['channels'].update({
                        key: copy.deepcopy(value)
                        for key, value in saved['channels'].items()
                        if value['status'] == 'hit'
                    })
                    updated['events'] = [
                        {**copy.deepcopy(event), 'description': event.get('text', '')}
                        for event in saved['events']
                    ] + updated.get('events', [])
                merged.append(updated)
            item['rules'] = merged
        item.update(
            batch_id=context['batch_id'],
            generation=context['generation'],
            evidence_revision=context['targets'][segment_id],
        )
    return result
