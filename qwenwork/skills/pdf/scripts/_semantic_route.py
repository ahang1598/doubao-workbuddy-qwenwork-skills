"""Process boundary for local-first PDF Skill semantic script routing.

The original script owns argument parsing and operation-specific cloud flags.
In auto mode this helper re-enters that same script once with
``local_required`` so dependency/import failures are observable without
installing anything.  At most one cloud fallback is allowed.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, TypeVar

from _execution_route import (
    BackendFailure,
    ExecutionMode,
    execute_with_fallback,
    execution_mode,
)


T = TypeVar("T")


def execute_semantic_script(
    *,
    argv: list[str],
    local_ready: Callable[[], bool],
    cloud_ready: Callable[[], bool],
    run_cloud: Callable[[], T],
    validate: Callable[[T], bool],
    local_result: Callable[[], T] | None = None,
    timeout_seconds: int = 620,
) -> bool:
    """Run a semantic script through one bounded local/cloud decision.

    Returns ``False`` only for ``local_required`` so the caller can continue
    into its existing local implementation in the current process.  Every
    other mode is fully handled here and returns ``True``.
    """

    mode = execution_mode()
    if mode == ExecutionMode.LOCAL_REQUIRED:
        return False
    if not argv or not isinstance(argv[0], str) or not argv[0]:
        raise BackendFailure("LOCAL_ENTRY_INVALID", retryable=False)

    script_path = Path(argv[0]).expanduser().resolve()

    def run_local() -> T:
        environment = os.environ.copy()
        environment["QWENWORK_DOCUMENT_EXECUTION_MODE"] = ExecutionMode.LOCAL_REQUIRED.value
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            result = subprocess.run(
                [sys.executable, str(script_path), *argv[1:]],
                stdin=subprocess.DEVNULL,
                env=environment,
                timeout=timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise BackendFailure("LOCAL_PROCESS_UNAVAILABLE", retryable=True) from exc
        if result.returncode != 0:
            raise BackendFailure("LOCAL_OPERATION_FAILED", retryable=True)
        return local_result() if local_result is not None else None  # type: ignore[return-value]

    result, report = execute_with_fallback(
        mode=mode,
        local_ready=local_ready,
        cloud_ready=cloud_ready,
        run_local=run_local,
        run_cloud=run_cloud,
        validate=validate,
    )
    del result
    report.emit()
    return True
