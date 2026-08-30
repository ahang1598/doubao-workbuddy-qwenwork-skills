import sys
import json
import re

def calculate_platform_fit(text):
    """计算各平台适配得分"""
    # 小红书特征：Emoji, 短句, 口语
    emoji_count = len(re.findall(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', text))
    short_sentences = len([s for s in text.split('。') if len(s) < 15])
    
    # B站/知乎特征：长难句, 专业术语（此处简化为标点密度和字数）
    long_sentences = len([s for s in text.split('。') if len(s) > 50])
    
    xhs_score = min(100, (emoji_count * 5) + (short_sentences * 2))
    zhihu_score = min(100, (long_sentences * 5) + (len(text) / 50))
    
    return {
        "xhs_fit_score": round(xhs_score, 2),
        "zhihu_bilibili_fit_score": round(zhihu_score, 2),
        "emoji_density": round(emoji_count / max(len(text), 1), 4)
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing input text"}))
        sys.exit(1)
        
    input_text = sys.argv[1]
    result = calculate_platform_fit(input_text)
    print(json.dumps(result, ensure_ascii=False))
