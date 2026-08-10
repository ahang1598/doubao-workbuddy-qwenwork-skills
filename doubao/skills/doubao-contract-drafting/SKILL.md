---
name: doubao-contract-drafting
description: 直接起草中国大陆商业合同并生成无批注、无颜色、中文字体正确的可编辑 Word 文件。适用于采购、服务、营销、工程施工、软件许可、SaaS、委托开发、联合研发、知识产权、租赁、数据处理和保密等场景；读取题干及附件后完成交易信息拆解、风险识别、起草方标准条款与默认商业参数填充、合同生成与交付校验。涉及跨境交易、境外法域或境外争议解决安排时，需升级并要求复核。
---

# doubao-Contract Drafting

## 核心原则

直接起草，不在首轮追问。以用户题干、邮件和附件为最高事实来源；使用起草方标准政策补足法律风险分配，并按场景填入可控的默认商业参数。默认法域仅适用于中国大陆商业合同；如题干、附件或交易结构显示涉及跨境交易、境外主体、境外履行、境外法域或仲裁/法院安排冲突，需升级并要求复核。不得编造主体、标的、金额、绝对日期等交易客观事实。Word 正文只用黑色文字，不使用批注、颜色或高亮；未知事实不作文字标注，仅保留可填写空白。

## 工作流

1. 读取题干及全部附件；DOCX、表格或邮件较复杂时，先运行 `${CLAUDE_SKILL_DIR}/scripts/extract_deal.py`，再读 `references/deal-schema.md` 完成交易信息拆解。
2. 识别起草方、合同形态、主骨架族、场景模块和风险标签。先只读 `references/scenario-risk-index.md`；命中一个或多个飞书原始场景标题后，只读取 `references/scenario-risk-map.md` 中对应标题及其完整项下内容，禁止全文读取该文件。随后只读取 `references/scenario-risk-checklist.md` 中同一标题或命中的专项模块，作风险防漏检查；压缩清单不得替代完整风险源。同时读取 `references/skeleton_families.md` 和 `references/module_catalog.md`。
3. 为每项信息标注：`confirmed`、`derived`、`standard_term`、`standard_parameter`、`pending` 或 `disputed`。不得将 `pending` 写为已完成或已确认；对 `disputed`，采用起草方方案并在交付说明中提示谈判敏感性。
4. 读取 `references/standard_policy.md` 和 `references/default-commercial-parameters.md`。前者补足适用法律、书面验收、付款前提、救济等标准条款；后者按骨架族和起草方角色补足付款天数、验收期、相对交付期、付款节点、违约金、普通责任上限、期限及质保/维护期。默认参数直接写入合同，不作“行业建议值”标记。
5. 在 JSON 的 `parameter_profile` 填入所选骨架族、起草方角色和每项应适用的默认参数；每项参数以 `confirmed` 或 `standard_parameter` 记录并给出 `coverage_terms`。不得以空白替代应预填参数。
6. 不得用默认参数虚构主体信息、型号、数量、金额、税率、账户、专利号、竞争对手名单或绝对日历日期。仅在中国大陆商业合同且未约定其他争议解决安排时，具体法院名称未知可写“起草方住所地有管辖权的人民法院”；涉及跨境交易、境外法域或境外争议解决安排时，不得直接套用该表述，需升级并要求复核。
7. 以主骨架组织合同；模块只能补充统一条款槽位，不得生成第二套付款、验收、知识产权、解除或签署条款。
8. 单项合同的未提供交易事实保留可填写空白；框架合同的具体型号、数量、价格、交期等写明“以订单、报价单或附件为准”。
9. 将草案整理为 `${CLAUDE_SKILL_DIR}/scripts/generate_docx.py` 的 JSON 格式，生成 Word；用户明确要求不使用表格时传入 `"allow_tables": false`。
10. 依次运行 `${CLAUDE_SKILL_DIR}/scripts/preflight.py`、`${CLAUDE_SKILL_DIR}/scripts/consistency_check.py`、`${CLAUDE_SKILL_DIR}/scripts/policy_gate.py` 和 `${CLAUDE_SKILL_DIR}/scripts/font_check.py`。检查失败则修正，不得交付。
11. 交付 Word 后，在对话中分开列出：①已确认事实（注明来源）；②本次预填的标准条款与默认商业参数（说明适用规则）；③仍为空白的事项及填写建议；④谈判敏感项。不得把该说明写入合同，除非用户明确要求起草说明。

## 命令契约

- 提取附件：`python3 "${CLAUDE_SKILL_DIR}/scripts/extract_deal.py" <input...>`，标准输出为结构化 JSON。
- 生成 Word：`python3 "${CLAUDE_SKILL_DIR}/scripts/generate_docx.py" <contract.json> <output.docx>`。
- 交付门禁：依次执行三个 JSON 检查器和 `font_check.py <output.docx>`；任一命令非零退出时，根据输出修正后重新运行全部门禁。

## 优先级

用户明确事实与附件 > 用户明确格式/立场 > 受控附件 > 起草方标准政策 > 场景模块与风险地图 > 主骨架。

## 参考资料路由

- 主交易结构：`references/skeleton_families.md`；未收录或混合场景另读 `references/skeleton_00_generic.md`
- 模块与条款槽位：`references/module_catalog.md`
- 风险地图标题命中：`references/scenario-risk-index.md`
- 场景的完整风险内容：`references/scenario-risk-map.md`
- 场景压缩校验及派生专项：`references/scenario-risk-checklist.md`
- 事实状态、单项/框架规则：`references/deal-schema.md`
- 起草方默认条款：`references/standard_policy.md`
- 默认商业参数：`references/default-commercial-parameters.md`
- 默认参数覆盖项：`references/default-parameter-profiles.md`
- 输出格式：`references/drafting-conventions.md`
- 草案 JSON 字段与附件写入：`references/draft-json-schema.md`
- 校验清单：`references/validation_rules.md`

## 禁止事项

- 不得追问后才起草，不得输出“仅能澄清问题”。
- 不得默示验收、默示同意、自动续期或自动生效。
- 不得把待审批、待核查、待确认或存在分歧的事项写成既成事实。
- 不得使用方括号式或其他文字型占位符；未知信息仅留可填写空白。不得使用彩色文字、高亮或 Word 批注。
- 不得将用户上传的附件替换为空白模板；附件编号、名称、正文和引用必须一致。
- 不得交付中文文字未显式设置东亚字体的 Word 文件；标题、正文、附件、签署页和表格均须通过 `font_check.py`。

## 运行前提

使用工作区提供的 Python 运行时执行脚本。`generate_docx.py` 依赖 `python-docx`；运行前确认该库可用。不得为安装依赖而修改用户环境，缺少依赖时报告具体缺失项。
