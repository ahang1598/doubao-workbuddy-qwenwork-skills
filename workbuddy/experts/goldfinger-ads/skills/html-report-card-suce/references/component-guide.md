# 组件手册（11 个组件）

每个组件给一段说明 + 一段可复制的代码片段。视觉基调见 `design-rules.md` 规则 0（腾讯蓝体系）。

---

## 1. 版头 Banner（顶部品牌区，必填）

```html
<div class="banner">
  <img class="brand-logo" src="{{BRAND_LOGO}}" alt="金手指">
  <div class="brand-row">
    <p class="brand-tag">金手指<span class="sep">·</span>素材经理</p>
  </div>
  <h1 class="title">{产出物名称}</h1>
  <p class="subtitle">{一句话副标题：面向对象 · 关键参数}</p>
  <div class="meta">
    <span><i class="bi bi-calendar3"></i>{日期}</span>
    <span><i class="bi bi-flag"></i>{场景/阶段}</span>
    <span><i class="bi bi-hourglass-split"></i>{周期/范围}</span>
  </div>
</div>
```

**规则**：腾讯蓝渐变版头承载 —— **品牌行（左上、同一行左对齐：[logo] + 金手指 · 素材经理）→ title（产出物名）→ subtitle（简短说明）→ meta（facts：日期/阶段/周期）**。
- logo 放**品牌行最左、与品牌角色文字同行、白色圆角方块托住、不反白**（CSS 用 flex+gap 已定位，直接照抄）；brand-tag 整段写死不许改（详见规则 14/16）。
- meta 图标是版头元素；**不加紫色 doc-type 文档类型胶囊**（已废）。

**参数示例**：
- title=「素材策略 · 踏雪香薰」→ subtitle=「面向：首次投放商家 · 总预算 3 万 · 30 天」
- title=「金手指广告投放系统 · 素材策略」→ subtitle=「微信朋友圈 · 面向不会投广告的中小老板 · 引导注册试用」

---

## 2. Section 章节（骨架）

```html
<section>
  <h2 class="section-title"><span class="idx">01</span>章节标题<span class="sec-note">可选摘要</span></h2>
  <p class="lead">这节最该先知道的那句话（不加前缀；没有增量信息就省略整行）。</p>
  <!-- 内容区：任选下面 3-11 号组件 -->
</section>
```

- 序号 `.idx` 是**深灰方块**（白字），标题简短（≤10 字）。
- `.sec-note`（右上浅灰胶囊，可选）：一句话摘要 / 数量标注，如「6 条 · 首投」「全部官方口径」；没增量信息就删。
- `.lead` ≤60 字，**不加固定前缀**（禁「结论：」），且**只在有增量信息时才加**（详见 design-rules.md 规则 2、3c）。

---

## 3. 数据表格 `.data-table`（通用多列）

```html
<table class="data-table">
  <thead>
    <tr>
      <th style="width:130px;">列1</th>
      <th>列2</th>
      <th style="width:90px;">结论</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>行标题</strong></td>
      <td>说明内容...</td>
      <td><span class="pill pill-recommend">推荐</span></td>
    </tr>
  </tbody>
</table>
```

---

## 4. KV 型两列表格（字段名 + 一句话内容）

用于"字段 + 一句话"结构，如项目定位卡、需求六要素、产能匹配。

```html
<table class="data-table">
  <thead>
    <tr>
      <th style="width:130px;">重点维度</th>
      <th>定位建议</th>
    </tr>
  </thead>
  <tbody>
    <tr><td class="kv-key">人设一句话</td><td>...</td></tr>
    <tr><td class="kv-key">目标受众</td><td>...</td></tr>
  </tbody>
</table>
```

**表头搭配备选**：
- 定位类：`重点维度 / 定位建议`
- Brief 类：`Brief 要素 / 品牌方要求`
- 评估类：`评估维度 / 现状`
- 产能类：`产能维度 / 说明`
- 报价类：`报价档位 / 参考区间`

---

## 5. 标签 `.pill`（表格内嵌，半透明浅底）

```html
<span class="pill pill-recommend">推荐</span>      <!-- 蓝浅底蓝字，强推 -->
<span class="pill pill-brand">备选</span>           <!-- 蓝浅底蓝字，中性正向 -->
<span class="pill pill-ok">可接</span>              <!-- 绿浅底绿字 -->
<span class="pill pill-warn">待确认</span>          <!-- 琥珀浅底琥珀字 -->
<span class="pill pill-danger">拒绝</span>          <!-- 红浅底红字，谨慎使用 -->
<span class="pill pill-gray">仅单一来源</span>      <!-- 灰浅底灰字，中性 -->
```

**用途**：结论列、评级列、规模量级、状态标记。**保留业务语义、半透明浅底皮肤**（规则 0）。
- 状态三色示例（业务语义随内容而定）：绿=正向/达标 · 灰=单一/中性 · 琥珀=待确认。
- 放在表格右对齐列时，给该 `<td>` 加 `style="text-align:right;"`。

---

## 6. 时间轴 `.timeline`

```html
<div class="timeline">
  <div class="tl-item">
    <div class="tl-head"><span class="week">Week 1</span>阶段主题</div>
    <div class="tl-goal"><strong>目标：</strong>xxx</div>
    <ul class="tl-list">
      <li>动作 1</li>
      <li>动作 2</li>
    </ul>
  </div>
  <!-- 更多 tl-item... -->
</div>
```

**徽章文字备选**：`Week 1`、`Day 1-7`、`阶段 1`、`Q1`、`第一步`。

---

## 7. 提示卡 `.callout`（浅底 + 左侧竖条，2 色）

```html
<div class="callout">
  <strong class="title">建议：</strong>正向/中性说明——建议、核心主张、复用逻辑、口径说明、方案确认。
</div>
<div class="callout callout-warn">
  <strong class="title">风险提示：</strong>雷区/红线/风险提示——禁止、最忌、衰减、合规雷。
</div>
```

**只 2 色**（详细触发词见 `design-rules.md` 规则 3）：
- **蓝**（`.callout` 默认，浅蓝底 + 蓝竖条）：中性 / 正向 / 说明。触发词：建议、核心主张、一句话目标、说明、口径、补充、备注、已确认、可复用、推荐
- **琥珀**（`.callout callout-warn`，浅琥珀底 + 琥珀竖条）：雷区 / 红线 / 风险。触发词：禁止、最忌、红线、风险、衰减、雷、不可、一票否决

**同 section 混排**：允许同色多条，禁止蓝黄混排。teal/紫/灰 callout 已废。引用原话请用组件 10 的 `.quote`，不要拿 callout 凑。

---

## 8. 通用清单 `.plain-list`

**两种标准用法**：

### 8a. 简单动作清单（下一步建议、关联专家）

```html
<ul class="plain-list">
  <li>动作 1</li>
  <li>动作 2 → 可找 <strong>{角色代号}（{角色名}）</strong></li>
  <li>动作 3</li>
</ul>
```

### 8b. 「标签：描述」清单（分类说明、要点列举）—— **优先于 2 列表格**

```html
<ul class="plain-list">
  <li><strong>打工人「按点」午餐节奏：</strong>早 C 晚 A / 加班餐 / 凌晨局</li>
  <li><strong>冷门地铁站：</strong>14 号线沿线、龙岗、坪山方向</li>
  <li><strong>双人 100 元「吃到扶墙」组合：</strong>不是单店，是策略</li>
</ul>
```

CSS 已保证左标签深黑加粗、冒号后有 4px 空隙，扫读锚点清晰。

**判定优先级（详见规则 13）**：
- 2 列 + 右侧 ≥ 50% 是自由文本描述 → **一律用 8b，不用 table**
- 只有可对比字段（评分/分级/数值）才用 `data-table`

**风险类多点写法**（规则 12 最新版：**≥ 2 条风险并列一律裸 `plain-list`，不套 callout**）：
```html
<h2 class="section-title"><span class="idx">04</span>合规红线</h2>
<ul class="plain-list">
  <li><strong>标题：</strong>禁用绝对化用语</li>
  <li><strong>合作项目：</strong>必须走官方平台报备</li>
  <li><strong>导流：</strong>不放联系方式</li>
</ul>
```
- 前缀词（标题/合作项目/导流）用 `<strong>` 加粗黑字，**不加红/黄字色**——靠章节标题（"合规红线"）表达风险语义
- 仅当**只有孤立 1 条警示**时才用 `<div class="callout callout-warn">`；≥ 2 条一律走上面这种裸列表

---

## 9. 决策分支 `.plain-list` + `.tag-*`（If-then 枚举）

**用途**：条件枚举 / 决策裁决 / If-then 结构（"若 A → 可接 / 若 B → 谨慎 / 若 C → 不接"）。**禁止用 3 条并列 callout 承载**（见规则 15）。

```html
<ul class="plain-list">
  <li><strong>若两点都谈成：</strong><span class="tag-ok">可接 ✓</span>品牌方产品与你账号定位（平价基础款）高度匹配；报价 6k 在你当前粉丝层级属于合理偏上。</li>
  <li><strong>若只谈成内容框架、对赌保留：</strong><span class="tag-warn">谨慎接</span>可以接，但要在合同里把"对赌扣款"改成"补内容"而非"扣现金"，最坏情况是免费再产出 1 篇。</li>
  <li><strong>若对赌坚持不改：</strong><span class="tag-bad">不建议接</span>点赞对赌不合理是行业共识，坚持这条的品牌方通常后续沟通也会有麻烦。</li>
</ul>
```

**三档字色**（只染字色、不加底色）：

| CSS 类 | 字色 | 触发词 |
|---|---|---|
| `.tag-ok` | 绿 | 可接 / 推荐 / YES / 通过 / 达标 |
| `.tag-warn` | 橙 | 谨慎接 / 有条件 / 观望 / 待定 |
| `.tag-bad` | 红 | 不建议接 / 不推荐 / NO / 淘汰 |

**结构约定**：`<strong>若条件：</strong> + <span class="tag-*">结果词</span> + 说明文字`。

**典型场景**：
- 需求评估类：接 / 不接裁决、档位裁决
- 备选筛选类：该做 / 观望 / 淘汰
- 阿视（视觉规划）：可复用 / 需改造 / 不适配
- 任何专家的"3 档判定"场景，都走这个组件

**不做**：
- ❌ 用 3 条并列 callout（1 蓝 + 2 黄 / 3 黄）承载 3 档决策
- ❌ 用 2 列表格（条件｜结论）——右侧长文本会撑爆表格，违反规则 13
- ❌ 给 `.tag-*` 加底色/胶囊/边框——底色噪音正是要避免的（这是它与 `.pill-*` 的关键区别）


---

## 10. 原话块 `.quote`（引用原话）

引用**用户需求原文 / 腾讯广告官方口径原文**时用它，不要拿 callout 凑：

```html
<div class="quote">
  <div class="q-text">被引用的原话，前后自动带「」引号</div>
  <cite>来源说明（如：用户需求原文 / 腾讯广告官方口径）</cite>
</div>
```
- 浅底 + 左侧蓝竖线，`.q-text` 前后由 CSS 自动补「」；`<cite>` 自动带"— "前缀。
- 与 callout 分工：callout 是"我要提醒你"，quote 是"这是谁说的原话"（详见规则 3b）。

---

## 10b. 素材卡 `.material-card`（创意规划专用：左文右图）

素材策略里推荐每类创意时用它——左侧文字（类型名 + 优先级标签 + 数量尺寸 + 说明），右侧内嵌该类型的样式示例图：

```html
<div class="material-card">
  <div class="mc-main">
    <div class="mc-head">
      <span class="mc-type">模拟朋友圈</span>
      <span class="mc-spec"><span class="lv">优先级：主推</span><span class="dim">· 10张 · 竖 9:16 1080×1920</span></span>
    </div>
    <p class="mc-desc">一句话讲清这类素材怎么给用户传信息、为什么选它。</p>
  </div>
  <div class="mc-thumb"><img src="assets/case_samples/模拟朋友圈.webp" alt="模拟朋友圈 样式示例"></div>
</div>
```
- `.mc-type` 用官方 13 类创意原名；`.mc-spec .lv` 蓝色优先级、`.dim` 灰色数量尺寸。
- 右侧 `.mc-thumb` 内嵌样式示例图，`object-fit:contain` 防裁切；打印前 `inline_assets.js` 转 base64 防丢图。
- 移动端自动上下堆叠。

---

## 11. 页脚三行 `.footer`（必填）

```html
<div class="footer">
  <p class="f-line"><strong>给谁用：</strong>面向对象</p>
  <p class="f-line"><strong>怎么读：</strong>阅读指引</p>
  <p class="f-line"><strong>有效期：</strong>时效说明</p>
</div>
```
放在 `.body` 之后、`.disclaimer` 之前。三行固定「给谁用 / 怎么读 / 有效期」，灰阶小字。

---

## 底部 disclaimer（可选）

```html
<div class="disclaimer">
  金手指 · 素材经理出品｜本策略基于用户提供的输入与腾讯广告官方口径整理定制；实际投放表现受多因素影响，量化数据仅作参考，具体以投放后台为准。
</div>
```

放在 `.footer` 之后、`.container` 之内。**行业中立、不承诺流量数字** 是全队铁律。
