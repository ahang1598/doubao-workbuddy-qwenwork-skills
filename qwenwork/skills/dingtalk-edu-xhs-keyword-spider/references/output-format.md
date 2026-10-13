# 输出格式模板

## HTML 舆情报告

搜索完成后，通过 `generate_report.sh` 脚本将搜索结果 JSON 生成为可视化 HTML 舆情报告，包含以下模块：

- **统计概览**：笔记总数、视频/图文分布、总点赞/收藏/评论
- **内容类型分布**：视频 vs 图文占比条形图
- **高频标签云**：从笔记 tag_list 中提取出现频率最高的标签
- **笔记详情列表**：按热度（点赞+收藏+评论）排序，展示标题、摘要、互动数据、标签、链接
- **免责声明**：数据来源与使用限制说明

## generate_report.sh 输入 JSON 格式

脚本读取合并了详情数据的搜索结果 JSON，标准格式如下：

```json
{
  "success": true,
  "query": "搜索关键词",
  "search_time": "2025-01-15 14:30",
  "total": 20,
  "notes": [
    {
      "note_id": "笔记ID",
      "title": "标题",
      "type": "image|video",
      "user": {
        "nickname": "昵称",
        "user_id": "用户ID"
      },
      "interact_info": {
        "liked_count": "点赞数",
        "collected_count": "收藏数",
        "comment_count": "评论数",
        "share_count": "分享数"
      },
      "tag_list": ["标签1", "标签2"],
      "desc": "笔记正文内容（从detail回填）",
      "xsec_token": "安全令牌",
      "url": "笔记URL"
    }
  ]
}
```

### 字段说明

| 字段                      | 类型     | 来源            | 说明                               |
| ------------------------- | -------- | --------------- | ---------------------------------- |
| `query`                   | string   | search          | 搜索关键词                         |
| `search_time`             | string   | 合并时添加      | 搜索时间，格式 YYYY-MM-DD HH:mm    |
| `total`                   | int      | search          | 笔记总数                           |
| `notes[]`                 | array    | search + detail | 笔记列表                           |
| `notes[].desc`            | string   | detail 回填     | 笔记正文，由 detail 接口获取后回填 |
| `notes[].tag_list`        | string[] | detail 回填     | 标签列表，由 detail 接口获取后回填 |
| `notes[].interact_info.*` | string   | search          | 互动数据，**字符串类型**           |
| `notes[].type`            | string   | search          | `image`（图文）或 `video`（视频）  |

### 详情回填规则

1. 搜索返回的 `notes` 中不含 `desc` 和 `tag_list` 字段
2. 对 Top 5 高互动笔记调用 `xhs_search.py detail` 获取详情
3. 将详情返回的 `desc` 和 `tag_list` 回填到对应笔记（通过 `note_id` 匹配）
4. 添加 `search_time` 字段
5. 保存为完整 JSON 传给 `generate_report.sh`

**注意：**

- `interact_info` 中的值为**字符串类型**，不是数字，脚本内部会转为 int 排序和统计
- `type` 取值为 `image`（图文）或 `video`（视频）
- `url` 中的 `xsec_token` 参数有时效性
- 未获取详情的笔记，`desc` 和 `tag_list` 字段不存在，报告中不显示摘要

## HTML 报告输出

脚本输出文件名格式：`xhs_sentiment_report_YYYYMMDD_HHMMSS.html`

报告为自包含单文件 HTML，可直接在浏览器中打开，无需额外依赖。
