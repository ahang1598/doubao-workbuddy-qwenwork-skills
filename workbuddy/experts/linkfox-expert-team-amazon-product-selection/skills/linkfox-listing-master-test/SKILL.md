---
name: linkfox-listing-master-test
description: "Amazon Listing 全能生成器。输入竞品 ASIN，一键生成 Listing 文案（标题 + 五点描述 + 产品描述 + 后台搜索词）与 A+ 图片。支持三种模式：listing+图片 / 仅 listing / 仅图片。自动关键词分层、BAF 文案框架、Rufus 语义适配、A+ 版式复刻、卖点一致性校验与合规检测。用户说\"写 listing\"、\"改 listing\"、\"复刻竞品 listing\"、\"生成 A+ 图\"、\"listing 打分\"、\"亚马逊文案优化\"时触发。"
---

# Listing Master

输入竞品 ASIN → 模式选择 → 数据采集 → 双线并行生成（文案 + 图片） → 合规校验 → 输出完整报告。

## 前置依赖

- **LINKFOX_AGENT_API_KEY**：所有 linkfox 数据/生图能力均通过该环境变量鉴权。未配置时提示用户前往 https://skill.linkfox.com/linkfoxskills/guide.htm 申请，并 `export LINKFOX_AGENT_API_KEY=<your-key>`。**禁止在 skill 内硬编码任何 Token。**
- **数据采集 skill（同级 linkfoxagent-v2）**：
  - `linkfox-amazon-product-detail` —— 商品详情（标题、五点、描述、A+ 内容、主图/附图 URL、品牌、价格、类目）
  - `linkfox-sif-asin-keywords` —— ASIN 关键词（搜索量、自然/广告排名、月搜索量）
- **线上 AI 生图 skill（同级 linkfoxagent-v2）**：`linkfox-aigc-imagegen` —— A+ 图片生成（见 C.IMG.4）。
- **商品图须为可访问 URL**：本 skill 含图片模式时，用户提供的商品图（1-6 张）必须先由调用方/上游上传为可公网访问的图片 URL，再传入生图步骤（线上生图 skill 的参考图入参为 `imageUrls`，不接受本地 base64）。
- **Python 3 + Pillow**：图片拼接与切割。如未安装 Pillow：`python3 -m pip install Pillow`。

---

## 知识库索引

> **按需加载，不要一次性全部读入。**
> **工具源码禁止循环 Read**：`scripts/keyword_checker.py` 等工具脚本视为黑盒 CLI；最多允许读取一次用法或已缓存源码片段。看到 "File unchanged since last Read" 后必须停止 Read，直接执行命令或按已有结果继续，禁止围绕相邻行号反复读取脚本源码。
> **用户可见文案去技术化**：聊天进度不要暴露 `Phase C/D`、`约束`、脚本路径等内部术语；合规检查完成后统一说“合规检查完成，正在生成报告。”

| 文件 | 读取时机 | 用途 |
|------|---------|------|
| `references/amazon-platform-rules.md` | Phase C 开始时必读 | 平台合规概览 |
| `references/keyword-embedding-strategy.md` | C.1 执行前必读 | 字段权重、搜索量分段分配规则、去重逻辑 |
| `references/title-format-rules.md` | C.2 执行前必读 | 标题结构模板、各类目字符限制 |
| `references/baf-framework.md` + `references/rufus-semantic-rules.md` | C.3 执行前必读（两个一起） | BAF 倒叙法则 + Rufus 意图匹配 |
| `references/compliance-banned-words.md` | C.X 执行前必读 | 违禁词清单、商标侵权判定 |
| `references/image-layout-high.md` / `medium` / `low` | C.IMG.2 任务A 执行前按相似度读取 | 版式分析提示词（高/中/低相似度） |
| `references/image-selling-points-clothing.md` / `general` | C.IMG.2 任务B 执行前按品类读取 | 商品卖点提取提示词（服装/通用） |
| `templates/output-format.md` | Phase D 执行前必读 | 最终输出格式模板 |

---

## Phase A — 输入识别与模式选择

### A.1 生成模式

向用户确认生成模式（三选一）：

| 模式 | 执行线路 | 说明 |
|------|---------|------|
| **Listing + 图片**（默认） | Track 1 + Track 2 | 同时生成文案和 A+ 图片 |
| **仅 Listing** | Track 1 | 只生成文案，不生成图片 |
| **仅图片** | Track 2 | 只生成 A+ 图片，不生成文案 |

### A.2 复刻 vs 优化

根据用户是否提供**自己的商品图**自动判断工作模式：

| 条件 | 模式 | 含义 |
|------|------|------|
| 用户上传了商品图（1-6张） | **复刻模式** | 为新商品参照竞品生成全新 Listing 和/或 A+ 图 |
| 用户未上传商品图 | **优化模式** | 优化现有 ASIN 的 Listing 文案（图片线路不可用） |

> 优化模式下，如果用户选择了含图片的模式，提示：「优化模式需要提供商品图才能生成 A+ 图片，请上传 1-6 张您的商品图，或切换为"仅 Listing"模式。」

### A.3 竞品 ASIN 输入

从用户消息中提取 ASIN（10 位字母数字，如 `B0XXXXXXXXX`，或从 Amazon 商品链接中提取）。

**站点映射：**

| 用户说 | `marketplace` | 域名 |
|--------|---------------|------|
| 美国/US/默认 | US | amazon.com |
| 英国/UK | UK | amazon.co.uk |
| 德国/DE | DE | amazon.de |
| 日本/JP | JP | amazon.co.jp |
| 加拿大/CA | CA | amazon.ca |

如果未识别到 ASIN，向用户询问：
> 「请提供竞品 ASIN（如 B0C1XXXXXXX），我将为您生成完整的 Amazon Listing。可提供 1-3 个 ASIN，数据越多效果越好。」

### A.4 图片生成参数（含图片模式时确认）

| 参数 | 选项 | 默认值 |
|------|------|--------|
| 复刻相似度 | 低 / 中 / 高 | 高 |
| 输出分辨率 | 2K / 4K | 2K |

可不问直接用默认值。

---

## Phase B — 数据采集

向用户说明：
> 「正在采集商品数据和市场关键词，请稍候（通常需要 2-4 分钟）...」

数据采集通过同级 linkfoxagent-v2 数据 skill 完成，鉴权统一读取环境变量 `LINKFOX_AGENT_API_KEY`。按以下步骤采集并在本地汇总：

**步骤 G1 — 商品详情**：调用 `linkfox-amazon-product-detail`，获取亚马逊 `{marketplace}` 站下列 ASIN 的商品详情（标题、五点描述、产品描述、A+ 内容、主图 URL、附图 URL 列表、品牌、价格、类目）：
```
{asins}
```

**步骤 G2 — 关键词**：调用 `linkfox-sif-asin-keywords`，获取上述全部 ASIN 的关键词数据（含搜索量、自然排名、广告排名、月搜索量）。

**步骤 G3 — 标题分词**：对 G1 返回的全部 ASIN 商品标题做分词，统计核心词、场景词、属性词及词频（此步由模型对 G1 文本直接分析，无需额外接口）。

将上述结果完整汇总，供后续 Phase C 使用：
- 全部 ASIN 的：标题、五点描述、产品描述、A+ 内容全文、主图 URL、附图 URL 列表、品牌、价格、类目
- 全部 ASIN 的关键词列表（含搜索量、自然排名）
- 标题分词统计结果（词频表）

### 成功条件

| 必要字段 | 最低要求 |
|---------|---------|
| ASIN 商品详情 | ≥ 1 个 ASIN 含标题 + 五点描述 |
| 关键词数据（listing 模式需要） | ≥ 10 个关键词含搜索量 |
| 标题分词 | 有输出即可 |
| A+ 图片 URL（图片模式需要） | ≥ 1 个 ASIN 含 A+ 图片 URL |

满足以上（根据所选模式判断必要字段） → 进入 Phase C。

### B.+ 下载竞品 A+ 图片（含图片模式时执行）

从 G1 返回的数据中提取各 ASIN 的 A+ 图片 URL 列表，将所有图片下载到临时工作目录（中间产物可写 `/tmp`）。

```bash
mkdir -p /tmp/listing_master
curl -o /tmp/listing_master/aplus_01.jpg "{A+图片URL_1}"
curl -o /tmp/listing_master/aplus_02.jpg "{A+图片URL_2}"
# ...
```

记录下载的图片路径列表，后续 Track 2 使用。

### 失败处理

1. 若某步返回空或超时 → 原样重试一次
2. 重试后仍失败 → 停止，向用户说明
3. 数据 skill 返回 401 → 提示检查 `LINKFOX_AGENT_API_KEY`

**重试预算：每个数据步骤最多 2 次调用（首次 + 1 次重试）。**

---

## Phase C — 内容生成（双线并行）

> **⚠️ 一次生成原则**：直接生成最终版文案，不要先出草稿再重写。在生成前就严格遵守字符/字节限制，避免生成后再修正。

> **双线结构**：C.1 为共享基础步骤，完成后 Track 1（文案）和 Track 2（图片）**通过 Agent 子代理真正并行执行**。根据 Phase A 选择的模式，仅执行对应线路。

> **并行执行架构（Listing + 图片模式）**：
> ```
> 主 Agent
> ├─ C.1 关键词提取（共享基础）
> │
> ├──→ Agent(Track1)  ──► C.2-C.5.5 文案生成 + C.X.1 合规检查
> │         ↓ 返回: listing 全文 + 覆盖率 + 合规结果
> ├──→ Agent(Track2)  ──► C.IMG.1-5 图片生成 + C.X.2 图片合规
> │         ↓ 返回: 图片路径 + T2 卖点 + 图片合规结果
> │
> ├─ C.X.3 卖点一致性校验（需两线结果）
> └─ Phase D 输出报告
> ```
> 关键：**在一条消息中同时发出两个 Agent tool call**，让它们并行运行。

收到数据后，**读取 `references/amazon-platform-rules.md`**。

### C.1 关键词提取与布局 [共享基础]

> **必读 `references/keyword-embedding-strategy.md`**

> **仅图片模式可跳过此步骤。**

从竞品数据中提取高价值关键词：

1. 汇总所有竞品的关键词，按搜索量降序排列
2. 统计每个关键词被几个竞品覆盖
3. 按 keyword-embedding-strategy.md §4 的分段规则分配到字段：

| 搜索量排名 | 分配字段 | 说明 |
|-----------|---------|------|
| Top 1-2 | 标题前 40 字符 | 品类定义词 |
| Top 3-8 | 五点第 1-2 条 | 中高搜索量功能词 |
| Top 9-20 | 五点第 3-5 条 | 自然植入句子 |
| Top 21-40 | 后台搜索词 | 前端未覆盖词 |
| 长尾场景词 | 产品描述 + Subject Matter | 低搜索量高精准度 |

4. 标注特征标签：`[属性]`（材质/尺寸/认证）、`[场景]`（使用场景/人群）
5. 标注报告层级：标题词→「核心词」，五点/描述词→「长尾词」，后台词→「补充覆盖词」

结果保存为 `keyword_layers`，供后续步骤和 Phase D 报告使用。

---

### C.DISPATCH 并行派发（Listing + 图片模式）

> **仅 Listing + 图片模式执行此步骤。** 仅 Listing 或仅图片模式直接跳到对应 Track 串行执行即可。

C.1 完成后，主 Agent **在同一条消息中**发出两个 Agent tool call，分别派发 Track 1 和 Track 2。

#### 派发前：预读取共享 reference 文件

主 Agent 在派发前读取以下文件内容，**作为文本嵌入到子代理的 prompt 中**（子代理无法自行读取 reference 文件）：

**Track 1 需要的 reference（主 Agent 预读并嵌入）：**
- `references/amazon-platform-rules.md`
- `references/title-format-rules.md`
- `references/baf-framework.md`
- `references/rufus-semantic-rules.md`
- `references/compliance-banned-words.md`
- `references/keyword-embedding-strategy.md`

**Track 2 需要的 reference（主 Agent 预读并嵌入）：**
- `references/image-layout-high.md`（或 medium/low，取决于相似度）
- `references/image-selling-points-general.md`（或 clothing，取决于品类）
- `references/compliance-banned-words.md`（图片合规部分）

#### Agent(Track 1) — 文案生成 Prompt 模板

```
你是 Listing Master 的文案生成子代理。请根据以下数据和规则，执行 C.2→C.5.5 + C.X.1 全流程。

## 输入数据

### 竞品商品详情
{Phase B 返回的竞品标题、五点、描述、品牌、价格、类目等}

### 关键词分层表 (keyword_layers)
{C.1 生成的完整 keyword_layers}

### Reference 规则文件
{主 Agent 预读的 6 个 reference 文件内容，逐一嵌入}

## 执行步骤

按照以下顺序生成，一次到位，不出草稿：
1. C.2 标题生成（遵守 title-format-rules）
2. C.3 五点描述（遵守 BAF + Rufus）
3. C.4 产品描述
4. C.5 后台搜索词
5. C.5.5 Subject Matter
6. C.X.1 文案合规检查（调用 keyword_checker.py 脚本）

脚本路径：`{skill_path}/scripts/keyword_checker.py`
Python 路径：`python3`
执行约束：不要反复 Read `keyword_checker.py` 的实现细节；该脚本按固定 CLI 调用即可。若已读过脚本或 Read 返回文件未变化，立刻停止读取并继续生成/校验流程。
对用户展示：不要说 `约束/Phase`，合规检查完成后统一表述为“合规检查完成，正在生成报告。”

## 返回格式（严格 JSON）

请在最终输出中包含一个 ```json 代码块，格式如下：
{
  "title": "完整标题",
  "title_char_count": 数字,
  "bullets": ["五点1", "五点2", "五点3", "五点4", "五点5"],
  "description": "完整产品描述",
  "description_char_count": 数字,
  "search_terms": "后台搜索词",
  "search_terms_bytes": 数字,
  "subject_matter": ["主题1", "主题2", ...],
  "compliance": {
    "trademark_check": "PASS/FAIL",
    "banned_words_check": "PASS/FAIL",
    "title_length_check": "PASS/FAIL",
    "search_terms_bytes_check": "PASS/FAIL",
    "description_length_check": "PASS/FAIL",
    "medical_claims_check": "PASS/FAIL",
    "cta_check": "PASS/FAIL",
    "dedup_check": "PASS/FAIL",
    "issues": ["问题描述1", ...]
  },
  "keyword_coverage": {
    "total": 数字,
    "covered": 数字,
    "rate": "百分比",
    "uncovered_keywords": ["词1", "词2", ...],
    "field_coverage": {
      "title": {"total": 数字, "covered": 数字},
      "bullets": {"total": 数字, "covered": 数字},
      "description": {"total": 数字, "covered": 数字},
      "search_terms": {"total": 数字, "covered": 数字}
    }
  }
}
```

#### Agent(Track 2) — 图片生成 Prompt 模板

```
你是 Listing Master 的图片生成子代理。请根据以下数据和规则，执行 C.IMG.1→C.IMG.5 + C.X.2 全流程。

## 输入数据

### 竞品 A+ 图片路径
{Phase B 下载的图片路径列表}

### 用户商品图 URL
{用户提供的 1-6 张商品图的可访问 URL（已由上游上传）}

### 生成参数
- 复刻相似度：{高/中/低}
- 输出分辨率：{2K/4K}

### Reference 规则文件
{主 Agent 预读的 reference 文件内容}

## 执行步骤

1. C.IMG.1 拼接竞品 A+ 参考图
   脚本：`{skill_path}/scripts/stitch_images.py`
2. C.IMG.2 并行分析（版式分析 T1 + 卖点提取 T2）
   → 你可以用并行 tool call 同时做两个分析
3. C.IMG.3 整合生图提示词（含目标长宽像素）
4. C.IMG.4 调用线上生图 skill（linkfox-aigc-imagegen）
5. C.IMG.5 切割生成图片
   脚本：`{skill_path}/scripts/split_images.py`
6. C.X.2 图片合规检查

Python 路径：`python3`

## 返回格式（严格 JSON）

请在最终输出中包含一个 ```json 代码块，格式如下：
{
  "generated_long_image": "完整长图文件路径",
  "split_images": ["split_01.jpg路径", "split_02.jpg路径", ...],
  "generation_params": {
    "similarity": "high/medium/low",
    "resolution": "2K/4K",
    "provider": "模型枚举值",
    "target_pixels": "宽x高",
    "stitch_mode": "vertical/grid"
  },
  "t1_layout_summary": "T1 版式分析摘要",
  "t2_selling_points": {
    "product_name": "商品名称",
    "target_audience": "目标受众",
    "selling_points_description": "卖点描述",
    "craftsmanship_details": "工艺细节",
    "usage_method": "使用方法",
    "category_path": "类目路径"
  },
  "image_compliance": {
    "image_text_ratio": "PASS/WARN",
    "prohibited_elements": "PASS/WARN",
    "mobile_readability": "PASS/WARN",
    "product_clarity": "PASS/WARN",
    "brand_compliance": "PASS/WARN",
    "issues": ["问题描述1", ...]
  }
}
```

#### 派发执行

完成 reference 预读后，**在同一条消息中**发出以下两个 tool call：

```python
# 伪代码 — 实际使用 Agent tool
Agent(
    description="Track1 文案生成",
    prompt="{上面的 Track 1 prompt，替换所有占位符为实际数据}"
)
Agent(
    description="Track2 图片生成",
    prompt="{上面的 Track 2 prompt，替换所有占位符为实际数据}"
)
```

两个 Agent 并行执行，主 Agent 等待两者均返回后进入汇合阶段。

---

### ══ Track 1：Listing 文案生成 ══

> **仅图片模式跳过整个 Track 1。**

### C.2 标题生成

> **必读 `references/title-format-rules.md`**

- 大多数类目 ≤ 200 字符；服装 ≤ 125 字符（用 `len()` 精确计算）
- 未指定品牌时，标题开头不放品牌名，直接以核心关键词起始
- Top 1-2 品类定义词前置，占标题前 40 字符
- 属性修饰词和场景限定词自然衔接，不堆砌
- 撰写后精确统计字符数

### C.3 五点描述生成

> **必读 `references/baf-framework.md`**，紧接着读 **`references/rufus-semantic-rules.md`**（两个文件必须都读，缺一不可）

**分条关键词分配（与 BAF 五维度对齐）：**

| 条目 | 嵌入的关键词类型 | BAF 维度 |
|------|---------------|---------|
| 第 1 条 | 核心功能词 + 次高流量词（Top 3-5） | 核心功能 |
| 第 2 条 | 材质/认证词 + 安全相关词 | 材质安全 |
| 第 3 条 | `[场景]` 标签词 + 人群词 | 适用场景 |
| 第 4 条 | 易用性词 + 差异化竞争词 | 易用性 |
| 第 5 条 | 规格词 + 套装内容词 + 配件词 | 套装售后 |

**核心要点：**
- 每条以 **粗体 BENEFIT** 开头，紧跟 Advantage 说明，Feature 参数收尾
- **自然度优先于覆盖率**：关键词必须在句子中作为有意义的语法成分出现，读起来像人话。禁止生硬拼接和末尾罗列。无法自然融入的词降级至后台搜索词。前端覆盖率 80-90% 是健康区间，不必追求 100%
- 不使用任何竞品品牌词

### C.4 产品描述生成

- ≤ 2000 字符
- 不是五点的复制，而是场景化叙事展开
- 无品牌故事时：侧重使用场景、规格参数、适用人群
- 禁止：联系方式、官网链接、评价引用、促销信息

### C.5 后台搜索词生成

- ≤ 500 字节（`len(search_terms.encode('utf-8'))`）
- 严禁放入标题和五点中已出现的词
- 单个空格分隔，不用逗号或分号
- 不使用竞品品牌词、ASIN 编号
- 可填入：同义词、拼写错误、缩写别称、外语翻译词、不带空格的复合词
- 超限时按搜索量从低到高截掉

### C.5.5 Subject Matter（如适用）

- 每条 ≤ 50 字节，最多 5 条
- 从 keyword_layers 中取后台搜索词放不下的中等搜索量长尾词
- 与后台搜索词不重复
- 每条应是人可理解的主题短语（如 "reusable lint roller for cat owners"），而非后台词的堆叠

---

### ══ Track 2：A+ 图片生成 ══

> **仅 Listing 模式跳过整个 Track 2。**
>
> **前置条件**：用户已提供商品图 URL（1-6张，已由上游上传为可访问 URL）且 Phase B 已下载竞品 A+ 图片。

### C.IMG.1 拼接竞品 A+ 参考图

将 Phase B 下载的竞品 A+ 图片拼接为一张完整参考长图：

```bash
python3 {skill_path}/scripts/stitch_images.py \
  --images /tmp/listing_master/aplus_01.jpg /tmp/listing_master/aplus_02.jpg ... \
  --output /tmp/listing_master/stitched_aplus.jpg \
  --layout auto
```

**拼接模式：**
- `auto`（默认）：3 张以内用 vertical（垂直），4 张以上用 grid（网格）
- `vertical`：上下排列，适合同一 ASIN 的 A+ 图
- `grid`：网格排列，适合多来源参考图

脚本输出：
- 拼接后的图片文件
- **元数据文件**（`stitched_aplus.meta.json`）：记录拼接方式、每张图的坐标和大小
- 尺寸信息：`WIDTH=xxx HEIGHT=yyy RATIO=z.zz`

记录 **w**、**h**、**ratio** 和 **meta.json 路径**，后续步骤需要。

### C.IMG.2 并行分析

以下两个任务同时进行：

#### 任务A — 版式分析（得到 T1）

根据 Phase A 选择的**复刻相似度**，阅读对应的提示词文件：

| 相似度 | 提示词文件 | 效果 |
|--------|-----------|------|
| 低 | `references/image-layout-low.md` | 只提取基础骨架，最大创作自由度 |
| 中 | `references/image-layout-medium.md` | 提取主要结构和动线，允许细节变化 |
| 高（默认） | `references/image-layout-high.md` | 严格还原版式，精确复刻 |

**输入**：C.IMG.1 拼接好的长图
**操作**：按照对应提示词的要求，对长图进行版式分析
**输出 T1**：版式描述字符串

#### 任务B — 商品卖点提取（得到 T2）

首先**自动判断商品A的品类**：
- 观察商品A的图片内容
- 判断是否为**服装/鞋帽/配饰类**
- **服装类** → 阅读 `references/image-selling-points-clothing.md`
- **非服装类** → 阅读 `references/image-selling-points-general.md`

**输入**：用户提供的商品A图片（1-6张，可用其 URL 让模型读取）
**操作**：按照对应提示词要求，分析商品图并提取卖点信息
**输出 T2**：符合对应 JSON Schema 的结构化卖点数据

> **重要**：T2 提取的卖点将在 C.X 中与 Track 1 的五点描述做交叉校验，确保图文一致性。

### C.IMG.3 整合生图提示词

将 T1 和 T2 拼合为完整的生图提示词。根据相似度级别调整措辞强度。

> **长图比例处理**：线上生图 skill 的 `aspectRatio` 仅支持标准比例（1:1 / 16:9 / 9:16），无法表达 A+ 长图的极端比例。因此**不依赖 aspectRatio**，而是在提示词中**显式写出目标长宽像素**。目标尺寸取 C.IMG.1 拼接长图的 `w×h`（如需控制成本可等比缩放到宽 1000-1500px，高按比例换算），并在生图指令中加入一句：
> 「请生成一张宽 {W}px、高 {H}px 的完整长图（严格保持该宽高比，纵向连续排版）。」

#### 高相似度（默认）

```
【版式复刻要求】
{T1 的完整内容 — 版式描述字符串}

【商品信息与核心卖点】
商品名称：{从T2提取}
目标受众：{从T2提取}
核心卖点：{从T2提取关键卖点，转化为自然语言}
工艺/材质细节：{从T2提取}

【目标尺寸】
请生成一张宽 {W}px、高 {H}px 的完整长图（严格保持该宽高比，纵向连续排版）。

【生图指令】
请严格按照上述【版式复刻要求】中描述的空间分区、视觉层次和构成元素，以提供的商品图作为产品主体素材，结合【商品信息与核心卖点】中的文案内容，生成一张完整的 Amazon A+ 商品详情长图。
- 版式骨架必须与参考版式一致（分区比例、图文布局、视觉动线）
- 产品主体使用商品A的图片
- 文案内容使用商品A的卖点信息
- 整体风格专业、高端，符合Amazon A+页面标准
```

#### 中相似度

```
【版式参考】
{T1 的完整内容 — 版式结构描述}

【商品信息与核心卖点】
商品名称：{从T2提取}
目标受众：{从T2提取}
核心卖点：{从T2提取关键卖点，转化为自然语言}
工艺/材质细节：{从T2提取}

【目标尺寸】
请生成一张宽 {W}px、高 {H}px 的完整长图（严格保持该宽高比，纵向连续排版）。

【生图指令】
参考上述【版式参考】中的分区节奏和视觉动线方向，以提供的商品图作为产品主体素材，生成一张 Amazon A+ 商品详情长图。
- 整体分区结构和阅读节奏借鉴参考版式
- 具体的排列方式、元素数量和细节可以自由调整
- 产品主体使用商品A的图片
- 文案内容使用商品A的卖点信息
- 整体风格专业、高端，符合Amazon A+页面标准
```

#### 低相似度

```
【版式启发】
{T1 的完整内容 — 基础骨架描述}

【商品信息与核心卖点】
商品名称：{从T2提取}
目标受众：{从T2提取}
核心卖点：{从T2提取关键卖点，转化为自然语言}
工艺/材质细节：{从T2提取}

【目标尺寸】
请生成一张宽 {W}px、高 {H}px 的完整长图（严格保持该宽高比，纵向连续排版）。

【生图指令】
以上述【版式启发】作为灵感参考，以提供的商品图作为产品主体素材，自由设计一张 Amazon A+ 商品详情长图。
- 大致遵循参考的图文区域分布，但具体设计完全自由发挥
- 产品主体使用商品A的图片
- 文案内容使用商品A的卖点信息
- 追求独特的视觉表达，避免与参考图雷同
- 整体风格专业、高端，符合Amazon A+页面标准
```

### C.IMG.4 调用线上生图 skill（linkfox-aigc-imagegen）

本步骤调用同级线上 AI 生图技能 **`linkfox-aigc-imagegen`** 完成生图（替代原直连生图 API 的方式）。底层端点为 `POST ${LINKFOX_TOOL_GATEWAY}/aigc/imageGen`（基础域名从环境变量 `LINKFOX_TOOL_GATEWAY` 读取），鉴权用环境变量 `LINKFOX_AGENT_API_KEY`。

#### 选择模型（provider）

根据 C.IMG.1 得到的 ratio（h/w）选择模型：

| 条件 | provider | 说明 |
|------|----------|------|
| h/w > 4（超长图） | `BANANA_2` | 香蕉2，支持更高分辨率，适合极端长图 |
| h/w ≤ 4 | `BANANA_PRO`（默认） | 香蕉Pro，综合效果最好 |

> 备注：`BANANA`（基础版）仅支持 1K，不用于 2K/4K 输出。

#### 调用方式

调用 `linkfox-aigc-imagegen` 的脚本，传入 JSON 参数：

```bash
python3 {linkfox-aigc-imagegen}/scripts/aigc_imagegen.py '{
  "imageUrls": ["{商品图URL_1}", "{商品图URL_2}"],
  "prompt": "{C.IMG.3 整合后的完整提示词，已含目标长宽像素}",
  "provider": "BANANA_PRO",
  "outputNum": 1,
  "resolution": "2K"
}'
```

参数说明：
- `imageUrls`：用户商品图的可访问 URL 列表（参考图，必填，至少 1 张）。**不再使用本地 base64。**
- `prompt`：C.IMG.3 整合后的提示词，长图比例已通过其中的「目标尺寸」像素表达。
- `provider`：按上表选择（`BANANA_PRO` / `BANANA_2`）。
- `outputNum`：默认 `1`。
- `resolution`：`2K` 或 `4K`（按 Phase A.4）。
- **不传 `aspectRatio`**：长图比例由 prompt 中的像素尺寸控制（线上 skill 的 aspectRatio 仅支持 1:1/16:9/9:16，不足以表达极端长图）。

#### 解析响应

线上 skill 返回结构（关键字段）：

```json
{
  "taskId": "任务ID",
  "status": 3,
  "resultList": [
    {"id": "资源ID", "url": "https://...生成图片URL", "type": "..."}
  ],
  "costToken": 123
}
```

- `status`：`3`=成功，`4`=失败。
- 成功：从 `resultList[].url` 取生成图片 URL。
- 失败：读 `errorMsg`；若 HTTP 401 / 业务 `errcode=401`，提示检查 `LINKFOX_AGENT_API_KEY`。失败最多重试 3 次。

#### ⚠️ 上线前验证（首次部署后请实测）

1. **模型映射验证**：上表的 `BANANA_PRO`（h/w≤4）/ `BANANA_2`（h/w>4）是按命名对应原方案 nano pro / nano2 推断的映射，尚未在真实数据上验证。请先用 1-2 个真实竞品 ASIN 跑通整条图片线路，确认这两个模型对「极端长图 + prompt 像素尺寸」的实际还原效果，再据此固化或调整 provider 选择。
2. **aspectRatio 兜底策略**：线上 `linkfox-aigc-imagegen` 接口文档将 `aspectRatio` 标为必填（默认 1:1，仅支持 1:1/16:9/9:16）。本 skill 按设计**不传该字段**（底层脚本透传 JSON，不会强制补默认值），长图比例完全由 C.IMG.3 prompt 中的目标长宽像素控制。若实测发现服务端强制要求该字段，则退而传入与目标比例**最接近的 `9:16`**，但长图实际比例仍以 prompt 像素尺寸为准。

### C.IMG.5 切割生成图片

从响应的 `resultList[].url` 获取生成图片 URL，下载到本地，然后按 C.IMG.1 的拼接方式反向切割：

```bash
curl -o /tmp/listing_master/generated_aplus.jpg "{resultList[0].url}"
python3 {skill_path}/scripts/split_images.py \
  --image /tmp/listing_master/generated_aplus.jpg \
  --meta /tmp/listing_master/stitched_aplus.meta.json \
  --output-dir /tmp/listing_master/split/
```

脚本会：
- 读取拼接元数据
- 按比例映射到生成图片的实际尺寸
- 裁剪出每一块独立图片
- 输出到指定目录

> **最终交付**：切割后的独立图片与完整长图属于交付物，应放到会话目录 `<cwd>/linkfox/<YYYY-MM-DD>/<session>/media/` 下（`<session>` 取自环境变量 `SESSION_ID`），便于事后检索；`/tmp` 仅用于下载、拼接、切割等中间产物。

---

### ══ 两线汇合 ══

> **并行模式下**：主 Agent 等待两个子代理均返回后，从它们的返回 JSON 中提取结果，进入汇合阶段。
>
> - 从 **Agent(Track1)** 返回中提取：`title`, `bullets`, `description`, `search_terms`, `subject_matter`, `compliance`, `keyword_coverage`
> - 从 **Agent(Track2)** 返回中提取：`generated_long_image`, `split_images`, `t2_selling_points`, `image_compliance`, `generation_params`, `t1_layout_summary`
>
> **C.X.1 和 C.X.2 已由子代理在各自线路中完成**，主 Agent 只需执行 C.X.3（卖点一致性校验）。如子代理返回中有合规问题（`issues` 非空），主 Agent 应在报告中标注。

### C.X 合规检查（必须执行）

> **必读 `references/compliance-banned-words.md`**

两线输出完成后，执行以下检查。**这不是建议，是强制要求。**

> **⚡ 并行模式注意**：C.X.1 和 C.X.2 已由子代理执行完毕并随返回值带回。主 Agent 在此阶段仅需：
> 1. 检查子代理返回的合规结果是否有未修复的问题
> 2. 执行 C.X.3 卖点一致性校验（这是唯一需要两线数据交叉的步骤）
> 3. 如有严重合规问题，决定是否需要回退修改

#### C.X.1 文案合规检查（含 Listing 模式时执行）

文案草稿完成后，**必须执行以下检查**——跳过将导致 D1 维度直接失分。

**一步完成：写入临时文件 + 执行检查**

```bash
python3 -c "
import json, os
listing = {
  'title': '''此处替换为生成的标题''',
  'bullets': ['''五点1''', '''五点2''', '''五点3''', '''五点4''', '''五点5'''],
  'description': '''此处替换为产品描述''',
  'search_terms': '''此处替换为后台搜索词'''
}
keywords = ['''关键词1''', '''关键词2''', '''关键词3''']
open('/tmp/listing_draft.json','w').write(json.dumps(listing, ensure_ascii=False))
open('/tmp/keywords.txt','w').write('\n'.join(keywords))
os.system('python3 {skill_path}/scripts/keyword_checker.py --listing /tmp/listing_draft.json --keywords /tmp/keywords.txt --mode full --json')
"
```

**解析输出并修正：**

| 输出字段 | 处理方式 |
|---------|---------|
| `coverage` 中 `used=false` 的词 | 高搜量 → 追加至后台搜索词；中搜量 → 尝试嵌入五点 |
| `trademark_issues` | 立即替换为合规表达或删除 |
| `banned_issues` | 立即替换或删除 |
| `title_length.passed=false` | 截断标题 |
| `search_terms_bytes.passed=false` | 按搜索量从低到高截掉词 |
| `description_length.passed=false` | 截断描述 |
| `search_terms_dedup` | 从后台搜索词中移除重复词 |

> **脚本执行失败时的兜底：** 手动逐一检查关键词覆盖、品牌词、违禁词。

#### C.X.2 图片合规检查（含图片模式时执行）

对 C.IMG.5 生成的图片进行以下检查（人工审视 + 规则比对）：

| 检查项 | 标准 | 判定依据 |
|-------|------|---------|
| A+ 图文比例 | 推荐图片区域 ≥ 70%，文字 ≤ 30% | 观察生成图中文字/图片面积占比 |
| 违规元素 | 无水印、无价格标签、无 "Best Seller" 徽章、无站外链接 | 逐一检查生成图内容 |
| 移动端适配 | 核心信息在手机屏幕宽度内可辨认，文字不过小 | 评估关键文字尺寸 |
| 产品主体清晰度 | 商品图清晰可辨，不模糊、不变形 | 观察产品在生成图中的还原度 |
| 品牌合规 | 不出现竞品品牌标识或 logo | 检查是否残留竞品元素 |

对不达标项记录问题和修复建议，纳入 Phase D 合规检查报告。

#### C.X.3 卖点一致性校验（Listing + 图片模式时执行）

将 Track 2 提取的 **T2 卖点** 与 Track 1 生成的**五点描述核心卖点**做交叉比对：

**比对矩阵：**

| T2 卖点维度 | 对应五点条目 | 一致性状态 |
|------------|------------|-----------|
| 核心功能/产品名称 | 第 1 条（核心功能） | ✅ 一致 / ⚠️ 偏差 / ❌ 缺失 |
| 材质/工艺细节 | 第 2 条（材质安全） | ✅ / ⚠️ / ❌ |
| 使用场景/目标人群 | 第 3 条（适用场景） | ✅ / ⚠️ / ❌ |
| 功能体验/易用性 | 第 4 条（易用性） | ✅ / ⚠️ / ❌ |
| 规格/配件/类目路径 | 第 5 条（套装售后） | ✅ / ⚠️ / ❌ |

**判定规则：**
- **✅ 一致**：T2 卖点与五点条目的核心信息匹配
- **⚠️ 偏差**：T2 提取了某维度的信息，但五点中的表述侧重不同 → 建议调整五点或图片文案使其统一
- **❌ 缺失**：T2 提取的核心卖点未在五点中体现，或五点的核心卖点未在图片中体现 → 建议补充

一致性结果纳入 Phase D 输出报告。

---

## Phase D — 输出报告

> **⚠️ 前置检查**：在输出报告前，确认 C.X 各项检查已执行。如果未执行，现在立即回到 C.X 执行。

> **必读 `templates/output-format.md`**

根据所选模式输出对应板块。**Listing + 图片模式**输出全部 6 个板块，其他模式输出相关板块。

输出一份完整的 Markdown 报告，板块之间用 `---` 分隔，每个板块用 `#` 一级标题标识。

> 若最终报告正文较长（> 400 字），按项目规范走 `linkfox-report-generator` 生成交付文件，默认 `format: html`；不要在对话里拼接长文。

---

# Listing 文案

> **仅 Listing 和 Listing + 图片模式输出。**

### 标题 (Title)
[完整标题] — 字符数：{N} / {200 或 125}

### 五点描述 (Bullet Points)
1. **[BENEFIT]** [Advantage，1-2句] [Feature 参数收尾，1句]
2. **[BENEFIT]** [Advantage，1-2句] [Feature 参数收尾，1句]
3. **[BENEFIT]** [Advantage，1-2句] [Feature 参数收尾，1句]
4. **[BENEFIT]** [Advantage，1-2句] [Feature 参数收尾，1句]
5. **[BENEFIT]** [Advantage，1-2句] [Feature 参数收尾，1句]

### 产品描述 (Product Description)
[完整产品描述] — 字符数：{N} / 2000

### 后台搜索词 (Backend Search Terms)
[空格分隔] — 字节数：{N} / 500

### Subject Matter（如适用）
1. [主题词组1]
2. [主题词组2]
...

---

# 关键词埋词报告

> **仅 Listing 和 Listing + 图片模式输出。**

**覆盖率：{used}/{total}（{rate}%）**

#### 已埋词
| 关键词 | 所在字段 |
|-------|---------|
| [keyword] | title / bullets / description |

#### 未埋词
| 关键词 | 建议处理 |
|-------|---------|
| [keyword] | 已加入后台搜索词 / 建议嵌入五点 |

#### 商标风险词（如有）
| 词汇 | 所在字段 | 风险等级 | 处理结果 |
|------|---------|---------|---------|

---

# 合规检查报告

根据模式输出对应检查项。

#### 文案合规检查（含 Listing 时输出）

| 检查项 | 状态 | 说明 |
|-------|------|------|
| 品牌词检查 | ✅/⚠️ | [结果] |
| 极限词/违禁词 | ✅/⚠️ | [结果] |
| 标题字符数 | ✅ {N}/{limit} | |
| 搜索词字节数 | ✅ {N}/500 | |
| 描述字符数 | ✅ {N}/2000 | |
| 医疗/功效声明 | ✅/⚠️ | [结果] |
| 促销/CTA 语言 | ✅/⚠️ | [结果] |
| 搜索词去重 | ✅/⚠️ | [与前端重复的词] |

#### 图片合规检查（含图片时输出）

| 检查项 | 状态 | 说明 |
|-------|------|------|
| A+ 图文比例 | ✅/⚠️ | 图片区域约 {N}%，文字约 {N}% |
| 违规元素 | ✅/⚠️ | [无违规 / 发现 XX] |
| 移动端适配 | ✅/⚠️ | [核心文字可辨认 / 字号过小] |
| 产品主体清晰度 | ✅/⚠️ | [清晰 / 模糊/变形] |
| 品牌合规 | ✅/⚠️ | [无竞品标识 / 发现 XX] |

#### 图文卖点一致性（Listing + 图片模式输出）

| T2 卖点维度 | 对应五点条目 | 状态 | 说明 |
|------------|------------|------|------|
| 核心功能 | 第 1 条 | ✅/⚠️/❌ | [匹配情况] |
| 材质工艺 | 第 2 条 | ✅/⚠️/❌ | [匹配情况] |
| 使用场景 | 第 3 条 | ✅/⚠️/❌ | [匹配情况] |
| 功能体验 | 第 4 条 | ✅/⚠️/❌ | [匹配情况] |
| 规格配件 | 第 5 条 | ✅/⚠️/❌ | [匹配情况] |

**总体结论：**
- 全部通过，可直接上架
- 或：发现 {N} 处需修复（详见上表），修复后再上架

---

# 关键词布局说明

> **仅 Listing 和 Listing + 图片模式输出。**

> 本报告说明本次 Listing 用了哪些关键词、放在哪里、为什么这样放。

#### 完整关键词清单

| 关键词 | 月搜索量 | 分配字段 | 报告标签 | 特征标签 | 原因 |
|-------|---------|---------|---------|---------|------|
| [keyword] | {vol} | 标题 | 核心词 | [属性] | 搜索量 Top 1 |
| [keyword] | {vol} | 五点 #1 | 长尾词 | — | 搜索量 Top 3 |
| [keyword] | {vol} | 后台搜索词 | 补充覆盖词 | — | 同义词/变体 |

#### 字段布局逻辑

**标题（权重 W1）** — Top 1-2 品类定义词前置于前 40 字符。

**五点描述（权重 W2）** — Top 3-20 按条分配，第 1-2 条放高搜索量功能词，第 3-5 条放场景/属性/规格词。

**产品描述（权重 W4）** — 场景展开叙述中自然触及长尾场景词。

**后台搜索词（权重 W3）** — Top 21-40 + 同义词/变体/外语，按搜索量降序至 500 字节。

**Subject Matter（权重 W3）** — 后台放不下的中等搜索量长尾词组，5 条 × 50 字节。

#### 基于本次数据的调整建议

> 以下建议基于本次实际关键词数据生成。

- [动态生成，例如：]
- 「关键词 `{keyword}`（月搜索量 {vol}）当前在后台搜索词中，如相关度高可考虑替换五点中低搜索量词。」

**广告投放参考：**
- 自动广告 seed：标题 Top 1-2 词 → exact match；五点 Top 3-20 词 → phrase/broad match
- 手动广告候选：后台搜索词中搜索量较高的词

---

# A+ 图片生成报告

> **仅图片和 Listing + 图片模式输出。**

### 生成结果

- **完整 A+ 长图**：[文件路径]
- **切割后独立图片**：
  1. [split_01.jpg] — 对应参考图第 1 块
  2. [split_02.jpg] — 对应参考图第 2 块
  ...

### 生成参数

| 参数 | 值 |
|------|---|
| 复刻相似度 | 高 / 中 / 低 |
| 输出分辨率 | 2K / 4K |
| 使用模型 | BANANA_PRO / BANANA_2 |
| 参考图来源 | {ASIN} 的 A+ 图片 × {N} 张 |
| 拼接模式 | vertical / grid |
| 目标尺寸 | {W}×{H} px |

### 版式分析摘要（T1）
[T1 版式描述的关键内容摘要]

---

# 卖点提取与一致性报告

> **Listing + 图片模式输出。**

### 图片卖点提取结果（T2）

[展示 T2 的结构化卖点数据，按品类格式]

**非服装类格式：**
| 维度 | 提取内容 |
|------|---------|
| 商品名称 | {product_name} |
| 目标受众 | {target_audience} |
| 卖点描述 | {selling_points_description} |
| 工艺细节 | {craftsmanship_details} |
| 使用方法 | {usage_method} |
| 类目路径 | {category_path} |

**服装类格式：**
| 维度 | 提取内容 |
|------|---------|
| 商品名称 | {product_name} |
| 目标受众 | {target_audience} |
| 营销标题 | {marketing_headlines} |
| 面料推断 | {material_inference} |
| 工艺细节 | {craftsmanship_details} |
| 穿着体验 | {functionality_and_wearing_experience} |
| 场景搭配 | {scene_adaptation_and_styling} |

### 文案五点核心卖点

| 条目 | BAF 维度 | 核心卖点摘要 |
|------|---------|-------------|
| 第 1 条 | 核心功能 | [从五点提取] |
| 第 2 条 | 材质安全 | [从五点提取] |
| 第 3 条 | 适用场景 | [从五点提取] |
| 第 4 条 | 易用性 | [从五点提取] |
| 第 5 条 | 套装售后 | [从五点提取] |

### 一致性矩阵

| 维度 | 图片卖点 | 文案卖点 | 状态 | 优化建议 |
|------|---------|---------|------|---------|
| 核心功能 | [T2 摘要] | [五点 #1 摘要] | ✅/⚠️/❌ | [如有偏差的调整建议] |
| 材质工艺 | [T2 摘要] | [五点 #2 摘要] | ✅/⚠️/❌ | |
| 使用场景 | [T2 摘要] | [五点 #3 摘要] | ✅/⚠️/❌ | |
| 功能体验 | [T2 摘要] | [五点 #4 摘要] | ✅/⚠️/❌ | |
| 规格配件 | [T2 摘要] | [五点 #5 摘要] | ✅/⚠️/❌ | |

### 图文优化建议

> 基于一致性矩阵的分析，提出具体优化方向。

- [动态生成，例如：]
- 「图片突出了 {卖点X}，但五点描述中未充分体现，建议在第 {N} 条中补充相关描述。」
- 「五点第 {N} 条强调了 {卖点Y}，建议在 A+ 图片中增加对应的视觉元素。」
