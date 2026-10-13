#!/usr/bin/env bash
#
# 学校舆情监控 - HTML 报告生成器
# 用法: bash generate_report.sh <analysis_json> [output_dir]
#
# 读取分析结果 JSON，生成可视化 HTML 舆情报告
#

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "用法: bash generate_report.sh <analysis_json> [output_dir]"
    exit 1
fi

export ANALYSIS_JSON="$1"
export OUTPUT_DIR="${2:-$HOME/.qwenworkcn/workspace/sentiment-monitor}"

if [ ! -f "$ANALYSIS_JSON" ]; then
    echo "ERROR: 分析文件不存在: $ANALYSIS_JSON" >&2
    exit 1
fi

# 生成输出文件名
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
export OUTPUT_FILE="${OUTPUT_DIR}/sentiment_report_${TIMESTAMP}.html"

# 使用 Python 读取 JSON 并生成 HTML
python3 << 'PYEOF'
import json
import sys
import os
from datetime import datetime

analysis_json = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ANALYSIS_JSON", "")
output_file = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("OUTPUT_FILE", os.path.expanduser("~/.qwenworkcn/workspace/sentiment-monitor/sentiment_report.html"))

with open(os.environ["ANALYSIS_JSON"], "r", encoding="utf-8") as f:
    data = json.load(f)

school_name = data.get("school_name", "未知学校")
search_time = data.get("search_time", "")
period = data.get("period", "")
total_count = data.get("total_count", 0)
dist = data.get("sentiment_distribution", {})
items = data.get("items", [])
keywords = data.get("top_keywords", [])
alerts = data.get("alerts", [])
platform_dist = data.get("platform_distribution", {})

# 【强制修正】确保 total_count 与实际展示的 items 数量一致，避免用户质疑数据准确性
actual_items_len = len(items)
if total_count != actual_items_len:
    print(f"WARNING: JSON 中 total_count ({total_count}) 与 items 数组长度 ({actual_items_len}) 不一致，已自动修正为 {actual_items_len}")
    total_count = actual_items_len
    # 同步更新 data 字典，防止后续逻辑使用旧值
    data["total_count"] = total_count

pos = dist.get("positive", 0)
neu = dist.get("neutral", 0)
neg = dist.get("negative", 0)
total_sentiment = pos + neu + neg or 1
pos_pct = round(pos / total_sentiment * 100)
neu_pct = round(neu / total_sentiment * 100)
neg_pct = 100 - pos_pct - neu_pct

# 按 severity 排序
severity_order = {"critical": 0, "important": 1, "normal": 2}
sorted_items = sorted(items, key=lambda x: severity_order.get(x.get("severity", "normal"), 2))

# 生成舆情条目 HTML
items_html = ""
for item in sorted_items:
    sentiment = item.get("sentiment", "neutral")
    sentiment_label = {"positive": "正面", "negative": "负面", "neutral": "中性"}.get(sentiment, "中性")
    sentiment_class = sentiment
    severity = item.get("severity", "normal")
    severity_label = {"critical": "紧急预警", "important": "重点关注", "normal": "一般关注"}.get(severity, "一般")
    severity_class = severity
    score = item.get("sentiment_score", 50)
    topic_code = item.get("topic", "T99")
    source = item.get("source", "未知")
    url = item.get("url", "#")
    title = item.get("title", "无标题")
    summary = item.get("summary", "")
    pub_time = item.get("publish_time", "")
    kws = ", ".join(item.get("keywords", []))

    items_html += f'''
    <div class="item-card {sentiment_class} severity-{severity_class}">
      <div class="item-header">
        <span class="sentiment-badge {sentiment_class}">{sentiment_label} {score}分</span>
        <span class="severity-badge {severity_class}">{severity_label}</span>
        <span class="topic-badge">{topic_code}</span>
        <span class="source-badge">{source}</span>
        <span class="time-text">{pub_time}</span>
      </div>
      <h3 class="item-title"><a href="{url}" target="_blank" rel="noopener">{title}</a></h3>
      <p class="item-summary">{summary}</p>
      <div class="item-keywords">关键词: {kws}</div>
    </div>'''

# 平台分布 HTML
platform_html = ""
if platform_dist:
    total_p = sum(platform_dist.values()) or 1
    for pname, pcount in sorted(platform_dist.items(), key=lambda x: -x[1]):
        pct = round(pcount / total_p * 100)
        platform_html += f'''
        <div class="platform-row">
          <span class="platform-name">{pname}</span>
          <div class="platform-bar-bg"><div class="platform-bar" style="width:{pct}%"></div></div>
          <span class="platform-count">{pcount}条 ({pct}%)</span>
        </div>'''

# 关键词 HTML
keywords_html = ""
if keywords:
    # 兼容处理：支持 "word" 或 "keyword" 作为键名
    max_count = max(k.get("count", k.get("word_count", 1)) for k in keywords) or 1
    for kw in keywords[:20]:
        word = kw.get("word", kw.get("keyword", ""))
        count = kw.get("count", kw.get("word_count", 0))
        s = kw.get("sentiment", kw.get("word_sentiment", "neutral"))
        size = max(14, min(36, int(14 + 22 * count / max_count)))
        color_class = s
        keywords_html += f'<span class="keyword-tag {color_class}" style="font-size:{size}px">{word}({count})</span> '

# 预警条目
alerts_html = ""
if alerts:
    for a in alerts:
        a_title = a.get("title", "")
        a_summary = a.get("summary", "")
        a_score = a.get("sentiment_score", 0)
        a_url = a.get("url", "#")
        a_source = a.get("source", "")
        a_severity = a.get("severity", "important")
        s_label = {"critical": "紧急预警", "important": "重点关注"}.get(a_severity, "关注")
        alerts_html += f'''
        <div class="alert-card {a_severity}">
          <div class="alert-badge">{s_label}</div>
          <h4><a href="{a_url}" target="_blank" rel="noopener">{a_title}</a></h4>
          <p>{a_summary}</p>
          <span class="alert-meta">{a_source} | 负面评分 {a_score}</span>
        </div>'''
else:
    alerts_html = '<div class="no-alert">本周期无需预警事项</div>'

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>舆情监控报告 - {school_name}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; background:#f0f2f5; color:#1a1a2e; line-height:1.6; }}
  .container {{ max-width:960px; margin:0 auto; padding:24px 16px; }}
  .header {{ background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460); color:#fff; border-radius:16px; padding:32px; margin-bottom:24px; }}
  .header h1 {{ font-size:24px; margin-bottom:8px; }}
  .header .period {{ opacity:0.8; font-size:14px; }}
  .header .gen-time {{ opacity:0.6; font-size:12px; margin-top:4px; }}

  .stats-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:16px; margin-bottom:24px; }}
  .stat-card {{ background:#fff; border-radius:12px; padding:20px; text-align:center; box-shadow:0 2px 8px rgba(0,0,0,0.06); }}
  .stat-card .stat-value {{ font-size:32px; font-weight:700; }}
  .stat-card .stat-label {{ font-size:13px; color:#666; margin-top:4px; }}
  .stat-card.positive .stat-value {{ color:#10b981; }}
  .stat-card.neutral .stat-value {{ color:#6b7280; }}
  .stat-card.negative .stat-value {{ color:#ef4444; }}
  .stat-card.total .stat-value {{ color:#3b82f6; }}

  .section {{ background:#fff; border-radius:12px; padding:24px; margin-bottom:24px; box-shadow:0 2px 8px rgba(0,0,0,0.06); }}
  .section h2 {{ font-size:18px; margin-bottom:16px; padding-bottom:8px; border-bottom:2px solid #e5e7eb; }}

  .sentiment-bar {{ display:flex; height:32px; border-radius:8px; overflow:hidden; margin-bottom:12px; }}
  .sentiment-bar .seg-positive {{ background:#10b981; }}
  .sentiment-bar .seg-neutral {{ background:#9ca3af; }}
  .sentiment-bar .seg-negative {{ background:#ef4444; }}
  .sentiment-legend {{ display:flex; gap:20px; font-size:13px; }}
  .sentiment-legend span::before {{ content:""; display:inline-block; width:12px; height:12px; border-radius:3px; margin-right:4px; vertical-align:middle; }}
  .legend-pos::before {{ background:#10b981; }}
  .legend-neu::before {{ background:#9ca3af; }}
  .legend-neg::before {{ background:#ef4444; }}

  .item-card {{ border:1px solid #e5e7eb; border-radius:10px; padding:16px; margin-bottom:12px; transition:box-shadow .2s; }}
  .item-card:hover {{ box-shadow:0 4px 12px rgba(0,0,0,0.08); }}
  .item-card.severity-critical {{ border-left:4px solid #ef4444; }}
  .item-card.severity-important {{ border-left:4px solid #f59e0b; }}
  .item-header {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin-bottom:8px; }}
  .sentiment-badge, .severity-badge, .topic-badge, .source-badge {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:500; }}
  .sentiment-badge.positive {{ background:#d1fae5; color:#065f46; }}
  .sentiment-badge.negative {{ background:#fee2e2; color:#991b1b; }}
  .sentiment-badge.neutral {{ background:#f3f4f6; color:#374151; }}
  .severity-badge.critical {{ background:#fef2f2; color:#dc2626; font-weight:700; }}
  .severity-badge.important {{ background:#fffbeb; color:#d97706; }}
  .severity-badge.normal {{ background:#f0fdf4; color:#16a34a; }}
  .topic-badge {{ background:#eff6ff; color:#2563eb; }}
  .source-badge {{ background:#faf5ff; color:#7c3aed; }}
  .time-text {{ font-size:12px; color:#9ca3af; }}
  .item-title {{ font-size:15px; margin-bottom:6px; }}
  .item-title a {{ color:#1a1a2e; text-decoration:none; }}
  .item-title a:hover {{ color:#3b82f6; text-decoration:underline; }}
  .item-summary {{ font-size:13px; color:#4b5563; margin-bottom:6px; }}
  .item-keywords {{ font-size:12px; color:#9ca3af; }}

  .platform-row {{ display:flex; align-items:center; gap:12px; margin-bottom:8px; }}
  .platform-name {{ width:80px; font-size:13px; text-align:right; flex-shrink:0; }}
  .platform-bar-bg {{ flex:1; height:20px; background:#f3f4f6; border-radius:4px; overflow:hidden; }}
  .platform-bar {{ height:100%; background:linear-gradient(90deg,#3b82f6,#6366f1); border-radius:4px; transition:width .3s; }}
  .platform-count {{ font-size:12px; color:#6b7280; width:100px; flex-shrink:0; }}

  .keyword-tag {{ display:inline-block; margin:4px; padding:4px 8px; border-radius:6px; cursor:default; }}
  .keyword-tag.positive {{ background:#d1fae5; color:#065f46; }}
  .keyword-tag.negative {{ background:#fee2e2; color:#991b1b; }}
  .keyword-tag.neutral {{ background:#f3f4f6; color:#374151; }}

  .alert-card {{ border-radius:10px; padding:16px; margin-bottom:12px; }}
  .alert-card.critical {{ background:#fef2f2; border:1px solid #fca5a5; }}
  .alert-card.important {{ background:#fffbeb; border:1px solid #fcd34d; }}
  .alert-badge {{ display:inline-block; padding:2px 10px; border-radius:4px; font-size:12px; font-weight:700; margin-bottom:8px; color:#fff; }}
  .alert-card.critical .alert-badge {{ background:#dc2626; }}
  .alert-card.important .alert-badge {{ background:#d97706; }}
  .alert-card h4 {{ font-size:15px; margin-bottom:4px; }}
  .alert-card h4 a {{ color:inherit; text-decoration:none; }}
  .alert-card h4 a:hover {{ text-decoration:underline; }}
  .alert-card p {{ font-size:13px; color:#4b5563; margin-bottom:6px; }}
  .alert-meta {{ font-size:12px; color:#9ca3af; }}
  .no-alert {{ text-align:center; color:#6b7280; padding:20px; }}

  .footer {{ text-align:center; font-size:12px; color:#9ca3af; margin-top:24px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>学校舆情监控报告 - {school_name}</h1>
    <div class="period">监控时段: {period}</div>
    <div class="gen-time">报告生成时间: {search_time}</div>
  </div>

  <div class="stats-grid">
    <div class="stat-card total">
      <div class="stat-value">{total_count}</div>
      <div class="stat-label">舆情总数</div>
    </div>
    <div class="stat-card positive">
      <div class="stat-value">{pos_pct}%</div>
      <div class="stat-label">正面 ({pos}条)</div>
    </div>
    <div class="stat-card neutral">
      <div class="stat-value">{neu_pct}%</div>
      <div class="stat-label">中性 ({neu}条)</div>
    </div>
    <div class="stat-card negative">
      <div class="stat-value">{neg_pct}%</div>
      <div class="stat-label">负面 ({neg}条)</div>
    </div>
  </div>

  <div class="section">
    <h2>情感分布</h2>
    <div class="sentiment-bar">
      <div class="seg-positive" style="width:{pos_pct}%"></div>
      <div class="seg-neutral" style="width:{neu_pct}%"></div>
      <div class="seg-negative" style="width:{neg_pct}%"></div>
    </div>
    <div class="sentiment-legend">
      <span class="legend-pos">正面 {pos_pct}%</span>
      <span class="legend-neu">中性 {neu_pct}%</span>
      <span class="legend-neg">负面 {neg_pct}%</span>
    </div>
  </div>

  {"<div class='section'><h2>预警事项</h2>" + alerts_html + "</div>" if alerts else ""}

  <div class="section">
    <h2>平台分布</h2>
    {platform_html if platform_html else "<p style='color:#9ca3af;text-align:center'>暂无平台分布数据</p>"}
  </div>

  <div class="section">
    <h2>热门关键词</h2>
    <div style="text-align:center;padding:12px 0;">
      {keywords_html if keywords_html else "<p style='color:#9ca3af'>暂无关键词数据</p>"}
    </div>
  </div>

  <div class="section">
    <h2>舆情详情 ({total_count}条)</h2>
    {items_html if items_html else "<p style='color:#9ca3af;text-align:center'>暂无舆情数据</p>"}
  </div>

  <div class="footer">
    学校舆情监控助手 | 仅采集公开信息，不涉及任何非法数据获取
  </div>
</div>
</body>
</html>'''

with open(os.environ["OUTPUT_FILE"], "w", encoding="utf-8") as f:
    f.write(html)

# 自检：验证生成的 HTML 文件是否正常
output_path = os.environ["OUTPUT_FILE"]
file_size = os.path.getsize(output_path)

if file_size < 1024:
    # 文件过小，可能数据异常，输出诊断信息
    print(f"WARNING: 报告文件过小 ({file_size} bytes)，可能存在数据异常")
    print(f"DIAG: total_count={total_count}, items_len={len(items)}, dist_keys={list(dist.keys())}")
    print(f"DIAG: keywords_len={len(keywords)}, alerts_len={len(alerts)}, platform_dist_keys={list(platform_dist.keys())}")

    # 检查常见问题
    issues = []
    if total_count > 0 and len(items) == 0:
        issues.append("total_count > 0 但 items 数组为空，情感分析步骤可能丢失数据")
    if not dist:
        issues.append("sentiment_distribution 缺失")
    elif not all(k in dist for k in ["positive", "neutral", "negative"]):
        issues.append(f"sentiment_distribution 键名错误，期望 positive/neutral/negative，实际 {list(dist.keys())}")
    if keywords and any(not k.get("word") or not k.get("count") for k in keywords):
        issues.append("top_keywords 中存在缺少 word 或 count 键的条目")
    if alerts and any(a.get("severity") not in ("critical", "important", "normal") for a in alerts):
        issues.append(f"alerts 中存在非法 severity 值，仅允许 critical/important/normal")

    if issues:
        print("DIAG: 发现以下问题:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    else:
        print("DIAG: 未发现明显的 JSON 结构问题，可能是 HTML 渲染异常")
else:
    print(output_path)
PYEOF

# 自检：检查输出文件
if [ ! -f "${OUTPUT_FILE}" ]; then
    echo "ERROR: 报告文件未生成: ${OUTPUT_FILE}" >&2
    exit 1
fi

FILE_SIZE=$(stat -f%z "${OUTPUT_FILE}" 2>/dev/null || stat -c%s "${OUTPUT_FILE}" 2>/dev/null || echo 0)
if [ "$FILE_SIZE" -lt 1024 ]; then
    echo "WARNING: 报告文件异常 (${FILE_SIZE} bytes)，请检查 analysis JSON 数据结构"
fi

echo "报告已生成: ${OUTPUT_FILE}"
