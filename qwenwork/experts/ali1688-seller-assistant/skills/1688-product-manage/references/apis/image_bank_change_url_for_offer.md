# 图片 URL 转换（图片银行）

**接口路径**: `POST /api/image_bank_change_url_for_offer/1.0.0`  
**用途**: 将 AI 生成的图片 URL 转换为图片银行可应用的 URL，使其能够作为商品主图使用

## 请求参数

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| picUrl | string[] | 是 | 待转换的图片 URL 列表 |

## 响应结构

| 字段名 | 类型 | 描述 |
|--------|------|------|
| success | boolean | 请求是否成功 |
| model | object[] | 转换结果列表 |
| model[].relativeUrl | string | 图片相对路径（需拼接前缀得到完整 URL） |
| msgInfo | string | 错误信息（失败时） |
| msgCode | string | 错误码（失败时） |

## 示例

### 请求示例

```json
{
  "picUrl": [
    "https://ai-generated.example.com/result/img_001.jpg",
    "https://ai-generated.example.com/result/img_002.jpg"
  ]
}
```

### 响应示例

```json
{
  "success": true,
  "model": [
    {
      "relativeUrl": "img/ibank/O1CN01converted001.jpg"
    },
    {
      "relativeUrl": "img/ibank/O1CN01converted002.jpg"
    }
  ]
}
```

## 补充说明

- **URL 拼接规则**：最终可应用的完整 URL = `https://cbu01.alicdn.com/` + `model[*].relativeUrl`
  - 示例：`relativeUrl` 为 `img/ibank/O1CN01converted001.jpg`，则完整 URL 为 `https://cbu01.alicdn.com/img/ibank/O1CN01converted001.jpg`
- **用途定位**：此接口是 AI 生成图片 → 商品主图应用的桥梁，生成的图片必须经过此接口转换后才能用于修改商品主图
- **响应数据可能嵌套在 `data` 字段中**（兼容格式：`resp.data.success`、`resp.data.model`）
- **错误处理**：当 `success` 为 `false` 时，可从 `msgInfo` 或 `msgCode` 获取错误原因
- **批量支持**：`picUrl` 支持多张图片同时转换，`model` 数组中的顺序与请求中 `picUrl` 的顺序对应

## CLI 阶段命令

**所属阶段**：apply（回合⑤）

apply 阶段首先调用此接口将生成的图片 URL 转换为图片银行可应用的 URL，随后调用 [修改商品主图接口](./cbu_skill_change_main_image.md) 完成主图替换。

**CLI 命令**：与主图修改共用同一 apply 命令：
```bash
python3 cli.py ai_image_improve --offer_id <X> --apply
python3 cli.py ai_image_improve --offer_id <X> --apply --select "1,3,5"
```

**重试策略**：自动重试最多 2 次（共 3 次尝试，间隔 2s），3 次均失败后提示商家手动处理。
