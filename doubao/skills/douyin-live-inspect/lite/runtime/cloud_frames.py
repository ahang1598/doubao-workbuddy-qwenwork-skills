"""MediaKit frame requests and task-local, per-sample failure diagnostics."""
from contextlib import contextmanager
import json
import subprocess

from runtime import mediakit


class FrameError(RuntimeError):
    """A fixed local reason, never a provider message or image URL."""


class FrameRequest:
    def __init__(self, store, segment_id, sample_ms, offset):
        self.store = store
        self.segment_id = segment_id
        self.sample_ms = sample_ms
        self.offset = offset

    def failed(self, stage, error):
        detail = getattr(error, 'diagnostic', {})
        reason = str(error) if isinstance(error, FrameError) else type(error).__name__
        event = {'stage': stage, 'sample_ms': self.sample_ms,
                 'offset_ms': round(self.offset * 1000), 'reason': detail.get('category', reason)}
        if detail.get('failure_stage') == 'upload_address':
            event['upstream_stage'] = 'upload_address'
        for key in ('error_code', 'http_status', 'request_id', 'log_id', 'exit_code'):
            if detail.get(key) is not None:
                event[key] = detail[key]
        try:
            self.store.log('frame_remote_failure', json.dumps(event, separators=(',', ':')), self.segment_id)
        except Exception:
            pass  # Losing diagnostics must not change recovery or cause a second submission.
        return False

    @contextmanager
    def stage(self, stage):
        try:
            yield
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            self.failed(stage, error)
            raise

    def submit(self, binary, source, env, timeout):
        selector = (['--snapshot-type', 'SpecifiedFrames', '--specified-frames', '[0]']
                    if self.offset == 0 else
                    ['--snapshot-type', 'SpecifiedTime', '--specified-time', json.dumps([self.offset])])
        with self.stage('submit'):
            result = mediakit.invoke(binary, ['video', 'extract-frames', '--video-url', str(source), *selector],
                                     env=env, timeout=timeout, store=self.store, segment_id=self.segment_id)
            task_id = result.get('task_id')
            if not isinstance(task_id, str) or not task_id.strip():
                raise FrameError('missing_task_id')
            return task_id

    def query(self, binary, task_id, env, timeout):
        with self.stage('query'):
            result = mediakit.invoke(binary, ['shared', 'query-task', '--task-id', task_id],
                                     env=env, timeout=timeout, store=self.store, segment_id=self.segment_id)
            status = str(result.get('status', '')).lower()
            if status in {'running', 'queued', 'pending', 'submitted', 'processing'}:
                return None
            if status != 'completed':
                raise FrameError('remote_' + status if status in {'failed','canceled','cancelled'} else 'unexpected_status')
            snapshots = result.get('snapshots')
            if not isinstance(snapshots, list) or len(snapshots) != 1 or not isinstance(snapshots[0], dict):
                raise FrameError('invalid_snapshots')
            url = snapshots[0].get('image_url')
            if not isinstance(url, str) or not url.strip():
                raise FrameError('missing_image_url')
            return url


def validate_cloud_image(path, store=None, cancel=None):
    """Decode only the downloaded JPEG/PNG, bounded by bytes and pixels."""
    from runtime.media import media_command
    from runtime.mediakit import config
    if not 0 < path.stat().st_size <= 8 * 1024 * 1024:
        return False
    data = path.read_bytes()
    if data.startswith(b'\xff\xd8') and data.endswith(b'\xff\xd9'):
        codec = 'mjpeg'
    elif data.startswith(b'\x89PNG\r\n\x1a\n') and data.endswith(bytes.fromhex('0000000049454e44ae426082')):
        codec = 'png'
    else:
        return False
    try:
        from PIL import Image
    except ImportError:
        # The host already supplies or prepares this decoder for media work.
        task = store.task() if store else {}
        def decode():
            return media_command([config(task, 'ffmpeg_bin', 'ffmpeg'), '-nostdin', '-v', 'error',
                                  '-xerror', '-err_detect', 'explode', '-max_pixels', '16000000',
                                  '-f', 'image2pipe', '-c:v', codec, '-i', 'pipe:0', '-frames:v', '1',
                                  '-abort_on', 'empty_output', '-f', 'null', '-'],
                                 input=data, capture_output=True, timeout=10, store=store).returncode == 0
        try:
            return decode()
        except FileNotFoundError:
            from runtime.media_fallback import ensure
            if store is None or not ensure(store, cancel, 'frame_validation'):
                raise
            task = store.task()
            return decode()
    try:
        with Image.open(path) as image:
            if image.format not in {'JPEG', 'PNG'} or image.width * image.height > 16000000:
                return False
            image.verify()
        with Image.open(path) as image:
            image.load()
        return True
    except (OSError, ValueError, SyntaxError, EOFError, Image.DecompressionBombError):
        return False
