import importlib.util
import json
from pathlib import Path
import unittest


SKILL_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SKILL_ROOT / "scripts" / "jurisdiction_resolver.py"
RULES_PATH = SKILL_ROOT / "references" / "jurisdiction-rules.json"

SPEC = importlib.util.spec_from_file_location("jurisdiction_resolver", MODULE_PATH)
resolver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(resolver)


class JurisdictionResolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))

    def resolve(self, text):
        return resolver.resolve(text, self.rules)

    def test_eu_and_uk_are_separate_targets(self):
        result = self.resolve("比较欧盟和英国关于被遗忘权判例")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(
            [target["ldh_country"] for target in result["targets"]],
            ["EU", "UK"],
        )

    def test_ecthr_maps_to_council_of_europe_and_hudoc(self):
        result = self.resolve("欧洲人权法院第8条判例")
        target = result["targets"][0]
        self.assertEqual(target["ldh_country"], "CoE")
        self.assertIn("CoE/HUDOC", target["source_hints"])

    def test_subnational_region_uses_parent_country(self):
        result = self.resolve("加州 CCPA 合规义务")
        target = result["targets"][0]
        self.assertEqual(target["ldh_country"], "US")
        self.assertEqual(target["entity_level"], "subnational")
        self.assertIn("California", target["query_terms"])

    def test_ambiguous_georgia_requires_clarification(self):
        result = self.resolve("Georgia company law")
        self.assertEqual(result["status"], "ambiguous")
        self.assertTrue(result["requires_clarification"])
        self.assertEqual(
            {item["country_code"] for item in result["ambiguous_mentions"][0]["candidates"]},
            {"GE", "US"},
        )

    def test_ordinary_english_in_is_not_india_code(self):
        result = self.resolve("What remedies are available in a contract dispute?")
        self.assertEqual(result["status"], "unresolved")
        self.assertEqual(result["targets"], [])

    def test_uppercase_explicit_codes_are_recognised(self):
        result = self.resolve("Compare FR and DE employment law")
        self.assertEqual(
            [target["ldh_country"] for target in result["targets"]],
            ["FR", "DE"],
        )

    def test_compare_keyword_does_not_enable_unrelated_code_tokens(self):
        result = self.resolve("Compare IN contract clauses with France")
        self.assertEqual(
            [target["ldh_country"] for target in result["targets"]],
            ["FR"],
        )

    def test_dynamic_coverage_shapes_are_supported(self):
        self.assertEqual(
            resolver._extract_codes({
                "coverage": {
                    "countries": [{"country": "FR"}, {"code": "EU"}]
                }
            }),
            {"FR", "EU"},
        )
        self.assertEqual(
            resolver._extract_codes({"countries": {"FR": {}, "CoE": {}}}),
            {"FR", "CoE"},
        )

    def test_ca_domain_acronym_does_not_add_canada_to_russia(self):
        result = self.resolve("企业在俄罗斯申请一张数字认证牌照（CA）需要什么条件")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(
            [target["ldh_country"] for target in result["targets"]],
            ["RU"],
        )
        self.assertEqual(result["ignored_mentions"], [{
            "mention": "CA",
            "reason": "domain_acronym",
            "expansion": "Certification Authority",
        }])

    def test_explicit_canada_code_context_still_maps_ca(self):
        result = self.resolve("请研究国家代码 CA 的隐私法")
        self.assertEqual(
            [target["ldh_country"] for target in result["targets"]],
            ["CA"],
        )
        self.assertEqual(result["ignored_mentions"], [])

    def test_california_abbreviation_does_not_add_canada(self):
        result = self.resolve("California (CA) consumer privacy law")
        self.assertEqual(
            [target["ldh_country"] for target in result["targets"]],
            ["US"],
        )
        self.assertEqual(result["ignored_mentions"][0]["mention"], "CA")


if __name__ == "__main__":
    unittest.main()
