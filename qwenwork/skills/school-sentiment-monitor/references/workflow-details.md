# 工作流程详细说明

## 定时任务管理说明

本技能使用 QoderWork 定时任务功能进行舆情监控的周期性执行（QoderWork 支持定时任务/计划任务）：

- **创建定时任务**：在流程A中通过工作流描述直接创建
- **编辑/删除/暂停定时任务**：用户可在 QoderWork 中管理定时任务
- 当用户意图涉及修改、删除、暂停、恢复、查看已有定时任务时，直接引导用户在 QoderWork 中管理定时任务

## 流程A：创建监控任务（详细）

### A1. 询问学校名称

AskUserQuestion: "请输入要监控的学校名称（支持多所，用逗号分隔）"

### A2. 生成别名

AI 自动推断学校常见简称/别名，如 "杭州云谷学校" → ["云谷学校", "云谷", "yungu"]
展示别名列表，询问用户是否补充

### A3. 询问时间范围

AskUserQuestion: 过去24小时 / 过去3天 / 过去7天 / 过去30天 / 自定义

### A4. 询问执行频率

AskUserQuestion: 每小时一次 / 每天一次 / 每周一次 / 仅执行一次

### A5. 展示配置摘要，用户确认后创建

配置摘要示例：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 舆情监控任务配置摘要
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏫 监控学校：杭州云谷学校
📝 学校别名：云谷学校、云谷、yungu
⏱️ 时间范围：过去7天
🔄 执行频率：每天一次
📊 预计首次搜索平台：微博、小红书、抖音、快手、知乎
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

#### A5.1 通过自然语言指令创建定时任务

```
向 QoderWork 发送指令：
"创建一个定时任务，任务名称为'学校舆情监控 - {学校名称}'，
{频率描述}执行以下舆情监控操作：
监控学校：{学校名称}
学校别名：{别名列表}
时间范围：{时间范围}
监控平台：微博、小红书、抖音、快手、知乎、百度贴吧、今日头条
执行内容：搜索上述学校在指定平台的舆情信息，进行情感分析，生成舆情报告并推送通知。"

频率映射：
* 每小时一次 → "每小时"
* 每天一次 → "每天早上8点"
* 每周一次 → "每周一早上8点"
```

#### A5.2 【强制校验】检查定时任务是否创建成功

**⚠️ 重要：必须执行此校验步骤，确保定时任务真正创建成功**

```
向 QoderWork 发送指令：
"查看我的定时任务列表，筛选名称为'学校舆情监控 - {学校名称}'的任务"

校验逻辑:
1. 检查返回的任务列表中是否存在名称为 "学校舆情监控 - {学校名称}" 的任务
2. 验证任务状态为"启用"或"活跃"
3. 验证执行频率与用户选择的频率一致
4. 验证任务配置中包含正确的学校名称信息

如果校验失败:
→ 输出错误信息："定时任务创建失败，请稍后重试或联系管理员"
→ 记录失败原因（QoderWork 返回的错误信息）
→ 终止流程，不要执行首次搜索

如果校验成功:
→ 继续执行步骤A5.3
```

#### A5.3 反馈创建结果给用户

```
输出创建成功通知：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 舆情监控定时任务创建成功
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏫 监控学校：{学校名称}
📝 学校别名：{别名列表}
⏱️ 时间范围：{时间范围}
🔄 执行频率：{频率描述}
⏰ 下次执行：{计算出的下次执行时间}
📋 任务ID：{从列表接口获取的任务ID}

✓ 定时任务已激活并校验通过
✓ 系统将按配置自动执行舆情监控
✓ 监控结果将生成报告并推送通知

💡 管理任务：如需修改、暂停或删除此任务，
   请在 QoderWork 中管理定时任务
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### A6. 立即执行首次搜索 → 进入流程B

## 流程B：执行舆情搜索（详细）

### B0. 【连接前置校验】确认「我的浏览器」连接器就绪

在执行任何网页操作前，必须确认 QoderWork 浏览器连接器「我的浏览器」已就绪：
- 用户的 Chrome 已安装 QoderWork 浏览器扩展；
- 「我的浏览器」连接器已在 QoderWork 中启用；
- 当前活动标签页显示 QW 图标。

若未连接 → 停止，使用 AskUserQuestion 请用户先完成连接，**严禁编造搜索结果**。

### B1. 加载任务配置

python3 SKILL_DIR/scripts/manage_task.py read [task_id]

### B2. 构建搜索查询

#### 平台优先级与执行顺序

❗ **强制要求：必须严格按以下优先级顺序逐个平台执行，禁止跳过任何平台，禁止调整顺序：**

| 顺序 | 平台     | 搜索方式          | 说明                   |
| ---- | -------- | ----------------- | ---------------------- |
| 1    | 微博     | 「我的浏览器」连接器 | 舆情覆盖最广、传播最快 |
| 2    | 小红书   | 「我的浏览器」连接器 | 种草笔记与家长口碑聚集地 |
| 3    | 抖音     | 「我的浏览器」连接器 | 视频平台舆情影响力大   |
| 4    | 快手     | 「我的浏览器」连接器 | 视频平台下沉市场覆盖   |
| 5    | 今日头条 | WebSearch         | 新闻资讯类             |
| 6    | 知乎     | WebSearch         | 深度讨论类             |
| 7    | 百度贴吧 | WebSearch         | 本地化讨论类           |

#### 「我的浏览器」连接器使用规范

微博、小红书、抖音、快手在未登录或受限状态下，通用搜索引擎的公开索引结果覆盖不全。**必须**使用 QoderWork 浏览器连接器「我的浏览器」执行定向搜索。

**核心原则：**

- 「我的浏览器」是 QoderWork 的浏览器连接器（builtin_browser MCP），直接驱动用户本机 Chrome 中带 QW 图标的标签页，而非平台自带的浏览器服务
- 支持的连接器操作能力：**打开/导航到 URL、在输入框中输入关键词、点击元素、滚动页面、截图、读取渲染后的页面内容（DOM/文本）**
- 典型流程：通过「我的浏览器」打开搜索页 → 输入关键词（或直接携带关键词的搜索 URL）→ 滚动加载 → 读取渲染后的页面内容 → 提取舆情条目
- 未登录时暂停流程，使用 AskUserQuestion 引导用户在其 Chrome 中带 QW 图标的标签页完成登录

#### 登录状态检测规范（重要）

❗ **禁止仅通过“页面是否有搜索框/搜索结果”来判断已登录。** 必须综合以下多种特征全面审查：

**未登录特征（命中任一则判定为未登录）：**

| 类别     | 具体特征                                                                      |
| -------- | ----------------------------------------------------------------------------- |
| 登录弹窗 | 页面出现「立即登录」、「去登录」、「登录/注册」、「登录查看更多」等弹窗或浮层 |
| 登录按钮 | 顶栏或页面中存在明显的「登录」、「Login」按钮                                 |
| 内容遮罩 | 搜索结果被局部隐藏或模糊化，提示登录后查看                                    |
| 提示文案 | 页面含「登录后可查看」、「请先登录」、「登录解锁更多内容」等文字              |
| 结果截断 | 仅显示少量结果且提示「登录看更多」                                            |

**验证墙/人机验证特征（命中任一则暂停等待用户操作）：**

| 类别      | 具体特征                                                 |
| --------- | -------------------------------------------------------- |
| 滑动验证  | 页面出现「请拖动滑块」、「滑动验证」等交互式验证         |
| 图片验证  | 「请点击图中的xx」、「请按顺序点击」等图形验证           |
| 行为检测  | 「检测到异常操作」、「请完成安全验证」、「网络环境异常」 |
| reCAPTCHA | Google reCAPTCHA 或类似的人机验证组件                    |

**检测流程：**

```
1. 通过「我的浏览器」读取渲染后的页面内容，获取页面状态
2. 审查返回内容：
   a. 是否包含验证墙特征 → 是 → 暂停，用 AskUserQuestion 提示用户完成验证
   b. 是否包含登录弹窗/按钮/文案特征 → 是 → 暂停，用 AskUserQuestion 提示用户登录
   c. 以上均无 → 判定为已登录，继续执行
3. 【强制兜底】若读取页面内容后提取到的有效舆情条目为 0，或返回内容异常简短：
   - 必须通过「我的浏览器」对当前页面截图
   - 由 QoderWork 直接查看截图，判断：“页面上是否有‘立即登录’、‘扫码登录’等弹窗？是否显示了搜索结果？”
   - 根据视觉分析结果重新判定登录状态
```

#### 搜索 URL 模板

微博高级搜索 URL：
`https://s.weibo.com/weibo?q={URL编码别名}&typeall=1&suball=1&timescope=custom:{起始日期}:{结束日期}`

小红书搜索 URL：
`https://www.xiaohongshu.com/search_result?keyword={URL编码别名}`

抖音搜索 URL：
`https://www.douyin.com/search/{URL编码别名}?type=video`

快手搜索 URL：
`https://www.kuaishou.com/search/video?searchKey={URL编码别名}`

#### WebSearch 查询构建

针对今日头条、知乎、百度贴吧，构建标准搜索查询：

```python
queries = []
for alias in [school_name] + aliases:
    queries.append(f"{alias} site:toutiao.com")   # 平台5
    queries.append(f"{alias} site:zhihu.com")     # 平台6
    queries.append(f"{alias} site:tieba.baidu.com")  # 平台7
```

### B3. 【平台1】微博定向搜索（「我的浏览器」连接器）

对每个别名执行微博定向搜索：

1. **打开页面**：

   ```
   通过「我的浏览器」打开/导航到：https://s.weibo.com/weibo?q={URL编码别名}&typeall=1&suball=1&timescope=custom:{起始日期}:{结束日期}
   ```

2. **检测登录状态与验证墙**：

   ```
   通过「我的浏览器」读取渲染后的页面内容
   ```

   按「登录状态检测规范」全面审查返回内容：
   - 检查是否存在验证墙/人机验证（滑动验证、图片验证、安全检测等）
   - 检查是否存在登录弹窗、「立即登录」「去登录」按钮、内容遮罩、「登录查看更多」提示
   - ❗ 禁止仅因“页面有搜索框或搜索结果”就判定为已登录

3. **验证墙 → 使用 AskUserQuestion 请用户完成验证**：
   使用 AskUserQuestion 提示用户：
   「检测到微博页面出现了安全验证（如滑动验证/图形验证）。请在你的 Chrome 中 QoderWork 正在操作的标签页（带 QW 图标）手动完成验证，完成后继续。」
   → 暂停流程，用户完成后重新读取页面内容检查状态

4. **未登录 → 使用 AskUserQuestion 请用户登录**：
   使用 AskUserQuestion 提示用户：
   「检测到微博需要登录才能获取完整搜索结果。请在你的 Chrome 中 QoderWork 正在操作的标签页（带 QW 图标）手动完成微博登录，完成后继续。」
   → 暂停流程，用户完成登录后通过「我的浏览器」重新导航到搜索 URL，然后继续

5. **人工选择放弃该平台**：
   若用户明确表示“跳过”、“放弃”或“不登录”，则记录失败原因并进入下一平台。

6. **已登录/登录完成后**：
   ```
   通过「我的浏览器」滚动页面（向下）
   通过「我的浏览器」读取渲染后的页面内容
   ```
   从页面内容中提取标题、摘要、链接、发布时间、互动量（点赞/评论/分享）。
   **【强制校验】**：若提取到的有效舆情条目为 0，必须立即通过「我的浏览器」截图并由 QoderWork 直接查看截图进行视觉校验，确认是否为隐性登录墙或内容加载失败。

### B4. 【平台2】小红书定向搜索（「我的浏览器」连接器）

对每个别名执行小红书定向搜索：

1. **打开页面**：

   ```
   通过「我的浏览器」打开/导航到：https://www.xiaohongshu.com/search_result?keyword={URL编码别名}
   ```

2. **检测登录状态与验证墙**：

   ```
   通过「我的浏览器」读取渲染后的页面内容
   ```

   按「登录状态检测规范」全面审查返回内容：
   - 检查是否存在验证墙/人机验证（滑动验证、图片验证、安全检测等）
   - 检查是否存在登录弹窗、「立即登录」「去登录」按钮、内容遮罩、「登录查看完整内容」提示
   - ❗ 禁止仅因“页面有搜索框或搜索结果”就判定为已登录

3. **验证墙 → 使用 AskUserQuestion 请用户完成验证**：
   使用 AskUserQuestion 提示用户：
   「检测到小红书页面出现了安全验证（如滑动验证/图形验证）。请在你的 Chrome 中 QoderWork 正在操作的标签页（带 QW 图标）手动完成验证，完成后继续。」
   → 暂停流程，用户完成后重新读取页面内容检查状态

4. **未登录 → 使用 AskUserQuestion 请用户登录**：
   使用 AskUserQuestion 提示用户：
   「检测到小红书需要登录才能获取完整搜索结果。请在你的 Chrome 中 QoderWork 正在操作的标签页（带 QW 图标）手动完成小红书登录，完成后继续。」
   → 暂停流程，用户完成登录后通过「我的浏览器」重新导航到搜索 URL，然后继续

5. **人工选择放弃该平台**：
   若用户明确表示“跳过”、“放弃”或“不登录”，则记录失败原因并进入下一平台。

6. **已登录/登录完成后**：
   ```
   通过「我的浏览器」滚动页面（向下）
   通过「我的浏览器」读取渲染后的页面内容
   ```
   从页面内容中提取标题、摘要、链接、发布时间、互动量（点赞/收藏/评论）。
   **【强制校验】**：若提取到的有效舆情条目为 0，必须立即通过「我的浏览器」截图并由 QoderWork 直接查看截图进行视觉校验，确认是否为隐性登录墙或内容加载失败。

### B5. 【平台3】抖音 / 【平台4】快手定向搜索（「我的浏览器」连接器）

对每个别名执行抖音、快手定向搜索（抖音 URL 见「搜索 URL 模板」，以下以快手为例）：

1. **打开页面**：

   ```
   通过「我的浏览器」打开/导航到：https://www.kuaishou.com/search/video?searchKey={URL编码别名}
   ```

2. **检测登录状态与验证墙**：

   ```
   通过「我的浏览器」读取渲染后的页面内容
   ```

   按「登录状态检测规范」全面审查返回内容：
   - 检查是否存在验证墙/人机验证（滑动验证、图片验证、安全检测等）
   - 检查是否存在登录弹窗、「立即登录」「去登录」按钮、内容遮罩、登录提示
   - ❗ 禁止仅因“页面有搜索框或搜索结果”就判定为已登录

3. **验证墙 → 使用 AskUserQuestion 请用户完成验证**：
   使用 AskUserQuestion 提示用户：
   「检测到快手页面出现了安全验证（如滑动验证/图形验证）。请在你的 Chrome 中 QoderWork 正在操作的标签页（带 QW 图标）手动完成验证，完成后继续。」
   → 暂停流程，用户完成后重新读取页面内容检查状态

4. **未登录 → 使用 AskUserQuestion 请用户登录**：
   使用 AskUserQuestion 提示用户：
   「检测到快手需要登录才能获取完整搜索结果。请在你的 Chrome 中 QoderWork 正在操作的标签页（带 QW 图标）手动完成快手登录，完成后继续。」
   → 暂停流程，用户完成登录后通过「我的浏览器」重新导航到搜索 URL，然后继续

5. **人工选择放弃该平台**：
   若用户明确表示“跳过”、“放弃”或“不登录”，则记录失败原因并进入下一平台。

6. **已登录/登录完成后**：
   ```
   通过「我的浏览器」滚动页面（向下）
   通过「我的浏览器」读取渲染后的页面内容
   ```
   从页面内容中提取标题、摘要、链接、发布时间、互动量（点赞/评论/分享）。
   **【强制校验】**：若提取到的有效舆情条目为 0，必须立即通过「我的浏览器」截图并由 QoderWork 直接查看截图进行视觉校验，确认是否为隐性登录墙或内容加载失败。

### B6. 【平台5】今日头条 (WebSearch)

对每个别名执行今日头条搜索：

```
WebSearch(query="{alias} site:toutiao.com", time_range=...)
```

【必提取】title, summary, source("今日头条"), url, publish_time

### B7. 【平台6】知乎 (WebSearch)

对每个别名执行知乎搜索：

```
WebSearch(query="{alias} site:zhihu.com", time_range=...)
```

【必提取】title, summary, source("知乎"), url, publish_time

### B8. 【平台7】百度贴吧 (WebSearch)

对每个别名执行百度贴吧搜索：

```
WebSearch(query="{alias} site:tieba.baidu.com", time_range=...)
```

【必提取】title, summary, source("百度贴吧"), url, publish_time

### B9. 对高相关结果调用 WebFetch 获取详情

选取所有平台（含微博、小红书、抖音、快手）搜索结果中互动量高或标题含敏感词的 Top 10 条，用 WebFetch 抓取正文

【重要】WebFetch 获取的正文内容用于充实对应条目的 `summary` 字段，确保摘要内容充分、准确

### B10. 去重

标题相似度 > 80% 的合并为同一条，通过 Python 脚本去重

### B11. 情感分析

对每条结果用 LLM 结构化分析，输出 JSON 格式，参照 SKILL.md 数据格式区块

【强制要求】每条舆情 item 必须包含以下全部字段：

| 字段            | 类型          | 说明               | 示例                                 |
| --------------- | ------------- | ------------------ | ------------------------------------ |
| title           | string        | 舆情标题           | "食堂卫生问题被曝光"                 |
| summary         | string        | 内容摘要(50-200字) | "有家长反映该校食堂存在食材过期问题" |
| source          | string        | 来源平台名称       | "微博"、"抖音"、"知乎"等             |
| url             | string        | 原文链接           | "https://weibo.com/..."              |
| publish_time    | string        | 发布时间           | "2025-01-15 14:30"                   |
| sentiment       | string        | 情感倾向           | positive/neutral/negative            |
| sentiment_score | int           | 情感强度(0-100)    | 85                                   |
| topic           | string        | 主题分类编码       | "T04"                                |
| severity        | string        | 严重程度           | critical/important/normal            |
| keywords        | array[string] | 关键词列表         | ["食堂", "中毒"]                     |

### B12. 检查预警

参照 references/sensitive-keywords.md：

- 一级敏感词命中 → severity = critical，立即预警
- 二级敏感词 + sentiment_score >= 50 → severity = important
- 负面 sentiment_score >= 80 → severity = important

### B13. 生成分析数据 JSON

生成包含情感分布、平台分布、关键词、预警等信息的汇总 JSON

【强制要求】analysis JSON 必须包含以下全部顶层字段：

| 字段                   | 类型   | 说明             | 注意事项                                                                                                 |
| ---------------------- | ------ | ---------------- | -------------------------------------------------------------------------------------------------------- |
| school_name            | string | 学校名称         | 必填                                                                                                     |
| search_time            | string | 报告生成时间戳   | 格式“YYYY-MM-DD HH:mm:ss”                                                                                |
| period                 | string | 监控时段描述     | 格式“起始日期 ~ 结束日期”                                                                                |
| total_count            | int    | 去重后舆情总数   | 必须等于 items 数组长度                                                                                  |
| sentiment_distribution | object | 情感分布统计     | 必须包含 positive/neutral/negative 三个键                                                                |
| platform_distribution  | object | 平台分布统计     | key=平台名, value=条数，从 items 的 source 字段统计                                                      |
| items                  | array  | 舆情条目数组     | 每项必含全部 11 个字段（见 B11）                                                                         |
| top_keywords           | array  | 热门关键词 Top20 | 每项: {word, count, sentiment}                                                                           |
| alerts                 | array  | 预警条目         | severity=critical/important 的 item 副本，每项含: title, summary, sentiment_score, url, source, severity |

#### top_keywords 生成规则

```python
# 统计所有 items 中 keywords 字段的词频
from collections import Counter
kw_counter = Counter()
kw_sentiment = {}  # 记录每个词关联的主要情感
for item in items:
    for word in item["keywords"]:
        kw_counter[word] += 1
        # 取该词出现次数最多的情感倾向
        kw_sentiment.setdefault(word, Counter())[item["sentiment"]] += 1

top_keywords = [
    {"word": w, "count": c, "sentiment": kw_sentiment[w].most_common(1)[0][0]}
    for w, c in kw_counter.most_common(20)
]
```

#### platform_distribution 生成规则

```python
# 统计所有 items 中 source 字段的平台计数
from collections import Counter
platform_distribution = dict(Counter(item["source"] for item in items))
```

#### alerts 生成规则

```python
# 从 items 中提取 severity 为 critical 或 important 的条目
alerts = [
    {"title": item["title"], "summary": item["summary"],
     "sentiment_score": item["sentiment_score"], "url": item["url"],
     "source": item["source"], "severity": item["severity"]}
    for item in items if item["severity"] in ("critical", "important")
]
```

### B14. 判断是否有结果

如果 total_count == 0 → 输出「本周期未发现新增舆情，不生成报告」→ 结束
如果 total_count > 0 → 继续

### B15. 生成 HTML 报告

将 analysis JSON 保存到 `~/.qwenworkcn/workspace/<chatId>/outputs/sentiment-analysis.json`，然后执行：

```bash
bash SKILL_DIR/scripts/generate_report.sh ~/.qwenworkcn/workspace/<chatId>/outputs/sentiment-analysis.json ~/.qwenworkcn/workspace/<chatId>/outputs/
```

生成后用 `present_files` 工具把 HTML 报告交付给用户（不要用 `open` 命令）

### B16. 【自检】检查报告文件

**⚠️ 重要：报告生成后必须执行此自检步骤，确保 HTML 文件正常生成**

```
1. 检查报告文件:
   - 文件存在 AND 文件大小 >= 1KB → 报告正常，继续
   - 文件不存在 OR 文件大小 < 1KB → 报告异常，执行排查

2. 排查流程（按优先级）:
   a. 检查 generate_report.sh 退出码和 stderr:
      - 退出码 != 0 → 脚本执行错误，检查 stderr 具体报错

   b. 读取 ~/.qwenworkcn/workspace/<chatId>/outputs/sentiment-analysis.json 逐项排查:
      - items 数组是否为空但 total_count > 0
        → 情感分析步骤(B11)可能丢失数据，重新执行 B10~B12
      - sentiment_distribution 是否缺失
        → 应包含 positive/neutral/negative 三个键
      - sentiment_distribution 键名是否错误
        → 常见错误：positive 写成 pos、negative 写成 neg
      - top_keywords 中是否缺少 word/count 键
        → 每个关键词对象必须包含 word 和 count 字段
      - alerts 中是否包含非法 severity 值
        → 仅允许 critical/important/normal
      - JSON 是否合法
        → 中文引号、未转义字符、多余逗号

   c. 常见 analysis JSON 结构错误速查:
      ┌──────────────────────┬──────────────────────┬──────────────────────┐
      │ 症状                 │ 可能原因             │ 修正方式             │
      ├──────────────────────┼──────────────────────┼──────────────────────┤
      │ 报告文件为空         │ items=[]但total>0    │ 重新执行情感分析     │
      │ 情感分布显示0%       │ sentiment_distribution│ 键名必须为positive/  │
      │                      │ 键名错误             │ neutral/negative     │
      │ 关键词区域空白       │ top_keywords缺少     │ 每项必须有word+count │
      │                      │ word/count键         │                      │
      │ 预警区域显示异常     │ severity值不在枚举中 │ 仅允许critical/      │
      │                      │                      │ important/normal     │
      │ 脚本报JSONDecodeError│ JSON不合法           │ 检查引号、转义、逗号 │
      └──────────────────────┴──────────────────────┴──────────────────────┘

3. 修正 analysis JSON 后重新执行 generate_report.sh（最多重试 2 次）

4. 重试仍失败 → 直接输出 analysis JSON 文本摘要作为替代报告:
   「⚠️ HTML 报告生成失败，以下是文本格式摘要:
   学校: {school_name}
   舆情总数: {total_count}
   正面: {positive} | 中性: {neutral} | 负面: {negative}
   预警: {alerts 摘要}
   详细数据已保留在: ~/.qwenworkcn/workspace/<chatId>/outputs/sentiment-analysis.json」
```

### B17. 输出摘要通知

按 references/output-templates.md 中的通知模板格式输出

### B18. 如有 critical 级别预警

额外输出预警通知，按 references/output-templates.md 中的预警模板格式

## 流程C：查看报告（详细）

```
读取最近的分析 JSON → 调用 generate_report.sh 生成 HTML → 用 present_files 工具交付给用户
bash generate_report.sh ~/.qwenworkcn/workspace/<chatId>/outputs/sentiment-analysis.json ~/.qwenworkcn/workspace/<chatId>/outputs/
# 然后用 present_files 工具把生成的 HTML 报告交付给用户（不要用 open 命令）
```

## 流程D：管理定时任务引导（详细）

当用户意图为修改、暂停、恢复、删除、查看监控任务时：

```
输出引导文案：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 定时任务管理指引
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
学校舆情监控使用 QoderWork 定时任务功能执行。

如需管理您的监控任务，请在 QoderWork 中管理定时任务：

您可以：
• 查看所有监控任务列表
• 修改任务执行频率
• 暂停/恢复任务执行
• 删除不需要的监控任务
• 查看任务执行历史

当前通过本对话创建的任务将在 QoderWork 定时任务中显示为：
「学校舆情监控 - {学校名称}」
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
