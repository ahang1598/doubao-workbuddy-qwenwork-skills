# Adapted from skills_live_inspect_lite/runtime/media.py; content-only migration.
"""Local media sidecar. Only closed CSV-listed ffmpeg segments enter the Store.

Run with ``python -m runtime.media TASK_DIR``. Store remains the owning runtime's
contract; capture and preparation use separate Store instances per thread.
"""
import concurrent.futures
from runtime.platform_support import fcntl, nofollow_open, private_directory, private_file
from urllib.parse import urlsplit
import csv
import json
import os
import re
from pathlib import Path
import signal
import sys
import subprocess
import tempfile
import threading
import time

from runtime.store import Store, now_iso
from runtime import live_backlog
from runtime.platform_support import process_options, kill_tree, stop_capture
from runtime.mediakit import config, process_asr
from runtime.douyin_live import resolve_douyin_live, DouyinLiveError



# A small child supervisor observes stdin EOF if the worker crashes. This avoids
# leaving ffmpeg recording indefinitely and colliding with a resumed worker.
CAPTURE_GUARD = r"""
import os, signal, subprocess, sys, threading, time
child = subprocess.Popen(sys.argv[1:], stdin=subprocess.PIPE)
stopping = threading.Event()
def stop(*_): stopping.set()
def watch():
    try:
        while os.read(sys.stdin.fileno(), 1): pass
    finally: stopping.set()
threading.Thread(target=watch, daemon=True).start()
signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)
started = None
try:
    while child.poll() is None:
        if stopping.is_set() and started is None:
            started = time.monotonic()
            try: child.stdin.write(b'q\n'); child.stdin.flush(); child.stdin.close()
            except (OSError, ValueError): pass
        if started is not None and time.monotonic() - started > 20: child.kill()
        time.sleep(.1)
    sys.exit(child.returncode if child.returncode >= 0 else 128 - child.returncode)
finally:
    if child.poll() is None: child.kill()
    child.wait()
"""


def guarded_capture(args, errors, *, pcm=False):
    from runtime.platform_support import media_popen
    return media_popen([sys.executable, '-I', '-c', CAPTURE_GUARD, *[x for x in args if x!='-nostdin']], capture_child=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE if pcm else subprocess.DEVNULL,
                            stderr=errors, **process_options())


def stop_requested(store, cancel=None):
    return store.should_stop() or (cancel is not None and cancel.is_set())


def media_command(args, *, store=None, **kwargs):
    from runtime.finishing import enabled, closed
    if store is None or not enabled(store.task()):
        return subprocess.run(args, **kwargs)
    timeout = kwargs.pop('timeout', 30)
    from runtime.full_live import enabled as full
    if full(store.task()):
        timeout=min(timeout,max(0,store.finish_tick().get('media_deadline_at',float('inf'))-time.time()))
        if timeout<=0:raise subprocess.TimeoutExpired(args,timeout)
    kwargs.pop('capture_output', None)
    if store.task().get('media_frozen') or closed(store.finish_tick()) or live_backlog.remaining(store.task(),timeout)<=0:raise subprocess.TimeoutExpired(args, timeout)
    from runtime.platform_support import media_popen
    with media_popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **process_options(), **kwargs) as process:
        started = time.monotonic()
        while True:
            if store.task().get('media_frozen') or closed(store.finish_tick()) or live_backlog.remaining(store.task(),timeout)<=0 or time.monotonic() - started >= timeout:
                kill_tree(process)
                process.communicate()
                raise subprocess.TimeoutExpired(args, timeout)
            try:
                stdout, stderr = process.communicate(timeout=.2)
                return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
            except subprocess.TimeoutExpired:
                pass


def probe(path, task, store=None, *, timeout=30):
    p = media_command([config(task, 'ffprobe_bin', 'ffprobe'), '-v', 'error',
                        '-show_format', '-show_streams', '-of', 'json', str(path)],
                       capture_output=True, text=True, timeout=timeout, store=store)
    if p.returncode:
        raise RuntimeError('Media probe failed')
    return json.loads(p.stdout)


def atomic_json(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
    temp.replace(path)


class SourceError(RuntimeError):
    def __init__(self, code, retryable=False):
        super().__init__(code)
        self.code, self.retryable = code, retryable


class DouyinResolveError(SourceError):
    def __init__(self, code, retryable=False):
        # Only fixed codes cross into persistent logs; never CLI output or URLs.
        self.code = code if isinstance(code, str) and code in {
            'INVALID_INPUT', 'DOUYIN_FETCH_FAILED', 'DOUYIN_PAGE_UNAVAILABLE',
            'DOUYIN_FLV_UNAVAILABLE', 'DOUYIN_RESOLVER_UNAVAILABLE',
        } else 'DOUYIN_RESOLVER_UNAVAILABLE'
        super().__init__(self.code, retryable)


def resolve_douyin(source):
    match = re.search(r'https://(?:live|www|v)\.douyin\.com/[^\s<>"，。]+', str(source))
    try:
        result = resolve_douyin_live(match[0] if match else source)
    except DouyinLiveError as error:
        raise DouyinResolveError(error.code, error.retryable) from None
    except (OSError, ValueError, TypeError):
        raise DouyinResolveError('DOUYIN_RESOLVER_UNAVAILABLE', True) from None
    if not isinstance(result, dict):
        raise DouyinResolveError('DOUYIN_RESOLVER_UNAVAILABLE', True)
    if result.get('status') not in ('ready', 'not_live'):
        raise DouyinResolveError(result.get('code'), bool(result.get('retryable')))
    return result


def resolve_with_retry(store, cancel=None):
    for attempt in range(3):
        if stop_requested(store, cancel):
            raise SourceError('SOURCE_CANCELLED')
        if store.task().get('live_ended_at'):
            return {'status': 'not_live'}
        try:
            source = store.task()['source']
            if urlsplit(source).hostname not in {'live.douyin.com', 'www.douyin.com', 'v.douyin.com'}:
                return {'status': 'ready', 'streamUrl': source}
            resolved = resolve_douyin(source)
            store.update_task(live_source_status='not_live' if resolved['status']=='not_live' else 'live',
                              source_error_code='none', source_end_reason='offline' if resolved['status']=='not_live' else 'unknown')
            return resolved
        except (SourceError, OSError, subprocess.SubprocessError) as error:
            if isinstance(error, SourceError) and not error.retryable:
                raise
            store.log('source_retry', getattr(error, 'code', type(error).__name__))
            if attempt == 2:
                raise
            for _ in range(4 * (attempt + 1)):
                if stop_requested(store, cancel):
                    raise SourceError('SOURCE_CANCELLED')
                time.sleep(.25)


def valid_frame(path, task, store=None):
    """A JPEG envelope is insufficient: cached and newly produced evidence must decode."""
    try:
        content = path.read_bytes() if path.is_file() else b''
        if not (content.startswith(b'\xff\xd8') and content.endswith(b'\xff\xd9')):
            return False
        result = media_command([config(task, 'ffmpeg_bin', 'ffmpeg'), '-nostdin', '-v', 'error',
                                 '-xerror', '-i', str(path), '-f', 'null', '-'],
                                capture_output=True, timeout=30, store=store)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def frame_schedule(task, segment):
    interval = max(1, float(config(task, 'frame_interval_seconds', 20)))
    duration = (segment['end_ms'] - segment['start_ms']) / 1000
    return [(n * interval, segment['start_ms'] + round(n * interval * 1000))
            for n in range(max(1, int((duration - .001) / interval) + 1))]


def extract_frames(store, segment, folder):
    """Produce isolated artifacts; the queue owner publishes them after lease validation."""
    task = store.task()
    if task.get('image_inspection') is False:return ({'frames':[], 'frame_status':'disabled'},None,[])
    path = store.root / segment['media_file']
    details = probe(path, task, store)
    frames, expected_times, files = [], [], []
    if any(stream.get('codec_type') == 'video' for stream in details.get('streams', [])):
        for n, (offset, at) in enumerate(frame_schedule(task, segment)):
            expected_times.append(at)
            retained=next((f for f in segment.get('retained_frames',[]) if f['time_ms']==at),None)
            if retained:
                frames.append(retained)
                continue
            image = folder / f'{n:03d}.jpg'
            target = store.root / 'frames' / str(segment['id']) / image.name
            try:
                # Reuse only published, structurally valid JPEGs from the immutable segment.
                if valid_frame(target, task, store):
                    frames.append({'id': f"frame-{segment['id']}-{n}",
                                   'path': str(target.relative_to(store.root)), 'time_ms': at})
                    continue
                p = media_command([config(task, 'ffmpeg_bin', 'ffmpeg'), '-nostdin', '-v', 'error', '-y',
                                    '-ss', str(offset), '-i', str(path), '-frames:v', '1', '-vf',
                                    'scale=min(1280\\,iw):-2', '-q:v', '10', str(image)], capture_output=True, timeout=30, store=store)
                if p.returncode == 0 and valid_frame(image, task, store):
                    frames.append({'id': f"frame-{segment['id']}-{n}",
                                   'path': str(target.relative_to(store.root)), 'time_ms': at})
                    files.append((image, target))
            except (OSError, subprocess.SubprocessError):
                pass
    missing = sorted(set(expected_times) - {f['time_ms'] for f in frames})
    success = bool(frames) and not missing
    return ({'frames': frames, 'frame_expected_count': len(expected_times),
             'frame_missing_times_ms': missing, 'frame_status': 'success' if success else 'failed'},
            None if success else 'frames_incomplete', files)


def extract_audio(store, segment, folder):
    import wave
    task = store.task()
    if task.get('image_inspection') is False:return ({'frames':[], 'frame_status':'disabled'},None,[])
    path = store.root / segment['media_file']
    details = probe(path, task, store)
    if not any(stream.get('codec_type') == 'audio' for stream in details.get('streams', [])):
        return {'asr_status': 'no_audio'}, None, []
    audio = folder / 'audio.wav'
    target = store.root / 'audio' / f"{segment['id']}.wav"
    p = media_command([config(task, 'ffmpeg_bin', 'ffmpeg'), '-nostdin', '-v', 'error', '-y',
                        '-i', str(path), '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(audio)],
                       capture_output=True, timeout=120, store=store)
    if p.returncode:
        raise RuntimeError('audio extraction failed')
    try:
        with wave.open(str(audio), 'rb') as wav:
            if (wav.getnchannels(), wav.getframerate(), wav.getsampwidth()) != (1, 16000, 2) or wav.getnframes() <= 0:
                raise ValueError('invalid extracted audio')
            if len(wav.readframes(wav.getnframes())) != wav.getnframes() * 2:
                raise ValueError('truncated extracted audio')
    except (wave.Error, EOFError) as error:
        raise ValueError('invalid extracted audio') from error
    return {'audio_file': str(target.relative_to(store.root))}, None, [(audio, target)]


def prepare_segment(task_dir, segment):
    """Compatibility entry point for one synchronous preparation attempt."""
    import tempfile
    store = Store(task_dir, capture=True).for_session()
    operations = []
    if segment.get('frame_status', 'pending') == 'pending':
        operations.append(('frames', extract_frames))
    if segment.get('asr_status', 'pending') == 'pending' and not segment.get('audio_file'):
        operations.append(('audio', extract_audio))
    for kind, extract in operations:
        with tempfile.TemporaryDirectory(dir=store.root, prefix='.media-prep-') as temporary:
            try:
                fields, error, files = extract(store, segment, Path(temporary))
                for source, target in files:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(source, target)
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
                fields = {'frame_status': 'failed'} if kind == 'frames' else {'asr_status': 'failed'}
            store.update_segment(segment['id'], **fields)


def closed_segments(store, session):
    """Read closed CSV entries without changing the queue or task state."""
    listing = store.root / session['listing']
    if not listing.exists():
        return
    with listing.open(newline='', encoding='utf-8') as handle:
        for row in csv.reader(handle):
            if len(row) != 3:
                continue
            try:
                filename, begin, end = row
                index = int(Path(filename).stem.split('-')[-1])
                path = store.root / 'media' / Path(filename).name
                if not path.is_file() or path.stat().st_size == 0:
                    continue
                start_ms = session['base_ms'] + round(float(begin) * 1000)
                end_ms = session['base_ms'] + round(float(end) * 1000)
                if index >= 0 and start_ms >= 0 and end_ms > start_ms:
                    yield index, start_ms, end_ms, str(path.relative_to(store.root))
            except (ValueError, OSError):
                continue


def ingest_closed(store, session):
    if store.task().get('media_frozen'):return
    """CSV entries are emitted by ffmpeg on close, including a graceful EOF tail."""
    task = store.task()
    if task.get('pipeline_version')==2:
        from runtime.realtime import recording_segments
        spans=[{'start_ms':s['start_ms'],'end_ms':s['end_ms']} for s in recording_segments(store)]
        if spans != task.get('capture_spans'):
            store.update_task(capture_spans=spans)
        return
    for segment in closed_segments(store, session):
        try:
            store.add_segment(*segment)
        except (ValueError, OSError):
            continue


def recover_capture_tail(store, session):
    """Called only after capture exits; journal a readable, unlisted final file."""
    closed = list(closed_segments(store, session))
    index = max((s[0] for s in closed), default=int(Path(session['listing']).stem.split('-')[-1]) - 1) + 1
    path = store.root / 'media' / f'segment-{index:06d}.mp4'
    if not path.exists():
        return
    start = max((s[2] for s in closed), default=session['base_ms'])
    try:
        details = probe(path, store.task())
        duration = round(float(details['format']['duration']) * 1000)
        if duration <= 0 or not details.get('streams'):
            raise ValueError('empty tail')
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError):
        store.log('capture_tail_unrecoverable', f'Unclosed media segment {index} is unreadable; coverage remains incomplete')
        return
    # Persist before queue insertion so journal replay is safe after a crash.
    with (store.root / session['listing']).open('a', newline='') as handle:
        csv.writer(handle).writerow([path.name, (start-session['base_ms'])/1000,
                                    (start+duration-session['base_ms'])/1000])
        handle.flush()
        os.fsync(handle.fileno())
    ingest_closed(store, session)
    store.log('capture_tail_recovered', f'Recovered closed media segment {index}; duration {duration} ms')


def capture_session(store, source, base_ms, index, seek=0, cancel=None, bridge=None, duration_ms=None):
    task = store.task()
    folder = store.root / 'media'
    session = {'base_ms': base_ms, 'listing': f'media/session-{index:06d}.csv'}
    if duration_ms is not None:session['duration_ms']=duration_ms
    # Journal before spawning: recovery imports closed files after a worker crash.
    atomic_json(folder / f'session-{index:06d}.json', session)
    seconds = max(1, float(config(task, 'segment_seconds', 30)))
    args = [config(task, 'ffmpeg_bin', 'ffmpeg'), '-nostdin', '-hide_banner', '-loglevel', 'warning', '-y']
    if str(source).startswith(('http://', 'https://')):
        args += ['-rw_timeout', '15000000']
    if seek:
        args += ['-ss', str(seek)]
    args += ['-i', str(source)]
    if duration_ms is not None:args += ['-t', str(duration_ms/1000)]
    args += ['-map', '0:v:0?', '-map', '0:a:0?',
             '-c:v', 'libx264', '-preset', 'veryfast', '-pix_fmt', 'yuv420p',
             '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
             '-force_key_frames', f'expr:gte(t,n_forced*{seconds})',
             '-c:a', 'aac', '-ar', '48000', '-f', 'segment', '-segment_time', str(seconds),
             '-segment_start_number', str(index), '-reset_timestamps', '1',
             '-segment_format', 'mp4', '-segment_format_options',
             'movflags=+frag_keyframe+empty_moov+default_base_moof:frag_duration=1000000:flush_packets=1',
             '-segment_list', str(store.root / session['listing']), '-segment_list_type', 'csv',
             str(folder / 'segment-%06d.mp4')]
    stream=None
    if task.get('pipeline_version')==2:
        from runtime.realtime import CaptureStream
        stream=CaptureStream(store,session,index,bridge,cancel,
                             has_audio=task.get('source_has_audio',True) and not task.get('capture_audio_absent',False))
        args+=stream.outputs()
        if stream.sampled:args+=['-progress',str(stream.progress)]
    # Private stderr is temporary and never reaches logs (it may contain signed URLs).
    error_path = folder / f'session-{index:06d}.stderr'
    with error_path.open('w+b') as errors:
        process = guarded_capture(args, errors,pcm=True) if stream else guarded_capture(args, errors)
        if stream:stream.start(process)
        interrupted = None
        primary = None
        try:
            while process.poll() is None:
                ingest_closed(store, session)
                if (stream and stream.error) or stop_requested(store, cancel) or (task['kind'] == 'live' and store.task().get('live_ended_at')):
                    if interrupted is None:
                        stop_capture(process)
                        interrupted = time.monotonic()
                    elif time.monotonic() - interrupted > (5 if store.task().get('media_frozen') else 22) or live_backlog.remaining(store.task(),22)<=0:
                        kill_tree(process)
                time.sleep(.25)
        except BaseException as error:
            primary = error
        finally:
            from runtime.diagnostics import cleanup_actions, log_failure

            def stop_process():
                if process.poll() is None:
                    try:
                        stop_capture(process)
                    except BaseException as error:
                        cleanup_actions([('cleanup_capture_kill', lambda: kill_tree(process)),
                                         ('cleanup_capture_wait', process.wait)], error)
                        raise
                    try:
                        process.wait(timeout=max(.001,live_backlog.remaining(store.task(),22)))
                    except subprocess.TimeoutExpired:
                        kill_tree(process)
                        process.wait()

            actions = [('cleanup_capture_process', stop_process),
                       ('cleanup_capture_stdin', process.stdin.close)]
            if stream:
                actions.extend([
                    ('cleanup_capture_progress', lambda: store.update_task(capture_last_input_at=time.time())),
                    ('cleanup_capture_stream', stream.join),
                    ('cleanup_capture_stdout', process.stdout.close),
                    ('cleanup_stream_diagnostic', lambda: store.update_task(
                        stream_error=stream.error, stream_diagnostic=getattr(stream, 'diagnostic', None)) if stream.error else None)])
            actions.extend([('cleanup_ingest', lambda: ingest_closed(store, session)),
                            ('cleanup_capture_tail', lambda: recover_capture_tail(store, session))])
            primary = cleanup_actions(actions, primary)
            if primary is not None:
                log_failure(primary, stage='capture_session')
                cleanup_actions([('cleanup_capture_stderr', lambda: error_path.unlink(missing_ok=True))], primary)
                raise primary
        errors.seek(0, os.SEEK_END)
        errors.seek(max(0, errors.tell() - 16384))
        diagnostics=errors.read()
        is_404 = b'404' in diagnostics
        if stream and (b'matches no streams' in diagnostics or b'does not contain any stream' in diagnostics):
            store.update_task(capture_audio_absent=True)
    error_path.unlink(missing_ok=True)
    store.log('capture_process_exit', f'Capture process exit code {process.returncode}; stop requested: {bool(stop_requested(store, cancel))}')
    return process.returncode, is_404


def capture(task_dir, cancel=None, bridge=None):
    store = Store(task_dir, capture=True).for_session()
    acquiring, epoch = False, None
    capture_error = None
    try:
        for journal in sorted((store.root / 'media').glob('session-*.json')):
            ingest_closed(store, json.loads(journal.read_text(encoding='utf-8')))
        task = store.task()
        if task.get('capture_status') in ('ended', 'stopped'):
            return
        if stop_requested(store, cancel):
            reason = ('duration_limit' if task.get('stop_reason')=='duration_limit' else
                      'user_stop' if (task.get('stop_audit') or {}).get('reason')=='user_request' else 'unknown')
            store.update_task(capture_status='stopped', live_source_status=task.get('live_source_status','unknown'),
                              source_end_reason=reason, source_error_code=task.get('source_error_code','none'))
            return
        store.update_task(capture_status='running', live_source_status='unknown',
                          source_end_reason='unknown', source_error_code='none')
        acquiring = True
        if task.get('pipeline_version')==2:
            from runtime.realtime import recording_segments
            segments=recording_segments(store)
        else:segments=store.segments()
        end = max((s['end_ms'] for s in segments), default=0)
        index = max((s['index'] for s in segments), default=-1) + 1
        # Do not overwrite an orphaned unclosed file on restart.
        disk_indices = [int(p.stem.split('-')[-1]) for p in (store.root / 'media').glob('segment-*.mp4')]
        index = max([index, *[i + 1 for i in disk_indices]])
        epoch_file = store.root / 'media' / 'capture-clock.json'
        if epoch_file.exists():
            epoch = json.loads(epoch_file.read_text(encoding='utf-8'))['epoch']
        else:
            epoch = time.time()
            atomic_json(epoch_file, {'epoch': epoch})
        store.update_task(capture_start_ms=0, capture_end_ms=None, capture_epoch=epoch)
        failures, consecutive_404, resolved = 0, 0, None
        while not stop_requested(store, cancel) and not store.task().get('live_ended_at'):
            if resolved is None:
                resolved = resolve_with_retry(store, cancel)
                if resolved['status'] == 'not_live':
                    store.update_task(capture_status='ended')
                    store.log('capture_ended', 'Douyin resolver reports offline')
                    return
            before = len(recording_segments(store)) if task.get('pipeline_version')==2 else len(store.segments())
            # Offset includes downtime/reconnect gaps; never concatenate wall-clock gaps away.
            base = max(end, round((time.time() - epoch) * 1000))
            store.update_task(capture_observed_ms=base)
            code, is_404 = capture_session(store, resolved['streamUrl'], base, index, cancel=cancel,bridge=bridge)
            bridge=None
            store.update_task(capture_observed_ms=max(base, round((time.time() - epoch) * 1000)))
            segments = recording_segments(store) if task.get('pipeline_version')==2 else store.segments()
            end = max((s['end_ms'] for s in segments), default=end)
            index = max((s['index'] for s in segments), default=index) + 1
            # Even unsuccessful attempts may leave an unclosed orphan at this index.
            for orphan in (store.root / 'media').glob('segment-*.mp4'):
                index = max(index, int(orphan.stem.split('-')[-1]) + 1)
            if stop_requested(store, cancel) or store.task().get('live_ended_at'):
                break
            consecutive_404 = consecutive_404 + 1 if is_404 else 0
            failures = 0 if len(segments) > before else failures + 1
            if consecutive_404 >= 2 or not is_404:
                resolved = resolve_with_retry(store, cancel)
                if resolved['status'] == 'not_live':
                    store.update_task(capture_status='ended')
                    store.log('capture_ended', 'Douyin resolver reports offline')
                    return
            if failures >= 3:
                raise SourceError('STREAM_RETRY_EXHAUSTED')
            store.log('capture_reconnect', 'Live source interrupted; reconnecting')
            for _ in range(20):
                if stop_requested(store, cancel):
                    break
                time.sleep(.25)
        current = store.task()
        reason = ('duration_limit' if current.get('stop_reason')=='duration_limit' else
                  'user_stop' if (current.get('stop_audit') or {}).get('reason')=='user_request' else current.get('source_end_reason','unknown'))
        store.update_task(capture_status='ended' if current.get('live_ended_at') else 'stopped', source_end_reason=reason)
    except Exception as error:
        from runtime.diagnostics import failure_details, log_failure
        capture_error = error
        log_failure(error, stage='capture')
        try:
            stopped = stop_requested(store, cancel)
            current = store.task()
            if stopped:
                reason = ('duration_limit' if current.get('stop_reason')=='duration_limit' else
                          'user_stop' if (current.get('stop_audit') or {}).get('reason')=='user_request' else current.get('source_end_reason','unknown'))
            else:
                reason = ('stream_retry_exhausted' if isinstance(error, SourceError) and error.code=='STREAM_RETRY_EXHAUSTED' else
                          'source_resolution_failed' if isinstance(error, DouyinResolveError) else 'capture_failed')
            store.update_task(capture_status='stopped' if stopped else 'failed',
                              source_end_reason=reason,
                              live_source_status=current.get('live_source_status','unknown') if stopped else 'unknown',
                              source_error_code=error.code if not stopped and isinstance(error, SourceError) else current.get('source_error_code','none'),
                              capture_error=error.code if isinstance(error, SourceError) else None,
                              capture_diagnostic=failure_details(error))
            reason = error.code if isinstance(error, SourceError) else type(error).__name__
            store.log('capture_failed', f'Media acquisition unavailable ({reason}); closed segments remain inspectable')
        except Exception as secondary:
            log_failure(secondary, stage='cleanup_capture_failure_state')
            raise error
    finally:
        if acquiring:
            try:
                # Acquisition owns the end of coverage, before review draining.
                end = max((s['end_ms'] for s in store.segments()), default=0)
                if epoch is not None:
                    end = max(end, round(((store.task().get('capture_last_input_at') or time.time()) - epoch) * 1000))
                if store.task().get('capture_start_ms') is not None:
                    store.update_task(capture_end_ms=end, capture_observed_ms=end)
            except Exception as secondary:
                from runtime.diagnostics import log_failure
                log_failure(secondary, stage='cleanup_capture_window')
                if capture_error is None:
                    raise


def build_recording(store):
    """Playback is optional report output; its failure cannot fail inspection."""
    if live_backlog.enabled(store.task()):
        # Optional concatenation cannot hold live completion; retain original chunks.
        store.update_task(playback_status='segments_only')
        return
    try:
        # The report may become ready before the capture guardian closes its last MP4.
        if store.task().get('media_frozen'):
            deadline = time.monotonic() + 35
            while store.task().get('capture_status') == 'running' and time.monotonic() < deadline:
                time.sleep(.2)
        from runtime.platform_support import file_lock
        with file_lock(store.root/'.recording-export.lock', timeout=600):
            task = store.task()
            if task.get('capture_status') in {'stopped','ended','failed'}:
                # Recover recording metadata only; frozen inspection stays sealed.
                for journal in sorted((store.root/'media').glob('session-*.json'))[-1:]:
                    recover_capture_tail(store, json.loads(journal.read_text(encoding='utf-8')))
            playback = task.get('playback_file')
            if playback and (store.root/playback).is_file():
                if task.get('pipeline_version') != 2: return
                from runtime.realtime import recording_segments
                if [s['id'] for s in recording_segments(store)] == [s['segment_id'] for s in task.get('playback_map', [])]: return
            _build_recording(store)
    except Exception as error:
        from runtime.diagnostics import failure_details
        diagnostic = failure_details(error)
        try:
            store.update_task(playback_status='failed', playback_diagnostic=diagnostic)
            store.log('recording_failed', 'Combined recording unavailable; per-segment media retained')
        except Exception:
            # The same DB may be unavailable. Preserve a safe diagnostic without
            # replacing the inspection exception or echoing paths/SQL/credentials.
            print(json.dumps({'event':'recording_failed','diagnostic':diagnostic}), file=sys.stderr)


def _build_recording(store):
    """Browser MP4 plus piecewise mapping: recording time excludes capture gaps."""
    if store.task().get('pipeline_version')==2:
        from runtime.realtime import recording_segments
        segments=recording_segments(store)
    else:segments = sorted(store.segments(), key=lambda s: s['index'])
    if not segments:
        store.update_task(playback_status='segments_only')
        return
    # Playback packaging is report output, outside the inspection drain deadline.
    command_store=None if store.task().get('pipeline_version')==2 or store.task().get('media_frozen') else store
    listing = store.root / 'media' / 'concat.txt'
    # All media_file values here were produced locally, never supplied as ffmpeg syntax.
    listing.write_text(''.join("file '" + str((store.root / s['media_file']).resolve()).replace("'", "'\\''")
                               + "'\n" for s in segments), encoding='utf-8')
    destination = store.root / 'media' / 'recording.mp4'
    fd, name = tempfile.mkstemp(prefix='recording-', suffix='.mp4', dir=destination.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        p = media_command([config(store.task(), 'ffmpeg_bin', 'ffmpeg'), '-nostdin', '-v', 'error',
                            '-y', '-f', 'concat', '-safe', '0', '-i', str(listing), '-c', 'copy',
                            '-movflags', '+faststart', str(temporary)], capture_output=True, timeout=600, store=command_store)
        if p.returncode:
            raise RuntimeError('Recording mux failed')
        details = probe(temporary, store.task(), command_store)
        if not details.get('streams') or float(details['format']['duration']) <= 0:
            raise ValueError('Recording output is not playable')
        offset, mapping = 0, []
        for s in segments:
            # Container duration (including encoder padding) is the actual concatenation span.
            duration = round(float(probe(store.root / s['media_file'], store.task(), command_store)['format']['duration']) * 1000)
            mapping.append({'segment_id': s['id'], 'start_ms': s['start_ms'], 'end_ms': s['end_ms'],
                            'media_start_ms': offset, 'media_end_ms': offset + duration})
            offset += duration
        atomic_json(store.root / 'media' / 'recording-timeline.json', mapping)
        temporary.replace(destination)
        store.update_task(playback_file='media/recording.mp4', playback_map=mapping, playback_status='ready', playback_diagnostic=None)
    finally:
        temporary.unlink(missing_ok=True)


def asr_needs_processing(segment, *, recover_exhausted=False):
    if segment.get('asr_final'):return False
    from runtime.mediakit import unsubmitted_auth_failure
    if segment.get('review_status') in {'done','skipped'}:return False
    if recover_exhausted and (segment.get('asr_status') in {'failed','timed_out','submission_unknown'}
                              or segment.get('asr_recovery_status') in {'preparing','running'}):return True
    if segment.get('asr_selection_reason')=='cloud_unavailable_local':
        return segment.get('asr_status') in {'pending','running','fallback_pending'} and bool(segment.get('audio_file'))
    if (segment.get('asr_backend')=='mediakit' and not segment.get('local_failure')
            and segment.get('asr_status') in {'failed','submission_unknown'}):
        return bool(segment.get('audio_file'))
    if unsubmitted_auth_failure(segment):
        return bool(segment.get('audio_file'))
    status = segment.get('asr_status')
    if status in {'pending', 'running','fallback_pending'}:
        return bool(segment.get('audio_file') or segment.get('asr_task_id'))
    return status in {'submitted', 'timed_out'} and bool(segment.get('asr_task_id'))


def has_recoverable_work(store):
    from runtime.media_jobs import MediaJobs
    segments = store.segments()
    if (any(asr_needs_processing(s,recover_exhausted=store.task().get('asr_backend')=='local'
                and store.task().get('asr_policy') in {'local_first','local_only'}) for s in segments)
            or any(j['backend'] in {'ffmpeg','mediakit'} and j['status'] in {'queued', 'retry_wait', 'running'}
                   for j in MediaJobs(store).rows())):
        return True
    # A crash may leave durable media and CSV records before their SQLite registration.
    # Only discover here: dependency failure must not import evidence or invalidate reports.
    registered = {segment['index'] for segment in segments}
    for journal in sorted((store.root / 'media').glob('session-*.json')):
        if any(index not in registered for index, *_ in closed_segments(store, json.loads(journal.read_text(encoding='utf-8')))):
            return True
    return False


def _run_worker(task_dir, cancel, warmed_bridge=None):
    store = Store(task_dir, capture=True).for_session()
    for folder in ('media', 'audio', 'frames'):
        (store.root / folder).mkdir(parents=True, exist_ok=True)
    heartbeat_done = threading.Event()
    def heartbeat():
        heartbeat_store = Store(task_dir, capture=True).for_session()
        while not heartbeat_done.is_set():
            heartbeat_store.update_progress(worker_heartbeat=time.time())
            from runtime.finishing import closed
            if closed(heartbeat_store.finish_tick()) or heartbeat_store.task().get('media_frozen'):cancel.set()
            from runtime.sampling import enabled, prepare_frames
            if enabled(heartbeat_store.task()):prepare_frames(heartbeat_store)
            heartbeat_done.wait(2)
    pulse = threading.Thread(target=heartbeat, daemon=True)
    pulse.start()
    from runtime.full_live import enabled as full_live_enabled
    if full_live_enabled(store.task()):
        from runtime.live_frames import run as frame_loop
        threading.Thread(target=frame_loop,args=(store,heartbeat_done,cancel),daemon=True).start()
    from runtime.finishing import closed
    if closed(store.finish_tick()) and not (store.task().get('worker_mode') == 'processing_only'
            and store.task().get('stop_requested')
            and store.task().get('capture_status') not in {'ended', 'stopped', 'failed'}):
        heartbeat_done.set();pulse.join(timeout=3)
        return
    store.update_task(worker_status='running',processing_completed_at=None,recovery_state=None)
    acquisition = None
    local_processor = None
    local = store.task().get('asr_backend') == 'local'
    if local:
        from runtime.asr_router import Processor
        local_processor = Processor(store)
        if store.task().get('local_asr_mode')=='segment' and warmed_bridge is not None:
            local_processor.local.bridge=warmed_bridge
            warmed_bridge=None
        if store.task().get('local_asr_mode')=='segment' and warmed_bridge is not None:
            # Batch inference owns the warmed process; capture only queues WAVs.
            local_processor.local.bridge=warmed_bridge
            warmed_bridge=None
    from runtime.media_jobs import MediaJobs, run_job
    jobs = MediaJobs(store)
    attempted, reviewing = set(), {}
    media_cancel = live_backlog.Cancellation(store,cancel) if live_backlog.enabled(store.task()) else cancel
    from runtime.full_live import enabled as full
    if full(store.task()):
        from runtime.local_asr import MediaCancellation
        media_cancel=MediaCancellation(store,cancel)
    production = {'frames': {}, 'audio': {}}
    try:
        if store.task().get('worker_mode') == 'processing_only':
            # Import only already closed artifacts, including a tail journaled before a crash.
            for journal in sorted((store.root / 'media').glob('session-*.json')):
                ingest_closed(store, json.loads(journal.read_text(encoding='utf-8')))
            if store.task().get('pipeline_version')==2:
                from runtime.realtime import recover_spools
                recover_spools(store,cancel)
            task = store.task()
            terminal = task.get('capture_status')
            if terminal not in {'ended', 'stopped', 'failed'}:
                terminal = 'stopped' if task.get('stop_requested') else 'failed'
            store.update_task(capture_status=terminal)
        else:
            capture_fn = capture
            if store.task().get('kind') == 'video':
                from runtime.video import capture_video
                capture_fn = capture_video
            if store.task().get('pipeline_version')==2:
                from runtime.realtime import recover_spools
                recover_spools(store,cancel)
            acquisition = threading.Thread(target=capture_fn, args=(task_dir, cancel,warmed_bridge) if store.task().get('pipeline_version')==2 else (task_dir,cancel), daemon=True)
            acquisition.start()
        asr_concurrency = 10 if store.task().get('inspection_policy')=='lite_live_realtime_v2' else 2 if store.task().get('pipeline_version')==2 else 1 if local else max(1, int(config(store.task(), 'asr_concurrency', 2)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as frame_pool, \
                concurrent.futures.ThreadPoolExecutor(max_workers=2) as audio_pool, \
                concurrent.futures.ThreadPoolExecutor(max_workers=asr_concurrency) as asr_pool:
            executors = {'frames': frame_pool, 'audio': audio_pool}
            while True:
                if closed(store.finish_tick()) or store.task().get('media_frozen'):cancel.set()
                if cancel.is_set() and not reviewing and not any(production.values()):
                    break
                for kind, active in production.items():
                    for jid, future in list(active.items()):
                        if future.done():
                            # Unexpected infrastructure errors fail the worker; its supervisor can
                            # recover the persisted lease. Do not relabel unrelated ASR as failed.
                            future.result()
                            del active[jid]
                    while len(active) < 2 and not media_cancel.is_set():
                        job = jobs.claim(kind)
                        if job is None:
                            break
                        active[job['id']] = executors[kind].submit(run_job, store, job, cancel=media_cancel)
                for sid, future in list(reviewing.items()):
                    if future.done():
                        try:
                            future.result()
                        except Exception:
                            store.log('processing_failed', 'ASR processing failed', sid)
                            store.update_segment(sid, asr_status='failed')
                        del reviewing[sid]
                from runtime.mediakit import recover_credentials, submissions_paused
                if not local or store.task().get('asr_policy')=='local_first': attempted.difference_update(recover_credentials(store))
                paused = False if local else submissions_paused(store)
                todo = jobs.pending()
                for segment in store.segments():
                    sid = segment['id']
                    if segment.get('asr_status') == 'pending' and sid not in reviewing:
                        attempted.discard(sid)
                    if paused or media_cancel.is_set():
                        continue
                    if asr_needs_processing(segment,recover_exhausted=local and store.task().get('asr_policy') in {'local_first','local_only'}) and sid not in attempted:
                        todo = True
                        if len(reviewing) < asr_concurrency:
                            attempted.add(sid)
                            token = live_backlog.Cancellation(store,cancel,sid) if live_backlog.enabled(store.task()) else cancel
                            reviewing[sid] = asr_pool.submit(local_processor.process if local else process_asr, store, segment, cancel=token)
                if (acquisition is None or not acquisition.is_alive()) and not any(production.values()) and not reviewing and not todo:
                    break
                time.sleep(.2)
        if acquisition is not None:
            acquisition.join()
        if store.task().get('pipeline_version')==2 or not closed(store.finish_tick()):build_recording(store)
        capture_status = store.task()['capture_status']
        store.update_task(worker_status='stopped' if cancel.is_set() else 'failed' if capture_status == 'failed' else 'done',
                          failure_stage='capture' if capture_status == 'failed' else None,
                          finished_at=now_iso(),processing_completed_at=now_iso())
    except BaseException as error:
        cancel.set()
        if acquisition is not None:
            acquisition.join(timeout=35)
        # Acquisition owns capture_status. An unrelated frame/audio/ASR worker
        # failure must not be relabelled as a source capture failure.
        capture_status = store.task().get('capture_status')
        fields = worker_failure_fields(capture_status)
        fields['finished_at'] = now_iso()
        from runtime.diagnostics import failure_details
        fields['failure_diagnostic'] = failure_details(error)
        try:
            store.update_task(**fields)
        except Exception:
            pass  # The original failure is re-raised, even if its DB write fails.
        raise
    finally:
        cancel.set()
        heartbeat_done.set()
        pulse.join(timeout=3)
        if local_processor: local_processor.close()
        if warmed_bridge:warmed_bridge.close()


def worker_failure_fields(capture_status):
    fields = {'worker_status':'failed',
              'failure_stage':'capture' if capture_status == 'failed' else 'processing'}
    if capture_status not in {'ended','stopped','failed'}:
        fields['capture_status'] = 'stopped'
    return fields


def run_worker(task_dir, *, supervised=False):
    """One OS-owned capture/ASR worker per task; process death releases the lock."""
    store = Store(task_dir, capture=True).for_session()
    fd = nofollow_open(store.root / '.worker.lock', os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    cancel = threading.Event()
    with os.fdopen(fd, 'w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        clock_done=threading.Event()
        def stop_watchdog():
            from runtime.stop_signal import read as read_stop
            from runtime.platform_support import stop_capture_children, stop_media_children
            requested=False
            while not clock_done.wait(.1):
                intent=read_stop(store.root)
                if not intent:continue
                elapsed=time.time()-intent['requested_at']
                if not requested or elapsed>=4:
                    stop_capture_children(force=elapsed>=4)
                    requested=True
                if elapsed<29:continue
                try:
                    cancel.set()
                    stop_media_children()
                    # Best-effort bookkeeping must never prevent process exit.
                    with store.connection(True,timeout=0) as conn:
                        task=store._task(conn)
                        task.update(capture_status='stopped' if intent['reason']=='user_request' else task.get('capture_status','ended'),worker_status='stopped',processing_completed_at=now_iso())
                        store._set_task(conn,task)
                finally:
                    os._exit(0)
        if supervised and store.task().get('kind','live')=='live':threading.Thread(target=stop_watchdog,daemon=True).start()
        from runtime.sampling import enabled
        def sample_clock():
            while not clock_done.is_set():
                store.finish_tick()
                clock_done.wait(.1)
        clock_thread=threading.Thread(target=sample_clock,daemon=True) if enabled(store.task()) else None
        if clock_thread:clock_thread.start()
        previous = {}
        if threading.current_thread() is threading.main_thread():
            def stop(*_):
                cancel.set()
            for sig in (signal.SIGINT, signal.SIGTERM):
                previous[sig] = signal.signal(sig, stop)
        try:
            from runtime.model_preparation import before_capture
            media_started=False
            if store.task().get('pipeline_version')==2:
                from runtime.model_preparation import select_backend
                ready,bridge=select_backend(store,cancel)
                if ready:
                    media_started=True
                    _run_worker(task_dir,cancel,bridge)
            elif before_capture(store, cancel):
                media_started=True
                _run_worker(task_dir, cancel)
            from runtime.sampling import enabled
            if media_started and enabled(store.task()):
                while store.finish_tick().get('phase') != 'completed':
                    from runtime.sampling import prepare_frames
                    prepare_frames(store)
                    time.sleep(.25)
            return True
        finally:
            clock_done.set()
            if clock_thread:clock_thread.join(timeout=2)
            for sig, handler in previous.items():
                signal.signal(sig, handler)
            fcntl.flock(lock, fcntl.LOCK_UN)


if __name__ == '__main__':
    run_worker(Path(sys.argv[1]).resolve(), supervised=True)
