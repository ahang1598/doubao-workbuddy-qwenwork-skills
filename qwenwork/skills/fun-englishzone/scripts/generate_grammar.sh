#!/bin/bash

# 语法练习生成脚本
# 用法: bash generate_grammar.sh [主题] [难度] [输出目录]

TOPIC="${1:-tenses}"
LEVEL="${2:-beginner}"
OUTPUT_DIR="${3:-../examples}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

mkdir -p "$OUTPUT_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="grammar_${TOPIC}_${LEVEL}_${TIMESTAMP}.html"
OUTPUT_PATH="$OUTPUT_DIR/$FILENAME"

print_info "开始生成语法练习..."
print_info "主题: $TOPIC, 难度: $LEVEL"

cat << 'HTMLEOF' > "$OUTPUT_PATH"
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>语法探索器</title>
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
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .stats { display: flex; justify-content: center; gap: 30px; margin-top: 20px; flex-wrap: wrap; }
        .stat { background: rgba(255,255,255,0.2); padding: 10px 20px; border-radius: 10px; }
        .main-content { padding: 30px; }
        .question-card {
            background: #f8f9fa;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            border-left: 5px solid #667eea;
        }
        .question-text { font-size: 1.3em; margin-bottom: 20px; color: #333; }
        .options { display: flex; flex-direction: column; gap: 10px; }
        .option {
            padding: 15px 20px;
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .option:hover { border-color: #667eea; background: #f5f5f5; }
        .option.selected { border-color: #667eea; background: #e8eaf6; }
        .option.correct { border-color: #4caf50; background: #c8e6c9; }
        .option.wrong { border-color: #f44336; background: #ffcdd2; }
        .feedback {
            padding: 15px;
            border-radius: 10px;
            margin-top: 15px;
            display: none;
        }
        .feedback.show { display: block; }
        .feedback.correct { background: #e8f5e9; color: #2e7d32; }
        .feedback.wrong { background: #ffebee; color: #c62828; }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 30px;
            font-size: 1em;
            cursor: pointer;
            transition: all 0.3s;
            margin: 5px;
        }
        .btn:hover { transform: translateY(-3px); box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4); }
        .btn-success { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
        .controls { text-align: center; margin-top: 20px; }
        .progress-dots { display: flex; justify-content: center; gap: 10px; margin: 20px 0; }
        .dot { width: 15px; height: 15px; border-radius: 50%; background: #e0e0e0; transition: all 0.3s; }
        .dot.current { background: #667eea; transform: scale(1.2); }
        .dot.correct { background: #4caf50; }
        .dot.wrong { background: #f44336; }
        .explanation {
            background: #e3f2fd;
            padding: 15px;
            border-radius: 10px;
            margin-top: 15px;
            border-left: 5px solid #2196f3;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📝 语法探索器</h1>
            <p>掌握英语语法，提升语言能力</p>
            <div class="stats">
                <div class="stat">✅ 正确: <span id="correct">0</span></div>
                <div class="stat">❌ 错误: <span id="wrong">0</span></div>
                <div class="stat">📊 准确率: <span id="accuracy">0%</span></div>
            </div>
        </div>
        
        <div class="main-content">
            <div class="progress-dots" id="progressDots"></div>
            <div id="questionArea"></div>
            <div class="controls">
                <button class="btn" onclick="checkAnswer()">提交答案</button>
                <button class="btn btn-success" onclick="nextQuestion()">下一题</button>
            </div>
        </div>
    </div>

    <script>
        const questions = [
            {
                text: "She ___ to school every day.",
                options: ["go", "goes", "going", "went"],
                correct: 1,
                explanation: "第三人称单数，一般现在时动词加-s/es。"
            },
            {
                text: "I ___ my homework yesterday.",
                options: ["do", "does", "did", "done"],
                correct: 2,
                explanation: "yesterday表示过去，用一般过去时did。"
            },
            {
                text: "They ___ playing football now.",
                options: ["is", "are", "was", "were"],
                correct: 1,
                explanation: "They是复数，now表示现在进行时，用are。"
            },
            {
                text: "He ___ to Beijing twice.",
                options: ["has been", "have been", "was", "is"],
                correct: 0,
                explanation: "twice表示次数，用现在完成时，He是单数用has。"
            },
            {
                text: "If it ___ tomorrow, we will stay home.",
                options: ["rain", "rains", "rained", "will rain"],
                correct: 1,
                explanation: "条件状语从句，主将从现原则，用一般现在时。"
            }
        ];
        
        let currentQ = 0;
        let correct = 0;
        let wrong = 0;
        let selected = -1;
        let answered = [];
        
        function init() {
            const dots = document.getElementById('progressDots');
            dots.innerHTML = questions.map((_, i) => 
                `<div class="dot ${i === 0 ? 'current' : ''}" id="dot${i}"></div>`
            ).join('');
            showQuestion();
        }
        
        function showQuestion() {
            const q = questions[currentQ];
            document.getElementById('questionArea').innerHTML = `
                <div class="question-card">
                    <div class="question-text">${q.text}</div>
                    <div class="options">
                        ${q.options.map((opt, i) => `
                            <div class="option" onclick="selectOption(${i})" id="opt${i}">
                                ${String.fromCharCode(65 + i)}. ${opt}
                            </div>
                        `).join('')}
                    </div>
                    <div class="feedback" id="feedback"></div>
                </div>
            `;
            selected = -1;
        }
        
        function selectOption(index) {
            selected = index;
            document.querySelectorAll('.option').forEach((opt, i) => {
                opt.classList.remove('selected');
                if (i === index) opt.classList.add('selected');
            });
        }
        
        function checkAnswer() {
            if (selected === -1) return;
            const q = questions[currentQ];
            const isCorrect = selected === q.correct;
            
            document.querySelectorAll('.option').forEach((opt, i) => {
                if (i === q.correct) opt.classList.add('correct');
                else if (i === selected) opt.classList.add('wrong');
            });
            
            const feedback = document.getElementById('feedback');
            feedback.className = 'feedback show ' + (isCorrect ? 'correct' : 'wrong');
            feedback.innerHTML = isCorrect ? 
                '✅ 正确！' : 
                `❌ 错误！正确答案是 ${String.fromCharCode(65 + q.correct)}。<br><br>${q.explanation}`;
            
            if (isCorrect) correct++; else wrong++;
            answered[currentQ] = isCorrect;
            updateStats();
        }
        
        function nextQuestion() {
            currentQ = (currentQ + 1) % questions.length;
            document.querySelectorAll('.dot').forEach((dot, i) => {
                dot.classList.remove('current');
                if (i === currentQ) dot.classList.add('current');
                if (answered[i] === true) dot.classList.add('correct');
                if (answered[i] === false) dot.classList.add('wrong');
            });
            showQuestion();
        }
        
        function updateStats() {
            document.getElementById('correct').textContent = correct;
            document.getElementById('wrong').textContent = wrong;
            const total = correct + wrong;
            document.getElementById('accuracy').textContent = 
                total > 0 ? Math.round((correct / total) * 100) + '%' : '0%';
        }
        
        init();
    </script>
</body>
</html>
HTMLEOF

print_success "语法练习生成成功! 文件: $OUTPUT_PATH"
