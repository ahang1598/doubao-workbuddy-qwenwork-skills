"""Bounded one-shot review commands. SQLite, not an output pipe, proves a commit."""
import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time
from types import SimpleNamespace
import uuid

from runtime.platform_support import file_lock, nofollow_open, private_directory, process_options, kill_tree, fcntl
from runtime.store import atomic_json, encode

COMMANDS = {'review-next', 'review-submit', 'review-state', 'review-recover', 'result-page'}
_current = None


def active():
    return _current is not None


def source_input(path):
    return _current[1].get('input_path', path) if _current else path


def bind_result(store, conn, result):
    """Commit the request/result binding in the same transaction as allocation."""
    if not active(): return
    from runtime.report_delivery import bounded_output
    task = store._task(conn)
    if task.get('kind', 'live') == 'live' and task.get('review_protocol') == 'lite_review_v2':
        from runtime.live_continuation import annotate
        annotate(result)
    context = result.get('submission_contract', {}).get('template', {}).get('context_id')
    receipt = bounded_output(store, 'review-next', result)
    if context:
        row = conn.execute('SELECT data FROM review_contexts WHERE id=? AND session_id=?',
                           (context, store.session_id)).fetchone()
        contract = json.loads(row[0])
        contract['receipt'] = receipt
        conn.execute('UPDATE review_contexts SET data=? WHERE id=? AND session_id=?',
                     (encode(contract), context, store.session_id))
    key = 'context_id' if _current[1]['command'] == 'review-next' else 'next_context_id'
    bind_request(conn, store.session_id, **({key:context} if context else {}), claim_receipt=receipt)


def bind_request(conn, session_id, **fields):
    # This is a receipt ledger, not a second work queue. Batch state stays authoritative.
    conn.execute('CREATE TABLE IF NOT EXISTS review_requests '
                 '(id TEXT PRIMARY KEY, session_id TEXT NOT NULL, data TEXT NOT NULL)')
    request_id = _current[1]['request_id']
    row = conn.execute('SELECT data FROM review_requests WHERE id=? AND session_id=?',
                       (request_id, session_id)).fetchone()
    data = json.loads(row[0]) if row else {}
    data.update({k:v for k,v in _current[1].items() if k in {
        'request_id','command','argv_digest','fingerprint','input_path','task_id','resume_options'}})
    data.update(fields)
    conn.execute('INSERT OR REPLACE INTO review_requests VALUES(?,?,?)',
                 (request_id, session_id, encode(data)))


def bind_input(root, input_path):
    """Bind a known draft before reading it; damaged bytes cannot change its batch."""
    with contextlib.closing(sqlite3.connect(root/'inspection.db', timeout=.5)) as conn:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='review_batches'").fetchone(): return
        # ponytail: task-local scan; index draft paths if long-running tasks outgrow the command budget.
        for sid, raw in conn.execute('SELECT session_id,data FROM review_batches'):
            batch = json.loads(raw)
            if batch.get('input_path') and Path(batch['input_path']).resolve() == Path(input_path).resolve():
                context = batch.get('context_id')
                if context:
                    with conn: bind_request(conn, sid, context_id=context)
                    _current[1]['context_id'] = context
                return


def request_binding(conn, session_id, request_id):
    if not request_id or not conn.execute("SELECT 1 FROM sqlite_master WHERE name='review_requests'").fetchone():
        return {}
    row = conn.execute('SELECT data FROM review_requests WHERE id=? AND session_id=?',
                       (request_id, session_id)).fetchone()
    return json.loads(row[0]) if row else {}


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value):
        raise ValueError('invalid identity')
    return value


def failure(command, code, request_id=None):
    return {'ok':False, 'command':command, 'error':{
        'code':code, 'next_action':'blocked' if command in {'review-state','result-page'} else 'review-state',
        'message':'请核对原请求和批次的实际保存状态；不要重建任务或重放未知执行。',
        **({'request_id':request_id} if request_id else {})}}


def arguments(argv):
    parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)
    parser.add_argument('command', choices=sorted(COMMANDS))
    for name in ('task-dir', 'request-id', 'context-id', 'input-file', 'dispatch-input-file', 'result-id', 'offset'):
        parser.add_argument('--'+name)
    parser.add_argument('--next', action='store_true', dest='claim_next')
    parser.add_argument('--dispatcher-id', default='main')
    parser.add_argument('--known-rules-version')
    parser.add_argument('--limit', type=int, choices=range(1, 21))
    parser.add_argument('--takeover', action='store_true')
    args, _ = parser.parse_known_args(argv)
    if not args.task_dir:
        raise ValueError('task directory required')
    if args.request_id is not None: identifier(args.request_id)
    if args.context_id is not None: identifier(args.context_id)
    return args


def resume_options(args):
    return {key: getattr(args, key) for key in
            ('claim_next', 'dispatcher_id', 'known_rules_version', 'limit')}


def retry_command(root, input_path, options):
    argv = [sys.executable, str(Path(__file__).resolve().parents[1]/'scripts/live_inspect.py'),
            'review-submit', '--task-dir', str(root), '--input-file', input_path,
            '--request-id', uuid.uuid4().hex]
    if options.get('claim_next'): argv.append('--next')
    for key in ('dispatcher_id', 'known_rules_version', 'limit'):
        if options.get(key) is not None: argv += ['--'+key.replace('_', '-'), str(options[key])]
    return argv


def contract_options(context):
    receipt = context.get('receipt', {}).get('data', {})
    argv = receipt.get('submission_contract', {}).get('submit_argv')
    return resume_options(arguments(argv[2:])) if argv else None


def phase(name, **fields):
    """Only fixed stages and binding IDs; never persist exception text or argv."""
    if _current is None:
        return
    path, record = _current
    if record.get('phase') == name and not fields:
        return
    record['phase'] = name
    record.setdefault('stages', {}).setdefault(name, time.time())
    record.update(fields)
    try: atomic_json(path, record)
    except OSError: pass  # Diagnostics cannot change a business outcome.


def receipt_path(root, request_id):
    return root / '.review-requests' / (identifier(request_id)+'.json')


def read_record(root, request_id):
    path = receipt_path(root, request_id)
    if not path.exists(): return None
    with os.fdopen(nofollow_open(path, os.O_RDONLY), encoding='utf-8') as stream:
        return json.load(stream)


def execution_state(root, record):
    path = receipt_path(root, record['request_id']).with_suffix('.lock')
    if not path.exists(): return 'unknown'
    # Open existing locks only: querying must not create or modify task files.
    with os.fdopen(nofollow_open(path, os.O_RDWR), 'r+b') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 'running'
        fcntl.flock(stream, fcntl.LOCK_UN)
    return 'exited'


def current_recovery(conn, session_id, result):
    seen = set()
    while True:
        context_id = result.get('submission_contract', {}).get('template', {}).get('context_id')
        if not context_id: return result
        if context_id in seen: raise ValueError('cyclic recovery binding')
        seen.add(context_id)
        row = conn.execute('SELECT data FROM review_contexts WHERE id=? AND session_id=?',
                           (context_id, session_id)).fetchone()
        if not row: raise ValueError('recovery context missing')
        context = json.loads(row[0])
        if context.get('recovery'):
            result = context['recovery']
            continue
        task = json.loads(conn.execute('SELECT data FROM live_sessions WHERE id=?', (session_id,)).fetchone()[0])
        segments = {str(sid):json.loads(row[0]) for sid in context['targets']
                    for row in conn.execute('SELECT data FROM segments WHERE id=? AND session_id=?',
                                            (int(sid), session_id))}
        if len(segments) != len(context['targets']): raise ValueError('recovery segment missing')
        if (context['rules_version'] != task['rules_snapshot']['version'] or
                any(segments[sid]['evidence_revision'] != revision for sid, revision in context['targets'].items())):
            return {'task_id':task['id'], 'status':'evidence_changed', 'next_action':'review-next'}
        if (task.get('media_frozen') or task.get('stop_immediately') or
                (task.get('inspection_policy')!='lite_live_realtime_v2' and
                 (task.get('stop_requested') or task.get('capture_status') in {'failed','stopped','ended'}))):
            return {'task_id':task['id'], 'status':'stopped', 'next_action':'status'}
        statuses = [segment['review_status'] for segment in segments.values()]
        if all(status == 'done' for status in statuses):
            if context.get('continuation'):
                result = context['continuation']
                continue
            return {'task_id':result.get('task_id'), 'status':'saved', 'next_action':'review-next',
                    'saved_segment_ids':[int(sid) for sid in context['targets']]}
        if 'skipped' in statuses:
            return {'task_id':result.get('task_id'), 'status':'stopped', 'next_action':'status'}
        return result


def recovery_view(root, conn, session_id, result):
    from runtime.report_delivery import bounded_output
    return bounded_output(SimpleNamespace(root=root), 'review-recover',
                          current_recovery(conn, session_id, result), read_only=True)['data']


def state(root, request_id=None, context_id=None):
    if not request_id and not context_id: raise ValueError('identity required')
    record = read_record(root, request_id) if request_id else None
    requested_context = context_id
    context_id = context_id or (record or {}).get('context_id')
    execution = execution_state(root, {'request_id':request_id}) if request_id else 'unknown'
    result = {'request_id':request_id, 'execution_status':execution,
              'phase':(record or {}).get('phase', 'not_observed'),
              'stages':(record or {}).get('stages', {}),
              'error_code':(record or {}).get('error_code'),
              'diagnostics':(record or {}).get('diagnostics', []),
              'status':'unknown', 'next_action':'observe-original-command'}
    if record and record.get('response'): result['receipt'] = record['response']
    # URI read-only connection, no Store initialization, PRAGMA writes or finish_tick.
    with contextlib.closing(sqlite3.connect((root/'inspection.db').as_uri()+'?mode=ro', uri=True, timeout=.2)) as conn:
        conn.execute('BEGIN')
        sid, raw = conn.execute('SELECT id,data FROM live_sessions').fetchone()
        task = json.loads(raw)
        if record and record.get('task_id') not in (None, task['id']): raise ValueError('task mismatch')
        result['task_id'] = task['id']
        binding = request_binding(conn, sid, request_id)
        if request_id and requested_context and not record and not binding:
            raise ValueError('request binding unavailable')
        record = {**(record or {}), **binding}
        if binding.get('context_id'):
            if requested_context and requested_context != binding['context_id']:
                raise ValueError('request/context mismatch')
            context_id = binding['context_id']
        if requested_context and record and not binding.get('context_id') and record.get('context_id') != requested_context:
            raise ValueError('request/context mismatch')
        if binding.get('recovery_receipt'):
            result.update(status='recovered', recovery_receipt=recovery_view(root, conn, sid, binding['recovery_receipt']),
                          next_action='read-recovery-result')
            return result
        if binding.get('claim_receipt'):
            result['claim_receipt'] = binding['claim_receipt']
            result['next_context_id'] = binding.get('next_context_id')
        if not context_id:
            if binding.get('claim_receipt') or (record and record.get('response',{}).get('ok')):
                result.update(status='result_available', next_action='read-request-result')
                if binding.get('claim_receipt'): result['receipt'] = binding['claim_receipt']
            elif execution == 'exited':
                result.update(status='not_committed', next_action=(
                    'repair-review-input' if record.get('command') == 'review-submit' else 'review-next'))
                result['input_path'] = record.get('input_path')
            if execution == 'running': result['next_action'] = 'observe-original-command'
            return result
        identifier(context_id)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        row = (conn.execute('SELECT data FROM review_contexts WHERE id=? AND session_id=?', (context_id,sid)).fetchone()
               if 'review_contexts' in tables else None)
        if not row:
            if not record: raise ValueError('context missing')
            result.update(status='not_committed', next_action='repair-review-input'
                          if record.get('command') == 'review-submit' else 'review-next')
            if execution != 'exited': result['next_action'] = 'observe-original-command'
            return result
        context = json.loads(row[0])
        if context.get('recovery'):
            result.update(status='superseded', context_id=context_id,
                          recovery_receipt=recovery_view(root, conn, sid, context['recovery']), next_action='read-recovery-result')
            return result
        if context.get('receipt'): result['contract_receipt'] = context['receipt']
        row = conn.execute('SELECT data FROM review_batches WHERE id=? AND session_id=?', (context['batch_id'],sid)).fetchone()
        if not row: raise ValueError('batch missing')
        batch = json.loads(row[0])
        input_path = ((record or {}).get('input_path')
                      if (record or {}).get('command') == 'review-submit' else None) or batch.get('input_path')
        saved, pending, changed, skipped = [], [], [], []
        for segment_id, revision in context['targets'].items():
            row = conn.execute('SELECT data FROM segments WHERE id=? AND session_id=?', (int(segment_id),sid)).fetchone()
            segment = json.loads(row[0]) if row else {}
            target = (changed if segment.get('evidence_revision') != revision else
                      saved if segment.get('review_status') == 'done' else
                      skipped if segment.get('review_status') == 'skipped' else pending)
            target.append(int(segment_id))
        stale = (batch['generation'] != context['generation'] or batch.get('context_id') != context_id
                 or context['rules_version'] != task['rules_snapshot']['version'])
        result.update(context_id=context_id, batch_id=context['batch_id'], generation=context['generation'],
            batch_status=batch['status'], executor=batch['executor'], host_task_id=batch.get('host_task_id'),
            input_path=input_path if not stale else None,
            saved_segment_ids=saved, pending_segment_ids=pending, changed_segment_ids=changed,
            skipped_segment_ids=skipped, last_submitted_at=batch.get('submitted_at'),
            last_error=batch.get('last_review_error'))
        if changed or stale:
            result.update(status='evidence_changed', next_action='review-next')
        elif skipped:
            result.update(status='stopped', next_action='status')
        elif not pending:
            result.update(status='saved', next_action='review-next')
        else:
            result['status'] = 'partial' if saved else 'pending'
            if batch.get('executor') == 'child' and batch['status'] in {'dispatching','running','cancelling'}:
                result['next_action'] = 'observe-review-worker'
            elif execution == 'exited':
                result['next_action'] = 'repair-review-input' if batch.get('last_review_error') or record.get('error_code') else 'review-submit'
                options = record.get('resume_options') or contract_options(context)
                result['retry_argv'] = retry_command(root, input_path, options or {})
                result['retry_command_argv'] = result['retry_argv'][2:]
                if options is None:
                    result['after_submit_action'] = 'review-next'
            if not saved and execution == 'exited' and (record or {}).get('command') == 'review-next':
                result['next_action'] = 'read-request-result' if record.get('response') else 'review-next'
        if batch.get('executor') == 'child' and batch['status'] in {'dispatching','running','cancelling'}:
            result['next_action'] = 'observe-review-worker'
        if binding.get('claim_receipt') and result['next_action'] != 'observe-review-worker' and result['status'] not in {'evidence_changed','stopped'}:
            if pending and not binding.get('next_context_id'):
                result.update(receipt=binding['claim_receipt'], next_action='read-request-result')
            elif not pending and binding.get('next_context_id'):
                following = state(root, context_id=binding['next_context_id'])
                result['next_batch'] = following
                if following.get('recovery_receipt'):
                    result.update(recovery_receipt=following['recovery_receipt'], next_action='read-recovery-result')
                elif following['next_action'] == 'observe-review-worker':
                    result['next_action'] = 'observe-review-worker'
                elif following['status'] in {'pending','partial'}:
                    result.update(receipt=binding['claim_receipt'], next_action='read-request-result')
        if batch.get('executor') == 'main' and result['status'] in {'pending','partial','saved'}:
            result['recovery_argv'] = [sys.executable, str(Path(__file__).resolve().parents[1]/'scripts/live_inspect.py'),
                'review-recover','--task-dir',str(root),'--context-id',context_id,
                '--dispatcher-id',task.get('review_dispatch',{}).get('owner','main'),
                '--request-id',uuid.uuid4().hex,'--takeover']
            result['recovery_command_argv'] = result['recovery_argv'][2:]
            result['recovery_requires_explicit_request'] = True
        if execution == 'running': result['next_action'] = 'observe-original-command'
    return result


def input_bytes(path):
    from runtime.recap_submission import _read_fd, MAX_BYTES
    import stat
    fd = nofollow_open(path, os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0))
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode): raise ValueError('regular input required')
        raw = _read_fd(fd)
    finally: os.close(fd)
    if len(raw) > MAX_BYTES: raise ValueError('input too large')
    return raw


def child(argv, request_id, compact):
    global _current
    args = arguments(argv)
    root = Path(args.task_dir).expanduser().resolve()
    if args.command == 'result-page':
        from runtime.report_delivery import result_page
        return {'ok':True, 'command':args.command, 'data':result_page(
            SimpleNamespace(root=root), args.result_id, int(args.offset or 0))}, 0
    if args.command == 'review-state':
        return {'ok':True, 'command':args.command,
                'data':state(root, args.request_id, args.context_id)}, 0
    if not (root/'inspection.db').is_file(): raise ValueError('task missing')
    folder = private_directory(root/'.review-requests')
    path = receipt_path(root, request_id)
    # Hash exact arguments and bytes actually submitted. Snapshot the input so an
    # editor cannot change it between request binding and business execution.
    input_path = args.input_file or args.dispatch_input_file
    if not input_path and compact and args.command == 'review-submit':
        return failure(args.command, 'INPUT_FILE_REQUIRED', request_id), 1
    argv_digest = hashlib.sha256(encode(argv).encode()).hexdigest()
    try:
        with file_lock(path.with_suffix('.lock'), timeout=0):
            old = read_record(root, request_id)
            if old is None:
                with contextlib.closing(sqlite3.connect((root/'inspection.db').as_uri()+'?mode=ro', uri=True, timeout=.2)) as conn:
                    session = conn.execute('SELECT id FROM live_sessions').fetchone()[0]
                    old = request_binding(conn, session, request_id) or None
            if old and old['argv_digest'] != argv_digest:
                return failure(args.command, 'REQUEST_CONFLICT', request_id), 1
            if not old:
                record = {'request_id':request_id, 'argv_digest':argv_digest,
                          'command':args.command, 'input_path':input_path, 'state':'running', 'stages':{},
                          'resume_options':resume_options(args)}
                _current = (path, record)
                atomic_json(path, record)  # Establish identity before any business effect.
                if args.command == 'review-recover': record['context_id'] = args.context_id
                phase('cli_started')
                if args.command == 'review-submit' and input_path: bind_input(root, input_path)
                phase('input_read_started')
            if args.command == 'review-recover':
                if old: _current = (path, old)
                if not args.takeover or not args.context_id or not args.request_id:
                    raise ValueError('explicit takeover and identities required')
                from runtime.review_recovery import recover
                data = recover(root, args.context_id, args.dispatcher_id)
                from runtime.report_delivery import bounded_output
                response = bounded_output(SimpleNamespace(root=root), args.command, data)
                if not old: phase('result_persisted', response=response, state='completed', exit_code=0)
                return response, 0
            raw = input_bytes(input_path) if input_path else None
            fingerprint = hashlib.sha256(encode(argv).encode()+b'\0'+(raw or b'')).hexdigest()
            if old:
                if old.get('fingerprint') and old['fingerprint'] != fingerprint:
                    return failure(args.command, 'REQUEST_CONFLICT', request_id), 1
                if not old.get('response'):
                    return failure(args.command, 'REQUEST_RECONCILE_REQUIRED', request_id), 1
                return old['response'], old.get('exit_code', 0)
            phase('input_read', fingerprint=fingerprint)
            with contextlib.closing(sqlite3.connect((root/'inspection.db').as_uri()+'?mode=ro',uri=True,timeout=.2)) as conn:
                record['task_id'] = json.loads(conn.execute('SELECT data FROM live_sessions').fetchone()[0])['id']
            call_argv = list(argv)
            if args.request_id:
                index = call_argv.index('--request-id') if '--request-id' in call_argv else None
                if index is not None: del call_argv[index:index+2]
                else: call_argv = [a for a in call_argv if not a.startswith('--request-id=')]
            if raw is not None:
                binding_mismatch = False
                record['input_path'] = str(Path(input_path).expanduser().resolve())
                try:
                    value = json.loads(raw)
                    context = value.get('context_id') if isinstance(value,dict) else None
                    if context and args.command == 'review-submit':
                        binding_mismatch = bool(record.get('context_id') and record['context_id'] != context)
                        if not binding_mismatch: record['context_id'] = identifier(context)
                except (UnicodeError, ValueError): pass  # CLI returns precise syntax diagnostics.
                if binding_mismatch: raise ValueError('input/context mismatch')
                snapshot = folder/(request_id+'.input.json')
                from runtime.static_delivery import atomic
                atomic(snapshot, raw)
                option = '--input-file' if args.input_file else '--dispatch-input-file'
                if option in call_argv: call_argv[call_argv.index(option)+1] = str(snapshot)
                else: call_argv = [option+'='+str(snapshot) if a.startswith(option+'=') else a for a in call_argv]
            if args.command == 'review-submit' and record.get('context_id'):
                with contextlib.closing(sqlite3.connect(root/'inspection.db', timeout=.5)) as conn:
                    with conn:
                        row = conn.execute('SELECT session_id FROM review_contexts WHERE id=?',
                                           (record['context_id'],)).fetchone()
                        if row: bind_request(conn, row[0], context_id=record['context_id'])
            phase('business_started')
            from runtime.cli import main
            output = io.StringIO()
            try:
                with contextlib.redirect_stdout(output): code = main(call_argv)
                envelope = json.loads(output.getvalue())
            finally:
                # Input is retained only in its existing Agent-authored draft.
                if raw is not None: snapshot.unlink(missing_ok=True)
            data = envelope.get('data', {})
            if args.command == 'review-submit' and data.get('repair_required'):
                # A repaired draft is a new request; preserve automatic continuation.
                data['retry_argv'] = retry_command(root, input_path, record['resume_options'])
                data['retry_command_argv'] = data['retry_argv'][2:]
                data['repair_instruction'] = '仅修复失败段，然后从当前 Lite 目录用同一 Python 环境执行 retry_command_argv；不要复用原 request-id，不必额外核对已明确失败的请求。'
            contract = data.get('submission_contract', {})
            context = contract.get('template', {}).get('context_id')
            if context: record.setdefault('context_id', context)
            phase('business_returned')
            if envelope.get('ok'):
                from runtime.report_delivery import bounded_output
                response = bounded_output(SimpleNamespace(root=root), args.command, data)
                response['data']['request_id'] = request_id
            else: response = envelope
            # Evidence lives only in the versioned result, never in stage records.
            phase('result_persisted', response=response,
                  state='completed', exit_code=code)
            return response if compact else envelope, code
    except Exception as error:
        if not isinstance(error, TimeoutError):
            from runtime.diagnostics import log_failure
            log_failure(error, stage='review_command')
            raise
        old = read_record(root, request_id)
        return failure(args.command, 'REQUEST_CONFLICT' if old and old['argv_digest'] != argv_digest else 'REQUEST_RUNNING', request_id), 1
    finally:
        _current = None


def worker(argv, request_id, compact):
    try:
        for attempt in range(3):
            try:
                result, code = child(argv, request_id, compact)
                break
            except sqlite3.OperationalError as error:
                if argv[0] != 'review-state' or attempt == 2 or getattr(error,'sqlite_errorcode',0) & 255 not in (5,6,10):
                    raise
                time.sleep(.05 * (attempt+1))
    except (Exception, SystemExit) as error:
        from runtime.review_errors import ReviewError
        if argv[0] == 'review-recover' and isinstance(error, ValueError) and not isinstance(error, ReviewError):
            from runtime.review_errors import review_error
            detail = review_error(error)
            if detail:
                print(encode({'ok':False,'command':argv[0],'error':detail}),flush=True)
                return 1
        if isinstance(error, ReviewError):
            print(encode({'ok':False,'command':argv[0],'error':error.detail}),flush=True)
            return 1
        from runtime.diagnostics import is_memory_error
        code_name = ('OUT_OF_MEMORY' if is_memory_error(error) else 'REVIEW_STORAGE_UNAVAILABLE' if isinstance(error,sqlite3.Error) else
                     'REVIEW_BINDING_INVALID' if isinstance(error,ValueError) else 'REVIEW_COMMAND_UNAVAILABLE')
        result, code = failure(argv[0], code_name, request_id), 1
        if argv[0] not in {'review-state','result-page'}:
            try:
                root = Path(arguments(argv).task_dir).expanduser().resolve()
                path = receipt_path(root, request_id)
                with file_lock(path.with_suffix('.lock'), timeout=0):
                    record = read_record(root, request_id)
                    if record and not record.get('response'):
                        record.update(error_code=code_name, exit_code=1)
                        atomic_json(path, record)
            except Exception: pass  # Supervisor still bounds unavailable storage.
    print(encode(result), flush=True)
    return code


def supervise(argv):
    """The supervisor touches no task files: blocked filesystem calls stay in child."""
    command = argv[0]
    if command == 'review-recover' and any(a in ('-h','--help') for a in argv):
        print('review-recover --task-dir PATH --context-id ID --dispatcher-id ID --request-id ID --takeover\n'
              'Explicit serial takeover; never restarts capture.')
        return 0
    if command == 'review-state' and any(a in ('-h','--help') for a in argv):
        print('review-state --task-dir PATH [--request-id ID] [--context-id ID]\n'
              'Read-only reconciliation; at least one identity is required.')
        return 0
    try: args = arguments(argv)
    except (Exception, SystemExit):
        print(encode(failure(command, 'REVIEW_ARGUMENT_INVALID'))); return 1
    request_id = args.request_id or uuid.uuid4().hex
    print(encode({'event':'review_execution','command':command,'request_id':request_id,
                  'stage':'supervisor_started','time':time.time()}), file=sys.stderr, flush=True)
    budget = 3 if command in {'review-state', 'result-page'} else 10
    script = ('import sys; from runtime.review_execution import worker; '
              'sys.exit(worker(sys.argv[3:],sys.argv[1],sys.argv[2]=="1"))')
    env = dict(os.environ)
    # No optional Node bridge or network work on this latency-critical path.
    env.pop('BYTEDLIVE_LITE_TELEMETRY_IDENTITY', None)
    try:
        process = subprocess.Popen([sys.executable, '-c', script, request_id,
            '1' if args.request_id else '0', *argv], cwd=Path(__file__).resolve().parents[1],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env, **process_options())
    except OSError:
        print(encode(failure(command, 'REVIEW_START_FAILED', request_id))); return 1
    try:
        output, _ = process.communicate(timeout=budget)
        result = json.loads(output)
        if not isinstance(result, dict) or type(result.get('ok')) is not bool:
            raise ValueError('invalid command response')
    except subprocess.TimeoutExpired:
        kill_tree(process)
        result = failure(command, 'REVIEW_COMMAND_TIMEOUT', request_id)
        try:
            process.communicate(timeout=2)
            result['error']['exit_confirmed'] = True
        except subprocess.TimeoutExpired:
            result['error']['exit_confirmed'] = False
    except (ValueError, UnicodeError):
        result = failure(command, 'REVIEW_OUTPUT_UNAVAILABLE', request_id)
    except BaseException:
        kill_tree(process)
        process.communicate(timeout=2)
        raise
    if command not in {'review-state', 'result-page'} and not result.get('ok'):
        result['error']['state_argv'] = ['review-state','--task-dir',args.task_dir,'--request-id',request_id]
    print(encode({'event':'review_execution','command':command,'request_id':request_id,
                  'stage':'output_ready','time':time.time(),'exit_code':process.poll()}), file=sys.stderr, flush=True)
    print(encode(result), flush=True)
    return 0 if result.get('ok') else 1
