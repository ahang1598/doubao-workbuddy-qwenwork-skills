# 飞书文档交付流程

本文件定义默认交付方式。股票筛选 Skill 的默认成品应是读者可直接阅读的 display markdown，并用豆包 App 内置飞书文档/云文档能力创建飞书在线文档。display markdown 和飞书文档必须包含“数据来源”和“风险提示与免责声明”。

## 默认触发

用户要求“帮我看下”“筛一下”“分析一下”“有哪些优质股”“核心标的”“龙头股”等股票筛选任务时，若没有明确说“只在对话中简短回答”“不要生成飞书文档”，均视为正式输出，必须创建飞书在线文档并在最终回复附上文档。

若平台当前无法调用飞书文档/云文档能力，必须在最终回复中明确说明“当前未能创建飞书文档”，并仍交付完整 display markdown；不得假装已经创建文档。

## 交付物边界

- 对用户可见：display markdown 正文、数据来源、风险提示与免责声明、飞书在线文档。
- 对用户不可见：内部源稿、事实表、恢复入口、草稿、日志、脚本输出。
- 最终回复不得展示内部文件名、路径、文件清单或工作流说明。

## 内部工作目录

需要生成完整报告时，所有中间产物写入：

```text
_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/
```

如果该目录下存在 `00_RESUME_HERE__NEXT_STEP.md`，继续工作前先读取并按其中的下一步恢复。

## 源稿与事实绑定

完整报告应先写内部源 markdown，并将关键数字和关键判断绑定到事实表：

```markdown
公司相关业务收入为 12.3 亿元，同比增长 28%。{fact:related_revenue}
```

规则：

- `{fact:...}` 只用于源稿审计，不出现在 display markdown 和飞书文档中。
- 源稿不要手写 `[n]`、`[^n]` 等脚注角标。
- 正文必须先写完整数字或判断，再绑定 `{fact:claim_id}`；不要把 `{fact:...}` 当数值占位符。
- `claims[].source/url` 决定 display markdown 中自动生成的 `[n]` 来源标记和文末来源列表。
- 上述“不要手写 `[n]`”只适用于使用 finalize 的内部源稿；display markdown 和飞书文档必须显示 `[n]` 来源标记。若当前平台没有运行 finalize，直接生成 display markdown 时必须手动生成 `[n]` 标记和文末来源索引。
- display markdown 和飞书文档正文不得出现裸 URL、链接数组、检索结果原始 JSON 或 `["https://..."]`；URL 只放在文末“数据来源”索引表。

## 默认后处理

若 Skill 包或运行平台提供对应脚本，最终交付分两步：

1. 运行唯一入口命令生成 display markdown：

```bash
python3 scripts/finalize_report.py _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.md _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json --display-output _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md
```

2. 调用豆包 App 内置飞书文档/云文档能力，以 `FINAL_REPLY_BODY.md` 的全文创建飞书在线文档，并在最终回复中附上该飞书文档。

## 脚本边界

- `scripts/finalize_report.py` 是默认后处理入口。
- `scripts/make_display_markdown.py` 和 `scripts/normalize_report.py` 是 `finalize_report.py` 内部 helper，不作为交付入口。
- `scripts/make_docx.py` 仅在用户明确要求 Word/DOCX 导出时使用，不是默认交付物。
- 如果当前 Skill 包尚未内置 `scripts/`，不得声称已经运行 finalize；应先按平台已有后处理能力生成读者版正文，或补充脚本后再启用该命令。

## 最终回复格式

```text
<display markdown 全文>

飞书文档：<附上的飞书文档>
```

最终回复不得出现 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/`、`DO_NOT_DELIVER__facts.json`、`DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.md`、`FINAL_REPLY_BODY.md` 等内部文件名或路径。

## 固定免责声明

display markdown 和飞书文档末尾必须包含以下章节，标题和三条内容保持一致：

```markdown
## 风险提示与免责声明

- 以上内容为 AI 自动生成或 AI 辅助生成，仅用于信息整理、投研辅助、教育交流或一般性分析参考，不构成对任何金融产品、交易策略或投资行为的推荐、邀约、承诺或保证，也不构成投资、法律、税务、会计等专业意见。
- 以上内容可能基于公开信息、历史数据或用户提供材料进行总结、归纳、推演与情景分析，但相关内容可能存在时效性不足、信息缺漏、事实误差、模型偏差或生成性错误。历史数据、历史业绩、回测结果及情景假设均不代表未来表现。
- 用户应基于自身风险承受能力、投资目标、财务状况及适用法律法规独立作出判断，必要时咨询持牌专业机构或顾问。任何因依赖本分析输出而作出的决策及其后果，由用户自行承担。
```
