---
site: amazon
display_name: Amazon（全站点）
product_id_pattern: "^B[0-9A-Z]{9}$"
url_template: "https://www.amazon.{locale}/dp/{ASIN}"
review_url_template: "https://www.amazon.{locale}/product-reviews/{ASIN}/"
default_locale: us
post_process: amazon_image_post.py
tab_sensitive: true
known_gotchas:
  - "跨 locale 选择器通用：域名不同但 DOM 一致，仅换 tabUrl"
  - "图片默认缩略图（~50px）：CLI scrape 自动执行 amazon_image_post.py 放大至 1500px"
---

# Amazon 采集指南

## Locale 参考

CLI 的 `--site` 参数映射由 `run_crawl.py` 的 `AMAZON_SITE_DOMAINS` 和 `sites/INDEX.md` 联合确定。
仅给出 ASIN 无 URL 时默认 `--site amazon-us`。

| URL Domain | Site Key |
|---|---|
| `amazon.com` | `amazon-us` |
| `amazon.co.jp` | `amazon-jp` |
| `amazon.co.uk` | `amazon-uk` |
| `amazon.de` | `amazon-de` |
| `amazon.ca` | `amazon-ca` |
| `amazon.fr` | `amazon-fr` |
| `amazon.it` | `amazon-it` |
| `amazon.es` | `amazon-es` |
| `amazon.com.au` | `amazon-au` |
| `amazon.com.mx` | `amazon-mx` |
| `amazon.in` | `amazon-in` |
| `amazon.ae` | `amazon-ae` |
| `amazon.sa` | `amazon-sa` |
| `amazon.com.br` | `amazon-br` |
| `amazon.nl` | `amazon-nl` |
| `amazon.se` | `amazon-se` |
| `amazon.sg` | `amazon-sg` |

## 可用 Workflow

| 场景 | 文件 |
|---|---|
| 完整商品详情 | `base-full.json` |
| 评论采集 | `base-reviews.json` |

## 维护者注意事项

- **新增 locale**：更新 `run_crawl.py` 的 `AMAZON_SITE_DOMAINS` + `sites/INDEX.md` 的 Locale(s) 列
- **选择器过期**：Part 2 自愈优先（FIND_SELECTOR），不要手动改 `base-full.json`。确需更新时追加而非替换旧选择器
- **图片后处理**：`scripts/amazon_image_post.py` 的 ZOOM_RULES 按优先级排列，裸 `_AA<N>_` 模式由 Rule 0.5 匹配
