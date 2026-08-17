# Changelog

## v2.1.0 (2026-08-11) — 四批真机测试整改（L1/L2/L7/L8/L9）

1. **L1 门禁已知陷阱声明**：胜诉概率表述规则后加陷阱说明——概率/清偿率分析只允许在第八章立案建议出现，Decision Pack 等章节用定性表述
2. **L7① 能力覆盖表输出**：SKILL.md §4.2 要求能力覆盖摘要表附在报告「数据来源」章节，探测过程可审计
3. **L7② §A0 脱敏实体提取**：输入分流表加"企业名被遮挡/脱敏"分支（合同编号/项目名/地址片段/USCC末位/法代姓名组合推导）
4. **L8① §A5 备选触发**：开庭公告中多次出现与本案直接相关的案件时，不受裁判文书≥5件阈值限制做 1-2 次详情检索
5. **L8② §A4 条件必做**：实控人控制比例≥30%或多层架构控制时，实控人风险画像从可选升为必做
6. **L2 §A5 硬读指令**：补充检索前必须实际 Read websearch-strategy.md
7. **L9 脚本报错文案优化**：validate_risk_report.py 概率拦截文案明示"纯定性表述不拦截、检查同行混入数值、改区间或补依据"（放行口径不变；冒烟验证定性放行+数值拦截）

## v2.0.0 (2026-08-10) — 单元 8 二合一

- 合并 `lawd-recovery-assessment`（债务清偿能力评估）为本单元**模式B**，原诉讼风险评估为**模式A**；`name` 保持 `lawd-litigation-risk`，`name_zh` 改为「诉讼风险与清偿评估」
- SKILL.md 重写为固定六段结构：能力总述 / 触发与分流 / 模式工作流 / 数据源 / 门禁脚本 / 交付物
- frontmatter description 单行重写，覆盖两组触发词；两技能原互指的 NOT for 条目内化为模式路由，跨技能 NOT for（company-info / counterparty-check / contract-review-pro）保留
- 数据源按连接器三铁律重写为「企业工商信息查询」能力语义 + 三段式探测（tool_list → 语义匹配并用 tool_get 验证返回 schema → tool_call）+ A 档降级；删除供应商硬编码与无标注的网页检索兜底
- references/ 归并：吸收 recovery-assessment 8 个参考文件，同名冲突加 `recovery-` 前缀（`recovery-output-report.md`、`recovery-websearch-strategy.md`）
- 新增交付门禁 `scripts/validate_risk_report.py`：概率/清偿率必须区间或带依据、工商数据未取得时禁止完整评估结论、必备章节齐备
- 报告模板新增必填声明行「工商数据获取状态」，来源代码由供应商维度改为数据能力域维度

## v1.1.0 (2026-08-03)

- 自 LS-DEV 分支（commit 50dcb20）移植至 QwenWork-Legal-Skill 目录
- 互引名称统一为库内实际名称（lawd-party-check → lawd-counterparty-check、lawd-debt-recovery → lawd-recovery-assessment）

## v1.0 (2026-05-22)

- Initial release
- 三层穿透扫描：企业当前层(5维司法) + 企业历史层(5项) + 核心人员层(4项)
- Step 0 实体锚定：USCC正则/完整企业名/简称消歧
- 9 章报告模板（对齐主流工商数据商官方法律风险报告格式）
- 执行风险评级（极低/低/中/高/极高 五档）
- 置信度分布模型
- 补充检索（信用中国+裁判文书+舆情）
- 支持双工商数据源切换
