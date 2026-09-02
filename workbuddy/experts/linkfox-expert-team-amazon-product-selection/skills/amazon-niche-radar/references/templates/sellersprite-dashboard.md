# 卖家精灵看板模式 — HTML 片段模板

当用户要求"还原卖家精灵看板"或"三列数据总览面板"时，使用本模板生成 HTML 片段。

## 数据源

全部字段直接取自 `sellersprite-market-statistics` API 返回值，无派生计算。

## 布局结构

三列并排（`comparison-grid cols-3`），每列一个 `comparison-card` 内嵌 `data-table`：

| 列 | 标题 | 数据来源 | 字段数 |
|----|------|---------|--------|
| 左列 | 全部样本 | API 顶层字段 | 13 |
| 中列 | 头部商品（前 10） | API `hl*` 前缀字段 | 8 |
| 右列 | 新品（6个月内上架）+ 市场时间 | API `new*` 前缀字段 + `firstShelfDate`/`lastShelfDate` | 11 |

纯 API 直取值，无派生计算，无图表。

## 字段映射表

### 左列：全部样本

| 看板显示名 | API 字段 | 显示格式 |
|-----------|----------|---------|
| 样本商品数 | `products` | 整数 |
| 样本品牌数 / 卖家数 | `brands` / `sellers` | `43 / 48` |
| 平均 BSR | `avgBsr` | 千分位整数 |
| 近30天均销量 | `avgUnits` | 整数 |
| 近30天均销售额 | `avgRevenue` | `$` + 千分位 |
| 平均价格 | `avgPrice` | `$` + 两位小数 |
| 近30天评分平均增长数 | `avgRatingsCv` | 整数 |
| 平均评分数 | `avgRatings` | 千分位整数 |
| 平均星级 | `avgRating` | 一位小数 |
| 平均卖家数 | `avgSellers` | 一位小数 |
| 平均重量 | `avgWeight` / `baseAvgWeight` | `0.31 lbs / 140 g` |
| 平均体积 | `avgVolume` / `baseAvgVolume` | `14.74 in³ / 242 cm³` |
| 平均毛利率 | `avgProfit` | 百分比加粗 |

### 中列：头部商品（前 10）

| 看板显示名 | API 字段 | 显示格式 |
|-----------|----------|---------|
| 前10商品样本总数 | `hlProducts` | 整数 |
| 前10商品 BSR 均值 | `hlAvgBsr` | 千分位整数 |
| 前10商品近30天均销量 | `hlAvgUnits` | 整数加粗 |
| 前10商品近30天均销售额 | `hlAvgRevenue` | `$` + 千分位加粗 |
| 前10商品平均价格 | `hlAvgPrice` | `$` + 两位小数 |
| 前10商品近30天评分增长 | `hlAvgRatingsCv` | 整数 |
| 前10商品平均评分数 | `hlAvgRatings` | 千分位整数 |
| 前10商品平均星级 | `hlAvgRating` | 一位小数 |

### 右列：新品 + 市场时间

| 看板显示名 | API 字段 | 显示格式 |
|-----------|----------|---------|
| 新品数量 | `newProducts` | 整数 |
| 新品占比 | `newProductProportion` | 百分比加粗 |
| 新品评分数（最高） | `maxNewRatings` | 千分位整数 |
| 新品评分数（平均） | `newAvgRatings` | 整数 |
| 新品评分数（最低） | `minNewRatings` | 整数 |
| 新品平均价格 | `newAvgPrice` | `$` + 两位小数 |
| 新品平均星级 | `newAvgRating` | 一位小数 |
| 新品近30天均销量 | `newAvgUnits` | 整数 |
| 新品近30天均销售额 | `newAvgRevenue` | `$` + 千分位 |
| 商品首次上架时间 | `firstShelfDate` | `YYYY-MM-DD` |
| 商品最新上架时间 | `lastShelfDate` | `YYYY-MM-DD` |

### ECharts 对比图

本模板不包含图表，纯数据表格直取。如需可视化对比，可在报告生成时追加 ECharts 图表区块。

## HTML 片段模板

以下片段中 `{变量名}` 为占位符，生成时从 API 返回 JSON 中取值替换。

```html
<!-- CONTENT_START -->
<div class="report-header">
  <h1>{类目名称} 市场统计看板</h1>
  <div class="report-subtitle">{nodeLabelPath} · {nodeLabelPathLocale}</div>
  <div class="report-meta">数据快照: {date} · 数据源: sellersprite-market-statistics · 统计范围: 近30天 · 商品总数: {totalProducts} · 样本: {products}</div>
</div>

<section class="content-section">
  <h2>数据总览面板</h2>

  <div class="comparison-grid cols-3">
    <div class="comparison-card">
      <div class="card-title">全部样本</div>
      <div class="data-table-wrapper">
        <table class="data-table">
          <thead><tr><th>指标</th><th class="num">全部样本 ({products})</th></tr></thead>
          <tbody>
            <tr><td>样本商品数</td><td class="num">{products}</td></tr>
            <tr><td>样本品牌数 / 卖家数</td><td class="num">{brands} / {sellers}</td></tr>
            <tr><td>平均 BSR</td><td class="num">{avgBsr}</td></tr>
            <tr><td>近30天均销量</td><td class="num">{avgUnits}</td></tr>
            <tr><td>近30天均销售额</td><td class="num">${avgRevenue}</td></tr>
            <tr><td>平均价格</td><td class="num">${avgPrice}</td></tr>
            <tr><td>近30天评分平均增长数</td><td class="num">{avgRatingsCv}</td></tr>
            <tr><td>平均评分数</td><td class="num">{avgRatings}</td></tr>
            <tr><td>平均星级</td><td class="num">{avgRating}</td></tr>
            <tr><td>平均卖家数</td><td class="num">{avgSellers}</td></tr>
            <tr><td>平均重量</td><td class="num">{avgWeight} lbs / {baseAvgWeight} g</td></tr>
            <tr><td>平均体积</td><td class="num">{avgVolume} in³ / {baseAvgVolume} cm³</td></tr>
            <tr><td>平均毛利率</td><td class="num"><strong>{avgProfit}%</strong></td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="comparison-card">
      <div class="card-title">头部商品（前 10）</div>
      <div class="data-table-wrapper">
        <table class="data-table">
          <thead><tr><th>指标</th><th class="num">前10商品</th></tr></thead>
          <tbody>
            <tr><td>前10商品样本总数</td><td class="num">{hlProducts}</td></tr>
            <tr><td>前10商品 BSR 均值</td><td class="num">{hlAvgBsr}</td></tr>
            <tr><td>前10商品近30天均销量</td><td class="num"><strong>{hlAvgUnits}</strong></td></tr>
            <tr><td>前10商品近30天均销售额</td><td class="num"><strong>${hlAvgRevenue}</strong></td></tr>
            <tr><td>前10商品平均价格</td><td class="num">${hlAvgPrice}</td></tr>
            <tr><td>前10商品近30天评分增长</td><td class="num">{hlAvgRatingsCv}</td></tr>
            <tr><td>前10商品平均评分数</td><td class="num">{hlAvgRatings}</td></tr>
            <tr><td>前10商品平均星级</td><td class="num">{hlAvgRating}</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="comparison-card">
      <div class="card-title">新品（6个月内上架）+ 市场时间</div>
      <div class="data-table-wrapper">
        <table class="data-table">
          <thead><tr><th>指标</th><th class="num">新品数据</th></tr></thead>
          <tbody>
            <tr><td>新品数量</td><td class="num">{newProducts}</td></tr>
            <tr><td>新品占比</td><td class="num"><strong>{newProductProportion}%</strong></td></tr>
            <tr><td>新品评分数（最高）</td><td class="num">{maxNewRatings}</td></tr>
            <tr><td>新品评分数（平均）</td><td class="num">{newAvgRatings}</td></tr>
            <tr><td>新品评分数（最低）</td><td class="num">{minNewRatings}</td></tr>
            <tr><td>新品平均价格</td><td class="num">${newAvgPrice}</td></tr>
            <tr><td>新品平均星级</td><td class="num">{newAvgRating}</td></tr>
            <tr><td>新品近30天均销量</td><td class="num">{newAvgUnits}</td></tr>
            <tr><td>新品近30天均销售额</td><td class="num">${newAvgRevenue}</td></tr>
            <tr><td>商品首次上架时间</td><td class="num">{firstShelfDate}</td></tr>
            <tr><td>商品最新上架时间</td><td class="num">{lastShelfDate}</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <div class="data-source">
    <span class="ds-label">数据源：</span>
    <span class="ds-tool">sellersprite-market-statistics</span>
    <span class="ds-time">· {date}</span>
    <div class="ds-computed">
      <span class="ds-label">计算指标：</span>
      无派生计算，全部字段直接取自 API 返回值
    </div>
  </div>
</section>

<section class="content-section">
  <h2>头部 vs 均值 vs 新品 可视化对比</h2>

  <div class="chart-row cols-2">
    <div class="chart-container"><div id="chart_units" style="width:100%;height:300px;"></div></div>
    <div class="chart-container"><div id="chart_revenue" style="width:100%;height:300px;"></div></div>
  </div>
  <div class="chart-row cols-2">
    <div class="chart-container"><div id="chart_price" style="width:100%;height:300px;"></div></div>
    <div class="chart-container"><div id="chart_reviews" style="width:100%;height:300px;"></div></div>
  </div>

  <div class="data-source">
    <span class="ds-label">数据源：</span>
    <span class="ds-tool">sellersprite-market-statistics</span>
    <span class="ds-time">· {date}</span>
  </div>
</section>

<div class="report-footer">报告由 LinkFox AI 生成 · 数据截止 {date} · 数据源: sellersprite-market-statistics</div>
<!-- CONTENT_END -->
```

## 使用方式

1. 从 S3.2 的 `sellersprite-market-statistics` 返回 JSON 中取 `data[0]` 的全部字段
2. 将字段值填入上方模板的 `{变量名}` 占位符
3. `totalProducts` 字段不在 market-statistics 返回中，从 `amazon-category-lookup` 或 `sellersprite-market-research` 获取
4. `date` 取数据快照当天日期（YYYY-MM-DD）
5. 写入 `.fragment.html` 文件后调 `inject_report.py` 注入模板
