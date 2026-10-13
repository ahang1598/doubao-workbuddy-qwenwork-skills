from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_packet import BASE_PACKET_FILES, OPTIONAL_PACKET_FILES, WILL_FILE, build_packet  # noqa: E402
from build_will_docx import HEADINGS, build_will_docx  # noqa: E402
from evaluate_rules import evaluate_rules  # noqa: E402
from validate_case import TEMPLATE_SHA256, validate_case  # noqa: E402


class SkillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.demo = json.loads((ROOT / "assets" / "examples" / "demo-case.json").read_text(encoding="utf-8"))

    def test_schema_and_demo_are_valid_json(self) -> None:
        schema = json.loads((ROOT / "assets" / "schemas" / "case.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema_version"]["const"], "0.5.1")
        self.assertEqual(self.demo["schema_version"], "0.5.1")

    def test_card_deck_is_native_and_deterministic(self) -> None:
        self.assertFalse((ROOT / "assets" / "cards" / "welcome-messages.json").exists())
        self.assertFalse((ROOT / "scripts" / "select_welcome_message.py").exists())
        skill_md = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        expected_initial_welcome = """> 您好，我是由北京德恒（杭州）律师事务所的公益律师打造的遗嘱起草助手。
   >
   > 我的创作者们曾说，在社区提供公益服务的期间，他们接触最多、也最特别的一类需求，就是遗嘱起草。
   >
   > 遗嘱并非不祥的象征，只是为人生里不可预知的“万一”提前做好安排，如今越来越多年轻人开始主动咨询遗嘱，二三十岁群体的心态远比大众预想的更加坦然。
   >
   > 社会变化得很快。我们拥有的东西在变，对财产、关系和个人选择的理解也在变。今天的遗嘱，不仅是财产分配，还要面对宠物照护、自媒体和游戏账号等数字权益，以及同居、分居、再婚等复杂关系。
   >
   > 基于这些实践经验，我们制作了这个辅助遗嘱起草的 Skill，将信息收集、关系梳理和初稿生成等基础工作标准化，减少重复性工作，让热心公益的律师提供遗嘱服务的整个工作流程更加高效、可持续，也能帮助更多有需要的人。"""
        self.assertIn(expected_initial_welcome, skill_md)
        initial_section = skill_md.split("**初次调用**：", 1)[1].split("**再次调用**：", 1)[0]
        self.assertNotIn("过程中有什么需要补充", initial_section)
        self.assertIn("欢迎调用这项遗嘱公益skill", skill_md)
        self.assertIn("欢迎再次调用这项遗嘱公益skill", skill_md)
        self.assertIn("您可以从这一次新的需要开始", skill_md)
        self.assertIn("都可以通过「其他」选项输入", skill_md)
        collection = (ROOT / "references" / "card-collection.md").read_text(encoding="utf-8")
        self.assertIn("首组内联直发", collection)
        self.assertIn("① 办理人", collection)
        self.assertIn("用户类型不再询问", collection)
        self.assertNotIn("select_welcome_message", skill_md)
        self.assertIn("lawyer-privacy-consent", skill_md)
        deck = json.loads((ROOT / "assets" / "cards" / "intake-card-deck.json").read_text(encoding="utf-8"))
        self.assertEqual(deck["deck_id"], "will-intake-v3")
        self.assertEqual(deck["collection_channel"], "ask_user_question")
        self.assertEqual(deck["version"], "4.0.0")
        self.assertEqual(deck["navigation_mode"], "mode_routed_batched")
        self.assertEqual(deck["composition_mode"], "deterministic_coverage")
        modes = deck["collection_modes"]
        self.assertEqual(modes["default"], "fast")
        self.assertTrue(modes["single_summary_confirmation"])
        self.assertEqual(modes["lawyer_sheet"]["audience_required"], "lawyer")
        self.assertEqual(modes["lawyer_sheet"]["skip_card_ids"], ["actor-authority"])
        self.assertTrue(batching := deck["batching"])
        self.assertEqual(batching["work_data_write_frequency"], "per_stage")
        self.assertTrue(batching["independent_branch_questions_may_share_batch"])
        self.assertEqual(batching["correction_loop_max"], 2)
        for forbidden in ("chat_question_answer", "display_only_widget", "download_json"):
            self.assertIn(forbidden, deck["forbidden_collection_modes"])
        self.assertEqual(batching["max_questions_per_call"], 4)
        self.assertEqual(batching["max_options_per_question"], 4)
        self.assertTrue(batching["branch_question_must_end_batch"])
        self.assertTrue(batching["repeatable_page_is_single_call"])
        self.assertTrue(deck["preflight"]["assess_before_cards"])
        card_ids = [card["base_card_id"] for card in deck["cards"]]
        self.assertEqual(len(card_ids), len(set(card_ids)))
        for required_id in (
            "testator-basic-info", "testator-capacity", "family-map",
            "lawyer-privacy-consent", "asset-declaration", "estate-distribution",
            "liability-scope", "existing-arrangements", "distribution-goals",
            "executor-custody", "will-form-and-witnesses", "guardianship-special",
            "deliverable-selection", "intake-confirmation",
            "fast-persons-enumeration", "fast-assets-enumeration",
            "fast-distribution-enumeration", "fast-assumptions-correction",
            "lawyer-sheet-intake",
        ):
            self.assertIn(required_id, card_ids)
        for removed_id in (
            "privacy-consent", "asset-scope", "real-estate-details",
            "real-estate-distribution", "generic-asset-details", "asset-distribution",
            "heir-and-share-review", "arrangement-effect-review",
            "estate-administration-review", "complex-asset-routing",
            "fast-parse-confirmation",
        ):
            self.assertNotIn(removed_id, card_ids)
        actor = next(card for card in deck["cards"] if card["base_card_id"] == "actor-authority")
        self.assertEqual({option["value"] for option in actor["ask"]["options"]}, {"self", "authorized_assistant"})
        self.assertEqual(actor["skip_in_modes"], ["lawyer_sheet"])
        persons_enum = next(card for card in deck["cards"] if card["base_card_id"] == "fast-persons-enumeration")
        self.assertEqual(persons_enum["kind"], "enumeration_fill_in")
        self.assertIn("身份证号码", persons_enum["ask"]["question"])
        for enumeration_id in ("fast-persons-enumeration", "fast-assets-enumeration", "fast-distribution-enumeration"):
            enumeration = next(card for card in deck["cards"] if card["base_card_id"] == enumeration_id)
            meta = next(option for option in enumeration["ask"]["options"] if option["value"] == "enumerate_now")
            self.assertIn("本项勿选", meta["label"])
        deliverable = next(card for card in deck["cards"] if card["base_card_id"] == "deliverable-selection")
        self.assertIn("待律师人工复核的 AI 遗嘱草案", deliverable["ask"]["question"])
        self.assertEqual(
            {option["value"] for option in deliverable["ask"]["options"]},
            {"legal_research_report", "education_content", "asset_inventory", "relationship_diagram"},
        )
        self.assertEqual(
            [option["label"] for option in deliverable["ask"]["options"][:2]],
            ["法律法规与案例检索报告", "普法文章/视频"],
        )
        capacity = next(card for card in deck["cards"] if card["base_card_id"] == "testator-capacity")
        for field in capacity["fields"][:2]:
            self.assertIn("question_self", field["ask"])
            self.assertIn("question_reporter", field["ask"])
        self.assertTrue((ROOT / modes["lawyer_sheet"]["sheet_template"]).exists())
        basic = next(card for card in deck["cards"] if card["base_card_id"] == "testator-basic-info")
        self.assertEqual(basic["kind"], "fill_in_fields")
        self.assertEqual(basic["response_mode"], "field_values")
        self.assertTrue(basic["chat_text_substitute_forbidden"])
        self.assertEqual([field["field_id"] for field in basic["fields"]], ["name", "identity_number", "address"])
        self.assertNotIn("audience-type", card_ids)
        family = next(c for c in deck["cards"] if c["base_card_id"] == "family-map")
        family_page = [q["field_id"] for q in family["page"]["questions"]]
        self.assertEqual(family_page, ["relationship", "name", "identity_number", "is_possible_heir"])
        self.assertIn("希望把财产分配给几位重要关系人", family["count_question"]["question"])
        self.assertIn("第二顺位的兄弟姐妹", family["page"]["questions"][3]["ask"]["question"])
        self.assertEqual([q["field_id"] for q in family["trailing_questions"]],
                         ["other_statutory_heirs", "fetal_share_treatment", "disqualification_status"])
        scope = next(c for c in deck["cards"] if c["base_card_id"] == "asset-declaration")["scope_question"]
        self.assertEqual([o["value"] for o in scope["options"]], ["financial_assets", "real_estate", "digital_assets"])
        self.assertIn("游戏内道具", scope["options"][2]["label"])
        assets = next(card for card in deck["cards"] if card["base_card_id"] == "asset-declaration")
        self.assertEqual(assets["kind"], "repeatable_pages")
        self.assertIn("scope_question", assets)
        self.assertEqual([q["field_id"] for q in assets["page"]["questions"]],
                         ["description", "ownership", "mortgage_or_debt"])
        distribution = next(card for card in deck["cards"] if card["base_card_id"] == "estate-distribution")
        self.assertEqual(distribution["repeat_for"], "asset-declaration.items")
        self.assertEqual([q["field_id"] for q in distribution["page"]["questions"]],
                         ["beneficiaries", "distribution_method", "attached_obligation", "substitute_arrangement"])
        family = next(card for card in deck["cards"] if card["base_card_id"] == "family-map")
        conditional = next(card for card in deck["cards"] if card["base_card_id"] == "will-form-and-witnesses")
        self.assertEqual([option["value"] for option in conditional["ask"]["options"]],
                         ["holographic", "printed", "audio_video", "notarized"])
        self.assertIn("dictated", conditional["ask"]["other_value_parsing"])
        self.assertSetEqual(
            set(conditional["conditional_fields"]),
            {"holographic", "dictated", "printed", "audio_video", "oral", "notarized", "undecided"},
        )
        for form in ("holographic", "notarized", "undecided"):
            self.assertEqual([field["field_id"] for field in conditional["conditional_fields"][form]], ["acknowledgment"], form)
        for form in ("dictated", "printed", "audio_video", "oral"):
            self.assertEqual([field["field_id"] for field in conditional["conditional_fields"][form]],
                             ["acknowledgment", "witness_arrangement"], form)
        goals = next(card for card in deck["cards"] if card["base_card_id"] == "distribution-goals")
        self.assertIn("support_or_guardianship_duty_condition", {option["value"] for option in goals["ask"]["options"]})
        confirmation = next(card for card in deck["cards"] if card["base_card_id"] == "intake-confirmation")
        self.assertTrue(confirmation["always_include_after_collection"])
        # AskUserQuestion platform limits: <=4 options per question, everywhere.
        def walk_questions(node):
            if isinstance(node, dict):
                if "options" in node and isinstance(node["options"], list):
                    self.assertLessEqual(len(node["options"]), 4, node.get("header") or node.get("question"))
                for value in node.values():
                    walk_questions(value)
            elif isinstance(node, list):
                for item in node:
                    walk_questions(item)
        walk_questions(deck["cards"])

    def test_lawyer_html_form_template_exists(self) -> None:
        form = (ROOT / "assets" / "templates" / "lawyer-intake-form.html").read_text(encoding="utf-8")
        self.assertIn("__PREFILL_JSON__", form)
        self.assertIn("保 存", form)
        self.assertIn("intake-data", form)
        self.assertIn("lawyer-intake-filled-", form)
        self.assertIn("#F9D7E4", form)

    def test_identity_number_derives_gender_and_birth_date(self) -> None:
        import intake_runtime as rt
        self.assertEqual(rt.derive_from_id_number("330102198801010011"),
                         {"birth_date": "1988-01-01", "gender": "男"})
        self.assertEqual(rt.derive_from_id_number("330102198801010022"),
                         {"birth_date": "1988-01-01", "gender": "女"})
        self.assertEqual(rt.derive_from_id_number(None), {"birth_date": None, "gender": None})
        self.assertEqual(rt.derive_heir_status("儿子"), "yes")
        self.assertEqual(rt.derive_heir_status("友人"), "unknown")

    def test_deliverable_selection_persists_all_optional_outputs(self) -> None:
        import intake_runtime as rt
        case = {
            "intake_session": {"collection_mode": "complete", "card_responses": [], "required_card_ids": []}
        }
        response = {
            "card_id": "deliverable-selection",
            "base_card_id": "deliverable-selection",
            "selected_values": [
                "legal_research_report", "education_content", "asset_inventory", "relationship_diagram"
            ],
            "field_values": None,
            "free_text": None,
            "answer_status": "answered",
            "answered_at": "2026-08-17T10:00:00+08:00",
            "confirmed": True,
        }
        result = rt.apply_response(case, response)
        self.assertEqual(
            result["output_preferences"]["requested_deliverables"],
            [
                "will_docx", "execution_guide", "legal_research_report", "education_content",
                "asset_inventory", "relationship_diagram",
            ],
        )

    def test_schema_allows_all_optional_outputs(self) -> None:
        schema = json.loads((ROOT / "assets" / "schemas" / "case.schema.json").read_text(encoding="utf-8"))
        allowed = set(schema["properties"]["output_preferences"]["properties"]["requested_deliverables"]["items"]["enum"])
        self.assertEqual(
            allowed,
            {"will_docx", "execution_guide", "legal_research_report", "education_content", "asset_inventory", "relationship_diagram"},
        )

    def test_basic_info_chat_text_substitute_is_rejected(self) -> None:
        case = copy.deepcopy(self.demo)
        for response in case["intake_session"]["card_responses"]:
            if response["base_card_id"] == "testator-basic-info":
                response.pop("field_values", None)
                response["free_text"] = "张三，男，1950 年出生，住某市某区。"
        report = validate_case(case)
        self.assertIn("BASIC_INFO_FIELD_VALUES_REQUIRED", {item["code"] for item in report["messages"]})

    def test_client_runtime_navigation_is_rejected(self) -> None:
        case = copy.deepcopy(self.demo)
        case["intake_session"]["navigation_mode"] = "client_immediate"
        report = validate_case(case)
        self.assertIn("INVALID_CARD_NAVIGATION", {item["code"] for item in report["messages"]})

    def test_fast_mode_card_ids_are_accepted(self) -> None:
        case = copy.deepcopy(self.demo)
        intake = case["intake_session"]
        intake["collection_mode"] = "fast"
        intake["required_card_ids"] = [
            "actor-authority", "fast-persons-enumeration", "fast-assets-enumeration",
            "will-form-and-witnesses", "fast-distribution-enumeration",
            "fast-assumptions-correction", "intake-confirmation",
        ]
        intake["card_responses"] = [
            {
                "card_id": card_id, "base_card_id": card_id, "selected_values": [],
                "field_values": None, "free_text": None, "answer_status": "answered",
                "answered_at": "2026-08-11T10:00:00+08:00", "confirmed": True,
            }
            for card_id in intake["required_card_ids"]
        ]
        intake["progress"] = {
            "total_questions": len(intake["required_card_ids"]),
            "completed_questions": len(intake["required_card_ids"]),
            "current_question_index": None,
        }
        report = validate_case(case)
        codes = {item["code"] for item in report["messages"]}
        self.assertNotIn("UNKNOWN_REQUIRED_CARD", codes)
        self.assertNotIn("INVALID_COLLECTION_MODE", codes)

    def test_collection_mode_validation(self) -> None:
        case = copy.deepcopy(self.demo)
        case["intake_session"]["collection_mode"] = "voice_intake"
        report = validate_case(case)
        self.assertIn("INVALID_COLLECTION_MODE", {item["code"] for item in report["messages"]})
        case = copy.deepcopy(self.demo)
        case["intake_session"]["collection_mode"] = "lawyer_sheet"
        report = validate_case(case)
        self.assertIn("LAWYER_SHEET_REQUIRES_LAWYER", {item["code"] for item in report["messages"]})
        case["audience_profile"]["audience_type"] = "lawyer"
        case["audience_profile"]["language_profile"] = "professional"
        report = validate_case(case)
        self.assertNotIn("LAWYER_SHEET_REQUIRES_LAWYER", {item["code"] for item in report["messages"]})

    def test_lawyer_sheet_requires_privacy_card(self) -> None:
        case = copy.deepcopy(self.demo)
        intake = case["intake_session"]
        intake["collection_mode"] = "lawyer_sheet"
        case["audience_profile"]["audience_type"] = "lawyer"
        case["audience_profile"]["language_profile"] = "professional"
        intake["required_card_ids"] = [c for c in intake["required_card_ids"] if c != "actor-authority"]
        intake["card_responses"] = [r for r in intake["card_responses"] if r["card_id"] != "actor-authority"]
        intake["progress"]["total_questions"] = len(intake["required_card_ids"])
        intake["progress"]["completed_questions"] = len([r for r in intake["card_responses"] if r.get("confirmed")])
        report = validate_case(case)
        codes = {item["code"] for item in report["messages"]}
        self.assertIn("LAWYER_PRIVACY_CONSENT_REQUIRED", codes)
        intake["required_card_ids"].insert(0, "lawyer-privacy-consent")
        intake["card_responses"].insert(0, {
            "card_id": "lawyer-privacy-consent", "base_card_id": "lawyer-privacy-consent",
            "selected_values": ["accepted", "sensitive_data_acknowledged"],
            "field_values": None, "free_text": None, "answer_status": "answered",
            "answered_at": "2026-08-10T08:57:00+08:00", "confirmed": True,
        })
        intake["progress"]["total_questions"] = len(intake["required_card_ids"])
        intake["progress"]["completed_questions"] = len([r for r in intake["card_responses"] if r.get("confirmed")])
        report = validate_case(case)
        self.assertNotIn("LAWYER_PRIVACY_CONSENT_REQUIRED", {item["code"] for item in report["messages"]})

    def test_repeatable_instance_ids_are_resolved_and_unknown_rejected(self) -> None:
        case = copy.deepcopy(self.demo)
        self.assertTrue(any(card_id.endswith("-1") for card_id in case["intake_session"]["required_card_ids"]))
        report = validate_case(case)
        self.assertNotIn("UNKNOWN_REQUIRED_CARD", {item["code"] for item in report["messages"]})
        case["intake_session"]["required_card_ids"].append("bogus-card-9")
        case["intake_session"]["progress"]["total_questions"] = len(case["intake_session"]["required_card_ids"])
        report = validate_case(case)
        self.assertIn("UNKNOWN_REQUIRED_CARD", {item["code"] for item in report["messages"]})

    def test_option_value_outside_deck_vocabulary_is_rejected(self) -> None:
        case = copy.deepcopy(self.demo)
        for response in case["intake_session"]["card_responses"]:
            if response["card_id"] == "guardianship-special":
                response["selected_values"] = ["not_applicable"]
        report = validate_case(case)
        self.assertIn("CARD_OPTION_VALUE_UNKNOWN", {item["code"] for item in report["messages"]})

    def test_demo_passes_deterministic_validation(self) -> None:
        report = validate_case(copy.deepcopy(self.demo))
        self.assertTrue(report["valid"], report)
        self.assertEqual(report["counts"]["error"], 0)

    def test_audience_language_mismatch_is_blocked(self) -> None:
        case = copy.deepcopy(self.demo)
        case["audience_profile"]["language_profile"] = "professional"
        report = validate_case(case)
        self.assertFalse(report["valid"])
        self.assertIn("AUDIENCE_LANGUAGE_MISMATCH", {item["code"] for item in report["messages"]})

    def test_research_gate_blocks_output(self) -> None:
        case = copy.deepcopy(self.demo)
        case["legal_research"]["status"] = "in_progress"
        report = validate_case(case)
        self.assertFalse(report["valid"])
        self.assertIn("RESEARCH_GATE_NOT_PASSED", {item["code"] for item in report["messages"]})

    def test_missing_capacity_card_blocks_research(self) -> None:
        case = copy.deepcopy(self.demo)
        case["intake_session"]["card_responses"] = [
            item for item in case["intake_session"]["card_responses"]
            if item["card_id"] != "testator-capacity"
        ]
        case["intake_session"]["progress"]["completed_questions"] = len(case["intake_session"]["card_responses"])
        report = validate_case(case)
        self.assertFalse(report["valid"])
        self.assertIn("INCOMPLETE_CARD_DECK", {item["code"] for item in report["messages"]})

    def test_sufficient_uploaded_information_skips_corresponding_card(self) -> None:
        case = copy.deepcopy(self.demo)
        intake = case["intake_session"]
        intake["card_responses"] = [item for item in intake["card_responses"] if item["card_id"] != "liability-scope"]
        intake["required_card_ids"].remove("liability-scope")
        intake["skipped_base_card_ids"].append("liability-scope")
        intake["coverage_assessment"]["topics"]["liabilities"] = "sufficient"
        remaining = len(intake["required_card_ids"])
        intake["progress"] = {"total_questions": remaining, "completed_questions": remaining, "current_question_index": None}
        report = validate_case(case)
        self.assertTrue(report["valid"], report)

    def test_rule_pack_blocks_ineligible_witness(self) -> None:
        case = copy.deepcopy(self.demo)
        case["will_execution_plan"]["witnesses"][0]["is_heir_or_legatee"] = "yes"
        report = evaluate_rules(case)
        self.assertEqual(report["counts"]["BLOCKED"], 1)
        self.assertIn("INELIGIBLE_WITNESS", {item["code"] for item in report["results"]})

    def test_template_hash_mismatch_is_blocked(self) -> None:
        case = copy.deepcopy(self.demo)
        case["will_document"]["template_sha256"] = "0" * 64
        report = validate_case(case)
        self.assertFalse(report["valid"])
        self.assertIn("WILL_TEMPLATE_MISMATCH", {item["code"] for item in report["messages"]})

    def test_will_generator_preserves_package_parts(self) -> None:
        template = ROOT / "assets" / "templates" / "will-template.docx"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "will.docx"
            result = build_will_docx(copy.deepcopy(self.demo), output)
            self.assertEqual(result["template_sha256"], TEMPLATE_SHA256)
            with zipfile.ZipFile(template) as source, zipfile.ZipFile(output) as generated:
                self.assertEqual(source.namelist(), generated.namelist())
                for name in source.namelist():
                    if name != "word/document.xml":
                        self.assertEqual(source.read(name), generated.read(name), name)
                root = ET.fromstring(generated.read("word/document.xml"))
                namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
                paragraphs = ["".join(node.text or "" for node in paragraph.iter(namespace + "t")) for paragraph in root.iter(namespace + "p")]
                for heading in HEADINGS.values():
                    self.assertIn(heading, paragraphs)

    def test_full_packet_contains_required_deliverables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = build_packet(copy.deepcopy(self.demo), Path(tmp))
            expected = set(BASE_PACKET_FILES + (WILL_FILE,))
            self.assertEqual({Path(path).name for path in result["files"]}, expected)
            self.assertTrue(result["preparation_only"])
            self.assertFalse(result["signature_ready"])
            self.assertNotIn("case-snapshot.json", expected)
            self.assertNotIn("01-case-overview.md", expected)
            self.assertNotIn("06-professional-handoff.md", expected)
            diagram = (Path(tmp) / OPTIONAL_PACKET_FILES["relationship_diagram"]).read_text(encoding="utf-8")
            self.assertTrue(OPTIONAL_PACKET_FILES["relationship_diagram"].endswith(".svg"))
            self.assertTrue(diagram.lstrip().startswith("<svg"))
            self.assertIn("人物", diagram)
            self.assertIn("财产", diagram)
            self.assertIn("重要关系人A", diagram)
            self.assertIn("某市住宅一套", diagram)
            self.assertIn("拟继承/受益", diagram)
            self.assertIn("#F9D7E4", diagram)
            self.assertNotIn("mermaid", diagram)
            inventory = (Path(tmp) / OPTIONAL_PACKET_FILES["asset_inventory"]).read_text(encoding="utf-8")
            self.assertIn("资产与债务清单", inventory)
            self.assertIn("权利人与份额", inventory)
            self.assertIn("某市住宅一套", inventory)
            self.assertIn("房产", inventory)
            self.assertNotIn("record_type", inventory)
            guide = (Path(tmp) / "03-execution-guide.md").read_text(encoding="utf-8")
            self.assertIn("🧭 一页行动路线", guide)
            self.assertIn("还需要判断的事项", guide)
            self.assertIn("✍️ 签署当天", guide)
            self.assertIn("📦 签署后", guide)
            self.assertIn("打印遗嘱", guide)
            self.assertIn("遗嘱人和见证人在每一页签名", guide)
            self.assertIn("| 顺序 | 节点 | 必须做什么 |", guide)
            for omitted in ("工作数据：", "用户类型：", "规则包：", "使用方法：", "负责人", "状态", "[REVIEW_REQUIRED]", "[阻断]", "[非阻断]", "即使平台不显示底色", "02-legal-rule-evaluation.md"):
                self.assertNotIn(omitted, guide)
            self.assertFalse((Path(tmp) / "04-education-links.md").exists())
            self.assertFalse((Path(tmp) / "05-ai-judgment-notice.md").exists())
            self.assertEqual(result["conversation_education_links"][0]["name"], "最高法发布民法典遗产管理人制度典型案例")
            self.assertTrue(result["conversation_education_links"][0]["main_content"])
            self.assertTrue(result["conversation_education_links"][0]["link"].startswith("https://"))
            self.assertLess(len(guide.splitlines()), 100)

    def test_unselected_optional_deliverables_are_not_generated(self) -> None:
        case = copy.deepcopy(self.demo)
        core = ["will_docx", "execution_guide"]
        case["output_preferences"]["requested_deliverables"] = core
        selection = next(
            item for item in case["intake_session"]["card_responses"]
            if item["card_id"] == "deliverable-selection"
        )
        selection["selected_values"] = []
        with tempfile.TemporaryDirectory() as tmp:
            result = build_packet(case, Path(tmp))
            names = {Path(path).name for path in result["files"]}
            for key in ("relationship_diagram", "asset_inventory", "legal_research_report"):
                self.assertNotIn(OPTIONAL_PACKET_FILES[key], names)
                self.assertFalse((Path(tmp) / OPTIONAL_PACKET_FILES[key]).exists())
            self.assertEqual(result["conversation_education_links"], [])


if __name__ == "__main__":
    unittest.main()
