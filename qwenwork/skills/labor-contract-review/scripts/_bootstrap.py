from __future__ import annotations

from pathlib import Path
import sys


def ensure_skill_import_root(script_file: str) -> Path:
    """Add the skill root containing labor_contract_review to sys.path."""
    script_path = Path(script_file).resolve()
    candidates: list[Path] = []

    for parent in script_path.parents:
        candidates.append(parent)
    cwd = Path.cwd().resolve()
    candidates.append(cwd)
    candidates.extend(cwd.parents)
    candidates.extend(parent / "labor-contract-review" for parent in [cwd, *cwd.parents])

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if (candidate / "labor_contract_review" / "__init__.py").exists():
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            return candidate

    fallback = script_path.parents[1]
    if str(fallback) not in sys.path:
        sys.path.insert(0, str(fallback))
    return fallback
