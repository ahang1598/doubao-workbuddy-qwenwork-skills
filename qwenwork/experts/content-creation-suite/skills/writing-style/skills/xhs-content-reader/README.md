# xhs-content-reader

小红书内容读取子技能，从 `store-zhongcao` 技能集独立打包，供风格学习向导调用。

## 环境要求与权限说明

本方案基于 **CDP (Chrome DevTools Protocol)** 协议，通过直接读取浏览器前端数据源来获取结构化内容。

*   **完全访问权限**：使用此方案需要给悟空（Agent）开放**完全访问权限**，以便其能启动带调试端口的 Chrome 进程并建立 WebSocket 连接。
*   **适用场景**：本地拥有 GUI 权限的环境。
*   **兜底方案**：如果用户未授权完全访问权限，或 CDP 连接失败（如沙箱环境限制、浏览器无法启动），系统将自动降级为 `browser_use + OCR` 方案。该方案通过浏览器自动化打开页面截图并进行文字识别，虽无法获取深层评论等结构化数据，但能确保基础内容的提取。

## 技术原理

通过 Chrome + stealth.js 反检测 + CDP 协议，从小红书网页版 `__INITIAL_STATE__` 提取结构化 JSON 数据。

## 依赖

- Python ≥ 3.9
- `requests` — HTTP 请求（连接 Chrome DevTools）
- `websockets` — CDP WebSocket 通信
- Google Chrome 浏览器（本地已安装）

## 安装

```bash
cd scripts
pip install requests websockets
```

## 命令

所有命令通过 `cli.py` 调用，输出 JSON，退出码：0=成功, 1=未登录, 2=错误。

### 1. check-login — 检查登录状态

```bash
python cli.py check-login
```

输出示例：
```json
{"logged_in": true}
```

### 2. search-feeds — 搜索笔记列表

```bash
python cli.py search-feeds --keyword "护肤" --count 10
```

关键参数：
- `--keyword`（必填）：搜索关键词
- `--count`：返回数量上限（1~200，默认20）
- `--sort-by`：排序（综合|最新|最多点赞|最多评论|最多收藏）
- `--note-type`：类型（不限|视频|图文）
- `--publish-time`：时间（不限|一天内|一周内|半年内）
- `--time-start` / `--time-end`：精确时间过滤（ISO8601格式）

输出中每个 feed 包含 `id` 和 `xsecToken`，供 get-feed-detail 使用。

### 3. get-feed-detail — 获取笔记详情

```bash
python cli.py get-feed-detail --feed-id <ID> --xsec-token <TOKEN>
```

**重要约束**：`feed_id` 和 `xsec_token` 必须配对使用，`xsec_token` 只能通过 `search-feeds` 获取。

关键参数：
- `--feed-id`（必填）：笔记 ID
- `--xsec-token`（必填）：安全令牌
- `--load-all-comments`：加载全部评论
- `--scroll-speed`：滚动速度（slow|normal|fast）

输出包含：标题、正文、作者、互动数据、标签、图片列表、评论列表。

### 4. close-browser — 关闭浏览器标签页

```bash
python cli.py close-browser
```

完成内容读取后调用，释放资源。

## 典型调用流程

```
1. check-login          → 确认已登录
2. search-feeds         → 获取 feed_id + xsec_token
3. get-feed-detail      → 提取完整笔记内容
4. close-browser        → 释放资源
```

## 文件结构

```
scripts/
├── cli.py              # 精简版 CLI 入口（4个命令）
├── chrome_launcher.py  # Chrome 进程管理
└── xhs/
    ├── __init__.py
    ├── cdp.py          # CDP WebSocket 通信（Browser + Page）
    ├── stealth.py      # 反检测 JS 注入
    ├── errors.py       # 异常体系
    ├── human.py        # 人类行为模拟参数
    ├── selectors.py    # CSS 选择器常量
    ├── types.py        # 数据类型定义
    ├── urls.py         # URL 构建
    ├── cookies.py      # Cookie 持久化
    ├── login.py        # 登录状态检查
    ├── search.py       # 搜索功能
    ├── feed_detail.py  # 笔记详情提取（核心）
    └── storage.py      # SQLite 本地存储
```
