"""Finite local files: media PTS, atomic chunks and immutable source identity."""
import hashlib
import math
import os
from pathlib import Path
import signal
import subprocess
import time

from runtime.store import Store
from runtime.platform_support import kill_tree, stop_capture
from runtime.mediakit import config


class VideoError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def signature(path):
    st = path.stat()
    return {'bytes': st.st_size, 'mtime_ns': st.st_mtime_ns, 'device': st.st_dev, 'inode': st.st_ino}


def fingerprint(path):
    before = signature(path)
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''): digest.update(chunk)
    if signature(path) != before: raise VideoError('VIDEO_SOURCE_CHANGED')
    return {**before, 'sha256': digest.hexdigest()}


def inspect_video(source, ffprobe_bin='ffprobe'):
    import json
    if not isinstance(source, str) or not Path(source).is_absolute() or any(ord(c) < 32 for c in source):
        raise VideoError('LOCAL_VIDEO_PATH_REQUIRED')
    path = Path(source).resolve()
    if not path.is_file() or not os.access(path, os.R_OK): raise VideoError('VIDEO_SOURCE_UNAVAILABLE')
    identity = fingerprint(path)
    try:
        result = subprocess.run([ffprobe_bin, '-v', 'error', '-protocol_whitelist', 'file,pipe',
            '-show_format', '-show_streams', '-of', 'json', str(path)], capture_output=True, timeout=30)
        data = json.loads(result.stdout) if result.returncode == 0 else {}
        duration = float(data.get('format', {}).get('duration', 0))
    except (ValueError, OSError, subprocess.SubprocessError): raise VideoError('VIDEO_INVALID') from None
    if not math.isfinite(duration) or duration <= 0 or not any(s.get('codec_type') == 'video' for s in data.get('streams', [])):
        raise VideoError('VIDEO_INVALID')
    if signature(path) != {k: identity[k] for k in signature(path)}: raise VideoError('VIDEO_SOURCE_CHANGED')
    return str(path), {'source_duration_ms': round(duration * 1000), 'source_fingerprint': identity,'source_has_audio':any(s.get('codec_type')=='audio' for s in data.get('streams',[]))}


def capture_video(task_dir, cancel=None, bridge=None):
    from runtime.media import guarded_capture, stop_requested, probe
    store = Store(task_dir)
    task = store.task()
    if task['capture_status'] in {'ended', 'stopped'}: return
    from runtime.sampling import enabled
    if enabled(task):return capture_sample_video(store,cancel,bridge)
    if task.get('pipeline_version')==2:
        return capture_stream_video(store,cancel,bridge)
    duration = task['source_duration_ms']
    store.update_task(capture_start_ms=0, capture_end_ms=duration, capture_status='running')
    try:
        source = Path(task['source'])
        if not source.is_file() or fingerprint(source) != task['source_fingerprint']:
            raise VideoError('VIDEO_SOURCE_CHANGED')
        identity = signature(source)
        step = task.get('segment_seconds', 30) * 1000
        existing = {s['index']: s for s in store.segments()}
        for index, start in enumerate(range(0, duration, step)):
            if stop_requested(store, cancel):
                store.update_task(capture_status='stopped' if store.should_stop() else 'pending')
                return
            if index in existing: continue
            if signature(source) != identity: raise VideoError('VIDEO_SOURCE_CHANGED')
            end = min(duration, start + step)
            target = store.root / 'media' / f'video-{index:06d}.mp4'
            temporary = target.with_suffix('.part.mp4')
            args = [config(task,'ffmpeg_bin','ffmpeg'), '-nostdin', '-v', 'error', '-y', '-protocol_whitelist', 'file,pipe',
                    '-ss', str(start/1000), '-i', str(source), '-t', str((end-start)/1000),
                    '-map', '0:v:0', '-map', '0:a:0?', '-c:v', 'libx264', '-preset', 'veryfast',
                    '-pix_fmt', 'yuv420p', '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
                    '-c:a', 'aac', '-movflags', '+faststart', str(temporary)]
            process = guarded_capture(args, subprocess.DEVNULL)
            deadline = time.monotonic() + max(120, (end-start)/1000*4)
            try:
                while process.poll() is None:
                    if stop_requested(store, cancel) or time.monotonic() > deadline:
                        stop_capture(process)
                        try: process.wait(timeout=23)
                        except subprocess.TimeoutExpired: kill_tree(process); process.wait()
                        if stop_requested(store, cancel):
                            store.update_task(capture_status='stopped' if store.should_stop() else 'pending')
                            return
                        raise VideoError('VIDEO_DECODE_TIMEOUT')
                    time.sleep(.1)
                if process.returncode: raise VideoError('VIDEO_DECODE_FAILED')
                if signature(source) != identity: raise VideoError('VIDEO_SOURCE_CHANGED')
                measured = float(probe(temporary, task)['format']['duration']) * 1000
                if measured < end-start-1000: raise VideoError('VIDEO_INCOMPLETE_CHUNK')
                temporary.replace(target)
                store.add_segment(index, start, end, str(target.relative_to(store.root)))
                store.update_task(capture_observed_ms=end)
            finally:
                if process.poll() is None:
                    kill_tree(process); process.wait()
                process.stdin.close()
                temporary.unlink(missing_ok=True)
        store.update_task(capture_status='ended', capture_observed_ms=duration)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as error:
        store.update_task(capture_status='failed', capture_error=getattr(error, 'code', 'VIDEO_DECODE_FAILED'))
        store.log('video_capture_failed', getattr(error, 'code', 'VIDEO_DECODE_FAILED'))


def capture_stream_video(store,cancel,bridge):
    from runtime.media import capture_session
    from runtime.realtime import recording_segments
    task=store.task()
    try:
        source=Path(task['source'])
        if not source.is_file() or fingerprint(source)!=task['source_fingerprint']:
            raise VideoError('VIDEO_SOURCE_CHANGED')
        recordings=recording_segments(store)
        start=max((s['end_ms'] for s in recordings),default=0)
        disk=[int(p.stem.split('-')[-1]) for p in (store.root/'media').glob('segment-*.mp4')]
        index=max(disk,default=-1)+1
        store.update_task(capture_start_ms=0,capture_end_ms=task['source_duration_ms'],capture_status='running')
        code,_=capture_session(store,str(source),start,index,seek=start/1000,cancel=cancel,bridge=bridge)
        if fingerprint(source)!=task['source_fingerprint']:raise VideoError('VIDEO_SOURCE_CHANGED')
        status='stopped' if store.should_stop() else 'failed' if code or store.task().get('stream_error') else 'ended'
        store.update_task(capture_status=status,capture_observed_ms=max((s['end_ms'] for s in recording_segments(store)),default=start))
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
        store.update_task(capture_status='failed',capture_error=getattr(error,'code','VIDEO_DECODE_FAILED'))


def capture_sample_video(store, cancel, bridge):
    """Seek only selected windows; one pending/preparing candidate is the prefetch budget."""
    from runtime.media import capture_session, stop_requested
    from runtime.sampling import video_windows, windows
    task=store.task()
    try:
        source=Path(task['source'])
        if not source.is_file() or fingerprint(source)!=task['source_fingerprint']:
            raise VideoError('VIDEO_SOURCE_CHANGED')
        identity=signature(source)
        store.update_task(capture_start_ms=0,capture_end_ms=task['source_duration_ms'],capture_status='running')
        for index,(start,end) in enumerate(video_windows(task['source_duration_ms'])):
            while True:
                store.finish_tick()
                if stop_requested(store,cancel):
                    store.update_task(capture_status='stopped')
                    return
                rows=store._read_with_retry(lambda conn:windows(conn,store.session_id))
                current=next((r for r in rows if r['index']==index),None)
                if index in store.task().get('sampling_prepared_indices',[]) or (current and current['review_status'] in {'done','skipped'}):break
                if not any(r['index']!=index and r['review_status']=='pending' and r.get('review_started_at') is None for r in rows):
                    store.update_task(sampling_preparing_index=index)
                    store.finish_tick()
                    if signature(source)!=identity:raise VideoError('VIDEO_SOURCE_CHANGED')
                    disk=[int(p.stem.split('-')[-1]) for p in (store.root/'media').glob('segment-*.mp4')]
                    serial=max(disk,default=-1)+1
                    code,_=capture_session(store,str(source),start,serial,seek=start/1000,
                        cancel=cancel,bridge=bridge if index==0 else None,duration_ms=end-start)
                    if code or store.task().get('stream_error'):raise VideoError('VIDEO_DECODE_FAILED')
                    store.update_task(capture_observed_ms=end,sampling_prepared_indices=sorted(set(store.task().get('sampling_prepared_indices',[])+[index])))
                    break
                time.sleep(.1)
        if signature(source)!=identity:raise VideoError('VIDEO_SOURCE_CHANGED')
        store.update_task(capture_status='ended')
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
        store.update_task(capture_status='failed',capture_error=getattr(error,'code','VIDEO_DECODE_FAILED'))
