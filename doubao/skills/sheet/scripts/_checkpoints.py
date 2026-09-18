"""任务检查点：把「我核对过了」变成工具能判的事实。

自然语言回执只能证明调用方写了一段话，证明不了它真的回读过产物。检查点把
用户点名的格址、期望值、必须是公式的区域、必须存在的子表写成 JSON，由工具
回读产物逐条判，不符就是不符。

期望值只能来自用户明确给出的数，或调用方独立复算出来的数——把产物里读到的
数抄进期望值，判出来的「通过」没有任何信息量。

本模块不依赖 openpyxl 也不依赖 CLI：调用方传一个 lookup 回调，本地引擎与在线
引擎因此共用同一份契约和同一套判据。
"""
from __future__ import annotations

import json
import math
import re
from typing import Any, Callable, List, Optional, Tuple

CELL_RE = re.compile(r"^\$?([A-Z]{1,3})\$?([0-9]{1,7})$")
MAX_RANGE_CELLS = 20000


def col_index(letters: str) -> int:
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - 64)
    return idx


def col_letter(idx: int) -> str:
    out = ""
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        out = chr(65 + rem) + out
    return out


def split_ref(ref: str) -> Tuple[Optional[str], str]:
    """'汇总!B12' → ('汇总', 'B12')；没有子表名时返回 (None, ...)。"""
    text = str(ref or "").strip()
    if "!" not in text:
        return None, text.upper()
    sheet, addr = text.rsplit("!", 1)
    return sheet.strip().strip("'"), addr.strip().upper()


def iter_range(addr: str) -> Optional[List[str]]:
    """'A1:C3' / 'B12' → 坐标列表；超上限或解析不了返回 None。"""
    addr = addr.replace("$", "").upper()
    parts = addr.split(":")
    if len(parts) == 1:
        return [parts[0]] if CELL_RE.match(parts[0]) else None
    if len(parts) != 2:
        return None
    start_match, end_match = CELL_RE.match(parts[0]), CELL_RE.match(parts[1])
    if not (start_match and end_match):
        return None
    start_col, start_row = col_index(start_match.group(1)), int(start_match.group(2))
    end_col, end_row = col_index(end_match.group(1)), int(end_match.group(2))
    start_row, end_row = min(start_row, end_row), max(start_row, end_row)
    start_col, end_col = min(start_col, end_col), max(start_col, end_col)
    if (end_row - start_row + 1) * (end_col - start_col + 1) > MAX_RANGE_CELLS:
        return None
    return [
        f"{col_letter(c)}{r}"
        for r in range(start_row, end_row + 1)
        for c in range(start_col, end_col + 1)
    ]


def load_checkpoints(raw: Optional[str]) -> Tuple[List[dict], Optional[str]]:
    """`@路径` 从文件读，其余按内联 JSON 解析。返回 (条目列表, 错误说明)。"""
    if raw is None:
        return [], None
    text = raw.strip()
    if text.startswith("@"):
        path = text[1:].strip().strip("\"'")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            return [], f"检查点文件读不到：{path}（{exc.strerror or exc}）"
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return [], f"检查点不是合法 JSON：{exc}"
    if isinstance(data, dict):
        data = data.get("checkpoints", data.get("items"))
    if not isinstance(data, list) or not data:
        return [], "检查点必须是非空数组，或含 checkpoints 数组的对象"
    for i, item in enumerate(data):
        problem = _describe_item_problem(item, i + 1)
        if problem:
            return [], problem
    return data, None


# cell / range 条目要判什么，全靠这些键；一个都没有就只是个定位，判不出任何东西。
ASSERTION_KEYS = ("expect", "non_empty", "formula", "all_formula")


TARGET_KEYS = ("cell", "range", "sheets")
# 这三个判据靠真值决定要不要跑，写成 false 等于没写。expect 例外：期望值可能
# 正是 0 / false / 空串，所以它按「键在不在」判断。
TRUTHY_ASSERTIONS = ("non_empty", "formula", "all_formula")


def _describe_item_problem(item: Any, ordinal: int) -> Optional[str]:
    """契约本身写得不对时给出说明；没问题返回 None。"""
    if not isinstance(item, dict):
        return f"第 {ordinal} 条不是对象"

    targets = [k for k in TARGET_KEYS if k in item]
    if not targets:
        return f"第 {ordinal} 条缺少 cell / range / sheets，工具不知道要查哪里"
    if len(targets) > 1:
        # 判定按固定顺序只认一个目标，其余的连同它们的判据会被静默跳过。
        return (f"第 {ordinal} 条同时写了 {' 和 '.join(targets)}，只能写一个；"
                "拆成多条，否则只有一个会被执行")

    if "sheets" in item:
        return _describe_sheets_problem(item["sheets"], ordinal)
    return _describe_assertion_problem(item, ordinal)


def _describe_sheets_problem(sheets: Any, ordinal: int) -> Optional[str]:
    if not isinstance(sheets, list):
        # 字符串会被按字符迭代，dict 会被按键迭代，两者都会判出假结论。
        return f"第 {ordinal} 条的 sheets 要是数组，现在是 {type(sheets).__name__}"
    if not sheets:
        return f"第 {ordinal} 条的 sheets 是空的，没有要校验的子表"
    return None


def _describe_assertion_problem(item: dict, ordinal: int) -> Optional[str]:
    declared = [k for k in ASSERTION_KEYS if k in item]
    if not declared:
        # 只有定位没有判据，跑完什么都没校验，却会被当成「检查点跑过了」。
        return (f"第 {ordinal} 条只写了位置没写判据，"
                f"补一个 {' / '.join(ASSERTION_KEYS)}，否则这条什么都不查")
    disabled = [k for k in TRUTHY_ASSERTIONS if k in item and not item[k]]
    if len(disabled) == len(declared):
        # 全部判据都写成 false，跑起来一条 detail 都不会产生。
        return (f"第 {ordinal} 条的 {' / '.join(disabled)} 写成了 false，等于没写判据；"
                "要么改成 true，要么删掉这条")
    return _describe_tolerance_problem(item.get("tolerance"), ordinal)


def _describe_tolerance_problem(tolerance: Any, ordinal: int) -> Optional[str]:
    """容差必须是非负有限数。bool 是 int 子类，写成 true 会静默放宽成 1。"""
    if tolerance is None:
        return None
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)):
        return (f"第 {ordinal} 条的 tolerance 要是数字，"
                f"现在是 {type(tolerance).__name__}")
    # JSON 的整数没有位数上限，10**400 这类合法输入转 float 会抛 OverflowError，
    # 让「校验容差」这一步自己崩掉。转换放进 try，任何失败都归为契约写错。
    try:
        value = float(tolerance)
    except (OverflowError, ValueError):
        return f"第 {ordinal} 条的 tolerance 超出可表示范围"
    if not math.isfinite(value) or value < 0:
        return f"第 {ordinal} 条的 tolerance 要是非负有限数，现在是 {tolerance!r:.40}"
    return None


def _as_number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    text = re.sub(r"[¥￥$€£\s]", "", text)
    percent = text.endswith("%")
    if percent:
        text = text[:-1]
    try:
        num = float(text)
    except ValueError:
        return None
    return num / 100.0 if percent else num


def _label(item: dict, ref: str) -> str:
    name = str(item.get("label") or "").strip()
    return f"{ref}（{name}）" if name else ref


def _is_blank(value) -> bool:
    return value is None or str(value).strip() == ""


def _judge_formula_coverage(cells: List[tuple], sheet: str, strict: bool):
    """判「这片区域是否由公式驱动」，返回 (result, message)。

    strict（all_formula）承诺的是整片区域都由公式驱动，所以空格也不合格：夹在
    公式中间的空格若算通过，一个空格就能把门禁绕过去。非 strict（formula）保留
    宽松语义——只要求非空格都是公式，区域里允许留空。
    """
    blanks = [c for c, (v, f) in cells if not f and _is_blank(v)]
    statics = [c for c, (v, f) in cells if not f and not _is_blank(v)]
    missing = [c for c, (v, f) in cells if not f] if strict else statics
    if not strict and len(blanks) == len(cells):
        return "fail", "该区域没有任何内容，公式无从谈起"
    if strict and blanks:
        return "fail", (f"{len(missing)} 个格没有公式（其中 {len(blanks)} 个是空格），"
                        f"首个是 {sheet}!{missing[0]}")
    if statics:
        return "fail", f"{len(statics)} 个格是静态值不是公式，首个是 {sheet}!{statics[0]}"
    return "pass", "该区域由公式驱动"


def verify_checkpoints(items: List[dict],
                       lookup: Callable[[str, str], Tuple[Any, str]],
                       sheet_names: List[str],
                       values_available: bool = True) -> dict:
    """逐条判定。lookup(sheet, coord) 返回 (值, 公式串)，公式串为空表示不是公式。

    values_available=False 用于本地产物没有缓存值的情况：期望值类条目判不了，
    记为 skipped 并说明原因，形态类条目照判——判不了要说判不了，不能算通过。
    """
    details: List[dict] = []

    def add(result: str, ref: str, item: dict, message: str, actual: Any = None):
        entry = {"result": result, "ref": ref, "message": message}
        if item.get("label"):
            entry["label"] = item["label"]
        if actual is not None:
            entry["actual"] = actual
        details.append(entry)

    known = set(sheet_names)
    for item in items:
        if "sheets" in item:
            wanted = [str(s) for s in (item.get("sheets") or [])]
            ref = "子表集合"
            if not wanted:
                # 空列表什么都没校验。若记成 pass，上层看到 passed>0 且 skipped==0
                # 就会判本次通过，等于给出一个不含任何判据的通过。
                add("invalid", ref, item, "sheets 是空的，没有要校验的子表；删掉这条或写上子表名")
                continue
            missing = [s for s in wanted if s not in known]
            if missing:
                add("fail", ref, item, f"缺少子表：{'、'.join(missing)}", ", ".join(sheet_names))
            else:
                add("pass", ref, item, f"{len(wanted)} 张子表都在")
            continue

        raw_ref = str(item.get("cell") or item.get("range"))
        sheet, addr = split_ref(raw_ref)
        if sheet is None:
            add("invalid", raw_ref, item, "引用要带子表名，写成 '子表名!B12'")
            continue
        if sheet not in known:
            add("fail", raw_ref, item, f"子表「{sheet}」不存在", ", ".join(sheet_names))
            continue
        coords = iter_range(addr)
        if not coords:
            add("invalid", raw_ref, item, f"范围解析不了或超过 {MAX_RANGE_CELLS} 格")
            continue

        ref = _label(item, raw_ref)
        cells = [(c, lookup(sheet, c)) for c in coords]

        if item.get("non_empty"):
            empty = [c for c, (v, f) in cells
                     if (v is None or str(v).strip() == "") and not f]
            if empty:
                add("fail", ref, item, f"{len(empty)} 个格为空，首个是 {sheet}!{empty[0]}")
            else:
                add("pass", ref, item, "全部非空")

        if item.get("formula") or item.get("all_formula"):
            result, message = _judge_formula_coverage(
                cells, sheet, strict=bool(item.get("all_formula")))
            add(result, ref, item, message)

        if "expect" in item:
            if len(coords) != 1:
                add("invalid", ref, item, "期望值只能对单格写，范围请拆成多条")
                continue
            value, formula = cells[0][1]
            if not values_available:
                add("skip", ref, item, "产物里没有可读的计算值，期望值判不了")
                continue
            if formula and (value is None or str(value).strip() == ""):
                # 本地新写的公式没有缓存值，读出来是空。这不是「算错了」，
                # 是还没算过：重算或导入在线表回读之后才判得了。
                add("skip", ref, item,
                    "公式格还没有计算值（先完成重算，或导入在线表后用在线自检判）")
                continue
            expected = item["expect"]
            exp_num, act_num = _as_number(expected), _as_number(value)
            if exp_num is not None and act_num is not None:
                # 直接调 verify_checkpoints 的调用方可能没走 load_checkpoints 的
                # 校验，这里再挡一次：容差不合法就判 invalid，不让 float() 抛。
                if _describe_tolerance_problem(item.get("tolerance"), 0):
                    add("invalid", ref, item,
                        f"tolerance 不是非负有限数：{item.get('tolerance')!r}")
                    continue
                tol = float(item.get("tolerance", 0) or 0)
                if abs(act_num - exp_num) <= tol:
                    add("pass", ref, item, f"值符合期望（{expected}）")
                else:
                    add("fail", ref, item,
                        f"期望 {expected}，实际 {value}（容差 {tol}）", value)
            elif str(expected).strip() == str(value if value is not None else "").strip():
                add("pass", ref, item, f"值符合期望（{expected}）")
            else:
                add("fail", ref, item, f"期望 {expected}，实际 {value}", value)

    counts = {k: sum(1 for d in details if d["result"] == k)
              for k in ("pass", "fail", "skip", "invalid")}
    if counts["fail"] or counts["invalid"]:
        status = "failed"
    elif counts["skip"]:
        # 有判不了的条目就不能汇总成通过——「一条过 + 一条 skip」若返回 pass，
        # 调用方会当成全过而退出 0，未判定的期望值就这么被放行了。
        status = "inconclusive"
    elif counts["pass"]:
        status = "pass"
    else:
        status = "skipped"
    return {
        "status": status,
        "total": len(details),
        "passed": counts["pass"],
        "failed": counts["fail"] + counts["invalid"],
        "skipped": counts["skip"],
        "details": details,
    }


CHECKPOINT_HINT = """\
[checkpoints] {failed} 条未通过：
{lines}
检查点是用户点名要的数和形态，未通过就是产物没做到，不是判据太严。
逐条追到错源改正后重跑；确属期望值写错的，改期望值时要说明依据。"""


CHECKPOINT_SKIP_HINT = """\
[checkpoints] {skipped} 条判不了（未通过，也未失败）：
{lines}
判不了不等于通过：先完成重算或导入在线表回读，再重跑本命令把它们判掉。
在此之前不得声称检查点全过。"""


def emit_checkpoint_hint(result: dict, printer) -> bool:
    """把未通过的条目打印到 stderr。返回是否存在未通过项。"""
    bad = [d for d in result.get("details", []) if d["result"] in ("fail", "invalid")]
    if not bad:
        return False
    lines = "\n".join(f"  - {d['ref']}：{d['message']}" for d in bad[:12])
    printer(CHECKPOINT_HINT.format(failed=len(bad), lines=lines))
    return True


def checkpoint_skips(result: dict) -> list:
    """判不了的条目。调用方据此降级，不能当成通过。"""
    return [d for d in result.get("details", []) if d["result"] == "skip"]


def emit_checkpoint_skip_hint(result: dict, printer) -> bool:
    """把判不了的条目打印到 stderr。返回是否存在这类条目。"""
    skipped = checkpoint_skips(result)
    if not skipped:
        return False
    lines = "\n".join(f"  - {d['ref']}：{d['message']}" for d in skipped[:12])
    printer(CHECKPOINT_SKIP_HINT.format(skipped=len(skipped), lines=lines))
    return True
