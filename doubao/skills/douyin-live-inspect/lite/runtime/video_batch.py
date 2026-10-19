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
        entry = {k: item[k] for k in ('name', 'status', 'error') if k in item}
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
    from runtime.task_telemetry import observe_batch, batch_operation
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
        if task_id is None or any(p.name != FILE for p in root.iterdir()): raise ValueError('batch directory already in use')
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
        from runtime.task_telemetry import batch_changes
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
            # delivered full snapshot can upgrade a prior partial item in place.
            for i,item in enumerate(data['videos']):
                path=root/'tasks'/f'{i+1:04d}'
                if item['status']=='partial' and (path/'inspection.db').exists():
                    from runtime.video_report import delivered_report
                    delivered=delivered_report(Store(path))
                    if delivered and delivered.get('processing_complete') and delivered.get('coverage_complete'):
                        item['status']='completed'
                        atomic_json(root/'batch.json',data)
            if command == 'batch-status' or data['stopped']: return public(root, data)
            if command != 'batch-next': raise ValueError('unknown batch command')
            for i, item in enumerate(data['videos']):
                if item['status'] in {'completed', 'partial', 'failed'}: continue
                path = root / 'tasks' / f'{i+1:04d}'
                if (path / 'inspection.db').exists():
                    store = Store(path)
                    status = store.status()
                    from runtime.video_report import delivered_report
                    delivered=delivered_report(store)
                    if delivered:
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
                    atomic_json(root / 'batch.json', data)
                    return {**public(root, data), 'current_index': i+1, 'task_dir': str(path),
                            'delivery_required': True, 'delivery': delivery, 'next_action': 'deliver-then-review'}
                item['status'] = 'active'
                atomic_json(root / 'batch.json', data)
                try:
                    from runtime.task_telemetry import batch_context
                    with batch_context(root, data):
                        result = start(SimpleNamespace(task_dir=str(path)),
                            {k: v for k, v in {**item, 'delivery_mode': data['delivery_mode'], 'asr_policy':data.get('asr_policy','local_only'), 'image_inspection':data.get('image_inspection',True)}.items()
                             if k in {'source', 'name', 'scenario', 'delivery_mode','asr_policy','image_inspection'}}, kind='video', notice_batch={'root':str(root),'id':data['id']})
                    if result.get('status') == 'setup_pending':
                        item['status'] = 'queued'
                        atomic_json(root / 'batch.json', data)
                        return {**public(root, data), 'setup': result}
                    return {**public(root, data), 'current_index': i+1, 'current': result}
                except (ValueError, OSError, RuntimeError) as error:
                    # A partially created task remains resumable; never start a replacement.
                    if (path / 'inspection.db').exists():
                        return {**public(root, data), 'current_index': i+1, 'next_action': 'batch-next'}
                    item.update(status='failed', error=getattr(error, 'code', 'VIDEO_START_FAILED'))
                    atomic_json(root / 'batch.json', data)
                    return {**public(root, data), 'next_action': 'batch-next'}
            return {**public(root, data), 'status': 'completed' if all(item['status']=='completed' for item in data['videos']) else 'partial' if any(item['status'] in {'completed','partial'} for item in data['videos']) else 'failed'}
