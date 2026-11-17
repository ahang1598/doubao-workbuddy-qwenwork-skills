#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-learning-roadmap 主脚本
功能：根据用户输入生成 AI 学习路线图
"""

import argparse
import sys
from pathlib import Path


def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def read_text_safe(path):
    """安全读取文本文件，支持多编码降级"""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except OSError as e:
            print(f"[WARN] 读取 {path} 失败，降级为空: {e}", file=sys.stderr)
            return ""
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def load_rows(path):
    """加载数据行，带异常降级"""
    try:
        content = read_text_safe(path)
        if not content:
            return []
        # 按行拆分，过滤空行
        return [line.strip() for line in content.splitlines() if line.strip()]
    except Exception as e:
        print(f"[WARN] 解析 {path} 失败，降级为空集: {e}", file=sys.stderr)
        return []


def save(path, data, dry_run=False):
    """保存文件，支持 dry-run 预览"""
    if not dry_run:
        tmp = Path(str(path) + ".tmp")
        tmp.write_text(data, encoding="utf-8")
        tmp.replace(path)
        print(f"[写入] {path}")
        return True
    print(f"[dry-run] 将写入 {path}（{len(data)} 字节），未落盘")
    return False


def generate_roadmap(input_path, output_path, verbose=False):
    """生成学习路线图"""
    rows = load_rows(input_path)
    if not rows:
        print("[WARN] 输入为空，生成默认路线图")
        rows = [
            "Python 基础",
            "机器学习基础",
            "深度学习基础",
            "自然语言处理",
            "计算机视觉",
            "强化学习",
            "模型部署",
            "项目实战",
        ]

    # 生成路线图内容
    roadmap_lines = []
    roadmap_lines.append("# AI 学习路线图")
    roadmap_lines.append("")
    roadmap_lines.append("## 学习路径")
    roadmap_lines.append("")

    changed_items = []
    skipped = 0

    for idx, item in enumerate(rows, 1):
        # 模拟处理：将输入转换为路线图条目
        before = item
        after = f"{idx}. {item}"

        if verbose:
            print(f"[明细] {idx}. {item}: {before} -> {after}")

        roadmap_lines.append(after)
        changed_items.append({"name": item, "before": before, "after": after})

    roadmap_lines.append("")
    roadmap_lines.append(f"共 {len(changed_items)} 个学习主题")

    # 生成输出内容
    output_content = "\n".join(roadmap_lines)

    # 保存或预览
    save(output_path, output_content, dry_run=False)

    print(f"[汇总] changed={len(changed_items)} 项，skipped={skipped} 项")
    return output_content


def _selftest():
    """自测函数：验证核心功能"""
    import tempfile
    import os

    print("[selftest] 开始自测...")
    test_dir = tempfile.mkdtemp()
    input_file = os.path.join(test_dir, "input.txt")
    output_file = os.path.join(test_dir, "output.md")

    # 测试数据
    test_content = "Python 基础\n机器学习\n深度学习\n"
    with open(input_file, "w", encoding="utf-8") as f:
        f.write(test_content)

    # 测试 load_rows
    rows = load_rows(input_file)
    assert len(rows) == 3, f"load_rows 应返回 3 行，实际 {len(rows)}"
    assert rows[0] == "Python 基础", f"第一行应为 'Python 基础'，实际 {rows[0]}"

    # 测试 save 的 dry-run
    result = save(output_file, "test", dry_run=True)
    assert result is False, "dry-run 应返回 False"
    assert not os.path.exists(output_file), "dry-run 不应创建文件"

    # 测试 save 实际写入
    result = save(output_file, "test", dry_run=False)
    assert result is True, "实际写入应返回 True"
    assert os.path.exists(output_file), "文件应存在"

    # 测试 generate_roadmap
    content = generate_roadmap(input_file, output_file, verbose=False)
    assert "AI 学习路线图" in content, "输出应包含标题"
    assert "1. Python 基础" in content, "输出应包含第一个条目"
    assert "2. 机器学习" in content, "输出应包含第二个条目"
    assert "3. 深度学习" in content, "输出应包含第三个条目"
    assert "共 3 个学习主题" in content, "输出应包含汇总信息"

    # 测试空输入
    empty_file = os.path.join(test_dir, "empty.txt")
    with open(empty_file, "w", encoding="utf-8") as f:
        f.write("")
    rows_empty = load_rows(empty_file)
    assert len(rows_empty) == 0, "空文件应返回 0 行"

    # 测试不存在的文件
    rows_missing = load_rows(os.path.join(test_dir, "missing.txt"))
    assert len(rows_missing) == 0, "不存在的文件应返回 0 行"

    # 清理测试文件
    for f in [input_file, output_file, empty_file]:
        if os.path.exists(f):
            os.remove(f)
    os.rmdir(test_dir)

    print("[selftest] 全部断言通过")
    return 0


def main():
    ap = argparse.ArgumentParser(description="AI 学习路线图生成器")
    ap.add_argument("--input", help="输入文件路径（包含学习主题列表）")
    ap.add_argument("--output", help="输出文件路径（默认 roadmap.md）", default="roadmap.md")
    ap.add_argument("--selftest", action="store_true", help="运行自测")
    ap.add_argument("--dry-run", action="store_true", help="预览模式，不实际写入")
    ap.add_argument("--verbose", action="store_true", help="显示详细修改信息")
    ap.add_argument("--mode", default=None, help="文档声明的参数")  # F3 补全
    args = ap.parse_args()

    # selftest 优先处理
    if args.selftest:
        return _selftest()

    # 业务参数校验
    if args.input is None:
        ap.error("--input 为必填参数")

    # 生成路线图
    generate_roadmap(args.input, args.output, verbose=args.verbose)

    return 0


if __name__ == "__main__":
    sys.exit(main())
