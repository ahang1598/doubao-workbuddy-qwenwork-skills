import json
import os
import sys
import time
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from claw_pipe_http import PipeHttpTimeout, _read_fd  # noqa: E402
from image_understanding import image_understanding  # noqa: E402


class FakeConfig:
    personal_uid = ""

    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def skill_post(self, *_args, **_kwargs):
        if self.error:
            raise self.error
        return self.response


class FakeResponse:
    status_code = 200
    text = ""

    def __init__(self, lines):
        self.lines = lines
        self.closed = False

    def iter_lines(self, decode_unicode=False):
        del decode_unicode
        yield from self.lines

    def close(self):
        self.closed = True


class ImageUnderstandingTimeoutTests(unittest.TestCase):
    def test_done_event_stops_without_waiting_for_connection_close(self):
        caption_event = {
            "abilityInfos": [{
                "actionExecutorResult": {
                    "reply": {"streamInfo": {"streamContent": "识别完成"}}
                }
            }]
        }

        def lines():
            yield f"data: {json.dumps(caption_event, ensure_ascii=False)}"
            yield "data: [DONE]"
            raise AssertionError("收到 [DONE] 后不应继续读取 SSE")

        response = FakeResponse(lines())
        result = image_understanding(["https://example.com/a.png"], "描述图片", FakeConfig(response))

        self.assertEqual(result, {"caption": "识别完成"})
        self.assertTrue(response.closed)

    def test_pipe_timeout_is_reported_as_retryable(self):
        result = image_understanding(
            ["https://example.com/a.png"],
            "描述图片",
            FakeConfig(error=PipeHttpTimeout("等待响应数据超时（180s）")),
        )

        self.assertEqual(result["error"]["code"], "request_timeout")
        self.assertTrue(result["error"]["retryable"])

    def test_read_fd_enforces_idle_timeout(self):
        read_fd, write_fd = os.pipe()
        try:
            started = time.monotonic()
            with self.assertRaises(PipeHttpTimeout):
                _read_fd(
                    read_fd,
                    idle_timeout=0.05,
                    deadline=None,
                    label="测试读取",
                )
            self.assertLess(time.monotonic() - started, 1.0)
        finally:
            os.close(read_fd)
            os.close(write_fd)


if __name__ == "__main__":
    unittest.main()
