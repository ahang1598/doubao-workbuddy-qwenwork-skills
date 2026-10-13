---
name: data-report
description: |
  从表格文件 (.xlsx / .xlsm / .csv / .tsv) 生成自包含 HTML 数据分析报告。 含 KPI 卡片、ECharts 图表、文字洞察。数据 inline 嵌入。
  TRIGGER: 用户上传表格文件 + 提出分析/出报告/看趋势/做可视化/出 KPI/同环比/ 排名/构成/异常/帕累托/漏斗/留存/归因/分群等诉求时立即触发, 包括"出份报告"/ "做个分析"/"看看数据"这类模糊表达。
  PARTIAL: .xls 提示用户另存 xlsx; 加密/损坏 xlsx 明确告知; 纯文本无数值列降级 categorical。
  DO NOT TRIGGER: 扩展名不在白名单 (pdf/docx/pptx/txt/图片/xlsb/parquet/ods/numbers); 数据库 SQL 场景 (.db/.sqlite/jdbc/mysql://); 修改/编辑 Excel 本体 (改用 xlsx skill); 数据清洗/去重/合并 (先用 xlsx skill TRANSFORM 后再调本技能); 图片 PDF 中的表格 (先 OCR/pdf-extract); API/HTTP 返回数据 (先落盘 csv/xlsx); 无数据输入仅有分析诉求 (先引导上传文件)。
license: MIT
install_source: official
install_method: download
skill_id: official_4MXzeuSN
enabled_at: 1791893719915
version: 1.0.1
name_zh: 数据可视化
---

# data-report

从表格文件生成 HTML 数据分析报告 (KPI + 图表 + 洞察, 数据 inline 内嵌)。

## 🔒 4 条硬规则 (违反 = 报告作废, 必须重做)

1. **Step 1 INSPECT 必跑** — 直接 `pd.read_excel` = 撞 data_traps (合并表头/百分比串/重复列名/公式错值)
2. **Step 2 spot check 必过** — 写 HTML 前 pandas 重算 vs raw_stats 偏差 < 0.1% 才准写, **优先对账总聚合 (sum/total/GMV/总额)** — 这类最容易撞 raw_stats 字段错位 bug, 不能只对账均值/中位数. **每个 chart 的 series.data 至少 print 一个非零 cell 确认** (e.g. `print(stack_data['家电'][0])`), 不能只 print sum
3. **数字单源** — HTML 和 assistant_message 里同一指标必须可 grep 到同一处计算
4. **Step 3 VALIDATE 必跑** — 跳过 = 直接交付白图 / f-string 残留 / JSON 损坏 / ECharts 崩 (用户打不开). 报 `orphan_chart_div` 必须修复 — 每个 chart div 必须有对应 `echarts.init`

## 5 步主流程

```
Step 0 格式护栏  →  Step 1 INSPECT  →  Step 2 分析  →  Step 2.5 备份导入  →  Step 3 VALIDATE  →  交付
```

### Step 0 · 格式护栏

| 扩展名 | 动作 |
|---|---|
| .xlsx / .xlsm / .csv / .tsv | 继续 |
| .xls | 提示用户另存 xlsx (本技能不解析旧二进制) |
| .pdf / .docx / .pptx / 图片 / .db / .zip 等 | 退出, 引导对应 skill |

**禁止绕过**: 不要 `import sqlite3` / `import zipfile` / `import pyxlsb` / `import pypdf` / `pip install xlrd` 等强行解析非表格输入。完整规则见 [`references/inspect_details.md`](references/inspect_details.md)。

### Step 1 · INSPECT (必做)

```bash
python "${SKILL_DIR}/scripts/xlsx_reader.py" "<file>" --inspect
```

返回 JSON 含: `sheet_dims` / `column_info` / `data_traps` (每条带 `suggested_read_code`, 按它读不要自己琢磨) / `previews` (头尾真实行) / `profile_scope` / `next_action.recommend_validate_columns`。

INSPECT 报 quirk 时, 写完分析脚本首跑前预校验列名:
```bash
python "${SKILL_DIR}/scripts/xlsx_reader.py" "<file>" --validate-columns col1 col2 ...
```

陷阱清单与处理见 [`references/inspect_details.md`](references/inspect_details.md)。

### Step 2 · 分析

**步骤**:
1. 按 INSPECT 的 `suggested_read_code` 读数据
2. (推荐) 跑 `xlsx_analyze.py` 拿 `raw_stats` 作 spot check 锚点
3. 算 KPI / 维度切分 / 趋势
4. **spot check 门控** — 写 HTML 前必过
5. 写 HTML (ECharts 渲染, 数据 inline)

**spot check 怎么做**:
```python
# 用 pandas 独立重算每个将写入 HTML 的 KPI
total = df['销售额'].sum()
print(f"[SPOT CHECK] 总销售额 — pandas={total:,.2f} vs raw_stats={raw_stats['销售额']['sum']:,.2f}")
# 偏差 < 0.1% → 通过; 不一致 → 以 pandas 重算为准, 在 transcript 明示
```

**数字单源**: 把 KPI 都算在一个 `kpis = {...}` dict 里, HTML 和 assistant_message 都从同一个 dict 引用。禁止凭印象口算 / 在 HTML 不同位置重新算同一指标 / 在模板里写死字面量数字。

**HTML 拼接铁律**: 含 `{ }` 字符 (JS/CSS) 的 HTML 用 `.replace("__PLACEHOLDER__", value)`, 不要用 f-string / `.format()` (转义易错)。

**JSON 序列化铁律**: 写 JSON (`analysis_data.json` 等) 必加 `default=` 处理 numpy/Timestamp, 否则 `int64 is not JSON serializable` (最高频脚本错, ~半数 case 撞过)。模板见 [`references/cookbook_pandas.md`](references/cookbook_pandas.md) 「JSON 安全写出」。

**图表**: 渲染只用 ECharts (Chart.js/D3/Plotly 等禁用)。**CDN 必须从中国大陆可访问名单选**, 优先 `registry.npmmirror.com` (最稳定), 备选 `cdn.bootcdn.net` / `lib.baomitu.com` / `echarts.apache.org`; **非中国镜像** (如 `cdn.jsdelivr.net` / `unpkg.com` / `cdnjs.cloudflare.com`) **存在无法访问风险, 禁用**。完整模板见 [`references/chart-reference.md`](references/chart-reference.md)。

**洞察三段** (每条都要): 数字事实 / 原因 / 该做什么。禁止"表现不错/建议加强管理/有待提升/趋势上升" 等无数字套话。

**多 sheet**: INSPECT `sheet_dims` 显示多 sheet 时用 `sheet_name=None` 读全部, 不要默认只读第一个。

完整规则 (xlsx_analyze 用法 / 13 类 finding / 偏差处理 / 多 sheet 决策 / 大数据降级 / 洞察写法 / 套话黑名单) 见 [`references/analysis_details.md`](references/analysis_details.md)。

### Step 2.5 · 备份导入 AI 表格 (best-effort, 不阻塞交付)

**目的**: 把清洗后的数据持久化备份到钉钉 AI 表格, 作为报告的可追溯底表。**本步失败不影响 HTML 交付主链**。

**规则**:
1. **只导清洗后数据, 不导原始文件** — 用按 `suggested_read_code` 读出的 df 落 CSV (`index=False`, `utf-8-sig`) 再导入; 原始 data_traps (合并表头/百分比串/公式错值) 不进 Base
2. **默认新建 Base** — 命名与报告主题一致 (e.g. "销售数据分析-数据底表"); **仅当用户明确指定现有 Base** (名称或 alidocs URL) 才导入现有 Base, 不许默认猜
3. **失败语义 = 原样透出 + 交付不受阻**: 导入报错时把完整错误 (错误码/异常信息/调用参数) 原样写进 transcript 与交付消息, 然后继续走 Step 3; 禁止静默重试/降级/吞错。环境无 AI 表格能力时跳过并在交付消息注明
4. **结果必告知 (成功/失败均不阻塞流程)**: 导入成功或失败, 交付消息都必须有一段明确告知用户备份结果 — 成功: 告知"清洗后数据已导入为 AI 表格底表"并附 AI 表格可点击链接 (形如 https://alidocs.dingtalk.com/i/nodes/{baseId}, 从导入返回结果取); 失败: 附完整错误与本地 CSV 路径。不告知 = 该步未完成
5. **数字单源不变**: HTML 与 assistant_message 的 KPI 仍以 `kpis` dict 为唯一来源; Base 是数据备份, 不是第二计算源, 禁止从 Base 回读数据来写报告

具体操作 (CSV 导出规范 / 字段类型映射 / 大数据分批 / 错误透出格式) 见 [`references/aitable_import.md`](references/aitable_import.md)。

### Step 3 · VALIDATE (交付前必做)

```bash
python "${SKILL_DIR}/scripts/html_report.py" --validate-html <output.html>
# 8 项静态校验 + 无头浏览器真渲染 (best-effort, 默认开; 环境无可用浏览器时自动降级为纯静态)
```

校验失败 → 按错误**单点修**, 不要重写整张 HTML。详细 8 项与错误处理见 [`references/validate_details.md`](references/validate_details.md)。

**交付 (assistant_message)**:
- 全中文, 不要泄露 `[SPOT CHECK]` / `raw_stats` / `kpis['xxx']` 等开发术语
- 每个数字必须能在前面 transcript 的 print 中 grep 到同值
- HTML 顶部 / HTML 中间表格 / 本回复 — 同一指标必须取值一致
- Step 2.5 备份结果必须告知: 成功 → "清洗后数据已导入为 AI 表格底表" + AI 表格链接; 失败 → 完整错误与 CSV 路径 + 说明不影响报告交付; 跳过(无 AI 表格能力) → 注明跳过原因

## 🧰 SKILL 工具速查

| 命令 | 用途 | 时机 |
|---|---|---|
| `xlsx_reader.py <file> --inspect` | 数据陷阱 + 列画像 | Step 1 必跑 |
| `xlsx_reader.py <file> --validate-columns ...` | 校验列名 (防 KeyError 死循环) | 写完脚本首跑前 |
| `xlsx_analyze.py <file> [--profile-only / --head N]` | 全量统计 + raw_stats | Step 2 spot check 锚点 |
| `html_report.py --validate-html <html>` | 静态 + 无头浏览器真渲染校验 | Step 3 必跑 |

## 常见错误最小修复

- **多 sheet 只读了第一个** → 看 INSPECT `sheet_dims`, 多 sheet 用 `sheet_name=None`
- **洞察像流水账** → 按"数字 / 原因 / 行动"三段写, 只有数字搬运的删
- **`int64 is not JSON serializable`** → `json.dump` 漏 `default=`, 见 Step 2「JSON 序列化铁律」(最高频)
- **`Shell ... blocked` / `can't open file`** → 建目录用结构化 file 工具非 shell `mkdir`, 别用 `mkdir && python` 复合命令, 脚本用工作区相对路径; inspect/analyze 命令别加 `2>&1` (污染 JSON)
- **KPI 数字对不上** → 没按 `suggested_read_code` 读 → 抄
- **VALIDATE 报错重写整张 HTML** → 错通常是单点 (dom_id/fstring/JSON), 只改报错那行

更多见 [`references/common_fixes.md`](references/common_fixes.md)。

## 深度场景

差异归因 / 贡献度分析 / AB 测试显著性 / 时序异常等的 pandas/scipy 模板见 [`references/cookbook_pandas.md`](references/cookbook_pandas.md)。

## references 索引

| 文件 | 内容 |
|---|---|
| `references/inspect_details.md` | Step 0 格式护栏 + Step 1 INSPECT 详细 |
| `references/analysis_details.md` | Step 2 完整 (xlsx_analyze / spot check / 数字单源 / 多 sheet / 大数据 / 洞察) |
| `references/aitable_import.md` | Step 2.5 备份导入 (CSV 导出 / 字段类型映射 / 分批 / 错误透出) |
| `references/validate_details.md` | Step 3 校验 8 项 + assistant_message + 数据嵌入 + JS 白名单 |
| `references/chart-reference.md` | ECharts 模板片段 |
| `references/cookbook_pandas.md` | 深度场景 pandas/scipy 模板 |
| `references/common_fixes.md` | 常见错误最小修复扩展 |
