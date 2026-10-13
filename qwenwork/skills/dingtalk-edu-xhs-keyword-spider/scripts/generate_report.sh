#!/usr/bin/env bash
#
# 小红书学校舆情 - HTML 报告生成器
# 用法: bash generate_report.sh <search_json> [output_dir]
#
# 读取搜索结果 JSON（含笔记详情），生成可视化 HTML 舆情报告
#

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "用法: bash generate_report.sh <search_json> [output_dir]"
    exit 1
fi

export SEARCH_JSON="$1"
export OUTPUT_DIR="${2:-${TMPDIR:-/tmp}}"

if [ ! -f "$SEARCH_JSON" ]; then
    echo "ERROR: 搜索结果文件不存在: $SEARCH_JSON" >&2
    exit 1
fi

# 生成输出文件名
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
export OUTPUT_FILE="${OUTPUT_DIR}/xhs_sentiment_report_${TIMESTAMP}.html"

# 使用 Python 读取 JSON 并生成 HTML
python3 << 'PYEOF'
import json
import sys
import os
from datetime import datetime

search_json = os.environ.get("SEARCH_JSON", "")
output_file = os.environ.get("OUTPUT_FILE", os.path.join(os.environ.get("OUTPUT_DIR", "/tmp"), "xhs_sentiment_report.html"))

with open(search_json, "r", encoding="utf-8") as f:
    data = json.load(f)

query = data.get("query", "未知关键词")
search_time = data.get("search_time", datetime.now().strftime("%Y-%m-%d %H:%M"))
total = data.get("total", 0)
notes = data.get("notes", [])

# 统计数据
video_count = sum(1 for n in notes if n.get("type") == "video")
image_count = sum(1 for n in notes if n.get("type") == "image")
total_likes = sum(int(n.get("interact_info", {}).get("liked_count", "0")) for n in notes)
total_collects = sum(int(n.get("interact_info", {}).get("collected_count", "0")) for n in notes)
total_comments = sum(int(n.get("interact_info", {}).get("comment_count", "0")) for n in notes)

# 按互动量排序（点赞+收藏+评论）
for n in notes:
    info = n.get("interact_info", {})
    n["_heat"] = int(info.get("liked_count", "0")) + int(info.get("collected_count", "0")) + int(info.get("comment_count", "0"))

sorted_notes = sorted(notes, key=lambda x: -x.get("_heat", 0))

# 类型分布百分比
total_notes = len(notes) or 1
video_pct = round(video_count / total_notes * 100)
image_pct = 100 - video_pct

# 高频标签统计
tag_counter = {}
for n in notes:
    for tag in n.get("tag_list", []):
        tag_name = tag if isinstance(tag, str) else tag.get("name", "")
        if tag_name:
            tag_counter[tag_name] = tag_counter.get(tag_name, 0) + 1

top_tags = sorted(tag_counter.items(), key=lambda x: -x[1])[:20]
max_tag_count = top_tags[0][1] if top_tags else 1

# 笔记卡片 HTML
notes_html = ""
for idx, note in enumerate(sorted_notes, 1):
    info = note.get("interact_info", {})
    liked = info.get("liked_count", "0")
    collected = info.get("collected_count", "0")
    commented = info.get("comment_count", "0")
    shared = info.get("share_count", "0")
    ntype = "视频" if note.get("type") == "video" else "图文"
    ntype_class = "video" if note.get("type") == "video" else "image"
    title = note.get("title", "") or note.get("desc", "")[:60] or "无标题"
    desc = note.get("desc", "")
    desc_preview = desc[:150] + "..." if len(desc) > 150 else desc
    nickname = note.get("user", {}).get("nickname", "匿名用户")
    note_url = note.get("url", "#")
    tags = note.get("tag_list", [])
    tag_str = " ".join(f"#{t}" if isinstance(t, str) else f"#{t.get('name', '')}" for t in tags[:5])
    heat = note.get("_heat", 0)
    top_badge = '<span class="top-badge">TOP</span>' if idx <= 5 else ""

    notes_html += f'''
    <div class="note-card {ntype_class}">
      <div class="note-header">
        <span class="rank-num">#{idx}</span>
        {top_badge}
        <span class="type-badge {ntype_class}">{ntype}</span>
        <span class="author-text">{nickname}</span>
      </div>
      <h3 class="note-title"><a href="{note_url}" target="_blank" rel="noopener">{title}</a></h3>
      {"<p class='note-desc'>" + desc_preview + "</p>" if desc_preview else ""}
      <div class="note-tags">{tag_str}</div>
      <div class="note-interact">
        <span class="interact-item"><span class="icon-like"></span>{liked}</span>
        <span class="interact-item"><span class="icon-collect"></span>{collected}</span>
        <span class="interact-item"><span class="icon-comment"></span>{commented}</span>
        <span class="interact-item"><span class="icon-share"></span>{shared}</span>
        <span class="heat-score">热度 {heat}</span>
      </div>
    </div>'''

# 标签云 HTML
tags_html = ""
for tag_name, count in top_tags:
    size = max(13, min(32, int(13 + 19 * count / max_tag_count)))
    tags_html += f'<span class="tag-cloud-item" style="font-size:{size}px">{tag_name}({count})</span> '

# 统计概览 HTML
stats_html = f'''
  <div class="stats-grid">
    <div class="stat-card total">
      <div class="stat-value">{total}</div>
      <div class="stat-label">笔记总数</div>
    </div>
    <div class="stat-card video">
      <div class="stat-value">{video_count}</div>
      <div class="stat-label">视频笔记 ({video_pct}%)</div>
    </div>
    <div class="stat-card image">
      <div class="stat-value">{image_count}</div>
      <div class="stat-label">图文笔记 ({image_pct}%)</div>
    </div>
    <div class="stat-card likes">
      <div class="stat-value">{total_likes}</div>
      <div class="stat-label">总点赞</div>
    </div>
    <div class="stat-card collects">
      <div class="stat-value">{total_collects}</div>
      <div class="stat-label">总收藏</div>
    </div>
    <div class="stat-card comments">
      <div class="stat-value">{total_comments}</div>
      <div class="stat-label">总评论</div>
    </div>
  </div>'''

# 类型分布条
type_bar_html = f'''
  <div class="section">
    <h2>内容类型分布</h2>
    <div class="type-bar">
      <div class="type-seg video" style="width:{video_pct}%"><span>{video_pct}% 视频</span></div>
      <div class="type-seg image" style="width:{image_pct}%"><span>{image_pct}% 图文</span></div>
    </div>
  </div>'''

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>小红书学校舆情报告 - {query}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; background:#fafafa; color:#1a1a2e; line-height:1.6; }}
  .container {{ max-width:960px; margin:0 auto; padding:24px 16px; }}

  .header {{ background:linear-gradient(135deg,#ff2442,#ff6b6b,#ff8e8e); color:#fff; border-radius:16px; padding:32px; margin-bottom:24px; position:relative; overflow:hidden; }}
  .header::before {{ content:"小红书"; position:absolute; right:24px; top:50%; transform:translateY(-50%); font-size:72px; opacity:0.08; font-weight:900; }}
  .header h1 {{ font-size:24px; margin-bottom:8px; }}
  .header .meta {{ opacity:0.9; font-size:14px; }}
  .header .gen-time {{ opacity:0.7; font-size:12px; margin-top:4px; }}

  .stats-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:12px; margin-bottom:24px; }}
  .stat-card {{ background:#fff; border-radius:12px; padding:16px; text-align:center; box-shadow:0 2px 8px rgba(0,0,0,0.04); }}
  .stat-card .stat-value {{ font-size:28px; font-weight:700; }}
  .stat-card .stat-label {{ font-size:12px; color:#666; margin-top:2px; }}
  .stat-card.total .stat-value {{ color:#ff2442; }}
  .stat-card.video .stat-value {{ color:#6366f1; }}
  .stat-card.image .stat-value {{ color:#10b981; }}
  .stat-card.likes .stat-value {{ color:#f59e0b; }}
  .stat-card.collects .stat-value {{ color:#ef4444; }}
  .stat-card.comments .stat-value {{ color:#3b82f6; }}

  .section {{ background:#fff; border-radius:12px; padding:24px; margin-bottom:24px; box-shadow:0 2px 8px rgba(0,0,0,0.04); }}
  .section h2 {{ font-size:17px; margin-bottom:16px; padding-bottom:8px; border-bottom:2px solid #fee2e2; }}

  .type-bar {{ display:flex; height:32px; border-radius:8px; overflow:hidden; }}
  .type-seg {{ display:flex; align-items:center; justify-content:center; color:#fff; font-size:13px; font-weight:500; }}
  .type-seg.video {{ background:linear-gradient(90deg,#6366f1,#818cf8); }}
  .type-seg.image {{ background:linear-gradient(90deg,#10b981,#34d399); }}

  .tag-cloud {{ text-align:center; padding:12px 0; line-height:2.2; }}
  .tag-cloud-item {{ display:inline-block; margin:3px 6px; padding:4px 10px; border-radius:16px; background:#fff1f2; color:#be123c; font-weight:500; cursor:default; transition:transform .15s; }}
  .tag-cloud-item:hover {{ transform:scale(1.08); }}

  .note-card {{ border:1px solid #f3f4f6; border-radius:10px; padding:16px; margin-bottom:12px; transition:box-shadow .2s; background:#fff; }}
  .note-card:hover {{ box-shadow:0 4px 16px rgba(255,36,66,0.08); }}
  .note-card.video {{ border-left:4px solid #6366f1; }}
  .note-card.image {{ border-left:4px solid #10b981; }}
  .note-header {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin-bottom:8px; }}
  .rank-num {{ font-weight:700; color:#ff2442; font-size:15px; }}
  .top-badge {{ display:inline-block; padding:1px 6px; border-radius:4px; background:#ff2442; color:#fff; font-size:10px; font-weight:700; }}
  .type-badge {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:500; }}
  .type-badge.video {{ background:#eef2ff; color:#4338ca; }}
  .type-badge.image {{ background:#ecfdf5; color:#065f46; }}
  .author-text {{ font-size:13px; color:#6b7280; }}
  .note-title {{ font-size:15px; margin-bottom:6px; }}
  .note-title a {{ color:#1a1a2e; text-decoration:none; }}
  .note-title a:hover {{ color:#ff2442; text-decoration:underline; }}
  .note-desc {{ font-size:13px; color:#6b7280; margin-bottom:6px; line-height:1.5; }}
  .note-tags {{ font-size:12px; color:#be123c; margin-bottom:8px; }}
  .note-interact {{ display:flex; flex-wrap:wrap; gap:12px; align-items:center; font-size:13px; color:#9ca3af; }}
  .interact-item {{ display:flex; align-items:center; gap:2px; }}
  .icon-like::before {{ content:"\\2764"; }}
  .icon-collect::before {{ content:"\\2B50"; }}
  .icon-comment::before {{ content:"\\1F4AC"; }}
  .icon-share::before {{ content:"\\1F4E4"; }}
  .heat-score {{ margin-left:auto; font-weight:600; color:#ff2442; font-size:12px; }}

  .disclaimer {{ background:#fffbeb; border:1px solid #fcd34d; border-radius:10px; padding:16px; margin-top:24px; font-size:12px; color:#92400e; line-height:1.8; }}
  .disclaimer strong {{ color:#78350f; }}

  .footer {{ text-align:center; font-size:12px; color:#9ca3af; margin-top:16px; padding-bottom:24px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>小红书学校舆情报告</h1>
    <div class="meta">搜索关键词：{query}</div>
    <div class="gen-time">报告生成时间：{search_time}</div>
  </div>

  {stats_html}

  {type_bar_html}

  {"<div class='section'><h2>高频标签</h2><div class='tag-cloud'>" + tags_html + "</div></div>" if top_tags else ""}

  <div class="section">
    <h2>笔记详情 ({total}条)</h2>
    {notes_html if notes_html else "<p style='color:#9ca3af;text-align:center'>暂无笔记数据</p>"}
  </div>

  <div class="disclaimer">
    <strong>免责声明：</strong>本报告数据来自小红书公开笔记，仅供教育场景下的学校舆情监测与研究参考。<br>
    1. 禁止用于商业用途、数据倒卖、恶意爬取等任何违法违规行为；<br>
    2. 本技能需要用户自己提供账号进行登录操作，请严格控制使用频率；<br>
    3. 过于频繁使用会触发小红书平台风控规则，可能导致账号被限流或封禁，使用者自行承担相关风险；<br>
    4. 互动数据为采集时刻快照，实际数据可能变化；<br>
    5. 使用本技能所产生的一切法律后果，由使用者自行承担。
  </div>

  <div class="footer">
    小红书学校舆情搜索助手 | 仅采集公开信息，不涉及任何非法数据获取
  </div>
</div>
</body>
</html>'''

with open(output_file, "w", encoding="utf-8") as f:
    f.write(html)

# 自检：验证生成的 HTML 文件是否正常
file_size = os.path.getsize(output_file)

if file_size < 1024:
    print(f"WARNING: 报告文件过小 ({file_size} bytes)，可能存在数据异常")
    print(f"DIAG: total={total}, notes_len={len(notes)}, video={video_count}, image={image_count}")
    print(f"DIAG: tags_len={len(top_tags)}, total_likes={total_likes}")
else:
    print(output_file)
PYEOF

# 自检：检查输出文件
if [ ! -f "${OUTPUT_FILE}" ]; then
    echo "ERROR: 报告文件未生成: ${OUTPUT_FILE}" >&2
    exit 1
fi

FILE_SIZE=$(stat -f%z "${OUTPUT_FILE}" 2>/dev/null || stat -c%s "${OUTPUT_FILE}" 2>/dev/null || echo 0)
if [ "$FILE_SIZE" -lt 1024 ]; then
    echo "WARNING: 报告文件异常 (${FILE_SIZE} bytes)，请检查搜索结果 JSON 数据结构"
fi

echo "报告已生成: ${OUTPUT_FILE}"
