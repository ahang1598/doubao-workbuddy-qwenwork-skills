---
name: bilibili-summary
description: 当用户发送B站(bilibili.com)视频链接并要求"总结视频内容"、"帮我总结"、"总结一下这个视频/课程"时触发。生成美观的HTML学习报告+MD归档文件。自动识别单集(详细灵活分析)和多P系列(分组折叠+阶段总结)，支持上百集课程快速输出结构化报告。
install_source: official
install_method: download
skill_id: official_AySbIouN
enabled_at: 1791893756195
version: 1.0.0
name_zh: 视频速读
---

# B站视频内容总结

## 触发条件

当用户消息中包含以下全部要素时触发：
1. 一个 B站视频链接（`bilibili.com/video/BV...` 或 `b23.tv/...`）
2. 表达"总结视频内容"的意图（如：帮我总结、总结一下、概括内容、提炼要点、生成报告）

## 执行流程总览

```
解析BV号 → 调用API获取信息 → 判断单集/多P → 生成内容 → 输出HTML+MD
```

---

## 第1步：解析B站链接

从用户提供的链接中提取 BV 号（10位，以 `BV` 开头）。

常见格式：
- `https://www.bilibili.com/video/BV1GJ411x7h7`
- `https://www.bilibili.com/video/BV1GJ411x7h7?p=3`
- `https://b23.tv/xxxxx`（短链接需先 curl -L 获取重定向 URL）

如果是短链接（`b23.tv`），先用 curl 跟随重定向：
```bash
curl -sI -L "https://b23.tv/xxxxx" | grep -i "^location:" | tail -1
```

---

## 第2步：调用B站API获取视频信息

**每次请求必须携带以下请求头**：
- `Referer: https://www.bilibili.com`
- `User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36`

### 2.1 获取视频基本信息

```bash
curl -s -H "Referer: https://www.bilibili.com" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  "https://api.bilibili.com/x/web-interface/view?bvid={BV号}"
```

提取字段：
- `data.title` — 视频总标题
- `data.owner.name` — UP主名称
- `data.owner.mid` — UP主ID
- `data.desc` — 视频简介
- `data.pic` — 封面图URL
- `data.duration` — 总时长（秒）
- `data.stat.view` — 播放量
- `data.stat.danmaku` — 弹幕数
- `data.pubdate` — 发布时间（Unix时间戳）

### 2.2 获取分集列表

```bash
curl -s -H "Referer: https://www.bilibili.com" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  "https://api.bilibili.com/x/player/pagelist?bvid={BV号}"
```

提取字段：
- `data[i].part` — 分集标题
- `data[i].duration` — 分集时长（秒）
- `data[i].page` — 分集序号（从1开始）

### 2.3 判断视频模式

- `分集数 == 1` → **单集模式**：详细分析
- `分集数 >= 2` → **多P模式**：分组折叠+阶段总结

### 2.4 API失败回退

如果 API 返回 `code != 0` 或无数据，尝试：
1. 用 `https://api.bilibili.com/x/web-interface/view/detail?bvid={BV号}` 作为备选
2. 使用 `WebFetch` 工具直接抓取B站视频页面，从 HTML 的 `window.__INITIAL_STATE__` 中提取数据
3. 至少需要获取：标题、UP主、分集标题列表

---

## 第3步：内容生成策略

### 3.1 多P模式（2集及以上）

#### 分组策略

根据分集标题的语义相似性和顺序，将课程分为 5-15 个阶段组：

- **分组依据**：标题中的日期标记（Day01/Day02...）、主题关键词（注意力机制/Transformer...）、知识点依赖关系
- **每组规模**：5-20集为一组，逻辑紧密的集数放在一起
- **每组命名**：提炼该组的主题名称，格式如"第X阶段：{主题名}（P{N}-P{M}）"
- **阶段概述**：每个组开头写 2-4 句话的阶段小结，说明该阶段的学习目标和核心收获

#### 智能摘要规则（50集以上触发）

当课程超过 50 集时，对于标题高度重复的集数（如同一个知识点的多个子节），可在表格中合并为一行并标注"含N个子节"，但知识图谱和阶段概述仍需覆盖这些内容。

#### 表格格式

分集表格增加"阶段"分组标识，每组前有阶段标题行：

```html
<tr class="stage-header"><td colspan="3">第X阶段：{阶段名} — {阶段概述一句话}</td></tr>
```

### 3.2 单集模式（1集）

当视频只有 1 集时，切换到详细分析模式。根据视频标题和描述推断视频类型，灵活决定分析结构：

- **教程/课程类**：知识点拆解、学习路径、关键概念速查表
- **演讲/分享类**：核心观点、论证逻辑链、金句摘录
- **评测/演示类**：评测维度、对比表格、优缺点总结
- **Vlog/记录类**：时间线梳理、关键场景、主题提炼

单集报告结构至少包含：
1. 视频概要
2. 核心内容深度拆解（根据类型灵活组织）
3. 知识图谱（思维导图式，中心节点+放射状子节点）
4. 关键观点/结论
5. 延伸阅读建议

---

## 第4步：生成HTML报告

### 文件路径

```
~/.qwenworkcn/workspace/<当前chatId>/outputs/B站视频总结-{BV号}.html
```

### HTML完整模板

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>B站视频总结：【{视频总标题}】</title>
    <style>
        :root {
            --primary: #0078d4;
            --primary-light: #00a1d6;
            --bg-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --card-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
            --blue-gradient: linear-gradient(135deg, #0078d4 0%, #00a1d6 100%);
            --green-gradient: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            --purple-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --orange-gradient: linear-gradient(135deg, #f2994a 0%, #f2c94c 100%);
            --red-gradient: linear-gradient(135deg, #e74c3c 0%, #f39c12 100%);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
            line-height: 1.8; color: #333;
            background: var(--bg-gradient);
            min-height: 100vh; padding: 20px;
        }
        .container {
            max-width: 960px; margin: 0 auto; background: #fff;
            border-radius: 16px; box-shadow: var(--card-shadow); overflow: hidden;
        }
        .header {
            background: var(--blue-gradient);
            color: #fff; padding: 48px 40px; text-align: center;
            position: relative; overflow: hidden;
        }
        .header::before {
            content: ''; position: absolute; top: -50%; left: -50%;
            width: 200%; height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 60%);
            animation: headerShine 8s ease-in-out infinite;
        }
        @keyframes headerShine {
            0%, 100% { transform: translate(0, 0); }
            50% { transform: translate(10%, 10%); }
        }
        .header h1 {
            font-size: 26px; margin-bottom: 8px; font-weight: 700;
            position: relative; z-index: 1; line-height: 1.4;
        }
        .header .subtitle {
            font-size: 14px; opacity: 0.85; position: relative; z-index: 1; margin-top: 12px;
        }
        .video-link {
            display: inline-block; background: rgba(255,255,255,0.18);
            color: #fff; padding: 10px 24px; border-radius: 25px;
            text-decoration: none; margin-top: 16px; font-size: 14px;
            transition: all 0.3s ease; position: relative; z-index: 1;
            border: 1px solid rgba(255,255,255,0.25);
        }
        .video-link:hover {
            background: rgba(255,255,255,0.3); transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        .content { padding: 40px 48px; }
        .meta-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px; margin-bottom: 32px; padding: 24px;
            background: #f8f9fa; border-radius: 12px; border: 1px solid #e9ecef;
        }
        .meta-item { display: flex; align-items: baseline; gap: 6px; }
        .meta-label { font-weight: 600; color: #6c757d; white-space: nowrap; font-size: 14px; }
        .meta-value { color: #212529; font-size: 14px; }
        .meta-value a { color: var(--primary); text-decoration: none; }
        .meta-value a:hover { text-decoration: underline; }

        h2 {
            color: var(--primary); font-size: 22px; margin: 36px 0 16px 0;
            padding-bottom: 10px; border-bottom: 3px solid var(--primary);
            display: flex; align-items: center; gap: 8px;
        }
        h3 {
            color: var(--primary-light); font-size: 18px; margin: 28px 0 12px 0;
        }
        p { margin-bottom: 14px; text-align: justify; }

        /* 表格样式 */
        .table-wrapper { overflow-x: auto; margin: 20px 0; border-radius: 10px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
        table { width: 100%; border-collapse: collapse; background: #fff; }
        th {
            background: var(--blue-gradient); color: #fff;
            padding: 14px 16px; text-align: left; font-weight: 600; font-size: 14px;
        }
        td { padding: 10px 16px; border-bottom: 1px solid #e9ecef; font-size: 14px; }
        tr:nth-child(even) { background: #f8f9fa; }
        tr:hover { background: #e3f2fd; transition: background 0.2s ease; }

        /* 阶段分组样式（多P模式） */
        .stage-group { margin: 16px 0; border: 1px solid #e0e0e0; border-radius: 10px; overflow: hidden; }
        .stage-header {
            background: linear-gradient(135deg, #f0f4ff 0%, #e8f0fe 100%);
            padding: 14px 20px; cursor: pointer; font-weight: 700; color: var(--primary);
            display: flex; align-items: center; gap: 10px; user-select: none;
            border-bottom: 1px solid #d0d9e8; font-size: 15px;
        }
        .stage-header:hover { background: linear-gradient(135deg, #e8f0fe 0%, #dce8fc 100%); }
        .stage-header .arrow { transition: transform 0.3s ease; font-size: 12px; }
        .stage-header .badge {
            background: var(--blue-gradient); color: #fff; padding: 2px 10px;
            border-radius: 12px; font-size: 12px; font-weight: 500;
        }
        .stage-content { }
        .stage-summary {
            padding: 12px 20px; background: #fafbfc; color: #555;
            font-size: 14px; border-bottom: 1px solid #eee; line-height: 1.7;
        }
        .stage-content table { margin: 0; box-shadow: none; border-radius: 0; }
        .stage-content table th { background: #6c757d; }

        /* 折叠展开（使用details/summary原生元素） */
        details.stage-group { margin: 16px 0; border: 1px solid #e0e0e0; border-radius: 10px; overflow: hidden; }
        details.stage-group > summary {
            background: linear-gradient(135deg, #f0f4ff 0%, #e8f0fe 100%);
            padding: 14px 20px; cursor: pointer; font-weight: 700; color: var(--primary);
            display: flex; align-items: center; gap: 10px; user-select: none;
            border-bottom: 1px solid #d0d9e8; font-size: 15px; list-style: none;
        }
        details.stage-group > summary::-webkit-details-marker { display: none; }
        details.stage-group > summary:hover { background: linear-gradient(135deg, #e8f0fe 0%, #dce8fc 100%); }
        details.stage-group > summary .arrow { transition: transform 0.3s ease; font-size: 12px; display: inline-block; }
        details.stage-group[open] > summary .arrow { transform: rotate(90deg); }
        details.stage-group[open] > summary { border-bottom: 2px solid var(--primary); }
        details.stage-group > .stage-summary {
            padding: 12px 20px; background: #fafbfc; color: #555;
            font-size: 14px; border-bottom: 1px solid #eee; line-height: 1.7;
        }
        details.stage-group > table { width: 100%; margin: 0; box-shadow: none; border-radius: 0; }
        details.stage-group > table th { background: #6c757d; font-size: 13px; padding: 10px 14px; }

        /* 全部展开/折叠按钮 */
        .toggle-all-bar {
            display: flex; gap: 10px; margin-bottom: 16px;
        }
        .toggle-all-btn {
            padding: 6px 16px; border: 1px solid var(--primary); border-radius: 20px;
            background: #fff; color: var(--primary); cursor: pointer;
            font-size: 13px; transition: all 0.2s ease;
        }
        .toggle-all-btn:hover { background: var(--primary); color: #fff; }

        /* 高亮提示框 */
        .highlight-box {
            background: linear-gradient(135deg, #fff9e6 0%, #fff3cd 100%);
            border-left: 4px solid #ffc107; padding: 24px;
            margin: 24px 0; border-radius: 10px;
        }
        .highlight-box h3 { margin-top: 0; color: #856404; }
        .highlight-box ul { margin-bottom: 0; }

        /* 信息卡片 */
        .info-cards {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 16px; margin: 20px 0;
        }
        .info-card {
            background: #fff; border: 1px solid #e9ecef; border-radius: 10px;
            padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.05);
            transition: box-shadow 0.2s ease;
        }
        .info-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.1); }
        .info-card .card-icon { font-size: 24px; margin-bottom: 8px; }
        .info-card h4 { font-size: 15px; color: var(--primary); margin-bottom: 6px; }
        .info-card p { font-size: 13px; color: #666; margin-bottom: 0; }

        ul, ol { margin: 14px 0; padding-left: 28px; }
        li { margin-bottom: 8px; }

        .kg-container {
            overflow-x: auto; margin: 20px 0; background: #fafbfc;
            border-radius: 12px; padding: 24px; border: 1px solid #e9ecef;
        }

        /* 进度条 */
        .progress-section { margin: 20px 0; }
        .progress-bar-outer {
            height: 8px; background: #e9ecef; border-radius: 4px; overflow: hidden;
        }
        .progress-bar-inner {
            height: 100%; background: var(--blue-gradient); border-radius: 4px;
            transition: width 1s ease;
        }

        .footer {
            text-align: center; padding: 24px; color: #999;
            font-size: 13px; border-top: 1px solid #e9ecef; background: #fafbfc;
        }

        /* 返回顶部 */
        .back-to-top {
            position: fixed; bottom: 30px; right: 30px; width: 44px; height: 44px;
            background: var(--blue-gradient); color: #fff; border: none;
            border-radius: 50%; cursor: pointer; font-size: 20px;
            box-shadow: 0 4px 12px rgba(0,120,212,0.3);
            transition: all 0.3s ease; opacity: 0; pointer-events: none; z-index: 999;
        }
        .back-to-top.visible { opacity: 1; pointer-events: auto; }
        .back-to-top:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,120,212,0.4); }

        /* 响应式 */
        @media (max-width: 768px) {
            .header { padding: 32px 20px; }
            .header h1 { font-size: 20px; }
            .content { padding: 24px 20px; }
            .meta-info { grid-template-columns: 1fr; }
            table { font-size: 13px; }
            th, td { padding: 8px 10px; }
        }

        /* 打印样式 */
        @media print {
            body { background: #fff; padding: 0; }
            .container { box-shadow: none; border-radius: 0; }
            .back-to-top { display: none; }
            details.stage-group > .stage-content { display: block !important; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>【{视频总标题}】</h1>
            <div class="subtitle">{UP主名称} · {全X集 / 单集 · 时长XX:XX} · {播放量}</div>
            <a href="{原始B站链接}" target="_blank" class="video-link">📺 在 B 站观看视频</a>
        </div>

        <div class="content">
            <div class="meta-info">
                <div class="meta-item">
                    <span class="meta-label">UP 主：</span>
                    <span class="meta-value"><a href="https://space.bilibili.com/{mid}" target="_blank">{UP主名称}</a></span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">课程规模：</span>
                    <span class="meta-value">{全X集系列教程，总时长约XX小时 / 单集视频，时长XX:XX}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">适合人群：</span>
                    <span class="meta-value">{根据标题和描述推断的适合人群}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">发布日期：</span>
                    <span class="meta-value">{YYYY-MM-DD}</span>
                </div>
            </div>

            <h2>📋 视频概要</h2>
            <p>{视频简介（来自API）+ AI生成的概括性描述（2-3段），覆盖课程目标、内容范围和教学风格}</p>

            <h2>🎯 核心内容</h2>

            <!-- 多P模式：阶段分组 -->
            <div class="progress-section">
                <div style="display:flex;justify-content:space-between;margin-bottom:6px;font-size:13px;color:#666">
                    <span>课程进度概览</span><span>{X}集 · {Y}个阶段</span>
                </div>
                <div class="progress-bar-outer">
                    <div class="progress-bar-inner" style="width:100%"></div>
                </div>
            </div>

            <div class="toggle-all-bar">
                <button class="toggle-all-btn" onclick="document.querySelectorAll('details.stage-group').forEach(d=>d.open=true)">展开全部</button>
                <button class="toggle-all-btn" onclick="document.querySelectorAll('details.stage-group').forEach(d=>d.open=false)">折叠全部</button>
            </div>

            <!-- 阶段组1（示例） -->
            <details class="stage-group" open>
                <summary>
                    <span class="arrow">▶</span>
                    第1阶段：{阶段名称}（P1-P{N}）
                    <span class="badge">{N}集</span>
                </summary>
                <div class="stage-summary">
                    <strong>📌 阶段概述：</strong>{2-4句话的阶段学习目标和核心收获}
                </div>
                <table>
                    <thead>
                        <tr><th>集数</th><th>分集标题</th><th>核心内容</th></tr>
                    </thead>
                    <tbody>
                        <tr><td>P1</td><td>{原始标题}</td><td>{一句话核心内容}</td></tr>
                        <!-- ... -->
                    </tbody>
                </table>
            </details>

            <!-- 重复以上结构，每个阶段一个 details.stage-group -->

            <!-- 单集模式：知识拆解 -->
            <!-- 对于单集，不使用折叠分组，而是深度拆解知识结构 -->

            <h3>知识图谱</h3>
            <div class="kg-container">
                {内嵌SVG知识图谱，见下方「知识图谱构建规则」}
            </div>

            <h3>教学特点</h3>
            <div class="info-cards">
                <div class="info-card">
                    <div class="card-icon">🔬</div>
                    <h4>理论与实践并重</h4>
                    <p>{具体描述}</p>
                </div>
                <!-- 3-5张卡片 -->
            </div>

            <h3>知识点覆盖</h3>
            <ul>
                {按类别列出，每个类别一行，冒号后列出子知识点}
            </ul>

            <h2>💡 关键结论</h2>
            <ol>
                {3-5条核心结论，每条1-2句话}
            </ol>

            <div class="highlight-box">
                <h3>📚 学习建议</h3>
                <ul>
                    {5条具体可操作的学习建议，基于课程内容定制}
                </ul>
            </div>

            <h2>🔗 资源信息</h2>
            <ul>
                <li><strong>B站链接</strong>：<a href="{链接}" target="_blank">{链接}</a></li>
                <li><strong>UP主主页</strong>：<a href="https://space.bilibili.com/{mid}" target="_blank">https://space.bilibili.com/{mid}</a></li>
                {从视频描述中提取的配套资源链接（GitHub/网盘/公众号等）}
            </ul>
        </div>

        <div class="footer">
            <p>总结生成时间：{YYYY-MM-DD} | 由 QoderWork 自动生成 | 视频数据来源：B站API</p>
        </div>
    </div>

    <button class="back-to-top" onclick="window.scrollTo({top:0,behavior:'smooth'})" title="返回顶部">↑</button>
    <script>
        // 返回顶部按钮显隐
        const btn = document.querySelector('.back-to-top');
        window.addEventListener('scroll', () => {
            btn.classList.toggle('visible', window.scrollY > 400);
        });

        // 默认展开前2个阶段，其余折叠
        document.querySelectorAll('details.stage-group').forEach((d, i) => {
            if (i >= 2) d.open = false;
        });
    </script>
</body>
</html>
```

### 生成HTML时的关键要求

1. **多P模式**：每个阶段生成一个 `<details class="stage-group">`，默认前2个阶段展开
2. **单集模式**：不生成阶段折叠，直接在"核心内容"区域深度拆解
3. **知识图谱SVG**：必须内嵌，不能省略
4. **教学特点卡片**：使用 `.info-cards` 网格布局，3-5张卡片
5. **所有占位符** `{...}` 必须替换为实际内容
6. **日期使用当天实际日期**（YYYY-MM-DD格式）

---

## 第5步：生成MD归档文件

### 文件路径

```
~/.qwenworkcn/workspace/<当前chatId>/outputs/B站视频总结-{BV号}.md
```

### MD模板

```markdown
---
bv: {BV号}
title: "{视频总标题}"
up: "{UP主名称}"
up_mid: "{mid}"
episodes: {总集数}
total_duration_seconds: {总时长秒数}
total_duration_formatted: "{X小时Y分钟}"
views: {播放量}
published: "{YYYY-MM-DD}"
generated: "{YYYY-MM-DD}"
url: "{原始链接}"
mode: "{single / multi}"
stages: {阶段数（多P模式）}
---

# {视频总标题}

> **UP主**：[{UP主名称}](https://space.bilibili.com/{mid})
> **课程规模**：{全X集 / 单集，XX:XX}
> **播放量**：{播放量}
> **B站链接**：[{原始链接}]({原始链接})
> **总结生成时间**：{YYYY-MM-DD}

---

## 视频概要

{视频简介 + AI概括描述}

---

## 核心内容

### 课程结构

{多P模式：列出各阶段名称及集数范围}
{单集模式：列出核心知识板块}

{多P模式的分集表格（Markdown表格，每集一行，按阶段分组）}

| 集数 | 分集标题 | 核心内容 |
|------|----------|----------|
| P1   | {标题}   | {一句话} |

---

## 知识体系

{文字版知识图谱：使用缩进列表表示层级关系}
- 根主题
  - 子主题1
    - 知识点a
    - 知识点b
  - 子主题2
    - ...

---

## 教学特点

{列表形式}

---

## 知识点覆盖

{按类别分组列表}

---

## 关键结论

{编号列表}

---

## 学习建议

{编号列表}

---

## 资源信息

- **B站链接**：{链接}
- **UP主主页**：https://space.bilibili.com/{mid}
- **配套资源**：{从描述中提取}

---

*本报告由 QoderWork 自动生成，数据来源为 B站公开 API。*
```

### MD生成要求

1. **YAML frontmatter** 必须包含所有元数据字段
2. **Markdown表格**：多P模式每集一行，与HTML一致
3. **知识体系**：用缩进列表表示层级（代替SVG知识图谱）
4. **MD文件是完整归档**：包含HTML报告的所有文字内容，不因纯文本而省略

---

## 知识图谱构建规则

知识图谱是报告的固定板块，必须使用内嵌 SVG 绘制，**不得省略**。

### 颜色体系

| 颜色 | 渐变ID | 使用场景 |
|------|--------|----------|
| 蓝色 `bg-blue` | `#0078d4` → `#00a1d6` | 基础概念/入门知识 |
| 绿色 `bg-green` | `#11998e` → `#38ef7d` | 核心方法/工具 |
| 紫色 `bg-purple` | `#667eea` → `#764ba2` | 进阶理论/数学基础 |
| 橙色 `bg-orange` | `#f2994a` → `#f2c94c` | 高级技术/前沿方法 |
| 红色 `bg-red` | `#e74c3c` → `#f39c12` | 综合应用/实战 |

### 多P模式知识图谱

层级式纵向布局，从上到下 4-6 层：
- **根节点**（第一层）：课程主题，居中，宽 260-320px
- **分类层**（第二层）：3-5 个知识大类，水平排列
- **细化层**（第三/四层）：每个大类下的子主题
- **应用层**（最底层）：实战/综合应用

要求：
- `viewBox="0 0 840 {动态高度}"`，高度根据层数和节点数计算（推荐公式：层数 × 120 + 80）
- 使用 `<rect rx="8" filter="url(#shadow)">` 绘制节点
- 节点文本：主标题 13-15px 粗体白色，副标题 9-10px 半透明白色
- 连接线用 `<line>` 或 `<path>`，stroke-width=2，带箭头标记
- 右上角绘制图例（5个色块+标签）
- 节点内的子概念文字必须来自课程真实涉及的知识点

### 单集模式知识图谱

放射状思维导图式布局：
- 中心节点大号（180×60px），为视频核心主题
- 周围 4-8 个子节点环绕排列，用弧线或直线连接中心
- 每个子节点列出 2-3 个细分知识点（小字）
- 子节点颜色按知识点类别分配

---

## 内容质量要求

1. **如实反映**：基于真实 API 获取的标题和描述生成，不凭空编造课程中没有的内容
2. **阶段概述有洞察**：不只说"本阶段讲XX"，而要说明该阶段在整个学习路径中的位置和意义
3. **学习建议具体可操作**：如"先跟着P15的代码敲一遍再回看P13的理论讲解"而非"多练习"
4. **知识图谱贴合内容**：节点内容和连接关系必须基于真实课程知识点，不照搬模板
5. **语言专业但亲和**：中文撰写，避免翻译腔，术语准确但不堆砌

---

## 注意事项

- 优先用 curl 调用 API，失败时用 WebFetch 从B站页面提取 `window.__INITIAL_STATE__`
- 创建输出目录：`mkdir -p ~/.qwenworkcn/workspace/<当前chatId>/outputs/`
- 生成 HTML 后用 `present_files` 工具将文件呈现给用户（不要用 `open` 命令，QoderWork 桌面端内 `open` 不可用）
- HTML 文件编码必须是 UTF-8
- 如果视频介绍中包含微信公众号、GitHub、网盘等资源，务必在"资源信息"中列出
- 单集模式不生成折叠分组和进度条
- 多P模式 50 集以上：标题高度重复的连续集数可合并表格行（标注"含N个子节"）