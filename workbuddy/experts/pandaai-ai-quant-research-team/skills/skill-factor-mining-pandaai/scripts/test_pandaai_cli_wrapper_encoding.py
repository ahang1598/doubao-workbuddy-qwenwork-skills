#!/usr/bin/env python3
"""Tests for pandaai_cli_wrapper encoding handling (UTF-8 and GB18030)."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandaai_cli_wrapper as cli


def make_result(stdout_bytes: bytes, stderr_bytes: bytes = b"",
                returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode,
                                       stdout=stdout_bytes, stderr=stderr_bytes)


class TestDecodeBytes(unittest.TestCase):
    def test_utf8(self):
        raw = "正常中文 JSON".encode("utf-8")
        self.assertEqual(cli._decode_bytes(raw), "正常中文 JSON")

    def test_gb18030(self):
        raw = "正常中文 JSON".encode("gb18030")
        self.assertEqual(cli._decode_bytes(raw), "正常中文 JSON")

    def test_invalid_fallback(self):
        raw = b"\xd2\xff\xfe\xfd garbage"
        self.assertIn("garbage", cli._decode_bytes(raw))


class TestParseJsonOutput(unittest.TestCase):
    def test_utf8_list_payload(self):
        payload = json.dumps({"success": True, "factors": [{"name": "动量因子"}]},
                             ensure_ascii=False).encode("utf-8")
        result = make_result(payload)
        parsed = cli.parse_json_output(result)
        self.assertTrue(parsed["success"])
        self.assertEqual(parsed["factors"][0]["name"], "动量因子")

    def test_gb18030_list_payload(self):
        payload = json.dumps({"success": True, "factors": [{"name": "波动率动量"}]},
                             ensure_ascii=False).encode("gb18030")
        result = make_result(payload)
        parsed = cli.parse_json_output(result)
        self.assertTrue(parsed["success"])
        self.assertEqual(parsed["factors"][0]["name"], "波动率动量")

    def test_error_preferred_over_stdout(self):
        err = json.dumps({"success": False, "error": "WORKFLOW_FAILED"},
                         ensure_ascii=False).encode("gb18030")
        result = make_result(b'{"success": true}', stderr_bytes=err, returncode=1)
        parsed = cli.parse_json_output(result)
        self.assertFalse(parsed["success"])
        self.assertEqual(parsed["error"], "WORKFLOW_FAILED")

    def test_json_on_stderr(self):
        err = b'{"success": false, "error": "bad"}'
        result = make_result(b"", stderr_bytes=err, returncode=1)
        parsed = cli.parse_json_output(result)
        self.assertFalse(parsed["success"])
        self.assertEqual(parsed["error"], "bad")


class TestEndToEndEncoding(unittest.TestCase):
    """End-to-end: confirm action_list handles both encodings via run_cli."""

    def run_wrapper_list(self, payload: bytes) -> dict:
        old_run = cli.run_cli

        def fake_run(args, capture=True):
            return subprocess.CompletedProcess(args=args, returncode=0,
                                               stdout=payload, stderr=b"")
        cli.run_cli = fake_run
        try:
            return cli.action_list(limit=10, offset=0, no_detail=True)
        finally:
            cli.run_cli = old_run

    def test_list_utf8(self):
        payload = json.dumps({"success": True, "total": 1, "count": 1,
                              "factors": [{"name": "中文因子"}]},
                             ensure_ascii=False).encode("utf-8")
        parsed = self.run_wrapper_list(payload)
        self.assertEqual(parsed["total"], 1)
        self.assertEqual(parsed["factors"][0]["name"], "中文因子")

    def test_list_gb18030(self):
        payload = json.dumps({"success": True, "total": 1, "count": 1,
                              "factors": [{"name": "中文因子"}]},
                             ensure_ascii=False).encode("gb18030")
        parsed = self.run_wrapper_list(payload)
        self.assertEqual(parsed["factors"][0]["name"], "中文因子")


if __name__ == "__main__":
    unittest.main(verbosity=2)
