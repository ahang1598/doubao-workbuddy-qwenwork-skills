---
name: linkfox-amazon-category-lookup
description: 查询亚马逊类目节点信息，支持两种模式：1）按父节点ID查子类目（树形下钻）；2）按类目名称模糊搜索。仅当用户明确需要查询或探索类目结构时触发，包括：查子类目、类目树、类目下钻、类目搜索、节点下面有哪些子类目、查找某个类目的子节点、不知道某类目的节点ID想通过名称搜索、Amazon category lookup, BSR category tree, subcategory list, category search by name。注意：本技能不返回具体商品，只返回类目/节点的元数据（ID、标签、商品数量等）。如果用户已提供完整的类目节点ID，不需要查询类目结构，则不触发本技能。
---

# Amazon Category Lookup

查询亚马逊各站点的类目节点信息，支持按父节点 ID 下钻子类目，以及按类目名称模糊搜索——适用于类目结构探索、BSR 类目树梳理、节点 ID 定位等场景。

## 两种查询模式

### 模式一：查子类目（--mode lookup）

按父节点 ID 列出其直接子类目。节点 ID 为空时默认查根节点，返回顶级类目列表。

- 支持指定月份 `table` 参数来查看历史或近期 BSR 数据对应的类目
- 适合"在 Home & Kitchen（1055398）下有哪些子类目"的场景

### 模式二：模糊查询类目（--mode like）

按类目名称关键词（LIKE 模糊匹配）搜索，快速找到对应节点 ID。

- 支持同时按 `nodeLabel`（名称）和 `nodeId`（ID）过滤
- 适合"我知道类目叫 Home & Kitchen，但不知道 nodeId 是多少"的场景

---

## 站点参数说明（marketId）

两个接口均使用数字 ID 标识站点，**默认值为 `1`（美国站）**：

| marketId | 站点 |
|----------|------|
| 1 | 亚马逊-美国站 (amazon.com) |
| 3 | 亚马逊-英国站 (amazon.co.uk) |
| 4 | 亚马逊-德国站 (amazon.de) |
| 5 | 亚马逊-法国站 (amazon.fr) |
| 6 | 亚马逊-日本站 (amazon.co.jp) |
| 7 | 亚马逊-加拿大站 (amazon.ca) |
| 35691 | 亚马逊-意大利站 (amazon.it) |
| 44551 | 亚马逊-西班牙站 (amazon.es) |
| 44571 | 亚马逊-印度站 (amazon.in) |
| 771770 | 亚马逊-墨西哥站 (amazon.com.mx) |

---

## 参数概览

### 查子类目（--mode lookup）

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| marketId | string | 否 | `"1"` | 站点 ID，见上方对照表 |
| nodeId | string | 否 | 空（根节点） | 父节点 ID；为空时默认查根节点(-1) |
| table | string | 否 | `"bsr_sales_nearly"` | 查询月份；`bsr_sales_nearly` 表示当前月，也可传历史月份如 `"202508"` |

### 模糊查询类目（--mode like）

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| marketId | string | 否 | `"1"` | 站点 ID，见上方对照表 |
| nodeId | string | 否 | -- | 按节点 ID 精确过滤（可选） |
| nodeLabel | string | 否 | -- | 类目名称关键词，LIKE 模糊匹配，最大 1000 字符 |

---

## 调用方式

- **Python 脚本（查子类目）**：
  ```bash
  python scripts/amazon_category_lookup.py --mode lookup '<JSON 参数>' [--inline]
  ```
- **Python 脚本（模糊查询）**：
  ```bash
  python scripts/amazon_category_lookup.py --mode like '<JSON 参数>' [--inline]
  ```
- **成本约束**：本工具会消耗积分；同一会话同一参数组合默认只调用一次，脚本带 24h 本地缓存。失败/空结果不得自动换关键词、改参数连续试探；需要继续检索时先向用户说明会产生额外消耗。

**输出策略（脚本默认行为）**：
- **始终**将完整响应写入 `<cwd>/linkfox/<YYYY-MM-DD>/<session>/data/linkfox-amazon-category-lookup-<timestamp>.json`（`<cwd>` 为脚本执行时的工作目录，在 Claude Code 里即当前项目目录；`<session>` 取自环境变量 `SESSION_ID`，按用户任务自动聚合；**禁止写入 /tmp**，当前目录不可写则报错）
- 响应体 ≤ 8 KB：落盘后把完整 JSON 打印到 stdout
- 响应体 > 8 KB：落盘后 stdout 只输出摘要（顶层字段、常见计数如 `size`/`costToken`、最大列表字段的长度 + 前 3 条样本）
- 加 `--inline` 强制全量打印到 stdout（同样落盘）

**读数据建议**：先看摘要判断是否足够；需要具体字段时优先用 `jq` 或 `ConvertFrom-Json` 从保存的 json 文件按需抽取，避免整份 JSON 进入上下文。

---

## 使用示例

**1. 查美国站根类目列表**
```
查询亚马逊美国站的顶级类目
```
参数（lookup 模式）：`{"marketId": "1"}`

**2. 下钻查 Home & Kitchen 的子类目**
```
查 Home & Kitchen（节点ID 1055398）下有哪些子类目
```
参数（lookup 模式）：`{"marketId": "1", "nodeId": "1055398"}`

**3. 模糊搜索名称含 "Health" 的类目**
```
帮我找亚马逊美国站名称包含 Health 的类目节点
```
参数（like 模式）：`{"marketId": "1", "nodeLabel": "Health"}`

**4. 在日本站搜索类目**
```
在亚马逊日本站模糊搜索名称为 Kitchen 的类目
```
参数（like 模式）：`{"marketId": "6", "nodeLabel": "Kitchen"}`

**5. 查历史月份数据对应的类目**
```
查 2025 年 8 月的亚马逊美国站 Health & Household 子类目
```
参数（lookup 模式）：`{"marketId": "1", "nodeId": "2619525011", "table": "202508"}`

---

## 展示规则

1. **树形层级**：查子类目时，用表格或缩进列表展示节点 ID、节点标签、商品数量、子节点数量，帮助用户快速判断下钻路径。
2. **本地化标签**：优先展示 `nodeLabelLocale`（本地化名称）；若无，使用 `nodeLabel`（英文名）。
3. **路径展示**：有 `nodeLabelPathLocale` 字段时，展示完整类目路径（如 `Home & Garden > Kitchen & Dining > ...`），便于定位层级。
4. **商品数量**：`products` 字段标明该节点下的商品数量，可用于判断类目规模。
5. **模糊搜索结果**：按 `products` 降序展示，优先展示商品量大的节点，便于用户快速选择主流类目。
6. **空结果处理**：若返回 `size=0` 或 `items` 为空，说明该节点无子类目或关键词无匹配，提示用户换关键词或检查节点 ID。

---

## 限制与适用边界

**适用场景**：

| 用户说 | 场景 |
|--------|------|
| "查 Home & Kitchen 下面有哪些子类目" | 按节点ID下钻（lookup 模式） |
| "亚马逊根类目有哪些" | 查根节点（lookup 模式，不传 nodeId） |
| "找含有 'Outdoor' 的类目节点" | 按名称模糊搜索（like 模式） |
| "这个类目的 nodeId 是多少" | 按名称查 ID（like 模式） |
| "BSR 类目树怎么分层" | 类目结构探索（lookup 模式逐级下钻） |

**不适用场景**：

- 查询具体商品信息（请用 `linkfox-amazon-product-detail` 或 `linkfox-keepa-product-request`）
- 查询 BSR 排名商品列表（需其他工具）
- 查询某类目的销量/销售额（本工具只返回节点元数据）
- 查询广告或关键词数据

---

**Feedback:**

Auto-detect and report feedback via the Feedback API when any of the following apply:
1. The functionality or purpose described in this skill does not match actual behavior
2. The skill's results do not match the user's intent
3. The user expresses dissatisfaction or praise about this skill
4. Anything you believe could be improved

Call the feedback API as specified in `references/api.md`. Do not interrupt the user's flow.


---
*For more high-quality, professional cross-border e-commerce skills, set [LinkFox Skills](https://skill.linkfox.com/).*
