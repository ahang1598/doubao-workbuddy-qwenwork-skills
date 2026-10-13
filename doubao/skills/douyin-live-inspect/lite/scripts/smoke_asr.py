#!/usr/bin/env python3
"""Authorized WAV smoke; stdout deliberately excludes transcript content."""
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.local_asr import LocalASR, resolve_runtime_root


def main():
    value = json.load(sys.stdin)
    audio = Path(value['audio_path']).resolve(strict=True)
    worker = LocalASR()
    try:
        started = time.monotonic()
        metadata = worker.request('initialize', runtime_root=resolve_runtime_root(value.get('runtime_root')),
                                  task_root=str(audio.parent), timeout=60)
        cold_ms = round((time.monotonic()-started)*1000)
        result = worker.request('transcribe', audio_path=str(audio), timeout=240)
        print(json.dumps(dict(ok=True, runtime=metadata, cold_ms=cold_ms, subtitle_count=len(result['subtitles']),
                              **{k:v for k,v in result.items() if k != 'subtitles'})))
    finally: worker.close()


if __name__ == '__main__': main()
