# Shein Category Registry

将商品页面按品类分类，并为每个品类提供特有字段的 EXTRACT 步骤定义。本文档是 Shein category detection 的权威索引——AI 在执行采集前读取此索引，根据 probe workflow 返回的信号匹配品类。

Shein 与 Amazon 的关键差异：Shein 所有品类商品页共享相同的页面骨架和 CSS class 命名体系（`product-intro__*`、`common-product__*`），但不同品类的详情区（Description / Size & Fit / Specs 标签页）内容完全不同——服装有材质和尺码表，鞋履有跟高和鞋型，美妆有成分和净含量。

base-full.json 已覆盖 Shein 通用字段（title, price, original_price, discount, sku, color, color_options, size_options, main_image, images, bestseller_rank, bestseller_category, seller, seller_ship_from）。品类字段文件仅追加品类特有的 EXTRACT 步骤，不重复 base 中的通用字段。

## Category Map

| Category Key | Display Name | Shein 对应类目 | Detection Signals | Field File |
|---|---|---|---|---|
| `clothing` | 服装 / Clothing | Women, Men, Kids, Activewear, Sleepwear, Swimwear | breadcrumb 含 "Women"/"Men"/"Kids"/"Clothing"/"Dresses"/"Tops"/"Bottoms", detail_keys 含 "Material"/"Fabric"/"Fit"/"Neckline"/"Sleeve" | [fields/clothing.json](fields/clothing.json) |
| `shoes` | 鞋履 / Shoes | Shoes, Boots, Sandals, Sneakers, Heels, Flats | breadcrumb 含 "Shoes"/"Boots"/"Sandals"/"Heels"/"Sneakers", detail_keys 含 "Heel"/"Upper"/"Sole"/"Toe" | [fields/shoes.json](fields/shoes.json) |
| `bags` | 包袋 / Bags & Luggage | Bags, Backpacks, Handbags, Wallets, Luggage | breadcrumb 含 "Bags"/"Backpacks"/"Handbags"/"Luggage"/"Wallets", detail_keys 含 "Size"/"Dimensions"/"Strap"/"Closure"/"Interior" | [fields/bags.json](fields/bags.json) |
| `home` | 家居生活 / Home & Living | Home & Living, Kitchen & Dining, Home Decor, Bedding, Bath, Storage | breadcrumb 含 "Home"/"Kitchen"/"Bedding"/"Decor"/"Bath"/"Storage", detail_keys 含 "Material"/"Capacity"/"Dimensions" | [fields/home.json](fields/home.json) |
| `beauty` | 美妆个护 / Beauty & Health | Beauty, Makeup, Skincare, Hair Care, Nails, Personal Care | breadcrumb 含 "Beauty"/"Makeup"/"Skincare"/"Hair"/"Nails"/"Fragrance", detail_keys 含 "Ingredients"/"Net"/"Skin"/"Texture" | [fields/beauty.json](fields/beauty.json) |
| `electronics` | 电子配件 / Electronics | Phone Cases, Chargers, Cables, Earphones, Tech Accessories | breadcrumb 含 "Electronics"/"Phone"/"Charger"/"Cable"/"Headphone", detail_keys 含 "Compatible"/"USB"/"Battery"/"Spec" | [fields/electronics.json](fields/electronics.json) |
| `generic` | 通用 / Generic | 任何未匹配的类目 | 无明确信号 | 仅使用 base-full.json |

## Detection Signal Priority

信号按可靠性降序排列。当多个品类匹配时，优先选择信号命中数更多的品类。若平票，按 INDEX 表顺序选取第一个。

| Priority | Signal Source | Reliability | Example |
|---|---|---|---|
| 1 | breadcrumb 面包屑 | 高 — 直接反映 Shein 类目树 | `Home > WOMEN > Clothing > Dresses` |
| 2 | detail_keys 含品类特有字段 | 高 — 直接反映详情页标签内容 | `Heel height: 5cm` → shoes |
| 3 | 用户输入语义 | 低 — 用户可能说错 | "scrape these shoes" |

## Probe Workflow Signals Format

`_category-probe.json` 返回两类信号：

```json
{
  "breadcrumb": "Home > WOMEN > Clothing > Dresses > Casual Dresses",
  "detail_keys": [
    "Material: 95% Polyester, 5% Spandex",
    "Fit: Slim Fit",
    "Neckline: V-neck",
    "Sleeve Type: Short Sleeve",
    "Pattern Type: Solid"
  ]
}
```

AI 解析步骤：
1. 检查 `breadcrumb` 文本是否包含 Category Map 中的 Detection Signals 关键词
2. 检查 `detail_keys` 数组是否包含品类特有字段名（Material/Fabric/Heel/Dimensions/Ingredients 等）
3. 两个信号源结合判断：breadcrumb 为主，detail_keys 为确认

## Adding a New Category

只需 3 步：

1. **创建** `categories/fields/<category-key>.json` — 定义该品类的特有 EXTRACT 步骤
2. **添加** 本 INDEX.md 表格中的一行 — 包含 detection signals
3. **可选更新** SKILL.md Part 0.1 的关键词表 — 让用户可以直接说品类名跳过 probe

不需要修改 server、browser extension、base workflow 或任何 tools/ 文件。

## Keyword Hints (for SKILL.md Step 0.1)

用户输入中的关键词可直接推断品类，跳过 probe：

| 用户关键词 | 推断品类 | categoryKey |
|---|---|---|
| "dress" / "shirt" / "top" / "pants" / "skirt" / "jacket" / "sweater" / "clothing" / "衣服" / "裙子" / "上衣" / "裤子" / "外套" | 服装 | `clothing` |
| "shoes" / "boots" / "sneakers" / "heels" / "sandals" / "slippers" / "鞋" / "靴子" / "凉鞋" / "拖鞋" | 鞋履 | `shoes` |
| "bag" / "backpack" / "handbag" / "purse" / "wallet" / "luggage" / "包" / "书包" / "钱包" / "行李箱" | 包袋 | `bags` |
| "home" / "kitchen" / "decor" / "bedding" / "storage" / "bath" / "mug" / "cup" / "家居" / "厨房" / "收纳" / "杯子" | 家居生活 | `home` |
| "makeup" / "skincare" / "cream" / "serum" / "lipstick" / "nail" / "beauty" / "化妆品" / "护肤品" / "美妆" / "口红" / "香水" | 美妆个护 | `beauty` |
| "phone case" / "charger" / "cable" / "earphone" / "headphone" / "power bank" / "手机壳" / "充电器" / "数据线" / "耳机" / "充电宝" | 电子配件 | `electronics` |
