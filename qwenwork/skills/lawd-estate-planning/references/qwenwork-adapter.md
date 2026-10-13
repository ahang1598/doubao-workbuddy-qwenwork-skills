# 千问办公平台适配

## 能力映射（原生机制优先）

| 任务 | 千问办公能力 | 失败处理 |
|---|---|---|
| 欢迎语 | `SKILL.md` 内置三情形文案（初次/再次/中立），随首条回复原文开场；情形判定仅在平台记忆可用时读写单个布尔标记 | 文案缺失 → 停止并要求修复 Skill，不得自拟欢迎语 |
| 附件解析 | Read 工具；PDF/Word 走 `pdf`、`docx` skill 的读取路径 | 指明无法读取的文件，该主题降级为卡片填写 |
| 覆盖评估 | 一次模型抽取 + Schema 对照 | 不确定项标 `partial/missing` |
| 信息采集 | `AskUserQuestion`（每次 1–4 题、单选/多选、自动"其他"自填、备注 notes） | 无降级通道：不得改用聊天逐题采集 |
| 法源与案例 | pkulaw MCP：`mcp__pkulaw__mcp-law-search-service.search_article` / `get_article`、`mcp__pkulaw__mcp-case-search-service.search_case`；官网效力核对与普法链接用 `WebSearch` + `WebFetch` | MCP 不可用 → 官网检索；全部不可用 → `legal_research.status = "blocked"`，不伪造 |
| 卡片编译与解析 | Bash 运行 `compile_intake.py`、`normalize_card_response.py`、`parse_fast_lists.py`、`apply_intake_response.py`、`reconcile_coverage.py` | 脚本失败 → 保持原数据不变，修复输入后重跑 |
| 规则执行/校验/生成 | Bash 运行 `evaluate_rules.py`、`validate_case.py`、`validate_signature_readiness.py`、`build_packet.py`（python3） | 脚本失败 → 修复数据重跑，不跳过门禁 |
| Word 生成 | `scripts/build_will_docx.py` 补丁式修改权威范本（不用通用 DOCX 重建） | 范本校验失败 → 停止生成 |
| 成果交付 | 输出目录 + `qwenwork_file_present_files`；普法内容使用 `conversation_education_links` 直接写入对话 | 文件未生成不得呈现，不得另建普法或 AI 待判断文件 |

## 采集通道边界

- 欢迎语随首条回复开场，不单独占轮、不跑脚本；三情形文案逐字取自 `SKILL.md`，不得改写；同一回复紧接发出信息整理方式选择卡。
- `AskUserQuestion` 是唯一能把用户结构化输入带回执行上下文的通道；`qoder_show_widget` 仅用于展示（如关系图预览），不得冒充表单提交。
- 隐私分层：律师通道必须先完成与《千问办公隐私政策》一致的 `lawyer-privacy-consent` 确认卡；其他模式在采集方式选择话术中告知用途，首次作答视为同意并自动记入 `consent`。欢迎语不包含隐私条款。
- 律师通道采集表单以 HTML 文件呈现（马卡龙配色、保存按钮、提示词信息预填）；保存产物为下载目录中的 `lawyer-intake-filled-*.html`，经 `intake-data` 嵌入 JSON 自动回收；回收内容仍须经汇总核对确认。
- 禁止让用户下载 JSON、复制 JSON 回传、或以"我已填完"之类的聊天消息代替卡片提交。
- 唯一披露例外：`lawyer_sheet` 律师通道以消息/附件文本一次填回（仅律师），解析结果须经汇总核对确认后才写入工作数据。
- 每次卡片调用最多 4 题、每题最多 4 个选项；超出时按 `references/card-collection.md` §5 合组或分页。
- 「其他」项由平台固定追加在选项末尾，位置与提示文字不可自定义：凡需要文字填写的选项一律标注「请在「其他」中填写，本项勿选」，填写指引与示例写入题干。

## 运行顺序

1. 首条回复以 `SKILL.md` 内置欢迎语原文开场，并同轮发出采集方式选择卡；
2. 接收指令与附件 → 阶段 0 覆盖评估；
3. 阶段 1–2：编译必答卡组，分组发卡，回答写入 `work-data.json`，汇总确认；
4. 阶段 3：pkulaw 检索 + 官网核验 → `legal_research.status = "verified"`；
5. 阶段 4：`evaluate_rules.py` → 有 `BLOCKED` 时转缺口报告；无 `BLOCKED` 也不产生签署结论；
6. 阶段 5：`build_packet.py` / `build_will_docx.py` 仅生成待律师人工复核的 AI 草案及其他成果并呈现。

## Agent 记忆适配

- 平台可直接导出 JSON 时，向选择器提供形如 `{"skill_usage":{"lawd-estate-planning":{"has_invoked":true}}}` 的快照。
- 平台提供记忆 API 时直接以查询结果判定：无本 Skill 记录表示首次调用；写回仅限单个布尔标记。
- 无法可靠读取记忆时使用中立文案；不得把“本次上传了旧材料”当作再次调用，也不得把“当前没有材料”当作首次调用。
- Agent 记忆和本次 `work-data.json` 必须分离；案件数据不得写入记忆。

## 成果交付

只交付本次用户需要的法律成果和核验报告；不生成案件概览、快照、交接单、归档或任务管理文件。附件原件只读；生成件写入独立输出目录。每个生成文件显示“该文件由AI生成，不能取代律师专业意见，请审慎核实”；呈现文件前，交付对话醒目显示“本内容由人工智能生成，可能存在偏差、遗漏或错误，建议由律师进行人工复核”。待判断事项并入执行指引；普法文章或视频随后在对话中逐项显示名称、主要内容和链接。

## 旧客户端运行时（已移除）

v2 的浏览器端 `card-runtime.js` / `card-renderer.js` 提交桥不适用于千问办公对话（无事件回传通道），已在 v3 移除；如未来接入微应用形态，应重新设计桥接而不是复用旧代码。
