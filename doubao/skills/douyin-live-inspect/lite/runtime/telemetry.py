"""Optional Node bridge. Telemetry must never become a media dependency."""
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CHILD_MARKER = 'BYTEDLIVE_LITE_TELEMETRY_CHILD'
from runtime.telemetry_keys import COMMANDS

# Execution context for existing task lifecycle hooks, not a usage-event whitelist.
BRIDGE_COMMANDS = COMMANDS | {'doctor', 'status', 'resume', 'refresh-credentials', 'asr-reconcile',
            'review-next', 'review-state', 'rules-load', 'review-submit', 'prepare-runtime',
            'start-video', 'batch-create', 'batch-next', 'batch-status', 'batch-stop',
            'recap-input', 'recap-submit', 'report-delivery-ack', 'delivery-ack', 'result-page', 'scene-confirm', 'review-defer', 'snapshot'}


def prepare_identity_directory(directory):
    # On Windows this applies the existing user/SYSTEM DACL, not POSIX chmod.
    from runtime.platform_support import private_directory
    private_directory(directory)


def wait_windows(command):
    try:
        child = subprocess.Popen(command, creationflags=getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x200))
    except OSError:
        return None  # No business command started: caller may safely fall back.
    try:
        return child.wait()
    except KeyboardInterrupt:
        try:
            child.send_signal(signal.CTRL_BREAK_EVENT)
            child.wait()
        except (KeyboardInterrupt, OSError):
            try:
                child.kill()
                child.wait()
            except OSError:
                pass
        return 130
    except OSError:
        # A process already exists: never rerun a potentially accepted write.
        return 1


def capability():
    if os.environ.get('BYTEDLIVE_TELEMETRY_DISABLED', '').strip().lower() in ('1', 'true'):
        return {'status': 'disabled'}, None
    node = shutil.which('node')
    if not node:
        return {'status': 'missing_node'}, None
    try:
        probe = subprocess.run([node, '--version'], capture_output=True, text=True, timeout=1)
        match = re.fullmatch(r'v(\d+)\.\d+\.\d+\s*', probe.stdout)
        if probe.returncode or not match or int(match[1]) < 20:
            return {'status': 'unsupported_node'}, None
    except (OSError, ValueError, subprocess.SubprocessError):
        return {'status': 'unavailable'}, None
    if not (ROOT / 'scripts/telemetry.cjs').is_file() or not (ROOT / 'scripts/vendor/tooling-telemetry.cjs').is_file():
        return {'status': 'unavailable'}, None
    return {'status': 'available'}, node


def enter_bridge():
    # Consume the marker so unrelated subprocesses do not inherit a bypass.
    if os.environ.pop(CHILD_MARKER, None) == '1':
        return
    args = sys.argv[1:]
    if not args or args[0] not in BRIDGE_COMMANDS or '--help' in args or '-h' in args:
        return
    _, node = capability()
    if node:
        command = [node, str(ROOT / 'scripts/telemetry.cjs'), sys.executable,
                   str(ROOT / 'scripts/live_inspect.py'), *args]
        if os.name == 'nt':
            code = wait_windows(command)
            if code is not None:
                raise SystemExit(code)
            return
        try:
            os.execv(node, command)
        except OSError:
            # exec failure means no business process has started; safe to run locally.
            pass

# Compatibility for pre-extraction callers; one metadata implementation.
from runtime.telemetry_context import publish_metadata
