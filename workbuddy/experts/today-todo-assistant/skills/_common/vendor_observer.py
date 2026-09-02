"""随专家包分发的最小可用观测 SDK。

仅在 `ssv-agent-obser-sdk` 无法安装或导入时使用；保持与专家所需公共接口兼容，
并只依赖 Python 标准库。
"""

import contextvars
import hashlib
import json
import os
import platform
import ssl
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


SDK_VERSION = "0.3.0-bundled"
GALILEO_COLLECT_URL = "https://galileotelemetry.tencent.com/collect"
_TRACE = contextvars.ContextVar("ssv_observe_trace", default=None)
_SPAN = contextvars.ContextVar("ssv_observe_span", default=None)


def _now_ns():
    return time.time_ns()


def _identifier(value, length):
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:length]


def _sanitize(attributes):
    hidden = (
        "authorization", "cookie", "password", "secret", "credential", "token",
        "api_key", "apikey", "prompt", "content", "message", "text",
    )
    return {
        str(key)[:100]: value
        for key, value in (attributes or {}).items()
        if str(key).strip() and not any(item in str(key).lower() for item in hidden)
    }


def _json_value(value):
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:500]
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value[:100]]
    if isinstance(value, dict):
        return {str(key)[:100]: _json_value(item) for key, item in list(value.items())[:100]}
    return str(value)[:500]


def build_collect_payload(trace, topic):
    """构造与 `ssv-agent-obser-sdk` 兼容的 Galileo collect 负载。"""
    env = "production" if trace.get("environment") == "production" else "test"

    def record(item, root=False):
        start = trace["start_time_unix_nano"] if root else item["start_time_unix_nano"]
        end = trace["end_time_unix_nano"] if root else item["end_time_unix_nano"]
        status = item.get("status") or "ok"
        message = {
            key: _json_value(value)
            for key, value in (trace["attributes"] if root else item["attributes"]).items()
        }
        name = trace["operation"] if root else item["name"]
        message.update(
            {
                "msg": f"{trace['expert_id']} {name}",
                "trace_id": trace["trace_id"],
                "span_id": trace["root_span_id"] if root else item["span_id"],
                "parent_span_id": "" if root else item["parent_span_id"],
                "span_name": name,
                "kind": "agent" if root else item["kind"],
                "duration_ms": max(0, end - start) // 1_000_000,
                "status": status,
                "error_type": item.get("error_type") or "",
                "status_message": item.get("status_message") or "",
            }
        )
        return {
            "fields": json.dumps(
                {
                    "type": "normal",
                    "level": "error" if status == "error" else "info",
                    "plugin": "log",
                    "env": env,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            "message": [json.dumps(message, ensure_ascii=False, separators=(",", ":"))],
            "timestamp": end // 1_000_000,
        }

    root = {
        "status": trace["status"],
        "error_type": trace["error_type"],
        "status_message": trace["status_message"],
    }
    return {
        "topic": topic,
        "bean": {
            "uid": trace["session_id_hash"] or trace["run_id"],
            "version": trace["expert_version"],
            "aid": _identifier(
                "|".join((platform.node(), platform.system(), platform.machine())), 32
            ),
            "env": env,
            "platform": platform.system() or "unknown",
            "netType": "",
            "vp": "",
            "sr": "",
            "referer": "",
            "from": trace["expert_id"],
        },
        "ext": json.dumps(
            {
                "trace_id": trace["trace_id"],
                "run_id": trace["run_id"],
                "expert_id": trace["expert_id"],
                "expert_version": trace["expert_version"],
                "environment": trace["environment"],
                "sdk_version": SDK_VERSION,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        "scheme": "v2",
        "d2": [record(root, root=True), *[record(item) for item in trace["spans"]]],
    }


class Span:
    def __init__(self, trace, name, kind="span", attributes=None):
        self.trace = trace
        self.item = {
            "span_id": os.urandom(8).hex(),
            "parent_span_id": _SPAN.get() or trace.root_span_id,
            "name": str(name)[:200],
            "kind": str(kind)[:80],
            "start_time_unix_nano": _now_ns(),
            "end_time_unix_nano": 0,
            "status": "ok",
            "error_type": None,
            "status_message": None,
            "attributes": _sanitize(attributes),
        }
        self.token = None

    def __enter__(self):
        self.token = _SPAN.set(self.item["span_id"])
        return self

    def set_attributes(self, **attributes):
        self.item["attributes"].update(_sanitize(attributes))

    def __exit__(self, exc_type, exc, _tb):
        self.item["end_time_unix_nano"] = _now_ns()
        if exc is not None:
            self.item.update(
                status="error",
                error_type=type(exc).__name__.upper()[:80],
                status_message=type(exc).__name__[:500],
            )
        self.trace.spans.append(self.item)
        if self.token is not None:
            _SPAN.reset(self.token)
        return False


class Trace:
    def __init__(self, observer, operation, run_id=None, session_id=None, attributes=None):
        self.observer = observer
        self.operation = str(operation)[:200]
        self.trace_id = os.urandom(16).hex()
        self.root_span_id = os.urandom(8).hex()
        self.run_id = str(run_id or uuid.uuid4())[:200]
        self.session_id_hash = _identifier(session_id, 32) if session_id else None
        self.attributes = _sanitize(attributes)
        self.start_time_unix_nano = _now_ns()
        self.end_time_unix_nano = 0
        self.status = "ok"
        self.error_type = None
        self.status_message = None
        self.spans = []
        self.trace_token = None
        self.span_token = None

    def __enter__(self):
        self.trace_token = _TRACE.set(self)
        self.span_token = _SPAN.set(self.root_span_id)
        return self

    def __exit__(self, exc_type, exc, _tb):
        self.end_time_unix_nano = _now_ns()
        if exc is not None:
            self.set_result(
                success=False,
                error_type=type(exc).__name__.upper(),
                status_message=type(exc).__name__,
            )
        if self.span_token is not None:
            _SPAN.reset(self.span_token)
        if self.trace_token is not None:
            _TRACE.reset(self.trace_token)
        self.observer.emit(self.as_dict())
        return False

    def span(self, name, kind="span", attributes=None):
        return Span(self, name, kind, attributes)

    def set_result(
        self, status="ok", error_type=None, status_message=None, attributes=None, success=None
    ):
        self.status = "ok" if success is not False and status != "error" else "error"
        self.error_type = str(error_type)[:80] if error_type else None
        self.status_message = str(status_message)[:500] if status_message else None
        self.attributes.update(_sanitize(attributes))

    def add_completed_span(self, name, duration_ms, kind="span", status="ok", error_type=None,
                           attributes=None):
        end = _now_ns()
        self.spans.append(
            {
                "span_id": os.urandom(8).hex(),
                "parent_span_id": self.root_span_id,
                "name": str(name)[:200],
                "kind": kind,
                "start_time_unix_nano": end - max(0, int(float(duration_ms) * 1_000_000)),
                "end_time_unix_nano": end,
                "status": status,
                "error_type": error_type,
                "status_message": None,
                "attributes": _sanitize(attributes),
            }
        )

    def as_dict(self):
        return {
            "trace_id": self.trace_id,
            "root_span_id": self.root_span_id,
            "run_id": self.run_id,
            "session_id_hash": self.session_id_hash,
            "expert_id": self.observer.expert_id,
            "expert_version": self.observer.expert_version,
            "environment": self.observer.environment,
            "operation": self.operation,
            "start_time_unix_nano": self.start_time_unix_nano,
            "end_time_unix_nano": self.end_time_unix_nano,
            "status": self.status,
            "error_type": self.error_type,
            "status_message": self.status_message,
            "attributes": self.attributes,
            "spans": self.spans,
        }


class Observer:
    def __init__(self, expert_id, expert_version, galileo_topic=None, environment=None,
                 spool_dir=None, timeout_ms=None, enabled=None, **_kwargs):
        self.expert_id = str(expert_id)[:120]
        self.expert_version = str(expert_version)[:80]
        self.galileo_topic = galileo_topic or os.environ.get("GALILEO_TOPIC", "")
        self.galileo_collect_url = os.environ.get("GALILEO_COLLECT_URL", GALILEO_COLLECT_URL)
        self.transport = os.environ.get("SSV_OBSERVE_TRANSPORT", "galileo_collect")
        self.environment = environment or os.environ.get("SSV_OBSERVE_ENVIRONMENT", "workbuddy")
        self.spool_dir = spool_dir or os.environ.get("SSV_OBSERVE_SPOOL_DIR", "")
        self.timeout_ms = int(timeout_ms or os.environ.get("SSV_OBSERVE_TIMEOUT_MS", "350"))
        self.enabled = (
            os.environ.get("SSV_OBSERVE_ENABLED", "true").lower() not in ("0", "false", "off")
            if enabled is None else bool(enabled)
        )
        self.verify_tls = os.environ.get("SSV_OBSERVE_VERIFY_TLS", "true").lower() not in (
            "0", "false", "off"
        )
        self.keep_local = os.environ.get("SSV_OBSERVE_KEEP_LOCAL", "false").lower() in (
            "1", "true", "on"
        )

    def trace(self, operation, run_id=None, session_id=None, trace_id=None, attributes=None):
        return Trace(self, operation, run_id, session_id, attributes)

    def emit(self, envelope):
        delivered = (
            self._post_galileo_collect(envelope)
            if self.enabled and self.transport == "galileo_collect"
            else False
        )
        if self.keep_local or not delivered:
            self._spool(envelope)

    def _post_galileo_collect(self, envelope):
        if not self.galileo_topic:
            return False
        try:
            body = json.dumps(
                build_collect_payload(envelope, self.galileo_topic),
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            request = urllib.request.Request(
                self.galileo_collect_url,
                data=body,
                headers={"content-type": "text/plain;charset=UTF-8"},
                method="POST",
            )
            context = None if self.verify_tls else ssl._create_unverified_context()
            with urllib.request.urlopen(
                request, timeout=max(0.05, self.timeout_ms / 1000.0), context=context
            ) as response:
                return 200 <= int(response.status) < 300 and json.loads(
                    response.read().decode("utf-8")
                ).get("code") == 0
        except (OSError, ValueError, urllib.error.URLError):
            return False

    def _spool(self, envelope):
        if not self.spool_dir:
            return
        try:
            directory = Path(self.spool_dir).expanduser()
            directory.mkdir(parents=True, exist_ok=True)
            with (directory / f"ssv-observe-{time.strftime('%Y%m%d')}.jsonl").open(
                "a", encoding="utf-8"
            ) as handle:
                handle.write(json.dumps(envelope, ensure_ascii=False) + "\n")
        except OSError:
            pass


class _NoopSpan:
    def __enter__(self):
        return self

    def set_attributes(self, **_attributes):
        return None

    def __exit__(self, *_args):
        return False


def current_trace():
    return _TRACE.get()


def observe_span(name, kind="span", attributes=None):
    trace = current_trace()
    return trace.span(name, kind, attributes) if trace is not None else _NoopSpan()


def record_stage_timings(trace, timings, prefix="stage", excluded=("total",)):
    for name, duration in timings.items():
        if name in set(excluded):
            continue
        try:
            trace.add_completed_span(
                f"{prefix}.{name}", float(duration), attributes={"timing_source": "summary"}
            )
        except (TypeError, ValueError):
            pass
