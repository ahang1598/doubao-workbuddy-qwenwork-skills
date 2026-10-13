# INSPECT 详细 (Step 1 拆出)

> 主文 SKILL.md 已精简, 本文存放 INSPECT 完整说明

## Step 1 — INSPECT

```bash
python scripts/xlsx_reader.py <file> --inspect
```

返回 JSON 含:

| 字段 | 用来做什么 |
|---|---|
| `sheet_dims` | 各 sheet 行列数(多 sheet 必看,见下方多 sheet 决策);行数为真实值 |
| `column_info` | 列名 / dtype / 样本 / null 率(大表时基于采样,见 `profile_scope`) |
| `data_traps` | 陷阱清单,**每条含 `suggested_read_code`** — pandas 该怎么读 |
| `previews` | 每 sheet 头尾行(大表时 `tail` 为真实表尾,非采样段尾巴) |
| `profile_scope` | 每 sheet 画像采样范围 `{sampled, rows_profiled, rows_total}` — 大表 INSPECT 仅采样前 20000 行做 `column_info`/`data_traps`;`sampled=true` 时全量统计须改用 `xlsx_analyze.py`,勿把采样画像当全表 |
| `next_action.recommend_validate_columns` | schema 含中英混排 / 半角括号 / 中文+下划线 时自动出现;建议写完脚本跑 `--validate-columns` 预校验 |

**必须先看 `data_traps`**。常见陷阱及不修后果:

| 陷阱 | 不修后果 |
|---|---|
| 合并表头 | 把 "2024年"/"合计" 当数据行,KPI 偏差 30%+ |
| 日期序列号(45000) | 当成大数,聚合错 |
| 百分比字符串('15%') | sum 报错或当 None |
| 跨 sheet 公式 cache 缺失 | 拿到全 None |
| 多 sheet 同名列 | concat 后口径混淆 |
| 动态数组函数 | 只拿左上角值 |
| **重复列名(duplicate_header)** | pandas 静默改第 2 个为 `name.1`,KPI 引用『销售额』时口径混淆 |
| **公式错误值(formula_error_cells)** | `#DIV/0!`/`#VALUE!` 被转 NaN,`.sum()` 静默忽略,聚合偏低 |

按 `suggested_read_code` 读,不要自己琢磨。

### 纯文本数据降级(仅适用「确认无可数值化语义」场景)

✅ **应降级**的特征——三条都满足:
1. INSPECT 报所有列 `dtype='str'`、measure 列计数为 0
2. 列内容是**描述性文本 / 状态枚举 / 类别标签**(如:功能特征、品牌名、"支持/不支持"、"通过/未通过")
3. `pd.to_numeric(df[col], errors='coerce').notna().mean()` 试探转换成功率 **<50%**(即多数无法 coerce)

→ 降级到分类分布分析: `value_counts()` / 频次表 / 组合占比;报告显式声明「数据无数值列,已降级 categorical」。

⚠️ **不要误伤**——以下场景虽然 INSPECT 报 `str`,但**应该清洗后聚合**:
- 金额字符串 `'1,234.56'` / 百分比 `'15%'` / 数字带单位 `'8.5万'`:data_traps 会提示 coerce 模式,按 `suggested_read_code` 清洗后聚合
- 日期字符串 `'2024-01-15'`:用 `parse_dates` 转 datetime
- 数值列因编码 / 混入空字符串被误识别为 str:`pd.to_numeric(errors='coerce')` 转换后聚合
- 上述任一情况 to_numeric 成功率 ≥50% → 视为数值列处理,不降级

判断关键:**先试 `pd.to_numeric(df[col], errors='coerce')` 看转换率**,再决定是降级还是清洗。

## Step 0 — 格式护栏

### 支持范围

| 扩展名 | 动作 |
|---|---|
| `.xlsx` / `.xlsm` / `.csv` / `.tsv` | 继续 Step 1 |
| `.xls` | 告知用户另存为 `.xlsx`(旧二进制格式,本 skill 不解析)|
| `.pdf` / `.docx` / `.pptx` / `.txt` / 图片 | 退出 data-report;agent 可调用其他 skill 处理 |
| `.db` / `.sqlite` / `.mdb` | 退出 data-report;agent 可用 SQL skill,或让用户先导出 csv |
| `.zip` / `.rar` / `.tar` / `.gz` | 退出 data-report;让用户解压后再给表格文件 |

### data-report 流程内禁止的绕过手段

| ❌ 在 data-report 流程内禁止 | 为什么 |
|---|---|
| `import sqlite3` + 当作 data-report 的输入 | data-report 不是 DB 分析 skill |
| `pandas.read_sql()` 当作 data-report 的输入 | 同上 |
| `import zipfile` 解压用户给的 .zip 后塞给 data-report | data-report 期待用户给已解压的表格 |
| `import pypdf / pdfplumber` 提取 PDF 表格喂给 data-report | data-report 不做 PDF |
| `import pyxlsb / xlrd` 读 .xls / .xlsb | 这两格式本 skill 不支持 |
| `pip install <绕过依赖>` 为了在 data-report 里硬解析非表格 | 增加 skill 不该有的依赖 |

**编造 mock 数据填报告**:用户没给数据时不能假装有数据。用户明示"造测试数据"时可以,但报告里必须标"模拟数据"。

### 退出模板

非表格输入时,告知用户范围 + 建议路由(数据库→导出 csv;压缩包→先解压;PDF/图片→先 OCR/pdf-extract)。不要在 data-report 流程内强行解析。

### 用户消息含非表格内容时(聊天记录 / 邮件 / PDF 章节 / 用户口述数字)

**不要假装读过这些内容;不要把用户口述数字当数据源**(除非用户明示"这是数据,请直接用")。报告中引用时显式标"用户提供的描述"而非脚本计算。

