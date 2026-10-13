"""generate-report 命令

从 AI 表格导出的 JSON 数据生成 HTML 格式的督导报告。

用法：
  python cli.py generate-report <inspection_data.json> --fields <fields.json> [--output report.html]
  python cli.py generate-report <data.json> --fields <fields.json> --template ~/my_template.html --save-template multi

模板优先级（从高到低）：
  1. 本次通过 --template 显式传入的 HTML 文件（可配合 --save-template 持久化）
  2. 持久化目录中的用户自定义模板（~/.store-inspection/custom_report_template_*.html）
  3. 技能内置默认模板（single_store_template.html / report_template.html 对应的内联生成）

单店 vs 多店报告判定规则：
  - 单店报告（--mode single-store）：用户明确指定了一家且仅一家门店生成报告。
    例如"为西溪1店生成报告"、"看看朝阳店的情况"。
  - 多店报告（默认）：涉及多家门店、筛选条件可能命中多家、或未指定具体门店。
    例如"为 A、B 门店生成报告"、"为所有杭州门店生成报告"、"生成今天的巡店报告"。
"""

import json
import os
import re
import sys
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scripts.template_store import (
    check_and_confirm_overwrite,
    has_custom_template,
    read_custom_template,
    save_custom_template,
)

# 内置默认模板路径
_BUILTIN_SINGLE_TEMPLATE = Path(__file__).resolve().parent.parent.parent / "single_store_template.html"
_BUILTIN_MULTI_TEMPLATE = Path(__file__).resolve().parent.parent.parent / "report_template.html"


def _load_template_with_priority(
    report_type: str,
    explicit_template_path: Optional[str] = None,
) -> Optional[str]:
    """按优先级加载 HTML 模板。

    优先级（从高到低）：
    1. explicit_template_path：用户本次通过 --template 显式传入
    2. 持久化的用户自定义模板（~/.store-inspection/custom_report_template_*.html）
    3. 内置默认模板文件

    如果用户没有配置过自定义模板，也没有本次传入，则使用内置默认模板，
    并输出提示告知用户正在使用默认模板。

    Args:
        report_type: "single" 或 "multi"。
        explicit_template_path: 用户本次显式传入的 HTML 模板文件路径。

    Returns:
        HTML 模板字符串，或 None（模板不存在时）。
    """
    # Level 1: 用户本次显式传入
    if explicit_template_path:
        resolved = Path(_expand_path(explicit_template_path))
        if resolved.exists():
            print(f"  📄 使用用户传入的模板: {resolved}")
            return resolved.read_text(encoding="utf-8")
        print(f"  ⚠️ 用户传入的模板文件不存在: {resolved}")

    # Level 2: 持久化的用户自定义模板
    custom_content = read_custom_template(report_type)
    if custom_content:
        print(f"  📄 使用持久化的用户自定义{_type_label(report_type)}模板")
        return custom_content

    # Level 3: 内置默认模板
    builtin_path = (
        _BUILTIN_SINGLE_TEMPLATE if report_type == "single"
        else _BUILTIN_MULTI_TEMPLATE
    )
    if builtin_path.exists():
        type_label = _type_label(report_type)
        print(f"  ℹ️ 当前没有持久化的{type_label}巡店模板，将使用默认模板生成报告")
        return builtin_path.read_text(encoding="utf-8")

    return None


def _type_label(report_type: str) -> str:
    """report_type 转中文标签。"""
    return "单店" if report_type == "single" else "多店"


# ============================================================
# 数据加载与预处理
# ============================================================

def _expand_path(raw_path: str) -> str:
    """展开路径中的 ``~`` 和环境变量。

    Python 的 ``open("~/path")`` 不会像 shell 一样自动展开 ``~``，
    会直接把 ``~`` 当字面字符查找——导致 FileNotFoundError。
    本函数统一处理所有外部传入的路径。
    """
    return os.path.expandvars(os.path.expanduser(raw_path))


def _load_json_file(file_path: str, description: str) -> Any:
    """加载 JSON 文件并返回解析后的数据。"""
    resolved_path = _expand_path(file_path)
    try:
        with open(resolved_path, "r", encoding="utf-8-sig") as file_handle:
            return json.load(file_handle)
    except Exception as error:
        print(f"❌ 加载{description}失败: {error}")
        print(f"   原始路径: {file_path}")
        print(f"   展开路径: {resolved_path}")
        sys.exit(1)


def _build_field_id_map(fields_data) -> Tuple[Dict[str, str], Dict[str, str]]:
    """从 field-get 的输出构建两张映射表。

    Returns:
        (field_id_map, ai_to_attachment_map) 二元组：
        - field_id_map: fieldId → 字段名称
        - ai_to_attachment_map: AI 审核字段名 → 对应附件字段名
          （通过 aiConfig.prompt[].fieldRef.fieldId 关联）
    """
    if isinstance(fields_data, dict):
        # 兼容多种 dws 导出格式：
        #   {items: [...]}  /  {fields: [...]}  /  {data: {fields: [...]}}
        #   {data: {tables: [{fields: [...]}]}}  (dws aitable table get)
        inner = fields_data.get("data", fields_data) if "data" in fields_data else fields_data
        # 处理 {data: {tables: [{fields: [...]}]}} 格式
        if "tables" in inner and isinstance(inner["tables"], list) and inner["tables"]:
            inner = inner["tables"][0]
        field_list = inner.get("items", inner.get("fields", []))
    elif isinstance(fields_data, list):
        field_list = fields_data
    else:
        print("❌ 字段数据格式错误：期望 JSON 对象或数组")
        sys.exit(1)

    field_map: Dict[str, str] = {}
    # 临时收集：AI 审核字段名 → 引用的附件 fieldId
    ai_field_refs: Dict[str, str] = {}

    has_encoding_issue = False
    for field_def in field_list:
        field_id = field_def.get("fieldId") or field_def.get("id", "")
        # 兼容 dws 导出的 "fieldName" 和 report-generator 内部的 "name"
        field_name = (
            field_def.get("name")
            or field_def.get("fieldName")
            or field_id
        )
        # 编码乱码检测：中文字段名变成 ? 说明文件编码不对
        if field_name and "?" in field_name and not has_encoding_issue:
            has_encoding_issue = True
            print(
                f"⚠️ 警告：字段名 '{field_name}' 包含乱码字符 '?'，"
                f"可能是 fields.json 文件编码问题。\n"
                f"   Windows 用户请确保用 UTF-8 无 BOM 编码保存文件：\n"
                f"   $fields = dws aitable field list ... --format json\n"
                f"   [IO.File]::WriteAllText(\"$env:TEMP\\fields.json\", $fields)"
            )
        if field_id:
            field_map[field_id] = field_name

        # 从 aiConfig.prompt 数组中提取 fieldRef → 附件字段 fieldId
        ai_config = field_def.get("aiConfig") or field_def.get("ai_config")
        if ai_config and isinstance(ai_config, dict) and field_name:
            prompt_items = ai_config.get("prompt", [])
            if isinstance(prompt_items, list):
                for prompt_item in prompt_items:
                    if (
                        isinstance(prompt_item, dict)
                        and prompt_item.get("type") == "fieldRef"
                        and prompt_item.get("fieldId")
                    ):
                        ai_field_refs[field_name] = prompt_item["fieldId"]
                        break

    # 将 AI 审核字段名 → 附件 fieldId 转换为 AI 审核字段名 → 附件字段名
    ai_to_attachment_map: Dict[str, str] = {}
    for ai_field_name, attachment_field_id in ai_field_refs.items():
        attachment_field_name = field_map.get(attachment_field_id)
        if attachment_field_name:
            ai_to_attachment_map[ai_field_name] = attachment_field_name

    return field_map, ai_to_attachment_map


def _extract_cell_value(raw_value):
    """从 dws 返回的 cell 值中提取可读内容。

    attachment 类型保留为 list[dict]，后续渲染时提取图片 URL。
    user 类型提取 name 字段。
    """
    if raw_value is None:
        return None
    if isinstance(raw_value, (str, int, float, bool)):
        return raw_value
    if isinstance(raw_value, list):
        # attachment 类型: [{"url": "...", "name": "..."}] — 保留原结构
        return raw_value
    if isinstance(raw_value, dict):
        # user 类型: {"name": "张三", "userId": "xxx"}
        if "name" in raw_value and "userId" in raw_value:
            return raw_value["name"]
        if "name" in raw_value:
            return raw_value["name"]
        if "markdown" in raw_value:
            return raw_value["markdown"]
        if "value" in raw_value:
            return raw_value["value"]
        return json.dumps(raw_value, ensure_ascii=False)
    return str(raw_value)


def _normalize_records(raw_records: list, field_id_map: dict) -> list:
    """将 cells + fieldId 格式的记录转换为 fields + 字段名称 格式。"""
    normalized = []
    for record in raw_records:
        if "fields" in record and "cells" not in record:
            normalized.append(record)
            continue

        cells = record.get("cells", {})
        fields = {}
        for field_id, raw_value in cells.items():
            field_name = field_id_map.get(field_id, field_id)
            fields[field_name] = _extract_cell_value(raw_value)
        normalized.append({"fields": fields})
    return normalized


def load_inspection_data(data_file: str) -> list:
    """加载督导数据文件并返回记录列表。

    兼容多种 dws 导出格式：
      - {records: [...]}
      - {data: {records: [...]}}
      - 直接数组 [...]
    """
    data = _load_json_file(data_file, "督导数据")

    if isinstance(data, dict):
        # 兼容 dws 导出的 {data: {records: [...]}} 嵌套格式
        inner = data.get("data", data) if "data" in data else data
        return inner.get("records", [])
    if isinstance(data, list):
        return data

    print("❌ 数据格式错误：期望 JSON 对象或数组")
    sys.exit(1)


# ============================================================
# 数据分析
# ============================================================

def _classify_ai_result(raw_text: str) -> str:
    """将 AI 审核原文归类为 passed / failed / pending。

    注意匹配顺序：必须先匹配"不合格/不通过"再匹配"合格/通过"，
    因为"不合格"包含"合格"子串，顺序反了会误判。
    """
    if not raw_text or not raw_text.strip():
        return "pending"
    text = raw_text.strip()
    # 先匹配否定（更具体的模式），再匹配肯定
    if "不合格" in text or "不通过" in text:
        return "failed"
    if "合格" in text or "通过" in text:
        return "passed"
    return "pending"


def _extract_photo_urls(value) -> list:
    """从 attachment 类型字段值中提取图片 URL 列表。

    兼容钉钉 AI 表格导出的多种数据结构：
    - list: [{"url": "..."}, ...] — 多个附件
    - dict: {"url": "...", "filename": "...", ...} — 单个附件对象
    - str: "https://..." — 单个 URL 字符串
    """
    if not value:
        return []
    if isinstance(value, list):
        urls = []
        for item in value:
            if isinstance(item, dict):
                url = item.get("url") or item.get("src") or ""
                if url:
                    urls.append(url)
            elif isinstance(item, str) and item.startswith("http"):
                urls.append(item)
        return urls
    if isinstance(value, dict):
        url = value.get("url") or value.get("src") or ""
        return [url] if url else []
    if isinstance(value, str) and value.startswith("http"):
        return [value]
    return []


def _resolve_store_name(fields: dict) -> str:
    """从记录字段中提取门店名称，兼容多种字段名。"""
    for candidate in ("门店名称", "store_name", "storeName"):
        name = fields.get(candidate)
        if name and isinstance(name, str):
            return name
    return "未知门店"


def _resolve_manager_name(fields: dict) -> str:
    """从记录字段中提取店长姓名，兼容 user 类型和文本类型。"""
    for candidate in ("店长", "manager", "manager_name"):
        value = fields.get(candidate)
        if not value:
            continue
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return value.get("name", "")
        if isinstance(value, list) and value:
            first = value[0]
            if isinstance(first, dict):
                return first.get("name", "")
    return ""


def _is_attachment_field(key: str, value) -> bool:
    """判断字段是否为附件类型（含照片）。

    兼容钉钉 AI 表格导出的多种结构：
    - list: [{"url": "..."}, ...] — 多个附件
    - dict: {"url": "...", "filename": "...", ...} — 单个附件对象
    """
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict) and ("url" in first or "src" in first):
            return True
    if isinstance(value, dict) and ("url" in value or "src" in value):
        return True
    return False


# 照片/图片/附件等后缀的正则（与 ai_prompt_builder.py 保持一致）
_PHOTO_SUFFIX_RE = re.compile(
    r"(照片|图片|附件|photo|image|attachment)$", re.IGNORECASE
)


def _strip_photo_suffix(field_name: str) -> str:
    """去掉字段名末尾的 照片/图片/附件 等后缀。

    与主技能 ``ai_prompt_builder.derive_ai_field_name`` 使用相同的
    后缀剥离规则，保证 AI 审核字段名和附件字段名的配对一致性。

    Examples:
        >>> _strip_photo_suffix("仓库陈列规范照片")
        '仓库陈列规范'
        >>> _strip_photo_suffix("OC 鲜食柜陈列")
        'OC 鲜食柜陈列'
    """
    return _PHOTO_SUFFIX_RE.sub("", field_name).strip()


def _match_attachment_photos(
    item_name: str,
    ai_field_key: str,
    attachment_fields: Dict[str, List[str]],
    ai_to_attachment_map: Dict[str, str],
) -> List[str]:
    """多级 fallback 配对 AI 审核项和附件字段的照片 URL。

    三级匹配策略：
    1. 精确匹配：``attachment_fields[item_name]``
    2. 后缀剥离匹配：对 ``attachment_fields`` 的每个 key 去掉"照片/图片/附件"后缀，
       看剥离后是否等于 ``item_name``
    3. fieldRef 关联：通过字段定义 JSON 中 AI 字段的 ``aiConfig.prompt[].fieldRef``
       获取的 ``ai_to_attachment_map``，精确关联 AI 审核字段名 → 附件字段名

    Args:
        item_name: AI 审核项名称（已去掉 ``AI审核_`` 前缀），如 ``仓库陈列规范``。
        ai_field_key: AI 审核字段的完整 key，如 ``AI审核_仓库陈列规范``。
        attachment_fields: 当前记录中所有附件字段名 → 照片 URL 列表 的映射。
        ai_to_attachment_map: AI 审核字段名 → 附件字段名 的映射（从字段定义 JSON 提取）。

    Returns:
        匹配到的照片 URL 列表，匹配不到返回空列表。
    """
    # Level 1: 精确匹配
    urls = attachment_fields.get(item_name)
    if urls:
        return urls

    # Level 2: 后缀剥离匹配
    for attachment_key, attachment_urls in attachment_fields.items():
        stripped = _strip_photo_suffix(attachment_key)
        if stripped == item_name and attachment_urls:
            return attachment_urls

    # Level 3: fieldRef 关联（通过字段定义 JSON 中 aiConfig 提取的映射）
    if ai_to_attachment_map:
        linked_attachment_name = ai_to_attachment_map.get(ai_field_key)
        if linked_attachment_name:
            urls = attachment_fields.get(linked_attachment_name)
            if urls:
                return urls

    return []


def analyze_inspection_records(
    records: list,
    expected_stores: Optional[List[str]] = None,
    ai_to_attachment_map: Optional[Dict[str, str]] = None,
) -> dict:
    """分析督导数据，统计各项指标并保留审核原文和照片 URL。

    Args:
        records: 标准化后的记录列表（每条含 ``fields`` 字典）。
        expected_stores: 预期门店名称列表，用于计算未提交数。
        ai_to_attachment_map: AI 审核字段名 → 附件字段名 的映射（可选），
            从字段定义 JSON 的 ``aiConfig.prompt[].fieldRef`` 提取。
    """
    store_details: Dict[str, dict] = {}
    issue_stats: Dict[str, list] = {}
    effective_map = ai_to_attachment_map or {}

    if expected_stores:
        for store_name in expected_stores:
            store_name = store_name.strip()
            if store_name:
                store_details[store_name] = {
                    "submitted": False,
                    "status": "unsubmitted",
                    "items": [],
                    "manager": "",
                }

    for record in records:
        fields = record.get("fields", {})
        store_name = _resolve_store_name(fields)
        manager_name = _resolve_manager_name(fields)

        # 收集所有附件字段（不仅限于以"照片"结尾的字段）
        attachment_fields: Dict[str, List[str]] = {}
        for key, value in fields.items():
            if _is_attachment_field(key, value):
                attachment_fields[key] = _extract_photo_urls(value)
            elif isinstance(value, str) and key.endswith("照片") and value:
                attachment_fields[key] = [value] if value.startswith("http") else []

        has_photo = any(urls for urls in attachment_fields.values())

        # 收集 AI 审核结果，并通过多级 fallback 关联对应的照片字段
        items = []
        for key, value in fields.items():
            if not key.startswith("AI审核_"):
                continue
            item_name = key.replace("AI审核_", "")
            raw_text = str(value) if value else ""
            status = _classify_ai_result(raw_text)
            photo_urls = _match_attachment_photos(
                item_name, key, attachment_fields, effective_map,
            )
            items.append({
                "name": item_name,
                "status": status,
                "detail": raw_text,
                "photos": photo_urls,
            })
            if status == "failed":
                issue_stats.setdefault(item_name, []).append(store_name)

        if not has_photo:
            store_status = "unsubmitted"
        elif not items or all(item["status"] == "pending" for item in items):
            store_status = "pending"
        elif all(item["status"] == "passed" for item in items):
            store_status = "passed"
        else:
            has_failed = any(item["status"] == "failed" for item in items)
            store_status = "failed" if has_failed else "pending"

        store_details[store_name] = {
            "submitted": has_photo,
            "status": store_status,
            "items": items,
            "manager": manager_name,
        }

    total = len(store_details)
    submitted = sum(1 for detail in store_details.values() if detail["submitted"])
    passed = sum(1 for detail in store_details.values() if detail["status"] == "passed")
    failed = sum(1 for detail in store_details.values() if detail["status"] == "failed")
    pending = sum(1 for detail in store_details.values() if detail["status"] == "pending")
    unsubmitted = sum(1 for detail in store_details.values() if detail["status"] == "unsubmitted")

    submission_rate = (submitted / total * 100) if total > 0 else 0
    pass_rate = (passed / submitted * 100) if submitted > 0 else 0

    return {
        "total_stores": total,
        "submitted_count": submitted,
        "unsubmitted_count": unsubmitted,
        "passed_count": passed,
        "failed_count": failed,
        "pending_count": pending,
        "submission_rate": submission_rate,
        "pass_rate": pass_rate,
        "store_details": store_details,
        "issue_stats": issue_stats,
    }


# ============================================================
# HTML 报告生成（参照 Ant Design 风格 + 打印适配）
# ============================================================

# 状态 → (中文标签, CSS class 后缀)
_STATUS_CSS = {
    "passed": ("合格", "pass"),
    "failed": ("不合格", "fail"),
    "pending": ("待确认", "warn"),
    "unsubmitted": ("未提交", "muted"),
}


def _render_check_item(index: int, item: dict) -> str:
    """渲染单个检查项（卡片式布局，含 AI 审核 + 照片网格）。"""
    label, css_suffix = _STATUS_CSS.get(item["status"], ("未知", "muted"))
    detail_text = escape(item["detail"]) if item.get("detail") else "暂无审核结果"

    photos_html = ""
    photo_urls = item.get("photos", [])
    if photo_urls:
        images = "".join(
            f'<img src="{escape(url)}" class="photo-item" alt="{escape(item["name"])}">'
            for url in photo_urls
        )
        photos_html = f'<div class="photo-grid">{images}</div>'

    return (
        f'<div class="check-item">'
        f'<div class="item-header">'
        f'<span class="item-name">{index}. {escape(item["name"])}</span>'
        f'<span class="status-badge status-{css_suffix}">{label}</span>'
        f'</div>'
        f'<div class="ai-review">AI 审核：{detail_text}</div>'
        f'{photos_html}'
        f'</div>'
    )


def _render_store_section(store_name: str, detail: dict) -> str:
    """渲染单个门店的完整单店报告区块。

    输出结构：section.store-report 包含：
    - .store-header：门店标题 + 状态徽章 + 店长信息
    - .summary-card：综合得分 KPI + 总体结论 + AI 审核通过项 + 自然语言摘要
    - .detail-section：详细检查结果（逐项渲染）
    """
    label, css_suffix = _STATUS_CSS.get(detail["status"], ("未知", "muted"))
    escaped_name = escape(store_name)
    manager_name = escape(detail.get("manager", "")) or ""
    manager_text = f"店长：{manager_name}" if manager_name else ""

    items = detail.get("items", [])
    total_items = len(items)
    passed_items = sum(1 for item in items if item["status"] == "passed")
    failed_items = sum(1 for item in items if item["status"] == "failed")

    # 综合得分（0-10 分制）
    if total_items > 0:
        score = round(passed_items / total_items * 10)
    else:
        score = 0
    if score >= 9:
        score_color = "var(--success-color)"
    elif score >= 6:
        score_color = "var(--warning-color)"
    else:
        score_color = "var(--error-color)"

    # 总体结论
    if detail["status"] == "passed":
        conclusion = "合格"
        conclusion_color = "var(--success-color)"
    elif detail["status"] == "failed":
        conclusion = "不合格"
        conclusion_color = "var(--error-color)"
    elif detail["status"] == "unsubmitted":
        conclusion = "未提交"
        conclusion_color = "#999"
    else:
        conclusion = "待确认"
        conclusion_color = "var(--warning-color)"

    # 检查结果摘要文本
    summary_text = f"检查结果摘要"
    if manager_text:
        summary_text += f" · {manager_text}"

    # 自然语言分析段落
    failed_names = [item["name"] for item in items if item["status"] == "failed"]
    if detail["status"] == "unsubmitted":
        analysis_html = '<p>该门店尚未提交检查照片，无法生成分析报告。</p>'
    elif not items:
        analysis_html = '<p>暂无 AI 审核结果，可能 AI 字段尚未完成计算。</p>'
    else:
        analysis_parts = [
            f'<p><strong>整体评价：</strong>本次检查总体结论为<strong>{conclusion}</strong>。'
            f'AI 自动审核显示 {total_items} 个检查项中有 {passed_items} 项符合标准'
        ]
        if failed_names:
            analysis_parts.append(
                f'，但<strong>{"、".join(escape(n) for n in failed_names)}</strong>未达标。</p>'
            )
        else:
            analysis_parts.append('。</p>')

        if failed_names:
            analysis_parts.append(
                '<p><strong>主要问题：</strong>建议立即针对上述不合格项进行整改并重新检查。</p>'
            )
        analysis_html = "\n".join(analysis_parts)

    # 详细检查结果
    if items:
        items_html = "".join(
            _render_check_item(i, item)
            for i, item in enumerate(items, 1)
        )
    elif detail["status"] == "unsubmitted":
        items_html = '<p class="empty-hint">该门店尚未提交照片。</p>'
    else:
        items_html = '<p class="empty-hint warn">暂无 AI 审核结果，可能 AI 字段尚未完成计算。</p>'

    return (
        f'<section class="store-report">'
        # store-header
        f'<div class="store-header">'
        f'<h2 class="store-title">{escaped_name}'
        f'<span class="status-badge status-{css_suffix}">{label}</span></h2>'
        f'<p class="store-meta">{escape(summary_text)}</p>'
        f'</div>'
        # summary-card（单店 KPI + 分析）
        f'<div class="summary-card">'
        f'<div class="summary-title">总结分析</div>'
        f'<div class="kpi-grid">'
        f'<div class="kpi-item"><div class="kpi-value" style="color:{score_color};">{score}</div>'
        f'<div class="kpi-label">综合得分</div></div>'
        f'<div class="kpi-item"><div class="kpi-value" style="color:{conclusion_color};">{conclusion}</div>'
        f'<div class="kpi-label">总体结论</div></div>'
        f'<div class="kpi-item"><div class="kpi-value">{passed_items}/{total_items}</div>'
        f'<div class="kpi-label">AI 审核通过项</div></div>'
        f'</div>'
        f'<div class="analysis-content">{analysis_html}</div>'
        f'</div>'
        # detail-section（详细检查结果）
        f'<div class="detail-section">'
        f'<div class="summary-title">详细检查结果</div>'
        f'{items_html}'
        f'</div>'
        f'</section>'
    )


def _render_kpi_card(value: str, label: str, color: str = "") -> str:
    """渲染单个 KPI 指标卡片。"""
    style = f' style="color:{color};"' if color else ""
    return (
        f'<div class="kpi-item">'
        f'<div class="kpi-value"{style}>{value}</div>'
        f'<div class="kpi-label">{escape(label)}</div>'
        f'</div>'
    )


def _render_overview_card(stats: dict) -> str:
    """渲染多店模式下的整体概览卡片（提交率/通过率/不合格/待确认/未提交 五格 KPI + 摘要）。"""
    kpi_html = "".join([
        _render_kpi_card(
            f"{stats['submission_rate']:.0f}%", "照片提交率",
            color="var(--primary-color)"),
        _render_kpi_card(
            f"{stats['pass_rate']:.0f}%", "审核通过率",
            color="var(--success-color)"),
        _render_kpi_card(
            str(stats["failed_count"]), "不合格门店",
            color="var(--error-color)"),
        _render_kpi_card(
            str(stats["pending_count"]), "待确认",
            color="var(--warning-color)"),
        _render_kpi_card(str(stats["unsubmitted_count"]), "未提交"),
    ])

    # 自然语言摘要
    store_details = stats["store_details"]
    failed_stores = [name for name, detail in store_details.items() if detail["status"] == "failed"]
    analysis_parts = [
        f'<p><strong>提交情况：</strong>'
        f'{stats["submitted_count"]}/{stats["total_stores"]} 家门店已提交照片，'
        f'提交率 {stats["submission_rate"]:.0f}%。</p>',
        f'<p><strong>审核结果：</strong>'
        f'{stats["passed_count"]} 家通过，'
        f'{stats["failed_count"]} 家未通过，'
        f'{stats["pending_count"]} 家待确认。</p>',
    ]
    if failed_stores:
        analysis_parts.append(
            f'<p><strong>不合格门店：</strong>'
            f'{"、".join(escape(s) for s in failed_stores)}，'
            f'建议重点关注并督促整改。</p>'
        )

    return (
        f'<div class="summary-card">'
        f'<div class="summary-title">整体概览</div>'
        f'<div class="kpi-grid">{kpi_html}</div>'
        f'<div class="analysis-content">{"".join(analysis_parts)}</div>'
        f'</div>'
    )


def build_report_html(
    stats: dict,
    force_mode: str = "auto",
    explicit_template_path: Optional[str] = None,
) -> str:
    """根据统计数据生成完整的 HTML 报告。

    Args:
        stats: analyze_inspection_records 返回的统计数据。
        force_mode: 报告模式。
            - ``"auto"``: 默认使用多店模板（即使只有 1 家门店也走多店），
              仅当显式指定 single-store 时才用单店。
            - ``"single-store"``: 强制使用单店模板（仅限用户明确要求"单店报告"）。
            - ``"multi-store"``: 强制使用多店模板（整体概览 + 共性问题分析）。

        explicit_template_path: 用户本次通过 --template 传入的 HTML 文件路径。

    Note:
        单店报告触发条件：用户明确指定了一家且仅一家门店。
        例如"为西溪1店生成报告"、"看看朝阳店的情况"。

        以下情况均为多店报告：
        - "为 A、B 门店生成报告"（多家门店 = 多店）
        - "为所有杭州门店生成报告"（筛选条件可能命中多家 = 多店）
        - "生成今天巡店任务的报告"（未指定具体门店 = 多店）
    """
    store_details = stats["store_details"]

    # 确定实际使用的模式：仅 single-store 才走单店，其余全部多店
    if force_mode == "single-store":
        use_single = True
    elif force_mode == "multi-store":
        use_single = False
    else:
        # auto 模式：默认多店（不再按门店数自动切换，需用户显式指定单店）
        use_single = False

    if use_single:
        mode_label = "单店"
        print(f"  📋 模式: {mode_label}（使用单店模板）")
        return _build_single_store_html(stats, explicit_template_path=explicit_template_path)

    # ---------- 多店模式 ----------
    mode_label = "多店"
    print(f"  📋 模式: {mode_label}（使用多店模板）")

    # 检查是否有用户自定义多店模板（优先级：显式传入 > 持久化 > 内置拼装）
    custom_multi_template = _load_template_with_priority("multi", explicit_template_path)
    if custom_multi_template and _is_user_custom_template(custom_multi_template):
        # 用户自定义多店模板：通过占位符替换方式生成
        return _build_multi_store_from_custom_template(stats, custom_multi_template)

    # 无自定义模板：走内置的内联 HTML 拼装逻辑
    now = datetime.now()
    date_str = now.strftime("%Y年%m月%d日")
    time_str = now.strftime("%H:%M")

    # 按状态分组渲染门店详情（failed → pending → passed → unsubmitted）
    status_order = ["failed", "pending", "passed", "unsubmitted"]
    store_sections = ""
    for status_key in status_order:
        stores_in_group = [
            (name, detail) for name, detail in store_details.items()
            if detail["status"] == status_key
        ]
        for name, detail in stores_in_group:
            store_sections += _render_store_section(name, detail)

    title = "📋 门店督导报告"
    overview_html = _render_overview_card(stats)
    issue_html = _build_issue_analysis_html(stats["issue_stats"])

    return _assemble_html(title, date_str, time_str, overview_html, store_sections, issue_html)


def _is_user_custom_template(template_content: str) -> bool:
    """判断模板是否可通过占位符替换方式渲染。

    包含 ``{{`` 占位符的模板（无论内置还是用户自定义）都走模板渲染路径。
    仅当模板是旧版纯参考文档（含标志性注释）时才返回 False，回退到内联拼装。
    """
    # 旧版参考模板的标志性注释——该模板不可直接渲染
    if "巡店检查报告 HTML 模板（脱敏示例）" in template_content:
        return False
    # 包含占位符的模板均视为可渲染模板
    return "{{" in template_content


def _compute_per_store_stats(stats: dict) -> List[dict]:
    """计算每个门店的检查项统计（总量/合格/不合格/待确认/合格率）。

    返回按合格率升序排列的列表，每项包含：
    name, total, passed, failed, pending, rate
    """
    result = []
    for store_name, detail in stats["store_details"].items():
        items = detail.get("items", [])
        total = len(items)
        passed = sum(1 for it in items if it["status"] == "passed")
        failed = sum(1 for it in items if it["status"] == "failed")
        pending = total - passed - failed
        rate = (passed / total * 100) if total > 0 else 0.0
        result.append({
            "name": store_name,
            "total": total,
            "passed": passed,
            "failed": failed,
            "pending": pending,
            "rate": rate,
        })
    result.sort(key=lambda x: x["rate"])
    return result


def _compute_per_item_stats(stats: dict) -> List[dict]:
    """计算每个检查项在所有门店中的统计（总量/合格/不合格/待确认/合格率）。

    返回按合格率升序排列的列表，每项包含：
    name, total, passed, failed, pending, rate
    """
    item_counters: Dict[str, Dict[str, int]] = {}
    for detail in stats["store_details"].values():
        for item in detail.get("items", []):
            name = item["name"]
            if name not in item_counters:
                item_counters[name] = {"total": 0, "passed": 0, "failed": 0, "pending": 0}
            item_counters[name]["total"] += 1
            if item["status"] == "passed":
                item_counters[name]["passed"] += 1
            elif item["status"] == "failed":
                item_counters[name]["failed"] += 1
            else:
                item_counters[name]["pending"] += 1

    result = []
    for name, counts in item_counters.items():
        rate = (counts["passed"] / counts["total"] * 100) if counts["total"] > 0 else 0.0
        result.append({"name": name, "rate": rate, **counts})
    result.sort(key=lambda x: x["rate"])
    return result


def _rate_css_class(rate: float) -> str:
    """根据合格率返回 CSS 样式类名。"""
    if rate >= 90:
        return "good"
    if rate >= 75:
        return "warn"
    return "bad"


def _build_store_table_rows(per_store: List[dict]) -> str:
    """生成门店横向对比表格的 <tr> 行。"""
    rows = []
    for store in per_store:
        css = _rate_css_class(store["rate"])
        rows.append(
            f'<tr><td>{escape(store["name"])}</td>'
            f'<td>{store["total"]}</td>'
            f'<td>{store["passed"]}</td>'
            f'<td>{store["failed"]}</td>'
            f'<td>{store["pending"]}</td>'
            f'<td class="{css}">{store["rate"]:.1f}%</td></tr>'
        )
    return "\n".join(rows)


def _build_item_table_rows(per_item: List[dict]) -> str:
    """生成检查项维度表格的 <tr> 行。"""
    rows = []
    for item in per_item:
        css = _rate_css_class(item["rate"])
        impact = "高" if item["rate"] < 80 else ("中" if item["rate"] < 95 else "低")
        impact_css = "bad" if impact == "高" else ("warn" if impact == "中" else "good")
        rows.append(
            f'<tr><td>{escape(item["name"])}</td>'
            f'<td>{item["total"]}</td>'
            f'<td>{item["passed"]}</td>'
            f'<td>{item["failed"]}</td>'
            f'<td>{item["pending"]}</td>'
            f'<td class="{css}">{item["rate"]:.1f}%</td>'
            f'<td class="{impact_css}">{impact}</td></tr>'
        )
    return "\n".join(rows)


def _build_matrix_headers(item_names: List[str]) -> str:
    """生成矩阵表格的表头 <th> 列。"""
    header_cells = ["<th>门店</th>"]
    for name in item_names:
        header_cells.append(f"<th>{escape(name)}</th>")
    header_cells.append("<th>合格率</th>")
    return "".join(header_cells)


def _build_matrix_rows(stats: dict, item_names: List[str]) -> str:
    """生成门店×检查项矩阵的 <tr> 行。"""
    rows = []
    for store_name, detail in stats["store_details"].items():
        item_status_map: Dict[str, str] = {}
        for item in detail.get("items", []):
            item_status_map[item["name"]] = item["status"]

        cells = [f"<td><strong>{escape(store_name)}</strong></td>"]
        passed_count = 0
        total_count = len(item_names)
        for item_name in item_names:
            status = item_status_map.get(item_name, "pending")
            if status == "passed":
                cells.append('<td class="good">✅</td>')
                passed_count += 1
            elif status == "failed":
                cells.append('<td class="bad">❌</td>')
            else:
                cells.append('<td><small>—</small></td>')

        rate = (passed_count / total_count * 100) if total_count > 0 else 0.0
        css = _rate_css_class(rate)
        cells.append(f'<td class="{css}">{rate:.1f}%</td>')
        rows.append(f"<tr>{''.join(cells)}</tr>")
    return "\n".join(rows)


def _build_issue_detail_rows(stats: dict) -> str:
    """生成不合格项明细表格的 <tr> 行（含照片缩略图）。"""
    rows = []
    for store_name, detail in stats["store_details"].items():
        for item in detail.get("items", []):
            if item["status"] != "failed":
                continue
            ai_summary = escape(item.get("detail", "")) or "—"
            photo_html = ""
            photos = item.get("photos", [])
            if photos:
                photo_imgs = " ".join(
                    f'<img src="{escape(url)}" style="width:60px;height:60px;'
                    f'object-fit:cover;border-radius:6px;cursor:pointer;margin:2px;" '
                    f'onclick="openLightbox(this.src)">'
                    for url in photos[:4]
                )
                photo_html = photo_imgs
            else:
                photo_html = "<small>无照片</small>"
            rows.append(
                f'<tr><td>{escape(store_name)}</td>'
                f'<td>{escape(item["name"])}</td>'
                f'<td><small>{ai_summary}</small></td>'
                f'<td>{photo_html}</td></tr>'
            )
    return "\n".join(rows) if rows else '<tr><td colspan="4">所有检查项均合格，无不合格明细。</td></tr>'


def _json_string_array(names: List[str]) -> str:
    """将字符串列表序列化为 JS 数组字面量（用于 ECharts）。"""
    return json.dumps(names, ensure_ascii=False)


def _js_number_array(numbers: List[float]) -> str:
    """将数字列表序列化为 JS 数组字面量（用于 ECharts）。"""
    return json.dumps(numbers)


def _build_overview_summary(stats: dict, per_store: List[dict], per_item: List[dict]) -> str:
    """生成经营概览的自然语言摘要 HTML。"""
    total = stats["total_stores"]
    submitted = stats["submitted_count"]
    passed = stats["passed_count"]
    failed = stats["failed_count"]
    pass_rate = stats["pass_rate"]

    parts = [
        f"本次巡检覆盖 <strong>{total}</strong> 家门店，"
        f"已提交 {submitted} 家，"
        f"审核通过 {passed} 家，不合格 {failed} 家，"
        f"检查项合格率 <strong>{pass_rate:.1f}%</strong>。",
    ]
    # 找出不合格门店
    failed_stores = [s["name"] for s in per_store if s["rate"] < 100 and s["failed"] > 0]
    if failed_stores:
        parts.append(
            f"<br>需重点关注：<strong>{'、'.join(escape(s) for s in failed_stores[:5])}</strong>"
            + (f" 等 {len(failed_stores)} 家" if len(failed_stores) > 5 else "")
            + "。"
        )
    # 找出低合格率检查项
    weak_items = [it for it in per_item if it["rate"] < 90]
    if weak_items:
        parts.append(
            f"<br>薄弱检查项：<strong>{'、'.join(escape(it['name']) for it in weak_items[:5])}</strong>"
            + f"，建议优先整改。"
        )
    return "".join(parts)


def _build_multi_store_from_custom_template(stats: dict, template: str) -> str:
    """使用多店模板通过占位符替换生成报告。

    支持两类模板占位符：
    A) 基础 KPI 类（REPORT_TITLE, CHECK_DATE, TOTAL_STORES, PASS_RATE 等）
    B) 高级分析类（表格行、ECharts 数据、矩阵、不合格明细等）

    模板中未使用的占位符会被保留原样（不影响渲染）。
    """
    now = datetime.now()
    date_str = now.strftime("%Y年%m月%d日")
    time_str = now.strftime("%Y-%m-%d %H:%M")

    store_details = stats["store_details"]
    store_names = list(store_details.keys())

    # 计算门店维度和检查项维度的统计数据
    per_store = _compute_per_store_stats(stats)
    per_item = _compute_per_item_stats(stats)
    item_names = [it["name"] for it in per_item]

    # 总检查项数（所有门店的检查项总量）
    total_checks = sum(s["total"] for s in per_store)
    # 单次开档全项合格率（全部合格的门店占已提交门店的比例）
    full_pass_stores = sum(1 for s in per_store if s["total"] > 0 and s["failed"] == 0 and s["pending"] == 0)
    submitted = stats["submitted_count"] or 1
    full_pass_rate = full_pass_stores / submitted * 100

    # 旧模板兼容：按状态分组渲染门店详情
    status_order = ["failed", "pending", "passed", "unsubmitted"]
    store_sections = ""
    for status_key in status_order:
        stores_in_group = [
            (name, detail) for name, detail in store_details.items()
            if detail["status"] == status_key
        ]
        for name, detail in stores_in_group:
            store_sections += _render_store_section(name, detail)

    overview_html = _render_overview_card(stats)
    issue_html = _build_issue_analysis_html(stats["issue_stats"])

    # 新模板：表格行、ECharts 数据
    store_table_rows = _build_store_table_rows(per_store)
    item_table_rows = _build_item_table_rows(per_item)
    matrix_headers = _build_matrix_headers(item_names)
    matrix_rows = _build_matrix_rows(stats, item_names)
    issue_detail_rows = _build_issue_detail_rows(stats)

    # ECharts 数据
    store_chart_names = _json_string_array([s["name"] for s in per_store])
    store_chart_rates = _js_number_array([round(s["rate"], 2) for s in per_store])
    item_chart_names = _json_string_array([it["name"] for it in per_item])
    item_chart_rates = _js_number_array([round(it["rate"], 2) for it in per_item])

    # 自然语言分析摘要（数据驱动，非 LLM 生成）
    overview_summary = _build_overview_summary(stats, per_store, per_item)

    # 门店对比分析
    best_stores = [s["name"] for s in per_store if s["rate"] >= 100]
    worst_stores = [s for s in per_store if s["rate"] < 90]
    store_comparison_parts = []
    if best_stores:
        store_comparison_parts.append(
            f"全项合格门店：<strong>{'、'.join(escape(s) for s in best_stores[:5])}</strong>"
            + (f" 等 {len(best_stores)} 家" if len(best_stores) > 5 else "")
            + "，表现稳定。"
        )
    if worst_stores:
        store_comparison_parts.append(
            f"合格率低于 90% 的门店：<strong>"
            + "、".join(f"{escape(s['name'])}({s['rate']:.1f}%)" for s in worst_stores[:5])
            + "</strong>，需重点督导。"
        )
    store_comparison_analysis = " ".join(store_comparison_parts) if store_comparison_parts else "各门店表现均衡。"

    # 检查项维度分析
    weak_items = [it for it in per_item if it["rate"] < 90]
    if weak_items:
        item_dimension_analysis = (
            f"合格率低于 90% 的检查项：<strong>"
            + "、".join(f"{escape(it['name'])}({it['rate']:.1f}%)" for it in weak_items[:5])
            + "</strong>，建议总部优先关注并制定专项整改方案。"
        )
    else:
        item_dimension_analysis = "所有检查项合格率均在 90% 以上，整体执行质量良好。"

    # 矩阵分析
    matrix_analysis = (
        f"矩阵展示了 {len(store_names)} 家门店在 {len(item_names)} 个检查项上的逐项结果，"
        f"✅ 表示合格，❌ 表示不合格，— 表示缺失/待确认。"
    )

    # 不合格项明细分析
    total_failed_items = sum(
        1 for detail in store_details.values()
        for item in detail.get("items", [])
        if item["status"] == "failed"
    )
    if total_failed_items > 0:
        issue_detail_analysis = f"共发现 <strong>{total_failed_items}</strong> 项不合格，以下为逐条明细（点击照片可放大查看）。"
    else:
        issue_detail_analysis = "本次巡检所有检查项均合格，无不合格明细。"

    # 占位符替换（兼容新旧两种模板格式）
    replacements = {
        # 基础 KPI
        "{{REPORT_TITLE}}": "📋 门店督导报告",
        "{{CHECK_DATE}}": date_str,
        "{{GENERATED_AT}}": time_str,
        "{{DATA_SOURCE}}": f"钉钉 AI 表格（{date_str}导出）",
        "{{TOTAL_STORES}}": str(stats["total_stores"]),
        "{{STORE_LIST}}": "、".join(escape(s) for s in store_names),
        "{{REPORT_DESCRIPTION}}": f"本报告基于 {date_str} 的巡检数据自动生成，涵盖 {len(item_names)} 个检查维度。",
        "{{TOTAL_CHECKS}}": str(total_checks),
        "{{PASS_RATE}}": f"{stats['pass_rate']:.1f}%",
        "{{FULL_PASS_RATE}}": f"{full_pass_rate:.1f}%",
        "{{FAILED_COUNT}}": str(stats["failed_count"]),
        "{{SUBMITTED_COUNT}}": str(stats["submitted_count"]),
        "{{SUBMISSION_RATE}}": f"{stats['submission_rate']:.0f}%",
        "{{PASSED_COUNT}}": str(stats["passed_count"]),
        "{{PENDING_COUNT}}": str(stats["pending_count"]),
        "{{UNSUBMITTED_COUNT}}": str(stats["unsubmitted_count"]),
        # 分析摘要
        "{{OVERVIEW_SUMMARY}}": overview_summary,
        "{{STORE_COMPARISON_ANALYSIS}}": store_comparison_analysis,
        "{{ITEM_DIMENSION_ANALYSIS}}": item_dimension_analysis,
        "{{MATRIX_ANALYSIS}}": matrix_analysis,
        "{{ISSUE_DETAIL_ANALYSIS}}": issue_detail_analysis,
        # 表格行
        "{{STORE_TABLE_ROWS}}": store_table_rows,
        "{{ITEM_TABLE_ROWS}}": item_table_rows,
        "{{MATRIX_TABLE_HEADERS}}": matrix_headers,
        "{{MATRIX_TABLE_ROWS}}": matrix_rows,
        "{{ISSUE_DETAIL_ROWS}}": issue_detail_rows,
        # ECharts 数据（JS 数组字面量，不带引号）
        "{{STORE_CHART_NAMES}}": store_chart_names,
        "{{STORE_CHART_RATES}}": store_chart_rates,
        "{{ITEM_CHART_NAMES}}": item_chart_names,
        "{{ITEM_CHART_RATES}}": item_chart_rates,
        # 旧模板兼容
        "{{STORE_SECTIONS}}": store_sections,
        "{{OVERVIEW_HTML}}": overview_html,
        "{{ISSUE_HTML}}": issue_html,
    }

    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)

    return result


def _build_issue_analysis_html(issue_stats: dict) -> str:
    """构建共性问题分析 HTML 片段。"""
    if not issue_stats:
        return (
            '<div class="summary-card">'
            '<div class="summary-title">共性问题分析</div>'
            '<p class="empty-hint">暂无共性问题，所有检查项均已通过。</p>'
            '</div>'
        )

    sorted_issues = sorted(issue_stats.items(), key=lambda x: len(x[1]), reverse=True)
    rows = []
    for issue_name, affected_stores in sorted_issues:
        store_list = "、".join(escape(s) for s in affected_stores[:8])
        suffix = f" 等 {len(affected_stores)} 家" if len(affected_stores) > 8 else ""
        rows.append(
            f'<tr>'
            f'<td class="issue-cell">{escape(issue_name)}</td>'
            f'<td class="issue-cell center">'
            f'<span class="issue-count">{len(affected_stores)}</span></td>'
            f'<td class="issue-cell sub">{store_list}{suffix}</td>'
            f'</tr>'
        )
    return (
        '<div class="summary-card">'
        '<div class="summary-title">共性问题分析</div>'
        '<table class="issue-table"><thead><tr>'
        '<th class="issue-th">检查项</th>'
        '<th class="issue-th center">不通过数</th>'
        '<th class="issue-th">涉及门店</th>'
        '</tr></thead><tbody>'
        + "".join(rows)
        + '</tbody></table></div>'
    )


def _build_single_store_html(
    stats: dict,
    explicit_template_path: Optional[str] = None,
) -> str:
    """使用单店模板生成 HTML 报告（聚焦单家门店，按记录分组，卡片式网格布局）。

    与多店模板的核心区别：
    - 渐变色 header（非纯文本标题）
    - 按记录/时段分组（每条记录一个 section）
    - 网格卡片式检查项布局（item-grid）
    - 总结分析卡片
    - 图片点击放大 lightbox
    """
    now = datetime.now()
    date_str = now.strftime("%Y年%m月%d日")
    time_str = now.strftime("%Y-%m-%d %H:%M")

    store_details = stats["store_details"]
    store_name = next(iter(store_details))
    detail = store_details[store_name]
    items = detail.get("items", [])
    manager = detail.get("manager", "")

    # 模板加载优先级：显式传入 > 持久化自定义 > 内置默认
    template = _load_template_with_priority("single", explicit_template_path)
    if template is None:
        print(f"⚠️ 单店模板不存在，回退到多店模板")
        return build_report_html(stats, force_mode="multi-store")

    # --- 构建总结分析 HTML ---
    total_items = len(items)
    passed_items = sum(1 for it in items if it["status"] == "passed")
    failed_items = sum(1 for it in items if it["status"] == "failed")
    failed_names = [it["name"] for it in items if it["status"] == "failed"]

    if detail["status"] == "unsubmitted":
        summary_html = "<p>该门店尚未提交检查照片，无法生成分析报告。</p>"
    elif not items:
        summary_html = "<p>暂无 AI 审核结果。</p>"
    else:
        parts = []
        if failed_names:
            parts.append(
                f"<p><strong>整体情况：</strong>本次检查共 {total_items} 个检查项，"
                f"其中 {passed_items} 项合格，{failed_items} 项不合格。</p>"
            )
            parts.append(
                f'<p><strong>不合格项：</strong>'
                f'{"、".join(escape(n) for n in failed_names)}，'
                f'建议立即整改。</p>'
            )
        else:
            parts.append(
                f"<p><strong>整体情况：</strong>本次检查共 {total_items} 个检查项，"
                f"全部合格，表现优秀。</p>"
            )
        summary_html = "\n".join(parts)

    # --- 构建检查项 HTML（按记录分组，单店只有一条记录时渲染一个 section） ---
    record_sections_html = ""
    record_class = "morning"
    overall_label, overall_css = _STATUS_CSS.get(detail["status"], ("未知", "muted"))

    # 渲染检查项卡片
    items_html = ""
    for idx, item in enumerate(items, 1):
        label, css_suffix = _STATUS_CSS.get(item["status"], ("未知", "muted"))
        ai_review = escape(item.get("detail", "")) if item.get("detail") else "暂无审核结果"
        photos = item.get("photos", [])
        img_src = photos[0] if photos else ""
        img_tag = (
            f'<img src="{escape(img_src)}" class="item-img" alt="{idx}. {escape(item["name"])}">'
            if img_src else '<div style="height:180px;display:flex;align-items:center;'
            'justify-content:center;background:#f5f5f5;border-radius:4px;color:#999;">'
            '暂无照片</div>'
        )
        items_html += (
            f'<div class="check-item">'
            f'<div class="item-header">{idx}. {escape(item["name"])} '
            f'<span class="status-tag status-{"pass" if css_suffix == "pass" else "fail"}">'
            f'{label}</span></div>'
            f'<div class="item-content">'
            f'{img_tag}'
            f'<div class="item-desc">{ai_review}</div>'
            f'</div></div>\n'
        )

    record_sections_html = (
        f'<div class="section">'
        f'<div class="section-title">检查详情</div>'
        f'<div class="record-card {record_class}">'
        f'<div class="record-header">'
        f'<span>检查记录</span>'
        f'<span class="status-tag status-{"pass" if overall_css == "pass" else "fail"}">'
        f'{overall_label}</span></div>'
        f'<div class="item-grid">{items_html}</div>'
        f'</div></div>'
    )

    # --- 模板占位符替换 ---
    # 移除模板中的 BEGIN/END 注释块，用实际 HTML 替换
    # 先移除 BEGIN_RECORD_SECTION 到 END_RECORD_SECTION 之间的内容
    pattern = r'<!-- BEGIN_RECORD_SECTION -->.*?<!-- END_RECORD_SECTION -->'
    html = re.sub(pattern, record_sections_html, template, flags=re.DOTALL)

    html = html.replace("{{STORE_NAME}}", escape(store_name))
    html = html.replace("{{REPORT_TYPE}}", "巡店检查报告")
    html = html.replace("{{CHECK_DATE}}", date_str)
    html = html.replace("{{INSPECTOR_NAME}}", escape(manager) if manager else "—")
    html = html.replace("{{SUMMARY_CONTENT}}", summary_html)
    html = html.replace("{{GENERATED_AT}}", time_str)
    html = html.replace("{{DATA_SOURCE}}", "钉钉 AI 表格")

    return html


def _assemble_html(
    title: str, date_str: str, time_str: str,
    overview_html: str, store_sections: str, issue_html: str,
) -> str:
    """组装完整的多店 HTML 文档。

    签名：(title, date_str, time_str, overview_html, store_sections, issue_html)
    - title: 页面标题（单店为「{门店名} - 巡店检查报告」，多店为通用标题）
    - overview_html: 多店模式下的整体概览卡片（单店为空字符串）
    - store_sections: 各门店的 section.store-report 拼接
    - issue_html: 共性问题分析（单店为空字符串）
    """
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(title)} - {date_str}</title>
<style>
  :root {{
    --primary-color: #1677ff;
    --success-color: #52c41a;
    --warning-color: #faad14;
    --error-color: #ff4d4f;
    --text-primary: #333;
    --text-secondary: #666;
    --bg-color: #f5f5f5;
    --card-bg: #ffffff;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
    background: var(--bg-color);
    color: var(--text-primary);
    line-height: 1.6;
    padding: 20px;
  }}
  .container {{ max-width: 800px; margin: 0 auto; }}

  /* 页头 */
  .header {{ text-align: center; margin-bottom: 30px; }}
  .header h1 {{ font-size: 24px; margin: 0; color: var(--text-primary); }}
  .header p {{ margin: 5px 0 0; color: var(--text-secondary); font-size: 14px; }}

  /* 通用卡片 */
  .summary-card {{
    background: var(--card-bg);
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    margin-bottom: 20px;
  }}
  .summary-title {{
    font-size: 18px; font-weight: 600;
    margin-bottom: 15px;
    border-left: 4px solid var(--primary-color);
    padding-left: 10px;
  }}

  /* KPI 网格 */
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 15px; margin-bottom: 20px;
  }}
  .kpi-item {{
    text-align: center; padding: 10px;
    background: #fafafa; border-radius: 8px;
  }}
  .kpi-value {{ font-size: 24px; font-weight: bold; color: var(--primary-color); }}
  .kpi-label {{ font-size: 12px; color: var(--text-secondary); margin-top: 5px; }}

  /* 分析内容 */
  .analysis-content {{ font-size: 14px; color: var(--text-secondary); }}
  .analysis-content strong {{ color: var(--text-primary); }}

  /* 单店报告区块（分页控制） */
  .store-report {{
    margin-bottom: 28px;
    page-break-inside: avoid;
    break-inside: avoid-page;
  }}
  .store-report + .store-report {{
    page-break-before: always;
    break-before: page;
  }}

  /* 门店标题 */
  .store-header {{ margin-bottom: 16px; }}
  .store-title {{
    display: flex; align-items: center; flex-wrap: wrap;
    gap: 10px; font-size: 20px; margin: 0;
  }}
  .store-meta {{
    font-size: 13px; color: var(--text-secondary);
    margin-top: 4px;
  }}

  /* 门店详情区块 */
  .detail-section {{
    background: var(--card-bg);
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    margin-bottom: 20px;
  }}

  /* 检查项 */
  .check-item {{ border-bottom: 1px solid #eee; padding: 15px 0; }}
  .check-item:last-child {{ border-bottom: none; }}
  .item-header {{
    display: flex; justify-content: space-between;
    align-items: center; margin-bottom: 10px;
  }}
  .item-name {{ font-weight: 600; font-size: 16px; }}

  /* 状态徽章 */
  .status-badge {{
    padding: 4px 12px; border-radius: 20px;
    font-size: 12px; font-weight: 500;
    white-space: nowrap;
  }}
  .status-pass {{
    background: #f6ffed; color: var(--success-color);
    border: 1px solid #b7eb8f;
  }}
  .status-fail {{
    background: #fff2f0; color: var(--error-color);
    border: 1px solid #ffccc7;
  }}
  .status-warn {{
    background: #fffbe6; color: var(--warning-color);
    border: 1px solid #ffe58f;
  }}
  .status-muted {{
    background: #f5f5f5; color: #999;
    border: 1px solid #d9d9d9;
  }}

  /* AI 审核文本 */
  .ai-review {{
    font-size: 13px; color: var(--text-secondary);
    background: #fafafa; padding: 10px;
    border-radius: 6px; margin-bottom: 10px;
    word-wrap: break-word; word-break: break-word;
  }}

  /* 照片网格（自适应） */
  .photo-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 10px; margin-top: 10px;
  }}
  .photo-item {{
    width: 100%; max-width: 100%; display: block;
    aspect-ratio: 1; object-fit: cover;
    border-radius: 8px; border: 1px solid #eee;
    transition: transform 0.2s;
  }}
  .photo-item:hover {{
    transform: scale(1.02);
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
  }}

  /* 问题表格 */
  .issue-table {{ width: 100%; border-collapse: collapse; }}
  .issue-th {{
    padding: 10px 12px; text-align: left;
    font-size: 13px; color: #666;
    border-bottom: 2px solid #e5e7eb; background: #f8f9fa;
  }}
  .issue-th.center {{ text-align: center; }}
  .issue-cell {{
    padding: 10px 12px; border-bottom: 1px solid #f0f0f0;
    font-weight: 500;
    word-wrap: break-word; word-break: break-word;
  }}
  .issue-cell.center {{ text-align: center; }}
  .issue-cell.sub {{ color: #555; font-size: 13px; font-weight: 400; }}
  .issue-count {{
    background: #fef2f2; color: var(--error-color);
    padding: 2px 10px; border-radius: 12px;
    font-weight: 600; font-size: 13px;
  }}

  /* 提示文本 */
  .empty-hint {{ color: #9ca3af; font-size: 13px; padding: 8px 0; }}
  .empty-hint.warn {{ color: var(--warning-color); }}

  /* 页脚 */
  .footer {{
    text-align: center; margin-top: 30px;
    font-size: 12px; color: #999;
  }}

  /* 打印 / PDF 适配 */
  @page {{ size: A4; margin: 15mm; }}
  @media print {{
    body {{ background: #fff; padding: 0; font-size: 12px; }}
    .container {{ max-width: 100%; }}
    .summary-card, .detail-section {{
      box-shadow: none; border: 1px solid #e5e7eb;
      break-inside: avoid;
    }}
    .check-item {{ break-inside: avoid; }}
    .kpi-grid {{ grid-template-columns: repeat(3, 1fr); }}
    .kpi-value {{ font-size: 18px; }}
    .kpi-label {{ font-size: 10px; }}
    .summary-title {{ font-size: 15px; }}
    .store-title {{ font-size: 17px; }}
    .photo-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .photo-item {{ max-height: 120px; aspect-ratio: auto; }}
  }}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <h1>{escape(title)}</h1>
    <p>检查日期：{date_str} | 生成时间：{time_str}</p>
  </div>

  {overview_html}

  {store_sections}

  {issue_html}

  <div class="footer">
    <p>本报告由 AI 自动生成 · 数据来源：钉钉 AI 表格</p>
  </div>

</div>
</body>
</html>"""


# ============================================================
# CLI 注册与执行
# ============================================================

def register(subparsers) -> None:
    """注册 generate-report 子命令。"""
    parser = subparsers.add_parser(
        "generate-report",
        help="从督导数据 JSON 生成 HTML 格式的督导报告",
    )
    parser.add_argument(
        "data_file",
        help="督导数据 JSON 文件路径（record-query 导出）",
    )
    parser.add_argument(
        "--fields", "-f",
        required=True,
        help="字段定义 JSON 文件路径（field-get 导出），用于 fieldId → 字段名称映射",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="输出报告文件路径（默认为 inspection_report_YYYYMMDD.html）",
    )
    parser.add_argument(
        "--stores", "-s",
        default=None,
        help="预期门店名称列表（逗号分隔），用于计算未提交门店数。"
             "例如: '西溪1店,西溪2店,萧山1店'。"
             "如果不传，则仅统计表格中已有记录的门店。",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["auto", "single-store", "multi-store"],
        default="auto",
        help="报告模式。single-store: 单店报告（仅当用户明确要求'为某一家门店"
             "生成单店报告'时使用）；multi-store: 多店报告（多家门店并列，含整体"
             "概览和共性问题分析）；auto: 默认走多店报告。"
             "注意：'为 A、B 门店生成报告'、'为所有杭州门店生成报告'等均为多店。",
    )
    parser.add_argument(
        "--template", "-t",
        default=None,
        help="用户自定义 HTML 报告模板文件路径。传入后直接使用该模板（不脱敏，"
             "通过占位符替换内容）。配合 --save-template 可持久化供后续复用。",
    )
    parser.add_argument(
        "--save-template",
        choices=["single", "multi"],
        default=None,
        help="将 --template 传入的模板持久化为用户默认模板。"
             "single: 持久化为单店模板；multi: 持久化为多店模板。"
             "持久化后，后续生成报告将优先使用该模板，除非再次传入新模板覆盖。"
             "每种类型最多保留一份。如已有持久化模板，会输出旧模板内容并提示确认。",
    )
    parser.set_defaults(handler=run)


def run(args) -> None:
    """执行 generate-report 命令。"""
    data_file = args.data_file
    fields_file = args.fields
    output_file = args.output or f"inspection_report_{datetime.now().strftime('%Y%m%d')}.html"
    template_path = getattr(args, "template", None)
    save_template_type = getattr(args, "save_template", None)

    # ── 模板持久化处理（在生成报告前完成） ──
    if template_path and save_template_type:
        _handle_template_persistence(template_path, save_template_type)

    print(f"📊 正在加载数据: {data_file}")
    raw_records = load_inspection_data(data_file)
    print(f"📋 共 {len(raw_records)} 条记录")

    print(f"🔧 正在加载字段定义: {fields_file}")
    fields_data = _load_json_file(fields_file, "字段定义")
    field_id_map, ai_to_attachment_map = _build_field_id_map(fields_data)
    print(f"📎 已映射 {len(field_id_map)} 个字段")
    if ai_to_attachment_map:
        print(f"🔗 已识别 {len(ai_to_attachment_map)} 组 AI 审核→附件字段关联")

    print("🔄 正在转换数据格式...")
    records = _normalize_records(raw_records, field_id_map)

    expected_stores = None
    stores_arg = getattr(args, "stores", None)
    if stores_arg:
        expected_stores = [
            s.strip() for s in stores_arg.replace("，", ",").split(",") if s.strip()
        ]
        print(f"📋 预期门店列表: {', '.join(expected_stores)}（共 {len(expected_stores)} 家）")

    print("🔍 正在分析数据...")
    stats = analyze_inspection_records(
        records,
        expected_stores=expected_stores,
        ai_to_attachment_map=ai_to_attachment_map,
    )

    mode = getattr(args, "mode", "auto") or "auto"
    print(f"📝 正在生成 HTML 报告 (mode={mode})...")
    report_content = build_report_html(
        stats, force_mode=mode, explicit_template_path=template_path,
    )

    output_path = Path(_expand_path(output_file))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        output_path.write_text(report_content, encoding="utf-8")
        print(f"✅ 报告已生成: {output_path.resolve()}")
    except Exception as error:
        print(f"❌ 保存报告失败: {error}")
        print(f"   路径: {output_path}")
        sys.exit(1)

    print(f"\n📊 报告摘要:")
    print(f"  - 总门店数: {stats['total_stores']}")
    print(f"  - 已提交: {stats['submitted_count']} ({stats['submission_rate']:.1f}%)")
    print(f"  - 已通过: {stats['passed_count']} ({stats['pass_rate']:.1f}%)")
    print(f"  - 未通过: {stats['failed_count']}")
    print(f"  - 待确认: {stats['pending_count']}")
    print(f"  - 未提交: {stats['unsubmitted_count']}")
    print(f"\n💡 提示: 在浏览器中打开 {output_path.resolve()} 查看完整报告")
    print("✅ 完成!")


def _handle_template_persistence(template_path: str, report_type: str) -> None:
    """处理模板持久化逻辑。

    如果目标类型已有持久化模板，输出旧模板路径和前 20 行预览，
    提示用户确认覆盖（通过 --confirmed 标志或交互确认）。
    当前 CLI 模式下直接覆盖并输出警告。
    """
    resolved = Path(_expand_path(template_path))
    if not resolved.exists():
        print(f"❌ 模板文件不存在: {resolved}")
        sys.exit(1)

    new_content = resolved.read_text(encoding="utf-8")
    type_label = _type_label(report_type)

    needs_confirm, existing_content = check_and_confirm_overwrite(report_type)
    if needs_confirm and existing_content:
        # 输出旧模板信息供用户确认
        print(f"⚠️ 已存在持久化的{type_label}报告模板，即将覆盖。")
        print(f"   旧模板预览（前 10 行）:")
        for line in existing_content.splitlines()[:10]:
            print(f"   │ {line}")
        print(f"   ...")
        print(f"   覆盖为新模板: {resolved}")

    saved_path = save_custom_template(report_type, new_content)
    print(f"✅ {type_label}报告模板已持久化: {saved_path}")
    print()
