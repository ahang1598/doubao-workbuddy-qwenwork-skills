#!/usr/bin/env python3
"""虚拟试衣间 CLI 脚本。

封装试衣间 API 调用，提供子命令：
  tmpcode      - 获取临时鉴权码 tmpCode
  init         - 初始化试衣间，获取 storeId
  upload       - 上传衣服信息，获取 serialNo
  run          - 一步完成 tmpcode + init + upload，输出最终试衣链接
  store-update - 更新店铺信息

输出: JSON（ensure_ascii=False）
退出码: 0=成功, 1=API 错误, 2=参数错误
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import urllib.error
import urllib.request

TEAMBITION_HOST = "https://ai.teambition.net"
# TEAMBITION_HOST = "http://127.0.0.1:7100"

BASE_URL = f"{TEAMBITION_HOST}/api/opt/soa/dress-mirror"
STORE_URL_TEMPLATE = f"{TEAMBITION_HOST}/api/opt/store/{{tmp_token}}"
DEFAULT_MINI_QRCODE_FILENAME = "store_mini_qrcode.png"

REQUEST_TIMEOUT = 30  # 秒
REQUEST_HEADERS = {} #{"X-Canary": "prepub"}


# ── 工具函数 ──────────────────────────────────────────────────────────────────

DWS_SEARCH_PATHS = [
    "~/.qoderwork/bin/dws",
    "~/.local/bin/dws",
    "dws",
]

def print_json(data: dict) -> None:
    """将字典以格式化 JSON 输出到 stdout。"""
    print(json.dumps(data, ensure_ascii=False, indent=2))

def exit_with_error(message: str, code: int = 1) -> None:
    """输出错误 JSON 并以指定退出码退出。"""
    print_json({"success": False, "error": message})
    sys.exit(code)


class HttpResponse:
    """urllib 响应的简单封装，提供与 httpx.Response 兼容的接口。"""

    def __init__(self, status_code: int, body: bytes, headers: dict[str, str]):
        self.status_code = status_code
        self.content = body
        self.headers = headers

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")

    def json(self) -> dict:
        return json.loads(self.content)


def http_post(url: str, payload: dict, headers: dict | None = None, timeout: int = REQUEST_TIMEOUT) -> HttpResponse:
    """使用 urllib.request 发送 JSON POST 请求，返回 HttpResponse。"""
    request_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    merged_headers = {"Content-Type": "application/json; charset=utf-8"}
    if headers:
        merged_headers.update(headers)

    req = urllib.request.Request(url, data=request_body, headers=merged_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            resp_headers = {key.lower(): value for key, value in resp.getheaders()}
            return HttpResponse(resp.status, body, resp_headers)
    except urllib.error.HTTPError as error:
        body = error.read() if error.fp else b""
        resp_headers = {key.lower(): value for key, value in error.headers.items()}
        return HttpResponse(error.code, body, resp_headers)
    except urllib.error.URLError as error:
        if "timed out" in str(error.reason):
            raise TimeoutError(f"请求超时: {url}") from error
        raise ConnectionError(f"网络请求失败: {error.reason}") from error

def resolve_dws_binary() -> str:
    """查找 dws 可执行文件路径，优先使用已知安装路径。"""
    from pathlib import Path
    for candidate in DWS_SEARCH_PATHS:
        expanded = str(Path(candidate).expanduser())
        if Path(expanded).is_file():
            return expanded
    found = shutil.which("dws")
    if found:
        return found
    exit_with_error(
        "找不到 dws 命令，请确认已安装 dws CLI 工具。"
        "可尝试手动指定 --corp-id 参数跳过自动获取。"
    )
    return ""  # unreachable, exit_with_error calls sys.exit

def fetch_corp_id_from_dws() -> str:
    """通过 dws auth status --format json 自动获取 corpId。"""
    dws_bin = resolve_dws_binary()
    try:
        result = subprocess.run(
            [dws_bin, "auth", "status", "--format", "json"],
            capture_output=True, text=True, timeout=15,
        )
    except FileNotFoundError:
        exit_with_error(f"dws 命令不存在: {dws_bin}，请手动指定 --corp-id")
    except subprocess.TimeoutExpired:
        exit_with_error("执行 dws auth status 超时，请手动指定 --corp-id")

    if result.returncode != 0:
        exit_with_error(f"dws auth status 执行失败 (exit={result.returncode}): {result.stderr.strip()}")

    try:
        auth_info = json.loads(result.stdout)
    except json.JSONDecodeError:
        exit_with_error(f"dws auth status 输出解析失败: {result.stdout[:500]}")

    if not auth_info.get("success") or not auth_info.get("authenticated"):
        exit_with_error("dws 未登录或认证已过期，请先执行 dws auth login 登录后重试")

    corp_id = auth_info.get("corp_id", "")
    if not corp_id:
        exit_with_error(f"dws auth status 响应中缺少 corp_id: {json.dumps(auth_info, ensure_ascii=False)}")

    return corp_id


def fetch_user_info_from_dws() -> dict:
    """通过 dws contact user get-self获取当前用户信息。

    返回包含 corpId, staffId, orgUserName, orgUserMobile, orgName 的字典。
    """
    dws_bin = resolve_dws_binary()
    try:
        result = subprocess.run(
            [dws_bin, "contact", "user", "get-self"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=15,
        )
    except FileNotFoundError:
        exit_with_error(f"dws 命令不存在: {dws_bin}")
    except subprocess.TimeoutExpired:
        exit_with_error("执行 dws contact user get-self 超时，请重试")

    if result.returncode != 0:
        exit_with_error(
            f"dws contact user get-self 执行失败 (exit={result.returncode}): {result.stderr.strip()}"
        )

    try:
        user_data = json.loads(result.stdout)
    except json.JSONDecodeError:
        exit_with_error(f"dws contact user get-self 输出解析失败: {result.stdout[:500]}")

    if not user_data.get("success"):
        exit_with_error(f"dws contact user get-self 返回失败: {json.dumps(user_data, ensure_ascii=False)}")

    results = user_data.get("result", [])
    if not results:
        exit_with_error("dws contact user get-self 返回结果为空")

    emp_model = results[0].get("orgEmployeeModel", {})
    if not emp_model:
        exit_with_error("dws contact user get-self 响应中缺少 orgEmployeeModel")

    corp_id = emp_model.get("corpId", "")
    staff_id = emp_model.get("userId", "")
    if not corp_id or not staff_id:
        exit_with_error(
            f"dws contact user get-self 响应中缺少 corpId 或 userId: "
            f"{json.dumps(emp_model, ensure_ascii=False)}"
        )

    return {
        "corpId": corp_id,
        "staffId": staff_id,
        "orgUserName": emp_model.get("orgUserName", ""),
        "orgUserMobile": emp_model.get("orgUserMobile", ""),
        "orgName": emp_model.get("orgName", ""),
    }


def resolve_corp_id(args: argparse.Namespace) -> str:
    """获取 corpId：优先使用命令行参数，否则自动从 dws 获取。"""
    if hasattr(args, "corp_id") and args.corp_id:
        return args.corp_id
    return fetch_corp_id_from_dws()


def resolve_user_info(args: argparse.Namespace) -> dict:
    """获取用户信息：优先使用命令行参数，否则自动从 dws contact user get-self 获取。

    返回包含 corpId, staffId, orgUserName, orgUserMobile, orgName 的字典。
    """
    has_corp_id = hasattr(args, "corp_id") and args.corp_id
    has_staff_id = hasattr(args, "staff_id") and args.staff_id

    if has_corp_id and has_staff_id:
        return {
            "corpId": args.corp_id,
            "staffId": args.staff_id,
            "orgUserName": getattr(args, "org_user_name", "") or "",
            "orgUserMobile": getattr(args, "org_user_mobile", "") or "",
            "orgName": getattr(args, "org_name", "") or "",
        }

    user_info = fetch_user_info_from_dws()
    if has_corp_id:
        user_info["corpId"] = args.corp_id
    if has_staff_id:
        user_info["staffId"] = args.staff_id
    return user_info

# ── API 调用 ──────────────────────────────────────────────────────────────────

def api_tmp_code(
    corp_id: str,
    staff_id: str,
    org_user_name: str = "",
    org_user_mobile: str = "",
    org_name: str = "",
) -> str:
    """
    调用临时鉴权码接口，返回 tmpCode。

    POST {TEAMBITION_HOST}/api/opt/soa/dress-mirror/tmpCode
    """
    url = f"{BASE_URL}/tmpCode"
    payload: dict = {
        "corpId": corp_id,
        "staffId": staff_id,
    }
    if org_user_name:
        payload["orgUserName"] = org_user_name
    if org_user_mobile:
        payload["orgUserMobile"] = org_user_mobile
    if org_name:
        payload["orgName"] = org_name

    try:
        response = http_post(url, payload, headers=REQUEST_HEADERS)
    except TimeoutError:
        exit_with_error("请求超时，请检查网络连接后重试")
    except ConnectionError as error:
        exit_with_error(f"网络请求失败: {error}")

    if response.status_code >= 400:
        exit_with_error(f"HTTP 错误 {response.status_code}: {response.text}")

    try:
        body = response.json()
    except Exception:
        exit_with_error(f"响应解析失败，原始内容: {response.text}")

    if not body.get("success"):
        exit_with_error(f"API 返回失败: {json.dumps(body, ensure_ascii=False)}")

    tmp_code = body.get("result", {}).get("tmpCode")
    if not tmp_code:
        exit_with_error(f"响应中缺少 tmpCode 字段: {json.dumps(body, ensure_ascii=False)}")

    return tmp_code


def api_init(corp_id: str, tmp_code: str) -> str:
    """
    调用初始化接口，返回 storeId。

    POST {TEAMBITION_HOST}/api/opt/soa/dress-mirror/init
    """
    url = f"{BASE_URL}/init"
    payload = {"corpId": corp_id, "tmpCode": tmp_code}

    try:
        response = http_post(url, payload, headers=REQUEST_HEADERS)
    except TimeoutError:
        exit_with_error("请求超时，请检查网络连接后重试")
    except ConnectionError as error:
        exit_with_error(f"网络请求失败: {error}")

    if response.status_code >= 400:
        exit_with_error(f"HTTP 错误 {response.status_code}: {response.text}")

    try:
        body = response.json()
    except Exception:
        exit_with_error(f"响应解析失败，原始内容: {response.text}")

    if not body.get("success"):
        exit_with_error(f"API 返回失败: {json.dumps(body, ensure_ascii=False)}")

    tmp_token = body.get("result", {}).get("storeId")
    if not tmp_token:
        exit_with_error(f"响应中缺少 storeId 字段: {json.dumps(body, ensure_ascii=False)}")

    return tmp_token


def api_fetch_store_qrcode(corp_id: str, tmp_code: str, output_path: Path) -> Path:
    """
    调用二维码生成接口，下载 PNG 图片并保存到本地。

    POST {TEAMBITION_HOST}/api/opt/soa/dress-mirror/qrcode
    返回 image/png 二进制流。
    """
    url = f"{BASE_URL}/qrcode"
    payload = {"corpId": corp_id, "tmpCode": tmp_code}

    try:
        response = http_post(url, payload, headers=REQUEST_HEADERS)
    except TimeoutError:
        exit_with_error("请求超时，请检查网络连接后重试")
    except ConnectionError as error:
        exit_with_error(f"网络请求失败: {error}")

    if response.status_code >= 400:
        exit_with_error(f"HTTP 错误 {response.status_code}: {response.text}")

    content_type = response.headers.get("content-type", "")
    if "image/png" not in content_type.lower():
        try:
            body = response.json()
            exit_with_error(f"二维码接口返回失败: {json.dumps(body, ensure_ascii=False)}")
        except Exception:
            exit_with_error(f"二维码接口返回非 PNG 内容: {response.text[:500]}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)
    return output_path

def api_fetch_miniprogram_qrcode(corp_id: str, tmp_code: str, output_path: Path) -> Path:
    """
    调用小程序太阳码生成接口，下载 PNG 图片并保存到本地。

    POST {TEAMBITION_HOST}/api/opt/soa/dress-mirror/miniprogram-qrcode
    返回 image/png 二进制流。
    """
    url = f"{BASE_URL}/miniprogram-qrcode"
    payload: dict = {"corpId": corp_id, "tmpCode": tmp_code}

    try:
        response = http_post(url, payload, headers=REQUEST_HEADERS)
    except TimeoutError:
        exit_with_error("请求超时，请检查网络连接后重试")
    except ConnectionError as error:
        exit_with_error(f"网络请求失败: {error}")

    if response.status_code >= 400:
        exit_with_error(f"HTTP 错误 {response.status_code}: {response.text}")

    content_type = response.headers.get("content-type", "")
    if "image/png" not in content_type.lower():
        try:
            body = response.json()
            exit_with_error(f"小程序太阳码接口返回失败: {json.dumps(body, ensure_ascii=False)}")
        except Exception:
            exit_with_error(f"小程序太阳码接口返回非 PNG 内容: {response.text[:500]}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)
    return output_path

def api_upload_clothes(
    corp_id: str,
    tmp_code: str,
    name: str,
    image_url: str,
    desc: str,
    category: str,
    color: str,
    style: str,
    features: list[str],
    occasion: list[str],
    season: list[str],
    selling_points: str = "",
) -> dict:
    """
    调用衣服上传接口，返回完整的衣服信息字典（含 serialNo）。

    POST {TEAMBITION_HOST}/api/opt/soa/dress-mirror/clothes/upload
    """
    url = f"{BASE_URL}/clothes/upload"
    payload = {
        "corpId": corp_id,
        "tmpCode": tmp_code,
        "name": name,
        "imageUrl": image_url,
        "desc": desc,
        "category": category,
        "color": color,
        "style": style,
        "features": features,
        "occasion": occasion,
        "season": season,
        "sellingPoints": selling_points,
    }

    try:
        response = http_post(url, payload, headers=REQUEST_HEADERS)
    except TimeoutError:
        exit_with_error("请求超时，请检查网络连接后重试")
    except ConnectionError as error:
        exit_with_error(f"网络请求失败: {error}")

    if response.status_code >= 400:
        exit_with_error(f"HTTP 错误 {response.status_code}: {response.text}")

    try:
        body = response.json()
    except Exception:
        exit_with_error(f"响应解析失败，原始内容: {response.text}")

    if not body.get("success"):
        exit_with_error(f"API 返回失败: {json.dumps(body, ensure_ascii=False)}")

    result = body.get("result")
    if not result:
        exit_with_error(f"响应中缺少 result 字段: {json.dumps(body, ensure_ascii=False)}")

    if "serialNo" not in result:
        exit_with_error(f"响应中缺少 serialNo 字段: {json.dumps(body, ensure_ascii=False)}")
    return result


def api_update_store(
    corp_id: str,
    tmp_code: str,
    shop_name: str = "",
    wechat: str = "",
    shop_address: str = "",
    slogan: str = "",
    shop_image_url: str = "",
    shop_video_url: str = "",
    shop_logo_url: str = "",
) -> dict:
    """
    调用店铺信息更新接口。

    POST {TEAMBITION_HOST}/api/opt/soa/dress-mirror/store/update
    """
    url = f"{BASE_URL}/store/update"
    payload: dict = {"corpId": corp_id, "tmpCode": tmp_code}
    if shop_name:
        payload["shopName"] = shop_name
    if wechat:
        payload["wechat"] = wechat
    if shop_address:
        payload["shopAddress"] = shop_address
    if slogan:
        payload["slogan"] = slogan
    if shop_image_url:
        payload["shopImageUrl"] = shop_image_url
    if shop_video_url:
        payload["shopVideoUrl"] = shop_video_url
    if shop_logo_url:
        payload["shopLogoUrl"] = shop_logo_url

    try:
        response = http_post(url, payload, headers=REQUEST_HEADERS)
    except TimeoutError:
        exit_with_error("请求超时，请检查网络连接后重试")
    except ConnectionError as error:
        exit_with_error(f"网络请求失败: {error}")

    if response.status_code >= 400:
        exit_with_error(f"HTTP 错误 {response.status_code}: {response.text}")

    try:
        body = response.json()
    except Exception:
        exit_with_error(f"响应解析失败，原始内容: {response.text}")

    if not body.get("success"):
        exit_with_error(f"API 返回失败: {json.dumps(body, ensure_ascii=False)}")

    return body.get("result", {})

def api_get_store_detail(
    corp_id: str,
    tmp_code: str,
) -> dict:
    """
    调用获取店铺详情接口。

    POST {TEAMBITION_HOST}/api/opt/soa/dress-mirror/store/detail
    """
    url = f"{BASE_URL}/store/detail"
    payload = {"corpId": corp_id, "tmpCode": tmp_code}

    try:
        response = http_post(url, payload, headers=REQUEST_HEADERS)
    except TimeoutError:
        exit_with_error("请求超时，请检查网络连接后重试")
    except ConnectionError as error:
        exit_with_error(f"网络请求失败: {error}")

    if response.status_code >= 400:
        exit_with_error(f"HTTP 错误 {response.status_code}: {response.text}")

    try:
        body = response.json()
    except Exception:
        exit_with_error(f"响应解析失败，原始内容: {response.text}")

    if not body.get("success"):
        exit_with_error(f"API 返回失败: {json.dumps(body, ensure_ascii=False)}")

    return body.get("result", {})


def api_update_sku_source(
    corp_id: str,
    tmp_code: str,
    sku_source: str = "",
    aitable_url: str = "",
) -> dict:
    """
    调用 SKU 数据源切换接口。

    POST {TEAMBITION_HOST}/api/opt/soa/dress-mirror/store/sku-source
    """
    url = f"{BASE_URL}/store/sku-source"
    payload: dict = {"corpId": corp_id, "tmpCode": tmp_code}
    if sku_source:
        payload["skuSource"] = sku_source
    if aitable_url:
        payload["aitableUrl"] = aitable_url

    try:
        response = http_post(url, payload, headers=REQUEST_HEADERS)
    except TimeoutError:
        exit_with_error("请求超时，请检查网络连接后重试")
    except ConnectionError as error:
        exit_with_error(f"网络请求失败: {error}")

    if response.status_code >= 400:
        exit_with_error(f"HTTP 错误 {response.status_code}: {response.text}")

    try:
        body = response.json()
    except Exception:
        exit_with_error(f"响应解析失败，原始内容: {response.text}")

    if not body.get("success"):
        exit_with_error(f"API 返回失败: {json.dumps(body, ensure_ascii=False)}")

    return body.get("result", {})


def api_publish_style_note(
    corp_id: str,
    tmp_code: str,
    title: str,
    content: str,
    images: list[str],
    product_ids: list[str],
    tags: list[str],
    target_audience: str = "",
    note_intent: str = "",
    author_name: str = "官方搭配师",
) -> dict:
    """
    调用穿搭笔记发布接口，返回发布结果。

    POST {TEAMBITION_HOST}/api/opt/soa/dress-mirror/style-notes/create
    """
    url = f"{BASE_URL}/style-notes/create"
    payload: dict = {
        "corpId": corp_id,
        "tmpCode": tmp_code,
        "title": title,
        "content": content,
        "images": images,
        "productIds": product_ids,
        "tags": tags,
        "author": {"displayName": author_name},
    }
    if target_audience:
        payload["targetAudience"] = target_audience
    if note_intent:
        payload["noteIntent"] = note_intent

    try:
        response = http_post(url, payload, headers=REQUEST_HEADERS)
    except TimeoutError:
        exit_with_error("请求超时，请检查网络连接后重试")
    except ConnectionError as error:
        exit_with_error(f"网络请求失败: {error}")

    if response.status_code >= 400:
        exit_with_error(f"HTTP 错误 {response.status_code}: {response.text}")

    try:
        body = response.json()
    except Exception:
        exit_with_error(f"响应解析失败，原始内容: {response.text}")

    if not body.get("success"):
        exit_with_error(f"API 返回失败: {json.dumps(body, ensure_ascii=False)}")

    return body.get("result", {})

def api_list_orders(
    corp_id: str,
    tmp_code: str,
) -> list:
    """
    调用店主端订单列表查询接口。

    POST {TEAMBITION_HOST}/api/opt/soa/dress-mirror/orders/list
    """
    url = f"{BASE_URL}/orders/list"
    payload = {"corpId": corp_id, "tmpCode": tmp_code}

    try:
        response = http_post(url, payload, headers=REQUEST_HEADERS)
    except TimeoutError:
        exit_with_error("请求超时，请检查网络连接后重试")
    except ConnectionError as error:
        exit_with_error(f"网络请求失败: {error}")

    if response.status_code >= 400:
        exit_with_error(f"HTTP 错误 {response.status_code}: {response.text}")

    try:
        body = response.json()
    except Exception:
        exit_with_error(f"响应解析失败，原始内容: {response.text}")

    if not body.get("success"):
        exit_with_error(f"API 返回失败: {json.dumps(body, ensure_ascii=False)}")

    return body.get("result", []) or []


def api_update_order_status(
    corp_id: str,
    tmp_code: str,
    order_id: str,
    status: str,
) -> dict:
    """
    调用店主端订单状态更新接口。

    POST {TEAMBITION_HOST}/api/opt/soa/dress-mirror/orders/update-status
    """
    url = f"{BASE_URL}/orders/update-status"
    payload = {
        "corpId": corp_id,
        "tmpCode": tmp_code,
        "orderId": order_id,
        "status": status,
    }

    try:
        response = http_post(url, payload, headers=REQUEST_HEADERS)
    except TimeoutError:
        exit_with_error("请求超时，请检查网络连接后重试")
    except ConnectionError as error:
        exit_with_error(f"网络请求失败: {error}")

    if response.status_code >= 400:
        exit_with_error(f"HTTP 错误 {response.status_code}: {response.text}")

    try:
        body = response.json()
    except Exception:
        exit_with_error(f"响应解析失败，原始内容: {response.text}")

    if not body.get("success"):
        exit_with_error(f"API 返回失败: {json.dumps(body, ensure_ascii=False)}")

    return body.get("result", {})


def api_ensure_aitable(
    corp_id: str,
    tmp_code: str,
) -> dict:
    """
    调用 ensure-aitable 接口，确保店铺多维表已创建。
    已有则直接返回 dentryUuid，否则自动创建并返回。

    POST {TEAMBITION_HOST}/api/opt/soa/dress-mirror/ensure-aitable
    """
    url = f"{BASE_URL}/ensure-aitable"
    payload = {"corpId": corp_id, "tmpCode": tmp_code}

    try:
        response = http_post(url, payload, headers=REQUEST_HEADERS)
    except TimeoutError:
        exit_with_error("请求超时，请检查网络连接后重试")
    except ConnectionError as error:
        exit_with_error(f"网络请求失败: {error}")

    if response.status_code >= 400:
        exit_with_error(f"HTTP 错误 {response.status_code}: {response.text}")

    try:
        body = response.json()
    except Exception:
        exit_with_error(f"响应解析失败，原始内容: {response.text}")

    if not body.get("success"):
        exit_with_error(f"API 返回失败: {json.dumps(body, ensure_ascii=False)}")

    return body.get("result", {})


# ── 子命令处理 ────────────────────────────────────────────────────────────────

def cmd_tmpcode(args: argparse.Namespace) -> None:
    """子命令 tmpcode：获取临时鉴权码 tmpCode。"""
    user_info = resolve_user_info(args)
    tmp_code = api_tmp_code(
        corp_id=user_info["corpId"],
        staff_id=user_info["staffId"],
        org_user_name=user_info["orgUserName"],
        org_user_mobile=user_info["orgUserMobile"],
        org_name=user_info["orgName"],
    )
    print_json({"success": True, "tmpCode": tmp_code, "corpId": user_info["corpId"]})


def resolve_tmp_code(args: argparse.Namespace, corp_id: str) -> str:
    """获取 tmpCode：优先使用命令行参数，否则自动通过 /tmpCode 接口获取。"""
    if hasattr(args, "tmp_code") and args.tmp_code:
        return args.tmp_code
    user_info = resolve_user_info(args)
    return api_tmp_code(
        corp_id=corp_id,
        staff_id=user_info["staffId"],
        org_user_name=user_info["orgUserName"],
        org_user_mobile=user_info["orgUserMobile"],
        org_name=user_info["orgName"],
    )


def cmd_init(args: argparse.Namespace) -> None:
    """子命令 init：初始化试衣间，并生成店铺 H5 二维码和小程序太阳码。

    - 调用 /init 完成店铺初始化
    - 调用 /qrcode 接口下载 H5 二维码 PNG 到本地
    - 调用 /miniprogram-qrcode 接口下载小程序太阳码 PNG 到本地
    - 输出 qrcode_path 和 mini_qrcode_path
    """
    corp_id = resolve_corp_id(args)
    tmp_code = resolve_tmp_code(args, corp_id)
    api_init(corp_id=corp_id, tmp_code=tmp_code)

    # 小程序太阳码
    mini_output_arg = getattr(args, "mini_output", "") or DEFAULT_MINI_QRCODE_FILENAME
    mini_output_path = Path(mini_output_arg).resolve()
    mini_saved_path = api_fetch_miniprogram_qrcode(
        corp_id=corp_id,
        tmp_code=tmp_code,
        output_path=mini_output_path,
    )

    print_json({
        "success": True,
        "mini_qrcode_path": str(mini_saved_path),
    })


def cmd_upload(args: argparse.Namespace) -> None:
    """子命令 upload：上传衣服信息，输出衣服详情（不含试衣链接，需配合 init 使用）。"""
    corp_id = resolve_corp_id(args)
    tmp_code = resolve_tmp_code(args, corp_id)
    validate_image_url(args.image_url)
    clothes = api_upload_clothes(
        corp_id=corp_id,
        tmp_code=tmp_code,
        name=args.name,
        image_url=args.image_url,
        desc=args.desc,
        category=args.category,
        color=args.color,
        style=args.style,
        features=args.features,
        occasion=args.occasion,
        season=args.season,
    )
    print_json({"success": True, "clothes": clothes})


def cmd_store_update(args: argparse.Namespace) -> None:
    """子命令 store-update：更新店铺信息（店铺名称、微信号、店铺地址、店主说、店铺照片、店铺视频、店铺 logo）。"""
    corp_id = resolve_corp_id(args)
    tmp_code = resolve_tmp_code(args, corp_id)
    result = api_update_store(
        corp_id=corp_id,
        tmp_code=tmp_code,
        shop_name=args.shop_name or "",
        wechat=args.wechat or "",
        shop_address=args.shop_address or "",
        slogan=getattr(args, "slogan", "") or "",
        shop_image_url=getattr(args, "shop_image_url", "") or "",
        shop_video_url=getattr(args, "shop_video_url", "") or "",
        shop_logo_url=getattr(args, "shop_logo_url", "") or "",
    )
    print_json({"success": True, "store": result})


def cmd_store_detail(args: argparse.Namespace) -> None:
    """子命令 store-detail：获取店铺详情（含多维表配置信息）。"""
    corp_id = resolve_corp_id(args)
    tmp_code = resolve_tmp_code(args, corp_id)
    result = api_get_store_detail(corp_id=corp_id, tmp_code=tmp_code)
    print_json({"success": True, "store": result})


def cmd_ensure_aitable(args: argparse.Namespace) -> None:
    """子命令 ensure-aitable：确保店铺多维表已创建，返回 aitableDentryUuid。"""
    corp_id = resolve_corp_id(args)
    tmp_code = resolve_tmp_code(args, corp_id)
    result = api_ensure_aitable(corp_id=corp_id, tmp_code=tmp_code)
    print_json({"success": True, "result": result})


def cmd_orders_list(args: argparse.Namespace) -> None:
    """子命令 orders-list：查询店铺所有订单（店主端）。"""
    corp_id = resolve_corp_id(args)
    tmp_code = resolve_tmp_code(args, corp_id)
    orders = api_list_orders(corp_id=corp_id, tmp_code=tmp_code)
    print_json({"success": True, "orders": orders, "count": len(orders)})


def cmd_order_update_status(args: argparse.Namespace) -> None:
    """子命令 order-update-status：更新订单状态（店主端）。"""
    corp_id = resolve_corp_id(args)
    tmp_code = resolve_tmp_code(args, corp_id)
    result = api_update_order_status(
        corp_id=corp_id,
        tmp_code=tmp_code,
        order_id=args.order_id,
        status=args.status,
    )
    print_json({"success": True, "order": result})


def cmd_sku_source(args: argparse.Namespace) -> None:
    """子命令 sku-source：设置 SKU 数据源（多维表 / 系统数据库切换）。"""
    corp_id = resolve_corp_id(args)
    tmp_code = resolve_tmp_code(args, corp_id)

    aitable_url = getattr(args, "aitable_url", "") or ""
    source = getattr(args, "source", "") or ""

    # 如果传了多维表链接且没有明确指定 source=mongodb，则自动切换到 aitable
    if aitable_url and source != "mongodb":
        source = "aitable"
    elif not aitable_url and not source:
        source = "mongodb"

    result = api_update_sku_source(
        corp_id=corp_id,
        tmp_code=tmp_code,
        sku_source=source,
        aitable_url=aitable_url,
    )
    print_json({"success": True, "skuSource": result})


def cmd_publish_note(args: argparse.Namespace) -> None:
    """子命令 publish-note：发布穿搭笔记到店铺。"""
    corp_id = resolve_corp_id(args)
    tmp_code = resolve_tmp_code(args, corp_id)
    result = api_publish_style_note(
        corp_id=corp_id,
        tmp_code=tmp_code,
        title=args.title,
        content=args.content,
        images=args.images,
        product_ids=args.product_ids,
        tags=args.tags,
        target_audience=args.target_audience or "",
        note_intent=args.note_intent or "",
        author_name=args.author_name or "官方搭配师",
    )
    print_json({"success": True, "note": result})

def cmd_run(args: argparse.Namespace) -> None:
    """子命令 run：一步完成 tmpcode + init + upload，输出店铺链接和衣服信息。"""
    corp_id = resolve_corp_id(args)
    validate_image_url(args.image_url)

    # 第一步：获取 tmpCode
    tmp_code = resolve_tmp_code(args, corp_id)

    # 第二步：初始化获取 storeId
    tmp_token = api_init(corp_id=corp_id, tmp_code=tmp_code)

    # 第三步：上传衣服信息
    clothes = api_upload_clothes(
        corp_id=corp_id,
        tmp_code=tmp_code,
        name=args.name,
        image_url=args.image_url,
        desc=args.desc,
        category=args.category,
        color=args.color,
        style=args.style,
        features=args.features,
        occasion=args.occasion,
        season=args.season,
        selling_points=args.selling_points or "",
    )

    store_url = STORE_URL_TEMPLATE.format(tmp_token=tmp_token)

    print_json({
        "success": True,
        "store_url": store_url,
        "clothes": clothes,
    })

# ── 参数解析 ──────────────────────────────────────────────────────────────────

def validate_image_url(image_url: str) -> None:
    """校验衣服图片 URL 格式，必须是钉钉媒体链接。"""
    if not image_url.startswith("https://down.dingtalk.com/"):
        exit_with_error(
            f"图片链接格式不正确：{image_url!r}\n"
            "衣服图片必须是钉钉媒体链接，格式为：https://down.dingtalk.com/media/xxxx.png",
            code=2,
        )


def add_corp_id_arg(parser: argparse.ArgumentParser) -> None:
    """为子命令添加 --corp-id 参数（可选，不传则自动从 dws 获取）。"""
    parser.add_argument("--corp-id", required=False, dest="corp_id", default="",
                        help="企业 corpId（可选，不传则自动通过 dws auth status 获取）")


def add_tmp_code_arg(parser: argparse.ArgumentParser) -> None:
    """为子命令添加 --tmp-code 参数（可选，不传则自动通过 /tmpCode 接口获取）。"""
    parser.add_argument("--tmp-code", required=False, dest="tmp_code", default="",
                        help="临时鉴权码 tmpCode（可选，不传则自动通过 /tmpCode 接口获取）")


def add_user_info_args(parser: argparse.ArgumentParser) -> None:
    """为子命令添加用户信息参数（用于获取 tmpCode，可选）。"""
    parser.add_argument("--staff-id", required=False, dest="staff_id", default="",
                        help="员工 userId/staffId（可选，不传则自动通过 dws contact user get-self 获取）")
    parser.add_argument("--org-user-name", required=False, dest="org_user_name", default="",
                        help="员工姓名（可选）")
    parser.add_argument("--org-user-mobile", required=False, dest="org_user_mobile", default="",
                        help="员工手机号（可选）")
    parser.add_argument("--org-name", required=False, dest="org_name", default="",
                        help="组织名称（可选）")


def build_clothes_args(parser: argparse.ArgumentParser) -> None:
    """为 upload / run 子命令添加衣服特征参数。"""
    parser.add_argument("--name", required=True, help="衣服名称，如：经典白衬衫")
    parser.add_argument("--image-url", required=True, dest="image_url", help="衣服图片 URL（需可公开访问）")
    parser.add_argument("--desc", required=True, help="衣服详细描述，包含面料、剪裁等信息")
    parser.add_argument("--category", required=True,
                        help="品类：上衣 / 下装 / 外套 / 连衣裙 / 裤子 / 裙子 / 内搭 / 配件")
    parser.add_argument("--color", required=True, help="主色调，如：白色、藏蓝色")
    parser.add_argument("--style", required=True, help="整体风格，如：通勤简约、休闲街头")
    parser.add_argument("--features", required=True, nargs="+",
                        help="核心特征标签（至少 3 个），如：透气棉质 修身剪裁 百搭经典")
    parser.add_argument("--occasion", required=True, nargs="+",
                        help="适合场合（至少 1 个），如：职场 日常 约会")
    parser.add_argument("--season", required=True, nargs="+",
                        help="适合季节（至少 1 个），如：春季 夏季")
    parser.add_argument("--selling-points", required=False, dest="selling_points", default="",
                        help="衣服卖点描述，如：显瘦修身、高级垂感面料")


def parse_args() -> argparse.Namespace:
    root_parser = argparse.ArgumentParser(
        prog="try_on_cli.py",
        description="虚拟试衣间 CLI — 封装试衣间 API 调用",
    )
    subparsers = root_parser.add_subparsers(dest="command", required=True)

    # tmpcode 子命令
    tmpcode_parser = subparsers.add_parser("tmpcode", help="获取临时鉴权码 tmpCode")
    add_corp_id_arg(tmpcode_parser)
    add_user_info_args(tmpcode_parser)

    # init 子命令
    init_parser = subparsers.add_parser("init", help="初始化试衣间，并下载 H5 二维码和小程序太阳码 PNG 到本地")
    add_corp_id_arg(init_parser)
    add_tmp_code_arg(init_parser)
    add_user_info_args(init_parser)
    init_parser.add_argument("--mini-output", required=False, dest="mini_output", default="",
                             help=f"小程序太阳码输出路径（默认：{DEFAULT_MINI_QRCODE_FILENAME}）")

    # upload 子命令
    upload_parser = subparsers.add_parser("upload", help="上传衣服信息（需先执行 init 获取 storeId）")
    add_corp_id_arg(upload_parser)
    add_tmp_code_arg(upload_parser)
    add_user_info_args(upload_parser)
    build_clothes_args(upload_parser)

    # run 子命令（推荐：一步完成 tmpcode + init + upload）
    run_parser = subparsers.add_parser("run", help="一步完成鉴权 + 初始化 + 上传，输出最终试衣链接（推荐）")
    add_corp_id_arg(run_parser)
    add_tmp_code_arg(run_parser)
    add_user_info_args(run_parser)
    build_clothes_args(run_parser)

    # publish-note 子命令
    publish_note_parser = subparsers.add_parser("publish-note", help="发布穿搭笔记到店铺")
    add_corp_id_arg(publish_note_parser)
    add_tmp_code_arg(publish_note_parser)
    add_user_info_args(publish_note_parser)
    publish_note_parser.add_argument("--title", required=True, help="笔记标题")
    publish_note_parser.add_argument("--content", required=True, help="完整的 Markdown 正文（含图片标记）")
    publish_note_parser.add_argument("--images", required=True, nargs="+", help="图片 URL 列表")
    publish_note_parser.add_argument("--product-ids", required=True, nargs="+", dest="product_ids",
                                     help="关联商品 ID 列表")
    publish_note_parser.add_argument("--tags", required=True, nargs="+", help="标签列表（3-5个）")
    publish_note_parser.add_argument("--target-audience", required=False, dest="target_audience", default="",
                                     help="目标用户群，如：全体用户")
    publish_note_parser.add_argument("--note-intent", required=False, dest="note_intent", default="",
                                     help="笔记意图，如：夏日感碎片")
    publish_note_parser.add_argument("--author-name", required=False, dest="author_name", default="官方搭配师",
                                     help="作者显示名称（默认：官方搭配师）")

    # sku-source 子命令
    sku_source_parser = subparsers.add_parser("sku-source", help="设置 SKU 数据源（多维表 / 系统数据库切换）")
    add_corp_id_arg(sku_source_parser)
    add_tmp_code_arg(sku_source_parser)
    add_user_info_args(sku_source_parser)
    sku_source_parser.add_argument("--aitable-url", required=False, dest="aitable_url", default="",
                                    help="多维表链接（传入时切换到多维表模式，如 https://alidocs.dingtalk.com/i/nodes/xxx?...）")
    sku_source_parser.add_argument("--source", required=False, default="",
                                    choices=["mongodb", "aitable"],
                                    help="数据源类型（mongodb / aitable，传 aitable-url 时可省略，默认自动判断）")

    # store-detail 子命令
    store_detail_parser = subparsers.add_parser("store-detail", help="获取店铺详情（含多维表配置信息）")
    add_corp_id_arg(store_detail_parser)
    add_tmp_code_arg(store_detail_parser)
    add_user_info_args(store_detail_parser)

    # ensure-aitable 子命令
    ensure_aitable_parser = subparsers.add_parser("ensure-aitable", help="确保店铺多维表已创建（已有则返回，否则自动创建）")
    add_corp_id_arg(ensure_aitable_parser)
    add_tmp_code_arg(ensure_aitable_parser)
    add_user_info_args(ensure_aitable_parser)

    # orders-list 子命令
    orders_list_parser = subparsers.add_parser("orders-list", help="查询店铺所有订单列表（店主端）")
    add_corp_id_arg(orders_list_parser)
    add_tmp_code_arg(orders_list_parser)
    add_user_info_args(orders_list_parser)

    # order-update-status 子命令
    order_update_parser = subparsers.add_parser("order-update-status",
                                                help="更新订单状态（店主端）")
    add_corp_id_arg(order_update_parser)
    add_tmp_code_arg(order_update_parser)
    add_user_info_args(order_update_parser)
    order_update_parser.add_argument("--order-id", required=True, dest="order_id",
                                     help="订单 ID")
    order_update_parser.add_argument("--status", required=True,
                                     choices=["pending", "confirmed", "shipping", "completed", "cancelled"],
                                     help="订单状态：pending（已提交）/ confirmed（店主已确认）/ shipping（配送中）/ completed（已完成）/ cancelled（已取消）")

    # store-update 子命令
    store_update_parser = subparsers.add_parser("store-update", help="更新店铺信息（店铺名称、微信号、店铺地址、店主说、店铺照片、店铺视频、店铺 logo）")
    add_corp_id_arg(store_update_parser)
    add_tmp_code_arg(store_update_parser)
    add_user_info_args(store_update_parser)
    store_update_parser.add_argument("--shop-name", required=False, dest="shop_name", default="",
                                     help="店铺名称")
    store_update_parser.add_argument("--wechat", required=False, default="",
                                     help="微信号")
    store_update_parser.add_argument("--shop-address", required=False, dest="shop_address", default="",
                                     help="店铺地址")
    store_update_parser.add_argument("--slogan", required=False, default="",
                                     help="店主说（slogan，将展示在店铺首页 hero 区域）")
    store_update_parser.add_argument("--shop-image-url", required=False, dest="shop_image_url", default="",
                                     help="店铺照片 URL（将展示在店铺首页和首页 3D 展厅区域）")
    store_update_parser.add_argument("--shop-video-url", required=False, dest="shop_video_url", default="",
                                     help="店铺视频 URL（将展示在店铺首页 Hero 区域）")
    store_update_parser.add_argument("--shop-logo-url", required=False, dest="shop_logo_url", default="",
                                     help="店铺 logo / 头像 URL（将展示在店铺首页顶部品牌区与 Hero 区）")

    return root_parser.parse_args()


# ── 入口 ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    command_handlers = {
        "tmpcode": cmd_tmpcode,
        "init": cmd_init,
        "upload": cmd_upload,
        "run": cmd_run,
        "publish-note": cmd_publish_note,
        "store-detail": cmd_store_detail,
        "store-update": cmd_store_update,
        "sku-source": cmd_sku_source,
        "ensure-aitable": cmd_ensure_aitable,
        "orders-list": cmd_orders_list,
        "order-update-status": cmd_order_update_status,
    }

    handler = command_handlers.get(args.command)
    if handler is None:
        exit_with_error(f"未知子命令: {args.command}", code=2)

    handler(args)


if __name__ == "__main__":
    main()
