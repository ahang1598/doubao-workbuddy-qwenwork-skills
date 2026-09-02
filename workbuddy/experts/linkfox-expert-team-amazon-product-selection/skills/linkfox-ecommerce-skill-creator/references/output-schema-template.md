# 产物输出契约（内联模板）

> **生成产物时**：把本文件复制为 `references/output-schema.md`，按业务删改占位符。**禁止**在产物 SKILL.md 中反向引用 `linkfox-ecommerce-skill-creator/...`。

---

## 1. 路径协议

运行期落盘一律走 `scripts/linkfox_paths.py`：

| 类型 | 函数 | 落点 |
|------|------|------|
| 中间数据 | `resolve_data_path(slug, ts)` | `<cwd>/linkfox/<date>/<session>/data/` |
| 最终 JSON / 报告 | `resolve_report_path(slug, ts, ext)` | `<cwd>/linkfox/<date>/<session>/reports/` |
| 媒体 | `resolve_media_path(slug, ts, ext)` | `<cwd>/linkfox/<date>/<session>/media/` |

禁止写 `/tmp`、绝对路径硬编码、自造 `--out-dir`。

---

## 2. 传输层（stdout → 前端）

脚本 stdout 通过 `Saved full response:` 行通知 acpx-bridge（详见 `skill-output-protocol.md`）：

**结构化 JSON（推荐）**：

```python
if not os.path.isfile(abs_json_path):
    raise RuntimeError(f"output file not found: {abs_json_path}")
print(f"Saved full response: {abs_json_path} ({size_bytes} bytes)")
```

**图片 / 视频 / 音频**：

```python
missing = [p for p in abs_media_paths if not os.path.isfile(p)]
if missing:
    raise RuntimeError(f"media file not found: {missing[0]}")
print("Saved full response: " + json.dumps(abs_media_paths, ensure_ascii=False))
```

要求：绝对路径；路径必须指向已存在文件；JSON 文件名匹配 `linkfox-<slug>-<数字>.json`；stdout 可含其他日志，bridge 只匹配 `Saved full response:` 行。禁止复制占位符路径（如 `<YYYY-MM-DD>`、`<session>`、`linkfox-generated-media-123.png`）作为真实输出。`resolve_media_path()` 只分配路径，不写文件；媒体数组输出前必须先完成写入并逐项 `os.path.isfile()` 校验。

---

## 3. 载荷层（JSON 文件内容）

### 3.1 product_list（商品列表）

写入 JSON 文件的**推荐形状**（不要包 `type: "skill-output"` envelope）：

```json
{
  "type": "productList",
  "total": 0,
  "products": [
    {
      "asin": "B0XXXXXXXX",
      "title": "商品标题",
      "brand": "品牌",
      "imageUrl": "https://...",
      "price": 19.99,
      "currency": "$",
      "rating": 4.5,
      "ratings": 1000,
      "unitsSold": 5000,
      "revenue": 99950,
      "profit": 18.5,
      "bsr": 120,
      "sellerCount": 5,
      "fulfillment": "FBA"
    }
  ]
}
```

**硬规则**：

- 顶层必须有 `products` 数组（不能是裸数组）
- 每条 product 至少含 `asin` 或 `title`
- `profit` 为百分数且**已 ×100**（12.3 = 12.3%）
- `productImageUrls` / `aboutItemFivePoint` 必须是数组

### 3.2 报告 HTML

需要精美报告时，SKILL.md「报告产物」章节末尾 handoff 给 `linkfox-report-generator`。**不要**在 JSON 里写 blocks / 自拼 HTML。

---

## 4. 自检

```bash
python scripts/validate_product_payload.py examples/sample-output.json
```

产物若输出商品列表，应复制 `scripts/validate_product_payload.py` 并在 `examples/` 放样本后执行上述命令。
