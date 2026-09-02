---
name: amazon-competitor-monitor
description: 全面亚马逊竞品动态监控与异常检测，含数据清洗与可视化交付。当用户提到竞品监控、竞品追踪、竞品动态、ASIN监控、BSR价格评论销量变化、竞品异常、周度竞品报告、仪表盘、可视化、Excel图表、PPT周报、HTML仪表盘、ECharts、多图联动、数据清洗、Keepa SIF 卖家精灵集成监控时触发。支持输入ASIN列表自动采集、清洗、检测异常并输出异常清单、对比报告及 Excel/PPT/交互HTML可视化。
---

# Amazon Competitor Monitor（最终版）

面向中国亚马逊卖家的竞品动态监控技能。整合 Linkfox 最小工具集，完成采集 → 清洗 → 异常检测 → 文字报告 → 可视化交付的完整闭环。

**用户偏好（贯穿始终）**：
- 全部中文输出
- 异常描述风格贴近 Linkfox 截图（简洁、前后对比、可行动建议）
- 去重后只保留 5 个核心工具，避免冗余调用
- 可视化优先交互 HTML（ECharts + 深色主题 + 多图联动），其次 Excel / PPT
- 异常检测前必须做数据清洗，降低误报

## 核心工具集（5 个历史/快照源 + 2 个实时源）

### 历史与快照数据（5 个核心）

1. **linkfox-keepa-product-series** — 历史价格、BSR、销量估算、评论数趋势、库存
2. **linkfox-amazon-product-detail** — 当前 Listing 快照（标题、图片、五点、A+、价格、BSR、评分、变体）
3. **linkfox-sif-asin-keywords** — 流量关键词 + 自然/广告排名 + 流量占比
4. **linkfox-sellersprite-competitor-lookup** — 竞品发现与监控池扩展
5. **linkfox-amazon-reviews-list** — 评论内容与星级分布

### 实时前台数据（2 个补充，按需触发）

6. **linkfox-amazon-search** — 模拟亚马逊前台关键词搜索，获取实时自然排名位、广告位（SP/SB）、搜索页价格、徽标（Amazon's Choice / Best Seller）。用于：Step 1 按关键词发现竞品、Step 2 验证 SIF 排名延迟、Step 4 检测关键词排名异常时做前台实况核对
7. **linkfox-amazon-search-by-image** — 以商品图片搜亚马逊，跨 8 站点找视觉相似竞品。用于：Step 1 用户只有图片无 ASIN 时扩展竞品池

> 需配置 `LINKFOXAGENT_API_KEY` 且已安装对应 Linkfox skills。

## 完整工作流

```
输入 ASIN/关键词
    ↓
1. 初始化监控对象（扩展竞品池）
    ↓
1.5. 积分消耗预估与预警（必做，见 references/credit-alert-rules.md）
    ↓
2. 数据采集（每日轻量 / 每周深度）
    ↓
3. 数据清洗（必做，见 references/data-cleaning.md）
    ↓
4. 异常检测（references/anomaly-rules.md）
    ↓
5. 文字报告（references/report-template.md）
    ↓
6. 可视化（按需：HTML / Excel / PPT，见 references/visualization-guide.md）
    ↓
7. 快照持久化（供下次增量对比）
```

### 1. 初始化监控对象
- 接收 ASIN 列表 / 关键词 / 品牌 / 商品图片
- 仅关键词或品牌时，先调 `linkfox-sellersprite-competitor-lookup` 扩展（Top 10–20）
- 有商品图片无 ASIN 时，调 `linkfox-amazon-search-by-image` 以图搜图找相似竞品
- 需要前台实况验证时，调 `linkfox-amazon-search` 按关键词搜索，获取实时排名与广告位
- 默认站点 US，可指定 UK/DE/JP 等
- 单次建议 ≤20 个 ASIN

### 1.5. 积分消耗预估与预警（强制）

在初始化完成、已知最终 ASIN 列表与监控模式后、正式采集前执行。详见 `references/credit-alert-rules.md`。

- 按公式计算预计调用次数（每日轻量 = ASIN × 2；每周深度 = ASIN × 4；竞品扩展 +1）
- 分级预警：🟢 ≤20 / 🟡 21–50 / 🟠 51–100 / 🔴 >100
- 🟡 及以上必须向用户展示预估明细表并等待确认后再执行
- 提供优化建议（减 ASIN / 改轻量 / 跳评论 / 跳 SIF / 分批）
- 创建定时任务时需换算日/周累计消耗

### 2. 数据采集
**每日轻量**：Keepa series（近 7–30 天）+ product-detail → 算变化率
**每周深度**：上述 + SIF asin-keywords + reviews-list
**实时补充**（按需）：`linkfox-amazon-search` 按关键词抓前台搜索页（排名位、广告位、徽标），弥补 SIF 数据延迟

### 3. 数据清洗（强制）
在异常检测前执行，详见 `references/data-cleaning.md`。核心规则：
- 时间窗口对齐
- 评分数大降但评分几乎不变 → 降级为「疑似评论清理/变体合并」
- 销量归零但 BSR 仍在且非断货 → 标记「疑似数据延迟」
- 价格用 Buy Box，并单独记录 Deal 状态变化
- 极值过滤（价格、BSR、评分合理区间）
- 同一指标前后对比禁止跨工具混用

### 4. 异常检测
规则见 `references/anomaly-rules.md`。输出优先级：高 / 中 / 低。

高优先级典型场景：
- 评分数 ±30% 或绝对变化大，且评分同步变化
- 价格 ±5% 或 Deal 状态切换
- 销量骤降 50%+ 或归零（已排除断货/延迟）
- BSR 恶化 ≥20%

### 5. 文字报告
始终输出中文 Markdown：
1. 异常清单（「检测到 X 项异常」风格）
2. 核心指标对比表
3. 关键词流量摘要（深度时）
4. 行动建议（立即 / 观察 / 策略参考）

模板：`references/report-template.md`。

### 6. 可视化交付

| 格式 | 触发词 | 引擎 / 方式 | 关键能力 |
|------|--------|-------------|----------|
| **交互 HTML** | 仪表盘、可视化、HTML、交互、深色 | **ECharts 5** 单文件 | 深色主题、优先级筛选、搜索、价格/BSR/评分数**多图联动**（axisPointer + dataZoom + 图例同步）、localStorage 安全读写 |
| **CSV 数据看板** | CSV、表格、数据导出 | Python csv 模块 | 多表 CSV（异常清单、指标对比、趋势数据、关键词），可直接导入 Excel/Sheets |
| **PPT 周报** | PPT、周报、汇报、演示 | `ppt-maker` skill | HTML 演示稿，7 页：封面→异常→指标→价格图→评论销量→行动建议→结尾 |

**默认策略**：
- 只说「监控/异常」→ 仅 Markdown
- 说「可视化/仪表盘」→ 优先生成 **ECharts HTML**
- 说「CSV」→ 生成多表 CSV
- 说「PPT/周报」→ 调 `ppt-maker` 生成 HTML 演示稿
- 说「全部」→ 三种都生成

颜色语义（三套交付物统一）：
- 高优先级 / 不利 → 红 `#E63946`
- 中 / 需关注 → 橙 `#F4A261`
- 低 / 观察 → 黄 `#E9C46A`
- 有利 → 绿 `#2A9D8F`
- 主色 → 深蓝 `#1B3A4B` + `#2E86AB`

HTML 实现要点（最终版）：
- ECharts 5 CDN，`echarts.connect` 连接价格/BSR/评分数三张折线
- dataZoom（inside + slider）三图同步
- 图例 `legendselectchanged` 跨图同步显隐
- 深色主题：`data-theme="dark"` + `echarts.init(dom, 'dark')`
- localStorage 用 try/catch 安全封装（兼容沙箱 iframe）
- 评分数图用 markPoint 标最低点；销量柱用圆角

完整字段映射与生成步骤见 `references/visualization-guide.md`。

### 7. 状态持久化
每次运行保存快照 JSON（ASIN → 时间戳 + 关键指标 + 历史序列），供下次增量对比与图表数据区使用。

## 注意事项
- Keepa series 作历史主源，product-detail 作当前快照
- SIF 单 ASIN 循环调用
- 异常描述保持「前后数值 + 百分比 + 可能原因 + 建议」结构
- 可视化数据必须与文字报告一致，先检测再出图
- 输出文件统一放会话目录 `linkfox/<YYYY-MM-DD>/<session>/` 下的 `data/`（数据）与 `reports/`（报告）

## 触发示例
- 「监控这几个竞品 ASIN」
- 「跑本周竞品异常检测」
- 「做可视化仪表盘」
- 「出 Excel 仪表盘 / PPT 周报」
- 「生成带多图联动的 HTML 仪表盘」
- 「清洗数据后再检测异常」
- 「把这次结果全部可视化」
