# 输出契约（路径协议 + 载荷 Schema）

所有 Tier 2/3 产物 skill 共用一套输出契约。本文件是硬规范，新建 / 复刻 / 微调优化三模式都要落到这里。

> **范围**：路径协议适用所有 skill 的所有落盘行为；**载荷 Schema** 规定 JSON 文件**内容**长什么样；**传输**（stdout → bridge → 前端）见同目录 `skill-output-protocol.md`，产物内联时一并写入 `references/output-schema.md`。

---

## 1. 路径协议（会话目录）

### 1.1 目录结构

```
<cwd>/linkfox/
├── <YYYY-MM-DD>/
│   └── <session-id>/
│       ├── _meta.json                  会话元信息（自动维护）
│       ├── reports/<slug>-<ts>.<ext>   最终交付（report-generator / Tier 3 报告）
│       ├── data/<slug>-<ts>.json       原始数据 / 中间产物
│       └── media/<slug>-<ts>.<ext>     图片 / 视频 / 音频
└── index.jsonl                         全局会话索引（按行追加）
```

### 1.2 session-id 规则

- 优先 `os.environ["SESSION_ID"]`（同回合所有 skill 自动聚合到同一目录）
- 缺省自动生成 `HHMMSS-<6 hex>`，进程内稳定
- **不允许**自造 session 命名格式或在 SKILL.md 里另起目录树

### 1.3 实现方式

复制 `linkfoxagent-v2/_shared/linkfox_paths.py` 进产物 `scripts/linkfox_paths.py`（与 `_shared` hash 一致），通过下列三个函数拿路径：

| 函数 | 用途 | 落点 |
|------|------|------|
| `resolve_data_path(slug, ts, ext="json")` | 中间数据 / Tier 1 拉回的原始数据 | `<session>/data/<slug>-<ts>.<ext>` |
| `resolve_report_path(slug, ts, ext)` | 最终交付（HTML / MD / JSON 报告） | `<session>/reports/<slug>-<ts>.<ext>` |
| `resolve_media_path(slug, ts, ext)` | 图 / 视频 / 音频 | `<session>/media/<slug>-<ts>.<ext>` |

调用任一函数会**自动**：
- 创建会话目录与子目录
- 首次写入时建好 `_meta.json` 并向 `linkfox/index.jsonl` 追加一行
- 把本次写入登记到 `_meta.json` 对应分类（`data_files / deliverables / media_files`）和 `skills_called`

### 1.4 硬禁止

- ❌ 写 `/tmp`、`/var/tmp`、`~`、绝对路径硬编码
- ❌ 写到 `<cwd>` 之外的位置
- ❌ 自造会话目录格式（如 `output/research/<slug>/`、`<skill>/runs/<run_id>/`）
- ❌ `<cwd>` 不可写时静默 fallback —— 必须直接报错让 agent 决策
- ❌ 在 SKILL.md 里让用户传 `--out-dir`：交付路径由协议决定，用户只能改 `SESSION_ID`

> 例外：用户**显式**要求"导出到桌面 / 我指定的目录"，可以走 `shutil.copy` 把已落盘的 reports/* 复制到目标位置，但**主路径仍必须**是 `<cwd>/linkfox/...`。

### 1.5 临时缓存

仅供调试 / 单次进程内使用的纯临时文件可以走 `/tmp`，但：

- 必须是真临时（进程退出即可丢）
- 不进 `_meta.json`、不暴露给上游 / 用户
- SKILL.md 里**不**把 `/tmp` 路径作为契约暴露

---

## 2. 两层交付协议（传输 + 载荷）

### 2.1 传输层（stdout → 前端）

Tier 2/3 **最终面向用户的结构化 JSON** 必须通过 stdout 交给 acpx-bridge，规范见 **`references/skill-output-protocol.md`**（产物内联到 `references/output-schema.md`）：

| 方式 | 何时用 |
|------|--------|
| `os.path.isfile(abs_json_path)` 通过后 `print(f"Saved full response: {abs_json_path} ({size_bytes} bytes)")` | 结构化 JSON 结果（**推荐**） |
| 所有 `abs_media_paths` 逐项 `os.path.isfile()` 通过后 `print("Saved full response: " + json.dumps(abs_media_paths, ensure_ascii=False))` | 图片 / 视频 / 音频 |

bridge 将文件转为 `resource_link`；前端再 **fetch 文件内容** 并按 §2.2 载荷类型解析。

> **禁止输出占位符示例路径**：任何真实 stdout 行里的路径都必须是 `resolve_*_path()` / `download_media()` 返回的已存在绝对路径。不要把 `<YYYY-MM-DD>`、`<session>`、`linkfox-generated-media-123.png` 这类文档占位符原样打印，否则 bridge 会按真实文件加载并报 `Local file does not exist`。

> **禁止输出未写入文件的预分配路径**：`resolve_media_path()` 只返回目标文件名，不会创建图片/视频。必须先下载/写入/rename 成功，并用 `os.path.isfile(path)` 校验通过，再把路径放入 `Saved full response` 媒体数组。不要使用 `...` 省略路径或 `linkfox-generated-media-*` 这类泛化假文件名。

> **暂存草稿不走传输层**：访谈纪要、流程草图、选型表、DAG、试跑提示词等 `.draft/` 工作稿不提供 `resource_link` / 文件链接，也不打印 `Saved full response:`。需要用户检查时，直接在当前会话中展示草稿摘要或全文。

### 2.2 载荷层（JSON 文件内容）

**JSON 文件里写什么**由本节约定。前端当前按 **payload 形状** 探测（如 `{ products: [...] }`），**不要求** `type: "skill-output"` 包装。

| `payload_type` | 适用场景 | 状态 |
|----------------|----------|------|
| `product_list` | 商品列表（选品池、对标池、批量 ASIN） | ✅ 见 §2.3.1 |
| `keyword_list` | 关键词清单 / 打分表 | 占位，待补字段表 |
| `report_html` | 精美 HTML 报告 | 走 `linkfox-report-generator` 或业务专用 HTML skill handoff，**不在此定义 blocks** |

> **已废弃（勿再写）**：`skill-output` envelope 的 `props.blocks` + KvGrid/DataTable 等组件白名单。该方案无聊天 UI 承接，已从产品侧移除。报告型排版请 handoff 给 `linkfox-report-generator`（或业务方指定的 HTML 渲染 skill），不要自造 blocks JSON。

### 2.3 各 payload 的 Schema

#### 2.3.1 `product_list`

##### 推荐形状（写入 JSON 文件的内容）

```json
{
  "type": "productList",
  "total": 23,
  "products": [
    {
      "asin": "B086L79Q6X",
      "title": "Hanes mens Underwear Boxer Briefs Pack...",
      "brand": "Hanes",
      "imageUrl": "https://m.media-amazon.com/images/I/81abc.jpg",
      "price": 18.02,
      "currency": "$",
      "rating": 4.5,
      "ratings": 78900,
      "unitsSold": 50000,
      "revenue": 901000,
      "profit": 23.5,
      "bsr": 7,
      "sellerCount": 12,
      "fulfillment": "FBA"
    }
  ]
}
```

- `type` 可选：`"productList"` 或 legacy `"productWorkbenches"` 均可
- `total` 可选；与 `products.length` 不一致时表示已过滤 / 分页
- **最低门槛**：每条 product 至少含 **`asin` 或 `title` 之一**

##### `ProductItem` 字段表

| 字段 | 类型 | legacy 别名 | 推荐 | 说明 |
| --- | --- | --- | --- | --- |
| `asin` | string | — | ✅ | 表格 ASIN / React key |
| `title` | string | — | ✅ | 标题列 |
| `brand` | string | — | ✅ | 品牌列 |
| `imageUrl` | string | — | 推荐 | 主图 |
| `productImageUrls` | string[] | — | 否 | 多图轮播 |
| `price` | number | — | ✅ | 配合 `currency` |
| `currency` | string | — | 否 | 默认 `$` |
| `rating` | number | — | 推荐 | 0~5 |
| `ratings` | number | — | 否 | 评论数 |
| `unitsSold` | number | `monthlySalesUnits` | 推荐 | 月销量 |
| `revenue` | number | `monthlySalesRevenue` | 否 | 月销售额 |
| `profit` | number | — | 否 | **已 ×100**（12.3 = 12.3%） |
| `bsr` | number | — | 推荐 | BSR，越小越好 |
| `sellerCount` | number | `sellerNum` | 否 | 卖家数 |
| `fulfillment` | string | — | 否 | `FBA` / `FBM` |
| `aboutItemFivePoint` | string[] | — | 否 | 五点描述 |
| `variationNum` | number | — | 否 | 变体数 |
| `badgeBestSeller` 等 | string | — | 否 | 非空且非 `N`/`0` 才显示 badge |

##### 单位与精度

| 字段 | 约定 |
| --- | --- |
| `profit` | 百分数数值，**已 ×100**；不要写 `0.123` 表示 12.3% |
| `price` / `revenue` | 纯数字，货币符号放 `currency` |
| `rating` | 数字 0~5，不要传字符串 |
| `productImageUrls` / `aboutItemFivePoint` | 必须是 **数组** |

##### 反例

| ❌ 错法 | ✅ 正确 |
| --- | --- |
| 顶层直接是数组 `[{asin,...}, ...]`（无 `products` 键） | `{ "products": [...] }` |
| `profit: 0.123` | `profit: 12.3` |
| `productImageUrls: "https://..."` | `["https://..."]` |
| 包一层 `type:"skill-output"` + `props.blocks` | 裸 `products` JSON + 传输层 `Saved full response` |
| 每条商品单独 push 一个 artifact | 同一文件内 `products` 数组 |

##### 兼容说明（legacy，新 skill 勿用）

历史文档曾要求 `type: "skill-output"` + `props.data.products`。部分前端仍能从 `props.data` **宽松解包**，但**新产物一律写裸 payload**，不要新增 envelope。

##### 自动化体检

本仓库自带样例：

```bash
python scripts/validate_product_payload.py examples/sample-product-list.json
```

产物 skill 应在 `examples/` 放一份自己的样本后执行（需先复制 `scripts/validate_product_payload.py`）：

```bash
python <产物 skill>/scripts/validate_product_payload.py examples/sample-output.json
```

#### 2.3.2 `keyword_list`

占位。待前端 keyword schema 稳定后在本节补充 `{ keywords: [...] }` 字段表。

---

## 3. 完整示例（商品列表 + 传输）

**步骤 1**：落盘 JSON（内容见 §2.3.1）

```python
path = resolve_report_path("amazon-underwear-screener", ts, "json")
# 写入 { "type": "productList", "total": 23, "products": [...] }
```

**步骤 2**：stdout 通知 bridge

```python
if not os.path.isfile(abs_json_path):
    raise RuntimeError(f"output file not found: {abs_json_path}")
print(f"Saved full response: {abs_json_path} ({size_bytes} bytes)")
```

**步骤 3**：HTML 报告（若需要）

SKILL.md 报告章节末尾 handoff 给 `linkfox-report-generator`（或业务指定的 HTML skill）。**不要**在 JSON 里拼 `blocks` 数组代替报告。

---

## 4. 自检清单

### 4.1 路径

- [ ] 落盘路径全部走 `linkfox_paths.resolve_*_path`，没有 `/tmp` / 绝对路径硬编码
- [ ] `linkfox_paths.py` hash 与 `linkfoxagent-v2/_shared/linkfox_paths.py` 一致

### 4.2 传输（stdout）

- [ ] 最终交付符合 `skill-output-protocol.md`（`Saved full response` 文件 / 媒体数组）
- [ ] `jsonPath` / 文件路径为**绝对路径**

### 4.3 载荷（JSON 内容）

- [ ] `product_list`：`{ "products": [...] }` 形状正确，字段单位无错
- [ ] 未使用已废弃的 `props.blocks` / KvGrid / DataTable envelope blocks
- [ ] 含「报告产物」章节时，末尾有 `linkfox-report-generator`（或业务 HTML skill）handoff，未自造 HTML

### 4.4 边界

- [ ] 产物 SKILL.md / references 中**无**反向引用 `linkfox-ecommerce-skill-creator/...`——契约已内联到产物 `references/output-schema.md`
