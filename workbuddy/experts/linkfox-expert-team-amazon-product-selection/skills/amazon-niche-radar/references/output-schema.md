# 输出契约

## 路径协议

运行期落盘一律走 `scripts/linkfox_paths.py`：

| 类型 | 函数 | 落点 |
|------|------|------|
| 中间数据 | `resolve_data_path(slug, ts)` | 当前工作目录下 linkfox 子目录的 data 分区 |
| 最终 HTML 报告 | `resolve_report_path(slug, ts, ext)` | 当前工作目录下 linkfox 子目录的 reports 分区 |

禁止写 `/tmp`、绝对路径硬编码。

## 传输层

最终 HTML 报告通过 `linkfox-report-generator` 的 `inject_report.py` 落盘，返回路径通过 `Saved full response:` 行输出。

## 载荷层

本 skill 的最终产物是 HTML 报告（由 linkfox-report-generator 生成），不输出 product_list JSON。中间数据（四个数据源的原始 JSON + 派生计算 JSON）落入 `data/` 目录供 S5 读取。
