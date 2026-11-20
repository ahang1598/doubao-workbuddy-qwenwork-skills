import io
for p in [".workflow/report_body.md", r"D:\AI\code\solo\hu\compare\2023年以来self-instruct小模型论文调研.md"]:
    s = io.open(p, encoding="utf-8").read()
    s = s.replace("（Xu 等，2024；Luo 等，2024）", "（Xu et al.，2024；Luo et al.，2024）")
    s = s.replace("（Cui 和 Wang，2024）", "（Cui & Wang，2024）")
    io.open(p, "w", encoding="utf-8").write(s)
print("ok")
