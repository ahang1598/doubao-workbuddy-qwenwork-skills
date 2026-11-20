import io, json, os
body = io.open(".workflow/report_body.md", encoding="utf-8").read()
draft = io.open(".workflow/review_draft.md", encoding="utf-8").read().strip()
body = body.replace("<!-- REVIEW_DRAFT_PLACEHOLDER -->", draft)
out = r"D:\AI\code\solo\hu\compare\2023年以来self-instruct小模型论文调研.md"
os.makedirs(os.path.dirname(out), exist_ok=True)
io.open(out, "w", encoding="utf-8").write(body)
print("written", out, len(body))

p = ".workflow/requirement_checklist.json"
d = json.load(io.open(p, encoding="utf-8"))
res = {
 "R1": "六、主题章节（一）–（三）逐条列出并分析；第十一节参考文献第 1–10 条",
 "R2": "第三节文献多维地图表与（一）（二）（三）对比表的「评测方式 / benchmark」列，主题章节正文逐篇给出 benchmark 名称",
 "R3": "四、研究视角与本文结构的分类轴说明；七、争议与开放问题末尾「条件不完全满足的边界工作」清单（6 篇）",
 "R4": "一、核心结论 6 条判断；七、争议与开放问题；八、可研究的方向 5 条",
}
for r in d["requirements"]:
    if r["id"] in res:
        r["resolution"] = res[r["id"]]
json.dump(d, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("checklist updated")
