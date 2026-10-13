#!/bin/bash

# 词汇学习工具生成脚本
# 用法: bash generate_vocabulary.sh [主题] [难度] [输出目录]

# 默认参数
TOPIC="${1:-daily}"
LEVEL="${2:-beginner}"
OUTPUT_DIR="${3:-../examples}"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 打印函数
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 帮助信息
show_help() {
    cat << EOF
词汇学习工具生成脚本

用法:
    bash generate_vocabulary.sh [主题] [难度] [输出目录]

参数:
    主题        - 词汇主题 (默认: daily)
                可选: daily, food, travel, business, academic
    难度        - 难度级别 (默认: beginner)
                可选: beginner, intermediate, advanced
    输出目录    - HTML文件输出路径 (默认: ../examples)

示例:
    bash generate_vocabulary.sh food beginner ./output
    bash generate_vocabulary.sh travel intermediate
    bash generate_vocabulary.sh business advanced ./my-vocab

EOF
}

# 检查参数
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    show_help
    exit 0
fi

print_info "开始生成词汇学习工具..."
print_info "主题: $TOPIC"
print_info "难度: $LEVEL"

# 确保输出目录存在
mkdir -p "$OUTPUT_DIR"

# 生成文件名
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="vocabulary_${TOPIC}_${LEVEL}_${TIMESTAMP}.html"
OUTPUT_PATH="$OUTPUT_DIR/$FILENAME"

print_info "正在生成文件: $FILENAME"

# 生成词汇学习HTML
cat << 'HTMLEOF' > "$OUTPUT_PATH"
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>词汇学习工具</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .score-board {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        .score-item {
            background: rgba(255,255,255,0.2);
            padding: 10px 20px;
            border-radius: 10px;
            font-size: 1.1em;
        }
        .main-content { padding: 30px; }
        .card-container {
            perspective: 1000px;
            margin-bottom: 30px;
        }
        .flashcard {
            width: 100%;
            height: 300px;
            position: relative;
            transform-style: preserve-3d;
            transition: transform 0.6s;
            cursor: pointer;
        }
        .flashcard.flipped { transform: rotateY(180deg); }
        .card-front, .card-back {
            position: absolute;
            width: 100%;
            height: 100%;
            backface-visibility: hidden;
            border-radius: 20px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .card-front {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
        }
        .card-back {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            transform: rotateY(180deg);
        }
        .word { font-size: 3em; font-weight: bold; margin-bottom: 10px; }
        .phonetic { font-size: 1.3em; opacity: 0.9; }
        .meaning { font-size: 2em; margin-bottom: 15px; }
        .example { font-size: 1.1em; opacity: 0.9; text-align: center; font-style: italic; }
        .controls {
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 30px;
            font-size: 1em;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }
        .btn-success { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
        .btn-warning { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        .progress-bar {
            width: 100%;
            height: 10px;
            background: #e0e0e0;
            border-radius: 5px;
            margin-bottom: 20px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #11998e, #38ef7d);
            transition: width 0.3s;
        }
        .word-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 10px;
            margin-top: 20px;
        }
        .word-item {
            padding: 10px;
            background: #f5f5f5;
            border-radius: 10px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }
        .word-item:hover { background: #e0e0e0; }
        .word-item.learned { background: #c8e6c9; }
        .achievements {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            justify-content: center;
            margin-top: 20px;
        }
        .badge {
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            opacity: 0.3;
            transition: all 0.3s;
        }
        .badge.unlocked {
            opacity: 1;
            background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        @media (max-width: 600px) {
            .header h1 { font-size: 1.8em; }
            .word { font-size: 2em; }
            .meaning { font-size: 1.5em; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 词汇学习工具</h1>
            <p>点击卡片翻转查看释义</p>
            <div class="score-board">
                <div class="score-item">⭐ 已学: <span id="learned">0</span></div>
                <div class="score-item">🔥 连胜: <span id="streak">0</span></div>
                <div class="score-item">📊 进度: <span id="progress">0%</span></div>
            </div>
        </div>
        
        <div class="main-content">
            <div class="progress-bar">
                <div class="progress-fill" id="progressBar" style="width: 0%"></div>
            </div>
            
            <div class="card-container">
                <div class="flashcard" id="flashcard" onclick="flipCard()">
                    <div class="card-front">
                        <div class="word" id="word">hello</div>
                        <div class="phonetic" id="phonetic">/həˈləʊ/</div>
                    </div>
                    <div class="card-back">
                        <div class="meaning" id="meaning">你好</div>
                        <div class="example" id="example">Hello, how are you?</div>
                    </div>
                </div>
            </div>
            
            <div class="controls">
                <button class="btn btn-warning" onclick="markUnknown()">还不熟悉</button>
                <button class="btn btn-success" onclick="markKnown()">已掌握</button>
                <button class="btn" onclick="nextWord()">下一个</button>
            </div>
            
            <div class="achievements">
                <span class="badge" id="badge1">📖 学习10词</span>
                <span class="badge" id="badge2">🔥 连胜5词</span>
                <span class="badge" id="badge3">🎯 掌握50词</span>
                <span class="badge" id="badge4">🏆 词汇达人</span>
            </div>
        </div>
    </div>

    <script>
        // 词汇数据
        const vocabulary = [
            { word: "hello", phonetic: "/həˈləʊ/", meaning: "你好", example: "Hello, how are you?" },
            { word: "goodbye", phonetic: "/ɡʊdˈbaɪ/", meaning: "再见", example: "Goodbye, see you tomorrow!" },
            { word: "thank", phonetic: "/θæŋk/", meaning: "感谢", example: "Thank you for your help." },
            { word: "please", phonetic: "/pliːz/", meaning: "请", example: "Please sit down." },
            { word: "sorry", phonetic: "/ˈsɒri/", meaning: "抱歉", example: "I'm sorry for being late." },
            { word: "friend", phonetic: "/frend/", meaning: "朋友", example: "She is my best friend." },
            { word: "family", phonetic: "/ˈfæməli/", meaning: "家庭", example: "I love my family." },
            { word: "school", phonetic: "/skuːl/", meaning: "学校", example: "I go to school every day." },
            { word: "book", phonetic: "/bʊk/", meaning: "书", example: "This is an interesting book." },
            { word: "water", phonetic: "/ˈwɔːtə/", meaning: "水", example: "I drink water every day." }
        ];
        
        let currentIndex = 0;
        let learned = 0;
        let streak = 0;
        let known = new Set();
        
        function updateCard() {
            const card = vocabulary[currentIndex];
            document.getElementById('word').textContent = card.word;
            document.getElementById('phonetic').textContent = card.phonetic;
            document.getElementById('meaning').textContent = card.meaning;
            document.getElementById('example').textContent = card.example;
            document.getElementById('flashcard').classList.remove('flipped');
        }
        
        function flipCard() {
            document.getElementById('flashcard').classList.toggle('flipped');
        }
        
        function markKnown() {
            if (!known.has(currentIndex)) {
                known.add(currentIndex);
                learned++;
                streak++;
                updateProgress();
                checkBadges();
            }
            nextWord();
        }
        
        function markUnknown() {
            streak = 0;
            document.getElementById('streak').textContent = streak;
            nextWord();
        }
        
        function nextWord() {
            currentIndex = (currentIndex + 1) % vocabulary.length;
            updateCard();
        }
        
        function updateProgress() {
            const percent = Math.round((learned / vocabulary.length) * 100);
            document.getElementById('learned').textContent = learned;
            document.getElementById('streak').textContent = streak;
            document.getElementById('progress').textContent = percent + '%';
            document.getElementById('progressBar').style.width = percent + '%';
        }
        
        function checkBadges() {
            if (learned >= 10) document.getElementById('badge1').classList.add('unlocked');
            if (streak >= 5) document.getElementById('badge2').classList.add('unlocked');
            if (learned >= 50) document.getElementById('badge3').classList.add('unlocked');
            if (learned >= 100) document.getElementById('badge4').classList.add('unlocked');
        }
        
        updateCard();
    </script>
</body>
</html>
HTMLEOF

# 检查文件
if [ -f "$OUTPUT_PATH" ]; then
    print_success "词汇学习工具生成成功!"
    print_info "文件路径: $OUTPUT_PATH"
    print_info "文件大小: $(du -h "$OUTPUT_PATH" | cut -f1)"
else
    print_error "文件生成失败"
    exit 1
fi

print_success "完成! 📚"
