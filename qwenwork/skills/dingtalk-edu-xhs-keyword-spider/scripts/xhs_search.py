#!/usr/bin/env python3
# encoding: utf-8
"""
小红书关键词搜索脚本 - 爬虫代码已内置
功能：搜索指定关键词的笔记，获取详情，输出结构化JSON
"""

from xhs_apis import XHS_Apis
import sys
import os
import json
import argparse

# 将 scripts 目录加入 sys.path，使 xhs_apis / xhs_utils 可被正确导入
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def load_cookies(cookie_path):
    """从文件加载cookie字符串"""
    if not os.path.exists(cookie_path):
        return None
    with open(cookie_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("cookies", "")


def search_notes(query, require_num, cookies_str, sort_type=0, note_type=0,
                 note_time=0, output_path=None):
    """
    搜索小红书笔记
    :param query: 搜索关键词
    :param require_num: 搜索数量
    :param cookies_str: cookie字符串
    :param sort_type: 排序方式 0综合 1最新 2最多点赞 3最多评论 4最多收藏
    :param note_type: 笔记类型 0不限 1视频 2图文
    :param note_time: 时间范围 0不限 1一天内 2一周内 3半年内
    :param output_path: 输出文件路径
    """
    api = XHS_Apis()
    success, msg, notes = api.search_some_note(
        query, require_num, cookies_str,
        sort_type_choice=sort_type,
        note_type=note_type,
        note_time=note_time,
        note_range=0,
        pos_distance=0,
        geo=None,
        proxies=None
    )

    if not success:
        result = {"success": False, "error": msg, "query": query}
    else:
        # 过滤仅保留笔记类型结果
        note_items = [n for n in notes if n.get("model_type") == "note"]
        result_list = []
        for note in note_items:
            item = {
                "note_id": note.get("id", ""),
                "title": note.get("note_card", {}).get("display_title", ""),
                "type": "video" if note.get("note_card", {}).get("type") == "video" else "image",
                "user": {
                    "nickname": note.get("note_card", {}).get("user", {}).get("nickname", ""),
                    "user_id": note.get("note_card", {}).get("user", {}).get("userid", ""),
                },
                "interact_info": {
                    "liked_count": note.get("note_card", {}).get("interact_info", {}).get("liked_count", "0"),
                    "collected_count": note.get("note_card", {}).get("interact_info", {}).get("collected_count", "0"),
                    "comment_count": note.get("note_card", {}).get("interact_info", {}).get("comment_count", "0"),
                    "share_count": note.get("note_card", {}).get("interact_info", {}).get("share_count", "0"),
                },
                "xsec_token": note.get("xsec_token", ""),
                "url": f"https://www.xiaohongshu.com/explore/{note.get('id', '')}?xsec_token={note.get('xsec_token', '')}&xsec_source=pc_search",
            }
            result_list.append(item)

        result = {
            "success": True,
            "query": query,
            "total": len(result_list),
            "notes": result_list
        }

    # 输出结果
    output_json = json.dumps(result, ensure_ascii=False, indent=2)
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"搜索结果已保存至: {output_path}")
    else:
        print(output_json)

    return result


def get_note_detail(note_url, cookies_str, output_path=None):
    """
    获取笔记详情
    :param note_url: 笔记URL
    :param cookies_str: cookie字符串
    :param output_path: 输出文件路径
    """
    api = XHS_Apis()
    success, msg, note_info = api.get_note_info(note_url, cookies_str)

    if not success:
        result = {"success": False, "error": msg, "url": note_url}
    else:
        try:
            data = note_info.get("data", {}).get("items", [{}])[0]
            note_card = data.get("note_card", {})
            result = {
                "success": True,
                "url": note_url,
                "note_id": note_card.get("note_id", ""),
                "title": note_card.get("title", ""),
                "desc": note_card.get("desc", ""),
                "type": note_card.get("type", ""),
                "user": {
                    "nickname": note_card.get("user", {}).get("nickname", ""),
                    "user_id": note_card.get("user", {}).get("userid", ""),
                },
                "interact_info": {
                    "liked_count": note_card.get("interact_info", {}).get("liked_count", "0"),
                    "collected_count": note_card.get("interact_info", {}).get("collected_count", "0"),
                    "comment_count": note_card.get("interact_info", {}).get("comment_count", "0"),
                    "share_count": note_card.get("interact_info", {}).get("share_count", "0"),
                },
                "tag_list": [tag.get("name", "") for tag in note_card.get("tag_list", [])],
                "time": note_card.get("time", ""),
                "last_update_time": note_card.get("last_update_time", ""),
            }
        except (IndexError, KeyError, TypeError) as e:
            result = {"success": False,
                      "error": f"解析笔记详情失败: {e}", "url": note_url}

    output_json = json.dumps(result, ensure_ascii=False, indent=2)
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"笔记详情已保存至: {output_path}")
    else:
        print(output_json)

    return result


def main():
    parser = argparse.ArgumentParser(description="小红书关键词搜索工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # search 子命令
    search_parser = subparsers.add_parser("search", help="搜索小红书笔记")
    search_parser.add_argument("--query", "-q", required=True, help="搜索关键词")
    search_parser.add_argument(
        "--num", "-n", type=int, default=20, help="搜索数量（默认20）")
    search_parser.add_argument("--sort", "-s", type=int, default=0,
                               choices=[0, 1, 2, 3, 4],
                               help="排序方式: 0综合 1最新 2最多点赞 3最多评论 4最多收藏")
    search_parser.add_argument("--type", "-t", type=int, default=0,
                               choices=[0, 1, 2],
                               help="笔记类型: 0不限 1视频 2图文")
    search_parser.add_argument("--time", type=int, default=0,
                               choices=[0, 1, 2, 3],
                               help="时间范围: 0不限 1一天内 2一周内 3半年内")
    search_parser.add_argument("--cookie-file", "-c", default="cookies.json",
                               help="Cookie文件路径（默认cookies.json）")
    search_parser.add_argument("--output", "-o", default=None, help="输出文件路径")

    # detail 子命令
    detail_parser = subparsers.add_parser("detail", help="获取笔记详情")
    detail_parser.add_argument("--url", "-u", required=True, help="笔记URL")
    detail_parser.add_argument("--cookie-file", "-c", default="cookies.json",
                               help="Cookie文件路径（默认cookies.json）")
    detail_parser.add_argument("--output", "-o", default=None, help="输出文件路径")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 加载cookie
    cookie_path = os.path.abspath(args.cookie_file)
    cookies_str = load_cookies(cookie_path)
    if not cookies_str:
        print(json.dumps({
            "success": False,
            "error": f"Cookie文件不存在或为空: {cookie_path}",
            "hint": "请先通过浏览器登录小红书获取Cookie"
        }, ensure_ascii=False))
        sys.exit(1)

    if args.command == "search":
        search_notes(
            query=args.query,
            require_num=args.num,
            cookies_str=cookies_str,
            sort_type=args.sort,
            note_type=args.type,
            note_time=args.time,
            output_path=args.output
        )
    elif args.command == "detail":
        get_note_detail(
            note_url=args.url,
            cookies_str=cookies_str,
            output_path=args.output
        )


if __name__ == "__main__":
    main()
