#!/usr/bin/env python3
"""Parse local documents with Alibaba Cloud DTS-AI and save Markdown results."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import time
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen
import uuid

_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import dts_api_key_configuration  # noqa: E402  (provided with this script)


ENDPOINT = "https://dtsai.cn-beijing.aliyuncs.com"
VERSION = "2026-04-01"
REGION = "cn-beijing"
OUTPUT_FORMAT = "markdown"
DEFAULT_OUTPUT_DIR = Path.home() / ".aliyun-dts" / "doc-parse"
JOBS_MANIFEST_NAME = "jobs.jsonl"
MANIFEST_SCHEMA_VERSION = 1
HEARTBEAT_SECONDS = 30.0
DEFAULT_POLL_INTERVAL_SECONDS = 5.0
DEFAULT_POLL_TIMEOUT_SECONDS = 300.0
HTTP_TIMEOUT_SECONDS = 120.0
TRANSIENT_HTTP_STATUSES = {408, 425, 429, 500, 502, 503, 504}
PARSER_JOB_STATUSES = frozenset(
    {"init", "pending", "running", "success", "failed", "cancelled"}
)
PARSER_JOB_IN_PROGRESS_STATUSES = frozenset({"init", "pending", "running"})
PARSER_JOB_SUCCESS_STATUS = "success"
PARSER_JOB_FAILED_STATUS = "failed"
PARSER_JOB_CANCELLED_STATUS = "cancelled"
SUPPORTED_FORMATS = {
    "docx",
    "jpeg",
    "jpg",
    "pdf",
    "png",
    "pptx",
}
CONTENT_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "pdf": "application/pdf",
    "png": "image/png",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
UPLOAD_FIELDS = (
    "AccessKeyId",
    "SecurityToken",
    "Bucket",
    "EncodedPolicy",
    "Endpoint",
    "ObjectKey",
    "Signature",
)


class DtsError(RuntimeError):
    """A validation, transport, protocol, or DTS-AI API error."""


class ValidationError(DtsError):
    """A local input, output, or environment prerequisite check failure."""


def _is_windows() -> bool:
    return os.name == "nt"


class JobTimeoutError(DtsError):
    """A parser job that can be resumed after the local polling timeout."""


_progress_to_stderr = False


def progress(message: str) -> None:
    """Print a progress step; --json redirects these lines to stderr."""
    stream = sys.stderr if _progress_to_stderr else sys.stdout
    print(message, file=stream, flush=True)


def run_setup(*, language: str = "en") -> None:
    """Open the system browser to configure DTS_AI_API_KEY locally."""
    try:
        dts_api_key_configuration.run_setup(language=language)
    except dts_api_key_configuration.SetupError as exc:
        raise ValidationError(str(exc)) from exc


def require_api_key() -> str:
    try:
        api_key = dts_api_key_configuration.resolve_api_key()
    except dts_api_key_configuration.CredentialError as exc:
        raise ValidationError(str(exc)) from exc
    if not api_key:
        raise ValidationError(
            "DTS_AI_API_KEY is not configured. Run 'setup' to open the local browser, "
            "or set it in the current environment and retry."
        )
    return api_key


def parse_json_object(raw: bytes, context: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DtsError(f"{context} returned invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise DtsError(f"{context} returned a non-object JSON response")
    return value


def integer_or_zero(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def api_error_message(action: str, response: dict[str, Any], http_status: int) -> str:
    code = response.get("ErrorCode") or response.get("Code") or "UnknownApiError"
    message = response.get("ErrorMessage") or response.get("Message") or "no details"
    request_id = response.get("RequestId") or "unknown"
    api_status = integer_or_zero(response.get("HttpStatusCode"))
    status_details = f"HTTP {http_status or 'unknown'}"
    if api_status and api_status != http_status:
        status_details += f", API HttpStatusCode={api_status}"
    return (
        f"{action} failed: {code}: {message} "
        f"({status_details}, RequestId={request_id})"
    )


def call_api(
    action: str,
    payload: dict[str, Any],
    api_key: str,
    *,
    retries: int = 0,
) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    last_error = "unknown error"

    for attempt in range(retries + 1):
        nonce = str(uuid.uuid4())
        url = f"{ENDPOINT}?Action={action}&Version={VERSION}&SignatureNonce={nonce}"
        request = Request(
            url,
            data=body,
            headers={
                "X-Acs-ApiKey": api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        raw = b""
        http_status = 0
        transport_error: Optional[BaseException] = None

        try:
            with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as reply:
                http_status = reply.getcode()
                raw = reply.read()
        except HTTPError as exc:
            http_status = exc.code
            raw = exc.read()
        except (URLError, TimeoutError, OSError) as exc:
            transport_error = exc

        if transport_error is not None:
            last_error = f"{action} transport error: {transport_error}"
            transient = True
        else:
            try:
                response = parse_json_object(raw, action)
            except DtsError as exc:
                last_error = str(exc)
                transient = http_status in TRANSIENT_HTTP_STATUSES
            else:
                api_status = integer_or_zero(response.get("HttpStatusCode"))
                if (
                    http_status == 200
                    and response.get("Success") is True
                    and api_status == 200
                ):
                    return response
                last_error = api_error_message(action, response, http_status)
                transient = (
                    http_status in TRANSIENT_HTTP_STATUSES
                    or api_status in TRANSIENT_HTTP_STATUSES
                )

        if not transient or attempt == retries:
            raise DtsError(last_error)
        time.sleep(1.0 + attempt)

    raise DtsError(last_error)


def validate_input(path_value: str) -> tuple[Path, str]:
    path = Path(path_value).expanduser().resolve()
    if not path.is_file():
        raise ValidationError(f"Input is not a readable regular file: {path}")
    if not os.access(path, os.R_OK):
        raise ValidationError(f"Input is not readable: {path}")
    if path.stat().st_size <= 0:
        raise ValidationError(f"Input file is empty: {path}")
    file_format = path.suffix.lower().lstrip(".")
    if file_format not in SUPPORTED_FORMATS:
        supported = ", ".join(sorted(SUPPORTED_FORMATS))
        raise ValidationError(f"Unsupported input format '{file_format}'. Supported: {supported}")
    return path, file_format


def _ensure_default_output_dir() -> None:
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def default_output_path(input_path: Path) -> Path:
    return DEFAULT_OUTPUT_DIR / f"{input_path.name}.md"


def default_collision_output_path(input_path: Path, sha256: str) -> Path:
    return DEFAULT_OUTPUT_DIR / f"{input_path.name}-{sha256[:8]}.md"


def validate_output(
    path_value: str,
    input_path: Optional[Path],
    force: bool,
    derived_default: bool = False,
) -> Path:
    path = Path(path_value).expanduser().resolve()
    if input_path is not None and path == input_path:
        raise ValidationError("Output path must differ from the input path")
    if not path.parent.is_dir():
        if path.parent == DEFAULT_OUTPUT_DIR:
            _ensure_default_output_dir()
        else:
            raise ValidationError(f"Output directory does not exist: {path.parent}")
    if path.exists() and not force:
        if derived_default:
            raise ValidationError(
                f"Default output already exists: {path}. If this is a different "
                "input, pass --output with a distinct path; pass --force only to "
                "replace the existing result."
            )
        raise ValidationError(f"Output already exists; pass --force to replace it: {path}")
    return path


def resolve_parse_output(
    input_path: Path,
    sha256: str,
    output_value: Optional[str],
    force: bool,
) -> Path:
    """Resolve a stable output path without silently replacing existing content."""
    if output_value is not None:
        return validate_output(output_value, input_path, force)

    preferred = default_output_path(input_path)
    if force or not preferred.exists():
        return validate_output(
            str(preferred), input_path, force, derived_default=True
        )

    fallback = default_collision_output_path(input_path, sha256)
    return validate_output(
        str(fallback), input_path, False, derived_default=True
    )


def _manifest_path() -> Path:
    return DEFAULT_OUTPUT_DIR / JOBS_MANIFEST_NAME


def _manifest_object_without_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate manifest field")
        value[key] = item
    return value


def _decode_manifest_entry(line: str) -> Optional[dict[str, Any]]:
    try:
        entry = json.loads(
            line,
            object_pairs_hook=_manifest_object_without_duplicate_keys,
        )
    except (json.JSONDecodeError, ValueError):
        return None
    required = {
        "schema_version",
        "time",
        "event",
        "job_id",
        "input",
        "output",
    }
    if (
        not isinstance(entry, dict)
        or set(entry) not in (required, required | {"sha256"})
        or type(entry.get("schema_version")) is not int
        or entry["schema_version"] != MANIFEST_SCHEMA_VERSION
        or entry.get("event") not in {"created", "saved"}
        or not isinstance(entry.get("time"), str)
        or not entry["time"]
        or not isinstance(entry.get("job_id"), str)
        or not entry["job_id"]
        or not isinstance(entry.get("input"), str)
        or not isinstance(entry.get("output"), str)
        or not entry["output"]
    ):
        return None
    sha256 = entry.get("sha256")
    if sha256 is not None and (
        not isinstance(sha256, str)
        or not re.fullmatch(r"[0-9a-f]{64}", sha256)
    ):
        return None
    return entry


def record_job_event(
    event: str,
    job_id: str,
    output_path: Path,
    input_name: str = "",
    sha256: str = "",
) -> None:
    """Append one recovery record that contains no secrets.

    A failure to write the record does not terminate the parser job.
    """
    entry = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event": event,
        "job_id": job_id,
        "input": input_name,
        "output": str(output_path),
    }
    if sha256:
        entry["sha256"] = sha256
    try:
        _ensure_default_output_dir()
        with _manifest_path().open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as exc:
        print(f"warning: could not write recovery record: {exc}", file=sys.stderr)


def lookup_job_output(job_id: str) -> Optional[Path]:
    """Return the most recently recorded output path for a JobId, if any."""
    try:
        lines = _manifest_path().read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    recorded: Optional[str] = None
    for line in lines:
        entry = _decode_manifest_entry(line)
        if entry is None:
            continue
        if entry.get("job_id") == job_id and entry.get("output"):
            recorded = str(entry["output"])
    return Path(recorded) if recorded else None


def input_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_saved_duplicate_record(sha256: str) -> Optional[tuple[str, Path]]:
    """Return the latest usable saved job whose input content was identical."""
    try:
        lines = _manifest_path().read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    created: dict[str, str] = {}
    candidates: list[tuple[str, Path]] = []
    for line in lines:
        entry = _decode_manifest_entry(line)
        if entry is None:
            continue
        job_id = str(entry.get("job_id"))
        if entry.get("event") == "created" and entry.get("sha256"):
            created[job_id] = str(entry["sha256"])
        elif (
            entry.get("event") == "saved"
            and created.get(job_id) == sha256
            and entry.get("output")
        ):
            candidates.append((job_id, Path(str(entry["output"]))))
    for candidate in reversed(candidates):
        if candidate[1].is_file():
            return candidate
    return None


def find_saved_duplicate(sha256: str) -> Optional[Path]:
    """Return the saved output of a completed job whose input content was identical."""
    record = find_saved_duplicate_record(sha256)
    return record[1] if record is not None else None


def saved_result_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError as exc:
        raise ValidationError(f"Saved Markdown result cannot be reused: {path}: {exc}") from exc


def summarize_jobs() -> list[dict[str, str]]:
    """Combine recovery records into one record per job, ordered from oldest."""
    try:
        lines = _manifest_path().read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    jobs: dict[str, dict[str, str]] = {}
    order: list[str] = []
    for line in lines:
        entry = _decode_manifest_entry(line)
        if entry is None:
            continue
        job_id = str(entry["job_id"])
        record = jobs.get(job_id)
        if record is None:
            record = {
                "job_id": job_id,
                "state": "pending",
                "input": "",
                "output": "",
                "time": "",
            }
            jobs[job_id] = record
            order.append(job_id)
        if entry.get("event") == "created" and entry.get("input"):
            record["input"] = str(entry["input"])
        if entry.get("event") == "saved":
            record["state"] = "saved"
        if entry.get("output"):
            record["output"] = str(entry["output"])
        if entry.get("time"):
            record["time"] = str(entry["time"])
    return [jobs[job_id] for job_id in order]


def require_fields(response: dict[str, Any], fields: tuple[str, ...], context: str) -> None:
    missing = [field for field in fields if not str(response.get(field) or "").strip()]
    if missing:
        raise DtsError(f"{context} response is missing required fields: {', '.join(missing)}")


def normalize_endpoint_host(endpoint: str) -> str:
    candidate = endpoint.strip()
    parsed = urlsplit(candidate if "://" in candidate else f"//{candidate}")
    if parsed.scheme and parsed.scheme != "https":
        raise DtsError(f"Unsupported OSS endpoint scheme: {parsed.scheme}")
    if parsed.username or parsed.password or not parsed.hostname:
        raise DtsError("AuthorizeFileUpload returned an invalid OSS endpoint")
    host = parsed.hostname
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return host


def disposition_value(value: str, field_name: str) -> str:
    if "\r" in value or "\n" in value:
        raise DtsError(f"Invalid newline in multipart {field_name}")
    return value.replace("\\", "\\\\").replace('"', '\\"')


def multipart_field(boundary: str, name: str, value: str) -> bytes:
    safe_name = disposition_value(name, "name")
    return (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{safe_name}"\r\n\r\n'
        f"{value}\r\n"
    ).encode("utf-8")


def upload_file(auth: dict[str, Any], input_path: Path, file_format: str) -> str:
    require_fields(auth, UPLOAD_FIELDS, "AuthorizeFileUpload")
    endpoint_host = normalize_endpoint_host(str(auth["Endpoint"]))
    bucket = disposition_value(str(auth["Bucket"]), "bucket")
    if any(char in bucket for char in "/?#@"):
        raise DtsError("AuthorizeFileUpload returned an invalid OSS bucket")
    object_key = str(auth["ObjectKey"])
    boundary = f"----dts-doc-parse-{uuid.uuid4().hex}"

    fields = (
        ("key", object_key),
        ("OSSAccessKeyId", str(auth["AccessKeyId"])),
        ("x-oss-security-token", str(auth["SecurityToken"])),
        ("policy", str(auth["EncodedPolicy"])),
        ("Signature", str(auth["Signature"])),
        ("success_action_status", "201"),
    )
    prefix = b"".join(multipart_field(boundary, name, value) for name, value in fields)
    safe_filename = disposition_value(object_key, "filename")
    content_type = CONTENT_TYPES[file_format]
    prefix += (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{safe_filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8")
    suffix = f"\r\n--{boundary}--\r\n".encode("ascii")
    content_length = len(prefix) + input_path.stat().st_size + len(suffix)
    upload_host = f"{bucket}.{endpoint_host}"

    connection = http.client.HTTPSConnection(upload_host, timeout=HTTP_TIMEOUT_SECONDS)
    try:
        connection.putrequest("POST", "/")
        connection.putheader("Content-Type", f"multipart/form-data; boundary={boundary}")
        connection.putheader("Content-Length", str(content_length))
        connection.putheader("Connection", "close")
        connection.endheaders()
        connection.send(prefix)
        with input_path.open("rb") as source:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                connection.send(chunk)
        connection.send(suffix)
        reply = connection.getresponse()
        response_body = reply.read()
        status = reply.status
    except (OSError, http.client.HTTPException) as exc:
        raise DtsError(f"OSS PostObject transport error: {exc}") from exc
    finally:
        connection.close()

    if status not in {200, 201, 204}:
        details = response_body.decode("utf-8", errors="replace").strip()[:1000]
        raise DtsError(
            f"OSS PostObject failed: HTTP {status}"
            + (f", response={details}" if details else "")
        )

    encoded_key = quote(object_key, safe="/-._~")
    return f"https://{upload_host}/{encoded_key}"


def authorize_upload(api_key: str) -> dict[str, Any]:
    response = call_api("AuthorizeFileUpload", {"RegionId": REGION}, api_key)
    require_fields(response, UPLOAD_FIELDS, "AuthorizeFileUpload")
    return response


def create_parser_job(
    api_key: str,
    oss_file_url: str,
    input_path: Path,
    file_format: str,
) -> str:
    response = call_api(
        "CreateDocParserJob",
        {
            "RegionId": REGION,
            "OssFileUrl": oss_file_url,
            "FileName": input_path.name,
            "FileFormat": file_format,
            "OutputFormat": OUTPUT_FORMAT,
        },
        api_key,
    )
    job_id = str(response.get("JobId") or "").strip()
    if not job_id:
        raise DtsError("CreateDocParserJob response is missing JobId")
    return job_id


def poll_job(
    api_key: str,
    job_id: str,
    timeout_seconds: float,
    interval_seconds: float,
    status_step: str = "4/5",
) -> None:
    start = time.monotonic()
    deadline = start + timeout_seconds
    last_status = ""
    last_report = start

    while True:
        response = call_api(
            "DescribeDocParserJobStatus",
            {"RegionId": REGION, "JobId": job_id},
            api_key,
            retries=2,
        )
        raw_job_status = str(response.get("Status") or "").strip()
        if not raw_job_status:
            raise DtsError("DescribeDocParserJobStatus response is missing Status")
        if raw_job_status not in PARSER_JOB_STATUSES:
            raise DtsError(
                f"Parser job returned unknown status '{raw_job_status}' (JobId={job_id})"
            )
        now = time.monotonic()
        if raw_job_status != last_status:
            progress(f"[{status_step}] Job status: {raw_job_status}")
            last_status = raw_job_status
            last_report = now
        elif now - last_report >= HEARTBEAT_SECONDS:
            progress(
                f"[{status_step}] Job status: {raw_job_status} "
                f"(elapsed {int(now - start)}s)"
            )
            last_report = now
        if raw_job_status == PARSER_JOB_SUCCESS_STATUS:
            return
        if raw_job_status == PARSER_JOB_FAILED_STATUS:
            failure_message = str(response.get("FailureMessage") or "no details")
            raise DtsError(
                f"Parser job {raw_job_status}: {failure_message} (JobId={job_id})"
            )
        if raw_job_status == PARSER_JOB_CANCELLED_STATUS:
            raise DtsError(
                f"Parser job {raw_job_status} (JobId={job_id})"
            )
        if raw_job_status not in PARSER_JOB_IN_PROGRESS_STATUSES:
            raise AssertionError(f"Unhandled parser job status: {raw_job_status}")

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise JobTimeoutError(
                f"Parser job did not finish within {timeout_seconds:g}s (JobId={job_id})"
            )
        time.sleep(min(interval_seconds, remaining))


def fetch_result(api_key: str, job_id: str) -> str:
    response = call_api(
        "DescribeDocParserJobResult",
        {"RegionId": REGION, "JobId": job_id},
        api_key,
        retries=2,
    )
    result = response.get("Result")
    if not isinstance(result, str) or not result:
        raise DtsError("DescribeDocParserJobResult response contains an empty Result")
    return result


def write_result_atomic(output_path: Path, result: str, force: bool) -> int:
    if output_path.exists() and not force:
        raise DtsError(f"Output already exists; pass --force to replace it: {output_path}")
    data = result.encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.", suffix=".tmp", dir=str(output_path.parent)
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        if output_path.exists() and not force:
            raise DtsError(f"Output already exists; pass --force to replace it: {output_path}")
        os.replace(temporary_path, output_path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
    return len(data)


def resume_command(job_id: str, output_path: Path, force: bool) -> str:
    arguments = [
        sys.executable,
        str(Path(__file__).resolve()),
        "resume",
        job_id,
        "--output",
        str(output_path),
    ]
    if force:
        arguments.append("--force")
    if _is_windows():
        return subprocess.list2cmdline(arguments)
    return shlex.join(arguments)


def finish_job(
    api_key: str,
    job_id: str,
    output_path: Path,
    force: bool,
    timeout_seconds: float,
    interval_seconds: float,
    status_step: str = "4/5",
    save_step: str = "5/5",
) -> int:
    try:
        poll_job(api_key, job_id, timeout_seconds, interval_seconds, status_step)
        try:
            result = fetch_result(api_key, job_id)
            byte_count = write_result_atomic(output_path, result, force)
        except DtsError:
            print(
                f"Result not saved; resume with: {resume_command(job_id, output_path, force)}",
                file=sys.stderr,
            )
            raise
    except KeyboardInterrupt:
        print(f"\nInterrupted. Resume with: {resume_command(job_id, output_path, force)}", file=sys.stderr)
        raise
    except JobTimeoutError as exc:
        print(f"Resume with: {resume_command(job_id, output_path, force)}", file=sys.stderr)
        raise exc
    progress(f"[{save_step}] Markdown saved: {output_path} ({byte_count} bytes)")
    record_job_event("saved", job_id, output_path)
    return byte_count


def positive_number(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def add_poll_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--poll-timeout",
        type=positive_number,
        default=DEFAULT_POLL_TIMEOUT_SECONDS,
        help=f"polling timeout in seconds (default: {DEFAULT_POLL_TIMEOUT_SECONDS:g})",
    )
    parser.add_argument(
        "--poll-interval",
        type=positive_number,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        help=f"polling interval in seconds (default: {DEFAULT_POLL_INTERVAL_SECONDS:g})",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse a local document into Markdown with Alibaba Cloud DTS-AI."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("check", help="check required environment configuration")

    setup_parser = subparsers.add_parser(
        "setup",
        help="open the system browser to configure DTS_AI_API_KEY locally",
    )
    setup_parser.add_argument(
        "--language",
        choices=dts_api_key_configuration.SUPPORTED_LANGUAGES,
        default="en",
        help="local browser page language (default: en)",
    )

    jobs_parser = subparsers.add_parser(
        "jobs", help="list recorded parser jobs and their local state (offline)"
    )
    jobs_parser.add_argument(
        "--json", action="store_true", help="print the job records as JSON"
    )

    parse_parser = subparsers.add_parser("parse", help="parse a local file to Markdown with DTS-AI")
    parse_parser.add_argument("input", help="local input file")
    parse_parser.add_argument(
        "--output",
        help=(
            "Markdown output path (default: "
            "~/.aliyun-dts/doc-parse/<input-name>.md; a short content hash is "
            "added if that path is occupied)"
        ),
    )
    parse_parser.add_argument(
        "--json",
        action="store_true",
        help="print progress to stderr and one final JSON result to stdout",
    )
    parse_parser.add_argument("--force", action="store_true", help="replace an existing output file")
    add_poll_options(parse_parser)

    resume_parser = subparsers.add_parser("resume", help="resume polling an existing parser job")
    resume_parser.add_argument("job_id", help="DTS-AI parser JobId")
    resume_parser.add_argument(
        "--output",
        help="Markdown output path (default: the recorded path for this JobId)",
    )
    resume_parser.add_argument(
        "--json",
        action="store_true",
        help="print progress to stderr and one final JSON result to stdout",
    )
    resume_parser.add_argument("--force", action="store_true", help="replace an existing output file")
    add_poll_options(resume_parser)
    return parser


def run(args: argparse.Namespace) -> None:
    global _progress_to_stderr
    if getattr(args, "json", False):
        _progress_to_stderr = True

    if args.command == "check":
        require_api_key()
        print("DTS-AI API key configuration check passed.")
        return

    if args.command == "setup":
        run_setup(language=args.language)
        return

    if args.command == "jobs":
        records = summarize_jobs()
        if getattr(args, "json", False):
            print(json.dumps(records, ensure_ascii=False, indent=2))
        elif not records:
            print("No recorded parser jobs.")
        else:
            for record in records:
                print(
                    f"{record['state'].upper()}\t{record['job_id']}\t"
                    f"{record['input']}\t{record['output']}"
                )
        return

    if args.command == "parse":
        input_path, file_format = validate_input(args.input)
        digest = input_sha256(input_path)
        duplicate = find_saved_duplicate_record(digest)
        if duplicate is not None and not args.force:
            job_id, saved_output = duplicate
            if args.output is None:
                output_path = saved_output
                byte_count = saved_result_size(saved_output)
                progress(f"Identical input content already parsed; reusing: {output_path}")
            else:
                requested_output = Path(args.output).expanduser().resolve()
                if requested_output == saved_output.resolve():
                    output_path = saved_output
                    byte_count = saved_result_size(saved_output)
                    progress(
                        f"Identical input content already parsed; reusing: {output_path}"
                    )
                else:
                    output_path = validate_output(
                        args.output, input_path, force=False
                    )
                    try:
                        result = saved_output.read_text(encoding="utf-8")
                    except (OSError, UnicodeError) as exc:
                        raise ValidationError(
                            f"Saved Markdown result cannot be reused: {saved_output}: {exc}"
                        ) from exc
                    byte_count = write_result_atomic(output_path, result, force=False)
                    record_job_event("saved", job_id, output_path)
                    progress(
                        "Identical input content already parsed; copied saved Markdown "
                        f"to: {output_path}"
                    )
            if getattr(args, "json", False):
                print(
                    json.dumps(
                        {
                            "status": "success",
                            "job_id": job_id,
                            "output": str(output_path),
                            "bytes": byte_count,
                        },
                        ensure_ascii=False,
                    )
                )
            return

        output_path = resolve_parse_output(
            input_path, digest, args.output, args.force
        )
        api_key = require_api_key()
        progress("[1/5] Requesting temporary OSS upload authorization")
        authorization = authorize_upload(api_key)
        progress("[2/5] Uploading input with OSS PostObject")
        oss_file_url = upload_file(authorization, input_path, file_format)
        job_id = create_parser_job(api_key, oss_file_url, input_path, file_format)
        progress(f"[3/5] Parser job created: JobId={job_id}")
        record_job_event("created", job_id, output_path, input_path.name, digest)
        status_step, save_step = "4/5", "5/5"
    else:
        job_id = args.job_id.strip()
        if not job_id:
            raise ValidationError("JobId must not be empty")
        output_value = args.output
        if not output_value:
            recorded = lookup_job_output(job_id)
            if recorded is None:
                raise ValidationError(
                    f"No recorded output path for JobId {job_id}; pass --output"
                )
            output_value = str(recorded)
        output_path = validate_output(output_value, None, args.force)
        api_key = require_api_key()
        progress(f"[1/3] Resuming parser job: JobId={job_id}")
        status_step, save_step = "2/3", "3/3"

    byte_count = finish_job(
        api_key,
        job_id,
        output_path,
        args.force,
        args.poll_timeout,
        args.poll_interval,
        status_step,
        save_step,
    )
    if getattr(args, "json", False):
        print(
            json.dumps(
                {
                    "status": "success",
                    "job_id": job_id,
                    "output": str(output_path),
                    "bytes": byte_count,
                },
                ensure_ascii=False,
            )
        )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        run(args)
    except KeyboardInterrupt:
        return 130
    except JobTimeoutError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4
    except ValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except DtsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
