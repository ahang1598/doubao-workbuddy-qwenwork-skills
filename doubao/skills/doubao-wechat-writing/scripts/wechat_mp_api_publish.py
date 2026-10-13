#!/usr/bin/env python3
"""Publish WeChat Official Account articles through official APIs.

This script is intentionally CLI-oriented so an agent can drive the publishing
flow for non-technical users without opening the WeChat web editor.

Credentials are read from environment variables by default:
  WECHAT_MP_APPID
  WECHAT_MP_APPSECRET
  WECHAT_MP_ACCESS_TOKEN      optional, bypasses token retrieval

In local/direct mode, the current public egress IP must be added to the
Official Account API IP whitelist before calling WeChat server APIs.

Input payload is JSON. Typical workflow:
  python3 scripts/wechat_mp_api_publish.py workflow --payload payload.json
"""

from __future__ import annotations

import argparse
import html
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any


API_BASE = "https://api.weixin.qq.com/cgi-bin"
WECHAT_DEVELOPER_PLATFORM_URL = "https://developers.weixin.qq.com/platform/"
WECHAT_APPID_SECRET_DOC_URL = "https://developers.weixin.qq.com/doc/oplatform/developers/dev/appid.html"
WECHAT_IP_WHITELIST_DOC_URL = "https://developers.weixin.qq.com/doc/oplatform/developers/basic_func/ip_whitelist.html"
WECHAT_STABLE_TOKEN_DOC_URL = "https://developers.weixin.qq.com/doc/subscription/api/base/api_getstableaccesstoken.html"
WECHAT_API_DEBUG_URL = "https://developers.weixin.qq.com/console/devtools/debug"
LOCAL_CONFIG_DIR = Path.home() / ".config" / "doubao-wechat-writing"
LOCAL_CONFIG_PATH = LOCAL_CONFIG_DIR / "wechat-mp.json"
MMBIZ_IMAGE_PREFIXES = (
    "http://mmbiz.qpic.cn/",
    "https://mmbiz.qpic.cn/",
    "http://mmbiz.qpic.com/",
    "https://mmbiz.qpic.com/",
)


class UsageError(Exception):
    """User-fixable input or environment problem."""


class WeChatAPIError(Exception):
    """Wechat API returned an error response."""

    def __init__(self, payload: dict[str, Any]):
        self.payload = payload
        errcode = payload.get("errcode")
        errmsg = payload.get("errmsg")
        super().__init__(f"WeChat API error {errcode}: {errmsg}")


def now() -> int:
    return int(time.time())


def load_json_file(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path).expanduser()
    if not p.is_file():
        raise UsageError(f"payload 文件不存在：{p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise UsageError(f"payload 不是合法 JSON：{exc}") from exc
    if not isinstance(data, dict):
        raise UsageError("payload 根节点必须是 JSON object")
    return data


def local_config_path(payload: dict[str, Any] | None = None) -> Path:
    configured = (payload or {}).get("config_path") or os.getenv("WECHAT_MP_CONFIG_PATH")
    return Path(str(configured)).expanduser() if configured else LOCAL_CONFIG_PATH


def load_local_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UsageError(f"本地公众号配置无法读取：{path}，原因：{exc}") from exc
    if not isinstance(data, dict):
        raise UsageError(f"本地公众号配置格式错误：{path}")
    return data


def save_local_config(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def validate_appid(appid: str) -> None:
    if not re.fullmatch(r"wx[A-Za-z0-9]{8,}", appid):
        raise UsageError("公众号 AppID 格式不正确，应以 wx 开头。")


def configure_local(payload: dict[str, Any]) -> dict[str, Any]:
    path = local_config_path(payload)
    current = load_local_config(path)
    appid = str(
        payload.get("appid")
        or os.getenv("WECHAT_MP_APPID")
        or current.get("appid")
        or ""
    ).strip()
    appsecret = str(payload.get("appsecret") or os.getenv("WECHAT_MP_APPSECRET") or "").strip()

    if not appid or not appsecret:
        raise UsageError(
            "本地配置未完成。请先打开微信开发者平台获取公众号 AppID/AppSecret："
            f"{WECHAT_DEVELOPER_PLATFORM_URL}\n"
            "路径：微信开发者平台 → 前往控制台 → 我的业务与服务 → 公众号 → 基础信息；"
            "AppSecret 和 API IP 白名单位于“开发密钥”。\n"
            "获取后可直接提供给 Agent 用于本次发布，或选择保存到本地供后续复用。"
        )
    validate_appid(appid)

    config_data = {
        "appid": appid,
        "appsecret": appsecret,
        "secret_storage": "local_config_0600",
    }
    save_local_config(path, config_data)
    return {
        "config_path": str(path),
        "appid": appid,
        "secret_storage": "local_config_0600",
        **get_public_ip_snapshot(),
    }


def merge_local_config(payload: dict[str, Any]) -> dict[str, Any]:
    path = local_config_path(payload)
    local = load_local_config(path)
    merged = {**local, **payload}
    merged["config_path"] = str(path)
    return merged


def write_json(path: str | None, data: dict[str, Any]) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if path:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text + "\n", encoding="utf-8")
    print(text)


def cidr_24_of(ip: str | None) -> str | None:
    """Return the /24 CIDR block for an IPv4 address, else None."""
    if not ip:
        return None
    match = re.fullmatch(r"(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})", ip.strip())
    if not match:
        return None
    octets = [int(part) for part in match.groups()]
    if any(part > 255 for part in octets):
        return None
    return f"{octets[0]}.{octets[1]}.{octets[2]}.0/24"


def friendly_api_message(payload: dict[str, Any]) -> str:
    errcode = payload.get("errcode")
    errmsg = str(payload.get("errmsg", ""))
    reported_ip_match = re.search(r"\binvalid ip\s+([0-9a-fA-F:.]+)", errmsg, re.IGNORECASE)
    reported_ip = reported_ip_match.group(1) if reported_ip_match else None
    ip_snapshot = get_public_ip_snapshot() if errcode in (40164, 61004) and not reported_ip else {}
    observed_ips = ip_snapshot.get("observed_public_ips") or []
    ip_text = reported_ip or "、".join(observed_ips) or "未能自动检测"
    cidr = cidr_24_of(reported_ip) or cidr_24_of(observed_ips[0] if observed_ips else None)
    cidr_hint = (
        f"当前出口 IP 常在同一网段内轮换，建议直接把整个网段 {cidr} 加入白名单（微信支持 /24 CIDR），"
        "不要逐个加 IP。"
        if cidr
        else "请把该 IP 加入白名单。"
    )
    mapping = {
        40001: "公众号接口凭据已失效或不是最新值，请重新验证本地配置后重试。",
        40013: f"公众号 AppID 不正确。查看入口：{WECHAT_DEVELOPER_PLATFORM_URL}；说明：{WECHAT_APPID_SECRET_DOC_URL}",
        40125: f"公众号 AppSecret 不正确。查看入口：{WECHAT_DEVELOPER_PLATFORM_URL}；说明：{WECHAT_APPID_SECRET_DOC_URL}",
        40164: (
            f"微信接口实际看到的公网出口 IP 为：{ip_text}。{cidr_hint}"
            f"说明：{WECHAT_IP_WHITELIST_DOC_URL}"
        ),
        61004: (
            f"微信接口实际看到的公网出口 IP 为：{ip_text}。{cidr_hint}"
            f"说明：{WECHAT_IP_WHITELIST_DOC_URL}"
        ),
        40243: f"公众号 AppSecret 已被冻结。查看入口：{WECHAT_DEVELOPER_PLATFORM_URL}；说明：{WECHAT_APPID_SECRET_DOC_URL}",
        45009: "接口调用已超过公众号每日额度，请稍后或明天重试。",
        45011: "接口调用过于频繁，请稍后重试。",
        48001: (
            "账号无接口发布权限，通常是个人主体或未认证账号（接口发布仅限已认证企业主体）。"
            "草稿已可用，Agent 会用浏览器自动打开公众号后台草稿箱并定位到该文章，"
            "请在编辑器右下角点「发表」。"
            "微信没有免登录一键发布链接；如需接口全自动发布，需升级为已认证企业主体。"
        ),
        53503: "该草稿未通过发布检查，请检查标题、封面、正文图片、原创/转载声明等信息。",
        53504: "该草稿需要前往公众平台官网处理后才能发布。",
        53505: "该草稿需要在公众平台官网手动保存成功后再发布。",
        89503: "本次接口调用需要公众号管理员在微信侧确认。",
        89506: "管理员拒绝了该 IP 的调用请求，请 24 小时后再试，并先与管理员确认。",
        89507: "管理员拒绝了该 IP 的调用请求，请 1 小时后再试，并先与管理员确认。",
    }
    if errcode in mapping:
        return mapping[errcode]
    if errcode is None:
        return errmsg or "接口返回异常。"
    return f"微信接口返回错误 {errcode}：{errmsg}"


def http_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    body = None
    headers = {"User-Agent": "doubao-wechat-writing-api/1.0"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as json_exc:
            raise WeChatAPIError({"errcode": exc.code, "errmsg": raw}) from json_exc
        raise WeChatAPIError(data) from exc
    except urllib.error.URLError as exc:
        raise UsageError(f"网络请求失败：{exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UsageError(f"微信接口返回非 JSON 内容：{raw[:300]}") from exc
    check_api_error(data)
    return data


def multipart_upload(
    url: str,
    file_path: Path,
    field_name: str = "media",
    timeout: int = 60,
) -> dict[str, Any]:
    if not file_path.is_file():
        raise UsageError(f"文件不存在：{file_path}")
    boundary = f"----doubaoWechatBoundary{uuid.uuid4().hex}"
    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    filename = file_path.name
    file_bytes = file_path.read_bytes()

    parts = [
        f"--{boundary}\r\n".encode("utf-8"),
        (
            f'Content-Disposition: form-data; name="{field_name}"; '
            f'filename="{filename}"\r\n'
        ).encode("utf-8"),
        f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
        file_bytes,
        f"\r\n--{boundary}--\r\n".encode("utf-8"),
    ]
    body = b"".join(parts)
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
            "User-Agent": "doubao-wechat-writing-api/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as json_exc:
            raise WeChatAPIError({"errcode": exc.code, "errmsg": raw}) from json_exc
        raise WeChatAPIError(data) from exc
    except urllib.error.URLError as exc:
        raise UsageError(f"上传文件失败：{exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UsageError(f"微信接口返回非 JSON 内容：{raw[:300]}") from exc
    check_api_error(data)
    return data


def check_api_error(data: dict[str, Any]) -> None:
    errcode = data.get("errcode")
    if errcode not in (None, 0):
        raise WeChatAPIError(data)


def token_cache_path(payload: dict[str, Any], artifact_dir: Path) -> Path:
    configured = payload.get("token_cache") or os.getenv("WECHAT_MP_TOKEN_CACHE")
    if configured:
        return Path(str(configured)).expanduser()
    return local_config_path(payload).parent / ".wechat_access_token.json"


def get_access_token(payload: dict[str, Any], artifact_dir: Path, force_refresh: bool = False) -> tuple[str, list[str]]:
    warnings: list[str] = []
    direct_token = payload.get("access_token") or os.getenv("WECHAT_MP_ACCESS_TOKEN")
    if direct_token:
        return str(direct_token), warnings

    appid = payload.get("appid") or os.getenv("WECHAT_MP_APPID")
    appsecret = payload.get("appsecret") or os.getenv("WECHAT_MP_APPSECRET")
    if not appid or not appsecret:
        snapshot = get_public_ip_snapshot()
        observed_ips = snapshot.get("observed_public_ips") or []
        ip_line = (
            f"\n- 检测到的公网出口 IP：{'、'.join(observed_ips)}"
            if observed_ips
            else ""
        )
        raise UsageError(
            "当前缺少公众号直连接口配置。请在微信开发者平台获取公众号 AppID/AppSecret，"
            "并把微信回显出口 IP 所在的 /24 网段加入 API IP 白名单：\n"
            f"- 微信开发者平台：{WECHAT_DEVELOPER_PLATFORM_URL}\n"
            f"- AppID/AppSecret 说明：{WECHAT_APPID_SECRET_DOC_URL}\n"
            f"- API IP 白名单说明：{WECHAT_IP_WHITELIST_DOC_URL}\n"
            f"- 稳定版 access_token 接口：{WECHAT_STABLE_TOKEN_DOC_URL}"
            f"{ip_line}\n"
            "- 获取后可直接提供给 Agent 用于本次发布，或选择保存到本地。"
        )

    cache_file = token_cache_path(payload, artifact_dir)
    if not force_refresh and cache_file.is_file():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            token = cached.get("access_token")
            expires_at = int(cached.get("expires_at", 0))
            if token and expires_at > now() + 300:
                return str(token), warnings
        except (OSError, ValueError, json.JSONDecodeError):
            warnings.append("token 缓存不可读，已重新获取。")

    token_payload = {
        "grant_type": "client_credential",
        "appid": appid,
        "secret": appsecret,
        "force_refresh": bool(force_refresh or payload.get("force_refresh")),
    }
    data = http_json("POST", f"{API_BASE}/stable_token", token_payload)
    token = data.get("access_token")
    if not token:
        raise WeChatAPIError(data)
    expires_in = int(data.get("expires_in") or 7200)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(
        json.dumps(
            {
                "access_token": token,
                "expires_at": now() + max(expires_in - 60, 60),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    cache_file.chmod(0o600)
    return str(token), warnings


def api_url(path: str, access_token: str, **params: str) -> str:
    query = {"access_token": access_token}
    query.update(params)
    return f"{API_BASE}/{path}?{urllib.parse.urlencode(query)}"


def get_public_ip(timeout: int = 5) -> str | None:
    services = [
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://checkip.amazonaws.com",
    ]
    for url in services:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "doubao-wechat-writing-api/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                value = resp.read().decode("utf-8", errors="replace").strip()
            if re.match(r"^[0-9a-fA-F:.]+$", value):
                return value
        except Exception:
            continue
    return None


def get_public_ip_snapshot(sample_count: int = 4) -> dict[str, Any]:
    observed: list[str] = []
    for _ in range(max(sample_count, 1)):
        value = get_public_ip()
        if value and value not in observed:
            observed.append(value)
        if sample_count > 1:
            time.sleep(0.15)
    recommendation = cidr_24_of(observed[0]) if observed else None
    return {
        "current_public_ip": observed[0] if len(observed) == 1 else None,
        "observed_public_ips": observed,
        "public_ip_stable": len(observed) == 1,
        "ip_whitelist_recommendation": recommendation,
    }


def verify_direct_config(payload: dict[str, Any]) -> dict[str, Any]:
    appid = str(payload.get("appid") or os.getenv("WECHAT_MP_APPID") or "").strip()
    appsecret = str(payload.get("appsecret") or os.getenv("WECHAT_MP_APPSECRET") or "").strip()
    if not appid or not appsecret:
        raise UsageError(
            "缺少 AppID/AppSecret。请先在微信开发者平台获取后直接提供用于本次任务，"
            "或选择保存到本地后再验证。"
        )
    data = http_json(
        "POST",
        f"{API_BASE}/stable_token",
        {
            "grant_type": "client_credential",
            "appid": appid,
            "secret": appsecret,
            "force_refresh": False,
        },
    )
    if not data.get("access_token"):
        raise WeChatAPIError(data)
    return {
        "verified": True,
        "appid": appid,
        **get_public_ip_snapshot(),
        "message": "AppID、AppSecret 和 API IP 白名单均已通过微信接口验证。",
    }


def ensure_artifact_dir(payload: dict[str, Any]) -> Path:
    raw = payload.get("artifact_dir") or os.getenv("TASK_ARTIFACT_DIR") or os.getcwd()
    path = Path(str(raw)).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_source_to_file(source: str, work_dir: Path, label: str) -> Path:
    if not source:
        raise UsageError(f"缺少 {label} 文件或 URL。")
    if source.startswith(("http://", "https://")):
        return download_to_file(source, work_dir, label)
    path = Path(source).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if not path.is_file():
        raise UsageError(f"{label} 文件不存在：{path}")
    return path


def download_to_file(url: str, work_dir: Path, label: str) -> Path:
    req = urllib.request.Request(url, headers={"User-Agent": "doubao-wechat-writing-api/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            content_type = resp.headers.get("Content-Type", "").split(";")[0].strip()
    except urllib.error.URLError as exc:
        raise UsageError(f"{label} 下载失败：{url}，原因：{exc}") from exc
    ext = mimetypes.guess_extension(content_type) or Path(urllib.parse.urlparse(url).path).suffix
    if not ext:
        ext = ".bin"
    out = work_dir / f"{label}_{uuid.uuid4().hex}{ext}"
    out.write_bytes(data)
    return out


def compress_content_image(file_path: Path, work_dir: Path) -> Path:
    max_bytes = 1024 * 1024
    if file_path.stat().st_size <= max_bytes:
        return file_path
    sips = shutil.which("sips")
    attempts = ((1920, 80), (1600, 72), (1280, 65), (1080, 58))
    if sips:
        # JPEG quality and resolution are reduced together to keep the API request reliable.
        for width, quality in attempts:
            target = work_dir / f"{file_path.stem}_wechat_{width}_{quality}.jpg"
            completed = subprocess.run(
                [
                    sips,
                    "--resampleWidth",
                    str(width),
                    "--setProperty",
                    "format",
                    "jpeg",
                    "--setProperty",
                    "formatOptions",
                    str(quality),
                    str(file_path),
                    "--out",
                    str(target),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode == 0 and target.is_file() and target.stat().st_size <= max_bytes:
                return target

    try:
        from PIL import Image, ImageOps
    except ImportError:
        raise UsageError(
            f"正文图片超过 1MB，且当前环境无法自动压缩：{file_path}。"
            "请在本机安装 Pillow，或提供小于 1MB 的图片。"
        ) from None

    with Image.open(file_path) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")
        for width, quality in attempts:
            target = work_dir / f"{file_path.stem}_wechat_{width}_{quality}.jpg"
            candidate = image.copy()
            candidate.thumbnail((width, width * 4), Image.Resampling.LANCZOS)
            candidate.save(target, "JPEG", quality=quality, optimize=True)
            candidate.close()
            if target.stat().st_size <= max_bytes:
                return target
    raise UsageError(f"正文图片自动压缩后仍超过 1MB：{file_path}。请更换或裁剪图片。")


def can_auto_compress_images() -> bool:
    if shutil.which("sips"):
        return True
    try:
        import PIL  # noqa: F401
    except ImportError:
        return False
    return True


def upload_content_image(source: str, access_token: str, work_dir: Path) -> tuple[str, str]:
    if source.startswith(MMBIZ_IMAGE_PREFIXES):
        return source, "kept_mmbiz"
    file_path = resolve_source_to_file(source, work_dir, "content_image")
    original_path = file_path
    file_path = compress_content_image(file_path, work_dir)
    data = multipart_upload(api_url("media/uploadimg", access_token), file_path)
    url = data.get("url")
    if not url:
        raise WeChatAPIError(data)
    state = "compressed_and_uploaded" if file_path != original_path else "uploaded"
    return str(url), state


def upload_cover_image(payload: dict[str, Any], access_token: str, work_dir: Path) -> tuple[str, dict[str, Any]]:
    existing_media_id = payload.get("cover_media_id") or payload.get("thumb_media_id")
    if existing_media_id:
        return str(existing_media_id), {"source": "existing_media_id"}

    source = payload.get("cover_path") or payload.get("cover_url")
    if not source:
        raise UsageError(
            "缺少封面图。请提供 payload.cover_path / payload.cover_url，"
            "或提供已上传的 cover_media_id。"
        )
    file_path = resolve_source_to_file(str(source), work_dir, "cover")
    data = multipart_upload(api_url("material/add_material", access_token, type="image"), file_path)
    media_id = data.get("media_id")
    if not media_id:
        raise WeChatAPIError(data)
    return str(media_id), {"source": str(file_path), "url": data.get("url")}


IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\((https?://[^)\s]+)\)")
HTML_IMG_SRC_RE = re.compile(r"(<img\b[^>]*\bsrc=[\"'])([^\"']+)([\"'][^>]*>)", re.IGNORECASE)
HORIZONTAL_RULE_RE = re.compile(r"^(\*{3,}|-{3,}|_{3,})$")
PUBLISH_EXCLUDED_SECTION_RE = re.compile(
    r"^#{1,6}\s*(?:封面图(?:推荐)?|备选标题|内容验真|运营策略(?:建议)?|"
    r"发布(?:信息|配置)?|编辑备注|内部备注|提示词)\s*$",
    re.IGNORECASE,
)
PUBLISH_PACKAGE_SCHEMA_VERSION = 1


def load_publish_package(payload: dict[str, Any]) -> dict[str, Any]:
    package_path = payload.get("publish_package_path")
    if not package_path:
        return {}
    path = Path(str(package_path)).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    package = load_json_file(str(path))
    version = package.get("schema_version")
    if version != PUBLISH_PACKAGE_SCHEMA_VERSION:
        raise UsageError(
            f"发布包 schema_version 必须为 {PUBLISH_PACKAGE_SCHEMA_VERSION}：{path}"
        )
    body_markdown = package.get("body_markdown")
    body_markdown_path = package.get("body_markdown_path")
    if bool(body_markdown) == bool(body_markdown_path):
        raise UsageError(
            f"发布包必须且只能提供 body_markdown 或 body_markdown_path：{path}"
        )
    if body_markdown_path:
        body_path = Path(str(body_markdown_path)).expanduser()
        if not body_path.is_absolute():
            body_path = (path.parent / body_path).resolve()
        if not body_path.is_file():
            raise UsageError(f"发布包正文文件不存在：{body_path}")
        body_markdown = body_path.read_text(encoding="utf-8")
    if not isinstance(body_markdown, str) or not body_markdown.strip():
        raise UsageError(f"发布包缺少非空 body_markdown：{path}")
    excluded = [
        line.strip()
        for line in body_markdown.splitlines()
        if PUBLISH_EXCLUDED_SECTION_RE.fullmatch(line.strip())
    ]
    if excluded:
        raise UsageError(
            "发布包正文包含非发布区块："
            + "、".join(excluded)
            + "。请将封面、备选标题、验真、运营建议等保留在飞书交付文档，"
            "不要写入 body_markdown。"
        )
    package = dict(package)
    package.pop("schema_version", None)
    package.pop("body_markdown_path", None)
    package.pop("body_markdown", None)
    package["markdown"] = body_markdown
    package["publish_package_path"] = str(path)
    return package


def get_layout_styles(payload: dict[str, Any]) -> dict[str, str]:
    profile = str(payload.get("layout_profile") or "clean").strip().lower()
    profiles = {
        "clean": {
            "section": "font-size:16px;line-height:1.85;color:#1f1f1f;letter-spacing:0.03em;",
            "paragraph": "margin:0 0 18px;line-height:1.9;font-size:16px;color:#1f1f1f;text-align:justify;",
            "heading": "margin:34px 0 16px;padding-left:10px;border-left:4px solid #1f1f1f;line-height:1.45;font-weight:700;color:#1f1f1f;",
            "quote": "margin:4px 0 22px;padding:13px 15px;border-left:3px solid #8c8c8c;background:#f7f7f7;color:#555;line-height:1.85;font-size:15px;",
            "list": "margin:0 0 18px 1.2em;padding:0;font-size:16px;color:#1f1f1f;line-height:1.9;",
            "rule": "border:0;border-top:1px solid #dedede;margin:28px 0;",
        },
        "minimal": {
            "section": "font-size:16px;line-height:1.85;color:#1f1f1f;",
            "paragraph": "margin:0 0 16px;line-height:1.85;font-size:16px;color:#1f1f1f;",
            "heading": "margin:28px 0 14px;line-height:1.5;font-weight:700;color:#1f1f1f;",
            "quote": "margin:0 0 16px;padding:10px 14px;border-left:4px solid #d0d7de;background:#f6f8fa;color:#555;line-height:1.8;font-size:15px;",
            "list": "margin:0 0 16px 1.2em;padding:0;font-size:16px;color:#1f1f1f;",
            "rule": "border:0;border-top:1px solid #e5e5e5;margin:24px 0;",
        },
    }
    if profile not in profiles:
        raise UsageError("layout_profile 仅支持 clean 或 minimal。")
    return profiles[profile]


def inline_markdown(text: str, image_uploads: list[dict[str, str]] | None = None) -> str:
    escaped = html.escape(text.strip())
    escaped = BOLD_RE.sub(r"<strong>\1</strong>", escaped)
    escaped = LINK_RE.sub(r'<a href="\2">\1</a>', escaped)
    if image_uploads:
        for idx, upload in enumerate(image_uploads):
            placeholder = f"WECHAT_IMAGE_PLACEHOLDER_{idx}"
            if placeholder in escaped and upload.get("html"):
                escaped = escaped.replace(placeholder, upload["html"])
    return escaped


def replace_markdown_images(text: str, access_token: str, work_dir: Path, uploads: list[dict[str, str]]) -> str:
    def repl(match: re.Match[str]) -> str:
        alt = match.group(1).strip()
        source = match.group(2).strip()
        uploaded_url, state = upload_content_image(source, access_token, work_dir)
        idx = len(uploads)
        alt_attr = html.escape(alt, quote=True)
        image_html = (
            f'<img src="{html.escape(uploaded_url, quote=True)}" alt="{alt_attr}" '
            'style="max-width:100%;height:auto;display:block;margin:16px auto;" />'
        )
        uploads.append({"source": source, "url": uploaded_url, "state": state, "html": image_html})
        return f"WECHAT_IMAGE_PLACEHOLDER_{idx}"

    return IMAGE_RE.sub(repl, text)


def build_html_from_markdown(
    markdown_text: str,
    title: str,
    access_token: str,
    work_dir: Path,
    strip_title: bool = True,
    layout_payload: dict[str, Any] | None = None,
) -> tuple[str, list[dict[str, str]]]:
    styles = get_layout_styles(layout_payload or {})
    uploads: list[dict[str, str]] = []
    lines = markdown_text.replace("\r\n", "\n").split("\n")
    blocks: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    table_buffer: list[str] = []
    expecting_table_separator = False

    def flush_paragraph() -> None:
        if paragraph:
            text = " ".join(part.strip() for part in paragraph if part.strip())
            text = replace_markdown_images(text, access_token, work_dir, uploads)
            blocks.append(
                f'<p style="{styles["paragraph"]}">'
                + inline_markdown(text, uploads)
                + "</p>"
            )
            paragraph.clear()

    def flush_list() -> None:
        if list_items:
            items = "".join(
                '<li style="margin:0 0 8px;line-height:1.8;">'
                + inline_markdown(item, uploads)
                + "</li>"
                for item in list_items
            )
            blocks.append(
                f'<ul style="{styles["list"]}">'
                + items
                + "</ul>"
            )
            list_items.clear()

    def flush_table() -> None:
        if not table_buffer:
            return
        # 解析 Markdown 表格行：| 列1 | 列2 | 列3 |
        parsed_rows: list[list[str]] = []
        for row_line in table_buffer:
            stripped_line = row_line.strip()
            # 去掉首尾的 |，然后按 | 分割
            if stripped_line.startswith("|"):
                stripped_line = stripped_line[1:]
            if stripped_line.endswith("|"):
                stripped_line = stripped_line[:-1]
            cells = [cell.strip() for cell in stripped_line.split("|")]
            parsed_rows.append(cells)
        # 第一行是表头，第二行是分隔线（---），后续是数据行
        if len(parsed_rows) >= 2:
            header_cells = parsed_rows[0]
            body_rows = parsed_rows[2:] if len(parsed_rows) > 2 else []
            thead_html = "<tr>" + "".join(
                f'<th style="border:1px solid #ddd;padding:8px 12px;background:#f6f8fa;text-align:left;line-height:1.6;">'
                + inline_markdown(cell, uploads)
                + "</th>"
                for cell in header_cells
            ) + "</tr>"
            tbody_html = ""
            for row in body_rows:
                tbody_html += "<tr>" + "".join(
                    f'<td style="border:1px solid #ddd;padding:8px 12px;line-height:1.6;">'
                    + inline_markdown(cell, uploads)
                    + "</td>"
                    for cell in row
                ) + "</tr>"
            blocks.append(
                '<table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:14px;">'
                f"<thead>{thead_html}</thead><tbody>{tbody_html}</tbody></table>"
            )
        table_buffer.clear()

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            flush_list()
            flush_table()
            continue

        # 如果正在期待表格分隔行（上一行是 | 表头 |）
        if expecting_table_separator:
            if re.match(r"^\|[\s\-:|]+\|$", stripped):
                table_buffer.append(stripped)
                expecting_table_separator = False
                continue
            else:
                # 不是表格，把暂存的行作为段落
                for tb in table_buffer:
                    paragraph.append(tb)
                table_buffer.clear()
                expecting_table_separator = False
                # 继续处理当前行

        # 如果正在收集表格行
        if table_buffer and not expecting_table_separator:
            if re.match(r"^\|.*\|$", stripped):
                table_buffer.append(stripped)
                continue
            else:
                # 表格结束
                flush_table()
                # 继续处理当前行

        # 检测表格开始：当前行是 | ... | 格式
        if re.match(r"^\|.*\|$", stripped) and not table_buffer:
            # 暂存，期待下一行是分隔行
            table_buffer.append(stripped)
            expecting_table_separator = True
            flush_paragraph()
            flush_list()
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        list_match = re.match(r"^[-*+]\s+(.+)$", stripped)
        quote_match = re.match(r"^>\s?(.+)$", stripped)

        if HORIZONTAL_RULE_RE.fullmatch(stripped):
            flush_paragraph()
            flush_list()
            blocks.append(f'<hr style="{styles["rule"]}" />')
        elif heading_match:
            flush_paragraph()
            flush_list()
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
            if strip_title and level == 1 and heading_text == title:
                continue
            size = "20px" if level <= 2 else "18px"
            blocks.append(
                f'<h{min(level + 1, 6)} style="{styles["heading"]}font-size:{size};">'
                + inline_markdown(heading_text, uploads)
                + f"</h{min(level + 1, 6)}>"
            )
        elif list_match:
            flush_paragraph()
            item = replace_markdown_images(list_match.group(1), access_token, work_dir, uploads)
            list_items.append(item)
        elif quote_match:
            flush_paragraph()
            flush_list()
            quote = replace_markdown_images(quote_match.group(1), access_token, work_dir, uploads)
            blocks.append(
                f'<blockquote style="{styles["quote"]}">'
                + inline_markdown(quote, uploads)
                + "</blockquote>"
            )
        else:
            flush_list()
            paragraph.append(stripped)

    flush_paragraph()
    flush_list()
    flush_table()
    content = "\n".join(blocks)
    return f'<section style="{styles["section"]}">\n{content}\n</section>', uploads


def replace_html_images(content_html: str, access_token: str, work_dir: Path) -> tuple[str, list[dict[str, str]]]:
    uploads: list[dict[str, str]] = []

    def repl(match: re.Match[str]) -> str:
        prefix, source, suffix = match.groups()
        uploaded_url, state = upload_content_image(source, access_token, work_dir)
        uploads.append({"source": source, "url": uploaded_url, "state": state})
        return prefix + html.escape(uploaded_url, quote=True) + suffix

    return HTML_IMG_SRC_RE.sub(repl, content_html), uploads


def get_article_html(payload: dict[str, Any], access_token: str, work_dir: Path) -> tuple[str, list[dict[str, str]]]:
    if payload.get("publish_package_path"):
        return build_html_from_markdown(
            str(payload["markdown"]),
            str(payload.get("title") or ""),
            access_token,
            work_dir,
            bool(payload.get("strip_title", True)),
            payload,
        )
    if payload.get("content_html"):
        return replace_html_images(str(payload["content_html"]), access_token, work_dir)
    if payload.get("markdown"):
        return build_html_from_markdown(
            str(payload["markdown"]),
            str(payload.get("title") or ""),
            access_token,
            work_dir,
            bool(payload.get("strip_title", True)),
            payload,
        )
    markdown_path = payload.get("markdown_path")
    if markdown_path:
        path = Path(str(markdown_path)).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        if not path.is_file():
            raise UsageError(f"Markdown 文件不存在：{path}")
        text = path.read_text(encoding="utf-8")
        return build_html_from_markdown(
            text,
            str(payload.get("title") or ""),
            access_token,
            work_dir,
            bool(payload.get("strip_title", True)),
            payload,
        )
    raise UsageError("缺少正文。请提供 payload.content_html、payload.markdown 或 payload.markdown_path。")


def normalize_digest(payload: dict[str, Any], article_html: str, warnings: list[str]) -> str:
    digest = str(payload.get("digest") or "").strip()
    if not digest:
        text = re.sub(r"<[^>]+>", "", article_html)
        text = html.unescape(re.sub(r"\s+", " ", text)).strip()
        digest = text[:54]
    if len(digest) > 120:
        warnings.append("摘要超过 120 字，已自动截断。")
        digest = digest[:120]
    return digest


def validate_title_author(title: str, author: str | None) -> None:
    if not title:
        raise UsageError("缺少文章标题 title。")
    title_bytes = len(title.encode("utf-8"))
    if title_bytes > 64:
        raise UsageError(
            f"微信草稿接口标题不能超过 64 字节；当前为 {title_bytes} 字节。"
            "请先让用户确认一个更短标题。"
        )
    if author and len(author) > 16:
        raise UsageError("微信草稿接口作者总长度不能超过 16 个字，请先让用户缩短作者名。")


def collect_markdown_image_sources(markdown_text: str) -> list[str]:
    return [match.group(2).strip() for match in IMAGE_RE.finditer(markdown_text)]


def get_markdown_text(payload: dict[str, Any]) -> str:
    if payload.get("markdown"):
        return str(payload["markdown"])
    markdown_path = payload.get("markdown_path")
    if not markdown_path:
        raise UsageError("缺少正文。请提供 payload.markdown 或 payload.markdown_path。")
    path = Path(str(markdown_path)).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if not path.is_file():
        raise UsageError(f"Markdown 文件不存在：{path}")
    return path.read_text(encoding="utf-8")


def inspect_image_source(source: str, label: str) -> dict[str, Any]:
    if source.startswith(("http://", "https://")):
        req = urllib.request.Request(
            source,
            headers={"User-Agent": "doubao-wechat-writing-api/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                content_type = resp.headers.get("Content-Type", "").split(";")[0].strip()
                content_length = resp.headers.get("Content-Length")
                sample = resp.read(512)
        except urllib.error.URLError as exc:
            raise UsageError(f"{label} 无法访问：{source}，原因：{exc}") from exc
        if not content_type.startswith("image/"):
            raise UsageError(f"{label} 不是图片资源：{source}，Content-Type={content_type or '未知'}")
        return {
            "source": source,
            "content_type": content_type,
            "content_length": int(content_length) if content_length and content_length.isdigit() else None,
            "sample_bytes_read": len(sample),
        }

    path = Path(source).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if not path.is_file():
        raise UsageError(f"{label} 文件不存在：{path}")
    content_type = mimetypes.guess_type(str(path))[0] or ""
    if not content_type.startswith("image/"):
        raise UsageError(f"{label} 不是图片文件：{path}")
    return {
        "source": str(path),
        "content_type": content_type,
        "content_length": path.stat().st_size,
    }


def preflight(payload: dict[str, Any]) -> dict[str, Any]:
    title = str(payload.get("title") or "").strip()
    author = str(payload.get("author") or payload.get("account_name") or "").strip()
    validate_title_author(title, author or None)
    markdown_text = get_markdown_text(payload)
    image_sources = collect_markdown_image_sources(markdown_text)
    cover_source = payload.get("cover_path") or payload.get("cover_url")
    if not cover_source and not (payload.get("cover_media_id") or payload.get("thumb_media_id")):
        raise UsageError("缺少封面图。请提供 payload.cover_path / payload.cover_url 或 cover_media_id。")

    content_images = [
        inspect_image_source(source, f"正文图片 {index}")
        for index, source in enumerate(image_sources, start=1)
    ]
    cover = (
        {"source": "existing_media_id"}
        if payload.get("cover_media_id") or payload.get("thumb_media_id")
        else inspect_image_source(str(cover_source), "封面图")
    )
    warnings: list[str] = []
    for image in content_images:
        if image.get("content_length") and int(image["content_length"]) > 1024 * 1024:
            if can_auto_compress_images():
                image["upload_plan"] = "will_auto_compress_to_under_1MB"
            else:
                warnings.append(f"正文图片超过 1MB，且当前环境无法自动压缩：{image['source']}")
    if cover.get("content_length") and int(cover["content_length"]) > 2 * 1024 * 1024:
        warnings.append(f"封面图超过 2MB，上传前需压缩：{cover['source']}")
    return {
        "passed": not warnings,
        "title": title,
        "title_utf8_bytes": len(title.encode("utf-8")),
        "author": author,
        "markdown_characters": len(markdown_text),
        "content_images": content_images,
        "cover": cover,
        "warnings": warnings,
    }


def create_draft(payload: dict[str, Any], access_token: str, work_dir: Path, warnings: list[str]) -> dict[str, Any]:
    title = str(payload.get("title") or "").strip()
    author = str(payload.get("author") or payload.get("account_name") or "").strip()
    validate_title_author(title, author or None)
    article_html, image_uploads = get_article_html(payload, access_token, work_dir)
    if len(article_html) > 1024 * 1024:
        raise UsageError("正文 HTML 超过 1MB，请压缩正文或图片后重试。")
    if len(re.sub(r"<[^>]+>", "", article_html)) > 20000:
        warnings.append("正文纯文本可能超过 2 万字，微信接口可能拒绝保存。")

    thumb_media_id, cover_state = upload_cover_image(payload, access_token, work_dir)
    digest = normalize_digest(payload, article_html, warnings)
    article: dict[str, Any] = {
        "article_type": "news",
        "title": title,
        "author": author,
        "digest": digest,
        "content": article_html,
        "content_source_url": str(payload.get("content_source_url") or ""),
        "thumb_media_id": thumb_media_id,
        "need_open_comment": int(bool(payload.get("need_open_comment", 0))),
        "only_fans_can_comment": int(bool(payload.get("only_fans_can_comment", 0))),
    }
    cover_info = payload.get("cover_info")
    if cover_info:
        article["cover_info"] = cover_info
    elif payload.get("cover_crop_percent_list"):
        article["cover_info"] = {"crop_percent_list": payload["cover_crop_percent_list"]}

    data = http_json("POST", api_url("draft/add", access_token), {"articles": [article]})
    media_id = data.get("media_id")
    if not media_id:
        raise WeChatAPIError(data)
    draft_url = find_draft_url(str(media_id), access_token)
    public_image_uploads = [
        {key: value for key, value in item.items() if key != "html"}
        for item in image_uploads
    ]
    return {
        "media_id": media_id,
        "url": draft_url,
        "title": title,
        "author": author,
        "digest": digest,
        "thumb_media_id": thumb_media_id,
        "cover": cover_state,
        "content_images": public_image_uploads,
    }


def find_draft_url(media_id: str, access_token: str) -> str | None:
    try:
        data = http_json(
            "POST",
            api_url("draft/batchget", access_token),
            {"offset": 0, "count": 20, "no_content": 0},
        )
    except Exception:
        return None
    for item in data.get("item", []) or []:
        if item.get("media_id") != media_id:
            continue
        content = item.get("content") or {}
        news_items = content.get("news_item") or []
        if news_items and news_items[0].get("url"):
            return str(news_items[0]["url"])
    return None


def submit_publish(payload: dict[str, Any], access_token: str, media_id: str | None = None) -> dict[str, Any]:
    media_id = media_id or payload.get("media_id")
    if not media_id:
        raise UsageError("缺少草稿 media_id，无法发布。")
    if not bool(payload.get("confirm_publish")):
        raise UsageError("正式发布前必须取得用户明确确认，并在 payload.confirm_publish=true 后再调用发布。")
    data = http_json("POST", api_url("freepublish/submit", access_token), {"media_id": media_id})
    publish_id = data.get("publish_id")
    if not publish_id:
        raise WeChatAPIError(data)
    return {
        "submitted": True,
        "publish_id": publish_id,
        "msg_data_id": data.get("msg_data_id"),
        "response": data,
    }


def get_publish_status(payload: dict[str, Any], access_token: str, publish_id: str | None = None) -> dict[str, Any]:
    publish_id = publish_id or payload.get("publish_id")
    if not publish_id:
        raise UsageError("缺少 publish_id，无法查询发布状态。")
    data = http_json("POST", api_url("freepublish/get", access_token), {"publish_id": publish_id})
    return data


def user_next_message(result: dict[str, Any]) -> str:
    if result.get("error"):
        return str(result.get("friendly_message") or result.get("error"))

    pieces: list[str] = []
    setup = result.get("setup") or {}
    config = result.get("config") or {}
    draft = result.get("draft") or {}
    publish = result.get("publish") or {}
    publish_status = result.get("publish_status") or {}

    if setup:
        pieces.append("公众号 AppID/AppSecret 已安全保存到本机。")
        observed_ips = setup.get("observed_public_ips") or []
        recommendation = setup.get("ip_whitelist_recommendation")
        if observed_ips:
            pieces.append(
                f"预检测公网出口 IP：{'、'.join(observed_ips)}（仅供参考）。"
            )
        if recommendation:
            pieces.append(
                f"出口 IP 会在同一网段内轮换，建议直接把整个网段 {recommendation} 加入 API IP 白名单（微信支持 /24 CIDR），不要逐个加 IP。"
            )
        pieces.append("请运行验证；若仍失败，以微信错误中 invalid ip 后 IP 所在的 /24 网段加白。")
        pieces.append(f"微信开发者平台：{WECHAT_DEVELOPER_PLATFORM_URL}")
        pieces.append("加白完成后，我会验证配置并继续创建草稿。")
    if config:
        if config.get("verified"):
            pieces.append("公众号直连配置已通过微信接口验证，可以继续创建草稿。")
        elif config.get("access_token_configured") or (
            config.get("appid_configured") and config.get("appsecret_configured")
        ):
            pieces.append(f"微信开发者平台：{WECHAT_DEVELOPER_PLATFORM_URL}")
            pieces.append("路径：微信开发者平台 → 前往控制台 → 我的业务与服务 → 公众号 → 基础信息 → 开发密钥")
            pieces.append("公众号直连配置已存在；请运行验证，确认 IP 白名单已经生效。")
            observed_ips = config.get("observed_public_ips") or []
            recommendation = config.get("ip_whitelist_recommendation")
            if observed_ips:
                pieces.append(f"预检测公网出口 IP：{observed_ips[0]}（仅供参考）。")
            if recommendation:
                pieces.append(
                    f"出口 IP 会在同一网段内轮换，建议直接把整个网段 {recommendation} 加入 API IP 白名单（微信支持 /24 CIDR），不要逐个加 IP。"
                )
        else:
            pieces.append(f"微信开发者平台：{WECHAT_DEVELOPER_PLATFORM_URL}")
            pieces.append("路径：微信开发者平台 → 前往控制台 → 我的业务与服务 → 公众号 → 基础信息")
            pieces.append("AppID 在“基础信息”；AppSecret 和 API IP 白名单在“开发密钥”。")
            pieces.append(
                "若启用 AppSecret 时提示“尚未完成实名”：个人主体请到微信公众平台 "
                "https://mp.weixin.qq.com/ 的“设置与开发 → 人员设置 → 管理员信息”完成管理员实名。"
            )
            observed_ips = config.get("observed_public_ips") or []
            recommendation = config.get("ip_whitelist_recommendation")
            if observed_ips:
                pieces.append(f"预检测公网出口 IP：{'、'.join(observed_ips)}（仅供参考）。")
            if recommendation:
                pieces.append(
                    f"出口 IP 会在同一网段内轮换，建议直接把整个网段 {recommendation} 加入 API IP 白名单（微信支持 /24 CIDR），不要逐个加 IP。"
                )
            pieces.append("获取 AppID/AppSecret 后，可直接提供给我用于本次发布，或选择保存到本地。")
            pieces.append(f"AppID/AppSecret 说明：{WECHAT_APPID_SECRET_DOC_URL}")
            pieces.append(f"API IP 白名单说明：{WECHAT_IP_WHITELIST_DOC_URL}")
    if draft:
        pieces.append(f"草稿已创建：{draft.get('title')}")
        if draft.get("url"):
            pieces.append(f"草稿临时预览链接：{draft['url']}")
        else:
            pieces.append("草稿已保存，但接口未返回临时预览链接；可在公众号后台草稿箱中查看。")
        pieces.append(
            "下一步：\n"
            "- Agent 必须紧接着用浏览器打开 https://mp.weixin.qq.com/ ，登录后进入"
            "「内容管理 → 草稿箱」，按标题定位并点开本篇草稿，让用户直接在编辑器中确认或点「发表」。\n"
            "- 如果是已认证企业号且用户要求发表：回复 \"确认发布\"，通过接口正式发布。\n"
            "- 如果是个人号或未认证号：在自动打开的编辑器右下角直接点「发表」。"
        )
    if publish:
        pieces.append(f"发布任务已提交，publish_id：{publish.get('publish_id')}")
    if publish_status:
        status = publish_status.get("publish_status")
        status_text = {
            0: "发布成功",
            1: "发布中",
            2: "原创失败",
            3: "常规失败",
            4: "平台审核不通过",
            5: "成功后用户删除所有文章",
            6: "成功后系统封禁所有文章",
        }.get(status, f"未知状态 {status}")
        pieces.append(f"发布状态：{status_text}")
        article_detail = publish_status.get("article_detail") or {}
        items = article_detail.get("item") or []
        if items and items[0].get("article_url"):
            pieces.append(f"文章链接：{items[0]['article_url']}")
    if not pieces:
        pieces.append("接口调用完成。")
    return "\n".join(pieces)


def run(args: argparse.Namespace) -> dict[str, Any]:
    payload = load_json_file(args.payload)
    cli_payload = {
        key: value
        for key, value in {
            "appid": args.appid,
            "appsecret": args.appsecret,
            "config_path": args.config_path,
            "title": args.title,
            "markdown_path": args.markdown_path,
            "cover_path": args.cover_path,
            "media_id": args.media_id,
            "publish_id": args.publish_id,
            "publish_package_path": args.publish_package,
        }.items()
        if value is not None
    }
    package_path = cli_payload.get("publish_package_path") or payload.get("publish_package_path")
    if package_path:
        payload["publish_package_path"] = package_path
        payload = {**payload, **load_publish_package(payload)}
    payload.update(cli_payload)
    if args.confirm_publish:
        payload["confirm_publish"] = True
    if args.publish:
        payload["publish"] = True

    result: dict[str, Any] = {
        "ok": True,
        "action": args.action,
    }
    if args.action == "setup-local":
        result["setup"] = configure_local(payload)
        result["next_user_message"] = user_next_message(result)
        return result

    payload = merge_local_config(payload)
    if args.action == "check-config":
        result["config"] = {
            "access_token_configured": bool(payload.get("access_token") or os.getenv("WECHAT_MP_ACCESS_TOKEN")),
            "appid_configured": bool(payload.get("appid")),
            "appsecret_configured": bool(payload.get("appsecret")),
            "config_path": payload.get("config_path"),
            "secret_storage": payload.get("secret_storage"),
            **get_public_ip_snapshot(),
        }
        result["next_user_message"] = user_next_message(result)
        return result
    if args.action == "verify-config":
        result["config"] = verify_direct_config(payload)
        result["next_user_message"] = user_next_message(result)
        return result
    if args.action == "preflight":
        result["preflight"] = preflight(payload)
        result["preflight"]["source"] = (
            "publish_package"
            if payload.get("publish_package_path")
            else "legacy_markdown_or_html"
        )
        if not payload.get("publish_package_path"):
            result["preflight"]["warnings"].append(
                "当前使用兼容输入 markdown_path/markdown/content_html。正式发布建议改用 publish_package。"
            )
        result["next_user_message"] = "稿件预检完成。通过后可在公众号配置验证成功时创建草稿。"
        return result

    artifact_dir = ensure_artifact_dir(payload)
    warnings: list[str] = []
    access_token, token_warnings = get_access_token(payload, artifact_dir, bool(args.force_refresh))
    warnings.extend(token_warnings)
    result["warnings"] = warnings
    result["artifact_dir"] = str(artifact_dir)
    media_id = str(payload.get("media_id") or "") or None

    if args.action in ("create-draft", "workflow"):
        draft = create_draft(payload, access_token, artifact_dir, warnings)
        result["draft"] = draft
        media_id = str(draft["media_id"])
    if args.action in ("publish", "workflow") and (args.action == "publish" or payload.get("publish")):
        publish = submit_publish(payload, access_token, media_id)
        result["publish"] = publish
        if args.poll_seconds > 0:
            deadline = time.time() + args.poll_seconds
            while True:
                status = get_publish_status(payload, access_token, str(publish["publish_id"]))
                result["publish_status"] = status
                if status.get("publish_status") != 1:
                    break
                if time.time() >= deadline:
                    break
                time.sleep(args.poll_interval)
    if args.action == "status":
        result["publish_status"] = get_publish_status(payload, access_token, payload.get("publish_id"))
    result["next_user_message"] = user_next_message(result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WeChat Official Account API publisher")
    parser.add_argument(
        "action",
        choices=[
            "setup-local",
            "check-config",
            "verify-config",
            "preflight",
            "create-draft",
            "publish",
            "status",
            "workflow",
        ],
        help="API action to execute",
    )
    parser.add_argument("--payload", help="JSON payload path")
    parser.add_argument("--out", help="write result JSON to this path as well as stdout")
    parser.add_argument("--appid", help="Official Account AppID")
    parser.add_argument(
        "--appsecret",
        help="Official Account AppSecret",
    )
    parser.add_argument("--config-path", help="override local config path")
    parser.add_argument("--title", help="article title")
    parser.add_argument("--markdown-path", help="article markdown file path")
    parser.add_argument(
        "--publish-package",
        help="canonical publish package JSON path; overrides body fields from --payload",
    )
    parser.add_argument("--cover-path", help="cover image file path")
    parser.add_argument("--media-id", help="draft media_id")
    parser.add_argument("--publish-id", help="publish task id")
    parser.add_argument("--publish", action="store_true", help="submit publish during workflow")
    parser.add_argument("--confirm-publish", action="store_true", help="required for publish")
    parser.add_argument("--force-refresh", action="store_true", help="force refresh access token")
    parser.add_argument("--poll-seconds", type=int, default=0, help="poll publish status after submit")
    parser.add_argument("--poll-interval", type=int, default=5, help="publish status poll interval")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = run(args)
    except WeChatAPIError as exc:
        result = {
            "ok": False,
            "error_type": "wechat_api_error",
            "error": str(exc),
            "api_response": exc.payload,
            "friendly_message": friendly_api_message(exc.payload),
        }
        result["next_user_message"] = user_next_message(result)
        write_json(args.out, result)
        return 2
    except UsageError as exc:
        result = {
            "ok": False,
            "error_type": "usage_error",
            "error": str(exc),
            "friendly_message": str(exc),
        }
        result["next_user_message"] = user_next_message(result)
        write_json(args.out, result)
        return 2
    except Exception as exc:  # keep CLI failure structured for the agent
        result = {
            "ok": False,
            "error_type": exc.__class__.__name__,
            "error": str(exc),
            "friendly_message": "发布脚本执行失败，请查看 error 字段并修复后重试。",
        }
        result["next_user_message"] = user_next_message(result)
        write_json(args.out, result)
        return 1

    write_json(args.out, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
