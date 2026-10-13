#!/usr/bin/env python3
"""compliance_training_gen.py — 合规培训材料生成 (Skill #43)"""
import sys
from datetime import datetime

def generate_training(topic: str = "数据合规") -> str:
    slides = f"""# 合规培训课件：{topic}

**培训时间**: {datetime.now().strftime('%Y年%m月%d日')}

---

## 第一章 培训目标
- 了解{topic}相关法律法规
- 识别日常业务中的合规风险
- 掌握合规操作要点

## 第二章 法律框架
- 《个人信息保护法》
- 《数据安全法》
- 《网络安全法》
- 行业监管规定

## 第三章 典型违规案例
1. 某APP过度收集个人信息被罚5000万
2. 某企业数据泄露未报告被行政处罚
3. 员工违规导出客户数据被解雇

## 第四章 合规操作指引
1. 最小必要原则收集数据
2. 敏感数据加密存储
3. 定期更新密码和权限
4. 发现违规立即报告

## 第五章 测试与考核
- 单选题10道
- 多选题5道
- 案例分析1道

---

**培训人**: ________ **参训人签字**: ________
"""
    return slides

def main():
    import argparse; p = argparse.ArgumentParser(); p.add_argument("--topic", default="数据合规"); p.add_argument("--output","-o"); a = p.parse_args()
    r = generate_training(a.topic)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f: f.write(r); print(f"✅ 已保存至: {a.output}")
    else: print(r)

if __name__ == "__main__": main()
