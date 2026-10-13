# 常用命令速查

## 多维表格（lark-base）

### Base 管理

**新建 Base**
```bash
lark-cli base +base-create --name "项目名称"
```

**列出所有表**
```bash
lark-cli base +table-list --base-token <base_token>
```

### 表管理

**新建表**
```bash
lark-cli base +table-create --base-token <base_token> --name "表名" --fields '<fields_json>'
```

**删除表**
```bash
lark-cli base +table-delete --base-token <base_token> --table-id <table_id>
```

### 字段管理

**列出字段**
```bash
lark-cli base +field-list --base-token <base_token> --table-id <table_id>
```

**新建字段**
```bash
lark-cli base +field-create --base-token <base_token> --table-id <table_id> --json '{"type":"text","name":"字段名"}'
```

**新建关联字段**
```bash
lark-cli base +field-create --base-token <base_token> --table-id <table_id> --json '{"type":"link","name":"关联字段名","link_table":"<link_table_id>"}'
```

**新建单选字段**
```bash
lark-cli base +field-create --base-token <base_token> --table-id <table_id> --json '{"type":"singleSelect","name":"字段名","options":[{"name":"选项1","hue":"Blue"},{"name":"选项2","hue":"Green"}]}'
```

### 记录管理

**批量创建记录**
```bash
lark-cli base +record-batch-create --base-token <base_token> --table-id <table_id> --json '{
  "create_records": [
    {"字段名1": "值1", "字段名2": "值2"},
    {"字段名1": "值3", "字段名2": "值4"}
  ]
}'
```

**批量更新记录**
```bash
lark-cli base +record-batch-update --base-token <base_token> --table-id <table_id> --json '{
  "update_records": {
    "record_id_1": {"字段名": "新值"},
    "record_id_2": {"字段名": "新值2"}
  }
}'
```

**上传附件**
```bash
lark-cli base +record-upload-attachment --base-token <base_token> --table-id <table_id> --record-id <record_id> --field-id "字段名" --file <本地文件路径>
```

**注意**：附件上传必须用相对路径（当前目录下的文件），不能用绝对路径如 /tmp/

---

## 飞书文档（lark-doc）

### 读取文档

**读取文档内容**
```bash
lark-cli docs +fetch --doc <document_id> --doc-format markdown
```

**格式选项**：
- `markdown`：Markdown 格式
- `xml`：XML 格式
- `im-markdown`：IM Markdown 格式

### Wiki 文档

**获取 Wiki 节点信息**
```bash
lark-cli wiki +node-get --node-token <wiki_token>
```

返回的 `obj_token` 就是文档 ID，然后用 `docs +fetch` 读取内容。

---

## 图片生成（image_gen）

### 基本用法

```
image_gen 工具参数：
- prompt：图片描述
- width：宽度（像素）
- height：高度（像素）
- model_version：模型版本（默认 seedream_4.5）
```

### 常用尺寸

| 用途 | 尺寸 | 比例 |
|------|------|------|
| 角色全身立绘 | 1536×2048 | 3:4 |
| 场景全景 | 2048×2048 | 1:1 |
| 道具特写 | 1024×1024 | 1:1 |
| 头像特写 | 1024×1536 | 2:3 |
| 横版海报 | 2048×1536 | 4:3 |
| 竖版海报 | 1536×2048 | 3:4 |

### 一次生成多张

request_list 里放多个请求对象，每个对象有独立的 prompt、width、height。

---

## 视频生成（image_to_video / text_to_video）

### image_to_video（带参考图）

```
参数：
- prompt：视频描述
- image_reference_url_list：参考图 URL 列表（最多9张）
- ratio：视频比例（9:16, 16:9, 1:1, 4:3, 3:4, 21:9）
- duration：时长（5-15秒）
```

### text_to_video（纯文字）

```
参数：
- prompt：视频描述
- ratio：视频比例
- duration：时长（5-15秒）
```

### 常用比例

| 比例 | 用途 |
|------|------|
| 9:16 | 竖屏短剧、抖音、TikTok |
| 16:9 | 横屏视频、YouTube、B站 |
| 1:1 | 方形视频、Instagram |
| 3:4 | 竖版、小红书 |
| 21:9 | 宽屏、电影感 |

### 限制

- 一次最多生成 2 个视频
- 时长 5-15 秒
- image_to_video 最多 9 张参考图
- 生成时间：约 30 秒 - 2 分钟（取决于时长和复杂度）

---

## 文件下载

### 下载图片/视频

```bash
curl -L -o <本地路径> "<URL>"
```

### 批量下载

```bash
curl -L -o file1.png "url1" && curl -L -o file2.png "url2"
```

---

## 命名规范

### 图片文件

```
项目前缀_角色/场景/道具名[_视图].png
```

示例：
- `family_chengwei.png`（成薇正面）
- `family_chengwei_side.png`（成薇侧面）
- `family_kitchen.png`（厨房场景）

### 视频文件

```
项目前缀_场次_片段.mp4
```

示例：
- `family_sc1_clip1.mp4`（Sc1 片段一）
- `family_sc1_clip2.mp4`（Sc1 片段二）

---

## 工作目录

所有文件都放在当前工作目录下（项目根目录），不要放在 /tmp/ 或其他目录，因为附件上传需要相对路径。

### 推荐目录结构

```
项目目录/
├── 角色图/
│   ├── chengwei.png
│   ├── chengwei_side.png
│   └── ...
├── 场景图/
│   ├── kitchen.png
│   └── ...
├── 道具图/
│   └── ...
└── 视频/
    ├── sc1_clip1.mp4
    └── ...
```

或者简单点，所有文件都放根目录，用前缀区分。
