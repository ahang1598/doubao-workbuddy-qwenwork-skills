from __future__ import annotations

import hashlib
import io
import json
import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "openai-templates"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
ZIP_SIGNATURE = b"PK\x03\x04"
MAX_PREVIEW_EDGE_PX = 800
MAX_PLUGIN_ARCHIVE_BYTES = 26 * 1024 * 1024
MAX_PLUGIN_ARCHIVE_ENTRIES = 5_000
EXPECTED_BINARY_ASSET_SET_SHA256 = (
    "ee1a1469054c77c71dd54a5bc36122fa679a9b639daddf51f20a057fcafac136"
)
TEMPLATES = (
    (
        "artifact-template-analytics-dashboard",
        "Analytics Dashboard",
        "spreadsheet",
        "xlsx",
    ),
    ("artifact-template-business-review", "Business Review", "presentation", "pptx"),
    (
        "artifact-template-design-report",
        "Design Report",
        "document",
        "docx",
    ),
    (
        "artifact-template-experiment-analysis",
        "Experiment Analysis",
        "document",
        "docx",
    ),
    (
        "artifact-template-financial-budget",
        "Financial Budget",
        "spreadsheet",
        "xlsx",
    ),
    (
        "artifact-template-investment-committee-memo",
        "Investment Committee Memo",
        "document",
        "docx",
    ),
    ("artifact-template-legal-memorandum", "Legal Memorandum", "document", "docx"),
    (
        "artifact-template-market-trends-report",
        "Market Trends Report",
        "presentation",
        "pptx",
    ),
    (
        "artifact-template-minimal-letterhead",
        "Minimal Letterhead",
        "document",
        "docx",
    ),
    (
        "artifact-template-operating-calendar",
        "Operating Calendar",
        "spreadsheet",
        "xlsx",
    ),
    (
        "artifact-template-operating-review",
        "Operating Review",
        "presentation",
        "pptx",
    ),
    (
        "artifact-template-project-kickoff",
        "Project Kickoff",
        "presentation",
        "pptx",
    ),
    ("artifact-template-project-tracker", "Project Tracker", "spreadsheet", "xlsx"),
    ("artifact-template-sales-pipeline", "Sales Pipeline", "spreadsheet", "xlsx"),
    (
        "artifact-template-simple-dark-mode",
        "Simple Dark Mode",
        "presentation",
        "pptx",
    ),
    (
        "artifact-template-simple-light-mode",
        "Simple Light Mode",
        "presentation",
        "pptx",
    ),
    (
        "artifact-template-strategy-memorandum",
        "Strategy Memorandum",
        "document",
        "docx",
    ),
    ("artifact-template-system-design", "System Design", "document", "docx"),
    (
        "artifact-template-team-alignment",
        "Team Alignment",
        "presentation",
        "pptx",
    ),
    (
        "artifact-template-three-statement-forecast",
        "Three-Statement Forecast",
        "spreadsheet",
        "xlsx",
    ),
)


def test_openai_templates_plugin_contract() -> None:
    manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())
    app_manifest = json.loads((PLUGIN_ROOT / ".app.json").read_text())
    marketplace = json.loads((REPO_ROOT / "marketplace.json").read_text())

    assert manifest["name"] == "openai-templates"
    assert manifest["skills"] == "./skills/"
    assert manifest["apps"] == "./.app.json"
    assert manifest["interface"]["displayName"] == "Default templates"
    assert manifest["interface"]["shortDescription"] == (
        "Default templates for documents, spreadsheets, and presentations"
    )
    assert manifest["interface"]["defaultPrompt"] == [
        "Create a document using the Minimal Letterhead template",
        "Create an Analytics Dashboard spreadsheet using the Analytics Dashboard template",
        "Create a planning presentation with the Team Alignment template",
    ]
    assert app_manifest == {
        "apps": {
            "default_templates": {
                "id": "connector_openai_default_templates",
                "required": True,
            },
        }
    }
    assert {
        "name": "openai-templates",
        "source": {
            "source": "local",
            "path": "./plugins/openai-templates",
        },
        "policy": {
            "installation": "AVAILABLE",
            "authentication": "ON_USE",
        },
        "category": "Productivity",
    } in marketplace["plugins"]


def test_openai_templates_are_packaged_for_chatgpt() -> None:
    package_files = sorted(
        path
        for path in PLUGIN_ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
    assert len(package_files) < MAX_PLUGIN_ARCHIVE_ENTRIES

    archive_buffer = io.BytesIO()
    with ZipFile(archive_buffer, "w", compression=ZIP_DEFLATED) as archive:
        for path in package_files:
            archive.write(path, path.relative_to(PLUGIN_ROOT))
    assert archive_buffer.tell() < MAX_PLUGIN_ARCHIVE_BYTES

    assert sorted(path.name for path in (PLUGIN_ROOT / "skills").iterdir()) == sorted(
        name for name, _display_name, _kind, _extension in TEMPLATES
    )
    assert {
        kind: sum(template_kind == kind for _, _, template_kind, _ in TEMPLATES)
        for kind in ("document", "presentation", "spreadsheet")
    } == {"document": 7, "presentation": 7, "spreadsheet": 6}

    binary_asset_set = hashlib.sha256()
    for name, display_name, kind, extension in TEMPLATES:
        skill_root = PLUGIN_ROOT / "skills" / name
        manifest = json.loads((skill_root / "artifact-template.json").read_text())
        metadata = (skill_root / "agents" / "openai.yaml").read_text()
        skill = (skill_root / "SKILL.md").read_text()
        assets_root = skill_root / "assets"
        preview_path = assets_root / "preview.png"
        reference_path = assets_root / f"reference.{extension}"

        assert manifest == {
            "schemaVersion": 1,
            "kind": kind,
            "reference": f"assets/reference.{extension}",
            "preview": "assets/preview.png",
        }
        assert sorted(path.name for path in assets_root.iterdir()) == [
            "preview.png",
            f"reference.{extension}",
        ]
        assert f"\nname: {name}\n" in skill
        assert f'description: "Create a {kind} using the {display_name} template' in skill
        assert f'display_name: "{display_name}"' in metadata
        assert 'icon_large: "./assets/preview.png"' in metadata
        assert f'default_prompt: "Create a new {kind} with this template."' in metadata
        assert metadata.endswith("policy:\n  allow_implicit_invocation: false\n")
        assert "plugin://" not in skill
        assert "prompt-advertised preinstalled" in skill
        assert "artifact_handoff.prepare_artifact_generation" not in skill
        preview = preview_path.read_bytes()
        assert preview.startswith(PNG_SIGNATURE)
        width, height = struct.unpack(">II", preview[16:24])
        assert width > 0 and height > 0
        assert max(width, height) <= MAX_PREVIEW_EDGE_PX

        reference = reference_path.read_bytes()
        assert reference.startswith(ZIP_SIGNATURE)
        _assert_sanitized_office_archive(reference, name)

        for binary_path, contents in (
            (preview_path, preview),
            (reference_path, reference),
        ):
            binary_asset_set.update(binary_path.relative_to(PLUGIN_ROOT).as_posix().encode())
            binary_asset_set.update(b"\0")
            binary_asset_set.update(hashlib.sha256(contents).digest())

    assert binary_asset_set.hexdigest() == EXPECTED_BINARY_ASSET_SET_SHA256


def _assert_sanitized_office_archive(archive: bytes, label: str) -> None:
    with ZipFile(io.BytesIO(archive)) as package:
        names = package.namelist()
        assert all(not name.lower().startswith("customxml/") for name in names)

        for name in names:
            contents = package.read(name)
            if name == "docProps/core.xml":
                root = ET.fromstring(contents)
                private_fields = {
                    "creator",
                    "lastModifiedBy",
                    "created",
                    "modified",
                    "lastPrinted",
                    "revision",
                }
                for element in root.iter():
                    local_name = element.tag.rsplit("}", 1)[-1]
                    if local_name in private_fields:
                        assert not (element.text or "").strip(), f"{label} retains {local_name}"

            if name.endswith((".xml", ".rels")):
                assert not re.search(rb"\bw:rsid(?:[A-Za-z]+)?=", contents), (
                    f"{label}:{name} retains Word editing metadata"
                )
                assert b"x15ac:absPath" not in contents
                assert not re.search(
                    rb"(?:file:///)?(?:/Users/|/home/|[A-Za-z]:[\\/](?:Users|Documents and Settings)[\\/])",
                    contents,
                    re.IGNORECASE,
                ), f"{label}:{name} retains a local path"

            if contents.startswith(ZIP_SIGNATURE):
                _assert_sanitized_office_archive(contents, f"{label}:{name}")
