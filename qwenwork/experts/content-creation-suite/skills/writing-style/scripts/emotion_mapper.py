import sys
import json

def analyze_emotion_arc(text):
    """分析情感曲线和共情触发词"""
    # 简易共情词库
    empathy_words = ["说实话", "心碎", "避坑", "终于", "真的", "太", "救命", "绝了", "破防"]
    found_empathy = [word for word in empathy_words if word in text]
    
    # 简易情感极性判断（基于关键词）
    positive_words = ["好", "棒", "强", "赞", "爱", "喜欢", "成功"]
    negative_words = ["坏", "差", "弱", "烦", "难", "失望", "失败"]
    
    pos_count = sum(text.count(w) for w in positive_words)
    neg_count = sum(text.count(w) for w in negative_words)
    
    polarity = "positive" if pos_count > neg_count else ("negative" if neg_count > pos_count else "neutral")
    
    return {
        "emotional_polarity": polarity,
        "empathy_triggers": found_empathy,
        "sentiment_score": round((pos_count - neg_count) / max(len(text), 1), 4)
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing input text"}))
        sys.exit(1)
        
    input_text = sys.argv[1]
    result = analyze_emotion_arc(input_text)
    print(json.dumps(result, ensure_ascii=False))
