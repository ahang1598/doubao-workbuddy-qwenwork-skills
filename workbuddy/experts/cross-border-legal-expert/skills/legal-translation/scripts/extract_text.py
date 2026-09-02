# © 深圳市法大大网络科技有限公司 版权所有
"""
提取 .docx 文件的全部文本内容（用于预分析阶段）。
用法: python extract_text.py <docx文件路径>
输出: 将全文文本打印到 stdout。

每行带 [L编号] 前缀，方便模型引用具体段落。
段落与表格按文档实际顺序交错输出（而非表格全部放在最后）。
"""
import sys
from pathlib import Path

try:
    from docx import Document
except ImportError:
    print("错误: 需要安装 python-docx (pip install python-docx)", file=sys.stderr)
    sys.exit(1)

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def _para_text(elem) -> str:
    """从段落 XML 元素中拼接所有 run 文本。"""
    return ''.join(t.text or '' for t in elem.iter(f'{W}t')).strip()


def _table_rows(elem):
    """从表格 XML 元素中逐行提取单元格文本，跳过空行。"""
    for tr in elem.findall(f'.//{W}tr'):
        cells = []
        for tc in tr.findall(f'{W}tc'):
            cell_text = ''.join(t.text or '' for t in tc.iter(f'{W}t')).strip()
            if cell_text:
                cells.append(cell_text)
        if cells:
            yield ' | '.join(cells)


def extract(docx_path: str) -> str:
    doc = Document(docx_path)
    lines = []
    line_idx = 0

    for child in doc.element.body:
        tag = child.tag

        if tag == f'{W}p':
            text = _para_text(child)
            if text:
                line_idx += 1
                lines.append(f"[L{line_idx}] {text}")

        elif tag == f'{W}tbl':
            for row_text in _table_rows(child):
                line_idx += 1
                lines.append(f"[L{line_idx}] {row_text}")

    return '\n'.join(lines)


def main():
    if len(sys.argv) < 2:
        print("用法: python extract_text.py <docx文件路径>", file=sys.stderr)
        sys.exit(1)

    docx_path = Path(sys.argv[1]).resolve()
    if not docx_path.exists():
        print(f"错误: 文件不存在 {docx_path}", file=sys.stderr)
        sys.exit(1)

    print(extract(str(docx_path)))


if __name__ == "__main__":
    main()
