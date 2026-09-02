"""Path policy for generated english-contract-review artifacts."""

from __future__ import annotations

from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent


def generated_path(path: Path, label: str = "output") -> Path:
    resolved = path.expanduser().resolve()
    try:
        relative = resolved.relative_to(SKILL_ROOT)
    except ValueError as exc:
        raise ValueError(
            f"{label} must be stored inside the english-contract-review skill"
        ) from exc
    if not relative.parts or relative.parts[0] != "outputs":
        raise ValueError(
            f"{label} must be stored under outputs/ in this skill"
        )
    return resolved
