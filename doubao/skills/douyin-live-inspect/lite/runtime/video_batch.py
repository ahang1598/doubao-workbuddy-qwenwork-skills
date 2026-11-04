# 核心实现模块：负责本模块的检测、状态、遥测或交付边界；敏感输入和原始响应不进入日志。
"""Agent-driven batch: each next call advances at most one isolated video task."""
from runtime.platform_support import fcntl, nofollow_open, private_directory, private_file
import json
import os
from pathlib import Path
from types import SimpleNamespace

from runtime.store import Store, atomic_json
from runtime.delivery_notice import attach_notice


def public(root, data):
    items = []
    for i, item in enumerate(data['videos']):
        entry = {k: item[k] for k in ('name', 'status', 'error', 'diagnostic') if k in item}
        path = root / 'tasks' / f'{i+1:04d}'
        if (path / 'inspection.db').exists():
            store = Store(path)
            from runtime.recap import recap_report
            recap=recap_report(store)
            entry.update(task_id=store.task_id, task_dir=str(path), progress=store.status(), recap={k:v for k,v in recap.items() if k in ('status','available','message')})
        entry['index'] = i + 1
        items.append(entry)
    return {'task_id':data['id'], 'batch_id': data['id'], 'stopped': data['stopped'], 'items': items}


def dispatch(command, directory, value=None):
    from runtime.transaction import observe_batch, batch_operation
    with batch_operation(directory):
        result = _dispatch(command, directory, value)
    if command == 'batch-create':
        observe_batch(directory, created=True)
    return result


def _dispatch(command, directory, value=None):
    from runtime.cli import start, launch, video_delivery, resume_setup
    root = Path(directory).expanduser().resolve()
    skill = Path(__file__).resolve().parents[2]
    if root == skill or skill in root.parents: raise ValueError('batch must be outside Skill')
    if command == 'batch-create':
        if not isinstance(value, dict) or set(value) - {'videos', 'delivery_mode', 'asr_policy', 'image_inspection'}: raise ValueError('invalid batch')
        videos = value.get('videos')
        if not isinstance(videos, list) or not 1 <= len(videos) <= 100: raise ValueError('batch requires 1..100 videos')
        image_inspection=value.get('image_inspection',False)
        if type(image_inspection) is not bool:raise ValueError('image_inspection must be boolean')
        policy = value.get('asr_policy','remote_first')
        if policy not in {'remote_first','local_first','local_only'}: raise ValueError('invalid ASR policy')
        from runtime.delivery_notice import is_doubao_cloud
        mode = value.get('delivery_mode', 'html_snapshot' if is_doubao_cloud() else 'local_dashboard')
        if mode not in {'local_dashboard', 'html_snapshot', 'chat'}: raise ValueError('invalid delivery mode')
        for item in videos:
            if not isinstance(item, dict) or set(item) - {'source', 'name', 'scenario'}: raise ValueError('invalid video item')
            if not isinstance(item.get('source'), str) or not Path(item['source']).is_absolute(): raise ValueError('local path required')
        # Reserve the batch directory; never overwrite an existing batch or task.
        from runtime.task_context import reserve, FILE
        task_id=reserve(root)
        # The business entry reserves identity and workflow state before batch creation.
        entry_files={FILE, FILE+'.lock', '.workflow-telemetry.json', '.workflow-telemetry.json.lock'}
        if task_id is None or any(p.name not in entry_files or p.is_symlink() or not p.is_file()
                                  for p in root.iterdir()): raise FileExistsError('batch directory already in use')
        (root / 'tasks').mkdir(mode=0o700)
        data = {'id': task_id, 'stopped': False, 'delivery_mode': mode, 'asr_policy':policy,
                'image_inspection':image_inspection, 'videos': [{**item, 'status': 'queued'} for item in videos]}
        atomic_json(root / 'batch.json', data)
        return public(root, data)
    if not root.is_dir() or (os.name!='nt' and root.stat().st_mode & 0o077): raise ValueError('private batch required')
    fd = nofollow_open(root / '.batch.lock', os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = json.loads((root / 'batch.json').read_text(encoding='utf-8'))
        from runtime.transaction import batch_changes
        with batch_changes(data):
            if command == 'batch-stop':
                data['stopped'] = True
                atomic_json(root / 'batch.json', data)
                for i, item in enumerate(data['videos']):
                    if item['status'] == 'active':
                        path = root / 'tasks' / f'{i+1:04d}'
                        if (path / 'inspection.db').exists(): Store(path).request_stop()
                return public(root, data)
            # Explicit child continuation never rewinds the batch. A newer
            # delivered effective snapshot can upgrade an incomplete item in place.
            for i,item in enumerate(data['videos']):
                path=root/'tasks'/f'{i+1:04d}'
                recoverable = item['status']=='partial' or (item['status']=='failed' and item.get('error')=='NO_REVIEWED_CONTENT')
                if recoverable and (path/'inspection.db').exists():
                    from runtime.video_report import delivered_report
                    delivered=delivered_report(Store(path))
                    if delivered and delivered['report']['conclusion'].get('effective_evidence'):
                        status='completed' if delivered.get('processing_complete') and delivered.get('coverage_complete') else 'partial'
                        if item['status'] != status:
                            item['status']=status
                            item.pop('error',None)
                            atomic_json(root/'batch.json',data)
            if command == 'batch-status' or data['stopped']: return public(root, data)
            if command != 'batch-next': raise ValueError('unknown batch command')
            retry_index = (value or {}).get('retry_index')
            if retry_index is not None:
                if type(retry_index) is not int or not 1 <= retry_index <= len(data['videos']):
                    raise ValueError('invalid retry index')
                selected = data['videos'][retry_index - 1]
                if selected['status'] != 'failed':
                    raise ValueError('retry requires a failed item')
                selected['status'] = 'queued'
            for i, item in enumerate(data['videos']):
                if retry_index is not None and i + 1 != retry_index: continue
                if item['status'] in {'completed', 'partial', 'failed'}: continue
                path = root / 'tasks' / f'{i+1:04d}'
                if (path / 'inspection.db').exists():
                    store = Store(path)
                    status = store.status()
                    from runtime.video_report import delivered_report
                    delivered=delivered_report(store)
                    if delivered:
                        if not delivered['report']['conclusion'].get('effective_evidence'):
                            item.update(status='failed', error='NO_REVIEWED_CONTENT')
                        else:
                            item['status'] = 'completed' if delivered.get('processing_complete') and delivered.get('coverage_complete') else 'partial'
                        atomic_json(root / 'batch.json', data)
                        continue
                    if not status['segment_count'] and store.task()['worker_status'] in {'done', 'failed'}:
                        item.update(status='failed', error=store.task().get('setup_error') or 'VIDEO_NO_INSPECTABLE_MEDIA')
                        atomic_json(root / 'batch.json', data)
                        continue
                    if status['report_ready'] or (store.task()['worker_status'] in {'done','failed','stopped'} and status['segment_count']):
                        return {**public(root,data),'current_index':i+1,'task_dir':str(path),
                                'next_action':'report' if status['report_ready'] else 'review-next' if status['review_ready_pending'] else 'report --allow-partial'}
                    # Existing task is always continued by id, including a crash between
                    # SQLite creation and the first worker launch. The worker lock fences launches.
                    task = store.task()
                    if task.get('worker_status') != 'done':
                        check = resume_setup(store)
                        if not check['ready']:
                            return {**public(root, data), 'setup': {'status': 'setup_pending', 'doctor': check}}
                        launch('worker', store)
                    store.update_task(notice_batch={'root':str(root),'id':data['id']})
                    delivery = attach_notice(store, video_delivery(resumed=True))
                    item['status'] = 'active'
                    item.pop('error', None)
                    atomic_json(root / 'batch.json', data)
                    return {**public(root, data), 'current_index': i+1, 'task_dir': str(path),
                            'delivery_required': True, 'delivery': delivery, 'next_action': 'deliver-then-review'}
                item['status'] = 'active'
                atomic_json(root / 'batch.json', data)
                try:
                    from runtime.transaction import batch_context
                    with batch_context(root, data):
                        result = start(SimpleNamespace(task_dir=str(path)),
                            {k: v for k, v in {**item, 'delivery_mode': data['delivery_mode'], 'asr_policy':data.get('asr_policy','local_only'), 'image_inspection':data.get('image_inspection',True)}.items()
                             if k in {'source', 'name', 'scenario', 'delivery_mode','asr_policy','image_inspection'}}, kind='video', notice_batch={'root':str(root),'id':data['id']})
                    if result.get('status') == 'setup_pending':
                        item['status'] = 'queued'
                        atomic_json(root / 'batch.json', data)
                        return {**public(root, data), 'setup': result}
                    item.pop('error', None)
                    atomic_json(root / 'batch.json', data)
                    return {**public(root, data), 'current_index': i+1, 'current': result}
                except (ValueError, OSError, RuntimeError) as error:
                    from runtime.diagnostics import failure_details, is_memory_error
                    from runtime.diagnostics import BUSINESS_ERRORS as ERRORS
                    code = getattr(error, 'code', None)
                    code = 'OUT_OF_MEMORY' if is_memory_error(error) else 'PERMISSION_DENIED' if isinstance(error, PermissionError) else code if code in ERRORS else 'VIDEO_START_FAILED'
                    detail = failure_details(error)
                    item.update(error=code, diagnostic={**detail,
                                                       'index': i+1, 'stage': detail.get('stage', 'video_start')})
                    # A partially created task remains resumable; persist its error too.
                    resumable = (path / 'inspection.db').exists()
                    if not resumable: item['status'] = 'failed'
                    atomic_json(root / 'batch.json', data)
                    if resumable:
                        return {**public(root, data), 'current_index': i+1, 'next_action': 'batch-next'}
                    return {**public(root, data), 'next_action': 'batch-next'}
            return {**public(root, data), 'status': 'completed' if all(item['status']=='completed' for item in data['videos']) else 'partial' if any(item['status'] in {'completed','partial'} for item in data['videos']) else 'failed'}
