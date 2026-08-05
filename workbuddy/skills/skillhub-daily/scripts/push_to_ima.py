#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IMA 简报推送脚本 — 跨平台版
用法: python push_to_ima.py <简报文件路径> [笔记标题]

凭证来源优先级：
  1. 环境变量: IMA_CLIENT_ID, IMA_API_KEY, IMA_KB_ID
  2. Skill 配置: skillhub-daily/references/config.json
  3. IMA Skill 配置: ima-skill/config.json（OpenClaw 环境）
  4. WorkBuddy 配置: ~/.workbuddy/skills/ima-skill/config.json
"""

import sys
import os
import json
import ssl
import urllib.request
from pathlib import Path

BASE_URL = "https://ima.qq.com"

# ── 凭证搜索路径（按优先级） ──────────────────────────────
_CONFIG_SEARCH_PATHS = [
    # 1. 本 skill 目录下的 config
    Path(__file__).resolve().parent.parent / "references" / "config.json",
    # 2. OpenClaw IMA skill
    Path.home() / ".qclaw" / "skills" / "ima-skill" / "config.json",
    # 3. WorkBuddy IMA skill
    Path.home() / ".workbuddy" / "skills" / "ima-skill" / "config.json",
]


def _find_credentials_in_configs():
    """从多个候选路径搜索凭证。"""
    for config_path in _CONFIG_SEARCH_PATHS:
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                client_id = cfg.get("ima_client_id") or cfg.get("client_id")
                api_key = cfg.get("ima_api_key") or cfg.get("api_key")
                kb_id = cfg.get("ima_kb_id") or cfg.get("kb_id")
                if client_id and api_key:
                    return client_id, api_key, kb_id
            except Exception:
                continue
    return None, None, None


def load_credentials():
    """
    凭证加载优先级：
    1. 环境变量
    2. 配置文件（多路径搜索）
    """
    client_id = os.environ.get("IMA_CLIENT_ID")
    api_key = os.environ.get("IMA_API_KEY")
    kb_id = os.environ.get("IMA_KB_ID")

    if client_id and api_key:
        return client_id, api_key, kb_id

    # 降级到配置文件搜索
    cfg_id, cfg_key, cfg_kb = _find_credentials_in_configs()
    client_id = client_id or cfg_id
    api_key = api_key or cfg_key
    kb_id = kb_id or cfg_kb

    return client_id, api_key, kb_id


# ── API 调用 ───────────────────────────────────────────────

def ima_api(endpoint, data=None, client_id=None, api_key=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "ima-openapi-clientid": client_id,
        "ima-openapi-apikey": api_key,
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(
        url, data=body, headers=headers,
        method="POST" if data else "GET",
    )
    # SSL: 生产环境应启用验证；若遇证书问题可设置 IMA_SKIP_SSL_VERIFY=1
    skip_ssl = os.environ.get("IMA_SKIP_SSL_VERIFY", "").strip() in ("1", "true", "yes")
    if skip_ssl:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    else:
        ctx = None

    try:
        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ctx) if ctx else urllib.request.HTTPSHandler()
        )
        with opener.open(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


# ── 主流程 ─────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python push_to_ima.py <briefing_file> [note_title]")
        print("Env vars: IMA_CLIENT_ID, IMA_API_KEY, IMA_KB_ID")
        print("Example: python push_to_ima.py data/reports/2026-06-03-briefing.md 'SkillHub Daily | 2026-06-03'")
        sys.exit(1)

    file_path = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else None

    # 读取简报内容
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"[ERROR] Failed to read file: {e}")
        sys.exit(1)

    # 获取凭证
    client_id, api_key, kb_id = load_credentials()
    if not client_id or not api_key:
        print("[ERROR] Missing IMA credentials. Set env vars or check config files.")
        sys.exit(1)

    print(f"[INFO] Pushing: {file_path}")
    if kb_id:
        print(f"[INFO] KB ID: {kb_id[:20]}...")

    # 创建笔记
    note_payload = {
        "content": content,
        "content_format": 1,
    }
    if title:
        note_payload["folder_name"] = title

    result = ima_api("/openapi/note/v1/import_doc", note_payload, client_id, api_key)

    if "error" in result:
        print(f"[ERROR] Create note failed: {result['error']}")
        sys.exit(1)

    if "data" not in result or "note_id" not in result["data"]:
        print(f"[ERROR] Unexpected response: {json.dumps(result, ensure_ascii=False)[:200]}")
        sys.exit(1)

    note_id = result["data"]["note_id"]
    print(f"[OK] Note created: {note_id}")

    # 关联到知识库
    if kb_id:
        note_title = title or os.path.basename(file_path)
        kb_result = ima_api("/openapi/wiki/v1/add_knowledge", {
            "knowledge_base_id": kb_id,
            "media_type": 11,
            "title": note_title,
            "note_info": {"content_id": note_id},
        }, client_id, api_key)

        if "error" in kb_result:
            print(f"[WARN] KB link failed: {kb_result['error']}")
            print(f"[INFO] Note created but not linked to KB. Link manually.")
        else:
            print(f"[OK] Note linked to knowledge base")
    else:
        print(f"[INFO] No KB_ID configured. Note created but not linked.")

    print(f"\nDone! Note ID: {note_id}")


if __name__ == "__main__":
    main()
