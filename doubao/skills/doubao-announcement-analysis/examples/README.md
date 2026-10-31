# 虚构冒烟示例

facts.example.json 和 report.example.json 只用于验证结构化交付流程；公司、数字和链接均为示意，不能用于真实投研报告。

在 Skill 根目录运行：

~~~bash
python3 scripts/finalize_report.py examples/report.example.json examples/facts.example.json --html-output /tmp/announcement-example.html --summary-output /tmp/announcement-summary.md
~~~

运行应生成含完整章节、来源、免责声明和内联 SVG 图表的 HTML，以及只含重点结论和报告链接的对话摘要。
