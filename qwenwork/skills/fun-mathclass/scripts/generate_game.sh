#!/bin/bash

# 数学游戏生成脚本
# 用法: bash generate_game.sh [主题] [游戏模式] [输出目录]

# 默认参数
TOPIC="${1:-arithmetic}"
GAME_MODE="${2:-quiz}"
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
数学游戏生成脚本

用法:
    bash generate_game.sh [主题] [模式] [输出目录]

参数:
    主题        - 数学主题 (默认: arithmetic)
                可选: arithmetic, algebra, geometry, speed, challenge
    模式        - 游戏模式 (默认: quiz)
                可选: quiz, speed, survival, puzzle
    输出目录    - HTML文件输出路径 (默认: ../examples)

示例:
    bash generate_game.sh arithmetic quiz ./games
    bash generate_game.sh algebra speed
    bash generate_game.sh geometry survival ./my-games

EOF
}

# 检查参数
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    show_help
    exit 0
fi

print_info "开始生成数学游戏..."
print_info "主题: $TOPIC"
print_info "模式: $GAME_MODE"

# 确保输出目录存在
mkdir -p "$OUTPUT_DIR"

# 生成文件名
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="${TOPIC}_game_${GAME_MODE}_${TIMESTAMP}.html"
OUTPUT_PATH="$OUTPUT_DIR/$FILENAME"

print_info "正在生成文件: $FILENAME"

# 生成算术测验游戏
generate_arithmetic_quiz() {
    cat << 'EOF'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>算术挑战赛</title>
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
        
        .game-container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .game-header {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .game-header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .stats-bar {
            display: flex;
            justify-content: space-around;
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
        }
        
        .stat {
            text-align: center;
        }
        
        .stat-value {
            font-size: 2em;
            font-weight: bold;
        }
        
        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        .game-area {
            padding: 40px;
            text-align: center;
        }
        
        .timer-bar {
            width: 100%;
            height: 10px;
            background: #e0e0e0;
            border-radius: 5px;
            overflow: hidden;
            margin-bottom: 30px;
        }
        
        .timer-fill {
            height: 100%;
            background: linear-gradient(90deg, #4caf50, #8bc34a);
            transition: width 0.1s linear;
        }
        
        .timer-fill.warning {
            background: linear-gradient(90deg, #ff9800, #ffc107);
        }
        
        .timer-fill.danger {
            background: linear-gradient(90deg, #f44336, #ff5722);
        }
        
        .question {
            font-size: 3em;
            margin: 30px 0;
            color: #333;
            font-weight: bold;
        }
        
        .answer-input {
            font-size: 2em;
            padding: 15px 30px;
            border: 3px solid #ddd;
            border-radius: 10px;
            text-align: center;
            width: 200px;
            outline: none;
            transition: border-color 0.3s;
        }
        
        .answer-input:focus {
            border-color: #667eea;
        }
        
        .answer-input.correct {
            border-color: #4caf50;
            background: #e8f5e9;
        }
        
        .answer-input.wrong {
            border-color: #f44336;
            background: #ffebee;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 30px;
            font-size: 1.2em;
            cursor: pointer;
            transition: all 0.3s;
            margin: 10px;
        }
        
        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }
        
        .btn-secondary {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }
        
        .feedback {
            font-size: 1.5em;
            margin: 20px 0;
            min-height: 40px;
        }
        
        .feedback.correct {
            color: #4caf50;
        }
        
        .feedback.wrong {
            color: #f44336;
        }
        
        .progress-bar {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin: 20px 0;
        }
        
        .progress-dot {
            width: 15px;
            height: 15px;
            border-radius: 50%;
            background: #e0e0e0;
            transition: all 0.3s;
        }
        
        .progress-dot.correct {
            background: #4caf50;
            transform: scale(1.2);
        }
        
        .progress-dot.wrong {
            background: #f44336;
        }
        
        .progress-dot.current {
            background: #667eea;
            animation: pulse 1s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.3); }
        }
        
        .achievements-panel {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 15px;
            margin-top: 20px;
        }
        
        .achievement {
            display: inline-block;
            padding: 8px 15px;
            margin: 5px;
            border-radius: 20px;
            background: #e0e0e0;
            opacity: 0.5;
            transition: all 0.3s;
        }
        
        .achievement.unlocked {
            opacity: 1;
            background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        .start-screen, .end-screen {
            text-align: center;
            padding: 40px;
        }
        
        .start-screen h2, .end-screen h2 {
            font-size: 2em;
            margin-bottom: 20px;
            color: #333;
        }
        
        .difficulty-selector {
            margin: 20px 0;
        }
        
        .difficulty-btn {
            padding: 10px 25px;
            margin: 5px;
            border: 2px solid #667eea;
            background: white;
            color: #667eea;
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .difficulty-btn:hover, .difficulty-btn.selected {
            background: #667eea;
            color: white;
        }
        
        .final-score {
            font-size: 4em;
            color: #667eea;
            font-weight: bold;
            margin: 20px 0;
        }
        
        .confetti {
            position: fixed;
            width: 10px;
            height: 10px;
            background: #f0f;
            position: absolute;
            animation: confetti-fall 3s linear forwards;
        }
        
        @keyframes confetti-fall {
            0% { transform: translateY(-100px) rotate(0deg); opacity: 1; }
            100% { transform: translateY(100vh) rotate(720deg); opacity: 0; }
        }
        
        @media (max-width: 600px) {
            .question { font-size: 2em; }
            .answer-input { font-size: 1.5em; width: 150px; }
            .game-header h1 { font-size: 1.8em; }
        }
    </style>
</head>
<body>
    <div class="game-container">
        <div class="game-header">
            <h1>🚀 算术挑战赛</h1>
            <p>测试你的计算速度和准确度！</p>
        </div>
        
        <div class="game-area">
            <!-- 开始界面 -->
            <div id="startScreen" class="start-screen">
                <h2>选择难度</h2>
                <div class="difficulty-selector">
                    <button class="difficulty-btn selected" data-level="easy">简单</button>
                    <button class="difficulty-btn" data-level="medium">中等</button>
                    <button class="difficulty-btn" data-level="hard">困难</button>
                </div>
                <button class="btn" onclick="startGame()">开始挑战</button>
            </div>
            
            <!-- 游戏界面 -->
            <div id="gameScreen" style="display: none;">
                <div class="stats-bar">
                    <div class="stat">
                        <div class="stat-value" id="score">0</div>
                        <div class="stat-label">得分</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="streak">0</div>
                        <div class="stat-label">连胜</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="timer">30</div>
                        <div class="stat-label">时间</div>
                    </div>
                </div>
                
                <div class="timer-bar">
                    <div class="timer-fill" id="timerBar"></div>
                </div>
                
                <div class="progress-bar" id="progressBar"></div>
                
                <div class="question" id="question">?</div>
                
                <input type="number" class="answer-input" id="answerInput" 
                       placeholder="?" autofocus>
                
                <div class="feedback" id="feedback"></div>
                
                <button class="btn" onclick="checkAnswer()">提交答案</button>
                <button class="btn btn-secondary" onclick="skipQuestion()">跳过</button>
            </div>
            
            <!-- 结束界面 -->
            <div id="endScreen" class="end-screen" style="display: none;">
                <h2>🎉 挑战结束!</h2>
                <div class="final-score" id="finalScore">0</div>
                <p>正确: <span id="correctCount">0</span> | 错误: <span id="wrongCount">0</span></p>
                <p>准确率: <span id="accuracy">0%</span></p>
                <div class="achievements-panel">
                    <h3>🏆 获得成就</h3>
                    <div id="achievementsList"></div>
                </div>
                <button class="btn" onclick="restartGame()">再玩一次</button>
            </div>
        </div>
    </div>

    <script>
        // 游戏配置
        const CONFIG = {
            easy: { maxNum: 10, time: 30 },
            medium: { maxNum: 50, time: 25 },
            hard: { maxNum: 100, time: 20 }
        };
        
        // 游戏状态
        let gameState = {
            difficulty: 'easy',
            score: 0,
            streak: 0,
            correct: 0,
            wrong: 0,
            currentQuestion: 0,
            totalQuestions: 10,
            timeLeft: 30,
            timerInterval: null,
            questions: []
        };
        
        // 难度选择
        document.querySelectorAll('.difficulty-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.difficulty-btn').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                gameState.difficulty = btn.dataset.level;
            });
        });
        
        // 生成题目
        function generateQuestions() {
            const config = CONFIG[gameState.difficulty];
            const questions = [];
            const operations = ['+', '-', '*'];
            
            for (let i = 0; i < gameState.totalQuestions; i++) {
                const op = operations[Math.floor(Math.random() * operations.length)];
                let a, b, answer;
                
                switch(op) {
                    case '+':
                        a = Math.floor(Math.random() * config.maxNum) + 1;
                        b = Math.floor(Math.random() * config.maxNum) + 1;
                        answer = a + b;
                        break;
                    case '-':
                        a = Math.floor(Math.random() * config.maxNum) + 1;
                        b = Math.floor(Math.random() * a) + 1;
                        answer = a - b;
                        break;
                    case '*':
                        a = Math.floor(Math.random() * Math.sqrt(config.maxNum)) + 1;
                        b = Math.floor(Math.random() * Math.sqrt(config.maxNum)) + 1;
                        answer = a * b;
                        break;
                }
                
                questions.push({
                    text: `${a} ${op} ${b} = ?`,
                    answer: answer,
                    userAnswer: null
                });
            }
            
            return questions;
        }
        
        // 开始游戏
        function startGame() {
            gameState.questions = generateQuestions();
            gameState.currentQuestion = 0;
            gameState.score = 0;
            gameState.streak = 0;
            gameState.correct = 0;
            gameState.wrong = 0;
            gameState.timeLeft = CONFIG[gameState.difficulty].time;
            
            document.getElementById('startScreen').style.display = 'none';
            document.getElementById('gameScreen').style.display = 'block';
            document.getElementById('endScreen').style.display = 'none';
            
            initProgressBar();
            showQuestion();
            startTimer();
            
            document.getElementById('answerInput').focus();
        }
        
        // 初始化进度条
        function initProgressBar() {
            const bar = document.getElementById('progressBar');
            bar.innerHTML = '';
            for (let i = 0; i < gameState.totalQuestions; i++) {
                const dot = document.createElement('div');
                dot.className = 'progress-dot';
                if (i === 0) dot.classList.add('current');
                bar.appendChild(dot);
            }
        }
        
        // 显示题目
        function showQuestion() {
            if (gameState.currentQuestion >= gameState.totalQuestions) {
                endGame();
                return;
            }
            
            const q = gameState.questions[gameState.currentQuestion];
            document.getElementById('question').textContent = q.text;
            document.getElementById('answerInput').value = '';
            document.getElementById('answerInput').className = 'answer-input';
            document.getElementById('feedback').textContent = '';
            
            // 更新进度点
            document.querySelectorAll('.progress-dot').forEach((dot, i) => {
                dot.classList.remove('current');
                if (i === gameState.currentQuestion) dot.classList.add('current');
            });
            
            // 重置计时器
            gameState.timeLeft = CONFIG[gameState.difficulty].time;
            updateTimerBar();
        }
        
        // 计时器
        function startTimer() {
            gameState.timerInterval = setInterval(() => {
                gameState.timeLeft--;
                updateTimerBar();
                
                if (gameState.timeLeft <= 0) {
                    handleTimeout();
                }
            }, 1000);
        }
        
        function updateTimerBar() {
            document.getElementById('timer').textContent = gameState.timeLeft;
            const percentage = (gameState.timeLeft / CONFIG[gameState.difficulty].time) * 100;
            const bar = document.getElementById('timerBar');
            bar.style.width = percentage + '%';
            
            bar.classList.remove('warning', 'danger');
            if (percentage < 30) bar.classList.add('danger');
            else if (percentage < 60) bar.classList.add('warning');
        }
        
        function handleTimeout() {
            gameState.wrong++;
            gameState.streak = 0;
            updateStats();
            showFeedback(false, '时间到!');
            
            setTimeout(() => {
                gameState.currentQuestion++;
                showQuestion();
            }, 1500);
        }
        
        // 检查答案
        function checkAnswer() {
            const input = document.getElementById('answerInput');
            const userAnswer = parseInt(input.value);
            
            if (isNaN(userAnswer)) return;
            
            const q = gameState.questions[gameState.currentQuestion];
            const isCorrect = userAnswer === q.answer;
            
            q.userAnswer = userAnswer;
            
            if (isCorrect) {
                gameState.correct++;
                gameState.streak++;
                const points = 10 + (gameState.streak > 3 ? 5 : 0);
                gameState.score += points;
                input.classList.add('correct');
                showFeedback(true, `正确! +${points}分`);
            } else {
                gameState.wrong++;
                gameState.streak = 0;
                input.classList.add('wrong');
                showFeedback(false, `错误! 答案是${q.answer}`);
            }
            
            updateStats();
            updateProgressDot(isCorrect);
            
            setTimeout(() => {
                gameState.currentQuestion++;
                showQuestion();
            }, 1500);
        }
        
        // 跳过题目
        function skipQuestion() {
            gameState.wrong++;
            gameState.streak = 0;
            updateStats();
            updateProgressDot(false);
            
            gameState.currentQuestion++;
            showQuestion();
        }
        
        // 更新统计
        function updateStats() {
            document.getElementById('score').textContent = gameState.score;
            document.getElementById('streak').textContent = gameState.streak;
        }
        
        // 更新进度点
        function updateProgressDot(isCorrect) {
            const dots = document.querySelectorAll('.progress-dot');
            const currentDot = dots[gameState.currentQuestion];
            currentDot.classList.remove('current');
            currentDot.classList.add(isCorrect ? 'correct' : 'wrong');
        }
        
        // 显示反馈
        function showFeedback(isCorrect, message) {
            const feedback = document.getElementById('feedback');
            feedback.textContent = message;
            feedback.className = 'feedback ' + (isCorrect ? 'correct' : 'wrong');
        }
        
        // 结束游戏
        function endGame() {
            clearInterval(gameState.timerInterval);
            
            document.getElementById('gameScreen').style.display = 'none';
            document.getElementById('endScreen').style.display = 'block';
            
            document.getElementById('finalScore').textContent = gameState.score;
            document.getElementById('correctCount').textContent = gameState.correct;
            document.getElementById('wrongCount').textContent = gameState.wrong;
            
            const accuracy = Math.round((gameState.correct / gameState.totalQuestions) * 100);
            document.getElementById('accuracy').textContent = accuracy + '%';
            
            showAchievements();
            
            if (accuracy >= 80) {
                createConfetti();
            }
        }
        
        // 显示成就
        function showAchievements() {
            const achievements = [];
            
            if (gameState.score >= 50) achievements.push('🌟 初学者');
            if (gameState.score >= 100) achievements.push('🏆 高分选手');
            if (gameState.streak >= 5) achievements.push('🔥 连胜大师');
            if (gameState.correct === gameState.totalQuestions) achievements.push('💯 完美通关');
            if (gameState.difficulty === 'hard' && gameState.score >= 80) achievements.push('🎖️ 困难征服者');
            
            const list = document.getElementById('achievementsList');
            list.innerHTML = achievements.map(a => 
                `<span class="achievement unlocked">${a}</span>`
            ).join('');
        }
        
        // 创建彩带效果
        function createConfetti() {
            const colors = ['#f44336', '#e91e63', '#9c27b0', '#673ab7', '#3f51b5', 
                           '#2196f3', '#03a9f4', '#00bcd4', '#4caf50', '#8bc34a', 
                           '#cddc39', '#ffeb3b', '#ffc107', '#ff9800', '#ff5722'];
            
            for (let i = 0; i < 50; i++) {
                setTimeout(() => {
                    const confetti = document.createElement('div');
                    confetti.className = 'confetti';
                    confetti.style.left = Math.random() * 100 + 'vw';
                    confetti.style.background = colors[Math.floor(Math.random() * colors.length)];
                    confetti.style.animationDuration = (Math.random() * 2 + 2) + 's';
                    document.body.appendChild(confetti);
                    
                    setTimeout(() => confetti.remove(), 4000);
                }, i * 50);
            }
        }
        
        // 重新开始
        function restartGame() {
            document.getElementById('endScreen').style.display = 'none';
            document.getElementById('startScreen').style.display = 'block';
        }
        
        // 键盘事件
        document.getElementById('answerInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') checkAnswer();
        });
    </script>
</body>
</html>
EOF
}

# 生成游戏文件
case "$TOPIC" in
    "arithmetic"|"算术")
        generate_arithmetic_quiz > "$OUTPUT_PATH"
        ;;
    *)
        generate_arithmetic_quiz > "$OUTPUT_PATH"
        print_warning "未知主题 '$TOPIC'，使用默认主题 'arithmetic'"
        ;;
esac

# 检查文件
if [ -f "$OUTPUT_PATH" ]; then
    print_success "游戏文件生成成功!"
    print_info "文件路径: $OUTPUT_PATH"
    print_info "文件大小: $(du -h "$OUTPUT_PATH" | cut -f1)"
else
    print_error "文件生成失败"
    exit 1
fi

print_success "完成! 🎮"
