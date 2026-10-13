# API 参考

## xhs_search.py search

搜索小红书笔记，返回结构化JSON结果。

```bash
python3 SKILL_DIR/scripts/xhs_search.py search \
  --query <关键词> \
  --num <数量> \
  --sort <排序> \
  --type <笔记类型> \
  --time <时间范围> \
  --cookie-file <cookie文件> \
  --output <输出路径>
```

| 参数                   | 类型   | 必填 | 说明                                                      |
| ---------------------- | ------ | ---- | --------------------------------------------------------- |
| `--query` / `-q`       | string | 是   | 搜索关键词                                                |
| `--num` / `-n`         | int    | 否   | 搜索数量，默认20                                          |
| `--sort` / `-s`        | int    | 否   | 排序方式：0综合(默认) 1最新 2最多点赞 3最多评论 4最多收藏 |
| `--type` / `-t`        | int    | 否   | 笔记类型：0不限(默认) 1视频 2图文                         |
| `--time`               | int    | 否   | 时间范围：0不限(默认) 1一天内 2一周内 3半年内             |
| `--cookie-file` / `-c` | string | 否   | Cookie文件路径，默认 `cookies.json`                       |
| `--output` / `-o`      | string | 否   | 输出JSON文件路径，不指定则输出到stdout                    |

**返回示例（成功）：**

```json
{
  "success": true,
  "query": "幼儿教育",
  "total": 20,
  "notes": [
    {
      "note_id": "683fe17f0000000023017c6a",
      "title": "笔记标题",
      "type": "image",
      "user": {
        "nickname": "用户昵称",
        "user_id": "64c3f392000000002b009e45"
      },
      "interact_info": {
        "liked_count": "1234",
        "collected_count": "567",
        "comment_count": "89",
        "share_count": "12"
      },
      "xsec_token": "ABBr_cMzallQeLyKSRdPk9fwzA0torkbT_ubuQP1ayvKA=",
      "url": "https://www.xiaohongshu.com/explore/..."
    }
  ]
}
```

**返回示例（失败）：**

```json
{
  "success": false,
  "error": "Cookie无效或已过期",
  "query": "幼儿教育"
}
```

---

## xhs_search.py detail

获取笔记详细内容。

```bash
python3 SKILL_DIR/scripts/xhs_search.py detail \
  --url <笔记URL> \
  --cookie-file <cookie文件> \
  --output <输出路径>
```

| 参数                   | 类型   | 必填 | 说明                                |
| ---------------------- | ------ | ---- | ----------------------------------- |
| `--url` / `-u`         | string | 是   | 笔记完整URL（含xsec_token）         |
| `--cookie-file` / `-c` | string | 否   | Cookie文件路径，默认 `cookies.json` |
| `--output` / `-o`      | string | 否   | 输出JSON文件路径                    |

**返回示例：**

```json
{
  "success": true,
  "url": "https://www.xiaohongshu.com/explore/...",
  "note_id": "683fe17f0000000023017c6a",
  "title": "笔记标题",
  "desc": "笔记正文内容...",
  "type": "image",
  "user": {
    "nickname": "用户昵称",
    "user_id": "64c3f392000000002b009e45"
  },
  "interact_info": {
    "liked_count": "1234",
    "collected_count": "567",
    "comment_count": "89",
    "share_count": "12"
  },
  "tag_list": ["标签1", "标签2"],
  "time": 1718000000000,
  "last_update_time": 1718000000000
}
```

---

## generate_report.sh

根据搜索结果 JSON（含回填的详情数据）生成可视化 HTML 舆情报告。

```bash
bash SKILL_DIR/scripts/generate_report.sh <search_json> [output_dir]
```

| 参数          | 类型   | 必填 | 说明                                   |
| ------------- | ------ | ---- | -------------------------------------- |
| `search_json` | string | 是   | 合并了详情数据的搜索结果 JSON 文件路径 |
| `output_dir`  | string | 否   | 输出目录，默认 `/tmp`                  |

**输出：** 生成 `xhs_sentiment_report_YYYYMMDD_HHMMSS.html`

**输入 JSON 格式：** 参照 [output-format.md](./output-format.md)

**自检机制：**

- 生成后自动检查文件大小，< 1KB 输出 WARNING 及诊断信息
- 诊断项包括：notes 数组是否为空、interact_info 字段类型、tag_list 格式

---

## setup_env.sh

安装 Python 和 Node.js 依赖。

```bash
bash SKILL_DIR/scripts/setup_env.sh
```

**前置条件：**

- Python 3.10+
- Node.js 20+

**安装内容：**

1. 安装 Python 依赖（PyExecJS, requests, loguru, playwright）
2. 安装 Playwright 浏览器（Chromium — Cookie获取核心）
3. 安装 Node.js 依赖（crypto-js, jsdom — 签名算法核心）到 `SKILL_DIR/node_modules`

**安装完成后**会在 `SKILL_DIR/.env_ready` 记录就绪标记，搜索脚本自动检查。

---

## Cookie 管理

### Cookie 文件格式

`cookies.json` 文件格式：

```json
{
  "cookies": "a1=xxx; webId=xxx; web_session=xxx; ..."
}
```

### Cookie 来源

通过 Playwright 自动化浏览器登录小红书后获取，详见 [cookie-guide.md](./cookie-guide.md)。

### Cookie 有效期

- Cookie 有时效性，通常 7-30 天
- 失效后需重新登录获取
- 搜索返回错误时首先检查 Cookie 是否过期
