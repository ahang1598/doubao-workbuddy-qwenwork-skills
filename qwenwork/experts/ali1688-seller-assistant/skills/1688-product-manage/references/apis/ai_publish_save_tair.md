# 保存选品数据

**接口路径**: `POST /api/ai_publish_save_tair/1.0.0`  
**用途**: 保存商家选择的同款商品数据，返回发品跳转链接所需的 UUID（`aigcSelectCategoryTime`）

## 请求参数

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| picUrl | string | 是 | 商品图片链接（与发品识别使用的同一张图片 URL） |
| categoryId | string | 是 | 类目 ID（来源于 [AI 发品识别](./ai_publish_by_imageurl.md) 返回的 `categoryId`） |
| categoryName | string | 是 | 类目名称（同上） |
| tkItemIds | string[] | 是 | 相关商品 ID 列表（同上） |
| absoluteSameItemId | string | 是 | 商家选中的同款商品 ID |
| absoluteSameItemTitle | string | 是 | 商家选中的同款商品标题 |

## 响应结构

| 字段名 | 类型 | 描述 |
|--------|------|------|
| success | boolean | 请求是否成功 |
| dataJson | string | JSON 字符串，解析后含 `aigcSelectCategoryTime`（UUID） |

`dataJson` 解析后：

| 字段 | 类型 | 描述 |
|------|------|------|
| aigcSelectCategoryTime | string | UUID，用于拼接发品跳转链接 |

## 示例

### 请求示例

```json
{
  "picUrl": "https://cbu01.alicdn.com/img/ibank/O1CN01abc123.jpg",
  "categoryId": "1031910",
  "categoryName": "女士单肩包",
  "tkItemIds": ["728458413589", "728458413590"],
  "absoluteSameItemId": "728458413589",
  "absoluteSameItemTitle": "2024新款女士单肩包真皮手提包"
}
```

### 响应示例

```json
{
  "success": true,
  "dataJson": "{\"aigcSelectCategoryTime\": \"e8a1f2c4-7b6d-4f9a-9c10-1234567890ab\"}"
}
```

## 补充说明

### `aigcSelectCategoryTime` 用途

- 是后续生成 1688 发品跳转链接的**核心参数**
- 与 `categoryId` 共同拼接出商家发品页面 URL，预填类目 / 同款信息

### 跳转链接格式

```
https://offer-new.1688.com/aigc/publish.htm?operator=new&scene=effectiveType&aigcSelectCategoryTime={uuid}&catId={categoryId}
```

| 占位符 | 来源 |
|--------|------|
| `{uuid}` | 本接口响应中的 `aigcSelectCategoryTime` |
| `{categoryId}` | [AI 发品识别](./ai_publish_by_imageurl.md) 返回的 `categoryId` |

商家点击链接进入 1688 发品页面，在该页补充价格、库存、SKU 等信息后点击【发布商品】完成发布。

### 链接有效期

- 发品跳转链接**有效期为 3 天**
- 超期后链接失效，需重新走完「上传 → 识别 → 选品」流程获取新链接
- 批量发品 Excel 文件命名建议带过期时间，例如：  
  `批量发品链接_2026年5月21日15:30_过期2026年5月24日15:30.xlsx`

### 错误场景

| 场景 | 处理建议 |
|------|----------|
| categoryId / picUrl 与识别结果不一致 | 严格使用上一步识别返回的字段透传 |
| absoluteSameItemId 不在 effectiveItemIds 中 | 校验商家选品序号映射是否正确 |
| AK 未配置 | 执行 `configure` 命令配置认证信息 |
