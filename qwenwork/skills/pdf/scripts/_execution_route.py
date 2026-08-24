"""One-shot local/cloud backend routing for PDF Skill semantic scripts.

This module never installs dependencies and never knows operation-specific
parameters.  Each script supplies bounded probes, adapters, and output
validation at this seam.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Callable, Generic, TypeVar


T = TypeVar("T")


class ExecutionMode(str, Enum):
    AUTO = "auto"
    LOCAL_REQUIRED = "local_required"
    CLOUD_REQUIRED = "cloud_required"


class BackendFailure(RuntimeError):
    """One backend failed with a stable, bounded reason."""

    def __init__(self, code: str, *, retryable: bool, message: str = ""):
        super().__init__(message or code)
        self.code = code
        self.retryable = retryable


class BackendUnavailable(BackendFailure):
    def __init__(self, code: str):
        super().__init__(code, retryable=False)


@dataclass(frozen=True)
class ExecutionReport:
    backend: str
    initial_backend: str
    fallback_used: bool
    fallback_reason: str = ""
    selection_reason: str = ""
    validation: str = "passed"

    def emit(self) -> None:
        print(
            "[QWENWORK-PDF-EXECUTION] "
            + json.dumps(asdict(self), ensure_ascii=False, separators=(",", ":")),
            file=sys.stderr,
            flush=True,
        )


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes"}


def execution_mode() -> ExecutionMode:
    configured = os.environ.get("QWENWORK_DOCUMENT_EXECUTION_MODE", "").strip().lower()
    if configured:
        try:
            return ExecutionMode(configured)
        except ValueError as exc:
            raise BackendUnavailable("EXECUTION_MODE_INVALID") from exc
    if _truthy("QWENWORK_DOCUMENT_RUNTIME_REQUIRED"):
        return ExecutionMode.CLOUD_REQUIRED
    return ExecutionMode.AUTO


def _run_and_validate(run: Callable[[], T], validate: Callable[[T], bool]) -> T:
    result = run()
    try:
        valid = validate(result)
    except BackendFailure:
        raise
    except Exception as exc:
        raise BackendFailure(
            "OUTPUT_VALIDATION_FAILED", retryable=True,
            message="backend output validation failed",
        ) from exc
    if not valid:
        raise BackendFailure(
            "OUTPUT_VALIDATION_FAILED", retryable=True,
            message="backend output validation failed",
        )
    return result


def execute_with_fallback(
    *,
    mode: ExecutionMode,
    local_ready: Callable[[], bool],
    cloud_ready: Callable[[], bool],
    run_local: Callable[[], T],
    run_cloud: Callable[[], T],
    validate: Callable[[T], bool],
) -> tuple[T, ExecutionReport]:
    """Execute once, with at most one eligible switch to the other backend."""

    if mode == ExecutionMode.LOCAL_REQUIRED:
        if not bool(local_ready()):
            raise BackendUnavailable("LOCAL_DEPENDENCY_MISSING")
        result = _run_and_validate(run_local, validate)
        return result, ExecutionReport("local", "local", False)
    if mode == ExecutionMode.CLOUD_REQUIRED:
        if not bool(cloud_ready()):
            raise BackendUnavailable("CLOUD_RUNTIME_UNAVAILABLE")
        result = _run_and_validate(run_cloud, validate)
        return result, ExecutionReport("cloud", "cloud", False)

    cloud_available = bool(cloud_ready())
    local_available = bool(local_ready())
    if cloud_available:
        initial_backend = "cloud"
        initial_run = run_cloud
        alternate_backend = "local"
        alternate_run = run_local
        alternate_available = local_available
        selection_reason = "CLOUD_CAPABILITY_READY"
    elif local_available:
        initial_backend = "local"
        initial_run = run_local
        alternate_backend = "cloud"
        alternate_run = run_cloud
        alternate_available = False
        selection_reason = "CLOUD_RUNTIME_UNAVAILABLE_OR_INCOMPATIBLE"
    else:
        raise BackendUnavailable("NO_EXECUTION_BACKEND_AVAILABLE")

    try:
        result = _run_and_validate(initial_run, validate)
        return result, ExecutionReport(
            initial_backend,
            initial_backend,
            False,
            selection_reason=selection_reason,
        )
    except BackendFailure as exc:
        if not exc.retryable or not alternate_available:
            raise
        result = _run_and_validate(alternate_run, validate)
        return result, ExecutionReport(
            alternate_backend,
            initial_backend,
            True,
            fallback_reason=exc.code,
            selection_reason=selection_reason,
        )
