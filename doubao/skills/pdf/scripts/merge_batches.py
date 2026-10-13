#!/usr/bin/env python3
"""按 section-safe 语义合并多个 batch DOCX 为一个整体 DOCX。

## 设计动机

评测报告显示 4/15 case 因 docxcompose 类第三方库在合并时 flatten sectPr，
导致跨 batch 的页面方向 / 页边距 / 页眉页脚全部丢失（case 2/3/9/14）。
本脚本走 low-level OPC 操作：
  1. 把 base 当前 body 尾部 sectPr 转成"段落级 sectPr"（塞入新段落的 pPr），
     从而在合并处形成 section 边界，保留 batch1 的 orientation/margin/header/footer；
  2. 追加 batch 的 body 内容；
  3. batch 尾部的 sectPr 成为新的 base 尾部 sectPr，作为最后一个 section 的定义。
media（图片）/ header / footer 等 part 按 batch index 加前缀重命名，rId 全局重映射，
避免多 batch rId 冲突。

## 用法

    python scripts/merge_batches.py batch-01.docx batch-02.docx batch-03.docx \\
        --output merged.docx

## 已知限制

- **styles / numbering / theme / fontTable / settings 只用 base（第一个 batch）的**——SubAgent
  在生成 batch 时应从同一份空白模板起，避免多 batch 样式定义冲突；如果某个 batch
  自己在 numbering.xml 中定义了 numId，合并后该 numId 会指向 base 的 numbering
  条目，可能错位。合并结束会 warn。
- 合并后仍需跑 audit_docx.py + inspect_pdf_pages.py 做最终 QA；本脚本只保证结构
  合并正确，不保证 rendering 视觉与 batch 完全一致。
"""

from __future__ import annotations

import argparse
import hashlib
import io
import re
import shutil
import sys
import zipfile
from pathlib import Path

from lxml import etree

# OOXML 常用命名空间
_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"

# 每个 batch 独占 + 需要重命名的 part 前缀 / 模式
_MEDIA_DIR = "word/media/"
_EMBED_DIR = "word/embeddings/"
_HEADER_RE = re.compile(r"^word/header(\d+)\.xml$")
_FOOTER_RE = re.compile(r"^word/footer(\d+)\.xml$")

# rels 中 target 归属这几类的部件属于 batch 独有，需要跟着 batch 一起重命名；
# 其余类型（numbering/styles/theme/fontTable/settings/webSettings）复用 base。
_RENAMABLE_REL_TYPES = frozenset({
    f"{_R_NS.rstrip('/')[:-len('officeDocument/2006/relationships')]}officeDocument/2006/relationships/image",  # 未使用，占位
})

_RENAMABLE_TARGET_HINTS = ("media/", "embeddings/", "header", "footer")


def _qn(prefix: str, name: str) -> str:
    """Return lxml Clark-notation tag using the OOXML namespace prefix."""
    ns = {"w": _W_NS, "r": _R_NS, "pkg": _PKG_REL_NS, "ct": _CT_NS}[prefix]
    return f"{{{ns}}}{name}"


def _read_zip(path: Path) -> dict[str, bytes]:
    """Read a zip into {member_name: bytes}. Skip pure directory entries."""
    files: dict[str, bytes] = {}
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            files[name] = zf.read(name)
    return files


def _write_zip(path: Path, files: dict[str, bytes]) -> None:
    """Write {name: bytes} back to a zip with DOCX-friendly compression."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        # [Content_Types].xml 必须位于 zip 首个条目，Word 打开更稳
        if "[Content_Types].xml" in files:
            zf.writestr("[Content_Types].xml", files["[Content_Types].xml"])
        for name, data in files.items():
            if name == "[Content_Types].xml":
                continue
            zf.writestr(name, data)


def _parse_xml(data: bytes) -> etree._Element:
    return etree.fromstring(data)


def _serialize_xml(elem: etree._Element) -> bytes:
    return etree.tostring(
        elem, xml_declaration=True, encoding="UTF-8", standalone=True
    )


def _parse_rels(rels_bytes: bytes) -> dict[str, tuple[str, str, str]]:
    """Parse a rels part → {rId: (Type, Target, TargetMode)}."""
    root = _parse_xml(rels_bytes)
    out: dict[str, tuple[str, str, str]] = {}
    for rel in root:
        rid = rel.get("Id") or ""
        typ = rel.get("Type") or ""
        target = rel.get("Target") or ""
        mode = rel.get("TargetMode") or "Internal"
        out[rid] = (typ, target, mode)
    return out


def _build_rels_xml(rels: dict[str, tuple[str, str, str]]) -> bytes:
    """Serialize {rId: (Type, Target, TargetMode)} back to a rels part."""
    root = etree.Element(
        f"{{{_PKG_REL_NS}}}Relationships", nsmap={None: _PKG_REL_NS}
    )
    for rid, (typ, target, mode) in rels.items():
        rel = etree.SubElement(root, f"{{{_PKG_REL_NS}}}Relationship")
        rel.set("Id", rid)
        rel.set("Type", typ)
        rel.set("Target", target)
        if mode == "External":
            rel.set("TargetMode", "External")
    return _serialize_xml(root)


def _next_rid_number(rels: dict[str, tuple[str, str, str]]) -> int:
    """Return max existing rId number + 1，用于给新 rId 排号避免冲突。"""
    max_n = 0
    for rid in rels:
        if rid.startswith("rId") and rid[3:].isdigit():
            max_n = max(max_n, int(rid[3:]))
    return max_n + 1


def _abs_target(target: str) -> str:
    """把 rels target 归一化到 zip 内绝对路径（相对 word/ 视为 word/…）。"""
    if target.startswith("/"):
        return target.lstrip("/")
    return "word/" + target


def _target_is_renamable(abs_target: str) -> bool:
    """判断 target 是否属于 batch 独占的可重命名部件。"""
    if abs_target.startswith(_MEDIA_DIR) or abs_target.startswith(_EMBED_DIR):
        return True
    if _HEADER_RE.match(abs_target) or _FOOTER_RE.match(abs_target):
        return True
    return False


def _rename_target(abs_target: str, batch_idx: int, used: set[str]) -> str:
    """给 batch 独占部件生成新的 zip 内绝对路径。冲突时 append 数字后缀。"""
    if abs_target.startswith(_MEDIA_DIR):
        stem = abs_target[len(_MEDIA_DIR):]
        candidate = f"{_MEDIA_DIR}b{batch_idx}_{stem}"
    elif abs_target.startswith(_EMBED_DIR):
        stem = abs_target[len(_EMBED_DIR):]
        candidate = f"{_EMBED_DIR}b{batch_idx}_{stem}"
    else:
        m = _HEADER_RE.match(abs_target)
        if m:
            candidate = f"word/header_b{batch_idx}_{m.group(1)}.xml"
        else:
            m = _FOOTER_RE.match(abs_target)
            assert m, f"unexpected target: {abs_target}"
            candidate = f"word/footer_b{batch_idx}_{m.group(1)}.xml"
    # 冲突处理（极少见）
    final = candidate
    n = 1
    while final in used:
        final = f"{candidate}.{n}"
        n += 1
    return final


def _find_body(doc_elem: etree._Element) -> etree._Element:
    body = doc_elem.find(_qn("w", "body"))
    if body is None:
        raise SystemExit("word/document.xml 缺少 <w:body>")
    return body


def _detach_tail_sectpr(body: etree._Element) -> etree._Element | None:
    """从 body 尾部摘掉 sectPr（如果存在），返回它。用于降级为段落级 sectPr。"""
    tail = None
    # body 尾部 sectPr 只能是 body 的直接子元素、且是最后一个
    for child in reversed(body):
        if child.tag == _qn("w", "sectPr"):
            tail = child
            break
        # 非 sectPr 的最后一个元素说明 body 没有尾部 sectPr（罕见但要兼容）
        break
    if tail is not None:
        body.remove(tail)
    return tail


def _demote_sectpr_to_paragraph(body: etree._Element, sectpr: etree._Element) -> None:
    """把 sectPr 塞入 body 尾部一个新段落的 pPr 里，从而形成段落级 sectPr。

    这是保留跨 batch section 边界的关键操作：
      - body 直接子级尾部 sectPr = "最后一个 section 的属性"
      - <w:p><w:pPr><w:sectPr/></w:pPr></w:p> = "当前 section 到此段落结束"

    合并时把 base 原尾部 sectPr 降级，让 batch1 的 section 定义结束在 batch1 内容末端。
    """
    wrap_p = etree.SubElement(body, _qn("w", "p"))
    pPr = etree.SubElement(wrap_p, _qn("w", "pPr"))
    pPr.append(sectpr)


def _rewrite_rid_attrs(elem: etree._Element, rid_map: dict[str, str]) -> None:
    """把 body 树里所有 r:id / r:embed / r:link 引用按 rid_map 重映射。"""
    # 只需处理 r 命名空间下的常用引用属性
    rid_attrs = {_qn("r", "id"), _qn("r", "embed"), _qn("r", "link")}
    for node in elem.iter():
        for attr in rid_attrs & set(node.attrib):
            old_rid = node.attrib[attr]
            new_rid = rid_map.get(old_rid)
            if new_rid is not None:
                node.attrib[attr] = new_rid
            # rid_map 中不存在的 rid 保持原样：可能是 batch 引用了 numbering/styles
            # 之类由 base 共用的部件——它们的 rId 不参与 body 引用，理应不出现在 body 里；
            # 若真的出现，保持原 rid 至少不会立即错乱，Word 可能忽略未知 rid。


def _update_content_types(
    ct_root: etree._Element,
    old_to_new: dict[str, str],
    batch_ct_root: etree._Element | None = None,
) -> None:
    """更新 [Content_Types].xml：给新增的 batch part 补齐 Override / Default。

    OPC 规则：非默认扩展名的 part 需要在 [Content_Types] 里显式声明 Override，
    有 Default extension 的可以走 default 匹配。这里两步都要处理：
      1. 拿到 batch 自己的 [Content_Types] 里的 Default extension（比如 png/jpeg），
         合并进 base_ct（避免重复），让 media 图片能被 default 命中；
      2. 对被 rename 的 part（带 PartName Override 的，比如 header/footer.xml），
         复制旧 Override 改成新 PartName。
    """
    ct_tag_override = f"{{{_CT_NS}}}Override"
    ct_tag_default = f"{{{_CT_NS}}}Default"

    existing_overrides = {
        elem.get("PartName"): elem for elem in ct_root
        if elem.tag == ct_tag_override
    }
    existing_default_exts = {
        (elem.get("Extension") or "").lower() for elem in ct_root
        if elem.tag == ct_tag_default
    }

    # 1. 合并 batch 的 Default extension（图片 png/jpeg/gif 等）
    if batch_ct_root is not None:
        for child in batch_ct_root:
            if child.tag != ct_tag_default:
                continue
            ext = (child.get("Extension") or "").lower()
            if ext and ext not in existing_default_exts:
                new_default = etree.SubElement(ct_root, ct_tag_default)
                new_default.set("Extension", ext)
                new_default.set("ContentType", child.get("ContentType") or "")
                existing_default_exts.add(ext)

    # 2. 复制 batch 有 Override 的 rename part（header/footer.xml 等）
    for old_abs, new_abs in old_to_new.items():
        old_part = "/" + old_abs
        new_part = "/" + new_abs
        old_override = existing_overrides.get(old_part)
        # base 自己的 Override（对应 batch1）会命中；batch2/batch3 的 Override 在
        # batch_ct_root 里；这里两处都查一下
        if old_override is None and batch_ct_root is not None:
            for child in batch_ct_root:
                if child.tag == ct_tag_override and child.get("PartName") == old_part:
                    old_override = child
                    break
        if old_override is None:
            continue
        if new_part in existing_overrides:
            continue
        new_override = etree.SubElement(ct_root, ct_tag_override)
        new_override.set("PartName", new_part)
        new_override.set("ContentType", old_override.get("ContentType") or "")
        existing_overrides[new_part] = new_override


def _copy_part_rels(
    batch_files: dict[str, bytes],
    old_abs: str,
    new_abs: str,
    dest_files: dict[str, bytes],
    batch_idx: int,
    batch_to_new_rid: dict[str, str],
    dest_rels: dict[str, tuple[str, str, str]],
) -> None:
    """如果被重命名的 part（如 header1.xml）有配套 _rels 文件，也要一起搬。

    比如 word/header1.xml 引用了图片 media/imgX.png，会在
    word/_rels/header1.xml.rels 里挂关系；rename 时新 header 的 rels 位置是
    word/_rels/{new_stem}.rels，内部 rId 保留但 target 需要按 media rename 后指向新名字。

    实现细节：header/footer 自身的 rels 里的 rId 独立于 document.xml.rels 的 rId 命名
    空间，本函数暂不处理这类嵌套 rels 的重命名——仅在 rels 存在时原样拷贝到新位置。
    绝大多数场景 header/footer 只放静态文字/页码，不引用媒体；如遇到复杂 header 引用
    图片场景，需要另做扩展。
    """
    old_stem = Path(old_abs).name
    new_stem = Path(new_abs).name
    old_rels_path = f"word/_rels/{old_stem}.rels"
    new_rels_path = f"word/_rels/{new_stem}.rels"
    if old_rels_path in batch_files:
        dest_files[new_rels_path] = batch_files[old_rels_path]


def merge_docx(inputs: list[Path], output: Path, verbose: bool = False) -> dict:
    """按 section-safe 语义合并 inputs → output。返回统计 dict 用于日志。"""
    if len(inputs) < 2:
        raise SystemExit("需要至少 2 个 batch DOCX 才需要合并")

    # 读第一个 batch 作为 base 部件表
    base_files = _read_zip(inputs[0])
    if "word/document.xml" not in base_files:
        raise SystemExit(f"{inputs[0]} 不是有效 DOCX：缺 word/document.xml")

    base_doc = _parse_xml(base_files["word/document.xml"])
    base_body = _find_body(base_doc)
    base_rels_bytes = base_files.get("word/_rels/document.xml.rels", b"")
    base_rels = _parse_rels(base_rels_bytes) if base_rels_bytes else {}
    base_ct = _parse_xml(base_files["[Content_Types].xml"])

    # 追踪 zip 内已用名字，避免 rename 冲突
    used_names = set(base_files.keys())

    # numbering.xml 比对：如果任一 batch 的 numbering 与 base 不同就 warn
    base_numbering_hash = _sha1_of(base_files.get("word/numbering.xml"))
    numbering_warnings: list[str] = []

    stats = {
        "batch_count": len(inputs),
        "renamed_parts": [],
        "external_rels_added": 0,
        "warnings": [],
    }

    for batch_idx, batch_path in enumerate(inputs[1:], start=2):
        batch_files = _read_zip(batch_path)
        if "word/document.xml" not in batch_files:
            raise SystemExit(f"{batch_path} 不是有效 DOCX：缺 word/document.xml")

        batch_doc = _parse_xml(batch_files["word/document.xml"])
        batch_body = _find_body(batch_doc)
        batch_rels_bytes = batch_files.get("word/_rels/document.xml.rels", b"")
        batch_rels = _parse_rels(batch_rels_bytes) if batch_rels_bytes else {}

        # 1) numbering.xml 一致性检查
        batch_numbering_hash = _sha1_of(batch_files.get("word/numbering.xml"))
        if (batch_numbering_hash and base_numbering_hash
                and batch_numbering_hash != base_numbering_hash):
            numbering_warnings.append(
                f"batch #{batch_idx}({batch_path.name}) 的 word/numbering.xml 与 base 不一致——"
                f"合并后所有 batch 只用 base 的 numbering.xml，本 batch 里的 numPr 编号可能错位"
            )

        # 2) 构造 rId 重映射：batch 的每个 rId 都换成 base 命名空间中未占用的新 rId
        next_rid = _next_rid_number(base_rels)
        rid_map: dict[str, str] = {}
        old_to_new_target: dict[str, str] = {}

        for old_rid, (typ, target, mode) in batch_rels.items():
            new_rid = f"rId{next_rid}"
            next_rid += 1
            rid_map[old_rid] = new_rid

            if mode == "External":
                # 外部超链接：只搬关系，target 保持
                base_rels[new_rid] = (typ, target, mode)
                stats["external_rels_added"] += 1
                continue

            abs_target = _abs_target(target)
            if _target_is_renamable(abs_target):
                # media / header / footer / embedding：加 batch 前缀 rename + 拷贝
                new_abs = _rename_target(abs_target, batch_idx, used_names)
                used_names.add(new_abs)
                if abs_target in batch_files:
                    base_files[new_abs] = batch_files[abs_target]
                    _copy_part_rels(
                        batch_files, abs_target, new_abs, base_files, batch_idx,
                        rid_map, base_rels,
                    )
                    old_to_new_target[abs_target] = new_abs
                    stats["renamed_parts"].append({
                        "batch_index": batch_idx,
                        "from": abs_target,
                        "to": new_abs,
                    })
                # target 保持相对 word/ 表达
                new_rel_target = (
                    new_abs[len("word/"):] if new_abs.startswith("word/") else new_abs
                )
                base_rels[new_rid] = (typ, new_rel_target, mode)
            else:
                # numbering / styles / theme / fontTable / settings 等共享部件：
                # 不重命名、不加进 base_rels（base 已有等价关系）；rid_map 保留映射
                # 但 body 引用 numbering/styles 不通过 r:id，因此这里不 pop 也不影响正确性。
                # 保留 mapping 供以后可能扩展（比如加 warn 时找源关系）
                continue

        # 3) 更新 [Content_Types].xml：合并 batch 的 Default extension（png/jpeg 等）
        #    并给 renamed part 补 Override。传入 batch_ct 让 Default 和 Override 都能被拷贝。
        batch_ct_root = _parse_xml(batch_files["[Content_Types].xml"])
        _update_content_types(base_ct, old_to_new_target, batch_ct_root)

        # 4) 把 batch body 里的 r:id/r:embed/r:link 引用替换成新 rId
        _rewrite_rid_attrs(batch_body, rid_map)

        # 5) 关键：把 base 当前 body 尾部 sectPr 降级为段落级 sectPr，
        #    形成"batch1 内容 → 段落级 sectPr(batch1 属性) → batch2 内容 → 尾部 sectPr(batch2 属性)"
        base_tail_sectpr = _detach_tail_sectpr(base_body)
        if base_tail_sectpr is not None:
            _demote_sectpr_to_paragraph(base_body, base_tail_sectpr)

        # 6) 摘掉 batch body 尾部 sectPr（稍后作为新的 base 尾部 sectPr 挂上去）
        batch_tail_sectpr = _detach_tail_sectpr(batch_body)

        # 7) batch body 剩余内容追加到 base body
        for child in list(batch_body):
            base_body.append(child)

        # 8) batch 的尾部 sectPr 成为新的 base 尾部 sectPr
        if batch_tail_sectpr is not None:
            base_body.append(batch_tail_sectpr)

        if verbose:
            print(f"[ok] merged batch #{batch_idx}: {batch_path.name} "
                  f"(rid_map size={len(rid_map)}, renamed={len(old_to_new_target)})",
                  file=sys.stderr)

    # 序列化并写回
    base_files["word/document.xml"] = _serialize_xml(base_doc)
    base_files["word/_rels/document.xml.rels"] = _build_rels_xml(base_rels)
    base_files["[Content_Types].xml"] = _serialize_xml(base_ct)

    _write_zip(output, base_files)

    stats["warnings"] = numbering_warnings
    return stats


def _sha1_of(data: bytes | None) -> str | None:
    if not data:
        return None
    return hashlib.sha1(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="按 section-safe 语义合并多个 batch DOCX 为一个整体 DOCX。"
                    "保留每个 batch 的 sectPr（页面方向/页边距/页眉页脚），"
                    "media/header/footer 加 batch 前缀 rename 避免冲突。",
    )
    parser.add_argument("inputs", nargs="+", type=Path,
                        help="按最终顺序列出的 batch DOCX 路径，至少 2 个")
    parser.add_argument("-o", "--output", type=Path, required=True,
                        help="合并后输出的 DOCX 路径")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="打印每个 batch 的合并信息到 stderr")
    args = parser.parse_args()

    for p in args.inputs:
        if not p.is_file():
            print(f"error: batch not found: {p}", file=sys.stderr)
            return 1

    stats = merge_docx(args.inputs, args.output, verbose=args.verbose)

    print(f"合并完成：{args.output}")
    print(f"  batch 数：{stats['batch_count']}")
    print(f"  重命名部件数：{len(stats['renamed_parts'])}")
    print(f"  外部关系数（新增）：{stats['external_rels_added']}")
    for warn in stats["warnings"]:
        print(f"  ⚠ {warn}", file=sys.stderr)

    # 合并后建议下游立即跑 audit_docx.py + inspect_pdf_pages.py；这里不自动跑，让调用方按需组织流程
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
