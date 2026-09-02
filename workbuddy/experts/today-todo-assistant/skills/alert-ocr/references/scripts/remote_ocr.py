#!/usr/bin/env python3
"""远程 OCR 识别（1.3）：脚本内一次性完成
  get_org_cos_credential → 上传 COS → get_org_ocr_data → 轮询 get_org_ocr_result
直接返回上传链接与识别结果（K-V 字段），AI 无需分步调 MCP。

private / ocr_type 由 AI 在 Stage-1 本地证件类型判断后给出：
  身份证（法人/专项基金负责人）= 1，其它证件（登记证/募捐资格证）= 0；两者必须同为 0 或同为 1。

输出 JSON：
  { "success": true, "access_url": "...", "key": "...", "fields":[{"name","value"}], "original_data": {...} }
  { "success": false, "error": "...", "reason": "..." }

用法：python remote_ocr.py <文件> --private 0|1 --ocr_type 0|1
依赖：skills/_common/mcp_client.py、skills/alert-ocr/references/scripts/upload_cos.py
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "_common")))
from mcp_client import (call_mcp,
                        CALLER_EXPERT_ID, mask, _sanitize, ALLOWED_EXT,
                        MCPAuthError)
from observe_bootstrap import observe_entrypoint
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from upload_cos import upload_file, build_access_url  # 复用 OCR skill 内的上传真源


def get_credential(private, timeout=60):
    """仅获取 COS 临时凭证（不完成上传）。"""
    r = call_mcp("get_org_cos_credential",
                 {"private": private},
                 timeout)
    data = r["data"]
    if not isinstance(data, dict) or "tmp_secret_id" not in data:
        raise RuntimeError("获取 COS 临时凭证失败: " + str(r["text"])[:300])
    return data


def upload_to_cos(local_path, private, timeout=60):
    """取临时凭证 + 上传 + 拼访问链接，返回 {key,access_url,private,bucket}。

    上传与链接拼接复用 upload_cos.py，保证和文档铁律工具行为一致。
    """
    cred = get_credential(private, timeout)
    key = upload_file(cred, local_path)
    access_url = build_access_url(cred, key, private)
    return {"key": key, "access_url": access_url, "private": private, "bucket": cred["bucket"]}


def poll_ocr(task_key, timeout=60, interval=5, max_elapsed=30):
    """轮询 get_org_ocr_result 直到 state==1（完成），返回 original_data。

    30 秒仍无结果则抛错，提示需从 Step 1 重来。
    """
    start = time.time()
    while True:
        r = call_mcp("get_org_ocr_result",
                     {"key": task_key},
                     timeout)
        data = r["data"] or {}
        if str(data.get("state")) == "1":
            return data.get("original_data")
        if time.time() - start >= max_elapsed:
            raise RuntimeError("OCR 轮询超时 30 秒仍无结果, 需从 Step 1 重来")
        time.sleep(interval)


def _main():
    ap = argparse.ArgumentParser(description="远程 OCR 识别（凭证+上传+提交+轮询 一体）")
    ap.add_argument("file", help="本地待识别图片路径")
    ap.add_argument("--private", type=int, default=0, choices=[0, 1],
                    help="桶类型：1=私有桶(身份证) / 0=公有桶，默认 0")
    ap.add_argument("--ocr_type", type=int, default=0, choices=[0, 1],
                    help="识别类型：1=身份证 / 0=非身份证，默认 0；必须与 --private 一致")
    args = ap.parse_args()

    if args.private != args.ocr_type:
        print(json.dumps({"success": False, "error_code": "param_mismatch",
                          "message": "private 与 ocr_type 必须同时为 0 或同时为 1（隐私与安全约束）"},
                         ensure_ascii=False))
        sys.exit(2)
    if not os.path.isfile(args.file):
        print(json.dumps({"success": False, "error_code": "file_not_found",
                          "message": f"文件不存在: {args.file}"}, ensure_ascii=False))
        sys.exit(2)
    ext = os.path.splitext(args.file)[1].lower()
    if ext not in ALLOWED_EXT:
        print(json.dumps({"success": False, "error_code": "unsupported_type",
                          "message": f"不支持的文件类型 {ext}，仅支持 JPG/PNG/PDF"},
                         ensure_ascii=False))
        sys.exit(2)

    try:
        up = upload_to_cos(args.file, args.private, 60)
        # Step 2：提交 OCR 检测
        sub = call_mcp("get_org_ocr_data",
                       {"image_url": up["access_url"],
                        "ocr_type": args.ocr_type}, 60)
        data = sub["data"] or {}
        task_key = data.get("key")
        if not task_key:
            raise RuntimeError("get_org_ocr_data 未返回任务 key")
        # Step 3：轮询结果
        original = poll_ocr(task_key, timeout=60)
        infos = (original or {}).get("enterprise_license_infos") or []
        fields = [{"name": i.get("name"), "value": i.get("value")} for i in infos]
        print(json.dumps({"success": True, "access_url": up["access_url"], "key": up["key"],
                          "fields": fields, "original_data": original}, ensure_ascii=False))
    except Exception as e:  # noqa: BLE001
        need_refresh = isinstance(e, MCPAuthError)
        print(json.dumps({"success": False,
                          "error_code": "auth_failed" if need_refresh else "ocr_failed",
                          "message": "远程 OCR 识别失败: " + _sanitize(str(e)),
                          "need_refresh": need_refresh}, ensure_ascii=False))
        sys.exit(1)


def main():
    observe_entrypoint(CALLER_EXPERT_ID, "alert.remote_ocr", "remote_ocr", _main)


if __name__ == "__main__":
    main()
