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

import datetime
import json
import math
import re
from decimal import Decimal, DecimalException, InvalidOperation, localcontext
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
    sheet = sheet.strip()
    if len(sheet) >= 2 and sheet.startswith("'") and sheet.endswith("'"):
        sheet = sheet[1:-1].replace("''", "'")
    return sheet, addr.strip().upper()


def resolve_sheet(name: str, known: List[str]) -> Optional[str]:
    if name in known:
        return name
    hits = [candidate for candidate in known if candidate.strip() == name.strip()]
    return hits[0] if len(hits) == 1 else None


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


def checkpoint_file_path(raw: Optional[str]) -> Optional[str]:
    """提取 @文件参数的路径；内联 JSON 或未传参数时返回 None。"""
    text = raw.strip() if raw is not None else ""
    return text[1:].strip().strip("\"'") if text.startswith("@") else None


def load_checkpoints(raw: Optional[str], require_sheet: bool = True) -> Tuple[List[dict], Optional[str]]:
    """`@路径` 从文件读，其余按内联 JSON 解析；CSV 可省略子表名前缀。"""
    if raw is None:
        return [], None
    text = raw.strip()
    path = checkpoint_file_path(raw)
    if path is not None:
        try:
            with open(path, "r", encoding="utf-8-sig") as fh:
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
        problem = _describe_item_problem(item, i + 1, require_sheet)
        if problem:
            return [], problem
    return data, None


# cell / range 条目要判什么，全靠这些键；一个都没有就只是个定位，判不出任何东西。
ASSERTION_KEYS = ("expect", "non_empty", "formula", "all_formula")


TARGET_KEYS = ("cell", "range", "sheets")
# 这三个判据靠真值决定要不要跑，写成 false 等于没写。expect 例外：期望值可能
# 正是 0 / false / 空串，所以它按「键在不在」判断。
TRUTHY_ASSERTIONS = ("non_empty", "formula", "all_formula")


def _describe_item_problem(item: Any, ordinal: int, require_sheet: bool = True) -> Optional[str]:
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
    return (_describe_reference_problem(item, ordinal, require_sheet)
            or _describe_assertion_problem(item, ordinal))


def _describe_reference_problem(item: dict, ordinal: int, require_sheet: bool) -> Optional[str]:
    """只校验引用契约；子表是否存在、值是否匹配留到读取产物后判断。"""
    ref = item.get("cell") if "cell" in item else item.get("range")
    if not isinstance(ref, str) or not ref.strip():
        return f"第 {ordinal} 条的引用要是非空字符串，写成 '子表名!B12'"
    sheet, addr = split_ref(ref)
    if (sheet is None and require_sheet) or (sheet is not None and not sheet.strip()):
        return f"第 {ordinal} 条的引用要带非空子表名，写成 '子表名!B12'"
    coords = iter_range(addr)
    if not coords:
        return f"第 {ordinal} 条的范围解析不了或超过 {MAX_RANGE_CELLS} 格"
    if "expect" in item and len(coords) != 1:
        return f"第 {ordinal} 条的期望值只能对单格写，范围请拆成多条"
    return None


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


def _as_number(value: Any) -> Optional[Decimal]:
    if isinstance(value, bool) or value is None:
        return None
    text = str(value).strip().replace(",", "")
    text = re.sub(r"[¥￥$€£\s]", "", text)
    percent = text.endswith("%")
    if percent:
        text = text[:-1]
    try:
        num = Decimal(text)
    except InvalidOperation:
        return None
    if not num.is_finite():
        return None
    if percent:
        # scaleb / 除法会受 Decimal 默认精度影响，直接调整指数保留原始数字。
        parts = num.as_tuple()
        return Decimal((parts.sign, parts.digits, parts.exponent - 2))
    return num


class Unjudgeable:
    """lookup 用它表示「这一格的值判不了」，并带上原因。

    例：重算引擎不支持某个新函数，算出 #NAME?——这不是产物算错，按 skip 处理。
    """

    def __init__(self, reason: str):
        self.reason = reason

    def __str__(self) -> str:
        return self.reason


_DATE_TYPES = (datetime.date, datetime.time, datetime.timedelta)   # datetime.datetime 是 date 的子类
TIME_FRACTION_RE = re.compile(r"(\d+:\d{2}:\d{2})\.(\d+)([+-]\d{2}:\d{2})?$")


def _normalized_time_fraction(text):
    """只规范化秒的小数末尾零，零微秒也可用 .0 / .000 表达，不舍入。"""
    def replace(match):
        fraction = match.group(2).rstrip("0")
        return match.group(1) + ("." + fraction if fraction else "") + (match.group(3) or "")
    return TIME_FRACTION_RE.sub(replace, text)


def _matches_text(value, expected):
    expected_text = str(expected).strip()
    forms = [text.strip() for text in _text_forms(value)]
    if isinstance(value, _DATE_TYPES):
        expected_text = _normalized_time_fraction(expected_text)
        forms = [_normalized_time_fraction(text) for text in forms]
    return expected_text in forms


def _fractional_forms(text: str, microsecond: int) -> List[str]:
    """只省略小数末尾的零，不舍入实际时间；首项用于精确报告。"""
    if not microsecond:
        return [text]
    fraction = ".{:06d}".format(microsecond)
    forms = [text]
    shortened = fraction
    while shortened.endswith("0"):
        shortened = shortened[:-1]
        forms.append(text.replace(fraction, shortened, 1))
    return forms


def _text_forms(value: Any) -> List[str]:
    """日期 / 时间 / 时长的等值文本写法，不丢弃秒或微秒。"""
    if isinstance(value, datetime.datetime):
        forms = _fractional_forms(value.isoformat(sep=" "), value.microsecond)
        if value.time() == datetime.time(0, 0):
            forms.insert(0, value.date().isoformat())
        if value.second == 0 and value.microsecond == 0:
            forms.append(value.isoformat(sep=" ", timespec="minutes"))
        return forms + [text.replace(" ", "T", 1) for text in forms if " " in text]
    if isinstance(value, datetime.date):
        return [value.isoformat()]
    if isinstance(value, datetime.time):
        forms = _fractional_forms(value.isoformat(), value.microsecond)
        return forms + ([value.isoformat(timespec="minutes")]
                        if value.second == 0 and value.microsecond == 0 else [])
    if isinstance(value, datetime.timedelta):
        # 使用整数微秒，避免 total_seconds() 的浮点量化和负亚秒值丢失符号。
        micros = (value.days * 86400 + value.seconds) * 1000000 + value.microseconds
        sign = "-" if micros < 0 else ""
        secs, fraction = divmod(abs(micros), 1000000)
        h, rem = divmod(secs, 3600)
        m, s = divmod(rem, 60)
        suffix = ".{:06d}".format(fraction) if fraction else ""
        forms = _fractional_forms(f"{sign}{h}:{m:02d}:{s:02d}{suffix}", fraction)
        forms += _fractional_forms(f"{sign}{h:02d}:{m:02d}:{s:02d}{suffix}", fraction)
        return forms + ([f"{sign}{h}:{m:02d}", f"{sign}{h:02d}:{m:02d}"]
                        if s == 0 and fraction == 0 else [])
    return [str(value if value is not None else "")]


EPOCH_1900 = datetime.datetime(1899, 12, 30)
EPOCH_1904 = datetime.datetime(1904, 1, 1)


def _excel_serial(value: Any, epoch: Optional[datetime.datetime] = None) -> Optional[float]:
    """日期 / 时间 / 时长换成 Excel 序列值（天），好跟写成数字的期望值比。

    epoch 取工作簿的日期系统（openpyxl 的 wb.epoch），默认 1900 系统。1900 系统沿用
    Excel 把 1900 年当闰年的历史偏差：仅纪元后第 1–60 天减 1（同 openpyxl.to_excel）。
    """
    if isinstance(value, (datetime.datetime, datetime.date)):
        if not isinstance(value, datetime.datetime):
            value = datetime.datetime.combine(value, datetime.time())
        if value.tzinfo is not None:
            value = value.replace(tzinfo=None)
        origin = epoch if epoch is not None else EPOCH_1900
        delta = value - origin
        days = delta.days
        if origin == EPOCH_1900 and 0 < days <= 60:
            days -= 1
        return days + (delta.seconds + delta.microseconds / 1e6) / 86400.0
    if isinstance(value, datetime.time):
        return (value.hour * 3600 + value.minute * 60 + value.second
                + value.microsecond / 1e6) / 86400.0
    if isinstance(value, datetime.timedelta):
        return value.total_seconds() / 86400.0
    return None


def _jsonable(value: Any) -> Any:
    """写进结果 JSON 的实际值：日期 / 时间 / 时长等非 JSON 基本类型转成可读文本。"""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return _text_forms(value)[0]


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


def _date_number(value, epoch, stored_number):
    if stored_number is not None:
        return stored_number
    serial = _excel_serial(value, epoch)
    return Decimal(repr(serial)) if serial is not None else None


def verify_checkpoints(items: List[dict],
                       lookup: Callable[[str, str], Tuple[Any, str]],
                       sheet_names: List[str],
                       values_available: bool = True,
                       rel_tol: float = 0.0,
                       formula_values_computed: bool = False,
                       date_epoch: Optional[datetime.datetime] = None,
                       numeric_lookup: Optional[Callable[[str, str], Optional[Decimal]]] = None) -> dict:
    """逐条判定。lookup(sheet, coord) 返回 (值, 公式串)，公式串为空表示不是公式。

    values_available=False 用于本地产物没有缓存值的情况：期望值类条目判不了，
    记为 skipped 并说明原因，形态类条目照判——判不了要说判不了，不能算通过。
    lookup 返回 Unjudgeable 作为值时，该格的期望值条目记为 skipped，原因取它自带的说明。
    rel_tol 仅用于未显式声明 tolerance 的公式格（吸收重算引擎的浮点尾差）。
    显式 tolerance（包括 0）始终作为绝对容差；静态格不应用 rel_tol。默认 0 即精确比较。
    date_epoch 是工作簿的日期系统，日期值与数字期望比较时按它换算序列值；默认 1900 系统。
    numeric_lookup 可提供日期格未经量化的原包数值；没有原包数值（如 ISO 日期）时才反算序列值。
    formula_values_computed=True 表示公式格的值来自刚完成的重算：值为空就是公式算出了
    空串，照常比对；默认 False 时空值视为「还没算」，判不了。
    """
    details: List[dict] = []

    def add(result: str, ref: str, item: dict, message: str, actual: Any = None):
        entry = {"result": result, "ref": ref, "message": message}
        if item.get("label"):
            entry["label"] = item["label"]
        if actual is not None:
            entry["actual"] = _jsonable(actual)
        details.append(entry)

    known = list(dict.fromkeys(sheet_names))
    for item in items:
        if "sheets" in item:
            wanted = [str(s) for s in (item.get("sheets") or [])]
            ref = "子表集合"
            if not wanted:
                # 空列表什么都没校验。若记成 pass，上层看到 passed>0 且 skipped==0
                # 就会判本次通过，等于给出一个不含任何判据的通过。
                add("invalid", ref, item, "sheets 是空的，没有要校验的子表；删掉这条或写上子表名")
                continue
            resolved_wanted = [resolve_sheet(s, known) for s in wanted]
            missing = [s for s, resolved in zip(wanted, resolved_wanted) if resolved is None]
            if missing:
                add("fail", ref, item, f"缺少子表：{'、'.join(missing)}", ", ".join(sheet_names))
            elif len(set(resolved_wanted)) != len(resolved_wanted):
                add("invalid", ref, item, "多个子表名指向同一张实际子表，请去重", ", ".join(sheet_names))
            else:
                add("pass", ref, item, f"{len(wanted)} 张子表都在")
            continue

        raw_ref = str(item.get("cell") or item.get("range"))
        sheet, addr = split_ref(raw_ref)
        if sheet is None:
            add("invalid", raw_ref, item, "引用要带子表名，写成 '子表名!B12'")
            continue
        resolved = resolve_sheet(sheet, known)
        if resolved is None:
            add("fail", raw_ref, item, f"子表「{sheet}」不存在", ", ".join(sheet_names))
            continue
        sheet = resolved
        coords = iter_range(addr)
        if not coords:
            add("invalid", raw_ref, item, f"范围解析不了或超过 {MAX_RANGE_CELLS} 格")
            continue

        ref = _label(item, raw_ref)
        cells = [(c, lookup(sheet, c)) for c in coords]

        if item.get("non_empty"):
            empty = [c for c, (v, f) in cells
                     if not isinstance(v, Unjudgeable) and _is_blank(v)
                     and (not f or (values_available and formula_values_computed))]
            unknown = [(c, v) for c, (v, f) in cells
                       if isinstance(v, Unjudgeable)
                       or (f and (not values_available
                                  or (not formula_values_computed and _is_blank(v))))]
            if empty:
                add("fail", ref, item, f"{len(empty)} 个格为空，首个是 {sheet}!{empty[0]}")
            elif unknown:
                first, value = unknown[0]
                reason = value.reason if isinstance(value, Unjudgeable) else "没有可用计算值"
                add("skip", ref, item,
                    f"{len(unknown)} 个格的结果未验证，首个是 {sheet}!{first}：{reason}；"
                    "不能以公式存在证明结果非空")
            else:
                add("pass", ref, item, "全部具有可读的非空值")

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
            if isinstance(value, Unjudgeable):
                add("skip", ref, item, value.reason)
                continue
            if (formula and not formula_values_computed
                    and (value is None or str(value).strip() == "")):
                # 公式格读出来是空且调用方没声明值已算好：可能是还没算过，
                # 也可能真算出了空串，分不清就不判。原因由调用方按场景给（Unjudgeable）。
                add("skip", ref, item, "公式格读不到计算值，判不了")
                continue
            expected = item["expect"]
            # JSON 类型表达判据：编号和精确文本不能先去空格、转数值再比较。
            # 实际值是日期 / 时间 / 时长时例外，期望文本按下方的日期写法展开比较。
            if isinstance(expected, (str, bool)) and not isinstance(value, _DATE_TYPES):
                matches = (type(value) is type(expected) and value == expected)
                # 保留空串检查空单元格的既有用法。
                matches = matches or (expected == "" and value is None)
                add("pass" if matches else "fail", ref, item,
                    "文本/布尔值符合期望" if matches else
                    f"期望 {expected!r}（{type(expected).__name__}），"
                    f"实际 {value!r}（{type(value).__name__}）；按原值精确比较", value)
                continue
            exp_num, act_num = _as_number(expected), _as_number(value)
            if act_num is None and exp_num is not None and not isinstance(expected, str):
                stored_number = numeric_lookup(sheet, coords[0]) if numeric_lookup else None
                act_num = _date_number(value, date_epoch, stored_number)
            if exp_num is not None and act_num is not None:
                # 直接调 verify_checkpoints 的调用方可能没走 load_checkpoints 的
                # 校验，这里再挡一次：容差不合法就判 invalid，不让 Decimal() 抛。
                if _describe_tolerance_problem(item.get("tolerance"), 0):
                    add("invalid", ref, item,
                        f"tolerance 不是非负有限数：{item.get('tolerance')!r}")
                    continue
                tol = Decimal(str(item.get("tolerance", 0) or 0))
                # 引擎的默认相对容差不能放宽用户明确声明的绝对精度。
                scale = Decimal(repr(rel_tol)) if formula and "tolerance" not in item else Decimal(0)
                try:
                    with localcontext() as ctx:
                        ctx.prec = max(len(n.as_tuple().digits) + abs(n.as_tuple().exponent)
                                       for n in (act_num, exp_num, tol, scale)) + 2
                        limit = max(tol, scale * max(abs(act_num), abs(exp_num)))
                        matches = abs(act_num - exp_num) <= limit
                        comparison = f"绝对容差 {tol}，相对容差 {scale}，有效容差 {limit}"
                except DecimalException:
                    # 指数超出 Decimal 运算范围（如 1E+999999999）：算不了容差，按原值精确比较
                    matches = act_num == exp_num
                    comparison = "超出容差运算范围，按原值精确比较"
                if matches:
                    add("pass", ref, item, f"值符合期望（{expected}；{comparison}）")
                else:
                    add("fail", ref, item,
                        f"期望 {expected}，实际 {value}（{comparison}）", value)
            elif _matches_text(value, expected):
                add("pass", ref, item, f"值符合期望（{expected}）")
            else:
                add("fail", ref, item, f"期望 {expected}，实际 {_jsonable(value)}", value)

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
判不了不等于通过：按每条后面的原因处理，判掉之前不得声称检查点全过。"""


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
