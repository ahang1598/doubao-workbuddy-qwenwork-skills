# AI 发品识别

**接口路径**: `POST /api/ai_publish_by_imageurl/1.0.0`  
**用途**: 通过图片 URL 调用 AI 识别同款商品，返回类目信息与同款候选列表

## 请求参数

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| picUrl | string | 是 | 图片链接，须来自图片银行（`cbu01.alicdn.com`）或合法可公开访问的外部 URL |

## 响应结构

| 字段名 | 类型 | 描述 |
|--------|------|------|
| success | boolean | 请求是否成功 |
| dataJson | string | 识别结果的 JSON 字符串（需二次 `JSON.parse` 解析）；为空表示无法识别 |

### dataJson 解析后字段详解

| 字段 | 类型 | 描述 |
|------|------|------|
| categoryId | string | 类目 ID（用于后续保存选品 & 拼接跳转链接） |
| categoryName | string | 类目名称 |
| tkItemIds | string[] | 相关商品 ID 列表 |
| effectiveItemIds | object[] | 同款商品列表，每项结构见下表 |

`effectiveItemIds` 子字段：

| 字段 | 类型 | 描述 |
|------|------|------|
| sameItemId | string | 同款商品 ID |
| sameItemTitle | string | 同款商品标题 |
| sameItemPicUrl | string | 同款商品图片 URL |
| sameItemSellerPoint | object | 同款商品卖点（属性键值对，如 `{"颜色":"黑色","尺码":"L"}`） |

## 示例

### 请求示例

```json
{
  "picUrl": "https://cbu01.alicdn.com/img/ibank/O1CN01abc123.jpg"
}
```

### 响应示例

```json
{
  "success": true,
  "dataJson": "{\"categoryId\":\"1031910\",\"categoryName\":\"女士单肩包\",\"tkItemIds\":[\"728458413589\",\"728458413590\"],\"effectiveItemIds\":[{\"sameItemId\":\"728458413589\",\"sameItemTitle\":\"2024新款女士单肩包真皮手提包\",\"sameItemPicUrl\":\"https://cbu01.alicdn.com/img/ibank/O1CN01xxx.jpg\",\"sameItemSellerPoint\":{\"材质\":\"真皮\",\"风格\":\"通勤\"}}]}"
}
```

### 无 dataJson 的响应示例

```json
{
  "success": true,
  "dataJson": ""
}
```

## 补充说明

### 图片来源要求

- 必须为图片银行 URL（`cbu01.alicdn.com`）或合法可公开访问的 URL
- 本地路径 / 私网链接不可直接传入，需先通过 [图片银行上传](./image_bank_upload_picture.md) 转换

### 无同款回退逻辑

- 当 `dataJson` 为空字符串或解析后无 `effectiveItemIds` 时：
  - 视为 **AI 无法识别图片内容**
  - 返回默认跳转链接 `https://offer-new.1688.com/select.htm`
  - 商家可在该页面**手动选择类目并发品**
  - 不进入 [保存选品数据](./ai_publish_save_tair.md) 流程

### 错误场景

| 场景 | 处理建议 |
|------|----------|
| picUrl 不可访问 | 改用图片银行 URL 或确保外链可公开访问 |
| dataJson 为空 | 走无同款回退逻辑，返回手动发品链接 |
| AK 未配置 | 执行 `configure` 命令配置认证信息 |
