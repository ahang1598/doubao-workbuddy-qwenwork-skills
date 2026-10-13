"""Private-directory setup for the optional Node identity cache; no identity output."""
import sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.telemetry import prepare_identity_directory

if __name__ == '__main__':
    try:
        prepare_identity_directory(sys.argv[1])
    except Exception:
        raise SystemExit(1) from None
