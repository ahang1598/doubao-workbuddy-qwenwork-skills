import contextlib
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock


SKILL_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SKILL_ROOT / "scripts" / "ldh_client.py"

SPEC = importlib.util.spec_from_file_location("ldh_client", MODULE_PATH)
client = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(client)


def precise_args(**overrides):
    values = {
        "q": "droit à l'oubli",
        "country": "FR",
        "namespace": "case_law",
        "source": ["FR/Judilibre"],
        "court": None,
        "court_tier": None,
        "jurisdiction": None,
        "language": None,
        "date_start": None,
        "date_end": None,
        "top_k": 10,
        "alpha": 0.7,
        "result_detail": "snippet",
        "max_source_checks": 12,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def run_emitting(func, args):
    output = io.StringIO()
    with contextlib.redirect_stdout(output), unittest.TestCase().assertRaises(SystemExit):
        func(args)
    return json.loads(output.getvalue())


class LdhClientTests(unittest.TestCase):
    def test_country_catalog_normalisation(self):
        codes = client._normalise_country_codes({
            "data": [{"country": "FR"}, {"code": "GB"}, "CoE"]
        })
        self.assertEqual(codes, {"FR", "UK", "CoE"})

    def test_source_catalog_normalisation(self):
        sources = client._normalise_sources({
            "sources": [
                {"id": "FR/Judilibre", "data_types": ["case_law"]},
                "FR/Legifrance",
            ]
        })
        self.assertEqual(
            [item["source"] for item in sources],
            ["FR/Judilibre", "FR/Legifrance"],
        )

    def test_precise_search_validates_and_rejects_cross_country_hit(self):
        def fake_http(method, path, **kwargs):
            if path.endswith("/discover/countries"):
                return True, {"countries": [{"code": "FR"}, {"code": "DE"}]}
            if "/discover/sources/FR" in path:
                return True, {
                    "sources": [{
                        "source": "FR/Judilibre",
                        "data_types": ["case_law"],
                        "quality_tier": 1,
                    }]
                }
            raise AssertionError("unexpected HTTP call: %s %s" % (method, path))

        search_response = {
            "query": "droit à l'oubli",
            "total_hits": 2,
            "hits": [
                {
                    "source": "FR/Judilibre",
                    "source_id": "good",
                    "country": "FR",
                    "title": "French case",
                },
                {
                    "source": "DE/BVerfG",
                    "source_id": "wrong",
                    "country": "DE",
                    "title": "German case",
                },
            ],
        }
        with mock.patch.object(client, "_http", side_effect=fake_http), \
                mock.patch.object(client, "_search", return_value=(True, search_response)):
            result = run_emitting(client.cmd_precise_search, precise_args())

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["accepted_hits"], 1)
        self.assertEqual(result["hits"][0]["source_id"], "good")
        self.assertEqual(
            result["rejected_hits"][0]["reasons"],
            ["country_mismatch", "source_mismatch"],
        )

    def test_noncanonical_gb_is_blocked_before_search(self):
        result = run_emitting(
            client.cmd_precise_search,
            precise_args(country="GB", source=[]),
        )
        self.assertEqual(result["status"], "bad_request")
        self.assertEqual(result["canonical_country"], "UK")

    def test_unknown_source_is_blocked(self):
        def fake_http(method, path, **kwargs):
            if path.endswith("/discover/countries"):
                return True, {"countries": ["FR"]}
            if "/discover/sources/FR" in path:
                return True, {"sources": ["FR/Judilibre"]}
            raise AssertionError(path)

        with mock.patch.object(client, "_http", side_effect=fake_http):
            result = run_emitting(
                client.cmd_precise_search,
                precise_args(source=["FR/Invented"]),
            )
        self.assertEqual(result["status"], "bad_request")
        self.assertEqual(result["unknown_sources"], ["FR/Invented"])

    def test_filter_directory_values_are_extracted(self):
        payload = {
            "filters": {
                "courts": [{"name": "Cour de cassation"}],
                "languages": [{"code": "fr"}],
            }
        }
        self.assertEqual(
            client._flatten_filter_values(payload, "court"),
            {"cour de cassation"},
        )
        self.assertEqual(client._flatten_filter_values(payload, "language"), {"fr"})


if __name__ == "__main__":
    unittest.main()
