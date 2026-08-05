# 专家包审查报告 - stock-partner-team

## 一、总体结论

**整体结论：可上架**

| 项目 | 值 |
|------|-----|
| 包名 | stock-partner-team |
| 作者 | jensonli（jensonli@tencent.com） |
| 类型 | Team（专家团，7 成员） |
| 分类 | 08-FinanceInvestment（金融投资） |
| 来源类型 | internal（作者邮箱为腾讯内部域名 @tencent.com，README 自称腾讯证券产品部） |
| 阻断问题（BLOCKER） | 0 个 |
| 建议改进项（SUGGESTION） | 4 个 |
| 不在审查范围（仓库管理员职责） | 4 项 |

> 📋 来源推断说明：author 邮箱 `jensonli@tencent.com` 属于腾讯内部域名，README 自述为"腾讯证券产品部"开发，按 internal 来源全量审查（含命名风格等创意层规则）。如实际为外部第三方提交，请告知，将切换为 external 模式重审（跳过创意层规则）。

---

## 二、阻断问题（BLOCKER）— 必修

无。本专家包结构完整、规范符合度高，未发现阻断性问题。

---

## 三、建议改进项（SUGGESTION）

### S01 ⚠️ `bin/init_task.py` 上报到腾讯内网域名

- **现状**：`bin/init_task.py` 第 59 行向 `https://trace.inlong.qq.com/{INLONG_CLUSTER_TAG}/dataproxy/message` 上报匿名埋点（dev_id、事件类型、时间戳）。该域名为腾讯内网 InLong 数据通道。
- **影响**：若专家包 `visibility` 设为 `external_only` 或 `all`（司外可见），外部用户无法访问此内网域名，上报会静默失败。脚本已做 fail-safe（`except Exception: return`），不影响专家团分析功能，但渠道数据看板将收不到外部用户的使用统计。
- **规范依据**：CODEBUDDY.md §十六 外部提交审查原则；WorkBuddy §6.6 注意事项（专家包通用性）
- **修复方案**：
  - 方案 A（推荐）：若专家包仅司内可见（`visibility: internal_only`），当前实现可接受，无需修改
  - 方案 B：若需司外可见，将上报地址改为公网可达的网关，或在 `init_task.py` 中增加域名可达性检测，外网环境直接跳过上报
  - 方案 C：README 已说明"删除或清空 `bin/init_task.py` 即可关闭"，可保持现状但在 README 中补充说明外网环境上报不可用

### S02 ⚠️ `skills/westock-data/` 和 `skills/westock-tool/` 下存在 `package.json` 但未被使用

- **现状**：两个 skill 目录下各有一个 `package.json`，但对应 `SKILL.md` 明确声明"禁止运行本地 `scripts/`"，取数通道为 westock-mcp 连接器的 MCP Tool，不涉及 node 脚本调用。
- **影响**：`package.json` 为历史遗留文件，可能误导审查者或维护者以为存在 node 依赖。不影响运行时功能。
- **规范依据**：CODEBUDDY.md §5 Skill 规范（skill 目录应只包含必要文件）
- **修复方案**：确认无 node 脚本依赖后，删除两个 `package.json`（若 `references/` 下也无 node 脚本引用）

### S03 ⚠️ 主理人 prompt 篇幅较长（368 行）

- **现状**：`agents/stock-partner-lead.md` 含 frontmatter 共 368 行，涵盖团队协作铁律、连接器状态判断、会话初始化/收尾、圆桌编排方法、任务说明模板、结果汇编（4 模块结构）、输出格式、9 条铁律/红线等。
- **影响**：内容完整且结构清晰，但篇幅较长会占用较多上下文窗口。对于复杂圆桌编排（主理人需并行 spawn 6 位成员），长 prompt 可能影响模型对关键铁律的遵从度。
- **规范依据**：深度质量评审 - 上下文效率维度
- **修复方案**（可选）：
  - 将"圆桌报告 4 模块结构"的详细 DOM 规范（模块 1-4 的字段细节）抽到 `references/report-structure.md`，主理人 prompt 中保留引用 `@references/report-structure.md`
  - 将"HTML 渲染细节"也抽到 `skills/md-to-html/references/` 下，主理人只保留调用入口
  - 保留所有铁律/红线在主理人 prompt 内（不可外移）

### S04 ⚠️ 成员 prompt 中历史案例含具体股价数字

- **现状**：各成员 prompt 的"经典案例"章节包含具体股价数字（如"腾讯从 600+ 跌到 200"、"中际旭创 1000 多亿市值时买入，约 10 倍 PE"）。虽然成员 prompt 已明确"历史归历史，实时归实时：档案里的价格是访谈快照，讲当前必须用实时数据"，但这些数字仍可能被模型误用为"当前价"。
- **影响**：低风险。成员 prompt 有明确的"历史 vs 实时"约束和"数据不可捏造"铁律，模型误用概率低。
- **规范依据**：CODEBUDDY.md §十八 17.3 数据来源披露
- **修复方案**（可选）：在案例数字后统一标注"（访谈时快照，非实时）"，进一步降低误用风险

---

## 四、深度质量评审

| 维度 | 评级 | 判断 |
|------|------|------|
| AI 可执行性 | 优 | 铁律明确、任务说明模板完整、执行预算（MCP≤4次、报告800-1500字）清晰可执行 |
| 路由/触发清晰度 | 优 | 主理人有"研究维度拆解→维度映射成员→并行调度→整合"四步编排法，附3个编排样例（单股/主题/组合），成员区分说明清晰 |
| 上下文效率 | 良 | 主理人 prompt 较长（368行），但结构层次分明；成员 prompt 有"执行预算"铁律防止轮次耗尽 |
| 容错降级 | 优 | 连接器未连接时有完整降级方案（WebSearch+其他skill）；成员轮次中断有恢复指令（最多1次）；缺席席位标注机制；HTML渲染失败保留md |
| 角色边界 | 优 | 每位成员有"易混淆成员区分"章节，6位成员两两对比差异明确（如产业策略师vs财报研究员、信号派vs短线冲浪手） |
| 团队编排 | 优 | 主理人"维度映射"而非固定组合，支持并行spawn；等待纪律完善（少播报、禁边等边取数、收齐即汇编）；HTML必交付 |
| 用户体验 | 优 | 三层交付（Chat简版/圆桌MD/圆桌HTML），HTML可分享微信邮件；默认对话输出不写本地文件，适配无工作空间环境 |
| 受众适配 | 优 | 面向个人投资者，用语通俗（"打五折你不买吗"），专业术语有解释，免责声明到位 |
| 可移植性 | 良 | 依赖 westock-mcp 连接器（腾讯自选股），未连接时降级方案完善；init_task 上报内网域名（见S01）；Python+Pillow依赖有README说明 |
| 领域准确性 | 优 | 6位成员覆盖产业策略/信号/估值/逆向/基本面/短线全视角，投资方法论真实（PE Bands/PEG/支撑位/四层信号体系等），常见误读纠正章节专业 |
| 可维护性 | 良 | 模块化清晰（agents/skills/bin分离），但主理人prompt较长（见S03）；README有完整目录结构说明和环境要求 |

---

## 五、形状层确定性检查结果

### 5.1 一致性约束（CODEBUDDY.md §十三）

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | agentName = Agent MD name = 文件名 | ✅ | `stock-partner-lead`，有业务语义 |
| 2 | teamInfo.memberAgents[] = members[].id = 文件名 | ✅ | 6个成员ID全部一致 |
| 3 | avatar 路径指向实际文件 | ✅ | team.png + 7个成员头像全部存在 |
| 4 | settings.json agent = agentName | ✅ | `{"agent": "stock-partner-lead"}` |
| 5 | skills[] 路径下有 SKILL.md | ✅ | westock-data / westock-tool / md-to-html |
| 6 | Agent frontmatter 无 tools 字段 | ✅ | 7个agent均无 |
| 7 | expert_center.json 同步 | ⏭️ | 仓库管理员职责，不在审查范围 |

### 5.2 目录结构（CODEBUDDY.md §二 Team型）

| 检查项 | 结果 |
|--------|------|
| `.codebuddy-plugin/plugin.json` 存在 | ✅ |
| `avatars/` 在根目录（team.png + 主理人 + 6成员） | ✅ |
| `agents/` 在根目录（7个md，带frontmatter） | ✅ |
| `skills/` 在根目录（3个skill） | ✅ |
| `bin/` 在根目录（init_task / init_task.cmd / init_task.py） | ✅ |
| `settings.json` 存在 | ✅ |
| `README.md` 存在 | ✅ |
| `.codebuddy-plugin/` 下只有 plugin.json | ✅ |
| 无 hooks/commands/.lsp.json | ✅ |

### 5.3 plugin.json 字段（CODEBUDDY.md §三）

| 字段 | 结果 | 说明 |
|------|------|------|
| name | ✅ | `stock-partner-team`（小写+连字符） |
| version | ✅ | `1.0.0`（语义化版本） |
| description | ✅ | 英文一句话 |
| author | ✅ | `{name, email}` 完整 |
| expertType | ✅ | `team` |
| agentName | ✅ | `stock-partner-lead`（非通用名） |
| teamInfo | ✅ | leadAgent + memberAgents[6] 完整 |
| agents[] | ✅ | 7个路径全部存在 |
| skills[] | ✅ | 3个目录全部有SKILL.md |
| displayName | ✅ | {en, zh} 齐全 |
| profession | ✅ | {en, zh} 齐全，与displayName一致 |
| displayDescription | ✅ | 中文42字（40-50范围） |
| avatar | ✅ | `avatars/team.png` 存在 |
| categoryId | ✅ | `08-FinanceInvestment`（合法分类） |
| defaultInitPrompt | ✅ | 与quickPrompts[0]一致 |
| tags | ✅ | 3个标签 |
| quickPrompts | ✅ | 3个提示词 |
| members[] | ✅ | 7个成员（含主理人role=lead） |
| dependencies.connectors | ✅ | `["westock-mcp"]` |
| plugin | ✅ | 与name一致 |

### 5.4 Agent MD Frontmatter

| Agent | name | description | displayName | profession | maxTurns | tools |
|-------|------|-------------|-------------|------------|----------|-------|
| stock-partner-lead | ✅ | ✅ | ✅ | ✅ | 200 | 无 ✅ |
| industry-strategist | ✅ | ✅ | ✅ | ✅ | 80 | 无 ✅ |
| signal-chief | ✅ | ✅ | ✅ | ✅ | 80 | 无 ✅ |
| valuation-analyst | ✅ | ✅ | ✅ | ✅ | 80 | 无 ✅ |
| contrarian-investor | ✅ | ✅ | ✅ | ✅ | 80 | 无 ✅ |
| fundamental-researcher | ✅ | ✅ | ✅ | ✅ | 80 | 无 ✅ |
| shortterm-surfer | ✅ | ✅ | ✅ | ✅ | 80 | 无 ✅ |

### 5.5 头像检查

| 头像 | 尺寸 | 大小 | 格式 |
|------|------|------|------|
| team.png | 512×512 | 23KB | PNG ✅ |
| stock-partner-lead.png | 512×512 | 155.1KB | PNG ✅ |
| industry-strategist.png | 512×512 | 145.7KB | PNG ✅ |
| signal-chief.png | 512×512 | 164.7KB | PNG ✅ |
| valuation-analyst.png | 512×512 | 151.3KB | PNG ✅ |
| contrarian-investor.png | 512×512 | 151.8KB | PNG ✅ |
| fundamental-researcher.png | 512×512 | 134.7KB | PNG ✅ |
| shortterm-surfer.png | 512×512 | 148.9KB | PNG ✅ |

全部符合 512×512px、<500KB、PNG 格式要求。

---

## 六、规范层检查结果（ai_actions）

### 6.1 team-rule-check（主理人铁律）— WorkBuddy §5.2.1 / CODEBUDDY §4.4

**结论：✅ 通过**

主理人 `agents/stock-partner-lead.md` 包含完整的「团队协作机制（铁律）」章节：

- ✅ **TeamCreate 铁律**：「团队创建（TeamCreate）必须且只能由主理人执行，严禁委派任何成员创建团队」（第24行）
- ✅ **4条正则**：建立团队 / 调度成员 / 消息中转（SendMessage）/ 成员结论为准
- ✅ **5条红线**：禁止跳过TeamCreate / 禁止代写成员产出 / 禁止跳阶段 / 禁止成员直连 / 禁止spawn主理人自己
- ✅ **协作规则**：TeamCreate → Agent spawn → SendMessage 回传正式流程
- ✅ **子任务命名**：`name` 和 `subagent_type` 必须用 Agent ID（第45-51行完整列出6个成员）
- ✅ **成员能力清单**：团队成员表格含 Agent名称/花名/头衔/独特增量区
- ✅ **预设Workflow**：3个编排样例（单股深度/非个股主题/多标的组合）
- ✅ **单agent直调**：点名某位成员的说明（第53-61行）
- ✅ **等待与恢复纪律**：防掉线/防轮次耗尽机制（Step 3.5）

### 6.2 member-rule-check（成员prompt）— CODEBUDDY §4.5.3

**结论：✅ 通过**

6个成员agent均包含：

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 角色定义 | ✅ | 每位开头"你是XX，一位..." |
| 擅长领域 | ✅ | 3-5个具体能力点 |
| 分析框架 | ✅ | 分步骤研究流程（如产业策略师的"选方向→拆产业链→选个股→持续跟踪"四步） |
| 数据获取方式 | ✅ | data_* 工具调用示例（data_quote/data_kline/data_finance等） |
| 输出模板 | ✅ | 报告目标800-1500字，结构自定但须覆盖框架关键环节 |
| SendMessage回传 | ✅ | 每位结尾"必须通过 SendMessage 将完整报告内容回传给主理人" |

### 6.3 naming-style（命名风格）— CODEBUDDY §9.1（internal适用）

**结论：✅ 通过**

| 成员 | displayName(zh) | profession(zh) | 谐音巧思 | 评估 |
|------|---------------|----------------|----------|------|
| 主理人 | 圆汇众 | 投研主编 | 圆桌汇众人之见 | ✅ 花名+profession不重复 |
| 成员1 | 星望远 | 产业策略师 | 星望远=远望产业趋势 | ✅ |
| 成员2 | 洲四方 | 信号派首席 | 洲四方=四层信号体系 | ✅ |
| 成员3 | 文衡价 | 估值分析师 | 文衡价=文能衡价 | ✅ |
| 成员4 | 坤候底 | 逆向投资人 | 坤=地=底，候底=等底 | ✅ |
| 成员5 | 钊审财 | 财报研究员 | 钊审财=审财报 | ✅ |
| 成员6 | 磊追浪 | 短线冲浪手 | 磊追浪=追涨如追浪 | ✅ |

- ✅ 花名均为三字中文姓名结构，不与profession重复
- ✅ 主理人profession"投研主编"体现业务定位，非通用title
- ✅ 英文displayName用拼音姓氏（Yuan/Xing/Zhou/Wen/Kun/Zhao/Lei）
- ✅ 无叠字谐音、无短语式命名

### 6.4 finance-compliance（金融合规）— CODEBUDDY §十八

**结论：✅ 通过**

#### 外露文案（§17.1）

| 字段 | 内容 | 结果 |
|------|------|------|
| defaultInitPrompt | "算力 VS 人形机器人，2026 下半年哪条主线更值得关注？" | ✅ 无"能不能买/该买吗/推荐"等决策类措辞 |
| displayDescription | "六位投研专家团，兼擅产业策略、信号捕捉、估值定价、逆向布局、基本面与短线，基于实时行情多视角研判。" | ✅ 不暗示投资建议 |
| description | "6 stock market experts + 1 lead editor collaborate as an agent team for stock market information analysis and discussion" | ✅ 无投资建议措辞 |

#### 免责声明（§17.2）

统一模板：`> ⚠️ 以上内容由 AI 基于公开信息整理生成，仅供参考，不构成任何投资建议或个股推荐。投资有风险，决策需谨慎。`

四要素检查：

| 要素 | 包含 |
|------|------|
| AI 生成 | ✅ |
| 基于公开信息 | ✅ |
| 不构成投资建议 | ✅ |
| 不构成个股推荐 | ✅ |

出现位置：

| 文件 | 位置 | 结果 |
|------|------|------|
| stock-partner-lead.md | 铁律#7（第365行） | ✅ |
| industry-strategist.md | 报告底部（第464行） | ✅ |
| signal-chief.md | 报告底部（第282行） | ✅ |
| valuation-analyst.md | 报告底部（第392行） | ✅ |
| contrarian-investor.md | 报告底部（第373行） | ✅ |
| fundamental-researcher.md | 报告底部（第340行） | ✅ |
| shortterm-surfer.md | 报告底部（第378行） | ✅ |
| README.md | 文末（第154行） | ✅ |

#### 数据来源披露（§17.3）

- ✅ 主理人铁律#6："数据来源可追溯：引用行情、财务、资金、宏观、新闻数据时必须标注具体来源（如 `data_quote 腾讯`、`WebSearch："港股 汽车 政策"`），禁止'综合来看''据了解''根据公开信息'等无来源表述"

#### 指令性结论禁止（主理人铁律#5）

- ✅ "禁止'建议买入/卖出/加仓/减仓/止损/X成仓/清仓/抄底/追高'等指令性结论——用'偏多/偏空/观望/分歧'或按持仓状态/风险偏好分组的差异化参考代替"

#### 成员合规约束

- ✅ 每位成员prompt含："你不是真人账户，不能说'我昨天买了'——可以说'按我的框架，这个位置我会 XX'"
- ✅ 每位成员prompt含："历史归历史，实时归实时：档案里的价格是访谈快照，讲当前必须用实时数据"

### 6.5 platform-claim-check（平台技术承诺）

**结论：✅ 通过**

未发现"本地AI""全程不联网""离线运行"等与平台运行方式不符的技术承诺。专家团明确依赖 westock-mcp 连接器获取云端数据，未连接时降级 WebSearch。

### 6.6 security-hygiene-review（安全检查）

**结论：✅ 通过（含 S01 建议）**

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 凭据硬编码 | ✅ 无 | init_task.py 无硬编码Token/密钥 |
| 危险命令 | ✅ 无 | 无 rm -rf / 系统破坏类命令 |
| 内网域名 | ⚠️ | init_task.py 上报到 `trace.inlong.qq.com`（见S01） |
| 个人路径 | ✅ 无 | 无硬编码个人开发路径 |
| CDN @latest | ✅ 无 | 无外部CDN依赖 |
| 文件操作 | ✅ 安全 | init_task.py 用原子写入（tmp+rename），避免竞态 |

### 6.7 dependency-guide-check（依赖引导）

**结论：✅ 通过**

README 包含完整的环境依赖说明：

| 依赖项 | 引导内容 | 结果 |
|--------|---------|------|
| Python 3.8+ | README "环境要求"章节 | ✅ |
| Pillow | `pip install pillow` | ✅ |
| 验证安装 | `python3 -c "import PIL; print(PIL.__version__)"` | ✅ |
| westock-mcp 连接器 | README "数据来源"章节 + 主理人prompt连接状态判断 | ✅ |
| 连接器未连接降级 | README 表格 + 主理人prompt降级取数优先级 | ✅ |

---

## 七、不在审查范围（仓库管理员入库时处理）

以下为入库时仓库管理员负责处理的事项，不作为外部提交者的阻断项：

1. **expert_center.json 条目追加**：新增专家需在 `expert_center.json` 的 `experts[]` 末尾追加条目（含 id/categoryId/displayName/promptFile/avatar/createdAt/updatedAt 等）
2. **marketplace.json 条目追加**：`.codebuddy-plugin/marketplace.json` 条目同步
3. **项目根目录 avatars/ 复制**：plugin 内部 `avatars/*.png` 需复制到项目根目录 `avatars/`，按 `{ExpertId}.png` / `{MemberId}.png` 命名
4. **updatedAt 刷新**：expert_center.json 对应条目 `updatedAt` 刷新为当前 UTC 时间戳

---

## 八、修复优先级表

| 优先级 | 编号 | 问题 | 工作量 | 建议 |
|--------|------|------|--------|------|
| P2 | S01 | init_task.py 上报内网域名 | 小 | 确认 visibility 后决定是否调整 |
| P3 | S02 | westock-data/tool 下遗留 package.json | 极小 | 删除即可 |
| P3 | S03 | 主理人 prompt 篇幅较长 | 中 | 可选优化，抽离参考资料 |
| P3 | S04 | 成员案例含历史股价数字 | 小 | 可选，标注"访谈快照" |

---

## 九、亮点

1. **投资方法论真实专业**：6位成员的投资框架来自真实投资实践（PE Bands分位数法、四层信号体系、支撑位分批建仓十次法则、生活体感选股等），非泛化模板。每位成员的"常见误读纠正"章节体现了对AI易犯错误的预判防御。

2. **成员区分设计精妙**：6位成员两两之间都有"关键区分"章节（如产业策略师vs财报研究员的top-down vs bottom-up、信号派vs短线冲浪手的周/月级vs天级、估值分析师vs逆向投资人的精确定价vs模糊判断），有效防止成员同质化。

3. **连接器降级方案完善**：主理人prompt对westock-mcp连接器"已连接/未连接"两种状态有完整的取数策略和用户提示流程，未连接时降级WebSearch并明确告知用户"效果可能受影响"，体验诚实。

4. **执行预算铁律防轮次耗尽**：每位成员有"MCP取数≤4次、WebSearch≤1次、报告800-1500字、取数结束立即SendMessage"的硬约束，有效防止Agent在数据查询阶段耗尽轮次。

5. **圆桌报告产品化**：4模块结构（结论卡/子专家观点/深度思考/后续关注）+ HTML渲染（Anthropic浅色风、头像base64内嵌、可微信分享），将AI输出做成可交付的"答案产品"而非会议纪要。

6. **等待与恢复纪律**：主理人"防掉线/防轮次耗尽"机制（Step 3.5）设计细致——少播报、禁边等边取数、轮次中断恢复指令（最多1次）、收齐即汇编、缺席标注，保证圆桌不因单成员掉线而卡死。
