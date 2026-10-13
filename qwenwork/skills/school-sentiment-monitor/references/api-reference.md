# API 参考

## generate_report.sh

根据分析 JSON 生成可视化 HTML 舆情报告。

```bash
bash generate_report.sh <analysis_json> [output_dir]
```

| 参数            | 类型   | 必填 | 说明                   |
| --------------- | ------ | ---- | ---------------------- |
| `analysis_json` | string | 是   | 分析结果 JSON 文件路径 |
| `output_dir`    | string | 否   | 输出目录，默认 `~/.qwenworkcn/workspace/sentiment-monitor` |

**输出：** 生成 `sentiment_report_YYYYMMDD_HHMMSS.html`
