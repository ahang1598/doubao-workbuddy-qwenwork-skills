#!/usr/bin/env python3
"""
统一命令行入口

自动发现 biz/ 下所有业务域，路由到对应的 cmd.py 执行。

用法：python3 scripts/cli.py <业务域> <动作> [--参数名=参数值]

示例：
  python3 scripts/cli.py product_search_helper search --filters='[{"code":"title","value":["垃圾袋"],"queryType":"contains_any"}]'
  python3 scripts/cli.py shop_info query
  python3 scripts/cli.py offer_info query --offer_id=894529405810
  python3 scripts/cli.py distribute_helper execute --app_key=6541416 --shop_code=65450009 --channel=douyin --offer_ids=983715805496
  python3 scripts/cli.py order_helper query
  python3 scripts/cli.py order_helper query --order_id=4502201509012068443
  python3 scripts/cli.py order_helper send --question="请尽快发货" --order_ids=4502201509012068443
  python3 scripts/cli.py knowledge_helper query --query="铺货流程"
  python3 scripts/cli.py knowledge_helper query --query="发货" --channel="抖音" --business="自动分销"
"""

import glob
import json
import os
import sys
import importlib

# Windows 默认 GBK 编码，强制 stdout/stderr 使用 UTF-8 避免中文输出报错
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def _find_project_root():
    """
    查找项目根目录（包含 scripts/biz/ 的目录）。

    兼容两种运行场景：
    1. 原地执行：python3 scripts/cli.py（__file__ 在 scripts/ 下）
    2. 复制执行：skill 运行时将 cli.py 复制到工作目录后执行
    """
    def _has_biz(path):
        return os.path.isdir(os.path.join(path, 'scripts', 'biz'))

    # 1. __file__ 基准（开发模式：cli.py 在 scripts/ 下，父目录即项目根）
    file_parent = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    if _has_biz(file_parent):
        return file_parent

    # 2. CWD 基准（从项目根目录执行）
    cwd = os.path.abspath(os.getcwd())
    if _has_biz(cwd):
        return cwd

    # 3. 从 CWD 向上搜索 skills 安装目录，定位本项目
    current = cwd
    for _ in range(10):
        for skills_name in ('.skills', 'skills'):
            skills_dir = os.path.join(current, skills_name)
            if os.path.isdir(skills_dir):
                for entry in os.listdir(skills_dir):
                    candidate = os.path.join(skills_dir, entry)
                    if _has_biz(candidate):
                        skill_md = os.path.join(candidate, 'SKILL.md')
                        if os.path.isfile(skill_md):
                            try:
                                with open(skill_md, 'r', encoding='utf-8') as f:
                                    if 'name: 1688-distribution' in f.read(500):
                                        return candidate
                            except Exception:
                                pass
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    # 4. AGENT_WORK_ROOT 环境变量
    agent_root = os.environ.get('AGENT_WORK_ROOT')
    if agent_root:
        for pattern in (
            os.path.join(agent_root, '.skills', '*'),
            os.path.join(agent_root, 'skills', '*'),
        ):
            for candidate in glob.glob(pattern):
                if _has_biz(candidate):
                    return candidate

    # fallback
    return file_parent


_PROJECT_ROOT = _find_project_root()
sys.path.insert(0, _PROJECT_ROOT)

BIZ_DIR = os.path.join(_PROJECT_ROOT, 'scripts', 'biz')


def discover_commands():
    """自动发现 biz/ 下所有包含 cmd.py 的子目录"""
    commands = {}
    if not os.path.isdir(BIZ_DIR):
        return commands
    for name in sorted(os.listdir(BIZ_DIR)):
        cmd_path = os.path.join(BIZ_DIR, name, 'cmd.py')
        if os.path.isfile(cmd_path):
            commands[name] = f"scripts.biz.{name}.cmd"
    return commands


def parse_args(args):
    """解析 --key=value 或 --key value 两种格式的参数"""
    kwargs = {}
    positional = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith('--'):
            if '=' in arg:
                # --key=value 格式
                key, value = arg[2:].split('=', 1)
                key = key.replace('-', '_')
                kwargs[key] = value
            else:
                key = arg[2:].replace('-', '_')
                # --key value 格式：下一个 token 不以 -- 开头则视为值
                if i + 1 < len(args) and not args[i + 1].startswith('--'):
                    kwargs[key] = args[i + 1]
                    i += 1
                else:
                    # 单独的 --flag 视为布尔 True
                    kwargs[key] = True
        else:
            positional.append(arg)
        i += 1
    return positional, kwargs


def main():
    commands = discover_commands()

    if len(sys.argv) < 2:
        print("用法：python3 scripts/cli.py <业务域|命令> <动作> [--参数]")
        print()
        print("可用业务域：")
        for name in commands:
            print(f"  - {name}")
        print()
        sys.exit(1)

    domain = sys.argv[1]

    if domain not in commands:
        print(f"❌ 未知业务域：{domain}")
        print(f"可用：{', '.join(commands.keys())}")
        sys.exit(1)

    if len(sys.argv) < 3:
        print(f"❌ 请指定动作")
        print(f"用法：python3 scripts/cli.py {domain} <动作> [--参数]")
        sys.exit(1)

    action = sys.argv[2]
    positional, kwargs = parse_args(sys.argv[3:])

    # 动态导入对应的 cmd 模块
    try:
        cmd_module = importlib.import_module(commands[domain])
    except ImportError as e:
        print(f"❌ 加载模块失败：{e}")
        sys.exit(1)

    # 查找并调用对应的动作函数
    handler = getattr(cmd_module, action, None)
    if handler is None or not callable(handler):
        print(f"❌ 未知动作：{domain}.{action}")
        available = [name for name in dir(cmd_module)
                     if not name.startswith('_') and callable(getattr(cmd_module, name))]
        if available:
            print(f"可用动作：{', '.join(available)}")
        sys.exit(1)

    try:
        handler(*positional, **kwargs)
    except TypeError as e:
        print(f"❌ 参数错误：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
