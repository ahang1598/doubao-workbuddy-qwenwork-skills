"""Expose XML as UTF-8 for byte patches, then restore its original encoding."""
import codecs
import re

_DECLARATION = re.compile(r"^<\?xml\s[^?]*\?>")
_ENCODING = re.compile(r'''\bencoding\s*=\s*(['"])([^'"]+)\1''')
_BYTE_ENCODING = re.compile(br'''^<\?xml\s[^?]*?\bencoding\s*=\s*(['"])([^'"]+)\1''')


def _source_encoding(raw):
    for bom, encoding in [(codecs.BOM_UTF8, "utf-8"),
                          (codecs.BOM_UTF16_LE, "utf-16-le"),
                          (codecs.BOM_UTF16_BE, "utf-16-be")]:
        if raw.startswith(bom):
            return encoding, bom
    if raw.startswith(b"<\x00"):
        return "utf-16-le", b""
    if raw.startswith(b"\x00<"):
        return "utf-16-be", b""
    declared = _BYTE_ENCODING.match(raw)
    return (declared.group(2).decode("ascii") if declared else "utf-8"), b""


def _codec_name(encoding):
    try:
        return codecs.lookup(encoding).name
    except LookupError as exc:
        raise ValueError("unsupported XML encoding: " + encoding) from exc


class PatchXml:
    def __init__(self, raw):
        self.raw = raw
        encoding, self.bom = _source_encoding(raw)
        self.encoding = _codec_name(encoding)
        text = raw[len(self.bom):].decode(self.encoding)
        declaration = _DECLARATION.match(text)
        self.declaration = declaration.group() if declaration else ""
        declared = _ENCODING.search(self.declaration)
        if declared:
            declared_encoding = _codec_name(declared.group(2))
            if declared_encoding != self.encoding and not (
                    declared_encoding == "utf-16" and self.encoding in ("utf-16-le", "utf-16-be")):
                raise ValueError("XML declaration conflicts with byte encoding")
            text = text[:declared.start(2)] + "UTF-8" + text[declared.end(2):]
        self.utf8 = text.encode("utf-8")

    def restore(self, patched):
        if patched == self.utf8:
            return self.raw
        text = patched.decode("utf-8")
        if self.declaration:
            declaration = _DECLARATION.match(text)
            if declaration is None:
                raise ValueError("XML patch removed the declaration")
            text = self.declaration + text[declaration.end():]
        return self.bom + text.encode(self.encoding)
