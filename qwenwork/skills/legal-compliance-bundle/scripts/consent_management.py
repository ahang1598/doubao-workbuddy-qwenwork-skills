#!/usr/bin/env python3
"""consent_management.py — 合规同意管理 (Skill #37) 设计用户同意流程。"""
import sys
from datetime import datetime

def design_consent_flow(product: str = "APP") -> str:
    r = f"# {product}用户同意管理方案\n\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n\n"
    r += "## 同意类型\n\n| 场景 | 同意类型 | 法律依据 |\n|------|----------|----------|\n| 基础功能信息收集 | 一般同意 | PIPL第13条 |\n| 敏感信息(位置/通讯录) | 单独同意 | PIPL第29条 |\n| 14岁以下儿童 | 监护人同意 | PIPL第31条 |\n| 个人信息出境 | 单独同意 | PIPL第39条 |\n| 营销推送 | 明确同意 | 个保法第24条 |\n\n"
    r += "## 同意流程设计\n\n"
    r += "### Step 1: 首次打开\n- 显示隐私政策弹窗（非默认勾选）\n- 勾选框必须用户主动勾选\n- 提供「拒绝」和「同意」两个同等明显按钮\n\n"
    r += "### Step 2: 功能触发时\n- 弹出该功能所需的权限说明\n- 解释为什么需要该权限\n- 提供「仅使用时允许」「始终允许」「拒绝」选项\n\n"
    r += "### Step 3: 敏感信息收集\n- 单独弹窗，不得合并到隐私政策\n- 明确告知收集目的和使用方式\n- 提供便捷的撤回途径\n\n"
    r += "## 合规要点\n\n1. 不得默认勾选同意\n2. 不得以拒绝提供服务为由强迫同意\n3. 必须提供便捷的撤回同意方式\n4. 同意记录保存至少3年\n5. 隐私政策语言通俗易懂\n"
    return r

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--product", default="APP")
    p.add_argument("--output", "-o")
    a = p.parse_args()
    r = design_consent_flow(a.product)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f: f.write(r)
        print(f"✅ 已保存至: {a.output}")
    else: print(r)

if __name__ == "__main__": main()
