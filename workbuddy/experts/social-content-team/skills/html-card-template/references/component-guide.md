# 组件手册（9 个组件）

每个组件给一段说明 + 一段可复制的代码片段。

---

## 1. Banner（顶部品牌区，必填）

```html
<div class="banner">
  <h1 class="title">{产出物名称}</h1>
  <p class="subtitle">{一句话副标题：面向对象 · 关键参数}</p>
  <div class="meta">
    <span><i class="bi bi-calendar3"></i>{日期}</span>
    <span><i class="bi bi-flag"></i>{场景/阶段}</span>
    <span><i class="bi bi-hourglass-split"></i>{周期/范围}</span>
  </div>
</div>
```

**规则**：Banner 只承载 3 类信息 —— **title（产出物名）→ subtitle（简短说明）→ meta（日期/阶段/周期）**。品牌归属（营销通 · XXX）**放页脚 disclaimer**，不进 banner。禁止再加"专家名字胶囊""版本号""水印小标签"等杂物。

**参数示例**：
- 起号规划师产出：title=「账号 0→1 规划方案」→ subtitle=「面向：城市白领 · 目标平台：小红书 · 每周产能 3-4 小时」
- 爆款分析师产出：title=「爆款拆解报告」→ subtitle=「样本：@xxx 12 万赞图文 · 拆解维度：10 维方法论」
- 内容变现顾问产出：title=「商单 Brief 评估」→ subtitle=「品牌：xxx · 合作类型：图文单条 · 报价区间：5k-10k」

---

## 2. Section 章节（骨架）

```html
<section>
  <h2 class="section-title"><span class="idx">01</span>章节标题</h2>
  <p class="lead">这节最该先知道的那句话（不加前缀；没有增量信息就省略整行）。</p>
  <!-- 内容区：任选下面 3-8 号组件 -->
</section>
```

序号连续（01、02、...），标题简短（≤10 字），`.lead` ≤60 字。**注意**：`.lead` **不加固定前缀**（禁「结论：」「小结：」），且**只在有增量信息时才加**——纯罗列/陈述/流程章节直接省略 lead 上内容（详见 design-rules.md 规则 2）。

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

用于"字段 + 一句话"结构，如账号定位卡、Brief 六要素、产能匹配。

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

## 5. 徽章 `.pill`（表格内嵌）

```html
<span class="pill pill-recommend">推荐</span>      <!-- 蓝底白字，强推 -->
<span class="pill pill-brand">备选</span>           <!-- 蓝底蓝字，中性正向 -->
<span class="pill pill-ok">可接</span>              <!-- 绿底绿字 -->
<span class="pill pill-warn">不建议</span>          <!-- 橙底橙字 -->
<span class="pill pill-danger">拒绝</span>          <!-- 红底红字，谨慎使用 -->
```

**用途**：结论列、评级列、粉丝量级、状态标记。

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

## 7. 提示条 `.callout`（2 色：蓝｜黄）

```html
<div class="callout">
  <strong class="title">建议：</strong>正向/中性说明——建议、复用逻辑、口径说明、方案确认。
</div>
<div class="callout callout-warn">
  <strong class="title">风险提示：</strong>雷区/红线/风险提示——禁止、最忌、衰减、合规雷。
</div>
```

**色板对应**（详细触发词映射见 `design-rules.md` 规则 3）：
- **蓝**（`.callout` 默认，不加修饰类）：中性 / 正向 / 说明。触发词：建议、说明、口径、补充、备注、已确认、可复用、通过、匹配、推荐
- **黄**（`.callout callout-warn`）：雷区 / 红线 / 风险。触发词：禁止、最忌、红线、风险、衰减、雷、不可、一票否决

**同 section 混排**：允许同色多条，禁止蓝黄混排。绿色（`callout-ok`）已废弃。

---

## 8. 通用清单 `.plain-list`

**两种标准用法**：

### 8a. 简单动作清单（下一步建议、关联专家）

```html
<ul class="plain-list">
  <li>动作 1</li>
  <li>动作 2 → 可找 <strong>包火（爆款分析师）</strong></li>
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
  <li><strong>商单：</strong>必须走蒲公英报备</li>
  <li><strong>导流：</strong>不放联系方式</li>
</ul>
```
- 前缀词（标题/商单/导流）用 `<strong>` 加粗黑字，**不加红/黄字色**——靠章节标题（"合规红线"）表达风险语义
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
- 卞现（商单 Brief 评估）：接 / 不接裁决、报价档位裁决
- 郝选题（内容选题）：这题该做 / 观望 / 淘汰
- 阿视（视觉规划）：可复用 / 需改造 / 不适配
- 任何专家的"3 档判定"场景，都走这个组件

**不做**：
- ❌ 用 3 条并列 callout（1 蓝 + 2 黄 / 3 黄）承载 3 档决策
- ❌ 用 2 列表格（条件｜结论）——右侧长文本会撑爆表格，违反规则 13
- ❌ 给 `.tag-*` 加底色/胶囊/边框——底色噪音正是要避免的（这是它与 `.pill-*` 的关键区别）


---

## 底部 disclaimer（可选）

```html
<div class="disclaimer">
  本方案基于用户提供的输入定制，实际效果受平台算法、执行度等多因素影响，不承诺具体流量数字。
</div>
```

放在 `.body` 之外、`.container` 之内。**行业中立、不承诺流量数字** 是全队铁律。
