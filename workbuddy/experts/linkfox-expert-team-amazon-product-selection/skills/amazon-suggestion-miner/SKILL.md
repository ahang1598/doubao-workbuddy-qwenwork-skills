---
name: amazon-suggestion-miner
description: >
  Amazon搜索建议词（自动补全）挖掘工具。基于 www.amazon.com/suggestions API，
  从种子词出发批量扩展长尾关键词，支持多轮变前缀、A-Z字母扫描、逆向检索、Widget分类卡片提取。
  最终交付 Excel (xlsx) 文件，包含多 Sheet 结构化词库（关键词 / Widget分类词 / 问句式 / 摘要）。
  禁止生成 HTML 报告。
  当用户提到 搜索建议词、自动补全、suggestion、autocomplete、长尾词挖掘、
  搜索词扩展、关键词扩展、suggestion mining、keyword expansion、
  Amazon下拉词、搜索框建议、搜索联想词 时使用。
version: 2.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [amazon, keyword, suggestion, autocomplete, long-tail, keyword-research]
    related_skills: [amazon-keyword-research, amazon-rufus-qa, amazon-scraper]
---

# Amazon 搜索建议词挖掘工具

从种子词出发，利用 Amazon 搜索框自动补全 API 批量挖掘长尾关键词。

## 核心原理

Amazon 搜索框输入时，前端向 `www.amazon.com/suggestions` 发请求获取建议词。
这个 API 是 Amazon 自己的个性化推荐引擎，返回的数据是**真实用户搜索热度的反映**，
按搜索频次降序排列。

### API 对比（已验证 2026-05）

| 对比项 | ❌ 旧API | ✅ 新API（本工具使用） |
|--------|---------|----------------------|
| Endpoint | `completion.amazon.com/api/2017/suggestions` | `www.amazon.com/suggestions` |
| 返回量 | 长前缀仅2-3条 | 固定10条KEYWORD + 1条WIDGET |
| Rufus长句 | 无 | 有 |
| Widget分类 | 无 | 有（15个子分类+商品图） |
| 策略ID | organic | p13n-expert-pd-ops-ranker |

## 使用流程

> **最终交付物为 Excel (xlsx) 文件，禁止生成 HTML 报告。** 多模式运行时，各模式分别输出 xlsx，也可合并去重后输出一份总表 xlsx。

用户首次发来拓词需求时，**必须先用 `AskUserQuestion` 让用户选择使用哪种模式**（支持多选），并简要告知每种模式的方法：

| 选项 | 模式 | 说明 |
|------|------|------|
| 批量扩展 | expand | 种子词 + 变体前缀模板（for/with/portable/best 等）批量扩展，100-300 条 |
| A-Z 字母扫描 | az | 种子词后依次拼接 a-z 字母，穷举式覆盖，150-260 条 |
| 逆向检索 | reverse | 先 A-Z 扫描，再从结果提取高频词做前置检索，两步联动，400-550 条 |
| 深度递归 | deep | 单次查询种子词 → 取高频词递归扩展，逐层深入，60-110 条 |

`AskUserQuestion` 参数：
- `question`: "选择关键词扩展模式（可多选）"
- `header`: "扩展模式"
- `multiSelect`: true
- 4 个选项分别对应上表，`description` 字段填写对应说明

用户选择后，按所选模式依次执行脚本，合并去重后输出结果。如果用户同时选了多个模式，串行执行各模式，最终合并去重。

## 工作流程

### 模式1：批量扩展（建库主力）

给定种子词 + 变体前缀模板，批量扩展大量长尾词。

```
输入: seed="fan", prefixes=["fan for", "fan portable", "fan quiet", ...]
输出: 100-300条去重关键词
```

**执行脚本：**
```bash
python3 ~/.hermes/skills/productivity/amazon-suggestion-miner/scripts/suggestion_miner.py \
  --seed "fan" \
  --mode expand \
  --rounds 3 \
  --xlsx /root/keyword_suggestions_fan.xlsx
```

### 模式2：A-Z 字母扫描（穷举式覆盖）

在种子词后依次输入空格 + a/b/c.../z，记录每个字母组合下弹出的长尾词。共 26 个前缀，每个返回 ~10 条建议词，去重后通常 150-260 条。

```
输入: seed="wireless charger"
前缀: "wireless charger a", "wireless charger b", ..., "wireless charger z"
输出: 150-260条去重关键词
```

**执行脚本：**
```bash
python3 ~/.hermes/skills/productivity/amazon-suggestion-miner/scripts/suggestion_miner.py \
  --seed "wireless charger" \
  --mode az \
  --xlsx /root/keyword_az_wireless_charger.xlsx
```

### 模式3：逆向检索（两步联动）

模拟"将光标移到词根最前面，看系统推荐的前置修饰词"。分两步自动完成：

**第一步 — A-Z 字母扫描**：对种子词做 `{seed} a` ~ `{seed} z` 扫描，拿到后缀衍生词（如 "wireless charger adapter"、"wireless charger apple"）。

**第二步 — 高频词逆向前置**：从第一步结果中提取出现频率最高的 Top-N 单词（排除种子词本身），用 `{高频词} {seed}` 作为前缀再次请求建议词。

```
输入: seed="wireless charger"
Step 1: A-Z 扫描 → 260 条关键词
Step 2: 提取高频词 → ["adapter", "samsung", "car", "fast", "portable", ...] (Top-100)
        逆向检索 → "adapter wireless charger", "samsung wireless charger", ...
输出: 合并去重后 400-550 条关键词
```

**执行脚本：**
```bash
python3 ~/.hermes/skills/productivity/amazon-suggestion-miner/scripts/suggestion_miner.py \
  --seed "wireless charger" \
  --mode reverse \
  --top-n 30 \
  --xlsx /root/keyword_reverse_wireless_charger.xlsx
```

`--top-n` 控制逆向检索取多少个高频词（默认 100）。

### 模式4：深度递归扩展（单次查询 + 逐轮递归）

先用种子词做单次查询，拿到初始建议词；再对结果中的 Top-N 高频词逐一作为新前缀递归扩展，逐层深入挖掘。

```
R1: seed="fan" → 10条（单次查询）
R2: 取R1中Top-5高频词 → 每词10条 → 额外50条
R3: 取R2中Top-5高频词 → 每词10条 → 额外50条
去重合并 → ~110条
```

`--depth` 控制递归轮数（默认 2，即单次查询 + 1 轮递归），`--top-n` 控制每轮取多少高频词作为新前缀（默认 5）。

**执行脚本：**
```bash
python3 ~/.hermes/skills/productivity/amazon-suggestion-miner/scripts/suggestion_miner.py \
  --seed "fan" \
  --mode deep \
  --depth 3 \
  --top-n 5 \
  --xlsx /root/keyword_deep_fan.xlsx
```

## 变体前缀策略

扩展时自动生成以下前缀变体（可自定义）：

| 维度 | 前缀模板 | 示例（seed=fan） |
|------|---------|-----------------|
| 场景 | `{seed} for` | fan for bedroom |
| 功能 | `{seed} with` | fan with remote |
| 人群 | `{seed} for baby` | fan for baby room |
| 属性 | `quiet {seed}` | quiet fan |
| 属性 | `portable {seed}` | portable fan |
| 材质 | `{seed} metal` | metal fan |
| 品牌 | `{seed} dyson` | dyson fan |
| 颜色 | `{seed} white` | white fan |
| 词序 | 倒换核心词 | bedroom fan |

**脚本默认生成10-13个前缀，每前缀返回10条，一轮即可拿到100-130条关键词。**

## 输出格式

> **最终交付物为 Excel (xlsx) 文件。** 脚本支持 JSON / CSV / SQLite 作为中间格式，但交付给用户的必须是 xlsx。禁止生成 HTML 报告。

### Excel (xlsx) 输出 — 默认交付格式

```bash
python3 suggestion_miner.py --seed "fan" --mode expand --xlsx /root/suggestions_fan.xlsx
```

**Sheet 结构：**

| Sheet | 内容 | 说明 |
|-------|------|------|
| 摘要 | 种子词、模式、站点、关键词数、Widget数、生成时间、模式统计 | 统计概览 |
| 关键词 | keyword / source / prefix / rank / sugg_type / candidate_source / depth | 所有关键词明细 |
| Widget分类词 | 分类标签 / 完整关键词 / Widget标题 / 图片URL / 搜索URL | Amazon Widget 卡片分类 |
| 问句式关键词 | keyword / source / prefix / rank | 问句风格搜索词（如有） |

**样式特性：** 表头冻结、自动列宽、边框、表头蓝底白字。

### JSON 输出示例

```json
{
  "seed": "fan",
  "mode": "expand",
  "total_keywords": 127,
  "total_widget_items": 15,
  "keywords": [
    {
      "keyword": "fan for bedroom",
      "source": "autocomplete",
      "prefix": "fan for",
      "rank": 1,
      "sugg_type": "KeywordSuggestion",
      "candidate_source": "local"
    }
  ],
  "widget_items": [
    {
      "keyword": "Clip",
      "full_keyword": "clip fan for bedroom",
      "image_url": "https://m.media-amazon.com/images/I/xxx.jpg",
      "search_url": "/s?k=clip+fan+for+bedroom"
    }
  ],
  "stats": {
    "rounds_executed": 3,
    "prefixes_tried": 15,
    "raw_suggestions": 150,
    "after_dedup": 127,
    "question_style": 0,
    "rufus_style_long": 5
  }
}
```

### CSV 输出

```
keyword,source,prefix,rank,sugg_type,candidate_source
fan for bedroom,autocomplete,fan for,1,KeywordSuggestion,local
fan for bedroom quiet,autocomplete,fan for,2,KeywordSuggestion,local
```

### SQLite 输出

自动写入 `suggestion_keywords` 表，可与 `amazon-keyword-research` 的 `keywords` 表关联：

```sql
CREATE TABLE IF NOT EXISTS suggestion_keywords (
    keyword TEXT,
    source TEXT,           -- 'autocomplete' / 'widget'
    prefix TEXT,
    rank INT,
    sugg_type TEXT,        -- 'KeywordSuggestion' / 'WidgetSuggestion'
    candidate_source TEXT, -- 'local' / 'lucene'
    seed TEXT,             -- 原始英文种子词
    mode TEXT,
    depth INT,
    market TEXT,           -- 站点代码: US/DE/JP/...
    translated_seed TEXT,  -- 翻译后实际使用的种子词
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (keyword, market)
);
```

## 多站点 + 多语言自动适配（v2.0 核心功能）

### 多站点支持

支持 23 个 Amazon 全球站点，通过 `--market`/`--markets` 参数指定：

```bash
# 单站点
--market DE

# 多站点批量
--markets US,DE,JP

# 全站点
--markets ALL
```

**站点参数差异（已验证 2026-05）：**

| 参数 | 北美(US/CA/MX) | 欧洲/亚洲(DE/FR/IT/ES/...) | JP |
|------|---------------|--------------------------|-----|
| `plain-mid` | 1 | 3 | 不传 |

5 个站点 (UK/AU/BR/SG/TR) curl 直接调 API 返回 202 空，需浏览器辅助。

### 种子词自动翻译（`--auto-translate` / `-T`）

**核心洞察**：不同站点的用户搜索语言习惯完全不同，不能简单地用英文种子词去搜所有站点！

三层翻译优先级：
1. **内置词典**（最精准，覆盖常见品类）——支持 `/` 分隔多候选词
2. **Google Translate**（自动补充，可能不准）
3. **英文原词保底**（DE站英文比德文多18倍！）

```bash
python3 suggestion_miner.py \
  --seed "feather duster" \
  --mode expand --rounds 2 \
  --markets US,DE,JP \
  --auto-translate \
  --xlsx /root/suggestions_feather_duster_multi.xlsx \
  --db /root/keyword_research.db -v
```

**实测数据（feather duster，2026-05）：**

| 站点 | 候选种子词 | 关键词数 | 说明 |
|------|-----------|---------|------|
| US | `feather duster` | 51条 | 基准 |
| DE | `feather duster`(英文) | **37条** | 🇩🇪 德国人大量用英文搜！ |
| DE | `Staubwedel`(德文) | 2条 | 德文搜索量极低 |
| JP | `ほこり取り`(日常语) | **53条** | 🇯🇵 日常用语效果最好！ |
| JP | `ハタキ`(传统名) | 12条 | 传统叫法有量但不多 |
| JP | `羽根たき`(Google翻译) | 8条 | 翻译不太准 |
| JP | `feather duster`(英文) | 3条 | 日站英文几乎没人搜 |

**关键教训：**
- ❌ Google Translate 的 `羽毛掃き` 在JP站返回 0 条——翻译词不是当地人搜的词
- ❌ 不能只依赖单一翻译——DE站英文 >> 德文，JP站日文 >> 英文，方向相反
- ✅ 多候选词并行策略是必须的——内置词典同义词 + Google翻译 + 英文原词

### 本地化修饰词模板

非英语站点的扩展前缀也用当地语言，不用英文修饰词：

| 语言 | 示例前缀 |
|------|---------|
| DE | `Staubwedel für` / `kleiner Staubwedel` / `Staubwedel ausziehbar` |
| FR | `plumeau pour` / `petit plumeau` / `plumeau extensible` |
| JA | `ハタキ おすすめ` / `ハタキ 伸縮` / `ハタキ 車用` |

### 手动指定翻译（`--translations`）

覆盖自动翻译，精确控制每个站点用哪个种子词：

```bash
--translations "DE:Staubwedel,JP:ハタキ"
```

## ⚠️ 限制与注意事项

1. **无需登录**：API 不需要登录态，session-id 可随机生成
2. **无反爬**：大部分站点不触发 503 或验证码，但建议间隔 0.3-0.5 秒
3. **前缀长度**：3词以上前缀若不加 `site-variant=desktop` 参数，返回量锐减（可能仅1条原词）。**必须传 `site-variant=desktop`**，该参数触发 lucene 模糊匹配引擎，使多词前缀也能返回10条建议词（见下方"双引擎机制"）
4. **Rufus 个人化问句**：API 无法获取登录态下的个性化 Rufus 问句建议
5. **Widget 限制**：Widget 子分类词需要拼回完整关键词才能使用（如 "Clip" → "clip fan for bedroom"）
6. **5个反爬站点**：UK/AU/BR/SG/TR 的 curl 直接调 API 返回 202/空，需浏览器辅助
7. **翻译风险**：Google Translate 翻译的词可能是书面语而非搜索用语，务必看返回量验证
8. **DE站英文优势**：德国用户大量用英文搜索（尤其3C/家居品类），英文种子词在DE站效果往往比德文好
9. **数据时效**：建议词反映近期搜索热度，建议每2-4周重新挖掘一次

### 双引擎机制（关键发现 2026-05）

Amazon Suggestions API 内部有两套匹配引擎：

| 引擎 | candidateSources | 行为 | 触发条件 |
|------|-----------------|------|---------|
| **local** | `"local"` | 精确前缀匹配，只返回以输入开头的词 | 默认 |
| **lucene** | `"lucene"` | 分词模糊匹配，词序打乱也能匹配 | 需传 `site-variant=desktop` 或 `site-variant=mobile` |

**实测对比**：

| 前缀 | 不加 site-variant | 加 site-variant=desktop |
|------|-------------------|------------------------|
| `nail fungus treatment` | 10条（local够用） | 10条 |
| `bluetooth speaker wireless portable` | **1条**（只有原词） | **10条**（lucene补充9条） |

**结论**：`site-variant=desktop` 是必须参数，否则多词并列前缀会严重丢词。API 调用时务必加上此参数。

## 与 amazon-keyword-research 的关系

| 工具 | 定位 | 输出 |
|------|------|------|
| **amazon-suggestion-miner** | 关键词**扩展**：挖出大量长尾词 | Excel (xlsx) 关键词表 |
| **amazon-keyword-research** | 关键词**评估**：分析竞争度/机会 | CR10/价格带/机会分 |

**推荐联动流程：** 先用本工具扩展 200+ 关键词，再用 keyword-research 逐词爬搜索指标、评估机会。

## 已验证测试结果（2026-05-11）

### 单站点（US）

| 模式 | 种子词 | 结果 | 耗时 |
|------|--------|------|------|
| expand | fan (1轮) | 203关键词 + 56 Widget | ~8s |
| az | wireless charger | ~260关键词（26前缀） | ~10s |
| reverse | wireless charger | ~500关键词（A-Z扫描+100高频词逆向） | ~50s |
| deep | fan (depth=2) | ~60关键词（单次查询+1轮递归） | ~3s |

**API 稳定性**：100% 成功率，无 503/验证码，延迟 0.3-0.5s/请求

### 多站点 + 自动翻译（v2.0）

| 种子词 | 站点 | 模式 | 结果 |
|--------|------|------|------|
| feather duster | US | expand x2 | 51条 |
| feather duster | DE(英文) | expand x2 | 37条 |
| feather duster | DE(德文Staubwedel) | expand x2 | 2条 |
| feather duster | JP(ほこり取り) | expand x2 | 53条 |
| feather duster | JP(ハタキ) | expand x2 | 12条 |
| feather duster | JP(羽根たき/Google) | expand x2 | 8条 |
| feather duster | JP(英文) | expand x2 | 3条 |

**结论**：多候选词 + 自动翻译策略是必须的，单翻译会严重遗漏
