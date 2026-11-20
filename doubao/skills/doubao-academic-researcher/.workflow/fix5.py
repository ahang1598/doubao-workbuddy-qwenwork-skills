import io
p = r"D:\AI\code\solo\hu\compare\2023年以来self-instruct小论文调研.md"
p = r"D:\AI\code\solo\hu\compare\2023年以来self-instruct小模型论文调研.md"
s = io.open(p, encoding="utf-8").read()
s = s.replace("发现 Self-Instruct 的表现明显不如在大模型上，原因是大模型才具备足够的 in-context 学习能力去稳定地"照着种子写新任务"",
              "发现 Self-Instruct 的表现明显不如在大模型上；按论文的观察，一个合理解释是只有足够大的模型才具备稳定的 in-context 学习能力去"照着种子写新任务"")
io.open(p,"w",encoding="utf-8").write(s)
print("ok")
