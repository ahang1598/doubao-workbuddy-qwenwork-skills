---
name: school-sentiment-monitor
description: 监控指定学校在社交媒体上的舆论动态，进行情感分析、趋势研判和负面预警。当用户提到舆情监控、学校口碑、帮我盯着某学校、查看舆情报告时触发。不要在需要创建教案、批改作业、管理课程表时触发。
install_source: official
install_method: download
skill_id: official_7R25nhbc
enabled_at: 1791893820293
version: 1.0.0
name_zh: 学校社媒舆情监控
---

# 学校舆情监控助手

## ⚠️ 免责声明

- **用途限定**：本技能仅用于学校舆情分析场景（如校方口碑监测、负面舆情预警、家校沟通参考等），**严禁用于商业用途**（包括但不限于竞品监控、营销广告、舆情代运营、付费报告转售等）。
- **账号自备与自主使用**：本技能运行过程中需要用户自行准备微博、小红书、抖音、快手等平台的个人账号，并在自己的 Chrome 中（由 QoderWork 浏览器连接器「我的浏览器」操作的标签页）手动完成登录。账号的所有权与使用责任完全归属于用户本人。
- **风险自担**：使用过程中如出现账号被平台警告、限流、处罚、封禁等任何后果，均与本技能开发者无关，用户需自行承担。建议控制合理的查询频率，避免触发平台风控机制。
- **合规要求**：仅采集公开可访问的网络内容，禁止访问非公开信息、禁止违反各平台服务条款与 robots 协议、禁止用于任何违法违规用途。
- **数据使用**：采集结果仅供本技能生成舆情报告使用，用户应妥善保管报告内容，不得对外传播未脱敏的原始数据。

## 🔌 连接前置校验（CONNECTION GATE）

**在执行任何网页操作（打开页面、输入、点击、滚动、截图、读取页面内容）之前，必须先确认 QoderWork 浏览器连接器「我的浏览器」已就绪：**

1. 用户的 Chrome 已安装 QoderWork 浏览器扩展；
2. 「我的浏览器」连接器已在 QoderWork 中启用；
3. 当前活动标签页显示 QW 图标（表示该标签页已被连接、可被驱动）。

**若上述任一条件不满足 → 立即停止，使用 AskUserQuestion 提示用户先完成连接：**「请在你的 Chrome 中安装并启用 QoderWork 浏览器扩展，打开需要操作的标签页并确认其显示 QW 图标，然后回复继续」。

**在未连接成功前，严禁执行任何网页操作，更严禁编造/虚构搜索结果。**

## ❗❗❗ 核心红线（最高优先级）

**微博、小红书、抖音、快手必须通过 QoderWork 浏览器连接器「我的浏览器」执行定向搜索，这是本技能的核心价值与不可屈服的底线。**

原因：微博、小红书、抖音、快手是学校舆情爆发的主战场，占舆情信息量的70%以上。如果不通过「我的浏览器」连接器执行这四个平台的定向搜索：

- 用户将认为舆情监控严重不完整、无法信任
- 用户将丧失对本技能的信心，导致弃用
- 仅依赖 WebSearch 的结果远远不能满足用户对舆情全面性的期望

因此：**无论任何情况，微博、小红书、抖音、快手通过「我的浏览器」连接器的定向搜索不可跳过、不可用 WebSearch 替代、不可降级。**

## 严格禁止

- 禁止编造搜索结果 — 所有数据必须来自真实搜索，禁止虚构任何条目
- 禁止访问非公开信息 — 仅采集公开可访问的网络内容
- 禁止跳过微博/小红书/抖音/快手定向搜索 — 必须通过「我的浏览器」连接器执行定向搜索
- 禁止对微博/小红书/抖音/快手使用 WebSearch — 禁止 `site:weibo.com`、`site:xiaohongshu.com`、`site:douyin.com`、`site:kuaishou.com` 等 WebSearch 查询，这四个平台只能通过「我的浏览器」连接器定向搜索
- 禁止调整平台执行顺序 — 必须严格按 微博>小红书>抖音>快手>今日头条>知乎>百度贴吧 顺序执行
- 禁止跳过任何平台 — 7 个平台必须全部执行，失败时记录原因并继续下一平台（**注：微博/小红书/抖音/快手遇到登录墙或验证码时，必须使用 AskUserQuestion 提示用户在其 Chrome 中 QoderWork 正在操作的标签页（带 QW 图标）手动完成登录/验证，完成后继续，严禁自行跳过**）
- 禁止跳过情感分析 — 每条舆情必须标注情感倾向和置信度
- 禁止在无搜索结果时生成报告 — 无结果时明确告知「本周期无新增舆情」
- 禁止手写 JSON — 配置和分析结果必须通过 Python json.dump() 生成
- 禁止在用户未确认前创建任务 — 必须展示配置摘要让用户确认
- 禁止跳过写入/报告自检 — 报告生成后必须执行自检，数据为空时必须排查原因

## 命令总览

| 命令/工具            | 用途                                                                                     | 必填参数                                          |
| -------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------- |
| `WebSearch`          | 搜索通用平台舆情                                                                         | query, time_range                                 |
| 「我的浏览器」连接器 | **QoderWork 浏览器连接器（builtin_browser MCP）** — 驱动用户 Chrome 执行浏览器操作：打开 URL、输入、点击、滚动、截图、读取渲染后的页面内容 | 操作类型 + URL（打开/导航时）+ 元素/文本（点击/输入时） |
| `WebFetch`           | 抓取高相关结果详情                                                                       | url                                               |
| `generate_report.sh` | 生成可视化 HTML 报告                                                                     | analysis_json, [output_dir]                       |

## 意图判断

用户说"舆情监控/监控学校/帮我盯着/口碑监控/舆情搜索/学校舆情":

- 创建监控 -- 流程A (询问配置→创建定时任务)
- 立即搜索 -- 流程B (直接执行搜索)

用户说"搜一下舆情/现在查一下/马上看看/立即搜索":

- 立即搜索 -- 流程B

用户说"详细报告/完整报告/舆情详情/查看报告/历史报告":

- 查看报告 -- 流程C

用户说"修改监控/暂停监控/恢复监控/取消监控/删除监控/监控列表/有哪些监控":

- 管理任务 -- 流程D (引导用户在 QoderWork 中管理定时任务)

关键区分: 创建监控=设置定时任务，立即搜索=单次执行，管理任务=在 QoderWork 中管理定时任务

## 核心工作流

### 流程A: 创建监控任务

```
# 1. 询问学校名称、别名、时间范围、频率 → 展示摘要，用户确认后继续

# 2. 使用 QoderWork 定时任务功能创建定时任务（自然语言指令）
# 3. 【强制校验】检查任务存在且状态为"启用"
# 4. 立即执行首次搜索 → 流程B
```

### 流程B: 执行舆情搜索

```
# 0. 【连接前置校验】确认「我的浏览器」连接器已就绪（见上方 CONNECTION GATE）；未连接则停止并提示用户连接

# 1. 加载任务配置
python3 SKILL_DIR/scripts/manage_task.py read [task_id]

# 2. 构建搜索查询
#    平台优先级: 微博 > 小红书 > 抖音 > 快手 > 今日头条 > 知乎 > 百度贴吧
#    【强制】必须严格按以上优先级顺序逐个平台执行，禁止跳过任何平台

# 3. 【平台1】微博定向搜索（「我的浏览器」连接器）
#    通过「我的浏览器」打开微博搜索页 → 读取渲染后的页面内容 → 检测登录 → 未登录则用 AskUserQuestion 请用户完成登录 → 读取结果
#    【必提取】title, summary, source("微博"), url, publish_time

# 4. 【平台2】小红书定向搜索（「我的浏览器」连接器）
#    通过「我的浏览器」打开小红书搜索页 → 读取渲染后的页面内容 → 检测登录 → 未登录则用 AskUserQuestion 请用户完成登录 → 读取结果
#    【必提取】title, summary, source("小红书"), url, publish_time

# 5. 【平台3】抖音定向搜索（「我的浏览器」连接器）
#    通过「我的浏览器」打开抖音搜索页 → 读取渲染后的页面内容 → 检测登录 → 未登录则用 AskUserQuestion 请用户完成登录 → 读取结果
#    【必提取】title, summary, source("抖音"), url, publish_time

# 6. 【平台4】快手定向搜索（「我的浏览器」连接器）
#    通过「我的浏览器」打开快手搜索页 → 读取渲染后的页面内容 → 检测登录 → 未登录则用 AskUserQuestion 请用户完成登录 → 读取结果
#    【必提取】title, summary, source("快手"), url, publish_time

# 7. 【平台5】今日头条 (WebSearch)
#    WebSearch(query="{alias} site:toutiao.com", time_range=...)
#    【必提取】title, summary, source("今日头条"), url, publish_time

# 8. 【平台6】知乎 (WebSearch)
#    WebSearch(query="{alias} site:zhihu.com", time_range=...)
#    【必提取】title, summary, source("知乎"), url, publish_time

# 9. 【平台7】百度贴吧 (WebSearch)
#    WebSearch(query="{alias} site:tieba.baidu.com", time_range=...)
#    【必提取】title, summary, source("百度贴吧"), url, publish_time

# 9. 对高相关结果调用 WebFetch 获取详情 → 充实 summary 字段

# 10. 去重 + 情感分析 → 标准化 JSON (参照 references/topic-categories.md)
#    【必填字段】每条 item 必须包含:
#    title, summary, source, url, publish_time,
#    sentiment(positive/neutral/negative), sentiment_score(整数 0-100),
#    topic(T01~T99), severity(critical/important/normal), keywords(字符串数组)

# 11. 检查预警 (参照 references/sensitive-keywords.md)
#    一级敏感词 → severity = critical; 二级敏感词 + score >= 50 → important
#    【重要】生成 alerts 数组，每条必含: title, summary, sentiment_score, url, source, severity

# 12. 汇总生成 analysis JSON
#    【必填顶层字段】:
#    - school_name: 学校名称
#    - search_time: 当前时间戳 ("YYYY-MM-DD HH:mm:ss")
#    - period: 监控时段 ("起始日期 ~ 结束日期")
#    - total_count: **必须严格等于 items 数组的长度**。若上游统计口径不同（如去重前总数），请存入 raw_search_count，而 total_count 专指最终报告展示的条目数。
#    - sentiment_distribution: {"positive": N, "neutral": N, "negative": N}
#    - platform_distribution: {"微博": N, "抖音": N, ...} — 按平台统计条数
#    - items: 舆情条目数组
#    - top_keywords: 统计所有 items 中 keywords 出现频次，取 Top20
#      每项: {"word": "", "count": N, "sentiment": "该词关联的主要情感"}
#    - alerts: severity 为 critical/important 的条目副本

# 13. 调用 generate_report.sh 生成 HTML 报告
#    将 analysis JSON 保存到 ~/.qwenworkcn/workspace/<chatId>/outputs/sentiment-analysis.json
#    bash SKILL_DIR/scripts/generate_report.sh ~/.qwenworkcn/workspace/<chatId>/outputs/sentiment-analysis.json ~/.qwenworkcn/workspace/<chatId>/outputs/
#    【数据一致性强制修正】脚本内部会自动将 total_count 修正为 len(items)，确保报告展示无误。
#    生成后用 present_files 工具把 HTML 报告交付给用户（不要用 open 命令）

# 14. 【自检】检查报告文件
#    检查 HTML 文件是否存在且非空（size > 1KB）
#    若为空或异常 → 读取 analysis JSON 排查：items 数组是否为空、sentiment_distribution 是否缺失、字段类型是否正确
#    修正后重新生成，最多重试 2 次
```

### 流程C: 查看报告

```
# 读取最近分析 JSON → 调用 generate_report.sh 生成 HTML → 用 present_files 工具交付给用户
bash generate_report.sh ~/.qwenworkcn/workspace/<chatId>/outputs/sentiment-analysis.json ~/.qwenworkcn/workspace/<chatId>/outputs/
# 然后用 present_files 工具把生成的 HTML 报告交付给用户（不要用 open 命令）
```

### 流程D: 管理任务

```
在 QoderWork 中管理定时任务（QoderWork 支持定时任务/计划任务）
```

## 上下文传递

| 操作                        | 从返回中提取                                                                    | 用于                                    |
| --------------------------- | ------------------------------------------------------------------------------- | --------------------------------------- |
| 用户输入                    | `school_name`, `aliases`                                                        | 搜索查询构建                            |
| 用户输入                    | 时间范围选择                                                                    | 生成 `period` 字段                      |
| `WebSearch` /「我的浏览器」 | 标题(title)、链接(url)、摘要(summary)、发布时间(publish_time)、来源平台(source) | `WebFetch` / 情感分析输入               |
| `WebFetch`                  | 正文内容                                                                        | 充实 `summary` 字段                     |
| 情感分析                    | `sentiment`, `sentiment_score`, `severity`, `topic`, `keywords`                 | items 数组                              |
| items 统计                  | 平台计数、关键词频次                                                            | `platform_distribution`, `top_keywords` |
| 分析汇总 JSON               | `~/.qwenworkcn/workspace/<chatId>/outputs/sentiment-analysis.json`                                             | `generate_report.sh` 参数               |

## 数据格式

### 舆情条目 JSON（items 数组中的每个元素）

```python
# [正确] 完整字段 — 所有字段均为必填
{"title": "食堂卫生问题被曝光",
 "summary": "有家长反映该校食堂存在食材过期问题，引发关注",
 "source": "微博",
 "url": "https://weibo.com/...",
 "publish_time": "2025-01-15 14:30",
 "sentiment": "negative",
 "sentiment_score": 85,
 "topic": "T04",
 "severity": "critical",
 "keywords": ["食堂", "中毒", "过期"]}

# [错误] 缺少 summary — 报告中摘要区域为空
{"title": "标题", "source": "微博", "sentiment": "negative", "sentiment_score": 85}

# [错误] 缺少 publish_time — 报告中时间显示为空
{"title": "标题", "summary": "摘要", "source": "微博"}

# [错误] sentiment_score 是字符串 — 应为整数
{"sentiment_score": "85"}

# [错误] severity 取值不在枚举中 — 仅允许 critical/important/normal
{"severity": "urgent"}
```

### top_keywords 数组中的每个元素

```python
# [正确] 必须包含 word + count + sentiment 三个字段
{"word": "食堂", "count": 8, "sentiment": "negative"}
{"word": "升学率", "count": 5, "sentiment": "positive"}
{"word": "师资", "count": 3, "sentiment": "neutral"}

# [错误] 缺少 count — 关键词云无法计算字号
{"word": "食堂", "sentiment": "negative"}

# [错误] 缺少 sentiment — 关键词云颜色无法区分
{"word": "食堂", "count": 8}
```

### alerts 数组中的每个元素

```python
# [正确] 预警条目必须包含以下全部字段
{"title": "食堂卫生问题被曝光",
 "summary": "有家长反映该校食堂存在食材过期问题",
 "sentiment_score": 85,
 "url": "https://weibo.com/...",
 "source": "微博",
 "severity": "critical"}

# [错误] 缺少 summary — 预警卡片描述为空
{"title": "标题", "severity": "critical"}

# [错误] severity 不在枚举 — 仅允许 critical/important
{"severity": "high"}
```

### analysis JSON (generate_report.sh 输入 - 顶层结构)

```python
# [正确] 完整顶层字段 — 所有字段均为必填
{"school_name": "杭州云谷学校",
 "search_time": "2025-01-15 15:00:00",
 "period": "2025-01-08 ~ 2025-01-15",
 "total_count": 12,
 "sentiment_distribution": {"positive": 5, "neutral": 3, "negative": 4},
 "platform_distribution": {"微博": 4, "抖音": 3, "快手": 2, "知乎": 2, "百度贴吧": 1},
 "items": [{...}, {...}],
 "top_keywords": [{"word": "食堂", "count": 8, "sentiment": "negative"}, ...],
 "alerts": [{"title": "...", "summary": "...", "sentiment_score": 85, "url": "...", "source": "...", "severity": "critical"}, ...]}

# [错误] 缺少 search_time — 报告头部生成时间为空
# [错误] 缺少 period — 报告头部监控时段为空
# [错误] 缺少 platform_distribution — 平台分布图表为空
# [错误] items 为空数组但 total_count > 0
# [错误] sentiment_distribution 缺失或键名错误(如用pos代替positive)
```

## 错误处理

1. WebSearch 返回空 → 换用备选查询词重试一次
2. WebFetch 抓取失败 → 跳过该条，仅保留搜索摘要
3. **微博/小红书/抖音/快手登录检测与兜底（强制流程）**：
   - **步骤一**：通过「我的浏览器」读取渲染后的页面内容后，必须尝试提取至少一条有效舆情条目（如视频标题、作者名）。
   - **步骤二**：若提取结果为空或无法识别有效内容，**严禁直接关闭标签页或跳过该平台**。
   - **步骤三（强制兜底）**：必须立即通过「我的浏览器」对当前页面截图。
   - **步骤四**：由 QoderWork 直接查看该截图，明确判断：“页面上是否有‘立即登录’、‘扫码登录’等弹窗？是否显示了搜索结果？”
   - **步骤五**：根据视觉分析结果判定：
     - 若确认为登录墙/验证墙 → 使用 AskUserQuestion 请用户在其 Chrome 中带 QW 图标的标签页手动完成登录/验证，完成后继续；若仍无法获取，则记录失败原因并标注「该平台因登录限制未能获取完整结果」。
     - 若确认为无结果 → 标注「该平台暂无相关舆情」。
4. JSON 生成失败 → 检查引号，改用中文引号「」
5. 脚本执行失败 → 检查退出码和 stderr，确认 JSON 路径和格式
6. HTML 报告为空或异常 → 自检 analysis JSON 结构（见下方）

## 报告自检流程

### HTML 报告自检（步骤 8）

```
IF 报告文件不存在 OR 文件大小 < 1KB:
  1. 检查 generate_report.sh 退出码和 stderr
  2. 读取 analysis JSON 逐项排查:
     a. items 数组是否为空但 total_count > 0 → 情感分析步骤可能丢失数据
     b. **total_count 是否等于 len(items)** → 若不一致，脚本会自动修正，但应记录警告
     c. sentiment_distribution 是否缺失或键名错误 → 应为 positive/neutral/negative
     d. top_keywords 是否缺少 word/count/sentiment 键
     e. alerts 中是否包含非法 severity 值 或缺少 summary/url/source 字段
     f. items 中是否缺少 summary/publish_time 字段 → 报告中摘要/时间区域为空
     g. 顶层是否缺少 search_time/period/platform_distribution → 报告头部/平台图表为空
     h. JSON 是否合法 → 中文引号、未转义字符
  3. 修正 analysis JSON 后重新生成（最多重试 2 次）
  4. 仍失败 → 直接输出 analysis JSON 文本摘要作为替代报告
```

## 渠道说明

本技能覆盖以下社交平台的舆情监控：微博、小红书、抖音、快手（通过 QoderWork 浏览器连接器「我的浏览器」定向搜索）、知乎、百度贴吧、今日头条（通过 WebSearch 搜索）。

**平台执行顺序**：微博 > 小红书 > 抖音 > 快手 > 今日头条 > 知乎 > 百度贴吧。

## 详细参考

- [references/workflow-details.md](./references/workflow-details.md) — 完整工作流程 (流程A/B/C/D)
- [references/api-reference.md](./references/api-reference.md) — generate_report.sh 脚本参数
- [references/output-templates.md](./references/output-templates.md) — 通知消息与预警模板
- [references/search-strategy.md](./references/search-strategy.md) — 搜索策略与平台优先级
- [references/topic-categories.md](./references/topic-categories.md) — 舆情主题分类编码表
- [references/sensitive-keywords.md](./references/sensitive-keywords.md) — 预警敏感词库
