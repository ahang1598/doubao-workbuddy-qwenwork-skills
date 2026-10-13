# 活动推荐接口说明

## 接口地址

根据查询意图选择不同接口：

| 接口 | 用途 | 地址 |
|------|------|------|
| 模糊推荐 | 商家无具体活动条件描述，泛泛找活动 | `queryRecommend.json` |
| 条件推荐 | 商家有具体活动条件（类型/权益/场景等） | `recommend.json` |

> 两个接口均通过 URL query 参数 `param` 传递 JSON 字符串，但参数结构不同。

## 功能

根据商家自然语言描述，智能匹配并推荐营销活动。

## 请求方式

通过 URL query 参数 `param` 传递 JSON 字符串，参数值需做 URL 编码。

```
https://pre-ppxk.tmall.com/new/api/agent/recommend.json?param=<URL编码JSON>
https://pre-ppxk.tmall.com/new/api/agent/queryRecommend.json?param=<URL编码JSON>
```

### recommend.json 参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `question` | string | 是 | 商家的自然语言输入，描述活动需求 |

### queryRecommend.json 参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `solutionIds` | number[] | 否 | 方案ID，**按平台传入**：天猫 `[166, 148]`，淘宝 `[167, 146]` |
| `sellerId` | number | 否 | 商家ID |
| `activityId` | number | 否 | 活动ID |
| `activityName` | string | 否 | 活动名称 |
| `page` | number | 否 | 页码，默认 1 |
| `pageSize` | number | 否 | 每页条数，默认 5 |

### 请求示例

```bash
# 条件查询（有具体活动描述）
curl -s -G "https://pre-ppxk.tmall.com/new/api/agent/recommend.json" \
  --data-urlencode 'param={"question":"帮我推荐几个适合新品推广的活动"}'

# 模糊查询（无具体条件，天猫活动）
curl -s -G "https://pre-ppxk.tmall.com/new/api/agent/queryRecommend.json" \
  --data-urlencode 'param={"solutionIds":[166,148],"sellerId":123456,"activityId":252,"activityName":"天猫全域-场景合并新品标签","page":1,"pageSize":5}'
```

## 响应结构

两个接口返回结构不同。

### recommend.json 响应

```json
{
  "data": {
    "knowledgeTitleList": ["活动名(ID)", ...],
    "knowledgeTitle": "活动名(ID)",
    "contentList": ["# Markdown...", ...]
  }
}
```

| 字段路径 | 类型 | 说明 |
|----------|------|------|
| `data.knowledgeTitleList` | array | 活动名称列表，格式 `"活动名(ID)"` |
| `data.contentList` | array | 活动详情数组，每个元素是 Markdown 文本 |

### queryRecommend.json 响应

```json
{
  "data": {
    "total": 6,
    "pageSize": 5,
    "page": 1,
    "list": [
      {
        "activityId": 303,
        "activityName": "活动名",
        "knowledgeTitle": "活动名(ID)",
        "startTime": 1776614400000,
        "endTime": 1786723140000,
        "solutionIds": 146,
        "content": "# Markdown...",
        "desc": "简短描述"
      }
    ]
  },
  "info": { "ok": true, "traceId": "..." }
}
```

| 字段路径 | 类型 | 说明 |
|----------|------|------|
| `data.total` | number | 总活动数 |
| `data.list` | array | 活动对象数组，**包含结构化字段** |
| `data.list[].activityId` | number | 活动ID |
| `data.list[].activityName` | string | 活动名称 |
| `data.list[].startTime` | number | **毫秒时间戳**，需转换为日期 |
| `data.list[].endTime` | number | **毫秒时间戳**，需转换为日期 |
| `data.list[].desc` | string | 简短描述摘要 |
| `data.list[].content` | string | Markdown 文本，格式同 recommend |
| `info.ok` | boolean | 请求是否成功 |

> ⚠️ **两个接口的 content / contentList 中 Markdown 开头格式相同**，详见 `SKILL.md` 中的解析规则。

## 认证

接口可能需要认证（Cookie / Token），具体认证方式以平台实际要求为准。

## 错误码

| 错误码 | 说明 |
|--------|------|
| `SUCCESS` | 请求成功 |
| `PARAM_ERROR` | 参数错误（如 question 为空或 param 格式错误） |
| `SYSTEM_ERROR` | 系统内部错误 |
| `AUTH_ERROR` | 认证失败 |

## 注意事项

1. **内容大小**：`contentList` 中的 Markdown 文档可能包含数万字的推广内容（图片、HTML、操作指引等），解析时聚焦提取关键信息，不要全文展示
2. **超时设置**：建议设置 30s 超时，接口内部可能涉及模型推理
3. **重试策略**：网络异常时按 1s → 3s → 8s 退避重试，最多 3 次
