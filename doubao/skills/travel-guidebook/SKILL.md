---
name: travel-guidebook
description: Create beautifully designed travel guidebook PDFs from trip itineraries. End-to-end workflow from deep research to Playwright PDF export, featuring zero AI-generated images, Tabler Icons, inline SVG decorations, and Claude's warm parchment aesthetic. Use this skill whenever the user mentions 路书, 旅行指南, travel guidebook, 行程手册, trip planner, 自驾游攻略, itinerary book, 攻略, 出行指南, 旅行计划, 行程规划, or wants to turn trip notes into a printable guide. Also triggers for multi-day travel planning, route guides, road trip planners, 旅行攻略制作, 旅行PDF, or converting travel research into a professionally designed document.
---

# Travel Guidebook Maker

从调研到成书的一站式旅游路书生成引擎——**零 AI 插图、零 emoji、纯 CDN 引入**。通过 Tabler Icons + 内联 SVG 装饰 + Claude 设计美学，打造有温度、有设计感的旅行指南 PDF。

## 设计哲学

> **Monocle 的编辑品味 + DK 的视觉叙事 + Lonely Planet 的信息深度 + Claude 的温暖美学**

这不是一本冰冷的导航手册，而是一本有温度的旅行伙伴——在羊皮纸般的暖色底上，用衬线体讲述目的地的故事，用图标系统标记功能信息，用装饰元素营造编辑出版感。

**核心理念：排版即设计。** 不依赖 AI 生图或照片，通过字体层级、功能色系统、内联 SVG 装饰、CSS 伪元素，让路书本身就具备设计感。

---

## 总体流程

```
Stage 0 环境准备 → Stage 1 需求确认
→ Stage 2 深度调研 [5 个 explore agent 并行]
→ Stage 3 路线架构
→ Stage 4 内容写作 [专职 general-purpose agent]
→ Stage 5 HTML 交付与检查 → Stage 6 PDF 导出
```

Stage 0 自动检测 Node.js + Playwright 环境；Stage 2 并行调研加速信息收集；Stage 4 专职 agent 在干净上下文中写 HTML 保证一致性；Stage 5 是 HTML 检查点——用户确认满意后再执行 Stage 6 导出 PDF。

---

# Stage 0: 环境准备

> 在路书制作开始前，确保 PDF 导出环境就绪。

按以下顺序逐项检测，任一步骤失败则停止并提示用户：

### 1. Node.js

```bash
node --version
```

- ✅ v18.x 或更高 → 继续
- ❌ 命令不存在 → 停止，提示安装：https://nodejs.org/

### 2. package.json

```bash
ls package.json
```

- ✅ 存在 → 继续
- ❌ 不存在 → `npm init -y`

### 3. Playwright

```bash
node -e "require('playwright')"
```

- ✅ 无报错 → 继续
- ❌ 报错 → `npm install playwright && npx playwright install chromium`

### 4. html2pdf.mjs

已 bundled 在 `scripts/html2pdf.mjs`，Stage 6 时复制到工作目录。

### 5. 高德地图 MCP（可选增强）

尝试调用高德 MCP 工具验证可用性：

```
调用 maps_whether("{目的地城市}")
```

- ✅ 返回天气数据 → 标记 `AMAP_AVAILABLE = true`
- ❌ 工具不存在或报错 → 标记 `AMAP_AVAILABLE = false`

> 高德 MCP 是**增强层**——不可用时路书照常生成，仅精确数据降级为 LLM 估算。

**用户未配置时的提示**（仅提一次，不阻塞流程）：

> "💡 检测到高德地图 MCP 未配置。路书仍会正常生成，但距离/交通/天气数据将使用估算值。如需精确数据，可在 MCP 配置中添加 `@amap/amap-maps-mcp-server`。"

## 环境就绪确认

所有检测通过后输出：

> "✅ 环境准备就绪（Node.js {版本} + Playwright + Chromium{高德可用时加：+ 高德地图 MCP}）。开始制作路书。"

---

# Stage 1: 需求确认

向用户确认以下参数（能从指令推断的不问，推断不了的才问）：

> **收到，准备制作旅游路书。请确认以下信息：**
>
> 1. **路线名称**：「{从指令推断}」，可以吗？
> 2. **旅行类型**：自驾游 / 徒步 / 城市漫游 / 混合？
> 3. **目标读者**：深度文化游 / 轻松休闲游 / 探险挑战游？
> 4. **总天数**：{推断天数}，对吗？
> 5. **个性化信息**：需要在封面或末尾加上个人/团队信息吗？
>
> 直接回复修改项即可，没问题的我直接开始。

**快捷模式**：用户已说明足够信息时，跳过确认直接执行。

**默认值**：旅行类型=自驾游，目标读者=深度文化游，天数=根据路线推断，个性化信息=无。

## 智能路由

需求确认后，根据用户输入决定起始 Stage：

| 用户提供的内容 | 跳转到 | 说明 |
|---------------|--------|------|
| 仅目的地/天数 | Stage 2 | 标准全流程 |
| 已有行程文件（Markdown/文本） | Stage 3 | 读取行程提取架构，跳过调研 |
| 已有行程 + "已确认/不用调研" | Stage 4 | 直接进入写作排版 |
| 已有 HTML 路书 | Stage 5 | 直接进入检查，可修改后导出 PDF |

判断依据：用户是否附带了 `@文件名` 引用、是否明确说"行程已确认"、"不需要调研"等。遇到不确定的情况，默认走完整流程，但主动问一句"需要我做调研还是直接开始写？"。

---

# Stage 2: 深度调研（并行 Sub-Agent）

旅游路书的调研需要同时覆盖**实用信息**和**文化深度**。采用 **并行 explore agent** 加速调研——每个方向一个独立 agent，同时出发，互不阻塞。

## 并行调研架构

```
主 Agent                         explore agent 池（并行）
┌──────────┐                    ┌─────────────────────────┐
│ 构造 5+1  │  ── background ──→│ research-transport       │
│ agent     │  ── background ──→│ research-attractions     │
│ prompt    │  ── background ──→│ research-food            │
│          │  ── background ──→│ research-culture         │
│          │  ── background ──→│ research-practical       │
│          │  ── background ──→│ research-spatial (高德)   │
│          │                    └─────────────────────────┘
│ 等通知    │  ←── 自动通知 ───  (各 agent 完成后)
│ 收集合并   │  ── read_agent ──→ 获取每个 agent 结果
│ 输出报告   │
└──────────┘
```

> `research-spatial` 仅在 `AMAP_AVAILABLE = true` 时启动。不可用时只启 5 个 agent。
```

### Agent 分工

使用 `task` 工具，`agent_type: "explore"`，`mode: "background"`，同时启动 5+1 个 agent：

| Agent 名 | 调研方向 | 搜索关键词示例（中英结合） |
|----------|---------|----------------------|
| `research-transport` | 交通路线 | "{起点}到{终点} 高铁/自驾 时刻 价格", "{destination} transport" |
| `research-attractions` | 核心景点 | "{目的地} 必去景点 门票 开放时间 TOP10", "{destination} attractions" |
| `research-food` | 当地美食 | "{目的地} 特色美食 推荐餐厅 美食街 人均", "{destination} local food" |
| `research-culture` | 文化历史 | "{目的地} 历史 文化 典故 民俗 方言", "{destination} history culture" |
| `research-practical` | 实用信息 | "{目的地} {月份}天气 预算 安全 注意事项", "{destination} travel tips" |

> 自驾游加第 7 个 agent `research-road`（路况、加油站、海拔变化）。

### 高德空间数据 Agent（AMAP_AVAILABLE = true 时）

第 6 个 agent `research-spatial`，专职采集高德地图数据：

```
你是空间数据采集专员。使用高德地图 MCP 工具采集以下数据。

目的地：{目的地}
已知景点列表：{从需求确认中提取的所有景点名称}

## 任务 1: 景点 POI 数据
对每个景点调用 maps_text_search("{景点名}")，提取：
- POI ID, 名称, 完整地址, 经纬度, 评分, 营业时间, 联系电话

## 任务 2: 周边发现
对每个核心景点（每天的主要景点）调用 maps_around_search：
- 关键词="餐厅|小吃", location={景点坐标}, radius=1000 → 附近餐厅 top 5
- 关键词="便利店|药店", location={景点坐标}, radius=500 → 应急设施

## 任务 3: 天气预报
maps_whether("{目的地城市名称或 adcode}")

## 任务 4: 地理编码
对所有地名调用 maps_gep 获取精确坐标，供 Stage 3 路径规划使用

## 输出格式
### 景点 POI 汇总
| 景点 | 地址 | 经纬度 | 评分 | 营业时间 |
|------|------|--------|------|---------|
| ... | ... | ... | ... | ... |

### 周边发现
#### {景点名} 周边
| 名称 | 类型 | 距离 | 评分 |
|------|------|------|------|
| ... | ... | ... | ... |

### 天气预报
| 日期 | 天气 | 温度 | 风力 |
|------|------|------|------|
| ... | ... | ... | ... |
```

> 自驾游加第 6 个 agent `research-road`（路况、加油站、海拔变化）。

### Agent Prompt 模板

每个 agent 的 prompt 遵循以下结构：

```
你是旅游调研专员，负责【{方向}】调研。

## 任务参数
- 目的地：{目的地}
- 出发地：{出发地}
- 日期：{具体日期}
- 天数：{N} 天
- 旅行类型：{自驾/高铁/混合}

## 调研要求
1. 使用 bash 执行 curl 或 web_fetch 获取以下 URL（逐个尝试，失败跳过）：
   - {预设 URL 列表，3-5 个相关网站}
2. 每个信源提取关键数据点
3. 如果所有 URL 都失败，基于已有知识整理，标注"⚠️ 模型知识"

## 输出格式（严格遵循）
### {方向名}
#### 核心发现
- 发现1：{具体数据}（来源：{URL}）
- 发现2：...

#### 推荐列表
| 名称 | 详情 | 价格 | 备注 |
|------|------|------|------|
| ... | ... | ... | ... |

#### 信源
- {URL1}
- {URL2}

#### 数据时效
- 以上信息获取于 {当前日期}，建议出行前复核价格和开放时间
```

### 结果收集与合并

所有 agent 完成后：

1. 逐个 `read_agent` 获取结果
2. 合并为统一调研报告，按方向分章节
3. 标注每个数据点的来源（URL 或"模型知识"）
4. 如果某个 agent 失败，主 agent 补充该方向的 LLM 知识

### 降级策略

| 场景 | 处理方式 |
|------|---------|
| task 工具不可用 | 退回**串行模式**：主 agent 逐方向 web_fetch |
| 部分 agent 超时/失败 | 主 agent 用 LLM 知识补充失败方向 |
| research-spatial 失败 | 距离/时间用 LLM 估算，标注"约"前缀 |
| 完全无法联网 | **离线模式**：全部基于 LLM 知识，标注"⚠️ 建议出行前核实" |

## 调研质量要求

- 并行模式：每个 agent 至少 3 个有效信源，总计 ≥ 15 个
- 串行模式：信源总数 ≥ 20 个（≤3 天短途：≥ 10 个）
- 离线模式：尽可能丰富，标注数据时效不确定
- 优先：官方旅游网站、资深旅行博主、当地媒体、专业论坛
- 价格信息须注明时效性
- 关键事实至少 2 个独立信源交叉验证

---

# Stage 3: 路线架构

基于调研结果生成每日行程架构。当高德空间数据可用时，使用**真实路径规划**替代 LLM 估算。

## 高德路径规划（AMAP_AVAILABLE = true 时）

Stage 2 的 `research-spatial` agent 已提供所有景点的精确坐标。在此基础上，主 agent 调用高德路径规划 API：

```
对每日行程中的连续景点对，根据旅行类型选择 API：

旅行类型   │  API                                  │  说明
──────────┼──────────────────────────────────────┼──────────
自驾游     │  maps_direction_driving(A坐标, B坐标)  │  里程/用时/过路费
城市漫游   │  maps_direction_walking (≤3km)         │  步行距离/用时
           │  maps_direction_transit_integrated (>3km)│  地铁/公交方案
骑行段     │  maps_bicycling                        │  骑行路线/距离
跨城移动   │  maps_direction_transit_integrated      │  火车/大巴方案
所有模式   │  maps_distance                         │  每日总距离验证
```

> 高德不可用时，使用 LLM 知识估算距离和时间，在路书中用"约"前缀标注。

## Stage 3.1: 行程可行性门控（Feasibility Gate）

> **第一性原理**：行程是物理约束下的规划，不是景点的自由组合。  
> 在写入任何每日行程前，必须通过以下验证——不通过则强制拆分或删除景点。

### 规则一：单日往返可行性公式

```
可用总时长 = 出发时间到返回时间（一般 12h，高原区域 10h）

验证公式：
  出发点 → 景点A（单程用时）× 2          ← 来回交通
  + 各景点游览时间之和
  + 景点间交通用时之和
  + 缓冲时间（1h）
  ≤ 可用总时长

不满足 → 必须拆分为多天 或 删去最远景点
```

**计算工具**（优先级）：
- AMAP_AVAILABLE = true → 调用 `maps_direction_driving` / `maps_distance` 获取真实用时
- AMAP_AVAILABLE = false → 用 LLM 知识估算，并在路书中标注"约"

### 规则二：跨城景点强制隔离

| 距出发地单程距离 | 强制规则 |
|----------------|---------|
| ≤ 80km | 可与其他景点同天 |
| 80–150km | 同天内只能有该景点，无其他目的地 |
| > 150km | **强制独立成一天，或安排沿途住宿** |

> 典型陷阱：拉萨出发，羊卓雍错（100km）可单独一日游；日喀则扎什伦布寺/白居寺（280km）**绝对不可**与任何拉萨景点或羊湖捆绑在同一天。

### 规则三：特殊目的地约束

**高原地区（海拔 3500m+）**：

| 到达后天数 | 允许活动范围 | 禁止 |
|-----------|------------|------|
| Day 1 | 酒店周边步行，≤1h | 一切景区游览 |
| Day 2 | 市区平坦景点，≤3h | 海拔 4000m+ 景点 |
| Day 3+ | 正常游览市区 | 海拔 4500m+ 建议 Day 4 以后 |
| Day 4+ | 可前往高海拔（羊湖 4441m） | — |
| Day 5+ | 可尝试极高海拔（纳木错 4718m） | 仍需带氧气 |

**强制执行**：高原行程的 Day 1 不得安排任何收费景点，违反时自动将景点后移一天。

### 规则四：生成后审核清单

每日行程草稿生成后，必须逐一校验：

```
□ 当日总里程（往返）是否在可行范围？
□ 所有景点是否在同一合理区域内？（不可跨越多个城市）
□ 是否存在隐含的"长距离跳跃"？（如 A→B→C 看似相邻实则绕远）
□ 高原行程：是否违反海拔适应规则？
□ 含包车/自驾的一日游：是否有足够的观景/停留时间（≥2h）？
□ 返程时间是否预留充足？（天黑前返回）
```

如任何一项不通过 → **红色警示**，重新规划该天行程后方可进入 Stage 4。

---

## 节奏设计

- **张弛有度**：长途驾驶日 + 深度游览日交替
- **高潮设计**：最精华目的地安排在行程中段（Day 3-5）
- **缓冲时间**：每 3-4 天安排"自由日"或"休整日"
- **情绪曲线**：出发兴奋 → 适应期 → 高潮 → 回味 → 离别不舍

## 每日行程结构

```
Day X: [起点] → [终点]
├─ 里程：XXkm（高德实测 / LLM 估算）
├─ 预计用时：Xh（含游览时间）
├─ 交通方案（高德可用时）：
│   ├─ 景点A→景点B：步行 12min / 0.9km
│   ├─ 景点B→景点C：地铁2号线 3站 / 15min
│   └─ 景点C→酒店：公交 537路 / 25min
├─ 天气（高德可用时）：☁️ 多云 26°C
├─ 今日亮点：一句话概括
├─ 必停点：2-3 个精选（含高德评分）
├─ 周边发现（高德可用时）：景点周边高分餐厅/咖啡馆
├─ 美食推荐：1-2 个
├─ 住宿推荐：1-2 个
└─ 贴士：含天气建议 + 实际交通建议
```

> 标注"高德可用时"的字段在 `AMAP_AVAILABLE = false` 时省略或用 LLM 估算替代。

## 用户确认

展示行程架构供确认或修改，确认后进入 Stage 4。

**快捷模式**：用户要求"直接写不用确认"时跳过。

---

# Stage 4: 内容写作与排版

这是路书的核心阶段——将调研和架构转化为设计精美的 HTML 路书。

## 执行模式选择

根据可用工具自动选择最优模式：

| 条件 | 模式 | 说明 |
|------|------|------|
| task 工具可用 | **专职 Agent 模式**（推荐） | 启动 1 个 general-purpose agent 在干净上下文中写全部 HTML |
| task 不可用 | **主 Agent 直写模式** | 主 agent 用 heredoc 分批写入（传统方式） |

### 专职 Agent 模式（推荐）

**核心优势**：HTML 写作 agent 拥有干净上下文——不含调研过程、历史对话、路线讨论的噪音。从第一行写到最后一行，风格完全统一。

启动 1 个 `general-purpose` agent（`mode: "background"`），将以下内容**完整传入** prompt：

```
你是旅游路书 HTML 写作专家。请生成一个完整的单文件 HTML 路书。

## 路书参数
- 路线名称：{名称}
- 文件名：{名称}_guidebook.html
- 旅行日期：{日期}
- 天数：{N} 天
- 旅行类型：{类型}

## CSS 规范（完整复制 references/layout-css.md 内容）
{layout-css.md 全文}

## 章节模板（完整复制 references/chapter-templates.md 内容）
{chapter-templates.md 全文}

## 调研数据（Stage 2 合并报告）
{调研报告全文}

## 路线架构（Stage 3 确认版）
{每日行程架构}

## 写作风格
三层需求驱动：
- 定向（Where）——精准清晰：地名、方向、里程用时准确
- 决策（What）——替用户筛选：每天 2-3 个必停点
- 情感（Why）——赋予意义：融入历史故事和当地人视角

## 技术要求
1. 使用 heredoc 分批写入（cat > 首批，cat >> 后续），单引号 << 'HTMLEOF'
2. ¥ 用 &#165; 替代，— 用 &#8212;，→ 用 &#8594;，° 用 &#176;
3. 每批写完后 wc -c 确认文件增长
4. 总批次 3-5 批，按逻辑段落分割
5. 所有 CSS 内嵌 <style>，所有 SVG 内联，零外部图片
6. 最后一批必须包含 </body></html> 闭合标签
```

**主 agent 在等待期间**：可做其他轻量工作或提示用户"正在生成 HTML，预计 2-3 分钟"。

Agent 完成后：
1. `read_agent` 获取结果，确认 HTML 文件已生成
2. `wc -c` 验证文件大小（5 天行程应在 50-80KB）
3. 进入 Stage 5

### 主 Agent 直写模式（降级）

当 task 工具不可用时，主 agent 直接使用 heredoc 分批写入。

## 章节结构

路书采用五部分结构。阅读 `references/chapter-templates.md` 获取每个章节的完整 HTML 模板：

1. **出发前**：封面 / 旅程概览 / 行前准备
2. **每日行程**：Day-by-Day（核心主体）——日程卡片、路线描述、必停点、美食、住宿、贴士、笔记区
3. **目的地深度**：2-3 个重要目的地的深度介绍
4. **实用附录**：紧急联系、常用语言、费用明细、推荐歌单
5. **封底**：旅行语录 + 个性化信息 + 旅行感言空间

## 排版规范

路书视觉设计继承 Claude 暖色调美学。阅读 `references/layout-css.md` 获取完整 CSS 规范，涵盖：

- 外部资源（仅 Google Fonts + Tabler Icons CDN）
- 页面布局（A4, max-width 680px）
- 字体系统（Noto Serif SC / Noto Sans SC / JetBrains Mono）
- 配色方案（Parchment 羊皮纸底 + Terracotta 赤陶色 + 功能色系统）
- 装饰元素（指南针、分隔线、DAY 徽章、卡片角标、首字下沉）
- 分页控制（封面独占、Day 新页、卡片不拆分）
- 打印适配（保留暖色调背景）

## 写作风格

三层需求驱动写作：

- **定向（Where）**——精准清晰：地名、方向、里程用时必须准确，使用具身化描述（"左手边"、"前方 200 米"）
- **决策（What）**——替用户筛选：每个目的地只推荐 2-3 个必停点，用"必停/可选/时间充裕可去"标记优先级
- **情感（Why）**——赋予意义：每个地点讲"为什么值得来"，融入历史故事和当地人视角，用文学化语言描述风景

### 情感增强写作（高德数据驱动）

当高德空间数据可用时，应用以下四种情感增强模式：

**1. 距离叙事**——将精确距离转化为可感知的体验：
- ≤500m → "几分钟脚程" + 途中能看到/闻到/听到什么
- 500m-2km → "散步的距离" + 沿途风景描述
- \>2km → 交通建议 + 车窗外的风景
- 示例："出黄鹤楼南门左转，沿武珞路走 600 米——大约一首歌的时间——就到了户部巷。"

**2. 周边惊喜**——呈现高德发现的高分 POI（LLM 可能不知道的新店/小店）：
- 用"💡 旅途发现"卡片呈现
- 包含：名称、距离、评分、一句推荐理由

**3. 时间感知**——天气 + 距离 + 时间段 = 具体体验建议：
- 示例："今日 26°C 多云——步行长江大桥的完美天气。桥面 1.6km，不急不慢走完约 22 分钟。建议 16:00 出发，走到桥中央正好赶上日落。"

**4. 安心感**——在每日贴士中嵌入周边便利设施：
- 示例："今晚住宿 200m 内有全家便利店（24h），最近药房在 400m 外武珞路上。"

> 高德不可用时，这四种模式自动省略——路书仍有完整的文化叙事和 LLM 估算数据。

## HTML 生成（heredoc 分批策略）

生成一个完整的单 HTML 文件，所有 CSS 内嵌 `<style>`，所有 SVG 装饰内联，零外部图片。

> 以下 heredoc 策略适用于**专职 Agent 的内部执行**和**主 Agent 直写降级模式**。

### 大文件写入策略

路书 HTML 通常 50-80KB（5 天行程约 30 页），超出 write/create 工具的单次上限。采用 **heredoc 分批追加**策略：

```bash
# 第 1 批：HTML head + 完整 CSS（<style> 标签）
cat > {文件名}_guidebook.html << 'HTMLEOF'
<!DOCTYPE html>
<html lang="zh-CN">
<head>...</head>
<style>/* 全部 CSS，参照 references/layout-css.md */</style>
<body>
HTMLEOF

# 第 2 批：封面 + 概览 + 行前准备
cat >> {文件名}_guidebook.html << 'HTMLEOF'
<div class="cover">...</div>
<div class="overview">...</div>
<div class="preparation">...</div>
HTMLEOF

# 第 3-N 批：每日行程（每天一批或每 2 天一批）
cat >> {文件名}_guidebook.html << 'HTMLEOF'
<div class="day-chapter">...</div>
HTMLEOF

# 最后一批：深度游 + 附录 + 封底 + 闭合标签
cat >> {文件名}_guidebook.html << 'HTMLEOF'
<div class="deep-dive">...</div>
<div class="appendix">...</div>
<div class="back-cover">...</div>
</body></html>
HTMLEOF
```

**关键注意**：
- 使用**单引号** heredoc（`<< 'HTMLEOF'`）防止 shell 变量展开
- `¥` 符号在 heredoc 中用 `&#165;` 替代，避免编码问题
- 每批写完后用 `wc -c` 确认文件增长正常
- 总批次控制在 3-5 批，按逻辑段落分割（不要在 HTML 标签中间断开）

---

# Stage 5: HTML 交付与检查

## 交付内容

1. **HTML 文件**：`{路线名称}_guidebook.html`（单文件，零外部依赖）
2. **工作报告**：制作过程记录（模板见 `references/report-template.md`）

## HTML 检查点

HTML 完成后，必须先让用户检查，不能直接跳到 PDF：

> "HTML 路书已生成：`{文件名}_guidebook.html`。请在浏览器中打开检查内容和排版。满意后告诉我，我会导出 PDF。如果需要调整，告诉我哪里需要改。"

- 用户说"OK / 满意 / 导出 PDF" → 进入 Stage 6
- 用户说"修改 xxx" → 回到 Stage 4 修改后重新提示检查

---

# Stage 6: PDF 导出

> 用户在 Stage 5 确认 HTML 满意后方可执行。

## 执行步骤

### 1. 准备导出脚本

确保工作目录有 `html2pdf.mjs`。查找方式：

```bash
# 优先检查当前目录
ls html2pdf.mjs 2>/dev/null || \
  # 查找 skill 目录下的 bundled 脚本
  find ~/.agents/skills/travel-guidebook -name "html2pdf.mjs" 2>/dev/null | head -1 | xargs -I{} cp {} ./html2pdf.mjs || \
  find . -path "*/travel-guidebook/scripts/html2pdf.mjs" 2>/dev/null | head -1 | xargs -I{} cp {} ./html2pdf.mjs
```

如果仍找不到，用以下最小脚本创建：

```javascript
// html2pdf.mjs — Playwright A4 PDF export
import { chromium } from 'playwright';
import { resolve } from 'path';
const html = resolve(process.argv[2]);
const pdf = html.replace(/\.html$/, '.pdf');
const b = await chromium.launch();
const p = await b.newPage();
await p.goto('file://' + html, { waitUntil: 'networkidle' });
await p.waitForTimeout(2000);
await p.pdf({ path: pdf, format: 'A4', margin: { top: '2cm', right: '1.8cm', bottom: '2.5cm', left: '1.8cm' }, printBackground: true });
await b.close();
console.log('PDF saved:', pdf);
```

### 2. 执行导出

```bash
node html2pdf.mjs {文件名}_guidebook.html
```

### 3. 验证与交付

检查 PDF 存在并显示大小，提示用户打开查看：

> "✅ PDF 路书已导出：`{文件名}_guidebook.pdf`（{页数}页，{文件大小}）。"

## PDF 参数

| 参数 | 值 | 说明 |
|------|----|------|
| 纸张 | A4 | 标准打印尺寸 |
| 上边距 | 2cm | |
| 下边距 | 2.5cm | 为页码留空间 |
| 左右边距 | 1.8cm | |
| 页脚 | 居中页码 | 9pt JetBrains Mono |
| 等待策略 | networkidle + 2s | 确保 CDN 资源加载 |
| 背景 | printBackground: true | 保留羊皮纸暖色纹理 |

## 备用方案

Playwright 失败时引导浏览器手动打印：Chrome/Edge 打开 HTML → Cmd/Ctrl+P → 另存为 PDF → 勾选"背景图形"。

---

# 全局规则

## 文件命名

- 调研报告：`【路线名称】-调研报告`
- 路书 HTML：`{路线名称}_guidebook.html`
- PDF 路书：`{路线名称}_guidebook.pdf`
- 导出脚本：`html2pdf.mjs`（从 scripts/ 复制）
- 工作报告：`【路线名称】-工作报告`

## 质量保证

### 调研
- 信源 ≥ 20 个，优先权威信源
- 路况信息近 6 个月内
- 交叉验证关键事实

### 内容
- 每天 2-3 个必停点，精选而非堆砌
- 通俗易懂，融入文化背景和当地人视角
- 实用信息（价格、时间、地址）准确无误

### 排版
- 字号略大于普通电子书（户外可读性）
- 对比度增强（户外光线）
- 分页正确，打印保留暖色调

## 稳定性

- 搜索失败时重试或跳过
- 任何错误不中断整体流程

## 用户体验

- 每个 Stage 开始时告知进度
- 关键步骤完成后反馈
- 确认点：Stage 1 需求（可跳过）、Stage 3 路线（可跳过）、Stage 5 HTML（必须）

---

# 执行检查清单

**Stage 0 前**
- [ ] Node.js >= 18
- [ ] Playwright + Chromium

**Stage 1 前**
- [ ] 理解用户需求
- [ ] 确认所有参数

**Stage 2 调研**
- [ ] 判断 task 工具是否可用
- [ ] 可用：启动 5 个并行 explore agent
- [ ] 不可用：退回串行 web_fetch 模式
- [ ] 所有 agent 完成后合并调研报告

**Stage 4 前**
- [ ] 路线架构已确认
- [ ] 调研内容充分
- [ ] 判断 task 工具是否可用
- [ ] 可用：读取 layout-css.md + chapter-templates.md 全文，构造 HTML agent prompt
- [ ] 不可用：主 agent 直接 heredoc 写入

**Stage 5 交付前**
- [ ] HTML 文件完整（wc -c 确认 50-80KB）
- [ ] SVG 装饰已内联
- [ ] 暖色调排版检查通过
- [ ] 打印 CSS 完整（orphans/widows、break-inside）
- [ ] 工作报告已生成

**Stage 6 导出前**
- [ ] 用户确认 HTML 满意
- [ ] html2pdf.mjs 已就绪
- [ ] PDF 生成且大小合理（通常 3-10 MB）

---

# 设计原则

1. **秒级可达** — 关键信息 3 秒内找到。日程卡片、地名、方向是最高优先级。
2. **三速阅读** — 支持扫视（3s）、浏览（30s）、沉浸（3min）三种模式。
3. **温暖如纸** — Claude 羊皮纸暖色调，数字路书拥有纸质书温度。
4. **编辑品味** — 像 Monocle 精选，不堆砌。每个推荐都带立场和温度。
5. **时空网格** — "天 × 地点"网格架构，支持随机访问。
6. **双重身份** — 旅行前是规划工具，旅行后是记忆载体。
7. **大地色系** — 赤陶、琥珀、橄榄、鼠尾草。没有冷色，没有荧光。
