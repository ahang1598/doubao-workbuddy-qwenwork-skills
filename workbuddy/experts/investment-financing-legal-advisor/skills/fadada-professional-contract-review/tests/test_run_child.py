#!/usr/bin/env python3
"""子进程 UTF-8 强制回归（Windows 真机 45dbba0b）。

那次驱动脚本直接崩在 `subprocess._readerthread`：
`UnicodeDecodeError: 'gbk' codec can't decode` —— 父进程用系统默认编码（中文
Windows 为 GBK）解码子进程输出，而本技能的中文错误话术含 GBK 未必覆盖的字符。
父进程崩了，连子进程成败都拿不到，模型转而自造 pandoc 链路产出残缺报告。

运行：python3 tests/test_run_child.py
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import run_child  # noqa: E402

# GBK 覆盖不全或易出问题的字符——正是技能话术里大量使用的
TRICKY = "破折号—— 直角引号「」 不等号≥≤ 箭头→ 省略号…"


class ChildEnvTest(unittest.TestCase):
    def test_forces_utf8_env(self) -> None:
        env = run_child.child_env()
        self.assertEqual(env["PYTHONUTF8"], "1")
        self.assertEqual(env["PYTHONIOENCODING"], "utf-8")

    def test_extra_env_is_merged_not_replacing_utf8(self) -> None:
        env = run_child.child_env({"MY_VAR": "x"})
        self.assertEqual(env["MY_VAR"], "x")
        self.assertEqual(env["PYTHONUTF8"], "1", "叠加自定义env不得丢掉UTF-8强制")


class RoundTripTest(unittest.TestCase):
    def test_chinese_output_survives_round_trip(self) -> None:
        proc = run_child.run(
            [sys.executable, "-c", f"print({TRICKY!r})"])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("「」", proc.stdout)
        self.assertIn("≥", proc.stdout)

    def test_stderr_also_decoded(self) -> None:
        proc = run_child.run(
            [sys.executable, "-c",
             f"import sys; sys.stderr.write({TRICKY!r}); sys.exit(1)"])
        self.assertEqual(proc.returncode, 1)
        self.assertIn("——", proc.stderr)

    def test_invalid_bytes_do_not_crash(self) -> None:
        """errors='replace'：子进程吐非法字节也不能让父进程崩。

        真机故障的本质就是这一步抛异常，把成败信息一起弄丢了。
        """
        proc = run_child.run(
            [sys.executable, "-c",
             "import sys; sys.stdout.buffer.write(b'\\xff\\xfe bad bytes')"])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("bad bytes", proc.stdout)

    def test_explicit_encoding_is_utf8(self) -> None:
        """锁定实现：不得回退到系统默认编码。"""
        captured = {}
        real = subprocess.run

        def spy(cmd, **kwargs):
            captured.update(kwargs)
            return real(cmd, **kwargs)

        run_child.subprocess.run = spy
        try:
            run_child.run([sys.executable, "-c", "pass"])
        finally:
            run_child.subprocess.run = real
        self.assertEqual(captured.get("encoding"), "utf-8")
        self.assertEqual(captured.get("errors"), "replace")


class NoBypassTest(unittest.TestCase):
    def test_no_script_calls_subprocess_run_directly(self) -> None:
        """任何绕过 run_child 的直接调用都会重新引入该缺陷。"""
        offenders = []
        for path in SCRIPTS.glob("*.py"):
            if path.name == "run_child.py":
                continue
            for num, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if "subprocess.run(" in line and not line.strip().startswith("#"):
                    offenders.append(f"{path.name}:{num}")
        self.assertEqual(offenders, [], f"这些调用点绕过了 run_child: {offenders}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
