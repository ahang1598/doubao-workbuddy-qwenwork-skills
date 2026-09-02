"""
预扫描 docx 文档，生成"可修订位置清单"。

用途：Redlining 修订工作流的前置步骤。AI 拿到清单后，
可以直接知道每段文本在 XML 中的行号和上下文，无需 grep document.xml。

行号与 utilities.py 的 get_node(line_number=...) 完全一致：
- 用相同的 line tracking parser（defusedxml.minidom.parse + _create_line_tracking_parser）
- <w:r> 元素的 parse_position[0] 即为起始行号
- 直接用此行号调用 get_node(line_number=N, contains="文本")

用法：
    python scripts/scan_revisions.py <docx_or_unpacked> [--output <report.md>]
"""
import sys
import os
import argparse
import re
import html
import defusedxml.minidom


def extract_text_from_element(elem):
    """递归提取元素内所有 <w:t> 文本"""
    texts = []
    # 用 childNodes 递归遍历，兼容 SAX parser 生成的 DOM
    def _walk(node):
        if node.nodeName == 'w:t':
            # 直接取 <w:t> 的所有 Text 子节点
            for child in node.childNodes:
                if child.nodeType == child.TEXT_NODE:
                    texts.append(child.nodeValue)
        else:
            for child in node.childNodes:
                _walk(child)
    _walk(elem)
    return ''.join(texts)


def _get_line_tracking_parser():
    """复用 utilities.py 的 line tracking parser，确保行号一致"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from scripts.utilities import _create_line_tracking_parser
    return _create_line_tracking_parser()


def scan_unpacked(unpacked_dir):
    """扫描已解包的文档目录，返回段落和 run 清单"""
    document_xml_path = os.path.join(unpacked_dir, 'word', 'document.xml')
    if not os.path.exists(document_xml_path):
        raise FileNotFoundError(f'找不到 word/document.xml: {document_xml_path}')

    # 用与 utilities.py 完全一致的 line tracking parser，确保行号一致
    parser = _get_line_tracking_parser()
    dom = defusedxml.minidom.parse(document_xml_path, parser)

    # 保留原始 XML 文本用于 <w:t> 行号映射
    with open(document_xml_path, 'rb') as f:
        xml_content = f.read().decode('utf-8')

    # 构建 <w:t> 文本 → 行号映射
    t_line_map = []
    for m in re.finditer(r'<w:t[^>]*>([^<]*)</w:t>', xml_content):
        line = xml_content[:m.start()].count('\n') + 1
        text = html.unescape(m.group(1))
        if text:
            t_line_map.append((line, text))

    # 辅助：获取元素直接子元素中指定标签的第一个
    def _first_child(parent, tagname):
        for child in parent.childNodes:
            if child.nodeType == child.ELEMENT_NODE and child.nodeName == tagname:
                return child
        return None

    paragraphs = []
    runs = []

    para_idx = 0

    for p in dom.getElementsByTagName('w:p'):
        para_idx += 1
        text = extract_text_from_element(p)
        if not text.strip():
            continue

        # 获取段落样式
        style_name = 'Normal'
        pPr = _first_child(p, 'w:pPr')
        if pPr is not None:
            pStyle = _first_child(pPr, 'w:pStyle')
            if pStyle is not None:
                style_name = pStyle.getAttribute('w:val') or 'Normal'

        # 找段落第一个 <w:t> 对应的行号
        para_line = None
        def _find_first_t_line(node):
            nonlocal para_line
            if node.nodeName == 'w:t':
                t_text = ''
                for child in node.childNodes:
                    if child.nodeType == child.TEXT_NODE:
                        t_text += child.nodeValue
                if t_text:
                    for line, txt in t_line_map:
                        if txt == t_text:
                            para_line = line
                            return True
                    if para_line is None:
                        for line, txt in t_line_map:
                            if t_text in txt or txt in t_text:
                                para_line = line
                                return True
                return False
            for child in node.childNodes:
                if child.nodeType == child.ELEMENT_NODE:
                    if _find_first_t_line(child):
                        return True
            return False
        _find_first_t_line(p)

        if para_line is None:
            para_line = 1

        paragraphs.append({
            'idx': para_idx,
            'text': text,
            'style': style_name,
            'line': para_line,
        })

        # 收集段落内的所有 run（直接子元素 w:r，避免嵌套 run 重复）
        run_idx = 0
        def _collect_runs(node):
            nonlocal run_idx
            for child in node.childNodes:
                if child.nodeType != child.ELEMENT_NODE:
                    continue
                if child.nodeName == 'w:r':
                    run_idx += 1
                    run_text = extract_text_from_element(child)
                    if run_text.strip():
                        parse_pos = getattr(child, 'parse_position', None)
                        run_r_line = parse_pos[0] if parse_pos else None
                        runs.append({
                            'para_idx': para_idx,
                            'run_idx': run_idx,
                            'text': run_text,
                            'line': run_r_line if run_r_line else para_line,
                        })
                # 不递归进入嵌套的 w:r（如修订标记内的 w:r）
                elif child.nodeName not in ('w:del', 'w:ins', 'w:moveFrom', 'w:moveTo'):
                    _collect_runs(child)
        _collect_runs(p)

    return paragraphs, runs


def _is_meaningful_text(text, min_length=4):
    """判断文本是否有修订价值（过滤纯编号、纯标点、单字等无意义内容）

    Args:
        text: 待判断的文本
        min_length: 最小有效长度（默认 4 字符），短于此的文本通常无独立修订价值
    """
    stripped = text.strip()
    if not stripped:
        return False
    # 纯标点
    if re.match(r'^[，。、；：？！,.;:?!()\(\)（）《》\[\]【】"\']+$', stripped):
        return False
    # 纯空格
    if re.match(r'^[\s　]+$', stripped):
        return False
    # 太短（如单字"年" "月" "：" "，" 等无独立修订价值）
    if len(stripped) < min_length:
        return False
    return True


def _is_meaningful_paragraph(p):
    """判断段落是否有修订价值"""
    text = p['text'].strip()
    if not text:
        return False
    # 跳过目录项（通常含 TOC 样式或前导制表符+页码）
    if 'TOC' in p['style'] or 'toc' in p['style']:
        return False
    # 跳过纯编号行（如 "第一章 投标人须知" 这种标题保留，但纯 "1." 跳过）
    return _is_meaningful_text(text)


def format_report(paragraphs, runs, source_name, filter_keyword=None, compact=True):
    """格式化为 markdown 报告

    Args:
        paragraphs: 段落列表
        runs: run 列表
        source_name: 源文件名
        filter_keyword: 可选关键词过滤（只返回含该词的段落/run）
        compact: True=紧凑模式（过滤无价值内容、截断长文本），False=完整模式
    """
    # 过滤
    if compact:
        paragraphs = [p for p in paragraphs if _is_meaningful_paragraph(p)]
        runs = [r for r in runs if _is_meaningful_text(r['text'])]

    if filter_keyword:
        paragraphs = [p for p in paragraphs if filter_keyword in p['text']]
        runs = [r for r in runs if filter_keyword in r['text']]

    lines = []
    lines.append('# 修订位置预扫描报告')
    lines.append(f'\n源文件: `{source_name}`')
    lines.append(f'段落总数: {len(paragraphs)} | run 总数: {len(runs)}')
    if filter_keyword:
        lines.append(f'（已按关键词 `{filter_keyword}` 过滤）')
    lines.append('')

    lines.append('---\n')
    lines.append('## 段落清单（含每段文本的 XML 行号）\n')
    lines.append('> 行号对应 `word/document.xml` 中 `<w:t>` 标签所在行\n')
    lines.append('| # | 行号 | 样式 | 文本（前40字） |')
    lines.append('|---|------|------|---------------|')
    for p in paragraphs:
        max_len = 40 if compact else 80
        text_preview = p['text'][:max_len].replace('|', '\\|').replace('\n', ' ')
        if len(p['text']) > max_len:
            text_preview += '...'
        lines.append(f"| {p['idx']} | {p['line']} | {p['style']} | {text_preview} |")

    lines.append('---\n')
    lines.append('## Run 级清单（用于 `get_node(tag="w:r", line_number=N, contains="...")` 精确定位）\n')
    lines.append('> `行号` 列可直接传给 `get_node(line_number=...)`\n')
    lines.append('| 行号 | 段# | run# | 文本 |')
    lines.append('|------|-----|-------|------|')
    for r in runs:
        # 紧凑模式：截断到 30 字
        max_len = 30 if compact else 60
        text_preview = r['text'][:max_len].replace('|', '\\|').replace('\n', ' ')
        lines.append(f"| {r['line']} | {r['para_idx']} | {r['run_idx']} | {text_preview} |")

    lines.append('\n---\n')
    lines.append('## 使用示例\n')
    lines.append('```python')
    lines.append('# 用行号精确定位（避免 Multiple nodes 错误）')
    if runs:
        sample = runs[0]
        text_escaped = sample['text'][:20].replace('"', '\\"')
        lines.append(f"node = editor.get_node(tag=\"w:r\", line_number={sample['line']}, contains=\"{text_escaped}\")")
    lines.append('```')

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='预扫描 docx/unpacked 生成修订位置清单')
    parser.add_argument('input', help='输入 docx 文件或解包后的目录')
    parser.add_argument('--output', '-o', help='输出报告路径（默认 stdout）')
    parser.add_argument('--filter', '-f', help='关键词过滤（只返回含该词的段落/run）')
    parser.add_argument('--full', action='store_true', help='完整模式（默认紧凑模式，过滤无价值内容）')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f'ERROR: 路径不存在: {args.input}', file=sys.stderr)
        sys.exit(1)

    # 自动判断是 docx 还是解包目录
    if os.path.isdir(args.input):
        paragraphs, runs = scan_unpacked(args.input)
        source_name = os.path.basename(args.input.rstrip(os.sep))
    else:
        # docx 文件：先解包到临时目录
        import tempfile
        import shutil
        import subprocess
        temp_dir = tempfile.mkdtemp(prefix='scan_')
        try:
            unpack_script = os.path.join(os.path.dirname(__file__), '..', 'ooxml', 'scripts', 'unpack.py')
            subprocess.run(
                [sys.executable, unpack_script, args.input, temp_dir],
                capture_output=True, check=True
            )
            paragraphs, runs = scan_unpacked(temp_dir)
            source_name = os.path.basename(args.input)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    report = format_report(
        paragraphs, runs, source_name,
        filter_keyword=args.filter,
        compact=not args.full
    )

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f'报告已生成: {args.output}', file=sys.stderr)
        print(f'段落: {len(paragraphs)} | run: {len(runs)}', file=sys.stderr)
    else:
        print(report)


if __name__ == '__main__':
    main()
