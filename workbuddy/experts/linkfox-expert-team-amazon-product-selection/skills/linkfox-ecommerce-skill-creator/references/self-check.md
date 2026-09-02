# 统一自检 Checklist

> 每个 skill 交付前过一遍。分 4 组，含条件必勾项（报告、商品列表、已挂载能力、并发、大纲化）。逐条勾选，不通过回到对应步骤补救。
>
> 本 checklist 适用于 Tier 2（跨源组合 / 流程编排）与 Tier 3 skill。Tier 1（单源 wrapper）由各 vendor 自行维护，不在本范围。

---

## A. Frontmatter（5 条）

- [ ] **1**. `name` = 目录名 = 交付 slug，三者完全一致；只能使用小写字母、数字和连字符 `-`（正则：`^[a-z0-9-]+$`），无大写、无下划线、无空格、无中文。
- [ ] **2**. frontmatter 只用允许的 6 个字段（`name` / `description` / `license` / `allowed-tools` / `metadata` / `compatibility`）；其它字段已删除。
- [ ] **3**. `description` 含 5–10 个同义改写短语，覆盖中英两种说法。
- [ ] **4**. `description` 末尾有"反向补漏"一句（如"即使用户只说……也应触发"或反向限定"X 不在本范围"）。
- [ ] **5**. `description` ≤ 1024 字符，不含 `<` `>` 字符；`compatibility` ≤ 500 字符。

> 跑 `python scripts/quick_validate.py <skill 目录>` 自动校验 1/2/5；流程型产物交付前跑 `python scripts/quick_validate.py --type A <skill 目录>`，会额外校验 runtime helper hash。

---

## B. 结构（4 条）

- [ ] **6**. Tier 已选定（Tier 2 / Tier 3），主体章节齐全（参考 `SPEC.md` §6 矩阵）。
- [ ] **7**. 目录结构符合 `references/target-structure.md`：必有 SKILL.md，按需有 references / scripts / examples。
- [ ] **8**. `scripts/response_io.py` 已从本 skill 复制进产物，hash 与本 skill 一致；`scripts/linkfox_paths.py` 已从 `linkfoxagent-v2/_shared/linkfox_paths.py` 复制进产物，hash 与 `_shared` 一致。
- [ ] **9**. `scripts/*.py` 文件命名 kebab-case，每个文件单一职责。

---

## C. 内容（4 条）

- [ ] **10**. 每个 `scripts/*.py` 通过三步回环验证（见 `verification-guide.md`）。
- [ ] **11**. 大 I/O 双向暂存到位：**响应端**——满足落盘特征的步骤（字段数 ≥ 10 / 含数组 / 分页 / 长文本 / 跨步复用）已嵌入 `large-response-snippet.md` 段落；**请求端**——参数含大数组 / 长文本 / 来自上游落盘文件的步骤改用 `response_io.py run --params-file`，未把大 JSON 拼进命令行/上下文。命令路径指向**产物自身的** `scripts/response_io.py`。
- [ ] **12**. 至少 2–3 条试跑提示词写在 `examples/trial-prompts.md`，覆盖核心 + 边界 + 欠触发探针三类。
- [ ] **13**. 局限性章节真实可信——只列实际遇到的限制，不臆测。
- [ ] **13b (报告类必勾)**. 含「报告产物」章节的 skill：章节末尾含 `linkfox-report-generator` handoff 段落（语义为"报告必须由该 skill 接管样式 / 导出"，不是"建议"）；本 skill 内**没有**复制报告样式 / html 骨架 / 配色 / 字号规范。
- [ ] **13c (商品列表必勾)**. 最终交付为商品列表时：JSON 为裸 `{ products: [...] }` 形状（见产物 `references/output-schema.md`）；`examples/` 有样本且 `python scripts/validate_product_payload.py <样本>` 通过。
- [ ] **13d**. 已挂载能力检查完整：产物每个可执行步骤引用的公共 skill 均已在当前 agent 挂载；未挂载能力只出现在局限性 / 安装提示中，未写成当前可执行步骤；安装提示指向技能广场或 `https://skill.linkfox.com/`。

---

## D. Tier 特定（1 条）

- [ ] **14**. DAG 自检通过：每个步骤的输出至少有一条出边指向"下游步骤的输入 / 报告章节 / 用户决策"；每个交付字段至少有一条入边可反向追溯到某步骤的输出。Tier 1 调用清单完备（每步注明真实 skill slug，如 `linkfox-amazon-product-detail`，以及入参）。
- [ ] **14b**. 并发设计到位：每步写齐 `依赖` 字段；无数据依赖的步骤已归入并行层；流水线章节开头有「执行编排」说明并行计划；不存在"彼此无依赖却被串行"的疑似无谓串行。
- [ ] **14c (长流程必勾)**. 大纲化到位：步骤 ≥ 4 或单步细节重的流程，SKILL.md 流水线章节是**大纲**（执行编排 + 总览表，每步含 `依赖` / `用途` / 指向 `references/steps/S<N>.md`）；单步血肉已拆到 `references/steps/S<N>.md`，agent 按步加载。短流程（≤ 3 步且每步几行）可内联，免勾。

最后一条统一：

- [ ] **15**. 跑 `python scripts/quick_validate.py --type A <skill 目录>` 通过；`scripts/verify_skill_scripts.py <skill 目录>` 通过（无 scripts 时跳过）。

---

## 自检失败的处理

| 失败项 | 回到哪一步 |
|--------|-----------|
| 1–5（Frontmatter） | 改 SKILL.md frontmatter，对照 `frontmatter-spec.md` |
| 6（章节缺失） | 对照 `SPEC.md` §6 主体矩阵补齐 |
| 7（目录结构） | 对照 `target-structure.md` 调整 |
| 8（runtime helpers） | 复制本 skill 的 `scripts/response_io.py` 进产物；复制 `linkfoxagent-v2/_shared/linkfox_paths.py` 为产物 `scripts/linkfox_paths.py` |
| 9（命名） | 重命名 .py 文件，更新 SKILL.md 引用 |
| 10（脚本验证） | 修脚本，重跑三步回环验证 |
| 11（落盘段落） | 嵌入 `large-response-snippet.md` |
| 12（试跑词） | 写 examples/trial-prompts.md |
| 13（局限性） | 删臆测项；补真实限制 |
| 13b（报告 handoff） | 在「报告产物」章节末尾植入 `linkfox-report-generator` handoff，删除本 skill 内复制的样式 / html |
| 13c（商品列表 payload） | 改 JSON 形状；补 examples 样本；跑 validate_product_payload.py |
| 13d（已挂载能力） | 对照当前 agent 已挂载 skill 清单重做选型；未挂载能力改为安装提示或阻断说明 |
| 14（DAG） | 用途字段补全；确认每步有出边、每个交付字段有来源 |
| 14b（并发） | 回访谈阶段 4 补 `依赖` 字段与并行层；在流水线章节开头补「执行编排」 |
| 14c（大纲化） | 把 SKILL.md 流水线收成大纲（总览表），单步血肉拆到 `references/steps/S<N>.md`，见 `workflow-skill-template.md` §3 |
| 15（validator） | 看 validator 报错信息 |

不通过即不算交付。

---

## 软警告（不阻塞但建议处理）

`quick_validate.py --strict` 模式下，以下会从 warning 升级为 fail：

- description 含中文同义词但缺英文（或反之）。
- description 缺反向补漏关键词（"即使" / "even if" / "也应" / "should also" 之一）。
- SKILL.md > 500 行而未拆分到 `references/`（progressive disclosure 不到位）。
- examples/ 目录不存在或为空（试跑词缺失）。
- 多步流程（≥ 2 步）完全没有并发设计标注（缺 `依赖` / 并行 / 执行编排）。
- 长流程（步骤 ≥ 4 或 SKILL.md 正文 > 200 行）未大纲化、无 `references/steps/`（细节一次性灌入易致注意力失焦）。
