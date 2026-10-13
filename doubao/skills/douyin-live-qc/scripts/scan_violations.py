#!/usr/bin/env python3
"""Rule-based compliance scanner for livestream transcripts.
Fast pre-screen layer: catches known violation patterns in milliseconds so the
LLM review can focus on semantic judgement instead of keyword hunting.

Supports multiple product categories via --category:
    general  - generic e-commerce (default)
    apparel  - clothing / shoes / hats
    software - software / SaaS / digital memberships / 3C
    food     - food / health supplements
    beauty   - cosmetics / skincare

Usage:
    python3 scan_violations.py transcript.txt
    python3 scan_violations.py transcript.txt --category apparel
    python3 scan_violations.py transcript.txt --category software --json
"""
import argparse
import json
import re
import sys

# Each rule: (id, level, pattern, label, legal_basis, fix_hint, categories)
# categories=None means the rule applies to ALL categories.
# Otherwise it is a set of category names where the rule is active.
RULES = [
    # ================================================================
    # UNIVERSAL RULES — apply to every category
    # ================================================================

    # ---------- HIGH: absolute superlatives (Ad Law art.9) ----------
    ("A01", "high", r"(全网|全渠道|全平台|全年)[^？！]{0,20}?(最低价?|地板价|地板折扣)",
     "全网最低价断言", "《广告法》第9条；《明码标价和禁止价格欺诈规定》第17条",
     "改为「本场直播专属价」", None),
    ("A02", "high", r"(顶奢|顶级奢[侈华]|最高端|最好的一件|最顶级)",
     "顶级绝对化用语", "《广告法》第9条", "改为「高端系列」「品质款」", None),
    ("A03", "high", r"至高(可达|填充|达)",
     "「至高」等同「最高」", "《广告法》第9条", "改为「高达」「最大可达」", None),
    ("A04", "high", r"(所有链接里面|全店)[^。！？]{0,10}最(显高|显瘦|好|优)",
     "店内最优绝对化", "《广告法》第9条", "改为「版型设计显高显瘦」", None),
    ("A05", "high", r"百搭百配|百搭不挑人|百搭不出错",
     "「百」字绝对化", "《广告法》第9条；《广告审查标准》第29条", "改为「非常好搭配」", None),
    ("A06", "high", r"(第一品牌|销量第一|排名第一|唯一)",
     "第一/唯一类绝对化", "《广告法》第9条", "需有权威依据，否则删除", None),
    ("A07", "high", r"(100%|百分之百|百分百)(保证|有效|成功|提升|解决|满意)",
     "百分百效果保证", "《广告法》第9条、第28条", "改为「多数用户反馈有效」或删除比例", None),
    ("A08", "high", r"(永久|终身)(免费|使用|有效|售后|保修)",
     "永久/终身承诺", "《广告法》第28条；《合同法》相关",
     "明确具体服务期限，如「首年免费」", None),

    # ---------- HIGH: unverifiable data claims ----------
    ("B04", "high", r"(卖了|销量|卖出)\s*\d+\s*(万|亿|多万)件",
     "销量数据需真实出处", "《广告法》第11条；《反不正当竞争法》第8条",
     "补充官方数据出处或删除具体数字", None),
    ("B05", "high", r"(国家级|世界级|顶级|极品|绝佳)",
     "等级类绝对化用语", "《广告法》第9条",
     "改为客观描述，如「高品质」", None),

    # ---------- HIGH: price deception ----------
    ("C01", "high", r"(双十一|双11|618)[^？！]{0,20}?(只能开|也要|最低)\s*\d+",
     "历史大促价格断言", "《明码标价和禁止价格欺诈规定》第17条", "需真实交易记录支撑", None),
    ("C02", "high", r"(这价格就今天|就今天晚上|今天最后一天)[^。！？]{0,10}(全年|全网)?",
     "价格时效绝对化", "《广告法》第4条", "如实告知活动截止时间", None),
    ("C03", "high", r"(原价|日常价|专柜价)\s*\d+[^。！？]{0,10}(现在|今天|只要)\s*\d+",
     "原价对比需真实", "《明码标价和禁止价格欺诈规定》第17条",
     "原价须为活动前7日内最低成交价，保留交易记录", None),

    # ---------- MID: guarantees / hunger marketing ----------
    ("D02", "mid", r"(今天不拍|明天没了|以后.{0,6}(见不到|遇不到|不会再有))",
     "虚假紧迫感", "《广告法》第4条；《侵害消费者权益处罚办法》第6条",
     "如实说明库存或活动截止时间", None),
    ("D03", "mid", r"最后\s*\d+\s*(件|单|套|个名额)|库存非常有限|断码不[加补]",
     "库存/名额声称需真实", "《侵害消费者权益处罚办法》第6条", "如实播报剩余数量", None),
    ("D04", "mid", r"闭眼(冲|买|带|入)",
     "诱导冲动消费", "《广告法》第4条", "改为「了解清楚再下单」", None),
    ("D07", "mid", r"大爆款|全网爆款",
     "爆款声称需数据", "《反不正当竞争法》第8条", "有数据则说具体销量", None),
    ("D08", "mid", r"(官方|旗舰店)[^。！？]{0,10}(不撒谎|不骗人|骗你.{0,4}狗)",
     "自我担保式承诺", "《广告法》第28条",
     "用事实和参数说话，删除人格担保表述", None),

    # ---------- MID: disparaging competitors ----------
    ("E01", "mid", r"(其他|别的|人家)(直播间|播送|家|店)[^？！]{0,15}?(老款|旧款|不如|差)",
     "贬损同行", "《反不正当竞争法》第11条", "删除，只讲自身优势", None),
    ("E02", "mid", r"不用再买.{0,6}了|不好你就别",
     "品牌信誉赌注式承诺", "《广告法》第28条", "删除，改为客观参数对比", None),

    # ---------- LOW: vague comparatives ----------
    ("F01", "low", r"更加的?(低调|高级|有内涵|好)",
     "比较级无比较对象", "《广告法》第8条", "明确比较对象", None),

    # ================================================================
    # APPAREL-SPECIFIC RULES — only active with --category apparel
    # ================================================================
    ("B01", "high", r"零下\s*\d+\s*度",
     "具体温度承诺", "《广告法》第8、11、28条",
     "需第三方检测报告并标注机构；否则改为「适合严寒地区」", {"apparel"}),
    ("B02", "high", r"保命款|保命的",
     "超出服装功能的夸大", "《广告法》第28条", "改为「严寒保暖款」", {"apparel"}),
    ("B03", "high", r"(\d+\s*(蓬|蓬松度)|蓬松度\s*\d+)",
     "蓬松度数据需标明出处", "《广告法》第11条", "补充「检测报告见详情页」", {"apparel"}),
    ("D01", "mid", r"穿\s*\d+\s*[到\-~]\s*\d+\s*年|久穿如新|\d+年不过时",
     "耐用年限保证性承诺", "《广告法》第28条", "改为「面料耐穿，正常打理可穿多季」", {"apparel"}),
    ("D05", "mid", r"完全(三防|防水|耐脏)|连.{0,4}都防|不需要打理|免洗",
     "防护性能绝对化", "《广告法》第8、28条", "改为「防泼水防泼油，日常污渍易清理」", {"apparel"}),
    ("D06", "mid", r"回头率拉满|一点都不挑人|超级显瘦",
     "夸大穿着效果", "《广告法》第28条", "改为客观描述", {"apparel"}),
    ("F02", "low", r"生活三防|三防(材质|面料)(?!.{0,6}(防泼水|防污))",
     "三防内容未明确", "《广告法》第8条", "明确防水/防油/防污具体内容", {"apparel"}),

    # ================================================================
    # SOFTWARE / 3C-SPECIFIC RULES
    # ================================================================
    ("S01", "high", r"(效率|速度|性能)(提升|提高|增加)\s*\d+\s*[%倍]",
     "效果提升数据需依据", "《广告法》第11条、第28条",
     "需标注数据来源和测试条件，如「基于XX测试」", {"software"}),
    ("S02", "mid", r"(一键|全自动|傻瓜式)[^。！？]{0,10}(搞定|解决|生成|完成)",
     "过度简化操作难度", "《广告法》第28条",
     "如实描述操作步骤，避免「一键搞定」式夸大", {"software"}),
    ("S03", "mid", r"(替代|取代|不用再找|不需要)(人工|设计师|程序员|客服|运营)",
     "替代人工的绝对化承诺", "《广告法》第28条",
     "改为「辅助」「提升效率」，不承诺完全替代", {"software"}),

    # ================================================================
    # FOOD-SPECIFIC RULES
    # ================================================================
    ("G01", "high", r"(治疗|治愈|根治|防癌|抗癌|降血压|降血糖|减肥|瘦身)",
     "食品疾病治疗/功效宣称", "《广告法》第17条；《食品安全法》第73条",
     "普通食品不得宣称保健/治疗功效，删除", {"food"}),
    ("G02", "high", r"(纯天然|零添加|无添加|不含任何添加剂)",
     "纯天然/无添加绝对化", "《广告法》第9条、第28条",
     "如属实需提供检测报告；否则改为「配料表干净」", {"food"}),
    ("G03", "mid", r"(最健康|最营养|最安全|最好的油|最好的米)",
     "食品类绝对化用语", "《广告法》第9条", "改为「营养丰富」「品质优良」", {"food"}),

    # ================================================================
    # BEAUTY-SPECIFIC RULES
    # ================================================================
    ("H01", "high", r"(医用|药妆|医美级|医学护肤|治疗)",
     "化妆品医疗术语宣称", "《化妆品监督管理条例》第43条；《广告法》第17条",
     "化妆品不得使用医疗术语，删除", {"beauty"}),
    ("H02", "high", r"(100%|完全|绝对)(不过敏|不敏感|温和)",
     "化妆品安全性绝对承诺", "《广告法》第28条",
     "改为「温和配方，敏感肌建议先做皮试」", {"beauty"}),
    ("H03", "mid", r"(立即|瞬间|当天|一次)(见效|变白|祛斑|去皱|瘦脸)",
     "即时效果承诺", "《广告法》第28条；《化妆品监督管理条例》",
     "效果因人而异，不得承诺即时见效", {"beauty"}),
    ("H04", "mid", r"(纯天然|无添加|零添加)(护肤|化妆品|配方)",
     "化妆品纯天然宣称", "《广告法》第28条",
     "化妆品均含化学成分，改为「成分精简」", {"beauty"}),
]

# SOP checklist per category: item -> regex signalling the item was covered.
# Every category inherits the "通用" (general) items automatically.
SOP_BASE = [
    ("售后政策", r"(七天无理由|7天无理由|运费险|质保|价保|能退能换|不满意.{0,4}退|退款|退货|取消订阅)"),
    ("关注/粉丝团引导", r"(点.{0,2}关注|粉丝券|粉丝团|专享券|关注主播)"),
    ("互动引导", r"(扣公屏|打在公屏|扣\s*1|评论区|有问题.{0,4}问|打在屏幕上)"),
    ("价格/优惠说明", r"(原价|折|优惠|活动价|到手价|券后|多少钱|价格)"),
    ("行动指令", r"(下单|拍|抢|买|点链接|小黄车|小风车|购物车|链接)"),
]

SOP_CATEGORY = {
    "apparel": [
        ("尺码引导", r"(\d{3}\s*穿|身高.{0,4}体重|报身高|码.{0,4}穿.{0,4}斤|尺码|穿多大)"),
        ("产品参数", r"(绒子|含绒量|充绒量|填充|克|面料|蓬松|棉|羽绒|材质)"),
        ("颜色款式讲解", r"(颜色|色系|黑色|白色|版型|款式|上身效果)"),
        ("发货时效", r"(小时.{0,4}发|今天买明天发|优先发货|门店调|现货|预售)"),
    ],
    "software": [
        ("功能介绍", r"(功能|模型|支持|可以.{0,4}做|能.{0,4}生成|版本)"),
        ("适用场景", r"(场景|适合|用于|办公|电商|自媒体|企业|个人|需求)"),
        ("退款/试用说明", r"(试用|退款|取消|到期|续费|订阅|免费试用|七天|7天)"),
        ("版本/套餐区别", r"(版本|套餐|档位|区别|不同|专业版|旗舰版|基础版)"),
    ],
    "food": [
        ("成分/配料说明", r"(配料|成分|原料|含量|蛋白质|脂肪|卡路里|热量)"),
        ("保质期/储存", r"(保质期|生产日期|储存|保存|冷藏|冷冻|常温)"),
        ("食用方法", r"(怎么吃|食用方法|做法|一次吃|每天|建议)"),
        ("规格/净含量", r"(克|斤|袋|盒|包|净含量|规格|装)"),
    ],
    "beauty": [
        ("成分/功效说明", r"(成分|功效|烟酰胺|玻尿酸|精华|保湿|美白|抗皱)"),
        ("适用肤质", r"(肤质|敏感肌|干皮|油皮|混合皮|适合.{0,4}肤)"),
        ("使用方法", r"(怎么用|使用方法|早晚|步骤|涂|抹|敷)"),
        ("规格/容量", r"(ml|毫升|g|克|瓶|支|片|容量|规格)"),
    ],
    "general": [],
}


def get_active_rules(category):
    """Return rules active for the given category."""
    return [r for r in RULES if r[6] is None or category in r[6]]


def get_sop_checks(category):
    """Return SOP checklist for the given category (base + category-specific)."""
    return SOP_BASE + SOP_CATEGORY.get(category, [])


def scan(text, category="general"):
    hits = []
    for rid, level, pattern, label, basis, fix, cats in get_active_rules(category):
        for match in re.finditer(pattern, text):
            snippet = text[max(0, match.start() - 15):match.end() + 15].replace("\n", " ")
            hits.append({
                "rule_id": rid,
                "level": level,
                "label": label,
                "matched": match.group(0),
                "context": snippet.strip(),
                "legal_basis": basis,
                "fix_hint": fix,
            })
    # dedupe by (rule_id, matched)
    seen, unique = set(), []
    for hit in hits:
        key = (hit["rule_id"], hit["matched"])
        if key not in seen:
            seen.add(key)
            unique.append(hit)
    return unique


def check_sop(text, category="general"):
    return [{"item": name, "covered": bool(re.search(pat, text))}
            for name, pat in get_sop_checks(category)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("transcript")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--category", default="general",
                        choices=["general", "apparel", "software", "food", "beauty"],
                        help="product category (default: general)")
    args = parser.parse_args()

    with open(args.transcript, encoding="utf-8") as handle:
        text = handle.read()

    hits = scan(text, args.category)
    sop = check_sop(text, args.category)

    if args.json:
        print(json.dumps({
            "category": args.category,
            "violations": hits,
            "sop": sop,
        }, ensure_ascii=False, indent=2))
        return

    order = {"high": 0, "mid": 1, "low": 2}
    hits.sort(key=lambda h: order.get(h["level"], 9))
    counts = {"high": 0, "mid": 0, "low": 0}
    for hit in hits:
        counts[hit["level"]] = counts.get(hit["level"], 0) + 1

    print(f"=== 违禁词扫描 [类目: {args.category}]：高{counts['high']} 中{counts['mid']} 低{counts['low']} ===\n")
    for hit in hits:
        print(f"[{hit['level'].upper()}] {hit['rule_id']} {hit['label']}")
        print(f"  命中：{hit['matched']}")
        print(f"  上下文：...{hit['context']}...")
        print(f"  依据：{hit['legal_basis']}")
        print(f"  建议：{hit['fix_hint']}\n")

    print("=== SOP 覆盖情况 ===")
    for item in sop:
        print(f"  {'✓' if item['covered'] else '✗'} {item['item']}")
    missing = [i["item"] for i in sop if not i["covered"]]
    if missing:
        print(f"\n[注意] 未检出：{', '.join(missing)}（需人工复核，关键词未命中不等于必然缺失）",
              file=sys.stderr)


if __name__ == "__main__":
    main()
