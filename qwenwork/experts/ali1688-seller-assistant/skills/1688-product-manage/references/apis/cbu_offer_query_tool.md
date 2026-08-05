# 商品基础信息查询

**接口路径**: `POST /api/cbu_offer_query_tool/1.0.0`  
**用途**: 根据商品 offerId 查询商品基础信息（标题、主图列表）

## 请求参数

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| offerId | string | 是 | 商品 ID |

## 响应结构

| 字段名 | 类型 | 描述 |
|--------|------|------|
| success | boolean | 请求是否成功 |
| title | string | 商品标题 |
| images | string[] | 商品主图 URL 列表（最多 5 张） |

## 示例

### 请求示例

```json
{
  "offerId": "728458413589"
}
```

### 响应示例

```json
{
  "success": true,
  "title": "2024新款女士单肩包真皮手提包",
  "images": [
    "https://cbu01.alicdn.com/img/ibank/O1CN01abc123.jpg",
    "https://cbu01.alicdn.com/img/ibank/O1CN01def456.jpg",
    "https://cbu01.alicdn.com/img/ibank/O1CN01ghi789.jpg"
  ]
}
```

## 补充说明

- 响应中 `images` 数组顺序即为商品主图的展示顺序（第 1 张为封面图）
- 当 `success` 为 `false` 时，表示商品信息查询失败，需检查 offerId 是否正确
- 响应数据可能嵌套在 `data` 字段中（兼容格式：`resp.data.title`、`resp.data.images`）

## CLI 阶段命令

**所属阶段**：prepare（回合①）

prepare 阶段首先调用此接口查询商品基础信息（标题、主图列表），随后自动调用 [图片解析接口](./cbu_image_analyse_tool.md) 并发解析每张主图。

**CLI 命令**：
```bash
python3 cli.py ai_image_improve --offer_id <商品ID>
```

**Agent 输出要求**：
1. 「默认 prompt 表」：列为 `序号 / 图片(![](url)) / 推荐卖点 / 比例 / 默认 prompt（完整句子）`
2. 「解析参考表」：列为 `序号 / 构图摘要 / 可见卖点`
3. 不得自行 `--generate`，默认 prompt 仅供参考
