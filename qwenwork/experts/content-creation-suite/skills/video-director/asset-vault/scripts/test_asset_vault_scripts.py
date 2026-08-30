#!/usr/bin/env python3
"""asset-vault 脚本最小契约测试。"""

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import check_consistency
import scan_interrupted
import update_index


class AssetVaultScriptContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.vault_path = Path(self.temporary_directory.name) / "asset-vault"
        self.vault_path.mkdir(parents=True)
        (self.vault_path / "projects").mkdir()
        (self.vault_path / "patterns").mkdir()
        (self.vault_path / "industry").mkdir()
        (self.vault_path / "_index").mkdir()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def create_project(self, project_name: str, metadata: dict, files: dict[str, str] | None = None) -> Path:
        project_path = self.vault_path / "projects" / project_name
        project_path.mkdir(parents=True)
        (project_path / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False),
            encoding="utf-8",
        )
        for relative_path, content in (files or {}).items():
            file_path = project_path / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
        return project_path

    def test_update_index_preserves_manual_summary_content_and_updates_auto_list(self) -> None:
        hooks_path = self.vault_path / "patterns" / "hooks"
        hooks_path.mkdir(parents=True)
        (hooks_path / "悬念开头.md").write_text(
            "---\ntitle: 悬念开头\n---\n\n# 悬念开头\n",
            encoding="utf-8",
        )
        (hooks_path / "_summary.md").write_text(
            "# Hook 总结\n\n人工内容保留。\n",
            encoding="utf-8",
        )

        updated_count = update_index.update_summary_files(self.vault_path)

        summary_content = (hooks_path / "_summary.md").read_text(encoding="utf-8")
        self.assertGreaterEqual(updated_count, 1)
        self.assertIn("人工内容保留。", summary_content)
        self.assertIn(update_index.AUTO_SUMMARY_START, summary_content)
        self.assertIn("- [悬念开头](悬念开头.md)", summary_content)

    def test_check_consistency_reports_missing_fixed_artifacts(self) -> None:
        self.create_project(
            "20260602_客户A_项目A",
            {
                "status": "in_progress",
                "client": "客户A",
                "project": "项目A",
                "date": "2026-06-02",
            },
            {
                "step_01_brief.md": "# brief\n",
                "final_script.md": "# final\n",
            },
        )

        issues = check_consistency.check_missing_files(self.vault_path)
        issue_messages = "\n".join(issue["message"] for issue in issues)

        self.assertIn("step_02_creative.md", issue_messages)
        self.assertIn("step_03_script.md", issue_messages)
        self.assertIn("uploads", issue_messages)

    def test_check_consistency_recommends_delivered_before_completed(self) -> None:
        self.create_project(
            "20260602_客户A_项目A",
            {"status": "in_progress", "date": "2026-06-02"},
            {"final_script.md": "# final\n"},
        )

        issues = check_consistency.check_status_anomalies(self.vault_path)
        fixes = "\n".join(issue["fix"] for issue in issues)

        self.assertIn("先更新 status 为 delivered", fixes)
        self.assertIn("再更新为 completed", fixes)

    def test_check_consistency_reports_summary_missing_and_missing_listed_asset(self) -> None:
        hooks_path = self.vault_path / "patterns" / "hooks"
        hooks_path.mkdir(parents=True)
        (hooks_path / "悬念开头.md").write_text("# 悬念开头\n", encoding="utf-8")
        (hooks_path / "_summary.md").write_text(
            "<!-- AUTO_ASSET_LIST_START -->\n\n"
            "## 自动资产清单\n\n"
            "- [旧资产](旧资产.md)\n\n"
            "<!-- AUTO_ASSET_LIST_END -->\n",
            encoding="utf-8",
        )

        selling_points_path = self.vault_path / "patterns" / "selling-points"
        selling_points_path.mkdir(parents=True)
        (selling_points_path / "产品测评型.md").write_text("# 产品测评型\n", encoding="utf-8")

        issues = check_consistency.check_summary_consistency(self.vault_path)
        issue_types = {issue["type"] for issue in issues}

        self.assertIn("汇总漏列", issue_types)
        self.assertIn("汇总缺失", issue_types)

    def test_check_consistency_reports_potential_duplicate_asset_names(self) -> None:
        hooks_path = self.vault_path / "patterns" / "hooks"
        hooks_path.mkdir(parents=True)
        (hooks_path / "悬念开头.md").write_text("# 悬念开头\n", encoding="utf-8")
        (hooks_path / "悬念开场.md").write_text("# 悬念开场\n", encoding="utf-8")

        issues = check_consistency.check_duplicate_asset_names(self.vault_path)

        self.assertTrue(any(issue["type"] == "疑似重复命名" for issue in issues))

    def test_scan_interrupted_returns_existing_files_and_interruption_info(self) -> None:
        self.create_project(
            "20260602_客户A_项目A",
            {
                "status": "interrupted",
                "client": "客户A",
                "project": "项目A",
                "date": "2026-06-02",
                "interruption": {
                    "interrupted_at": "step_02",
                    "reason": "用户暂停",
                },
            },
            {
                "step_01_brief.md": "# brief\n",
                "step_02_creative.md": "# creative\n",
            },
        )

        interrupted_projects = scan_interrupted.scan_interrupted(self.vault_path)

        self.assertEqual(1, len(interrupted_projects))
        interrupted_project = interrupted_projects[0]
        self.assertEqual("interrupted", interrupted_project["reason_type"])
        self.assertEqual("step_02", interrupted_project["interrupted_at"])
        self.assertEqual("用户暂停", interrupted_project["reason"])
        self.assertTrue(interrupted_project["has_step_01"])
        self.assertEqual(2, interrupted_project["step_count"])

    def test_scan_interrupted_returns_stale_in_progress_projects(self) -> None:
        stale_updated_at = datetime.now(timezone.utc) - timedelta(hours=25)
        fresh_updated_at = datetime.now(timezone.utc) - timedelta(hours=2)
        self.create_project(
            "20260602_客户A_超时项目",
            {
                "status": "in_progress",
                "client": "客户A",
                "project": "超时项目",
                "date": "2026-06-02",
                "updated_at": stale_updated_at.isoformat(),
            },
            {"step_01_brief.md": "# brief\n"},
        )
        self.create_project(
            "20260602_客户A_新项目",
            {
                "status": "in_progress",
                "client": "客户A",
                "project": "新项目",
                "date": "2026-06-02",
                "updated_at": fresh_updated_at.isoformat(),
            },
            {"step_01_brief.md": "# brief\n"},
        )

        interrupted_projects = scan_interrupted.scan_interrupted(self.vault_path)

        self.assertEqual(1, len(interrupted_projects))
        stale_project = interrupted_projects[0]
        self.assertEqual("stale_in_progress", stale_project["reason_type"])
        self.assertEqual("超时项目", stale_project["project"])
        self.assertTrue(stale_project["has_step_01"])


if __name__ == "__main__":
    unittest.main()
