"""One bounded, cancellable preparation using the existing FFmpeg installer."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
from runtime.store import Store, atomic_json


def ensure(store, cancel, reason):
    from runtime.platform_support import media_popen, kill_tree, process_options, open_lock, lock_file
    from runtime.mediakit import config
    def stopped():
        return (cancel is not None and cancel.is_set()) or (reason in {'local_backend','capture_format'} and store.should_stop())
    with os.fdopen(open_lock(store.root/'.ffmpeg-preparation.lock'), 'r+b') as lock:
        while True:
            if stopped():return False
            try:
                lock_file(lock, blocking=False)
                break
            except BlockingIOError:
                time.sleep(.1)
        task=store.task()
        from runtime.artifacts import binary_ok
        names = ('ffmpeg', 'ffprobe')
        paths = [config(task, name+'_bin', None) for name in names]
        if reason == 'playback' and sys.platform.startswith('linux') and not task.get('artifact_specs', {}).get('ffmpeg'):
            # Export probes every retained source and validates the muxed tracks and duration.
            paths = [path or shutil.which(name)
                     for name, path in zip(names, paths)]
            if all(path and binary_ok(path, name) for name, path in zip(names, paths)):
                binaries = dict(task.get('runtime_binaries', {}))
                binaries.update({name + '_bin': path for name, path in zip(names, paths)})
                store.update_task(runtime_binaries=binaries, ffmpeg_fallback_status='ready',
                                  ffmpeg_fallback_reason=reason, ffmpeg_fallback_issues=[])
                return True
        if all(paths) and (task.get('kind', 'live') != 'live' or all(
                binary_ok(path, name, require_v8=True) for name, path in zip(names, paths))):
            return True
        if task.get('ffmpeg_fallback_status') == 'failed' and reason != 'playback':return False
        if stopped():return False
        store.update_task(ffmpeg_fallback_status='preparing',ffmpeg_fallback_reason=reason)
        result=store.root/'.ffmpeg-preparation.json'
        result.unlink(missing_ok=True)
        process = None
        try:
            process=media_popen([sys.executable,'-m','runtime.media_fallback',str(store.root)],cwd=Path(__file__).resolve().parents[1],
                                stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL, **process_options())
            # The installer bounds network stalls and local work separately.
            while process.poll() is None:
                if stopped():
                    kill_tree(process);break
                time.sleep(.1)
            process.wait(timeout=5)
            check=json.loads(result.read_text()) if result.is_file() else {}
            if check.get('ready') and not stopped():
                store.update_task(runtime_binaries={**task.get('runtime_binaries',{}),**check['binaries']},
                                  ffmpeg_fallback_status='ready', ffmpeg_fallback_issues=[])
                return True
            store.update_task(ffmpeg_fallback_status='failed',
                              ffmpeg_fallback_issues=check.get('issues',[]))
            return False
        except (OSError, ValueError, subprocess.SubprocessError):
            store.update_task(ffmpeg_fallback_status='failed')
            raise
        finally:
            if process is not None:
                if process.poll() is None:kill_tree(process);process.wait(timeout=5)
                process.stdin.close()
            result.unlink(missing_ok=True)


def audio(store, segment, cancel):
    from runtime.media import media_command
    from runtime.mediakit import config
    if segment.get('media_container')!='flv':return True
    target=store.root/'audio'/f"flv-{segment['id']}.wav"
    if segment.get('flv_audio_prepared') and target.is_file():return True
    if segment.get('flv_audio_attempted'):return False
    if not store.update_segment(segment['id'],flv_audio_attempted=True):return False
    if not ensure(store,cancel,'local_audio'):return False
    temporary=target.with_suffix('.part.wav')
    try:
        result=media_command([config(store.task(),'ffmpeg_bin',None),'-nostdin','-v','error','-y',
            '-i',str(store.local_path(segment['media_file'])),'-vn','-ac','1','-ar','16000',
            '-c:a','pcm_s16le',str(temporary)],store=store,timeout=45)
        if result.returncode or not temporary.is_file():return False
        temporary.chmod(0o600);temporary.replace(target)
        return store.update_segment(segment['id'],audio_file=str(target.relative_to(store.root)),flv_audio_prepared=True)
    except (OSError,RuntimeError,subprocess.SubprocessError):return False
    finally:temporary.unlink(missing_ok=True)


if __name__=='__main__':
    owns_group = os.name != 'nt' and os.getpgrp() == os.getpid()
    def parent_watch():
        os.read(sys.stdin.fileno(),1)
        if owns_group:
            import signal
            os.killpg(os.getpgrp(), signal.SIGKILL)
        os._exit(0)
    threading.Thread(target=parent_watch,daemon=True).start()
    from runtime.artifacts import prepare
    store=Store(sys.argv[1])
    atomic_json(store.root/'.ffmpeg-preparation.json',prepare(task=store.task(),common_only=True,supervised=owns_group))
