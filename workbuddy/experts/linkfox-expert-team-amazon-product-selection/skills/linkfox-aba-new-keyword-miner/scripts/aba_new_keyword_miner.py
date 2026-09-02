#!/usr/bin/env python3
"""ABA 新词挖掘专家 (ABA New Keyword Mining Expert) - LinkFox Skill
调用 /aba/intelligentQuery 接口，AI 批量翻译，自动导出 CSV。

完整流程：ABA 查询 → 返回 searchTerm + searchFrequencyRank → AI 批量翻译 → 合并导出 CSV

Usage:
  python aba_new_keyword_miner.py '<JSON parameters>'           # 始终落盘 JSON + CSV；<=8KB 额外全量打印；>8KB 只打印摘要
  python aba_new_keyword_miner.py '<JSON parameters>' --inline  # 始终落盘；强制全量打印到 stdout

参数（JSON）：
  analysisDescription  (str,  必填) 自然语言筛选描述
  region               (str,  可选) 站点代码，默认 US
  exportCsv            (bool, 可选) 是否导出 CSV，默认 true
  translate            (bool, 可选) 是否 AI 批量翻译为中文，默认 true
"""

import csv
import json
import os
import subprocess
import sys
import time
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

API_PATH = "/aba/intelligentQuery"
SLUG = "linkfox-aba-new-keyword-miner"

# AIGC 文本生成脚本路径（用于批量翻译）
AIGC_TEXTGEN_PATH = os.path.join(
    os.environ.get("LINKFOX_SKILLS_DIR", "/root/.linkfox/.ce/skills"),
    "linkfox-aigc-textgen", "scripts", "aigc_textgen.py",
)

# 响应 <= 该字节数时落盘后额外全量打印到 stdout；超过则只打摘要
SMALL_THRESHOLD = 8000

from linkfox_paths import get_api_base, resolve_data_path


def get_api_url():
    return get_api_base() + API_PATH


def get_api_key():
    key = os.environ.get("LINKFOX_AGENT_API_KEY") or os.environ.get("LINKFOXAGENT_API_KEY")
    if not key:
        print(
            "API Key not configured. Please complete authorization first:\n"
            "1. Visit https://agent.linkfox.com → 设置 → API KEY to obtain your Key\n"
            "2. Set the environment variable: export LINKFOX_AGENT_API_KEY=your-key-here",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def call_api(params):
    req = Request(
        get_api_url(),
        data=json.dumps(params).encode("utf-8"),
        headers={
            "Authorization": get_api_key(),
            "Content-Type": "application/json",
            "User-Agent": "LinkFox-Skill/2.0",
            "SESSION_ID": os.environ.get("SESSION_ID", ""),
            "MESSAGE_ID": os.environ.get("MESSAGE_ID", ""),
            "MODE_ID": os.environ.get("MODE_ID", ""),
            "APP_NAME": os.environ.get("APP_NAME", ""),
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        try:
            return json.loads(body) if body else {"error": f"HTTP {e.code}: {e.reason}"}
        except Exception:
            return {"error": f"HTTP {e.code}: {e.reason}", "details": body}
    except URLError as e:
        return {"error": f"Connection failed: {e.reason}"}


def _find_main_list(obj):
    """递归找到元素数最多的 list 字段。不写死字段名，适配任意结构。"""
    best = (None, None, -1)

    def walk(node, path):
        nonlocal best
        if isinstance(node, list):
            if len(node) > best[2]:
                best = (path, node, len(node))
        elif isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k)

    walk(obj, "")
    return best[0], best[1]


def _extract_results(result):
    """从 ABA 响应中提取搜索词及排名，兼容 searchTerm/searchterm 字段名。

    返回 list[dict]，每个 dict 含 term(str) 和 rank(int 或 None)。
    """
    if not isinstance(result, dict):
        return []
    _, main_list = _find_main_list(result)
    if not main_list:
        return []
    results = []
    for row in main_list:
        if not isinstance(row, dict):
            continue
        term = row.get("searchTerm") or row.get("searchterm") or ""
        if not term:
            continue
        rank = row.get("searchFrequencyRank")
        if rank is not None:
            try:
                rank = int(rank)
            except (ValueError, TypeError):
                rank = None
        results.append({"term": term, "rank": rank})
    return results


def _batch_translate(terms):
    """调用 linkfox-aigc-textgen 批量翻译搜索词为中文。

    返回 list[str]，与 terms 等长；翻译失败时对应位置为空字符串。
    """
    if not terms:
        return []
    if not os.path.exists(AIGC_TEXTGEN_PATH):
        print(f"Translation script not found: {AIGC_TEXTGEN_PATH}", file=sys.stderr)
        return [""] * len(terms)

    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(terms))
    prompt = (
        "请将以下亚马逊英文搜索词逐一翻译成简体中文。"
        "要求：每行一个翻译结果，按原顺序输出，只输出中文翻译，"
        "不要输出英文原文、序号或任何解释。保持简洁，专有名词保留英文。\n\n"
        f"{numbered}"
    )

    params = {
        "prompt": prompt,
        "imageUrls": [],
        "model": "GEM_3_FLASH",
        "thinkingLevel": "minimal",
    }

    try:
        proc = subprocess.run(
            [sys.executable, AIGC_TEXTGEN_PATH, "--stdin", "--content-only"],
            input=json.dumps(params, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        print("Translation timed out (600s)", file=sys.stderr)
        return [""] * len(terms)
    except Exception as e:
        print(f"Translation call failed: {e}", file=sys.stderr)
        return [""] * len(terms)

    if proc.returncode != 0:
        print(f"Translation failed (exit {proc.returncode}): {proc.stderr[:200]}", file=sys.stderr)
        return [""] * len(terms)

    # --content-only 模式下 stdout 为纯文本 content，换行符被压平为 ⏎
    content = proc.stdout.strip()
    if not content:
        return [""] * len(terms)

    # 还原换行符并按行拆分
    translations = content.replace("⏎", "\n").strip().split("\n")
    translations = [t.strip() for t in translations if t.strip()]

    # 对齐长度
    while len(translations) < len(terms):
        translations.append("")
    return translations[:len(terms)]


def export_csv(results, ts):
    """将搜索词列表导出为 CSV（6 列），返回 CSV 文件路径。

    results: list[dict]，每个 dict 含 term, rank, translation 字段。
    """
    csv_path = resolve_data_path(SLUG, ts).replace(".json", ".csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["序号", "搜索词", "中文翻译", "搜索频率排名", "标记", "备注"])
        for i, row in enumerate(results, 1):
            rank_str = str(row["rank"]) if row["rank"] is not None else ""
            writer.writerow([i, row["term"], row.get("translation", ""), rank_str, "", ""])
    return csv_path


def summarize(result):
    """打印紧凑摘要：顶层字段 + 常见计数 + 最大列表前 3 条。"""
    if not isinstance(result, dict):
        print(f"Response type: {type(result).__name__}")
        print(json.dumps(result, ensure_ascii=False)[:500])
        return

    print(f"Top-level keys: {list(result.keys())}")

    for k in ("errcode", "errorCode", "code", "errmsg", "msg",
              "total", "totalCount", "count", "currentPage", "perPage",
              "costToken", "costTime", "success"):
        if k in result and isinstance(result[k], (int, float, bool, str)):
            print(f"  {k}: {result[k]}")

    list_path, main_list = _find_main_list(result)
    if list_path is not None and main_list:
        sample = main_list[:3]
        print(f"\nMain list field: `{list_path}` (length={len(main_list)})")
        print(f"Sample (first {len(sample)} of {len(main_list)}):")
        print(json.dumps(sample, indent=2, ensure_ascii=False))


def _resolve_output_path(ts):
    return resolve_data_path(SLUG, ts)


def main():
    argv = sys.argv[1:]
    inline = "--inline" in argv
    argv = [a for a in argv if a != "--inline"]

    if not argv:
        print(f"Usage: {os.path.basename(__file__)} '<JSON parameters>' [--inline]", file=sys.stderr)
        sys.exit(1)

    try:
        params = json.loads(argv[0])
    except json.JSONDecodeError as e:
        print(f"Invalid parameter format: {e}", file=sys.stderr)
        sys.exit(1)

    # 提取本 skill 专属参数，不传给后端
    export_csv_flag = params.pop("exportCsv", True)
    translate_flag = params.pop("translate", True)

    result = call_api(params)

    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    ts = int(time.time())
    out_path = _resolve_output_path(ts)
    try:
        with open(out_path, "w") as f:
            f.write(serialized)
        print(f"Saved full response: {out_path} ({len(serialized)} bytes)")
    except OSError as e:
        print(f"Failed to save to {out_path}: {e}", file=sys.stderr)

    # 提取搜索词 + 排名
    if isinstance(result, dict) and result.get("errcode") == 200:
        results = _extract_results(result)
        if results:
            # AI 批量翻译
            if translate_flag:
                terms = [r["term"] for r in results]
                print(f"Translating {len(terms)} search terms...")
                translations = _batch_translate(terms)
                for i, t in enumerate(translations):
                    results[i]["translation"] = t
                print(f"Translation done: {sum(1 for t in translations if t)} / {len(translations)} succeeded")
            else:
                for r in results:
                    r["translation"] = ""

            # CSV 导出
            if export_csv_flag:
                csv_path = export_csv(results, ts)
                print(f"CSV exported: {csv_path}")
            print(f"Total search terms: {len(results)}")

    if inline or len(serialized.encode("utf-8")) <= SMALL_THRESHOLD:
        print(serialized)
    else:
        summarize(result)


if __name__ == "__main__":
    main()
