import os
import sys
import json
import math
from collections import Counter

def calculate_entropy(text):
    """计算文本的信息熵，衡量信息密度"""
    if not text:
        return 0
    freq = Counter(text)
    length = len(text)
    entropy = -sum((count / length) * math.log2(count / length) for count in freq.values())
    return round(entropy, 4)

def analyze_logic_density(text):
    """分析逻辑连接词和抽象/具体比率"""
    # 简易逻辑词库
    logic_words = ["因为", "所以", "但是", "然而", "本质上", "首先", "其次", "最后", "综上所述", "换句话说"]
    counts = {word: text.count(word) for word in logic_words}
    
    # 统计总字数和逻辑词总数
    total_chars = len(text)
    logic_total = sum(counts.values())
    
    # 简单估算：动词多则具体，名词/形容词多则抽象（此处做简化处理）
    # 实际项目中可引入 jieba 分词进行词性标注
    
    return {
        "information_entropy": calculate_entropy(text),
        "logic_connectors": counts,
        "logic_density_ratio": round(logic_total / total_chars, 4) if total_chars > 0 else 0
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing input text"}))
        sys.exit(1)
        
    input_text = sys.argv[1]
    result = analyze_logic_density(input_text)
    print(json.dumps(result, ensure_ascii=False))
