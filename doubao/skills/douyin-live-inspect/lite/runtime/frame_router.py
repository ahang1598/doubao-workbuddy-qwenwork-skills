"""Leased frame extraction with sticky local/cloud failover and no upload replay."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urljoin

from runtime import backend_routing, mediakit
from runtime.media_jobs import MediaJobs

CLOUD_SECONDS = 600


class FrameJobCancelled(RuntimeError):
    pass


def download_image(url, target, store):
    """Bound network/DNS/body time in a credential-free child; never persist URLs."""
    from runtime.media import media_command
    env = {k: v for k, v in os.environ.items() if k in
           {'PATH','SYSTEMROOT','SystemRoot','WINDIR','TEMP','TMP','TMPDIR','LANG','LC_ALL','SSL_CERT_FILE','SSL_CERT_DIR'}}
    deadline = time.monotonic() + 30
    for _ in range(4):
        remaining = deadline - time.monotonic()
        if remaining <= 0: raise RuntimeError('frame_download_timeout')
        result = media_command([sys.executable, '-I', str(Path(__file__).with_name('http_fetch.py'))],
            input=json.dumps({'url': url, 'headers': {}, 'timeout': remaining, 'maximum_bytes': 8*1024*1024,
                              'content_kind': 'image'}), capture_output=True, text=True, timeout=remaining, env=env, store=store)
        if result.returncode: raise RuntimeError('frame_download_failed')
        value = json.loads(result.stdout)
        if 300 <= value.get('status', 0) < 400:
            location = value.get('headers', {}).get('location')
            if not isinstance(location, str) or not location: break
            url = urljoin(url, location)
            continue
        if value.get('status') != 200 or not value.get('body'): break
        target.write_bytes(base64.b64decode(value['body'], validate=True))
        return
    raise RuntimeError('frame_download_failed')


def extract(store, segment, folder, job, *, cancelled=lambda: False):
    from runtime.media import extract_frames, frame_schedule, valid_frame, media_command
    from runtime.asr_router import cloud_available

    queue = MediaJobs(store)
    task = store.task()
    if task.get('image_inspection') is False:return ({'frames':[], 'frame_status':'disabled'},None,[])
    remote_first = task.get('frames_policy') == 'remote_first' and task.get('asr_policy') == 'remote_first'
    allowed = remote_first or (task.get('frames_policy') == 'local_first' and task.get('asr_policy') == 'local_first')
    route = backend_routing.choice(task, 'frames', 'ffmpeg')
    backend = segment.get('frame_backend') or (route['backend'] if allowed else 'ffmpeg')
    generation = segment.get('frame_route_generation', route['generation'])
    switched = segment.get('frame_switched', False)
    # local_only never uploads, including when opening historical task state.
    if not allowed: backend = 'ffmpeg'

    def checkpoint(**fields):
        if cancelled() or not queue.checkpoint(job, **fields): raise FrameJobCancelled()
        segment.update(fields)

    selection = segment.get('remote_frames_selection')
    if remote_first:
        if selection is None:
            selection = backend_routing.remote_choice(store,'frames',f"segment-{segment['id']}",budget=CLOUD_SECONDS+90)
            checkpoint(remote_frames_selection=selection)
        backend = segment.get('frame_backend') or selection['backend']
    checkpoint(frame_backend=backend, frame_route_generation=generation)
    fields, error, files = {'frame_status': 'failed'}, 'frames_incomplete', []
    local_folder, cloud_folder = folder/'ffmpeg', folder/'mediakit'
    local_folder.mkdir(exist_ok=True)
    cloud_folder.mkdir(exist_ok=True)

    def cloud():
        nonlocal fields, files
        if not allowed: raise RuntimeError('cloud_frames_unavailable')
        if remote_first and not segment.get('frame_remote'):
            capability=cloud_available(store,capability='frames')
            if not capability['ready']:
                raise mediakit.CommandFailure(None,category=capability.get('code','cloud_frames_unavailable'))
        env = mediakit.credentials_env(store)
        env = {**env, 'MEDIAKIT_SURFACE': 'skill', 'MEDIAKIT_RUNTIME': env.get('MEDIAKIT_RUNTIME') or 'unknown'}
        binary = mediakit.config(task, 'mediakit_bin', 'mediakit-cli')
        records = dict(segment.get('frame_remote') or {})
        deadline = segment.get('frame_cloud_deadline_at')
        if deadline is None:
            deadline = time.time() + CLOUD_SECONDS
            checkpoint(frame_cloud_deadline_at=deadline)
        schedule = frame_schedule(task, segment)
        # Retain verified local partial evidence; remote fills only its gaps.
        frames = list(fields.get('frames', []))
        expected = [at for _, at in schedule]
        fields = {'frames': frames, 'frame_expected_count': len(expected),
                  'frame_missing_times_ms': expected, 'frame_status': 'failed'}
        for n, (offset, at) in enumerate(schedule):
            if any(f['time_ms'] == at for f in frames): continue
            if cancelled(): raise FrameJobCancelled()
            target = store.root / 'frames' / str(segment['id']) / f'{n:03d}.jpg'
            image = cloud_folder / f'{n:03d}.jpg'
            if valid_frame(target, task, store):
                frames.append({'id': f"frame-{segment['id']}-{n}", 'path': str(target.relative_to(store.root)), 'time_ms': at})
                continue
            record = records.get(str(n)) or {}
            if record.get('status') == 'unknown': raise RuntimeError('frame_submission_unknown')
            if not record.get('task_id'):
                if time.time() >= deadline: raise RuntimeError('cloud_frames_timeout')
                # Contract exposes image_url only, not timestamps or an ordering
                # guarantee. A single requested instant makes attribution exact.
                records[str(n)] = {'status': 'unknown'}
                checkpoint(frame_remote=records)
                result = mediakit.invoke(binary, ['video', 'extract-frames', '--video-url',
                    str(store.root / segment['media_file']), '--snapshot-type', 'SpecifiedTime',
                    '--specified-time', json.dumps([offset])],
                    env=env, timeout=min(60, deadline-time.time()), store=store)
                remote_id = result.get('task_id')
                if not isinstance(remote_id, str) or not remote_id.strip(): raise RuntimeError('invalid_frame_task')
                record = records[str(n)] = {'status': 'submitted', 'task_id': remote_id}
                checkpoint(frame_remote=records)
            while True:
                if cancelled(): raise FrameJobCancelled()
                if time.time() >= deadline: raise RuntimeError('cloud_frames_timeout')
                # Reading a saved task is retryable; submitting its audio/video is not.
                try:
                    result = mediakit.invoke(binary, ['shared','query-task','--task-id',record['task_id']],
                        env=env, timeout=min(60, deadline-time.time()), store=store)
                except mediakit.CommandFailure as failure:
                    if failure.diagnostic.get('category') not in {'request_timeout','network_error','rate_limited','service_unavailable'}:
                        raise
                    result = {'status': 'running'}
                state = str(result.get('status', '')).lower()
                if state == 'completed': break
                if state not in {'running','queued','pending','submitted','processing'}: raise RuntimeError('cloud_frames_failed')
                until = min(time.monotonic()+3, time.monotonic()+max(0,deadline-time.time()))
                while time.monotonic() < until:
                    if cancelled(): raise FrameJobCancelled()
                    time.sleep(min(.2, until-time.monotonic()))
            snapshots = result.get('snapshots')
            if not isinstance(snapshots, list) or len(snapshots) != 1 or not isinstance(snapshots[0],dict):
                raise RuntimeError('invalid_frame_result')
            url = snapshots[0].get('image_url')
            if not isinstance(url,str): raise RuntimeError('invalid_frame_result')
            raw = cloud_folder / f'{n:03d}.download'
            download_image(url, raw, store)
            # The remote image may be PNG. Decode and normalize to the existing
            # JPEG evidence format; source-video decoding is not needed here.
            result = media_command([mediakit.config(task,'ffmpeg_bin','ffmpeg'),'-nostdin','-v','error','-y',
                '-i',str(raw),'-frames:v','1','-vf','scale=min(1280\\,iw):-2',str(image)],
                capture_output=True,timeout=30,store=store)
            if result.returncode or not valid_frame(image,task,store): raise RuntimeError('invalid_frame_image')
            files.append((image,target))
            frames.append({'id': f"frame-{segment['id']}-{n}", 'path': str(target.relative_to(store.root)), 'time_ms': at})
        frames.sort(key=lambda frame: frame['time_ms'])
        fields.update(frame_status='success',frame_missing_times_ms=[])
        return fields, None, files

    while True:
        category = None
        try:
            if backend == 'ffmpeg':
                previous, previous_files = fields, files
                fields, error, files = extract_frames(store, {**segment,'retained_frames':previous.get('frames',[])} if remote_first else segment, local_folder)
                if (remote_first or error) and previous.get('frames'):
                    combined = {f['time_ms']: f for f in previous['frames']}
                    combined.update({f['time_ms']: f for f in fields.get('frames',[]) if not remote_first or f['time_ms'] not in combined})
                    fields['frames'] = sorted(combined.values(),key=lambda f:f['time_ms'])
                    missing = sorted(set(at for _,at in frame_schedule(task,segment)) - set(combined))
                    fields.update(frame_missing_times_ms=missing,frame_expected_count=len(frame_schedule(task,segment)))
                    files = list({target: source for source,target in previous_files+files}.items())
                    files = [(source,target) for target,source in files]
                    if not missing:
                        fields['frame_status']='success'
                        error=None
            else:
                fields, error, files = cloud()
        except FrameJobCancelled:
            raise
        except (OSError, ValueError, RuntimeError, EOFError, subprocess.SubprocessError) as failure:
            category = getattr(failure,'diagnostic',{}).get('category')
            error = 'frames_extraction_failed'
        if remote_first and backend=='mediakit':
            backend_routing.remote_result(store,'frames',selection,not error,category=category,job=job)
        if not error:
            if switched and not remote_first:
                backend_routing.promote(store,'frames',backend,generation,'ffmpeg',job=job)
            fields['frame_backend'] = backend
            return fields, None, files
        if not allowed or switched or (remote_first and backend=='ffmpeg'):
            # Preserve any valid partial frames; never call them full coverage.
            if fields.get('frames') is not None:
                fields['frame_missing_times_ms'] = sorted(set(at for _,at in frame_schedule(task,segment)) -
                                                         {f['time_ms'] for f in fields['frames']})
            fields['frame_status'] = 'failed'
            return fields, error, files
        if backend == 'ffmpeg' and not cloud_available(store, capability='frames')['ready']:
            return fields, error, files
        backend = 'mediakit' if backend == 'ffmpeg' else 'ffmpeg'
        switched = True
        checkpoint(frame_backend=backend,frame_switched=True)
