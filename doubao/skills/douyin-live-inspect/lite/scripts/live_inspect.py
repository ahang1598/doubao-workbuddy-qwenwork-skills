#!/usr/bin/env python3
import sys
from pathlib import Path
# JSON stdin/stdout is UTF-8 on every host, including Windows consoles.
for stream in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(stream, 'reconfigure'): stream.reconfigure(encoding='utf-8')
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runtime.telemetry_context import open_channel, close_channel
open_channel()
from runtime.cli import main
if __name__=='__main__':
    from runtime.review_execution import COMMANDS, supervise
    if len(sys.argv) > 1 and (sys.argv[1] in {'review-state', 'result-page'} or (sys.argv[1] in COMMANDS and any(a.split('=')[0] == '--request-id' for a in sys.argv[2:]))) and not any(a in ('-h','--help') for a in sys.argv):
        raise SystemExit(supervise(sys.argv[1:]))
    from runtime.telemetry import enter_bridge
    enter_bridge()
    try:
        raise SystemExit(main())
    finally:
        close_channel()
