# OCR API 接入规范

---

## 接口基本信息

| 项目 | 值 |
|------|----|
| 请求方式 | POST |
| 数据格式 | multipart/form-data |
| 鉴权方式 | RicheeAI Token（放在请求 Header `richee-token` 中） |
| 支持输入 | 扫描 PDF、图片文件（PNG/JPG/JPEG/BMP/TIFF） |
| 接口地址 | `{RICHEEAI_API_BASE}/claw/contractFile/parseFile` |
| 测试地址 | `https://claw.richee.cn/claw-api/claw/contractFile/parseFile` |

---

## 请求格式

### Headers

```http
richee-token: <RICHEEAI_TOKEN>    # 认证 Token
User-Agent: RicheeAI-FadadaSearch/1.0
Content-Type: multipart/form-data; boundary=----FormBoundary7MA4YWxkTrZu0gW
```

### Body (multipart/form-data)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `files` | file | ✅ | 待上传的文件（支持多文件） |
| `fileType` | string | ✅ | 文件类型：`pdf`/`png`/`jpg`/`jpeg`/`bmp`/`tiff`/`tif` |

> **注意**：文件通过 `files` 字段上传（与普通 JSON body 不同），需构造标准的 `multipart/form-data` 请求体。`fileType` 字段用于告知服务端文件格式。

### 输入类型适配

| 输入材料 | `files` 内容 | `fileType` 示例 |
|----------|-------------|------------------|
| 扫描版 PDF / 图片式 PDF | PDF 文件二进制 | `pdf` |
| 独立图片文件 / 扫描件图片 / 截图 | 图片文件二进制 | `png` / `jpg` / `jpeg` |

---

## 返回格式

### 成功响应（HTTP 200）

```json
{
  "code": "000000",
  "message": "操作成功！",
  "success": true,
  "data": [
    {
      "fileName": "合同.pdf",
      "content": "解析后的文本内容..."
    }
  ],
  "callSuccess": true
}
```

> **说明**：
> - `code` 为字符串类型，成功时值为 `"000000"`
> - `data` 为数组，每个元素对应一个上传文件的解析结果
> - `fileName` 为原始文件名
> - **`content`** 为 OCR 解析后的文本内容（注意：不是 `parseResult`）
> - `callSuccess: true` 表示底层 OCR 调用成功
> - 成功判断：检查外层 `success == true` 且 `code == "000000"`

### 失败响应

```json
{
  "code": <非0>,
  "message": "错误描述",
  "data": null
}
```

---

## 调用示例

```python
import base64
import urllib.request
import urllib.parse
import ssl
import os
import json

RICHEEAI_TOKEN = os.environ.get("RICHEEAI_TOKEN", "")
RICHEEAI_API_BASE = os.environ.get("RICHEEAI_API_BASE", "https://claw.richee.cn/claw-api")

def parse_contract_file(file_path: str) -> dict:
    url = f"{RICHEEAI_API_BASE}/claw/contractFile/parseFile"
    file_name = os.path.basename(file_path)
    file_type = os.path.splitext(file_path)[1].lower().lstrip(".")

    headers = {
        "richee-token": RICHEEAI_TOKEN,
        "User-Agent": "RicheeAI-FadadaSearch/1.0",
    }

    boundary = "----FormBoundary7MA4YWxkTrZu0gW"
    with open(file_path, "rb") as f:
        file_content = f.read()

    body_parts = [
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="files"; filename="{file_name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n",
    ]
    body_parts.append(file_content)
    body_parts.append(b"\r\n")
    body_parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="fileType"\r\n\r\n'
        f"{file_type}\r\n"
    )
    body_parts.append(f"--{boundary}--\r\n")
    body = b"".join(body_parts)

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    ssl_context = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ssl_context, timeout=300) as response:
        return json.loads(response.read().decode("utf-8"))
```

---

## 限制与注意事项

| 限制项 | 值 |
|--------|----|
| 单文件最大体积 | 建议不超过 50MB |
| 接口超时时间 | 建议 timeout=300（5分钟） |
| 并发限制 | 按服务端配置 |

> **注意**：
> - 使用 `urllib.request.Request` 时，需手动构造 `multipart/form-data` 请求体，不能用 `urllib.parse.urlencode()`
> - `files` 字段支持多文件上传，同一个 `boundary` 内可添加多个文件块
> - 图片类型根据扩展名判断：`png`/`jpg`/`jpeg`/`bmp`/`tiff`/`tif`

---

## 变更记录

| 日期 | 变更内容 |
|------|----------|
| 2026-04-01 | 根据 `ContractFileController.parseFile` 接口补充完整接入规范 |
