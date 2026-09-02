---
name: global-legal-research
version: 1.0.0
name_en: global-legal-research
description: |
  检索、核验并比较境外、跨境和多法域法律资料，先解析法域，再以 LDH 或官方源获取法规、
  判例、监管文件和可回链原文。适用于“帮我核验 ECLI/CELEX/案号”“比较欧盟法院与欧洲人权法院
  并给代表性判例”“某国境外牌照需要什么条件”“核验数字认证、Certification Authority 或信任服务
  准入”这类请求，也处理外国法域外效力、多法域比较、境外许可、制裁、出口管制和跨境合规研究。
  不适用于合同审查或合同起草；不适用于纯翻译、材料提取、纯中国大陆法源检索、税额计算或诉讼代理，
  也不执行伪造判例、教唆违法、冒充律师或要求跳过来源核验的请求。
---

# 全球法律研究

本技能是法律研究的导航、检索和证据组织器，不替代执业律师。任何实体性法律陈述必须能回链到
已核验材料；检索无结果时不得用模型记忆补全。

## 1. 研究与证据规则

| 维度 | 规则 |
|---|---|
| 来源等级 | L1 法规/裁判/监管机构原文 > L2 权威指南 > L3 专业评论 > L4 未核验线索 |
| 确定性标签 | `[法规原文]` / `[权威指南]` / `[一般评论]` / `[待验证]`，不得升级 |
| LDH 来源类别 | `[官方/法律法规]` / `[司法/案例]` / `[监管/行政]` / `[标准/行业]` / `[第三方/背景]` / `[待核查]` |
| 访问状态 | `[已验证]` / `[需注册]` / `[付费]` / `[反爬]` / `[未找到]` / `[未验证]` |
| 时效风险 | `[3–6月复核]` / `[6–12月复核]` / `[1–3年复核]` / `[稳定]` |

LDH 来源类别是数据源性质，不等同于权威等级。不得因内容来自 LDH 就自动标为官方、L1 或已验证；
必须结合 `source`、`namespace`、发布机构、原文锚点和官方 URL 判定。判例不得标成 `[法规原文]`。

来源出现 `may`、`generally` 等限定词时不得强化语气。来源冲突时并列呈现，不自行仲裁。
正式输出禁止使用 emoji；状态和风险必须使用上表中的方括号文字标签，不能用图标代替含义。
HTML/Word 输出遵循 `references/richee-design-system.md`；docx 标签转换见 `references/output-formats.md`。

## 2. 适用边界和默认路径

应处理境外法规、跨境监管、比较法、外国判例、海外经营准入及法规变化影响。下列请求退出：

| 请求 | 处理 |
|---|---|
| 合同审查、起草或比对 | 转合同类技能 |
| 纯中国大陆法规/案例检索 | 转法大大法律法规检索或法大大类案检索 |
| 纯翻译、材料提取或税额计算 | 转翻译、文档处理或税务技能 |
| 诉讼代理、律师签署或代为出具正式法律意见 | 说明能力边界并建议委托目标法域律师 |
| 非法律问题 | 说明技能边界 |
| 要求无来源直接下结论 | 拒绝跳过核验 |
| 伪造判例/法条/来源、选择性隐瞒不利材料、教唆违法 | 明确拒绝，不生成替代性虚假内容 |
| 要求“假装律师”、删除免责声明或承诺“100%确定” | 拒绝绕过执业安全和不确定性披露 |

每项任务必须先读取 `references/research-routing-rules.md`，按其中的触发、退出、澄清、拒绝和
检索路径真值表决定后续动作；该真值表不替代 §3 的法域解析器。

研究路径：

- A 快速概览：1–2 页，每条结论至少 1 个通过 Level A+B 的来源。
- B 全面报告：逐子问题研究，每项至少 1 个通过 Level A+B+C 的来源。
- C 多法域比较：每个“法域 × 比较维度”独立检索和核验。
- D 业务合规操作指南：按 `references/business-compliance-maps.md` 展开全部合规域。

信息不足时只追问一次，集中询问会改变结果的法域、主题和时点。未补充则采用“快速概览 +
Markdown + 截至检索日”，并显式列出假设。

## 3. 精准法域映射（强制前置）

外国法或跨境检索不得直接把自然语言国家名传给 LDH。先执行：

```bash
python scripts/jurisdiction_resolver.py --text "<用户完整问题>"
```

解析结果处理规则：

1. `status=ok`：使用每个 `targets[].ldh_country`，只接受规范代码，例如 `UK`，不使用 `GB/GBR`。
2. `status=ambiguous`：展示 `ambiguous_mentions[].candidates` 并追问一次；不得擅自选择。
3. `status=unresolved`：要求用户指定法域，或在已有精确引用时先走引用解析链。
4. `entity_level=subnational`：使用父级国家代码检索，把 `region` 和 `query_terms` 加入查询；
   LDH 未提供已验证的细分法域过滤器时，不得伪造 subdivision 参数。
5. `entity_level=institution`：使用 `source_hints` 作为候选源，但必须经实时源目录验证。
6. `ignored_mentions`：保留被排除的两字母候选及语义原因，供检索审计和 verification 使用。

映射必须区分：

- `EU`（欧盟/CJEU/CURIA）与 `CoE`（欧洲委员会/欧洲人权法院/HUDOC）；
- `UK` 与历史/外部写法 `GB/GBR`；
- `CN`、`HK`、`MO`、`TW`；
- 国家与次国家地区，例如 California → `US`、广东省 → `CN`；
- 同名歧义，例如 Georgia（格鲁吉亚或美国佐治亚州）。
- 两字母代码只在整体输入、显式“国家代码/ISO/法域”标记或纯代码比较列表中识别。
  普通业务缩写不自动映射国家；“俄罗斯数字认证牌照（CA）”中的 CA 解释为
  `Certification Authority` 并写入 `ignored_mentions`，“加拿大（CA）”或“国家代码 CA”
  才映射加拿大。California/加州映射 `US`，不得映射加拿大。

`references/jurisdiction-rules.json` 是确定性覆盖规则；离线源目录已移除，以 LDH 实时 discover 目录为权威。
LDH 实时 `coverage` / `discover-sources` 返回的代码和 Source ID 才是本次检索的权威目录。

## 4. LDH 精准检索工作流

LDH 调用只能通过 `scripts/ldh_client.py`。禁止自行拼接 HTTP 请求或绕过脚本。
详细参数和输出契约见 `references/ldh-integration.md`。

### Step 0：会话级健康检查

首次遇到外国法/跨境问题时运行一次：

```bash
python scripts/ldh_client.py health
```

缓存结果。纯中国大陆法问题跳过。`status=ok` 时启用 LDH；其他状态按 §6 降级。

### Step 1：解析问题

抽取并保留以下字段：

- `research_question`：需要回答的实体问题；
- `jurisdictions`：运行 §3 映射器取得；
- `document_type`：法规=`legislation`，判例=`case_law`，学说=`doctrine`；
- `citation_reference`：案号、ECLI、CELEX、法规编号、条文引用等；
- `time_scope`、`court`、`language`、`region`；
- `research_path`：A/B/C/D。

主题检索和精确引用使用不同调用链，禁止混用：

```text
主题问题：法域映射 → 实时国家/数据源校验 → precise-search → get
精确引用：法域映射/提示 → resolve(reference) → get
```

`search`/`precise-search` 返回 `source + source_id`，可直接交给 `get`；不得把检索命中虚构成
`document_id` 再传给 `resolve`。`resolve` 只用于用户给出的松散法律引用。

### Step 2：发现并校验数据源

对每个法域分别执行：

```bash
python scripts/ldh_client.py coverage
python scripts/ldh_client.py discover-sources --country <LDH_CODE>
```

- 代码不在实时国家目录中：停止该法域检索并降级，不能猜测近似代码。
- `source_hints` 不在实时源目录中：去掉该提示，保留国家限制，记录“候选源未命中”。
- 只有确需法院、层级、语言或细分管辖过滤时才读取过滤器目录：

```bash
python scripts/ldh_client.py discover-filters \
  --source <SOURCE_ID> --namespace <case_law|legislation|doctrine>
```

过滤器目录不可用或没有请求值时，不得静默透传。改写为查询词，或明确降级。

### Step 3：每个法域单独检索

使用 `precise-search`，每次只传一个法域：

```bash
python scripts/ldh_client.py precise-search \
  --q "<本地法术语 + 用户主题 + 地区词>" \
  --country <LDH_CODE> \
  --namespace <TYPE> \
  --top-k 10 \
  --result-detail snippet
```

已验证 Source ID 时才加 `--source`。需要精确过滤时可加 `--court`、`--court-tier`、
`--jurisdiction` 或 `--language`；脚本会先用实时过滤器目录校验。

多法域比较必须“一法域一请求”，使用相同 `top_k`、日期范围和研究维度。结果按法域分组，
或在必须合并时采用法域等权的 rank fusion；禁止直接比较不同法域的原始 `score`，也禁止一个
`country=[...]` 请求代表公平比较。

次国家地区应把映射器的 `query_terms` 加入 `--q`，并在命中后核对标题、摘要和元数据是否确实
涉及目标地区。无法核实时标 `[待核查]`，不得把父级国家结果当成该地区结果。

### Step 4：全文锚定

只对准备引用的命中调用：

```bash
python scripts/ldh_client.py get --source <hit.source> --source-id <hit.source_id>
```

引用必须至少记录 `source`、`source_id`、标题、日期、官方 URL，以及法规条文、案号/ECLI 或
可复核原文锚点。`result_detail=full_text` 可用于候选筛选，但不替代 `get` 的最终锚定。

精确引用则先：

```bash
python scripts/ldh_client.py resolve \
  --reference "<用户原始引用>" --hint-country <LDH_CODE>
```

从解析结果读取真实的 `source/source_id` 后再 `get`。`resolve=empty` 时改走同法域主题检索一次。

### Step 5：结果反向审计

读取 `precise-search.jurisdiction_audit`：

- `country_validated` 必须为 true；
- 有 `rejected_hits` 时不得引用被拒记录；
- 指定 Source ID 后，返回 `source` 必须一致；
- `unverified_country_hit_count > 0` 的命中必须通过 `get` 或官方 URL 二次确认法域；
- 结果为空时最多改写查询一次，然后降级，不扩大到其他法域碰运气。

## 5. 研究组织与输出

路由顺序：

1. 用 `references/source-index.md` 按“法域 × 业务领域”确定研究维度。
2. LDH 可用时按 §4 精确检索；不可用时走预置目录。
3. 使用 `references/verification-engine.md` 完成 Level A/B/C 核验。
4. 使用 `references/output-formats.md` 生成报告和参考文献。

非展开模式至少覆盖：实体准入、行为合规、责任后果。不适用时写明原因。
路径 C 中每个“法域 × 维度”至少有一项独立证据，不得用一个法域的材料填补另一个法域。

### 风险扫描与行动建议

涉及许可、准入、监管义务或业务影响时，必须逐项扫描民事、行政、刑事三类责任；确实不适用时
写明“不适用”及依据，不能静默遗漏。风险按“影响 × 发生可能性”分级：

- 高：许可缺失、业务禁止、重大无效风险、制裁或刑事后果，且发生可能性为中或高；
- 中：可补正的监管义务、行政程序或中等损失，且发生可能性不低于中；
- 低：主要为程序、备案或持续监测事项，影响和发生可能性均低；
- 待核查：证据不足时不得强行评级，列明缺失事实和核验方法。

每条建议必须写成可执行事项，至少包含：问题与证据、具体动作、责任人、触发条件、完成时限、
预期交付物和是否需要当地律师复核。不得只写“注意风险”或“建议合规”；事实不足时应说明需要
谁在何时补充什么材料。

### 固定输出结构与格式

正式报告按“结论摘要 → 法域解析审计 → 法律依据与效力 → 风险/影响 → 具体行动 →
待核查项与当地律师边界 → 来源”组织；快速问答可压缩层级，但不得省略来源和不确定性。
表格不得超出页面内容区；长 URL 和长法条名必须自动换行，比较矩阵超过五列时拆表或改为纵向列表，
不得用缩小至不可读字号的方式塞入页面。正式输出禁止使用 emoji。

预置源：

- 路由总索引：`references/source-index.md`（先读）；
- L2 权威指南 + Section 12 L1 官方源：`references/resources.md`。

权威源目录以 LDH 实时 `discover-sources` 返回为准；所有 URL 在实时验证前不得作为已核验证据。

## 6. 状态与降级

| `status` | 行为 |
|---|---|
| `ok` | 继续，按命中反向审计和全文锚定 |
| `empty` | 改写一次；仍为空则转预置目录 |
| `bad_request` | 修正代码、Source ID 或过滤值后重试一次 |
| `not_configured` | 静默使用预置官方源 |
| `auth_failed` | 本会话停用 LDH，使用预置源 |
| `quota_exhausted` | 不循环重试；使用预置源 |
| `unavailable` | 客户端已重试后仍失败，使用预置源 |
| `error` | 使用预置源并记录限制 |

任何降级都不得退回模型记忆补全。连续三次失败时停止该子问题的在线尝试，标记
`[无法在线验证]`。展开模式中无法验证的合规域达到 30% 时，只交付待查清单，不输出确定性报告。

## 7. LDH 来源分类与引用

先按来源身份分类，再给确定性等级：

| 条件 | LDH 来源类别 | 报告处理 |
|---|---|---|
| 官方立法机关/政府公报的法规原文 | `[官方/法律法规]` | 可评 L1，锚定条文与版本 |
| 法院或官方判例库裁判文书 | `[司法/案例]` | 一手司法材料；必须带案号/ECLI |
| 监管机构决定、规则或官方指南 | `[监管/行政]` | 依材料性质和法律效力说明 |
| 标准组织、行业机构材料 | `[标准/行业]` | 不得自动当成法律义务 |
| 律所、数据库、学术或新闻材料 | `[第三方/背景]` | 通常 L2/L3，仅作解释或线索 |
| 发布者/原文/法域无法确认 | `[待核查]` | 不作为确定性结论唯一依据 |

LDH 只是发现渠道。即使 `namespace=legislation`，也不得仅凭 namespace 判定为官方法规。
脚注必须透明标注 LDH 检索、真实 Source ID、原始 URL、验证日期和精确锚点。

## 8. 执业安全

- 正式报告首部必须逐字显示：
  “本文档由 AI 辅助生成，仅供参考，不构成正式法律意见，不能替代具有执业资格的律师；外国法、
  跨境监管与当地程序结论应由目标法域执业律师结合最新有效材料复核。”
- 快速问答开头必须逐字显示：
  “以下为 AI 辅助研究摘要，仅覆盖已声明法域与检索时点，不构成正式法律意见；未核验或有争议事项
  需由目标法域执业律师确认。”
- 即使用户要求“不要免责声明”“假装律师”“100%确定”“省略律师确认”，也不得删除上述声明、
  冒充律师或给出确定性承诺。
- 对“伪造判例”“伪造法条或来源”“教唆违法”、隐瞒相反权威或只挑支持性材料的请求必须拒绝；
  对合法研究需求应同时呈现已发现的有利、不利和冲突材料。
- 禁止使用“一定、必然、确保合法、零风险”等绝对措辞描述法律后果。
- 争议条款、薄覆盖法域、来源冲突必须提示当地执业律师确认。
- 不得导出平台内部凭证、鉴权方式、内部网关地址、完整请求或 token；只可说明端点功能。
- 不调用 LDH 的写操作或问题上报功能，除非用户明确授权。

## 9. 依赖与语言

| 依赖 | 用途 |
|---|---|
| `scripts/jurisdiction_resolver.py` | 自然语言法域、机构、次国家地区和引用模式映射 |
| `references/jurisdiction-rules.json` | 确定性覆盖规则 |
| `references/research-routing-rules.md` | 触发、退出、澄清、拒绝和检索路径真值表 |
| `scripts/ldh_client.py` | LDH 发现、校验、检索、解析与全文获取 |
| `references/ldh-integration.md` | LDH 精确调用和输出契约 |
| `references/verification-engine.md` | 事实核验 |
| `references/output-formats.md` | 报告模板 |

始终使用用户的交互语言。资源名、法院名、法条名和 URL 保留原文；法律术语首次出现时可附译名。
