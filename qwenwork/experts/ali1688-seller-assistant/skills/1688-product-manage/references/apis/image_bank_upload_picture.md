# 图片银行上传

**接口路径**: `POST /api/image_bank_upload_picture/1.0.0`  
**用途**: 将图片以 base64 格式上传到 1688 图片银行，返回可用于后续业务流程的图片 URL

## 请求参数

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| imageName | string | 是 | 图片名称（建议含扩展名，例如 `main.jpg`） |
| base64Str | string | 是 | 图片的 base64 编码字符串（不含 `data:image/...;base64,` 前缀） |

## 响应结构

| 字段名 | 类型 | 描述 |
|--------|------|------|
| __success__ | boolean | 请求是否成功 |
| model.relativeUrl | string | 图片在图片银行中的相对路径，需拼接 CDN 域名后使用 |

### 完整 URL 拼接规则

```
https://cbu01.alicdn.com/ + relativeUrl
```

例如 `relativeUrl = "img/ibank/O1CN01abc123.jpg"`，则完整 URL 为：

```
https://cbu01.alicdn.com/img/ibank/O1CN01abc123.jpg
```

## 示例

### 请求示例

```json
{
  "imageName": "main.jpg",
  "base64Str": "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAg..."
}
```

### 响应示例

```json
{
  "__success__": true,
  "model": {
    "relativeUrl": "img/ibank/O1CN01abc123.jpg"
  }
}
```

## 补充说明

### 图片压缩策略

上传前需保证图片大小 ≤ 1MB，压缩流程：

1. 先**逐步降低 JPEG quality**：从 95 开始，每次 -5
2. 若仍超过 1MB，则**缩小分辨率**：width/height 每轮 ×0.8
3. 缩小分辨率最多执行 **5 轮**
4. 仍无法压到 1MB 以内则报错（图片格式不受支持或源文件异常）

### 上传限制（重要）

- 所有图片**必须且只能**上传到图片银行（即本接口）
- **严禁**将图片上传 / 存储到图片银行以外的任何位置
- 后续业务（如发品识别）所用的图片 URL 需来自：
  - 图片银行域名 `cbu01.alicdn.com`
  - 或合法可公开访问的外部 URL

### 支持格式与大小

| 项 | 限制 |
|----|------|
| 格式 | JPG / PNG / WEBP |
| 大小 | ≤ 1MB（压缩后） |

### 错误场景

| 场景 | 处理建议 |
|------|----------|
| 文件不存在 | 校验图片路径 |
| 格式不支持 | 转换为 JPG / PNG / WEBP 后重试 |
| 压缩仍超限 | 客户端预先降采样后再上传 |
| AK 未配置 | 执行 `configure` 命令配置认证信息 |
