#!/usr/bin/env python3
"""从 JSONL 分块新建普通明细工作簿，不读取或改写已有模板。

python3 scripts/excel_build_workbook.py --spec ./book.json --output ./report.xlsx
仅重建本次生成的文件时可加 --overwrite。数据路径相对 spec 文件所在目录。
退出码 0 为构建成功，2 为输入或保存失败；不调用 LibreOffice、渲染或导入。
"""
import argparse
from datetime import date
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile

try:
    from openpyxl import Workbook
    from openpyxl.compat import safe_string
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
except ImportError as exc:
    OPENPYXL_IMPORT_ERROR = exc
else:
    OPENPYXL_IMPORT_ERROR = None


class BuildError(ValueError):
    """配置、数据或输出不满足无损构建要求时报告的错误。"""


CELL_TYPES = ("text", "number", "boolean", "date", "formula")
# Match the editable reader's unsupported Xstring spellings, including escaped underscores.
XSTRING_ESCAPE = re.compile(r"_[xX][0-9A-Fa-f]{4}_")


def unique_object(pairs):
    """解析 JSON 对象键值对，拒绝重复字段而不静默覆盖。"""
    result = {}
    for key, value in pairs:
        if key in result:
            raise BuildError("JSON 包含重复字段：{}".format(key))
        result[key] = value
    return result


def reject_constant(value):
    """拒绝 JSON 中非标准的 NaN 和 Infinity 常量。"""
    raise BuildError("JSON 不接受非有限数值：{}".format(value))


def parse_json(text, location):
    """严格解析 JSON，并在错误中附上输入位置与局部恢复提示。"""
    try:
        return json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant)
    except (ValueError, TypeError) as exc:
        raise BuildError("{}：{}；只修复该文件，不重写其它已完成文件".format(location, exc)) from exc


def fields(obj, allowed, required, where):
    """检查配置对象的必需字段及允许字段集合。"""
    if not isinstance(obj, dict):
        raise BuildError("{} 必须是 JSON object".format(where))
    unknown, missing = set(obj) - set(allowed), set(required) - set(obj)
    if unknown or missing:
        raise BuildError("{} 字段不匹配：缺少 {}；不支持 {}".format(where, sorted(missing), sorted(unknown)))


def text(value, where):
    """验证并返回非空、未超出单格长度限制的文本。"""
    if not isinstance(value, str) or not value.strip() or len(value) > 32767:
        raise BuildError("{} 必须是非空文本且不超过 32767 字符".format(where))
    return value


def dimension(value, where, maximum):
    """验证行高或列宽是允许范围内的有限正数。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise BuildError("{} 必须是有限数值".format(where))
    if not 0 < value <= maximum:
        raise BuildError("{} 必须在 (0, {}] 内".format(where, maximum))
    return value


def read_spec(path):
    """读取建表配置，校验子表与列定义并解析数据块路径。"""
    spec = parse_json(path.read_text(encoding="utf-8-sig"), str(path))
    fields(spec, {"sheets"}, {"sheets"}, "spec")
    if not isinstance(spec["sheets"], list) or not spec["sheets"]:
        raise BuildError("sheets 必须是非空数组")
    names, inputs = set(), {path.resolve()}
    for sheet in spec["sheets"]:
        fields(sheet, {"name", "columns", "data_files", "data_keys", "defaults",
                       "row_height", "freeze_header", "expected_rows"},
               {"name", "columns", "data_files"}, "sheet")
        name = text(sheet["name"], "sheet.name")
        if len(name) > 31 or re.search(r"[\\/*?:\[\]]", name) or name.startswith("'") or name.endswith("'"):
            raise BuildError("子表名不符合 Excel 命名限制：{}".format(name))
        if name.casefold() in names:
            raise BuildError("子表名重复（不区分大小写）：{}".format(name))
        names.add(name.casefold())
        columns = sheet["columns"]
        if not isinstance(columns, list) or not 1 <= len(columns) <= 16384:
            raise BuildError("{}.columns 必须含 1~16384 列".format(name))
        keys = set()
        for column in columns:
            fields(column, {"key", "title", "width", "number_format", "align", "type"},
                   {"key"}, name + ".column")
            key = text(column["key"], name + ".column.key")
            if key in keys:
                raise BuildError("{} 列字段重复：{}".format(name, key))
            keys.add(key)
            column["title"] = text(column.get("title", key), name + ".column.title")
            column["width"] = dimension(column.get("width", 18), name + ".column.width", 255)
            if "number_format" in column:
                text(column["number_format"], name + ".column.number_format")
            if "align" in column and column["align"] not in ("left", "center", "right"):
                raise BuildError("{}.column.align 只支持 left / center / right".format(name))
            if "type" in column and column["type"] not in CELL_TYPES:
                raise BuildError("{}.column.type 只支持 {}".format(name, " / ".join(CELL_TYPES)))
        fields(sheet.get("defaults", {}), keys, (), name + ".defaults")
        if "data_keys" in sheet:
            data_keys = sheet["data_keys"]
            if not isinstance(data_keys, list) or not data_keys:
                raise BuildError("{}.data_keys 必须是非空字段名数组".format(name))
            for key in data_keys:
                text(key, name + ".data_keys[]")
            if len(set(data_keys)) != len(data_keys):
                raise BuildError("{}.data_keys 包含重复字段".format(name))
            missing = keys - set(data_keys) - set(sheet.get("defaults", {}))
            if missing:
                raise BuildError("{} 的 data_keys / defaults 缺少输出字段 {}".format(name, sorted(missing)))
            untyped = [c["key"] for c in columns if "type" not in c]
            if untyped:
                raise BuildError("{} 紧凑数组的输出列须声明 type：{}；混合类型或字段不稳定时用具名对象".format(
                    name, untyped))
        sheet["row_height"] = dimension(sheet.get("row_height", 30), name + ".row_height", 409)
        if not isinstance(sheet.get("freeze_header", False), bool):
            raise BuildError("freeze_header 必须是 boolean")
        expected = sheet.get("expected_rows")
        if expected is not None and (type(expected) is not int or not 0 <= expected <= 1048575):
            raise BuildError("expected_rows 必须是 0~1048575 的整数")
        files = sheet["data_files"]
        if not isinstance(files, list) or (not files and expected != 0):
            raise BuildError("{}.data_files 必须是 JSONL 文件列表；仅 expected_rows=0 时允许空列表".format(name))
        resolved = [(path.parent / text(f, "data_files[]")).resolve() for f in files]
        if len(set(resolved)) != len(resolved):
            raise BuildError("{} 重复引用数据块".format(name))
        sheet["data_files"] = resolved
        inputs.update(resolved)
    return spec, inputs


def validate_integer(value, where):
    """拒绝无法在写入序列化及浮点表示中精确保留的整数。"""
    try:
        # Use the writer's numeric serializer, then the spreadsheet's floating-point
        # representation. A binary-exact int can still lose precision during serialization.
        retained = float(safe_string(value)) == value
    except (OverflowError, ValueError):
        retained = False
    if not retained:
        raise BuildError("{} 整数无法经数值序列化和浮点表示精确保留；"
                         "请按业务语义选择文本或其它精确表示，不自动舍入".format(where))


def assign(cell, value, where):
    """按显式类型写入单格，保留字面文本并拒绝不支持的值。"""
    if isinstance(value, dict):
        if set(value) == {"formula"}:
            formula = text(value["formula"], where + ".formula")
            if not formula.startswith("=") or not formula[1:].strip():
                raise BuildError("{} 的公式必须以 = 开头且有表达式".format(where))
            cell.value = formula
            return 1
        if set(value) == {"date"}:
            cell.value = date.fromisoformat(text(value["date"], where + ".date"))
            cell.number_format = "yyyy-mm-dd"
            return 0
        raise BuildError("{} 仅支持 JSON 标量或单字段 formula/date 对象".format(where))
    if isinstance(value, str):
        if len(value) > 32767:
            raise BuildError("{} 文本超出 Excel 单格长度，未截断保存".format(where))
        if re.search(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]", value):
            raise BuildError("{} 含 Excel 不支持的控制字符，未自动删除内容".format(where))
        if XSTRING_ESCAPE.search(value):
            raise BuildError("{} 含 OOXML 特殊转义形态文本，当前编辑加载器不支持；"
                             "请保留原文并选择可保真处理该文本的路径，不自动转义或删改".format(where))
        cell.value = value
        cell.data_type = "s"  # = 开头的外部文本不能隐式变成公式；编号保持文本。
    elif value is None or isinstance(value, (bool, int, float)):
        if type(value) is int:
            validate_integer(value, where)
        elif isinstance(value, float) and not math.isfinite(value):
            raise BuildError("{} 不接受非有限数值".format(where))
        cell.value = value
    else:
        raise BuildError("{} 不接受数组或嵌套数据".format(where))
    return 0


def bind_record(record, sheet, where):
    """先按声明的字段顺序绑定，再按输出 columns 选择；不在业务代码里手写位置索引。"""
    if "data_keys" in sheet:
        keys = sheet["data_keys"]
        if not isinstance(record, list) or len(record) != len(keys):
            raise BuildError("{} 必须是与 data_keys 对应的 {} 项数组，不自动补齐或截短".format(where, len(keys)))
        record = dict(zip(keys, record))
    elif not isinstance(record, dict):
        raise BuildError("{} 必须是具名字段 object；紧凑数组须先声明 data_keys".format(where))
    result = dict(sheet.get("defaults", {}))
    result.update(record)  # 只补缺省字段；显式 null / 0 / false / 空字符串均覆盖默认值。
    missing = [c["key"] for c in sheet["columns"] if c["key"] not in result]
    if missing:
        raise BuildError("{} 缺少字段 {}；未知值显式写 null，不移动其它字段补位".format(where, missing))
    return result


def validate_type(value, column, where):
    """验证声明类型，不推断字段语义、不自动转换编号或数字文本。"""
    expected = column.get("type")
    if expected is None or value is None:
        return
    matches = {
        "text": isinstance(value, str),
        "number": type(value) in (int, float),
        "boolean": type(value) is bool,
        "date": isinstance(value, dict) and set(value) == {"date"},
        "formula": isinstance(value, dict) and set(value) == {"formula"},
    }
    if not matches[expected]:
        raise BuildError("{} 字段 {} 要求 {}，实际为 {}；检查字段顺序，不自动转换".format(
            where, column["key"], expected, type(value).__name__))


def horizontal_alignment(cell):
    """根据已写入的单元格类型选择基础水平对齐方式。"""
    if cell.data_type == "f":
        return "general"  # 公式可能返回文本，交给表格引擎按结果类型展示。
    if isinstance(cell.value, (bool, date)):
        return "center"
    if isinstance(cell.value, (int, float)):
        return "right"
    return "left"


def publish_workbook(temp_path, destination, overwrite):
    """只发布完整文件；默认原子创建且不覆盖，完成后移除临时名称。"""
    if overwrite:
        os.replace(str(temp_path), str(destination))
    else:
        # 目标名称出现时已是完整工作簿；并发创建同名文件时 os.link 拒绝覆盖。
        # 文件系统不支持此操作时向调用方报告失败，不降级为可见的半成品复制。
        os.link(str(temp_path), str(destination))
        temp_path.unlink()


def append_data_file(ws, sheet, data_path, count, body_font):
    """校验并追加一个 JSONL 数据块，返回累计行数与新增公式数。"""
    formulas, nonempty = 0, False
    with data_path.open(encoding="utf-8-sig") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            nonempty = True
            where = "{}:{}".format(data_path, line_no)
            record = bind_record(parse_json(line, where), sheet, where)
            count += 1
            if count > 1048575:
                raise BuildError("{} 超过 Excel 行数限制".format(ws.title))
            for j, column in enumerate(sheet["columns"], 1):
                cell = ws.cell(count + 1, j)
                try:
                    validate_type(record[column["key"]], column, where)
                    formulas += assign(cell, record[column["key"]], where + "." + column["key"])
                except (ValueError, TypeError, OverflowError) as exc:
                    raise BuildError("{} 字段 {}：{}".format(where, column["key"], exc)) from exc
                cell.font = body_font
                cell.alignment = Alignment(horizontal=column.get("align", horizontal_alignment(cell)),
                                           vertical="center", wrap_text=True)
                if "number_format" in column:
                    cell.number_format = column["number_format"]
            ws.row_dimensions[count + 1].height = sheet["row_height"]
    if not nonempty and sheet.get("expected_rows") != 0:
        raise BuildError("数据块意外为空：{}；补齐该块；仅确认业务结果为零条时声明 expected_rows=0".format(data_path))
    return count, formulas


def build(spec_path, output, overwrite=False):
    """按配置创建工作簿，完整保存后原子发布并返回构建摘要。"""
    if OPENPYXL_IMPORT_ERROR is not None:
        raise OPENPYXL_IMPORT_ERROR
    spec, inputs = read_spec(spec_path)
    destination = output.resolve()
    if destination.suffix.lower() != ".xlsx":
        raise BuildError("output 必须是 .xlsx 文件")
    if destination in inputs or (destination.exists() and any(
            p.exists() and destination.samefile(p) for p in inputs)):
        raise BuildError("output 不能覆盖 spec 或数据块")
    if output.is_symlink() or (output.exists() and not overwrite):
        raise BuildError("输出已存在或是符号链接；换新路径，仅重建本次生成的文件时使用 --overwrite")
    wb = Workbook()
    wb.remove(wb.active)
    summaries, formulas = [], 0
    temp_path = None
    try:
        for sheet in spec["sheets"]:
            ws = wb.create_sheet(sheet["name"])
            columns = sheet["columns"]
            header_font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
            body_font = Font(name="微软雅黑", size=11)
            for j, column in enumerate(columns, 1):
                cell = ws.cell(1, j)
                assign(cell, column["title"], "{} 子表 {} 表头字段 {}".format(
                    spec_path, sheet["name"], column["key"]))
                cell.font = header_font
                cell.fill = PatternFill("solid", fgColor="3370FF")
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = Border(bottom=Side(style="thin", color="B8C7D9"))
                ws.column_dimensions[get_column_letter(j)].width = column["width"]
            ws.row_dimensions[1].height = 30
            count = 0
            for data_path in sheet["data_files"]:
                count, added_formulas = append_data_file(ws, sheet, data_path, count, body_font)
                formulas += added_formulas
            if sheet.get("expected_rows") is not None and count != sheet["expected_rows"]:
                raise BuildError("{} 记录数为 {}，要求 {}；按需求修正数据，不凑数或静默裁剪".format(
                    ws.title, count, sheet["expected_rows"]))
            ws.auto_filter.ref = "A1:{}{}".format(get_column_letter(len(columns)), count + 1)
            if sheet.get("freeze_header", False):
                ws.freeze_panes = "A2"
            summaries.append({"sheet_name": ws.title, "rows": count, "columns": len(columns)})
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".excel-build-", suffix=".xlsx", dir=str(destination.parent))
        os.close(fd)
        temp_path = Path(name)
        wb.save(str(temp_path))
        publish_workbook(temp_path, destination, overwrite)
        return {"status": "built", "output": str(destination), "sheets": summaries,
                "formula_cells": formulas, "formula_results_calculated": False}
    finally:
        wb.close()
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def main():
    """处理命令行参数，输出 JSON 回执并返回构建结果退出码。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true", help="仅重建本次生成的工作簿，不用于编辑用户原件")
    args = parser.parse_args()
    try:
        result = build(args.spec, args.output, args.overwrite)
    except (OSError, ValueError, TypeError, OverflowError, ImportError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        print("构建未完成。修复指定数据块或配置后重跑，已有输出不因输入错误被覆盖。"
              "缺少 openpyxl 时在同一 Python 环境安装；用户原件或模板请走原有编辑流程。", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
