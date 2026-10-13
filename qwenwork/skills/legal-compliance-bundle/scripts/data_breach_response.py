#!/usr/bin/env python3
"""data_breach_response.py — 数据泄露应急预案生成 (Skill #38)"""
import sys
from datetime import datetime

def generate_plan(company: str = "公司") -> str:
    return f"""# {company}数据泄露应急预案

**版本**: 1.0 | **生成时间**: {datetime.now().strftime('%Y-%m-%d')}

## 一、应急组织架构
- **应急总指挥**: 首席安全官(CSO)
- **技术处置组**: 信息安全团队
- **法务合规组**: 法务部 + 合规部
- **公关协调组**: 公关部 + 客服部
- **管理层报告**: CEO / CTO

## 二、事件分级
| 级别 | 定义 | 响应时间 | 上报对象 |
|------|------|----------|----------|
| P0-严重 | 超10万人数据泄露 | 15分钟 | 管理层+监管 |
| P1-重大 | 1-10万人数据泄露 | 1小时 | 管理层 |
| P2-较大 | <1万人数据泄露 | 4小时 | 安全部门 |
| P3-一般 | 疑似泄露/小规模 | 24小时 | 安全部门 |

## 三、应急响应流程

### 3.1 发现与报告 (0-30分钟)
1. 发现异常立即报告安全团队
2. 安全团队确认事件真实性
3. 评估影响范围和严重程度
4. 启动对应级别应急响应

### 3.2 遏制与止损 (30分钟-4小时)
1. 隔离受影响系统
2. 收集并保全证据（日志、截图）
3. 修补漏洞
4. 阻断泄露渠道

### 3.3 通知与报告 (72小时内)
1. **监管报告**: 向网信部门和公安部门报告（PIPL第57条）
2. **用户通知**: 通知受影响用户（方式：短信/邮件/APP推送）
3. **内容**: 泄露类型、可能影响、已采取措施、用户防护建议

### 3.4 恢复与整改
1. 恢复正常服务
2. 完整取证分析
3. 整改安全措施
4. 事后复盘报告

## 四、联系方式
- 网信办举报中心: 12377
- 公安部网络违法犯罪举报: www.12321.cn
- 信息安全应急: （填写内部联系方式）
"""
def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--company", default="公司")
    p.add_argument("--output", "-o")
    a = p.parse_args()
    r = generate_plan(a.company)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f: f.write(r)
        print(f"✅ 已保存至: {a.output}")
    else: print(r)
if __name__ == "__main__": main()
