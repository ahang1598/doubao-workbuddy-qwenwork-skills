---
site: shein
display_name: SHEIN
product_id_pattern: null
url_template: null
review_url_template: null
default_locale: us
post_process: null
tab_sensitive: true
category_detection: probe
known_gotchas:
  - "需要完整 URL：不能从数字 ID 拼 URL，必须由用户提供完整商品链接（含 slug）"
  - "class 名频繁变更：选择器使用 [class*='xxx'] 模糊匹配，selector 过期时走 Part 2 修复"
  - "详情区动态加载：材质/尺码等通过 tab 切换懒加载，base-full 不会自动点击 tab——品类字段依赖页面初始渲染内容"
  - "评论在商品页底部：reviews workflow 打开商品页（非独立评论页），通过 SCROLL 触发评论区域懒加载"
  - "校准方式：某字段长期采空 → 打开 Shein 商品页确认 DOM → 更新 base-full.json 中的 selector（追加不替换）"
---

# SHEIN 采集指南

## 品类关键词

AI 可根据用户输入中的关键词直接推断品类，跳过探针。
完整检测信号表见 [categories/INDEX.md](categories/INDEX.md)。

| 用户关键词 | categoryKey |
|---|---|
| "dress" / "shirt" / "top" / "pants" / "clothing" / "衣服" / "裙子" / "上衣" / "裤子" | `clothing` |
| "shoes" / "boots" / "sneakers" / "heels" / "鞋" / "靴子" / "凉鞋" | `shoes` |
| "bag" / "backpack" / "handbag" / "wallet" / "包" / "书包" / "钱包" | `bags` |
| "home" / "kitchen" / "decor" / "bedding" / "家居" / "厨房" / "收纳" | `home` |
| "makeup" / "skincare" / "cream" / "beauty" / "化妆品" / "护肤品" / "美妆" | `beauty` |
| "phone case" / "charger" / "cable" / "earphone" / "手机壳" / "充电器" / "数据线" / "耳机" | `electronics` |

## Locale 参考

当前仅支持 `us.shein.com`（US）。CLI 的 `--site` 参数固定为 `shein`。

## 可用 Workflow

| 场景 | 文件 |
|---|---|
| 完整商品详情 | `base-full.json` |
| 评论采集 | `base-reviews.json`（打开商品页，通过 SCROLL 触发底部评论懒加载） |

## 与 Amazon 的关键差异

| 维度 | Amazon | SHEIN |
|---|---|---|
| URL 构造 | ASIN → 模板拼接 | 必须用户提供完整 URL（含 slug） |
| 评论 | 独立评论页 URL | 商品页底部懒加载 |
| 详情区 | 静态渲染 | 动态加载（tab 切换触发） |
| CSS 稳定性 | 相对稳定 | 频繁变更，需定期校准 |
| 图片后处理 | `amazon_image_post.py` 放大缩略图 | 无需 |

## 维护者注意事项

- **选择器校准**：Shein class 名随版本更新变化，优先依赖 Part 2 自愈。确需手动更新时追加新选择器到数组头部，不删除旧项
- **品类字段定位**：所有品类共享 `product-intro__*` / `common-product__*` 命名体系，品类差异仅在详情区标签页内容
