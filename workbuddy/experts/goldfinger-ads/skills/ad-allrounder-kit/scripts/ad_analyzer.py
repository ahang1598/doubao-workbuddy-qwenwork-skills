#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分广告级分级与操作建议脚本 v3（投放诊断优化专家 · 优化阶段使用）
支持自定义考核目标，适用于 ROI/CPL/CPA 多种模式。
在 v2 基础上：同时输出 CSV 调整清单 + Markdown 操作建议摘要，供闸门3逐条确认。
"""

import csv
import os
import argparse
from datetime import datetime, timedelta
from collections import defaultdict

def parse_num(s):
    """解析数值，兼容各种格式"""
    if not s or s == '-' or s == 'null':
        return 0.0
    try:
        val = float(str(s).replace(',', '').replace('%', ''))
        return val
    except:
        return 0.0

def calculate_age_days(ad_name):
    """从广告名称中提取上线日期，计算机龄"""
    import re
    # 匹配 MMDD 格式，如 0330, 0421
    match = re.search(r'-(\d{4})-', ad_name)
    if match:
        mmdd = match.group(1)
        try:
            month = int(mmdd[:2])
            day = int(mmdd[2:])
            # 假设当前年份
            year = datetime.now().year
            launch_date = datetime(year, month, day)
            age = (datetime.now() - launch_date).days
            return age if age >= 0 else age + 365
        except:
            pass
    return None

def get_health_tag(metric_value, target, metric_type='ROI'):
    """
    根据指标值和目标返回健康标签
    ROI/CPA/CPL 的判断逻辑不同
    """
    if metric_type == 'ROI':
        # ROI 越高越好
        if metric_value == 0:
            return '🔴 止损', '无转化'
        ratio = metric_value / target if target > 0 else 0
        if ratio >= 2.0:
            return '🚀 王牌', f'ROI 超目标 {ratio:.1f} 倍'
        elif ratio >= 1.0:
            return '🟢 健康', '达标'
        elif ratio >= 0.5:
            return '🟡 观察', '接近红线'
        else:
            return '🔴 止损', 'ROI 严重不达标'
    else:
        # CPL/CPA 越低越好
        if metric_value == 0 or metric_value == 999:
            return '🔴 止损', '无转化'
        ratio = metric_value / target if target > 0 else 999
        if ratio <= 0.5:
            return '🚀 王牌', f'成本仅为目标的 {ratio:.0%}'
        elif ratio <= 1.0:
            return '🟢 健康', '达标'
        elif ratio <= 1.5:
            return '🟡 观察', '成本偏高'
        else:
            return '🔴 止损', '成本严重超标'

def get_action_suggestion(health_tag, age_days, spend_today, metric_type='ROI'):
    """根据健康标签和机龄给出操作建议"""
    if '止损' in health_tag:
        return '软关停', '修改 begin_date 至次日'
    elif '王牌' in health_tag:
        if spend_today < 500:
            return '梯度提价', '提价 5-10%，观察 4 小时'
        else:
            return '保持/扩量', '可考虑放开预算上限'
    elif '观察' in health_tag:
        if age_days and age_days > 21:
            return '减量观察', '老计划衰退期，准备替换'
        else:
            return '继续观察', '监控 2-4 小时'
    else:  # 健康
        if age_days and age_days > 14:
            return '保持', '成熟期，稳定为主'
        else:
            return '保持/提价', '可尝试小幅提价'

def analyze_ads(input_csv, output_csv, mode, daily_target, weekly_target, stop_loss_threshold):
    """
    主分析函数
    
    Args:
        input_csv: 输入数据文件路径
        output_csv: 输出结果文件路径
        mode: 分析模式 (ROI/CPL/CPA)
        daily_target: 当日考核目标
        weekly_target: 7日考核目标（ROI模式专用）
        stop_loss_threshold: 止损消耗阈值
    """
    
    # 读取数据
    data = []
    try:
        with open(input_csv, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return
    
    if not data:
        print("❌ 数据为空")
        return
    
    print(f"📊 读取到 {len(data)} 条记录")
    
    # 字段映射（兼容不同来源的CSV）
    field_mapping = {
        'date': ['日期', 'date', 'stat_date'],
        'account_id': ['账户ID', 'account_id', 'advertiser_id'],
        'ad_id': ['广告ID', 'adgroup_id', 'ad_id'],
        'ad_name': ['广告名称', 'adgroup_name', 'ad_name'],
        'cost': ['花费', 'cost', '消耗', 'spend'],
        'conversions': ['转化数', 'conversions', '付费次数', 'purchase_pv'],
        'purchase_roi': ['付费ROI', 'purchase_roi', 'ROI'],
        'fd_roi': ['当日ROI', 'cheout_fd_reward', 'first_day_roi'],
        'roi_7d': ['7日ROI', 'cheout_ow_reward', 'roi_7d'],
        'cpl': ['CPL', 'cpl', '表单成本', 'form_cost'],
        'leads': ['线索数', 'leads', 'leads_count', '表单预约'],
    }
    
    def get_field(row, field_type):
        """根据字段类型获取值"""
        for key in field_mapping.get(field_type, []):
            if key in row:
                return row[key]
        return None
    
    # 识别日期范围
    dates = sorted(list(set(get_field(row, 'date') or '' for row in data if get_field(row, 'date'))))
    if not dates:
        print("❌ 无法识别日期字段")
        return
    
    today = dates[-1]
    week_ago = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=6)).strftime("%Y-%m-%d") if len(dates) > 1 else today
    
    print(f"📅 分析周期: {week_ago} ~ {today}")
    print(f"🎯 考核模式: {mode}")
    if mode == 'ROI':
        print(f"🎯 考核目标: 当日 ROI > {daily_target}, 7日 ROI > {weekly_target}")
    else:
        print(f"🎯 考核目标: {mode} ≤ {daily_target}")
    
    # 聚合广告级数据
    ad_stats = defaultdict(lambda: {
        'account_id': '',
        'ad_name': '',
        'spend_7d': 0.0,
        'spend_today': 0.0,
        'conversions_7d': 0,
        'roi_today': 0.0,
        'roi_7d': 0.0,
        'cpl_7d': 999.0,
    })
    
    for row in data:
        ad_id = get_field(row, 'ad_id')
        if not ad_id:
            continue
        
        dt = get_field(row, 'date') or ''
        cost = parse_num(get_field(row, 'cost'))
        conv = parse_num(get_field(row, 'conversions'))
        
        ad_stats[ad_id]['account_id'] = get_field(row, 'account_id') or ''
        ad_stats[ad_id]['ad_name'] = get_field(row, 'ad_name') or ''
        
        # 7日累计
        if dt >= week_ago:
            ad_stats[ad_id]['spend_7d'] += cost
            ad_stats[ad_id]['conversions_7d'] += int(conv)
        
        # 今日数据
        if dt == today:
            ad_stats[ad_id]['spend_today'] = cost
            
            if mode == 'ROI':
                # 优先使用 API 返回的 ROI 字段
                roi_today = parse_num(get_field(row, 'fd_roi'))
                roi_7d = parse_num(get_field(row, 'roi_7d'))
                # 如果没有专门字段，用 purchase_roi
                if roi_7d == 0:
                    roi_7d = parse_num(get_field(row, 'purchase_roi'))
                ad_stats[ad_id]['roi_today'] = roi_today
                ad_stats[ad_id]['roi_7d'] = roi_7d
    
    # 计算 CPL（针对 CPL/CPA 模式）
    if mode in ['CPL', 'CPA']:
        for ad_id, stats in ad_stats.items():
            if stats['conversions_7d'] > 0:
                stats['cpl_7d'] = stats['spend_7d'] / stats['conversions_7d']
            else:
                stats['cpl_7d'] = 999.0 if stats['spend_7d'] > 0 else 0
    
    # 分析每个广告
    results = []
    for ad_id, stats in ad_stats.items():
        # 跳过无消耗的广告
        if stats['spend_7d'] == 0:
            continue
        
        # 计算机龄
        age_days = calculate_age_days(stats['ad_name'])
        
        # 确定核心指标
        if mode == 'ROI':
            core_metric = stats['roi_7d']
            core_metric_label = f"{core_metric:.2f}" if core_metric > 0 else "0"
            daily_metric = stats['roi_today']
            daily_metric_label = f"{daily_metric:.2f}" if daily_metric > 0 else "0"
            
            # 健康度判定
            health_tag, health_reason = get_health_tag(core_metric, weekly_target, 'ROI')
            
            # 空耗止损判定
            if stats['spend_7d'] > stop_loss_threshold and core_metric == 0:
                health_tag = '🔴 止损'
                health_reason = f'空耗 {stats["spend_7d"]:.0f} 元，无ROI产出'
        else:
            core_metric = stats['cpl_7d']
            core_metric_label = f"{core_metric:.2f}" if core_metric < 999 else "无转化"
            daily_metric = core_metric  # CPL 模式当日=7日
            daily_metric_label = core_metric_label
            
            health_tag, health_reason = get_health_tag(core_metric, daily_target, 'CPL')
            
            if stats['spend_7d'] > stop_loss_threshold and stats['conversions_7d'] == 0:
                health_tag = '🔴 止损'
                health_reason = f'空耗 {stats["spend_7d"]:.0f} 元，无转化'
        
        # 获取操作建议
        action, detail = get_action_suggestion(health_tag, age_days, stats['spend_today'], mode)
        
        results.append({
            'account_id': stats['account_id'],
            'adgroup_id': ad_id,
            'adgroup_name': stats['ad_name'],
            'cost_7d': round(stats['spend_7d'], 2),
            'cost_today': round(stats['spend_today'], 2),
            'conversions_7d': stats['conversions_7d'],
            'core_metric': core_metric_label,
            'daily_metric': daily_metric_label,
            'target': weekly_target if mode == 'ROI' else daily_target,
            'health_tag': health_tag,
            'health_reason': health_reason,
            '调整动作': action,
            '具体详情': detail,
            'age_days': age_days if age_days else '-'
        })
    
    # 按健康度排序：止损 > 观察 > 健康 > 王牌
    tag_order = {'🔴 止损': 0, '🟡 观察': 1, '🟢 健康': 2, '🚀 王牌': 3}
    results.sort(key=lambda x: (tag_order.get(x['health_tag'], 99), -x['cost_7d']))
    
    # 输出结果
    if results:
        with open(output_csv, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        print(f"✅ 分析完成，CSV 调整清单已保存至: {output_csv}")
        print(f"   - 总计 {len(results)} 条在投广告")
        print(f"   - 🔴 止损: {sum(1 for r in results if '止损' in r['health_tag'])} 条")
        print(f"   - 🟡 观察: {sum(1 for r in results if '观察' in r['health_tag'])} 条")
        print(f"   - 🟢 健康: {sum(1 for r in results if '健康' in r['health_tag'])} 条")
        print(f"   - 🚀 王牌: {sum(1 for r in results if '王牌' in r['health_tag'])} 条")
        # 同步输出 Markdown 操作建议摘要（供闸门3逐条确认）
        md_path = os.path.splitext(output_csv)[0] + '_操作建议.md'
        write_action_md(results, md_path, mode, week_ago, today)
        print(f"✅ Markdown 操作建议已保存至: {md_path}")
    else:
        print("⚠️ 未找到有效数据")


def write_action_md(results, md_path, mode, week_ago, today):
    """按健康度分组输出可逐条确认的操作建议 Markdown。"""
    def group(tag_kw):
        return [r for r in results if tag_kw in r['health_tag']]
    stop = group('止损'); watch = group('观察'); good = group('健康'); ace = group('王牌')
    total_cost = sum(r['cost_7d'] for r in results)
    L = []
    L.append(f"# 分广告级操作建议（{mode} 模式）\n")
    L.append(f"> 周期 {week_ago} ~ {today}　|　在投 {len(results)} 条　|　总消耗 {total_cost:,.0f}\n")
    L.append(f"> 🔴止损 {len(stop)}　🟡观察 {len(watch)}　🟢健康 {len(good)}　🚀王牌 {len(ace)}\n")
    L.append("\n> ⚠️ 以下为建议清单，请**逐条确认**是否执行；默认只出清单不直接改账户。\n")

    def section(title, rows, note):
        if not rows:
            return
        L.append(f"\n## {title}（{len(rows)} 条）")
        L.append(f"_{note}_\n")
        L.append("| 确认 | 计划ID | 计划名 | 7日消耗 | 核心指标 | 动作 | 详情 |")
        L.append("| :-: | :-- | :-- | --: | :-- | :-- | :-- |")
        for r in rows:
            L.append(f"| ☐ | {r['adgroup_id']} | {r['adgroup_name'][:24]} | "
                     f"{r['cost_7d']:,.0f} | {r['core_metric']} | {r['调整动作']} | {r['具体详情']} |")

    section("🔴 止损池", stop, "建议改起投日为次日软关停，保模型不硬关。")
    section("🚀 扩量池", ace, "远超目标，建议梯度提价/提预算抢量。")
    section("🟡 观察池", watch, "临界状态，按详情减量观察或微调。")
    section("🟢 健康池", good, "达标，保持或小幅优化。")
    L.append("\n---\n确认后请告知：全部采纳 / 部分采纳（列出计划ID）/ 调整某条。")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(L))

def main():
    parser = argparse.ArgumentParser(description='分广告级分级与操作建议工具 v3')
    parser.add_argument('input_csv', help='输入CSV文件路径')
    parser.add_argument('output_csv', help='输出CSV文件路径')
    parser.add_argument('mode', choices=['ROI', 'CPL', 'CPA'], help='分析模式')
    parser.add_argument('--daily_target', type=float, default=None, 
                        help='当日考核目标 (ROI模式为当日ROI阈值，CPL/CPA模式为成本红线)')
    parser.add_argument('--weekly_target', type=float, default=None,
                        help='7日考核目标 (仅ROI模式需要)')
    parser.add_argument('--target', type=float, default=None,
                        help='统一考核目标 (简化参数，用于CPL/CPA模式)')
    parser.add_argument('--stop_loss', type=float, default=None,
                        help='止损消耗阈值 (默认: ROI模式500元, CPL/CPA模式为目标的3倍)')
    
    args = parser.parse_args()
    
    # 参数处理
    if args.mode == 'ROI':
        daily_target = args.daily_target if args.daily_target else 1.0
        weekly_target = args.weekly_target if args.weekly_target else 2.0
        stop_loss = args.stop_loss if args.stop_loss else 500
    else:
        daily_target = args.target if args.target else (args.daily_target if args.daily_target else 27)
        weekly_target = daily_target  # CPL/CPA 模式不区分日/周
        stop_loss = args.stop_loss if args.stop_loss else (daily_target * 3)
    
    analyze_ads(args.input_csv, args.output_csv, args.mode, 
                daily_target, weekly_target, stop_loss)

if __name__ == '__main__':
    main()
