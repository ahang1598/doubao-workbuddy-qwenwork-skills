"""定位 Playwright 所在的 node_modules。

验证器需要 Playwright，但它在不同机器上位置不同：Codex 运行时自带一份、
用户也可能全局装。硬编码某台机器的绝对路径会让这套测试一出本机就跑不起来，
所以按「显式指定 → 运行时自带 → node 自己找得到」的顺序解析。
"""
import os
import subprocess
from pathlib import Path


def node_modules():
    """返回可用的 node_modules 路径；找不到返回 None（由调用方决定怎么报错）。"""
    explicit = os.environ.get("CODEX_NODE_MODULES")
    if explicit and Path(explicit, "playwright").exists():
        return explicit

    # Codex 运行时自带的那份，目录名带版本号，用通配匹配
    for candidate in sorted(Path.home().glob(
            ".cache/codex-runtimes/*/dependencies/node/node_modules"), reverse=True):
        if (candidate / "playwright").exists():
            return str(candidate)

    # 最后问 node 自己：全局或项目里装过就能解析到
    try:
        resolved = subprocess.run(
            ["node", "-e", "process.stdout.write(require.resolve('playwright'))"],
            capture_output=True, text=True, timeout=15)
        if resolved.returncode == 0 and resolved.stdout.strip():
            for parent in Path(resolved.stdout.strip()).parents:
                if parent.name == "node_modules":
                    return str(parent)
    except Exception:
        pass
    return None


def env_with_playwright(base=None):
    """在环境变量里补上 CODEX_NODE_MODULES，供子进程里的验证器使用。"""
    env = dict(base if base is not None else os.environ)
    found = node_modules()
    if found:
        env["CODEX_NODE_MODULES"] = found
    return env
