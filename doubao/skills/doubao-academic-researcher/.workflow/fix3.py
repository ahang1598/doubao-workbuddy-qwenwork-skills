import io
p = r"D:\AI\code\solo\hu\compare\2023年以来self-instruct小模型论文调研.md"
s = io.open(p, encoding="utf-8").read()
reps = [
 ("（Wei 等，2024）", "（Wei et al.，2024）"),
 ("（Xu 等，2025）", "（Xu et al.，2025）"),
 ("（Mukherjee 等，2023；Mitra 等，2023）", "（Mukherjee et al.，2023；Mitra et al.，2023）"),
 ("（Ma 等，2025 的日语部分）", "（Ma et al.，2025 的日语部分）"),
 ("横评 7B/13B 模型，发现", "横评 7B/13B/65B 模型，发现"),
 ("## 五、核心逻辑图\n\n<whiteboard type=\"mermaid\">",
  "## 五、核心逻辑图\n\n图按“核心问题 → 五条路线 → 路线之间的限定与反驳”组织：配比与规模边界（D）限定了规模路线（A）与生成器路线（B）的适用区间；生成器路线（B）成熟后又分化出种子源替换（C），而（C）反过来为（B）补充了“复杂度从哪来”的来源；人类指令反证（E）既反驳（A）的“量足够”假设，也限定了（C）的适用范围。\n\n```mermaid"),
 ("</whiteboard>", "```"),
]
for a,b in reps:
    s = s.replace(a,b)
io.open(p,"w",encoding="utf-8").write(s)
print("ok", "whiteboard" in s)
