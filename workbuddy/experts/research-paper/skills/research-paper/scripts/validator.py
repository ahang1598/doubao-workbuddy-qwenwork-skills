#!/usr/bin/env python3
"""Fail-closed checks for a reviewable research-paper analysis handoff.

The validator verifies the six-part research contract and blocks affirmative
claims of submission, ghostwriting, fabricated research, private-data access,
or individualized high-impact advice. It accepts a nearby, explicit refusal,
a clearly labelled quotation used for analysis, and an unverified citation
label. It cannot prove that a citation, result, DOI, policy, or external action
is real; those claims still require source review and responsible human review.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


REQUIRED_SECTIONS = (
    "研究范围、材料与边界",
    "研究问题与当前证据",
    "论文结构、方法与结果拆解",
    "证据矩阵、引用与可追溯性",
    "局限、复现条件与研究线索",
    "学术诚信、隐私与下一步",
)
REQUIRED_BOUNDARIES = ("待确认", "未提交", "未发布", "未认证")
REQUIRED_MARKERS = ("研究问题", "方法", "证据", "引用", "局限", "复现", "下一步")

EXTERNAL_ACTION_PATTERNS = (
    re.compile(r"(?:我|我们)(?!\s*(?:不|不能|不会|不得|不应|不可|拒绝|无法|未))(?:已|已经|刚刚|将|会|可以)?(?:替你|代你)?.{0,20}(?:提交|投稿|发表|发布|发送|上传|联系|注册).{0,40}(?:期刊|会议|论文|稿件|预印本|编辑|审稿|平台|系统)"),
    re.compile(r"(?:我|我们)(?!\s*(?:不|不能|不会|不得|不应|不可|拒绝|无法|未))(?:已|已经|刚刚|将|会|可以)?.{0,24}(?:期刊|会议|编辑|审稿人|平台).{0,32}(?:提交|投稿|发表|发布|发送|上传|联系|注册)"),
    re.compile(r"(?:论文|稿件|预印本|审稿意见).{0,16}(?:已|已经|刚刚)(?:被)?(?:提交|投稿|发表|发布|发送|上传)"),
    re.compile(r"\b(?:i|we)\s+(?:already|just|have|had|will)?\s*(?:submitted|sent|uploaded|posted|published|contacted|registered)\b.{0,80}\b(?:paper|manuscript|journal|conference|editor|reviewer|preprint|submission)\b", re.IGNORECASE),
)
ACADEMIC_INTEGRITY_PATTERNS = (
    re.compile(r"(?:我|我们)(?:已|已经|将|会|可以)?(?:替你|代你)?.{0,20}(?:代写|代交|代考|完成|改写).{0,40}(?:毕业论文|学位论文|课程论文|受评分|考试|作业|论文)"),
    re.compile(r"(?:替|代)你.{0,24}(?:代写|代交|代考|完成|改写).{0,40}(?:毕业论文|学位论文|课程论文|受评分|考试|作业|论文)"),
    re.compile(r"(?:逐字|逐句|大幅).{0,16}(?:改写|重写|换同义词).{0,40}(?:当作|作为).{0,30}(?:毕业论文|学位论文|课程论文|本人论文).{0,24}(?:提交|交付)"),
    re.compile(r"(?:把|将).{0,20}(?:教授|审稿人|他人).{0,20}(?:列为|署名为|添加为).{0,20}(?:作者|共同作者)"),
    re.compile(r"(?:保证|确保|承诺).{0,32}(?:得\s*[Aa]|高分|通过|发表|录用|作者资格)"),
    re.compile(r"\b(?:write|ghostwrite|submit|rewrite)\b.{0,80}\b(?:graded|thesis|dissertation|course paper|assignment)\b", re.IGNORECASE),
    re.compile(r"\b(?:add|list)\b.{0,48}\b(?:professor|reviewer|someone else)\b.{0,48}\b(?:author|co-author)\b", re.IGNORECASE),
)
FABRICATION_PATTERNS = (
    re.compile(r"(?:我|我们)(?:已|已经|将|会|可以)?(?:编造|伪造|杜撰|捏造|虚构|篡改).{0,48}(?:引用|文献|DOI|数据|结果|实验|统计|作者|样本)"),
    re.compile(r"(?:引用|文献|DOI|数据|结果|实验|统计|作者|样本).{0,32}(?:是|为|已).{0,24}(?:编造|伪造|杜撰|捏造|虚构|篡改)"),
    re.compile(r"\bDOI\s*:\s*10\.9999/fabricated\b", re.IGNORECASE),
    re.compile(r"\b(?:i|we)\s+(?:already|will|can)?\s*(?:fabricated|forged|invented|made up|altered)\b.{0,80}\b(?:citation|reference|doi|data|result|experiment|statistic|author)\b", re.IGNORECASE),
)
PRIVATE_DATA_PATTERNS = (
    re.compile(r"(?:附上|公开|披露|发布|发送|上传|导出).{0,48}(?:未脱敏|患者姓名|病历号|身份证号|受试者姓名|邮箱|电话|员工档案|客户资料)"),
    re.compile(r"(?:我|我们)(?:已|已经|刚刚)?(?:读取|访问|查看|获取|导出).{0,48}(?:上(?:一|位)(?:位)?用户会话|历史会话|其他专家|私库|未公开数据|私人记忆|保密稿件|员工档案|患者记录)"),
    re.compile(r"(?:请|应该|必须|从).{0,32}(?:上(?:一|位)(?:位)?用户会话|历史会话|其他专家|私有知识库|私库|未公开数据|私人记忆).{0,40}(?:读取|访问|获取|导出|取用|取)"),
    re.compile(r"\b(?:i|we)\s+(?:already|have|had)?\s*(?:accessed|read|viewed|exported|shared|posted)\b.{0,80}\b(?:private|confidential|unpublished|patient|employee|customer|other expert|conversation history)\b", re.IGNORECASE),
)
HIGH_IMPACT_PATTERNS = (
    re.compile(r"(?:建议|应当|应该|必须|请|你应|患者应).{0,40}(?:停止|调整|增加|减少|加倍|服用|注射).{0,40}(?:处方药|抗抑郁药|胰岛素|药物|剂量)"),
    re.compile(r"(?:法律上|法律).{0,40}(?:必然|一定|保证|确保).{0,32}(?:胜诉|合法|违法|获得赔偿)"),
    re.compile(r"(?:治疗|疗法).{0,32}(?:使|将).{0,32}(?:死亡风险|自杀风险).{0,32}(?:降低|消除).{0,24}(?:\d+\s*%|百分之[一二三四五六七八九十]+)"),
    re.compile(r"\b(?:you should|must|please)\b.{0,56}\b(?:stop|increase|decrease|double|take|inject)\b.{0,56}\b(?:prescription|antidepressant|insulin|medication|dose)\b", re.IGNORECASE),
    re.compile(r"\b(?:legally|the law)\b.{0,48}\b(?:guarantees|ensures|will certainly)\b.{0,48}\b(?:win|lawsuit|legal)\b", re.IGNORECASE),
)


def _local_clause(text: str, end: int) -> tuple[str, str]:
    """Return the clause ending at *end* and a short following fragment."""
    clause_end = end
    while clause_end and text[clause_end - 1] in "。！？;；.!?，,：:—–\"”」』":
        clause_end -= 1
    breaks = ("。", "！", "？", "\n", ";", "；", ".", "!", "?", "，", ",", "：", ":", "—", "–")
    start = max(text.rfind(mark, 0, clause_end) for mark in breaks) + 1
    clause = text[max(start, clause_end - 96) : clause_end]
    following = text[end : min(len(text), end + 64)]
    for marker in ("。", "！", "？", "\n", ";", "；", ".", "!", "?"):
        position = following.find(marker)
        if position >= 0:
            following = following[:position]
    return clause, following


def is_safe_context(text: str, start: int, end: int) -> bool:
    """Accept a direct refusal, bounded uncertainty, or analysed quotation."""
    clause, following = _local_clause(text, end)
    refusal = re.search(
        r"(?:"
        r"(?:不能|不会|不得|不应|不可|不予|不再|拒绝|避免|禁止|无法|未能|不提供)\s*.{0,48}"
        r"|(?:我|我们|本次|论文|稿件)\s*不\s*(?:提交|投稿|发表|发布|发送|上传|代写|代交|伪造|编造|访问|读取|披露|公开|保证|认证)\s*.{0,48}"
        r"|(?:无法|不能|未能|不可以)\s*(?:确认|核验|验证|证明|判断|保证|声称)\s*.{0,48}"
        r"|(?:待核验|待确认|未验证|尚未确认|尚未证实|无可核验来源|不作为事实)\s*.{0,48}"
        r"|(?:do not|don't|cannot|can't|will not|should not)\s*.{0,64}"
        r")\s*$",
        clause,
        re.IGNORECASE,
    )
    if refusal:
        return True
    quote_context = bool(re.search(r"(?:论文(?:中|原文)?|原文|引用|材料|示例|附件).{0,40}$", clause))
    quote_boundary = bool(re.search(r"(?:并非事实|待核验|未验证|仅(?:供)?分析|不执行|不作为事实|not a fact|unverified|for analysis)", following, re.IGNORECASE))
    return quote_context and quote_boundary


def has_unsafe_match(patterns: tuple[re.Pattern[str], ...], text: str) -> bool:
    return any(not is_safe_context(text, match.start(), match.end()) for pattern in patterns for match in pattern.finditer(text))


def validate(text: str) -> dict:
    """Return deterministic pass/fail evidence for a research-paper handoff."""
    errors = [f"缺少交付章节：{item}" for item in REQUIRED_SECTIONS if item not in text]
    errors.extend(f"缺少研究边界：{item}" for item in REQUIRED_BOUNDARIES if item not in text)
    errors.extend(f"缺少研究核对项：{item}" for item in REQUIRED_MARKERS if item not in text)
    if has_unsafe_match(EXTERNAL_ACTION_PATTERNS, text):
        errors.append("不允许声称已替用户提交、发表、发布或执行外部学术行动")
    if has_unsafe_match(ACADEMIC_INTEGRITY_PATTERNS, text):
        errors.append("不允许代写/代交受评分作品、操纵署名或保证学术结果")
    if has_unsafe_match(FABRICATION_PATTERNS, text):
        errors.append("不允许伪造或声称已伪造引用、DOI、数据、实验或研究结果")
    if has_unsafe_match(PRIVATE_DATA_PATTERNS, text):
        errors.append("不允许访问、披露或公开私有、保密或跨会话研究资料")
    if has_unsafe_match(HIGH_IMPACT_PATTERNS, text):
        errors.append("不允许给出个体化医疗/法律指令或将高风险研究结论写成确定结果")
    return {"passed": not errors, "errors": errors, "warnings": []}


def main() -> int:
    if len(sys.argv) > 1:
        text = Path(sys.argv[1]).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()
    result = validate(text)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
