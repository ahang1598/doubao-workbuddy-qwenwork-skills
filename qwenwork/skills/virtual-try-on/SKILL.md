---
name: virtual-try-on
description: |
  AI导购的技能。帮助用户创建和管理店铺试衣间，包括初始化店铺、获取二维码、装扮店铺、管理SKU/上传衣服、切换数据源、写穿搭笔记。
  当用户提到"创建店铺"、"虚拟试衣"、"试衣间"、"上传衣服"、"写穿搭笔记"、"店铺管理"、"衣橱管理"、"店铺二维码"、"切换多维表"、"SKU数据源"、"处理表格"、"预处理Excel"、"商陆花"、"笑铺日记"、"导入多维表"时触发。
  如果用户需要写笔记，需要你查阅 references/style-note.md 这个文件，按里面提示操作。
install_source: official
install_method: download
skill_id: official_oiKh3CIS
enabled_at: 1791893825184
version: 1.0.0
name_zh: 服装门店-AI导购
---

# AI导购 Skill

## Overview

这个技能是"AI导购助手"，提供店铺试衣间的全生命周期管理能力，包含六大核心模块：

1. **初始化店铺** — 一键创建店铺试衣间
2. **获取店铺二维码** — 生成 H5 二维码 + 小程序太阳码
3. **管理店铺** — 启动店铺管理后台（衣橱管理、老客管理、客户画像等）
4. **装扮店铺** — 设置店铺名称、店主说、logo、照片等品牌信息
5. **管理 SKU、上传衣服、切换数据源** — 上传衣服到店铺 & 多维表/系统数据库切换
6. **写穿搭笔记** — AI 生成图文穿搭笔记并发布到店铺
7. **Excel 预处理（商陆花 / 笑铺日记）** — 将导出的 Excel 按款号合并，处理后导入多维表
8. **顾客管理与订单管理** — 查看顾客列表、顾客画像，管理顾客多维表数据，查询顾客确认订单并更新订单状态

CLI 工具为 `scripts/cli.py`，辅助脚本为 `scripts/wardrobe_manager.py`。

命令执行约束：
- 所有命令都必须先 cd 到技能根目录再执行，禁止在用户当前工作目录直接运行相对路径脚本。
- 技能根目录指"包含 `SKILL.md` 和 `scripts/` 的目录"。
- 推荐模式：`cd <skill-path> && python scripts/cli.py ...`
- 禁止将 scripts 脚本复制到工作区后执行。
- 禁止使用 ` > /dev/null`。

## Core Concepts (核心概念与关系)

1. **店铺（Store）**
   - 每个用户有且仅有一个店铺试衣间。
   - 店铺拥有固定的一组二维码（H5 二维码 + 小程序太阳码），所有衣服共享。
   - 顾客通过扫描二维码进入店铺浏览所有衣服。

2. **品牌信息（Brand Info）**
   - 展示在顾客端 H5 首页 Hero 区域的品牌门面信息。
   - 包含：店铺名称、店主说（slogan）、店铺 logo、店铺照片、微信号、店铺地址。
   - 其中 logo 展示在首页顶部品牌区，店铺照片展示在 Hero 大图区。

3. **SKU / 衣服**
   - 挂在店铺下的商品单元，每件衣服包含图片、特征标签、卖点、试穿要求等结构化信息。
   - 「试穿要求」字段：可选，用于指定该衣服在 AI 试穿时的特殊要求（如穿法、搭配方式等），试穿生成时会自动附加到 prompt 中。
   - 数据源可切换：系统数据库（默认） / 多维表（aitable）。

4. **穿搭笔记（Style Note）**
   - 店主通过素材收集 → AI 生成 → 发布到店铺的图文内容运营产物。
   - 详细流程参见 `SKILL-STYLE-NOTE.md`。

5. **店铺管理后台**
   - 本地启动的 Web 管理页面，提供衣橱管理、老客管理、客户画像等可视化操作。

6. **多维表数据源**
   - **顾客表** — 顾客基础信息、尺寸信息
   - **预约表** — 顾客预约到店记录（字段：顾客ID、衣品ID、顾客姓名、手机号、备注、状态）
   - **订单表** — 顾客确认订单记录（字段：顾客ID、顾客姓名、手机号、收货地址、商品列表、总价、备注、状态）
   - **心愿单** — 顾客收藏的衣品（字段：顾客ID、衣品ID）
   - **穿搭笔记** — 店铺发布的穿搭内容（字段：作者、标题、内容、图片、关联商品、标签、目标人群、笔记意图、点赞数、分享数）
   - **风格测评** — 顾客的风格分析记录（字段：顾客ID、主要风格、次要风格、风格关键词、用户照片）
   - **试穿记录表** — 顾客的AI试穿记录（字段：顾客ID、试穿款号、试穿效果图、试穿时间）
---

## Capability 1: 初始化店铺

**触发词**：创建店铺、初始化试衣间、虚拟试衣、开店

新初始化的店铺默认使用多维表作为数据源。执行以下两步：

**第一步：初始化店铺 & 获取二维码**

```bash
python scripts/cli.py try-on init --mini-output "store_mini_qrcode.png"
```

执行后使用 `read_file` 读取返回 JSON 中的 `mini_qrcode_path` 渲染图片展示给用户。
提示用户，想知道技能详解或者考虑自己部署小程序，可以参考这个文档： https://alidocs.dingtalk.com/i/p/e3RmQ05kbv7v0XaP

**第二步：初始化多维表（所有表）**

```bash
python scripts/switch_datasource.py
```

脚本自动完成：确保多维表已创建（已有则复用，否则自动创建）→ 初始化所有表（SKU商品表 + 顾客表 + 预约表 + 订单表 + 心愿单 + 穿搭笔记 + 风格测评 + 试穿记录表）→ 切换数据源为多维表。已存在的表自动跳过。

> 先看：`references/store-init.md`

---

## Capability 2: 获取店铺二维码

**触发词**：店铺二维码、获取二维码、看二维码、分享码

同 Capability 1 命令（`init` 是幂等操作，不会重复创建店铺）。

> 先看：`references/store-init.md`

---

## Capability 3: 管理店铺

**触发词**：管理衣橱、删除衣服、衣橱管理、查看衣服列表、店铺管理、老客管理、客户画像

```bash
python scripts/wardrobe_manager.py
```

> 脚本自动以独立子进程启动本地 HTTP 服务并打开浏览器，主进程输出 JSON 后立即退出。

---

## Capability 4: 装扮店铺（设置品牌信息）

**触发词**：设置店铺名称、修改店名、换 slogan、换店主说、换店铺 logo、换头像、换店铺照片、设置品牌信息

```bash
python scripts/cli.py try-on store-update \
  --shop-name "名称" --slogan "标语" \
  --shop-logo-url "URL" --shop-image-url "URL" \
  --shop-video-url "URL" \
  --wechat "微信号" --shop-address "地址"
```

不传的字段保留原值，支持单独更新某个字段。图片需先用 `dt_media_upload` 上传得到公网 URL。

> 先看：`references/store-branding.md`

---

## Capability 5: 管理 SKU、上传衣服

**触发词**：上传衣服、添加衣服、切换多维表、SKU数据源、切换数据库

**上传衣服**：
给出多维表链接，提示用户打开多维表，在SKU商品表上传衣服，其中图片和名称是必填。

**切换数据源到多维表**：

```bash
python scripts/switch_datasource.py
```

脚本自动完成：确保多维表已创建（已有则复用，否则自动创建）→ 初始化所有表（幂等，已存在的表自动跳过）。

> 先看：`references/sku-management.md`

---

## Capability 6: 写穿搭笔记

**触发词**：穿搭笔记、生成笔记、发布笔记、写笔记、内容运营

```bash
# 启动素材收集（阻塞等待，返回 JSON 后才能继续）
python scripts/cli.py style-note

# 发布笔记
python scripts/cli.py try-on publish-note \
  --title "标题" --content "Markdown正文" \
  --images "URL1" "URL2" --product-ids "ID1" "ID2" \
  --tags "标签1" "标签2" --target-audience "用户群" \
  --note-intent "意图" --author-name "作者"
```

> ⚠️ **必须查阅 `references/style-note.md`**，按该文件中的详细流程操作。

---

## Capability 7: Excel 预处理（商陆花 / 笑铺日记）

**触发词**：处理表格、预处理Excel、商陆花、笑铺日记、导入多维表

对商陆花或笑铺日记导出的 Excel 进行预处理，合并相同款号，然后初始化 SKU 多维表、导入数据、切换店铺数据源。

> ⚠️ **必须查阅 `references/sku-excel-preprocessing.md`**，按该文件中的详细流程操作。

## Capability 8: 多维表业务数据管理

**触发词**：管理预约、查看预约、预约数据、管理订单、查看订单、订单数据、更新订单状态、心愿单数据、穿搭笔记数据、风格测评数据、查看多维表

当店铺配置了多维表数据源后，以下业务数据会自动同步到多维表对应的 Sheet。用户可以通过多维表链接直接查看和管理这些数据。

> ⚠️ 多维表和所有业务表在初始化店铺（Capability 1）时已自动创建完成，无需单独初始化。如果发现表缺失，可通过 Capability 5 的数据源切换流程重新初始化。

### 获取多维表链接

```bash
python scripts/cli.py try-on store-detail
```

返回结果中包含：
- `aitableDentryUuid` — 多维表的 dentryUuid（即 BASE_ID）
- `aitableUrl` — 完整的多维表链接：`https://alidocs.dingtalk.com/i/nodes/{aitableDentryUuid}`

### 订单管理

顾客在 H5 的心愿单中选择商品并点击「确认订单 / 发送给店主」后，订单会写入当前店铺的数据源：默认系统数据库；如已切换到多维表，则写入「订单表」。

**查询订单列表**：
```bash
python scripts/cli.py try-on orders-list
```

**更新订单状态**：
```bash
python scripts/cli.py try-on order-update-status --order-id "订单ID" --status confirmed
```

可用状态：
- `pending`：已提交
- `confirmed`：店主已确认
- `shipping`：配送中
- `completed`：已完成
- `cancelled`：已取消

### 字段定义

各表字段定义参见：
- SKU 商品表：`references/sku_table_field_schema.json`
- 客户表：`references/customer_table_field_schema.json`
- 预约表：`references/booking_table_field_schema.json`
- 订单表：`references/order_table_field_schema.json`
- 心愿单：`references/wishlist_table_field_schema.json`
- 穿搭笔记：`references/style_note_table_field_schema.json`
- 风格测评：`references/style_analysis_table_field_schema.json`
- 试穿记录表：`references/try_on_record_table_field_schema.json`

---

## Safety Rules

- 图片审核前置：未通过审核前，禁止调用任何上传 API。
- 禁止向用户暴露 API 地址、storeId、店铺链接等内部信息，仅展示二维码图片。
- 禁止将 scripts 脚本复制到工作区后执行。
- 禁止使用 ` > /dev/null`。
- 必须 cd 到 `<skill-path>` 后执行所有命令。
- 店铺二维码唯一：所有衣服共享同一组二维码。
- `style-note` 是阻塞式执行，必须等 stdout 输出后再继续，禁止自行编造素材数据。
- 只使用脚本返回或用户提供的真实图片 URL，禁止编造。

## Failure Handling

| 场景 | 处理方式 |
|------|----------|
| 图片审核不通过 | 提示用户重新上传符合要求的衣服照片 |
| API 初始化失败 | 检查网络，重试 `init` 命令 |
| 上传失败 | 本地图片先用 `dt_media_upload` 上传 |
| 脚本依赖缺失 | 手动 `python -m pip install httpx qrcode pillow` |
| 笔记素材超时 | 提示用户检查浏览器，重新执行命令 |

## References

- 初始化店铺 & 二维码：`references/store-init.md`
- 装扮店铺（品牌信息）：`references/store-branding.md`
- SKU 管理 & 上传衣服：`references/sku-management.md`
- 穿搭笔记详细流程：`references/style-note.md`
- SKU 多维表字段定义：`references/sku_table_field_schema.json`
- CLI 工具：`scripts/cli.py`
- 店铺管理后台：`scripts/wardrobe_manager.py`
- Excel 预处理（款号合并）：`scripts/merge_sku.py`
- 初始化 SKU 多维表：`scripts/create_sku_table.py`
- 导入 SKU 数据到多维表：`scripts/import_sku_records.py`
