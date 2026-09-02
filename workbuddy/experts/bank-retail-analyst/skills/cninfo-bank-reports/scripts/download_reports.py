#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从巨潮资讯网下载上市银行的年度报告和半年度报告
用法: python3 download_reports.py --stock-code 601818 --org-id 9900006246 --start-year 2020 --end-year 2025
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
import urllib.error

# ── 请求头 ─────────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.cninfo.com.cn/",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}

# 报告类型分类代码（上交所/深交所通用）
CATEGORY_MAP = {
    "annual":    "category_ndbg_szsh",   # 年度报告
    "semi":      "category_bndbg_szsh",  # 半年度报告
    "quarterly": "category_jdbg_szsh",   # 季度报告（一季报、三季报）
}

FILE_BASE_URL = "https://static.cninfo.com.cn/"
QUERY_API = "https://www.cninfo.com.cn/new/hisAnnouncement/query"


def http_post(url, data_dict, retry=3):
    """带重试的 HTTP POST"""
    data = urllib.parse.urlencode(data_dict).encode("utf-8")
    for attempt in range(retry):
        try:
            req = urllib.request.Request(url, data=data, headers=HEADERS, method="POST")
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt == retry - 1:
                raise
            time.sleep(2 ** attempt)
    return None


def http_get_file(url, save_path, retry=3):
    """下载文件，带重试"""
    download_headers = {
        "User-Agent": HEADERS["User-Agent"],
        "Referer": HEADERS["Referer"],
    }
    req = urllib.request.Request(url, headers=download_headers)
    for attempt in range(retry):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                with open(save_path, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
            size = os.path.getsize(save_path)
            if size < 1024:
                os.remove(save_path)
                raise ValueError(f"文件太小 ({size} 字节)，可能下载失败")
            return size
        except Exception as e:
            if os.path.exists(save_path):
                os.remove(save_path)
            if attempt == retry - 1:
                raise
            time.sleep(3)
    return 0


def fetch_all_announcements(stock_code, org_id, plate, category):
    """分页获取全部公告列表"""
    all_items = []
    page = 1
    while True:
        payload = {
            "stock": f"{stock_code},{org_id}",
            "searchkey": "",
            "plate": plate,
            "category": category,
            "tabName": "fulltext",
            "pageSize": 30,
            "pageNum": page,
            "column": plate,
            "sortName": "",
            "sortType": "",
            "clusterFlag": "true",
        }
        try:
            result = http_post(QUERY_API, payload)
        except Exception as e:
            print(f"    [警告] 第{page}页请求失败: {e}")
            break

        announcements = result.get("announcements") or []
        all_items.extend(announcements)

        total_pages = result.get("totalPageNum", 1)
        if page >= total_pages or not announcements:
            break
        page += 1
        time.sleep(0.5)

    return all_items


def parse_year_from_title(title):
    """从公告标题中解析报告年份"""
    # 优先匹配 "2024年度报告"、"2023年年度报告" 中的年份
    years = re.findall(r'(20\d{2})', title or "")
    if years:
        return int(years[0])
    return None


def get_quarter_label(title):
    """从季度报告标题中提取季度标签（第一季度报告 / 第三季度报告）"""
    if "第一季度" in title or "一季报" in title or "一季度" in title:
        return "第一季度报告"
    elif "第三季度" in title or "三季报" in title or "三季度" in title:
        return "第三季度报告"
    return "季度报告"


def is_target_report(title, report_type):
    """
    判断是否为目标报告（排除摘要、英文版、修订等附属文件）
    """
    title = title or ""

    # 排除非正文文件
    exclude_keywords = ["摘要", "英文", "更新", "补充", "修订", "修正", "说明", "更正",
                        "英文版", "全文(英文)", "英文年报"]
    for kw in exclude_keywords:
        if kw in title:
            return False

    if report_type == "annual":
        # 匹配：年度报告（包含"年度报告"或"年报"，不含半年）
        return (("年度报告" in title or "年报" in title) and "半年" not in title
                and "中期" not in title)
    elif report_type == "semi":
        # 匹配：半年度报告 / 中期报告
        return "半年度报告" in title or "半年报" in title or "中期报告" in title
    elif report_type == "quarterly":
        # 匹配：季度报告（一季报或三季报），排除年报/半年报
        if ("年度报告" in title or "年报" in title or
            "半年度报告" in title or "半年报" in title or "中期报告" in title):
            return False
        return ("第一季度" in title or "一季报" in title or "一季度" in title or
                "第三季度" in title or "三季报" in title or "三季度" in title)

    return False


def build_pdf_url(ann):
    """从公告记录构建 PDF 下载 URL"""
    path = ann.get("adjunctUrl", "")
    if path:
        return FILE_BASE_URL + path.lstrip("/")
    return None


def download_reports(stock_code, org_id, plate, start_year, end_year,
                     report_type, save_dir, bank_name):
    """主下载逻辑，返回 (success_list, failed_list, skipped_list)"""
    os.makedirs(save_dir, exist_ok=True)

    types_to_download = []
    if report_type in ("all", "annual"):
        types_to_download.append("annual")
    if report_type in ("all", "semi"):
        types_to_download.append("semi")
    if report_type in ("all", "quarterly"):
        types_to_download.append("quarterly")

    type_label = {"annual": "年度报告", "semi": "半年度报告", "quarterly": "季度报告"}

    success_list = []
    failed_list  = []
    skipped_list = []

    for rtype in types_to_download:
        category = CATEGORY_MAP[rtype]
        print(f"\n── 获取{type_label[rtype]}列表 (category={category}) ──")

        announcements = fetch_all_announcements(stock_code, org_id, plate, category)
        print(f"  共获取到 {len(announcements)} 条公告记录")

        # 筛选目标年份范围内的正文报告
        matched = []
        for ann in announcements:
            title = ann.get("announcementTitle", "")
            if not is_target_report(title, rtype):
                continue
            year = parse_year_from_title(title)
            if year and start_year <= year <= end_year:
                matched.append((year, title, ann))

        # 按年份降序，同年取最新一条（季度报告按年份+季度去重）
        matched.sort(key=lambda x: (x[0], x[2].get("announcementTime", "")), reverse=True)
        seen_keys = set()
        unique_matched = []
        for year, title, ann in matched:
            if rtype == "quarterly":
                key = (year, get_quarter_label(title))
            else:
                key = year
            if key not in seen_keys:
                seen_keys.add(key)
                unique_matched.append((year, title, ann))

        print(f"  筛选后目标报告: {len(unique_matched)} 份")

        missing_years = set(range(start_year, end_year + 1)) - {y for y, _, _ in unique_matched}
        if missing_years:
            print(f"  [提示] 以下年份未找到{type_label[rtype]}: {sorted(missing_years)}")
            for y in sorted(missing_years):
                failed_list.append({"label": f"{y}年{type_label[rtype]}", "reason": "公告列表中未找到"})

        # 开始下载
        for year, title, ann in unique_matched:
            if rtype == "quarterly":
                quarter = get_quarter_label(title)
                label = f"{year}年{quarter}"
            else:
                label = f"{year}年{type_label[rtype]}"
            name_prefix = f"{bank_name}_" if bank_name else ""
            save_path = os.path.join(save_dir, f"{name_prefix}{label}.pdf")

            # 已存在则跳过
            if os.path.exists(save_path) and os.path.getsize(save_path) > 10240:
                size = os.path.getsize(save_path)
                print(f"  [跳过] {label} 已存在 ({size/1024/1024:.2f} MB)")
                skipped_list.append({"label": label, "path": save_path})
                success_list.append({"label": label, "path": save_path, "size": size})
                continue

            pdf_url = build_pdf_url(ann)
            if not pdf_url:
                print(f"  [失败] {label}: 无法获取PDF链接 (title={title})")
                failed_list.append({"label": label, "reason": "无PDF链接"})
                continue

            print(f"  [下载] {label}")
            print(f"    原标题: {title}")
            print(f"    URL:    {pdf_url}")
            try:
                size = http_get_file(pdf_url, save_path)
                print(f"    ✓ 完成 ({size/1024/1024:.2f} MB)  →  {save_path}")
                success_list.append({"label": label, "path": save_path, "size": size})
            except Exception as e:
                print(f"    ✗ 失败: {e}")
                failed_list.append({"label": label, "reason": str(e)})

            time.sleep(1)

    return success_list, failed_list, skipped_list


def main():
    parser = argparse.ArgumentParser(
        description="从巨潮资讯网下载上市银行定期报告（年报/半年报/季报）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 下载某某银行 2020-2025 年所有定期报告
  python3 download_reports.py --stock-code 601818 --org-id 9900006246 \\
      --start-year 2020 --end-year 2025 --bank-name 某某银行

  # 只下载某甲银行 2021-2023 年年度报告
  python3 download_reports.py --stock-code 600036 --org-id gssh0600036 \\
      --start-year 2021 --end-year 2023 --report-type annual --bank-name 某甲银行

  # 下载深交所上市银行（某乙银行）
  python3 download_reports.py --stock-code 000001 --org-id gssz0000001 \\
      --start-year 2020 --end-year 2024 --plate szse --bank-name 某乙银行

  # 只下载2026年季度报告（一季报）
  python3 download_reports.py --stock-code 601818 --org-id 9900006246 \\
      --start-year 2026 --end-year 2026 --report-type quarterly --bank-name 某某银行
        """
    )
    parser.add_argument("--stock-code", "-c", required=True,
                        help="股票代码，如 601818")
    parser.add_argument("--org-id",     "-o", required=True,
                        help="巨潮机构ID，如 9900006246 或 gssh0600036")
    parser.add_argument("--start-year", "-s", type=int, required=True,
                        help="起始年份（含），如 2020")
    parser.add_argument("--end-year",   "-e", type=int, required=True,
                        help="结束年份（含），如 2025")
    parser.add_argument("--save-dir",   "-d", default="./bank_reports",
                        help="PDF保存目录（默认: ./bank_reports）")
    parser.add_argument("--report-type", "-t",
                        choices=["all", "annual", "semi", "quarterly"], default="all",
                        help="报告类型: all全部 / annual仅年报 / semi仅半年报 / quarterly仅季度报告（默认: all）")
    parser.add_argument("--plate", "-p",
                        choices=["sse", "szse", "hk"], default="sse",
                        help="上市市场: sse上交所 / szse深交所 / hk港交所（默认: sse）")
    parser.add_argument("--bank-name", "-n", default="",
                        help="银行名称，用于文件命名前缀（可选）")

    args = parser.parse_args()

    if args.start_year > args.end_year:
        print("[错误] --start-year 不能大于 --end-year")
        sys.exit(1)

    print("=" * 60)
    print("巨潮资讯银行报告下载工具")
    print("=" * 60)
    print(f"银行名称:  {args.bank_name or '(未指定)'}")
    print(f"股票代码:  {args.stock_code}")
    print(f"机构ID:    {args.org_id}")
    print(f"年份范围:  {args.start_year} ~ {args.end_year}")
    print(f"报告类型:  {args.report_type}")
    print(f"市场:      {args.plate}")
    print(f"保存目录:  {args.save_dir}")
    print("=" * 60)

    success_list, failed_list, skipped_list = download_reports(
        stock_code=args.stock_code,
        org_id=args.org_id,
        plate=args.plate,
        start_year=args.start_year,
        end_year=args.end_year,
        report_type=args.report_type,
        save_dir=args.save_dir,
        bank_name=args.bank_name,
    )

    # ── 汇总 ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("下载完成！")
    print(f"  成功: {len(success_list)} 份")
    print(f"  失败: {len(failed_list)} 份")
    print(f"  跳过: {len(skipped_list)} 份（已存在）")

    if success_list:
        print("\n成功列表:")
        for item in success_list:
            size_mb = item["size"] / 1024 / 1024
            print(f"  ✓ {item['label']}  ({size_mb:.2f} MB)")
            print(f"    → {item['path']}")

    if failed_list:
        print("\n失败/未找到列表:")
        for item in failed_list:
            print(f"  ✗ {item['label']}: {item['reason']}")

    print("=" * 60)

    # JSON 输出（供 Agent 解析路径后生成下载链接）
    print("\n=== JSON_OUTPUT_START ===")
    print(json.dumps({
        "success":  success_list,
        "failed":   failed_list,
        "skipped":  skipped_list,
        "save_dir": args.save_dir,
    }, ensure_ascii=False, indent=2))
    print("=== JSON_OUTPUT_END ===")

    if failed_list and not success_list:
        sys.exit(1)


if __name__ == "__main__":
    main()
