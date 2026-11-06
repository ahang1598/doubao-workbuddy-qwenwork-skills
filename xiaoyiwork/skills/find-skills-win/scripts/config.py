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
  PERSONAL_UID        - x-uid header（仅旧沙箱形态）
  PERSONAL_API_KEY    - x-api-key header（仅旧沙箱形态）
"""

import os
from dataclasses import dataclass

# 桌面形态默认接入点：主进程 skill API 代理（命名管道，authority 段即管道名）
DEFAULT_SERVICE_URL = "np://claw-skill"


# ============================================================
# dotenv: 从 .xiaoyienv 加载环境变量（仅旧沙箱形态需要）
# ============================================================

def _parse_double_quoted(raw: str) -> str:
    """解析双引号值，支持 \\n \\t \\\\ \\" 转义"""
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


def load_dotenv():
    """
    加载 .xiaoyienv 到进程环境变量。
    查找顺序：ACP2SERVICE_ENV 指定路径 → ~/.openclaw/.xiaoyienv。
    文件不存在时静默跳过；已存在的环境变量不被覆盖。
    """
    path = os.getenv("ACP2SERVICE_ENV", "")
    if not path or path.startswith("~"):
        path = str(os.path.expanduser("~/.openclaw/.xiaoyienv"))

    if not os.path.isfile(path):
        return

    with open(path, encoding="utf-8") as f:
        for line in f:
            result = _parse_dotenv_line(line)
            if result is None:
                continue
            key, value = result
            # key 中的 "-" 替换为 "_"
            env_key = key.replace("-", "_")
            # 不覆盖已存在的环境变量
            if not os.getenv(env_key):
                os.environ[env_key] = value


def _parse_bool(value: str) -> bool:
    return value.lower() in ("true", "1", "yes")


@dataclass
class Config:
    service_url: str = DEFAULT_SERVICE_URL
    personal_uid: str = ""
    personal_api_key: str = ""
    skill_token: str = ""
    tls_skip_verify: bool = False
    request_timeout: int = 30

    @property
    def pipe_mode(self) -> bool:
        """np:// 形态：经主进程管道代理（鉴权主进程注入，skill 侧零业务凭证）。"""
        return self.service_url.lower().startswith("np://")

    @property
    def pipe_path(self) -> str:
        from claw_pipe_http import pipe_path_from_url
        return pipe_path_from_url(self.service_url)

    def auth_headers(self) -> dict:
        """旧沙箱形态的鉴权 headers（小写 key）；管道形态返回空（主进程注入）。"""
        if self.pipe_mode:
            return {}
        headers = {}
        if self.personal_uid:
            headers["x-uid"] = self.personal_uid
        if self.personal_api_key:
            headers["x-api-key"] = self.personal_api_key
        return headers

    def skill_post(self, path: str, payload: dict, headers: dict | None = None, stream: bool = False):
        """POST 到 skill 云 API。

        np:// 形态：经主进程管道代理（claw_pipe_http；业务鉴权由代理注入，
        仅携带 CLAW_SKILL_TOKEN）；http(s):// 形态：requests 直连（旧沙箱兼容，
        鉴权头取 auth_headers()）。

        返回 claw_pipe_http.PipeHttpResponse 或 requests.Response——两者同构
        最小接口（status_code/text/json()/raise_for_status()/with）。
        """
        hdrs = {"Content-Type": "application/json", **(headers or {})}
        if self.pipe_mode:
            import json as _json
            from claw_pipe_http import pipe_request
            if not self.skill_token:
                raise ValueError("CLAW_SKILL_TOKEN 环境变量未设置（桌面形态由主进程注入）")
            return pipe_request(
                "POST",
                path,
                body=_json.dumps(payload, ensure_ascii=False).encode("utf-8"),
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
        cfg.personal_uid = os.getenv("PERSONAL_UID", "")
        cfg.personal_api_key = os.getenv("PERSONAL_API_KEY", "")
        cfg.tls_skip_verify = _parse_bool(os.getenv("TLS_SKIP_VERIFY", ""))
        cfg.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30") or "30")
        return cfg

