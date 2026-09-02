#!/usr/bin/env python3
"""
project_matcher.py — 项目名归一化 + 三级匹配

CLI:
  python project_matcher.py --input '<JSON>'
  python project_matcher.py --input-file <path/to/input.json>
  python project_matcher.py --input '<JSON>' --projects-file <path/to/projects.json>

⚠️ 项目列表往往上千条(实测 1710 条), 直接拼进命令行会超出 Windows 8191 字符上限。
   **必须**把 get_project_list 的结果落成临时 JSON 文件, 再用
   `--projects-file` 或入参里的 `projects_file` 传路径。
   (写临时 JSON 文件属于"传参手段", 不属于"自己写匹配脚本"的违规行为)

入参 JSON:
  {
    "texts": { "project_name_raw": "教育扶贫项目", "remarks": "...", "other_info": "..." },
    // 或 "texts": ["教育扶贫项目", "...", "..."]  (按顺序视为 project_name_raw/remarks/other_info)
    "projects": [ { "project_no": "PRJ001", "project_name": "乡村教育扶贫计划" }, ... ],
    // 或 "projects_file": "./_tmp/projects.json"
    "max_results": 20        // 可选, 默认 20
  }

出参 JSON (stdout):
  {
    "success": true,
    "matches": [
      { "project_no": "PRJ001", "project_name": "乡村教育扶贫计划",
        "matched_from": "project_name_raw", "matched_text": "教育扶贫项目",
        "match_type": "substring", "confidence": "medium" }
    ],
    "distinct_project_ids": ["PRJ001"],   // ★ 去重后的项目 ID 集合
    "distinct_count": 1,                  // ★ 判据就是这个数
    "project_id": "PRJ001",               // ★ 直接可填进 filters.project_id
    "project_name_list": ["乡村教育扶贫计划"],  // ★ 进入 UI 的「匹配出项目名」, 与 project_id 对应; ⛔ 非抽取原文
    "best_match": { ... } | null,
    "projects_count": 1710,
    "ambiguous": false,
    "warnings": []
  }

★ project_id 收敛规则(需求方 2026-08-10 确认):

  | distinct_count | project_id | 说明                                  |
  |----------------|------------|---------------------------------------|
  | 0              | `""`       | 无项目信号, 仅按 title + amount 匹配  |
  | **1**          | 该 ID      | 正常路径, 加严匹配                    |
  | > 1            | `""`       | 无法收敛, **不猜**|

  ⚠️ 判据是「**去重后的项目 ID 数量**」, 不是「命中的项目名数量」。
     多个项目名若都指向同一个 ID, 去重后是 1 个 → **应当填入该 ID**。

  ⚠️ 传错的 project_id 会让本该命中的申请单**直接落空**(精确匹配下多一个
     错条件 = 不命中), 比不传更糟。所以 >1 时一律传空。

  ⚠️ `project_id` 对后端是 **nice to have**: 有则加严, 无则不参与过滤。
     传空是安全降级, 不会导致匹配失败。

匹配级别(按优先级):
  1. exact      原文完全相等→ confidence high
  2. normalized 归一化(去空白/标点/全半角/繁简)后相等 → confidence high
  3. substring  归一化后互相包含                    → confidence medium
     ⚠️ substring 是需求方**明确要求**的能力: OCR 提取的项目名常夹带前后缀
        (如 `捐赠项目：乡村教育扶贫计划（2026年度）`), 只做精确匹配会丢掉
        绝大多数票据的项目信号。
     ⚠️ 但归一化后长度 < 3 时**跳过** substring, 防短串命中海量项目。

text 优先级: project_name_raw > remarks > other_info (高优先级命中即不再看低优先级)

  ⚠️ `project_name_list` 是 `MatchItem.project_name_list` 的【唯一】权威来源:
      = 由项目列表匹配出来的项目名(从 `matches` 按 project_no 去重), **不是**票据识别
      的"项目名称"/"备注"原文(那是匹配输入, 只进 `texts`)。未命中(distinct_count=0)
      时为 `[]`, 交用户在 UI 从机构项目库重新选填。

上游接口: `get_project_list`(返回机构全部项目, 与 application_number 无关)
"""
import argparse
import json
import re
import sys
import unicodedata
from typing import List, Optional

TEXT_PRIORITY = ["project_name_raw", "remarks", "other_info"]

PUNCT_PATTERN = re.compile(
    r"[\s\-—_·•、,，.。;；:：/／\\|«»“”\"'’‘()（）\[\]【】{}『』「」<>《》!！?？~～@#$%^&*+=]"
)

# 常见繁体 → 简体(仅覆盖公益项目名高频字, 避免引入 opencc 依赖)
# 用「成对列表」构建, 从结构上排除两串长度不等导致 maketrans 报错的风险
_TRAD_SIMP_PAIRS = [
    ("愛", "爱"), ("幫", "帮"), ("報", "报"), ("備", "备"), ("補", "补"), ("參", "参"),
    ("產", "产"), ("長", "长"), ("車", "车"), ("處", "处"), ("創", "创"), ("辦", "办"),
    ("邊", "边"), ("變", "变"), ("場", "场"), ("誠", "诚"), ("傳", "传"), ("從", "从"),
    ("達", "达"), ("帶", "带"), ("單", "单"), ("當", "当"), ("黨", "党"), ("導", "导"),
    ("燈", "灯"), ("點", "点"), ("電", "电"), ("動", "动"), ("讀", "读"), ("獨", "独"),
    ("對", "对"), ("隊", "队"), ("兒", "儿"), ("發", "发"), ("飛", "飞"), ("費", "费"),
    ("豐", "丰"), ("風", "风"), ("婦", "妇"), ("復", "复"), ("剛", "刚"), ("鋼", "钢"),
    ("個", "个"), ("給", "给"), ("觀", "观"), ("館", "馆"), ("廣", "广"), ("規", "规"),
    ("國", "国"), ("過", "过"), ("漢", "汉"), ("號", "号"), ("護", "护"), ("華", "华"),
    ("懷", "怀"), ("歡", "欢"), ("環", "环"), ("還", "还"), ("會", "会"), ("機", "机"),
    ("積", "积"), ("級", "级"), ("極", "极"), ("際", "际"), ("繼", "继"), ("價", "价"),
    ("堅", "坚"), ("間", "间"), ("檢", "检"), ("見", "见"), ("講", "讲"), ("獎", "奖"),
    ("節", "节"), ("結", "结"), ("進", "进"), ("盡", "尽"), ("經", "经"), ("舊", "旧"),
    ("據", "据"), ("開", "开"), ("課", "课"), ("樂", "乐"), ("類", "类"), ("離", "离"),
    ("裡", "里"), ("歷", "历"), ("麗", "丽"), ("連", "连"), ("煉", "炼"), ("練", "练"),
    ("糧", "粮"), ("兩", "两"), ("療", "疗"), ("靈", "灵"), ("領", "领"), ("龍", "龙"),
    ("樓", "楼"), ("陸", "陆"), ("論", "论"), ("羅", "罗"), ("媽", "妈"), ("馬", "马"),
    ("買", "买"), ("賣", "卖"), ("滿", "满"), ("夢", "梦"), ("難", "难"), ("腦", "脑"),
    ("內", "内"), ("寧", "宁"), ("農", "农"), ("盤", "盘"), ("貧", "贫"), ("憑", "凭"),
    ("齊", "齐"), ("啟", "启"), ("氣", "气"), ("錢", "钱"), ("親", "亲"), ("輕", "轻"),
    ("慶", "庆"), ("窮", "穷"), ("區", "区"), ("權", "权"), ("讓", "让"), ("認", "认"),
    ("榮", "荣"), ("賽", "赛"), ("傷", "伤"), ("設", "设"), ("聲", "声"), ("師", "师"),
    ("時", "时"), ("實", "实"), ("識", "识"), ("勢", "势"), ("壽", "寿"), ("書", "书"),
    ("術", "术"), ("樹", "树"), ("數", "数"), ("雙", "双"), ("順", "顺"), ("說", "说"),
    ("歲", "岁"), ("孫", "孙"), ("態", "态"), ("談", "谈"), ("題", "题"), ("體", "体"),
    ("條", "条"), ("鐵", "铁"), ("聽", "听"), ("統", "统"), ("頭", "头"), ("圖", "图"),
    ("團", "团"), ("萬", "万"), ("網", "网"), ("為", "为"), ("維", "维"), ("衛", "卫"),
    ("溫", "温"), ("問", "问"), ("務", "务"), ("習", "习"), ("係", "系"), ("鄉", "乡"),
    ("項", "项"), ("興", "兴"), ("學", "学"), ("陽", "阳"), ("養", "养"), ("業", "业"),
    ("醫", "医"), ("義", "义"), ("藝", "艺"), ("陰", "阴"), ("應", "应"), ("營", "营"),
    ("優", "优"), ("與", "与"), ("園", "园"), ("願", "愿"), ("遠", "远"), ("運", "运"),
    ("災", "灾"), ("則", "则"), ("戰", "战"), ("張", "张"), ("長", "长"), ("這", "这"),
    ("誌", "志"), ("質", "质"), ("鐘", "钟"), ("種", "种"), ("眾", "众"), ("週", "周"),
    ("專", "专"), ("轉", "转"), ("莊", "庄"), ("資", "资"), ("總", "总"), ("組", "组"),
    # 公益项目名高频补充批
    ("計", "计"), ("劃", "划"), ("測", "测"), ("試", "试"), ("關", "关"), ("濟", "济"),
    ("貴", "贵"), ("標", "标"), ("準", "准"), ("織", "织"), ("藥", "药"), ("診", "诊"),
    ("幣", "币"), ("贈", "赠"), ("獻", "献"), ("齡", "龄"), ("殘", "残"), ("錄", "录"),
    ("線", "线"), ("絡", "络"), ("財", "财"), ("稅", "税"), ("額", "额"), ("銀", "银"),
    ("錦", "锦"), ("綠", "绿"), ("藍", "蓝"), ("紅", "红"), ("黃", "黄"), ("蘇", "苏"),
    ("縣", "县"), ("鎮", "镇"), ("鳳", "凤"), ("鵬", "鹏"), ("綜", "综"), ("傑", "杰"),
    ("億", "亿"), ("淨", "净"), ("潔", "洁"), ("廠", "厂"), ("擔", "担"), ("擁", "拥"),
    ("擴", "扩"), ("攝", "摄"), ("檔", "档"), ("歸", "归"), ("監", "监"), ("禮", "礼"),
    ("穩", "稳"), ("競", "竞"), ("筆", "笔"), ("簡", "简"), ("籃", "篮"), ("籌", "筹"),
    ("紀", "纪"), ("納", "纳"), ("純", "纯"), ("紙", "纸"), ("緊", "紧"), ("紹", "绍"),
    ("細", "细"), ("終", "终"), ("絕", "绝"), ("綱", "纲"), ("緣", "缘"), ("編", "编"),
    ("緩", "缓"), ("縮", "缩"), ("績", "绩"), ("繳", "缴"), ("續", "续"), ("纖", "纤"),
]
TRAD_TO_SIMP = str.maketrans(
    "".join(t for t, _ in _TRAD_SIMP_PAIRS),
    "".join(s for _, s in _TRAD_SIMP_PAIRS),
)


def normalize(text: str) -> str:
    """归一化: 全半角统一 →繁转简 → 去标点空白 → 小写。"""
    if not text:
        return ""
    s = unicodedata.normalize("NFKC", str(text))
    s = s.translate(TRAD_TO_SIMP)
    s = PUNCT_PATTERN.sub("", s)
    return s.lower()


def _pick(d: dict, keys) -> str:
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return str(v)
    return ""


def _normalize_projects(projects: List[dict]) -> List[dict]:
    """兼容 get_project_list 的多种字段命名。

    ⚠️ 出参统一叫 `project_no`, 但它**就是** `filters.project_id` 要填的值 ——
       两侧字段名不同, 语义相同, 不要以为是两个东西。
    """
    out = []
    for p in projects:
        if not isinstance(p, dict):
            continue
        pid = _pick(p, ("project_no", "project_id", "projectId", "id", "no"))
        pname = _pick(p, ("project_name", "projectName", "name", "title"))
        if not pname:
            continue
        out.append({"project_no": pid, "project_name": pname, "_norm": normalize(pname)})
    return out


def _normalize_texts(texts) -> List[tuple]:
    """统一成 [(source_name, raw_text), ...], 按优先级排序。"""
    pairs = []
    if isinstance(texts, dict):
        for key in TEXT_PRIORITY:
            v = texts.get(key)
            if v:
                pairs.append((key, str(v)))
        for key, v in texts.items():
            if key not in TEXT_PRIORITY and v:
                pairs.append((key, str(v)))
    elif isinstance(texts, list):
        for idx, v in enumerate(texts):
            if v:
                name = TEXT_PRIORITY[idx] if idx < len(TEXT_PRIORITY) else f"text_{idx}"
                pairs.append((name, str(v)))
    elif texts:
        pairs.append(("project_name_raw", str(texts)))
    return pairs


def match_projects(texts, projects: List[dict], max_results: int = 20) -> List[dict]:
    """三级匹配: exact → normalized → substring。高优先级 text 命中后不再看低优先级。"""
    norm_projects = _normalize_projects(projects)
    text_pairs = _normalize_texts(texts)

    for source, raw_text in text_pairs:
        norm_text = normalize(raw_text)
        if not norm_text:
            continue

        exact, normalized_hit, substring = [], [], []
        for p in norm_projects:
            item = {
                "project_no": p["project_no"],
                "project_name": p["project_name"],
                "matched_from": source,
                "matched_text": raw_text,
            }
            if p["project_name"] == raw_text:
                exact.append(dict(item, match_type="exact", confidence="high"))
            elif p["_norm"] == norm_text:
                normalized_hit.append(dict(item, match_type="normalized", confidence="high"))
            elif len(norm_text) >= 3 and (
                (len(p["_norm"]) >= 3 and norm_text in p["_norm"])
                or (len(p["_norm"]) >= 3 and p["_norm"] in norm_text)
            ):
                # 归一化文本过短(<3)时不做包含匹配, 否则会命中海量无关项目;
                # 项目名也须 >=3, 防止单字符/超短项目名(如测试数据 "1")被任意含该字符的文本误命中
                substring.append(dict(item, match_type="substring", confidence="medium"))

        for bucket in (exact, normalized_hit, substring):
            if bucket:
                bucket.sort(key=lambda x: len(x["project_name"]))
                return bucket[:max_results]

    return []


def _distinct_ids(matches: List[dict]) -> List[str]:
    """去重后的项目 ID 集合(保持首次出现顺序)。空 ID 不计入。"""
    seen, out = set(), []
    for m in matches:
        pid = str(m.get("project_no") or "")
        if pid and pid not in seen:
            seen.add(pid)
            out.append(pid)
    return out


def _resolve_project_id(distinct: List[str], warnings: List[str]) -> str:
    """按「去重后的项目 ID 数量」三分支决定 filters.project_id。"""
    if len(distinct) == 1:
        return distinct[0]
    if not distinct:
        warnings.append(
            "未匹配到项目 ID, project_id 传空字符串"
            "(project_id 对后端是 nice to have, 传空不影响 title+amount 精确匹配)"
        )
    else:
        warnings.append(
            f"去重后命中 {len(distinct)} 个不同项目 ID, 无法收敛, project_id 传空字符串; "
            "严禁从中任选一个 —— 传错会让本该命中的申请单直接落空"
        )
    return ""


def _empty_result(projects_count: int, warnings: List[str]) -> dict:
    return {
        "success": True,
        "matches": [],
        "distinct_project_ids": [],
        "distinct_count": 0,
        "project_id": "",
        "project_name_list": [],  # ★ 未命中即空, 交用户在 UI 从机构项目库选填
        "best_match": None,
        "projects_count": projects_count,
        "ambiguous": False,
        "warnings": warnings,
    }


def _build_project_name_list(matches: List[dict]) -> List[str]:
    """由 matches 去重得到「匹配出的项目名」列表(按命中顺序)。

    这是 `MatchItem.project_name_list` 的【唯一】权威来源——只放**从项目列表
    匹配出来**的项目名, ⛔ 不放票据识别的 "项目名称"/"备注" 原文(那是匹配输入)。
    去重以 project_no 为基准(同一项目被多路文本命中只算一次)。
    """
    seen, out = set(), []
    for m in matches:
        no = m.get("project_no")
        name = m.get("project_name")
        if name and no not in seen:
            seen.add(no)
            out.append(name)
    return out


def process(input_data: dict, projects_file: Optional[str] = None) -> dict:
    texts = input_data.get("texts", {})
    projects = input_data.get("projects") or []
    warnings = []

    path = projects_file or input_data.get("projects_file")
    if path:
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                loaded = loaded.get("list") or loaded.get("projects") or loaded.get("data") or []
            if isinstance(loaded, list):
                projects = loaded
            else:
                warnings.append(f"projects_file 内容不是数组: {path}")
        except (OSError, json.JSONDecodeError) as e:
            return {
                "success": False,
                "error": f"读取 projects_file 失败: {e}",
                "projects_file": path,
            }

    if not projects:
        return _empty_result(0, warnings + ["projects 列表为空, 无法匹配"])

    if not _normalize_texts(texts):
        return _empty_result(len(projects), warnings + ["texts 为空, 无可匹配文本"])

    try:
        max_results = int(input_data.get("max_results") or 20)
        matches = match_projects(texts, projects, max_results)
    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": f"匹配失败: {e}", "input_keys": list(input_data.keys())}

    distinct = _distinct_ids(matches)
    project_id = _resolve_project_id(distinct, warnings)
    project_name_list = _build_project_name_list(matches)

    if len(matches) > 1 and len(distinct) == 1:
        warnings.append(
            f"命中 {len(matches)} 条项目名但去重后只有 1 个 ID, 按规则应当填入该 ID: {distinct[0]}"
        )

    return {
        "success": True,
        "matches": matches,
        "distinct_project_ids": distinct,
        "distinct_count": len(distinct),
        "project_id": project_id,
        "project_name_list": project_name_list,
        "best_match": matches[0] if len(distinct) == 1 else None,
        "projects_count": len(projects),
        "ambiguous": len(distinct) > 1,
        "warnings": warnings,
    }


def _load_input(args) -> dict:
    if args.input_file:
        with open(args.input_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(args.input)


def main():
    # ⚠️ Windows 实测: stdout 为管道时用 locale 编码(GBK), 中文 JSON 会写成 GBK 字节,
    #    UTF-8 读取方直接 UnicodeDecodeError。项目名必然含中文, 必须显式改 UTF-8。
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="JSON 格式的入参")
    parser.add_argument("--input-file", dest="input_file", help="入参 JSON 文件路径")
    parser.add_argument(
        "--projects-file",
        dest="projects_file",
        help="项目列表 JSON 文件路径(推荐, 避免命令行长度超限)",
    )
    args = parser.parse_args()

    if not args.input and not args.input_file:
        print(
            json.dumps({"success": False, "error": "必须提供 --input 或 --input-file"}),
            flush=True,
        )
        sys.exit(1)

    try:
        input_data = _load_input(args)
    except (json.JSONDecodeError, OSError) as e:
        print(
            json.dumps({"success": False, "error": f"入参非合法 JSON: {e}"}, ensure_ascii=False),
            flush=True,
        )
        sys.exit(1)

    result = process(input_data, args.projects_file)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
