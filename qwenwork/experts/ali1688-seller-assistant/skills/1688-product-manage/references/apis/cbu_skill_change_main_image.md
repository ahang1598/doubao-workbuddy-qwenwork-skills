# 修改商品主图

**接口路径**: `POST /api/cbu_skill_change_main_image/1.0.0`  
**用途**: 修改指定商品的主图列表，将优化后的图片应用到商品

## 请求参数

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| offerId | string | 是 | 商品 ID |
| images | string[] | 是 | 新的主图 URL 列表（需为图片银行可应用的 URL） |

## 响应结构

| 字段名 | 类型 | 描述 |
|--------|------|------|
| success | boolean | 主图修改是否成功 |

## 示例

### 请求示例

```json
{
  "offerId": "728458413589",
  "images": [
    "https://cbu01.alicdn.com/img/ibank/O1CN01converted001.jpg",
    "https://cbu01.alicdn.com/img/ibank/O1CN01converted002.jpg",
    "https://cbu01.alicdn.com/img/ibank/O1CN01original003.jpg"
  ]
}
```

### 响应示例

```json
{
  "success": true
}
```

## 补充说明

- **前置依赖**：`images` 中的 URL 必须是经过 `image_bank_change_url_for_offer` 接口转换后的图片银行 URL（`https://cbu01.alicdn.com/` 前缀），直接使用 AI 生成的原始 URL 将导致修改失败
- **图片顺序**：`images` 数组的顺序即为商品主图的最终展示顺序（第 1 个元素为封面图）
- **部分应用场景**：当商家选择仅应用部分主图时，`images` 列表应包含优化后的图（替换位）+ 原图（保留位），保持完整的主图列表
- **响应数据可能嵌套在 `data` 字段中**（兼容格式：`resp.data.success`）
- **操作不可逆**：主图修改后立即生效，如需回退需重新调用此接口传入原始主图列表

## CLI 阶段命令

**所属阶段**：apply（回合⑤）

作为 apply 阶段的第二步，在 URL 转换成功后调用此接口完成主图替换。

**CLI 命令**：
- 全部应用：`python3 cli.py ai_image_improve --offer_id <X> --apply`
- 部分应用：`python3 cli.py ai_image_improve --offer_id <X> --apply --select "1,3,5"`

**Agent 输出要求**：「最终主图表」：列为 `序号 / 原图(![](url)) / 最终主图(![](url)) / 来源`

apply 成功后状态文件自动清理；如需再次优化同一商品，重新从 prepare 开始。
