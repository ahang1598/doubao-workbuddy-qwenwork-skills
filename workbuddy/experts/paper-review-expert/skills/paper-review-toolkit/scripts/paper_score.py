#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper_score.py — 论文评审工具集评分内核

功能：
  1. weights  查看三套场景权重与维度定义
  2. score    按场景权重的七维度加权算分 + 等级 + 通过率区间
  3. pri      缺陷 PRI = S x O x E 排序与分级
  4. report   由会话 JSON 生成完整 Markdown 评审报告
  5. selftest 模型自检（权重、边界、分级、通过率单调性）

用法：
  python3 paper_score.py weights
  python3 paper_score.py score --scene journal-cn --json '{"D1":13,"D2":11,"D3":12,"D4":14,"D5":11,"D6":8,"D7":7}'
  python3 paper_score.py pri --json '[{"id":"C4-2","name":"样本量不足","s":5,"o":2,"e":3}]'
  python3 paper_score.py report --input session.json --out review.md
  python3 paper_score.py selftest
"""

import argparse
import json
import sys

WEIGHTS = {
    "thesis":     {"D1": 15, "D2": 18, "D3": 15, "D4": 15, "D5": 15, "D6": 10, "D7": 12},
    "journal-cn": {"D1": 15, "D2": 13, "D3": 15, "D4": 20, "D5": 15, "D6": 10, "D7": 12},
    "journal-en": {"D1": 15, "D2": 12, "D3": 15, "D4": 20, "D5": 16, "D6": 12, "D7": 10},
}

SCENE_LABEL = {
    "thesis": "学位论文",
    "journal-cn": "中文期刊",
    "journal-en": "英文期刊",
}

DIM_NAMES = {
    "D1": "选题与创新性",
    "D2": "结构与逻辑",
    "D3": "文献与引用规范",
    "D4": "研究方法与数据统计",
    "D5": "论证与证据充分性",
    "D6": "学术表达",
    "D7": "格式合规与投稿就绪度",
}

# (最低分, 等级, 名称, 结论)
GRADE_BANDS = [
    (90, "A", "优秀", "可投 / 可送审，小修即可"),
    (80, "B", "良好", "有竞争力，需一轮实质修改"),
    (70, "C", "合格", "大修，问题明确可救"),
    (60, "D", "临界", "高退稿风险，需结构性调整"),
    (0,  "E", "不合格", "建议重构核心章节后再投"),
]

# (总分, 通过率下限, 通过率上限)
PASS_ANCHORS = [
    (0,   2,  5),
    (50,  5, 15),
    (60, 20, 40),
    (70, 45, 65),
    (80, 68, 85),
    (90, 88, 96),
    (100, 95, 99),
]

PRI_BANDS = [
    (45, "P0 必改", "不改就可能直接被退 / 被毙"),
    (25, "P1 应改", "评审人会写进意见并要求回应"),
    (10, "P2 可优化", "影响印象，不影响结论成立"),
    (0,  "P3 锦上添花", "细节打磨"),
]

FATAL_NAMES = {
    "F1": "学术不端（伪造 / 篡改 / 抄袭 / 代写）",
    "F2": "伦理缺失（无审批号 / 无知情同意 / 隐私未脱敏）",
    "F3": "统计或方法致命（结论不成立 / 数据无法溯源）",
    "F4": "形式致命（查重超阈值 / 一稿多投 / 署名争议 / 字数超限）",
}


def _interp(x, anchors):
    """在 anchors 上做分段线性插值，返回 (low, high)。"""
    if x <= anchors[0][0]:
        return float(anchors[0][1]), float(anchors[0][2])
    if x >= anchors[-1][0]:
        return float(anchors[-1][1]), float(anchors[-1][2])
    for i in range(len(anchors) - 1):
        x0, l0, h0 = anchors[i]
        x1, l1, h1 = anchors[i + 1]
        if x0 <= x <= x1:
            t = (x - x0) / float(x1 - x0)
            return l0 + t * (l1 - l0), h0 + t * (h1 - h0)
    return float(anchors[-1][1]), float(anchors[-1][2])


def grade_of(total):
    for floor, letter, name, conclusion in GRADE_BANDS:
        if total >= floor:
            return letter, name, conclusion
    return GRADE_BANDS[-1][1], GRADE_BANDS[-1][2], GRADE_BANDS[-1][3]


def pass_interval(total, p0_count=0, fatal=None):
    """通过率区间（百分比整数元组）。红线优先，其次 P0 惩罚。"""
    if fatal:
        return 0, 8
    low, high = _interp(total, PASS_ANCHORS)
    if p0_count > 0:
        high = min(high, 62.0)
        low = max(2.0, low - 3.0 * p0_count)
    if low > high:
        low = high
    return int(round(low)), int(round(high))


def pri_of(defect):
    s = int(defect.get("s", 1))
    o = int(defect.get("o", 1))
    e = int(defect.get("e", 1))
    return s * o * e


def pri_grade(pri):
    for floor, label, meaning in PRI_BANDS:
        if pri >= floor:
            return label, meaning
    return PRI_BANDS[-1][1], PRI_BANDS[-1][2]


def is_hidden_mine(defect):
    """隐性雷区：严重度高但不易被当场发现。"""
    return int(defect.get("s", 1)) >= 4 and int(defect.get("e", 5)) <= 2


def score_dimensions(scene, dims):
    """校验并计算七维度得分。返回 (total, rows)。"""
    if scene not in WEIGHTS:
        raise ValueError("未知场景: %s（可选 %s）" % (scene, "/".join(WEIGHTS)))
    weights = WEIGHTS[scene]
    rows = []
    total = 0
    for key in ("D1", "D2", "D3", "D4", "D5", "D6", "D7"):
        full = weights[key]
        if key not in dims:
            raise ValueError("缺少维度 %s（%s）的得分" % (key, DIM_NAMES[key]))
        got = float(dims[key])
        if got < 0 or got > full:
            raise ValueError("维度 %s 得分 %.1f 超出满分 %d，请核对场景权重" % (key, got, full))
        rate = got / full * 100.0
        total += got
        rows.append({
            "key": key,
            "name": DIM_NAMES[key],
            "got": got,
            "full": full,
            "rate": rate,
        })
    return total, rows


def build_report(session):
    scene = session.get("scene", "journal-cn")
    dims = session.get("dimensions", {})
    total, rows = score_dimensions(scene, dims)

    fatal = [f for f in session.get("fatal", []) if f]
    defects = session.get("defects", []) or []
    for d in defects:
        d["pri"] = pri_of(d)
        d["grade"], d["meaning"] = pri_grade(d["pri"])
    defects_sorted = sorted(defects, key=lambda d: d["pri"], reverse=True)
    p0 = [d for d in defects_sorted if d["pri"] >= 45]
    p1 = [d for d in defects_sorted if 25 <= d["pri"] < 45]
    p2 = [d for d in defects_sorted if 10 <= d["pri"] < 25]
    p3 = [d for d in defects_sorted if d["pri"] < 10]
    mines = [d for d in defects_sorted if is_hidden_mine(d)]

    letter, gname, conclusion = grade_of(total)
    low, high = pass_interval(total, len(p0), fatal)
    verdict = "不予通过（命中红利线）" if fatal else conclusion

    out = []
    w = out.append

    w("# 论文评审报告")
    w("")
    w("- 论文标题：%s" % (session.get("title") or "（未填写）"))
    w("- 目标场景：%s（%s）" % (SCENE_LABEL.get(scene, scene), scene))
    w("- 目标刊物 / 学校：%s" % (session.get("target") or "（未填写）"))
    w("- 当前阶段：%s" % (session.get("stage") or "（未填写）"))
    w("- 权重方案：%s" % " / ".join("%s %d" % (k, WEIGHTS[scene][k]) for k in ("D1", "D2", "D3", "D4", "D5", "D6", "D7")))
    w("")

    w("## 1. 结论卡")
    w("")
    w("| 项目 | 结果 |")
    w("|------|------|")
    w("| 总分 | **%d / 100** |" % round(total))
    w("| 等级 | **%s %s** |" % (letter, gname))
    w("| 通过率区间 | **%d%% – %d%%** |" % (low, high))
    w("| 红线结论 | %s |" % ("**命中 %s**，结论为不予通过" % "、".join(fatal) if fatal else "未命中"))
    w("| 缺陷分布 | P0 %d 条 / P1 %d 条 / P2 %d 条 / P3 %d 条 |" % (len(p0), len(p1), len(p2), len(p3)))
    w("| 判断 | %s |" % verdict)
    w("")

    w("## 2. 红线筛查结果")
    w("")
    w("| 代码 | 红线 | 结论 |")
    w("|------|------|------|")
    for code in ("F1", "F2", "F3", "F4"):
        hit = "**命中**" if code in fatal else "未命中"
        w("| %s | %s | %s |" % (code, FATAL_NAMES[code], hit))
    w("")

    w("## 3. 七维度评分")
    w("")
    w("| 维度 | 得分 | 满分 | 得分率 | 水平 |")
    w("|------|------|------|--------|------|")
    for r in rows:
        w("| %s %s | %.1f | %d | %.0f%% | %s |" % (
            r["key"], r["name"], r["got"], r["full"], r["rate"], _level_word(r["rate"])))
    w("| **合计** | **%.1f** | **100** | **%.0f%%** | **%s %s** |" % (
        total, total, letter, gname))
    w("")
    w("> 每个维度的扣分理由与证据位置需在对话报告中补充（脚本只负责算分，不臆测理由）。")
    w("")

    w("## 4. 缺陷清单（按 PRI 降序）")
    w("")
    if not defects_sorted:
        w("未记录缺陷。")
    else:
        w("| PRI | 分级 | 编号 | 缺陷 | 位置 | S | O | E | 建议改法 | 耗时 |")
        w("|-----|------|------|------|------|---|---|---|----------|------|")
        for d in defects_sorted:
            w("| %d | %s | %s | %s | %s | %d | %d | %d | %s | %s |" % (
                d["pri"], d["grade"], d.get("id", "-"), d.get("name", "-"),
                d.get("where", "-"), int(d.get("s", 1)), int(d.get("o", 1)),
                int(d.get("e", 1)), d.get("fix", "-"), d.get("effort", "-")))
    w("")
    w("PRI = S（严重度）x O（普遍程度）x E（暴露度），取值 1–125；P0 ≥45、P1 25–44、P2 10–24、P3 ≤9。")
    w("")

    if mines:
        w("## 5. 隐性雷区（S ≥ 4 且 E ≤ 2）")
        w("")
        w("以下问题评审人当场未必发现，但一旦深究或在答辩被追问就会暴露，建议投稿前处理：")
        w("")
        for d in mines:
            w("- **%s** %s（PRI %d，位置 %s）" % (d.get("id", "-"), d.get("name", "-"), d["pri"], d.get("where", "-")))
        w("")

    w("## 6. 三阶段行动计划")
    w("")
    w("| 阶段 | 目标 | 包含项 |")
    w("|------|------|--------|")
    w("| 阶段一 | 消除退稿级风险 | %s |" % (", ".join(d.get("id", "-") for d in p0) or "无 P0"))
    w("| 阶段二 | 整体等级提升一档 | %s |" % (", ".join(d.get("id", "-") for d in p1) or "无 P1"))
    w("| 阶段三 | 定稿与投稿材料 | %s |" % (", ".join(d.get("id", "-") for d in p2 + p3) or "无 P2/P3"))
    w("")

    if session.get("notes"):
        w("## 7. 补充说明")
        w("")
        w(session["notes"])
        w("")

    w("---")
    w("")
    w("说明：本评分为「按当前文本估计的通过风险」，通过率区间为经验估算，不构成任何录用承诺；")
    w("评审人口味差异客观存在，报告聚焦于降低可避免的风险。Before→After 改写示例请见对话报告。")
    return "\n".join(out)


def _level_word(rate):
    if rate >= 90:
        return "优秀"
    if rate >= 80:
        return "良好"
    if rate >= 70:
        return "合格"
    if rate >= 60:
        return "临界"
    return "不合格"


def cmd_weights(_args):
    print("场景权重（合计均为 100）\n")
    header = "| 维度 | " + " | ".join("%s %s" % (k, SCENE_LABEL[k]) for k in WEIGHTS) + " |"
    print(header)
    print("|------|" + "------|" * len(WEIGHTS))
    for key in ("D1", "D2", "D3", "D4", "D5", "D6", "D7"):
        cells = " | ".join(str(WEIGHTS[s][key]) for s in WEIGHTS)
        print("| %s %s | %s |" % (key, DIM_NAMES[key], cells))
    print("| **合计** | " + " | ".join("**100**" for _ in WEIGHTS) + " |")
    print()
    print("等级区间：")
    for floor, letter, name, conclusion in GRADE_BANDS:
        print("  %s 及以上 → %s %s：%s" % (floor, letter, name, conclusion))
    print()
    print("PRI 分级：")
    for floor, label, meaning in PRI_BANDS:
        print("  PRI ≥ %d → %s（%s）" % (floor, label, meaning))
    return 0


def cmd_score(args):
    dims = json.loads(args.json)
    total, rows = score_dimensions(args.scene, dims)
    letter, gname, conclusion = grade_of(total)
    low, high = pass_interval(total, args.p0 or 0, args.fatal or None)
    print("场景：%s（%s）" % (SCENE_LABEL[args.scene], args.scene))
    for r in rows:
        print("  %s %-22s %5.1f / %-3d  %3.0f%%  %s" % (
            r["key"], r["name"], r["got"], r["full"], r["rate"], _level_word(r["rate"])))
    print("  合计：%d / 100" % round(total))
    print("  等级：%s %s → %s" % (letter, gname, conclusion))
    print("  通过率区间：%d%% – %d%%%s" % (
        low, high, "（含红线或 P0 惩罚）" if (args.fatal or args.p0) else ""))
    return 0


def cmd_pri(args):
    defects = json.loads(args.json)
    if not isinstance(defects, list):
        raise ValueError("pri 需要 JSON 数组")
    for d in defects:
        d["pri"] = pri_of(d)
        d["grade"], _ = pri_grade(d["pri"])
    for d in sorted(defects, key=lambda x: x["pri"], reverse=True):
        flag = "  [隐性雷区]" if is_hidden_mine(d) else ""
        print("PRI %3d  %-10s %-10s %-28s S=%d O=%d E=%d%s" % (
            d["pri"], d["grade"], d.get("id", "-"), d.get("name", "-"),
            int(d.get("s", 1)), int(d.get("o", 1)), int(d.get("e", 1)), flag))
    return 0


def cmd_report(args):
    with open(args.input, "r", encoding="utf-8") as f:
        session = json.load(f)
    text = build_report(session)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print("已写入 %s（%d 字）" % (args.out, len(text)))
    else:
        print(text)
    return 0


def cmd_selftest(_args):
    checks = []

    def check(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    # 1. 权重合计必须为 100
    for scene, w in WEIGHTS.items():
        check("权重合计=100 (%s)" % scene, sum(w.values()) == 100, "sum=%d" % sum(w.values()))

    # 2. 满分输入应得 100 分与最高档
    total, _ = score_dimensions("journal-cn", WEIGHTS["journal-cn"])
    check("满分场景总分=100", total == 100, "total=%s" % total)
    check("满分等级=A", grade_of(total)[0] == "A", grade_of(total)[0])

    # 3. 0 分应落在 E 档
    zero = {k: 0 for k in WEIGHTS["thesis"]}
    t0, _ = score_dimensions("thesis", zero)
    check("零分等级=E", grade_of(t0)[0] == "E", grade_of(t0)[0])

    # 4. 维度超满分必须报错
    bad = dict(WEIGHTS["thesis"])
    bad["D6"] = WEIGHTS["thesis"]["D6"] + 1
    try:
        score_dimensions("thesis", bad)
        check("超满分报错", False, "未抛异常")
    except ValueError:
        check("超满分报错", True)

    # 5. 通过率区间单调不减
    prev = -1
    mono = True
    for s in range(0, 101):
        low, _h = pass_interval(s)
        if low < prev:
            mono = False
            break
        prev = low
    check("通过率下限随分数单调不减", mono)

    # 6. 红线压制通过率
    low_f, high_f = pass_interval(95, 0, ["F1"])
    check("红线命中→区间 0–8%", (low_f, high_f) == (0, 8), "%s" % ((low_f, high_f),))

    # 7. P0 惩罚生效
    l0, h0 = pass_interval(92, 0, None)
    l1, h1 = pass_interval(92, 2, None)
    check("P0 惩罚压低通过率", h1 < h0 and l1 < l0, "无P0=%s 有2条P0=%s" % ((l0, h0), (l1, h1)))

    # 8. PRI 边界与分级
    check("PRI 上限=125", pri_of({"s": 5, "o": 5, "e": 5}) == 125)
    check("PRI 下限=1", pri_of({"s": 1, "o": 1, "e": 1}) == 1)
    check("PRI 45→P0", pri_grade(45)[0].startswith("P0"), pri_grade(45)[0])
    check("PRI 44→P1", pri_grade(44)[0].startswith("P1"), pri_grade(44)[0])
    check("PRI 25→P1", pri_grade(25)[0].startswith("P1"), pri_grade(25)[0])
    check("PRI 24→P2", pri_grade(24)[0].startswith("P2"), pri_grade(24)[0])
    check("PRI 9→P3", pri_grade(9)[0].startswith("P3"), pri_grade(9)[0])

    # 9. 隐性雷区判定
    check("隐性雷区 S=5,E=2 命中", is_hidden_mine({"s": 5, "e": 2}))
    check("隐性雷区 S=5,E=3 不命中", not is_hidden_mine({"s": 5, "e": 3}))
    check("隐性雷区 S=3,E=1 不命中", not is_hidden_mine({"s": 3, "e": 1}))

    # 10. 报告端到端可生成
    demo = {
        "scene": "journal-cn",
        "title": "自检样例",
        "dimensions": {"D1": 13, "D2": 11, "D3": 12, "D4": 14, "D5": 11, "D6": 8, "D7": 7},
        "fatal": [],
        "defects": [
            {"id": "C4-2", "name": "样本量不足", "where": "3.2", "s": 5, "o": 2, "e": 3},
            {"id": "C6-1", "name": "术语不一致", "where": "全文", "s": 2, "o": 5, "e": 3},
        ],
    }
    md = build_report(demo)
    check("报告含结论卡", "## 1. 结论卡" in md)
    check("报告含缺陷清单", "## 4. 缺陷清单" in md)
    check("报告含 76 分", "**76 / 100**" in md, [l for l in md.split("\n") if "总分" in l][:1])
    check("报告含 PRI 排序", md.index("C4-2") < md.index("C6-1") if "C4-2" in md and "C6-1" in md else False)

    passed = sum(1 for _, ok, _ in checks if ok)
    for name, ok, detail in checks:
        print("%s %s%s" % ("PASS" if ok else "FAIL", name, ("  <- " + str(detail)) if (not ok and detail) else ""))
    print("\n自检结果：%d/%d 通过" % (passed, len(checks)))
    return 0 if passed == len(checks) else 1


def main():
    parser = argparse.ArgumentParser(description="论文评审工具集评分内核")
    sub = parser.add_subparsers(dest="cmd")

    p_w = sub.add_parser("weights", help="查看三套场景权重与分级")
    p_w.set_defaults(func=cmd_weights)

    p_s = sub.add_parser("score", help="七维度加权算分")
    p_s.add_argument("--scene", default="journal-cn", choices=list(WEIGHTS))
    p_s.add_argument("--json", required=True, help='形如 {"D1":13,"D2":11,...}')
    p_s.add_argument("--p0", type=int, default=0, help="P0 缺陷条数（用于压制通过率）")
    p_s.add_argument("--fatal", action="append", help="命中的红线代码，可重复，如 --fatal F1")
    p_s.set_defaults(func=cmd_score)

    p_p = sub.add_parser("pri", help="缺陷 PRI 排序")
    p_p.add_argument("--json", required=True, help='形如 [{"id":"C4-2","name":"...","s":5,"o":2,"e":3}]')
    p_p.set_defaults(func=cmd_pri)

    p_r = sub.add_parser("report", help="由会话 JSON 生成完整报告")
    p_r.add_argument("--input", required=True)
    p_r.add_argument("--out", default=None)
    p_r.set_defaults(func=cmd_report)

    p_t = sub.add_parser("selftest", help="模型自检")
    p_t.set_defaults(func=cmd_selftest)

    args = parser.parse_args()
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    try:
        return args.func(args)
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        print("参数错误：%s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
