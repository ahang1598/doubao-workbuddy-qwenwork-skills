"""
config.py - 统一配置加载模块

桌面形态（默认）：SERVICE_URL=np://claw-skill —— 云端接口调用经主进程
SkillApiProxy（命名管道）转发，businessCredential 鉴权由主进程注入，
skill 侧零业务凭证，仅需 CLAW_SKILL_TOKEN 本机防借用令牌（主进程经
AgentServer 环境变量注入，孙进程继承）。此形态下无需任何配置文件。

旧沙箱形态（兼容）：SERVICE_URL=http(s)://... 时直连云端，鉴权头
（x-uid/x-api-key）从 .xiaoyienv 读取。

.xiaoyienv 查找顺序（仅旧沙箱形态需要）：
  1. ACP2SERVICE_ENV 环境变量指定的路径
  2. ~/.openclaw/.xiaoyienv

环境变量配置：
  SERVICE_URL         - skill 云 API base，默认 np://claw-skill（桌面管道代理）
  CLAW_SKILL_TOKEN    - 管道代理本机防借用令牌（桌面形态必填，主进程注入）
  REQUEST_FROM        - x-request-from header，默认 "openclaw"（仅旧沙箱形态）
  PERSONAL_UID        - x-uid header（仅旧沙箱形态；桌面形态由主进程注入）
  PERSONAL_API_KEY    - x-api-key header（仅旧沙箱形态）
  TLS_SKIP_VERIFY     - 跳过 TLS 验证，默认 false（仅旧沙箱形态）
  REQUEST_TIMEOUT     - 请求超时秒数，默认 3600（仅旧沙箱形态）
  OSMS_OBJECT_TYPE    - OSMS 对象类型，默认 "TEMPORARY_MATERIAL_DOC"
  OSMS_TLS_SKIP_VERIFY- OSMS 请求跳过 TLS 验证，未设置时继承 TLS_SKIP_VERIFY
  DEVICE_APP_VERSION  - 默认 "1.0.0"
  DEVICE_ID           - 默认自动生成 UUID
  DEVICE_MODEL        - 默认 "acp-cli"
  DEVICE_TYPE         - 默认 "vm"
  DEVICE_PRD_PKG_NAME - 默认 "com.huawei.hmos.vassistant"
"""

import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path

# 桌面形态默认接入点：主进程 skill API 代理（命名管道，authority 段即管道名）
DEFAULT_SERVICE_URL = "np://claw-skill"


# ============================================================
# dotenv: 从 .xiaoyienv 加载环境变量
# ============================================================

def _parse_double_quoted(raw: str) -> str:
    """解析双引号值，支持 \n \t \\ \" 转义"""
    raw = raw[1:]  # 去掉开头引号
    result = []
    escaped = False
    for ch in raw:
        if escaped:
            if ch == "n":
                result.append("\n")
            elif ch == "t":
                result.append("\t")
            elif ch == "\\":
                result.append("\\")
            elif ch == '"':
                result.append('"')
            else:
                result.append("\\")
                result.append(ch)
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == '"':
            break
        result.append(ch)
    return "".join(result)


def _parse_single_quoted(raw: str) -> str:
    """解析单引号值（不处理转义）"""
    raw = raw[1:]
    idx = raw.find("'")
    return raw[:idx] if idx >= 0 else raw


def _parse_value(raw: str) -> str:
    """解析等号右侧的值"""
    raw = raw.strip()
    if not raw:
        return ""
    if raw[0] == '"':
        return _parse_double_quoted(raw)
    if raw[0] == "'":
        return _parse_single_quoted(raw)
    # 无引号：行内 # 视为注释
    for sep in (" #", "\t#"):
        idx = raw.find(sep)
        if idx >= 0:
            raw = raw[:idx]
    return raw.strip()


def _parse_dotenv_line(line: str):
    """解析单行，返回 (key, value) 或 None"""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    # 剥除 export 前缀
    if line.startswith("export ") or line.startswith("export\t"):
        line = line[7:].strip()
    eq_idx = line.find("=")
    if eq_idx < 1:
        return None
    key = line[:eq_idx].strip()
    value = _parse_value(line[eq_idx + 1:])
    return key, value


def _load_env_file(file_path: str) -> None:
    """解析一个 dotenv 文件并写入进程环境变量（不覆盖已存在变量）。"""
    if not Path(file_path).is_file():
        return
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            result = _parse_dotenv_line(line)
            if result is None:
                continue
            key, value = result
            # key 中的 "-" 替换为 "_"
            env_key = key.replace("-", "_")
            if not os.getenv(env_key):
                os.environ[env_key] = value


def load_dotenv():
    """
    加载 .xiaoyienv（可选）与 .xiaoyiruntime（可选）到进程环境变量。
    .xiaoyienv：ACP2SERVICE_ENV 指定路径 → ~/.openclaw/.xiaoyienv
    .xiaoyiruntime：~/.openclaw/.xiaoyiruntime
    文件不存在时静默跳过；已存在的环境变量不被覆盖。
    """
    path = os.getenv("ACP2SERVICE_ENV", "")
    if not path or path.startswith("~"):
        path = str(Path.home() / ".openclaw" / ".xiaoyienv")
    _load_env_file(path)

    _load_env_file(str(Path.home() / ".openclaw" / ".xiaoyiruntime"))


def _parse_bool(value: str) -> bool:
    return value.lower() in ("true", "1", "yes")


# ============================================================
# Config
# ============================================================

@dataclass
class DeviceInfo:
    app_version: str = "1.0.0"
    device_id: str = ""
    device_model: str = "acp-cli"
    device_type: str = "vm"
    prd_pkg_name: str = "com.huawei.hmos.vassistant"

    def to_dict(self, trace_id: str = "") -> dict:
        return {
            "x-app-version": self.app_version,
            "x-device-id": self.device_id,
            "x-device-model": self.device_model,
            "x-device-type": self.device_type,
            "x-prd-pkg-name": self.prd_pkg_name,
            "x-trace-id": trace_id,
        }


@dataclass
class Config:
    service_url: str = DEFAULT_SERVICE_URL
    request_from: str = "openclaw"
    personal_uid: str = ""
    personal_api_key: str = ""
    tls_skip_verify: bool = False
    request_timeout: int = 3600
    osms_object_type: str = "TEMPORARY_MATERIAL_DOC"
    osms_tls_skip_verify: bool = False
    device: DeviceInfo = field(default_factory=DeviceInfo)
    sn: str = ""
    sessionId: str = ""
    skill_token: str = ""

    @property
    def pipe_mode(self) -> bool:
        """np:// 形态：经主进程管道代理（鉴权主进程注入，skill 侧零业务凭证）。"""
        return self.service_url.lower().startswith("np://")

    @property
    def pipe_path(self) -> str:
        from claw_pipe_http import pipe_path_from_url
        return pipe_path_from_url(self.service_url)

    def auth_headers(self) -> dict[str, str]:
        """旧沙箱形态的鉴权 headers（小写 key）；管道形态返回空（主进程注入）。"""
        if self.pipe_mode:
            return {}
        headers = {}
        if self.request_from:
            headers["x-request-from"] = self.request_from
        if self.personal_uid:
            headers["x-uid"] = self.personal_uid
        if self.personal_api_key:
            headers["x-api-key"] = self.personal_api_key
        return headers

    def skill_post(self, path: str, payload, headers: dict | None = None, stream: bool = False):
        """POST 到 skill 云 API。

        np:// 形态：经主进程管道代理（claw_pipe_http；业务鉴权由代理注入，
        仅携带 CLAW_SKILL_TOKEN）；http(s):// 形态：requests 直连（旧沙箱兼容，
        鉴权头取 auth_headers()）。

        返回 claw_pipe_http.PipeHttpResponse 或 requests.Response——两者同构
        最小接口（status_code/text/json()/iter_lines()/raise_for_status()/with）。
        """
        hdrs = {"Content-Type": "application/json", **(headers or {})}
        if self.pipe_mode:
            import json as _json
            from claw_pipe_http import pipe_request
            if not self.skill_token:
                raise ValueError("CLAW_SKILL_TOKEN 环境变量未设置（桌面形态由主进程注入）")
            body = payload if isinstance(payload, bytes) else _json.dumps(payload, ensure_ascii=False).encode("utf-8")
            return pipe_request(
                "POST",
                path,
                body=body,
                headers=hdrs,
                pipe_path=self.pipe_path,
                token=self.skill_token,
            )
        import requests
        return requests.post(
            self.service_url.rstrip("/") + path,
            json=payload,
            headers={**self.auth_headers(), **hdrs},
            stream=stream,
            timeout=self.request_timeout,
            verify=not self.tls_skip_verify,
        )

    @staticmethod
    def load() -> "Config":
        """从 .xiaoyienv（可选）+ 环境变量加载配置。"""
        load_dotenv()

        cfg = Config()
        # 未设置时默认 np://claw-skill（桌面管道代理）；旧沙箱经 .xiaoyienv 配 http(s) 地址
        cfg.service_url = os.getenv("SERVICE_URL", "") or DEFAULT_SERVICE_URL
        cfg.skill_token = os.getenv("CLAW_SKILL_TOKEN", "")

        cfg.request_from = os.getenv("REQUEST_FROM", "openclaw")
        cfg.personal_uid = os.getenv("PERSONAL_UID", "")
        cfg.personal_api_key = os.getenv("PERSONAL_API_KEY", "")
        cfg.tls_skip_verify = _parse_bool(os.getenv("TLS_SKIP_VERIFY", ""))
        cfg.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "3600"))

        cfg.osms_object_type = os.getenv("OSMS_OBJECT_TYPE", "TEMPORARY_MATERIAL_DOC")
        osms_tls = os.getenv("OSMS_TLS_SKIP_VERIFY", "")
        cfg.osms_tls_skip_verify = _parse_bool(osms_tls) if osms_tls else cfg.tls_skip_verify

        cfg.sn = (os.getenv("TASK_ID", "") + "1").replace("&", "_")
        cfg.sessionId = os.getenv("TASK_ID", "").replace("&", "_")

        cfg.device = DeviceInfo(
            app_version=os.getenv("DEVICE_APP_VERSION", ""),
            device_id=os.getenv("DEVICE_ID", "") or str(uuid.uuid4()),
            device_model=os.getenv("DEVICE_MODEL", "acp-cli"),
            device_type=os.getenv("DEVICE_TYPE", "vm"),
            prd_pkg_name=os.getenv("DEVICE_PRD_PKG_NAME", "com.huawei.hmos.vassistant"),
        )
        return cfg
