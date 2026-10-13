# 技术架构（千问办公原生版）

```text
Agent 记忆中的最小调用标记
  -> SKILL.md 内置欢迎语随首条回复开场（零额外调用）
  -> 当前指令与附件的一次性材料解析和覆盖度评估（阶段 0）
  -> 确定性卡片编译 + AskUserQuestion 分组采集（阶段 1–2）
  -> 单次结构化工作数据 work-data.json
  -> pkulaw/官方法源案例核验 + 确定性规则执行（阶段 3–4）
  -> 确定性成果生成与交付（阶段 5）
```

## 职责分离

- 欢迎层：欢迎文案内置于 `SKILL.md`，随首条回复原文开场并同轮发出采集方式选择卡；不读记忆、不跑脚本、不单独占轮。数据用途告知包含在欢迎文案中；用户首次作答视为同意，`consent` 由运行时自动记录。
- 解析层：从当前材料提取候选事实和来源，不决定卡片导航。
- 覆盖层：判断各主题 `sufficient/partial/missing/not_applicable`，生成必答卡片集合。
- 交互层：`assets/cards/intake-card-deck.json` 是唯一题库，按五类卡组归并（人员确认/财产确认/遗产分配/形式订立/遗嘱执行），专项复核项改为推导与尾题；简易模式前两轮按协议内联规格直发以消除首组延迟；`compile_intake.py` 按覆盖度、模式和已确认分支编译队列，`normalize_card_response.py`、`parse_fast_lists.py`、`apply_intake_response.py` 和 `reconcile_coverage.py` 分别规范化、解析、写回和对账，模型不得运行时重新设计问卷。
- 数据层：`work-data.json` 只保存本次起草需要的事实、确认、研究、规则输入和成果输入，不承担案件管理。
- 规则层：加载版本化规则包并输出可审计结果。
- 生成层：从同一数据生成 Word、合并待判断事项的执行指引和可选图表；经核验的普法内容结构化返回并直接用于交付对话，不另生成链接或须知文件。

## 为什么仍需要结构化工作数据

没有单次结构化事实源，材料提取、卡片答案、法律规则和多份成果会互相不一致。该 JSON 随本次执行使用，不提供案件列表、长期恢复、归档、任务、权限或 CRM 功能。

## 目录

```text
assets/cards/       # AskUserQuestion 题库与材料评估后话术
assets/rules/       # 法律规则包
assets/schemas/     # 单次工作数据 Schema
assets/templates/   # Word 范本与内容预览壳
references/        # 法源、交互、输出和安全契约（渐进披露，按阶段加载）
scripts/           # 卡片运行时、规则、校验、成果和 DOCX 生成
tests/             # 回归测试
```

本 Skill 不需要 `agents/`；各阶段有严格先后门禁。v2 的浏览器端卡片运行时（card-runtime/renderer）因千问办公对话无事件回传通道已在 v3 移除。
