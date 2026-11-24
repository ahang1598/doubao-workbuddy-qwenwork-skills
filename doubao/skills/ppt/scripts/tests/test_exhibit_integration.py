"""Exercise the imported Exhibit library against the current PPT runtime."""

from xml.etree import ElementTree as ET

import pytest

from scripts.svg_lib.exhibit import Exhibit, columns, exhibit_help, frame, pie_of_pie
from scripts.svg_lib.exhibit._palette import roles


@pytest.mark.parametrize("topic", [None, "api", "standalone", "atomize", "columns"])
def test_exhibit_help_is_available(topic):
    assert len(exhibit_help(topic)) > 100


def test_exhibit_composes_a_page_with_native_chart_elements():
    page = frame("Quarterly sales grew", "Sales, USD thousands", source=["Company report"])
    exhibit = Exhibit(w=600, h=300, palette="mckinsey_blue")
    columns(exhibit, exhibit.body, ["Q1", "Q2", "Q3"], [("Sales", [10, 20, 30])], cagr=False)

    result = page.publish(ex=exhibit)

    assert result["ok"], result
    root = ET.fromstring(result["page_xml"])
    assert root.findall(".//{*}shape")
    assert not root.findall(".//{*}embed")
    content = " ".join(root.itertext())
    assert all(label in content for label in ("Quarterly sales grew", "Q1", "Q2", "Q3"))


def test_pie_hatches_survive_current_schema_validation():
    exhibit = Exhibit(w=880, h=330, palette="mckinsey_blue")
    pie_of_pie(exhibit, exhibit.body, [("门店", 46), ("线上", 38), ("批发", 16)],
               "线上", [("天猫", 60), ("京东", 22), ("抖音", 18)])

    fragment = exhibit.to_slide(40, 120)

    assert not exhibit._issues
    root = ET.fromstring(fragment)
    patterns = root.findall(".//{*}fillPattern")
    assert len(patterns) == 4
    assert all(pattern.get("type") == "wd-up-diag" for pattern in patterns)
    assert all(float(border.get("width", "1")) > 0 for border in root.findall(".//{*}border"))


@pytest.mark.parametrize("palette", ["mckinsey_blue", "claret_oxford", "exec_navy", "sage_review"])
def test_exhibit_palette_roles_are_available(palette):
    assert {"main", "accent", "second", "light", "deep", "neg"} <= roles(palette).keys()
