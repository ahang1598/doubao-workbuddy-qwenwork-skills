#!/usr/bin/env python3
"""
legal_qa.py — 法律问答技能 (Skill #11)
基于中国法律知识库的智能法律问答。

用法: python legal_qa.py "你的法律问题" [--api-key KEY]
"""

import os
import sys
import json
import httpx
from pathlib import Path
from typing import Optional

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"

# ─── 法律知识库（精简版）───
LEGAL_KNOWLEDGE = {
    "劳动合同": {
        "相关法律": ["《劳动合同法》", "《劳动法》", "《社会保险法》"],
        "要点": [
            "试用期最长不超过6个月（3年以上合同）",
            "用人单位不得随意解除劳动合同（第39-41条除外）",
            "经济补偿金按每满一年支付一个月工资标准",
            "竞业限制期限最长不超过2年",
        ],
        "常见问题": {
            "被辞退怎么赔偿": "如用人单位违法解除，应支付2倍经济补偿金（《劳动合同法》第87条）",
            "试用期被辞退": "试用期内用人单位需证明不符合录用条件，否则属违法解除",
            "没签劳动合同": "超过1个月未签合同，用人单位应支付双倍工资（第82条）",
        }
    },
    "合同纠纷": {
        "相关法律": ["《民法典》合同编", "《合同法》（已废止，参考用）"],
        "要点": [
            "合同成立需要约+承诺",
            "违约金过高可请求法院调整（第585条）",
            "不可抗力可免责（第180条）",
            "合同撤销权1年除斥期间（第152条）",
        ],
        "常见问题": {
            "对方违约怎么办": "可要求继续履行、采取补救措施或赔偿损失",
            "合同无效的情形": "无民事行为能力、虚假意思表示、违反法律强制性规定等（第144-157条）",
            "定金和订金区别": "定金有担保效力，违约方丧失定金或双倍返还；订金无此效力",
        }
    },
    "个人信息保护": {
        "相关法律": ["《个人信息保护法》", "《数据安全法》", "《网络安全法》"],
        "要点": [
            "处理个人信息需取得同意（第13条）",
            "敏感个人信息需单独同意（第29条）",
            "跨境传输需安全评估（第38-40条）",
            "个人信息主体有查阅、复制、删除权（第44-47条）",
        ],
        "常见问题": {
            "App收集信息合规吗": "需遵循最小必要原则，明示收集目的和范围",
            "个人信息泄露怎么办": "可向网信部门投诉，造成损害的可起诉要求赔偿",
            "企业数据出境": "达到规定数量的需通过安全评估、标准合同或认证",
        }
    },
    "知识产权": {
        "相关法律": ["《专利法》", "《商标法》", "《著作权法》", "《反不正当竞争法》"],
        "要点": [
            "发明专利保护期20年，实用新型10年，外观设计15年",
            "商标注册有效期10年，可续展",
            "著作权自作品完成之日起自动产生",
            "商业秘密需采取保密措施",
        ],
        "常见问题": {
            "被侵权怎么维权": "可向市场监管部门投诉、起诉或报警（严重情形）",
            "职务发明": "执行本单位任务或主要利用单位物质技术条件的发明为职务发明",
            "商标被抢注": "可在初审公告期内异议，或注册后5年内申请无效宣告",
        }
    },
}


def search_knowledge(question: str) -> list[dict]:
    """Search legal knowledge base for relevant entries."""
    results = []
    q_lower = question.lower()

    for category, data in LEGAL_KNOWLEDGE.items():
        relevance = 0

        # Check category match
        if category in question:
            relevance += 3

        # Check key points
        for point in data.get("要点", []):
            keywords = point[:4]  # Use first 4 chars as keyword
            if keywords in question:
                relevance += 2

        # Check FAQ
        for faq_q, faq_a in data.get("常见问题", {}).items():
            # Simple keyword overlap
            overlap = len(set(faq_q) & set(question))
            if overlap >= 3:
                relevance += overlap

        if relevance > 0:
            results.append({
                "category": category,
                "relevance": relevance,
                "data": data,
            })

    results.sort(key=lambda x: x["relevance"], reverse=True)
    return results


def generate_local_response(question: str) -> Optional[str]:
    """Generate response from local knowledge base."""
    results = search_knowledge(question)

    if not results:
        return None

    top = results[0]
    category = top["category"]
    data = top["data"]

    lines = [f"根据{category}相关法律知识：\n"]

    # Add relevant key points
    lines.append("📋 相关要点：")
    for point in data.get("要点", [])[:3]:
        lines.append(f"  • {point}")

    # Add relevant FAQ
    for faq_q, faq_a in data.get("常见问题", {}).items():
        overlap = len(set(faq_q) & set(question))
        if overlap >= 3:
            lines.append(f"\n💡 参考回答：")
            lines.append(f"  {faq_a}")

    # Add laws reference
    laws = data.get("相关法律", [])
    if laws:
        lines.append(f"\n📚 相关法律：{', '.join(laws)}")

    lines.append("\n⚠️ 以上为AI初步分析，仅供参考，不构成法律意见。重大事项请咨询专业律师。")

    return "\n".join(lines)


async def generate_llm_response(question: str, api_key: str) -> Optional[str]:
    """Generate response using LLM with legal context."""
    results = search_knowledge(question)
    context = ""

    if results:
        top = results[0]
        context = json.dumps(top["data"], ensure_ascii=False, indent=2)

    system_prompt = f"""你是一位专业的中国法律顾问，擅长用通俗易懂的语言解答法律问题。
请基于以下知识库信息回答用户问题。如果知识库中没有相关信息，明确告知。
请在回答末尾提醒用户"以上仅供参考，不构成法律意见"。

知识库信息：
{context}"""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": question},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1024,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[WARN] LLM调用失败: {e}")
        return None


async def answer_question(question: str, api_key: str = "") -> str:
    """Main entry point for legal Q&A."""
    # Try LLM first if API key available
    if api_key:
        llm_response = await generate_llm_response(question, api_key)
        if llm_response:
            return llm_response

    # Fallback to local knowledge base
    local_response = generate_local_response(question)
    if local_response:
        return local_response

    return (
        "抱歉，我暂时无法回答这个问题。建议您：\n"
        "1. 咨询专业律师获取准确意见\n"
        "2. 拨打12348法律援助热线\n"
        "3. 访问中国法律服务网 (www.12348.gov.cn)\n\n"
        "⚠️ 以上仅供参考，不构成法律意见。"
    )


def main():
    if len(sys.argv) < 2:
        print("用法: python legal_qa.py '你的法律问题' [--api-key KEY]")
        sys.exit(1)

    question = sys.argv[1]
    api_key = os.getenv("DEEPSEEK_API_KEY", "")

    if "--api-key" in sys.argv:
        idx = sys.argv.index("--api-key")
        if idx + 1 < len(sys.argv):
            api_key = sys.argv[idx + 1]

    import asyncio
    response = asyncio.run(answer_question(question, api_key))
    print(response)


if __name__ == "__main__":
    main()
