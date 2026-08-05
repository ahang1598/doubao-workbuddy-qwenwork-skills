---
name: doubao-market-hotspot
description: 面向普通股民的市场整体与宏观事件解读。用户关注全市场涨跌、交易主线、市场热点、宏观/政策/新闻/风险事件、央行利率、通胀就业、跨资产联动、资金风险偏好或市场情绪时使用。命中后先输出结构完整、观点深入的对话框分析，用户确认后通过 lark-doc 写入飞书 XML 文档。不要用于单股、具体板块/行业/公司/财报分析，或荐股、目标价、买卖点、仓位建议；不确定时先澄清。飞书交付需已安装 lark-doc 伴生 Skill。
---

# 股民简报 / 市场信息与事件解读

把用户关注的**市场整体、宏观/政策/新闻/风险事件、跨资产联动和市场情绪**，整理成**专业、可溯源、可证伪**的研究输出。目标是直接回答「核心判断是什么、事实怎么变、为什么重要、如何传导、分歧在哪里、后续怎么验证」。

分析开始前，先按 `references/analysis-playbook.md` 选择主 Lens 和 1–3 个辅助 Lens。Lens 只规定思考方式，不暴露给前台章节。

## 技能包组成

本 Skill **仅**含 `SKILL.md` + `references/`（Markdown/XML 契约与范例）。交付质量靠契约 + `qa-checklist.md` 自检。

## 前置依赖

飞书文档交付依赖伴生 Skill **`lark-doc`**。进入第二阶段前读 `references/feishu-doc-style.md`「前置依赖」并确认已加载；未安装则只交付第一阶段正文，**不得**降级为 Markdown / `docs +create`。

## 路由边界

**触发**：全市场涨跌归因、交易主线、宏观/政策/风险事件、跨资产联动、风险偏好/情绪。  
**不触发**：单股日报、板块热度、行业/公司深度、财报、荐股/目标价/买卖点 → 转相邻 Skill 或澄清。  
完整分类见 `references/question-types.md`。

## 阶段读取路径

启动后只读本文件。按阶段读取 contract，不要一次性读全目录。

**第一阶段（检索 + 对话框正文）：**

1. `references/question-types.md` — 问题类型、时间窗、转接
2. `references/analysis-playbook.md` — Lens 选择与洞见框架
3. `references/search-playbook.md`、`references/source-verification.md` — 检索与来源
4. `references/chat_contract.md`、`references/chat_example.md` — 写正文前必读

**用户确认生成飞书文档后：**

1. `references/feishu-doc-style.md` — MD→XML 映射（对照 `references/example_feishu.xml`；免责声明读 `references/disclaimers.json`）
2. `references/qa-checklist.md` — 交付门禁

**按需读取：** `references/compliance.md`

## 第一阶段流程

1. 判定问题类型、市场范围、时间窗、是否越界。
2. 选择 Lens；决定检索角度与洞见重心。
3. 检索取证、去重合并；传闻默认不进入前台。**行情/库内数字须挂靠可打开文章 URL 再编号，禁止 `（行情数据）` 占位**（见 `source-verification.md`）。
4. 建议写入 `work/<主题>_分析草稿.md`（内部工作文件，不交付用户）。
5. 按 `chat_contract.md` 写**完整对话框正文**；写前读 `chat_example.md` 校准深度。
6. 正文必须以固定句结尾，等待用户确认。

固定结尾（**用户可见输出的最后一行，输出后立刻停止**）：

> 下一步是否为您生成飞书文档版？

**交付终止（硬规则）：** 固定结尾句之后**不得**再输出任何内容——无空行、无附言、无第二段、无 bullet 摘要、无改写版飞书问句。详见 `chat_contract.md`「交付终止」。

**第一阶段禁止：** 构造 lark-doc XML、调用 `lark-doc`、输出「仅预览摘要」代替完整正文；正文前后或结尾后再写「核心结论如下」类 TL;DR；暴露 Skill 名或「已按 Skill 完成」类元叙述。

## 飞书文档流程

用户对上述问句作出**肯定性回复**后即进入（如「需要」「好的」「可以」等）。用户拒绝或改提其他需求时不进入。不重新检索，复用第一阶段已验证正文与来源。

1. 读 `feishu-doc-style.md`；**若 `lark-doc` 不可用，停止本流程**（见该文件「前置依赖」），说明原因并给出安装指引，保留第一阶段正文。
2. 基于第一阶段正文（或 `work/<主题>_分析草稿.md`）**直接组装** lark-doc XML；组装前读取 `disclaimers.json`；只允许原句搬运与 Markdown→XML 结构转换，禁止压缩、改写、同义替换或新增判断。
3. 建议写入 `work/<主题>_飞书.xml`（内部工作文件，不交付用户），便于自检。
4. 跑 `qa-checklist.md` 逐项自检；失败则回母版补正文或修正 XML 后重检。
5. 调用 `lark-doc` skill 写入飞书文档；写入后按 `feishu-doc-style.md` 复核真实渲染。

**如 `lark-doc` 写入失败：** 说明阻塞原因，保留已交付的第一阶段正文；**不得**改用 Markdown、`docs +create` 或其他格式静默替代。

## 冲突优先级

1. `references/qa-checklist.md` 硬规则
2. 本文件的阶段流程
3. `chat_contract.md`、`feishu-doc-style.md`
4. `chat_example.md`、`references/example_feishu.xml` 与其它长参考

## 免责声明

第一阶段正文第一行逐字输出固定风险提醒（见 `chat_contract.md`）。  
飞书文档免责声明正文逐字来自 `references/disclaimers.json`（注入方式见 `feishu-doc-style.md`），不得从第一阶段搬运短风险提醒行或模块9 风险条目。
