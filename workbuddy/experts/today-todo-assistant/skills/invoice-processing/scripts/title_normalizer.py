#!/usr/bin/env python3
"""
title_normalizer.py — 抬头归一化 + 申请单独占顺序分配 + 提交剔除

三个 mode, 对应 SOP 的环节:

| mode        | 时机                     | 作用                                              |
|-------------|--------------------------|---------------------------------------------------|
| `normalize` | Step 5.4 (送匹配之前)    | 输出归一化抬头, 供构造 `filters`|
| `allocate`  | Step 6 (拿到回包之后)    | 反向映射 + m:n 独占顺序分配 + 组装 `UiReq`        |
| `prune`     | 「提交票据到远程」步骤   | 剔除已提交项 |

CLI:
  python title_normalizer.py --input '<JSON>'
  python title_normalizer.py --input-file <path/to/input.json>

⚠️ 多张(>1 张)时**建议**用 `--input-file`: 2000 张票据的 JSON 会超出
   Windows 8191 字符命令行上限。候选池(`pending_list`)也**必须**走
   `--candidates-file`, 它可能有上千行, 直接进 agent 上下文会 token 爆表。

═══════════════════════════════════════════════════════════════════════════
mode = normalize
═══════════════════════════════════════════════════════════════════════════
入参:
  {
    "mode": "normalize",
    "items": [ { "seq": 1, "title": "深圳市腾讯公益慈善基金會", "amount": 33000 } ]
  }
出参:
  {
    "success": true,
    "mode": "normalize",
    "items": [ { "seq": 1, "title": "...原样...", "title_normalized": "深圳市腾讯公益慈善基金会",
                 "changed": true, "ops": ["whitespace", "fullwidth", "traditional"] } ]
  }

⛔ 归一化**只做格式层等价变换**: 空白折叠 / 全半角统一(NFKC) / 繁转简。
   **严禁**截短、去除"深圳市"等前缀、同义替换 —— 那会改变抬头实质内容,
   导致绑错申请单。见 SKILL.md 门禁与 invoice-matching spec。

═══════════════════════════════════════════════════════════════════════════
mode = allocate
═══════════════════════════════════════════════════════════════════════════
入参:
  {
    "mode": "allocate",
    "org_no": "org_123",
    "items": [
      { "seq": 1, "md5": "ab12...", "invoice_url": "https://cdn/x.pdf",
        "title": "深圳市腾讯公益慈善基金会", "amount": 33000,
        "project_name_list": ["乡村教育扶贫计划"],
        "project_id": "PRJ001",           // ★ 可选, project_matcher.py 收敛后的结果
        "md5_duplicate": false, "duplicate_of_seq": null,
        "incomplete": false }
    ],
    "pending_list": [
      { "application_number": "AP001", "title": "...", "amount": 33000,
        "project_id": "PRJ001" }          // ★ 可选; 后端尚未支持时不传, 自动降级
    ],
    "success_list": [ { "application_number": "AP900", "title": "...", "amount": 33000 } ],
    "candidates_file": "./_tmp/session_x/candidates.json",   // 与上两个字段二选一
    "output_items_file": "./_tmp/session_x/items.json",
    "expected_total": 20// 可选, 条数守恒断言
  }

★ project_id 加严匹配(2026-08-10 真实票据实测追加):
  同一捐款人同一天给同一机构捐同一金额但**不同项目**的多张票, 仅靠
  (title, amount) 无法区分该绑哪个 application_number, 而候选行返回顺序
  不保证与上传顺序一致, 盲目按顺序分配存在**静默绑错**的风险。

  一旦 pending_list 的某一行带有 project_id/project_no 字段(需求方已推动
  后端补齐,尚未上线), 本脚本会自动启用**项目子队列**分配: 本票据有
  project_id 就只吃同project_id 的候选行, 没有 project_id 就只吃没打
  project_id 标记的候选行, 绝不跨项目瞎猜。候选行**完全没有** project_id
  时自动退回原有纯 (title, amount) 池式分配, 向后兼容, 不影响任何既有单测。

  items[].project_id 的来源就是 Step 5.4 project_matcher.py 已经产出的
  `project_id`(按「去重后 ID 数量 0/1/>1」收敛的结果), **不需要**额外计算,
  直接把已有值透传进来即可。

出参:
  {
    "success": true, "mode": "allocate",
    "summary": { "total": 20, "matched": 14, "failed": 6,
                 "failed_breakdown": { "no_match": 3, "occupied": 1,
                                       "submitted": 1, "md5_duplicate": 1, "incomplete": 0 } },
    "items_file": "./_tmp/session_x/items.json",
    "ui_req": { "org_no": "...", "matched_items": [...], "matched_failed_items": [...],
                "submit": { "next_step": "使用提交票据到远程步骤, ..." } },
    "assertions": { "list_self_consistent": true, "conservation": true, "identity": true },
    "duplicates": [ { "seq": 7, "duplicate_of_seq": 3 } ],     // 供对话告知, 不进UI
    "warnings": []
  }

★ui_req.submit: 固定的自然语言续接Prompt, 由本脚本统一写入,⛔ agent 不得自行
  拼装或改写。UI 内直接完成提交后, 把文案连同「已提交成功的 pdf 链接列表」一并
  交还 Host, Host 依据文案里的步骤名重新调度 invoice-expert 执行「提交票据到远程」。
  不存在旧版 submit.target_expert_name / submit.next_skill_step 这些结构化字段,
  也不存在 next_step_modify。

═══════════════════════════════════════════════════════════════════════════
mode = prune
═══════════════════════════════════════════════════════════════════════════
入参:
  {
    "mode": "prune",
    "org_no": "org_123",
    "items_file": "./_tmp/session_x/items.json",        // 既有全量结果(必填)
    "submitted_invoice_urls": [ "https://cdn/x.pdf", ... ],  // UI 回传的已提交成功 pdf 链接
    "output_items_file": "./_tmp/session_x/items.json"
  }

行为:
  1. 从 items_file 读既有全量结果(**剔除由脚本读盘完成, 不经 agent 上下文**)
  2. 以 `invoice_url` 为唯一键, 剔除出现在 submitted_invoice_urls 里的项
  3. 写回 output_items_file
  4. 返回 removed_count(已提交数) / remaining_count(剩余数), 供 Agent 告知用户
     "已提交 X 条, 剩余 Y 条"(UI 侧已自行刷新展示剩余, 无需重新呼起 UI)

═══════════════════════════════════════════════════════════════════════════
match_status_reason 五种文案(见 invoice-matching spec)
═══════════════════════════════════════════════════════════════════════════
| 来源                | 文案                                   |
|-------------------------------|----------------------------------------|
| pending_list 无命中           | 识别的信息匹配不到待开票记录           |
| 候选行被同组前序票占用        | 已经有别的票据匹配上了                 |
| 命中 success_list             | 该票据对应的开票申请已提交             |
| 本批 md5 重复                 | 存在相同文件|
| 抬头缺失 / 金额换算失败       | 票据信息识别不完整, 请补填后重新匹配   |

参考: ../SKILL.md Step 5.4 / Step 6
"""
import argparse
import json
import os
import re
import sys
import unicodedata
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# match_status / reason 常量
# ---------------------------------------------------------------------------
MATCHED = 1
FAILED = 2

REASON_NO_MATCH = "识别的信息匹配不到待开票记录"
REASON_OCCUPIED = "已经有别的票据匹配上了"
REASON_SUBMITTED = "该票据对应的开票申请已提交"
REASON_DUPLICATE_FILE = "存在相同文件"
REASON_INCOMPLETE = "票据信息识别不完整, 请补填后重新匹配"

# ui_req.submit 的固定续接Prompt。
# ⛔ 固定文案, 不做参数化, 不由 agent 拼装——UI 结束时把文案连同已提交清单
# 一并交还 Host, Host 据此重新调度 invoice-expert 执行文案里点名的步骤。
# 提交在 UI 内直接完成, 无 next_step_modify。
SUBMIT_NEXT_STEP = "使用提交票据到远程步骤，剔除本地已提交项"

_REASON_TO_BUCKET = {
    REASON_NO_MATCH: "no_match",
    REASON_OCCUPIED: "occupied",
    REASON_SUBMITTED: "submitted",
    REASON_DUPLICATE_FILE: "md5_duplicate",
    REASON_INCOMPLETE: "incomplete",
}

# UI 协议(MatchItem)允许的字段, 多一个都不许出现
MATCH_ITEM_FIELDS = (
    "status",
    "invoice_url",
    "title",
    "amount",
    "project_name_list",
    "match_status",
    "match_status_reason",
    "application_number",
    "modify_status",
)

# ---------------------------------------------------------------------------
# 归一化: 只做格式层等价变换
# ---------------------------------------------------------------------------
_WS_PATTERN = re.compile(r"\s+")

# 常见繁体 → 简体(与 project_matcher.py 共用同一张表, 用「成对列表」构建,
# 从结构上排除两串长度不等导致 maketrans 报错的风险)
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
    ("災", "灾"), ("則", "则"), ("戰", "战"), ("張", "张"), ("這", "这"), ("誌", "志"),
    ("質", "质"), ("鐘", "钟"), ("種", "种"), ("眾", "众"), ("週", "周"), ("專", "专"),
    ("轉", "转"), ("莊", "庄"), ("資", "资"), ("總", "总"), ("組", "组"),
    # 机构抬头高频补充批
    ("計", "计"), ("劃", "划"), ("關", "关"), ("濟", "济"), ("貴", "贵"), ("標", "标"),
    ("準", "准"), ("織", "织"), ("藥", "药"), ("幣", "币"), ("贈", "赠"), ("獻", "献"),
    ("線", "线"), ("絡", "络"), ("財", "财"), ("稅", "税"), ("額", "额"), ("銀", "银"),
    ("錦", "锦"), ("綠", "绿"), ("藍", "蓝"), ("紅", "红"), ("黃", "黄"), ("蘇", "苏"),
    ("縣", "县"), ("鎮", "镇"), ("鳳", "凤"), ("鵬", "鹏"), ("綜", "综"), ("傑", "杰"),
    ("億", "亿"), ("淨", "净"), ("潔", "洁"), ("廠", "厂"), ("擔", "担"), ("擁", "拥"),
    ("擴", "扩"), ("歸", "归"), ("監", "监"), ("禮", "礼"), ("競", "竞"), ("簡", "简"),
    ("紀", "纪"), ("納", "纳"), ("純", "纯"), ("紙", "纸"), ("紹", "绍"), ("細", "细"),
    ("終", "终"), ("綱", "纲"), ("緣", "缘"), ("編", "编"), ("績", "绩"), ("續", "续"),
]
TRAD_TO_SIMP = str.maketrans(
    "".join(t for t, _ in _TRAD_SIMP_PAIRS),
    "".join(s for _, s in _TRAD_SIMP_PAIRS),
)


def normalize_title(text: str) -> Tuple[str, List[str]]:
    """抬头归一化, 返回 (归一化结果, 生效的变换列表)。

    只做三类**格式层等价变换**:
      1. whitespace   去首尾空白 + 中间连续空白折叠为空(中文抬头内的空格是排版产物)
      2. fullwidth    NFKC 统一全半角(全角数字/字母/括号 → 半角)
      3. traditional  繁体 → 简体

    ⛔ 不做: 截短 / 去前缀 / 同义替换 / 去标点 / 大小写折叠。
       抬头是绑定申请单的凭据, 任何实质性变换都可能绑错单。
    """
    if not text:
        return "", []
    original = str(text)
    ops = []

    s = unicodedata.normalize("NFKC", original)
    if s != original:
        ops.append("fullwidth")

    before_trad = s
    s = s.translate(TRAD_TO_SIMP)
    if s != before_trad:
        ops.append("traditional")

    before_ws = s
    s = _WS_PATTERN.sub("", s.strip())
    if s != before_ws:
        ops.append("whitespace")

    return s, ops


def _norm_key(text: str) -> str:
    return normalize_title(text)[0]


# ---------------------------------------------------------------------------
# 入参解析
# ---------------------------------------------------------------------------
def _as_int_cents(value) -> Optional[int]:
    """金额必须是 uint32 分。字符串数字也接受(协议改造过渡期), 但拒绝小数。"""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    s = str(value).strip()
    if not re.fullmatch(r"\d+", s):
        return None
    return int(s)


def _read_json_file(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_candidates(input_data: dict, candidates_file: Optional[str]) -> Tuple[List[dict], List[dict], List[str]]:
    """候选池优先走文件(token 治理: 上千行候选池不得进 agent 上下文)。"""
    warnings: List[str] = []
    pending = input_data.get("pending_list") or []
    success = input_data.get("success_list") or []

    path = candidates_file or input_data.get("candidates_file")
    if path:
        loaded = _read_json_file(path)
        if isinstance(loaded, dict):
            pending = loaded.get("pending_list") or []
            success = loaded.get("success_list") or []
        elif isinstance(loaded, list):
            pending = loaded
            warnings.append(f"candidates_file 是裸数组, 视为 pending_list: {path}")
    return list(pending), list(success), warnings


def _index_rows(rows: List[dict]) -> Dict[Tuple[str, int], List[dict]]:
    """把扁平候选池按 (归一化 title, amount) 建索引; 附带每行的 project_id(若有)。

    ⚠️ 不假设 pending_list[i] 对应 filters[i] —— 回包顺序与入参顺序无关,
       只能靠 title + amount(+ project_id, 若后端已支持) 反向映射。

    ⚠️ 2026-08-10 真实票据实测发现的问题: 同一捐款人在同一机构、同一天、
       同一金额, 捐给**不同项目**的多张票(例如"陈家辉"给深圳壹基金基金会
       捐了两笔各1.00 元, 一笔给"海洋天堂计划", 一笔给"儿童服务站")——
       仅靠 (title, amount) 完全无法区分该绑定哪个application_number,
       而候选行返回顺序**不保证**与上传顺序对应,
       盲目按顺序分配存在**静默绑错**的风险, 且当前协议下事后无法发现。

    ⚠️ 需求方(2026-08-10)已确认会推动后端在 `pending_list` 每行补上
       `project_id`(或 `project_no`) 字段。本函数**已做好接收准备**——
       一旦某行带有该字段, `allocate()` 会用它做加严匹配; 在后端尚未
       补齐之前, 该字段普遍缺失, 自动退回纯 (title, amount) 匹配,
       现有行为(含全部既有单测)**完全不受影响**(向后兼容)。
    """
    index: Dict[Tuple[str, int], List[dict]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        cents = _as_int_cents(row.get("amount"))
        if cents is None:
            continue
        key = (_norm_key(row.get("title") or ""), cents)
        pid = str(row.get("project_id") or row.get("project_no") or "").strip()
        index.setdefault(key, []).append(
            {
                "application_number": str(row.get("application_number") or ""),
                "title": str(row.get("title") or ""),
                "amount": cents,
                "project_id": pid,
            }
        )
    return index


# ---------------------------------------------------------------------------
# 独占顺序分配 (m 张同内容票 对 n 个候选申请单)
# ---------------------------------------------------------------------------
def allocate(
    items: List[dict],
    pending_index: Dict[Tuple[str, int], List[dict]],
    success_index: Dict[Tuple[str, int], List[dict]],
    locked_applications: Optional[set] = None,
) -> Tuple[List[dict], List[dict]]:
    """按(归一化 title, amount) 分组做一对一分配, **project_id 可用时加严**。

    规则(需求方2026-08-10 确认; 2026-08-12 修正计数单位: 按申请号而非候选行):
      1. 组内 m 张票, 候选申请号 n 个(按 application_number 去重, 同一申请号
         多行视为 1 个) → 一对一分配 min(m, n) 组
      2. m > n → 多出的 (m - n) 张 match_status=2, reason=「已经有别的票据匹配上了」
         (一个申请号只能被一张票认领, 其余同组票判"被同批其他票匹配上")
      3. n > m → 多余的 (n - m) 个候选申请号不使用
      4. locked_applications 里的编号对本轮**不可见**(重匹配的存量占用保护)

    ★ project_id 加严匹配(2026-08-10 真实票据实测追加, 待后端支持):
      同一 (title, amount) 组内, 如果候选行**已经带有** project_id(说明后端
      已升级支持项目区分), 则:
        - 本票据有明确 project_id → 只能消费**同project_id** 的候选行子队列,
          绝不理会返回顺序, 也绝不因为顺序凑巧就绑到别的项目
        - 本票据没有 project_id(无信号 / 多候选歧义) → 只能消费**未带
          project_id** 的候选行, 绝不在多个不同项目里瞎猜
      组内候选行**完全没有** project_id(后端未升级) → 自动退回原有纯
      (title, amount) 池式分配, 与升级前**逐字节一致**(向后兼容, 不影响
      任何既有单测)。

    ★ pdf_filename(2026-08-10新增, 可选): 原始 PDF 本地文件名,仅用于
      Host 侧维护的会话记录(items.json)——「pdf 文件名 / 识别信息 / 匹配结果 /
      上传链接」四要素齐全, 便于用户排查"哪张票的原始文件叫什么"。⛔ 不进
      MatchItem/UiReq(UI 层协议里没有这个字段, to_match_item() 不会外泄)。

    返回 (结果列表, 重复票明细)。结果列表保持入参顺序。
    """
    locked = locked_applications or set()

    # 组内按上传序排序, 保证"第 i 张票 ← 第 i 个未占用申请号"的分配是稳定的
    ordered = sorted(range(len(items)), key=lambda i: (items[i].get("seq") if items[i].get("seq") is not None else i))

    # 每组(含项目子队列)已占用的申请号集合: 保证一个申请号只被一张票认领,
    # 即使候选池里同一申请号出现多行(一个申请单可被多张票匹配, 但只能提交一张)。
    consumed: Dict[tuple, set] = {}
    results: List[Optional[dict]] = [None] * len(items)
    duplicates: List[dict] = []

    for idx in ordered:
        item = items[idx]
        title_raw = str(item.get("title") or "")
        cents = _as_int_cents(item.get("amount"))
        title_norm, _ops = normalize_title(title_raw)
        item_pid = str(item.get("project_id") or "").strip()

        base = {
            "seq": item.get("seq"),
            "md5": item.get("md5") or "",
            "pdf_filename": str(item.get("pdf_filename") or ""),  # ★ Host侧记录用, 不进MatchItem
            "invoice_url": str(item.get("invoice_url") or ""),
            "title": title_raw,
            "title_normalized": title_norm,
            "amount": cents if cents is not None else 0,
            "project_name_list": list(item.get("project_name_list") or []),
            "project_id": item_pid,          # 仅供内部审计, to_match_item() 不会外泄
            "application_number": "",
            "match_status": FAILED,
            "match_status_reason": REASON_NO_MATCH,
            "status": 0,
            "modify_status": 0,
        }

        # ① 本批 md5 重复 —— 匹配之前就判定, 不占任何申请单
        if item.get("md5_duplicate"):
            base["match_status_reason"] = REASON_DUPLICATE_FILE
            duplicates.append({"seq": item.get("seq"), "duplicate_of_seq": item.get("duplicate_of_seq")})
            results[idx] = base
            continue

        # ② 识别不完整 ——抬头为空或金额换算失败, 不得送匹配
        if item.get("incomplete") or not title_norm or cents is None:
            base["match_status_reason"] = REASON_INCOMPLETE
            results[idx] = base
            continue

        key = (title_norm, cents)
        rows = pending_index.get(key) or []
        available = [r for r in rows if r["application_number"] not in locked]
        group_has_pid = any(r["project_id"] for r in available)

        if item_pid and group_has_pid:
            # 候选池已能区分项目, 本票据也有明确项目 → 只在同项目子队列里找,
            # 不看返回顺序, 杜绝"顺序凑巧对了/凑巧错了"的静默绑错
            pool = [r for r in available if r["project_id"] == item_pid]
            cursor_key = (key, "pid", item_pid)
        elif not item_pid and group_has_pid:
            # 本票据没有项目信号, 但候选池要求项目区分 → 只能吃"无项目标记"的
            # 候选行, 绝不在多个不同项目里瞎猜
            pool = [r for r in available if not r["project_id"]]
            cursor_key = (key, "pid", "__no_project__")
        else:
            # 候选池完全没有project_id(后端未升级) → 退回原有纯(title,amount)
            # 池式分配, 与升级前行为一致
            pool = available
            cursor_key = (key, "pid", "")

        # ★ 2026-08-12: 独占分配单位是【申请号】而非候选行。同一申请号在候选池
        #   可能多行出现(一个申请单可被多张票匹配), 但只能有一张票认领它; 其余
        #   同组票必须判 REASON_OCCUPIED(被同批其他票匹配上)。用 consumed 集合
        #   按组追踪已占申请号, 跳过被前序票/存量已占的申请号。
        taken = consumed.setdefault(cursor_key, set())
        eligible = [r for r in pool if r["application_number"] not in taken]
        if eligible:
            row = eligible[0]
            taken.add(row["application_number"])
            base["application_number"] = row["application_number"]
            base["match_status"] = MATCHED
            base["match_status_reason"] = ""
            base["status"] = 1
            # C11恒等: 匹配成功时识别值即申请单值(归一化空间内恒等, 由key 保证)
            if row["title"] != title_raw:
                base["_title_raw_differs"] = row["title"]
            results[idx] = base
            continue

        # ③ 有候选行但已被同组前序票/ 存量占用 / 项目不匹配吃掉 → 独立文案
        if rows:
            base["match_status_reason"] = REASON_OCCUPIED
            results[idx] = base
            continue

        # ④ 命中已提交列表 → 该申请已处理过, 改识别信息也没用
        if success_index.get(key):
            base["match_status_reason"] = REASON_SUBMITTED
            results[idx] = base
            continue

        # ⑤ 彻底没命中
        results[idx] = base

    return [r for r in results if r is not None], duplicates


# ---------------------------------------------------------------------------
# UiReq 组装 + 一致性断言
# ---------------------------------------------------------------------------
def to_match_item(result: dict) -> dict:
    """裁剪成UI 协议允许的字段。

    ⛔ 严禁出现 match_confidence / default_selected / pdf_id / project_id /
       application_title / application_amount / application_project_name_list。
    """
    return {
        "status": int(result.get("status") or 0),
        "invoice_url": result.get("invoice_url") or "",
        "title": result.get("title") or "",
        "amount": int(result.get("amount") or 0),
        "project_name_list": list(result.get("project_name_list") or []),
        "match_status": int(result.get("match_status") or FAILED),
        "match_status_reason": result.get("match_status_reason") or "",
        "application_number": result.get("application_number") or "",
        "modify_status": 0,
    }


def build_ui_req(org_no: str, results: List[dict], expected_total: Optional[int]) -> Tuple[dict, dict, List[str]]:
    matched, failed = [], []
    errors: List[str] = []

    for r in results:
        item = to_match_item(r)
        if item["match_status"] == MATCHED:
            if item["status"] != 1:
                errors.append(f"seq={r.get('seq')} match_status=1 但 status!=1")
            if not item["application_number"]:
                errors.append(f"seq={r.get('seq')} match_status=1 但 application_number 为空")
            matched.append(item)
        else:
            if item["status"] != 0:
                errors.append(f"seq={r.get('seq')} match_status=2 但 status!=0(未匹配票不得预勾选)")
            if item["application_number"]:
                errors.append(f"seq={r.get('seq')} match_status=2 但 application_number 非空")
            if not item["match_status_reason"]:
                errors.append(f"seq={r.get('seq')} match_status=2 但 match_status_reason 为空")
            failed.append(item)

    total = len(matched) + len(failed)
    conservation = expected_total is None or total == expected_total
    if not conservation:
        errors.append(f"条数守恒断言失败: 两列表合计 {total} != 预期 {expected_total}")

    identity = all(not r.get("_title_raw_differs") for r in results if r.get("match_status") == MATCHED)

    ui_req = {
        "org_no": org_no or "",
        # ★ 2026-08-12: repeated 字段允许缺省(等价于空)。实测接口调用失败的根因是
        #   agent 把空列表字段写成 `""`(而非框架序列化)。因此空列表一律【省略该字段】,
        #   使出参里压根不存在该字段, agent 原样使用时无从把它写成 `""`, 从根上杜绝该事故。
        "submit": {
            "next_step": SUBMIT_NEXT_STEP,
        },
    }
    if matched:
        ui_req["matched_items"] = matched
    if failed:
        ui_req["matched_failed_items"] = failed
    assertions = {
        "list_self_consistent": not errors or all("守恒" in e for e in errors),
        "conservation": conservation,
        "identity": identity,
        "total": total,
    }
    return ui_req, assertions, errors


def _summarize(results: List[dict]) -> dict:
    breakdown = {"no_match": 0, "occupied": 0, "submitted": 0, "md5_duplicate": 0, "incomplete": 0}
    matched = 0
    for r in results:
        if r.get("match_status") == MATCHED:
            matched += 1
            continue
        bucket = _REASON_TO_BUCKET.get(r.get("match_status_reason") or "")
        if bucket:
            breakdown[bucket] += 1
    return {
        "total": len(results),
        "matched": matched,
        "failed": len(results) - matched,
        "failed_breakdown": breakdown,
    }


def _write_items(path: Optional[str], org_no: str, results: List[dict]) -> Optional[str]:
    if not path:
        return None
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    payload = {"org_no": org_no or "", "items": results}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


# ---------------------------------------------------------------------------
# mode 实现
# ---------------------------------------------------------------------------
def do_normalize(input_data: dict) -> dict:
    out = []
    for idx, item in enumerate(input_data.get("items") or []):
        raw = str(item.get("title") or "")
        norm, ops = normalize_title(raw)
        entry = {
            "seq": item.get("seq", idx + 1),
            "title": raw,
            "title_normalized": norm,
            "changed": norm != raw,
            "ops": ops,
        }
        cents = _as_int_cents(item.get("amount"))
        entry["amount"] = cents
        if cents is None and item.get("amount") not in (None, ""):
            entry["amount_error"] = "金额不是合法的 uint32 分值, 该票不得送匹配"
        out.append(entry)
    return {"success": True, "mode": "normalize", "items": out}


def do_allocate(input_data: dict, candidates_file: Optional[str]) -> dict:
    items = input_data.get("items") or []
    if not items:
        return {"success": False, "error": "items 为空, 无可分配票据"}

    pending, success, warnings = _load_candidates(input_data, candidates_file)
    pending_index = _index_rows(pending)
    success_index = _index_rows(success)

    results, duplicates = allocate(items, pending_index, success_index)

    org_no = str(input_data.get("org_no") or "")
    expected = input_data.get("expected_total")
    expected = int(expected) if expected not in (None, "") else len(items)
    ui_req, assertions, errors = build_ui_req(org_no, results, expected)

    if errors:
        return {
            "success": False,
            "mode": "allocate",
            "error": "一致性断言失败, 不得呼起 UI",
            "assertion_errors": errors,
            "assertions": assertions,
        }

    items_file = _write_items(input_data.get("output_items_file"), org_no, results)

    # 同时命中 pending 与 success 的抬头金额 → 按 pending 处理, 但要提示历史记录
    for r in results:
        if r.get("match_status") == MATCHED:
            key = (r.get("title_normalized"), r.get("amount"))
            if success_index.get(key):
                warnings.append(
                    f"seq={r.get('seq')} 的抬头金额同时存在已提交记录, 已按待开票处理, 请提示用户核对"
                )

    return {
        "success": True,
        "mode": "allocate",
        "summary": _summarize(results),
        "items_file": items_file,
        "ui_req": ui_req,
        "assertions": assertions,
        "duplicates": duplicates,
        "pending_pool_size": len(pending),
        "success_pool_size": len(success),
        "warnings": warnings,
    }


def do_prune(input_data: dict) -> dict:
    """剔除已提交项。

    「提交票据到远程」步骤专用: 提交动作已在 UI 内直接完成, UI 只回传「已提交
    成功的 pdf 链接列表」, 本函数按 invoice_url 把这些项从既有 items 里剔除并写回。
    UI 侧提交后已自行刷新展示剩余, 因此 agent 无需重新呼起 UI, 只需据
    removed_count / remaining_count 告知用户"已提交 X 条, 剩余 Y 条"。
    """
    items_file = input_data.get("items_file")
    if not items_file:
        return {"success": False, "error": "prune 必须提供 items_file(既有全量结果)"}
    try:
        stored = _read_json_file(items_file)
    except (OSError, json.JSONDecodeError) as e:
        return {"success": False, "error": f"读取 items_file 失败: {e}"}

    existing = stored.get("items") if isinstance(stored, dict) else stored
    if not isinstance(existing, list):
        return {"success": False, "error": f"items_file 内容格式非法: {items_file}"}

    org_no = str(input_data.get("org_no") or (stored.get("org_no") if isinstance(stored, dict) else "") or "")
    submitted = {str(u or "") for u in (input_data.get("submitted_invoice_urls") or [])}

    removed, remaining, unknown = [], [], []
    existing_urls = {str(r.get("invoice_url") or "") for r in existing}
    for r in existing:
        url = str(r.get("invoice_url") or "")
        if url and url in submitted:
            removed.append(url)
        else:
            remaining.append(r)
    for u in sorted(submitted):
        if u and u not in existing_urls:
            unknown.append(u)

    if not removed:
        return {
            "success": False,
            "error": "无匹配的已提交项: 回传的 pdf 链接均不在本会话 items 中",
            "unknown_invoice_urls": unknown,
        }

    out_path = _write_items(input_data.get("output_items_file") or items_file, org_no, remaining)

    return {
        "success": True,
        "mode": "prune",
        "removed_count": len(removed),
        "remaining_count": len(remaining),
        "items_file": out_path,
        "unknown_invoice_urls": unknown,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def process(input_data: dict, candidates_file: Optional[str] = None) -> dict:
    mode = str(input_data.get("mode") or "").strip().lower()
    try:
        if mode == "normalize":
            return do_normalize(input_data)
        if mode == "allocate":
            return do_allocate(input_data, candidates_file)
        if mode == "prune":
            return do_prune(input_data)
    except (OSError, json.JSONDecodeError) as e:
        return {"success": False, "error": f"读写失败: {e}"}
    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": f"{mode or '未知 mode'} 执行失败: {e}"}
    return {"success": False, "error": f"mode 非法: {mode!r}, 只支持 normalize / allocate / prune"}


def _load_input(args) -> dict:
    if args.input_file:
        with open(args.input_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(args.input)


def main():
    # ⚠️ 2026-08-10 实测事故: Windows 下 stdout 是**管道**时默认用 locale 编码
    #    (中文环境 = GBK), 于是 `ensure_ascii=False` 的中文 JSON 被写成 GBK 字节,
    #    UTF-8 读取方直接 UnicodeDecodeError —— 表现为"脚本成功了但返回值读不出来"。
    #抬头/reason 文案必然含中文, 所以本行**不是可选优化**。
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="JSON 格式的入参")
    parser.add_argument("--input-file", dest="input_file", help="入参 JSON 文件路径(大批量必用)")
    parser.add_argument(
        "--candidates-file",
        dest="candidates_file",
        help="list_pending_tickets 回包落盘路径(候选池不得进 agent 上下文)",
    )
    args = parser.parse_args()

    if not args.input and not args.input_file:
        print(json.dumps({"success": False, "error": "必须提供 --input 或 --input-file"}), flush=True)
        sys.exit(1)

    try:
        input_data = _load_input(args)
    except (json.JSONDecodeError, OSError) as e:
        print(
            json.dumps({"success": False, "error": f"入参非合法 JSON: {e}"}, ensure_ascii=False),
            flush=True,
        )
        sys.exit(1)

    result = process(input_data, args.candidates_file)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
