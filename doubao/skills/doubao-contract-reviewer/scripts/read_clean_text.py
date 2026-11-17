#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
read_clean_text.py — clean_text.json 的唯一读取入口

【为什么要有这个脚本】
  clean_text.json 是合同审查的唯一文本来源,设计上必须"一次性完整读取"。
  历史上出现过的坑:调用方(尤其中等能力的模型)在合同较长时,会自作主张地
  "翻页/分块"读这个文件,而分页实现里每次 offset 又从 0 起算 —— 结果是
  已经读过的段落被反复塞进上下文,造成:
    - 重复内容不断累计,新消息里堆着历史上出现过的旧段落;
    - 上下文膨胀、token 浪费、审查明显变慢;
    - 段落被重复计入,干扰"存在性检查/条款计数"等判断。

  仅靠 clean_text.json 里的 read_hint 文字提示 + SKILL.md 里的约定,是"软约束",
  依赖调用方守规矩。本脚本把防护下沉到代码层,提供一个确定性的读取契约:

    1) 默认行为 = 一次性吐出【全部】段落文本,调用方拿到就是全文,没有"翻页"这个选项;
    2) 万一确实要分片(--limit),游标(offset)由脚本维护并【显式打印下一条命令】,
       调用方永远不用自己算 offset,从根上消灭"每次从 0 开始"的重复累计;
    3) 读取时对段落 idx 做【去重 + 单调性校验】,发现重复/乱序直接告警到 stderr,
       把原本隐蔽的"重复累计"软坑变成一眼可见的硬信号。

【用法】
  # 推荐:一次性拿全文(纯文本,最省 token)
  python3 read_clean_text.py clean_text.json

  # 需要元信息时输出 JSON(含 has_revisions / paragraph_count / 全部段落)
  python3 read_clean_text.py clean_text.json --format json

  # 仅在文件极大、单次读取被工具层强制截断时才分片;游标由脚本给出
  python3 read_clean_text.py clean_text.json --limit 200
  # → 末尾会打印形如:
  #   [next] 还有剩余段落,读取下一片请执行:
  #     python3 read_clean_text.py clean_text.json --limit 200 --offset 200
  # 直接照抄执行即可,offset 已由脚本算好,不要自己从 0 重来。

【退出码】
  0  成功(全文读完 / 分片读到本片)
  1  参数或文件错误
  3  数据完整性告警(检测到重复 idx 或乱序);内容照常输出,但请重新生成 clean_text.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys


def _load(path: str) -> dict:
    if not os.path.isfile(path):
        print(f"[ERROR] 文件不存在: {path}", file=sys.stderr)
        sys.exit(1)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[ERROR] 无法解析 clean_text.json: {exc}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(data, dict) or "paragraphs" not in data:
        print("[ERROR] 不是合法的 clean_text.json(缺少 paragraphs 字段)", file=sys.stderr)
        sys.exit(1)
    return data


def _check_integrity(paragraphs: list) -> bool:
    """对段落 idx 做去重 + 单调性校验。返回 True 表示健康,False 表示检测到问题。

    这是把"重复累计"从隐蔽软坑变成可见硬信号的关键一环:
    - 重复 idx = 同一段落被塞了多次(典型的翻页 offset 从 0 重来的后果);
    - 乱序 idx = 段落顺序被打乱,交叉引用/条款定位会错。
    """
    healthy = True
    seen = {}
    prev = None
    for pos, p in enumerate(paragraphs):
        idx = p.get("idx", pos)
        if idx in seen:
            healthy = False
            print(
                f"[WARN] 检测到重复段落 idx={idx}(首次出现在第 {seen[idx]} 个,"
                f"又出现在第 {pos} 个)—— 这正是'翻页重复累计'的特征,"
                f"请重新用 preprocess_contract.py 生成 clean_text.json 后一次性完整读取。",
                file=sys.stderr,
            )
        else:
            seen[idx] = pos
        if prev is not None and idx < prev:
            healthy = False
            print(
                f"[WARN] 段落 idx 非单调递增(第 {pos} 个 idx={idx} < 前一个 idx={prev}),"
                f"顺序可能被打乱。",
                file=sys.stderr,
            )
        prev = idx
    return healthy


def main():
    ap = argparse.ArgumentParser(
        description="clean_text.json 唯一读取入口:默认一次性吐全文,禁止调用方自行翻页。")
    ap.add_argument("path", help="clean_text.json 路径")
    ap.add_argument("--format", choices=["text", "json"], default="text",
                    help="text=纯文本段落(默认,最省 token);json=含元信息的结构化输出")
    ap.add_argument("--limit", type=int, default=0,
                    help="仅在被工具层强制截断时使用:每片最多返回多少段(0=不分片,返回全文)")
    ap.add_argument("--offset", type=int, default=0,
                    help="配合 --limit 的起始段索引;正常情况请勿手动指定,照抄脚本打印的 [next] 命令即可")
    args = ap.parse_args()

    data = _load(args.path)
    paragraphs = data.get("paragraphs", [])
    total = len(paragraphs)

    healthy = _check_integrity(paragraphs)

    # 计算本次返回的切片
    if args.limit and args.limit > 0:
        start = max(0, args.offset)
        end = min(total, start + args.limit)
        chunk = paragraphs[start:end]
        has_more = end < total
    else:
        start, end = 0, total
        chunk = paragraphs
        has_more = False

    if args.format == "json":
        out = {
            "has_revisions": data.get("has_revisions"),
            "revision_count": data.get("revision_count"),
            "paragraph_count": total,
            "returned_range": {"start": start, "end": end},
            "integrity_ok": healthy,
            "paragraphs": chunk,
            "notes": data.get("notes", ""),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        # 纯文本:每段一行,带 idx 前缀便于定位;这是审查阶段最省 token 的形态
        lines = []
        for p in chunk:
            idx = p.get("idx", "")
            text = p.get("text", "")
            flag = " [MOD]" if p.get("has_revision") else ""
            lines.append(f"[{idx}]{flag} {text}")
        sys.stdout.write("\n".join(lines) + ("\n" if lines else ""))

    # 分片模式下,游标由脚本维护并显式打印下一条命令,调用方无需自己算 offset
    if has_more:
        print(
            f"\n[next] 已返回段落 {start}..{end - 1}(共 {total} 段),仍有剩余。"
            f"读取下一片请【照抄】执行,不要把 offset 重置为 0:\n"
            f"    python3 {os.path.basename(sys.argv[0])} {args.path} "
            f"--limit {args.limit} --offset {end}"
            + (f" --format {args.format}" if args.format != 'text' else ""),
            file=sys.stderr,
        )
    elif args.limit and args.limit > 0:
        print(f"\n[done] 已读完全部 {total} 段(最后一片 {start}..{end - 1})。", file=sys.stderr)

    sys.exit(0 if healthy else 3)


if __name__ == "__main__":
    main()
