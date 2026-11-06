import json
import os
import tempfile
import pytest

from scripts.content_builder import ContentBlock, save_content


def test_save_content_basic():
    blocks = [
        ContentBlock(type="h1", text="Hello World"),
        ContentBlock(type="body", text="This is a paragraph."),
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        path = f.name
    try:
        save_content(blocks, path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data == [
            {"type": "h1", "text": "Hello World"},
            {"type": "body", "text": "This is a paragraph."},
        ]
    finally:
        os.unlink(path)


def test_save_content_omits_none_fields():
    blocks = [ContentBlock(type="divider")]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        path = f.name
    try:
        save_content(blocks, path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data == [{"type": "divider"}]
    finally:
        os.unlink(path)


def test_save_content_special_characters():
    blocks = [
        ContentBlock(type="body", text='He said "Hello"'),
        ContentBlock(type="body", text="Path: C:\\Users\\name"),
        ContentBlock(type="body", text="Line 1\nLine 2\tTabbed"),
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        path = f.name
    try:
        save_content(blocks, path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data[0]["text"] == 'He said "Hello"'
        assert data[1]["text"] == "Path: C:\\Users\\name"
        assert data[2]["text"] == "Line 1\nLine 2\tTabbed"
    finally:
        os.unlink(path)


def test_save_content_table_and_chart():
    blocks = [
        ContentBlock(
            type="table",
            headers=["Country", "Wins"],
            rows=[["Brazil", "5"], ["Germany", "4"]],
            caption="World Cup winners",
        ),
        ContentBlock(
            type="chart",
            chart_type="bar",
            labels=["Q1", "Q2"],
            datasets=[{"label": "Revenue", "values": [100, 200]}],
            title="Revenue",
        ),
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        path = f.name
    try:
        save_content(blocks, path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data[0]["type"] == "table"
        assert data[0]["headers"] == ["Country", "Wins"]
        assert data[0]["rows"] == [["Brazil", "5"], ["Germany", "4"]]
        assert data[0]["caption"] == "World Cup winners"
        assert data[1]["type"] == "chart"
        assert data[1]["chart_type"] == "bar"
        assert data[1]["datasets"][0]["values"] == [100, 200]
    finally:
        os.unlink(path)


def test_save_content_creates_parent_and_leaves_no_partial_file(tmp_path):
    output = tmp_path / "job-id" / "content.json"

    save_content([ContentBlock(type="body", text="isolated")], str(output))

    assert json.loads(output.read_text(encoding="utf-8")) == [
        {"type": "body", "text": "isolated"}
    ]
    assert list(output.parent.iterdir()) == [output]
