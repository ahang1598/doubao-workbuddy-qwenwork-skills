#!/usr/bin/env python3
"""
trademark_search.py — 商标检索技能 (Skill #27)
根据关键词/图形编码检索商标注册情况。

用法: python trademark_search.py "小米" --class 9
"""

import sys
import json
from datetime import datetime

NICE_CLASSIFICATIONS = {
    1: "化学品", 2: "颜料油漆", 3: "日化用品", 4: "燃料油脂", 5: "医药",
    6: "金属材料", 7: "机械设备", 8: "手工器具", 9: "电子仪器/软件",
    10: "医疗器械", 11: "灯具空调", 12: "运输工具", 13: "军火烟火",
    14: "珠宝钟表", 15: "乐器", 16: "办公用品", 17: "橡胶制品",
    18: "皮革皮具", 19: "建筑材料", 20: "家具", 21: "厨房洁具",
    22: "绳网袋篷", 23: "纺织纱线", 24: "布料床单", 25: "服装鞋帽",
    26: "钮扣拉链", 27: "地毯席垫", 28: "健身器材", 29: "食品",
    30: "方便食品", 31: "生鲜农产", 32: "啤酒饮料", 33: "酒",
    34: "烟草烟具", 35: "广告销售", 36: "金融物管", 37: "建筑修理",
    38: "通讯服务", 39: "运输贮藏", 40: "材料加工", 41: "教育娱乐",
    42: "科技服务", 43: "餐饮住宿", 44: "医疗园艺", 45: "法律服务"
}

MOCK_TRADEMARK_DB = [
    {"name": "小米", "class": 9, "owner": "小米科技有限责任公司", "reg_no": "8911234", "status": "有效", "reg_date": "2012-03-28", "expiry": "2032-03-27"},
    {"name": "小米", "class": 35, "owner": "小米科技有限责任公司", "reg_no": "10212345", "status": "有效", "reg_date": "2013-01-15", "expiry": "2033-01-14"},
    {"name": "小米", "class": 42, "owner": "小米科技有限责任公司", "reg_no": "12456789", "status": "有效", "reg_date": "2014-07-20", "expiry": "2034-07-19"},
    {"name": "华为", "class": 9, "owner": "华为技术有限公司", "reg_no": "6543210", "status": "有效", "reg_date": "2005-09-10", "expiry": "2035-09-09"},
    {"name": "微信", "class": 9, "owner": "腾讯科技(深圳)有限公司", "reg_no": "9876543", "status": "有效", "reg_date": "2011-01-21", "expiry": "2031-01-20"},
    {"name": "微信", "class": 38, "owner": "腾讯科技(深圳)有限公司", "reg_no": "10123456", "status": "有效", "reg_date": "2011-06-15", "expiry": "2031-06-14"},
    {"name": "抖音", "class": 9, "owner": "北京字节跳动科技有限公司", "reg_no": "23456789", "status": "有效", "reg_date": "2016-09-01", "expiry": "2036-08-31"},
    {"name": "抖音", "class": 41, "owner": "北京字节跳动科技有限公司", "reg_no": "24567890", "status": "有效", "reg_date": "2017-02-15", "expiry": "2037-02-14"},
    {"name": "淘宝", "class": 35, "owner": "阿里巴巴集团控股有限公司", "reg_no": "5432109", "status": "有效", "reg_date": "2004-05-20", "expiry": "2034-05-19"},
    {"name": "拼多多", "class": 35, "owner": "上海寻梦信息技术有限公司", "reg_no": "19876543", "status": "有效", "reg_date": "2015-12-01", "expiry": "2035-11-30"},
]


def search_trademark(keyword: str, nice_class: int = None) -> list:
    """检索商标"""
    results = []
    for tm in MOCK_TRADEMARK_DB:
        if keyword.lower() in tm["name"].lower():
            if nice_class is None or tm["class"] == nice_class:
                results.append(tm)
    return results


def analyze_conflict(keyword: str, nice_class: int) -> dict:
    """分析商标注册冲突风险"""
    existing = search_trademark(keyword, nice_class)
    same_class = [tm for tm in existing if tm["class"] == nice_class]
    similar_class = [tm for tm in existing if tm["class"] != nice_class]

    if same_class:
        risk = "高"
        advice = f"在第{nice_class}类已有相同商标注册，申请可能被驳回。建议：(1) 修改商标名称；(2) 查询是否有共存协议可能；(3) 考虑商标撤销（连续3年不使用）。"
    elif similar_class:
        risk = "中"
        advice = f"在其他类别有相同商标注册，在第{nice_class}类注册存在一定的近似风险。建议申请前做好商标监测。"
    else:
        risk = "低"
        advice = f"在第{nice_class}类未检索到相同商标，注册前景较好。建议尽快提交申请以抢占先机。"

    return {
        "keyword": keyword,
        "nice_class": nice_class,
        "class_name": NICE_CLASSIFICATIONS.get(nice_class, "未知"),
        "existing_trademarks": existing,
        "conflict_risk": risk,
        "advice": advice
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="商标检索")
    parser.add_argument("keyword", help="商标名称")
    parser.add_argument("--class", dest="nice_class", type=int, help="尼斯分类号(1-45)")
    parser.add_argument("--output", "-o")
    args = parser.parse_args()

    if args.nice_class:
        analysis = analyze_conflict(args.keyword, args.nice_class)
        report = f"# 商标检索报告\n\n"
        report += f"**检索商标**: {analysis['keyword']}\n"
        report += f"**申请类别**: 第{analysis['nice_class']}类 - {analysis['class_name']}\n"
        report += f"**冲突风险**: {'🔴' if analysis['conflict_risk'] == '高' else '🟡' if analysis['conflict_risk'] == '中' else '🟢'} {analysis['conflict_risk']}\n\n"
        report += f"## 检索结果\n\n"
        if analysis['existing_trademarks']:
            for tm in analysis['existing_trademarks']:
                report += f"- **{tm['name']}**（第{tm['class']}类）注册号: {tm['reg_no']} | 持有人: {tm['owner']} | 状态: {tm['status']}\n"
        else:
            report += "未检索到相同商标。\n"
        report += f"\n## 建议\n\n{analysis['advice']}\n"
    else:
        results = search_trademark(args.keyword)
        report = f"# 商标检索结果\n\n关键词: {args.keyword}\n\n"
        for tm in results:
            report += f"- **{tm['name']}**（第{tm['class']}类 {NICE_CLASSIFICATIONS.get(tm['class'], '')}）注册号: {tm['reg_no']} | 持有人: {tm['owner']} | 到期: {tm['expiry']}\n"
        if not results:
            report += "未检索到相关商标。\n"

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"✅ 已保存至: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
