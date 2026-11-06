---
name: xiaoyi-image-search-win
description: 图片搜索技能。支持搜索图片并直接下载到本地临时目录，返回本地路径而非URL链接。适用于为文档、PPT、报告等场景查找配图素材。
---

# Image-Search: 多引擎图片搜索器

## 简介

图片搜索工具，支持两种模式：

- **下载模式（默认，推荐）**：搜索图片并逐张下载到本地临时目录（Windows：`%TEMP%\xiaoyi-image-search\{sn}`；Linux：`/tmp/xiaoyi-image-search/{sn}`），下载完一张立即输出该图片信息。**不返回原图URL，避免模型篡改链接的风险。**
- **URL模式（向后兼容）**：返回原图链接（OSMS 预签名 URL）、缩略图、标题、尺寸等信息。

> **桌面接入说明（小艺 Work Desktop）**
>
> - 图片搜索走主进程 skill API 代理（`np://claw-skill` 命名管道），业务鉴权由主进程自动注入，本 Skill **零业务凭证**，仅需主进程注入的环境变量 `CLAW_SKILL_TOKEN`。
> - 旧云沙箱兼容：`SERVICE_URL` 为空 → 默认 `np://claw-skill`（管道）；`np://` 开头 → 命名管道；`http(s)://` 开头 → 原 HTTP 直连（从 `.xiaoyienv` 读 `PERSONAL_API_KEY`/`PERSONAL_UID` 鉴权）。
> - 图片的 `img_ori_url` 为 OSMS 一次性预签名链接，下载保持 HTTP 直连（不经过管道代理）。

## 触发条件

当用户表达以下意图时，请激活此技能：

### 1. 直接指令型 (Direct Commands)

- "搜索一张关于XXX的图片"
- "帮我找几张XXX的图"
- "搜图 XXX"
- "执行 image-search"
- "运行图片搜索技能"

### 2. 素材需求型 (Asset Gathering)

- "帮我找一些配图素材"
- "我需要几张关于XXX的图片用于PPT"
- "给报告找些插图"
- "搜索一些XXX相关的图片素材"

### 3. 自然语言型 (Natural Language Intent)

- "有没有XXX的图片？"
- "能不能帮我搜一下XXX的图？"
- "我想要一些XXX的图片"

## 文件结构

```
xiaoyi-image-search-win/
    ├── package.json       # Node 依赖声明（由小艺 Work 后台安装）
    ├── package-lock.json  # Node 依赖锁文件
    ├── scripts            # 程序文件夹
    │ ├── index.js         # 主程序（CLI入口，支持下载模式）
    │ ├── env_loader.js    # 加载环境变量
    │ ├── image_search.js  # 请求服务（执行搜索逻辑）
    └── SKILL.md           # 使用说明（本文档）
```

## 参数说明

| 参数                 | 必填  | 默认值                              | 说明                         |
|:------------------ |:--- |:-------------------------------- |:-------------------------- |
| `query`            | 是   | -                                | 搜索关键词                      |
| `num_results`      | 否   | 5                                | 返回结果数量                     |
| `store`            | 否   | `osms`                           | 图片存储方式                     |
| `--download <dir>` | 否   | 系统临时目录`xiaoyi-image-search/{sn}` | 下载模式：逐张下载到指定目录，默认自动创建临时目录  |
| `--workspace`      | 否   | -                                | 直接交付模式：下载到当前任务工作空间的 `图片搜索/` 子目录 |
| `--url`            | 否   | -                                | URL模式：返回原图链接（向后兼容，不使用下载模式） |

## 输出格式

### 下载模式（`--download` 指定目录）

```
| 序号 | 标题 | 尺寸 | 本地路径 | 来源页面 |
|:---|:---|:---|:---|:---|
| 1 | XXX | 1920 x 1080 | `<系统临时目录>/xiaoyi-image-search/a1b2c3d4/image_01.jpg` | https://example.com |
| 2 | YYY | 800 x 600 | `<系统临时目录>/xiaoyi-image-search/a1b2c3d4/image_02.jpg` | https://example2.com |
```

**注意**：下载模式下不输出 `原图URL` 和 `缩略图`，避免AI模型输出时篡改链接。

### URL模式（无 `--download`）

```
| 序号 | 标题 | 尺寸 | 原图URL | 缩略图 | 来源页面 |
|:---|:---|:---|:---|:---|:---|
| 1 | XXX | 1920 x 1080 | https://... | https://... | https://example.com |
| 2 | YYY | 800 x 600 | https://... | https://... | https://example2.com |
```

## 核心逻辑

1. **依赖检查**：小艺 Work 会根据 Skill 根目录的 `package-lock.json` 在后台安装 Node.js 依赖；依赖未就绪时应等待客户端完成安装或在技能页重试，不在调用过程中自行执行 `npm install`。

2. **接收参数**：解析搜索关键词及可选参数。

3. **发送请求**：调用内部 ImageSearch 接口（`mcp_server_name: browser-use`, `mcp_function_name: image_search`）。

4. **解析响应**：`result` 字段为 JSON 字符串，需二次解析获取图片列表。

5. **下载（可选）**：逐张下载图片到指定目录，每下载完一张立即输出该图片信息（用 `<<<END_OF_IMAGE>>>` 分隔）。

6. **格式化输出**：下载模式下输出标题、尺寸、本地路径；URL模式下输出标题、尺寸、原图URL等。

## 使用方法

### 依赖安装

Node.js 依赖由小艺 Work 客户端依据 Skill 根目录的 `package-lock.json` 自动安装，调用方无需也不应在任务中执行 `npm install`。

### 命令行调用

```bash
# 用法1：默认下载模式（自动保存到系统临时目录/xiaoyi-image-search/{sn}，逐张下载并输出）
node /path/to/current/skill/scripts/index.js "黄山"
node /path/to/current/skill/scripts/index.js "黄山" 4

# 用法2：指定下载目录
node /path/to/current/skill/scripts/index.js "黄山" --download <目标目录>

# 用法3：指定存储方式
node /path/to/current/skill/scripts/index.js "黄山" 5 osms --download <目标目录>

# 用法4：URL模式（向后兼容）
node /path/to/current/skill/scripts/index.js "黄山" --url

# 用法5：用户直接索要图片文件时，持久化到当前任务工作空间
node /path/to/current/skill/scripts/index.js "黄山" --workspace
```

### 执行流程

> **前置条件：**客户端技能页中本 Skill 的依赖状态已就绪。

#### 1. 搜索并下载图片

```bash
# 执行搜索（依赖由小艺 Work 客户端预先就绪）
node /path/to/current/skill/scripts/index.js "黄山"
```

默认临时目录仅用于 PPT、报告等其他 Skill 的中间素材。用户直接要求搜索并交付图片时必须使用 `--workspace`，不得把系统临时目录中的图片作为最终交付。

#### 2. 解析输出，获取本地文件路径

```
输出格式：

<<<DOWNLOAD_DIR:<系统临时目录>/xiaoyi-image-search/a1b2c3d4>>>

| 序号 | 标题 | 尺寸 | 本地路径 | 来源页面 |
|:---|:---|:---|:---|:---|
| 1 | XXX | 1920 x 1080 | `<系统临时目录>/xiaoyi-image-search/a1b2c3d4/image_01.jpg` | https://example.com |
| 2 | YYY | 800 x 600 | `<系统临时目录>/xiaoyi-image-search/a1b2c3d4/image_02.jpg` | https://example2.com |
```

> 上例 `<系统临时目录>` 在 Windows 为 `%TEMP%`（如 `C:\Users\<用户>\AppData\Local\Temp`），在 Linux 沙箱为 `/tmp`。

#### 3. 发送图片给用户（按顺序返回）

按顺序逐张发送图片

```javascript
// 按序号顺序发送图片（1→2→3→...）
send_file_to_user(abs_file_path_list=["<任务工作空间>/图片搜索/黄山-a1b2c3d4/image_01.jpg"])
// 等待上一张发送完成
send_file_to_user(abs_file_path_list=["<任务工作空间>/图片搜索/黄山-a1b2c3d4/image_02.jpg"])
// 等待上一张发送完成
send_file_to_user(abs_file_path_list=["<任务工作空间>/图片搜索/黄山-a1b2c3d4/image_03.jpg"])
```

**注意**：

1. 图片按照表格中的序号顺序返回给用户。
2. 每次发送前确认该图片是否已发送，禁止重复发送

### 环境变量要求

**桌面形态（默认，推荐）：** 零配置零凭证，仅需主进程注入的环境变量：

- `CLAW_SKILL_TOKEN` — 管道代理本机防借用令牌（桌面形态必填，主进程注入）
- `SERVICE_URL` — 缺省 `np://claw-skill`（命名管道代理）；`np://` 开头 → 管道；`http(s)://` 开头 → 旧沙箱直连

**旧沙箱形态（兼容）：** 需要在 `~/.xiaoyienv` 或系统环境变量中配置（桌面形态无需）：

- `SERVICE_URL` — 服务基础地址
- `PERSONAL_UID` — 鉴权 UID
- `PERSONAL_API_KEY` — 鉴权 API Key

**必须严格遵守以下规则**

1. 禁止自动修正链接。
2. 禁止替换域名后缀，所有域名后缀必须严格保留原样：.cn 永远是 .cn，绝对不能改成 .com。
3. **禁止拆分关键词**：当搜索结果数量不满足用户要求时，严禁将关键词拆分成多个更宽泛的词进行多次搜索。例如：用户搜索"黄山日出"要求10张但只返回5张时，禁止分别搜索"黄山"和"日出"来凑数。必须保持原关键词不变，返回实际搜索到的结果即可。
