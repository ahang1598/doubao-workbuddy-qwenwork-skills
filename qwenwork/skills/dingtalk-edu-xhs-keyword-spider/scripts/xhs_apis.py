# encoding: utf-8
"""
小红书PC端API - 精简版（仅包含搜索和笔记详情接口）
基于 Spider_XHS (https://github.com/cv-cat/Spider_XHS) 整合
仅保留本技能所需的核心接口：search_note / search_some_note / get_note_info
"""
import json
import urllib

import requests

from xhs_utils.xhs_util import (
    splice_str,
    generate_request_params,
    generate_search_id,
    generate_x_rap_param,
    get_common_headers,
)
from xhs_utils.http_util import REQUEST_TIMEOUT


def _log_api_error(error):
    return str(error)


def _get_query_params(parsed_url):
    return {
        key: values[-1] if values else ''
        for key, values in urllib.parse.parse_qs(parsed_url.query, keep_blank_values=True).items()
    }


class XHS_Apis():
    def __init__(self):
        self.base_url = "https://edith.xiaohongshu.com"

    def get_note_info(self, url: str, cookies_str: str, proxies: dict = None):
        """
            获取笔记的详细
            :param url: 你想要获取的笔记的url
            :param cookies_str: 你的cookies
            返回笔记的详细
        """
        res_json = None
        try:
            urlParse = urllib.parse.urlparse(url)
            note_id = urlParse.path.split("/")[-1]
            kvDist = _get_query_params(urlParse)
            api = f"/api/sns/web/v1/feed"
            data = {
                "source_note_id": note_id,
                "image_formats": [
                    "jpg",
                    "webp",
                    "avif"
                ],
                "extra": {
                    "need_body_topic": "1"
                },
                "xsec_source": kvDist['xsec_source'] if 'xsec_source' in kvDist else "pc_search",
                "xsec_token": kvDist.get('xsec_token', '')
            }
            headers, cookies, data = generate_request_params(
                cookies_str, api, data, 'POST')
            headers["x-rap-param"] = generate_x_rap_param(api, data)
            headers["xy-direction"] = "13"
            response = requests.post(self.base_url + api, headers=headers, data=data,
                                     cookies=cookies, proxies=proxies, timeout=REQUEST_TIMEOUT)
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = _log_api_error(e)
        return success, msg, res_json

    def search_note(self, query: str, cookies_str: str, page=1, sort_type_choice=0, note_type=0, note_time=0, note_range=0, pos_distance=0, geo="", search_id=None, proxies: dict = None):
        """
            获取搜索笔记的结果
            :param query 搜索的关键词
            :param cookies_str 你的cookies
            :param page 搜索的页数
            :param sort_type_choice 排序方式 0 综合排序, 1 最新, 2 最多点赞, 3 最多评论, 4 最多收藏
            :param note_type 笔记类型 0 不限, 1 视频笔记, 2 普通笔记
            :param note_time 笔记时间 0 不限, 1 一天内, 2 一周内天, 3 半年内
            :param note_range 笔记范围 0 不限, 1 已看过, 2 未看过, 3 已关注
            :param pos_distance 位置距离 0 不限, 1 同城, 2 附近 指定这个必须要指定 geo
            返回搜索的结果
        """
        res_json = None
        sort_type = "general"
        if sort_type_choice == 1:
            sort_type = "time_descending"
        elif sort_type_choice == 2:
            sort_type = "popularity_descending"
        elif sort_type_choice == 3:
            sort_type = "comment_descending"
        elif sort_type_choice == 4:
            sort_type = "collect_descending"
        filter_note_type = "不限"
        if note_type == 1:
            filter_note_type = "视频笔记"
        elif note_type == 2:
            filter_note_type = "普通笔记"
        filter_note_time = "不限"
        if note_time == 1:
            filter_note_time = "一天内"
        elif note_time == 2:
            filter_note_time = "一周内"
        elif note_time == 3:
            filter_note_time = "半年内"
        filter_note_range = "不限"
        if note_range == 1:
            filter_note_range = "已看过"
        elif note_range == 2:
            filter_note_range = "未看过"
        elif note_range == 3:
            filter_note_range = "已关注"
        filter_pos_distance = "不限"
        if pos_distance == 1:
            filter_pos_distance = "同城"
        elif pos_distance == 2:
            filter_pos_distance = "附近"
        if geo:
            geo = json.dumps(geo, separators=(',', ':'))
        try:
            api = "/api/sns/web/v1/search/notes"
            data = {
                "keyword": query,
                "page": page,
                "page_size": 20,
                "search_id": search_id or generate_search_id(),
                "sort": "general",
                "note_type": 0,
                "ext_flags": [],
                "filters": [
                    {
                        "tags": [
                            sort_type
                        ],
                        "type": "sort_type"
                    },
                    {
                        "tags": [
                            filter_note_type
                        ],
                        "type": "filter_note_type"
                    },
                    {
                        "tags": [
                            filter_note_time
                        ],
                        "type": "filter_note_time"
                    },
                    {
                        "tags": [
                            filter_note_range
                        ],
                        "type": "filter_note_range"
                    },
                    {
                        "tags": [
                            filter_pos_distance
                        ],
                        "type": "filter_pos_distance"
                    }
                ],
                "geo": geo,
                "image_formats": [
                    "jpg",
                    "webp",
                    "avif"
                ]
            }
            headers, cookies, data = generate_request_params(
                cookies_str, api, data, 'POST')
            headers["x-rap-param"] = generate_x_rap_param(api, data)
            response = requests.post(self.base_url + api, headers=headers, data=data.encode(
                'utf-8'), cookies=cookies, proxies=proxies, timeout=REQUEST_TIMEOUT)
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = _log_api_error(e)
        return success, msg, res_json

    def search_some_note(self, query: str, require_num: int, cookies_str: str, sort_type_choice=0, note_type=0, note_time=0, note_range=0, pos_distance=0, geo="", proxies: dict = None):
        """
            指定数量搜索笔记，设置排序方式和笔记类型和笔记数量
            :param query 搜索的关键词
            :param require_num 搜索的数量
            :param cookies_str 你的cookies
            :param sort_type_choice 排序方式 0 综合排序, 1 最新, 2 最多点赞, 3 最多评论, 4 最多收藏
            :param note_type 笔记类型 0 不限, 1 视频笔记, 2 普通笔记
            :param note_time 笔记时间 0 不限, 1 一天内, 2 一周内天, 3 半年内
            :param note_range 笔记范围 0 不限, 1 已看过, 2 未看过, 3 已关注
            :param pos_distance 位置距离 0 不限, 1 同城, 2 附近 指定这个必须要指定 geo
            :param geo: 定位信息 经纬度
            返回搜索的结果
        """
        page = 1
        note_list = []
        root_search_id = generate_search_id()
        try:
            while True:
                search_id = generate_search_id(root_search_id)
                success, msg, res_json = self.search_note(
                    query, cookies_str, page, sort_type_choice, note_type, note_time, note_range, pos_distance, geo, search_id, proxies)
                if not success:
                    raise Exception(msg)
                if "items" not in res_json["data"]:
                    break
                notes = res_json["data"]["items"]
                note_list.extend(notes)
                page += 1
                if len(note_list) >= require_num or not res_json["data"]["has_more"]:
                    break
        except Exception as e:
            success = False
            msg = _log_api_error(e)
        if len(note_list) > require_num:
            note_list = note_list[:require_num]
        return success, msg, note_list
