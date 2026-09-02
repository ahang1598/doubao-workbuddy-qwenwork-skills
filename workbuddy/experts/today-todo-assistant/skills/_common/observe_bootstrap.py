"""可观测埋点引导层（专家通用版）。

埋点是非关键路径：优先复用专家隔离运行时中的 `ssv-agent-obser-sdk`；
首次缺失时自动安装，安装失败则回退到随专家包分发的兼容 SDK，绝不能让业务流程失败。

SDK 只依赖标准库，安装见同目录 requirements.txt（需指定腾讯内网 index）。
上报 topic 见 DEFAULT_GALILEO_TOPIC，可由环境变量或本地配置覆盖。

本文件随专家包放在 skills/_common/ 下，与 mcp_client.py 同级：独立运行时用本专家
的 _common，被合并进专家团后脚本的 sys.path 会重定向到专家团的 _common，从而自动
按专家团的配置（expert_id / 版本号 / runtime 目录）上报。
"""

import contextlib
import io
import json
import os
import shutil
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))

# 伽利略观测对象 gy-wb-expert 的上报 topic。
# 这是只写凭据——只能投递、不能查询，所以随专家包分发到客户端是可接受的；
# 专家运行在用户机器上，不会有本地配置文件，不内置就等于永远不上报。
DEFAULT_GALILEO_TOPIC = "SDK-f00cdec417fe8ce186a2"
DEFAULT_GALILEO_ENVIRONMENT = "production"
DEFAULT_GALILEO_PLATFORM = "Electron"

_CONFIG_PATH = "~/.workbuddy/ssv-agent-obser.json"
_SDK_RUNTIME_BUNDLE_VERSION = "ssv-agent-obser-sdk-0.3.0"
_SDK_PACKAGE = "ssv-agent-obser-sdk==0.3.0"
_SDK_INDEX_URL = os.environ.get(
    "SSV_OBSERVE_INDEX_URL",
    "https://mirrors.tencent.com/repository/pypi/tencent_pypi/simple",
)


def _is_test_process():
    return bool(os.environ.get("PYTEST_CURRENT_TEST")) or "unittest" in sys.modules


def _plugin_dir():
    """向上定位含 .codebuddy-plugin/plugin.json 的专家包根目录；找不到返回 None。"""
    directory = _HERE
    for _ in range(8):
        candidate = os.path.join(directory, ".codebuddy-plugin", "plugin.json")
        if os.path.exists(candidate):
            return directory
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent
    return None


def _runtime_root():
    configured = (os.environ.get("SSV_OBSERVE_RUNTIME_DIR") or "").strip()
    if configured:
        return Path(configured).expanduser()
    pkg = _plugin_dir()
    name = os.path.basename(pkg) if pkg else "workbuddy-expert"
    return Path.home() / ".workbuddy" / "runtimes" / name / _SDK_RUNTIME_BUNDLE_VERSION


def _load_external_sdk():
    try:
        from ssv_agent_obser import Observer, observe_span
        from ssv_agent_obser.sdk import build_collect_payload, record_stage_timings

        return Observer, observe_span, build_collect_payload, record_stage_timings
    except Exception:  # noqa: BLE001
        return None


def _activate_managed_runtime():
    """激活专家专属 site-packages，不改写 WorkBuddy 的共享 Python。"""
    try:
        marker = _runtime_root() / "active.json"
        payload = json.loads(marker.read_text(encoding="utf-8"))
        site_packages = Path(str(payload.get("site_packages") or ""))
        if not site_packages.is_dir():
            return False
        site_path = str(site_packages)
        if site_path not in sys.path:
            sys.path.insert(0, site_path)
        return True
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def _install_managed_runtime():
    """首次将 SDK 安装到专家私有目录；失败后由包内 SDK 继续提供观测能力。"""
    if _is_test_process() or os.environ.get("SSV_OBSERVE_AUTO_INSTALL") == "0":
        return False

    root = _runtime_root()
    try:
        root.mkdir(parents=True, exist_ok=True)
        lock_file = (root / "install.lock").open("a+", encoding="utf-8")
    except OSError:
        return False
    try:
        try:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        except (ImportError, OSError):
            pass

        if _activate_managed_runtime() and _load_external_sdk():
            return True

        staging = root / f"site-packages-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            "--quiet",
            "--no-deps",
            "--index-url",
            _SDK_INDEX_URL,
            "--target",
            str(staging),
            _SDK_PACKAGE,
        ]
        try:
            installed = subprocess.run(
                command, capture_output=True, text=True, timeout=120, check=False
            )
        except (OSError, subprocess.SubprocessError):
            return False
        if installed.returncode != 0:
            shutil.rmtree(staging, ignore_errors=True)
            return False

        env = os.environ.copy()
        env["PYTHONPATH"] = str(staging) + (
            os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
        )
        try:
            verified = subprocess.run(
                [sys.executable, "-c", "from ssv_agent_obser import Observer"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                env=env,
            )
        except (OSError, subprocess.SubprocessError):
            verified = None
        if verified is None or verified.returncode != 0:
            shutil.rmtree(staging, ignore_errors=True)
            return False

        marker_tmp = root / f"active.{os.getpid()}.tmp"
        marker_tmp.write_text(
            json.dumps(
                {
                    "bundle": _SDK_RUNTIME_BUNDLE_VERSION,
                    "site_packages": str(staging),
                    "python": sys.executable,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        os.replace(marker_tmp, root / "active.json")
        return _activate_managed_runtime() and bool(_load_external_sdk())
    except OSError:
        return False
    finally:
        try:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        except (ImportError, OSError):
            pass
        lock_file.close()


_sdk = _load_external_sdk()
SDK_SOURCE = "preinstalled"
if _sdk is None and _activate_managed_runtime():
    _sdk = _load_external_sdk()
    SDK_SOURCE = "managed"
if _sdk is None and _install_managed_runtime():
    _sdk = _load_external_sdk()
    SDK_SOURCE = "managed"
if _sdk is not None:
    Observer, observe_span, build_collect_payload, record_stage_timings = _sdk
    SDK_AVAILABLE = True
else:
    try:
        from vendor_observer import (
            Observer,
            build_collect_payload,
            observe_span,
            record_stage_timings,
        )

        SDK_AVAILABLE = True
        SDK_SOURCE = "bundled"
    except Exception:  # noqa: BLE001
        SDK_AVAILABLE = False
        SDK_SOURCE = "unavailable"

if not SDK_AVAILABLE:
    class _NoopTrace:
        def set_result(self, **kwargs):
            return None

        def add_timing(self, *args, **kwargs):
            return None

        def add_event(self, *args, **kwargs):
            return None

    class _NoopSpan:
        def __enter__(self):
            return _NoopTrace()

        def __exit__(self, *exc_info):
            return False

    class Observer:
        def __init__(self, *args, **kwargs):
            pass

        def trace(self, *args, **kwargs):
            return _NoopSpan()

    def observe_span(*args, **kwargs):
        return _NoopSpan()

    def record_stage_timings(*args, **kwargs):
        return None


def expert_version(default="unknown"):
    """从最近的 .codebuddy-plugin/plugin.json 读版本号，避免埋点里硬编码版本。"""
    pkg = _plugin_dir()
    if pkg:
        candidate = os.path.join(pkg, ".codebuddy-plugin", "plugin.json")
        try:
            with open(candidate, encoding="utf-8") as fh:
                return str(json.load(fh).get("version") or default)
        except Exception:  # noqa: BLE001
            return default
    return default


def galileo_topic():
    """解析上报 topic：环境变量 > 本地配置文件 > 包内默认值。

    SDK 自己也读前两个来源，但构造参数优先级最高；这里必须按同样顺序先解析一遍，
    否则把默认值直接传进去会把用户的本地覆盖顶掉。
    """
    from_env = (os.environ.get("GALILEO_TOPIC") or "").strip()
    if from_env:
        return from_env
    # 单测会直接调 main()，不加这道拦截每跑一次测试就往生产观测对象打一批数据。
    if _is_test_process():
        return ""
    path = os.path.expanduser(os.environ.get("SSV_OBSERVE_CONFIG") or _CONFIG_PATH)
    try:
        with open(path, encoding="utf-8") as fh:
            configured = str(json.load(fh).get("galileo_topic") or "").strip()
        if configured:
            return configured
    except Exception:  # noqa: BLE001
        pass
    return DEFAULT_GALILEO_TOPIC


def _add_galileo_correlation_fields(payload):
    """补齐 Galileo 日志详情页识别的驼峰 Trace/Span 字段，并把错误信息并入 msg。

    Galileo 列表页直接展示 message（对应 payload 里的 msg 字段），而 msg 由 SDK 固定
    生成为 `expert_id + span_name`（只标识"哪个专家的哪个操作"），错误详情只落在
    status_message 这个 tag 里，列表页看不到。这里把非空的 status_message 追加到 msg
    末尾让列表页一眼可见，同时清空 status_message，避免同一份错误描述在两个字段重复。
    机器可读的错误码仍由 error_type 单独承载，不受影响。status_message 已脱敏，无额外
    隐私风险。
    """
    for record in payload.get("d2") or []:
        messages = record.get("message")
        if not isinstance(messages, list):
            continue
        for index, encoded in enumerate(messages):
            try:
                message = json.loads(encoded)
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if not isinstance(message, dict):
                continue
            message["traceID"] = message.get("trace_id") or ""
            message["spanID"] = message.get("span_id") or ""
            message["parentSpanID"] = message.get("parent_span_id") or ""
            status_message = message.get("status_message")
            if status_message:
                message["msg"] = f"{message.get('msg', '')} | {status_message}"
                message["status_message"] = ""
            messages[index] = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
    return payload


class GalileoObserver(Observer):
    """将 WorkBuddy 专家的日志路由到 Galileo 的指定环境与平台。"""

    def __init__(self, *args, galileo_platform=DEFAULT_GALILEO_PLATFORM, **kwargs):
        super().__init__(*args, **kwargs)
        self.galileo_platform = str(galileo_platform or DEFAULT_GALILEO_PLATFORM).strip()

    def _post_galileo_collect(self, envelope):
        """复用 SDK 的事件结构，仅覆盖专家在 Galileo 中的路由平台。"""
        if not SDK_AVAILABLE or not self.galileo_topic:
            return False
        try:
            payload = build_collect_payload(envelope, self.galileo_topic)
            payload["bean"]["platform"] = self.galileo_platform
            _add_galileo_correlation_fields(payload)
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            request = urllib.request.Request(
                self.galileo_collect_url,
                data=body,
                headers={
                    "content-type": "text/plain;charset=UTF-8",
                    "User-Agent": "ssv-agent-obser/galileo-route",
                },
                method="POST",
            )
            context = None if self.verify_tls else ssl._create_unverified_context()
            with urllib.request.urlopen(
                request, timeout=max(0.05, self.timeout_ms / 1000.0), context=context
            ) as response:
                if not 200 <= int(response.status) < 300:
                    return False
                result = json.loads(response.read().decode("utf-8"))
            return isinstance(result, dict) and result.get("code") == 0
        except (OSError, ValueError, urllib.error.URLError):
            return False


def galileo_observer(*args, **kwargs):
    """构造默认投递到正式环境 Electron 目标的 Galileo 观察器。

    SDK 的本地配置可指定 transport，且该配置优先于自动选路；若不显式处理，
    即使专家传入了 Galileo topic，也可能被重定向到其它通道。仅当调用方通过
    环境变量明确指定 transport 时才保留该覆盖，其余情况固定使用 Galileo。
    """
    configured_transport = os.environ.get("SSV_OBSERVE_TRANSPORT")
    selected_transport = (configured_transport or "").strip().lower()
    if selected_transport and selected_transport != "galileo_collect":
        return Observer(*args, **kwargs)

    kwargs.setdefault(
        "environment",
        (os.environ.get("SSV_OBSERVE_ENVIRONMENT") or DEFAULT_GALILEO_ENVIRONMENT).strip(),
    )
    kwargs.setdefault(
        "galileo_platform",
        (os.environ.get("GALILEO_PLATFORM") or DEFAULT_GALILEO_PLATFORM).strip(),
    )
    if not selected_transport:
        os.environ["SSV_OBSERVE_TRANSPORT"] = "galileo_collect"
    try:
        return GalileoObserver(*args, **kwargs)
    finally:
        if not selected_transport:
            if configured_transport is None:
                os.environ.pop("SSV_OBSERVE_TRANSPORT", None)
            else:
                os.environ["SSV_OBSERVE_TRANSPORT"] = configured_transport


def extract_error_info(output):
    """从脚本 stdout 的失败 JSON 中提取 (error_type, status_message)。

    入口脚本的失败 JSON 统一为：
        {"success": false, "error_code": "<码>", "message": "<描述>", "need_refresh": <bool>}
    - error_type：取 error_code（机器可读错误码），便于告警聚合与分类；
    - status_message：取 message（人类可读描述）。
    """
    if not output:
        return None, None
    lines = [ln for ln in output.strip().splitlines() if ln.strip()]
    if not lines:
        return None, None
    last = lines[-1].strip()
    try:
        data = json.loads(last)
    except (ValueError, TypeError):
        return "SCRIPT_FAILED", last[:500]
    if not isinstance(data, dict):
        return "SCRIPT_FAILED", str(data)[:500]

    error_type = data.get("error_code")
    if error_type:
        error_type = str(error_type)[:80]
    message = data.get("message")
    if message:
        message = str(message)[:500]
    return error_type, message


def observe_entrypoint(expert_id, trace_name, entrypoint, fn):
    """统一入口埋点：捕获 stdout → 运行 fn → 上报成功/失败并提取错误信息 → 回写 stdout。

    fn 通常是脚本的 _main()，其契约是「成功/失败都 print 一段 JSON 到 stdout，
    失败时再 sys.exit(非 0)」。这里用 redirect_stdout 捕获输出，既能从失败输出里
    提取具体错误码与描述上报（而不是笼统的 SCRIPT_FAILED），又在结束时把输出原样
    回写到真实 stdout，不破坏 agent 依赖的 JSON 输出契约。

    注意：SystemExit（脚本正常失败）不能继续 raise——SDK 的 Trace.__exit__ 看到
    异常会无条件用 type(exc).__name__ 覆盖我们 set 好的 error_type/status_message
    （把具体错误码/描述变成笼统的 SYSTEMEXIT），所以这里吞掉 SystemExit，在 trace
    上下文之外再用 sys.exit(code) 传播退出码，既保留上报信息又不改变脚本退出语义。
    """
    observer = galileo_observer(
        expert_id, expert_version(),
        galileo_topic=galileo_topic(),
        spool_dir=os.path.join(os.getcwd(), ".observe"),
    )
    exit_code = 0
    with observer.trace(
        trace_name,
        run_id=os.environ.get("WB_SESSION_ID") or None,
        session_id=os.environ.get("WB_SESSION_ID") or None,
        attributes={"entrypoint": entrypoint},
    ) as observe_trace:
        captured = io.StringIO()
        try:
            with contextlib.redirect_stdout(captured):
                fn()
            observe_trace.set_result(success=True)
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 1
            exit_code = code
            if code == 0:
                observe_trace.set_result(success=True, attributes={"exit_code": code})
            else:
                error_type, message = extract_error_info(captured.getvalue())
                observe_trace.set_result(
                    success=False,
                    error_type=error_type or "SCRIPT_FAILED",
                    status_message=message,
                    attributes={"exit_code": code},
                )
        except Exception as e:  # noqa: BLE001
            observe_trace.set_result(
                success=False,
                error_type=type(e).__name__.upper(),
                status_message=str(e)[:200],
            )
            raise
        finally:
            # 无论成败，把脚本输出原样回写到真实 stdout（agent 依赖该 JSON 契约）
            sys.stdout.write(captured.getvalue())
    if exit_code:
        sys.exit(exit_code)


__all__ = [
    "DEFAULT_GALILEO_TOPIC",
    "DEFAULT_GALILEO_ENVIRONMENT",
    "DEFAULT_GALILEO_PLATFORM",
    "GalileoObserver",
    "Observer",
    "SDK_AVAILABLE",
    "SDK_SOURCE",
    "expert_version",
    "extract_error_info",
    "galileo_observer",
    "galileo_topic",
    "observe_entrypoint",
    "observe_span",
    "record_stage_timings",
]
