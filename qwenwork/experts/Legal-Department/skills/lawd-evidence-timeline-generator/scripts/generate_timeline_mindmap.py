#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
证据时间线思维导图生成脚本

功能：根据 JSON 格式的时间线数据，生成基于 ECharts 的交互式 HTML 思维导图文件。

使用方法：
    python generate_timeline_mindmap.py \
        --case-name "案件名称" \
        --output "outputs/案件名称_时间线思维导图.html" \
        --data '{"basic_info": [...], "timeline": [...], ...}'

或：
    python generate_timeline_mindmap.py \
        --case-name "案件名称" \
        --output "outputs/案件名称_时间线思维导图.html" \
        --data-file "data/timeline_data.json"

依赖：
    - Python 3.7+
    - 无需额外 pip 包（仅使用标准库）
"""

import argparse
import json
import os
import sys
from pathlib import Path


def load_template(template_path=None):
    """加载 HTML 模板文件"""
    if template_path is None:
        # 默认模板路径：当前脚本所在目录的 references/mindmap-template.html
        script_dir = Path(__file__).parent.parent
        template_path = script_dir / "references" / "mindmap-template.html"
    
    if not os.path.exists(template_path):
        print(f"错误：模板文件不存在：{template_path}", file=sys.stderr)
        sys.exit(1)
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    
    return template


def build_tree_data(data):
    """
    构建 ECharts 树形图数据结构
    
    参数：
        data: 包含 basic_info, timeline, disputes, evidence_list 的字典
    
    返回：
        ECharts 树形图数据节点
    """
    case_name = data.get("case_name", "案件名称")
    
    # 根节点
    root = {
        "name": f"{case_name}\n证据材料",
        "children": []
    }
    
    # 1. 案件基本信息分支
    basic_info = data.get("basic_info", [])
    if basic_info:
        basic_node = {
            "name": "案件基本信息",
            "itemStyle": {"color": "#FFD700"},  # 金色
            "children": [
                {"name": item.get("name", "")} for item in basic_info
            ]
        }
        root["children"].append(basic_node)
    
    # 2. 时间线事件分支
    timeline = data.get("timeline", [])
    if timeline:
        timeline_node = {
            "name": "时间线事件",
            "itemStyle": {"color": "#90EE90"},  # 浅绿色
            "children": []
        }
        
        for month_data in timeline:
            month = month_data.get("month", "")
            events = month_data.get("events", [])
            
            if not events:
                continue
            
            month_node = {
                "name": month,
                "children": []
            }
            
            for event in events:
                date = event.get("date", "")
                event_name = event.get("event", "")
                page = event.get("page", "")
                
                # 构建节点名称
                if page:
                    node_name = f"{date}<br>{event_name}<br><span style=\"color:#999\">{page}</span>"
                else:
                    node_name = f"{date}<br>{event_name}"
                
                month_node["children"].append({"name": node_name})
            
            timeline_node["children"].append(month_node)
        
        root["children"].append(timeline_node)
    
    # 3. 关键争议点分支
    disputes = data.get("disputes", [])
    if disputes:
        disputes_node = {
            "name": "关键争议点",
            "itemStyle": {"color": "#FF6B6B"},  # 浅红色
            "children": []
        }
        
        for dispute in disputes:
            dispute_name = dispute.get("name", "")
            items = dispute.get("items", [])
            
            dispute_node = {
                "name": dispute_name,
                "children": [
                    {"name": item.get("name", "")} for item in items
                ]
            }
            disputes_node["children"].append(dispute_node)
        
        root["children"].append(disputes_node)
    
    # 4. 证据清单分支
    evidence_list = data.get("evidence_list", [])
    if evidence_list:
        evidence_node = {
            "name": "证据清单",
            "itemStyle": {"color": "#87CEEB"},  # 天蓝色
            "children": [
                {"name": item.get("name", "")} for item in evidence_list
            ]
        }
        root["children"].append(evidence_node)
    
    return root


def generate_html(case_name, data, output_path, template_path=None):
    """
    生成 HTML 思维导图文件
    
    参数：
        case_name: 案件名称
        data: JSON 格式的时间线数据（字典或 JSON 字符串）
        output_path: 输出文件路径
        template_path: 模板文件路径（可选）
    """
    # 加载模板
    template = load_template(template_path)
    
    # 解析数据
    if isinstance(data, str):
        data_dict = json.loads(data)
    else:
        data_dict = data
    
    # 构建树形数据
    tree_data = build_tree_data(data_dict)
    
    # 替换模板变量
    html = template.replace("{CASE_NAME}", case_name)
    
    # 将树形数据转换为 JSON 字符串并替换
    data_json = json.dumps(tree_data, ensure_ascii=False, indent=4)
    html = html.replace("{DATA}", data_json)
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✓ 思维导图已生成：{output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="生成证据时间线思维导图（HTML 格式）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 使用 JSON 字符串
  python generate_timeline_mindmap.py \\
      --case-name "锦溪颐景御府项目" \\
      --output "outputs/锦溪颐景御府项目_时间线思维导图.html" \\
      --data '{"case_name": "锦溪颐景御府项目", "basic_info": [...]}'

  # 使用 JSON 文件
  python generate_timeline_mindmap.py \\
      --case-name "锦溪颐景御府项目" \\
      --output "outputs/锦溪颐景御府项目_时间线思维导图.html" \\
      --data-file "data/timeline_data.json"
        """
    )
    
    parser.add_argument(
        "--case-name",
        required=True,
        help="案件名称"
    )
    
    parser.add_argument(
        "--output",
        required=True,
        help="输出文件路径（HTML 文件）"
    )
    
    parser.add_argument(
        "--data",
        help="JSON 格式的时间线数据（字符串）"
    )
    
    parser.add_argument(
        "--data-file",
        help="JSON 格式的时间线数据文件路径"
    )
    
    parser.add_argument(
        "--template",
        help="HTML 模板文件路径（可选，默认使用 references/mindmap-template.html）"
    )
    
    args = parser.parse_args()
    
    # 验证参数
    if not args.data and not args.data_file:
        parser.error("必须指定 --data 或 --data-file 参数")
    
    # 读取数据
    if args.data_file:
        if not os.path.exists(args.data_file):
            print(f"错误：数据文件不存在：{args.data_file}", file=sys.stderr)
            sys.exit(1)
        
        with open(args.data_file, 'r', encoding='utf-8') as f:
            data = f.read()
    else:
        data = args.data
    
    # 生成 HTML
    try:
        generate_html(
            case_name=args.case_name,
            data=data,
            output_path=args.output,
            template_path=args.template
        )
    except Exception as e:
        print(f"错误：生成失败：{e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
