# Site Registry

将商品页面按站点分类，每个站点有独立的 base workflow、品类探测和品类字段体系。本文档是 site detection 的权威索引——AI 在执行采集前读取此索引，根据用户请求匹配站点。

## Site Map

| Site Key | Display Name | Domain | Locale(s) | URL Template | Probe Path | Category Index |
|---|---|---|---|---|---|---|
| `amazon` | Amazon | amazon.com | us, jp, uk, de, ca, fr, it, es, au, mx, in, ae, sa, br, nl, se, sg | `https://www.amazon.{locale}/dp/{id}` | — | — |
| `shein` | Shein | shein.com | us | `https://us.shein.com/{slug}-p-{id}.html` | `sites/shein/_category-probe.json` | `sites/shein/categories/INDEX.md` |

`—` 表示该站点尚无该文件。探针不存在时跳过 Part 0，直接使用 base workflow。

## Site Detection Signal Priority

| Priority | Signal Source | Reliability | Example |
|---|---|---|---|
| 1 | URL domain 精确匹配 | 高 | `amazon.com/dp/` → amazon |
| 2 | Amazon ASIN 模式（`B` + 9 位字母数字） | 高（仅 Amazon） | `B0C5J7X5N5` |
| 3 | URL domain 模糊匹配（含 Shein 等） | 高 | `shein.com` → shein |
| 4 | 用户明确指定站点名 | 高 | "从亚马逊采集" |
| 5 | 无匹配信号 | — | **询问用户** |

## Adding a New Site

5 步：

1. **创建** `sites/<site-key>/base-full.json` — 该站点的完整采集 workflow（含站点特有选择器）
2. **创建** `sites/<site-key>/README.md` — 含 frontmatter 元数据（`site` / `url_template` / `known_gotchas` 等）+ 品类关键词表
3. **可选创建** `sites/<site-key>/_category-probe.json` — 轻量级品类探针（4 步以内）
4. **可选创建** `sites/<site-key>/categories/INDEX.md` + `fields/*.json` — 品类字段体系
5. **添加** 本 INDEX.md 表格中的一行 — URL 模板 / locale / 探针路径

不需要修改 SKILL.md 或 tools/ 下的任何文件。
