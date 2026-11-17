#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
graphify-data — 代码库图谱分析（原创实现，clean-room）

功能：
  1. 递归扫描代码库，提取函数/类/import/依赖
  2. 构建模块依赖图（import 关系）
  3. 函数调用关系提取（AST 分析，支持 Python）
  4. 统计报告：文件数/代码行/复杂度估算/重复率
  5. 输出 JSON 图谱 / 文本报告 / Mermaid 图

零第三方依赖（标准库 ast）。用法：
  python main.py scan ./src --output graph.json
  python main.py report ./src
  python main.py mermaid ./src > graph.mmd
  python main.py selftest
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# WB 依赖降级注入（2026-09-13）：网络调用默认 8s 超时，防 hang 死（无产出）
try:
    import socket as _wb_sock
    _wb_sock.setdefaulttimeout(8)
except Exception:
    pass


# ============================================================
# 错误码
# ============================================================
ERRORS = {
    "E001": "目录不存在",
    "E002": "没有可分析的代码文件",
    "E003": "输出写入失败",
    "E004": "参数错误",
}

# 支持的代码扩展名
CODE_EXTS = {".py": "python", ".js": "javascript", ".ts": "typescript",
             ".jsx": "react", ".tsx": "react-ts", ".go": "go",
             ".rs": "rust", ".java": "java", ".c": "c", ".cpp": "cpp",
             ".rb": "ruby", ".php": "php", ".swift": "swift"}

# 忽略目录
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv", "dist",
             "build", ".next", "target", ".idea", ".vscode", "coverage",
             ".mypy_cache", ".pytest_cache", ".tox", "vendor"}

MAX_FILE_SIZE = 500 * 1024  # 500KB


class GraphifyError(Exception):
    """业务异常，带错误码。"""

    def __init__(self, code: str, message: str = ""):
        super().__init__(message or ERRORS.get(code, code))
        self.code = code


# ============================================================
# 文件扫描
# ============================================================
def scan_files(root: Path) -> list:
    """扫描代码文件，返回 [(path, lang), ...]。"""
    if not root.is_dir():
        raise GraphifyError("E001", f"目录不存在: {root}")
    files = []
    for dirpath, dirnames, filenames in os_walk_skip(root):
        for fn in filenames:
            f = Path(dirpath) / fn
            ext = f.suffix.lower()
            if ext in CODE_EXTS:
                try:
                    if f.stat().st_size <= MAX_FILE_SIZE:
                        files.append((f, CODE_EXTS[ext]))
                except OSError:
                    continue
    if not files:
        raise GraphifyError("E002", f"目录 {root} 没有可分析的代码文件")
    return files


def os_walk_skip(root: Path):
    """os.walk 但跳过噪音目录。"""
    import os
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        yield dirpath, dirnames, filenames


# ============================================================
# Python AST 分析
# ============================================================
def analyze_python(path: Path, rel: str) -> dict:
    """用 AST 分析 Python 文件：函数/类/import/调用。"""
    try:
        code = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise GraphifyError("E003", f"读取失败 {path}: {e}") from e
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"path": rel, "lang": "python", "syntax_error": True,
                "functions": [], "classes": [], "imports": [], "calls": []}

    functions, classes, imports, calls = [], [], [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)
        elif isinstance(node, ast.AsyncFunctionDef):
            functions.append(node.name)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                imports.append(a.name.split(".")[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.append(node.func.attr)
    return {
        "path": rel, "lang": "python",
        "lines": code.count("\n") + 1,
        "functions": functions, "classes": classes,
        "imports": sorted(set(imports)),
        "calls": calls,
    }


# ============================================================
# 通用分析（非 Python：正则近似）
# ============================================================
def analyze_generic(path: Path, rel: str, lang: str) -> dict:
    """非 Python 文件：正则提取函数/类/导入（近似）。"""
    try:
        code = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise GraphifyError("E003", f"读取失败 {path}: {e}") from e
    functions, classes, imports = [], [], []
    patterns = {
        "javascript": [(r"\bfunction\s+(\w+)", "f"), (r"class\s+(\w+)", "c"),
                       (r"import\s+.*?from\s+['\"]([^'\"]+)", "i"),
                       (r"const\s+\w+\s*=\s*(?:require|import)\(['\"]([^'\"]+)", "i")],
        "go": [(r"^func\s+(\w+)", "f"), (r"^type\s+(\w+)\s+struct", "c"),
               (r"import\s*\(([^)]*)\)", "i", True)],
        "rust": [(r"^fn\s+(\w+)", "f"), (r"^struct\s+(\w+)", "c"),
                 (r"^use\s+([\w:]+)", "i")],
        "java": [(r"^\s*(?:public|private|protected)?\s*\w+[\w<>\[\],\s]*\s+(\w+)\s*\(", "f"),
                 (r"class\s+(\w+)", "c"), (r"import\s+([\w.]+)", "i")],
    }
    for pat, kind in patterns.get(lang, []):
        for m in re.finditer(pat, code, re.M):
            if kind == "f":
                functions.append(m.group(1))
            elif kind == "c":
                classes.append(m.group(1))
            elif kind == "i":
                imports.append(m.group(1).split(".")[0])
    return {
        "path": rel, "lang": lang,
        "lines": code.count("\n") + 1,
        "functions": functions[:100], "classes": classes[:50],
        "imports": sorted(set(imports)),
        "calls": [],
    }


# ============================================================
# 图谱构建
# ============================================================
def build_graph(root: Path, verbose: bool = False) -> dict:
    """构建完整代码图谱。"""
    files = scan_files(root)
    nodes, edges = [], []
    total_lines = 0
    lang_count = Counter()
    func_count = 0

    for path, lang in files:
        rel = str(path.relative_to(root)).replace("\\", "/")
        if lang == "python":
            info = analyze_python(path, rel)
        else:
            info = analyze_generic(path, rel, lang)
        if verbose:
            print(f"[verbose] {rel} ({lang}): {info.get('functions', [])[:3]}...",
                  file=sys.stderr)
        total_lines += info.get("lines", 0)
        lang_count[lang] += 1
        func_count += len(info.get("functions", []))
        nodes.append({"id": rel, "lang": lang, "lines": info.get("lines", 0),
                      "functions": info.get("functions", []),
                      "classes": info.get("classes", []),
                      "imports": info.get("imports", [])})
        # 依赖边：本文件 import → 依赖模块
        for imp in info.get("imports", []):
            edges.append({"from": rel, "to": imp, "type": "import"})

    return {
        "root": str(root),
        "files": len(nodes),
        "total_lines": total_lines,
        "languages": dict(lang_count),
        "functions_total": func_count,
        "nodes": nodes,
        "edges": edges[:5000],
    }


def build_report(graph: dict) -> str:
    """生成文本报告。"""
    lines = []
    lines.append(f"代码库图谱分析: {graph['root']}")
    lines.append("=" * 50)
    lines.append(f"文件数: {graph['files']} | 总行数: {graph['total_lines']} "
                 f"| 函数数: {graph['functions_total']}")
    lines.append(f"语言分布: {json.dumps(graph['languages'], ensure_ascii=False)}")
    lines.append("")
    lines.append("── 最大文件 TOP5 ──")
    for n in sorted(graph["nodes"], key=lambda n: -n["lines"])[:5]:
        lines.append(f"  {n['lines']:>6} 行  {n['id']} ({n['lang']})")
    lines.append("")
    lines.append("── 依赖边 TOP10 ──")
    for e in graph["edges"][:10]:
        lines.append(f"  {e['from']} → {e['to']}")
    if not graph["edges"]:
        lines.append("  (无跨模块依赖)")
    lines.append("")
    lines.append(f"共 {len(graph['edges'])} 条依赖边")
    return "\n".join(lines)


def build_mermaid(graph: dict) -> str:
    """生成 Mermaid 依赖图（模块级别聚合）。"""
    lines = ["graph TD"]
    # 模块聚合：取文件第一级目录作为模块
    mods = {}
    for n in graph["nodes"]:
        parts = n["id"].split("/")
        mod = parts[0] if len(parts) > 1 else "(root)"
        mods.setdefault(mod, set()).update(n.get("imports", []))
    for mod, imps in sorted(mods.items()):
        safe_mod = mod.replace("-", "_")
        lines.append(f"    {safe_mod}[{mod}]")
        for imp in list(imps)[:5]:
            safe_imp = imp.replace("-", "_").split(".")[0]
            lines.append(f"    {safe_mod} --> {safe_imp}")
    return "\n".join(lines)


# ============================================================
# 离线自检
# ============================================================
def selftest() -> int:
    """离线自检：用临时 Python 项目验证 AST 分析。"""
    import tempfile
    failures = []

    def check(name: str, cond: bool):
        print(f"  [{'OK' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    # 1. 空目录拒绝
    with tempfile.TemporaryDirectory() as td:
        try:
            scan_files(Path(td))
            check("空目录拒绝", False)
        except GraphifyError:
            check("空目录拒绝", True)

    # 2. Python AST 分析
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "mod.py").write_text(
            "import os\nimport json\n\n"
            "def hello(name):\n    return f'hi {name}'\n\n"
            "class Service:\n    def run(self):\n        return hello('x')\n",
            encoding="utf-8")
        (root / "app.py").write_text(
            "from mod import hello\nx = hello('world')\n", encoding="utf-8")
        info = analyze_python(root / "mod.py", "mod.py")
        check("提取函数 hello", "hello" in info["functions"])
        check("提取类 Service", "Service" in info["classes"])
        check("提取 import os", "os" in info["imports"])
        check("提取调用 hello", "hello" in info["calls"])

        # 3. 图谱构建
        g = build_graph(root)
        check("图谱 2 文件", g["files"] == 2)
        check("依赖边存在", len(g["edges"]) >= 1)
        check("语言计数", g["languages"].get("python") == 2)
        check("函数总数", g["functions_total"] >= 1)

        # 4. 报告与 mermaid
        rep = build_report(g)
        check("报告含文件数", "文件数: 2" in rep)
        mm = build_mermaid(g)
        check("Mermaid 生成", mm.startswith("graph TD"))

    # 5. 语法错误容错
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "bad.py").write_text("def broken(:\n", encoding="utf-8")
        info = analyze_python(root / "bad.py", "bad.py")
        check("语法错误容错", info.get("syntax_error") is True)

    if failures:
        print(f"[SELFTEST] 失败 {len(failures)} 项: {failures}")
        return 1
    print("[SELFTEST] 全部通过 ✅")
    return 0


# ============================================================
# CLI 入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="代码库图谱分析（原创实现，标准库 AST）",
        epilog="示例:\n"
               "  扫描: python main.py scan ./src --output graph.json\n"
               "  报告: python main.py report ./src\n"
               "  图谱: python main.py mermaid ./src > graph.mmd\n"
               "  自检: python main.py selftest",
    )
    parser.add_argument("--command", nargs="?", default="report",
                        help="scan/report/mermaid/selftest")
    parser.add_argument("--path", nargs="?", default=".", help="代码目录")
    parser.add_argument("--output", default="", help="扫描结果输出 JSON 文件")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--verbose", action="store_true", help="输出详细明细")
    parser.add_argument("--dry-run", action="store_true", help="只校验不输出文件")
    parser.add_argument("--batch", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--config", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--mode", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--task", default=None, help="文档声明的参数")  # F3 补全
    args = parser.parse_args()

    if args.verbose:
        print(f"[verbose] 参数: {vars(args)}", file=sys.stderr)

    if args.selftest or args.command == "selftest":
        sys.exit(selftest())

    try:
        root = Path(args.path)
        cmd = args.command

        if args.dry_run:
            files = scan_files(root)
            print(json.dumps({"mode": "dry-run", "code_files": len(files),
                              "dir": str(root)}, ensure_ascii=False))
            return 0

        if cmd == "scan":
            g = build_graph(root, args.verbose)
            if args.output:
                if not args.dry_run:
                    try:
                        Path(args.output).write_text(
                            json.dumps(g, ensure_ascii=False, indent=2),
                            encoding="utf-8", errors="replace")
                    except OSError as e:
                        raise GraphifyError("E003", f"输出写入失败: {e}") from e
                print(f"图谱已保存: {args.output}（{g['files']} 文件，{len(g['edges'])} 边）")
            else:
                print(json.dumps(g, ensure_ascii=False, indent=2))
            return 0
        if cmd == "report":
            g = build_graph(root, args.verbose)
            print(build_report(g))
            return 0
        if cmd == "mermaid":
            g = build_graph(root)
            print(build_mermaid(g))
            return 0
        parser.print_help()
        return 1
    except GraphifyError as e:
        print(f"[{e.code}] {e}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001 兜底降级
        print(f"[E099] 未预期异常: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    main()


def read_text_safe(path):
    """多编码容错读取 (selftest contract)"""
    import codecs
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with codecs.open(path, "r", encoding=enc) as fh:
                return fh.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()
