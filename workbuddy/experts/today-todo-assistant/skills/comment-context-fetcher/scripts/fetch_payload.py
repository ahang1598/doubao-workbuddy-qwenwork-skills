#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
腾讯公益留言运营专家 · 上下文数据批量拉取脚本
====================================
职责：参考 org-work-summary/fetch_templates.py 的模式，直连 oapi HTTP 接口
      批量拉取待回复留言 + 项目/进展上下文，大 JSON 直接落盘，不经过 LLM。

一次调用完成整个拉取+组装链路（Agent 无需逐次 MCP 调用）：
  1. get_org_upreplied_comments  → unreplied_comments.json（留言列表，全字段透传）
  2. project 组 get_project_detail（按 project_id 去重）→ project_<id>.json
  3. project 组 get_process_list（固定 index=1/size=5/platform_version=3/status=1/publish_status=-1，按 project_id 去重）→ process_list_<pid>.json
  4. process 组 get_process_detail（按 object_id 去重）→ process_<id>.json
  5. process 所属项目 get_project_detail（按 project_id 去重，与 project 组合并去重）→ project_<pid>.json
  6. 组装精简 contexts.json + comments_brief.json（原 build_contexts.py，已合并进本脚本）

缓存策略：单次 run 内按 id 去重（同一项目/进展仅拉一次，全部并行请求），
不做跨 run 磁盘缓存——每次 run 都实时拉取；留言列表始终实时拉取不缓存。

全部并行拉取；失败项落盘 {"error_code": ...}，不阻断其他项。

用法：
  python3 skills/comment-context-fetcher/scripts/fetch_payload.py \
    --token "<get_mcp_token 返回的 token>" \
    --caller-expert-id "comment-assistant"

参数：
  --token              MCP Token（脚本按 token 中的 prod/test 环境段自动路由端点，
                       不约定具体前缀格式；无法识别时需用 --endpoint 显式指定）
  --endpoint           接口地址显式覆盖（可选，调试/新型 token 兜底）
  --start-time         查询起始 Unix 秒（可选；不传则脚本内部按「当前 Unix 秒 - 2592000（30 天前）」实时计算）
  --out-dir            落盘根目录（可选；不传则脚本内部按 ./output/.cache/<当前Unix秒>/raw 生成，
                       并通过 stdout 第一行 JSON 输出实际路径，调用方无需自行计算时间戳）
  --caller-expert-id   调用方专家 ID（默认 comment-assistant）
  --page               留言分页页码（默认 0）
  --size               留言分页大小（默认 30）

stdout 第一行固定输出路径 JSON（供调用方读取后续阶段所需目录）：
  {"out_dir": "<abs>/raw", "run_dir": "<abs>"}

产出（out-dir 下）：
  unreplied_comments.json    {"code":0,"total":N,"risk_total":M,"list":[...OrgCommentItem...]}
  project_<project_id>.json  项目详情原始响应（data 对象）
  process_list_<pid>.json    {"code":0,"list":[...≤5条进展...]}
  process_<object_id>.json   进展详情原始响应（data 对象）
产出（out-dir 上级目录，供 AI 生成/组装阶段读取，indent=2 格式化落盘、行宽受控，
Agent 用 Read 工具一次即可完整读入，禁止脚本二次提取）：
  contexts.json              {"projects": {...}, "contexts": {...}} 两段式精简上下文：
                             projects 按 project_id 单独存放项目数据（project_detail 含
                             基础字段+项目背景/爱心故事/募捐信息/执行地(名称)/生效备案号预算，
                             process_list 仅 project 类型留言所属项目有），contexts 按
                             object_type:object_id 复合键存放各留言对象上下文、以
                             project_id 引用 projects
  comments_brief.json        留言精简列表（12 个协议字段白名单，保持后台原始数组顺序；
                             comment_id 统一为 uint64 数字——上游若以字符串返回，
                             落盘前已转为 int，本地文件与 set_common_data_cache 全程
                             为 JSON number，不得出现字符串形态；
                             生成与 UI 组装共用同一份，Agent 读一次即可）

上下文缓存：单次 run 内按 id 去重（同一 id 仅拉一次），不做跨 run 磁盘缓存——
项目详情 / 进展列表 / 进展详情每次 run 都实时拉取；留言列表始终实时拉取不缓存。

接口路径与 x1 规则（仅 comment_svc 带 x1，其余不带）：
  comment_svc:      /api/comment_svc/ListOrgUnrepliedCommentsForOrgPlatform（带 x1）
  proc_manage:      /api/proc_manage/GetProcessList、/api/proc_manage/GetProcessDetail（不带 x1）
  project_manager:  /api/project_manager_trpc/GetProjectDetailForSkill（不带 x1）
"""

import argparse
import html
import json
import os
import re
import stat
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

# 可观测埋点（非关键路径：SDK 不可用时自动降级为 no-op，绝不影响业务流程）
sys.path.insert(
    0,
    os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_common")
    ),
)
from observe_bootstrap import (  # noqa: E402
    expert_version,
    galileo_observer,
    galileo_topic,
    observe_span,
)

# 环境路由：不枚举具体 token 前缀（B 端长期 token gy_open_mcp_*、WorkBuddy OAuth
# access token gy_mcp_at_*、以及未来新增类型），只按 token 中是否含 prod/test
# 环境段判定；无法判定时 fail-closed 报错，由调用方用 --endpoint 显式指定。
ENDPOINT_PROD = "https://oapi.gongyi.qq.com"
ENDPOINT_TEST = "https://test-oapi.gongyi.qq.com"

EXIT_OK = 0
EXIT_PARAM_ERROR = 2
EXIT_TOKEN_ERROR = 10

# oapi 各接口路径与 x1 规则（仅 comment_svc 接口指定 x1，其余一律不带）
COMMENT_LIST_PATH = "/api/comment_svc/ListOrgUnrepliedCommentsForOrgPlatform"  # comment_svc，带 x1
PROCESS_LIST_PATH = "/api/proc_manage/GetProcessList"                          # proc_manage，不带 x1
PROCESS_DETAIL_PATH = "/api/proc_manage/GetProcessDetail"                      # proc_manage，不带 x1
PROJECT_DETAIL_PATH = "/api/project_manager_trpc/GetProjectDetailForSkill"     # project_manager_trpc，不带 x1

# project 类型留言的进展列表固定参数（产品约定，不可调整）
PROCESS_LIST_FIXED = {
    "index": 1,
    "size": 5,
    "platform_version": 3,
    "status": 1,
    "publish_status": -1,
}

# ---- 上下文组装（原 build_contexts.py，已合并）----

# 生成回复所需的项目详情关键字段（对接口原始 Info 做字段裁剪）
PROJECT_KEYS = [
    "project_name", "project_intro", "project_type", "fundras_filing_code",
    "closing_date", "close_fundraising_time", "exec_org_name", "project_status",
    "budget_total", "raised_amount", "donor_count",
    "project_first_name", "project_second_name",
    "fundras_object_first_name", "fundras_object_second_name",
]

# 项目 Detail 中的富文本字段（项目背景），落盘前剥离 HTML 标签
# （受助对象故事 aided_obj_story / 项目倡导 advocacy 不纳入，爱心故事走 loveStory）
PROJECT_RICH_TEXT_KEYS = [
    "project_backdrop_title", "project_backdrop",
]

# 爱心故事（loveStory）元素关键字段
LOVE_STORY_KEYS = [
    "story_name", "story_intro", "story_summary",
]

# 募捐信息（donate）关键字段
DONATE_KEYS = [
    "fundras_cycle_start_time", "fundras_cycle_end_time",
    "beneficiaries", "assisted_materials_unit", "assisted_materials",
]

# 生效备案号预算（filing_budget 中 is_valid=1 的那条）预算表（budget_list）元素关键字段
# （仅保留 4 个语义字段：费用项一/二级名称、执行内容、费用项说明；
#  单价/数量/单位/合计/备注不纳入，避免 AI 直接引用未经核对的金额数字）
FILING_BUDGET_INFO_KEYS = [
    "cost_item_one_name", "cost_item_two_name", "execution_content", "amount_desc",
]

# 进展条目关键字段（process_list 的元素）
PROCESS_ITEM_KEYS = [
    "id", "content_title", "desc", "concrete_info", "publish_time",
]

# 进展详情关键字段（process_detail）
PROCESS_DETAIL_KEYS = [
    "id", "project_id", "content_title", "desc", "concrete_info",
    "publish_time", "content",
]

# AI 生成 + UI 组装共用的留言字段（comments_brief.json；即 open_comment_reply_ui 入参的
# 12 个协议字段白名单，head_img 用于前端展示评论者头像）。
# Agent 一次读入后，Phase 2 生成与 Phase 3 组装复用同一份列表，无需回读 raw
BRIEF_KEYS = [
    "comment_id", "subject_id", "content", "project_id", "project_name",
    "created_at", "nick_name", "object_type", "object_id",
    "risk_audit_status", "risk_audit_reason", "head_img",
]


def load_json(path: str):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def pick(d: dict, keys):
    return {k: d.get(k) for k in keys if k in d and d.get(k) is not None}


def strip_html(value):
    """剥离富文本字段的 HTML 标签与实体，压缩空白，供 LLM 直接消费。非字符串原样返回。"""
    if not isinstance(value, str):
        return value
    text = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def slim_executor_sites(resp: dict):
    """裁剪执行地列表：仅保留省市区**名称**三个字段（province_name/city_name/area_name，
    编码不写入，避免 AI 二次解析），按（省/市/区）去重。

    名称由服务端 GetProjectDetailForSkill 统一回填（fillExecutorSiteNames）；
    名称为空的条目（如服务降级未回填）直接跳过，宁缺毋滥。
    """
    sites = []
    seen = set()
    raw = resp.get("executorSite") or resp.get("executor_site") or []
    for s in raw:
        if not isinstance(s, dict):
            continue
        item = {}
        for level in ("province", "city", "area"):
            v = s.get(f"{level}_name")
            if v:
                item[f"{level}_name"] = v
        key = (item.get("province_name"), item.get("city_name"), item.get("area_name"))
        if not any(key) or key in seen:
            continue
        seen.add(key)
        sites.append(item)
    return sites


def slim_filing_budget(resp: dict):
    """取 filing_budget 中 is_valid=1 的生效备案号预算：筹款目标 + 预算表。

    仅 is_valid=1 的条目写入 contexts.json，失效条目（is_valid=0）一律丢弃；
    兼容 is_valid 以数字 1 或字符串 "1" 返回两种形态。
    """
    raw = resp.get("filing_budget") or resp.get("FilingBudget") or []
    for fb in raw:
        if not isinstance(fb, dict) or str(fb.get("is_valid")) != "1":
            continue
        out = {}
        target = fb.get("fundras_target")
        if target not in (None, ""):
            out["fundras_target"] = target
        budget_list = [
            pick(b, FILING_BUDGET_INFO_KEYS)
            for b in (fb.get("budget_list") or [])
            if isinstance(b, dict)
        ]
        budget_list = [b for b in budget_list if b]
        if budget_list:
            out["budget_list"] = budget_list
        return out or None
    return None


def slim_project(resp: dict):
    """裁剪项目详情：Info 基础字段（含分类/资助对象名称）+ Detail 富文本（项目背景）
    + 爱心故事（loveStory）+ 募捐信息 + 执行地 + 生效备案号预算。
    （受助对象故事 aided_obj_story / 项目倡导 advocacy 不纳入）"""
    if not isinstance(resp, dict) or "error_code" in resp:
        return None
    info = resp.get("Info") or resp.get("info") or resp
    if not isinstance(info, dict):
        return None
    out = pick(info, PROJECT_KEYS)
    detail = resp.get("detail") or resp.get("Detail") or {}
    if isinstance(detail, dict):
        for k in PROJECT_RICH_TEXT_KEYS:
            v = detail.get(k)
            if v:
                out[k] = strip_html(v)
    stories = resp.get("loveStory") or resp.get("love_story") or []
    story_list = []
    for s in stories:
        if not isinstance(s, dict):
            continue
        item = pick(s, LOVE_STORY_KEYS)
        for k in ("story_intro", "story_summary"):
            if k in item:
                item[k] = strip_html(item[k])
        if item:
            story_list.append(item)
    if story_list:
        out["love_story_list"] = story_list
    donate = resp.get("donate") or resp.get("Donate") or {}
    if isinstance(donate, dict):
        for k in DONATE_KEYS:
            v = donate.get(k)
            if v not in (None, ""):
                out[k] = v
    sites = slim_executor_sites(resp)
    if sites:
        out["executor_site"] = sites
    filing_budget = slim_filing_budget(resp)
    if filing_budget:
        out["filing_budget"] = filing_budget
    return out or None


def slim_process_detail(resp: dict):
    if not isinstance(resp, dict) or "error_code" in resp:
        return None
    info = resp.get("Info") or resp.get("info") or resp
    if not isinstance(info, dict):
        return None
    return pick(info, PROCESS_DETAIL_KEYS)


def slim_process_list(resp: dict):
    """返回进展条目数组（≤5），无进展/失败返回 []。"""
    if not isinstance(resp, dict) or "error_code" in resp:
        return []
    lst = resp.get("list") or []
    return [pick(it, PROCESS_ITEM_KEYS) for it in lst if isinstance(it, dict)]


def build_contexts(comment_list, raw_dir: str):
    """读取 raw 落盘数据，组装精简 contexts.json + comments_brief.json。

    contexts.json 结构（项目数据单独存放、按 project_id 引用，避免同一项目的
    project_detail 在多条进展上下文里重复内嵌）：
      {
        "projects": { "<project_id>": {"project_detail": {...}, "process_list": [...]} },
        "contexts": {
          "project:<id>":  {"type": "project", "project_id": "<id>"},
          "process:<id>":  {"type": "process", "process_detail": {...}, "project_id": "<pid>"}
        }
      }
    process_list 仅对 project 类型留言所属项目拉取（process 类型所属项目无此键）。

    产出到 raw_dir 上级目录，返回 (payload, brief)，payload 即 contexts.json 内容。
    """
    contexts = {}
    projects = {}
    brief = []

    def ensure_project(pid: str, with_process_list: bool):
        """按 project_id 建立/补全 projects 条目（同一项目仅裁剪一次）。"""
        if not pid:
            return
        entry = projects.get(pid)
        if entry is None:
            entry = {
                "project_detail": slim_project(
                    load_json(os.path.join(raw_dir, f"project_{pid}.json")) or {}
                )
            }
            projects[pid] = entry
        if with_process_list and "process_list" not in entry:
            entry["process_list"] = slim_process_list(
                load_json(os.path.join(raw_dir, f"process_list_{pid}.json")) or {}
            )

    for item in comment_list:
        if not isinstance(item, dict):
            continue
        brief_item = {k: item.get(k) for k in BRIEF_KEYS if k in item}
        # comment_id 协议为 uint64：上游若以字符串返回，落盘前统一转为 int（Python int
        # 无精度问题），保证本地 JSON 文件与下游 set_common_data_cache 全程为 JSON number，
        # 任何环节不得再出现字符串形态
        cid = brief_item.get("comment_id")
        if isinstance(cid, str) and cid.isdigit():
            brief_item["comment_id"] = int(cid)
        brief.append(brief_item)
        otype = item.get("object_type")
        oid = str(item.get("object_id") or "")
        if not otype or not oid:
            continue
        key = f"{otype}:{oid}"
        if otype == "project":
            ensure_project(oid, with_process_list=True)
            contexts[key] = {"type": "project", "project_id": oid}
        elif otype == "process":
            pdetail = slim_process_detail(
                load_json(os.path.join(raw_dir, f"process_{oid}.json")) or {}
            )
            pid = str(item.get("project_id") or "")
            ensure_project(pid, with_process_list=False)
            contexts[key] = {
                "type": "process",
                "process_detail": pdetail,
                "project_id": pid,
            }

    payload = {"projects": projects, "contexts": contexts}
    out_dir = os.path.dirname(os.path.abspath(raw_dir))
    # 这两个文件是 Agent 用 Read 工具直接读入的产物，必须 pretty 落盘（行宽受控，一次读全）
    write_file(os.path.join(out_dir, "contexts.json"), payload, pretty=True)
    write_file(os.path.join(out_dir, "comments_brief.json"), brief, pretty=True)
    return payload, brief


def fail(message: str, exit_code: int = EXIT_PARAM_ERROR) -> None:
    print(f"fetch_payload error: {message}", file=sys.stderr)
    sys.exit(exit_code)


def get_endpoint(token: str, endpoint_override: str = "") -> str:
    """按 token 中的环境段（_prod_ / _test_）路由端点，不约定具体 token 前缀格式。

    endpoint_override 非空时优先使用（显式指定，绕过自动路由）；
    token 中同时不含 prod/test 段时 fail-closed 报错，不猜默认环境。
    """
    if endpoint_override:
        return endpoint_override
    if "_prod_" in token:
        return ENDPOINT_PROD
    if "_test_" in token:
        return ENDPOINT_TEST
    fail(
        "token 中未识别到环境段（_prod_ / _test_），请用 --endpoint 显式指定接口地址",
        EXIT_TOKEN_ERROR,
    )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="批量拉取留言与上下文数据并落盘")
    parser.add_argument(
        "--token",
        default=None,
        help="MCP Token（get_mcp_token 返回）；不传时读全局缓存 ~/.workbuddy/.gongyi_token",
    )
    parser.add_argument("--page", type=int, default=0, help="留言列表页码，0 开始")
    parser.add_argument("--size", type=int, default=30, help="留言列表每页大小，固定 30")
    parser.add_argument(
        "--start-time",
        type=int,
        default=None,
        help="查询起始时间（Unix 秒），不传则脚本内部按「当前 Unix 秒 - 2592000（30 天前）」实时计算",
    )
    parser.add_argument(
        "--mock-org-no", default="", help="模拟机构 ID（仅七彩石 mock 模式生效）"
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="数据落盘目录；不传则脚本内部按 output/.cache/<当前Unix秒>/raw 生成",
    )
    parser.add_argument(
        "--caller-expert-id", default="comment-assistant", help="调用方 expert id"
    )
    parser.add_argument("--max-workers", type=int, default=10, help="并发数")
    parser.add_argument("--timeout", type=int, default=60, help="HTTP 超时秒数")
    parser.add_argument(
        "--endpoint",
        default="",
        help="接口地址显式覆盖（可选）；不传时按 token 中的 prod/test 环境段自动路由",
    )
    return parser.parse_args(argv)


def write_file(path: str, content, pretty: bool = False) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        if pretty:
            # Agent 需用 Read 工具读入的产物必须 indent=2 格式化：
            # 单行紧凑 JSON 单行过长会被 Read 截断，引发「读取→截断→脚本提取」的多轮重复往返
            json.dump(content, fh, ensure_ascii=False, indent=2)
        else:
            json.dump(content, fh, ensure_ascii=False, separators=(",", ":"))


def call_tool(
    endpoint: str,
    token: str,
    path: str,
    arguments: dict,
    use_x1: bool,
    timeout: int,
) -> dict:
    """直连 oapi HTTP 接口，body 直接传参数，返回 data 对象。

    use_x1 控制是否注入 Gy-H-Test-Env-Key: x1（仅 comment_svc 接口为 True，
    其余 proc_manage / project_manager_trpc 一律 False）。
    """
    url = endpoint + path
    body = json.dumps(arguments, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Gy-H-Mcp-Token": token,
    }
    # 仅 comment_svc 接口注入测试环境 key，prod 环境本身不需要
    if endpoint == ENDPOINT_TEST and use_x1:
        headers["Gy-H-Test-Env-Key"] = "x1"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
    except Exception as e:
        return {"error_code": -2, "msg": repr(e)}
    finally:
        # 单请求耗时埋点（stderr），用于定位拉取阶段的慢接口
        print(f"[fetch] {path} 耗时 {time.time() - started:.1f}s", file=sys.stderr)

    try:
        resp_obj = json.loads(raw)
    except json.JSONDecodeError:
        return {"error_code": -3, "raw": raw[:500]}

    # 双层包装：code → 外层网关业务码；data → 实际数据（含列表或详情对象）
    outer_code = resp_obj.get("code")
    if outer_code != 0:
        return {"error_code": outer_code, "msg": resp_obj.get("msg", "")}
    outer_data = resp_obj.get("data")
    return outer_data if isinstance(outer_data, dict) else {}


# ---------------------------------------------------------------------------
# MCP token 全局缓存（对齐 invoice-expert skills/_common/mcp_client.py 约定）
#
# - 固定全局路径 ~/.workbuddy/.gongyi_token，跨专家共享（同一台机器同一环境）；
#   token 内含环境段（_prod_ / _test_），测试/正式环境切换由后端换发 token 天然隔离，
#   无需按环境分文件
# - 本地不判断过期时间（get_mcp_token 响应无 expires_in 契约）：文件里有就直接用，
#   过期以接口实际鉴权失败为准——识别口径对齐 mcp_client._is_auth_error：
#   「先确认是错误响应，再在错误文案里匹配鉴权关键词」，命中后打印 need_refresh JSON
#   并以特定退出码退出，Agent 据此调 get_mcp_token 重取（新 token 覆盖写回缓存）后重跑
# ---------------------------------------------------------------------------
TOKEN_CACHE_PATH = os.path.expanduser(os.path.join("~", ".workbuddy", ".gongyi_token"))

# 鉴权失败关键词（仅在返回确为"错误"时命中才视为 token 失效，避免正常业务文案误伤）
AUTH_HINTS = (
    "unauthorized", "unauthenticated", "token expired", "token invalid",
    "invalid token", "permission denied", "forbidden", "鉴权失败",
    "未登录", "登录失效", "401",
)

EXIT_NO_TOKEN = 3       # 本地无 token 缓存
EXIT_NEED_REFRESH = 4   # 接口鉴权失败，token 过期/失效


def load_cached_token():
    """读取全局缓存的 token；文件不存在或内容为空时返回 None"""
    try:
        with open(TOKEN_CACHE_PATH, encoding="utf-8") as f:
            token = f.read().strip()
        return token or None
    except OSError:
        return None


def save_token_cache(token):
    """把新获取的 token 覆盖写入全局缓存（0600 权限），供后续 run / 其他专家复用"""
    try:
        os.makedirs(os.path.dirname(TOKEN_CACHE_PATH), exist_ok=True)
        with open(TOKEN_CACHE_PATH, "w", encoding="utf-8") as f:
            f.write(token)
        os.chmod(TOKEN_CACHE_PATH, stat.S_IRUSR | stat.S_IWUSR)
    except OSError as e:
        print(f"[fetch] token 缓存写入失败（不影响本次运行）: {e!r}", file=sys.stderr)


def clear_token_cache():
    """token 失效时删除全局缓存，避免后续 run 继续复用坏 token"""
    try:
        os.remove(TOKEN_CACHE_PATH)
    except OSError:
        pass


def emit_need_refresh(reason):
    """鉴权失败统一出口：打印 need_refresh JSON（对齐 mcp_client 约定）。"""
    print(json.dumps(
        {"need_refresh": True, "error": "token_invalid", "message": reason},
        ensure_ascii=False,
    ))


def is_auth_error(err_obj):
    """判断接口返回是否表示鉴权失败（token 过期/失效）。

    err_obj 为 call_tool 归一化后的错误对象 {"error_code": ..., "msg": ...}。
    鉴权关键词只在错误文案 msg 中匹配——本函数只会在接口已返回错误时被调用，
    因此不会出现成功返回误判（对齐 mcp_client._is_auth_error 的语义）。
    """
    text = str(err_obj.get("msg", "")).lower()
    return any(h in text for h in AUTH_HINTS)


# 模块级观测结果透传：_main 内记录关键业务指标，main 的 trace.set_result 统一上报
_OBSERVE_RESULT = {}


def _main(argv=None) -> int:
    global _OBSERVE_RESULT
    _OBSERVE_RESULT = {}
    args = parse_args(argv)
    # --token 显式传入时优先使用（通常为新获取的 token，覆盖写回全局缓存）；
    # 未传时读全局缓存文件，文件里有就直接用、不重新拉取
    if args.token:
        token = args.token
        save_token_cache(token)
    else:
        token = load_cached_token()
        if not token:
            emit_need_refresh(
                f"本地无 token 缓存({TOKEN_CACHE_PATH} 不存在或为空)，"
                "请 agent 调用 get_mcp_token 获取 token 后以 --token 传入"
            )
            return EXIT_NO_TOKEN
    endpoint = get_endpoint(token, args.endpoint)
    # out-dir 不传时脚本内部按「当前 Unix 秒」生成，调用方无需 bash 计算时间戳
    out = args.out_dir or os.path.join("output", ".cache", str(int(time.time())), "raw")
    os.makedirs(out, exist_ok=True)
    # stdout 第一行固定输出路径 JSON，供调用方读取后续阶段所需目录
    abs_out = os.path.abspath(out)
    print(
        json.dumps(
            {"out_dir": abs_out, "run_dir": os.path.dirname(abs_out)},
            ensure_ascii=False,
        )
    )

    def fetch(path, arguments, use_x1):
        return call_tool(
            endpoint, token, path, arguments, use_x1, args.timeout
        )

    # ---- 第 1 步：拉取待回复留言列表（大 JSON 直接落盘，不进 LLM）----
    # start_time 默认脚本内部按「当前 Unix 秒 - 2592000（30 天前）」实时计算；
    # 调用方显式传 --start-time 时按传入值（兼容调试/复现）。
    # 仅传实际用到的参数：page/size/start_time（30天窗口）；mock_org_no 仅在非空时传（mock 模式）
    if args.start_time is None:
        start_time = int(time.time()) - 2592000
    else:
        start_time = args.start_time
    comments_args = {
        "page": args.page,
        "size": args.size,
        "start_time": start_time,
    }
    if args.mock_org_no:
        comments_args["mock_org_no"] = args.mock_org_no
    with observe_span(
        "comment_assistant.fetch.comments",
        kind="tool",
        attributes={"page": args.page, "size": args.size, "start_time": start_time},
    ) as comments_span:
        comments = fetch(COMMENT_LIST_PATH, comments_args, use_x1=True)
        comment_list = comments.get("list") or []
        comment_ids = [str(it.get("comment_id")) for it in comment_list if isinstance(it, dict)]
        # 响应侧关键字段：让「拉取列表」一个 span 完整反映请求+响应
        comments_span.set_attributes(
            total=comments.get("total"),
            risk_total=comments.get("risk_total"),
            comment_count=len(comment_ids),
            comment_ids=comment_ids,
        )
    write_file(os.path.join(out, "unreplied_comments.json"), comments)

    if "error_code" in comments:
        print(
            f"[fetch] get_org_upreplied_comments 失败 error_code={comments['error_code']}",
            file=sys.stderr,
        )
        if is_auth_error(comments):
            # token 过期/失效：删除全局缓存并打印 need_refresh JSON（对齐 mcp_client 约定），
            # Agent 据此调 get_mcp_token 获取新 token 后以 --token 重跑本脚本
            clear_token_cache()
            emit_need_refresh(
                f"接口鉴权失败，token 缓存已清除({TOKEN_CACHE_PATH})，"
                "请 agent 调用 get_mcp_token 重新获取后以 --token 重跑"
            )
            return EXIT_NEED_REFRESH
        # 非鉴权类失败（业务错误）：保留缓存，按原业务失败码退出
        return EXIT_OK

    comment_list = comments.get("list") or []
    _OBSERVE_RESULT["total"] = comments.get("total")
    _OBSERVE_RESULT["risk_total"] = comments.get("risk_total")
    _OBSERVE_RESULT["comment_count"] = len(comment_ids)
    _OBSERVE_RESULT["comment_ids"] = comment_ids
    print(
        f"[fetch] 留言列表 total={comments.get('total')} "
        f"risk_total={comments.get('risk_total')} list_len={len(comment_list)}",
        file=sys.stderr,
    )

    # ---- 第 2 步：分类去重，收集各组 ID（单次 run 内按 id 去重，同一 id 仅拉一次）----
    project_ids = []  # project 评论的项目 object_id（去重）
    process_ids = []  # process 评论的进展 object_id（去重）
    process_pids = []  # process 评论所属项目的 project_id（去重）
    for item in comment_list:
        if not isinstance(item, dict):
            continue
        otype = item.get("object_type")
        oid = str(item.get("object_id") or "")
        if otype == "project" and oid and oid not in project_ids:
            project_ids.append(oid)
        elif otype == "process" and oid and oid not in process_ids:
            process_ids.append(oid)
            pid = str(item.get("project_id") or "")
            if pid and pid not in process_pids:
                process_pids.append(pid)

    # project 组与 process 所属项目组合并去重（同一项目仅拉一次项目详情）
    all_project_detail_ids = []
    for pid in project_ids + process_pids:
        if pid not in all_project_detail_ids:
            all_project_detail_ids.append(pid)

    print(
        f"[fetch] 去重后 project={len(project_ids)} process={len(process_ids)} "
        f"项目详情(含process所属)={len(all_project_detail_ids)}",
        file=sys.stderr,
    )

    # ---- 第 3 步：并行拉取各类上下文并落盘 ----
    def job(func):
        try:
            func()
        except Exception as e:  # 兜底：单项失败不影响整体
            print(f"[fetch] 子任务异常 {e!r}", file=sys.stderr)

    def fetch_project_detail(pid):
        data = fetch(PROJECT_DETAIL_PATH, {"project_no": pid}, use_x1=False)
        write_file(os.path.join(out, f"project_{pid}.json"), data)

    def fetch_process_list(pid):
        arguments = dict(PROCESS_LIST_FIXED)
        try:
            arguments["project_id"] = int(pid)
        except ValueError:
            write_file(
                os.path.join(out, f"process_list_{pid}.json"),
                {"error_code": -6, "msg": f"project_id 非数字: {pid}"},
            )
            return
        data = fetch(PROCESS_LIST_PATH, arguments, use_x1=False)
        write_file(os.path.join(out, f"process_list_{pid}.json"), data)

    def fetch_process_detail(oid):
        try:
            nid = int(oid)
        except ValueError:
            write_file(
                os.path.join(out, f"process_{oid}.json"),
                {"error_code": -6, "msg": f"object_id 非数字: {oid}"},
            )
            return
        data = fetch(PROCESS_DETAIL_PATH, {"id": nid}, use_x1=False)
        write_file(os.path.join(out, f"process_{oid}.json"), data)

    with observe_span(
        "comment_assistant.fetch.contexts",
        kind="tool",
        attributes={
            "project_cnt": len(all_project_detail_ids),
            "process_list_cnt": len(project_ids),
            "process_detail_cnt": len(process_ids),
        },
    ):
        with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            futures = []
            for pid in all_project_detail_ids:
                futures.append(executor.submit(job, lambda p=pid: fetch_project_detail(p)))
            for pid in project_ids:
                futures.append(executor.submit(job, lambda p=pid: fetch_process_list(p)))
            for oid in process_ids:
                futures.append(executor.submit(job, lambda o=oid: fetch_process_detail(o)))
            for f in futures:
                f.result()

    print(
        f"[fetch] 上下文拉取完成（共 {len(futures)} 项，run 内去重实时拉取，无跨 run 缓存），输出目录 {out}",
        file=sys.stderr,
    )

    # ---- 第 4 步：组装生成上下文（原 build_contexts.py，已合并）----
    # 产出 contexts.json + comments_brief.json 到 out 上级目录，供 AI 生成阶段直接读取
    with observe_span("comment_assistant.fetch.build_contexts", kind="tool"):
        payload, brief = build_contexts(comment_list, out)
    print(
        f"[build] projects={len(payload['projects'])} "
        f"contexts={len(payload['contexts'])} brief={len(brief)} → "
        f"{os.path.dirname(os.path.abspath(out))}",
        file=sys.stderr,
    )
    return EXIT_OK


# 退出码 → 埋点错误类型映射（仅非 0 时上报 error_type）
_EXIT_ERROR_TYPES = {
    EXIT_NO_TOKEN: "NO_CACHED_TOKEN",
    EXIT_NEED_REFRESH: "TOKEN_INVALID",
}


def main(argv=None) -> int:
    """埋点 trace 包装：上报整体耗时、退出码与业务结果；失败不影响业务。"""
    observer = galileo_observer(
        "comment-assistant",
        expert_version(),
        galileo_topic=galileo_topic(),
        spool_dir=os.path.join("output", ".observe"),
    )
    run_id = str(int(time.time()))
    with observer.trace(
        "comment_assistant.fetch_payload",
        run_id=run_id,
        session_id=run_id,
        attributes={"entrypoint": "fetch_payload"},
    ) as observe_trace:
        try:
            exit_code = _main(argv)
        except SystemExit as error:
            code = error.code if isinstance(error.code, int) else 1
            observe_trace.set_result(
                success=(code == 0),
                error_type=None if code == 0 else "FETCH_FAILED",
                status_message=None if code == 0 else "fetch payload failed",
                attributes={"exit_code": code},
            )
            raise
        result_attrs = {"exit_code": exit_code}
        result_attrs.update(_OBSERVE_RESULT)
        observe_trace.set_result(
            success=(exit_code == 0),
            error_type=_EXIT_ERROR_TYPES.get(exit_code),
            attributes=result_attrs,
        )
        return exit_code


if __name__ == "__main__":
    sys.exit(main())
