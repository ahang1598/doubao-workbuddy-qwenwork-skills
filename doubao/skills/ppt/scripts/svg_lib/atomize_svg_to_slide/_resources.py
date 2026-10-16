"""Local SVG references and their transitive dependency closure."""

from __future__ import annotations

import copy
from functools import lru_cache
import re
import xml.etree.ElementTree as ET

URL_REF = re.compile(r"""url\(\s*['"]?#([^\s)'";]+)['"]?\s*\)""")
XLINK = "{http://www.w3.org/1999/xlink}href"


def name(node):
    return node.tag.split("}")[-1]


def references(node):
    found = set()
    for item in node.iter():
        for key, value in item.attrib.items():
            found.update(URL_REF.findall(value))
            if key in ("href", XLINK) and value.startswith("#"):
                found.add(value[1:])
    return found


@lru_cache(maxsize=64)
def resource_index(defs):
    root = ET.fromstring(defs) if defs else ET.Element("defs")
    return {node.get("id"): node for node in root.iter() if node.get("id")}


def resource_closure(source, defs):
    """Copy each required definition once, including href/use/filter chains."""
    if not defs:
        return ""
    node = ET.fromstring(source) if isinstance(source, str) else source
    index = resource_index(defs)
    supplied = {item.get("id") for item in node.iter() if item.get("id")}
    needed, pending = set(), list(references(node))
    while pending:
        key = pending.pop()
        if key in needed or key in supplied:
            continue
        needed.add(key)
        if key in index:
            pending.extend(references(index[key]) - needed)
    # Keep an ancestor definition only once when a descendant ID is referenced.
    root = ET.fromstring(defs)
    result = ET.Element("defs")

    def collect(parent):
        for child in parent:
            if child.get("id") in needed:
                overlap = supplied & {item.get("id") for item in child.iter() if item.get("id")}
                if overlap:
                    raise ValueError("SVG resource ID collides with source content: " + ", ".join(sorted(overlap)))
                result.append(copy.deepcopy(child))
            else:
                collect(child)

    collect(root)
    return ET.tostring(result, encoding="unicode").replace(" />", "/>") if len(result) else ""


def inherited_resource(node, index):
    """Resolve resource attribute inheritance without losing the original tree."""
    attrs = dict(node.attrib)
    current = node
    seen = set()
    while current.get("href", current.get(XLINK, "")):
        href = current.get("href", current.get(XLINK, ""))
        if not href.startswith("#") or href[1:] in seen or href[1:] not in index:
            return None
        seen.add(href[1:])
        current = index[href[1:]]
        for key, value in current.attrib.items():
            attrs.setdefault(key, value)
    result = copy.deepcopy(node)
    result.attrib.clear()
    result.attrib.update(attrs)
    return result
