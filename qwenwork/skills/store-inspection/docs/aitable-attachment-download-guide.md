# AI 表格附件字段下载链接获取指南

本文档说明在已知 `baseId`、`tableId`（sheetId）、`fieldId` 等信息时，如何获取 AI 表格中附件字段的下载链接。

## 核心流程

### 1. 获取 Base 信息

使用 `dws aitable base get` 命令获取 AI 表格的基本信息，包括所有数据表的列表：

```bash
dws aitable base get --base-id "<BASE_ID>" --format json
```

**返回示例：**
```json
{
  "data": {
    "baseId": "ndMj49yWjYqDovABsw7B0vqm83pmz5aA",
    "baseName": "门店巡检任务中心-0511",
    "tables": [
      {
        "fieldCount": 12,
        "tableId": "qNjliIl",
        "tableName": "素材收集任务-2026"
      }
    ]
  }
}
```

### 2. 获取字段信息

使用 `dws aitable field get` 命令获取指定数据表的所有字段信息，找到目标附件字段的 `fieldId`：

```bash
dws aitable field get --base-id "<BASE_ID>" --table-id "<TABLE_ID>" --format json
```

**返回示例：**
```json
{
  "data": {
    "fields": [
      {
        "fieldId": "EkbFXPQ",
        "fieldName": "AI 物料",
        "type": "attachment"
      },
      {
        "fieldId": "FdL0ujs",
        "fieldName": "素材",
        "type": "attachment"
      }
    ]
  }
}
```

> **注意：** 附件字段的 `type` 为 `"attachment"`，这是识别附件字段的关键标识。

### 3. 获取记录数据

使用 `dws aitable record list` 命令获取数据表中的记录，附件字段的值会包含完整的下载链接信息：

```bash
dws aitable record list --base-id "<BASE_ID>" --table-id "<TABLE_ID>" --format json
```

**返回示例：**
```json
{
  "data": {
    "records": [
      {
        "recordId": "SYKNaMy8fv",
        "cells": {
          "EkbFXPQ": [
            {
              "filename": "lQbPM4HdZpjyEL0AALCR6RCbxfvuCQnS7RX8vmYA.mp4",
              "resourceId": "a79d43f3-a17c-46ee-a9c1-5eebc9787190",
              "resourceUrl": "/core/api/resources/a79d43f3-a17c-46ee-a9c1-5eebc9787190/detail",
              "size": 12760108,
              "type": "video",
              "url": "https://alidocs2.oss-cn-zhangjiakou.aliyuncs.com/res/54Lq35oxZJkbMl7E/att/a79d43f3-a17c-46ee-a9c1-5eebc9787190.mp4?Expires=1778580198&OSSAccessKeyId=LTAI5tKTjg4Kq1HCdBJ8qpSp&Signature=chizvgKwPLor27URdarRAlk8bq0%3D"
            }
          ]
        }
      }
    ]
  }
}
```

## 下载链接结构

附件字段的值是一个数组，每个元素包含以下字段：

| 字段名 | 说明 | 示例 |
|--------|------|------|
| `filename` | 文件名 | `lQbPM4HdZpjyEL0AALCR6RCbxfvuCQnS7RX8vmYA.mp4` |
| `resourceId` | 资源唯一标识符 | `a79d43f3-a17c-46ee-a9c1-5eebc9787190` |
| `resourceUrl` | 资源内部 API 路径 | `/core/api/resources/a79d43f3-a17c-46ee-a9c1-5eebc9787190/detail` |
| `size` | 文件大小（字节） | `12760108` |
| `type` | 文件类型 | `video`、`image`、`document` 等 |
| `url` | **可直接访问的下载链接** | OSS 临时签名 URL |

## 关键说明

### 下载链接类型

1. **`url` 字段**：阿里云 OSS 临时签名 URL，可直接用于下载或预览
   - 包含 `Expires` 参数，表示链接过期时间（Unix 时间戳）
   - 包含 `OSSAccessKeyId` 和 `Signature` 参数，用于身份验证
   - 示例：`https://alidocs2.oss-cn-zhangjiakou.aliyuncs.com/res/.../file.mp4?Expires=1778580198&...`

2. **`resourceUrl` 字段**：钉钉内部 API 路径，需要通过钉钉认证才能访问
   - 通常不直接用于外部下载
   - 需要配合钉钉的认证机制使用

### 链接有效期

OSS 签名 URL 具有时效性，`Expires` 参数指定了链接的过期时间。超过该时间后，链接将失效，需要重新调用 `record list` 获取新的签名 URL。

### 多附件处理

如果某个记录的附件字段包含多个文件，`cells["<FIELD_ID>"]` 将返回一个数组，遍历数组即可获取所有附件的下载链接。

## 完整示例

假设要获取"素材收集任务 -2026"表中"AI 物料"字段的下载链接：

```bash
# Step 1: 获取 Base 信息（确认 tableId）
dws aitable base get --base-id "ndMj49yWjYqDovABsw7B0vqm83pmz5aA" --format json

# Step 2: 获取字段信息（确认 fieldId）
dws aitable field get --base-id "ndMj49yWjYqDovABsw7B0vqm83pmz5aA" --table-id "qNjliIl" --format json

# Step 3: 获取记录数据（提取下载链接）
dws aitable record list --base-id "ndMj49yWjYqDovABsw7B0vqm83pmz5aA" --table-id "qNjliIl" --format json
```

从返回结果中提取：
```python
# Python 伪代码示例
records = response["data"]["records"]
for record in records:
    attachments = record["cells"].get("EkbFXPQ", [])  # EkbFXPQ 是"AI 物料"字段的 fieldId
    for attachment in attachments:
        print(f"文件名: {attachment['filename']}")
        print(f"下载链接: {attachment['url']}")
        print(f"文件大小: {attachment['size']} bytes")
        print(f"文件类型: {attachment['type']}")
        print("---")
```

## 常见问题

### Q1: 如何判断字段是否为附件字段？

检查 `field get` 返回的 `type` 字段，值为 `"attachment"` 即为附件字段。

### Q2: 下载链接为什么会失效？

OSS 签名 URL 包含 `Expires` 参数，超过该时间后链接失效。解决方法是重新调用 `record list` 获取新的签名 URL。

### Q3: 如何批量获取多个记录的附件链接？

`record list` 支持分页，通过 `--cursor` 参数可以获取下一页数据。也可以结合脚本批量处理。

### Q4: 附件字段为空时返回什么？

如果某条记录的附件字段没有上传任何文件，`cells["<FIELD_ID>"]` 将不存在或返回空数组 `[]`。

## 相关文档

- [dws aitable 命令参考](../references/products/aitable.md)
- [URL 格式与处理规范](../references/url-patterns.md)
