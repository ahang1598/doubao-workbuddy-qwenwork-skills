import io
p = r"D:\AI\code\solo\hu\compare\2023年以来self-instruct小模型论文调研.md"
s = io.open(p, encoding="utf-8").read()
notice = "提示：以下内容是基于本次大方向调研生成的文献综述格式参考稿，用于示范如何组织已有研究、判断与引用；后续若要围绕具体细分题目写作，仍需根据该细分方向重新筛选、核验和补充文献，不应直接作为论文成品段落使用。\n\n"
s = s.replace("## 十、完整文献综述参考稿\n\n", "## 十、完整文献综述参考稿\n\n" + notice, 1)
io.open(p,"w",encoding="utf-8").write(s)
print("ok")
