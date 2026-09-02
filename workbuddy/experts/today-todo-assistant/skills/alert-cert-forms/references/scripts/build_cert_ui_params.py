#!/usr/bin/env python3
"""根据 org_cert_update_review 业务体，构造 open_org_cert_update_review_ui 工具入参。

输入（stdin 或 --json-file）：proto 业务体（即 org_cert_update_review，结构与提交时同一；字段契约见 tools/org_cert_update_review_input.md）
  {
    "cert_types": [1, 3],                       # 裸 int 数组（兼容 [{"cert_type":1}]）
    "charitable_person":  { charitable_person_file_url, certificate_validity_start_date,
                            certificate_validity_end_date, certificate_validity_permanent,
                            competent_unit, competent_unit_location, business_scope },
    "charitable_public":  { charitable_public_file_url, charitable_public_start_date,
                            charitable_public_end_date, charitable_public_permanent },
    "idcard":             { idcard_front, idcard_back, name, id_card, id_card_validity }
  }

校验范围（对应 alert-cert-forms 规则）：
  - cert_types 非空
  - 入口守卫：has_pending_review==true 禁止提交（审批中）
  - 每个 cert_type 必须存在匹配的命名业务块（charitable_person / charitable_public / idcard）
  - 身份证(idcard)：front/back 链接须用 COS 原始域名(.cos.)

成功时把 open_org_cert_update_review_ui 工具的入参（仅两字段）写到 --output 文件（不打印到 stdout，避免截断），
文件内容：
  {"caller_expert_id":"alert-expert", "data_cache_id":"<set_common_data_cache 返回的 key>"}
stdout 仅打印极简指针：{"success": true, "output_file": <path>, "hint": ...}
⚠️ 调 UI 前脚本已先调用
   set_common_data_cache({"data": {caller_expert_id, org_cert_update_review, submit}})
   —— data 即"原先直接输出给 UI 的那份完整 JSON" —— 拿到 data_cache_id；
   UI 调用时只传 caller_expert_id + data_cache_id。
⚠️ AI 调用 UI 工具时【直接读取 --output 文件内容】作为入参，⛔ 禁止二次转换/重组、⛔ 禁止读 inputSchema。

失败（校验/守卫不通过）：{"success": false, "error_code": "...", "message": "...", "field_errors": {...}}
"""
import argparse, json, sys, os
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "_common")))
from mcp_client import call_mcp, set_common_data_cache, CALLER_EXPERT_ID, MCPAuthError, mask, _sanitize
from observe_bootstrap import observe_entrypoint

NEXT_STEP = "使用提交证件到远程步骤，重新拉取新的证件和备案号待办事项"
BLOCK_KEY = {1: "charitable_person", 2: "charitable_public", 3: "idcard"}

# 凭证/密钥 已封装在 mcp_client 内，脚本层面不接触明文。


def _validate(biz):
    """返回 (details, err)。err 为 None 表示通过，否则为 (code, field_errors)。"""
    if not isinstance(biz, dict):
        return None, ("payload_not_object", {})
    cert_types = biz.get("cert_types")
    if not isinstance(cert_types, list) or len(cert_types) == 0:
        return None, ("cert_types_empty", {})
    details = {}
    for ct in cert_types:
        ctype = ct if isinstance(ct, int) else (ct.get("cert_type") if isinstance(ct, dict) else None)
        if ctype not in BLOCK_KEY:
            return None, ("cert_type_invalid", {})
        block_key = BLOCK_KEY[ctype]
        blk = biz.get(block_key)
        if not isinstance(blk, dict):
            return None, ("block_missing", {block_key: "missing"})
        if ctype == 3:
            for f in ("idcard_front", "idcard_back"):
                v = blk.get(f)
                if not (isinstance(v, str) and ".cos." in v):
                    return None, ("idcard_url_domain", {block_key: [f]})
        details[block_key] = blk
    return details, None


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-file", required=False)
    ap.add_argument("--output", default=None,
                    help="成功时 UI 入参 JSON 的写出路径（缺省: 与 --json-file 同目录同名的 <name>_ui_params.json，或 ./cert_ui_params.json）")
    args = ap.parse_args()
    # 决定输出文件路径（成功时把 UI 入参小 JSON 写文件，避免 stdout 截断）
    out_path = args.output
    if not out_path:
        if args.json_file:
            base, _ = os.path.splitext(os.path.abspath(args.json_file))
            out_path = base + "_ui_params.json"
        else:
            out_path = os.path.join(os.getcwd(), "cert_ui_params.json")
    try:
        if args.json_file:
            with open(args.json_file, "r", encoding="utf-8") as f:
                biz = json.load(f)
        else:
            biz = json.load(sys.stdin)
        details, err = _validate(biz)
        if err:
            code, fe = err
            raise ValueError(code)  # 下方按 code 转 error_code
        # 入口守卫：查 has_pending_review
        d = call_mcp("get_org_detail", {}, 30)["data"] or {}
        if d.get("has_pending_review") is True:
            raise PermissionError("audit_pending")
        # 原先输出的那份完整 UI 入参 JSON 整体写入公共缓存，调 UI 时只带 caller_expert_id + data_cache_id
        ui_params = {
            "caller_expert_id": CALLER_EXPERT_ID,
            "org_cert_update_review": biz,
            "submit": {"next_step": NEXT_STEP},
        }
        key = set_common_data_cache(ui_params)
        # UI 工具入参（仅两字段）写文件，避免 stdout 截断；内容 = caller_expert_id + data_cache_id
        result = {"caller_expert_id": CALLER_EXPERT_ID, "data_cache_id": key}
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False)
        except Exception as e:  # noqa: BLE001
            print(json.dumps({"success": False, "error_code": "write_output",
                              "message": f"写出 UI 入参文件失败: {_sanitize(str(e))}",
                              "field_errors": {}}, ensure_ascii=False))
            sys.exit(1)
        print(json.dumps({"success": True, "output_file": out_path,
                          "hint": "该文件内容即 open_org_cert_update_review_ui 入参 {caller_expert_id, data_cache_id}，UI 调用直接读取此文件、不做转换"},
                         ensure_ascii=False))
    except ValueError as e:
        print(json.dumps({"success": False, "error_code": _sanitize(str(e)),
                          "message": f"校验失败: {_sanitize(str(e))}",
                          "field_errors": {}}, ensure_ascii=False))
        sys.exit(1)
    except PermissionError as e:
        print(json.dumps({"success": False, "error_code": "audit_pending",
                          "message": "机构信息正在审核中, 暂不可提交证件更新",
                          "field_errors": {}}, ensure_ascii=False))
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        need_refresh = isinstance(e, MCPAuthError)
        print(json.dumps({"success": False,
                          "error_code": "auth_failed" if need_refresh else "mcp_error",
                          "message": f"构造 UI 入参失败: {_sanitize(str(e))}",
                          "field_errors": {},
                          "need_refresh": need_refresh}, ensure_ascii=False))
        sys.exit(1)


def main():
    observe_entrypoint(CALLER_EXPERT_ID, "alert.build_cert_ui_params", "build_cert_ui_params", _main)


if __name__ == "__main__":
    main()
