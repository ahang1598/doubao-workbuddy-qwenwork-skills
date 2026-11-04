"""Detached best-effort Node transport; never replays business operations."""
import json
import os
import subprocess
import threading

def _reap(child):
    # Node also has its own deadline; this watchdog handles a stuck executable.
    try:
        child.wait(timeout=4)
    except subprocess.TimeoutExpired:
        try:
            child.kill()
            child.wait(timeout=1)
        except (OSError, subprocess.SubprocessError):
            pass
    except (OSError, subprocess.SubprocessError):
        pass


def send(events):
    from runtime.task_telemetry import enabled
    if not events or not enabled():
        return
    try:
        from runtime.telemetry import capability, ROOT
        from runtime.credentials import background_env
        node = os.environ.get('BYTEDLIVE_LITE_TELEMETRY_NODE')
        if not node:
            _, node = capability()  # Direct Python callers have no bridge context.
        if not node:
            return
        for payload in events:
            child = None
            try:
                encoded = json.dumps(payload, ensure_ascii=False).encode('utf-8')
                # Fit below the minimum pipe capacity, so sending stdin never
                # depends on the reporter reading it or reaching the network.
                if len(encoded) > 4096:
                    continue
                options = ({'creationflags': getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x200)}
                           if os.name == 'nt' else {'start_new_session': True})
                child = subprocess.Popen([node, str(ROOT / 'scripts/telemetry-task.cjs')],
                    stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, env=background_env(), **options)
                try:
                    child.stdin.write(encoded)
                    child.stdin.close()
                finally:
                    threading.Thread(target=_reap, args=(child,), daemon=True).start()
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
                if child is not None:
                    try:
                        child.stdin.close()
                    except (OSError, ValueError):
                        pass
                    try:
                        child.kill()
                    except OSError:
                        pass
    except Exception:
        pass
