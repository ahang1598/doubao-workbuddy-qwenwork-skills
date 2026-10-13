#!/usr/bin/env python3
"""anti_bribery_policy.py — 反商业贿赂制度 (Skill #42)"""
import sys
from datetime import datetime

def generate_policy(company: str = "公司") -> str:
    return f"""# {company}反商业贿赂制度

**生效日期**: {datetime.now().strftime('%Y年%m月%d日')}

## 一、禁止行为
1. 不得以任何名义向政府官员、商业伙伴提供不当利益
2. 禁止收受回扣、佣金、礼金、有价证券等
3. 禁止安排旅游、宴请、娱乐等变相贿赂
4. 禁止通过第三方实施商业贿赂

## 二、礼品与招待标准
- 单次价值不超过500元人民币
- 不得为现金或等价物
- 须登记备案并经上级审批
- 禁止在招投标/决策敏感期赠送

## 三、第三方管理
1. 对代理商/经销商进行反贿赂尽职调查
2. 合同中加入反贿赂条款
3. 定期审计第三方合规情况

## 四、举报机制
- 设立匿名举报渠道
- 举报人保护措施
- 查实奖励机制

## 五、法律责任
- **行政处罚**: 没收违法所得+罚款（10万-300万）
- **刑事责任**: 行贿罪最高无期徒刑；对非国家工作人员行贿罪最高10年
- **内部处分**: 解除劳动合同、追缴违法所得

## 六、法律依据
《刑法》第164条、《反不正当竞争法》第7条
"""
def main():
    import argparse; p = argparse.ArgumentParser(); p.add_argument("--company", default="公司"); p.add_argument("--output","-o"); a = p.parse_args()
    r = generate_policy(a.company)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f: f.write(r); print(f"✅ 已保存至: {a.output}")
    else: print(r)
if __name__ == "__main__": main()
