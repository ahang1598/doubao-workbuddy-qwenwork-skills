# 策略单解析指南（投投 · 路径B 专用）

> 投投走「金手指策略单直灌建单」路径（主线一 · 路径B）时，按本指南把一份《投放执行确认单 v2》解析成可直接建单的要素，并逐项做字段体检、前置资产核对、多项目隔离。
> 字段全规范见项目根目录《投放执行确认单字段规范_v2_直灌建单版.md》；本文件是投投的**执行版速查**。

---

## 一、策略单来源（方式乙 · get_strategy）

投投前置从金手指拉策略单，优先走接口，接口未上线时接受用户直接给文件/内容。

| 来源 | 动作 | 说明 |
|---|---|---|
| **金手指 `get_strategy`（首选）** | 调 `get_strategy({offerName})` 拉完整策略单 object | ⚠️ 接口金手指侧待开发；未上线前走下面过渡方案 |
| **`list_strategies` 选单** | 多项目时先 `list_strategies()` 列出 `[{offerName,status,updatedAt}]`，让用户选要建哪个 | 一次只建一个 offerName |
| **过渡方案（现可用）** | 用户把确认单 md/json 内容贴进来，投投按 v2 骨架解析 | get_strategy 上线前不阻塞 |

> ⚠️ 注意：金手指现有 `open_config` 是**写入**策略（方向相反），`get_project_data` 只回投放数据不回建单字段——**都不能用来读策略单**。必须走 `get_strategy`。
>
> 📌 **读/写能力现状（2026-08-25 实测 `tools/list`，金手指 MCP 共 14 个工具）**：
> - **读策略单：仍不可用** —— `get_strategy` / `list_strategies` **均未在 MCP 中暴露**，路径B 继续走「用户贴确认单」过渡方案。
> - **写复盘产物：✅ 已可用** —— `upsert_review_artifact`（复盘材料）/ `upsert_review_intent`（复盘意图）/ `upsert_review_schedule`（复盘定时）/ `upsert_demand_brief`（需求单）四个写接口实测写入+回读均通过。
> - 可用读接口：`list_projects` / `get_project_data` / `get_project_context` / `list_creative_examples`。

---

## 二、B2 字段体检清单（够不够 / 精简 / 补齐）

拿到策略单后，逐组核对。分三档结论：✅齐全 / ⚠️可补 / ❌阻塞（缺了不能建单）。

### 2.1 建营销单元必需（缺 = ❌ 阻塞）

| 字段 | 来源 | 校验 |
|---|---|---|
| `offerName` | 段A | 非空、唯一 |
| `deliveryMode` / `isSmartDelivery` | 段A | 二选一，决定走 smart-create 还是 standard-create |
| `bidding` / `bidRange` | 段A | bidRange 必须**数字单值**（非"54元"字符串、非区间） |
| `dailyBudget` / `totalBudget` | 段A | 数字类型 |
| `adStructure` / `adCount` / `creativeGroupCount` | 段A | 数字，且 dailyBudget ≥ 考核成本×20 校验 |
| `kpi` | 段A | 对齐 AMS 转化目标枚举 |
| **`accountIds`** | **Part 4** | **真实账户 ID，非空**（v1 只有 accountCount 数量，直灌必须补真实 ID） |
| **`apikeyStatus`** | **Part 4** | **必须 = `ready`**；missing/invalid → 拒绝建单先引导录入 |

### 2.2 建创意必需（缺 = ❌ 阻塞创意，营销单元可先建）

| 字段 | 来源 | 缺失后果 |
|---|---|---|
| `assets.landingPageId` | Part 4 | 建创意失败（error 31065 类） |
| `assets.conversionId` | Part 4 | oCPM 无转化目标跑不动 |
| `assets.brandComponentId` | Part 4 | 腾讯3.0 建创意受阻（190166 类）|
| `assets.ctaButtonId` | Part 4 | 创意无行动按钮 |
| `assets.productId` | Part 4 | 仅电商/商品类必需 |
| `materialPool` / `materialSpecs` | 段B | 决定挂几条素材、裁什么尺寸 |

### 2.3 可精简 / 可选（缺不阻塞建单）

- 段B 内容字段：`coreClaim` / `imageCreativeTypes` / `copyDeck` / `sellingPoint` —— 素材助手的活，投投建单只要数量+尺寸对齐，**直灌场景跳过**。
- 段A 🆕 增强字段：`budgetAllocation` / `deliveryHours` / `refreshCadence` 等 —— 缺则用默认基线，不阻塞。
- `assets.overlayCardId` —— 可选组件，无则不挂。

### 2.4 体检输出

> 输出一张《策略单体检表》：每字段 ✅/⚠️/❌ + 缺口清单 + 每个 ❌ 项「去哪补」（金手指录入 or 腾讯广告后台配资产），**所有 ❌ 项清零前不进 B4 建单**。

---

## 三、B3 前置资产核对清单（对齐金手指配置页截图 8 项）

```
□ accountIds        真实账户 ID 已给
□ apikeyStatus=ready 鉴权已在金手指录入并校验通过
□ landingPageId     落地页 ID 已配（资产→创意资产管理→落地页）
□ productId         产品 ID（电商/商品类必需）
□ conversionId      转化归因 ID 已配
□ brandComponentId  品牌形象组件 512×512 已备
□ overlayCardId     浮层卡片（可选）
□ ctaButtonId       行动按钮已定
```

---

## 四、建单字段映射（策略单 → 腾讯广告 API）

| 策略单字段 | 建单动作 | 对接 skill/字段 |
|---|---|---|
| `isSmartDelivery=true` | 建智投营销单元 | `tencentads-delivery-smart-create` |
| `isSmartDelivery=false` + `placements` | 建标准营销单元（指定版位） | `tencentads-delivery-standard-create` |
| `bidding` + `bidRange` | 出价方式 + 出价 | 建单出价字段 |
| `dailyBudget` | 日预算 | 建单预算字段 |
| `adStructure` | 广告×创意组×素材 循环建 | 按 adCount/creativeGroupCount 展开 |
| `assets.*` | 建创意挂资产 | `tencentads-creatives`（落地页/转化/品牌组件/CTA） |
| `materialPool`/`materialSpecs` | 挂素材数量/尺寸 | 建创意挂素材 |
| 建单前 | 鉴权连通 | `tencentads-auth` 校验 apikey |

> 建单纪律：apikey 校验连通 → 逐条建单**前再确认一次** → 每建一个真实动作**即写操作日志一行**（见 operation_log_template.md）。

---

## 五、多项目隔离（一次一个 offerName）

- `offerName` = 唯一主键；多项目 = 多次 get_strategy，**逐个建，不批量混灌**。
- 每项目绑自己的 `accountIds`；`accountOfferMap` 防跨项目串号。
- 自动化命名 `投投·{offerName}·每日巡检调优`；操作日志按 offerName 独立成文件。
- B1 发现多项目 → 先问"这次建哪个 offerName？"

---

## 六、路径B 全流程（B1→B5）

```
B1 get_strategy 拉策略单（或用户贴）
  → B2 字段体检（2.1/2.2/2.3 三档，输出体检表，❌清零）
  → B3 前置资产 8 项核对（缺则列去哪补）
  → B4 直接建单（auth校验→smart/standard-create→creatives，逐条确认，每步写日志）
  → B5 落「每日巡检+调优」自动化（status=PAUSED，命名带offerName，告知手动开启）
  → 🚪 总确认 +《投前建单纪要》+ 操作日志（本地存+同步金手指）
```
