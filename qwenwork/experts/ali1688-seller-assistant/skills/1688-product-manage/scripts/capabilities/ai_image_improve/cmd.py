#!/usr/bin/env python3
"""AI 主图优化命令 — CLI 入口（四阶段：prepare / customize / generate / apply）"""

from __future__ import annotations

COMMAND_NAME = "ai_image_improve"
COMMAND_DESC = "AI 智能优化商品主图（四阶段：prepare / customize / generate / apply）"

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import argparse
import json
import time
import platform
import subprocess
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from _output import make_output, print_output, print_error
from capabilities.ai_image_improve.service import (
    query_offer_info,
    submit_image_parse,
    poll_image_parse_result,
    submit_image_generation,
    poll_image_generation_result,
    convert_image_urls,
    change_main_image,
)

# 状态文件
STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "..", ".image_state.json")
ALLOWED_SIZES = ("1:1", "3:4")
DEFAULT_SIZE = "1:1"
MAX_WORKERS = 5


# ===================== 状态管理 =====================

def _save_state(state: dict) -> None:
    state["saved_at"] = time.time()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


def _load_state() -> Optional[dict]:
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    # 旧版状态结构（无 image_specs）视为失效
    if not isinstance(data, dict) or "image_specs" not in data:
        return None
    return data


def _clear_state() -> None:
    try:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
    except Exception:
        pass


# ===================== Prompt 构造 =====================

def _build_prompt(size: str, text_selling_points: Optional[str] = None, background: Optional[str] = None) -> str:
    """根据比例 / 文字卖点 / 背景场景拼装 prompt。

    拼装规则（跟随示例标点）：
      仅比例：       做一张1688商品电商的主图,{size}比例
      比例+场景：    做一张1688商品电商的主图,{size}比例，背景换成{bg}
      比例+卖点：    做一张1688商品电商的主图,{size}比例，突出{tsp}的文字卖点
      比例+卖点+场景：做一张1688商品电商的主图,{size}比例，突出{tsp}的文字卖点,背景换成{bg}

    text_selling_points：商家手填的文字卖点原文（默认为空，无数据源支撑，仅可由商家主动填写）。
    例如填入 `“双头设计”和“油性不晕染”`，拼接后为 `突出“双头设计”和“油性不晕染”的文字卖点`。
    """
    if size not in ALLOWED_SIZES:
        size = DEFAULT_SIZE
    tsp = text_selling_points.strip() if (text_selling_points and text_selling_points.strip()) else None
    bg = background.strip() if (background and background.strip()) else None
    out = f"做一张1688商品电商的主图,{size}比例"
    if tsp:
        out += f"，突出{tsp}的文字卖点"
    if bg:
        # 前面已有卖点时用英文逗号划分（跟随示例）；否则仅比例后接背景仍使用中文逗号。
        sep = "," if tsp else "，"
        out += f"{sep}背景换成{bg}"
    return out


# ===================== HTML Prompt 编辑器 =====================

HTML_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..")


def _generate_prompt_html(offer_id: str, image_specs: list) -> str:
    """生成交互式 Prompt 编辑 HTML 文件，返回文件绝对路径。

    交互规则（于商家侧的强约束）：
    - 商家可调整「图片比例」「文字卖点」「场景」三个字段；其中「文字卖点」默认为空、无数据来源支撑、由商家自行选填；
    - 「提示词」由系统按 `比例 + (可选)文字卖点 + (可选)场景` 规则自动生成，**为只读展示**，不支持手动编辑；
    - 行级按钮「📋 用此行覆盖全部图」：把该行提示词作为全部图的提示词复制到剪贴板，不修改表格内容；
    - 全局按钮「📋 一键复制全部提示词」：把每行各自的提示词复制到剪贴板。
    """
    import html as html_mod

    # 构建表格行数据（JSON）—— 含 text_selling_points（默认空，可由商家在网页编辑）
    rows_data = []
    for spec in image_specs:
        rows_data.append({
            "index": spec["index"],
            "original_url": spec["original_url"],
            "size": spec.get("size", DEFAULT_SIZE),
            "text_selling_points": spec.get("text_selling_points", ""),
            "scene": spec.get("scene", ""),
            "prompt": spec.get("prompt", ""),
        })

    rows_json = json.dumps(rows_data, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>AI 主图优化 - 提示词编辑器（商品 {html_mod.escape(offer_id)}）</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; padding: 24px; background: #f5f7fa; color: #333; }}
.header {{ max-width: 1200px; margin: 0 auto 12px; }}
.header h1 {{ font-size: 1.4rem; margin-bottom: 8px; }}
.header p {{ color: #666; font-size: 0.9rem; }}
.tip {{ max-width: 1200px; margin: 0 auto 16px; padding: 10px 14px; background: #fff7e6; border: 1px solid #ffd591; border-radius: 6px; font-size: 0.85rem; color: #874d00; line-height: 1.7; }}
.tip b {{ color: #d46b08; }}
.toolbar {{ max-width: 1200px; margin: 0 auto 16px; display: flex; gap: 12px; flex-wrap: wrap; }}
.toolbar button {{ padding: 8px 16px; border: 1px solid #ddd; border-radius: 6px; background: #fff; cursor: pointer; font-size: 0.85rem; transition: all 0.2s; }}
.toolbar button:hover {{ background: #FF6A00; color: #fff; border-color: #FF6A00; }}
.toolbar button.primary {{ background: #FF6A00; color: #fff; border-color: #FF6A00; }}
.toolbar button.primary:hover {{ background: #e55d00; }}
table {{ width: 100%; max-width: 1200px; margin: 0 auto; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }}
th {{ background: #f8f9fa; padding: 12px 10px; text-align: left; font-size: 0.85rem; color: #555; border-bottom: 2px solid #eee; }}
td {{ padding: 10px; border-bottom: 1px solid #f0f0f0; vertical-align: top; font-size: 0.85rem; }}
tr:last-child td {{ border-bottom: none; }}
.img-cell img {{ width: 80px; height: 80px; object-fit: cover; border-radius: 4px; border: 1px solid #eee; }}
.size-select {{ padding: 6px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85rem; }}
.edit-input {{ width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85rem; resize: vertical; min-height: 36px; font-family: inherit; }}
.prompt-cell {{ min-width: 280px; }}
.prompt-display {{ padding: 8px 10px; min-height: 36px; background: #fafafa; border: 1px dashed #d9d9d9; border-radius: 4px; font-size: 0.85rem; line-height: 1.6; color: #555; word-break: break-all; white-space: pre-wrap; }}
.row-actions {{ display: flex; flex-direction: column; gap: 6px; min-width: 140px; }}
.row-actions button {{ padding: 5px 10px; border: 1px solid #ddd; border-radius: 4px; background: #fff; cursor: pointer; font-size: 0.78rem; white-space: nowrap; transition: all 0.2s; }}
.row-actions button:hover {{ background: #e8f4ff; border-color: #4096ff; color: #4096ff; }}
.toast {{ position: fixed; top: 20px; left: 50%; transform: translateX(-50%); background: #333; color: #fff; padding: 10px 24px; border-radius: 6px; font-size: 0.9rem; opacity: 0; transition: opacity 0.3s; pointer-events: none; z-index: 999; }}
.toast.show {{ opacity: 1; }}
</style>
</head>
<body>
<div class="header">
  <h1>🖼️ AI 主图优化 - 提示词编辑器</h1>
  <p>商品ID: {html_mod.escape(offer_id)}</p>
</div>

<div class="tip">
  💡 <b>使用说明</b>：你可调整「图片比例」「文字卖点」「场景」三个字段，<b>「文字卖点」默认为空、无数据来源，由你自行选填</b>（填完拼接为“突出{{你填写的文字卖点}}的文字卖点”）；<b>「提示词」由系统按规则自动生成，不支持手动编辑</b>。修改任一字段后，对应行的「提示词」会自动刷新。<b>调整完后点击下方按钮即可复制提示词</b>：点击「📋 一键复制全部提示词」复制每张图各自的提示词；点击行级「📋 用此行覆盖全部图」把该行提示词作为全部图的提示词复制。
</div>

<div class="toolbar">
  <button class="primary" onclick="copyAllPrompts()">📋 一键复制全部提示词</button>
</div>

<table>
  <thead>
    <tr>
      <th>序号</th>
      <th>主图</th>
      <th>图片比例</th>
      <th>文字卖点（默认空，可选填）</th>
      <th>场景</th>
      <th class="prompt-cell">提示词（系统自动生成，只读）</th>
      <th>操作</th>
    </tr>
  </thead>
  <tbody id="tableBody"></tbody>
</table>

<div class="toast" id="toast"></div>

<script>
const ROWS = {rows_json};

function buildPrompt(size, textSellingPoints, scene) {{
  const tsp = (textSellingPoints || '').trim();
  const sc = (scene || '').trim();
  let out = `\u505a\u4e00\u5f201688\u5546\u54c1\u7535\u5546\u7684\u4e3b\u56fe,${{size}}\u6bd4\u4f8b`;
  if (tsp) {{
    out += `\uff0c\u7a81\u51fa${{tsp}}\u7684\u6587\u5b57\u5356\u70b9`;
  }}
  if (sc) {{
    // 前面已有卖点时用英文逗号连接，否则仅比例后用中文逗号
    const sep = tsp ? ',' : '\uff0c';
    out += `${{sep}}\u80cc\u666f\u6362\u6210${{sc}}`;
  }}
  return out;
}}

function renderTable() {{
  const tbody = document.getElementById('tableBody');
  tbody.innerHTML = '';
  ROWS.forEach((row, i) => {{
    if (row.scene === undefined) row.scene = '';
    if (row.text_selling_points === undefined) row.text_selling_points = '';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${{row.index}}</td>
      <td class="img-cell"><img src="${{row.original_url}}" alt="\u4e3b\u56fe${{row.index}}"/></td>
      <td>
        <select class="size-select" data-idx="${{i}}" onchange="onSizeChange(this)">
          <option value="1:1" ${{row.size==='1:1'?'selected':''}}>1:1</option>
          <option value="3:4" ${{row.size==='3:4'?'selected':''}}>3:4</option>
        </select>
      </td>
      <td><textarea class="edit-input tsp-input" data-idx="${{i}}" rows="2" oninput="onTextSellingPointsChange(this)" placeholder="\u9009\u586b\uff0c\u5982\uff1a\u201c\u53cc\u5934\u8bbe\u8ba1\u201d\u548c\u201c\u6cb9\u6027\u4e0d\u6655\u67d3\u201d">${{row.text_selling_points}}</textarea></td>
      <td><textarea class="edit-input scene-input" data-idx="${{i}}" rows="2" oninput="onSceneChange(this)" placeholder="\u8f93\u5165\u56fe\u7247\u573a\u666f\uff0c\u5982\uff1a\u7c73\u767d\u8272\u5927\u7406\u77f3\u53f0\u9762 + \u6696\u8272\u81ea\u7136\u5149">${{row.scene}}</textarea></td>
      <td class="prompt-cell"><div class="prompt-display" data-idx="${{i}}">${{row.prompt}}</div></td>
      <td class="row-actions">
        <button onclick="applyRowPromptToAll(${{i}})">📋 用此行覆盖全部图</button>
      </td>
    `;
    tbody.appendChild(tr);
  }});
}}

function onSizeChange(el) {{
  const i = parseInt(el.dataset.idx);
  ROWS[i].size = el.value;
  syncPrompt(i);
}}

function onTextSellingPointsChange(el) {{
  const i = parseInt(el.dataset.idx);
  ROWS[i].text_selling_points = el.value;
  syncPrompt(i);
}}

function onSceneChange(el) {{
  const i = parseInt(el.dataset.idx);
  ROWS[i].scene = el.value;
  syncPrompt(i);
}}

function syncPrompt(i) {{
  const row = ROWS[i];
  row.prompt = buildPrompt(row.size, row.text_selling_points, row.scene);
  const displays = document.querySelectorAll('.prompt-display');
  if (displays[i]) displays[i].textContent = row.prompt;
}}

function applyRowPromptToAll(srcIdx) {{
  const srcPrompt = ROWS[srcIdx].prompt;
  const text = ROWS.map((r) => `\u56fe${{r.index}}: ${{srcPrompt}}`).join('\\n');
  copyToClipboard(text);
  showToast(`\u2705 \u5df2\u590d\u5236\uff08\u7b2c${{srcIdx+1}}\u884c\u4f5c\u4e3a\u5168\u90e8\u56fe\u63d0\u793a\u8bcd\uff09`);
}}

function copyAllPrompts() {{
  const text = ROWS.map((r) => `\u56fe${{r.index}}: ${{r.prompt}}`).join('\\n');
  copyToClipboard(text);
  showToast('\u2705 \u5df2\u590d\u5236\u5168\u90e8\u63d0\u793a\u8bcd');
}}

function copyToClipboard(text) {{
  if (navigator.clipboard) {{
    navigator.clipboard.writeText(text);
  }} else {{
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
  }}
}}

function showToast(msg) {{
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2000);
}}

renderTable();
</script>
</body>
</html>"""

    html_path = os.path.join(HTML_OUTPUT_DIR, f"prompt_editor_{offer_id}.html")
    html_path = os.path.abspath(html_path)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # 自动打开 HTML 文件
    try:
        system = platform.system()
        if system == "Darwin":
            subprocess.Popen(["open", html_path])
        elif system == "Windows":
            os.startfile(html_path)
        else:
            subprocess.Popen(["xdg-open", html_path])
    except Exception:
        pass

    return html_path


# ===================== 阶段 1：prepare =====================

def _parse_one(image_url: str) -> dict:
    """单图：提交解析 + 轮询，失败返回 success=False。"""
    try:
        task_id = submit_image_parse(image_url)
        result = poll_image_parse_result(task_id)
        return result if isinstance(result, dict) else {"success": False, "message": "解析返回异常"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def _mode_prepare(offer_id: str) -> None:
    offer_info = query_offer_info(offer_id)
    title = offer_info["title"]
    images = offer_info["images"]

    if not images:
        print_output(make_output(
            success=False,
            error_code="NO_IMAGE",
            markdown=f"## 主图获取失败\n\n**商品ID**: {offer_id}\n\n该商品未查询到主图，无法进行优化。",
            data={"offerId": offer_id},
        ))
        return

    # 并发解析每张主图
    parse_results: list = [None] * len(images)
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(images))) as pool:
        for idx, res in enumerate(pool.map(_parse_one, images)):
            parse_results[idx] = res

    # 构造 image_specs（不再写入卖点字段；解析数据保留供 Agent 推荐场景参考）
    image_specs: list = []
    for idx, (url, parse) in enumerate(zip(images, parse_results), 1):
        if parse and parse.get("success"):
            parse_save = {
                "text_region_summary": parse.get("text_region_summary", ""),
                "composition_summary": parse.get("composition_summary", ""),
                "selling_points_visible": list(parse.get("selling_points_visible") or []),
            }
        else:
            parse_save = {"success": False, "message": (parse or {}).get("message", "解析失败")}

        size = DEFAULT_SIZE
        prompt = _build_prompt(size)
        image_specs.append({
            "index": idx,
            "original_url": url,
            "size": size,
            "text_selling_points": "",
            "prompt": prompt,
            "parse": parse_save,
        })

    state = {
        "offer_id": offer_id,
        "original_title": title,
        "image_specs": image_specs,
        "stage": "prepare",
    }
    _save_state(state)

    # markdown 输出
    md = ["## 主图优化上下文已就绪\n"]
    md.append(f"**商品ID**: {offer_id}")
    if title:
        md.append(f"**商品标题**: {title}")
    md.append(f"**主图数量**: {len(image_specs)}\n")
    md.append("| 序号 | 图片 | 图片比例 | 文字卖点（默认空） | 默认 prompt（完整句子） |")
    md.append("|------|------|----------|------------------|---------------------------|")
    for spec in image_specs:
        prompt_cell = (spec["prompt"] or "").replace("|", "\\|").replace("\n", " ")
        tsp_cell = (spec.get("text_selling_points") or "—").replace("|", "\\|").replace("\n", " ")
        md.append(f"| {spec['index']} | {spec['original_url']} | {spec['size']} | {tsp_cell} | {prompt_cell} |")

    md.append("")
    md.append("### 解析参考（Agent 基于此为每张图推荐场景）")
    md.append("")
    md.append("| 序号 | 构图摘要 |")
    md.append("|------|----------|")
    for spec in image_specs:
        parse = spec.get("parse") or {}
        comp = (parse.get("composition_summary") or "—").replace("|", "\\|").replace("\n", " ")
        md.append(f"| {spec['index']} | {comp} |")
    md.append("")
    md.append("> 🔔 **Agent 行为约定**：默认 prompt 仅含「比例」，**未指定背景场景**，**「文字卖点」默认为空（无数据源支撑，仅可由商家主动填写）**。Agent 必须基于上方「解析参考」为每张图推荐一个具体的电商主图场景（如「米白色大理石台面 + 暖色自然光」「原木桌面 + 浅灰背景 + 绿植点缀」），通过 `--customize` 以 `background` 字段注入后，会自动打开 **Prompt 编辑器 HTML** 供商家调整「图片比例 / 文字卖点 / 场景」，再执行 generate。")
    md.append("")
    md.append("> ⛔ **提示词输入规范**：customize 仅接受 `size`（图片比例）、`background`（图片场景）、`text_selling_points`（文字卖点原文，可选）三个字段，提示词由系统按规则自动拼装，**不允许商家或 Agent 提交 `prompt` / `selling_points` 等自定义字段**，提交后 CLI 会直接报错。")
    md.append("")
    md.append("---")
    md.append("请商家选择下一步操作：")
    md.append(f"1. **应用默认 prompt（无背景，由模型自由生成）** → `python3 cli.py ai_image_improve --offer_id {offer_id} --generate`")
    md.append(f"2. **输入比例/场景生成 prompt**（统一或逐图） → ")
    md.append(f"   `python3 cli.py ai_image_improve --offer_id {offer_id} --customize '<JSON>'`")
    md.append("")
    md.append("**自定义 JSON 格式**（仅允许 `size` / `background` / `text_selling_points` 三个字段，后二者均可选）：")
    md.append("- 统一型：`{\"size\":\"1:1\",\"background\":\"米白色大理石台面 + 暖色自然光\",\"text_selling_points\":\"“双头设计”和“油性不晕染”\"}`")
    md.append("- 逐图型：`{\"1\":{\"size\":\"1:1\",\"background\":\"原木桌面 + 浅灰背景\",\"text_selling_points\":\"“防水”和“耐磨”\"},\"2\":{\"size\":\"3:4\",\"background\":\"米白色亚麻布平铺\"}}`")
    md.append("- `text_selling_points` 默认空、无数据源支撑，**仅可由商家主动填写，Agent 不得自行推断填充**")
    md.append("- 图片比例仅支持 `1:1` 或 `3:4`")

    print_output(make_output(
        success=True,
        markdown="\n".join(md),
        data={
            "offerId": offer_id,
            "title": title,
            "imageSpecs": image_specs,
        },
    ))


# ===================== 阶段 2：customize =====================

def _normalize_size(size: str) -> str:
    if size in ALLOWED_SIZES:
        return size
    raise ValueError(f"size 仅支持 1:1 / 3:4，收到：{size}")


ALLOWED_CUSTOMIZE_KEYS = {"size", "background", "text_selling_points"}


def _validate_customize_keys(payload: dict, where: str) -> None:
    """校验 customize payload 仅允许 size / background / text_selling_points，
    禁止 prompt / selling_points 等其他字段（提示词仍由系统拼装，不接受手填整句）。"""
    extra = sorted(set(payload.keys()) - ALLOWED_CUSTOMIZE_KEYS)
    if extra:
        raise ValueError(
            f"{where}出现不允许的字段：{extra}。仅支持 'size'（图片比例）、'background'（图片场景）、"
            f"'text_selling_points'（文字卖点，商家手填原文，可选）；提示词由系统按规则自动拼装，"
            f"**不允许提交 'prompt' / 'selling_points' 等自定义字段**。"
        )


def _apply_unified(specs: list, payload: dict) -> None:
    _validate_customize_keys(payload, "统一型 payload ")
    size = payload.get("size") or DEFAULT_SIZE
    size = _normalize_size(size)
    background = payload.get("background")
    tsp = payload.get("text_selling_points")

    for spec in specs:
        spec["size"] = size
        if background is not None:
            spec["scene"] = background
        if tsp is not None:
            spec["text_selling_points"] = tsp
        spec["prompt"] = _build_prompt(
            size,
            spec.get("text_selling_points") or "",
            spec.get("scene") or "",
        )


def _apply_per_image(specs: list, payload: dict) -> None:
    for key, val in payload.items():
        if not isinstance(val, dict):
            raise ValueError(f"序号 {key} 的配置必须是对象")
        try:
            idx = int(key)
        except (TypeError, ValueError):
            raise ValueError(f"非法的序号：{key}")
        target = next((s for s in specs if s["index"] == idx), None)
        if not target:
            raise ValueError(f"序号 {idx} 不存在（共 {len(specs)} 张图）")

        _validate_customize_keys(val, f"序号 {idx} 的 payload ")

        size = val.get("size") or target.get("size") or DEFAULT_SIZE
        size = _normalize_size(size)
        target["size"] = size

        background = val.get("background")
        if background is not None:
            target["scene"] = background

        tsp = val.get("text_selling_points")
        if tsp is not None:
            target["text_selling_points"] = tsp

        target["prompt"] = _build_prompt(
            size,
            target.get("text_selling_points") or "",
            target.get("scene") or "",
        )


def _is_per_image_payload(payload: dict) -> bool:
    """payload 的所有 key 都能被解释为正整数序号 → 逐图型。"""
    if not payload:
        return False
    for k in payload.keys():
        try:
            int(k)
        except (TypeError, ValueError):
            return False
    return True


def _mode_customize(offer_id: str, customize_json: str, no_html: bool = False) -> None:
    """customize 阶段：仅落库，不调用任何远程接口。

    no_html=True 时跳过 HTML 编辑器生成与浏览器自动打开（用于「直通 generate」例外路径——
    商家已通过逐图结构化文本一次性给出最终规格，HTML 编辑器形同虚设）。
    """
    state = _load_state()
    if not state or state.get("offer_id") != offer_id:
        print_output(make_output(
            success=False,
            error_code="NO_STATE",
            markdown=f"## 未找到主图优化上下文\n\n**商品ID**: {offer_id}\n\n请先执行 `python3 cli.py ai_image_improve --offer_id {offer_id}` 拉取上下文。",
        ))
        return

    try:
        payload = json.loads(customize_json)
        if not isinstance(payload, dict) or not payload:
            raise ValueError("必须为非空 JSON 对象")
    except Exception as e:
        print_output(make_output(
            success=False,
            error_code="INVALID_PARAM",
            markdown=f"## --customize 参数解析失败\n\n错误：{e}",
        ))
        return

    specs: list = state.get("image_specs") or []
    try:
        if _is_per_image_payload(payload):
            _apply_per_image(specs, payload)
        else:
            _apply_unified(specs, payload)
    except Exception as e:
        print_output(make_output(
            success=False,
            error_code="INVALID_PARAM",
            markdown=f"## --customize 参数错误\n\n{e}",
        ))
        return

    state["image_specs"] = specs
    state["stage"] = "customize"
    _save_state(state)

    md = ["## 主图优化 prompt 已更新\n"]
    md.append(f"**商品ID**: {offer_id}\n")
    if not no_html:
        # 常规回合②：生成交互式 Prompt 编辑器 HTML 并自动打开（场景已由 Agent 推荐注入）
        html_path = _generate_prompt_html(offer_id, specs)
        md.append("✨ **已为您打开《AI 主图优化 - 提示词编辑器》网页**，您可以在网页上调整**图片比例 / 文字卖点 / 场景**：")
        md.append("")
        md.append("- 调整「图片比例」「文字卖点」或「场景」→ 对应行的「提示词」会按默认规则自动重新生成")
        md.append("- 「文字卖点」默认为空、无数据源支撑，可由您自行选填（例：`“双头设计”和“油性不晕染”`，拼接为“突出“双头设计”和“油性不晕染”的文字卖点”）")
        md.append("- 提示词由系统按规则自动生成，**不支持手动编辑**（也不接受 customize 注入 `prompt` / `selling_points` 字段）")
        md.append("- 调整完后点击「📋 一键复制全部提示词」复制每张图各自的提示词；或点击行级「📋 用此行覆盖全部图」把当前行提示词作为全部图的提示词复制。")
        md.append("")
        md.append(f"> 网页未自动打开？手动打开文件：`{html_path}`")
        md.append("")
    else:
        # 直通 generate 例外路径：商家已逐图给出完整规格，跳过 HTML，仅落库 + 渲染最终 prompt 表
        md.append("> 🚀 **直通 generate 路径**：已识别商家逐图结构化输入，跳过 Prompt 编辑器 HTML，prompt 已直接落库。")
        md.append("")
    md.append("---")
    md.append("")
    md.append("### 当前 Prompt 表")
    md.append("")
    md.append("| 序号 | 图片 | 图片比例 | 文字卖点 | 场景 | 最终 prompt（完整句子） |")
    md.append("|------|------|----------|----------|------|---------------------------|")
    for spec in specs:
        tsp = (spec.get("text_selling_points") or "—").replace("|", "\\|").replace("\n", " ")
        sc = (spec.get("scene") or "—").replace("|", "\\|").replace("\n", " ")
        prompt_cell = (spec["prompt"] or "").replace("|", "\\|").replace("\n", " ")
        md.append(f"| {spec['index']} | {spec['original_url']} | {spec['size']} | {tsp} | {sc} | {prompt_cell} |")
    md.append("")
    md.append("---")
    md.append(f"确认无误后执行：`python3 cli.py ai_image_improve --offer_id {offer_id} --generate`")

    print_output(make_output(
        success=True,
        markdown="\n".join(md),
        data={"offerId": offer_id, "imageSpecs": specs},
    ))


# ===================== 阶段 3：generate =====================

def _generate_one(spec: dict) -> dict:
    """单图：提交生成 + 轮询。"""
    idx = spec["index"]
    try:
        task_id = submit_image_generation(
            image_id=str(idx),
            image_url=spec["original_url"],
            prompt=spec["prompt"],
            size=spec["size"],
        )
        result = poll_image_generation_result(task_id)
    except Exception as e:
        return {"index": idx, "success": False, "message": str(e), "original_url": spec["original_url"]}

    if result.get("success") and result.get("gen_image_urls"):
        return {
            "index": idx,
            "success": True,
            "generated_url": result["gen_image_urls"][0],
            "original_url": spec["original_url"],
        }
    return {
        "index": idx,
        "success": False,
        "message": result.get("message", "生成失败"),
        "original_url": spec["original_url"],
    }


def _mode_generate(offer_id: str) -> None:
    state = _load_state()
    if not state or state.get("offer_id") != offer_id:
        print_output(make_output(
            success=False,
            error_code="NO_STATE",
            markdown=f"## 未找到主图优化上下文\n\n**商品ID**: {offer_id}\n\n请先执行 `python3 cli.py ai_image_improve --offer_id {offer_id}` 拉取上下文。",
        ))
        return

    specs: list = state.get("image_specs") or []
    if not specs:
        print_output(make_output(
            success=False,
            error_code="NO_IMAGE_SPECS",
            markdown="## 无可生成的主图\n\n请重新执行 prepare。",
        ))
        return

    # 并发生成
    generated: list = [None] * len(specs)
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(specs))) as pool:
        for i, res in enumerate(pool.map(_generate_one, specs)):
            generated[i] = res

    # 按 index 排序
    generated.sort(key=lambda x: x["index"])
    state["generated"] = generated
    state["stage"] = "generate"
    _save_state(state)

    success_cnt = sum(1 for g in generated if g.get("success"))
    fail_cnt = len(generated) - success_cnt

    md = ["## AI 主图生成完成\n"]
    md.append(f"**商品ID**: {offer_id}")
    md.append(f"**成功**: {success_cnt} 张  **失败**: {fail_cnt} 张\n")
    md.append("| 序号 | 原图 | 优化后图片 |")
    md.append("|------|------|------------|")
    for g in generated:
        if g.get("success"):
            new_cell = g["generated_url"]
        else:
            msg = (g.get("message") or "生成失败").replace("|", "\\|").replace("\n", " ")
            new_cell = f"生成失败，已保留原图（{msg}）"
        md.append(f"| {g['index']} | {g['original_url']} | {new_cell} |")

    md.append("")
    md.append("---")
    md.append("请商家选择下一步操作：")
    md.append(f"1. **全部应用优化后的图片** → `python3 cli.py ai_image_improve --offer_id {offer_id} --apply`")
    md.append(f"2. **部分应用**（按序号，逗号分隔） → ")
    md.append(f"   `python3 cli.py ai_image_improve --offer_id {offer_id} --apply --select \"1,3,5\"`")
    md.append("3. **不应用**：直接结束，无需调用命令")

    print_output(make_output(
        success=True,
        markdown="\n".join(md),
        data={"offerId": offer_id, "generated": generated},
    ))


# ===================== 阶段 4：apply =====================

def _parse_select(select_str: str) -> list:
    if not select_str:
        return []
    out: list = []
    for tok in select_str.split(","):
        tok = tok.strip()
        if not tok:
            continue
        try:
            out.append(int(tok))
        except ValueError:
            raise ValueError(f"非法序号：{tok}")
    return out


def _mode_apply(offer_id: str, select_str: str) -> None:
    state = _load_state()
    if not state or state.get("offer_id") != offer_id:
        print_output(make_output(
            success=False,
            error_code="NO_STATE",
            markdown=f"## 未找到主图优化上下文\n\n**商品ID**: {offer_id}\n\n请先依次执行 prepare → generate。",
        ))
        return

    specs: list = state.get("image_specs") or []
    generated: list = state.get("generated") or []
    if not specs or not generated:
        print_output(make_output(
            success=False,
            error_code="NO_GENERATED",
            markdown=f"## 未找到生成结果\n\n**商品ID**: {offer_id}\n\n请先执行：`python3 cli.py ai_image_improve --offer_id {offer_id} --generate`",
        ))
        return

    # 计算 selected：默认全部成功的；指定 --select 时取交集
    success_set = {g["index"] for g in generated if g.get("success")}
    try:
        select_list = _parse_select(select_str)
    except Exception as e:
        print_output(make_output(
            success=False,
            error_code="INVALID_PARAM",
            markdown=f"## --select 参数错误\n\n{e}",
        ))
        return

    if select_list:
        selected = [i for i in select_list if i in success_set]
        ignored = [i for i in select_list if i not in success_set]
    else:
        selected = sorted(success_set)
        ignored = []

    if not selected:
        print_output(make_output(
            success=False,
            error_code="NO_SELECTED",
            markdown=f"## 无可应用的优化图片\n\n**商品ID**: {offer_id}\n\n所选序号均未成功生成。",
            data={"offerId": offer_id, "ignored": ignored},
        ))
        return

    # 转换 URL（仅对 selected 中已成功生成的图片，最多重试 2 次，共 3 次尝试）
    gen_index_map = {g["index"]: g for g in generated}
    pic_urls = [gen_index_map[i]["generated_url"] for i in selected]
    convert_result = None
    for attempt in range(3):
        convert_result = convert_image_urls(pic_urls)
        if convert_result.get("success"):
            break
        if attempt < 2:
            time.sleep(2)

    if not convert_result.get("success"):
        md = [
            "## AI 主图链接转换失败",
            "",
            f"**商品ID**: {offer_id}",
            "",
            "图片链接转换失败，请稍后重试",
            "",
            "**建议**：请商家将本地图片上传至图片银行后，由人工替换主图。",
        ]
        print_output(make_output(
            success=False,
            markdown="\n".join(md),
            data={"offerId": offer_id, "selected": selected},
        ))
        return

    converted_urls = convert_result["images"]
    if len(converted_urls) != len(selected):
        # 转换数量与请求不一致，按顺序对齐已转换的，剩余视为失败
        pass

    # 序号 → 转换后链接
    convert_map = {idx: url for idx, url in zip(selected, converted_urls)}

    # 合并最终主图：按 specs 顺序，命中 selected 用转换链接，否则保留 original_url
    final_images: list = []
    rows = []
    for spec in specs:
        idx = spec["index"]
        original = spec["original_url"]
        if idx in convert_map:
            final_images.append(convert_map[idx])
            rows.append((idx, original, convert_map[idx], "应用优化图"))
        else:
            final_images.append(original)
            reason = "未选中" if select_list else "生成失败" if idx not in success_set else "保留原图"
            rows.append((idx, original, original, reason))

    # 调用修改主图
    change_result = change_main_image(offer_id, final_images)

    md = []
    if change_result.get("success"):
        md.append("## 主图修改成功\n")
        md.append(f"**商品ID**: {offer_id}\n")
    else:
        md.append("## 主图修改失败\n")
        md.append(f"**商品ID**: {offer_id}")
        md.append(f"\n**错误**：{change_result.get('message', '未知错误')}\n")

    md.append("| 序号 | 原图 | 最终主图 | 来源 |")
    md.append("|------|------|----------|------|")
    for idx, orig, final, src in rows:
        md.append(f"| {idx} | {orig} | {final} | {src} |")

    if ignored:
        md.append("")
        md.append(f"> ⚠️ 以下序号未成功生成，已忽略：{ignored}")

    if change_result.get("success"):
        # 成功后清理状态
        _clear_state()

    print_output(make_output(
        success=bool(change_result.get("success")),
        markdown="\n".join(md),
        data={"offerId": offer_id, "finalImages": final_images, "selected": selected, "ignored": ignored},
    ))


# ===================== 入口 =====================

def _print_usage() -> None:
    print_output(make_output(
        success=False,
        error_code="MISSING_PARAM",
        markdown="""## 参数错误

请按以下方式使用（四阶段：prepare / customize / generate / apply）：

1. **prepare** 拉取主图并并发解析，生成默认 prompt 表：
   ```
   python3 cli.py ai_image_improve --offer_id 123456
   ```

2. **customize**（可选）调整图片比例 / 文字卖点 / 场景（仅允许 `size` / `background` / `text_selling_points` 三个字段，不接受 `prompt` / `selling_points`）：
   ```
   python3 cli.py ai_image_improve --offer_id 123456 --customize '{"size":"3:4","background":"米白色大理石台面 + 暖色自然光","text_selling_points":"“双头设计”和“油性不晕染”"}'
   python3 cli.py ai_image_improve --offer_id 123456 --customize '{"1":{"size":"1:1","background":"原木桌面 + 浅灰背景","text_selling_points":"“防水”和“耐磨”"}}'
   # 直通 generate 例外路径：商家已逐图给出完整规格，跳过 Prompt 编辑器 HTML
   python3 cli.py ai_image_improve --offer_id 123456 --customize '<JSON>' --no-html
   ```

3. **generate** 并发执行图生图：
   ```
   python3 cli.py ai_image_improve --offer_id 123456 --generate
   ```

4. **apply** 应用优化主图：
   ```
   python3 cli.py ai_image_improve --offer_id 123456 --apply
   python3 cli.py ai_image_improve --offer_id 123456 --apply --select "1,3,5"
   ```
""",
    ))


def main(args=None):
    """AI 主图优化命令入口（四阶段）。"""
    parser = argparse.ArgumentParser(prog="ai_image_improve", description=COMMAND_DESC)
    parser.add_argument("--offer_id", type=str, default="", help="商品ID（所有阶段必传）")
    parser.add_argument("--customize", type=str, default="", help="自定义 prompt/卖点/比例（JSON）")
    parser.add_argument("--no-html", dest="no_html", action="store_true", help="customize 阶段跳过 Prompt 编辑器 HTML 生成（用于直通 generate 例外路径）")
    parser.add_argument("--generate", action="store_true", help="并发执行图生图")
    parser.add_argument("--apply", action="store_true", help="应用优化主图（合并未选中位次保留原图）")
    parser.add_argument("--select", type=str, default="", help="apply 阶段：仅应用部分序号，如 \"1,3,5\"")

    if args is None:
        args = sys.argv[1:]
    parsed = parser.parse_args(args)

    try:
        if not parsed.offer_id:
            _print_usage()
            return

        # apply 阶段
        if parsed.apply:
            _mode_apply(parsed.offer_id, parsed.select)
            return

        # generate 阶段
        if parsed.generate:
            _mode_generate(parsed.offer_id)
            return

        # customize 阶段
        if parsed.customize:
            _mode_customize(parsed.offer_id, parsed.customize, no_html=parsed.no_html)
            return

        # 默认进入 prepare 阶段
        _mode_prepare(parsed.offer_id)

    except Exception as e:
        print_error(e)


if __name__ == "__main__":
    main()
