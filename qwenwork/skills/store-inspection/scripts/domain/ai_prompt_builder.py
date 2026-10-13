"""AI 审核字段的 Prompt 构建器（纯函数，无 IO）。

为每个需要 AI 审核的检查项（attachment 类型字段）生成完整的
``ai-config`` JSON，供 :meth:`DwsClient.aitable_field_create_single`
创建 AI 审核字段时使用。

Prompt 格式严格遵循钉钉 AI 表格要求（数组格式）：

    {
      "outputType": "text",
      "prompt": [
        {"type": "text",     "value": "...审核指令..."},
        {"type": "fieldRef", "fieldId": "fldXXX"},
        {"type": "text",     "value": "...标准与输出要求..."}
      ]
    }

三级 Prompt 机制：
1. 通用模板（默认）：角色设定 + "三不原则" + 输出格式
2. 自定义标准：用户通过 ``ai_standards`` 注入具体审核标准
3. 完全自定义：用户通过 ``ai_prompt`` 完全覆盖 Prompt 文本
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# AI 审核字段命名规则
# ---------------------------------------------------------------------------

_AI_FIELD_PREFIX = "AI审核_"
_PHOTO_SUFFIX_PATTERN = re.compile(r"(照片|图片|附件|photo|image|attachment)$", re.IGNORECASE)


def derive_ai_field_name(attachment_field_name: str) -> str:
    """从附件字段名推导 AI 审核字段名。

    规则：``AI审核_{去掉照片/图片等后缀的字段名}``

    Examples:
        >>> derive_ai_field_name("鲜食柜照片")
        'AI审核_鲜食柜'
        >>> derive_ai_field_name("饮料柜")
        'AI审核_饮料柜'
        >>> derive_ai_field_name("收银台图片")
        'AI审核_收银台'
    """
    base_name = _PHOTO_SUFFIX_PATTERN.sub("", attachment_field_name).strip()
    if not base_name:
        base_name = attachment_field_name
    return f"{_AI_FIELD_PREFIX}{base_name}"


# ---------------------------------------------------------------------------
# Prompt 模板
# ---------------------------------------------------------------------------

_ROLE_INTRO = (
    "你是一名专业的门店督导审核员。"
    "请仅针对【{item_name}】这一个检查位置的照片进行审核。"
    "\n\n请查看以下照片："
)

_STANDARDS_HEADER = "\n\n【本检查项的合格标准】\n"

_DEFAULT_STANDARDS = [
    "照片清晰，能看清检查位置的全貌",
    "检查位置整体整洁、有序",
    "无明显违规或不达标情况",
]

_REVIEW_PRINCIPLES = (
    "\n\n【审核原则（严格遵守）】\n"
    "1. 只审核本检查项，不对照片中其他区域或其他商品做任何评价\n"
    '2. 只有在照片清晰、能够明确看到违规情况时，才判定为"不通过"\n'
    "3. 凡是照片模糊、拍摄角度受限、关键区域被遮挡、无法明确判断是否达标的，"
    '"一律选择"待人工确认"，不得猜测或强行下结论\n'
    '4. 如果"特殊情况备注"中说明了合理原因（如临时缺货、设备维修等），直接视为通过'
)

_OUTPUT_REQUIREMENT = (
    "\n\n【输出要求】\n"
    "只回答以下三个选项之一：\n"
    "- 通过：照片清晰，该检查项符合上述所有标准\n"
    "- 不通过：照片清晰，且能明确看到违反上述标准的情况\n"
    "- 待人工确认：照片模糊/角度不佳/关键区域不可见，无法做出明确判断\n"
    "\n"
    '如果是\u201c通过\u201d，简述符合标准的依据（一句话）。\n'
    '如果是\u201c不通过\u201d，列出照片中能清晰确认的违规项，每条不超过30字。\n'
    '如果是\u201c待人工确认\u201d，说明具体无法判断的原因。'
)


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AiFieldSpec:
    """AI 审核字段的完整配置规格。

    Attributes:
        field_name: AI 审核字段名，如 ``AI审核_鲜食柜``。
        target_field_name: 引用的附件字段名（源字段），如 ``鲜食柜照片``。
        target_field_id: 引用的附件字段 ``fieldId``。
        ai_config: 完整的 ``ai-config`` JSON（含 ``outputType`` + ``prompt`` 数组）。
    """

    field_name: str
    target_field_name: str
    target_field_id: str
    ai_config: Dict[str, Any]


# ---------------------------------------------------------------------------
# Prompt 构建
# ---------------------------------------------------------------------------

def _format_standards(standards: List[str]) -> str:
    """将审核标准列表格式化为 Markdown 列表文本。"""
    return "\n".join(f"- {s}" for s in standards)


def _build_prompt_text(
    item_name: str,
    standards: Optional[List[str]] = None,
    custom_prompt: Optional[str] = None,
) -> tuple:
    """构建 prompt 数组中的文本片段。

    Returns:
        ``(intro_text, closing_text)`` 二元组：
        - ``intro_text``：放在 ``fieldRef`` 之前的引导文本
        - ``closing_text``：放在 ``fieldRef`` 之后的标准与输出要求
    """
    if custom_prompt:
        parts = custom_prompt.split("{fieldRef}", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return custom_prompt + "\n\n请查看以下照片：", _REVIEW_PRINCIPLES + _OUTPUT_REQUIREMENT

    intro_text = _ROLE_INTRO.format(item_name=item_name)

    effective_standards = standards if standards else _DEFAULT_STANDARDS
    standards_text = _STANDARDS_HEADER + _format_standards(effective_standards)
    closing_text = standards_text + _REVIEW_PRINCIPLES + _OUTPUT_REQUIREMENT

    return intro_text, closing_text


def build_ai_config(
    item_name: str,
    target_field_id: str,
    standards: Optional[List[str]] = None,
    custom_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """构建完整的 ``ai-config`` JSON。

    Args:
        item_name: 检查项名称（如 ``鲜食柜陈列``）。
        target_field_id: 附件字段的 ``fieldId``。
        standards: 审核标准列表（可选）。
        custom_prompt: 完全自定义的 Prompt 文本（可选，覆盖 standards）。

    Returns:
        符合钉钉 AI 表格要求的 ``ai-config`` 字典。
    """
    intro_text, closing_text = _build_prompt_text(item_name, standards, custom_prompt)

    return {
        "outputType": "text",
        "prompt": [
            {"type": "text", "value": intro_text},
            {"type": "fieldRef", "fieldId": target_field_id},
            {"type": "text", "value": closing_text},
        ],
    }


def build_ai_field_spec(
    attachment_field_name: str,
    target_field_id: str,
    standards: Optional[List[str]] = None,
    custom_prompt: Optional[str] = None,
) -> AiFieldSpec:
    """为单个检查项构建 AI 审核字段的完整配置规格。

    这是本模块的主入口函数。

    Args:
        attachment_field_name: 附件字段名（如 ``鲜食柜照片``）。
        target_field_id: 附件字段的 ``fieldId``。
        standards: 审核标准列表（可选）。
        custom_prompt: 完全自定义 Prompt（可选，覆盖 standards）。

    Returns:
        :class:`AiFieldSpec` 包含字段名和完整 ``ai-config``。

    Examples:
        >>> spec = build_ai_field_spec("鲜食柜照片", "fldABC123",
        ...     standards=["核心单品≥5个", "无欠品"])
        >>> spec.field_name
        'AI审核_鲜食柜'
        >>> spec.ai_config["outputType"]
        'text'
        >>> len(spec.ai_config["prompt"])
        3
    """
    item_name = _PHOTO_SUFFIX_PATTERN.sub("", attachment_field_name).strip()
    if not item_name:
        item_name = attachment_field_name

    ai_config = build_ai_config(item_name, target_field_id, standards, custom_prompt)

    return AiFieldSpec(
        field_name=derive_ai_field_name(attachment_field_name),
        target_field_name=attachment_field_name,
        target_field_id=target_field_id,
        ai_config=ai_config,
    )


# ---------------------------------------------------------------------------
# 批量构建（供 TableManager 使用）
# ---------------------------------------------------------------------------

def build_ai_field_specs_from_custom_fields(
    custom_fields: List[Dict[str, Any]],
    field_id_map: Dict[str, str],
) -> List[AiFieldSpec]:
    """从模板的 ``custom_fields`` 批量构建 AI 审核字段配置。

    Args:
        custom_fields: 模板的自定义字段定义列表，每项含 ``name``、``type``、
            可选 ``ai_review``、``ai_standards``、``ai_prompt``。
        field_id_map: 字段名 → ``fieldId`` 的映射（由 ``field-get`` 获得）。

    Returns:
        需要创建的 :class:`AiFieldSpec` 列表。仅包含
        ``type == "attachment"`` 且 ``ai_review == True`` 的字段。
    """
    specs: List[AiFieldSpec] = []

    for field_def in custom_fields:
        field_type = field_def.get("type", "")
        if field_type != "attachment":
            continue
        if not field_def.get("ai_review", False):
            continue

        field_name = field_def.get("name", "")
        if not field_name:
            continue

        target_field_id = field_id_map.get(field_name)
        if not target_field_id:
            continue

        standards = field_def.get("ai_standards")
        custom_prompt = field_def.get("ai_prompt")

        spec = build_ai_field_spec(
            attachment_field_name=field_name,
            target_field_id=target_field_id,
            standards=standards,
            custom_prompt=custom_prompt,
        )
        specs.append(spec)

    return specs
