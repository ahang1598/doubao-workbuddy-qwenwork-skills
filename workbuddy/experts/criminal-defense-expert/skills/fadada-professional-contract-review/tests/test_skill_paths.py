#!/usr/bin/env python3
"""skill_paths 跨平台路径解析回归。

覆盖真机故障：mac 上写用户工作区被白名单拒绝、模型转而 mkdir /mnt 撞只读文件
系统；Windows 上 /tmp 与 /mnt 均不成立导致全链路阻断。

运行：python3 tests/test_skill_paths.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import skill_paths  # noqa: E402


class OutputRootTest(unittest.TestCase):
    def setUp(self) -> None:
        self._env = os.environ.get(skill_paths.ENV_OUTPUT_DIR)
        os.environ.pop(skill_paths.ENV_OUTPUT_DIR, None)

    def tearDown(self) -> None:
        os.environ.pop(skill_paths.ENV_OUTPUT_DIR, None)
        if self._env is not None:
            os.environ[skill_paths.ENV_OUTPUT_DIR] = self._env

    def test_env_var_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ[skill_paths.ENV_OUTPUT_DIR] = tmp
            self.assertEqual(skill_paths.output_root(), Path(tmp))

    def test_env_var_expands_user(self) -> None:
        os.environ[skill_paths.ENV_OUTPUT_DIR] = "~/somewhere"
        self.assertEqual(skill_paths.output_root(), Path.home() / "somewhere")

    def test_desktop_fallback_when_cloud_absent(self) -> None:
        """桌面端（无 /mnt/user-data）落到用户工作区，而不是抛错。"""
        if skill_paths._writable(skill_paths.CLOUD_OUTPUT_DIR):
            self.skipTest("当前环境存在可写的 /mnt/user-data（云端沙箱）")
        self.assertEqual(skill_paths.output_root(),
                         Path.home() / "richeeai" / "project")

    def test_work_root_is_real_temp_dir(self) -> None:
        """中间产物目录必须是系统临时目录：Windows 上不能是伪造的 /tmp。"""
        work = skill_paths.work_root()
        self.assertEqual(work, Path(tempfile.gettempdir()))
        self.assertTrue(work.is_dir())


class GeneratedPathTest(unittest.TestCase):
    def setUp(self) -> None:
        self._env = os.environ.get(skill_paths.ENV_OUTPUT_DIR)
        self._tmp = tempfile.TemporaryDirectory()
        os.environ[skill_paths.ENV_OUTPUT_DIR] = self._tmp.name

    def tearDown(self) -> None:
        os.environ.pop(skill_paths.ENV_OUTPUT_DIR, None)
        if self._env is not None:
            os.environ[skill_paths.ENV_OUTPUT_DIR] = self._env
        self._tmp.cleanup()

    def test_output_root_accepted(self) -> None:
        target = Path(self._tmp.name) / "报告.docx"
        self.assertEqual(skill_paths.generated_path(target), target.resolve())

    def test_work_root_accepted(self) -> None:
        target = skill_paths.work_root() / "extracted.json"
        self.assertEqual(skill_paths.generated_path(target), target.resolve())

    def test_skill_local_dirs_accepted(self) -> None:
        for name in ("outputs", "evaluation"):
            target = skill_paths.SKILL_ROOT / name / "x.docx"
            self.assertEqual(skill_paths.generated_path(target), target.resolve())

    def test_unrelated_path_rejected_with_actionable_message(self) -> None:
        outside = Path.home() / "__definitely_not_a_delivery_dir__" / "x.docx"
        with self.assertRaises(ValueError) as ctx:
            skill_paths.generated_path(outside)
        # 报错必须给出当前环境的实际允许目录与补救办法，而不是写死云端路径
        self.assertIn(skill_paths.ENV_OUTPUT_DIR, str(ctx.exception))
        self.assertIn(self._tmp.name, str(ctx.exception))

    def test_sibling_prefix_not_confused(self) -> None:
        """`<root>_sibling` 不得因字符串前缀被误判为 `<root>` 下的路径。

        用 home 下的路径做交付根：临时目录的兄弟目录仍落在 work_root() 内，
        天然合法，无法验证前缀边界。
        """
        root = Path.home() / "__delivery_root__"
        os.environ[skill_paths.ENV_OUTPUT_DIR] = str(root)
        self.assertEqual(skill_paths.generated_path(root / "x.docx"),
                         (root / "x.docx").resolve())
        with self.assertRaises(ValueError):
            skill_paths.generated_path(Path(str(root) + "_sibling") / "x.docx")

    def test_nonexistent_path_does_not_raise_os_error(self) -> None:
        deep = Path(self._tmp.name) / "a" / "b" / "c" / "报告.docx"
        self.assertEqual(skill_paths.generated_path(deep), deep.resolve())


class EnsureDirTest(unittest.TestCase):
    def test_creates_and_returns_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "nested" / "outputs"
            self.assertEqual(skill_paths.ensure_dir(target), target.resolve())
            self.assertTrue(target.is_dir())

    def test_unwritable_parent_raises_actionable_error(self) -> None:
        if os.name == "nt":
            self.skipTest("POSIX 权限语义不适用于 Windows")
        if os.geteuid() == 0:
            self.skipTest("root 可写任意目录")
        with self.assertRaises(ValueError) as ctx:
            skill_paths.ensure_dir(Path("/__no_permission_here__/outputs"))
        self.assertIn(skill_paths.ENV_OUTPUT_DIR, str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
