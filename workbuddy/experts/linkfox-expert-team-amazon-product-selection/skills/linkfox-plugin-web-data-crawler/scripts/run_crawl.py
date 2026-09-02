#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_crawl.py — 跨境电商商品详情页采集调度器

支持子命令：health / probe / scrape / reviews / send
通过 LINKFOX_AGENT_API_URL/linkFoxApp/api/agent/crawlTask/startCrawlTask 接口执行采集。

环境变量：
  LINKFOX_AGENT_API_KEY   必填，Authorization 头的值（用户 accessToken）
  LINKFOX_TOOL_GATEWAY   后端基址，可通过环境变量覆盖（缺省走 get_api_base()）

用法：
  python scripts/run_crawl.py health
  python scripts/run_crawl.py probe  --site amazon-us --url https://www.amazon.com/dp/B0XXX
  python scripts/run_crawl.py scrape --site amazon-us --url https://www.amazon.com/dp/B0XXX [--category books] [--reuse-tab] [--scenario full]
  python scripts/run_crawl.py reviews --site amazon-us --url https://www.amazon.com/product-reviews/B0XXX/
  python scripts/run_crawl.py send --site amazon-us --file <path> [--url ...] [--reuse-tab] [--category ...]
  python scripts/run_crawl.py send --site amazon-us --json '<json>' [--url ...]
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# ── UTF-8 everywhere ──────────────────────────────────────────────────
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SKILL_DIR = Path(__file__).resolve().parent.parent  # scripts/ → skill root

# Allow importing validate_workflow from the same scripts/ directory
_scripts_dir = str(SKILL_DIR / "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

import validate_workflow

from linkfox_paths import get_api_base, resolve_data_path

SLUG = "linkfox-plugin-web-data-crawler"
API_PATH = "/linkFoxApp/api/agent/crawlTask/startCrawlTask"

# Amazon 站点 → 商品详情页域名（ASIN 拼 URL 用 + scrape --site 参数）
# TODO: 新增 locale 时需同步更新 sites/INDEX.md 的 locale 列表
AMAZON_SITE_DOMAINS = {
    "amazon-us": "www.amazon.com",
    "amazon-uk": "www.amazon.co.uk",
    "amazon-de": "www.amazon.de",
    "amazon-fr": "www.amazon.fr",
    "amazon-it": "www.amazon.it",
    "amazon-es": "www.amazon.es",
    "amazon-jp": "www.amazon.co.jp",
    "amazon-ca": "www.amazon.ca",
    "amazon-au": "www.amazon.com.au",
    "amazon-mx": "www.amazon.com.mx",
    "amazon-in": "www.amazon.in",
    "amazon-ae": "www.amazon.ae",
    "amazon-sa": "www.amazon.sa",
    "amazon-br": "www.amazon.com.br",
    "amazon-nl": "www.amazon.nl",
    "amazon-se": "www.amazon.se",
    "amazon-sg": "www.amazon.sg",
}


def _get_api_url() -> str:
    return get_api_base() + API_PATH


def _get_api_key() -> str:
    key = os.environ.get("LINKFOX_AGENT_API_KEY")
    if not key:
        raise SystemExit(
            "未设置 LINKFOX_AGENT_API_KEY，请前往 https://skill.linkfox.com/linkfoxskills/guide.htm "
            "申请并配置环境变量"
        )
    return key


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _run_post_process(result: dict, site_key: str) -> dict:
    """Auto-execute site-specific image post-processing if the script exists.

    Convention: scripts/<site_key>_image_post.py  (e.g. scripts/amazon_image_post.py).
    Returns the processed result on success; returns the original result on any failure
    so the scrape never breaks due to post-processing issues.
    """
    pp_script = SKILL_DIR / "scripts" / f"{site_key}_image_post.py"
    if not pp_script.exists():
        return result

    print(f"[Post-Process] Running {pp_script.name}...", file=sys.stderr)
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            f"{site_key}_image_post", str(pp_script)
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.post_process(result)
    except Exception as e:
        print(f"[Post-Process] Failed: {e} — returning raw result", file=sys.stderr)
        return result


def _post(workflow: dict) -> dict:
    """POST workflow JSON 到 startCrawlTask 接口，返回解析后的结果。"""
    workflow_str = json.dumps(workflow, ensure_ascii=False)
    body = json.dumps({"workflowJson": workflow_str, "sourceClient": "1"}, ensure_ascii=False).encode("utf-8")
    api_key = _get_api_key()
    url = _get_api_url()

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": api_key,
            "Content-Type": "application/json",
            "SESSION_ID": os.environ.get("SESSION_ID", ""),
            "MESSAGE_ID": os.environ.get("MESSAGE_ID", ""),
            "MODE_ID": os.environ.get("MODE_ID", ""),
            "APP_NAME": os.environ.get("APP_NAME", ""),
        },
        method="POST",
    )
    timeout = int(os.environ.get("LINKFOX_SYNC_TIMEOUT", "300"))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            # startCrawlTask 返回格式: { taskId, status, data, errorMsg }
            # 适配上层调用方对 code/success 的判断
            if result.get("status") == "SUCCESS":
                result["code"] = 0
                result["success"] = True
            else:
                result["code"] = -1
                result["success"] = False
            return result
    except urllib.error.HTTPError as e:
        payload = e.read().decode("utf-8", errors="replace")
        return {"success": False, "code": e.code, "message": payload}
    except urllib.error.URLError as e:
        return {"success": False, "code": -1, "message": f"Connection failed: {e.reason}"}


def _save_result(result: dict) -> str:
    """Save only the ``data`` field to session directory as standard JSON.

    API response format: {taskId, status, data, errorMsg} where ``data`` is a
    JSON string.  This extracts and normalizes ``data`` so the saved file is
    clean, structured JSON — no wrapper, no nested string quoting.

    Falls back to cwd if resolve_data_path raises (e.g. linkfox_paths init failure).
    """
    raw = result.get("data")
    if isinstance(raw, str):
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            payload = raw  # not valid JSON, save as-is
    else:
        payload = raw  # already a dict/list, or None
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    ts = time.time()
    try:
        out_path = resolve_data_path(SLUG, ts)
    except Exception:
        out_path = os.path.join(os.getcwd(), f"crawl-result-{int(ts * 1_000_000)}.json")
    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(serialized)
        return out_path
    except OSError as e:
        print(f"Failed to save result: {e}", file=sys.stderr)
        return ""


def _resolve_site_key(args_site: str) -> str:
    """将 run_crawl.py 的 --site (如 amazon-us) 映射为 skill 目录下的站点 key (如 amazon)。

    TODO: 新增站点族时需在此添加 prefix 分支，或改为从 sites/INDEX.md 动态推导。
    """
    # amazon-us → amazon, shein → shein
    if args_site.startswith("amazon"):
        return "amazon"
    return args_site


def _build_url_from_site(args) -> str:
    """根据 --site 和 --url 或 --asin 构造完整商品 URL。"""
    if args.url:
        return args.url
    if args.asin:
        domain = AMAZON_SITE_DOMAINS.get(args.site, "")
        if not domain:
            raise SystemExit(f"不支持从 ASIN 拼 URL 的站点 {args.site!r}")
        return f"https://{domain}/dp/{args.asin}"
    raise SystemExit("需要 --url 或 --asin 提供商品地址")


def _inject_category_fields(steps: list, site: str, category: str) -> list:
    """Insert category-specific EXTRACT steps before CLOSE_TAB."""
    fields_path = SKILL_DIR / "sites" / site / "categories" / "fields" / f"{category}.json"
    if not fields_path.exists():
        print(f"Warning: category field file not found: {fields_path}", file=sys.stderr)
        return steps

    ext = _load_json(fields_path)
    # Find CLOSE_TAB index (last step)
    close_idx = len(steps) - 1
    for i, s in enumerate(steps):
        if s.get("actionCode") == "CLOSE_TAB":
            close_idx = i
            break

    for field_def in ext.get("fields", []):
        step = {k: v for k, v in field_def.items() if k != "postProcess"}
        steps.insert(close_idx, step)
        close_idx += 1

    return steps


def _strip_open_tab(steps: list) -> list:
    """Remove OPEN_TAB step (first step) when reusing a probe's tab."""
    if steps and steps[0].get("actionCode") == "OPEN_TAB":
        return steps[1:]
    return steps


def _replace_url(steps: list, url: str) -> list:
    """Replace tabUrl in the first step that has one."""
    for step in steps:
        if "tabUrl" in step:
            step["tabUrl"] = url
            break
    return steps


def _validate_or_exit(wf: dict) -> None:
    """Run workflow validation; print errors and exit 1 on failure."""
    errors = validate_workflow.validate(wf)
    if errors:
        print(f"[VALIDATION FAILED] {len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)


# ── Subcommands ──────────────────────────────────────────────────────────


def cmd_health(_args):
    """检查 LINKFOX_AGENT_API_KEY 环境变量是否已配置。"""
    try:
        api_key = _get_api_key()
    except SystemExit:
        raise
    print(json.dumps({"api_configured": True, "api_url": _get_api_url()}, indent=2))
    sys.exit(0)


def cmd_probe(args):
    """Send category probe workflow."""
    site_key = _resolve_site_key(args.site)
    probe_path = SKILL_DIR / "sites" / site_key / "_category-probe.json"
    if not probe_path.exists():
        print(f"Error: probe file not found: {probe_path}", file=sys.stderr)
        sys.exit(1)

    wf = _load_json(probe_path)
    wf["steps"] = _replace_url(wf["steps"], _build_url_from_site(args))
    _validate_or_exit(wf)
    result = _post(wf)
    out_path = _save_result(result)
    if out_path:
        print(f"[Saved] {out_path}")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result.get("code") == 0 else 1)


def cmd_scrape(args):
    """Send base scrape workflow with optional category injection."""
    site_key = _resolve_site_key(args.site)
    scenario = args.scenario or "full"
    wf_path = SKILL_DIR / "sites" / site_key / f"base-{scenario}.json"
    if not wf_path.exists():
        print(f"Error: workflow file not found: {wf_path}", file=sys.stderr)
        sys.exit(1)

    if not args.reuse_tab and not args.url:
        print("Error: --url is required when not using --reuse-tab", file=sys.stderr)
        sys.exit(2)

    wf = _load_json(wf_path)

    if args.reuse_tab:
        wf["steps"] = _strip_open_tab(wf["steps"])
    else:
        wf["steps"] = _replace_url(wf["steps"], _build_url_from_site(args))

    if args.category:
        wf["steps"] = _inject_category_fields(wf["steps"], site_key, args.category)

    _validate_or_exit(wf)
    result = _post(wf)

    # Auto-execute site-specific image post-processing on success (unless opted out).
    if not args.no_post_process and result.get("code") == 0:
        result = _run_post_process(result, site_key)

    out_path = _save_result(result)
    if out_path:
        print(f"[Saved] {out_path}")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result.get("code") == 0 else 1)


def cmd_reviews(args):
    """Send reviews workflow."""
    site_key = _resolve_site_key(args.site)
    wf_path = SKILL_DIR / "sites" / site_key / "base-reviews.json"
    if not wf_path.exists():
        print(f"Error: reviews file not found: {wf_path}", file=sys.stderr)
        sys.exit(1)

    wf = _load_json(wf_path)
    wf["steps"] = _replace_url(wf["steps"], _build_url_from_site(args))
    _validate_or_exit(wf)
    result = _post(wf)
    out_path = _save_result(result)
    if out_path:
        print(f"[Saved] {out_path}")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result.get("code") == 0 else 1)


def cmd_send(args):
    """Send an arbitrary workflow file or inline JSON.

    Used for Part 2 exploration: GET_PAGE_INFO, GET_DOM, VERIFY_SELECTOR, etc.
    Can also send repaired workflows with --reuse-tab.
    """
    site_key = _resolve_site_key(args.site)
    if args.json_str:
        wf = json.loads(args.json_str)
    elif args.file:
        wf = _load_json(Path(args.file))
    else:
        print("Error: --file or --json required for 'send'", file=sys.stderr)
        sys.exit(1)

    if args.reuse_tab:
        wf["steps"] = _strip_open_tab(wf["steps"])

    # Replace URL in remaining steps (order matters: strip OPEN_TAB first,
    # then replace URL in any subsequent step that still has tabUrl).
    if args.url:
        wf["steps"] = _replace_url(wf["steps"], args.url)

    if args.category:
        wf["steps"] = _inject_category_fields(wf["steps"], site_key, args.category)

    _validate_or_exit(wf)
    result = _post(wf)
    out_path = _save_result(result)
    if out_path:
        print(f"[Saved] {out_path}")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result.get("code") == 0 else 1)


def cmd_legacy(args):
    """Legacy 模式：直接用模板文件路径 + --url/--asin 发送（兼容旧调用方式）。"""
    template_path = args.template
    obj = _load_json(Path(template_path))

    url = _build_url_from_site(args)
    wf = obj
    wf["steps"] = _replace_url(wf["steps"], url)
    _validate_or_exit(wf)
    result = _post(wf)
    out_path = _save_result(result)
    if out_path:
        print(f"[Saved] {out_path}")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result.get("code") == 0 else 1)


# ── CLI ──────────────────────────────────────────────────────────────────


def main():
    KNOWN_COMMANDS = {"health", "probe", "scrape", "reviews", "send"}

    # Legacy 兼容模式：第一个参数是文件路径（含 / \ 或 .json 后缀）且非已知子命令 → 走 legacy
    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        is_legacy = (first_arg not in KNOWN_COMMANDS
                     and ("/" in first_arg or "\\" in first_arg or first_arg.endswith(".json")))
    else:
        is_legacy = False

    if is_legacy:
        url = None
        asin = None
        site = None
        template_path = first_arg
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--url" and i + 1 < len(sys.argv):
                url = sys.argv[i + 1]; i += 2
            elif sys.argv[i] == "--asin" and i + 1 < len(sys.argv):
                asin = sys.argv[i + 1]; i += 2
            elif sys.argv[i] == "--site" and i + 1 < len(sys.argv):
                site = sys.argv[i + 1]; i += 2
            else:
                print(f"未知参数: {sys.argv[i]}", file=sys.stderr); sys.exit(2)
        if asin and not site:
            raise SystemExit("--asin 必须配合 --site（如 amazon-us）")
        if asin and url:
            raise SystemExit("--url 与 --asin 不能同时使用")
        obj = _load_json(Path(template_path))
        wf = obj
        wf["steps"] = _replace_url(
            wf["steps"],
            url or (f"https://{AMAZON_SITE_DOMAINS.get(site, '')}/dp/{asin}" if asin and site else "")
        )
        _validate_or_exit(wf)
        result = _post(wf)
        out_path = _save_result(result)
        if out_path:
            print(f"[Saved] {out_path}")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result.get("code") == 0 else 1)

    # 正常子命令模式
    parser = argparse.ArgumentParser(
        description="跨境电商商品详情页采集调度器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_crawl.py health
  python scripts/run_crawl.py probe  --site amazon-us --url https://www.amazon.com/dp/B0CP9YB3Q4
  python scripts/run_crawl.py scrape --site amazon-us --url https://www.amazon.com/dp/B0CP9YB3Q4
  python scripts/run_crawl.py scrape --site amazon-us --url https://www.amazon.com/dp/B0CP9YB3Q4 --reuse-tab --category books
  python scripts/run_crawl.py reviews --site amazon-us --url https://www.amazon.com/product-reviews/B0CP9YB3Q4/
  python scripts/run_crawl.py send --site amazon-us --file sites/amazon/base-full.json --reuse-tab
  python scripts/run_crawl.py send --site amazon-us --json '{"steps":[{"actionCode":"GET_PAGE_INFO","tabKey":"tabKey666","extractField":"p"}]}'

Legacy 兼容:
  python scripts/run_crawl.py sites/amazon/base-full.json --url "https://www.amazon.com/dp/B09TXQXS47"
  python scripts/run_crawl.py sites/amazon/base-full.json --asin B09TXQXS47 --site amazon-us
        """,
    )
    sub = parser.add_subparsers(dest="command")

    # health
    sub.add_parser("health", help="检查 API Key 是否已配置")

    # probe
    p = sub.add_parser("probe", help="Send category probe workflow")
    p.add_argument("--site", required=True, help="Site key: amazon-us, amazon-jp, shein, etc.")
    p.add_argument("--url", required=True, help="Full product page URL")

    # scrape
    p = sub.add_parser("scrape", help="Send base scrape workflow")
    p.add_argument("--site", required=True, help="Site key: amazon-us, amazon-jp, shein, etc.")
    p.add_argument("--url", help="Full product page URL（--reuse-tab 时不需要）")
    p.add_argument("--category", help="Category key for field injection (books, electronics, etc.)")
    p.add_argument("--reuse-tab", action="store_true", help="Strip OPEN_TAB — tab already open from probe")
    p.add_argument("--scenario", default="full", help="Workflow scenario: full, price-rating, title-price (default: full)")
    p.add_argument("--no-post-process", action="store_true", help="Skip site-specific image post-processing")

    # reviews
    p = sub.add_parser("reviews", help="Send reviews workflow")
    p.add_argument("--site", required=True, help="Site key: amazon-us, amazon-jp, shein, etc.")
    p.add_argument("--url", required=True, help="Full reviews page URL")

    # send (generic)
    p = sub.add_parser("send", help="Send arbitrary workflow file or inline JSON")
    p.add_argument("--site", required=True, help="Site key (for category injection context)")
    p.add_argument("--file", help="Path to workflow JSON file")
    p.add_argument("--json", dest="json_str", help="Inline workflow JSON string")
    p.add_argument("--url", help="Product page URL (replaces tabUrl in first step)")
    p.add_argument("--reuse-tab", action="store_true", help="Strip OPEN_TAB")
    p.add_argument("--category", help="Category key for field injection")

    args = parser.parse_args()

    handlers = {
        "health": cmd_health,
        "probe": cmd_probe,
        "scrape": cmd_scrape,
        "reviews": cmd_reviews,
        "send": cmd_send,
    }

    if not args.command:
        parser.print_help()
        sys.exit(2)

    handlers[args.command](args)


if __name__ == "__main__":
    main()
