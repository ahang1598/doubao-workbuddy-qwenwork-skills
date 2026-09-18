import argparse
import base64
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urljoin, urlsplit

from docx import Document
from lxml import etree


def write_output_file(path, content):
    output_path = Path(path).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    sys.stdout.write(content)


TRANSITIONAL_DOCUMENT_NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
}
STRICT_DOCUMENT_NS = {
    "w": "http://purl.oclc.org/ooxml/wordprocessingml/main",
    "r": "http://purl.oclc.org/ooxml/officeDocument/relationships",
    "a": "http://purl.oclc.org/ooxml/drawingml/main",
    "wp": "http://purl.oclc.org/ooxml/drawingml/wordprocessingDrawing",
    "pic": "http://purl.oclc.org/ooxml/drawingml/picture",
    "m": "http://purl.oclc.org/ooxml/officeDocument/math",
}
NS = {
    **TRANSITIONAL_DOCUMENT_NS,
    "v": "urn:schemas-microsoft-com:vml",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "rels": "http://schemas.openxmlformats.org/package/2006/relationships",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "ep": "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
    "w15": "http://schemas.microsoft.com/office/word/2012/wordml",
    "wp14": "http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing",
    "wpg": "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup",
    "wpi": "http://schemas.microsoft.com/office/word/2010/wordprocessingInk",
    "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
}
W = f"{{{NS['w']}}}"
R = f"{{{NS['r']}}}"
REL_TYPE_PREFIXES = (
    f"{TRANSITIONAL_DOCUMENT_NS['r']}/",
    f"{STRICT_DOCUMENT_NS['r']}/",
)
SPECIAL_TAGS = [
    "w:hyperlink",
    "w:bookmarkStart",
    "w:bookmarkEnd",
    "w:commentRangeStart",
    "w:commentRangeEnd",
    "w:commentReference",
    "w:fldSimple",
    "w:fldChar",
    "w:fldData",
    "w:instrText",
    "w:footnoteReference",
    "w:endnoteReference",
    "w:delText",
    "w:ins",
    "w:del",
    "w:moveFrom",
    "w:moveTo",
    "w:moveFromRangeStart",
    "w:moveFromRangeEnd",
    "w:moveToRangeStart",
    "w:moveToRangeEnd",
    "w:pPrChange",
    "w:rPrChange",
    "w:tblPrChange",
    "w:tblGridChange",
    "w:trPrChange",
    "w:tcPrChange",
    "w:sectPrChange",
    "w:numberingChange",
    "w:cellIns",
    "w:cellDel",
    "w:cellMerge",
    "w:customXmlInsRangeStart",
    "w:customXmlInsRangeEnd",
    "w:customXmlDelRangeStart",
    "w:customXmlDelRangeEnd",
    "w:customXmlMoveFromRangeStart",
    "w:customXmlMoveFromRangeEnd",
    "w:customXmlMoveToRangeStart",
    "w:customXmlMoveToRangeEnd",
    "w:sdt",
    "w:drawing",
    "w:pict",
    "w:object",
    "w:altChunk",
    "m:oMath",
    "m:oMathPara",
]
KEY_PARTS = [
    "word/document.xml",
    "word/styles.xml",
    "word/numbering.xml",
    "word/settings.xml",
    "word/theme/theme1.xml",
    "word/fontTable.xml",
    "_rels/.rels",
    "word/_rels/document.xml.rels",
    "docProps/core.xml",
    "docProps/app.xml",
    "word/comments.xml",
    "word/footnotes.xml",
    "word/endnotes.xml",
]
MODE_NAMES = {
    0: "content_markdown",
    1: "sections",
    2: "paragraphs",
    3: "runs",
    4: "styles",
    5: "tables",
    6: "objects",
    7: "headers_footers",
    8: "numbering",
    9: "special_parts",
}
MODEL_DROP_KEYS = {"xml", "raw_rPr", "sectPr", "paragraph_properties", "run_properties", "table_properties"}
BODY_TEXT_POLICY = "full text is emitted without truncation"


class AltChunkHTMLParser(HTMLParser):
    BLOCK_TAGS = {
        "address",
        "article",
        "blockquote",
        "br",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "p",
        "section",
        "table",
        "tr",
    }
    SKIP_TAGS = {"script", "style"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
        elif not self.skip_depth and tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self.skip_depth -= 1
        elif not self.skip_depth and tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip_depth:
            self.parts.append(data)

    def text(self):
        value = "".join(self.parts).replace("\r\n", "\n").replace("\r", "\n")
        value = re.sub(r"[^\S\n]+", " ", value)
        return re.sub(r"\n{3,}", "\n\n", value).strip()


def wtag(name):
    return W + name


def qname(name):
    value = etree.QName(name)
    prefixes = {uri: prefix for prefix, uri in NS.items()}
    prefix = prefixes.get(value.namespace)
    return f"{prefix}:{value.localname}" if prefix else value.localname


def xml_bytes(node):
    return etree.tostring(node, encoding="utf-8").decode("utf-8")


def configure_document_namespaces(root):
    global W, R
    namespace = etree.QName(root).namespace
    if namespace == TRANSITIONAL_DOCUMENT_NS["w"]:
        document_ns = TRANSITIONAL_DOCUMENT_NS
    elif namespace == STRICT_DOCUMENT_NS["w"]:
        document_ns = STRICT_DOCUMENT_NS
    else:
        raise ValueError(f"Unsupported WordprocessingML namespace: {namespace}")
    NS.update(document_ns)
    W = f"{{{NS['w']}}}"
    R = f"{{{NS['r']}}}"
    return document_ns is STRICT_DOCUMENT_NS


def is_removed_revision(node):
    for item in (node, *node.iterancestors()):
        if item.tag in {wtag("del"), wtag("moveFrom")}:
            return True
        if item.tag == wtag("tr") and item.find("w:trPr/w:del", namespaces=NS) is not None:
            return True
    return False


def text_node_value(node):
    if node.tag in (wtag("t"), wtag("delText")):
        return node.text or ""
    if node.tag == wtag("tab"):
        return "\t"
    if node.tag in (wtag("br"), wtag("cr")):
        return "\n"
    if node.tag == wtag("noBreakHyphen"):
        return "-"
    if node.tag == wtag("softHyphen"):
        return "\u00ad"
    if node.tag == wtag("sym"):
        font = node.get(W + "font")
        char = node.get(W + "char")
        return f"<symbol font={font!r} char={char!r}>"
    return ""


def text_value(node, include_removed=False):
    parts = []
    paragraph_seen = False
    for item in node.iter():
        if not include_removed and is_removed_revision(item):
            continue
        if item.tag == wtag("p"):
            if paragraph_seen:
                parts.append("\n")
            paragraph_seen = True
        else:
            parts.append(text_node_value(item))
    return "".join(parts)


def run_text_value(run, include_removed=False):
    if not include_removed and is_removed_revision(run):
        return ""
    parts = []
    for item in run.iter():
        owners = item.xpath("ancestor::w:r[1]", namespaces=NS)
        if owners and owners[0] is not run:
            continue
        if not include_removed and is_removed_revision(item):
            continue
        parts.append(text_node_value(item))
    return "".join(parts)


def attrs(node):
    return {qname(key): value for key, value in node.attrib.items()}


def attr(node, name):
    return None if node is None else node.get(name)


def child(node, path):
    return None if node is None else node.find(path, namespaces=NS)


def children(node, path):
    return node.findall(path, namespaces=NS)


def half_points(value):
    return None if value is None else int(value) / 2


def twips(value):
    return None if value is None else int(value) / 20


def int_twips(value):
    return None if value is None else int(value)


def rel_type(value):
    if value is None:
        return None
    for prefix in REL_TYPE_PREFIXES:
        if value.startswith(prefix):
            return value[len(prefix) :]
    return value


def content_type_maps(zf):
    content_types = parse_xml(zf.read("[Content_Types].xml"))
    type_by_ext = {
        item.get("Extension"): item.get("ContentType")
        for item in content_types.findall("{http://schemas.openxmlformats.org/package/2006/content-types}Default")
    }
    type_by_part = {
        item.get("PartName").lstrip("/"): item.get("ContentType")
        for item in content_types.findall("{http://schemas.openxmlformats.org/package/2006/content-types}Override")
    }
    return type_by_ext, type_by_part


def content_type_for(name, type_by_ext, type_by_part):
    filename = PurePosixPath(name).name
    extension = filename.rsplit(".", 1)[1] if "." in filename else ""
    return type_by_part.get(name) or type_by_ext.get(extension)


def parse_xml(data):
    parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True)
    return etree.fromstring(data, parser=parser)


def alternate_content_branch(node):
    for choice in children(node, "mc:Choice"):
        required = (choice.get("Requires") or "").split()
        if all(choice.nsmap.get(prefix) in set(NS.values()) for prefix in required):
            return choice
    fallback = child(node, "mc:Fallback")
    return fallback if fallback is not None else child(node, "mc:Choice")


def resolve_alternate_content(root):
    for node in reversed(root.xpath(".//mc:AlternateContent", namespaces=NS)):
        parent = node.getparent()
        branch = alternate_content_branch(node)
        index = parent.index(node)
        if branch is not None:
            for item in list(branch):
                parent.insert(index, item)
                index += 1
        parent.remove(node)
    return root


def alt_chunk_text(data, content_type):
    content_type = (content_type or "").lower()
    encoding = "utf-8-sig"
    if data.startswith((b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")):
        encoding = "utf-32"
    elif data.startswith((b"\xff\xfe", b"\xfe\xff")):
        encoding = "utf-16"
    else:
        match = re.search(r"(?:^|;)\s*charset\s*=\s*[\"']?([^;\"'\s]+)", content_type)
        if match is None and "html" in content_type:
            match = re.search(
                rb"charset\s*=\s*[\"']?\s*([a-z0-9._:-]+)",
                data[:4096],
                re.IGNORECASE,
            )
        if match is not None:
            encoding = match.group(1)
            if type(encoding) is bytes:
                encoding = encoding.decode("ascii")
    if "html" in content_type:
        parser = AltChunkHTMLParser()
        parser.feed(data.decode(encoding))
        return parser.text()
    if "xml" in content_type:
        return "\n".join(
            text.strip()
            for text in parse_xml(data).itertext()
            if text.strip()
        )
    if content_type.startswith("text/"):
        return data.decode(encoding).strip()
    return ""


def materialize_alt_chunks(root, zf, relationships):
    type_by_ext, type_by_part = content_type_maps(zf)
    names = set(zf.namelist())
    for node in root.xpath(".//w:altChunk", namespaces=NS):
        relationship = relationships.get(node.get(R + "id"), {})
        target = relationship.get("resolved_target")
        content_type = content_type_for(target, type_by_ext, type_by_part) if target else None
        text = alt_chunk_text(zf.read(target), content_type) if target in names else ""
        if not text:
            text = f"[altChunk part={target or 'unresolved'} type={content_type or 'unknown'}]"
        parent = node.getparent()
        index = parent.index(node)
        for value in (line.strip() for line in text.splitlines()):
            if not value:
                continue
            paragraph = etree.Element(wtag("p"))
            run = etree.SubElement(paragraph, wtag("r"))
            etree.SubElement(run, wtag("t")).text = value
            parent.insert(index, paragraph)
            index += 1
        parent.remove(node)
    return root


def on_off_value(node):
    if node is None:
        return None
    value = node.get(W + "val")
    return value is None or value.lower() not in {"0", "false", "off", "no"}


def safe_export_path(asset_dir, member_name):
    normalized = member_name.replace("\\", "/")
    relative = PurePosixPath(normalized)
    if relative.is_absolute() or re.match(r"^[A-Za-z]:", normalized) or ".." in relative.parts:
        raise ValueError(f"Unsafe OOXML member path: {member_name}")
    root = Path(asset_dir).expanduser().resolve()
    destination = root.joinpath(*relative.parts).resolve()
    if destination != root and root not in destination.parents:
        raise ValueError(f"OOXML member escapes asset directory: {member_name}")
    return destination


def part_xml(zf, name):
    return xml_bytes(parse_xml(zf.read(name)))


def locate_soffice():
    if os.environ.get("READ_PY_DISABLE_LIBREOFFICE"):
        return None
    choices = []

    # An explicit path is useful for portable and non-standard installations.
    for variable in ("READ_PY_LIBREOFFICE", "LIBREOFFICE_PATH", "SOFFICE_PATH"):
        value = os.environ.get(variable)
        if value:
            choices.append(value)

    commands = ("soffice.com", "soffice", "libreoffice") if sys.platform == "win32" else ("soffice", "libreoffice")
    for command in commands:
        found = shutil.which(command)
        if found:
            choices.append(found)

    if sys.platform == "win32":
        program_files = [
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramW6432"),
            os.environ.get("ProgramFiles(x86)"),
            os.environ.get("LOCALAPPDATA"),
        ]
        for root in program_files:
            if root:
                program = Path(root) / "LibreOffice" / "program"
                choices.extend([program / "soffice.com", program / "soffice.exe"])
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            program = Path(local_app_data) / "Programs" / "LibreOffice" / "program"
            choices.extend([program / "soffice.com", program / "soffice.exe"])
        choices.extend(
            [
                Path("C:/Program Files/LibreOffice/program/soffice.com"),
                Path("C:/Program Files/LibreOffice/program/soffice.exe"),
                Path("C:/Program Files (x86)/LibreOffice/program/soffice.com"),
                Path("C:/Program Files (x86)/LibreOffice/program/soffice.exe"),
            ]
        )
        try:
            import winreg

            for hive, key_name in (
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\LibreOffice\UNO\InstallPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\LibreOffice\UNO\InstallPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\LibreOffice\UNO\InstallPath"),
            ):
                try:
                    with winreg.OpenKey(hive, key_name) as key:
                        install_path, _ = winreg.QueryValueEx(key, "")
                        choices.extend(
                            [
                                Path(install_path) / "soffice.com",
                                Path(install_path) / "soffice.exe",
                            ]
                        )
                except (FileNotFoundError, OSError):
                    continue
        except ImportError:
            pass
    elif sys.platform == "darwin":
        choices.extend(
            [
                Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
                Path.home() / "Applications/LibreOffice.app/Contents/MacOS/soffice",
                Path("/opt/homebrew/bin/soffice"),
                Path("/usr/local/bin/soffice"),
                Path("/opt/local/bin/soffice"),
            ]
        )
    else:
        choices.extend(
            [
                Path("/usr/bin/soffice"),
                Path("/usr/local/bin/soffice"),
                Path("/snap/bin/libreoffice"),
                Path("/var/lib/flatpak/exports/bin/org.libreoffice.LibreOffice"),
            ]
        )

    seen = set()
    for candidate in choices:
        if not candidate:
            continue
        candidate = Path(candidate).expanduser()
        key = os.path.normcase(os.path.abspath(candidate))
        if key in seen:
            continue
        seen.add(key)
        if libreoffice_candidate_ok(candidate):
            return str(candidate)
    return None


def libreoffice_candidate_ok(path):
    path = Path(path)
    if not path.is_file():
        return False
    if os.name != "nt" and not os.access(path, os.X_OK):
        return False
    return True


def convert_with_libreoffice(source, out_dir, target):
    soffice = locate_soffice()
    if soffice is None:
        return None
    profile = out_dir / "libreoffice-profile"
    profile.mkdir(exist_ok=True)
    try:
        result = subprocess.run(
            [
                soffice,
                f"-env:UserInstallation={profile.as_uri()}",
                "--headless",
                "--nologo",
                "--nodefault",
                "--nofirststartwizard",
                "--nolockcheck",
                "--convert-to",
                target,
                "--outdir",
                str(out_dir),
                str(source),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"LibreOffice conversion failed: {exc}") from exc
    output = out_dir / f"{source.stem}.{target.split(':', 1)[0]}"
    if result.returncode == 0 and output.exists():
        return output
    raise RuntimeError(result.stderr.decode("utf-8", errors="ignore") or "LibreOffice conversion failed")


def section_nodes(root):
    return root.xpath(
        ".//w:sectPr[not(ancestor::w:sectPrChange)]",
        namespaces=NS,
    )


def relationship_source_part(relationships_part):
    path = PurePosixPath(relationships_part)
    if path == PurePosixPath("_rels/.rels"):
        return ""
    if path.parent.name != "_rels" or not path.name.endswith(".rels"):
        return None
    return str(path.parent.parent / path.name.removesuffix(".rels"))


def resolved_relationship_target(source_part, target, target_mode):
    if not target or target_mode == "External":
        return target
    base_uri = f"/{source_part}"
    return unquote(urlsplit(urljoin(base_uri, target)).path).lstrip("/")


def rel_records(root, part):
    source_part = relationship_source_part(part)
    return [
        {
            "record_type": "relationship",
            "part": part,
            "source_part": source_part,
            "id": rel.get("Id"),
            "type": rel_type(rel.get("Type")),
            "target": rel.get("Target"),
            "resolved_target": resolved_relationship_target(
                source_part, rel.get("Target"), rel.get("TargetMode")
            ),
            "target_mode": rel.get("TargetMode"),
        }
        for rel in root.findall("rels:Relationship", namespaces=NS)
    ]


def section_record(sect, index, source_path):
    pg_sz = child(sect, "w:pgSz")
    pg_mar = child(sect, "w:pgMar")
    cols = child(sect, "w:cols")
    pg_num = child(sect, "w:pgNumType")
    return {
        "record_type": "section",
        "source_path": source_path,
        "section_index": index,
        "page_size": attrs(pg_sz) if pg_sz is not None else None,
        "page_width_twip": int_twips(pg_sz.get(W + "w")) if pg_sz is not None else None,
        "page_height_twip": int_twips(pg_sz.get(W + "h")) if pg_sz is not None else None,
        "orientation": pg_sz.get(W + "orient") if pg_sz is not None and pg_sz.get(W + "orient") else "portrait",
        "page_margin": attrs(pg_mar) if pg_mar is not None else None,
        "columns": attrs(cols) if cols is not None else None,
        "section_type": attrs(child(sect, "w:type")) if child(sect, "w:type") is not None else None,
        "title_page": on_off_value(child(sect, "w:titlePg")),
        "header_references": [attrs(item) for item in children(sect, "w:headerReference")],
        "footer_references": [attrs(item) for item in children(sect, "w:footerReference")],
        "page_numbering": attrs(pg_num) if pg_num is not None else None,
        "sectPr": xml_bytes(sect),
    }


def paragraph_properties(p):
    ppr = child(p, "w:pPr")
    if ppr is None:
        return {}
    num_pr = child(ppr, "w:numPr")
    return {
        "style_id": attr(child(ppr, "w:pStyle"), W + "val"),
        "alignment": attr(child(ppr, "w:jc"), W + "val"),
        "indent": attrs(child(ppr, "w:ind")) if child(ppr, "w:ind") is not None else None,
        "spacing": attrs(child(ppr, "w:spacing")) if child(ppr, "w:spacing") is not None else None,
        "line_spacing": attr(child(ppr, "w:spacing"), W + "line"),
        "keep_with_next": on_off_value(child(ppr, "w:keepNext")),
        "keep_lines": on_off_value(child(ppr, "w:keepLines")),
        "page_break_before": on_off_value(child(ppr, "w:pageBreakBefore")),
        "widow_control": on_off_value(child(ppr, "w:widowControl")),
        "borders": xml_bytes(child(ppr, "w:pBdr")) if child(ppr, "w:pBdr") is not None else None,
        "shading": attrs(child(ppr, "w:shd")) if child(ppr, "w:shd") is not None else None,
        "tabs": [attrs(item) for item in children(ppr, "w:tabs/w:tab")],
        "numbering": {
            "num_id": attr(child(num_pr, "w:numId"), W + "val"),
            "level": attr(child(num_pr, "w:ilvl"), W + "val"),
        }
        if num_pr is not None
        else None,
    }


def run_properties(r):
    rpr = child(r, "w:rPr")
    if rpr is None:
        return {}
    strike_nodes = [child(rpr, "w:strike"), child(rpr, "w:dstrike")]
    strike_values = [on_off_value(node) for node in strike_nodes if node is not None]
    underline = child(rpr, "w:u")
    return {
        "style_id": attr(child(rpr, "w:rStyle"), W + "val"),
        "fonts": attrs(child(rpr, "w:rFonts")) if child(rpr, "w:rFonts") is not None else None,
        "size_pt": half_points(attr(child(rpr, "w:sz"), W + "val")),
        "size_complex_script_pt": half_points(attr(child(rpr, "w:szCs"), W + "val")),
        "bold": on_off_value(child(rpr, "w:b")),
        "italic": on_off_value(child(rpr, "w:i")),
        "underline": (
            attr(underline, W + "val") or "single"
            if underline is not None
            else None
        ),
        "strike": any(strike_values) if strike_values else None,
        "vertical_align": attr(child(rpr, "w:vertAlign"), W + "val"),
        "color": attrs(child(rpr, "w:color")) if child(rpr, "w:color") is not None else None,
        "highlight": attrs(child(rpr, "w:highlight")) if child(rpr, "w:highlight") is not None else None,
        "character_spacing": attrs(child(rpr, "w:spacing")) if child(rpr, "w:spacing") is not None else None,
        "character_scale": attrs(child(rpr, "w:w")) if child(rpr, "w:w") is not None else None,
        "language": attrs(child(rpr, "w:lang")) if child(rpr, "w:lang") is not None else None,
        "raw_rPr": xml_bytes(rpr),
    }


def special_nodes(scope):
    return [
        {
            "tag": qname(node.tag),
            "attrs": attrs(node),
            "text": text_value(node, include_removed=True),
            "location": node.getroottree().getpath(node),
            "xml": xml_bytes(node),
        }
        for node in scope.xpath(
            " | ".join(f".//{expression}" for expression in SPECIAL_TAGS),
            namespaces=NS,
        )
    ]


def drawing_record(node, rels):
    relationship_ids = list(
        dict.fromkeys(
            node.xpath(".//@r:embed | .//@r:link | .//@r:id", namespaces=NS)
        )
    )
    ext = node.find(".//wp:extent", namespaces=NS)
    doc_pr = node.find(".//wp:docPr", namespaces=NS)
    c_nv_pr = node.find(".//pic:cNvPr", namespaces=NS)
    positioning = node.find(".//wp:inline", namespaces=NS)
    if positioning is None:
        positioning = node.find(".//wp:anchor", namespaces=NS)
    targets = [
        {
            "relationship_id": relationship_id,
            "target": rels.get(relationship_id, {}).get("target"),
            "resolved_target": rels.get(relationship_id, {}).get("resolved_target"),
            "target_mode": rels.get(relationship_id, {}).get("target_mode"),
        }
        for relationship_id in relationship_ids
    ]
    return {
        "relationship_id": relationship_ids[0] if relationship_ids else None,
        "relationship_ids": relationship_ids,
        "target": targets[0]["target"] if targets else None,
        "resolved_target": targets[0]["resolved_target"] if targets else None,
        "targets": targets,
        "name": c_nv_pr.get("name") if c_nv_pr is not None else doc_pr.get("name") if doc_pr is not None else None,
        "alt_text": doc_pr.get("descr") if doc_pr is not None else None,
        "size_emu": attrs(ext) if ext is not None else None,
        "positioning": qname(positioning.tag) if positioning is not None else None,
        "location": node.getroottree().getpath(node),
        "xml": xml_bytes(node),
    }


def iter_child_blocks(container, path):
    for index, item in enumerate(container, 1):
        if is_removed_revision(item):
            continue
        location = f"{path}/*[{index}]"
        if item.tag in (wtag("p"), wtag("tbl")):
            yield item, location
        elif item.tag == f"{{{NS['mc']}}}AlternateContent":
            branch = alternate_content_branch(item)
            if branch is not None:
                yield from iter_child_blocks(
                    branch,
                    f"{location}/{qname(branch.tag)}",
                )
        else:
            yield from iter_child_blocks(item, location)


def iter_block_items(root, path):
    body = root.find("w:body", namespaces=NS)
    return iter_child_blocks(body, f"{path}/w:body")


def iter_cell_blocks(cell, path):
    return iter_child_blocks(cell, path)


def paragraph_record(p, indexes, location, source_path):
    props = paragraph_properties(p)
    text = "".join(run_text_value(run) for run in paragraph_runs(p))
    return {
        "record_type": "paragraph",
        "source_path": source_path,
        "location": location,
        "paragraph_index": indexes["paragraph"],
        "table_index": indexes.get("table") or None,
        "row_index": indexes.get("row"),
        "cell_index": indexes.get("cell"),
        "section_index": indexes.get("section"),
        "text": text,
        **props,
        "special_nodes": special_nodes(p),
        "xpath": location,
        "xml": xml_bytes(p),
    }


def active_range_ids(node, start_tag, end_tag):
    ended = set(node.xpath(f"preceding::{end_tag}/@w:id", namespaces=NS))
    return [
        item
        for item in node.xpath(f"preceding::{start_tag}/@w:id", namespaces=NS)
        if item not in ended
    ]


def paragraph_runs(paragraph):
    return [
        run
        for run in paragraph.xpath(".//w:r", namespaces=NS)
        if run.xpath("ancestor::w:p[1]", namespaces=NS)[0] is paragraph
        and not is_removed_revision(run)
    ]


def run_record(r, indexes, paragraph, rels, source_path):
    text = run_text_value(r)
    hyperlink = r.xpath("ancestor::w:hyperlink[1]", namespaces=NS)
    fields = r.xpath(".//w:instrText/text() | ancestor::w:fldSimple[1]/@w:instr", namespaces=NS)
    drawing_nodes = r.xpath(
        ".//w:drawing | .//w:object | .//w:pict[not(ancestor::w:object)]",
        namespaces=NS,
    )
    drawings = [drawing_record(node, rels) for node in drawing_nodes]
    bookmark_ids = active_range_ids(r, "w:bookmarkStart", "w:bookmarkEnd")
    comment_ids = active_range_ids(r, "w:commentRangeStart", "w:commentRangeEnd")
    comment_ids.extend(r.xpath(".//w:commentReference/@w:id", namespaces=NS))
    comment_ids = list(dict.fromkeys(comment_ids))
    return {
        "record_type": "run",
        "source_path": source_path,
        "location": r.getroottree().getpath(r),
        "paragraph_location": paragraph["location"],
        "paragraph_index": indexes["paragraph"],
        "run_index": indexes["run"],
        "table_index": indexes.get("table") or None,
        "row_index": indexes.get("row"),
        "cell_index": indexes.get("cell"),
        "section_index": indexes.get("section"),
        "text": text,
        "style": run_properties(r),
        "paragraph_style_id": paragraph.get("style_id"),
        "hyperlink": {
            "relationship_id": hyperlink[0].get(R + "id"),
            "anchor": hyperlink[0].get(W + "anchor"),
            "target": rels.get(hyperlink[0].get(R + "id"), {}).get("target"),
            "resolved_target": rels.get(
                hyperlink[0].get(R + "id"), {}
            ).get("resolved_target"),
            "target_mode": rels.get(hyperlink[0].get(R + "id"), {}).get(
                "target_mode"
            ),
        }
        if hyperlink
        else None,
        "bookmark_ids": bookmark_ids,
        "comment_anchor": comment_ids[-1] if comment_ids else None,
        "comment_anchor_ids": comment_ids,
        "field_codes": fields,
        "drawing": drawings[0] if drawings else None,
        "drawings": drawings,
        "xml": xml_bytes(r),
    }


def table_properties(tbl):
    tbl_pr = child(tbl, "w:tblPr")
    return {
        "table_style": attr(child(tbl_pr, "w:tblStyle"), W + "val") if tbl_pr is not None else None,
        "table_width": attrs(child(tbl_pr, "w:tblW")) if tbl_pr is not None and child(tbl_pr, "w:tblW") is not None else None,
        "borders": xml_bytes(child(tbl_pr, "w:tblBorders")) if tbl_pr is not None and child(tbl_pr, "w:tblBorders") is not None else None,
        "shading": attrs(child(tbl_pr, "w:shd")) if tbl_pr is not None and child(tbl_pr, "w:shd") is not None else None,
        "cell_margins": xml_bytes(child(tbl_pr, "w:tblCellMar")) if tbl_pr is not None and child(tbl_pr, "w:tblCellMar") is not None else None,
        "grid": [attrs(item) for item in children(tbl, "w:tblGrid/w:gridCol")],
    }


def cell_properties(cell):
    tc_pr = child(cell, "w:tcPr")
    if tc_pr is None:
        return {}
    return {
        "width": attrs(child(tc_pr, "w:tcW")) if child(tc_pr, "w:tcW") is not None else None,
        "grid_span": attr(child(tc_pr, "w:gridSpan"), W + "val"),
        "horizontal_merge": (
            attr(child(tc_pr, "w:hMerge"), W + "val") or "continue"
            if child(tc_pr, "w:hMerge") is not None
            else None
        ),
        "vertical_merge": (
            attr(child(tc_pr, "w:vMerge"), W + "val") or "continue"
            if child(tc_pr, "w:vMerge") is not None
            else None
        ),
        "borders": xml_bytes(child(tc_pr, "w:tcBorders")) if child(tc_pr, "w:tcBorders") is not None else None,
        "shading": attrs(child(tc_pr, "w:shd")) if child(tc_pr, "w:shd") is not None else None,
        "cell_margins": xml_bytes(child(tc_pr, "w:tcMar")) if child(tc_pr, "w:tcMar") is not None else None,
        "vertical_align": attr(child(tc_pr, "w:vAlign"), W + "val"),
    }


def table_record(tbl, indexes, location, source_path):
    rows = []
    for row_index, row in enumerate(children(tbl, "w:tr"), 1):
        if is_removed_revision(row):
            continue
        row_pr = child(row, "w:trPr")
        grid_before = child(row_pr, "w:gridBefore") if row_pr is not None else None
        grid_after = child(row_pr, "w:gridAfter") if row_pr is not None else None
        cells = []
        for cell_index, cell in enumerate(children(row, "w:tc"), 1):
            cells.append(
                {
                    "cell_index": cell_index,
                    "text": text_value(cell),
                    "properties": cell_properties(cell),
                    "paragraph_count": len(children(cell, "w:p")),
                }
            )
        rows.append(
            {
                "row_index": row_index,
                "height": attrs(child(row_pr, "w:trHeight")) if row_pr is not None and child(row_pr, "w:trHeight") is not None else None,
                "repeat_header": on_off_value(child(row_pr, "w:tblHeader")) if row_pr is not None else None,
                "cant_split": on_off_value(child(row_pr, "w:cantSplit")) if row_pr is not None else None,
                "grid_before": attr(grid_before, W + "val"),
                "grid_after": attr(grid_after, W + "val"),
                "cells": cells,
            }
        )
    text = text_value(tbl)
    return {
        "record_type": "table",
        "source_path": source_path,
        "location": location,
        "table_index": indexes["table"],
        "parent_table_index": indexes.get("parent_table"),
        "nesting_level": indexes.get("nesting_level", 0),
        "section_index": indexes.get("section"),
        "text": text,
        **table_properties(tbl),
        "rows": rows,
        "xml": xml_bytes(tbl),
    }


def body_content(root, rels, source_path):
    records = []
    counters = {"paragraph": 0, "table": 0}

    def append_paragraph(paragraph, location, indexes):
        counters["paragraph"] += 1
        paragraph_indexes = {**indexes, "paragraph": counters["paragraph"]}
        record = paragraph_record(
            paragraph,
            paragraph_indexes,
            location,
            source_path,
        )
        records.append(record)
        for run_index, run in enumerate(paragraph_runs(paragraph), 1):
            run_indexes = {**paragraph_indexes, "run": run_index}
            records.append(
                run_record(run, run_indexes, record, rels, source_path)
            )
        text_boxes = [
            text_box
            for text_box in paragraph.findall(".//w:txbxContent", namespaces=NS)
            if text_box.xpath("ancestor::w:p[1]", namespaces=NS)[0] is paragraph
        ]
        for text_box in text_boxes:
            text_box_path = text_box.getroottree().getpath(text_box)
            for block, block_path in iter_child_blocks(text_box, text_box_path):
                if block.tag == wtag("p"):
                    append_paragraph(block, block_path, paragraph_indexes)
                else:
                    append_table(block, block_path, paragraph_indexes)

    def append_table(table, location, indexes):
        counters["table"] += 1
        table_index = counters["table"]
        table_indexes = {
            **indexes,
            "table": table_index,
            "parent_table": indexes.get("table"),
            "nesting_level": indexes.get("nesting_level", -1) + 1,
        }
        records.append(
            table_record(table, table_indexes, location, source_path)
        )
        for row_index, row in enumerate(children(table, "w:tr"), 1):
            if is_removed_revision(row):
                continue
            for cell_index, cell in enumerate(children(row, "w:tc"), 1):
                cell_path = f"{location}/w:tr[{row_index}]/w:tc[{cell_index}]"
                child_indexes = {
                    **table_indexes,
                    "row": row_index,
                    "cell": cell_index,
                }
                for block, block_path in iter_cell_blocks(cell, cell_path):
                    if block.tag == wtag("p"):
                        append_paragraph(block, block_path, child_indexes)
                    else:
                        append_table(block, block_path, child_indexes)

    section_index = 1
    for item, location in iter_block_items(root, "/word/document.xml"):
        indexes = {"section": section_index, "nesting_level": -1}
        if item.tag == wtag("p"):
            append_paragraph(item, location, indexes)
            if child(child(item, "w:pPr"), "w:sectPr") is not None:
                section_index += 1
        else:
            append_table(item, location, indexes)
    return records


def style_records(zf):
    if "word/styles.xml" not in zf.namelist():
        return []
    root = parse_xml(zf.read("word/styles.xml"))
    records = []
    for style in root.findall("w:style", namespaces=NS):
        ppr = child(style, "w:pPr")
        rpr = child(style, "w:rPr")
        records.append(
            {
                "record_type": "style",
                "style_id": style.get(W + "styleId"),
                "type": style.get(W + "type"),
                "default": style.get(W + "default"),
                "name": attr(child(style, "w:name"), W + "val"),
                "based_on": attr(child(style, "w:basedOn"), W + "val"),
                "next": attr(child(style, "w:next"), W + "val"),
                "link": attr(child(style, "w:link"), W + "val"),
                "priority": attr(child(style, "w:uiPriority"), W + "val"),
                "hidden": on_off_value(child(style, "w:hidden")),
                "numbering": {
                    "num_id": attr(child(child(ppr, "w:numPr"), "w:numId"), W + "val"),
                    "level": attr(child(child(ppr, "w:numPr"), "w:ilvl"), W + "val"),
                }
                if child(ppr, "w:numPr") is not None
                else None,
                "paragraph_properties": xml_bytes(ppr) if ppr is not None else None,
                "run_properties": xml_bytes(rpr) if rpr is not None else None,
                "table_properties": xml_bytes(child(style, "w:tblPr")) if child(style, "w:tblPr") is not None else None,
                "xml": xml_bytes(style),
            }
        )
    return records


def numbering_records(zf):
    names = zf.namelist()
    if "word/numbering.xml" not in names:
        return []
    root = parse_xml(zf.read("word/numbering.xml"))
    records = []
    for picture in root.findall("w:numPicBullet", namespaces=NS):
        records.append(
            {
                "record_type": "picture_numbering",
                "picture_bullet_id": picture.get(W + "numPicBulletId"),
                "xml": xml_bytes(picture),
            }
        )
    for abstract in root.findall("w:abstractNum", namespaces=NS):
        records.append(
            {
                "record_type": "abstract_numbering",
                "abstract_num_id": abstract.get(W + "abstractNumId"),
                "multi_level_type": attr(child(abstract, "w:multiLevelType"), W + "val"),
                "name": attr(child(abstract, "w:name"), W + "val"),
                "style_link": attr(child(abstract, "w:styleLink"), W + "val"),
                "numbering_style_link": attr(child(abstract, "w:numStyleLink"), W + "val"),
                "levels": [
                    {
                        "level": level.get(W + "ilvl"),
                        "start": attr(child(level, "w:start"), W + "val"),
                        "format": attr(child(level, "w:numFmt"), W + "val"),
                        "text": attr(child(level, "w:lvlText"), W + "val"),
                        "suffix": attr(child(level, "w:suff"), W + "val"),
                        "justification": attr(child(level, "w:lvlJc"), W + "val"),
                        "paragraph_style": attr(child(level, "w:pStyle"), W + "val"),
                        "restart_after_level": attr(child(level, "w:lvlRestart"), W + "val"),
                        "legal_numbering": on_off_value(child(level, "w:isLgl")),
                        "paragraph_properties": xml_bytes(child(level, "w:pPr")) if child(level, "w:pPr") is not None else None,
                        "run_properties": xml_bytes(child(level, "w:rPr")) if child(level, "w:rPr") is not None else None,
                        "xml": xml_bytes(level),
                    }
                    for level in abstract.findall("w:lvl", namespaces=NS)
                ],
                "xml": xml_bytes(abstract),
            }
        )
    for num in root.findall("w:num", namespaces=NS):
        records.append(
            {
                "record_type": "numbering",
                "num_id": num.get(W + "numId"),
                "abstract_num_id": attr(child(num, "w:abstractNumId"), W + "val"),
                "level_overrides": [xml_bytes(item) for item in children(num, "w:lvlOverride")],
                "xml": xml_bytes(num),
            }
        )
    return records


def sibling_index(node):
    return 1 + sum(1 for item in node.itersiblings(preceding=True) if item.tag == node.tag)


def header_footer_parts(zf, relationships_by_part):
    names = set(zf.namelist())
    parts = {}
    for relationship in relationships_by_part.get("word/document.xml", {}).values():
        kind = (relationship.get("type") or "").lower()
        target = relationship.get("resolved_target")
        if kind in {"header", "footer"} and target in names:
            parts[target] = kind
    for name in names:
        match = re.fullmatch(r"word/(header|footer)\d+\.xml", name)
        if match:
            parts.setdefault(name, match.group(1))
    return parts


def header_footer_records(zf, relationships_by_part):
    records = []
    for name, kind in header_footer_parts(zf, relationships_by_part).items():
        root = parse_xml(zf.read(name))
        rels = relationships_by_part.get(name, {})
        resolve_alternate_content(root)
        materialize_alt_chunks(root, zf, rels)
        table_nodes = [
            table
            for table in root.findall(".//w:tbl", namespaces=NS)
            if not is_removed_revision(table)
        ]
        table_indexes = {node: index for index, node in enumerate(table_nodes, 1)}
        paragraphs = []
        paragraph_nodes = [
            paragraph
            for paragraph in root.findall(".//w:p", namespaces=NS)
            if not is_removed_revision(paragraph)
        ]
        for index, paragraph in enumerate(paragraph_nodes, 1):
            table = paragraph.xpath("ancestor::w:tbl[1]", namespaces=NS)
            row = paragraph.xpath("ancestor::w:tr[1]", namespaces=NS)
            cell = paragraph.xpath("ancestor::w:tc[1]", namespaces=NS)
            indexes = {
                "paragraph": index,
                "table": table_indexes.get(table[0]) if table else None,
                "row": sibling_index(row[0]) if row else None,
                "cell": sibling_index(cell[0]) if cell else None,
            }
            paragraphs.append(
                paragraph_record(
                    paragraph,
                    indexes,
                    paragraph.getroottree().getpath(paragraph),
                    name,
                )
            )
        tables = []
        for index, table in enumerate(table_nodes, 1):
            parent = table.xpath("ancestor::w:tbl[1]", namespaces=NS)
            indexes = {
                "table": index,
                "parent_table": table_indexes.get(parent[0]) if parent else None,
                "nesting_level": len(table.xpath("ancestor::w:tbl", namespaces=NS)),
            }
            tables.append(
                table_record(
                    table,
                    indexes,
                    table.getroottree().getpath(table),
                    name,
                )
            )
        drawing_nodes = [
            node
            for node in root.xpath(
                ".//w:drawing | .//w:object | .//w:pict[not(ancestor::w:object)]",
                namespaces=NS,
            )
            if not is_removed_revision(node)
        ]
        records.append(
            {
                "record_type": kind,
                "part": name,
                "text": text_value(root),
                "paragraphs": paragraphs,
                "tables": tables,
                "drawings": [drawing_record(item, rels) for item in drawing_nodes],
                "fields": root.xpath(".//w:instrText/text() | .//w:fldSimple/@w:instr", namespaces=NS),
                "xml": xml_bytes(root),
            }
        )
    return records


def object_records(zf, relationships, asset_dir, include_base64):
    records = []
    type_by_ext, type_by_part = content_type_maps(zf)
    infos = zf.infolist()
    alt_chunks = {
        relationship["resolved_target"]
        for relationship in relationships
        if (relationship.get("type") or "").lower() == "afchunk"
        and relationship.get("target_mode") != "External"
    }
    for info in infos:
        if info.is_dir():
            continue
        name = info.filename
        if name.startswith(
            (
                "word/media/",
                "word/embeddings/",
                "word/charts/",
                "word/diagrams/",
                "word/activeX/",
            )
        ) or name in alt_chunks:
            data = zf.read(name)
            out = None
            if asset_dir:
                out = safe_export_path(asset_dir, name)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data)
            references = [
                {
                    "source_part": relationship["source_part"],
                    "relationship_id": relationship["id"],
                    "type": relationship["type"],
                    "target_mode": relationship["target_mode"],
                }
                for relationship in relationships
                if relationship["resolved_target"] == name
            ]
            records.append(
                {
                    "record_type": "object",
                    "part": name,
                    "kind": "altChunk" if name in alt_chunks else PurePosixPath(name).parent.name,
                    "content_type": content_type_for(name, type_by_ext, type_by_part),
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "relationship_ids": [
                        reference["relationship_id"] for reference in references
                    ],
                    "relationships": references,
                    "exported_path": str(out) if out else None,
                    "base64": base64.b64encode(data).decode("ascii") if include_base64 else None,
                }
            )
    return records


def property_records(zf):
    records = []
    for name in zf.namelist():
        if name.startswith("docProps/") and name.endswith(".xml"):
            root = parse_xml(zf.read(name))
            records.append(
                {
                    "record_type": "document_property",
                    "part": name,
                    "properties": {
                        node.get("name") or qname(node.tag): "".join(node.itertext())
                        for node in root
                    },
                    "xml": xml_bytes(root),
                }
            )
    return records


def special_records(zf, content_records, relationships_by_part):
    records = []
    story_parts = {
        name
        for name in zf.namelist()
        if re.fullmatch(
            r"word/(document|comments|footnotes|endnotes)\.xml",
            name,
        )
    }
    story_parts.update(header_footer_parts(zf, relationships_by_part))
    for name in sorted(story_parts):
        root = parse_xml(zf.read(name))
        resolve_alternate_content(root)
        rels = relationships_by_part.get(name, {})
        for node in special_nodes(root):
            record = {
                **node,
                "record_type": "special_node",
                "source_path": name,
            }
            relationship_id = node["attrs"].get("r:id")
            if relationship_id:
                record["relationship"] = rels.get(relationship_id)
            records.append(record)
    for item in content_records:
        if item["record_type"] == "run" and (
            item.get("hyperlink")
            or item.get("field_codes")
            or item.get("drawings")
        ):
            records.append(
                {
                    key: item[key]
                    for key in (
                        "record_type",
                        "source_path",
                        "location",
                        "paragraph_location",
                        "paragraph_index",
                        "run_index",
                        "hyperlink",
                        "field_codes",
                        "drawings",
                    )
                }
            )
    special_parts = [
        name
        for name in zf.namelist()
        if name in {"word/footnotes.xml", "word/endnotes.xml", "word/people.xml"}
        or re.fullmatch(r"word/comments[^/]*\.xml", name)
    ]
    for name in special_parts:
        if name in zf.namelist():
            root = parse_xml(zf.read(name))
            records.append(
                {
                    "record_type": "special_part",
                    "part": name,
                    "text": text_value(root, include_removed=True),
                    "entries": [
                        {
                            "tag": qname(item.tag),
                            "attrs": attrs(item),
                            "text": text_value(item, include_removed=True),
                            "location": item.getroottree().getpath(item),
                            "xml": xml_bytes(item),
                        }
                        for item in root
                    ],
                    "xml": xml_bytes(root),
                }
            )
    records.extend(property_records(zf))
    if "word/vbaProject.bin" in zf.namelist():
        data = zf.read("word/vbaProject.bin")
        records.append({"record_type": "macro", "part": "word/vbaProject.bin", "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    return records


def length_twips(value):
    return value.twips if value is not None else None


def python_docx_sections(docx_path):
    doc = Document(docx_path)
    return [
        {
            "record_type": "python_docx_section",
            "section_index": index,
            "start_type": str(section.start_type),
            "orientation": str(section.orientation),
            "page_width_twip": length_twips(section.page_width),
            "page_height_twip": length_twips(section.page_height),
            "top_margin_twip": length_twips(section.top_margin),
            "bottom_margin_twip": length_twips(section.bottom_margin),
            "left_margin_twip": length_twips(section.left_margin),
            "right_margin_twip": length_twips(section.right_margin),
            "header_distance_twip": length_twips(section.header_distance),
            "footer_distance_twip": length_twips(section.footer_distance),
        }
        for index, section in enumerate(doc.sections, 1)
    ]


def build_data(docx_path, source_path, asset_dir, include_base64):
    with zipfile.ZipFile(docx_path) as zf:
        relationships_by_part = {}
        rel_records_all = []
        for name in zf.namelist():
            if name.endswith(".rels"):
                part_records = rel_records(parse_xml(zf.read(name)), name)
                rel_records_all.extend(part_records)
                source_part = relationship_source_part(name)
                relationships_by_part[source_part] = {
                    item["id"]: item for item in part_records
                }
        document_rels = relationships_by_part.get("word/document.xml", {})
        doc_root = parse_xml(zf.read("word/document.xml"))
        strict = configure_document_namespaces(doc_root)
        resolve_alternate_content(doc_root)
        materialize_alt_chunks(doc_root, zf, document_rels)
        content = body_content(
            doc_root,
            document_rels,
            "word/document.xml",
        )
        sections = [
            section_record(item, index, "word/document.xml")
            for index, item in enumerate(section_nodes(doc_root), 1)
        ]
        return {
            "sections": sections + ([] if strict else python_docx_sections(docx_path)),
            "content": content,
            "styles": style_records(zf),
            "numbering": numbering_records(zf),
            "objects": object_records(
                zf,
                rel_records_all,
                asset_dir,
                include_base64,
            ),
            "headers_footers": header_footer_records(
                zf,
                relationships_by_part,
            ),
            "special": special_records(zf, content, relationships_by_part),
            "properties": property_records(zf),
            "raw_parts": [
                {"record_type": "ooxml_part", "part": name, "xml": part_xml(zf, name)}
                for name in zf.namelist()
                if name.endswith(".xml") and (name in KEY_PARTS or name.startswith(("word/charts/", "customXml/")))
            ],
            "source": str(source_path),
        }


def build_sections_data(docx_path, source_path):
    with zipfile.ZipFile(docx_path) as zf:
        root = parse_xml(zf.read("word/document.xml"))
    strict = configure_document_namespaces(root)
    resolve_alternate_content(root)
    sections = [
        section_record(item, index, "word/document.xml")
        for index, item in enumerate(section_nodes(root), 1)
    ]
    return {
        "sections": sections + ([] if strict else python_docx_sections(docx_path)),
        "source": str(source_path),
    }


def markdown_table(table):
    rows = table["rows"]
    if not rows:
        return ""
    values = []
    for row in rows:
        row_values = [""] * int(row.get("grid_before") or 0)
        for cell in row["cells"]:
            text = cell["text"].replace("|", "\\|").replace("\n", "<br>").strip()
            grid_span = int(cell.get("properties", {}).get("grid_span") or 1)
            row_values.append(text)
            row_values.extend([""] * (grid_span - 1))
        row_values.extend([""] * int(row.get("grid_after") or 0))
        values.append(row_values)
    width = max([len(table.get("grid") or [])] + [len(row) for row in values])
    values = [row + [""] * (width - len(row)) for row in values]
    return "\n".join(["| " + " | ".join(values[0]) + " |", "| " + " | ".join(["---"] * width) + " |"] + ["| " + " | ".join(row) + " |" for row in values[1:]])


def heading_level(value):
    normalized = re.sub(r"[\s_-]+", "", value or "").casefold()
    if normalized in {"title", "标题"}:
        return 1
    match = re.fullmatch(r"(?:heading|标题)([1-6])", normalized)
    return int(match.group(1)) if match else None


def markdown_heading_levels(styles):
    levels = {"Title": 1, **{f"Heading{level}": level for level in range(1, 7)}}
    paragraph_styles = [style for style in styles if style.get("type") == "paragraph"]
    changed = True
    while changed:
        changed = False
        for style in paragraph_styles:
            style_id = style.get("style_id")
            level = heading_level(style_id) or heading_level(style.get("name"))
            level = level or levels.get(style.get("based_on"))
            if style_id and level and levels.get(style_id) != level:
                levels[style_id] = level
                changed = True
    return levels


def markdown_output(data):
    heading_levels = markdown_heading_levels(data["styles"])
    blocks = []
    for item in data["content"]:
        if item["record_type"] == "paragraph" and item["text"].strip():
            if item.get("row_index") is not None or item.get("cell_index") is not None:
                continue
            text = item["text"].strip()
            level = heading_levels.get(item.get("style_id"))
            blocks.append(f"{'#' * level} {text}" if level else text)
        if item["record_type"] == "table" and item.get("parent_table_index") is None:
            blocks.append(markdown_table(item))
    return "\n\n".join(blocks) + "\n"


def context_records(data, dimension):
    return [
        {
            "record_type": "output_manifest",
            "source": data["source"],
            "dimension": dimension,
            "mode": MODE_NAMES[dimension],
            "body_text_policy": BODY_TEXT_POLICY if 1 <= dimension <= 9 else None,
        }
    ]


def lean_value(value, drop_keys=MODEL_DROP_KEYS):
    if type(value) is dict:
        result = {}
        for key, item in value.items():
            if key in drop_keys:
                continue
            cleaned = lean_value(item, drop_keys)
            if cleaned in (None, "", [], {}):
                continue
            result[key] = cleaned
        return result
    if type(value) is list:
        return [
            item
            for item in [lean_value(item, drop_keys) for item in value]
            if item not in (None, "", [], {})
        ]
    return value


PARAGRAPH_FIELD_NAMES = {
    "source_path": "part",
    "style_id": "style",
    "alignment": "align",
    "keep_with_next": "keep_next",
    "page_break_before": "page_break",
    "widow_control": "widow",
    "special_nodes": "special",
}


def compact_xml(value):
    node = parse_xml(value.encode("utf-8"))

    def render(item):
        values = [f"{qname(key)}={inline_value(value)}" for key, value in item.attrib.items()]
        if item.text and item.text.strip():
            values.append(f"text={inline_value(item.text)}")
        values.extend(render(child_node) for child_node in item)
        return f"{qname(item.tag)}({','.join(values)})"

    return render(node)


def paragraph_value(key, value):
    if key == "borders":
        return compact_xml(value)
    if type(value) is dict:
        value = {name.removeprefix("w:"): item for name, item in value.items()}
    if type(value) is list:
        value = [
            {name.removeprefix("w:"): item for name, item in entry.items()} if type(entry) is dict else entry
            for entry in value
        ]
    return inline_value(value)


def paragraphs_text_output(records):
    manifest = records[0]
    paragraphs = [
        lean_value(item) for item in records if item.get("record_type") == "paragraph"
    ]
    defaults = {}
    structural_fields = {
        "record_type",
        "location",
        "xpath",
        "paragraph_index",
        "table_index",
        "row_index",
        "cell_index",
        "section_index",
        "text",
        "line_spacing",
    }
    if paragraphs:
        for key in set.union(*(set(item) for item in paragraphs)) - structural_fields:
            values = [item.get(key) for item in paragraphs]
            encoded = [json.dumps(value, ensure_ascii=False, sort_keys=True) for value in values]
            default = max(dict.fromkeys(encoded), key=encoded.count)
            if default != "null" and encoded.count(default) > len(paragraphs) / 2:
                defaults[key] = values[encoded.index(default)]
        location_base = os.path.commonprefix([item["location"] for item in paragraphs])
        location_base = location_base[: location_base.rfind("/") + 1]
    else:
        location_base = ""
    repeated_values = {}
    for paragraph in paragraphs:
        for key, value in paragraph.items():
            if key in structural_fields or key in defaults and value == defaults[key]:
                continue
            rendered = paragraph_value(key, value)
            if type(value) in (dict, list) and len(rendered) >= 24:
                repeated_values[(key, rendered)] = repeated_values.get((key, rendered), 0) + 1
    references = {
        value: f"@v{index}"
        for index, value in enumerate((value for value, count in repeated_values.items() if count > 1), 1)
    }
    default_values = [
        f"{PARAGRAPH_FIELD_NAMES.get(key, key)}={paragraph_value(key, value)}" for key, value in defaults.items()
    ]
    lines = [
        "# Dimension 2: paragraph layout",
        f"source: {manifest['source']}",
        f"location_base: {location_base}",
        "syntax: [P<n> ...] starts a paragraph; listed defaults apply when omitted; other missing attributes are unset/inherited; null overrides a default with unset/inherited.",
        f"defaults: {', '.join(sorted(default_values)) if default_values else 'none'}",
        "definitions: "
        + (
            "; ".join(
                f"{reference} {PARAGRAPH_FIELD_NAMES.get(key, key)}={value}"
                for (key, value), reference in references.items()
            )
            if references
            else "none"
        ),
        f"text_policy: {BODY_TEXT_POLICY}.",
        "omitted: record_type=paragraph; repeated default values; xpath because it equals location; raw XML.",
        "normalized: loc is body[/row/cell/block] indexes relative to location_base; @v references definitions; line_spacing duplicates spacing.line; border XML is losslessly compacted by tag and attributes.",
        "",
    ]
    for paragraph in paragraphs:
        header = [f"P{paragraph['paragraph_index']}"]
        for key, name in (
            ("section_index", "section"),
            ("table_index", "table"),
            ("row_index", "row"),
            ("cell_index", "cell"),
        ):
            if key in paragraph:
                header.append(f"{name}={paragraph[key]}")
        location = paragraph["location"].removeprefix(location_base)
        match = re.fullmatch(r"\*\[(\d+)\](?:/w:tr\[(\d+)\]/w:tc\[(\d+)\]/\*\[(\d+)\])?", location)
        location = "/".join(item for item in match.groups() if item) if match else location
        header.append(f"loc={location}")
        for key, value in paragraph.items():
            if key in structural_fields or key in defaults and value == defaults[key]:
                continue
            rendered = paragraph_value(key, value)
            header.append(f"{PARAGRAPH_FIELD_NAMES.get(key, key)}={references.get((key, rendered), rendered)}")
        for key in defaults.keys() - paragraph.keys():
            header.append(f"{PARAGRAPH_FIELD_NAMES.get(key, key)}=null")
        text = paragraph.get("text") or "<empty/>"
        lines.extend([f"[{' '.join(header)}]", text, ""])
    return "\n".join(lines).rstrip() + "\n"


TABLE_FIELD_NAMES = {
    "source_path": "part",
    "table_style": "style",
    "table_width": "width",
    "cell_margins": "cell_margin",
    "repeat_header": "header",
    "paragraph_count": "paragraphs",
    "grid_span": "colspan",
    "horizontal_merge": "hmerge",
    "vertical_merge": "vmerge",
    "vertical_align": "valign",
}


def table_value(key, value):
    if key in ("borders", "cell_margins"):
        return compact_xml(value)
    return paragraph_value(key, value)


def majority_defaults(items, structural_fields):
    defaults = {}
    if not items:
        return defaults
    for key in set.union(*(set(item) for item in items)) - structural_fields:
        values = [item.get(key) for item in items]
        encoded = [json.dumps(value, ensure_ascii=False, sort_keys=True) for value in values]
        default = max(dict.fromkeys(encoded), key=encoded.count)
        if default != "null" and encoded.count(default) > len(items) / 2:
            defaults[key] = values[encoded.index(default)]
    return defaults


DIMENSION_2_FIELD_NAMES = {
    "source_path": "part",
    "width_twip": "width",
    "height_twip": "height",
    "page_width_twip": "width",
    "page_height_twip": "height",
    "page_margin": "margins",
    "section_type": "start",
    "page_numbering": "numbering",
    "start_type": "start",
    "top_margin_twip": "margin_top",
    "bottom_margin_twip": "margin_bottom",
    "left_margin_twip": "margin_left",
    "right_margin_twip": "margin_right",
    "header_distance_twip": "header_distance",
    "footer_distance_twip": "footer_distance",
}


def scoped_defaults_text(defaults, names):
    return ", ".join(
        sorted(f"{names.get(key, key)}={paragraph_value(key, value)}" for key, value in defaults.items())
    ) or "none"


def scoped_attributes(item, structural, defaults, names):
    values = []
    for key, value in item.items():
        if key in structural or key in defaults and value == defaults[key]:
            continue
        values.append(f"{names.get(key, key)}={paragraph_value(key, value)}")
    for key in defaults.keys() - item.keys():
        values.append(f"{names.get(key, key)}=null")
    return values


def sections_text_output(records):
    manifest = records[0]
    sections = [lean_value(item) for item in records if item.get("record_type") == "section"]
    api_sections = [lean_value(item) for item in records if item.get("record_type") == "python_docx_section"]
    section_structural = {"record_type", "section_index"}
    section_defaults = majority_defaults(sections, section_structural)
    api_section_defaults = majority_defaults(api_sections, section_structural)
    lines = [
        "# Dimension 1: sections",
        f"source: {manifest['source']}",
        "syntax: SECTION is OOXML data and API_SECTION is python-docx data.",
        f"section_defaults: {scoped_defaults_text(section_defaults, DIMENSION_2_FIELD_NAMES)}",
        f"api_section_defaults: {scoped_defaults_text(api_section_defaults, DIMENSION_2_FIELD_NAMES)}",
        "omitted: record_type; repeated defaults; raw sectPr XML.",
        "normalized: geometry is in twips.",
        "",
    ]

    for label, items, defaults in (
        ("SECTION", sections, section_defaults),
        ("API_SECTION", api_sections, api_section_defaults),
    ):
        for section in items:
            header = [f"{label}{section['section_index']}"]
            header.extend(scoped_attributes(section, section_structural, defaults, DIMENSION_2_FIELD_NAMES))
            lines.extend([f"[{' '.join(header)}]", ""])
    return "\n".join(lines).rstrip() + "\n"


def tables_text_output(records):
    manifest = records[0]
    tables = [lean_value(item) for item in records if item.get("record_type") == "table"]
    table_items = [{key: value for key, value in table.items() if key not in ("rows", "text")} for table in tables]
    row_items = [
        {key: value for key, value in row.items() if key != "cells"}
        for table in tables
        for row in table.get("rows", [])
    ]
    cell_items = []
    for table in tables:
        for row in table.get("rows", []):
            for cell in row.get("cells", []):
                item = {key: value for key, value in cell.items() if key != "properties"}
                item.update(cell.get("properties", {}))
                cell_items.append(item)

    table_structural = {"record_type", "location", "table_index"}
    row_structural = {"row_index"}
    cell_structural = {"cell_index", "text"}
    table_defaults = majority_defaults(table_items, table_structural)
    row_defaults = majority_defaults(row_items, row_structural)
    cell_defaults = majority_defaults(cell_items, cell_structural)

    repeated_values = {}
    for scope, items, structural, defaults in (
        ("table", table_items, table_structural, table_defaults),
        ("row", row_items, row_structural, row_defaults),
        ("cell", cell_items, cell_structural, cell_defaults),
    ):
        for item in items:
            for key, value in item.items():
                if key in structural or key in defaults and value == defaults[key]:
                    continue
                rendered = table_value(key, value)
                if (type(value) in (dict, list) or key in ("borders", "cell_margins")) and len(rendered) >= 24:
                    token = (scope, key, rendered)
                    repeated_values[token] = repeated_values.get(token, 0) + 1
    references = {
        value: f"@v{index}"
        for index, value in enumerate((value for value, count in repeated_values.items() if count > 1), 1)
    }

    locations = [table["location"] for table in tables]
    location_base = os.path.commonprefix(locations) if locations else ""
    location_base = location_base[: location_base.rfind("/") + 1] if location_base else ""

    def defaults_text(defaults):
        return ", ".join(
            sorted(f"{TABLE_FIELD_NAMES.get(key, key)}={table_value(key, value)}" for key, value in defaults.items())
        ) or "none"

    lines = [
        "# Dimension 5: table structure",
        f"source: {manifest['source']}",
        f"location_base: {location_base}",
        "syntax: [T<n>] starts a table, [R<n>] a row, and [C<n>] a cell; listed defaults apply when omitted; null means unset/inherited.",
        f"table_defaults: {defaults_text(table_defaults)}",
        f"row_defaults: {defaults_text(row_defaults)}",
        f"cell_defaults: {defaults_text(cell_defaults)}",
        "definitions: "
        + (
            "; ".join(
                f"{reference} {scope}.{TABLE_FIELD_NAMES.get(key, key)}={value}"
                for (scope, key, value), reference in references.items()
            )
            if references
            else "none"
        ),
        f"text_policy: {BODY_TEXT_POLICY}.",
        "omitted: record_type=table; repeated defaults; table text because it is the ordered concatenation of cell text; raw table XML.",
        "normalized: loc is relative to location_base; @v references definitions; border and margin XML are losslessly compacted by tag and attributes.",
        "",
    ]

    row_position = 0
    cell_position = 0
    for table, table_item in zip(tables, table_items):
        header = [f"T{table['table_index']}"]
        location = table["location"].removeprefix(location_base)
        match = re.fullmatch(r"\*\[(\d+)\]", location)
        header.append(f"loc={match.group(1) if match else location}")
        for key, value in table_item.items():
            if key in table_structural or key in table_defaults and value == table_defaults[key]:
                continue
            rendered = table_value(key, value)
            header.append(f"{TABLE_FIELD_NAMES.get(key, key)}={references.get(('table', key, rendered), rendered)}")
        for key in table_defaults.keys() - table_item.keys():
            header.append(f"{TABLE_FIELD_NAMES.get(key, key)}=null")
        lines.extend([f"[{' '.join(header)}]", ""])

        for row in table.get("rows", []):
            row_item = row_items[row_position]
            row_position += 1
            row_header = [f"R{row['row_index']}"]
            for key, value in row_item.items():
                if key in row_structural or key in row_defaults and value == row_defaults[key]:
                    continue
                rendered = table_value(key, value)
                row_header.append(f"{TABLE_FIELD_NAMES.get(key, key)}={references.get(('row', key, rendered), rendered)}")
            for key in row_defaults.keys() - row_item.keys():
                row_header.append(f"{TABLE_FIELD_NAMES.get(key, key)}=null")
            lines.append(f"[{' '.join(row_header)}]")

            for cell in row.get("cells", []):
                cell_item = cell_items[cell_position]
                cell_position += 1
                cell_header = [f"C{cell['cell_index']}"]
                for key, value in cell_item.items():
                    if key in cell_structural or key in cell_defaults and value == cell_defaults[key]:
                        continue
                    rendered = table_value(key, value)
                    cell_header.append(
                        f"{TABLE_FIELD_NAMES.get(key, key)}={references.get(('cell', key, rendered), rendered)}"
                    )
                for key in cell_defaults.keys() - cell_item.keys():
                    cell_header.append(f"{TABLE_FIELD_NAMES.get(key, key)}=null")
                text = cell.get("text") or "<empty/>"
                lines.extend([f"[{' '.join(cell_header)}]", text])
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def common_run_defaults(runs):
    font_counts = {}
    size_counts = {}
    paragraph_styles = set()
    for run in runs:
        if not run.get("text"):
            continue
        style = run.get("style") or {}
        for font in (style.get("fonts") or {}).values():
            font_counts[font] = font_counts.get(font, 0) + 1
        size = style.get("size_pt")
        if size is not None:
            size_counts[size] = size_counts.get(size, 0) + 1
        paragraph_styles.add(run.get("paragraph_style_id"))
    most_common = lambda counts: max(counts, key=counts.get) if counts else None
    paragraph_style = paragraph_styles.pop() if len(paragraph_styles) == 1 else None
    return most_common(font_counts), most_common(size_counts), paragraph_style


def inline_value(value):
    if type(value) is dict:
        value = lean_value(value)
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def simple_property(value):
    return value.get("w:val") if type(value) is dict and set(value) == {"w:val"} else value


def render_run_parts(parts):
    return "".join(
        html.escape(value, quote=False) if kind == "text" else value
        for kind, value in parts
    )


def run_display_text(run):
    if not run.get("xml"):
        return html.escape(run.get("text") or "", quote=False)
    parts = []
    root = parse_xml(run["xml"].encode("utf-8"))
    for node in root.iter():
        owners = node.xpath("ancestor::w:r[1]", namespaces=NS)
        if owners and owners[0] is not root:
            continue
        name = qname(node.tag)
        if name in ("w:t", "w:delText"):
            parts.append(("text", node.text or ""))
        elif name == "w:tab":
            parts.append(("text", "\t"))
        elif name == "w:cr":
            parts.append(("text", "\n"))
        elif name == "w:br":
            break_type = node.get(W + "type")
            parts.append(
                ("text", "\n")
                if break_type in (None, "textWrapping")
                else ("markup", f"<break type={inline_value(break_type)}/>")
            )
        elif name == "w:noBreakHyphen":
            parts.append(("text", "-"))
        elif name == "w:softHyphen":
            parts.append(("text", "\u00ad"))
        elif name == "w:sym":
            parts.append(("markup", f"<symbol attrs={inline_value(attrs(node))}/>"))
    return render_run_parts(parts)


def run_inline_span(run, default_font, default_size, location_base):
    text = run_display_text(run)
    semantic_fields = (
        "hyperlink",
        "bookmark_ids",
        "comment_anchor_ids",
        "field_codes",
        "drawings",
    )
    if not text and not any(run.get(key) for key in semantic_fields):
        return None

    style = lean_value(run.get("style") or {})
    attributes = [
        f"i={run['run_index']}",
        f"loc={inline_value(run['location'].removeprefix(location_base))}",
    ]
    fonts = style.pop("fonts", None)
    for name, font in (fonts or {}).items():
        if font != default_font:
            attributes.append(f"font_{name.removeprefix('w:')}={inline_value(font)}")
    size = style.pop("size_pt", None)
    if size is not None and size != default_size:
        attributes.append(f"size={size:g}pt")
    size_cs = style.pop("size_complex_script_pt", None)
    if size_cs is not None and size_cs != default_size:
        attributes.append(f"size_cs={size_cs:g}pt")

    short_names = {
        "style_id": "style",
        "bold": "b",
        "italic": "i",
        "underline": "u",
        "strike": "strike",
        "vertical_align": "valign",
        "color": "color",
        "highlight": "highlight",
        "character_spacing": "spacing",
        "character_scale": "scale",
        "language": "lang",
    }
    for key, value in style.items():
        value = simple_property(value)
        if key == "color" and type(value) is str and value != "auto":
            value = f"#{value}"
        attributes.append(short_names[key] if value is True else f"{short_names[key]}={inline_value(value)}")

    for key, name in (
        ("hyperlink", "link"),
        ("bookmark_ids", "bookmarks"),
        ("comment_anchor_ids", "comments"),
        ("field_codes", "fields"),
        ("drawings", "drawings"),
    ):
        value = run.get(key)
        if value not in (None, [], {}):
            attributes.append(f"{name}={inline_value(value)}")

    return " ".join(attributes), text


def runs_text_output(records):
    manifest = records[0]
    runs = [item for item in records if item.get("record_type") == "run"]
    default_font, default_size, default_paragraph_style = common_run_defaults(runs)
    defaults = []
    if default_font:
        defaults.append(f"font={inline_value(default_font)}")
    if default_size is not None:
        defaults.append(f"size={default_size:g}pt")
    if default_paragraph_style:
        defaults.append(f"paragraph_style={inline_value(default_paragraph_style)}")
    locations = [run["location"] for run in runs]
    location_base = os.path.commonprefix(locations) if locations else ""
    location_base = location_base[: location_base.rfind("/") + 1] if location_base else ""

    lines = [
        "# Dimension 3: inline run formatting",
        f"source: {manifest['source']}",
        "syntax: [P<n> ...] starts a paragraph; each <r i=<n> loc=<path> ...> element is one source Run.",
        f"defaults: {', '.join(defaults) if defaults else 'none inferred'}",
        f"run_location_base: {location_base}",
        f"text_policy: {BODY_TEXT_POLICY}.",
        "omitted: repeated source_path; font, size, and paragraph style equal to defaults; raw XML; empty runs without text or semantic objects.",
        "notes: paragraph layout belongs to dimension 3; tabs, breaks, and symbols are preserved; script-specific font declarations equal to the default font are normalized.",
        "",
    ]

    current_key = None
    paragraph_runs = []
    paragraph = None

    def append_paragraph():
        if paragraph is None:
            return
        body = "".join(
            f"<r {marker}>{text}</r>" if text else f"<r {marker}/>"
            for marker, text in paragraph_runs
        )
        if not body:
            return
        header = [f"P{paragraph['paragraph_index']}"]
        for key, name in (
            ("section_index", "section"),
            ("table_index", "table"),
            ("row_index", "row"),
            ("cell_index", "cell"),
        ):
            if paragraph.get(key) is not None:
                header.append(f"{name}={paragraph[key]}")
        header.append(
            f"loc={inline_value(paragraph.get('paragraph_location') or '')}"
        )
        paragraph_style = paragraph.get("paragraph_style_id")
        if paragraph_style and paragraph_style != default_paragraph_style:
            header.append(f"style={inline_value(paragraph_style)}")
        lines.extend([f"[{' '.join(header)}]", body, ""])

    paragraph_fields = (
        "source_path",
        "paragraph_location",
        "paragraph_index",
        "table_index",
        "row_index",
        "cell_index",
        "section_index",
        "paragraph_style_id",
    )
    for run in runs:
        key = tuple(run.get(field) for field in paragraph_fields)
        if key != current_key:
            append_paragraph()
            current_key = key
            paragraph = run
            paragraph_runs = []
        span = run_inline_span(run, default_font, default_size, location_base)
        if span:
            paragraph_runs.append(span)
    append_paragraph()
    return "\n".join(lines).rstrip() + "\n"


def block_header(label, values):
    attributes = " ".join(
        f"{key}={inline_value(value)}"
        for key, value in values
        if value not in (None, "", [], {})
    )
    return f"[{label}{' ' + attributes if attributes else ''}]"


def compact_xml_without_children(value, excluded_tags):
    root = parse_xml(value.encode("utf-8"))
    for item in list(root):
        if item.tag in excluded_tags:
            root.remove(item)
    return compact_xml(xml_bytes(root))


def compact_part_lines(value, excluded_tags=()):
    root = parse_xml(value.encode("utf-8"))
    root_value = qname(root.tag)
    if root.attrib:
        root_value += f" attrs={inline_value(attrs(root))}"
    lines = [f"root={root_value}"]
    lines.extend(
        f"item={compact_xml(xml_bytes(item))}"
        for item in root
        if item.tag not in excluded_tags
    )
    return lines


def drawing_summary(drawing):
    return {
        key: value
        for key, value in drawing.items()
        if key != "xml" and value not in (None, "", [], {})
    }


def styles_text_output(records):
    manifest = records[0]
    styles = [item for item in records if item.get("record_type") == "style"]
    parts = [item for item in records if item.get("record_type") == "ooxml_part"]
    lines = [
        "# Dimension 4: styles, fonts, and theme",
        f"source: {manifest['source']}",
        "syntax: [STYLE<n>] starts a style definition; [PART<n>] starts a supporting OOXML part.",
        "omitted: record_type; namespace declarations; full style XML duplicated by metadata and property blocks.",
        "normalized: OOXML structures use compact prefix:tag(attribute,child) notation.",
        "",
    ]
    if not styles and not parts:
        lines.append("records: none")
    for index, style in enumerate(styles, 1):
        lines.append(
            block_header(
                f"STYLE{index}",
                [
                    ("id", style.get("style_id")),
                    ("type", style.get("type")),
                    ("name", style.get("name")),
                    ("default", style.get("default")),
                    ("based_on", style.get("based_on")),
                    ("next", style.get("next")),
                    ("link", style.get("link")),
                    ("priority", style.get("priority")),
                    ("hidden", style.get("hidden")),
                    ("numbering", style.get("numbering")),
                ],
            )
        )
        if style.get("xml"):
            lines.append(
                "meta="
                + compact_xml_without_children(
                    style["xml"],
                    {wtag("pPr"), wtag("rPr"), wtag("tblPr")},
                )
            )
        for key, name in (
            ("paragraph_properties", "pPr"),
            ("run_properties", "rPr"),
            ("table_properties", "tblPr"),
        ):
            if style.get(key):
                lines.append(f"{name}={compact_xml(style[key])}")
        lines.append("")
    for index, part in enumerate(parts, 1):
        lines.append(block_header(f"PART{index}", [("part", part.get("part"))]))
        excluded = {wtag("style")} if part.get("part") == "word/styles.xml" else ()
        lines.extend(compact_part_lines(part["xml"], excluded))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def objects_text_output(records):
    manifest = records[0]
    objects = [item for item in records if item.get("record_type") == "object"]
    anchors = [item for item in records if item.get("record_type") == "run"]
    lines = [
        "# Dimension 6: media and embedded objects",
        f"source: {manifest['source']}",
        "syntax: [OBJECT<n>] identifies a package object, [REL<n>] a reference, and [ANCHOR<n>] its source Run.",
        "omitted: record_type; Run formatting and raw Run XML, which belong to dimension 4.",
        "normalized: drawing OOXML uses compact prefix:tag(attribute,child) notation.",
        "",
    ]
    if not objects and not anchors:
        lines.append("records: none")
    for index, item in enumerate(objects, 1):
        lines.append(
            block_header(
                f"OBJECT{index}",
                [
                    ("part", item.get("part")),
                    ("kind", item.get("kind")),
                    ("type", item.get("content_type")),
                    ("size", item.get("size")),
                    ("sha256", item.get("sha256")),
                    ("relationship_ids", item.get("relationship_ids")),
                    ("exported", item.get("exported_path")),
                ],
            )
        )
        for relation_index, relationship in enumerate(item.get("relationships", []), 1):
            lines.append(
                block_header(
                    f"REL{relation_index}",
                    [
                        ("part", relationship.get("source_part")),
                        ("id", relationship.get("relationship_id")),
                        ("type", relationship.get("type")),
                        ("mode", relationship.get("target_mode")),
                    ],
                )
            )
        if item.get("base64"):
            lines.append(f"base64={item['base64']}")
        lines.append("")
    for index, run in enumerate(anchors, 1):
        lines.append(
            block_header(
                f"ANCHOR{index}",
                [
                    ("part", run.get("source_path")),
                    ("paragraph", run.get("paragraph_index")),
                    ("run", run.get("run_index")),
                    ("table", run.get("table_index")),
                    ("row", run.get("row_index")),
                    ("cell", run.get("cell_index")),
                    ("section", run.get("section_index")),
                    ("loc", run.get("location")),
                ],
            )
        )
        for drawing_index, drawing in enumerate(run.get("drawings", []), 1):
            lines.append(
                block_header(
                    f"DRAWING{drawing_index}",
                    list(drawing_summary(drawing).items()),
                )
            )
            if drawing.get("xml"):
                lines.append(f"structure={compact_xml(drawing['xml'])}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def headers_footers_text_output(records):
    manifest = records[0]
    stories = [
        item for item in records if item.get("record_type") in {"header", "footer"}
    ]
    lines = [
        "# Dimension 7: headers and footers",
        f"source: {manifest['source']}",
        "syntax: [HEADER<n>] or [FOOTER<n>] starts a story; nested [P], [T], [R], [C], and [DRAWING] blocks retain source indexes.",
        f"text_policy: {BODY_TEXT_POLICY}.",
        "omitted: record_type; raw story, paragraph, table, and drawing XML.",
        "normalized: border and margin XML use compact prefix:tag(attribute,child) notation.",
        "",
    ]
    if not stories:
        lines.append("records: none")
    for story_index, story in enumerate(stories, 1):
        lines.append(
            block_header(
                f"{story['record_type'].upper()}{story_index}",
                [
                    ("part", story.get("part")),
                    ("paragraphs", len(story.get("paragraphs", []))),
                    ("tables", len(story.get("tables", []))),
                    ("drawings", len(story.get("drawings", []))),
                ],
            )
        )
        text = story.get("text") or ""
        if text:
            lines.append(text)
        if story.get("fields"):
            lines.append(f"fields={inline_value(story['fields'])}")
        for paragraph in story.get("paragraphs", []):
            paragraph_values = [
                ("loc", paragraph.get("location")),
                ("style", paragraph.get("style_id")),
                ("align", paragraph.get("alignment")),
                ("indent", paragraph.get("indent")),
                ("spacing", paragraph.get("spacing")),
                ("keep_next", paragraph.get("keep_with_next")),
                ("keep_lines", paragraph.get("keep_lines")),
                ("page_break", paragraph.get("page_break_before")),
                ("widow", paragraph.get("widow_control")),
                ("borders", compact_xml(paragraph["borders"]) if paragraph.get("borders") else None),
                ("shading", paragraph.get("shading")),
                ("tabs", paragraph.get("tabs")),
                ("numbering", paragraph.get("numbering")),
            ]
            special = [
                {
                    key: node[key]
                    for key in ("tag", "attrs", "location")
                    if node.get(key) not in (None, "", [], {})
                }
                for node in paragraph.get("special_nodes", [])
            ]
            paragraph_values.append(("special", special))
            lines.append(
                block_header(
                    f"P{paragraph['paragraph_index']}",
                    paragraph_values,
                )
            )
            lines.append(paragraph.get("text") or "<empty/>")
        for table in story.get("tables", []):
            lines.append(
                block_header(
                    f"T{table['table_index']}",
                    [
                        ("parent", table.get("parent_table_index")),
                        ("level", table.get("nesting_level")),
                        ("loc", table.get("location")),
                        ("style", table.get("table_style")),
                        ("width", table.get("table_width")),
                        ("borders", compact_xml(table["borders"]) if table.get("borders") else None),
                        ("shading", table.get("shading")),
                        ("cell_margin", compact_xml(table["cell_margins"]) if table.get("cell_margins") else None),
                        ("grid", table.get("grid")),
                    ],
                )
            )
            for row in table.get("rows", []):
                lines.append(
                    block_header(
                        f"R{row['row_index']}",
                        [
                            ("height", row.get("height")),
                            ("header", row.get("repeat_header")),
                            ("cant_split", row.get("cant_split")),
                            ("grid_before", row.get("grid_before")),
                            ("grid_after", row.get("grid_after")),
                        ],
                    )
                )
                for cell in row.get("cells", []):
                    properties = cell.get("properties", {})
                    lines.append(
                        block_header(
                            f"C{cell['cell_index']}",
                            [
                                ("width", properties.get("width")),
                                ("colspan", properties.get("grid_span")),
                                ("hmerge", properties.get("horizontal_merge")),
                                ("vmerge", properties.get("vertical_merge")),
                                ("borders", compact_xml(properties["borders"]) if properties.get("borders") else None),
                                ("shading", properties.get("shading")),
                                ("cell_margin", compact_xml(properties["cell_margins"]) if properties.get("cell_margins") else None),
                                ("valign", properties.get("vertical_align")),
                                ("paragraphs", cell.get("paragraph_count")),
                            ],
                        )
                    )
                    lines.append(cell.get("text") or "<empty/>")
        for drawing_index, drawing in enumerate(story.get("drawings", []), 1):
            lines.append(
                block_header(
                    f"DRAWING{drawing_index}",
                    list(drawing_summary(drawing).items()),
                )
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def numbering_text_output(records):
    manifest = records[0]
    pictures = [
        item for item in records if item.get("record_type") == "picture_numbering"
    ]
    abstracts = [
        item for item in records if item.get("record_type") == "abstract_numbering"
    ]
    numbers = [item for item in records if item.get("record_type") == "numbering"]
    bindings = [
        item
        for item in records
        if item.get("record_type") == "paragraph_numbering_binding"
    ]
    lines = [
        "# Dimension 8: numbering",
        f"source: {manifest['source']}",
        "syntax: [PICTURE<n>] defines a picture bullet, [ABSTRACT<n>] a numbering scheme, [LEVEL<n>] a level, [NUM<n>] an instance, and [P<n>] a paragraph binding.",
        f"text_policy: {BODY_TEXT_POLICY}.",
        "omitted: record_type; full numbering XML duplicated by compact definition and override structures.",
        "normalized: OOXML structures use compact prefix:tag(attribute,child) notation.",
        "",
    ]
    if not pictures and not abstracts and not numbers and not bindings:
        lines.append("records: none")
    for index, picture in enumerate(pictures, 1):
        lines.append(
            block_header(
                f"PICTURE{index}",
                [("id", picture.get("picture_bullet_id"))],
            )
        )
        lines.extend(compact_part_lines(picture["xml"]))
        lines.append("")
    for index, abstract in enumerate(abstracts, 1):
        lines.append(
            block_header(
                f"ABSTRACT{index}",
                [
                    ("id", abstract.get("abstract_num_id")),
                    ("type", abstract.get("multi_level_type")),
                    ("name", abstract.get("name")),
                    ("style_link", abstract.get("style_link")),
                    ("numbering_style_link", abstract.get("numbering_style_link")),
                ],
            )
        )
        if abstract.get("xml"):
            lines.append(
                "meta="
                + compact_xml_without_children(
                    abstract["xml"],
                    {wtag("lvl")},
                )
            )
        for level in abstract.get("levels", []):
            lines.append(
                block_header(
                    f"LEVEL{level.get('level')}",
                    [
                        ("start", level.get("start")),
                        ("format", level.get("format")),
                        ("text", level.get("text")),
                        ("suffix", level.get("suffix")),
                        ("justify", level.get("justification")),
                        ("style", level.get("paragraph_style")),
                        ("restart_after", level.get("restart_after_level")),
                        ("legal", level.get("legal_numbering")),
                    ],
                )
            )
            if level.get("xml"):
                lines.append(f"structure={compact_xml(level['xml'])}")
        lines.append("")
    for index, number in enumerate(numbers, 1):
        lines.append(
            block_header(
                f"NUM{index}",
                [
                    ("id", number.get("num_id")),
                    ("abstract", number.get("abstract_num_id")),
                ],
            )
        )
        if number.get("xml"):
            lines.append(f"structure={compact_xml(number['xml'])}")
        lines.append("")
    for binding in bindings:
        lines.append(
            block_header(
                f"P{binding['paragraph_index']}",
                [
                    ("part", binding.get("source_path")),
                    ("loc", binding.get("location")),
                    ("table", binding.get("table_index")),
                    ("row", binding.get("row_index")),
                    ("cell", binding.get("cell_index")),
                    ("section", binding.get("section_index")),
                    ("style", binding.get("paragraph_style_id")),
                    ("source", binding.get("binding_source")),
                    ("source_style", binding.get("source_style_id")),
                    ("numbering", binding.get("numbering")),
                ],
            )
        )
        lines.extend([binding.get("text") or "<empty/>", ""])
    return "\n".join(lines).rstrip() + "\n"


def special_parts_text_output(records):
    manifest = records[0]
    items = records[1:]
    counts = {
        record_type: sum(item.get("record_type") == record_type for item in items)
        for record_type in (
            "special_node",
            "run",
            "special_part",
            "document_property",
            "macro",
        )
    }
    lines = [
        "# Dimension 9: special nodes and parts",
        f"source: {manifest['source']}",
        "syntax: [NODE<n>] is an inline special node, [RUN<n>] its semantic Run reference, [PART<n>] a comments/notes part, [ENTRY<n>] one part entry, [PROPERTY<n>] document metadata, and [MACRO<n>] a VBA payload.",
        f"text_policy: {BODY_TEXT_POLICY}.",
        "omitted: record_type; enclosing part XML duplicated by entry structures; raw Run and drawing XML.",
        "normalized: OOXML structures use compact prefix:tag(attribute,child) notation.",
        "",
    ]
    if not items:
        lines.append("records: none")
    indexes = {key: 0 for key in counts}
    for item in items:
        record_type = item.get("record_type")
        indexes[record_type] = indexes.get(record_type, 0) + 1
        index = indexes[record_type]
        if record_type == "special_node":
            lines.append(
                block_header(
                    f"NODE{index}",
                    [
                        ("tag", item.get("tag")),
                        ("part", item.get("source_path")),
                        ("loc", item.get("location")),
                        ("attrs", item.get("attrs")),
                        ("relationship", item.get("relationship")),
                    ],
                )
            )
            if item.get("text"):
                lines.append(item["text"])
            if item.get("xml"):
                lines.append(f"structure={compact_xml(item['xml'])}")
        elif record_type == "run":
            lines.append(
                block_header(
                    f"RUN{index}",
                    [
                        ("part", item.get("source_path")),
                        ("loc", item.get("location")),
                        ("paragraph_loc", item.get("paragraph_location")),
                        ("paragraph", item.get("paragraph_index")),
                        ("run", item.get("run_index")),
                        ("link", item.get("hyperlink")),
                        ("fields", item.get("field_codes")),
                        (
                            "drawings",
                            [
                                drawing_summary(drawing)
                                for drawing in item.get("drawings", [])
                            ],
                        ),
                    ],
                )
            )
        elif record_type == "special_part":
            lines.append(
                block_header(
                    f"PART{index}",
                    [
                        ("part", item.get("part")),
                        ("entries", len(item.get("entries", []))),
                    ],
                )
            )
            if item.get("text"):
                lines.append(item["text"])
            if item.get("xml"):
                root = parse_xml(item["xml"].encode("utf-8"))
                lines.append(
                    f"root={qname(root.tag)}"
                    + (f" attrs={inline_value(attrs(root))}" if root.attrib else "")
                )
            for entry_index, entry in enumerate(item.get("entries", []), 1):
                lines.append(
                    block_header(
                        f"ENTRY{entry_index}",
                        [
                            ("tag", entry.get("tag")),
                            ("loc", entry.get("location")),
                            ("attrs", entry.get("attrs")),
                        ],
                    )
                )
                if entry.get("text"):
                    lines.append(entry["text"])
                if entry.get("xml"):
                    lines.append(f"structure={compact_xml(entry['xml'])}")
        elif record_type == "document_property":
            lines.append(
                block_header(
                    f"PROPERTY{index}",
                    [("part", item.get("part"))],
                )
            )
            lines.extend(
                f"{key}={inline_value(value)}"
                for key, value in item.get("properties", {}).items()
            )
            if item.get("xml"):
                lines.append(f"structure={compact_xml(item['xml'])}")
        elif record_type == "macro":
            lines.append(
                block_header(
                    f"MACRO{index}",
                    [
                        ("part", item.get("part")),
                        ("size", item.get("size")),
                        ("sha256", item.get("sha256")),
                    ],
                )
            )
        else:
            lines.append(
                block_header(
                    f"RECORD{index}",
                    [
                        ("type", record_type),
                        (
                            "data",
                            lean_value(item, {"record_type", "xml"}),
                        ),
                    ],
                )
            )
            if item.get("xml"):
                lines.append(f"structure={compact_xml(item['xml'])}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def inherited_style_numbering(styles, style_id):
    styles_by_id = {style["style_id"]: style for style in styles}
    visited = set()
    while style_id and style_id not in visited:
        visited.add(style_id)
        style = styles_by_id.get(style_id)
        if style is None:
            return None, None
        if style.get("numbering"):
            return style["numbering"], style_id
        style_id = style.get("based_on")
    return None, None


def records_for_dimension(data, dimension):
    context = context_records(data, dimension)
    if dimension == 1:
        return context + data["sections"]
    if dimension == 2:
        return context + [item for item in data["content"] if item["record_type"] == "paragraph"]
    if dimension == 3:
        return context + [item for item in data["content"] if item["record_type"] == "run"]
    if dimension == 4:
        style_parts = [
            item
            for item in data["raw_parts"]
            if item["part"]
            in ["word/styles.xml", "word/theme/theme1.xml", "word/fontTable.xml"]
        ]
        return context + data["styles"] + style_parts
    if dimension == 5:
        return context + [item for item in data["content"] if item["record_type"] == "table"]
    if dimension == 6:
        return context + data["objects"] + [
            item
            for item in data["content"]
            if item["record_type"] == "run" and item.get("drawings")
        ]
    if dimension == 7:
        return context + data["headers_footers"]
    if dimension == 8:
        paragraph_numbering = []
        for item in data["content"]:
            if item["record_type"] != "paragraph":
                continue
            numbering = item.get("numbering")
            binding_source = "direct"
            source_style_id = None
            if numbering is None:
                numbering, source_style_id = inherited_style_numbering(
                    data["styles"],
                    item.get("style_id"),
                )
                binding_source = "style"
            if numbering is None:
                continue
            if str(numbering.get("num_id")) == "0":
                continue
            paragraph_numbering.append(
                {
                    "record_type": "paragraph_numbering_binding",
                    "source_path": item["source_path"],
                    "location": item["location"],
                    "paragraph_index": item["paragraph_index"],
                    "table_index": item["table_index"],
                    "row_index": item["row_index"],
                    "cell_index": item["cell_index"],
                    "section_index": item["section_index"],
                    "paragraph_style_id": item.get("style_id"),
                    "binding_source": binding_source,
                    "source_style_id": source_style_id,
                    "numbering": numbering,
                    "text": item["text"],
                }
            )
        return context + data["numbering"] + paragraph_numbering
    if dimension == 9:
        return context + data["special"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("filename")
    parser.add_argument("-d", "--dimension", type=int, required=True, choices=range(10))
    parser.add_argument("-o", "--output", required=True, help="utf-8 输出文件路径")
    parser.add_argument("--asset-dir", help="dimension=6 时导出媒体/嵌入对象")
    parser.add_argument("--include-media-base64", action="store_true")
    args = parser.parse_args()

    source = Path(args.filename)
    output_path = Path(args.output).expanduser()
    if args.asset_dir and args.dimension != 6:
        parser.error("--asset-dir is supported only for dimension 6")
    if args.include_media_base64 and args.dimension != 6:
        parser.error("--include-media-base64 is supported only for dimension 6")
    if not source.is_file():
        parser.error(f"file does not exist: {source}")
    if source.suffix.lower() not in {".doc", ".docx"}:
        parser.error("filename must be a .doc or .docx file")
    if source.resolve() == output_path.resolve() or (
        output_path.exists() and source.samefile(output_path)
    ):
        parser.error("output path must differ from input file")
    if source.suffix.lower() == ".doc":
        with tempfile.TemporaryDirectory() as tmp_name:
            docx_path = convert_with_libreoffice(source, Path(tmp_name), "docx")
            if docx_path is None:
                write_output_file(output_path, "当前环境中没有libreoffice\n")
                return
            data = (
                build_sections_data(docx_path, source)
                if args.dimension == 1
                else build_data(docx_path, source, args.asset_dir, args.include_media_base64)
            )
    else:
        data = (
            build_sections_data(source, source)
            if args.dimension == 1
            else build_data(source, source, args.asset_dir, args.include_media_base64)
        )

    if args.dimension == 0:
        output = markdown_output(data)
    else:
        records = records_for_dimension(data, args.dimension)
        output = {
            1: sections_text_output,
            2: paragraphs_text_output,
            3: runs_text_output,
            4: styles_text_output,
            5: tables_text_output,
            6: objects_text_output,
            7: headers_footers_text_output,
            8: numbering_text_output,
            9: special_parts_text_output,
        }[args.dimension](records)
    write_output_file(output_path, output)


if __name__ == "__main__":
    main()
