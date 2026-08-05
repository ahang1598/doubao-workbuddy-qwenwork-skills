# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
统计飞书文档「总字数」，对齐飞书官方字数统计规则，用于字数遵循校验。

飞书官方规则（总字数）：汉字 + 中文标点 + 英文单词 + 数字；英文标点、空格不计。
计数源：文档 raw_content（飞书已抽取的纯文本，标签已剥离）。
  ⚠️ raw_content 会包含 @文档 / @人 / 卡片等飞书「不计入字数」的嵌入内容文字。
     对「生成的散文」无影响（不含这些嵌入），与飞书一致；
     读取嵌入密集的已有文档会偏高，那不是本功能的目标场景。
说明：数字按「位」计（每个数字算 1，与飞书总字符数口径一致）；
     总字数含标题（飞书亦含标题）。

用法：
  # 给文档 token，自动取 raw_content 并计数
  uv run scripts/count_chars.py --doc <document_id>
  # 直接数一段文本（stdin / 文件）
  echo "文本" | uv run scripts/count_chars.py
  uv run scripts/count_chars.py --file draft.txt
  # 带目标校验（任选其一）：
  uv run scripts/count_chars.py --doc <id> --min 380 --max 420   # 区间 [x,y]
  uv run scripts/count_chars.py --doc <id> --min 100             # >=x（>x）
  uv run scripts/count_chars.py --doc <id> --max 100             # <=y（<y）
  uv run scripts/count_chars.py --doc <id> --approx 400          # x 左右 = ±10%

输出 JSON：{total_words, total_chars, target:{min,max}, verdict, gap}
  verdict: pass | under | over | none(未给目标)
  gap: 距区间还差多少（under/over 均为正数，pass=0）——告诉你要 +gap 或 -gap 字
"""
import sys
import re
import json
import argparse
import subprocess


def fetch_raw_content(doc_id, identity):
    cmd = ["lark-cli", "api", "GET",
           f"/open-apis/docx/v1/documents/{doc_id}/raw_content", "--as", identity]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit("未找到 lark-cli：请先安装/配置 lark-cli，或改用 --file / stdin 传入文本")
    if out.returncode != 0:
        sys.exit(f"取 raw_content 失败: {out.stderr or out.stdout}")
    try:
        return json.loads(out.stdout)["data"]["content"]
    except Exception as e:
        sys.exit(f"解析 raw_content 失败: {e}\n{out.stdout[:300]}")


def is_hanzi(ch):
    o = ord(ch)
    return (0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF
            or 0xF900 <= o <= 0xFAFF or 0x20000 <= o <= 0x2A6DF)


def is_zh_punct(ch):
    o = ord(ch)
    # CJK 符号与标点 / 兼容形式
    if 0x3000 <= o <= 0x303F or 0xFE10 <= o <= 0xFE1F or 0xFE30 <= o <= 0xFE4F:
        return True
    # 全角 ASCII 标点（排除全角数字 FF10-FF19、全角字母 FF21-FF3A / FF41-FF5A）
    if (0xFF01 <= o <= 0xFF0F or 0xFF1A <= o <= 0xFF20
            or 0xFF3B <= o <= 0xFF40 or 0xFF5B <= o <= 0xFF65
            or 0xFFE0 <= o <= 0xFFEE):   # 全角货币 ￥￡￠ 等
        return True
    return ch in "·—…“”‘’"


def count(text):
    hanzi = sum(1 for ch in text if is_hanzi(ch))
    zh_punct = sum(1 for ch in text if is_zh_punct(ch))
    en_words = len(re.findall(r"[A-Za-zÀ-ÿĀ-ɏḀ-ỿ]+", text))
    digits = len(re.findall(r"[0-9０-９]", text))   # 数字按位计
    total_words = hanzi + zh_punct + en_words + digits
    # 总字符数 = 所有非空白、非控制字符（仅供参考）
    total_chars = sum(1 for ch in text if (not ch.isspace()) and ord(ch) >= 0x20)
    return total_words, total_chars


def judge(words, mn, mx):
    if mn is None and mx is None:
        return "none", 0
    if mn is not None and words < mn:
        return "under", mn - words
    if mx is not None and words > mx:
        return "over", words - mx
    return "pass", 0


def main():
    ap = argparse.ArgumentParser(description="飞书文档总字数统计与字数遵循校验")
    ap.add_argument("--doc", help="文档 document_id（自动取 raw_content）")
    ap.add_argument("--file", help="从文件读取文本")
    ap.add_argument("--as", dest="identity", default="user", help="身份：user(默认)|bot|auto")
    ap.add_argument("--min", type=int, help="字数下限（>=x）")
    ap.add_argument("--max", type=int, help="字数上限（<=y）")
    ap.add_argument("--approx", type=int, help="x 左右：自动展开为 [round(0.9x), round(1.1x)]")
    args = ap.parse_args()

    if args.doc:
        text = fetch_raw_content(args.doc, args.identity)
    elif args.file:
        try:
            text = open(args.file, encoding="utf-8").read()
        except OSError as e:
            sys.exit(f"读取文件失败: {e}")
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        ap.error("需提供 --doc / --file 或从 stdin 传入文本")

    mn, mx = args.min, args.max
    if args.approx is not None:
        mn, mx = round(args.approx * 0.9), round(args.approx * 1.1)

    total_words, total_chars = count(text)
    verdict, gap = judge(total_words, mn, mx)

    print(json.dumps({
        "total_words": total_words,
        "total_chars": total_chars,
        "target": {"min": mn, "max": mx},
        "verdict": verdict,
        "gap": gap,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
