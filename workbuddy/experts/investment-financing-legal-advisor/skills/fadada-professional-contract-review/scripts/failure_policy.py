"""失败分级、重试预算与升级话术。

背景（真机诊断 rpt_20260806T065933Z / 070739Z / 100557Z 与 Windows 案例 6686f725）：
脚本是无状态的，闸门失败只返回 exit 1 + 「修正后重跑同一条命令」——这句话本身在邀请
无限重试，且没有任何计数上限；更糟的是「只有用户能修的错」（文件读不了、要装
LibreOffice）与「模型自己能修的错」（报告章节留空）返回同一种失败，于是模型对前者
也反复重试。三次真机里分别烧掉 751 秒、190 秒（22 次 Bash 全是 3 条命令的重复）和
20 分钟（89 次 Bash），最终都没有交付物。

本模块把「请模型自律」变成「脚本不配合」：

  user_action_required  预算 0 —— 立即升级，脚本拒绝再做无用功
  model_fixable         预算 2 —— 给模型两次自修机会
  transient             预算 1 —— 环境/接口抖动，重试一次

尝试次数按「合同指纹 + 阶段」计入临时目录的台账，跨进程累计；成功即清零。
超预算后调用方再怎么重跑，脚本都只返回 escalate 负载，不再执行实际工作。
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

# 本模块是纯库模块，只被同目录的入口脚本 import——入口脚本运行时 scripts/ 已在
# sys.path[0]，故此处不改 sys.path，保持 import 无副作用
# （skill-evaluator D6-S4：脚本模块可被 import 复用）。

from skill_paths import work_root

CLASS_USER = "user_action_required"
CLASS_MODEL = "model_fixable"
CLASS_TRANSIENT = "transient"

BUDGETS = {CLASS_USER: 0, CLASS_MODEL: 2, CLASS_TRANSIENT: 1}

# 台账过期时间：超过此时长的历史尝试不再计入，避免昨天的失败卡住今天的新会话
LEDGER_TTL_SECONDS = 6 * 3600


def scope_key(contract: Path | None) -> str:
    """以合同内容指纹作为重试作用域：换了合同就是新的预算。"""
    if contract is None or not Path(contract).exists():
        return "no_contract"
    digest = hashlib.sha256()
    with Path(contract).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()[:16]


def _ledger_path(key: str) -> Path:
    return work_root() / "fadada_attempts" / f"{key}.json"


def _load(key: str) -> dict:
    path = _ledger_path(key)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    now = time.time()
    return {stage: entry for stage, entry in data.items()
            if isinstance(entry, dict) and now - entry.get("at", 0) <= LEDGER_TTL_SECONDS}


def _save(key: str, data: dict) -> None:
    path = _ledger_path(key)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass  # 台账只是尽力而为，写不了不应阻断主流程


def record_attempt(key: str, stage: str) -> int:
    """登记一次失败尝试，返回该阶段累计失败次数（1 表示这是第一次）。"""
    data = _load(key)
    entry = data.get(stage, {"count": 0})
    entry = {"count": int(entry.get("count", 0)) + 1, "at": time.time()}
    data[stage] = entry
    _save(key, data)
    return entry["count"]


def attempts_so_far(key: str, stage: str) -> int:
    return int(_load(key).get(stage, {}).get("count", 0))


def clear(key: str) -> None:
    """成功后清空该合同的全部预算。"""
    try:
        _ledger_path(key).unlink()
    except OSError:
        pass


def exceeded(failure_class: str, attempts: int) -> bool:
    return attempts > BUDGETS.get(failure_class, 1)


def escalation(stage: str, failure_class: str, errors: list[str],
               user_message: str, attempts: int,
               partial: dict | None = None) -> dict:
    """构造升级负载。

    `userMessage` 是**可直接呈现给用户的成品话术**——真机中模型常把结构化错误
    重新组织成一段又绕回重试的说明，这里直接给到位：缺什么、为什么、用户做什么。
    """
    payload = {
        "status": "escalate",
        "stage": stage,
        "failureClass": failure_class,
        "errors": errors,
        "attempts": attempts,
        "budget": BUDGETS.get(failure_class, 1),
        "retryAllowed": False,
        "nextAction": "ask_user",
        "userMessage": user_message,
        "hint": (
            "重试预算已用尽，本脚本不会再执行实际工作。**不要重跑本命令、"
            "也不要改用其他子脚本绕行**——请把 userMessage 原样呈现给用户，"
            "等待用户处理后再继续。"
        ),
    }
    if partial:
        payload["partial"] = partial
    return payload


def user_message_for(stage: str, errors: list[str]) -> str:
    """按阶段给出面向用户的中文话术模板。"""
    detail = errors[0] if errors else "未知原因"
    templates = {
        "input_format": (
            "这份合同我无法直接解析（{detail}）。\n"
            "请二选一后我立刻继续：\n"
            "1. 用 Word/WPS 打开原件，另存为 .docx 格式后重新发我；\n"
            "2. 或在本机安装 LibreOffice，我可以自动完成格式转换。"
        ),
        "extract": (
            "合同段落抽取失败（{detail}）。\n"
            "这通常意味着文件已加密、受保护或已损坏。\n"
            "请确认文件能在 Word 中正常打开并另存为 .docx 后重新发我。"
        ),
        "apply_redline": (
            "带批注修订版生成失败（{detail}）。\n"
            "我已尝试自行修正但仍未通过，需要你决定：\n"
            "1. 我只交付审查报告，修订建议以清单形式给出；\n"
            "2. 或你确认合同原文可编辑（非扫描件/无保护）后我再试一次。"
        ),
        "build_report": (
            "审查报告生成失败（{detail}）。\n"
            "我已尝试自行修正但仍未通过，建议转人工核查报告数据后再生成。"
        ),
        "delivery_gate": (
            "交付前机检未通过（{detail}）。\n"
            "我已按预算自行修正过，仍不合格，不能把不合规的文件交付给你。\n"
            "建议转人工复核，或告诉我可以接受降级交付（报告先出、修订版后补）。"
        ),
        "review_subject": (
            "交付所用的合同与准备阶段的审查对象不是同一份文件。\n"
            "为避免用节选冒充全文，我已停止交付。请确认要审查的合同文件后重新发起。"
        ),
        "deliver": (
            "交付目录不可写（{detail}）。\n"
            "请指定一个可写目录，或设置环境变量 RICHEE_OUTPUT_DIR 指向你的工作区。"
        ),
    }
    return templates.get(
        stage, "执行到「{stage}」时失败（{detail}），需要你确认后才能继续。"
    ).format(detail=detail, stage=stage)


def classify(stage: str, errors: list[str]) -> str:
    """按阶段与错误内容分级。用户才能修的错一律预算 0，不浪费任何一次重试。"""
    blob = " ".join(errors).lower()
    if stage in {"input_format", "extract", "input", "deliver"}:
        return CLASS_USER
    if "review subject" in blob or "审查对象" in blob:
        return CLASS_USER
    if "not a zip" in blob or "badzipfile" in blob or "ooxml" in blob:
        return CLASS_USER
    if "permission" in blob or "read-only" in blob or "不可写" in blob:
        return CLASS_USER
    if stage in {"apply_redline", "build_report", "delivery_gate"}:
        return CLASS_MODEL
    return CLASS_TRANSIENT
