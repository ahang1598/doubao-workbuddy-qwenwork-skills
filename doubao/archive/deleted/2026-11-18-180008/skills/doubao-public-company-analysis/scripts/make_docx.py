#!/usr/bin/env python3
import re,sys,zipfile
from pathlib import Path
from xml.sax.saxutils import escape
def p(text,style=None):
    prop=f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f'<w:p>{prop}<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'
def main():
    if len(sys.argv)!=3:print("usage: make_docx.py input.md output.docx");return 2
    src=Path(sys.argv[1]);out=Path(sys.argv[2]);blocks=[]
    for raw in src.read_text(encoding="utf-8").splitlines():
        line=re.sub(r"\{fact:[^}]+\}","",raw.strip())
        if line.startswith("# "):blocks.append(p(line[2:],"Title"))
        elif line.startswith("## "):blocks.append(p(line[3:],"Heading1"))
        elif line.startswith("### "):blocks.append(p(line[4:],"Heading2"))
        elif re.match(r"^[-*] ",line):blocks.append(p("• "+line[2:]))
        else:blocks.append(p(line))
    document='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+''.join(blocks)+'<w:sectPr/></w:body></w:document>'
    types='<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'
    rels='<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:z.writestr("[Content_Types].xml",types);z.writestr("_rels/.rels",rels);z.writestr("word/document.xml",document)
    print(out);return 0
if __name__=="__main__":raise SystemExit(main())
