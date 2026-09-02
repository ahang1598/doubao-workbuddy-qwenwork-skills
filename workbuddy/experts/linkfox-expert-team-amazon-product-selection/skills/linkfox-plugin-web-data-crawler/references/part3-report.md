# Part 3 — 生成产品情报报告

采集完成且数据落盘后，由 AI 分析原始数据、整理为标准化 JSON，再调用模板注入脚本产出静态 HTML 报告。

---

## 流程概览

```
步骤 1 — 采集
  crawl → linkfox-plugin-web-data-crawler-<ts>.json

步骤 2 — AI 分析整理
  AI 读原始 JSON → 清洗/翻译/结构化 → clean_data.json

步骤 3 — 脚本注入
  python scripts/generate_report.py clean_data.json output.html

步骤 4 — 验证
  AI 检查报告完整性
```

---

## 步骤 2 — AI 分析整理

### 核心职责

脚本不做任何数据解析。以下工作全部由 AI 完成：

| 工作 | 说明 |
|------|------|
| 字段去重 | 如 `images` 与 `images_raw` 内容相同 → 只保留一份 |
| 配送信息去重 | `delivery_block_full` 常有重复行 → 去重后最多保留 2 条（标准/Prime） |
| Badge 清洗 | 过滤 `NO_OF_HOURS` 计时器占位符 → 只保留 `"Limited time deal"` |
| 变体信息精简 | 颜色选项去重（Amazon 每个色出现两次）、统计色数和尺码数 |
| 直方图解析 | 从 `5 star71%13%8%3%5%71%...` 格式中提取 5 个百分比值 |
| 品牌名清洗 | `"Visit the WIHOLL Store"` → `"WIHOLL"` |
| 评分提取 | `"4.4 out of 5 stars"` → `4.4` |
| 评价数提取 | `"(2,099)"` → `2099` |
| Bullet 翻译 | 英文原文 → 中文翻译（直译 + 本地化） |
| 规格名称中文化 | `"Fabric type"` → `"面料材质"`，`"Care instructions"` → `"洗护说明"` |
| 筛选规格 | 过滤掉已在前文展示的冗余行（ASIN、Customer Reviews、Best Sellers Rank） |
| BSR 提取 | 从 product_details 中提取大类排名和子类排名 |
| 价格分析 | 计算折扣百分比、判断有无 Coupon |

**🔴 核心原则：只做转换，不做推断。** `clean_data.json` 中的每一个值都必须能追溯到原始采集 JSON 中的对应字段。原始数据里没有的字段 → 填 `null` 或省略，**禁止**根据已有字段推算、估算、猜测缺失数据。典型违规示例：

| ❌ 错误做法 | ✅ 正确做法 |
|---|---|
| 从 `review_avg_score: 4.86` 倒推出 `histogram: {5:88, 4:9, ...}` | `histogram: null`（原始数据没有星级分布） |
| 从评分估算 `good_rate: 97` | `good_rate: null`（原始数据没有好评率） |
| 从评论正文编造 `ai_summary` | 标注来源：`"Based on top reviews: [引用原文]"` 或无数据时 `null` |
| 原始数据为空字符串 `""` → 填一个有意义的默认值 | 保持空字符串或 `null` |

> 一句话：**采集到什么就展示什么，没有的就诚实留白。** 数据完整性归采集 workflow 管，数据清洗只负责格式化和翻译。

### 输出格式：`clean_data.json`

完整 schema 见 `scripts/generate_report.py` 顶部的 `CLEAN_DATA_SCHEMA` 注释。核心结构：

```json
{
  "meta": {
    "title":    "商品短标题 — 产品情报报告",
    "subtitle": "规格摘要 · 评分 · 销量",
    "tagline":  "ASIN: B0XXX · 采集日期: YYYY-MM-DD · Amazon US",
    "date":     "2026-07-16",
    "asin":     "B0XXX"
  },
  "kpi": [
    {"value": "$7.59", "label": "当前售价", "sub": "24% off, 原价 $9.99"},
    {"value": "", "type": "rating", "label": "4.4 / 5 · 2,099 条评价", "sub": "好评率 84%（4-5星）"},
    {"value": "1K+", "label": "月销量", "sub": "BSR #97 服装大类"},
    {"value": "<span style=\"color:#059669;\">有货</span>", "label": "库存状态", "sub": "#6 女式 T 恤子类"}
  ],
  "overview": {
    "main_image":   "URL",
    "description":  "1-2 句产品概述",
    "info":         "品牌 · 款式 · 颜色 · 尺码 · 季节",
    "badges":       ["Limited time deal"]
  },
  "bullets": [
    {"en": "英文卖点（精简）", "zh": "中文翻译"}
  ],
  "price_variants": {
    "current":             "$7.59",
    "list":                "$9.99",
    "savings":             "24% off",
    "badge":               "Limited time deal",
    "variants_text":       ["S","M","L","XL","XXL","3XL"],
    "variants_dimensions": "Color（34 色）, Size（S-3XL）",
    "variants_summary":    "34 色 × 6 尺码 = 40 ASIN",
    "note":                "补充说明（可选）"
  },
  "rating": {
    "score":       4.4,
    "count":       2099,
    "good_rate":   84,
    "histogram":   {"5": 71, "4": 13, "3": 8, "2": 3, "1": 5},
    "aspects":     [{"name": "Fit", "count": 228}, ...],
    "ai_summary":  "Customers find...(Amazon AI 摘要原文)",
    "note":        null
  },
  "delivery": {
    "type":    "FBA 免邮 · 满 $35 免运费 · Prime 更快",
    "details": ["标准配送：...", "Prime 会员配送：..."],
    "note":    null
  },
  "images": ["url1", "url2", ...],
  "aplus":  ["url1", ...]  或 null,
  "specs": [
    {"name": "部门", "value": "女装"},
    ...
  ]
}
```

### 字段生成原则

- **🔴 评分 KPI 严禁手写星级 HTML**：`"type": "rating"` 时 `"value"` 必须为 `""`，星级由脚本根据 `rating.score` 自动生成（含半星）。手写 `★★★★★` 会导致星级与评分不一致
- **KPI 的 `value`** 可包含 HTML（如库存状态 `<span style="color:#059669;">有货</span>`），除此之外优先用纯文本
- **`bullets[].en`** 🔴 **原文原样照录，不做任何删减、改写、摘要、过滤**。采集到几条就是几条，采集到什么内容就是什么内容
- **`bullets[].zh`** 直译为主、本地化为辅，保留尺寸/品牌/专有名词原文
- **`specs`** 只保留有实际信息的行，过滤 ASIN/评分/BSR 等已在前文展示的冗余行
- **所有可空字段**传 `null`（不是空字符串），脚本自动跳过
- **🔴 变体维度必须分组**：每个变体类型（Color / Size / Flavor / Capacity 等）必须是 `dimensions` 数组中独立的一项，各渲染为独立的一行。禁止把所有选项合并到一个 dimension——反例：`{"name":"选项","options":["Black","XS","S","M","L"]}`
- **变体维度拆分规则**：从 `variant_dimensions` 读维度名（如 `["Color: Khaki", "Size: X-Large"]`），从 `variant_selected` 取当前选中值，颜色选项从 `variant_options` 去重 + `variant_thumbnails` 对应缩略图，尺码/口味等文本选项从 `variant_options_text` 获取

---

## 步骤 3 — 脚本注入

```bash
cd linkfoxagent-v2/linkfox-plugin-web-data-crawler
python scripts/generate_report.py <clean_data.json> [output.html]
```

脚本做的事：
1. 读 `templates/amazon-report.html`
2. 替换 `{{TITLE}}` / `{{SUBTITLE}}` / `{{META}}` 占位符
3. 注入 `report-header` + 各 `content-section` + `report-footer`
4. 注入 `drawDonut(...)` 图表初始化 JS
5. 写入目标文件

脚本不做的事：
- 不解析原始爬虫 JSON
- 不翻译文本
- 不分类规格
- 不计算折扣
- 不验证数据合理性

---

## 步骤 4 — 验证

报告生成后，AI 应检查以下要点：

- [ ] `kpi-grid` 包含 4 张卡片（售价/评分/销量/库存）
- [ ] `产品概览与卖点` 含主图 + 描述 + Badge + 基本信息
- [ ] `产品卖点` 表格每行原始文本/中文都有内容
- [ ] `价格与可购变体` 含价格 + Badge + 变体 Pill
- [ ] `评分与口碑分析` 含大数字评分 + 环形图 + 5 行星级进度条
- [ ] AI 摘要存在（`review_summary_text` 非空时）
- [ ] 评价话题标签存在（`review_aspects` 非空时）
- [ ] `物流配送` 含配送方式 + 时效
- [ ] `产品图片` 含灯箱交互（`data-full` 属性）
- [ ] A+ 内容存在（`aplus_images` 非空时）
- [ ] `产品规格` 表格无冗余行（ASIN/评分不重复出现）
- [ ] 环形图 5 个百分比之和 = 100%

---

## 调用示例

完整端到端流程：

```
# Step 1: 采集
$ python scripts/run_crawl.py scrape --site amazon-us \
    --url https://www.amazon.com/dp/B0FN47G8RJ
→ saved: linkfox/.../linkfox-plugin-web-data-crawler-<ts>.json

# Step 2: AI 分析（人工/AI 完成）
→ 产出: /tmp/clean-data.json

# Step 3: 生成报告
$ python scripts/generate_report.py /tmp/clean-data.json report.html
→ saved: report.html (33 KB)

# Step 4: AI 验证
→ 16 checks passed
```
