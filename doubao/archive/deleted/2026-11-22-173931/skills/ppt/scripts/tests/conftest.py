"""Use package imports regardless of the shell's PYTHONPATH."""
from pathlib import Path
import sys

skill_root = str(Path(__file__).resolve().parents[2])
if skill_root not in sys.path:
    sys.path.insert(0, skill_root)
