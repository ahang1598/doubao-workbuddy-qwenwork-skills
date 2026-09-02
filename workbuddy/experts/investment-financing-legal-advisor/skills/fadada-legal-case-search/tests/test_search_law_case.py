import importlib.util
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "search_law_case.py"
SPEC = importlib.util.spec_from_file_location("search_law_case", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ErrorOpener:
    def add_handler(self, _handler):
        return None

    def open(self, request, timeout):
        raise HTTPError(
            request.full_url,
            403,
            "Forbidden",
            {},
            io.BytesIO(b'{"message":"denied"}'),
        )


class SearchLawCaseTest(unittest.TestCase):
    def test_parses_semantic_request(self):
        payload = MODULE.parse_request(
            '{"retrievalScene":"case_semantic","searchContent":"竞业限制纠纷"}'
        )

        self.assertEqual("case_semantic", payload["retrievalScene"])
        self.assertEqual("竞业限制纠纷", payload["searchContent"])

    def test_allows_exact_docket_without_search_content(self):
        payload = MODULE.parse_request(
            '{"retrievalScene":"case_docket_exact",'
            '"structuredFields":{"docketNo":"（2021）粤0104民初44725号","caseType":"ptal"}}'
        )

        self.assertNotIn("searchContent", payload)
        self.assertEqual(
            "（2021）粤0104民初44725号",
            payload["structuredFields"]["docketNo"],
        )

    def test_preserves_structured_filters_in_json_body(self):
        payload = MODULE.parse_request(
            '{"retrievalScene":"case_structured_search",'
            '"structuredFields":{"hardFilters":true,"province":"广东",'
            '"dateStart":"2021-01-01","dateEnd":"2025-12-31"}}'
        )
        request = MODULE.build_http_request(payload, "secret-token", "https://example.test/base/")

        self.assertEqual("POST", request.get_method())
        self.assertEqual(
            "https://example.test/base/claw/searchTool/lawCase",
            request.full_url,
        )
        self.assertNotIn("?", request.full_url)
        self.assertEqual(
            "application/json; charset=utf-8",
            request.get_header("Content-type"),
        )
        self.assertEqual(payload, json.loads(request.data.decode("utf-8")))

    def test_rejects_invalid_requests(self):
        invalid_requests = (
            "not-json",
            "[]",
            '{}',
            '{"retrievalScene":1}',
            '{"retrievalScene":"case_semantic","searchContent":1}',
            '{"retrievalScene":"case_docket_exact","structuredFields":null}',
        )

        for raw_request in invalid_requests:
            with self.subTest(raw_request=raw_request):
                with self.assertRaises(MODULE.RequestValidationError):
                    MODULE.parse_request(raw_request)

    def test_http_error_does_not_expose_token(self):
        payload = {"retrievalScene": "case_semantic", "searchContent": "测试"}
        with patch.dict(
            os.environ,
            {"RICHEEAI_TOKEN": "secret-token", "RICHEEAI_API_BASE": "https://example.test"},
            clear=True,
        ), patch.object(MODULE, "get_proxy_handler", return_value=ErrorOpener()):
            result = MODULE.search_law_case(payload)

        rendered = json.dumps(result, ensure_ascii=False)
        self.assertFalse(result["success"])
        self.assertNotIn("secret-token", rendered)
        self.assertEqual(payload, result["request"])


if __name__ == "__main__":
    unittest.main()
