"""Platform-neutral model integrity contract; legacy single-pass assets remain readable."""
import hashlib
import json
from pathlib import Path
import re

MODEL = 'zipformer-multi-zh-hans-int8-2023-12-13'
VERSION = '1.13.4'
REQUIRED = ['vad/silero_vad.onnx', *[f'model/{MODEL}/{n}' for n in
            ('encoder.int8.onnx', 'decoder.onnx', 'joiner.int8.onnx', 'tokens.txt')]]


class ModelError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def checked_model(root):
    root = Path(root).resolve()
    if not root.is_dir(): raise ModelError('ASR_RUNTIME_NOT_FOUND')
    manifest = root / 'manifest.json'
    legacy = not manifest.exists()
    if legacy:
        candidates = list(root.glob('manifest.darwin-*.json'))
        if len(candidates) != 1: raise ModelError('ASR_RUNTIME_NOT_FOUND')
        manifest = candidates[0]
    if manifest.is_symlink() or manifest.stat().st_size > 65536:
        raise ModelError('ASR_RUNTIME_INVALID')
    m = json.loads(manifest.read_text(encoding='utf-8'))
    if (m.get('schemaVersion') != (2 if legacy else 3) or m.get('mode') != 'offline'
            or m.get('engine') != 'zipformer_transducer' or m.get('model') != MODEL
            or m.get('modelFile') != 'encoder.int8.onnx' or m.get('secondPassModel')
            or m.get('sherpaOnnxVersion') != VERSION):
        raise ModelError('ASR_RUNTIME_INCOMPATIBLE')
    entries = m.get('files')
    if not isinstance(entries, list) or len(entries) > 32: raise ModelError('ASR_RUNTIME_INVALID')
    allowed = set(REQUIRED) | {'licenses/sherpa-onnx-Apache-2.0.txt', 'licenses/onnxruntime-MIT.txt'}
    native = {f"darwin-{m.get('arch')}/bin/offline-asr",
              f"darwin-{m.get('arch')}/lib/libsherpa-onnx-c-api.dylib",
              f"darwin-{m.get('arch')}/lib/libonnxruntime.1.27.0.dylib"} if legacy else set()
    listed = {}
    for item in entries:
        if not isinstance(item, dict): raise ModelError('ASR_RUNTIME_INVALID')
        name = item.get('path', '')
        if (not isinstance(name, str) or name not in allowed | native or name in listed or '\\' in name or name.startswith('/')
                or any(part in ('', '.', '..') for part in name.split('/'))):
            raise ModelError('ASR_RUNTIME_INVALID')
        listed[name] = item
    if not set(REQUIRED) <= listed.keys(): raise ModelError('ASR_RUNTIME_INVALID')
    for name in listed.keys() - native:
        item = listed.get(name, {})
        path = root / name
        if (not path.resolve().is_relative_to(root) or path.is_symlink() or not path.is_file()
                or type(item.get('bytes')) is not int or not 0 < item['bytes'] <= 200_000_000
                or path.stat().st_size != item['bytes']
                or not re.fullmatch('[a-f0-9]{64}', str(item.get('sha256', '')))):
            raise ModelError('ASR_RUNTIME_INVALID')
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''): digest.update(block)
        if digest.hexdigest() != item['sha256']: raise ModelError('ASR_RUNTIME_INVALID')
    fingerprint = hashlib.sha256(json.dumps(m, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
    # Legacy single-pass task fingerprints pin identical weights/configuration. Do
    # not accept dual-pass tasks or silently migrate them to another model.
    metadata = dict(runtime_version=m['runtimeVersion'], protocol_version=m.get('protocolVersion', 1),
                    model=MODEL, model_file=m['modelFile'], engine=m['engine'],
                    asr_mode='single_pass', fingerprint=fingerprint)
    if legacy: metadata['arch'] = m['arch']
    else: metadata['inference_backend'] = f'sherpa-onnx-python-{VERSION}'
    return root, metadata
