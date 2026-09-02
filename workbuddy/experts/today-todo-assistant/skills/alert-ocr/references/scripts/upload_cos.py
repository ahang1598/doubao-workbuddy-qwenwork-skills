#!/usr/bin/env python3
"""通过 mcp_client 获取 COS 临时密钥并在内存中闭环上传。

安全约定（规避 local-shell 敏感信息检测）：
- 鉴权信息不硬编码：运行时从 ~/.workbuddy/mcp.json 的 gongyi-open-mcp 读取。
- 临时密钥只在进程内存流转，绝不 print / 不落盘 / 不进命令行参数。
- 调试模式只打印字段结构（值一律打码），不输出任何 AKID / 密钥原文。
- 凭证示例不再写进任何 .md 文档，避免静态命中敏感词检测。

依赖：仅 requests（COS 上传用，与 alert-expert 其它脚本一致，见 requirements.txt）。
MCP 调用统一走 skills/_common/mcp_client.py 的 call_mcp（caller_expert_id 由 call_mcp 注入，
合并进专家团后自动切换为专家团身份）。
"""
import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import uuid
from urllib.parse import quote

import requests

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "_common")))
from mcp_client import call_mcp, CALLER_EXPERT_ID, MCPAuthError, _sanitize
from observe_bootstrap import observe_entrypoint

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".pdf"}


def get_credential(private, timeout=60):
    """仅获取 COS 临时凭证（不完成上传）。caller_expert_id 由 call_mcp 统一注入。"""
    r = call_mcp("get_org_cos_credential", {"private": private}, timeout)
    data = r.get("data")
    if not isinstance(data, dict) or "tmp_secret_id" not in data:
        raise RuntimeError("获取 COS 临时凭证失败: " + _sanitize(str(r.get("text")))[:300])
    return data


# --------------------------------------------------------------------------- #
# COS 上传（SignatureV1，纯 requests 实现，不依赖 qcloud_cos）
# --------------------------------------------------------------------------- #
# ⚠️ 关键：ssl.gongyi.qq.com 前置 EdgeOne WAF 会拦截"非浏览器 UA"的请求
# （python-requests / curl 默认 UA 均被拦，统一回 567 Server Error），
# 必须带浏览器型 User-Agent 与 Origin，否则 COS PUT 会被拦。
_COMMON_UA = "Mozilla/5.0 (compatible; alert-expert-upload/1.0)"
_COMMON_ORIGIN = "https://ssl.gongyi.qq.com"


def _cos_signature(secret_id, secret_key, bucket, region, key, expire=600):
    now = int(time.time())
    sign_time = f"{now};{now + expire}"
    host = f"{bucket}.cos.{region}.myqcloud.com"
    http_uri = "/" + quote(key, safe="/")
    http_method = "put"
    http_parameters = ""
    http_headers = "host=" + host  # 只签 host

    def sha1_hex(s):
        return hashlib.sha1(s.encode("utf-8")).hexdigest()

    str_to_sign = (
        "sha1\n" + sign_time + "\n"
        + sha1_hex(http_method + "\n" + http_uri + "\n"
                   + http_parameters + "\n" + http_headers + "\n") + "\n"
    )
    # ⚠️ 关键：腾讯云 COS 要求 sign_key 用 HMAC 的 hex 字符串（非 digest 原始字节）
    # 作为第二层 HMAC 的 key，否则最终签名与服务器不一致 → SignatureDoesNotMatch
    sign_key = hmac.new(secret_key.encode("utf-8"), sign_time.encode("utf-8"),
                        hashlib.sha1).hexdigest()
    signature = hmac.new(sign_key.encode("utf-8"), str_to_sign.encode("utf-8"),
                         hashlib.sha1).hexdigest()
    auth = (
        f"q-sign-algorithm=sha1&q-ak={secret_id}&q-sign-time={sign_time}"
        f"&q-key-time={sign_time}&q-header-list=host&q-url-param-list="
        f"&q-signature={signature}"
    )
    return host, auth


_CONTENT_TYPES = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png", ".pdf": "application/pdf",
}


def upload_file(data, local_path):
    """用临时密钥把文件 PUT 到 COS，返回对象 key。密钥仅在此函数内使用。"""
    secret_id = data["tmp_secret_id"]
    secret_key = data["tmp_secret_key"]
    token = data["token"]
    bucket = data["bucket"]
    region = data["region"]
    pre_path = data["pre_path"].strip("/")

    ext = os.path.splitext(local_path)[1].lower()
    filename = uuid.uuid4().hex + ext  # UUID 去 '-' + 原始后缀
    key = f"{pre_path}/{filename}" if pre_path else filename

    host, auth = _cos_signature(secret_id, secret_key, bucket, region, key)
    url = f"https://{host}/{quote(key, safe='/')}"
    headers = {
        "Authorization": auth,
        "x-cos-security-token": token,
        "Content-Type": _CONTENT_TYPES.get(ext, "application/octet-stream"),
        "User-Agent": _COMMON_UA,
        "Origin": _COMMON_ORIGIN,
    }
    with open(local_path, "rb") as f:
        resp = requests.put(url, headers=headers, data=f, timeout=60)
    resp.raise_for_status()
    return key


def build_access_url(data, key, private):
    """按桶前缀拼访问链接（公有桶换 CDN，私有桶用 COS 原始域名）。"""
    bucket = data["bucket"]
    region = data["region"]
    cos_url = f"https://{bucket}.cos.{region}.myqcloud.com/{key}"
    if private == 1:
        return cos_url
    if bucket.startswith("jgpt3-test"):
        return f"https://test-orgcdn.gongyi.qq.com/{key}"
    if bucket.startswith("jgpt3-formal"):
        return f"https://orgcdn.gongyi.qq.com/{key}"
    return cos_url  # 未识别前缀，保守回退 COS 原始域名


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #
def _main():
    ap = argparse.ArgumentParser(description="COS 临时密钥上传（内存闭环，密钥不落盘）")
    ap.add_argument("file", nargs="?", help="本地待上传文件路径")
    ap.add_argument("--private", type=int, default=0,
                    help="桶类型：1=私有桶(身份证专用) / 0=公有桶，默认 0")
    ap.add_argument("--cred-stdin", action="store_true",
                    help="从 stdin 读取预取的凭证 JSON（绕过自取凭证，常用于自取接口临时不可用时）")
    ap.add_argument("--cred-file", default=None,
                    help="从本地 0600 权限文件读取预取的凭证 JSON（与 --cred-stdin 等价但不经命令行）")
    args = ap.parse_args()

    if args.private not in (0, 1):
        print(json.dumps({"success": False, "error_code": "param_invalid",
                          "message": "private 仅可为 0 或 1"}, ensure_ascii=False))
        sys.exit(2)

    if not args.file or not os.path.isfile(args.file):
        print(json.dumps({"success": False, "error_code": "file_not_found",
                          "message": "用法: python upload_cos.py <本地图片路径> [--private 0|1]"},
                         ensure_ascii=False))
        sys.exit(2)

    ext = os.path.splitext(args.file)[1].lower()
    if ext not in ALLOWED_EXT:
        print(json.dumps({"success": False, "error_code": "unsupported_type",
                          "message": f"不支持的文件类型 {ext}，仅支持 JPG/PNG/PDF"},
                         ensure_ascii=False))
        sys.exit(2)

    try:
        if args.cred_stdin:
            # 从 stdin 读取预取凭证（agent 已通过 MCP 工具拿到，避免再走自取）
            raw = sys.stdin.read().strip()
            cred = json.loads(raw)
            if not isinstance(cred, dict) or "tmp_secret_id" not in cred:
                raise RuntimeError("stdin 凭证格式异常")
        elif args.cred_file:
            with open(args.cred_file, "r", encoding="utf-8") as f:
                cred = json.loads(f.read().strip())
            if not isinstance(cred, dict) or "tmp_secret_id" not in cred:
                raise RuntimeError("cred-file 凭证格式异常")
        else:
            cred = get_credential(args.private, 60)
    except Exception as e:  # noqa: BLE001
        need_refresh = isinstance(e, MCPAuthError)
        print(json.dumps({"success": False,
                          "error_code": "auth_failed" if need_refresh else "credential_failed",
                          "message": "获取 COS 临时凭证失败: " + _sanitize(str(e)),
                          "need_refresh": need_refresh}, ensure_ascii=False))
        sys.exit(1)

    try:
        key = upload_file(cred, args.file)
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"success": False, "error_code": "upload_failed",
                          "message": "COS 上传失败: " + _sanitize(str(e))},
                         ensure_ascii=False))
        sys.exit(1)

    access_url = build_access_url(cred, key, args.private)
    # 输出不含任何密钥，仅含 bucket/路径/文件名，供后续 get_org_ocr_data 使用
    print(json.dumps({
        "success": True,
        "access_url": access_url,
        "key": key,
        "private": args.private,
        "bucket": cred["bucket"],
    }, ensure_ascii=False))


def main():
    observe_entrypoint(CALLER_EXPERT_ID, "alert.upload_cos", "upload_cos", _main)


if __name__ == "__main__":
    main()
