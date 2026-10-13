#!/usr/bin/env python3
"""穿搭笔记素材收集器 — 启动本地 H5 页面供店主选择衣服、填写笔记素材。

自动获取 tmpCode + storeId，拉取店铺衣服列表，
启动一个轻量 HTTP 服务托管 H5 选择页面，
店主选择衣服、上传照片、填写笔记意图后点击「开始生成」，
脚本输出所有选择结果的 JSON 到 stdout 供 AI 后续生成笔记。

用法:
    python style_note_generator.py
    python style_note_generator.py --port 8766
    python style_note_generator.py --corp-id xxx --staff-id yyy
"""

from __future__ import annotations

import argparse
import http.server
import json
import sys
import threading
import webbrowser
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from try_on_cli import (
    TEAMBITION_HOST,
    REQUEST_TIMEOUT,
    REQUEST_HEADERS,
    fetch_user_info_from_dws,
    api_tmp_code,
    api_init,
)

DEFAULT_PORT = 8766

# 用于线程间通信：H5 页面提交的结果
_result_event = threading.Event()
_result_data: dict = {}


def build_html(clothes_json: str) -> str:
    """构建 H5 选择页面的 HTML。"""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI笔记生成 · 素材收集</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #faf9f7; color: #1a1a1a; min-height: 100vh; }}
.container {{ max-width: 480px; margin: 0 auto; padding: 20px 16px 100px; }}
h1 {{ font-size: 22px; font-weight: 700; margin-bottom: 24px; text-align: center; }}
.section {{ background: #fff; border-radius: 16px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
.section-title {{ font-size: 15px; font-weight: 600; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }}
.section-title .num {{ display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 50%; background: linear-gradient(135deg, #e879a8, #d4628a); color: #fff; font-size: 12px; font-weight: 700; }}
.section-desc {{ font-size: 13px; color: #888; margin-bottom: 12px; }}

/* 衣服网格 — 固定3行高度，超出可滚动 */
.clothes-scroll {{ max-height: 390px; overflow-y: auto; -webkit-overflow-scrolling: touch; border-radius: 8px; }}
.clothes-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }}
.clothe-item {{ position: relative; border-radius: 12px; overflow: hidden; cursor: pointer; border: 2px solid transparent; transition: all 0.2s; }}
.clothe-item.selected {{ border-color: #d4628a; }}
.clothe-item.selected::after {{ content: '✓'; position: absolute; top: 6px; right: 6px; width: 22px; height: 22px; background: #d4628a; color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; }}
.clothe-item img {{ width: 100%; aspect-ratio: 1; object-fit: cover; display: block; }}
.clothe-item .name {{ font-size: 11px; padding: 6px 4px; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.clothes-header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }}
.clothes-header .count {{ font-size: 12px; color: #aaa; }}

/* 照片上传区 */
.upload-area {{ border: 2px dashed #ddd; border-radius: 12px; padding: 24px; text-align: center; cursor: pointer; transition: border-color 0.2s; }}
.upload-area:hover {{ border-color: #d4628a; }}
.upload-area .icon {{ font-size: 32px; margin-bottom: 8px; }}
.upload-area .text {{ font-size: 13px; color: #888; }}
.upload-preview {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 12px; }}
.upload-preview .preview-item {{ position: relative; border-radius: 8px; overflow: hidden; }}
.upload-preview .preview-item img {{ width: 100%; aspect-ratio: 1; object-fit: cover; display: block; }}
.upload-preview .preview-item .remove {{ position: absolute; top: 4px; right: 4px; width: 20px; height: 20px; background: rgba(0,0,0,0.5); color: #fff; border: none; border-radius: 50%; cursor: pointer; font-size: 11px; display: flex; align-items: center; justify-content: center; }}

/* 输入框 */
.input-field {{ width: 100%; padding: 12px 14px; border: 1px solid #e5e5e5; border-radius: 10px; font-size: 14px; outline: none; transition: border-color 0.2s; }}
.input-field:focus {{ border-color: #d4628a; }}
textarea.input-field {{ min-height: 80px; resize: vertical; font-family: inherit; }}

/* 目标用户群 */
.audience-options {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.audience-option {{ padding: 8px 16px; border-radius: 20px; border: 1px solid #e5e5e5; font-size: 13px; cursor: pointer; transition: all 0.2s; user-select: none; }}
.audience-option.selected {{ background: linear-gradient(135deg, #e879a8, #d4628a); color: #fff; border-color: #d4628a; }}

/* 提交按钮 */
.submit-btn {{ position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); width: calc(100% - 32px); max-width: 448px; padding: 14px; border: none; border-radius: 12px; background: linear-gradient(135deg, #e879a8, #d4628a); color: #fff; font-size: 16px; font-weight: 600; cursor: pointer; transition: opacity 0.2s; box-shadow: 0 4px 12px rgba(212,98,138,0.3); }}
.submit-btn:hover {{ opacity: 0.9; }}
.submit-btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}

/* 完成提示 */
.done-overlay {{ position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }}
.done-card {{ background: #fff; border-radius: 20px; padding: 40px 32px; text-align: center; max-width: 320px; }}
.done-card .icon {{ font-size: 48px; margin-bottom: 16px; }}
.done-card .title {{ font-size: 18px; font-weight: 600; margin-bottom: 8px; }}
.done-card .desc {{ font-size: 14px; color: #888; }}
</style>
</head>
<body>
<div class="container">
  <h1>📝 AI笔记生成</h1>

  <!-- ① 上传实拍穿搭照片 -->
  <div class="section">
    <div class="section-title"><span class="num">1</span>上传实拍穿搭照片（1-6张）</div>
    <div class="section-desc">支持上传实拍照片，或从下方衣服库选择</div>
    <div class="upload-area" id="uploadArea" onclick="document.getElementById('fileInput').click()">
      <div class="icon">📷</div>
      <div class="text">点击上传照片</div>
    </div>
    <input type="file" id="fileInput" accept="image/*" multiple style="display:none" onchange="handleFileUpload(event)">
    <div class="upload-preview" id="uploadPreview"></div>

    <div class="clothes-header" style="margin-top:16px;">
      <div class="section-desc" style="margin-bottom:0;">从衣服库选择：</div>
      <div class="count" id="clothesCount"></div>
    </div>
    <div class="clothes-scroll">
      <div class="clothes-grid" id="clothesGrid"></div>
    </div>
  </div>

  <!-- ② 笔记意图 -->
  <div class="section">
    <div class="section-title"><span class="num">2</span>笔记意图</div>
    <input type="text" class="input-field" id="noteIntent" placeholder="例如：夏日感碎片、职场通勤、周末约会、优雅气质...">
  </div>

  <!-- ③ 关联商品 -->
  <div class="section">
    <div class="section-title"><span class="num">3</span>关联商品（可选）</div>
    <div class="section-desc">已选择的衣服将自动关联为笔记商品</div>
    <div id="selectedProducts" style="font-size:13px;color:#666;"></div>
  </div>

  <!-- ④ 目标用户群 -->
  <div class="section">
    <div class="section-title"><span class="num">4</span>目标用户群（可选）</div>
    <div class="audience-options" id="audienceOptions">
      <div class="audience-option selected" data-value="全体用户" onclick="selectAudience(this)">全体用户</div>
      <div class="audience-option" data-value="温柔甜美风" onclick="selectAudience(this)">温柔甜美风</div>
      <div class="audience-option" data-value="职场干练风" onclick="selectAudience(this)">职场干练风</div>
      <div class="audience-option" data-value="休闲街头风" onclick="selectAudience(this)">休闲街头风</div>
      <div class="audience-option" data-value="优雅气质风" onclick="selectAudience(this)">优雅气质风</div>
    </div>
  </div>
</div>

<button class="submit-btn" id="submitBtn" onclick="handleSubmit()">开始生成</button>

<div class="done-overlay" id="doneOverlay" style="display:none;">
  <div class="done-card">
    <div class="icon">✅</div>
    <div class="title">素材收集完成</div>
    <div class="desc">请返回 QoderWork 查看执行情况</div>
  </div>
</div>

<script>
const allClothes = {clothes_json};
let selectedClotheIds = new Set();
let uploadedPhotos = []; // {{ name, dataUrl }}
let selectedAudience = '全体用户';
// 渲染衣服网格
function renderClothesGrid() {{
  const grid = document.getElementById('clothesGrid');
  const countEl = document.getElementById('clothesCount');

  countEl.textContent = `共 ${{allClothes.length}} 件${{selectedClotheIds.size > 0 ? '，已选 ' + selectedClotheIds.size + ' 件' : ''}}`;

  grid.innerHTML = allClothes.map(c => `
    <div class="clothe-item ${{selectedClotheIds.has(c.id) ? 'selected' : ''}}"
         onclick="toggleClothe('${{c.id}}')"
         data-id="${{c.id}}">
      <img src="${{c.imageUrl}}" alt="${{c.name}}" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22><rect fill=%22%23f0f0f0%22 width=%22100%22 height=%22100%22/><text x=%2250%22 y=%2250%22 text-anchor=%22middle%22 dy=%22.3em%22 fill=%22%23ccc%22 font-size=%2214%22>无图</text></svg>'">
      <div class="name">${{c.name}}</div>
    </div>
  `).join('');

  updateSelectedProducts();
}}

function toggleClothe(id) {{
  if (selectedClotheIds.has(id)) {{
    selectedClotheIds.delete(id);
  }} else {{
    selectedClotheIds.add(id);
  }}
  renderClothesGrid();
}}

function updateSelectedProducts() {{
  const el = document.getElementById('selectedProducts');
  const selected = allClothes.filter(c => selectedClotheIds.has(c.id));
  if (selected.length === 0) {{
    el.textContent = '暂未选择商品';
  }} else {{
    el.textContent = '已选：' + selected.map(c => c.name).join('、');
  }}
}}

// 照片上传
function handleFileUpload(event) {{
  const files = Array.from(event.target.files);
  const remaining = 6 - uploadedPhotos.length;
  const toAdd = files.slice(0, remaining);
  toAdd.forEach(file => {{
    const reader = new FileReader();
    reader.onload = function(e) {{
      uploadedPhotos.push({{ name: file.name, dataUrl: e.target.result }});
      renderUploadPreview();
    }};
    reader.readAsDataURL(file);
  }});
  event.target.value = '';
}}

function removePhoto(index) {{
  uploadedPhotos.splice(index, 1);
  renderUploadPreview();
}}

function renderUploadPreview() {{
  const preview = document.getElementById('uploadPreview');
  const area = document.getElementById('uploadArea');
  if (uploadedPhotos.length > 0) {{
    area.style.display = 'none';
    preview.innerHTML = uploadedPhotos.map((p, i) => `
      <div class="preview-item">
        <img src="${{p.dataUrl}}" alt="">
        <button class="remove" onclick="removePhoto(${{i}})">×</button>
      </div>
    `).join('') + (uploadedPhotos.length < 6 ? `
      <div class="preview-item" style="display:flex;align-items:center;justify-content:center;background:#f5f5f5;border-radius:8px;aspect-ratio:1;cursor:pointer;" onclick="document.getElementById('fileInput').click()">
        <span style="font-size:24px;color:#ccc;">+</span>
      </div>
    ` : '');
  }} else {{
    area.style.display = 'block';
    preview.innerHTML = '';
  }}
}}

// 目标用户群
function selectAudience(el) {{
  document.querySelectorAll('.audience-option').forEach(o => o.classList.remove('selected'));
  el.classList.add('selected');
  selectedAudience = el.dataset.value;
}}

// 提交
async function handleSubmit() {{
  const noteIntent = document.getElementById('noteIntent').value.trim();
  if (!noteIntent && selectedClotheIds.size === 0 && uploadedPhotos.length === 0) {{
    alert('请至少填写笔记意图或选择衣服/上传照片');
    return;
  }}

  const btn = document.getElementById('submitBtn');
  btn.disabled = true;
  btn.textContent = '提交中...';

  const selectedClothes = allClothes.filter(c => selectedClotheIds.has(c.id));

  const payload = {{
    noteIntent: noteIntent,
    targetAudience: selectedAudience,
    selectedClothes: selectedClothes,
    uploadedPhotoCount: uploadedPhotos.length,
    uploadedPhotoDataUrls: uploadedPhotos.map(p => p.dataUrl),
  }};

  try {{
    const response = await fetch('/submit', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify(payload),
    }});
    if (response.ok) {{
      document.getElementById('doneOverlay').style.display = 'flex';
      setTimeout(() => window.close(), 2000);
    }} else {{
      alert('提交失败，请重试');
      btn.disabled = false;
      btn.textContent = '开始生成';
    }}
  }} catch (err) {{
    alert('网络错误：' + err.message);
    btn.disabled = false;
    btn.textContent = '开始生成';
  }}
}}

// 初始化
renderClothesGrid();
</script>
</body>
</html>"""


class NoteGeneratorHandler(http.server.BaseHTTPRequestHandler):
    """处理 H5 页面请求和表单提交。"""

    page_bytes: bytes = b""
    clothes_list: list = []

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(self.page_bytes)))
        self.end_headers()
        self.wfile.write(self.page_bytes)

    def do_POST(self):
        global _result_data
        if self.path == "/submit":
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            try:
                _result_data = json.loads(raw_body)
            except json.JSONDecodeError:
                _result_data = {}

            self._send_json(200, {"success": True})
            _result_event.set()
        else:
            self._send_json(404, {"success": False, "error": "未知路径"})

    def _send_json(self, status_code: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def fetch_clothes_list(tmp_token: str) -> list:
    """通过 API 拉取店铺衣服列表。"""
    url = f"{TEAMBITION_HOST}/api/opt/dress-mirror/clothes/list"
    try:
        response = httpx.post(
            url,
            json={"storeId": tmp_token},
            headers=REQUEST_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        data = response.json()
        if data.get("success") and data.get("result"):
            return data["result"]
    except Exception as error:
        print(f"⚠️  拉取衣服列表失败: {error}", file=sys.stderr, flush=True)
    return []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="style_note_generator.py",
        description="AI笔记生成 · 素材收集器 — 唤起浏览器选择衣服和填写笔记素材",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"本地 HTTP 服务端口（默认 {DEFAULT_PORT}）")
    parser.add_argument("--corp-id", required=False, dest="corp_id", default="",
                        help="企业 corpId（可选，自动获取）")
    parser.add_argument("--staff-id", required=False, dest="staff_id", default="",
                        help="员工 userId/staffId（可选，自动获取）")
    parser.add_argument("--tmp-code", required=False, dest="tmp_code", default="",
                        help="已有的 tmpCode（可选，自动获取）")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # 获取用户信息 + tmpCode
    if args.tmp_code and args.corp_id:
        corp_id = args.corp_id
        tmp_code = args.tmp_code
    else:
        print("🔑 正在获取用户信息和鉴权码...", file=sys.stderr, flush=True)
        user_info = fetch_user_info_from_dws()
        corp_id = args.corp_id or user_info["corpId"]
        tmp_code = args.tmp_code or api_tmp_code(
            corp_id=corp_id,
            staff_id=args.staff_id or user_info["staffId"],
            org_user_name=user_info.get("orgUserName", ""),
            org_user_mobile=user_info.get("orgUserMobile", ""),
            org_name=user_info.get("orgName", ""),
        )
        print("✅ 鉴权码获取成功", file=sys.stderr, flush=True)

    # 获取 storeId
    print("📦 正在初始化试衣间...", file=sys.stderr, flush=True)
    tmp_token = api_init(corp_id=corp_id, tmp_code=tmp_code)
    print("✅ 试衣间初始化完成", file=sys.stderr, flush=True)

    # 拉取衣服列表
    print("👗 正在拉取衣服列表...", file=sys.stderr, flush=True)
    clothes = fetch_clothes_list(tmp_token)
    print(f"✅ 获取到 {len(clothes)} 件衣服", file=sys.stderr, flush=True)

    # 构建 H5 页面
    clothes_json_str = json.dumps(clothes, ensure_ascii=False)
    page_html = build_html(clothes_json_str)
    page_bytes = page_html.encode("utf-8")

    NoteGeneratorHandler.page_bytes = page_bytes
    NoteGeneratorHandler.clothes_list = clothes

    port = args.port
    server = http.server.HTTPServer(("127.0.0.1", port), NoteGeneratorHandler)

    url = f"http://127.0.0.1:{port}"
    print(f"📝 笔记素材收集页面已启动: {url}", file=sys.stderr, flush=True)

    # 在后台线程运行服务
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    # 打开浏览器
    webbrowser.open(url)

    print("⏳ 等待店主完成素材选择...", file=sys.stderr, flush=True)

    # 等待用户提交（阻塞）
    _result_event.wait()

    # 关闭服务
    server.shutdown()

    # 构建输出结果
    selected_clothes = _result_data.get("selectedClothes", [])
    uploaded_photos = _result_data.get("uploadedPhotoDataUrls", [])

    # 收集所有图片 URL（衣服库图片 + 上传照片）
    all_images = []
    for clothe in selected_clothes:
        image_url = clothe.get("imageUrl", "")
        if image_url:
            all_images.append(image_url)
    # 上传照片的 dataUrl 也加入（AI 将用这些照片生成笔记）
    for data_url in uploaded_photos:
        all_images.append(data_url)

    output = {
        "success": True,
        "noteIntent": _result_data.get("noteIntent", ""),
        "targetAudience": _result_data.get("targetAudience", "全体用户"),
        "selectedClothes": selected_clothes,
        "images": all_images,
        "productIds": [c.get("id", "") for c in selected_clothes if c.get("id")],
        "corpId": corp_id,
        "tmpCode": tmp_code,
    }

    # 输出 JSON 到 stdout
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
