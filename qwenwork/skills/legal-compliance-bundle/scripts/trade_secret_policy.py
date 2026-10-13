#!/usr/bin/env python3
"""trade_secret_policy.py — 商业秘密保护制度生成 (Skill #31)"""
import sys
from datetime import datetime

def generate_policy(company: str = "公司") -> str:
    return f"""# {company}商业秘密保护制度

**生效日期**: {datetime.now().strftime('%Y年%m月%d日')}

## 一、总则
为保护公司商业秘密，维护公司合法权益，根据《反不正当竞争法》及相关法律法规，制定本制度。

## 二、商业秘密范围
1. **技术秘密**: 产品配方、工艺流程、技术方案、设计图纸、源代码、算法模型等
2. **经营秘密**: 客户名单、供应商信息、定价策略、营销计划、财务数据、并购意向等
3. **管理秘密**: 人事薪酬、绩效考核、内部决策等

## 三、保密等级
- **绝密**: 泄露将造成特别严重损害（如核心源代码、战略规划）
- **机密**: 泄露将造成严重损害（如客户数据库、技术方案）
- **秘密**: 泄露将造成一定损害（如一般业务流程、内部通知）

## 四、保密措施
1. 与涉密人员签订保密协议和竞业限制协议
2. 商业秘密载体标注保密标识并妥善保管
3. 限制商业秘密的知悉范围，实行分级授权
4. 计算机信息系统设置访问权限和审计日志
5. 涉密区域设置门禁和监控

## 五、员工保密义务
1. 不得泄露工作中知悉的商业秘密
2. 不得利用商业秘密谋取个人利益
3. 离职时应归还全部涉密资料
4. 离职后保密义务持续有效（保密期限约定）

## 六、违约责任
违反本制度的，公司有权：
1. 要求立即停止侵害行为
2. 要求赔偿经济损失
3. 依法追究法律责任（刑事责任：侵犯商业秘密罪，最高7年有期徒刑）

## 七、附则
本制度自发布之日起施行，由法务部负责解释。
"""

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--company", default="公司")
    p.add_argument("--output", "-o")
    a = p.parse_args()
    r = generate_policy(a.company)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f: f.write(r)
        print(f"✅ 已保存至: {a.output}")
    else: print(r)

if __name__ == "__main__": main()
