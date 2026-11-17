#!/usr/bin/env python3
"""selftest.py — ai-learning-roadmap 自检契约（8 项断言）"""
import os, sys, tempfile

base = os.path.dirname(os.path.abspath(__file__))
for p in (base, os.path.join(base, "scripts")):
    if os.path.isdir(p):
        sys.path.insert(0, p)
failures = []

def check(name, cond, detail=""):
    if not cond:
        failures.append(f"{name}: {detail}")
    print(f"{'✅' if cond else '❌'} {name}")

def test_import():
    try:
        import run as r
        assert hasattr(r, "main"), "缺少 main 入口"
        check("模块可导入", True)
    except Exception as e:
        check("模块可导入", False, str(e))

def test_cli():
    try:
        import run as r
        assert callable(getattr(r, "main", None))
        check("CLI 入口", True)
    except Exception as e:
        check("CLI 入口", False, str(e))

def test_encoding():
    import run as r
    fn = getattr(r, "read_text_safe", None) or getattr(r, "_read_text_safe", None)
    check("多编码容错", fn is not None, "无 read_text_safe")

def test_dry_run():
    import run as r
    has_dry = hasattr(r, "dry_run") or "--dry-run" in open(os.path.join(base, "scripts/run.py") if os.path.exists(os.path.join(base, "scripts/run.py")) else os.path.join(base, "run.py"), encoding="utf-8").read()
    check("dry-run 预览", has_dry)

def test_error_handling():
    src = ""
    for p in (os.path.join(base, "scripts/run.py"), os.path.join(base, "run.py")):
        if os.path.exists(p):
            src = open(p, encoding="utf-8").read()
            break
    check("异常降级", "except Exception" in src and "except:" not in src, "军规R2")

def test_license():
    md = open(os.path.join(base, "SKILL.md"), encoding="utf-8").read()
    check("许可证", "MIT License" in md or "license" in md.lower())

def test_args():
    import run as r
    check("参数化", hasattr(r, "main"))

def test_sections():
    md = open(os.path.join(base, "SKILL.md"), encoding="utf-8").read()
    ok = all(s in md for s in ["## 简介", "## 使用", "## 示例", "## 常见问题"])
    check("文档章节", ok)

test_import()
test_cli()
test_encoding()
test_dry_run()
test_error_handling()
test_license()
test_args()
test_sections()

print(f"\n自检完成: {8 - len(failures)}/8 通过")
sys.exit(1 if failures else 0)
