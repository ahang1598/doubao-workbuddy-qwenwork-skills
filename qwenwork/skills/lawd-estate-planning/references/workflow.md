# 单次起草工作流与门禁

本 Skill 只管理一次执行中的阶段，不提供案件管理、继续案件、归档或生命周期状态。跨次调用不保存任何案件数据；欢迎语按初次/再次/中立三情形区分，仅依赖平台记忆中的单个布尔标记（可用时）。

```text
assessing_inputs -> card_collection -> confirming_summary
-> researching -> evaluating_rules -> ready_for_output -> output_generated
```

## 调用入口门禁（最轻方案）

1. Skill 被调用后的第一条回复，以 `SKILL.md` 内置欢迎语原文开场（不得改写、缩短或润色），并在同一回复中紧接发出采集方式选择卡；欢迎语不单独占用一轮对话。
2. 欢迎语情形判定：平台记忆可用且可靠可读时，仅读取并写回单个布尔标记 `skill_usage.lawd-estate-planning.has_invoked`（标记真→再次调用文案，无标记→初次调用文案）；记忆不可用、不可读或含义不明→中立文案；不运行选择脚本，不得以当前对话或材料猜测调用历史。
3. 数据用途与敏感信息处理已在欢迎语中告知；用户对任一采集卡片作答即视为同意，由运行时把 `consent`（accepted、accepted_at、purposes、sensitive_data_acknowledged）自动记入 `work-data.json`。不再设置独立的隐私确认卡。
4. 用户身份、家庭关系、财产债务、遗嘱意愿、附件、`work-data.json` 或输出文件一律不得写入长期 Agent 记忆。

阶段名与工作数据 `status` 枚举的对应关系（写入 `work-data.json` 时只能使用右侧枚举值）：

| 流程阶段 | 允许的 status 值 |
|---|---|
| 材料评估 | `audience_selecting` |
| 卡片采集 | `intake_cards`、`information_incomplete` |
| 汇总确认 | `user_confirming` |
| 法源核验 | `researching`、`research_blocked`、`research_verified` |
| 规则执行 | `review_required`（存在 REVIEW_REQUIRED 时） |
| 成果生成 | `ready_for_output`、`output_generated` |

## 材料评估门禁（阶段 0）

- 欢迎语与采集方式选择卡发出后再读取指令和全部上传材料；
- 逐项形成覆盖度，OCR 或推断不得当作已确认事实；
- `sufficient` / `not_applicable` 跳过对应卡片；`partial` / `missing` 编译为必答卡片；
- 没有材料时先给出"上传材料"或"直接填写卡片"两条清晰路径（见 opening-messages.json）。

## 卡片门禁（阶段 1–2）

- 同意记录：律师通道必须先完成 `lawyer-privacy-consent` 隐私确认卡（内容与《千问办公隐私政策》一致）；其他模式由用途告知 + 首次作答视为同意，`consent` 由运行时自动写入；无 `consent` 记录不得进入检索与生成；
- 卡片按五类归并发出（人员确认/财产确认/遗产分配/形式订立/遗嘱执行），通过回答可推导的不再单独提问；不设单独的人员、财产、分配中间确认卡；
- 采集只经 `AskUserQuestion` 卡组；每组 ≤4 题，分支题之后不同组追加依赖问题（互相独立的分支题可同组），可重复页独立成组；
- 全程只组织一次信息核对（`intake-confirmation` 汇总核对）；枚举解析结果在汇总核对确认前保持 `system_inference`，不得提前写入工作数据；
- 已确认字段不再重复发卡；遗嘱人基本信息（含住址）的缺失字段同组补采；签署要件以单张告知卡确认，不逐项追问；
- 律师通道：仅限 `audience = lawyer`，不出办理人题；文本输入属已披露例外，未经汇总核对确认不得写入工作数据；
- 必答卡组按覆盖度一次编译；可重复实例在数量题回答后确定性展开；
- 两种模式首组卡片均按协议内联规格直发，发出前不读卡组、不跑脚本、不写工作数据；卡组加载、compile/reconcile 与首次落盘推迟到首组回答收回后的同一轮一次完成，脚本调用用 `&&` 串联单次执行；
- 卡片队列、响应规范化、快速枚举解析、响应写回和覆盖度复算分别由 `compile_intake.py`、`normalize_card_response.py`、`parse_fast_lists.py`、`apply_intake_response.py`、`reconcile_coverage.py` 执行；不得以模型判断替代；
- 基本信息卡必须产出 `field_values`，不接受聊天文本替代；
- 房产分支、其他财产分支由卡组规则插入，不由模型临时发明字段；
- 进入检索前：全部 `required_card_ids` 均有已确认响应、`intake_session.status = "confirmed"`；
- 汇总核对同时呈现材料提取信息、卡片补充信息与枚举解析结果；需要修改时仅重发受影响卡片，更正答案即最终确认，不再二次汇总。

## 检索与规则门禁（阶段 3–4）

- 官方法源和近年案例已核验并记录检索时间（pkulaw 命中 + 官网效力核对）；
- 全部财产表述已完成清晰性核验：不动产已联网核验或标记 `address_unverified`；不清晰且无法联网补足的已标记 `description_unclear` 并明确提示用户补足；
- `cn-will-core` 规则包 ID、版本和法源基准匹配；
- `evaluate_rules.py` 已运行；`BLOCKED` 为零仅是 AI 草案生成门禁之一，不构成签署或效力结论；
- `BLOCKED`、`REVIEW_REQUIRED`、`WARN` 相关事项以简明事项和下一步动作合并进入执行指引，不另生成 AI 待判断文件，也不在执行指引中显示级别标签或展开事由。

## 输出门禁（阶段 5）

- 遗嘱正文七部分完整；
- 用户已选择的全部成果均已交付：文件类成果有对应文件，普法文章/视频在交付对话中呈现；
- 遗嘱形式与执行指引一致；
- 范本哈希和 OOXML 结构检查通过；
- `validate_case.py` 零 error；
- 所有文件含精确 AI 文件声明，输出元数据固定 `preparation_only=true`、`signature_ready=false`；
- 输出中不包含案件概览、快照、交接单、归档或任务管理文件。

## 失败处理

- 任何阶段不得使用 `rm` 等永久删除命令；原始回答与中间件保留为轨迹或 `mv` 入 `processed/`；
- 材料解析失败：说明具体文件和原因，允许重新上传或改用卡片填写；
- 用户中途离开：本次 `work-data.json` 保留在输出目录，但不承诺长期恢复（不做案件管理）；
- 法源无法访问：`legal_research.status = "blocked"`，披露失败来源，不伪造依据；
- 规则 `BLOCKED`：只输出缺口和处理路径，不生成遗嘱正文草案；
- DOCX 范本不匹配：停止生成，不自动重建版式。
