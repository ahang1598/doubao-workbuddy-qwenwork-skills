"""embed-images 命令 —— 将 HTML 中所有网络图片下载并转为 base64 内嵌。

解决 OSS 签名链接过期导致报告图片失效的问题。

两种工作模式：
1. **直接下载模式**（默认）：用 urllib 直接下载 img src 中的 URL。
   适用于公网可达的图片链接。
2. **DWS 附件模式**（传入 --base-id + --table-id + --skill-cli）：
   通过主技能 ``attachment get-urls`` 获取带鲜活签名的下载 URL，
   以 resourceId 作为匹配键替换 HTML 中对应的图片。
   适用于钉钉 AI 表格附件（OSS 签名链接 403 场景）。

零外部依赖，仅使用 Python 标准库。
"""

import base64
import json
import mimetypes
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Dict, List


# 匹配 <img ... src="https://..." ... > 中的 src 属性
_IMG_SRC_RE = re.compile(
    r'(<img\b[^>]*?\bsrc\s*=\s*")' r'(https?://[^"]+)' r'("[^>]*?>)',
    re.IGNORECASE | re.DOTALL,
)

# 从 OSS URL 路径中提取 resourceId（UUID 格式）
_RESOURCE_ID_RE = re.compile(r'/img/([a-f0-9-]{36})\.')


# 匹配已内嵌的 base64 图片 data URI（用于后置校验时提取）
_BASE64_IMG_RE = re.compile(
    r'(<img\b[^>]*?\bsrc\s*=\s*")'
    r'(data:image/[^;]+;base64,[A-Za-z0-9+/=]+)'
    r'("[^>]*?>)',
    re.IGNORECASE | re.DOTALL,
)


# ============================================================
# 通用工具
# ============================================================

def _estimate_text_size_kb(html_text: str) -> float:
    """估算 HTML 中非图片部分的实际大小（KB）。

    将所有 <img src="https://..."> 替换为空占位符后测量剩余大小。
    这能准确反映文字、CSS、HTML 标签的真实开销。
    """
    # 把所有网络图片 URL 替换为短占位符
    stripped = _IMG_SRC_RE.sub(r'\1__PLACEHOLDER__\3', html_text)
    # 也去掉可能已经存在的 base64 图片
    stripped = _BASE64_IMG_RE.sub(r'\1__PLACEHOLDER__\3', stripped)
    return len(stripped.encode("utf-8")) / 1024


def _guess_mime(url: str, content_type: str = "") -> str:
    """根据 URL 后缀或 Content-Type 推断 MIME 类型。"""
    if content_type and "/" in content_type:
        return content_type.split(";")[0].strip()
    path = url.split("?")[0]
    mime, _ = mimetypes.guess_type(path)
    if mime:
        return mime
    lower = path.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".gif"):
        return "image/gif"
    if lower.endswith(".webp"):
        return "image/webp"
    return "image/jpeg"


def _extract_resource_id(url: str) -> str:
    """从 OSS URL 中提取 resourceId（UUID）。

    示例 URL: https://alidocs2.oss.../img/927838c9-34af-4278-863d-0f32279bf5c6.jpg?...
    返回: 927838c9-34af-4278-863d-0f32279bf5c6
    """
    match = _RESOURCE_ID_RE.search(url)
    return match.group(1) if match else ""


def _download_url(url: str) -> bytes:
    """使用 curl 下载 URL 内容（比 urllib 更可靠，支持重定向）。"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            ["curl", "-sL", "--max-time", "30", "-o", tmp_path, url],
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"curl 退出码 {result.returncode}")
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _encode_to_data_uri(image_data: bytes, url: str) -> str:
    """将二进制图片数据编码为 data URI。"""
    mime = _guess_mime(url)
    b64 = base64.b64encode(image_data).decode("ascii")
    return f"data:{mime};base64,{b64}"


# ============================================================
# 模式 1：直接下载
# ============================================================

def _download_and_encode(url: str, index: int) -> str:
    """直接下载图片并返回 base64 data URI。失败返回原始 URL。"""
    try:
        data = _download_url(url)
        if len(data) < 100:
            raise RuntimeError("文件过小，可能下载失败")
        mime = _guess_mime(url)
        b64 = base64.b64encode(data).decode("ascii")
        size_kb = len(data) / 1024
        print(f"  ✅ [{index}] {size_kb:.0f} KB ({mime})")
        return f"data:{mime};base64,{b64}"
    except Exception as exc:
        print(f"  ⚠️ [{index}] 下载失败，保留原始 URL: {exc}")
        return url


def _embed_direct(html_text: str, compress_opts: dict = None) -> str:
    """直接下载模式：逐个下载 HTML 中的网络图片并转 base64，支持智能压缩。

    Args:
        html_text: 原始 HTML 文本
        compress_opts: 压缩配置字典，None 表示不压缩（原图嵌入）。
    """
    matches = list(_IMG_SRC_RE.finditer(html_text))
    if not matches:
        print("  ℹ️ 未找到网络图片，无需转换")
        return html_text

    print(f"  📸 找到 {len(matches)} 张网络图片，开始下载...")

    # 先下载所有图片
    raw_images: Dict[str, bytes] = {}  # index_key → image_data
    match_to_key: Dict[int, str] = {}  # match_start → index_key
    for idx, match in enumerate(matches, 1):
        url = match.group(2)
        try:
            data = _download_url(url)
            if len(data) < 100:
                print(f"  ⚠️ [{idx}] 文件过小 ({len(data)} bytes)，跳过")
                continue
            key = f"direct_{idx}"
            raw_images[key] = data
            match_to_key[match.start()] = key
            size_kb = len(data) / 1024
            print(f"  ✅ [{idx}] {size_kb:.0f} KB ({_guess_mime(url)})")
        except Exception as exc:
            print(f"  ⚠️ [{idx}] 下载失败，保留原始 URL: {exc}")

    if not raw_images:
        print("  ⚠️ 所有图片下载失败，返回原始 HTML")
        return html_text

    # 智能压缩
    key_to_b64: Dict[str, str] = {}
    if compress_opts and raw_images:
        actual_text_kb = _estimate_text_size_kb(html_text)
        effective_buffer_kb = max(
            compress_opts["text_buffer_kb"],
            actual_text_kb * 1.1,
        )
        print(f"\n  📊 开始智能压缩 {len(raw_images)} 张图片...")
        print(f"     文字缓冲: 实测 {actual_text_kb:.0f} KB → 生效 {effective_buffer_kb:.0f} KB")

        from commands.compress_images import smart_compress

        targets = smart_compress(
            images=raw_images,
            total_budget_kb=compress_opts["target_size_kb"],
            text_buffer_kb=effective_buffer_kb,
            min_quality=compress_opts["min_quality"],
            max_quality=compress_opts["max_quality"],
            prevent_enlargement=compress_opts["prevent_enlargement"],
        )
        for target in targets:
            data_uri = _encode_to_data_uri(target.compressed_data, f"img/{target.resource_id}.jpg")
            key_to_b64[target.resource_id] = data_uri
            if target.quality == -1:
                print(f"    • [{target.resource_id}] {target.original_size_kb:.0f} KB → 保持原大小")
            else:
                print(
                    f"    • [{target.resource_id}] {target.original_size_kb:.0f} KB "
                    f"→ {target.compressed_size_kb:.0f} KB (q={target.quality})"
                )

        total_orig = sum(t.original_size_kb for t in targets)
        total_comp = sum(t.compressed_size_kb for t in targets)
        if total_orig > 0:
            print(f"\n  压缩统计: {total_orig:.0f} KB → {total_comp:.0f} KB "
                  f"(节省 {(1 - total_comp / total_orig) * 100:.1f}%)")
    else:
        # 不压缩，直接编码
        for key, data in raw_images.items():
            key_to_b64[key] = _encode_to_data_uri(data, f"img/{key}.jpg")

    # 替换 HTML 中的图片 URL
    result = html_text
    replaced = 0
    for match in reversed(matches):
        key = match_to_key.get(match.start())
        if key and key in key_to_b64:
            replacement = match.group(1) + key_to_b64[key] + match.group(3)
            result = result[:match.start()] + replacement + result[match.end():]
            replaced += 1

    print(f"  ✅ 已替换 {replaced}/{len(matches)} 张图片")
    return result


# ============================================================
# 模式 2：DWS 附件模式（resourceId 匹配）
# ============================================================

def _get_attachment_field_ids(fields_file: str) -> List[str]:
    """从字段定义 JSON 中提取所有 attachment 类型字段的 fieldId。"""
    resolved = os.path.expanduser(fields_file)
    try:
        with open(resolved, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception as exc:
        print(f"  ⚠️ 无法读取字段定义文件: {exc}")
        return []

    # 兼容多种格式
    if isinstance(data, dict):
        inner = data.get("data", data) if "data" in data else data
        if "tables" in inner and isinstance(inner["tables"], list) and inner["tables"]:
            inner = inner["tables"][0]
        field_list = inner.get("items", inner.get("fields", []))
    elif isinstance(data, list):
        field_list = data
    else:
        return []

    attachment_ids = []
    for field_def in field_list:
        field_type = field_def.get("type") or field_def.get("fieldType", "")
        # attachment 类型：AI 表格中 type=17 或 type 字符串包含 "attachment"
        if field_type == 17 or str(field_type).lower() == "attachment":
            fid = field_def.get("fieldId") or field_def.get("id", "")
            if fid:
                attachment_ids.append(fid)

    return attachment_ids


def _fetch_fresh_urls_via_dws(
    skill_cli: str, base_id: str, table_id: str, field_ids: List[str]
) -> Dict[str, str]:
    """通过主技能 attachment get-urls 获取所有附件的鲜活 URL。

    Returns:
        resourceId → 鲜活下载 URL 的映射表。
    """
    resource_map: Dict[str, str] = {}

    for field_id in field_ids:
        print(f"  🔗 获取字段 {field_id} 的附件 URL...")
        cmd = [
            sys.executable, os.path.expanduser(skill_cli),
            "attachment", "get-urls",
            "--base-id", base_id,
            "--table-id", table_id,
            "--field-id", field_id,
            "--url-only",
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                print(f"    ⚠️ 命令失败: {result.stderr.strip()[:100]}")
                continue
            urls = [
                line.strip()
                for line in result.stdout.strip().split("\n")
                if line.strip() and line.strip().startswith("http")
            ]
            for url in urls:
                res_id = _extract_resource_id(url)
                if res_id:
                    resource_map[res_id] = url
            print(f"    找到 {len(urls)} 个附件")
        except Exception as exc:
            print(f"    ⚠️ 执行异常: {exc}")

    return resource_map


def _embed_via_dws(
    html_text: str,
    skill_cli: str,
    base_id: str,
    table_id: str,
    fields_file: str,
    compress_opts: dict = None,
) -> str:
    """DWS 附件模式：通过 resourceId 匹配并替换图片。

    Args:
        compress_opts: 压缩配置字典，None 表示不压缩。
            键: target_size_kb, text_buffer_kb, min_quality, max_quality, prevent_enlargement
    """
    # 1. 提取 HTML 中所有图片 URL 及其 resourceId
    matches = list(_IMG_SRC_RE.finditer(html_text))
    if not matches:
        print("  ℹ️ 未找到网络图片，无需转换")
        return html_text

    print(f"  📸 找到 {len(matches)} 张网络图片")

    # 提取 HTML 中图片的 resourceId
    html_resource_ids = set()
    for match in matches:
        url = match.group(2)
        # 处理 HTML 实体编码：&amp; → &
        decoded_url = url.replace("&amp;", "&")
        res_id = _extract_resource_id(decoded_url)
        if res_id:
            html_resource_ids.add(res_id)

    if not html_resource_ids:
        print("  ⚠️ 无法从图片 URL 中提取 resourceId，回退到直接下载模式")
        return _embed_direct(html_text, compress_opts=compress_opts)

    print(f"  🔑 提取到 {len(html_resource_ids)} 个唯一 resourceId")

    # 2. 获取附件字段 ID 列表
    if fields_file:
        field_ids = _get_attachment_field_ids(fields_file)
        if not field_ids:
            print("  ⚠️ 未找到 attachment 类型字段，尝试全表查询")
            field_ids = []
    else:
        field_ids = []

    # 3. 通过主技能获取鲜活 URL
    if field_ids:
        fresh_urls = _fetch_fresh_urls_via_dws(skill_cli, base_id, table_id, field_ids)
    else:
        # 如果没有字段定义，尝试用 record query 直接获取
        fresh_urls = {}
        print("  ⚠️ 无附件字段 ID，无法获取鲜活 URL，回退到直接下载模式")
        return _embed_direct(html_text, compress_opts=compress_opts)

    if not fresh_urls:
        print("  ⚠️ 未获取到任何鲜活 URL，回退到直接下载模式")
        return _embed_direct(html_text, compress_opts=compress_opts)

    print(f"  🔗 获取到 {len(fresh_urls)} 个鲜活 URL")

    # 4. 下载图片
    raw_images: Dict[str, bytes] = {}
    resource_to_b64: Dict[str, str] = {}
    total = len(fresh_urls)
    for idx, (res_id, url) in enumerate(fresh_urls.items(), 1):
        if res_id not in html_resource_ids:
            continue  # 跳过 HTML 中不需要的图片
        print(f"  [{idx}/{total}] 下载 resourceId={res_id[:12]}...")
        try:
            data = _download_url(url)
            if len(data) < 100:
                print(f"    ⚠️ 文件过小 ({len(data)} bytes)，跳过")
                continue
            raw_images[res_id] = data
            size_kb = len(data) / 1024
            print(f"    ✅ {size_kb:.0f} KB")
        except Exception as exc:
            print(f"    ⚠️ 下载失败: {exc}")

    print(f"  📦 成功下载 {len(raw_images)}/{len(html_resource_ids)} 张图片")

    # 5. 智能压缩（可选）
    if compress_opts and raw_images:
        # 动态计算文字缓冲：用实际 HTML 非图片部分的大小，而非静态估算
        actual_text_kb = _estimate_text_size_kb(html_text)
        # 取 CLI 传入值和实际值中较大的那个，并额外加 10% 安全余量
        effective_buffer_kb = max(
            compress_opts["text_buffer_kb"],
            actual_text_kb * 1.1,
        )
        print(f"\n  📊 开始智能压缩 {len(raw_images)} 张图片...")
        print(f"     文字缓冲: 实测 {actual_text_kb:.0f} KB → 生效 {effective_buffer_kb:.0f} KB")

        from commands.compress_images import smart_compress

        targets = smart_compress(
            images=raw_images,
            total_budget_kb=compress_opts["target_size_kb"],
            text_buffer_kb=effective_buffer_kb,
            min_quality=compress_opts["min_quality"],
            max_quality=compress_opts["max_quality"],
            prevent_enlargement=compress_opts["prevent_enlargement"],
        )
        for t in targets:
            data_uri = _encode_to_data_uri(t.compressed_data, f"img/{t.resource_id}.jpg")
            resource_to_b64[t.resource_id] = data_uri
            if t.quality == -1:
                print(f"    • [{t.resource_id[:12]}] {t.original_size_kb:.0f} KB → 保持原大小")
            else:
                print(
                    f"    • [{t.resource_id[:12]}] {t.original_size_kb:.0f} KB "
                    f"→ {t.compressed_size_kb:.0f} KB (q={t.quality})"
                )

        total_orig = sum(t.original_size_kb for t in targets)
        total_comp = sum(t.compressed_size_kb for t in targets)
        print(f"\n  压缩统计: {total_orig:.0f} KB → {total_comp:.0f} KB "
              f"(节省 {(1 - total_comp / total_orig) * 100:.1f}%)")
    else:
        # 不压缩，直接编码
        for res_id, data in raw_images.items():
            resource_to_b64[res_id] = _encode_to_data_uri(data, f"img/{res_id}.jpg")

    # 6. 替换 HTML 中的图片 URL
    result = html_text
    replaced = 0
    for match in reversed(matches):
        url = match.group(2)
        decoded_url = url.replace("&amp;", "&")
        res_id = _extract_resource_id(decoded_url)
        if res_id and res_id in resource_to_b64:
            replacement = match.group(1) + resource_to_b64[res_id] + match.group(3)
            result = result[:match.start()] + replacement + result[match.end():]
            replaced += 1

    print(f"  ✅ 已替换 {replaced} 张图片")
    return result


# ============================================================
# CLI 入口
# ============================================================

def run(args) -> None:
    """执行 embed-images 命令。"""
    html_path = Path(os.path.expanduser(args.input)).resolve()
    if not html_path.exists():
        print(f"❌ HTML 文件不存在: {html_path}")
        sys.exit(1)

    output_path = (
        Path(os.path.expanduser(args.output)).resolve()
        if args.output
        else html_path
    )

    print(f"📸 正在内嵌图片: {html_path.name}")
    html_text = html_path.read_text(encoding="utf-8")

    # ── 前置检查：HTML 中是否有网络图片 ──
    network_images = _IMG_SRC_RE.findall(html_text)
    if not network_images:
        print("  ✅ HTML 中未检测到网络图片（<img src=\"https://...\">），无需执行嵌入和压缩")
        # 仍然写出文件（保持 output 参数语义一致）
        if output_path != html_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(html_text, encoding="utf-8")
            print(f"  📄 已复制到: {output_path}")
        size_kb = html_path.stat().st_size / 1024
        print(f"   文件大小: {size_kb:.1f} KB ({size_kb / 1024:.2f} MB)")
        return

    # 构建压缩配置（默认启用，--no-compress 可关闭）
    compress_opts = None
    should_compress = not getattr(args, "no_compress", False)
    if should_compress:
        target_mb = getattr(args, "target_size_mb", 1.9)
        compress_opts = {
            "target_size_kb": target_mb * 1024,
            "text_buffer_kb": getattr(args, "text_buffer_kb", 400.0),
            "min_quality": getattr(args, "min_quality", 30),
            "max_quality": getattr(args, "max_quality", 95),
            "prevent_enlargement": not getattr(args, "no_prevent_enlargement", False),
        }
        print(f"  📦 智能压缩已启用 (目标: ≤{target_mb} MB)")
    else:
        print(f"  ℹ️ 压缩已关闭（--no-compress），图片将以原始大小嵌入")

    # 判断使用哪种模式
    base_id = getattr(args, "base_id", None)
    table_id = getattr(args, "table_id", None)
    skill_cli = getattr(args, "skill_cli", None)
    fields_file = getattr(args, "fields", None)

    if base_id and table_id and skill_cli:
        print(f"  🔧 模式: DWS 附件（通过主技能获取鲜活 URL + resourceId 匹配）")
        result = _embed_via_dws(
            html_text, skill_cli, base_id, table_id, fields_file or "",
            compress_opts=compress_opts,
        )
    else:
        print(f"  🔧 模式: 直接下载")
        result = _embed_direct(html_text, compress_opts=compress_opts)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result, encoding="utf-8")

    size_kb = output_path.stat().st_size / 1024
    print(f"✅ 完成: {output_path}")
    print(f"   文件大小: {size_kb:.1f} KB ({size_kb / 1024:.2f} MB)")

    # ── 后置闭环校验：最终 HTML 文件超标则自动重试 ──
    if compress_opts:
        threshold_kb = compress_opts["target_size_kb"]
        max_post_retries = 3
        retry = 0
        while size_kb > threshold_kb and retry < max_post_retries:
            retry += 1
            overshoot_kb = size_kb - threshold_kb
            print(f"\n  ⚠️ 文件 {size_kb / 1024:.2f} MB 超出目标 "
                  f"{threshold_kb / 1024:.1f} MB（差 {overshoot_kb:.0f} KB），"
                  f"后置校验重试 [{retry}/{max_post_retries}]")

            # 从最终 HTML 中提取所有 base64 图片，重新压缩
            from commands.compress_images import smart_compress
            b64_matches = list(_BASE64_IMG_RE.finditer(result))
            if not b64_matches:
                print("    无 base64 图片可重压，终止重试")
                break

            # 解码 base64 图片为原始数据
            retry_images: Dict[str, bytes] = {}
            for idx, m in enumerate(b64_matches):
                data_uri = m.group(2)
                # 提取 base64 部分
                b64_part = data_uri.split(",", 1)[1] if "," in data_uri else ""
                if b64_part:
                    retry_images[f"retry_{idx}"] = base64.b64decode(b64_part)

            if not retry_images:
                break

            # 用实际文字大小计算图片可用预算
            actual_text_kb = _estimate_text_size_kb(result)
            # base64 编码会增加约 33% 体积，预算需要反向折算
            b64_overhead_factor = 1.33
            available_for_images_kb = (threshold_kb / b64_overhead_factor) - actual_text_kb
            # 确保预算始终为正数，每张图片至少 10 KB
            min_budget_kb = len(retry_images) * 10
            shrink_budget_kb = max(available_for_images_kb, min_budget_kb)
            effective_buffer = actual_text_kb * 1.15  # 15% 余量

            print(f"    重压预算: {shrink_budget_kb:.0f} KB, "
                  f"文字缓冲: {effective_buffer:.0f} KB, "
                  f"图片: {len(retry_images)} 张")

            targets = smart_compress(
                images=retry_images,
                total_budget_kb=shrink_budget_kb,
                text_buffer_kb=effective_buffer,
                min_quality=max(20, compress_opts["min_quality"] - retry * 5),
                max_quality=max(50, compress_opts["max_quality"] - retry * 15),
                prevent_enlargement=compress_opts["prevent_enlargement"],
            )

            # 重建 base64 映射并替换
            new_b64: Dict[str, str] = {}
            for t in targets:
                mime = "image/jpeg"
                b64_str = base64.b64encode(t.compressed_data).decode("ascii")
                new_b64[t.resource_id] = f"data:{mime};base64,{b64_str}"

            # 逆序替换
            result_tmp = result
            for idx, m in enumerate(reversed(b64_matches)):
                key = f"retry_{len(b64_matches) - 1 - idx}"
                if key in new_b64:
                    replacement = m.group(1) + new_b64[key] + m.group(3)
                    result_tmp = result_tmp[:m.start()] + replacement + result_tmp[m.end():]

            result = result_tmp
            output_path.write_text(result, encoding="utf-8")
            size_kb = output_path.stat().st_size / 1024
            print(f"    重试后: {size_kb:.1f} KB ({size_kb / 1024:.2f} MB)")

        if size_kb <= threshold_kb:
            print(f"   ✅ 在移动端安全阈值内 (≤ {threshold_kb / 1024:.1f} MB)")
        else:
            print(f"   ⚠️ 仍超出目标阈值 ({size_kb / 1024:.2f} > {threshold_kb / 1024:.1f} MB)，"
                  f"建议手动降低 --target-size-mb 或减少图片数量")


def register(subparsers) -> None:
    """注册 embed-images 子命令。"""
    parser = subparsers.add_parser(
        "embed-images",
        help="将 HTML 报告中的网络图片下载并转为 base64 内嵌（防止 OSS 链接过期，支持智能压缩）",
    )
    parser.add_argument("--input", "-i", required=True, help="HTML 文件路径")
    parser.add_argument(
        "--output", "-o", default=None,
        help="输出路径（默认覆盖原文件）",
    )
    # DWS 附件模式参数（三个都传才启用）
    parser.add_argument(
        "--base-id", default=None,
        help="AI 表格 Base ID（启用 DWS 附件模式，解决 OSS 签名 403 问题）",
    )
    parser.add_argument(
        "--table-id", default=None,
        help="数据表 ID（与 --base-id 配合使用）",
    )
    parser.add_argument(
        "--skill-cli", default=None,
        help="主技能 CLI 脚本路径（如 ~/.qoderwork/skills/store-inspection/scripts/cli.py），"
             "用于调用 attachment get-urls 获取鲜活签名 URL",
    )
    parser.add_argument(
        "--fields", "-f", default=None,
        help="字段定义 JSON 文件路径（用于自动识别 attachment 类型字段）",
    )
    # 智能压缩参数
    compress_group = parser.add_argument_group("智能压缩（解决钉钉移动端 2MB 渲染阈值）")
    compress_group.add_argument(
        "--no-compress", action="store_true", default=False,
        help="关闭智能压缩（默认启用压缩，使用此选项可保留原始图片大小）",
    )
    compress_group.add_argument(
        "--compress", action="store_true", default=False,
        help="(已废弃，向后兼容) 压缩现已默认启用，无需显式传入此参数",
    )
    compress_group.add_argument(
        "--target-size-mb", type=float, default=1.9,
        help="目标文件总大小 (MB)，默认 1.9（移动端安全阈值）",
    )
    compress_group.add_argument(
        "--text-buffer-kb", type=float, default=400.0,
        help="预留文字+CSS空间 (KB)，默认 400",
    )
    compress_group.add_argument(
        "--min-quality", type=int, default=30,
        help="最低 JPEG 质量参数，默认 30",
    )
    compress_group.add_argument(
        "--max-quality", type=int, default=95,
        help="最高 JPEG 质量参数，默认 95",
    )
    compress_group.add_argument(
        "--no-prevent-enlargement", action="store_true", default=False,
        help="允许压缩后变大（默认禁止）",
    )
    parser.set_defaults(handler=run)
