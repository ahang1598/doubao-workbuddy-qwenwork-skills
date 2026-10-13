#!/usr/bin/env python3
"""dpi_template.py — 数据保护影响评估模板 (Skill #40)"""
import sys
from datetime as datetime

def generate_dpi(project: str, data_types: str, purpose: str) -> str:
    return f"""# 数据保护影响评估 (DPIA)

**项目名称**: {project}
**评估时间**: {datetime.now().strftime('%Y-%m-%d')}
**涉及数据类型**: {data_types}
**处理目的**: {purpose}

## 一、数据处理描述
1. 处理目的: {purpose}
2. 数据类型: {data_types}
3. 数据主体: 用户/员工/客户
4. 数据接收方: 内部系统
5. 是否跨境传输: 否

## 二、必要性与比例性评估
- [ ] 处理目的是否明确、合法
- [ ] 数据收集是否遵循最小必要原则
- [ ] 保留期限是否合理
- [ ] 是否有替代方案可降低数据处理量

## 三、风险评估
| 风险类型 | 可能性 | 影响程度 | 风险等级 |
|----------|--------|----------|----------|
| 数据泄露 | 低/中/高 | 低/中/高 | 需评估 |
| 未授权访问 | 低/中/高 | 低/中/高 | 需评估 |
| 数据篡改 | 低/中/高 | 低/中/高 | 需评估 |
| 过度收集 | 低/中/高 | 低/中/高 | 需评估 |

## 四、缓解措施
1. 技术措施: 加密存储与传输、访问控制、审计日志
2. 管理措施: 最小授权、定期培训、应急预案
3. 法律措施: 隐私政策、用户同意、数据处理协议

## 五、评估结论
- [ ] 风险可接受，可继续实施
- [ ] 需实施缓解措施后方可实施
- [ ] 风险过高，建议重新设计方案

**评估人**: ________ **审核人**: ________
"""
def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--project", default="新项目")
    p.add_argument("--data-types", default="个人信息")
    p.add_argument("--purpose", default="业务需要")
    p.add_argument("--output", "-o")
    a = p.parse_args()
    from datetime import datetime
    r = generate_dpi(a.project, a.data_types, a.purpose)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f: f.write(r)
        print(f"✅ 已保存至: {a.output}")
    else: print(r)
if __name__ == "__main__": main()
