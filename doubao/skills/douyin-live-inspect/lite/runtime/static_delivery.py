"""Task-local static artifacts. No listeners, credentials, or host publishing APIs."""
import base64
import copy
import datetime
import json
import hashlib
import mimetypes
import os
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
import time
import zipfile

from runtime.platform_support import file_lock, private_directory
from runtime.report_data import public_text
from runtime.store import Store
from runtime.ui import ASSETS, build_report, build_snapshot, _evidence
from runtime.recap import recap_report


CLOUD_SNAPSHOT_INTERVAL_SECONDS = 120


def atomic(path, content):
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content.encode('utf-8') if isinstance(content, str) else content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


class FrozenStore:
    """One SQLite read transaction supplies every projection of this export."""
    def __init__(self, store, *, snapshot=None):
        self.root = store.root
        if snapshot is not None:
            # Transaction callers already hold a consistent, possibly uncommitted view.
            self.data, self.rows, self.state = copy.deepcopy(snapshot)
        elif hasattr(store, 'read_snapshot'):
            self.data, self.rows, self.state = copy.deepcopy(store.read_snapshot())
        else:
            self.data, self.rows, self.state = copy.deepcopy((store.task(), store.segments(), store.status()))
    def task(self): return copy.deepcopy(self.data)
    def segments(self): return copy.deepcopy(self.rows)
    def finish_tick(self): return self.data.get('finishing', {})
    def status(self): return copy.deepcopy(self.state)


def media_file(store, raw):
    if not isinstance(raw, str) or not raw: return None
    root = store.root.resolve()
    path = (root / raw).resolve()
    if not path.is_relative_to(root) or not path.is_file(): return None
    return path


def image_data(store, raw):
    path = media_file(store, raw)
    if not path: return ''
    mime = mimetypes.guess_type(path.name)[0]
    if mime not in {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}: return ''
    return 'data:' + mime + ';base64,' + base64.b64encode(path.read_bytes()).decode('ascii')


def sanitize(value):
    if isinstance(value, dict): return {k: sanitize(v) for k, v in value.items()}
    if isinstance(value, list): return [sanitize(v) for v in value]
    if isinstance(value, str):
        if value.startswith('data:image/'): return value
        return public_text(value)
    return value


def script_json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


def render_html(group, payload, *, live=False):
    html = (ASSETS/group/'index.html').read_text(encoding='utf-8')
    if group == 'quality' and payload.get('recap_failed'):
        from runtime.report_delivery import RECAP_REMINDER
        html = html.replace('</main>', '<aside class="edition-guide" aria-label="内容复盘提示">' + RECAP_REMINDER + ' 本页为静态快照，后续结果请查看原对话。</aside></main>')
    def asset(raw):
        path = ASSETS/raw.lstrip('/') if raw.startswith('/shared/') else ASSETS/group/Path(raw).name
        return path.read_text(encoding='utf-8')
    html = re.sub(r'<link\b[^>]*href="([^"]+\.css)"[^>]*>', lambda m: '<style>' + asset(m[1]) + '</style>', html)
    variable = {'monitor':'__monitorPayload', 'quality':'__reportPayload', 'review':'__reviewPayload'}[group]
    bootstrap = '<script>window.' + variable + '=' + script_json(payload) + ';window.__liveMonitor=' + ('true' if live else 'false') + ';</script>'
    html = re.sub(r'<script\b[^>]*src="([^"]+)"[^>]*>\s*</script>', lambda m: '<script>' + asset(m[1]) + '</script>', html)
    # Bootstrap before all rendering scripts, after the DOM has been constructed.
    position = html.find('<script>')
    html = html[:position] + bootstrap + html[position:]
    if group == 'monitor' and not live:
        html = html.replace('实时识别直播内容风险，最新审核结果将在此持续更新', '此页面为生成时的工作台快照，后续结果请查看对话中新交付的版本')
    return html


def artifact(path, kind, version):
    return {'type':kind, 'path':str(path.resolve()), 'version':version, 'status':'ready'}


def attach_snapshot_delivery(data):
    monitor = next((item for item in data.get('artifacts', []) if item['type']=='monitor'), None)
    if data.get('artifact_status') != 'ready' or monitor is None:
        return
    data['delivery_required'] = True
    data['snapshot_delivery'] = {'type':'html_snapshot', 'path':monitor['path'],
        'message':'请通过宿主附件能力交付此单文件 HTML，并在对话给出实际返回的预览或下载入口；不要发送云电脑绝对路径或 file URI。附件是生成时的快照，不会自动刷新。'}


def export(store, *, snapshot=None, bundle=False, single_file=False, refresh_monitor=True, allow_partial=False, frozen_store=None):
    root = private_directory(store.root/'html')
    with file_lock(store.root/'.html-export.lock',timeout=2):
        task = store.task()
        frozen = frozen_store or FrozenStore(store)
        task = frozen.task()
        if snapshot is None:
            from runtime.delivery_notice import effective_delivery_mode
            snapshot = effective_delivery_mode(task.get('delivery_mode', 'local_dashboard')) == 'html_snapshot'
        state_path = root/'manifest.json'
        previous = json.loads(state_path.read_text()) if state_path.exists() else {}
        counter = store.root/'.html-version'
        version = max(int(counter.read_text()) if counter.exists() else 0, previous.get('version', 0)) + 1
        atomic(counter, str(version))
        report = build_report(frozen)
        monitor = build_snapshot(frozen)
        review = recap_report(frozen)
        images = {key:image_data(frozen, raw) for key, raw in _evidence(frozen).items() if key != 'playback'}
        for item in report['evidence']:
            item['images'] = [images[key] for key in item['frame_ids'] if images.get(key)]
        for row in monitor['records']:
            for sample in row['samples']: sample['image_url'] = images.get(sample.get('evidence_id'), '')
        for row in review.get('document', {}).get('content', {}).get('segments', []):
            row['frame_images'] = [images[key] for ref in row['evidence_ids']
                if ':frame:' in ref for key in [ref.replace(':frame:', ':', 1)] if images.get(key)]
        playback = media_file(frozen, task.get('playback_file', ''))
        # Immutable media names keep older versioned HTML playable after refresh.
        media_url = ''
        if playback:
            stat = playback.stat()
            media_key = hashlib.sha256(repr((str(playback), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)).encode()).hexdigest()[:24]
            media_url = f'media/playback-{media_key}.mp4'
            target = root/media_url
            private_directory(target.parent)
            if not target.is_file():
                fd, temporary = tempfile.mkstemp(prefix='.playback-', dir=target.parent)
                try:
                    with os.fdopen(fd, 'wb') as output, playback.open('rb') as source:
                        shutil.copyfileobj(source, output)
                    os.replace(temporary, target)
                finally:
                    if os.path.exists(temporary): os.unlink(temporary)
        report['video']['url'] = media_url
        if 'video' in review: review['video']['url'] = media_url
        ready = frozen.status()['report_ready']
        blocked = frozen.status().get('report_blocked_reason')
        deliverable = ready or (allow_partial and task.get('kind') == 'video')
        artifacts = []
        report_pages = {}
        report_fingerprints = {}
        embedded_video = None
        for group, data in (('quality', report), ('review', review)):
            if not deliverable or (group == 'review' and (not ready or not (review['available'] or review['status'] == 'failed'))):
                continue
            # Keep the ZIP lightweight, with one shared relative video. Sanitize
            # report text before injecting trusted task-local media bytes.
            if group == 'quality' and task.get('kind') == 'video':
                data = {**data, 'report_version':version, 'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
            from runtime.report_delivery import public_live_report
            payload = {'ok': True, 'report': sanitize(public_live_report(data) if task.get('kind','live')=='live' else data)}
            if group == 'quality' and task.get('kind', 'live') == 'live':
                payload['recap_failed'] = not review['available'] and review['status'] == 'failed'
            report_pages[group] = render_html(group, payload)
            stat = playback.stat() if playback else None
            fingerprint = hashlib.sha256((report_pages[group] + repr(
                (str(playback), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns) if stat else None
            )).encode('utf-8')).hexdigest()
            if single_file and (previous.get('report_fingerprints', {}).get(group) != fingerprint or not (root/(group + '.html')).is_file()):
                atomic(root/(group + '.html'), report_pages[group])
                report_fingerprints[group] = fingerprint
            cache_key = group + ('-single' if single_file else '')
            report_fingerprints[cache_key] = fingerprint
            path = root/(cache_key + '.html')
            # Periodic workbench exports must not repeatedly encode an unchanged
            # full recording. Changed report data, media or templates invalidate it.
            if previous.get('report_fingerprints', {}).get(cache_key) != fingerprint or not path.is_file():
                if single_file and playback and 'video' in payload['report']:
                    if embedded_video is None:
                        embedded_video = 'data:video/mp4;base64,' + base64.b64encode(playback.read_bytes()).decode('ascii')
                    payload['report']['video']['url'] = embedded_video
                atomic(path, render_html(group, payload))
            if group == 'quality' and task.get('kind') == 'video':
                versioned = root/f'{cache_key}-{version}.html'
                atomic(versioned, path.read_bytes())
                path = versioned
            artifacts.append(artifact(path, group, version))
        monitor['quality_report_url'] = 'quality.html' if 'quality' in report_pages and not snapshot else ''
        monitor['review_report_url'] = 'review.html' if 'review' in report_pages and review['available'] and not snapshot else ''
        monitor.update(task_id=task['id'], version=version,
            generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            frozen=snapshot, standalone=snapshot, complete=bool(blocked and task.get('worker_status') in {'done','failed','stopped'}) or ready and (task.get('kind') == 'video' or review['status'] in ('ready','insufficient')))
        monitor = sanitize(monitor)
        if task.get('kind') != 'video':
            filename = f'monitor-{version}.html' if snapshot else 'monitor.html'
            # File-preview hosts may reload the document when its HTML changes.
            # Periodic ticks update data.js only; explicit exports can refresh the shell.
            if snapshot or refresh_monitor or not (root/filename).exists():
                atomic(root/filename, render_html('monitor', monitor, live=not snapshot))
            artifacts.insert(0, artifact(root/filename, 'monitor', version))
        if not snapshot: atomic(root/'data.js', 'window.__INSPECT_DATA__=' + script_json(monitor) + ';\n')
        if bundle and deliverable:
            fd, temporary = tempfile.mkstemp(dir=root, prefix='.bundle-')
            os.close(fd)
            try:
                with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
                    # Frozen workbench: exported packages never poll another task's files.
                    if task.get('kind') != 'video':
                        packed = {**monitor, 'frozen':True, 'standalone':False, 'quality_report_url':'quality.html',
                            'review_report_url':'review.html' if review['available'] else ''}
                        archive.writestr('monitor.html', render_html('monitor', packed))
                    for group, page in report_pages.items():
                        archive.writestr(group + '.html', page)
                    if playback: archive.write(root/media_url, media_url)
                os.replace(temporary, root/(f'reports-{version}.zip' if task.get('kind')=='video' else 'reports.zip'))
            finally:
                if os.path.exists(temporary): os.unlink(temporary)
            artifacts.append(artifact(root/(f'reports-{version}.zip' if task.get('kind')=='video' else 'reports.zip'), 'bundle', version))
        if deliverable and playback and not single_file:
            artifacts.append(artifact(root/media_url, 'media', version))
        manifest = {'evidence_version':review.get('evidence_version'), 'media_layout':'embedded' if single_file else 'separate','version':version, 'artifact_status':'ready', 'artifacts':artifacts, 'complete':monitor['complete']}
        atomic(state_path, script_json({**manifest, 'report_fingerprints': {**previous.get('report_fingerprints', {}), **report_fingerprints}}))
        return manifest


def safe_export(store, **options):
    try:
        task=store.task()
        deadline=task.get('finishing',{}).get('recap_deadline_at' if task.get('recap',{}).get('status') in {'ready','insufficient','failed'} else 'quality_deadline_at')
        draining_report = task.get('finishing',{}).get('mode') == 'drain' and task.get('finishing',{}).get('phase') == 'completed'
        if (deadline is not None or draining_report) and 'frozen_store' not in options:
            import subprocess, sys
            script='import json,sys; from runtime.store import Store; from runtime.static_delivery import export; print(json.dumps(export(Store(sys.argv[1]),**json.loads(sys.argv[2]))))'
            # HTML is optional: recover once, then deliver saved report content.
            for attempt in range(2):
                try:
                    child=subprocess.run([sys.executable,'-c',script,str(store.root),json.dumps(options)],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,timeout=30)
                    break
                except subprocess.TimeoutExpired:
                    if attempt == 1:
                        return {'artifact_status':'failed', 'artifacts':[],
                                'fallback_reason':'HTML_EXPORT_TIMEOUT', 'fallback_action':'deliver-chat-report',
                                'message':'HTML 导出限时恢复后仍未完成；跳过 HTML，直接交付已保存的完整 Chat 报告并继续另一份报告。'}
            if child.returncode:raise ValueError('report export failed')
            return json.loads(child.stdout)
        return export(store, **options)
    except (OSError, ValueError, TypeError, KeyError, TimeoutError, sqlite3.OperationalError):
        return {'artifact_status':'failed', 'artifacts':[], 'message':'HTML 未能生成，请直接交付已保存的 Chat 结果。'}


def tick(store):
    """Finishing continues even without a browser or active Agent."""
    try:
        store.finish_tick()
        from runtime.review_dispatch import observe_backlog
        observe_backlog(store)
        recover_stalled_worker(store)
        task=store.task()
        if task.get('kind')=='video':
            return {'complete':task.get('capture_status') in {'ended','stopped','failed'} and task.get('worker_status') in {'done','failed','stopped'}}
        if task.get('delivery_mode', 'local_dashboard') == 'local_dashboard':
            return safe_export(store, refresh_monitor=False)
        if store.status().get('report_blocked_reason'):return safe_export(store)
        return {'complete': False}
    except (OSError, sqlite3.OperationalError):
        return {'artifact_status':'failed', 'complete':False}


def recover_stalled_worker(store, now=None, launch_worker=None):
    """Recover a stopped inspection's media worker without reopening capture."""
    now = time.time() if now is None else now
    task = store.task()
    if (task.get('media_frozen') or task.get('kind') != 'live' or not task.get('stop_requested')
            or task.get('finishing', {}).get('phase') == 'completed'
            or task.get('worker_status') == 'setup_pending'):
        return False
    status = store.status()
    if task.get('capture_status') in {'ended', 'stopped', 'failed'} and not status['media_pending']:
        return False
    stopped_at = task.get('stop_requested_at')
    try:
        stopped_at = datetime.datetime.fromisoformat(stopped_at.replace('Z', '+00:00')).timestamp() if isinstance(stopped_at, str) else float(stopped_at or 0)
    except (ValueError, TypeError):
        stopped_at = 0
    if now - max(task.get('worker_heartbeat') or 0, stopped_at) < 30:
        if task.get('recovery_state') == 'worker_unresponsive':
            store.update_task(recovery_state=None)
        return False
    if now - (task.get('recovery_last_attempt_at') or 0) < 60:
        return False
    if (task.get('recovery_attempts') or 0) >= 2:
        if task.get('recovery_state') != 'blocked': store.update_task(recovery_state='blocked')
        return False
    from runtime.platform_support import file_lock
    try:
        with file_lock(store.root/'.worker.lock', timeout=0):
            # Recheck after acquiring the worker lock; another process may have
            # finished the task while this watcher waited for the filesystem.
            task = store.task()
            if not task.get('stop_requested') or task.get('finishing', {}).get('phase') == 'completed':
                return False
            store.update_task(worker_mode='processing_only', recovery_state='restarting',
                              recovery_last_attempt_at=now,
                              recovery_attempts=(task.get('recovery_attempts') or 0) + 1)
            if launch_worker is None:
                from runtime.cli import launch
                launch_worker = lambda: launch('worker', store)
        # Do not hold the lock while spawning: the child must acquire it first.
        launch_worker()
        return True
    except TimeoutError:
        if task.get('recovery_state') != 'worker_unresponsive':
            store.update_task(recovery_state='worker_unresponsive')
        return False
    except OSError:
        store.update_task(recovery_state='blocked')
        return False


def watch(store):
    try:
        with file_lock(store.root/'.html-watch.lock', timeout=1):
            while True:
                try:
                    result = tick(store)
                    task = store.task()
                    terminal = task.get('capture_status') in ('ended','stopped','failed') and task.get('worker_status') in ('done','failed','stopped')
                    deadline = None if task.get('finishing',{}).get('mode')=='drain' else task.get('finishing',{}).get('recap_deadline_at')
                    if deadline is not None and time.time() >= deadline: return
                    if deadline is None and (result.get('complete') or (terminal and (not store.segments() or (task.get('delivery_mode', 'local_dashboard') != 'local_dashboard' and store.status()['report_ready'])))): return
                except (OSError, sqlite3.OperationalError):
                    pass  # A transient read failure must not stop deadline advancement.
                time.sleep(2)
    except TimeoutError: return


def attach_artifacts(store, data, command):
    try:
        _attach_artifacts(store, data, command)
    except (OSError, ValueError, TypeError, KeyError, TimeoutError, sqlite3.OperationalError):
        data.update(artifact_status='failed', artifacts=[])


def _attach_artifacts(store, data, command):
    from runtime.delivery_notice import effective_delivery_mode
    mode = effective_delivery_mode(store.task().get('delivery_mode', 'local_dashboard'))
    data['delivery_mode'] = mode
    if mode == 'chat' or command in ('serve','snapshot'): return
    if 'artifacts' in data: return
    if mode == 'local_dashboard':
        if command in ('start','start-video','resume','report','recap-report','recap-submit'):
            data.update(safe_export(store, single_file=command in ('report','recap-report')))
        return
    if store.task().get('kind') == 'video': return
    # Event state is private bookkeeping, never included in an attachment.
    try:
        with file_lock(store.root/'.html-events.lock'):
            state_file = store.root/'.html-events.json'
            saved = json.loads(state_file.read_text()) if state_file.exists() else {}
            # Older tasks stored only phase names. Export their current risks once.
            seen = saved if isinstance(saved,list) else saved.get('events',[])
            seen_risks = set(saved.get('risk_ids',[])) if isinstance(saved,dict) else set()
            last_snapshot_at = float(saved.get('last_snapshot_at', 0)) if isinstance(saved,dict) else 0
            frozen = FrozenStore(store)
            report = build_report(frozen)
            task = frozen.task()
            now = time.time()
            events = ['started']
            risk_ids = {row['id'] for row in report['evidence']}
            risk_ids.update('conclusion:' + str(key) for key in report.get('rule_conclusions',{}))
            new_risks = risk_ids - seen_risks
            if report['hit_rule_count']: events.append('first_risk')
            if task.get('capture_status') in ('ended','stopped','failed'): events.append('capture_ended')
            new = [event for event in events if event not in seen]
            if command == 'resume': new.append('resumed')
            if new_risks and 'first_risk' not in new: new.append('risk_detected')
            if (not new and task.get('capture_status') not in ('ended','stopped','failed')
                    and now - last_snapshot_at >= CLOUD_SNAPSHOT_INTERVAL_SECONDS):
                new.append('periodic_snapshot')
            if not new: return
            result = safe_export(store, snapshot=True)
            data.update(result)
            if result['artifact_status'] == 'ready':
                data['snapshot_events'] = new
                data['delivery_required'] = True
                data['new_risk_count'] = len(new_risks)
                monitor = next(item for item in result['artifacts'] if item['type']=='monitor')
                periodic = new == ['periodic_snapshot']
                data['snapshot_delivery'] = {'type':'html_snapshot', 'path':monitor['path'],
                    'message':('请通过宿主附件能力交付此 HTML 最新工作台快照，并在对话给出用户可点击的预览或下载入口；云电脑每2分钟交付一次新快照，旧附件保留历史状态。'
                               if periodic else
                               '请立即通过宿主附件能力交付此 HTML 工作台，并在对话给出用户可点击的预览或下载入口；不能只发送云电脑文件路径。旧附件保留原快照。')}
                atomic(state_file, script_json({'events':list(dict.fromkeys(seen + [event for event in new if event not in {'risk_detected','periodic_snapshot','resumed'}])),
                                               'risk_ids':sorted(seen_risks | risk_ids),
                                               'last_snapshot_at':now}))
    except (OSError, ValueError, TimeoutError):
        data.update(artifact_status='failed', artifacts=[])
