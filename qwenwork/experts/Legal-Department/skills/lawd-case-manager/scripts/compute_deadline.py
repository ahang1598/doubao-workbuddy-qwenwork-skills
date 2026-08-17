#!/usr/bin/env python3
"""诉讼期限计算器 —— 案件管家「期限」子模式的算术执行体。

设计前提（三条铁律）：

  铁律 1  日期运算交脚本，不让模型心算。模型只负责从法院文书里提取「送达日 / 文书类型」，
          起算日不计入、跨月跨年、月年对应日、末日顺延一律由本脚本计算并打印完整推算过程。
  铁律 2  节假日表过期保护。顺延依赖 assets/holidays-{年}.json；目标年份表缺失或未覆盖该
          日期时，拒绝输出顺延后的日期，只给「原始末日 + 该日可能为节假日，顺延需人工核对」。
  铁律 3  期间规则和法条依据须透明。本脚本不硬编码任何期间，全部从规则表读取。
          「待验真」规则可用于个人辅助草算，但输出必须显著标明未验真；已明确存在时效或语义
          风险的规则不得继续使用。

工程约束：
  * 只用 Python 标准库（无 python-docx 等第三方依赖）。
  * 运行时 CWD 是 workspace 根目录，不是技能目录。故技能内资源（规则表、节假日表）一律用
    __file__ 解析绝对路径；命令行传入的路径按相对 CWD 处理。

用法：
    python3 scripts/compute_deadline.py --start-date 2026-08-10 --type 上诉期 --scene 判决
    python3 scripts/compute_deadline.py --start-date 2026-08-10 --type 举证期限 --court-days 30
    python3 scripts/compute_deadline.py --list-types

退出码：
    0  给出届满日结论
    2  入参错误 / 规则表或节假日表无法解析
    4  节假日表缺失或未覆盖（铁律 2 门禁）→ 只输出原始末日，不输出顺延后日期
"""

from __future__ import annotations

import argparse
import calendar
import datetime
import json
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_RULES_FILE = SKILL_DIR / "references" / "deadline-rules.md"
DEFAULT_HOLIDAYS_DIR = SKILL_DIR / "assets"

RULES_TABLE_HEADER = ("编号", "期间类型", "适用情形", "期间值", "单位", "起算点", "法条依据", "验真状态")
VERIFY_PASSED = ("准确", "准确（有省略）", "准确(有省略)")
VERIFY_BLOCKED = ("时效风险", "语义不一致", "未命中")
COURT_DESIGNATED = "法院指定"
DISCLAIMER = "本计算供参考，最终以法院文书载明并由承办律师核实为准。"
WEEKDAY_CN = "一二三四五六日"


class InputError(Exception):
    """入参或资源文件问题，退出码 2。"""


# ---------------------------------------------------------------- 规则表解析


def _split_row(line: str) -> list:
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return cells


def parse_rules_file(path: Path) -> dict:
    """解析规则表：返回 {'rules': [...]} 。"""
    if not path.exists():
        raise InputError("找不到期限规则表：%s" % path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError("期限规则表无法读取：%s（%s）" % (path, exc))

    rules = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = _split_row(stripped)
        if len(cells) != len(RULES_TABLE_HEADER):
            continue
        if tuple(cells) == RULES_TABLE_HEADER:
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        if not re.match(r"^D\d{2}$", cells[0]):
            continue
        rules.append(
            {
                "编号": cells[0],
                "期间类型": cells[1],
                "适用情形": cells[2],
                "期间值": cells[3],
                "单位": cells[4],
                "起算点": cells[5],
                "法条依据": cells[6],
                "验真状态": cells[7],
            }
        )

    if not rules:
        raise InputError(
            "期限规则表里没解析出任何规则行（要求列顺序为 %s，编号形如 D01）" % " / ".join(RULES_TABLE_HEADER)
        )

    return {"rules": rules}


def match_rule(rules: list, deadline_type: str, scene: str, rule_id: str):
    """按编号或（期间类型 + 适用情形关键词）定位规则行。"""
    if rule_id:
        hits = [r for r in rules if r["编号"].lower() == rule_id.lower()]
        if not hits:
            raise InputError("规则表里没有编号 %s，用 --list-types 查看可用规则" % rule_id)
        return hits[0]

    hits = [r for r in rules if deadline_type and deadline_type in r["期间类型"]]
    if not hits:
        as_rule_id = [r for r in rules if r["编号"].lower() == (deadline_type or "").lower()]
        if as_rule_id:
            raise InputError(
                "「%s」是规则编号，不是期间类型。请改用 --rule-id %s（对应期间类型：%s）"
                % (deadline_type, as_rule_id[0]["编号"], as_rule_id[0]["期间类型"])
            )
        raise InputError(
            "规则表里没有期间类型「%s」，用 --list-types 查看可用类型（表中「期间类型」列用 --type，「编号」列用 --rule-id）" % deadline_type
        )
    if len(hits) == 1:
        return hits[0]

    if scene:
        narrowed = [r for r in hits if scene in r["适用情形"]]
        if len(narrowed) == 1:
            return narrowed[0]
        if len(narrowed) > 1:
            hits = narrowed

    raise InputError(
        "期间类型「%s」有 %d 条规则可选，请用 --scene 或 --rule-id 明确：\n%s"
        % (
            deadline_type,
            len(hits),
            "\n".join("  %s  %s（%s）" % (r["编号"], r["期间类型"], r["适用情形"]) for r in hits),
        )
    )


# ---------------------------------------------------------------- 节假日表


class HolidayCalendar:
    """按年加载节假日表；年份表缺失即拒绝判断，绝不猜。"""

    def __init__(self, holidays_dir: Path):
        self.dir = holidays_dir
        self._cache = {}

    def _load_year(self, year: int):
        if year in self._cache:
            return self._cache[year]
        path = self.dir / ("holidays-%d.json" % year)
        if not path.exists():
            self._cache[year] = None
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise InputError("节假日表 %s 无法解析：%s" % (path, exc))

        rest = {}
        for item in data.get("rest_days", []) or []:
            rest[item["date"]] = item.get("name", "法定节假日")
        work = {}
        for item in data.get("make_up_workdays", []) or []:
            work[item["date"]] = item.get("name", "调休上班日")
        coverage = data.get("coverage") or {}
        entry = {
            "path": path,
            "rest": rest,
            "work": work,
            "start": coverage.get("start"),
            "end": coverage.get("end"),
            "source": (data.get("source") or {}).get("title", "[来源待补]"),
            "has_data": bool(rest),
        }
        self._cache[year] = entry
        return entry

    def classify(self, day: datetime.date):
        """返回 (状态, 说明)。状态取值：'工作日' / '休假日' / '无法判断'。"""
        entry = self._load_year(day.year)
        iso = day.isoformat()
        if entry is None:
            return "无法判断", "缺少 %d 年节假日表（assets/holidays-%d.json）" % (day.year, day.year)
        if not entry["has_data"]:
            return "无法判断", "%d 年节假日表存在但未录入放假数据，须先补录并核对来源" % day.year
        if entry["start"] and iso < entry["start"]:
            return "无法判断", "%s 早于 %d 年节假日表覆盖起点 %s" % (iso, day.year, entry["start"])
        if entry["end"] and iso > entry["end"]:
            return "无法判断", "%s 晚于 %d 年节假日表覆盖终点 %s" % (iso, day.year, entry["end"])
        if iso in entry["rest"]:
            return "休假日", "法定节假日：%s" % entry["rest"][iso]
        if iso in entry["work"]:
            return "工作日", entry["work"][iso]
        if day.weekday() >= 5:
            return "休假日", "周末（周%s）" % WEEKDAY_CN[day.weekday()]
        return "工作日", "工作日（周%s）" % WEEKDAY_CN[day.weekday()]


# ---------------------------------------------------------------- 期间计算


def add_days(start: datetime.date, days: int) -> datetime.date:
    """起算日不计入：期间自次日起算，故届满日 = 起算日 + N 日。"""
    return start + datetime.timedelta(days=days)


def add_months(start: datetime.date, months: int) -> datetime.date:
    """以月计的期间：到期月对应日；该月无对应日的取该月最后一日。"""
    total = start.month - 1 + months
    year = start.year + total // 12
    month = total % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return datetime.date(year, month, min(start.day, last_day))


def fmt(day: datetime.date) -> str:
    return "%s（周%s）" % (day.isoformat(), WEEKDAY_CN[day.weekday()])


def rule_verification_state(rule: dict) -> str:
    """把规则的法条验真状态转为面向用户的结论状态。

    待验真不阻断个人辅助草算，但必须显著标识；已明确验出风险的规则视为不可用。
    """
    status = (rule.get("验真状态") or "").strip()
    if status in VERIFY_PASSED:
        return "辅助计算-法条依据已验真"
    if status in VERIFY_BLOCKED:
        raise InputError(
            "规则 %s（%s·%s）的法条验真状态为「%s」，已知存在风险，本次不应继续计算。"
            "请先更新规则表的期间、起算点或法条依据。"
            % (rule["编号"], rule["期间类型"], rule["适用情形"], status)
        )
    return "辅助草算-法条依据待验真"


def build_result(rule, start, court_days, cal, today):
    """返回 (结果 dict, 退出码)。"""
    steps = []
    unit = rule["单位"]
    raw_value = rule["期间值"]
    conclusion_state = rule_verification_state(rule)

    if raw_value == COURT_DESIGNATED:
        if court_days is None:
            raise InputError(
                "规则 %s（%s·%s）的期间由法院指定，脚本不自行推定。\n"
                "请从举证通知书/受理通知书里读出法院指定天数，用 --court-days 传入；"
                "文书未载明的，向法院书面确认后再算。" % (rule["编号"], rule["期间类型"], rule["适用情形"])
            )
        period_value = court_days
        unit = "日"
        steps.append("期间来源：法院指定 %d 日（由承办律师从法院文书录入，脚本不推定）" % court_days)
    else:
        try:
            period_value = int(raw_value)
        except ValueError:
            raise InputError(
                "规则 %s 的「期间值」既非数字也非「%s」，无法计算（当前值：%s）"
                % (rule["编号"], COURT_DESIGNATED, raw_value)
            )
        steps.append("期间来源：规则表 %s → %s %s" % (rule["编号"], raw_value, unit))

    steps.append("起算点：%s" % rule["起算点"])
    steps.append("录入的起算日：%s" % fmt(start))
    steps.append("起算日不计入，期间自 %s 起算" % fmt(start + datetime.timedelta(days=1)))

    if unit == "日":
        raw_due = add_days(start, period_value)
        steps.append("以日计算：%s + %d 日 → 原始末日 %s" % (start.isoformat(), period_value, fmt(raw_due)))
    elif unit == "月":
        raw_due = add_months(start, period_value)
        steps.append(
            "以月计算（到期月对应日，无对应日取月末）：%s + %d 个月 → 原始末日 %s"
            % (start.isoformat(), period_value, fmt(raw_due))
        )
    elif unit == "年":
        raw_due = add_months(start, period_value * 12)
        steps.append(
            "以年计算（到期年对应日，无对应日取月末）：%s + %d 年 → 原始末日 %s"
            % (start.isoformat(), period_value, fmt(raw_due))
        )
    else:
        raise InputError("规则 %s 的「单位」只支持 日/月/年，当前为「%s」" % (rule["编号"], unit))

    result = {
        "结论状态": conclusion_state,
        "规则编号": rule["编号"],
        "期间类型": rule["期间类型"],
        "适用情形": rule["适用情形"],
        "期间": "%s %s" % (period_value, unit),
        "起算日": start.isoformat(),
        "原始末日": raw_due.isoformat(),
        "届满日": None,
        "顺延": None,
        "推算过程": steps,
        "失权警示": DISCLAIMER,
        "法条依据": rule["法条依据"],
        "验真状态": rule["验真状态"],
    }

    # 末日顺延（铁律 2）
    cursor = raw_due
    shifted = 0
    while True:
        status, why = cal.classify(cursor)
        if status == "无法判断":
            steps.append("末日 %s 无法判断是否休假日：%s" % (cursor.isoformat(), why))
            result["顺延"] = "拒绝顺延"
            result["拒绝原因"] = why
            result["提示"] = (
                "原始末日 %s；该日可能为节假日，顺延需人工核对。"
                "请补齐 assets/holidays-%d.json 后重算，或由承办律师依当年国务院放假安排人工核定。"
                % (raw_due.isoformat(), cursor.year)
            )
            return result, 4
        if status == "休假日":
            steps.append("末日 %s 为休假日（%s）→ 顺延 1 日" % (cursor.isoformat(), why))
            cursor = cursor + datetime.timedelta(days=1)
            shifted += 1
            if shifted > 30:
                raise InputError("顺延超过 30 日，节假日表疑似异常，请人工核对")
            continue
        steps.append("末日 %s 为%s → 期间届满" % (cursor.isoformat(), why))
        break

    result["届满日"] = cursor.isoformat()
    result["顺延"] = "顺延 %d 日" % shifted if shifted else "无需顺延"
    if cursor != raw_due:
        steps.append("顺延后届满日：%s（共顺延 %d 日）" % (fmt(cursor), shifted))
    result["剩余天数"] = (cursor - today).days
    result["紧迫度"] = urgency_bucket(result["剩余天数"])
    return result, 0


def urgency_bucket(remaining: int) -> str:
    if remaining < 0:
        return "已过期"
    if remaining == 0:
        return "今日届满"
    if remaining <= 7:
        return "7 天内"
    if remaining <= 30:
        return "30 天内"
    return "30 天以上"


# ---------------------------------------------------------------- 输出


def print_result(result, exit_code):
    print("=" * 68)
    if exit_code == 0:
        print("诉讼期限计算结果")
    else:
        print("⚠️ 期限计算部分完成 —— 节假日表缺位，拒绝输出顺延后的日期")
    print("=" * 68)
    print("结论状态：%s" % result["结论状态"])
    print("规则编号：%s" % result["规则编号"])
    print("期间类型：%s（%s）" % (result["期间类型"], result["适用情形"]))
    print("期间长度：%s" % result["期间"])
    print("起算日　：%s" % result["起算日"])
    print("原始末日：%s" % result["原始末日"])
    if exit_code == 0:
        print("届满日　：%s  【%s】" % (result["届满日"], result["顺延"]))
        print("紧迫度　：%s（距今 %d 天）" % (result["紧迫度"], result["剩余天数"]))
    else:
        print("届满日　：不输出（%s）" % result.get("拒绝原因", ""))
        print("提示　　：%s" % result.get("提示", ""))
    print()
    print("推算过程：")
    for i, step in enumerate(result["推算过程"], 1):
        print("  %d. %s" % (i, step))
    print()
    print("法条依据：%s ｜ 验真状态：%s" % (result["法条依据"], result["验真状态"]))
    if result["验真状态"] not in VERIFY_PASSED:
        print("提醒　　：该行法条依据尚未完成验真，本次是个人辅助草算，不得冒充已验真结论。")
    print()
    print("失权警示：%s" % DISCLAIMER)


def cmd_list_types(parsed):
    print("规则表可用期间规则（来源：%s）" % DEFAULT_RULES_FILE.name)
    print("-" * 84)
    print("%-5s %-10s %-28s %-10s %s" % ("编号", "期间类型", "适用情形", "期间", "验真状态"))
    for r in parsed["rules"]:
        print(
            "%-5s %-10s %-28s %-10s %s"
            % (r["编号"], r["期间类型"], r["适用情形"], "%s %s" % (r["期间值"], r["单位"]), r["验真状态"])
        )
    print("-" * 84)


# ---------------------------------------------------------------- CLI


def build_parser():
    p = argparse.ArgumentParser(
        prog="compute_deadline.py",
        description="诉讼期限计算器：起算日不计入 + 月年对应日 + 末日休假顺延，规则与节假日均来自可追溯的数据文件。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  python3 scripts/compute_deadline.py --start-date 2026-08-10 --type 上诉期 --scene 判决\n"
            "  python3 scripts/compute_deadline.py --start-date 2026-08-10 --type 答辩期 --scene 涉外\n"
            "  python3 scripts/compute_deadline.py --start-date 2026-06-30 --type 举证期限 --scene 普通 --court-days 30\n"
            "  python3 scripts/compute_deadline.py --list-types\n\n"
            "退出码：0 出结论 ｜ 2 入参或资源错误 ｜ 4 节假日表缺位、拒绝顺延\n"
        ),
    )
    p.add_argument("--start-date", help="起算日（送达日/生效日/履行期末日等），格式 YYYY-MM-DD")
    p.add_argument("--type", dest="deadline_type", help="期间类型，如 答辩期 / 上诉期 / 举证期限 / 申请执行")
    p.add_argument("--scene", default="", help="适用情形关键词，用于在同一期间类型下选行，如 判决 / 裁定 / 涉外 / 动产")
    p.add_argument("--rule-id", default="", help="直接指定规则编号（如 D05），优先于 --type/--scene")
    p.add_argument("--doc-type", default="", help="文书类型（判决书/裁定书/起诉状副本…），仅记录进推算过程")
    p.add_argument("--court-days", type=int, default=None, help="法院指定天数，仅「法院指定」类期间需要")
    p.add_argument("--today", default="", help="以该日期计算紧迫度，默认取系统当天，格式 YYYY-MM-DD")
    p.add_argument("--rules-file", default=str(DEFAULT_RULES_FILE), help="期限规则表路径（默认随技能包）")
    p.add_argument("--holidays-dir", default=str(DEFAULT_HOLIDAYS_DIR), help="节假日表目录（默认随技能包）")
    p.add_argument("--list-types", action="store_true", help="列出规则表全部期间规则并退出")
    p.add_argument("--json", action="store_true", help="以 JSON 输出，便于回写台账")
    return p


def parse_date(value: str, label: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(value)
    except (ValueError, TypeError):
        raise InputError("%s 格式不合法，应为 YYYY-MM-DD（当前值：%s）" % (label, value))


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    try:
        parsed = parse_rules_file(Path(args.rules_file))

        if args.list_types:
            cmd_list_types(parsed)
            return 0

        if not args.start_date:
            raise InputError("缺少 --start-date（起算日）。模型只负责从法院文书提取该日期，不得推断。")
        if not (args.deadline_type or args.rule_id):
            raise InputError("缺少 --type 或 --rule-id，用 --list-types 查看可用期间类型。")

        start = parse_date(args.start_date, "--start-date")
        today = parse_date(args.today, "--today") if args.today else datetime.date.today()

        rule = match_rule(parsed["rules"], args.deadline_type, args.scene, args.rule_id)

        cal = HolidayCalendar(Path(args.holidays_dir))
        result, code = build_result(rule, start, args.court_days, cal, today)
        if args.doc_type:
            result["文书类型"] = args.doc_type
            result["推算过程"].insert(0, "文书类型（律师录入）：%s" % args.doc_type)

        if args.json:
            result["计算状态"] = "已计算届满日" if code == 0 else "拒绝顺延-节假日表缺位"
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_result(result, code)
        return code

    except InputError as exc:
        print("❌ %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
