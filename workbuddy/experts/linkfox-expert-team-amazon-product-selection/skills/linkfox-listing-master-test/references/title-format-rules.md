# Amazon 标题格式规则参考手册

> **何时读取本文件：** Phase C.2 标题生成时必读。含 2026-07-27 新规（Title 75c + Item Highlights 125c）与类目特例。

---

## 零、Amazon 2026 新规（默认，除 Media 外）

| 字段 | 上限 | 说明 |
|------|------|------|
| **Title** | **≤ 75 字符**（含空格） | 移动端完整展示；只保留「产品是什么」 |
| **Item Highlights** | **≤ 125 字符**（含空格） | 可搜索；承载迁出的场景、功能收益、次级规格 |

**旧标题拆分**：rewrite/优化旧标题时，将现有超长标题按 `legacy_title` 处理，把必须保留的信息迁移到 Title 或 Item Highlights。

详细政策源：`listing-title-writer/references/amazon-title-policy-2026.md`。如果本文件与 title-writer 冲突，以 title-writer 的 75/125 规则为准。

---

## 一、硬性字符限制（按类目）

> **2026-07-27 后**：下表「大多数类目」200 字符上限被 **75c Title + 125c Item Highlights** 取代。Media 除外。旧版 125/150/200 字符类目规则不得继续作为非 Media 的标题上限。

| 类目范围 | Title 上限 | Item Highlights | 违规后果 | 特殊要求 |
|---------|-----------|-----------------|---------|---------|
| **大多数类目（默认）** | ≤ **75** | ≤ **125** | AI 自动替换超长标题 | 见 §零 |
| **Media（书籍/音乐/视频）** | ≤ 200 | 不适用 | — | 沿用旧规则 |
| **服装 / 鞋帽 / 配饰** | ≤ **75** | ≤ **125** | 同上 | Title 必含性别/尺码体系 |
| **食品 / 饮料 / 保健品** | ≤ **75** | ≤ **125** | 同上 | 必含形态/份量；禁止功效词 |
| **珠宝 / 手表** | ≤ **75** | ≤ **125** | 同上 | 必含金属/宝石/性别 |
| **婴幼儿产品** | ≤ **75** | ≤ **125** | 同上 | 必含年龄段、安全认证 |
| **汽车配件** | ≤ **75** | ≤ **125** | 同上 | 年份/品牌/型号；Vehicle Fitment |
| **手机壳/电子配件** | ≤ **75** | ≤ **125** | 同上 | 具体机型代数 |
| **鞋类（细分）** | ≤ **75** | ≤ **125** | 同上 | 性别、尺码、类型 |
| **宠物用品** | ≤ **75** | ≤ **125** | 同上 | 宠物类型、重量范围 |
| **工具 / DIY** | ≤ **75** | ≤ **125** | 同上 | 功能类型、兼容标准 |
| **电子产品（主类目）** | ≤ **75** | ≤ **125** | 同上 | 关键规格优先放 Title |

> **验证**：`len(title) <= 75`，`len(item_highlights) <= 125`（Media 仅验 title）。

---

## 二、Title vs Item Highlights 分工

| 字段 | 应放 | 不应放 |
|------|------|--------|
| Title | 品类核心词、品牌（若规则要求）、型号、关键尺寸/数量、材质、兼容性锚点 | 场景堆砌、多条卖点并列、促销语 |
| Item Highlights | 迁出的功能收益、使用场景、量化卖点、套装摘要、次级规格 | 重复 Title 核心词、五点全文、促销/物流词 |

**旧标题拆分原则：**

- `must_keep_in_title`：品类核心词、关键规格、兼容性、型号、尺寸/数量。
- `must_migrate_to_highlights`：使用场景、功能收益、冷热保温时长、套装摘要、承诺型但合规的量化卖点。
- 硬规格不能丢失；若 Title 放不下，迁移到 Item Highlights。

---

## 三、标题结构模板

### 3.1 通用结构（general 类目）

```text
[核心关键词] + [材质/规格/数量] + [兼容性锚点]   -> Title（≤75c）
[使用场景] + [功能收益] + [次级规格]             -> Item Highlights（≤125c）
```

**铺货卖家特别规则：**

- **不放品牌名**：标题开头直接以核心关键词起始，不写无品牌或虚假品牌。
- **核心词前置**：搜索量最高的词放在标题最前 40 字符内。
- 各模块用空格或连接词（`for`、`with`、`-`、`&`）自然连接，不堆砌。

**示例（水瓶）：**

```text
Title（62c）: Premium Stainless Steel Insulated Water Bottle - BPA-Free
Item Highlights（~95c）: Keeps drinks cold 24 hours, hot 12 hours. Ideal for gym, office, and outdoor adventures.
```

### 3.2 服装 / 鞋帽结构

```text
[品类] + [核心属性（材质/版型）] + [适用人群/尺码锚点] -> Title（≤75c）
[场景] + [穿着体验] + [次级卖点]                       -> Item Highlights（≤125c）
```

**示例（T恤）：**

```text
Title: Cotton Graphic T-Shirt for Men, Short Sleeve Crew Neck
Item Highlights: Soft breathable cotton for daily wear, summer outings, and casual layering.
```

### 3.3 电子/3C 结构

```text
[产品类型] + [关键规格] + [兼容设备/型号] -> Title（≤75c）
[核心功能] + [场景/收益]                 -> Item Highlights（≤125c）
```

**示例（充电线）：**

```text
Title: USB-C to Lightning Cable 6ft, MFi Certified, 2-Pack
Item Highlights: Fast charging cable compatible with iPhone 15/14/13 for home, car, and travel use.
```

---

## 四、关键词布局策略

### 4.1 Title 关键词优先级

从 Phase B 采集的关键词数据中，按以下逻辑选词：

| 位置 | 选词标准 | 建议数量 |
|------|---------|---------|
| 前 40 字符 | 搜索量 Top 1-2 的核心词 | 1-2 个 |
| 中段 | 材质、规格、兼容性、型号 | 1-3 个 |
| 后段 | 尺寸/数量/关键锚点 | 0-2 个 |

场景词、长尾功能词、泛化收益词优先放入 Item Highlights，而不是挤压 Title。

### 4.2 关键词重复控制

- 同一关键词（含同义词/复数形式）在 Title 中**最多出现 2 次**。
- 例：`yoga mat` 和 `mat` 视为同一词根，合计计 2 次。
- 介词（for、with、in）、冠词（a、the）、连词（and、or）不计入。
- Item Highlights 不重复 Title 的核心词，除非为了可读性不可避免。

### 4.3 自然可读性测试

标题应能被人类顺畅朗读，无需刻意停顿。判断标准：

- 是否像正常的产品名称？
- 删掉任意一个词，语义是否断裂？（是 -> 词是必要的；否 -> 考虑删除）
- 是否能在移动端完整展示核心商品身份？

---

## 五、禁止内容清单

### 5.1 禁止字符

```text
! ？ _ * $ @ # % ^ & ~ ` ; : " '（单引号/双引号用于型号时例外）
```

> 例外：商标符号 ® ™ 和注册品牌名中自带的符号在品牌卖家场景允许；铺货卖家无品牌，跳过此项。

### 5.2 禁止词语类型

| 类型 | 示例 | 原因 |
|------|------|------|
| 主观促销词 | "Best", "#1", "Hot Sale", "Top Rated" | 无数据支撑，违反规则 |
| 物流/售后词 | "Free Shipping", "Fast Delivery", "Money Back" | 属于运营信息，不属于产品属性 |
| 竞品品牌词（引流） | "Like Nike", "Better than Yeti" | IP 侵权风险 |
| 虚假销量词 | "Bestseller", "1M Sold" | 误导性 |
| 完全重复短语 | "yoga mat yoga mat" | 算法降权 |

### 5.3 特殊场景：兼容产品写法

铺货卖家常做配件类产品，需遵守以下写法：

| 违规写法 | 合规写法 |
|----------|----------|
| "Apple AirPods Case" | "Case Compatible with AirPods Pro 2nd Generation" |
| "Samsung Galaxy Charger" | "USB-C Charger Compatible with Samsung Galaxy S24/S23" |
| "Fits iPhone - iPhone Case" | "Protective Case Fits iPhone 15/15 Pro, Not Made by Apple" |

---

## 六、标题生成后验证检查表

生成标题后，逐项确认：

- [ ] **Title 字符数**：`len(title)` ≤ 75（Media ≤ 200）
- [ ] **Item Highlights**：`len(item_highlights)` ≤ 125（非 Media）
- [ ] **信息迁移**：旧标题硬规格出现在 Title 或 Highlights 中
- [ ] **核心词前置**：搜索量最高的词在前 40 字符内
- [ ] **无禁止字符**：不含 `! ? _ * $ @` 等符号
- [ ] **关键词不超 2 次**：同义词/复数也计入
- [ ] **无促销语言**：不含 "Best"、"#1"、"Free"、"Sale" 等
- [ ] **无竞品品牌词**：不引用竞品品牌名
- [ ] **可自然朗读**：删掉任意一词不会完全破坏语义
- [ ] **铺货卖家**：开头不出现品牌名或 "Generic"

---

## 七、标题字符数精确计算方法

在 Phase C 结束后，若需要运行脚本验证：

```python
title = "Your Amazon Title Here"
highlights = "Keeps drinks cold 24 hours. Ideal for gym and office."
print(f"Title: {len(title)} / 75")
print(f"Highlights: {len(highlights)} / 125")
assert len(title) <= 75, f"Title 超出 {len(title) - 75} 字符"
assert len(highlights) <= 125, f"Highlights 超出 {len(highlights) - 125} 字符"
```

> 对于多字节 Unicode 字符（如日文、德文变音），`len()` 仍按字符计数（非字节），符合亚马逊标题的字符计算规则。
