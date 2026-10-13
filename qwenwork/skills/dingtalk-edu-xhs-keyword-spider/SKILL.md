---
name: dingtalk-edu-xhs-keyword-spider
description: 搜索小红书关键词相关笔记并生成可视化HTML舆情报告，主要用于获取学校在小红书上的舆情信息。当用户需要查学校小红书舆情、搜索小红书笔记、分析小红书趋势、学校口碑/关键词监控时使用。不要在需要搜索微博/抖音/知乎、创建教案、批改作业、管理课程表时触发。
install_source: official
install_method: download
skill_id: official_Yu36WBNE
enabled_at: 1791893794223
version: 1.0.0
name_zh: 小红书学校舆情助手
---

# 小红书学校舆情搜索与报告助手

## ⚠️ 免责声明

本技能旨在帮助用户更快捷地获取学校在小红书上的舆情数据，**禁止用作其他用途**。

- 本技能需要用户**自己提供账号**进行登录操作，技能仅通过 Playwright 引导用户在浏览器中自行登录并提取 Cookie，不提供任何账号或代登录服务。
- 请**严格控制使用频率**。过于频繁使用会触发小红书平台的风控规则，可能导致账号被限流、封禁等违规后果，**请使用者自行衡量是否使用并承担相关风险**。
- 本技能仅供教育场景下的学校舆情监测与研究分析使用，**禁止用于商业用途、数据倒卖、恶意爬取等任何违法违规行为**。
- 使用本技能所产生的一切法律后果，由使用者自行承担，技能开发者不承担任何责任。

## 严格禁止

- 禁止编造搜索结果 — 所有笔记数据必须来自内置爬虫引擎真实接口返回
- 禁止使用他人Cookie — 仅使用本人账号通过浏览器登录获取的Cookie
- 禁止跳过Cookie有效性检查 — 搜索前**必须**验证Cookie可用
- 禁止跳过环境初始化 — 首次使用**必须**运行 `setup_env.sh`
- 禁止请求频率过高 — 两次搜索间隔**必须** ≥ 3秒
- 禁止将Cookie分享或上传到公开位置
- 禁止商业用途 — 仅限教育场景分析与学习研究

## 命令总览

| 命令/工具              | 用途                               | 必填参数                  |
| ---------------------- | ---------------------------------- | ------------------------- |
| `setup_env.sh`         | 安装Python/Node.js/Playwright依赖  | 无                        |
| `xhs_cookie.py`        | Playwright自动登录小红书获取Cookie | --output, --timeout       |
| `xhs_search.py search` | 搜索小红书关键词笔记               | --query, --cookie-file    |
| `xhs_search.py detail` | 获取笔记详细内容                   | --url, --cookie-file      |
| `generate_report.sh`   | 生成可视化 HTML 舆情报告           | search_json, [output_dir] |

## 意图判断

用户说"搜小红书/查小红书/小红书搜索/小红书笔记/小红书关键词/学校舆情/学校口碑":

- 搜索关键词 -- 流程A (搜索→获取详情→生成HTML报告)

用户说"小红书详情/看看这篇笔记/笔记内容":

- 查看详情 -- 流程B (获取详情→深度分析)

用户说"小红书趋势/小红书分析/热门话题/学校舆情分析":

- 趋势分析 -- 流程A (搜索更多量→获取详情→HTML报告)

用户说"Cookie过期/登录小红书/重新登录":

- 更新Cookie -- 流程C (Playwright登录→context.cookies获取→保存)

关键区分: 搜索=按关键词搜索学校相关笔记, 详情=获取单条笔记正文, 趋势=搜索+详情+HTML报告, 舆情=学校口碑与热点监测

## 核心工作流

### 流程A: 关键词搜索与HTML报告生成

```
# 1. 环境检查 — 首次使用必须! 检查依赖是否安装
ls SKILL_DIR/.env_ready
# 不存在 → bash SKILL_DIR/scripts/setup_env.sh

# 2. Cookie检查 — 必须验证! 提取cookies.json
ls SKILL_DIR/cookies.json
# 不存在 → 流程C

# 3. 执行搜索 — 提取搜索结果JSON
#    WORKSPACE_OUTPUTS_DIR = ~/.qwenworkcn/workspace/<chat_id>/outputs/
python3 SKILL_DIR/scripts/xhs_search.py search \
  -q "{关键词}" -n 20 --sort 0 \
  -c SKILL_DIR/cookies.json \
  -o WORKSPACE_OUTPUTS_DIR/xhs_search_result.json

# 4. 获取高互动笔记详情（Top 5）— 将详情合并到搜索结果JSON
#    读取搜索结果，按互动量排序取Top5，逐条获取详情
#    将详情的 desc、tag_list 等字段回填到对应笔记
python3 SKILL_DIR/scripts/xhs_search.py detail \
  -u "{note_url}" -c SKILL_DIR/cookies.json

# 5. 合并详情到搜索结果JSON — 构造完整输入数据
#    将步骤4获取的详情数据回填到搜索结果的对应笔记中
#    添加 search_time 字段
#    保存到 WORKSPACE_OUTPUTS_DIR/xhs_report_data.json
#    格式参照 references/output-format.md

# 6. 生成HTML报告 — 通过脚本生成可视化页面
bash SKILL_DIR/scripts/generate_report.sh WORKSPACE_OUTPUTS_DIR/xhs_report_data.json WORKSPACE_OUTPUTS_DIR/
# 输出: WORKSPACE_OUTPUTS_DIR/xhs_sentiment_report_YYYYMMDD_HHMMSS.html

# 7. 交付报告给用户 — 使用 present_files 工具展示 HTML 报告
#    调用 mcp__qw-builtin__present_files 传入报告文件路径
```

### 流程B: 笔记详情

```
# 直接获取详情 — 提取笔记完整内容
python3 SKILL_DIR/scripts/xhs_search.py detail \
  -u "{笔记URL}" -c SKILL_DIR/cookies.json -o WORKSPACE_OUTPUTS_DIR/xhs_detail.json
# 构造单条笔记报告数据 → 生成HTML报告
bash SKILL_DIR/scripts/generate_report.sh WORKSPACE_OUTPUTS_DIR/xhs_detail_report_data.json WORKSPACE_OUTPUTS_DIR/
```

### 流程C: Playwright自动登录获取Cookie

```
# 1. 运行Cookie获取脚本 — 自动打开浏览器引导登录
#    Playwright context.cookies() 可获取包括 httpOnly 的完整 Cookie
python3 SKILL_DIR/scripts/xhs_cookie.py -o SKILL_DIR/cookies.json
#    浏览器自动打开 → 用户扫码/手机登录 → 检测到 web_session → 自动保存
#    默认等待300秒，可用 -t 参数调整超时时间

# 2. 验证Cookie有效性 — 必须执行!
python3 SKILL_DIR/scripts/xhs_search.py search -q "测试" -n 1 -c SKILL_DIR/cookies.json
```

## 上下文传递

| 操作                     | 从返回中提取                           | 用于                           |
| ------------------------ | -------------------------------------- | ------------------------------ |
| `setup_env.sh`           | `.env_ready`                           | 环境就绪标记                   |
| `xhs_cookie.py`          | 完整Cookie字符串（含httpOnly）         | `cookies.json`                 |
| `xhs_search.py search`   | `notes[].url`, `notes[].interact_info` | `detail` 的 `--url` 和热度排序 |
| `xhs_search.py detail`   | `desc`, `tag_list`, `interact_info`    | 回填到搜索结果JSON → 报告生成  |
| 详情回填后的搜索结果JSON | 完整笔记数据+详情                      | `generate_report.sh` 输入      |
| `generate_report.sh`     | HTML文件路径                           | 浏览器打开展示                 |

## 数据格式

```python
# [正确] 搜索结果JSON
{"success": True, "query": "幼儿教育", "total": 20, "notes": [...]}

# [错误] success不是布尔值
{"success": "true", "notes": [...]}

# [错误] 缺少success字段
{"query": "幼儿教育", "notes": [...]}

# [正确] Cookie文件
{"cookies": "a1=xxx; webId=xxx; web_session=xxx"}

# [错误] Cookie值直接存储为字符串
"a1=xxx; webId=xxx; web_session=xxx"
```

## 错误处理

1. Cookie过期 → 运行 `python3 SKILL_DIR/scripts/xhs_cookie.py` 重新登录获取
2. Cookie获取失败（登录超时）→ 重新运行 `xhs_cookie.py`，用 `-t` 增加超时时间
3. Python依赖缺失 → 运行 `bash SKILL_DIR/scripts/setup_env.sh` 重新安装
4. Playwright浏览器缺失 → 运行 `playwright install chromium`
5. Node.js依赖缺失 → `cd SKILL_DIR && npm install`
6. 签名算法失败 → 检查Node.js依赖：`cd SKILL_DIR && npm install`
7. 搜索返回空 → 检查关键词、Cookie有效性、是否被限流
8. 笔记详情失败 → 检查URL格式（需含xsec_token），可能笔记已删除
9. 报告生成失败 → 检查搜索结果JSON格式（参照 references/output-format.md），确认notes数组非空
10. HTML报告过小（<1KB）→ 自检JSON结构：notes是否为空、interact_info字段是否完整

## 报告自检流程

### HTML 报告自检（步骤7后）

```
IF 报告文件不存在 OR 文件大小 < 1KB:
  1. 检查 generate_report.sh 退出码和 stderr
  2. 读取搜索结果 JSON 逐项排查:
     a. notes 数组是否为空但 total > 0 → 详情获取步骤可能丢失数据
     b. interact_info 中 liked_count/collected_count 等是否为字符串类型
     c. tag_list 格式是否正确（字符串数组）
     d. JSON 是否合法 → 中文引号、未转义字符
  3. 修正 JSON 后重新生成（最多重试 2 次）
  4. 仍失败 → 直接输出搜索结果 JSON 文本摘要作为替代报告
```

## 详细参考

- [references/api-reference.md](./references/api-reference.md) — 搜索/详情/报告命令完整参数
- [references/cookie-guide.md](./references/cookie-guide.md) — Cookie浏览器获取完整流程
- [references/output-format.md](./references/output-format.md) — 报告数据JSON格式与HTML报告说明
- [references/error-codes.md](./references/error-codes.md) — 错误码与故障排查
