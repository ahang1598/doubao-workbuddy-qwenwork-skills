# Step 2 分析 详细

> 主文已精简, 完整规则与示例在此


按下面通用框架走,框架内具体内容(KPI 选什么、画什么图、洞察文字、布局风格)由你自由发挥。

### 报告里要有什么(交付物结构)

- **一句话结论**(报告开头,40 字内,核心数字+结论)
- **3-6 个 KPI 数字**(每个带:值 + 同期/基线对照)
- **主体分析**:维度切分表 + 趋势图(有日期列时) + 异常标注
- **洞察**:每条三段 — 数字事实 / 原因 / 该做什么
- **末尾**:可执行的下一步建议

### 写报告的步骤

1. 按 INSPECT 的 `suggested_read_code` 读数据
2. **可选但推荐**:跑 `xlsx_analyze.py` 拿事实摘录(见下方「xlsx_analyze 能做什么」)
3. 算 KPI / 维度切分 / 趋势(有日期列时)
4. **写 HTML 前必须跑 spot check(门控 — 不过不准写 HTML)**,流程见下方「spot check 门控」章节
5. 写 HTML(ECharts 渲染,数据 inline)
6. 进入 Step 3 跑 `--validate-html`,失败按 errors **单点修**

### xlsx_analyze.py 能做什么(以及何时不必跑)

```bash
python scripts/xlsx_analyze.py <file>                # 全量分析(默认)
python scripts/xlsx_analyze.py <file> --profile-only # 仅画像(最快路径,10x 快)
python scripts/xlsx_analyze.py <file> --head 100000  # 大文件读前 N 行(见数据量章节)
```

**返回结构(事实摘录器,不替你写报告)**:

| 字段 | 给你的 |
|---|---|
| `profile` | 每 sheet 的 role(config/summary/data)、列分类(dim/measure/date)、缺失率、quality_flags |
| `raw_stats` | 每列 sum/mean/median/std/p25/p75/p90/p99 + count/nunique/null_count — **spot check 的锚点** |
| `data_traps` | INSPECT 那 6 类陷阱 + V5 新增 `duplicate_header`/`formula_error_cells` |
| `findings` | 自动发现(13 类,见下表;每条含 text + data,**text 是纯数字事实不是叙事**) |
| `sampling` | mode/n/file_size_mb — 采样过必须在报告 transcript 引用 |

**13 类 finding 的语义和触发条件**(数据不满足条件就不会出,0 finding 是正常的):

| type | 含义 | 触发条件 |
|---|---|---|
| `outlier` | IQR 离群值(值 + 占比 + 极端示例) | 数值列 ≥10 行 |
| `distribution` | 分布偏度(中位数、均值、skew) | 数值列 abs(skew) > 1.5 |
| `concentration` | Top N 集中度(按 dim 求和) | 维度基数 3-50 且 Top 80% 集中 |
| `composition` | 维度构成(饼图素材) | 维度基数 ≤8 |
| `comparison` | 维度间 measure 差异(按 dim 求均值) | 维度基数 ≤10 且 max/min > 2 |
| `trend` | 时序前半/后半均值变化(含 slope/r²/missing_periods) | 日期列 + resample 后 ≥2 期 |
| `spike` | 时序环比 > 30% 的最大变化点 | 日期列 + 数值列 ≥3 期 |
| `growth_rate` | MoM(≥2 月)/ YoY(≥13 月)增长率 | 日期列 + 月聚合 |
| `periodicity` | 周内波动(CV + 峰谷比 + weeks_covered) | 日期列 + 周内 CV > 15% |
| `correlation` | Pearson r > 0.7 的列对 + sample_size + reliability | ≥2 数值列 |
| `percentile` | 长尾分位(p90 贡献 + 均值/中位数比) | 数值列 ≥20 行 |
| `cross_dimension` | 两维交叉 Top cell + min_cell_n + reliability | ≥2 维度(基数 2-15) |
| `data_quality` | 高缺失(>10%)/重复行 | 任意 |

**何时跑全量** vs **何时 `--profile-only`** vs **何时跳过**:

| 场景 | 怎么做 |
|---|---|
| 时序数据 / 多 sheet / 多维业务表 / > 1000 行 | 全量跑(finding 价值高) |
| 单 sheet 简单结构 / 已知列含义 | `--profile-only`(拿 raw_stats 做 spot check 即可) |
| 文件 > 200 MB | `--head N` 或 `--profile-only`(见数据量章节) |
| 小样本(< 50 行) / 纯文本 / 配置表 | 跳过,直接 pandas(analyzer 触发不了) |

**绝对禁止**:把 finding 的 `text` 字段直接 copy-paste 当洞察。text 只是事实陈述(如『某列偏度=2.3』),洞察必须由你结合业务语义重写。

### spot check 门控(用 raw_stats 锚点 + 偏差时以 pandas 重算为准)

写 HTML 前必须通过 spot check,不通过不准写 HTML。流程:

```python
# Step A: 跑 xlsx_analyze 拿 raw_stats 作锚点(已跑过则直接用 JSON)
#         例: raw_stats[col='销售额'] = {'sum': 1234567, 'mean': 246.9, ...}

# Step B: 用 pandas 独立重算将写入 HTML 的每个 KPI
total = df['销售额'].sum()
print(f"[SPOT CHECK] 总销售额 — pandas={total:,.2f} vs raw_stats={1234567:,.2f}")

# Step C: 比对
#   一致(偏差 < 0.1%)→ 通过,写 HTML 用这个值
#   不一致 → 见下方「raw_stats 与重算不一致怎么办」
```

**常见 check 项**(按报告内容选,不必全做):
- **总聚合**: `df['<value_col>'].sum()` vs `raw_stats[col]['sum']` — 偏差 < 0.1%
- **Top N**: `df.nlargest(N, '<col>')` — 名称和值都一致
- **占比/份额**: 所有占比求和 ≈ 100%
- **行数/记录数**: `len(df)` vs `raw_stats[col]['count']`(数值列)或 `profile[sheet]['rows']`
- **分组小计**: `df.groupby('<dim>').sum().sum()` == `raw_stats[col]['sum']`
- **分类值筛选**: 写死分类字面量(`df[df['col']=='x']` / `.isin([...])`)前,**主动**核对该值真实存在——`df['col'].value_counts()`(分块读取时逐 chunk 累计),不能只依赖 INSPECT 采样(低频值可能未被采到)。若关键筛选结果为 0、或与总量完全一致,回看分类值是否拼错(如 `退款` vs `已退款`)并在 transcript 说明已确认。(结果为 0 不一定是错——可能本就无该类数据,确认即可。)
- **chart series.data 非空**(结果导向硬门控): 每个 chart 写入 HTML 前必须确保 `series.data` 非空。用什么方式核(assert、spot check 打印、构造时 verify、`print(df)` 检查 等)由你选,**只看结果不看形式**。任一 chart 的 `series.data` 为空数组写入 HTML → ECharts 渲染时触发 `c.resize is not a function` 等运行时错,前端整图崩(已有真实失败案例)。常见根因:时间窗过滤掉所有行 / 维度筛选结果为空 / groupby 后某分桶 0 行 / 数据清洗后剩余 0 行等。

#### raw_stats 与 pandas 重算不一致怎么办

**优先信任你的 pandas 重算**——脚本的 `_coerce_numeric_text`/`_classify_columns` 在以下场景可能误判:

| 误判场景 | 现象 | 你的处理 |
|---|---|---|
| 百分比字符串(『15%』)被脚本当 15 而非 0.15 | sum 比预期大 100 倍 | 自己 `.str.rstrip('%').astype(float) / 100` |
| 含『万/亿』后缀的字符串聚合错位 | sum 偏离量级 | 自己处理单位 |
| 重复列名只算了一列 | sum 比预期小 | 按 V5 trap 的 `suggested_read_code` 分别 rename 后再算 |
| 公式错误值(#DIV/0!)被 fillna(0) 拉低 | mean 偏低 | 显式 `.dropna()` 并标注 n_excluded |
| 多 sheet 合并时被脚本独立分析 | 跨 sheet 加总有差 | 自己 concat 后算 |

**处理动作**:
1. **以 pandas 重算为准**写入 HTML
2. **transcript 明示**:『脚本 raw_stats 显示 X,pandas 重算得 Y,以重算为准(原因:<具体>)』

> ⛔ **跳过 spot check 直接写 HTML 是数字编造错误的首要根因**。不论模型多自信、文件多简单,门控不过不准写 HTML。

### 数字单源原则(硬性,所有模型适用)

**HTML 中和 assistant_message 中出现的同一个数字,必须来自同一次计算结果**。

**绝对禁止**:
1. 在 HTML 不同位置(顶部卡片 vs 中间表格 vs 末尾结论)独立计算或凭印象写同一指标
2. 在 assistant_message 中"复述" HTML 数字时**凭印象口算估算**
3. 在 HTML 模板里写死字面量数字("销售额 13650")若该数字本应来自 df 计算

**事后判定**:假设 HTML 顶部卡片写 X,assistant_message 也提到 X,能不能在代码里 grep 到一处 `X = <某次计算>` 是这两处共同的源?能 → 合规。不能 → 重做。

#### 实现方式(任选其一,重要的是『可追溯到一次计算』)

**方式 A:kpis dict(推荐——保证合规,弱模型/多 KPI/大型报告首选)**

```python
kpis = {
    'total_sales': df['销售额'].sum(),
    'top_region': df.groupby('区域')['销售额'].sum().idxmax(),
    'top_region_share': df.groupby('区域')['销售额'].sum().max() / df['销售额'].sum(),
}
print(f"[KPI SOURCE] {kpis}")  # 留印于 transcript

html = f"""
<div class="card">总销售额: {kpis['total_sales']:,.0f}</div>
<table>... {kpis['top_region']} 占 {kpis['top_region_share']:.1%} ...</table>
"""
# assistant 复述时也只能引用 kpis 的键
```

**方式 B:变量直接引用(简单报告 / 3-5 个数字 OK)**

```python
total = df['销售额'].sum()
top_region = df.groupby('区域')['销售额'].sum().idxmax()
print(f"[KPI] total={total:,}, top_region={top_region}")
html = f"<h1>总: {total:,}, Top: {top_region}</h1>"
```

**方式 C:模板引擎 / `.format(**context)`(大型 HTML,高级模型适用)**

```python
context = {'total_sales': total, 'top_region': top_region, ...}
html = TEMPLATE.format(**context)  # 或 jinja2 render
```

> `.format()` 占位符**只能是** `{name}` 或 `{name:spec}`,`name` 必须是 context 的键。
> **禁止**在占位符里写表达式:`{a/b}`、`{a if c else d}`、`{obj.method()}` 都会抛 `KeyError`。
> 所有派生值(比值、百分比、倍数)必须在 context dict 里**预先算好**再传入。

三种方式都满足『可 grep 到单一计算源』。**不允许的反模式**是在 HTML 不同位置重复写 `df['x'].sum()` 或凭印象敲字面量。

#### 🚫 铁律:禁止用 f-string / `.format()` 拼含 JS/CSS 对象字面量的 HTML

❌ 错误姿势(**禁止**):
```python
html = f"""
<style>.box {{ color: red; }}</style>     # f-string 里 CSS 的 { } 要写 {{ }} 转义,模型经常漏
<script>
  const data = {{ name: '{name}', value: {value} }};   # JS 对象的 { } 也要 {{ }} 转义,组合复杂会出错
  arr.map(x => ({{a: x.a}}));              # JS 箭头返回对象,需要内层 ({{ }}),f-string 视角=四层转义
</script>
"""
```

✅ 正确姿势(**只用这个**):占位符替换
```python
# template.html 里用人眼一看就懂的占位符(不会与 JS 冲突):
#   <script>const data = __DATA_JSON__;</script>
#   <h1>__TITLE__</h1>
template = open("template.html", encoding="utf-8").read()
html = (template
        .replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False))
        .replace("__TITLE__", title)
        .replace("__TOTAL__", f"{total:,}"))   # f-string 仅用于格式化单个值,不拼整段 HTML
```

口诀:**Python 字符串里有 `{` 或 `}` 字面量时(即里面藏了 JS/CSS),就别用 f-string / .format(),改用 replace。**

### 洞察怎么写(每条三段,缺一删)

| 段 | 该写成这样(有具体数字 + 因素) | ❌ 不要写成这样(模糊套话) |
|---|---|---|
| **数字事实** | "维度 A 在 <指标> 上 = 334,排第一,占全表 24%" | "维度 A 表现不错" |
| **原因** | "因子 X 在该 group 同期上升 30% + 因子 Y 在该时段集中" | "因为业绩好" |
| **行动** | "把资源 R 调整 30% 投入到维度 A" | "建议加强管理" |

### ❌ 禁止出现的套话(出现即不合格,必须用右侧替代写法改写)

| 禁止短语 | 为什么禁 | 替代写法示例 |
|----------|----------|-------------|
| "表现不错" / "表现良好" / "表现突出" | 没有数字支撑 | "同比增长 23%,高于行业均值 15%" |
| "建议加强管理" / "建议优化" / "有待提升" / "建议关注 X" | 无具体动作 | "将 A 渠道预算从 20% 提升至 35%" 或 "把 X 监控频率改为日报" |
| "有待进一步分析" / "需要更多数据" | 推卸结论 | 给出当前数据支持的初步结论 + "要验证需补充 X 数据" |
| "整体呈上升/下降趋势" | 没有幅度和时间段 | "Q1→Q2 月均增速 8.3%,Q3 回落至 2.1%" |
| "差异明显" / "差异显著" | 没有统计量 | 给出具体差值 + 百分比(如有 p-value 则附上) |

### ❌ 还有 4 类行为也不合格(套话表覆盖不到)

- **纯数字搬运**:洞察只有"X 列均值 3.2"——必须再加 So What(意味着什么、对谁、所以呢)
- **没说『谁做什么、调多少』的建议**:必须含具体操作对象 + 量化目标(如"把 A 渠道预算从 20% 提到 35%")
- **一条洞察堆 3 个以上数字而无解释**:只选最重要的 1-2 个,其余删
- **"相比之下"开头但不给基准和差值**:必须明示比较基准(同期/竞品/目标)+ 具体差值

### 多 sheet 文件怎么办

| 情况 | 处理 |
|---|---|
| 多 sheet 列名一样(同 schema) | `pd.concat` 合并 |
| 列名同但口径不同(销售额_含税 / 销售额_不含税) | 分别算 + KPI 标签注口径 |
| 一个 sheet 明细、一个汇总 | 用明细 `groupby().sum()` 验证汇总(汇总公式 cache 可能为空) |
| sheet 名是「配置」/「字典」/「参数」 | 跳过,不分析 |
| INSPECT `sheet_dims` 显示多 sheet 但用户没明示 | 默认 `pd.read_excel(path, sheet_name=None)` 全部循环读,**不要悄悄只读第一个** |

```python
# ❌ 错: 默认只读 sheet[0],悄悄丢掉其他 sheet 的数据
df = pd.read_excel('data.xlsx')

# ✅ 对: 看 INSPECT sheet_dims, 用 sheet_name=None 读所有
sheets = pd.read_excel('data.xlsx', sheet_name=None)  # 返回 dict[name → df]
for name, df in sheets.items():
    print(f"[SHEET] {name}: {df.shape}")
```

### 数据量大时怎么办

| 文件大小 / 行数 | 怎么读 | 嵌入 HTML 的 |
|---|---|---|
| < 200 MB(< 5 万行) | 全量 `pd.read_excel/csv` | 原始 + 聚合都嵌 |
| < 200 MB(5 万 ~ 100 万行) | 全量读,聚合后嵌 | 只嵌 KPI / Top N / 分组结果 |
| **> 200 MB**(百万行级) | `xlsx_analyze.py` 默认 fail-fast → 走显式入口 | 同上,明细另存 CSV |

**xlsx_analyze.py 对超大文件的默认行为**:文件 > 200 MB 时直接返回 `error_class: file_too_large`,不会读爆内存。next_action 给 4 个显式入口:

```bash
xlsx_analyze.py big.csv --profile-only           # 只出 profile,最快路径
xlsx_analyze.py big.csv --head 100000            # 读前 N 行做样本分析
xlsx_analyze.py big.csv --sample 200000          # 等概率抽样 N 行(csv/tsv)
# 或在 Step 2 自己写 chunked:
for chunk in pd.read_csv(file, chunksize=200_000):
    # 累加聚合
```

> **任何采样必须在 transcript 明示**「共 X 行,本次分析 Y 行」— 悄悄截断 = 用户基于残缺数据决策。脚本输出的 `sampling` 字段会标 mode/n/file_size_mb,务必引用。

### 渲染只用 ECharts

画什么图自己定(柱 / 线 / 饼 / 双轴 / Top N / 箱线 / 散点 / ...),**渲染必须用 ECharts**(详见 Step 3 JS 库白名单)。

> ECharts formatter 字符串支持 `{value}`/`{b}`/`{c}`/`{d}` 占位符,但**不支持** `:,.0f` 这类 Python 格式 spec。
> 需千分位/小数位时改用回调:`formatter: v => '¥' + v.toLocaleString()`。

