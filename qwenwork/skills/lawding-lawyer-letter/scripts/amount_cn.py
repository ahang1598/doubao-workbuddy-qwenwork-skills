# -*- coding: utf-8 -*-
"""人民币金额中文大写转换。

用于律师函中金额的规范表述，避免手工书写大写出错。
支持元、角、分（两位小数），最大到万亿级。

CLI:
    python3 amount_cn.py 258250        -> 贰拾伍万捌仟贰佰伍拾元整
    python3 amount_cn.py 1002.05       -> 壹仟零贰元零伍分

作为库:
    from amount_cn import to_cn_upper
    to_cn_upper(250000)  # '贰拾伍万元整'
"""
from decimal import Decimal, ROUND_HALF_UP
import sys

_DIGITS = "零壹贰叁肆伍陆柒捌玖"
# 每 4 位一节的节内单位
_UNITS = ["", "拾", "佰", "仟"]
# 节单位
_SEC_UNITS = ["", "万", "亿", "兆"]


def _four_digits_to_cn(seg: int) -> str:
    """把 0-9999 的整数转成中文（不含节单位），内部处理零。"""
    s = ""
    zero = False
    for i in range(3, -1, -1):
        d = (seg // (10 ** i)) % 10
        if d == 0:
            zero = True
        else:
            if zero and s:
                s += _DIGITS[0]
            s += _DIGITS[d] + _UNITS[i]
            zero = False
    return s


def _int_to_cn(n: int) -> str:
    if n == 0:
        return _DIGITS[0]
    segs = []
    while n > 0:
        segs.append(n % 10000)
        n //= 10000
    parts = []
    for idx in range(len(segs) - 1, -1, -1):
        seg = segs[idx]
        if seg == 0:
            # 记录一个零占位，稍后统一处理
            if parts and not parts[-1].endswith(_DIGITS[0]):
                parts.append(_DIGITS[0])
            continue
        seg_cn = _four_digits_to_cn(seg)
        # 若本节高位不足4位且前面已有更高节，需要补零（如 1,0001 -> 壹万零壹）
        if parts and seg < 1000:
            seg_cn = _DIGITS[0] + seg_cn if not seg_cn.startswith(_DIGITS[0]) else seg_cn
        parts.append(seg_cn + _SEC_UNITS[idx])
    result = "".join(parts)
    # 清理多余零
    while _DIGITS[0] * 2 in result:
        result = result.replace(_DIGITS[0] * 2, _DIGITS[0])
    result = result.rstrip(_DIGITS[0])
    return result or _DIGITS[0]


def to_cn_upper(amount) -> str:
    """将金额（int/float/str/Decimal）转为人民币中文大写。

    - 整数金额结尾用「元整」
    - 含角分时按「元/角/分」输出，无整数部分省略「元」前的零
    """
    d = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if d < 0:
        return "负" + to_cn_upper(-d)
    yuan = int(d)
    cents = int((d - yuan) * 100)  # 0-99
    jiao = cents // 10
    fen = cents % 10

    yuan_cn = _int_to_cn(yuan)
    if cents == 0:
        return f"{yuan_cn}元整"

    out = ""
    if yuan > 0:
        out += f"{yuan_cn}元"
    # 处理角分
    if jiao == 0 and fen > 0:
        # 元与分之间需要「零」
        if yuan > 0:
            out += _DIGITS[0]
        out += f"{_DIGITS[fen]}分"
    else:
        if jiao > 0:
            out += f"{_DIGITS[jiao]}角"
        if fen > 0:
            out += f"{_DIGITS[fen]}分"
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # 自测
        cases = {0: "零元整", 5: "伍元整", 250000: "贰拾伍万元整",
                 258250: "贰拾伍万捌仟贰佰伍拾元整", 1002.05: "壹仟零贰元零伍分",
                 100000000: "壹亿元整", 10001: "壹万零壹元整", 0.5: "伍角",
                 1234.56: "壹仟贰佰叁拾肆元伍角陆分"}
        ok = True
        for k, v in cases.items():
            got = to_cn_upper(k)
            flag = "OK " if got == v else "XX "
            if got != v:
                ok = False
            print(f"{flag}{k} -> {got}  (expect {v})")
        print("ALL PASS" if ok else "SOME FAILED")
    else:
        print(to_cn_upper(sys.argv[1]))
