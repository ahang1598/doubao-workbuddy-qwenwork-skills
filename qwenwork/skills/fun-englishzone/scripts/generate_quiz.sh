#!/bin/bash

# 英语测验生成脚本
# 用法: bash generate_quiz.sh [主题] [题目数] [输出目录]

TOPIC="${1:-mixed}"
COUNT="${2:-10}"
OUTPUT_DIR="${3:-../examples}"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }

mkdir -p "$OUTPUT_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="quiz_${TOPIC}_${COUNT}q_${TIMESTAMP}.html"
OUTPUT_PATH="$OUTPUT_DIR/$FILENAME"

print_info "生成英语测验: $TOPIC, $COUNT 题"

cat << 'HTMLEOF' > "$OUTPUT_PATH"
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>英语综合测验</title>
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
        .progress-bar {
            width: 100%;
            height: 10px;
            background: rgba(255,255,255,0.3);
            border-radius: 5px;
            margin-top: 20px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: white;
            transition: width 0.3s;
        }
        .main-content { padding: 30px; }
        .quiz-intro, .quiz-result { text-align: center; padding: 40px; }
        .quiz-intro h2, .quiz-result h2 { font-size: 2em; margin-bottom: 20px; }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 30px;
            font-size: 1.1em;
            cursor: pointer;
            transition: all 0.3s;
            margin: 10px;
        }
        .btn:hover { transform: translateY(-3px); box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4); }
        .question-card {
            background: #f8f9fa;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            border-left: 5px solid #667eea;
        }
        .question-number {
            display: inline-block;
            background: #667eea;
            color: white;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            text-align: center;
            line-height: 30px;
            margin-right: 10px;
        }
        .question-text { font-size: 1.2em; margin-bottom: 15px; color: #333; }
        .options { display: flex; flex-direction: column; gap: 10px; }
        .option {
            padding: 12px 20px;
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .option:hover { border-color: #667eea; }
        .option.selected { border-color: #667eea; background: #e8eaf6; }
        .option.correct { border-color: #4caf50; background: #c8e6c9; }
        .option.wrong { border-color: #f44336; background: #ffcdd2; }
        .result-circle {
            width: 200px;
            height: 200px;
            border-radius: 50%;
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            margin: 30px auto;
            color: white;
        }
        .result-score { font-size: 4em; font-weight: bold; }
        .result-label { font-size: 1.2em; }
        .result-stats { display: flex; justify-content: center; gap: 40px; margin: 20px 0; }
        .result-stat { text-align: center; }
        .result-stat-value { font-size: 2.5em; font-weight: bold; color: #667eea; }
        .result-stat-label { color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📋 英语综合测验</h1>
            <p>测试你的英语水平</p>
            <div class="progress-bar">
                <div class="progress-fill" id="progressBar" style="width: 0%"></div>
            </div>
        </div>
        
        <div class="main-content">
            <div id="quizContent">
                <div class="quiz-intro">
                    <h2>准备好了吗？</h2>
                    <p>本测验包含词汇、语法、阅读理解等多种题型</p>
                    <button class="btn" onclick="startQuiz()">开始测验</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        const questions = [
            { type: 'vocab', q: '"abandon" 的意思是？', opts: ['放弃', '接受', '增加', '减少'], ans: 0 },
            { type: 'grammar', q: 'She ___ to the gym every Monday.', opts: ['go', 'goes', 'going', 'went'], ans: 1 },
            { type: 'vocab', q: '"benefit" 的意思是？', opts: ['利益', '伤害', '成本', '风险'], ans: 0 },
            { type: 'grammar', q: 'I have ___ this movie before.', opts: ['see', 'saw', 'seen', 'seeing'], ans: 2 },
            { type: 'vocab', q: '"challenge" 的意思是？', opts: ['挑战', '机会', '困难', '成功'], ans: 0 },
            { type: 'grammar', q: 'If I ___ you, I would study harder.', opts: ['am', 'was', 'were', 'be'], ans: 2 },
            { type: 'vocab', q: '"determine" 的意思是？', opts: ['决定', '犹豫', '放弃', '开始'], ans: 0 },
            { type: 'grammar', q: 'The book ___ by millions of people.', opts: ['reads', 'read', 'is read', 'is reading'], ans: 2 },
            { type: 'vocab', q: '"establish" 的意思是？', opts: ['建立', '破坏', '改变', '保持'], ans: 0 },
            { type: 'grammar', q: 'He asked me where ___.', opts: ['I live', 'do I live', 'I lived', 'did I live'], ans: 2 }
        ];
        
        let current = 0;
        let score = 0;
        let answers = [];
        
        function startQuiz() {
            current = 0;
            score = 0;
            answers = [];
            showQuestion();
        }
        
        function showQuestion() {
            const q = questions[current];
            const progress = ((current) / questions.length) * 100;
            document.getElementById('progressBar').style.width = progress + '%';
            
            document.getElementById('quizContent').innerHTML = `
                <div class="question-card">
                    <div class="question-text">
                        <span class="question-number">${current + 1}</span>
                        ${q.q}
                    </div>
                    <div class="options">
                        ${q.opts.map((opt, i) => `
                            <div class="option" onclick="selectAnswer(${i})" id="opt${i}">
                                ${String.fromCharCode(65 + i)}. ${opt}
                            </div>
                        `).join('')}
                    </div>
                </div>
                <div style="text-align: center;">
                    <button class="btn" onclick="submitAnswer()">提交</button>
                </div>
            `;
        }
        
        let selected = -1;
        function selectAnswer(index) {
            selected = index;
            document.querySelectorAll('.option').forEach((opt, i) => {
                opt.classList.remove('selected');
                if (i === index) opt.classList.add('selected');
            });
        }
        
        function submitAnswer() {
            if (selected === -1) return;
            
            const q = questions[current];
            const isCorrect = selected === q.ans;
            if (isCorrect) score++;
            answers[current] = selected;
            
            document.querySelectorAll('.option').forEach((opt, i) => {
                opt.style.pointerEvents = 'none';
                if (i === q.ans) opt.classList.add('correct');
                else if (i === selected && !isCorrect) opt.classList.add('wrong');
            });
            
            setTimeout(() => {
                current++;
                selected = -1;
                if (current < questions.length) {
                    showQuestion();
                } else {
                    showResult();
                }
            }, 1000);
        }
        
        function showResult() {
            const percent = Math.round((score / questions.length) * 100);
            document.getElementById('progressBar').style.width = '100%';
            
            document.getElementById('quizContent').innerHTML = `
                <div class="quiz-result">
                    <h2>🎉 测验完成！</h2>
                    <div class="result-circle">
                        <div class="result-score">${percent}%</div>
                        <div class="result-label">正确率</div>
                    </div>
                    <div class="result-stats">
                        <div class="result-stat">
                            <div class="result-stat-value">${score}</div>
                            <div class="result-stat-label">正确</div>
                        </div>
                        <div class="result-stat">
                            <div class="result-stat-value">${questions.length - score}</div>
                            <div class="result-stat-label">错误</div>
                        </div>
                    </div>
                    <button class="btn" onclick="startQuiz()">再测一次</button>
                </div>
            `;
        }
    </script>
</body>
</html>
HTMLEOF

print_success "测验生成成功! 文件: $OUTPUT_PATH"
