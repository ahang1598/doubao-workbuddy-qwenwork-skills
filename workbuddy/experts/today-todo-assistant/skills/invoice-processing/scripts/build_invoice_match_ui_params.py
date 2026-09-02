#!/usr/bin/env python3
"""
build_invoice_match_ui_params.py — 票据匹配复核 UI 呼起参数装配

对齐 alert-expert/build_record_ui_params.py: 把「调用 open_invoice_match_review_ui 的完整入参
UiReq」先落盘为 json(由 run_pipeline 产出 ui_req.json), 再经 set_common_data_cache 缓存到
远程得到 data_cache_id, 最终只把 {caller_expert_id, data_cache_id} 交给 UI 接口。

这样可彻底规避「agent 把大体积 UiReq(含两个 repeated MatchItem 数组)经 stdout 透传时,
被二次序列化成字符串」导致的 []json.RawMessage 调用失败事故——数组永远只在 Python 侧
json.dumps 一次, 由 set_common_data_cache 直连发送, agent 不再触碰数组。

流程:
  1. 读取 run_pipeline 产出的 ui_req.json(含 org_no / matched_items / matched_failed_items / submit)
  2. 补全 caller_expert_id(缺省 invoice-expert)
  3. set_common_data_cache(ui_req_with_caller) -> data_cache_id
  4. 写出 ui_params.json = {caller_expert_id, data_cache_id}
  5. stdout 打印一行成功指针(output_file 等)

退出码: 0=成功, 2=参数/校验/缓存失败(失败信息以 {success:false,...} 输出)
"""
import argparse
import json
import os
import sys

sys.path.insert(
    0,
    os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_common")),
)
from mcp_client import (
    call_mcp,
    set_common_data_cache,
    CALLER_EXPERT_ID,
    mask,
    _sanitize,
    MCPAuthError,
)
from observe_bootstrap import observe_entrypoint


def _err(msg, error_code="input_invalid", need_refresh=False):
    print(json.dumps({"success": False, "error_code": error_code,
                      "message": msg, "need_refresh": need_refresh}, ensure_ascii=False))
    sys.exit(1)


def _main():
    ap = argparse.ArgumentParser(description="把 ui_req.json 缓存为 data_cache_id 并写出 UI 呼起参数")
    ap.add_argument("--json-file", required=True, help="run_pipeline 产出的 ui_req.json 路径")
    ap.add_argument(
        "--output-file",
        default=None,
        help="ui_params.json 输出路径; 缺省: <json-file>.ui_params.json",
    )
    args = ap.parse_args()

    if not os.path.isfile(args.json_file):
        _err(f"ui_req 文件不存在: {args.json_file}", "file_not_found")
    try:
        with open(args.json_file, "r", encoding="utf-8") as f:
            ui_req = json.load(f)
    except Exception as e:
        _err(f"ui_req 文件解析失败: {e}", "json_parse")

    if not isinstance(ui_req, dict):
        _err("ui_req 必须是一个 JSON 对象", "payload_not_object")

    # 补全 caller_expert_id(UI 入参与缓存内容都需带上, 与 alert-expert 对齐)
    if not ui_req.get("caller_expert_id"):
        ui_req["caller_expert_id"] = CALLER_EXPERT_ID

    # 基础结构校验(缓存失败会暴露, 但提前校验更友好)
    if not ui_req.get("org_no"):
        _err("ui_req 缺少 org_no", "org_no_missing")
    submit = ui_req.get("submit")
    if not isinstance(submit, dict) or not submit.get("next_step"):
        _err("ui_req.submit 缺失或缺少 next_step", "submit_missing")

    # 缓存到远程 -> data_cache_id
    try:
        key = set_common_data_cache(ui_req)
    except MCPAuthError as e:
        _err(f"鉴权失败: {e}", "auth_failed", need_refresh=True)
    except Exception as e:
        _err(f"set_common_data_cache 调用失败: {e}", "mcp_error")

    if not key:
        _err("set_common_data_cache 未返回 data_cache_id", "mcp_error")

    out = {
        "caller_expert_id": ui_req["caller_expert_id"],
        "data_cache_id": key,
    }
    output_file = args.output_file or (args.json_file + ".ui_params.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(
        json.dumps(
            {
                "success": True,
                "output_file": output_file,
                "caller_expert_id": out["caller_expert_id"],
                "data_cache_id": key,
            },
            ensure_ascii=False,
        )
    )


def main():
    observe_entrypoint(CALLER_EXPERT_ID, "invoice.build_invoice_match_ui_params", "build_invoice_match_ui_params", _main)


if __name__ == "__main__":
    main()
