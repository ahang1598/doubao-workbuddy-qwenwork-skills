#!/usr/bin/env python3
"""唯一交付入口：事实表 + 结构化报告 → HTML 报告和对话摘要。

用法：
  python3 scripts/finalize_report.py report.json facts.json \
      --html-output report.html --summary-output SUMMARY.md

完整报告内容只存于 report.json，不先生成完整 Markdown 正文。
"""

from render_structured_report import main


if __name__ == "__main__":
    raise SystemExit(main())
