# 交付流程：事实表 → 结构化报告 → HTML 与重点摘要

## 一、唯一内容源

完整报告只写一份结构化 report.json；先完成 facts.json，后写 report.json。不要先写完整 Markdown 报告，也不要让模型直接手写 HTML。正式 HTML 和对话摘要由同一份 report.json 生成。具体字段见 report-schema.md。

任务开始时建立内部目录和恢复入口：

~~~
_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/
├── 00_RESUME_HERE__NEXT_STEP.md
├── DO_NOT_DELIVER__facts.json
├── DO_NOT_DELIVER__report.json
└── SUMMARY.md
~~~

HTML 报告存放在可交付位置。内部目录中的事实表、结构化正文和摘要文件仅用于校验与组装最终回复；对话里只展示摘要文字和 HTML 链接。

## 二、阶段顺序

1. 按 SKILL.md 与 linked-signals.md 检索取证；单条深度解读必须核对原公告、历史同类公告、关联公告、市场讨论与股价阶段表现。
2. 按 facts-template.md 写事实表。正文、表格、摘要、图表中的关键数字和重要判断要有 claim_id；凡用于图表的数据点，claim 额外写数值 value 与单位 unit。
3. 按命中的 playbook、output-formats.md 和 report-schema.md 写 report.json。必须覆盖对应模式的全部章节及反方、风险、后续验证条件。summary 只保留 2–5 条最重要结论。图表写入核验后的 x_labels、series 和 events，不制作待插入的大图片。
4. 运行 scripts/finalize_report.py 校验两份 JSON，生成 HTML 和 SUMMARY.md。出现错误时修复输入后重跑。
5. 最终回复直接粘贴 SUMMARY.md，其中已有风险提示、重点结论和 HTML 报告链接。

## 三、执行命令

~~~bash
python3 scripts/finalize_report.py \
  _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__report.json \
  _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json \
  --html-output <可交付的报告.html> \
  --summary-output _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/SUMMARY.md
~~~

用户明确要求其他格式时，从同一份 report.json 导出。

## 四、引用和免责声明

report.json 中的每个事实绑定使用 fact_ids 数组，指向 facts.json 的 claims[].claim_id。正文不要手写来源编号。渲染器按首次出现顺序自动编号，同一来源名称加 URL 只占一个编号，并自动生成文末“数据来源”区块。

HTML 模板自动写入固定的长版免责声明；SUMMARY.md 自动写入固定的短风险提示和 HTML 报告链接。这样不会因遗漏源稿骨架而漏掉声明。数据缺口仍需在相关正文处明确说“数据不足”或“待核实”，不能依靠免责声明掩盖。

## 五、图表

数值图表由结构化数据直接绘制成 HTML 内的响应式 SVG。每个点必须引用带有匹配 value/unit 的 claim；事件必须绑定事实、所属市场和日期位置。A/H 股或其他跨市场叠加需要显式说明。图题、单位、图例、来源和口径都要可见，不能把整页图文当图片贴入正文。
