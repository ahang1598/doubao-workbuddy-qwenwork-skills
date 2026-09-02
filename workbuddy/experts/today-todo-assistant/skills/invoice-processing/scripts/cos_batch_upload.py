#!/usr/bin/env python3
"""
cos_batch_upload.py — 票据 PDF 批量并发上传 COS + CDN 域名替换

⚠️ 纯 requests 实现（与 alert-expert 的 upload_cos.py 同源），**不依赖 cos-python-sdk-v5**。
   COS 签名用腾讯云 SignatureV1，由本脚本本地用 HMAC-SHA1 计算（hex 摘要，非原始字节），
   与后端一致，规避 qcloud_cos SDK 的耦合与安装脆弱性。

✅ 支持多文件并发上传，并在凭证有效期内**自动分批**：
   - `files` 一次可传入数百个；脚本按 `batch_size`（默认 200）切片
   - 每一批上传前校验临时凭证有效性，过期则自动调 get_org_cos_credential 重取
   - 故「一次传入几百个文件」可稳定跑完，不会因凭证过期中断

CLI:
  python cos_batch_upload.py --input-file <path/to/input.json>

⚠️ **必须走 `--input-file`**: 入参含临时凭证与上千条路径,拼命令行会超长,
   且凭证出现在命令行历史里不安全。

═══════════════════════════════════════════════════════════════
入参 JSON
═══════════════════════════════════════════════════════════════
  {
    "credential": {                       // 可选；缺省时脚本经 mcp_client 自取
      "tmp_secret_id": "AKID...",         //   get_org_cos_credential(private=0)
                                          //   （token 取自 ~/.workbuddy/.gongyi_token）
      "tmp_secret_key": "...",
      "token": "...",
      "bucket": "jgpt3-test-1300000000",
      "region": "ap-guangzhou",
      "pre_path": "invoice/2026/08",
      "expired_time": 1754680800
    },
    "files": [
      { "seq": 1, "md5": "ab12...", "pdf_path": "D:/票据/1.pdf" }
    ],
    "workers": 16,                        // 可选, 默认 16 (并发线程数)
    "batch_size": 200,                    // 可选, 默认 200: 每批上传前校验凭证, 过期则重取
    "auto_install": true                  // 可选, 默认 true; 缺 requests 时自动 pip install
  }

═══════════════════════════════════════════════════════════════
出参 JSON (stdout)
═══════════════════════════════════════════════════════════════
  {
    "success": true,
    "total": 200, "succeeded": 199, "failed": 1,
    "elapsed_ms": 3120,
    "avg_ms_per_file": 156,
    "workers": 16,
    "batches": 1,                         // ★ 实际分批数
    "cdn_host": "test-orgcdn.gongyi.qq.com",
    "results": [
      { "seq": 1, "md5": "ab12...", "pdf_path": "...",
        "success": true, "invoice_url": "https://test-orgcdn.../xxx.pdf",
        "object_key": "invoice/2026/08/xxx.pdf", "elapsed_ms": 140 },
      { "seq": 7, "success": false, "error": "..." }
    ]
  }

⚠️ **部分失败不中断**其余上传(spec 明确要求): `success` 仅在全部失败时为 false。
   失败项单独回报, 由 SOP 决定是否重试; 上传失败的票据**不得**以空
   `invoice_url` 进入 `UiReq`。

⚠️ 出参**不回显任何凭证字段**。临时凭证不得持久化、不得打印给用户。

═══════════════════════════════════════════════════════════════
上传规则
═══════════════════════════════════════════════════════════════
- `private` 固定 `0`(公有桶) —— 由调用方在取凭证时保证, 本脚本不接受 private 入参
- 对象 key = `{pre_path}/{uuid去掉横线}.pdf`, **不得**使用用户原始文件名
- CDN 域名替换:

  | bucket 前缀      | 域名                          |
  |------------------|-------------------------------|
  | `jgpt3-test`     | `test-orgcdn.gongyi.qq.com`   |
  | `jgpt3-formal`   | `orgcdn.gongyi.qq.com`        |
  | 其它             | COS 原始域名(保守回退)        |

⚠️ 上传时机: **呼起 UI 之前**(因为 `MatchItem.invoice_url` 是 UI 入参),
   且**两个列表的全部票据都要上传** —— 未匹配的票用户更需要看原件才知道怎么改。
   重匹配循环中**复用**已有 `invoice_url`, 严禁为同一 PDF 重复上传。
"""
import argparse
import contextlib
import hashlib
import hmac
import io
import json
import os
import re
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

try:
    import requests
except ImportError:  # pragma: no cover - 运行时兜底
    requests = None


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
DEFAULT_WORKERS = 16
MAX_WORKERS = 32
DEFAULT_BATCH_SIZE = 200
EXPIRE_BUFFER_SEC = 120                  # 凭证剩余有效期小于此值即视为过期, 重取

# ---------------------------------------------------------------------------
# MCP Token：统一由 skills/_common/mcp_client.py 处理
#   - token 固定路径：~/.workbuddy/.gongyi_token（由连接器经 get_mcp_token 落盘）
#   - 鉴权头：Authorization: Bearer <token>（token 唯一来源 ~/.workbuddy/.gongyi_token，缺失时 mcp_client 报 need_refresh）
#   - 鉴权失败由 mcp_client 直接退出（stdout 带 need_refresh）
# ---------------------------------------------------------------------------

# WAF 浏览器特征头: ssl.gongyi.qq.com 前置 EdgeOne WAF 会拦截非浏览器 UA
# (python-requests / curl 默认 UA 均被拦, 统一回 567)。与 alert-expert 同源。
_COMMON_UA = "Mozilla/5.0 (compatible; invoice-expert-upload/1.0)"
_COMMON_ORIGIN = "https://ssl.gongyi.qq.com"

CDN_RULES = [
    ("jgpt3-test", "test-orgcdn.gongyi.qq.com"),
    ("jgpt3-formal", "orgcdn.gongyi.qq.com"),
]


# ---------------------------------------------------------------------------
# 脱敏(避免错误日志泄露密钥)
# ---------------------------------------------------------------------------
def _sanitize(s: str) -> str:
    s = re.sub(r"AKID[A-Za-z0-9]+", "AKID***", s)
    s = re.sub(r"Bearer\s+\S+", "Bearer ***", s)
    s = re.sub(r"[A-Za-z0-9+/_=]{24,}", "***", s)
    return s


# ---------------------------------------------------------------------------
# 依赖探测与自助补齐(requests)
# ---------------------------------------------------------------------------
def _probe_requests() -> bool:
    return requests is not None


def _try_install_requests() -> tuple:
    if requests is not None:
        return True, ""
    cmds = [
        [sys.executable, "-m", "pip", "install", "--quiet", "requests"],
        [sys.executable, "-m", "pip", "install", "--quiet", "--user", "requests"],
    ]
    logs = []
    for cmd in cmds:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
            logs.append(
                f"$ {' '.join(cmd)}\n"
                f"  rc={proc.returncode} out={proc.stdout.strip()[:200]} "
                f"err={proc.stderr.strip()[:200]}"
            )
            try:
                import requests as _r  # noqa: F401
                globals()["requests"] = _r
                return True, "\n".join(logs)
            except Exception:
                pass
        except Exception as e:  # noqa: BLE001
            logs.append(f"$ {' '.join(cmd)}\n  exception={e}")
    return False, "\n".join(logs)


# ---------------------------------------------------------------------------
# MCP 调用（统一走 skills/_common/mcp_client.py）
# ---------------------------------------------------------------------------
def fetch_credential(private: int = 0, timeout: int = 30) -> dict:
    """从 gongyi-open-mcp 拉取 COS 临时凭证（统一走 mcp_client.call_mcp）。

    鉴权失败（token 缺失 / 过期）由 mcp_client 直接退出（stdout 带 need_refresh）。
    其他失败抛 RuntimeError（已脱敏）。
    """
    # mcp_client 硬依赖 requests, 延迟到此函数（确保 requests 已按需安装后再导入）
    import os as _os
    import sys as _sys
    _sys.path.insert(
        0,
        _os.path.normpath(
            _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "_common")
        ),
    )
    from mcp_client import call_mcp
    r = call_mcp(
        "get_org_cos_credential",
        {"private": private},
        timeout,
    )
    if r.get("is_error"):
        raise RuntimeError("获取 COS 凭证失败: " + _sanitize(str(r.get("text")))[:300])
    data = r.get("data")
    if data is None:
        raise RuntimeError("获取 COS 凭证回包解析失败: " + _sanitize(str(r.get("text")))[:300])
    return data


# ---------------------------------------------------------------------------
# COS 上传(SignatureV1, 纯 requests 实现)
# ---------------------------------------------------------------------------
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
    # ⚠️ 腾讯云 COS 要求 sign_key 用 HMAC 的 hex 字符串(非 digest 原始字节)
    # 作为第二层 HMAC 的 key, 否则最终签名与服务器不一致 → SignatureDoesNotMatch
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


def resolve_host(bucket: str, region: str) -> str:
    """CDN 域名替换(票据固定公有桶, private=0)。"""
    for prefix, host in CDN_RULES:
        if bucket.startswith(prefix):
            return host
    # 未识别的桶前缀 → 保守回退到 COS 原始域名
    return f"{bucket}.cos.{region}.myqcloud.com"


def _cred_valid(cred: dict, buffer_sec: int = EXPIRE_BUFFER_SEC) -> bool:
    exp = cred.get("expired_time")
    if not exp:
        return False
    return int(exp) - int(time.time()) > buffer_sec


def _cred_fields_ok(cred: dict) -> bool:
    return all(cred.get(k) for k in
               ("tmp_secret_id", "tmp_secret_key", "token", "bucket", "region", "pre_path"))


def _ensure_credential(input_cred: dict, auto_fetch: bool) -> dict:
    """优先用入参凭证; 无效/缺字段且允许自取时, 从 MCP 自取。"""
    if _cred_fields_ok(input_cred) and _cred_valid(input_cred):
        return input_cred
    if not auto_fetch:
        raise RuntimeError(
            "入参 credential 缺失字段或已过期, 且 auto_fetch=false 无法自取"
        )
    return fetch_credential(private=0, timeout=30)


def _upload_one(cred, pre_path, entry, ua, origin):
    """用临时密钥把单个 PDF PUT 到 COS, 返回结果 dict。密钥仅在此函数内使用。"""
    started = time.time()
    pdf_path = str(entry.get("pdf_path") or "")
    out = {"seq": entry.get("seq"), "md5": entry.get("md5") or "", "pdf_path": pdf_path}
    try:
        if not pdf_path or not os.path.exists(pdf_path):
            raise RuntimeError(f"文件不存在: {pdf_path}")
        if os.path.splitext(pdf_path)[1].lower() != ".pdf":
            raise RuntimeError("只允许上传 PDF 格式的票据")

        secret_id = cred["tmp_secret_id"]
        secret_key = cred["tmp_secret_key"]
        token = cred["token"]
        bucket = str(cred["bucket"])
        region = str(cred["region"])
        pre = (pre_path or "").strip("/")
        filename = uuid.uuid4().hex + ".pdf"  # UUID 去掉所有横线
        key = f"{pre}/{filename}" if pre else filename

        host, auth = _cos_signature(secret_id, secret_key, bucket, region, key)
        url = f"https://{host}/{quote(key, safe='/')}"
        headers = {
            "Authorization": auth,
            "x-cos-security-token": token,
            "Content-Type": "application/pdf",
            "User-Agent": ua,
            "Origin": origin,
        }
        with open(pdf_path, "rb") as f:
            resp = requests.put(url, headers=headers, data=f, timeout=60)
        resp.raise_for_status()

        cdn_host = resolve_host(bucket, region)
        out.update({
            "success": True,
            "object_key": key,
            "invoice_url": f"https://{cdn_host}/{key}",
            "elapsed_ms": int((time.time() - started) * 1000),
        })
    except Exception as e:  # noqa: BLE001
        out.update({"success": False, "error": str(e),
                    "elapsed_ms": int((time.time() - started) * 1000)})
    return out


def _upload_batch(cred, pre_path, batch, workers, ua, origin):
    if len(batch) == 1 or workers == 1:
        return [_upload_one(cred, pre_path, e, ua, origin) for e in batch]
    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_upload_one, cred, pre_path, e, ua, origin) for e in batch]
        for fut in as_completed(futs):
            results.append(fut.result())
    return results


# ---------------------------------------------------------------------------
# stdout 纯净化(线程并发共享 sys.stdout, 父进程一层重定向覆盖)
# ---------------------------------------------------------------------------
def _run_quiet(fn, *args, **kwargs):
    if requests is None:
        return fn(*args, **kwargs)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = fn(*args, **kwargs)
    noise = buf.getvalue()
    if noise.strip():
        sys.stderr.write(noise)
        sys.stderr.flush()
    return result


# ---------------------------------------------------------------------------
# 主流程: 自动分批 + 并发上传
# ---------------------------------------------------------------------------
def process(input_data: dict) -> dict:
    files = input_data.get("files") or []
    if not files:
        return {"success": False, "error": "files 为空, 无可上传的票据"}

    workers = int(input_data.get("workers", DEFAULT_WORKERS) or DEFAULT_WORKERS)
    workers = max(1, min(workers, MAX_WORKERS))
    batch_size = max(1, int(input_data.get("batch_size", DEFAULT_BATCH_SIZE) or DEFAULT_BATCH_SIZE))

    # 凭证: 优先入参, 否则自取
    try:
        cred = _ensure_credential(input_data.get("credential") or {}, True)
    except Exception as e:  # noqa: BLE001
        return {"success": False,
                "error": "获取 COS 临时凭证失败: " + _sanitize(str(e)),
                "fix_hint": "确认 ~/.workbuddy/mcp.json 中 gongyi-open-mcp 配置正确"}

    pre_path = str(cred["pre_path"])
    ua = _COMMON_UA
    origin = _COMMON_ORIGIN

    started = time.time()
    results = []
    batches = 0
    for i in range(0, len(files), batch_size):
        batch = files[i:i + batch_size]
        # 每批前校验凭证, 过期则重取(支撑数百文件跨凭证周期)
        if not _cred_valid(cred):
            try:
                cred = fetch_credential(private=0, timeout=30)
                pre_path = str(cred["pre_path"])
            except Exception as e:  # noqa: BLE001
                for e2 in batch:
                    results.append({
                        "seq": e2.get("seq"), "md5": e2.get("md5") or "",
                        "pdf_path": str(e2.get("pdf_path") or ""),
                        "success": False, "error": "凭证重取失败: " + _sanitize(str(e)),
                    })
                continue
        results.extend(_upload_batch(cred, pre_path, batch, workers, ua, origin))
        batches += 1

    # 按输入顺序排序(并发无序)
    order = {str(f.get("pdf_path")): i for i, f in enumerate(files)}
    results.sort(key=lambda r: order.get(str(r.get("pdf_path")), 0))

    elapsed_ms = int((time.time() - started) * 1000)
    succeeded = sum(1 for r in results if r.get("success"))
    cdn_host = resolve_host(str(cred["bucket"]), str(cred["region"]))

    out = {
        "success": succeeded > 0,
        "total": len(results),
        "succeeded": succeeded,
        "failed": len(results) - succeeded,
        "elapsed_ms": elapsed_ms,
        "avg_ms_per_file": int(elapsed_ms / len(results)) if results else 0,
        "workers": workers,
        "batches": batches,
        "cdn_host": cdn_host,
        "results": results,
    }
    if succeeded == 0:
        out["error"] = "全部票据上传失败, 详见 results"
    return out


def main():
    # ⚠️ Windows 实测: stdout 为管道时用 locale 编码(GBK), 中文 JSON 会写成 GBK 字节,
    #    UTF-8 读取方直接 UnicodeDecodeError。必须显式改 UTF-8。
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="JSON 入参(不推荐: 凭证会进命令行历史)")
    parser.add_argument("--input-file", dest="input_file", help="入参 JSON 文件路径(推荐)")
    args = parser.parse_args()

    if not args.input and not args.input_file:
        print(json.dumps({"success": False, "error": "必须提供 --input-file"}, flush=True))
        sys.exit(1)

    # 依赖兜底: 缺 requests 时自助安装
    if not _probe_requests():
        ok, log = _try_install_requests()
        if not ok:
            print(json.dumps({"success": False,
                              "error": "缺少 requests 且自动安装失败",
                              "attempted_remediation": log,
                              "fix_hint": f"{sys.executable} -m pip install requests"},
                             ensure_ascii=False), flush=True)
            sys.exit(1)

    try:
        if args.input_file:
            with open(args.input_file, "r", encoding="utf-8") as f:
                input_data = json.load(f)
        else:
            input_data = json.loads(args.input)
    except (json.JSONDecodeError, OSError) as e:
        print(json.dumps({"success": False, "error": f"入参非合法 JSON: {e}"},
                         ensure_ascii=False), flush=True)
        sys.exit(1)

    result = _run_quiet(process, input_data)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
