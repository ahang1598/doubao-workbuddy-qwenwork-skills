#!/usr/bin/env python3
"""
跨平台 stdout 保存工具：替代 shell 重定向 `>` 和 `tee`

用法：
    <command> | python3 scripts/save_stdout.py <output_file>

示例：
    <输出 JSON 的检索命令> | python3 scripts/save_stdout.py ./tmp/cases_page1.json

    printf '%s\n' "保存的内容" \
        | python3 scripts/save_stdout.py ./tmp/query.txt

适用场景：
    当 shell 重定向（>、>>）被禁止时，使用本脚本通过管道保存命令输出。
    跨平台兼容（macOS / Linux / Windows CMD / PowerShell / Git Bash）。
    案例检索连接器的返回 JSON 也可由执行者直接写入分页文件，不必经过本脚本。
"""
import sys
import pathlib


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        # 无参数属误用（退出码 1）；显式请求帮助属正常（退出码 0）
        sys.exit(0 if len(sys.argv) >= 2 else 1)

    output_file = pathlib.Path(sys.argv[1])
    # 确保父目录存在
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # 从 stdin 读取并写入文件（使用二进制模式以支持任意内容，包括 JSON）
    data = sys.stdin.buffer.read()
    output_file.write_bytes(data)


if __name__ == '__main__':
    main()
