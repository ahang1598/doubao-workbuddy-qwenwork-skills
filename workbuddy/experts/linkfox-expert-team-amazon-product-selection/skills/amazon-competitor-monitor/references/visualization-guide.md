# 可视化生成指引（最终版）

采集并清洗、完成异常检测后，按用户意图生成一种或多种交付物。

参考成品（可复制结构后替换数据）：
- 竞品监控仪表盘模板.csv
- 竞品监控周报模板.html（ppt-maker 生成）
- 竞品监控交互仪表盘.html（ECharts 最终版）

## 统一数据 JSON

```json
{
  "period": "2026-07-21 ~ 2026-07-27",
  "site": "US",
  "asins": [{
    "asin": "B0FF399DLL",
    "brand": "CATPICK",
    "price_current": 29.99, "price_prev": 29.99,
    "bsr_main_current": 65000, "bsr_main_prev": 62000,
    "bsr_sub_current": 400, "bsr_sub_prev": 350,
    "reviews_current": 108, "reviews_prev": 1702,
    "sales_current": 800, "sales_prev": 950,
    "rating_current": 4.2, "rating_prev": 4.4,
    "price_history": [], "bsr_history": [], "review_history": [], "sales_history": []
  }],
  "anomalies": [{
    "priority": "高", "asin": "...", "brand": "...",
    "type": "评分数骤降", "desc": "1702→108", "change": "-93.7%",
    "action": "立即核查 Listing 评论来源与变体结构"
  }],
  "keywords": [{
    "asin": "...", "keyword": "...",
    "rank_current": 12, "rank_prev": 8, "ad_rank": 3,
    "traffic_share": 18.5, "search_volume": 12000
  }]
}
```

## 颜色语义（三套统一）

| 含义 | 色值 |
|------|------|
| 高优先级 / 不利 | #E63946 |
| 中 / 需关注 | #F4A261 |
| 低 / 观察 | #E9C46A |
| 有利 | #2A9D8F |
| 主色海军 / 蓝 | #1B3A4B / #2E86AB |

## 一、交互 HTML（默认优先）

- 引擎：Apache ECharts 5（CDN）
- 单文件自包含，输出到会话目录 `linkfox/<YYYY-MM-DD>/<session>/reports/`

必须包含：
1. 顶部 4 统计卡片（监控数、高/中/低优先级）
2. 5 标签：异常清单 / 核心指标 / 趋势图表 / 关键词 / 行动建议
3. 异常表：优先级筛选 + 文本搜索
4. 四图：价格、BSR、评分数（折线）、月销量（柱）
5. 多图联动（仅三张折线）：
   - echarts.connect([price, bsr, review])
   - 共享 dataZoom（inside + slider）
   - axisPointer 时间轴指示器联动
   - legendselectchanged 同步系列显隐
6. 深色主题：data-theme="dark" + echarts.init(dom, isDark ? 'dark' : null)
7. localStorage 安全封装（try/catch），兼容沙箱 iframe
8. 评分数图 markPoint 标最低点；销量柱 borderRadius 圆角
9. window.resize → chart.resize()

选择逻辑：用户说「可视化 / 仪表盘 / HTML / 交互」时优先生成此文件。

## 二、CSV 数据看板

使用 Python csv 模块直接生成（不依赖独立 skill）。多表 CSV 文件：

1. `anomalies.csv` — 异常清单（ASIN、品牌、异常类型、优先级、前后值、变化率、建议动作）
2. `metrics.csv` — 核心指标对比（ASIN、品牌、价格变化、BSR 大类/小类、月销量、评分数、评分、异常标签）
3. `trends.csv` — 趋势数据（ASIN、日期、价格、BSR、评分数、销量）
4. `keywords.csv` — 关键词监控（ASIN、关键词、当前排名、上期排名、变化、广告位、流量占比）

CSV 使用 UTF-8 with BOM 编码，确保 Excel 直接打开不乱码。

## 三、PPT 周报

调用 `ppt-maker` skill 生成 HTML 演示稿。

固定 7 页：
1. 封面（周期、站点、数据源）
2. 异常总览（统计卡片 + 表）
3. 核心指标对比（红橙绿标注）
4. 价格趋势折线
5. 评分数折线 + 月销量柱状
6. 行动建议三栏（立即 / 观察 / 策略）
7. 结尾

## 四、默认选择

```
仅「监控/异常」     → Markdown 文字报告
「可视化/仪表盘」   → ECharts HTML（优先）
「CSV/表格/数据」   → 多表 CSV
「PPT/周报/汇报」   → ppt-maker HTML 演示稿
「全部/三种」       → 全部生成
```

文件统一输出到会话目录 `linkfox/<YYYY-MM-DD>/<session>/reports/`，文件名含「竞品监控」前缀（英文命名：`competitor-monitor-*`）。
