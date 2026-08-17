# CHANGELOG

## v2.1.0 - 2026-08-11 — 四批真机测试整改（L2-L6）

1. **L4 连接器返回处理（P0）**：connector-search.md 新增"连接器返回处理"小节——归一化必须程序化（返回 dict 直接 json.dump(ensure_ascii=False) 写分页文件），禁止手动转写 content/sourceContent；中文引号不做替换、禁止截断绕过解析错误（针对首轮 content 截断-6 与编码 5 次失败-5）
2. **L5 元典映射示例**：data-structure.md 新增"常见连接器映射示例（元典 yuandian）"字段对照表，强调以运行时 schema 为准
3. **L2 交付前硬读指令**：mode-a-case-search.md 第七步加"交付前必须实际 Read output-format.md，未读取禁止交付"
4. **L3 扫描件处理优先级**：模式A 前置判断加文字提取 <50 字符即渲染 2x 图片视觉读取；足以形成 Query 可不强制全读但须标注覆盖率
5. **L6 格式使用场景**：output-format.md 顶部明确对话可用表格、Markdown 文件用列表；法规清单统一"《法条名》第X条：本次样本中用于处理…"格式

## v2.0.0 - 2026-08-10 — 单元 6「律师类案检索与报告」三合一合并

- `name_zh` 由「律师类案检索」改为「**律师类案检索与报告**」；`name` 与目录名保持 `lawd-case-retrieval` 不变（QwenWork 要求 name = 目录名，且库内证据/争点等多个技能互引指向它）。
- 按六段结构重写 SKILL.md（能力总述 / 触发与分流 / 模式工作流 / 数据源 / 门禁脚本 / 交付物），合并为一个入口、三种模式：
  - 模式A 类案检索（承本技能原七步工作流，**已改好的连接器检索段原文保留、逐字未动**）；
  - 模式B 按案号取裁判文书全文（承 `lawd-case-detail-query`）；
  - 模式C 正式类案检索报告（承 `lawd-case-retrieval-report`，产出经脚本校验的 `.docx`）。
- description 单行重写，覆盖三原技能触发词与 NOT for 边界；正文给「意图 → 模式」路由表，并明确**无案号却说要判决书全文一律走模式A**、模式A 完成后可内部接 C（报告）或 B（取某案全文）且不重复检索。
- 原主文件「下游报告交接」「查看案例详情」两处跨技能衔接，落地为「模式A → 模式C」「模式A → 模式B」内部路由。
- **模式B 浏览器改造**：悟空 `browser_use` 方案作废，改用「浏览器页面操作」能力（千问办公内置浏览器连接器，key `qwenwork.settings.connector.builtin.browser`，仅用于引导话术，能力匹配按语义不写死）；按三铁律写探测（关键词覆盖 `browser / 浏览器 / navigate / screenshot / 页面` 等）、schema 验证（须具备导航 + 页面内容读取）、**A 档拒绝降级**（不可用即停止并提示启用，严禁 WebSearch 摘要或模型记忆冒充全文）；保留 5 分钟登录轮询窗口；标注模式B 为**实验性能力**，失败须显性告知并建议改用模式A 取裁判要旨。
- references 归并至 10 项：`lawd-case-detail-query` 的 3 个加 `detail-query-` 前缀迁入，`lawd-case-retrieval-report` 的 report-format / report-validation-rules 原名迁入、case-input-contract 加 `report-` 前缀迁入；经 md5 比对 10 份两两无重复副本，均如实迁移；迁入文件内部交叉引用与步骤编号（B1/B4/B5 等）、悟空 browser_use 措辞同步修正。
- scripts 归并至 8 个（无文件名冲突）：迁入 `convert_to_md.py`、`normalize_case_no_for_search.py`（模式B）与 `generate_report_docx.py`、`validate_report_cases.py`、`validate_report_docx.py`（模式C）；`normalize_case_no_for_search.py` docstring 引用路径同步改名；修复 `save_stdout.py` 的 `--help` 会创建名为「--help」垃圾文件的缺陷。
- 新增模式A 门禁 `scripts/validate_case_fields.py`：针对 `process_case_results.py` 的两处 P0（① caseNo 非字符串会整页崩溃且无法定位；② 出处字段仅统计案号缺失）补校验——对案号 / 法院（`trialCourt.name`）/ 出处（`dataFrom`）三项做类型容错 + 缺失率统计，类型异常逐条定位、任一大面积缺失（默认 >30%）拦截且非零退出。
- 各模式交付环节加入「交付前必须运行对应门禁脚本，未通过禁止交付」指令。
- 被吸收的 `lawd-case-detail-query`、`lawd-case-retrieval-report` 两个目录**原样保留**，待验收后由产品决定去留。
- 本地自测：8 个脚本 `--help` 均可运行；`validate_case_fields.py` 1 合规样例通过 + 案号类型异常/法院缺失/出处缺失 2 违规样例均拦截；模式A→C 端到端（process → validate_case_fields → validate_report_cases → generate_report_docx → validate_report_docx）跑通并产出通过校验的 .docx；`grep "dws law"` 残留为 0。真实检索与浏览器抓取待用户在 QwenWork 上做 2 案例验收。

## v1.2.0 - 2026-08-10

- 摆脱旧 dws 检索命令依赖：SKILL.md 检索调用段改写为「案例/裁判文书检索」连接器能力语义 + 三段式探测 + A 档拒绝降级，执行门禁保留（未实际检索不得罗列判例，禁止虚构案号）。
- `references/dws-commands.md` 改名重写为 `references/connector-search.md`：新增 Query 改写 → 连接器入参语义映射（案情描述、案由、法院、地域、日期范围、文书类型、返回条数）与结果归一化说明。
- `references/data-structure.md` 重写：分页 JSON 定位为归一化输入契约，新增连接器返回字段语义 → caseDomain 映射表，明确以运行时 schema 为准。
- 写明已知缺口：连接器均无裁判文书逐字全文抓取能力；全文获取改用内置浏览器连接器，不稳时降级为仅提供检索摘要+出处。
- 脚本仅改数据来源说明（provider 改为 `case-retrieval-connector`），输入输出契约不变。

## v1.1.0 - 2026-08-04

- 重构 `SKILL.md`，统一 Query 改写、数量、分页、去重、案号缺失和样本内洞察规则。
- 新增 `scripts/process_case_results.py`，支持分页 JSON 校验、稳定去重、交付集裁剪、重字段裁剪和数量缺口统计。
- 新增 `references/output-format.md`，并重构数据结构、DWS 命令和 Query 改写参考文件。
- 扩充评测用例至 12 个，覆盖数量不足、重复案例、缺失案号和不应自动过滤等边界。
- 已完成本地脚本和构造数据验证；真实 DWS 服务联调尚未执行。

## v1.0.0 - 2026-08-03

- 合规整改：纳入 QwenWork-Legal-Skill 统一治理，补建 CHANGELOG 版本记录
- 此前历史变更详见 git 提交记录
