import json
from urllib.parse import parse_qsl, urlparse
import traceback

import time
import hmac
import base64
import hashlib

from urllib3.exceptions import InsecureRequestWarning
import urllib3

import os
from pathlib import Path

# 禁用 SSL 警告
urllib3.disable_warnings(InsecureRequestWarning)


DOC_GEN_PATH = "/celia-claw/v1/rest-api/skill/execute"


def gen_code_file(sn, code_block, file_type, device_info, ref_str="", cfg=None):
    request_data = {
        "content": code_block,
        "request_id": sn,
        "tgt_file_type": file_type,
        "agent": "dr_generate"
    }
    if ref_str:
        request_data['reference_type'] = 1
        request_data['references'] = json.dumps({"items": json.loads(ref_str)}, ensure_ascii=False)
    headers = {
        "Content-Type": "application/json",
        "x-skill-id": "deep_research_md2doc",
        "x-hag-trace-id": cfg.sn,
        "x-device-type": "phone",
        **cfg.auth_headers(),
    }

    output_dir_str = os.getenv("DR_SESSION_DIR", "")
    output_dir = Path(output_dir_str)

    with open(output_dir / "claw_doc_gen_log.json", "w", encoding="utf-8") as f:
        json.dump(headers, f, ensure_ascii=False, indent=4)

    # 经主进程管道代理；旧沙箱形态 requests 直连（cfg.skill_post 内部处理）
    with cfg.skill_post(DOC_GEN_PATH, request_data, headers=headers) as resp:
        resp_content = resp.text
    resp = json.loads(resp_content)
    file_name_ = resp.get("file_name", "")
    file_url_ = resp.get("url", "")
    return file_name_, file_url_



def get_file_download_command(sn, file_name_, file_url_):
    command = {
        "directives": [
            {
                "header": {
                    "namespace": "UserInteraction",
                    "name": "DisplayDocumentCard"
                },
                "payload": {
                    "templateType": "generateDocCard",
                    "cardParams": {
                        "fileId": sn,
                        "fileName": file_name_
                    }
                }
            },
            {
                "header": {
                    "namespace": "Command",
                    "name": "UpdateFileInfo"
                },
                "payload": {
                    "fileId": sn,
                    "retCode": "0",
                    "processType": "generate",
                    "fileResultInfo": {
                        "path": file_url_,
                        "previewPath": file_url_,
                    }
                }
            }
        ]
    }
    return json.dumps(command)
