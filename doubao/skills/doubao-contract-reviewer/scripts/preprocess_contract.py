# -*- coding: utf-8 -*-
"""
preprocess_contract.py —— 合同审查前置预处理脚本

目的:
- 检测 docx 是否含 Word Track Changes 修订痕迹
- 若有,按"接受全部修订"的语义重建段落可见文本(仅内存,不落盘 clean.docx)
- 自动备份原文档为 *_backup_with_revisions.docx,供回溯
- 输出 clean_text.json 作为后续审查的唯一文本来源

【为什么需要这个脚本】
  python-docx 的 paragraph.text 会把 <w:ins> 的内容包含进来,
  但会把 <w:del>/<w:delText> 也包含(或干脆忽略),得到的是"半拉子视图"。
  审查基于这种视图 → 看到留空、【0】%、缺字符 → 触发错误审查建议。
  直接按"接受修订后"的语义重建文本,可避免这一陷阱。

【用法】
  python3 preprocess_contract.py <contract.docx> [--out clean_text.json]

【输出 JSON 结构】
{
  "has_revisions": true,
  "revision_count": 36,
  "backup_file": "contract_backup_with_revisions.docx",  // 仅当 has_revisions=true
  "paragraphs": [
    {"idx": 0, "text": "货物采购合同", "has_revision": false},
    {"idx": 44, "text": "(1)预付款:合同签订后【3】个工作日内,甲方向乙方支付合同总价款的【80】%作为预付款", "has_revision": true},
    ...
  ],
  "notes": "审查必须基于本文件的 paragraphs[].text,不要使用 python-docx 的 paragraph.text"
}

【失败降级】
  - 非标准 docx / 无 document.xml → exit 2,输出错误信息
  - XML 解析异常 → exit 3
  - 非修订模式 → exit 0,has_revisions=false,paragraphs 照常输出
"""
import json
import os
import shutil
import sys
import zipfile
from xml.etree import ElementTree as ET

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{" + W_NS + "}"

# 需要检测的修订标记
REVISION_TAGS = {"ins", "del", "delText", "rPrChange", "pPrChange",
                 "sectPrChange", "tblPrChange", "tcPrChange", "trPrChange",
                 "moveFrom", "moveTo", "cellIns", "cellDel", "cellMerge"}


def _tag(elem):
    """Return local tag name without namespace."""
    t = elem.tag
    if "}" in t:
        return t.split("}", 1)[1]
    return t


def paragraph_accepted_text(p_elem):
    """
    重建一个段落"接受全部修订后"的可见文本。
    规则:
      - <w:ins> 子树:保留内容(剥离 ins 包装,等价于接受插入)
      - <w:del> 子树:整块跳过(等价于接受删除)
      - <w:delText>:跳过(仅在 del 内出现,但也做防御性处理)
      - <w:moveFrom>:整块跳过(移动源,等价于接受删除)
      - <w:moveTo>:保留内容(移动目标)
      - <w:t>:正常取 text
    """
    parts = []

    def walk(node):
        tag = _tag(node)
        # 直接跳过的子树
        if tag in ("del", "moveFrom", "delText"):
            return
        # 格式变更标记(不影响文本内容),跳过自身但不递归
        if tag in ("rPrChange", "pPrChange", "sectPrChange", "tblPrChange",
                   "tcPrChange", "trPrChange"):
            return
        # 正常取文本
        if tag == "t" and node.text:
            parts.append(node.text)
            return  # w:t 是叶节点
        # 其余节点递归(包含 ins/moveTo/r/p/body 等)
        for child in list(node):
            walk(child)

    walk(p_elem)
    return "".join(parts)


def paragraph_has_revision(p_elem):
    """检测段落是否包含任一修订标记。"""
    for node in p_elem.iter():
        if _tag(node) in REVISION_TAGS:
            return True
    return False


def count_revisions(root):
    """统计文档内所有修订标记总数(不含 rPrChange/pPrChange 等格式修订)。"""
    # 只数真正的"内容修订":ins / del / moveFrom / moveTo
    content_tags = {"ins", "del", "moveFrom", "moveTo"}
    count = 0
    for node in root.iter():
        if _tag(node) in content_tags:
            count += 1
    return count


def extract_document_xml(docx_path):
    """从 docx zip 包中读取 word/document.xml 的 bytes。"""
    with zipfile.ZipFile(docx_path) as z:
        try:
            with z.open("word/document.xml") as f:
                return f.read()
        except KeyError:
            raise FileNotFoundError("word/document.xml not found in docx")


def backup_original(docx_path):
    """备份原 docx 为 *_backup_with_revisions.docx,返回备份路径。"""
    base, ext = os.path.splitext(docx_path)
    backup_path = f"{base}_backup_with_revisions{ext}"
    # 若已存在备份,不覆盖(避免多次运行丢失最早版本)
    if not os.path.exists(backup_path):
        shutil.copy2(docx_path, backup_path)
    return backup_path


def preprocess(docx_path, out_json):
    """主流程。"""
    if not os.path.isfile(docx_path):
        print(f"[ERROR] File not found: {docx_path}", file=sys.stderr)
        sys.exit(2)

    try:
        xml_bytes = extract_document_xml(docx_path)
    except (zipfile.BadZipFile, FileNotFoundError) as e:
        print(f"[ERROR] Cannot read document.xml: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f"[ERROR] XML parse error: {e}", file=sys.stderr)
        sys.exit(3)

    # 检测修订 + 计数
    revision_count = count_revisions(root)
    has_revisions = revision_count > 0

    # 段落遍历
    paragraphs_out = []
    for idx, p in enumerate(root.iter(f"{W}p")):
        text = paragraph_accepted_text(p)
        has_rev = paragraph_has_revision(p) if has_revisions else False
        # 仅跳过完全空白段落,否则按原顺序保留
        if text.strip() or has_rev:
            paragraphs_out.append({
                "idx": idx,
                "text": text,
                "has_revision": has_rev,
            })

    result = {
        "has_revisions": has_revisions,
        "revision_count": revision_count,
        "paragraph_count": len(paragraphs_out),
        # 读取契约:clean_text.json 是审查的唯一文本来源,必须一次性完整读入。
        # 严禁对本文件做分块/翻页读取——历史上分块读时若每次 offset 从 0 起算,
        # 会把已读段落反复塞进上下文,造成重复累计、上下文膨胀、审查变慢。
        # 为把这条从"软约束"变成"代码层保障",请统一用 read_clean_text.py 读取:
        # 它默认一次性吐全文;确需分片时游标由脚本打印,调用方无需自算 offset。
        "read_hint": "READ_ONCE_FULL: 一次性完整读取本文件,禁止分块/翻页;paragraphs 已是全文。推荐用 `python3 scripts/read_clean_text.py <本文件>` 读取(默认一次吐全文;文件极大被工具层强制截断时用 --limit,游标由脚本打印,切勿自行把 offset 重置为 0)。",
        "paragraphs": paragraphs_out,
        "notes": (
            "审查请基于本文件的 paragraphs[].text,不要使用 python-docx 的 paragraph.text。"
            "本文本已按'接受全部修订'的语义重建:w:ins 内容保留、w:del 跳过。"
            if has_revisions
            else "本文档无修订痕迹,paragraphs[].text 等价于 python-docx 的 paragraph.text。"
        ),
    }

    if has_revisions:
        backup_path = backup_original(docx_path)
        result["backup_file"] = backup_path

    # 紧凑写出(去掉 indent 缩进与多余空格),显著压小文件体积,
    # 降低上层工具对大 JSON 做分块读取的概率;不影响机器解析。
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))

    # 人类可读的运行信息打印到 stderr,避免干扰管道
    print(f"[OK] has_revisions={has_revisions}, revision_count={revision_count}, "
          f"paragraphs={len(paragraphs_out)} -> {out_json}", file=sys.stderr)
    if has_revisions:
        print(f"[OK] Backup created: {result['backup_file']}", file=sys.stderr)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    docx_path = args[0]
    out_json = "clean_text.json"
    if "--out" in args:
        out_json = args[args.index("--out") + 1]

    preprocess(docx_path, out_json)


if __name__ == "__main__":
    main()
