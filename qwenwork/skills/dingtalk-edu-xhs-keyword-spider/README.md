# 小红书关键词搜索与HTML舆情报告 — 钉钉技能

基于 [Spider_XHS](https://github.com/cv-cat/Spider_XHS) 爬虫引擎，搜索小红书关键词相关笔记，生成可视化 HTML 舆情报告。

## 功能简介

| 功能       | 说明                       | 典型触发词                     |
| ---------- | -------------------------- | ------------------------------ |
| 关键词搜索 | 按关键词搜索小红书笔记     | 搜小红书、查小红书、小红书搜索 |
| 笔记详情   | 获取单条笔记正文与标签     | 笔记详情、看看这篇笔记         |
| 趋势分析   | 搜索+HTML热门趋势报告      | 小红书趋势、热门话题           |
| Cookie管理 | 浏览器引导登录并提取Cookie | 登录小红书、Cookie过期         |

## 技术架构

- **爬虫引擎**：[Spider_XHS](https://github.com/cv-cat/Spider_XHS) — 小红书PC端签名算法与API封装（代码已内置，无需 git clone）
- **Cookie获取**：基于 Playwright 自动化浏览器引导用户登录，通过 `context.cookies()` 提取（包括 httpOnly）
- **报告输出**：通过 `generate_report.sh` 生成自包含 HTML 可视化舆情报告

## 前置条件

- Python 3.9+
- Node.js 20+
- Git

## 快速开始

1. **安装爬虫环境**（首次使用）：

   ```bash
   bash scripts/setup_env.sh
   ```

2. **登录小红书获取Cookie**：
   - 运行 `python3 scripts/xhs_cookie.py`，自动打开 Playwright 浏览器
   - 用户扫码/手机号登录
   - 登录成功后自动提取 Cookie（包括 httpOnly）并保存

3. **搜索关键词**：

   ```bash
   python3 scripts/xhs_search.py search \
     -q "幼儿教育" -n 20 --sort 0 -c cookies.json
   ```

4. **获取笔记详情**：

   ```bash
   python3 scripts/xhs_search.py detail \
     -u "https://www.xiaohongshu.com/explore/xxx?xsec_token=yyy" \
     -c cookies.json
   ```

5. **生成HTML舆情报告**：

   ```bash
   bash scripts/generate_report.sh <搜索结果JSON> <输出目录>
   ```

## 文件结构

```
dingtalk-edu-xhs-keyword-spider/
├── SKILL.md                          # 主技能文件
├── package.json                      # Node.js 依赖声明（crypto-js, jsdom）
├── README.md                         # 本文档
├── .skillignore                      # 忽略文件列表
├── scripts/
│   ├── setup_env.sh                  # 环境安装脚本（Python + Node.js + Playwright）
│   ├── generate_report.sh            # HTML 舆情报告生成器
│   ├── xhs_search.py                 # 搜索/详情 Python 脚本
│   ├── xhs_cookie.py                 # Playwright 登录获取 Cookie
│   ├── xhs_apis.py                   # 小红书 API 封装
│   ├── requirements.txt              # Python 依赖
│   ├── xhs_utils/                    # 工具模块
│   │   ├── xhs_util.py               # 签名算法与请求参数生成
│   │   ├── cookie_util.py            # Cookie 解析
│   │   └── http_util.py              # HTTP 超时配置
│   └── static/                       # 小红书签名算法 JS 文件
│       ├── xhs_main_260411.js        # 主签名算法
│       ├── xhs_rap.js                # x-rap-param 生成
│       ├── xhs_xray.js               # xray traceId 生成
│       ├── xhs_xray_pack1.js         # xray 打包文件
│       └── xhs_xray_pack2.js         # xray 打包文件
├── references/
│   ├── api-reference.md              # 搜索/详情命令完整参数说明
│   ├── cookie-guide.md               # Cookie 浏览器获取完整流程
│   ├── output-format.md              # 报告数据 JSON 格式与 HTML 报告说明
│   └── error-codes.md                # 错误码与故障排查
└── tests/
    └── testcases.json                # 评测用例
```

## 安全合规

- Cookie 仅用于搜索接口调用，禁止分享或上传
- 仅抓取公开可访问的小红书笔记信息
- 遵守小红书 robots.txt 协议
- 控制请求频率（间隔 ≥ 3秒）
- 数据仅限教育场景分析使用，禁止商业用途

## 使用示例

> "帮我搜一下小红书上关于幼儿教育的笔记"

Agent 执行搜索 → 获取笔记详情 → 生成 HTML 舆情报告

> "小红书上编程启蒙的趋势怎么样？"

Agent 搜索更多量 → 获取详情 → 生成 HTML 报告含高频标签和热度排名

> "Cookie 过期了"

Agent 打开 Playwright 浏览器引导重新登录 → 自动提取并保存新 Cookie
