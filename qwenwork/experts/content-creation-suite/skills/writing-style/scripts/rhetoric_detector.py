import sys
import json
import re

def detect_rhetoric(text):
    """识别修辞、记忆锚点和金句潜力"""
    # 识别排比（简单正则：连续三个以上相似结构的短句）
    sentences = [s.strip() for s in text.split('。') if len(s) > 5]
    
    # 识别“金句”：短小精悍且包含强语气词
    potential_golden_quotes = [s + '。' for s in sentences if 10 < len(s) < 30 and any(w in s for w in ["是", "才", "就", "不"])]
    
    # 识别重复强化模式（关键词重复出现）
    words = re.findall(r'[\u4e00-\u9fa5]{2,}', text)
    from collections import Counter
    common_words = [word for word, count in Counter(words).most_common(5) if count > 2]
    
    return {
        "potential_golden_quotes": potential_golden_quotes[:3],
        "repeated_keywords": common_words,
        "sentence_count": len(sentences)
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing input text"}))
        sys.exit(1)
        
    input_text = sys.argv[1]
    result = detect_rhetoric(input_text)
    print(json.dumps(result, ensure_ascii=False))
