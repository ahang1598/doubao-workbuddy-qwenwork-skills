# 铺货执行参考文档

将 1688 商品铺货到用户的下游店铺（抖音、拼多多、淘宝等）。

---

## 一、CLI 调用

```bash
python3 scripts/cli.py distribute_helper execute \
  --app_key="{appKey}" \
  --shop_code="{shopCode}" \
  --channel="douyin" \
  --offer_ids="983715805496,983715805497" \
  --shop_name="大小姐精品铺子" \
  --tool_name="逸淘分销铺货"
```

### 接口工具名

`distribute_offer`

### 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `app_key` | 是 | 三方服务商唯一标识，从 shop_info 查询结果的 `toolList[].appKey` 获取 |
| `shop_code` | 是 | 目标店铺编码，从 shop_info 查询结果的 `shopList[].shopCode` 获取 |
| `channel` | 是 | 渠道标识（如 `douyin`、`pinduoduo`、`taobao`），从 shop_info 查询结果获取 |
| `offer_ids` | 是 | 商品 ID，多个用英文逗号分隔，如 `"983715805496,983715805497"` |
| `shop_name` | 否 | 店铺名称（用于展示），从 shop_info 查询结果的 `shopList[].shopName` 获取 |
| `tool_name` | 否 | 铺货工具名称（用于展示），从 shop_info 查询结果的 `toolList[].appName` 获取 |

> 接口实际传参：`outShopListStr` 为 `[{"code":"{shopCode}","channel":"{channel}"}]` 的 JSON 序列化字符串，CLI 内部自动拼装。

### 返回结构

```json
{
  "success": true,
  "data": {
    "errorCode": "200",
    "failCount": 0,
    "successCount": 1,
    "allCount": 1,
    "appKey": "{appKey}",
    "brandInvalidOfferIds": [],
    "successOfferIds": ["983715805496"],
    "failOfferIds": []
  }
}
```

---

## 二、结果反馈

根据返回的 `errorCode` 字段给出对应提示：

| errorCode | 含义 | 向用户展示的提示 |
|-----------|------|----------------|
| `200` / `0` | 全部成功 | ✅ 铺货完成！成功 {successCount} 件，共 {allCount} 件 |
| `210` | 部分成功 | ⚠️ 铺货部分成功。成功 {successCount} 件，失败 {failCount} 件，共 {allCount} 件 |
| `511` | 店铺授权失效 | ❌ 铺货失败：下游店铺授权信息已失效，请重新授权后再试 |
| `512` | 未完成铺货设置 | ❌ 铺货失败：您未完成铺货设置，请先完成设置后再铺货 |
| 其他 | 三方工具服务错误 | ❌ 铺货失败：三方工具服务请求错误，请稍后重试或联系技术支持 |

### 反馈模板

铺货命令返回的 JSON 中 `markdown` 字段已是完整的用户回复。**直接将 `markdown` 原样转发给用户，不得修改或追加任何内容。**

`markdown` 输出示例：
```
✅ 铺货完成！成功 1 件，共 1 件
店铺：大小姐精品铺子 | 铺货工具：逸淘分销铺货
- 成功商品 ID：700407352258

---

> ℹ️ 铺货结果到此结束。如有未铺货商品，请询问用户是否继续。
```

Agent 收到后只做两件事：
1. 原样转发 `markdown` 给用户
2. 如有未铺货商品，询问用户是否继续

**不得追加任何链接或额外文字，禁止增加‘后续操作建议’**。

> `errorCode` 为 `200`、`0` 或 `210` 时视为整体成功（`success: true`），其他均为失败。

---

## 三、注意事项

- 铺货前必须先通过 shop_info 确认目标店铺，获取 `appKey`、`shopCode`、`channel`
- 品牌商品（`brandInvalidOfferIds` 非空）铺货会失败，且有侵权风险。铺货前必须检查品牌授权状态（在选品决策分析阶段已检查），未授权商品引导用户申请授权：`[申请品牌授权](https://air.1688.com/app/channel-fe/distribution-work/brand.html#/auth_apply?offerId={offerId})`
- 单次铺货支持多个商品 ID，用逗号分隔
- **不得编造链接**：铺货结果反馈中只展示接口实际返回的数据，不得自行构造任何 URL（如"查看铺货进度"、"采购设置"、"自动售后"等链接均为虚构，会导致 404）
