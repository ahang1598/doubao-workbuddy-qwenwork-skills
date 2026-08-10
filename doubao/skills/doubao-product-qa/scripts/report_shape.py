#!/usr/bin/env python3
"""报告体裁选择：章节形状由任务类型 × 材料特征决定，不由常量写死。

为什么需要这一层（取证结论）：
旧实现里 renderer 对任何任务都输出同一套八段骨架（执行摘要 / 覆盖情况 / 执行结果 /
缺陷 / 验收摘要 / 风险机制 / 发布结论 / 未验证）。而四份金标准是四种不同形状：
纯方案题根本没有"执行结果"段，规则引擎题多一段"关键序列重算"，
冲突多的题把"最终需求口径"提到很靠前。一套骨架套所有 query，
等于把体裁判断推给执行者临场发挥，也等于所有人拿到的产物长得一样。

注意一个容易做反的地方：**同一类任务下结构相似是正确的**。
三份收口报告的骨架本来就该接近，因为 go/no-go 会议就需要那几件事。
差异应该来自：命中的形状、按材料取舍的专节、以及用业务词命名的标题——
不是为了不同而随机换顺序。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# 五种体裁。骨架取自四份金标准反推 + 多轮增量场景。
# 每段标注 when：材料里没有对应内容时该段不出现，不允许空章节占位。
# ---------------------------------------------------------------------------
SHAPES: dict[str, dict[str, Any]] = {
    "release-gate": {
        "when": "有执行记录，要给 go/no-go",
        "sections": [
            ("结论", "always"),
            ("需求口径与资料冲突", "has_conflicts"),
            ("业务链路与范围", "always"),
            ("风险排序", "always"),
            ("执行结果复核", "always"),
            ("已确认缺陷", "has_bugs"),
            ("待确认", "has_pending"),
            ("回归安排", "has_bugs"),
            ("准出条件", "always"),
        ],
    },
    "rule-model": {
        "when": "规则引擎/状态机/时序类，材料里有时间序列样本",
        "sections": [
            ("决策摘要", "always"),
            ("规则来源与处理模型", "always"),
            ("关键序列重算", "always"),
            ("逐条复核", "always"),
            ("风险排序", "always"),
            ("已确认缺陷", "has_bugs"),
            ("待补证", "has_pending"),
            ("尚未执行的重点", "has_not_run"),
            ("修复回归", "has_bugs"),
            ("准出条件", "always"),
        ],
    },
    "plan-only": {
        "when": "只有 PRD/原型，没有任何执行证据",
        "forbidden_sections": ["执行结果", "通过率", "发布结论", "上线建议"],
        "sections": [
            ("测试范围", "always"),
            ("风险点", "always"),
            ("需求口径与存疑项", "has_open_questions"),
            ("测试用例", "always"),
            ("开放问题", "has_open_questions"),
            ("已知未覆盖", "always"),
        ],
    },
    "bug-review": {
        "when": "用户只要 Bug 复核或归因",
        "sections": [
            ("归因结论", "always"),
            ("证据链", "always"),
            ("分层定位", "always"),
            ("影响与波及范围", "always"),
            ("回归点", "always"),
            ("待确认", "has_pending"),
        ],
    },
    "incremental": {
        "when": "多轮增删改，本轮只处理增量",
        "sections": [
            ("本轮变更", "always"),
            ("受影响集合", "always"),
            ("增删改对账", "always"),
            ("重验结论", "always"),
            ("未受影响范围", "always"),
        ],
    },
}

# 判据用四份金标准反标定过：只有药品题的金标是 rule-model（标题「关键序列重算」），
# 组合优化与企业知识库的金标是 release-gate。
# 早期判据写成"出现 HH:MM:SS 或 event_time"，结果三题全命中——因为任何 QA 材料都有日志时间戳。
# 真正区分药品题的不是"有时间"，而是**双时间轴需要重算**：事件时间 ≠ 到达时间，且存在乱序/补传。
DUAL_CLOCK = re.compile(r"event_time|事件时间|采集时间|发生时间")
REORDER = re.compile(r"乱序|补传|重排|离线缓存|按事件时间|迟到|out.of.order|backfill")
CONFLICT_HINT = re.compile(r"变更单|优先级是|以.*为准|自相矛盾|口径不一致|与 ?PRD 冲突")
OPEN_HINT = re.compile(r"待确认|存疑点|尚未确认|还在对|需与开发确认|没有写明|未定义")


def read_any(path: Path) -> str:
    """读出文本。docx/xlsx 是 zip，直接 read_text 会读成乱码，
    导致 PRD 里明写的「待确认 / 存疑点」章节被漏检（实测知贝题就是这么漏的）。"""
    suffix = path.suffix.lower()
    if suffix in {".docx", ".xlsx", ".pptx"}:
        import zipfile

        parts = {
            ".docx": ["word/document.xml"],
            ".pptx": None,
            ".xlsx": ["xl/sharedStrings.xml"],
        }[suffix]
        try:
            with zipfile.ZipFile(path) as archive:
                names = parts or [n for n in archive.namelist() if n.endswith(".xml")][:40]
                chunks = []
                for name in names:
                    try:
                        chunks.append(archive.read(name).decode("utf-8", "ignore"))
                    except KeyError:
                        continue
                return re.sub(r"<[^>]+>", " ", " ".join(chunks))
        except (OSError, zipfile.BadZipFile):
            return ""
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".zip", ".pdf", ".mp4"}:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def probe_sources(paths: list[Path]) -> dict[str, bool]:
    """从材料本身探测特征，不要求执行者自己判断体裁。"""
    features = {"has_timeseries": False, "has_conflicts": False, "has_open_questions": False}
    for path in paths:
        if not path.is_file() or path.stat().st_size > 4_000_000:
            continue
        text = read_any(path)[:200_000]
        if not text:
            continue
        if DUAL_CLOCK.search(text) and REORDER.search(text):
            features["has_timeseries"] = True
        if CONFLICT_HINT.search(text):
            features["has_conflicts"] = True
        if OPEN_HINT.search(text):
            features["has_open_questions"] = True
    return features


def select(run: dict[str, Any], features: dict[str, bool] | None = None) -> str:
    features = features or {}
    task_mode = str(run.get("request_contract", {}).get("task_mode", ""))
    executions = run.get("executions") or []
    bugs = run.get("bugs") or []
    ledger = [item for item in run.get("change_ledger", []) or [] if isinstance(item, dict)]

    if task_mode == "bug" or (bugs and not executions and not run.get("cases")):
        return "bug-review"
    if any(str(item.get("action")) in {"ADD", "REMOVE", "REPLACE", "RESTORE", "NARROW"} for item in ledger) and int(run.get("revision", 1)) > 2:
        return "incremental"
    if not executions:
        return "plan-only"
    if features.get("has_timeseries") or str(run.get("target", {}).get("type", "")) in {"rule_engine", "state_machine"}:
        return "rule-model"
    return "release-gate"


def resolve_sections(shape: str, run: dict[str, Any], features: dict[str, bool] | None = None) -> list[str]:
    """按材料取舍专节。没有对应内容的段直接不出现，禁止空章节占位。"""
    features = dict(features or {})
    spec = SHAPES.get(shape) or SHAPES["release-gate"]
    counts = (run.get("coverage") or {}).get("case_status_counts") or {}
    state = {
        "always": True,
        "has_conflicts": bool(run.get("input", {}).get("conflicts")) or features.get("has_conflicts", False),
        "has_bugs": bool(run.get("bugs")),
        "has_pending": int(counts.get("待确认", 0)) > 0 or bool(run.get("bug_candidates")),
        "has_not_run": int(counts.get("未执行", 0)) > 0,
        "has_open_questions": any(
            str(item.get("status", "open")) in {"open", "待确认"}
            for item in run.get("open_questions", []) or []
        ) or features.get("has_open_questions", False),
    }
    return [title for title, condition in spec["sections"] if state.get(condition, True)]


def business_terms(paths: list[Path], limit: int = 12) -> list[str]:
    """抽材料里的高频业务专名，供模型给章节起业务化标题。

    金标准的标题叫「关键序列重算」「最终需求口径」，不叫「数据分析」「需求梳理」。
    脚本不替模型起名，只把素材递过去。
    """
    counter: dict[str, int] = {}
    token = re.compile(r"[一-龥]{2,6}")
    stop = {
        "测试", "用例", "执行", "结果", "问题", "记录", "文档", "说明", "版本", "内容",
        "如果", "可以", "需要", "进行", "以及", "这个", "那个", "我们", "他们", "或者",
    }
    for path in paths:
        if not path.is_file() or path.stat().st_size > 4_000_000:
            continue
        text = read_any(path)[:120_000]
        if not text:
            continue
        for word in token.findall(text):
            if word in stop:
                continue
            counter[word] = counter.get(word, 0) + 1
    ranked = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return [word for word, count in ranked[:limit] if count >= 3]


def describe(run: dict[str, Any], source_paths: list[Path]) -> dict[str, Any]:
    features = probe_sources(source_paths)
    shape = select(run, features)
    spec = SHAPES[shape]
    return {
        "shape": shape,
        "why": spec["when"],
        "sections": resolve_sections(shape, run, features),
        "forbidden_sections": spec.get("forbidden_sections", []),
        "features": features,
        "business_terms": business_terms(source_paths),
    }


def render_card(info: dict[str, Any]) -> list[str]:
    lines = [
        f"报告体裁：{info['shape']}（{info['why']}）",
        f"章节（按此顺序写，没有内容的段已经被去掉，不要补空段）：{' → '.join(info['sections'])}",
    ]
    if info.get("forbidden_sections"):
        lines.append(f"本体裁禁止出现的段：{'、'.join(info['forbidden_sections'])}")
    if info.get("business_terms"):
        lines.append(f"标题请用本任务的业务词，例如：{'、'.join(info['business_terms'][:8])}")
    return lines


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="按任务与材料选择报告体裁")
    parser.add_argument("qa_run", type=Path)
    parser.add_argument("--source", action="append", default=[], type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    run = json.loads(args.qa_run.expanduser().resolve().read_text(encoding="utf-8-sig"))
    paths: list[Path] = []
    for entry in args.source:
        entry = entry.expanduser()
        paths.extend(sorted(entry.rglob("*")) if entry.is_dir() else [entry])
    info = describe(run, paths)
    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
    else:
        print("\n".join(render_card(info)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
