"""Parse the explicit target scope for sparse workbook edits."""
import re

SCOPE_ALL = "ALL"


def _col_index(letters: str) -> int:
    idx = 0
    for ch in letters.upper():
        idx = idx * 26 + (ord(ch) - 64)
    return idx


def split_scope_items(items):
    """按引号状态拆逗号：Excel 的 sheet 名允许逗号，`'Sales,2026'!A1:A2` 是合法写法。

    直接 split(",") 会把它拆成两段，其中 `'Sales` 去掉引号后没有 `!`，会被当成
    「整表放行」——目标表反而不在范围内，另一张真名 Sales 的表却被整张授权。
    """
    parts = []
    for raw in items or []:
        parts += _split_one_scope_item(str(raw))
    return [p.strip() for p in parts if p.strip()]


def split_sheet_and_range(part: str):
    """在引号外的第一个 `!` 处切开 sheet 名与范围；没有分隔符时返回 (part, None)。

    Excel 的 sheet 名允许 `!`，`'Sales!2026'!A1:A2` 是合法引用。直接 partition("!")
    会在名字内部切开，整条范围就此作废。
    """
    quoted = False
    for i, ch in enumerate(part):
        if ch == "'":
            quoted = not quoted
        elif ch == "!" and not quoted:
            return part[:i], part[i + 1:]
    return part, None


def _split_one_scope_item(text: str):
    parts, buf, quoted = [], [], False
    for ch in text:
        if ch == "'":
            quoted = not quoted
        elif ch == "," and not quoted:
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    parts.append("".join(buf))
    return parts


def unquote_sheet_name(name: str) -> str:
    """去掉包裹的单引号并反转义内部的 ''。"""
    name = name.strip()
    if len(name) >= 2 and name.startswith("'") and name.endswith("'"):
        name = name[1:-1]
    return name.replace("''", "'")


class ScopeError(ValueError):
    """--scope 写法不合法。范围认不出时必须报错，不能退化成整表。"""


def parse_scope(items) -> dict:
    """'明细!G:I' / '汇总' / '明细!A2:C10' → {sheet: SCOPE_ALL | [(r1,c1,r2,c2)]}。

    --scope 划的是「本轮允许改动」的边界，认不出的范围必须 fail closed：
    不能把无法识别的范围扩大为整表授权。
    """
    scope: dict = {}
    for part in split_scope_items(items):
        raw_name, rng = split_sheet_and_range(part)
        if rng is None:
            scope[unquote_sheet_name(raw_name)] = SCOPE_ALL
            continue
        name = unquote_sheet_name(raw_name)
        box = _parse_scope_range(rng.strip())
        if box is None:
            raise ScopeError(
                f"--scope 里的范围认不出：{part!r}。"
                "写成 '子表名!A2:C10' / '子表名!G:I' / '子表名!2:5'，整表只写子表名。")
        if scope.get(name) == SCOPE_ALL:
            continue
        scope.setdefault(name, [])
        scope[name].append(box)
    return scope


MAX_EXCEL_ROW = 1048576
MAX_EXCEL_COL = 16384          # XFD


def _within_excel_bounds(box) -> bool:
    """行列必须落在 Excel 的真实边界内。

    只校验形状会让 `A0:XFD9999999` 这类非法输入被接受：行 0 起、行号上不封顶，
    结果所有合法坐标都算 in-scope，等于把一个写错的范围放大成整表授权。
    越界一律判非法，不 clamp——clamp 同样是在替调用方扩大授权。
    """
    start_row, start_col, end_row, end_col = box
    # 起点必须不晚于终点：`Z:A` / `9:2` 这类反序范围本地会匹配 0 格、在线会被
    # 悄悄当成 A:Z，两种都不是调用方写下的意思。与 iter_range 拒绝 B2:A1 同档，
    # 一律判非法，让调用方自己改对。
    if start_row > end_row or start_col > end_col:
        return False
    return (1 <= start_row <= MAX_EXCEL_ROW and 1 <= end_row <= MAX_EXCEL_ROW
            and 1 <= start_col <= MAX_EXCEL_COL and 1 <= end_col <= MAX_EXCEL_COL)


def _parse_scope_range(rng: str):
    """'G:I' / '3:20' / 'A2:C10' / 'B7' → (r1,c1,r2,c2)；认不出或越界返回 None。"""
    box = _parse_scope_shape(rng.replace("$", "").upper())
    if box is None or not _within_excel_bounds(box):
        return None
    return box


def _parse_scope_shape(rng: str):
    m = re.fullmatch(r"([A-Z]{1,3}):([A-Z]{1,3})", rng)
    if m:
        return 1, _col_index(m.group(1)), MAX_EXCEL_ROW, _col_index(m.group(2))
    m = re.fullmatch(r"([0-9]{1,7}):([0-9]{1,7})", rng)
    if m:
        return int(m.group(1)), 1, int(m.group(2)), MAX_EXCEL_COL
    m = re.fullmatch(r"([A-Z]{1,3})([0-9]{1,7})(?::([A-Z]{1,3})([0-9]{1,7}))?", rng)
    if m:
        start_col, start_row = _col_index(m.group(1)), int(m.group(2))
        end_col = _col_index(m.group(3)) if m.group(3) else start_col
        end_row = int(m.group(4)) if m.group(4) else start_row
        # 单元格范围沿用原有的 min/max 归一：`C10:A2` 与 `A2:C10` 等价，
        # 这是本条评审之前就有的行为，不在「反序 fail-closed」的范围内。
        return (
            min(start_row, end_row), min(start_col, end_col),
            max(start_row, end_row), max(start_col, end_col),
        )
    return None


def _in_scope(scope: dict, sheet: str, coord: str) -> bool:
    entry = scope.get(sheet)
    if entry is None:
        return False
    if entry == SCOPE_ALL:
        return True
    m = re.fullmatch(r"([A-Z]{1,3})([0-9]{1,7})", coord)
    if not m:
        return False
    col, row = _col_index(m.group(1)), int(m.group(2))
    return any(r1 <= row <= r2 and c1 <= col <= c2 for r1, c1, r2, c2 in entry)
