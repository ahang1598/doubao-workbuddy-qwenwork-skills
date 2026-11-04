"""JS and Python read the same event registry; never duplicate wire keys here."""
import json
from pathlib import Path
from types import SimpleNamespace

_KEYS = json.loads((Path(__file__).resolve().parents[2] / 'runtime/telemetry-events.json').read_text(encoding='utf-8'))
TASK = SimpleNamespace(**_KEYS['task'])
FUNNEL = SimpleNamespace(**_KEYS['funnel'])
COMMANDS = frozenset(_KEYS['lite'].values())
