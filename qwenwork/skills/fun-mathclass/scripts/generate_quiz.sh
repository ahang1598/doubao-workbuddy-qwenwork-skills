#!/bin/bash

# 数学测验生成脚本
# 用法: bash generate_quiz.sh [主题] [题目数量] [输出目录]

# 默认参数
TOPIC="${1:-mixed}"
QUESTION_COUNT="${2:-10}"
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
数学测验生成脚本

用法:
    bash generate_quiz.sh [主题] [题目数] [输出目录]

参数:
    主题        - 数学主题 (默认: mixed)
                可选: arithmetic, algebra, geometry, calculus, statistics, mixed
    题目数      - 测验题目数量 (默认: 10)
    输出目录    - HTML文件输出路径 (默认: ../examples)

示例:
    bash generate_quiz.sh algebra 15 ./quizzes
    bash generate_quiz.sh geometry 20
    bash generate_quiz.sh mixed 10 ./my-quizzes

EOF
}

# 检查参数
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    show_help
    exit 0
fi

print_info "开始生成数学测验..."
print_info "主题: $TOPIC"
print_info "题目数: $QUESTION_COUNT"

# 确保输出目录存在
mkdir -p "$OUTPUT_DIR"

# 生成文件名
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="${TOPIC}_quiz_${QUESTION_COUNT}q_${TIMESTAMP}.html"
OUTPUT_PATH="$OUTPUT_DIR/$FILENAME"

print_info "正在生成文件: $FILENAME"

# 生成混合测验
generate_mixed_quiz() {
    cat << 'EOF'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>综合数学测验</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .quiz-container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .quiz-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .quiz-header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .progress-info {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 20px;
            font-size: 1.1em;
        }
        
        .quiz-body {
            padding: 40px;
        }
        
        .question-card {
            background: #f8f9fa;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            border-left: 5px solid #667eea;
            transition: all 0.3s;
        }
        
        .question-card:hover {
            transform: translateX(5px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .question-card.correct {
            border-left-color: #4caf50;
            background: #e8f5e9;
        }
        
        .question-card.wrong {
            border-left-color: #f44336;
            background: #ffebee;
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
            font-weight: bold;
            margin-right: 10px;
        }
        
        .question-text {
            font-size: 1.2em;
            margin-bottom: 15px;
            color: #333;
        }
        
        .options {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        
        .option {
            padding: 12px 20px;
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
        }
        
        .option:hover {
            border-color: #667eea;
            background: #f5f5f5;
        }
        
        .option.selected {
            border-color: #667eea;
            background: #e8eaf6;
        }
        
        .option.correct {
            border-color: #4caf50;
            background: #c8e6c9;
        }
        
        .option.wrong {
            border-color: #f44336;
            background: #ffcdd2;
        }
        
        .option-letter {
            display: inline-block;
            width: 28px;
            height: 28px;
            background: #e0e0e0;
            border-radius: 50%;
            text-align: center;
            line-height: 28px;
            font-weight: bold;
            margin-right: 12px;
            font-size: 0.9em;
        }
        
        .option.selected .option-letter,
        .option.correct .option-letter,
        .option.wrong .option-letter {
            background: white;
        }
        
        .explanation {
            margin-top: 15px;
            padding: 15px;
            background: #e3f2fd;
            border-radius: 10px;
            display: none;
        }
        
        .explanation.show {
            display: block;
        }
        
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
        
        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }
        
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        .btn-secondary {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }
        
        .controls {
            text-align: center;
            margin-top: 30px;
        }
        
        .result-panel {
            text-align: center;
            padding: 40px;
            display: none;
        }
        
        .result-panel.show {
            display: block;
        }
        
        .score-circle {
            width: 200px;
            height: 200px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            margin: 0 auto 30px;
            color: white;
        }
        
        .score-number {
            font-size: 4em;
            font-weight: bold;
        }
        
        .score-label {
            font-size: 1.2em;
        }
        
        .result-stats {
            display: flex;
            justify-content: center;
            gap: 40px;
            margin: 30px 0;
        }
        
        .result-stat {
            text-align: center;
        }
        
        .result-stat-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }
        
        .result-stat-label {
            color: #666;
            margin-top: 5px;
        }
        
        .topic-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            justify-content: center;
            margin: 20px 0;
        }
        
        .topic-tag {
            padding: 5px 15px;
            background: #e8eaf6;
            color: #667eea;
            border-radius: 20px;
            font-size: 0.9em;
        }
        
        @media (max-width: 600px) {
            .quiz-header h1 { font-size: 1.8em; }
            .question-text { font-size: 1em; }
            .result-stats { flex-direction: column; gap: 20px; }
        }
    </style>
</head>
<body>
    <div class="quiz-container">
        <div class="quiz-header">
            <h1>📝 综合数学测验</h1>
            <p>测试你的数学知识!</p>
            <div class="progress-info">
                <span>题目: <strong id="currentQ">1</strong> / <strong id="totalQ">10</strong></span>
                <span>得分: <strong id="score">0</strong></span>
            </div>
        </div>
        
        <div class="quiz-body" id="quizBody">
            <!-- 题目将通过JS动态生成 -->
        </div>
        
        <div class="controls" id="controls">
            <button class="btn" onclick="submitQuiz()">提交答案</button>
            <button class="btn btn-secondary" onclick="showHint()">提示</button>
        </div>
        
        <div class="result-panel" id="resultPanel">
            <div class="score-circle">
                <div class="score-number" id="finalScore">0</div>
                <div class="score-label">分</div>
            </div>
            
            <div class="result-stats">
                <div class="result-stat">
                    <div class="result-stat-value" id="correctCount">0</div>
                    <div class="result-stat-label">正确</div>
                </div>
                <div class="result-stat">
                    <div class="result-stat-value" id="wrongCount">0</div>
                    <div class="result-stat-label">错误</div>
                </div>
                <div class="result-stat">
                    <div class="result-stat-value" id="accuracy">0%</div>
                    <div class="result-stat-label">准确率</div>
                </div>
            </div>
            
            <div class="topic-tags" id="topicTags"></div>
            
            <button class="btn" onclick="restartQuiz()">重新测验</button>
        </div>
    </div>

    <script>
        // 题库
        const questionBank = [
            {
                topic: 'arithmetic',
                topicName: '算术',
                question: '15 + 27 = ?',
                options: ['40', '42', '44', '52'],
                correct: 1,
                explanation: '15 + 27 = 42。个位数相加：5 + 7 = 12，写下2，进1；十位数相加：1 + 2 + 1(进位) = 4。'
            },
            {
                topic: 'arithmetic',
                topicName: '算术',
                question: '如果 3x = 27，那么 x = ?',
                options: ['6', '7', '8', '9'],
                correct: 3,
                explanation: '3x = 27，两边同时除以3，得到 x = 9。'
            },
            {
                topic: 'geometry',
                topicName: '几何',
                question: '一个三角形的内角和是多少度?',
                options: ['90°', '180°', '270°', '360°'],
                correct: 1,
                explanation: '任何三角形的内角和都是180°。'
            },
            {
                topic: 'geometry',
                topicName: '几何',
                question: '半径为5的圆，其周长是多少?（π取3.14）',
                options: ['15.7', '31.4', '62.8', '78.5'],
                correct: 1,
                explanation: '圆的周长公式：C = 2πr = 2 × 3.14 × 5 = 31.4'
            },
            {
                topic: 'algebra',
                topicName: '代数',
                question: '化简：2(x + 3) - 4',
                options: ['2x + 2', '2x + 6', '2x + 10', '2x - 2'],
                correct: 0,
                explanation: '2(x + 3) - 4 = 2x + 6 - 4 = 2x + 2'
            },
            {
                topic: 'algebra',
                topicName: '代数',
                question: '解方程：2x - 5 = 11',
                options: ['6', '7', '8', '9'],
                correct: 2,
                explanation: '2x - 5 = 11 → 2x = 16 → x = 8'
            },
            {
                topic: 'fraction',
                topicName: '分数',
                question: '1/2 + 1/4 = ?',
                options: ['1/6', '2/6', '3/4', '2/4'],
                correct: 2,
                explanation: '1/2 = 2/4，所以 2/4 + 1/4 = 3/4'
            },
            {
                topic: 'fraction',
                topicName: '分数',
                question: '3/5 的小数形式是?',
                options: ['0.3', '0.5', '0.6', '0.8'],
                correct: 2,
                explanation: '3 ÷ 5 = 0.6'
            },
            {
                topic: 'statistics',
                topicName: '统计',
                question: '数据集 {3, 5, 7, 9, 11} 的平均数是多少?',
                options: ['6', '7', '8', '9'],
                correct: 1,
                explanation: '平均数 = (3+5+7+9+11) / 5 = 35/5 = 7'
            },
            {
                topic: 'statistics',
                topicName: '统计',
                question: '数据集 {2, 4, 4, 6, 8} 的中位数是多少?',
                options: ['4', '5', '6', '4.5'],
                correct: 0,
                explanation: '数据已排序，中间位置的数是4。'
            },
            {
                topic: 'percentage',
                topicName: '百分数',
                question: '20% 的 150 是多少?',
                options: ['20', '25', '30', '35'],
                correct: 2,
                explanation: '20% × 150 = 0.20 × 150 = 30'
            },
            {
                topic: 'percentage',
                topicName: '百分数',
                question: '如果一件商品原价200元，打8折后的价格是多少?',
                options: ['140元', '150元', '160元', '180元'],
                correct: 2,
                explanation: '8折 = 80%，200 × 0.80 = 160元'
            }
        ];
        
        // 游戏状态
        let currentQuestion = 0;
        let score = 0;
        let correct = 0;
        let wrong = 0;
        let userAnswers = [];
        let questions = [];
        
        // 初始化测验
        function initQuiz() {
            // 随机选择10道题
            questions = [...questionBank]
                .sort(() => Math.random() - 0.5)
                .slice(0, 10);
            
            document.getElementById('totalQ').textContent = questions.length;
            renderQuestions();
        }
        
        // 渲染题目
        function renderQuestions() {
            const container = document.getElementById('quizBody');
            container.innerHTML = '';
            
            questions.forEach((q, index) => {
                const card = document.createElement('div');
                card.className = 'question-card';
                card.id = `question-${index}`;
                
                let optionsHtml = '';
                q.options.forEach((opt, optIndex) => {
                    optionsHtml += `
                        <div class="option" onclick="selectOption(${index}, ${optIndex})" data-q="${index}" data-opt="${optIndex}">
                            <span class="option-letter">${String.fromCharCode(65 + optIndex)}</span>
                            <span>${opt}</span>
                        </div>
                    `;
                });
                
                card.innerHTML = `
                    <div class="question-text">
                        <span class="question-number">${index + 1}</span>
                        ${q.question}
                    </div>
                    <div class="options">${optionsHtml}</div>
                    <div class="explanation" id="explanation-${index}">
                        <strong>解析：</strong>${q.explanation}
                    </div>
                `;
                
                container.appendChild(card);
            });
        }
        
        // 选择选项
        function selectOption(qIndex, optIndex) {
            if (userAnswers[qIndex] !== undefined) return;
            
            userAnswers[qIndex] = optIndex;
            
            const card = document.getElementById(`question-${qIndex}`);
            const options = card.querySelectorAll('.option');
            
            options.forEach((opt, i) => {
                opt.classList.remove('selected');
                if (i === optIndex) {
                    opt.classList.add('selected');
                }
            });
            
            document.getElementById('currentQ').textContent = userAnswers.filter(a => a !== undefined).length;
        }
        
        // 提交测验
        function submitQuiz() {
            if (userAnswers.filter(a => a !== undefined).length < questions.length) {
                if (!confirm('还有题目未作答，确定要提交吗?')) return;
            }
            
            score = 0;
            correct = 0;
            wrong = 0;
            
            questions.forEach((q, index) => {
                const card = document.getElementById(`question-${index}`);
                const options = card.querySelectorAll('.option');
                const userAnswer = userAnswers[index];
                
                options.forEach((opt, i) => {
                    opt.style.pointerEvents = 'none';
                    if (i === q.correct) {
                        opt.classList.add('correct');
                    } else if (i === userAnswer && i !== q.correct) {
                        opt.classList.add('wrong');
                    }
                });
                
                if (userAnswer === q.correct) {
                    correct++;
                    score += 10;
                    card.classList.add('correct');
                } else {
                    wrong++;
                    card.classList.add('wrong');
                }
                
                document.getElementById(`explanation-${index}`).classList.add('show');
            });
            
            document.getElementById('score').textContent = score;
            document.getElementById('controls').style.display = 'none';
            
            setTimeout(showResults, 1000);
        }
        
        // 显示结果
        function showResults() {
            document.getElementById('quizBody').style.display = 'none';
            document.getElementById('controls').style.display = 'none';
            document.getElementById('resultPanel').classList.add('show');
            
            document.getElementById('finalScore').textContent = score;
            document.getElementById('correctCount').textContent = correct;
            document.getElementById('wrongCount').textContent = wrong;
            document.getElementById('accuracy').textContent = Math.round((correct / questions.length) * 100) + '%';
            
            // 显示涉及的主题
            const topics = [...new Set(questions.map(q => q.topicName))];
            document.getElementById('topicTags').innerHTML = topics.map(t => 
                `<span class="topic-tag">${t}</span>`
            ).join('');
        }
        
        // 显示提示
        function showHint() {
            const unanswered = questions.findIndex((q, i) => userAnswers[i] === undefined);
            if (unanswered === -1) {
                alert('所有题目已作答!');
                return;
            }
            
            const q = questions[unanswered];
            alert(`第${unanswered + 1}题提示：\n${q.explanation.substring(0, 30)}...`);
        }
        
        // 重新开始
        function restartQuiz() {
            currentQuestion = 0;
            score = 0;
            correct = 0;
            wrong = 0;
            userAnswers = [];
            
            document.getElementById('quizBody').style.display = 'block';
            document.getElementById('controls').style.display = 'block';
            document.getElementById('resultPanel').classList.remove('show');
            document.getElementById('score').textContent = '0';
            
            initQuiz();
        }
        
        // 初始化
        initQuiz();
    </script>
</body>
</html>
EOF
}

# 生成测验文件
case "$TOPIC" in
    "mixed"|"综合")
        generate_mixed_quiz > "$OUTPUT_PATH"
        ;;
    *)
        generate_mixed_quiz > "$OUTPUT_PATH"
        print_warning "未知主题 '$TOPIC'，使用默认主题 'mixed'"
        ;;
esac

# 检查文件
if [ -f "$OUTPUT_PATH" ]; then
    print_success "测验文件生成成功!"
    print_info "文件路径: $OUTPUT_PATH"
    print_info "文件大小: $(du -h "$OUTPUT_PATH" | cut -f1)"
else
    print_error "文件生成失败"
    exit 1
fi

print_success "完成! 📝"
