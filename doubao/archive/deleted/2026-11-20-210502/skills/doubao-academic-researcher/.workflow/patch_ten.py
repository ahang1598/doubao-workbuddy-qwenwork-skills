import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
doc = (root / ".workflow" / "report_doc.xml").read_text(encoding="utf-8")
draft = (root / ".workflow" / "review_draft.md").read_text(encoding="utf-8").strip()

hint = "提示：以下内容是基于本次大方向调研生成的文献综述格式参考稿"
hint_idx = doc.index(hint)
hint_end = doc.index("</p>", hint_idx) + len("</p>")

end_marker = "<h1>十一、参考文献</h1>"
end_idx = doc.index(end_marker)

paras = [p.strip() for p in re.split(r"\n\s*\n", draft) if p.strip()]
body = "\n".join("<p>" + p + "</p>" for p in paras) + "\n"

new_doc = doc[:hint_end] + "\n" + body + doc[end_idx:]
(root / ".workflow" / "report_doc.xml").write_text(new_doc, encoding="utf-8")
print("paragraphs:", len(paras), "len:", len(new_doc))
