"""Prepare inference dependencies without modifying the host Python environment."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from runtime.asr_model import ModelError

REQUIREMENTS = Path(__file__).resolve().parents[1] / 'requirements.txt'
DEPENDENCY_ERRORS = {'ASR_DEPENDENCY_UNAVAILABLE', 'ASR_DEPENDENCY_INCOMPATIBLE',
                     'ASR_NUMPY_MISSING', 'ASR_NUMPY_IMPORT_FAILED', 'ASR_NUMPY_LOAD_FAILED',
                     'ASR_SHERPA_IMPORT_FAILED', 'ASR_SHERPA_LOAD_FAILED'}


def location():
    from runtime.artifacts import cache_root, platform_key
    key = hashlib.sha256(REQUIREMENTS.read_bytes() +
                         json.dumps([sys.executable, sys.version, platform_key()]).encode()).hexdigest()
    root = cache_root() / 'python-asr' / key
    return root, root / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def interpreter():
    root, python = location()
    return str(python) if (root / '.ready').is_file() and python.is_file() else sys.executable


def probe(python):
    from runtime.model_preparation import environment
    code = ('from runtime.asr_worker import dependencies; from runtime.asr_model import ModelError\n'
            'try: dependencies()\n'
            'except ModelError as error: print(error.code); raise SystemExit(1)\n')
    try:
        result = subprocess.run([str(python), '-c', code], env=environment(),
                                capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        raise ModelError('ASR_DEPENDENCY_UNAVAILABLE') from None
    if result.returncode:
        code = result.stdout.strip()
        raise ModelError(code if code in DEPENDENCY_ERRORS else 'ASR_DEPENDENCY_UNAVAILABLE')


def prepare(*, install=False):
    from runtime.asr_worker import dependencies
    from runtime.model_preparation import environment
    from runtime.platform_support import file_lock, private_directory
    selected = interpreter()
    try:
        if selected == sys.executable: dependencies()
        else: probe(selected)
        return
    except ModelError:
        if not install: raise
    root, python = location()
    private_directory(root.parent)
    with file_lock(root.with_suffix('.lock')):
        if (root / '.ready').is_file():
            try:
                probe(python)
                return
            except ModelError:
                (root / '.ready').unlink()
        private_directory(root)
        try:
            for stage, command in (('create_venv', [sys.executable, '-m', 'venv', str(root)]),
                            ('install_wheels', [str(python), '-m', 'pip', '--isolated', 'install', '--disable-pip-version-check',
                             '--no-input', '--only-binary=:all:', '--force-reinstall', '-r', str(REQUIREMENTS)])):
                subprocess.run(command, env=environment(), stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               timeout=300, check=True)
            probe(python)
        except (OSError, subprocess.SubprocessError) as error:
            failure = ModelError('ASR_DEPENDENCY_TIMEOUT' if isinstance(error, subprocess.TimeoutExpired) else
                                 'ASR_DEPENDENCY_COMMAND_FAILED' if isinstance(error, subprocess.CalledProcessError) else
                                 'ASR_DEPENDENCY_UNAVAILABLE')
            failure.stage = stage
            failure.errno = getattr(error, 'errno', None)
            failure.winerror = getattr(error, 'winerror', None)
            raise failure from None
        (root / '.ready').touch(mode=0o600)
