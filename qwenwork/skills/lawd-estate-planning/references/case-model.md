# 单次起草工作数据

结构化 JSON（`work-data.json`）是一次执行中的计算数据，不是案件管理系统。它把材料提取、卡片补充、法律研究、规则检查和全部成果连接到同一事实集合；不提供案件列表、客户管理、归档、继续办理或生命周期运营。

欢迎语不依赖 Agent 记忆；本数据模型的任何字段不得写入长期 Agent 记忆。`consent` 分区记录同意：律师通道经隐私确认卡明示同意；其他模式在采集话术告知用途后由首次作答视为同意；运行时自动写入 `accepted`、`accepted_at`、`purposes`、`sensitive_data_acknowledged` 与 `basis`。

`inheritance_review` 分区由运行时 `_derive_inheritance_review` 从已确认卡片回答确定性推导（胎儿份额与丧失继承权来自人员卡尾题、附义务来自分配卡、执行人意愿来自执行卡等），不再设置四张独立专项复核卡；能由回答推导的结论不重复提问。

## 核心分区

- `intake_session.collection_mode`：`fast` / `complete` / `lawyer_sheet`；
- `intake_session.coverage_assessment`：材料和指令对各主题的覆盖度；
- `required_card_ids` / `skipped_base_card_ids`：本次实际发出和跳过的卡片（可重复卡的实例 ID 在数量题回答后确定性展开）；
- `card_responses`：经 `AskUserQuestion` 卡片确认的补充信息（选项 `selected_values`、填空 `field_values`、备注/清单原文 `free_text`、占位 `answer_status = "later"`）；枚举填空卡的解析结果仅在汇总核对确认后写入对应分区；
- `testator_basic_info`：姓名、性别、出生日期、身份证号码、住址及确认来源；
- `testator_capacity`：理解、表达、真实自愿和专业评估状态；
- `people`、`relationships`、`assets`、`liabilities`、`intentions`：成果事实；
- `will_execution_plan`：遗嘱形式、签名、日期、见证和旧安排审查；
- `reserved_share_review`：必要份额候选人排查和处理；
- `inheritance_review`：继承人范围、胎儿份额、丧失继承权、共有财产、遗赠、附义务、兜底条款、遗产管理、债务税费、保险监护和复杂资产分流状态；
- `legal_research`：本次官方法源、案例和普法链接；
- `rule_context`：规则包版本与法源核验基准；
- `will_document`、`deliverables`、`output_preferences`：生成输入和成果选择；`ai_judgment_items` 作为执行指引中“还需要判断的事项”的输入，不对应独立文件。

## 覆盖评估

每个主题只允许：`sufficient`、`partial`、`missing`、`not_applicable`。`sufficient` 必须有可追溯材料或明确指令支持；不确定、冲突或仅模型推断时不能跳过卡片。

编译后：

- `progress.total_questions == len(required_card_ids)`（实例展开后更新）；
- 进入检索前，所有 `required_card_ids` 均有已确认响应；
- 跳过卡片的信息仍必须出现在最终汇总确认中；
- 房产和其他财产的联动卡由卡组分支规则确定性插入。

## 数据原则

- 使用不含姓名、身份证号或电话的稳定 ID；
- 身份证号等敏感值掩码展示，日志不保存明文；
- 用户陈述、文件提取、系统推断、外部法源和专业判断分别标记；
- 系统推断不能自动升级为用户确认；
- `Intention.related_person_ids` 和 `related_asset_ids` 是关系图与遗嘱条款的唯一人物—财产映射来源；
- 占位（`later`）字段仅允许进入醒目标注的 AI 框架稿；`signature_ready` 固定为 `false`，由律师决定如何补充、核实及后续使用。

机器约束见 `assets/schemas/case.schema.json`，演示数据见 `assets/examples/demo-case.json`。
