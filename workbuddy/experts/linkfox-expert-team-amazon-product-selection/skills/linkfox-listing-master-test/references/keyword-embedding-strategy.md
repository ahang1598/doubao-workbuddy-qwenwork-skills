# 关键词埋词策略完整参考手册

> **何时读取本文件：** Phase C.1 执行前必读（已注册至 SKILL.md 知识库索引）。本文件覆盖亚马逊所有可索引字段的权重体系、搜索量分段分配规则、去重逻辑和品类特化埋词规则，是关键词分配到字段的权威规则手册。

---

## 一、亚马逊可索引字段完整清单与权重排序

### 1.1 字段权重金字塔

亚马逊搜索算法（A10 + Rufus）对不同字段赋予不同的索引权重，理解这个层级是分配关键词的基础：

| 权重层级 | 字段名称 | 字符/字节限制 | SEO 价值说明 |
|---------|---------|-------------|------------|
| **W1（最高）** | Title（标题） | ≤ 200 字符 | 权重最高，核心词必须在前 40 字符内 |
| **W2（高）** | Bullet Points（五点描述） | 每条 ≤ 1000 字符，5条合计约 5000 字符 | 第1-2条权重高于第3-5条 |
| **W3（中高）** | Backend Keywords / Search Terms | ≤ 500 字节 | 隐藏词库，补充前端未覆盖的词 |
| **W3（中高）** | Subject Matter（主题词） | 每条 ≤ 50 字节，最多 5 条 | 常被忽略的第二后台词库，独立于搜索词 |
| **W4（中）** | Product Description（产品描述） | ≤ 2000 字符 | 权重低于标题和五点，但仍被索引 |
| **W4（中）** | Item Specifics（后台属性）| 各字段不同 | 用于节点过滤 + 语义映射，间接影响流量 |
| **W5（低）** | Intended Use（预期用途） | 约 1000 字符 | 覆盖场景型长尾词 |
| **W5（低）** | Target Audience（目标受众） | 约 1000 字符 | 覆盖人群型词汇，被 Rufus 人群意图抓取 |

> **重要说明**：A+ Content 的文字部分**不被亚马逊搜索索引**（但会被 Google 等外部搜索引擎收录）。A+ 是转化工具，不是埋词工具。

---

## 二、各字段关键词分配策略

### 2.1 Title（标题）— 核心战略词

- 放置搜索量最高的 1-2 个核心词（占标题前 40 字符）
- 核心词只能出现 1-2 次（同义词/复数合计计入）
- 不要在标题中堆砌中等搜索量词，留给 Bullet Points

**示例分配逻辑：**
```
搜索量 Top 1 词 → 标题前端
搜索量 Top 2 词 → 标题中段
场景词/规格词 → 标题后段
其余词 → Bullet Points + Backend Keywords
```

---

### 2.2 Bullet Points（五点描述）— 最大可用词库

**字符上限：每条约 1000 字符，5条合计约 5000 字符**

> ⚠️ 常见误区：baf-framework.md 中建议 ≤ 250 字符是为了**可读性**，不是硬性字节限制。卖家应该利用 1000 字符的空间自然嵌入更多长尾词，同时保持语义连贯。

**关键词优先级分布原则：**

| 条目 | 推荐嵌入词类型 | 原因 |
|------|-------------|------|
| **第 1 条** | 核心功能词 + 次级高流量词 | 算法对前两条赋予更高权重 |
| **第 2 条** | 材质/认证词 + 安全相关词 | 权重仅次于第1条 |
| **第 3 条** | 场景词 + 人群词（2-3个场景） | 覆盖 Rufus 场景型/人群型意图 |
| **第 4 条** | 易用性词 + 竞争差异词 | 覆盖比较型意图 |
| **第 5 条** | 规格词 + 套装内容词 + 长尾配件词 | 覆盖搭配型意图 |

**禁止格式（2024-2025年明确打压）：**
- ❌ 开头使用全大写堆砌：`WATERPROOF DURABLE PORTABLE LIGHTWEIGHT...`
- ❌ 整条五点只有关键词列表，无句子结构
- ✅ 粗体开头（**Benefit**）后接自然语句，关键词植入句子中

**Bullet Points 粗体标签 SEO 说明：**
粗体 `**...**` 中的词汇同样会被索引，且在某些展示场景下有视觉权重加成。建议每条粗体开头包含 1 个搜索量较高的修饰词（如 **Waterproof Design**、**BPA-Free Materials**）。

**移动端展示规则：**
- 手机 App 默认仅展示前 2-3 条五点（需点击"See More"才展开全部）
- 因此，核心购买决策信息和最高权重关键词必须集中在前 2 条

---

### 2.3 Backend Keywords（后台搜索词）— 500 字节隐藏词库

**可合法填入的词汇类型（常被卖家遗漏）：**

| 类型 | 示例 | 说明 |
|------|------|------|
| **常见拼写错误** | "blutooth"、"earbuds" | 亚马逊官方允许，覆盖拼写错误的真实用户 |
| **缩写和别称** | "OTC meds"、"USB-C" vs "type-c" | 同一物品的不同叫法 |
| **近义词** | "tumbler" / "travel mug" / "thermos" | 系统不自动合并，需各自填入 |
| **外语翻译词** | 西班牙语词汇（美国西裔市场） | 如 "taza de viaje"（旅行马克杯）|
| **不带空格的复合词** | "yogamat"（vs "yoga mat"） | 部分用户搜索不带空格 |
| **产品分类俚语** | "stealthie"（隐形耳机圈内称呼） | 特定用户群的专属词汇 |
| **季节/场景触发词** | "Christmas gift"、"back to school" | 季节性流量词，可放后台 |

**绝对不能放的内容（复习）：**
- 标题或五点中已出现的词（重复浪费字节）
- 任何竞品品牌词（包括后台）
- ASIN 编号
- 与产品无关的词
- 逗号或分号（系统识别为无效，浪费字节）

**格式：** 所有词用单个空格分隔，仅此而已。
```
waterproof bluetooth speaker outdoor shower pool wireless portable shower radio
```

**字节计算方法：**
```python
search_terms = "your keywords here"
byte_count = len(search_terms.encode('utf-8'))
print(f"字节数：{byte_count} / 500")
# 变音符号（如德语 ü）和特殊符号占用更多字节
```

---

### 2.4 Subject Matter（主题词）— 被严重低估的第二后台词库

> **⚠️ 注意：** 这是与 Backend Keywords 完全独立的字段，绝大多数卖家不知道此字段的存在，导致大量关键词覆盖机会浪费。

**位置：** Seller Central → 管理库存 → 编辑 → "关键词"选项卡 → Subject Matter

**规格：** 每条最多 **50 字节**，最多可填 **5 条**（共约 250 字节额外词库）

**填写策略：**
- 每条填入一个主题词组（不是单词，而是短语）
- 与 Backend Keywords 不重复
- 优先填入中等搜索量但未被前端覆盖的词组

**示例（瑜伽垫）：**
```
Subject Matter 1: non slip yoga mat thick
Subject Matter 2: eco friendly exercise mat
Subject Matter 3: home gym floor mat
Subject Matter 4: hot yoga sweat mat
Subject Matter 5: beginner yoga accessories
```

---

### 2.5 Product Description（产品描述）— 低权重但可埋长尾词

- 权重远低于标题和五点，但仍被算法索引
- 适合植入**极长尾词**和**场景化描述性短语**（这些词太口语化，不适合放标题）
- 2000 字符上限：前 500 字符重要性最高（算法扫描优先级）

**埋词策略：** 在叙事性段落中自然覆盖 5-8 个额外场景词或长尾词，不刻意堆砌

---

### 2.6 Intended Use / Target Audience（预期用途/目标受众）

这两个 Item Specifics 字段**同时具有 SEO 索引功能**（不只是过滤属性）：

- **Intended Use**：填入 2-5 个使用场景（camping, outdoor, gym, travel, office）
- **Target Audience**：填入目标人群（Men, Women, Adults, Kids 3-8, Athletes）

> 填错（如将儿童产品填 "Adult"）不只影响节点分类，还会导致儿童人群词的搜索收录失效。

---

## 三、关键词去重与索引逻辑

### 3.1 哪些词系统会自动合并（无需手动分别填）

亚马逊索引系统**会**自动处理以下情况：
- 简单复数（mat → mats）
- 动词形态变化（run → running → ran）
- 大小写变体（Yoga Mat → yoga mat）

亚马逊**不会**自动合并：
- 真正的同义词（waterproof ≠ water resistant）
- 不同拼写习惯（grey ≠ gray）
- 缩写 vs 全称（USB-C ≠ type C ≠ type-c）
- 带连字符 vs 不带（eco-friendly ≠ eco friendly）

**实操建议：** 对于后两类，在后台搜索词中两种写法都填入。

### 3.2 跨字段重复的去重策略

已在 **标题** 中出现的词 → 不放 Backend Keywords（权重相同，浪费空间）
已在 **Bullet Points** 中出现的词 → 不放 Backend Keywords（已被高权重字段覆盖）
**Description** 中的词 → 可以与 Backend Keywords 重复（权重不同，可以加强信号）

---

## 四、Phase B 多数据源关键词矩阵

> Phase B 现在从 5 个数据源采集关键词，每个数据源有其独特的埋词价值。

| 数据源 | 提供的关键词类型 | 埋词优势 | 优先分配字段 |
|--------|--------------|---------|------------|
| **G2 SIF-ASIN关键词**（搜索量+排名） | 竞品已验证的流量词 | 有搜索量数据，可量化排序 | 标题、五点前两条、后台搜索词 |
| **G2 coverage_count**（跨竞品覆盖数） | 品类核心共识词 | coverage≥3 代表品类刚需词，标题必放 | 标题前 40 字符 |
| **G3 标题高频词**（分词统计） | 竞品标题共现词 | 多竞品标题验证 = 搜索入口词 | 本品标题（优先参考） |
| **G4 ABA搜索频次排名** | 有实际购买转化的词 | SFR越低=转化越强，修正纯搜索量的误差 | 标题、五点第1-2条（优先于同搜索量其他词） |
| **G5 VOC买家用词**（评论提取） | 买家自然语言词组 | 与Rufus语义匹配，流畅嵌入句子不显堆砌 | 五点第3-5条、产品描述前500字符 |
| **G5 竞品痛点词**（差评提取） | 竞品已暴露的弱点 | 转化为本品差异化优势词，覆盖比较型搜索意图 | 五点第4条（易用性/差异化条） |
| **`my_product_spec` 属性词** | 卖家自有差异化词 | 独有规格+颜色+套装 = 长尾精准词 | 标题后段、五点第5条、Subject Matter |
| **`pinned_keywords` 固定词** | 用户明确指定的核心词 | 业务判断优先，直接定位目标市场 | 标题前 40 字符（强制） |

### ABA 修正规则

当 ABA Search Frequency Rank（SFR）与 G2 月搜索量排名不一致时，按以下规则处理：

- **SFR 靠前但搜索量中等**（说明这个词虽然不是最多人搜，但搜的人转化率高）→ 优先级上调至 Top 3-8，放入五点第 1-2 条
- **搜索量高但 ABA 无数据**（可能是高曝光低转化词）→ 仍放标题/前两条，但不作为文案核心卖点，只做 SEO 覆盖
- **ABA Top 5 词且 coverage_count ≥ 2**（品类核心 + 高转化）→ 强制放入标题前 40 字符，即使用户未 pin

### VOC 词组嵌入规则

VOC 词组来自真实买家评论，是最自然的嵌入素材：

**VOC 词组的正确用法：**
```
买家原话: "the suction is really strong and it doesn't leave marks"
→ 转化为五点句子: "**Powerful Yet Gentle Suction** — delivers strong suction force for thorough cleaning
  without leaving marks on delicate surfaces, perfect for everyday household use."
→ 自然嵌入了: strong suction / leave marks / delicate surfaces / household cleaning
```

**VOC 竞品痛点词的转化用法：**
```
竞品差评词: "breaks after 2 weeks", "handle too slippery"
→ 转化为差异化五点: "**Built to Last** — reinforced [material] construction tested for [X] months of daily use;
  ergonomic grip design prevents slipping even with wet hands."
→ 自然嵌入了隐含对比关键词，覆盖了比较型买家搜索意图
```

---

## 五、关键词分配全局流程（含多数据源）

> **执行入口：** 本节的分段规则已集成至 SKILL.md C.1「关键词提取与布局」步骤 2，由 SKILL.md 编排执行。以下为规则参考原文。

```
Phase B 多源数据输入
│
├─ [G2] 关键词搜索量 + coverage_count（跨竞品覆盖）
├─ [G4] ABA Search Frequency Rank
├─ [G3] 标题高频共现词
├─ [G5] VOC买家词组 + 竞品痛点词
└─ [Phase A] my_product_spec 属性词 + pinned_keywords
│
▼ 构建关键词价值评分表（按优先级排序）
│
├── P0: pinned_keywords → 标题前 40 字符（强制，不排序）
│
├── P1: 搜索量 Top 1-2 + coverage≥2 + (ABA Top 20 加权) → 标题前 40 字符
│
├── P2: 搜索量 Top 3-8 + 标题验证词 + ABA Top 50 → 五点第1-2条
│
├── P3: 搜索量 Top 9-20 + 场景词 + VOC词组 → 五点第3-5条（自然植入句子中）
│
├── P4: my_product_spec 属性词 → 标题后段 + 五点第5条
│
├── P5: 搜索量 Top 21-40，前端未覆盖 → Backend Keywords
│
├── P6: 长尾场景词 + VOC词组（未进五点的）→ Description前500字符 + Subject Matter
│
├── P7: 竞品痛点的反面表述 → 五点第4条
│
└── P8: 特殊词汇（拼写错误/外语/不带空格）→ Backend Keywords 末尾
```

---

## 五、各品类关键词埋词特殊规则

### 5.1 电子/3C 配件类

- 型号兼容词（iPhone 15/14/13/12）按从新到旧排序，放入标题和 Bullet Points
- 芯片/接口规格词（USB 3.2、Bluetooth 5.3）必须精确，不可泛化
- 后台搜索词补充旧型号长尾（iPhone 11/X/SE 系列较冷门，放后台即可）

### 5.2 服装/鞋帽类

- 尺码相关词（S/M/L/XL、plus size、petite、tall）优先放 Item Specifics
- 颜色组合词（heather gray、navy blue）可作为同义词分别放后台
- 风格词（vintage、Y2K、streetwear）放 Bullet Points + Description

### 5.3 家居/厨房类

- 容量单位同义词（32 oz / 1 liter / 1000ml）在后台都要填
- 材质认证词（BPA-free、food-grade、FDA-registered）放五点 + 后台
- 场景词（meal prep、camping、office）放五点第3条 + Subject Matter

### 5.4 健康/保健类（FTC 双重合规）

- 避免任何功效词，改用材质/成分词（不写"提高免疫力"，写"Vitamin C 1000mg"）
- 认证词（Non-GMO、NSF Certified、USDA Organic）具有极高权重，必须放标题
- 后台避免任何疾病词，使用功能性描述

### 5.5 儿童/婴儿类

- 年龄段词（Ages 3-8、Toddler 2-4 Years）必须精确，放标题 + Item Specifics
- 安全认证词（ASTM F963、EN71、BPA-free、CPSC）极高权重，放五点前两条
- 情境词（nursery、playroom、car seat compatible）放 Subject Matter

---

## 六、关键词覆盖率自检清单

生成 Listing 文案后，逐项确认关键词分配是否合理：

- [ ] **标题前 40 字符**：含搜索量 Top 1 词？
- [ ] **五点第 1-2 条**：含 Top 3-8 搜索量词（自然植入句子）？
- [ ] **后台搜索词**：与标题/五点无重叠？已填拼写变体和同义词？
- [ ] **Subject Matter**：5条已填，内容与 Backend Keywords 不重复？
- [ ] **Description 前 500 字符**：含 2-3 个额外场景词？
- [ ] **字节计算**：后台搜索词字节数 ≤ 500？
- [ ] **Target Audience / Intended Use**：已按产品实际用途准确填写？
- [ ] **移动端优先**：最重要的购买决策信息在五点前 2 条？
