#!/usr/bin/env python3
"""
amount_conversion.py — 大写金额转数值 + 大小写交叉验证

CLI:
  python amount_conversion.py --input '<JSON>'
  python amount_conversion.py --input-file <path/to/input.json>

入参 JSON:
  { "upper": "壹万贰仟叁佰肆拾伍元捌角柒分", "lower": "12345.87" }

出参 JSON (stdout):
  {
    "success": true,
    "value": 12345.87,          # 元(float, 2 位小数)
    "value_cents": 1234587,     # 分(int) —— Step 6 list_pending_tickets 的 amount 直接用这个
    "unit": "元",
    "cross_validated": true,
    "warnings": []
  }

说明:
  - `value_cents` 是给 Step 6 直接用的"分"整数, Skill 侧 MUST NOT 自己再做 *100 换算
  - 无 `upper` 但有 `lower` 时会降级为"仅小写", 返回 cross_validated=null + warning
"""
import argparse
import json
import re
import sys
from decimal import Decimal, ROUND_HALF_UP

# ---------------------------------------------------------------- 字符表

DIGITS = {
    "零": 0, "〇": 0, "○": 0, "0": 0,
    "壹": 1, "一": 1, "1": 1,
    "贰": 2, "貳": 2, "二": 2, "两": 2, "兩": 2, "2": 2,
    "叁": 3, "參": 3, "参": 3, "三": 3, "3": 3,
    "肆": 4, "四": 4, "4": 4,
    "伍": 5, "五": 5, "5": 5,
    "陆": 6, "陸": 6, "六": 6, "6": 6,
    "柒": 7, "七": 7, "7": 7,
    "捌": 8, "八": 8, "8": 8,
    "玖": 9, "九": 9, "9": 9,
}

SMALL_UNITS = {"拾": 10, "十": 10, "佰": 100, "百": 100, "仟": 1000, "千": 1000}
BIG_UNITS = {"万": 10 ** 4, "萬": 10 ** 4, "亿": 10 ** 8, "億": 10 ** 8}

YUAN_CHARS = "元圆圓"
JIAO_CHARS = "角毛"
FEN_CHARS = "分"
# 结尾的"整/正"以及各类空白、货币符号、分隔符统一剔除
NOISE_PATTERN = re.compile(r"[\s,，、:：¥￥$人民币RMBrmb]")
TAIL_PATTERN = re.compile(r"[整正]+$")

PURE_NUMBER_PATTERN = re.compile(r"^\d+(\.\d+)?$")


# ---------------------------------------------------------------- 核心算法


def _parse_int_section(text: str) -> int:
    """解析中文大写的整数部分(不含角分)。"""
    total = 0
    section = 0
    num = None

    for ch in text:
        if ch in DIGITS:
            num = DIGITS[ch]
        elif ch in SMALL_UNITS:
            # "拾伍" = 15 (拾 前面无数字时视为 1)
            section += (num if num else 1) * SMALL_UNITS[ch]
            num = None
        elif ch in BIG_UNITS:
            unit = BIG_UNITS[ch]
            if num is not None:
                section += num
                num = None
            if unit == 10 ** 8:
                total = (total + section) * unit
                section = 0
            else:  # 万
                total += section * unit
                section = 0
        else:
            raise ValueError(f"无法识别的大写金额字符: {ch!r}")

    if num is not None:
        section += num
    return total + section


def _parse_decimal_part(text: str) -> int:
    """解析角/分部分, 返回"分"的整数值(0-99)。"""
    cents = 0
    matched_any = False

    jiao = re.search(r"([%s])[%s]" % ("".join(DIGITS.keys()), JIAO_CHARS), text)
    if jiao:
        cents += DIGITS[jiao.group(1)] * 10
        matched_any = True

    fen = re.search(r"([%s])[%s]" % ("".join(DIGITS.keys()), FEN_CHARS), text)
    if fen:
        cents += DIGITS[fen.group(1)]
        matched_any = True

    if not matched_any:
        leftover = TAIL_PATTERN.sub("", text)
        leftover = re.sub(r"[零〇○]", "", leftover)
        if leftover:
            raise ValueError(f"无法识别的角分部分: {text!r}")

    return cents


def convert_upper_to_cents(upper: str) -> int:
    """将中文大写金额转为"分"的整数。

    覆盖场景:
      "壹万元整"                     → 1000000
      "壹万贰仟叁佰肆拾伍元捌角柒分" → 1234587
      "壹佰零陆元"→ 10600
      "贰仟零元整"                   → 200000
      "壹角伍分"                     → 15
      "壹亿元整"                     → 10000000000
      "叁佰叁拾元整"                 → 33000
    """
    if not isinstance(upper, str):
        raise ValueError("upper 必须是字符串")

    text = NOISE_PATTERN.sub("", upper)
    text = TAIL_PATTERN.sub("", text)
    if not text:
        raise ValueError("大写金额为空")

    # 容错: 传进来的其实是阿拉伯数字
    if PURE_NUMBER_PATTERN.match(text):
        return int(
            (Decimal(text) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )

    yuan_pos = -1
    for idx, ch in enumerate(text):
        if ch in YUAN_CHARS:
            yuan_pos = idx
            break

    if yuan_pos >= 0:
        int_part = text[:yuan_pos]
        dec_part = text[yuan_pos + 1:]
    else:
        # 无"元": 要么纯角分("壹角伍分"), 要么缺字的整数
        if any(c in JIAO_CHARS or c in FEN_CHARS for c in text):
            int_part = ""
            dec_part = text
        else:
            int_part = text
            dec_part = ""

    yuan = _parse_int_section(int_part) if int_part else 0
    cents = _parse_decimal_part(dec_part) if dec_part else 0
    return yuan * 100 + cents


def convert_upper_to_number(upper: str) -> float:
    """兼容旧签名: 返回以元为单位的 float。"""
    return round(convert_upper_to_cents(upper) / 100.0, 2)


def _parse_lower(lower) -> int:
    """把小写金额解析成"分"的整数。"""
    if isinstance(lower, (int, float)):
        return int(
            (Decimal(str(lower)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )
    text = NOISE_PATTERN.sub("", str(lower))
    text = re.sub(r"^[（(]?小写[）)]?[:：]?", "", text)
    text = text.replace("元", "")
    if not PURE_NUMBER_PATTERN.match(text):
        raise ValueError(f"小写金额格式无法解析: {lower!r}")
    return int((Decimal(text) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


# ---------------------------------------------------------------- 编排


def process(input_data: dict) -> dict:
    upper = input_data.get("upper")
    lower = input_data.get("lower")
    warnings = []

    if not upper and lower in (None, ""):
        return {
            "success": False,
            "error": "缺少大写金额字段 (upper), 且无小写金额可降级",
            "input": input_data,
        }

    cents = None
    if upper:
        try:
            cents = convert_upper_to_cents(upper)
        except Exception as e:  # noqa: BLE001
            if lower in (None, ""):
                return {
                    "success": False,
                    "error": f"无法解析大写金额: {e}",
                    "input": input_data,
                }
            warnings.append(f"大写金额解析失败({e}), 降级为仅使用小写金额, 金额识别存疑")
    else:
        warnings.append("未提供大写金额, 降级为仅使用小写金额, 金额识别存疑")

    lower_cents = None
    if lower not in (None, ""):
        try:
            lower_cents = _parse_lower(lower)
        except ValueError as e:
            warnings.append(str(e))

    cross_validated = None
    if cents is not None and lower_cents is not None:
        cross_validated = cents == lower_cents
        if not cross_validated:
            warnings.append(
                "金额识别存疑: 大写=%.2f 元, 小写=%.2f 元"
                % (cents / 100.0, lower_cents / 100.0)
            )

    if cents is None:
        if lower_cents is None:
            return {
                "success": False,
                "error": "大写与小写金额均无法解析",
                "input": input_data,
            }
        cents = lower_cents
        source = "lower_only"
    elif cross_validated is False:
        source = "upper_preferred_conflict"
    elif cross_validated is True:
        source = "cross_validated"
    else:
        source = "upper_only"

    return {
        "success": True,
        "value": round(cents / 100.0, 2),
        "value_cents": cents,
        "unit": "元",
        "amount_source": source,
        "cross_validated": cross_validated,
        "warnings": warnings,
    }


def _load_input(args) -> dict:
    if args.input_file:
        with open(args.input_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(args.input)


def main():
    # ⚠️ Windows 实测: stdout 为管道时用 locale 编码(GBK), 中文 JSON 会写成 GBK 字节,
    #    UTF-8 读取方直接 UnicodeDecodeError。大写金额原文含中文, 必须显式改 UTF-8。
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="JSON 格式的入参")
    parser.add_argument("--input-file", dest="input_file", help="入参 JSON 文件路径")
    args = parser.parse_args()

    if not args.input and not args.input_file:
        print(
            json.dumps({"success": False, "error": "必须提供 --input 或 --input-file"}),
            flush=True,
        )
        sys.exit(1)

    try:
        input_data = _load_input(args)
    except (json.JSONDecodeError, OSError) as e:
        print(
            json.dumps({"success": False, "error": f"入参非合法 JSON: {e}"}, ensure_ascii=False),
            flush=True,
        )
        sys.exit(1)

    result = process(input_data)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
