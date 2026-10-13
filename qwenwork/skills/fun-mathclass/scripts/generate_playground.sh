#!/bin/bash

# 数学游乐场生成脚本
# 用法: bash generate_playground.sh [主题] [难度级别] [输出目录]

# 默认参数
TOPIC="${1:-fraction}"
DIFFICULTY="${2:-beginner}"
OUTPUT_DIR="${3:-../examples}"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印信息函数
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
数学游乐场生成脚本

用法:
    bash generate_playground.sh [主题] [难度] [输出目录]

参数:
    主题        - 数学主题 (默认: fraction)
                可选: fraction, algebra, geometry, calculus, statistics
    难度        - 难度级别 (默认: beginner)
                可选: beginner, intermediate, advanced
    输出目录    - HTML文件输出路径 (默认: ../examples)

示例:
    bash generate_playground.sh fraction beginner ./output
    bash generate_playground.sh quadratic intermediate
    bash generate_playground.sh derivative advanced ./my-playgrounds

EOF
}

# 检查参数
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    show_help
    exit 0
fi

print_info "开始生成交互式数学游乐场..."
print_info "主题: $TOPIC"
print_info "难度: $DIFFICULTY"
print_info "输出目录: $OUTPUT_DIR"

# 确保输出目录存在
mkdir -p "$OUTPUT_DIR"

# 生成文件名
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="${TOPIC}_${DIFFICULTY}_${TIMESTAMP}.html"
OUTPUT_PATH="$OUTPUT_DIR/$FILENAME"

print_info "正在生成文件: $FILENAME"

# 根据主题生成不同的HTML内容
generate_fraction_playground() {
    cat << 'EOF'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>分数可视化游乐场</title>
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
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        
        .score-board {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 20px;
        }
        
        .score-item {
            background: rgba(255,255,255,0.2);
            padding: 10px 20px;
            border-radius: 10px;
            font-size: 1.1em;
        }
        
        .main-content {
            padding: 30px;
        }
        
        .visualization {
            text-align: center;
            margin-bottom: 30px;
        }
        
        #pizzaCanvas {
            border: 3px solid #e0e0e0;
            border-radius: 15px;
            background: #fafafa;
        }
        
        .controls {
            background: #f8f9fa;
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 25px;
        }
        
        .control-group {
            margin-bottom: 20px;
        }
        
        .control-group label {
            display: block;
            font-weight: bold;
            margin-bottom: 8px;
            color: #333;
        }
        
        .slider-container {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        input[type="range"] {
            flex: 1;
            height: 8px;
            border-radius: 5px;
            background: #ddd;
            outline: none;
            -webkit-appearance: none;
        }
        
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            cursor: pointer;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        }
        
        .value-display {
            min-width: 50px;
            text-align: center;
            font-weight: bold;
            font-size: 1.2em;
            color: #667eea;
        }
        
        .fraction-display {
            text-align: center;
            font-size: 3em;
            margin: 20px 0;
            padding: 20px;
            background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
            border-radius: 15px;
        }
        
        .fraction {
            display: inline-flex;
            flex-direction: column;
            align-items: center;
            vertical-align: middle;
        }
        
        .numerator {
            border-bottom: 3px solid #333;
            padding: 5px 15px;
        }
        
        .denominator {
            padding: 5px 15px;
        }
        
        .info-panel {
            background: #e3f2fd;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border-left: 5px solid #2196f3;
        }
        
        .achievements {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            justify-content: center;
            margin-top: 20px;
        }
        
        .badge {
            background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            opacity: 0.3;
            transition: all 0.3s;
        }
        
        .badge.unlocked {
            opacity: 1;
            transform: scale(1.05);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        .challenge-section {
            background: #fff3e0;
            padding: 20px;
            border-radius: 15px;
            margin-top: 20px;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 25px;
            font-size: 1em;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            margin: 5px;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
        }
        
        .btn:active {
            transform: translateY(0);
        }
        
        .btn-secondary {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }
        
        @keyframes celebrate {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        
        .celebrate {
            animation: celebrate 0.5s ease-in-out;
        }
        
        @media (max-width: 600px) {
            .header h1 {
                font-size: 1.8em;
            }
            
            .score-board {
                flex-direction: column;
                gap: 10px;
            }
            
            .fraction-display {
                font-size: 2em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🍕 分数可视化游乐场</h1>
            <p>通过互动披萨学习分数！</p>
            <div class="score-board">
                <div class="score-item">⭐ 得分: <span id="score">0</span></div>
                <div class="score-item">🔥 连胜: <span id="streak">0</span></div>
                <div class="score-item">🎯 正确率: <span id="accuracy">0%</span></div>
            </div>
        </div>
        
        <div class="main-content">
            <div class="visualization">
                <canvas id="pizzaCanvas" width="400" height="400"></canvas>
            </div>
            
            <div class="controls">
                <div class="control-group">
                    <label>分子（已吃片数）:</label>
                    <div class="slider-container">
                        <input type="range" id="numerator" min="0" max="12" value="1">
                        <span class="value-display" id="numValue">1</span>
                    </div>
                </div>
                
                <div class="control-group">
                    <label>分母（总片数）:</label>
                    <div class="slider-container">
                        <input type="range" id="denominator" min="1" max="12" value="4">
                        <span class="value-display" id="denValue">4</span>
                    </div>
                </div>
            </div>
            
            <div class="fraction-display">
                <div class="fraction">
                    <span class="numerator" id="fracNum">1</span>
                    <span class="denominator" id="fracDen">4</span>
                </div>
                <span style="margin: 0 20px;">=</span>
                <span id="decimal">0.25</span>
                <span style="margin: 0 20px;">=</span>
                <span id="percentage">25%</span>
            </div>
            
            <div class="info-panel">
                <strong>💡 知识点:</strong>
                <p id="infoText">分数表示整体的一部分。分子表示取了多少份，分母表示总共分成了多少份。</p>
            </div>
            
            <div class="challenge-section">
                <h3>🎮 挑战模式</h3>
                <p id="challengeText">根据披萨图案，这个分数是多少？</p>
                <div id="challengeOptions"></div>
                <div id="challengeFeedback"></div>
            </div>
            
            <div class="achievements">
                <span class="badge" id="badge1">🌟 初学者</span>
                <span class="badge" id="badge2">🔥 连胜5题</span>
                <span class="badge" id="badge3">🎯 全对</span>
                <span class="badge" id="badge4">🏆 分数大师</span>
                <span class="badge" id="badge5">💡 发现者</span>
            </div>
        </div>
    </div>

    <script>
        // 游戏状态
        let score = 0;
        let streak = 0;
        let totalAttempts = 0;
        let correctAttempts = 0;
        let badges = new Set();
        
        // 获取元素
        const canvas = document.getElementById('pizzaCanvas');
        const ctx = canvas.getContext('2d');
        const numeratorSlider = document.getElementById('numerator');
        const denominatorSlider = document.getElementById('denominator');
        const numValue = document.getElementById('numValue');
        const denValue = document.getElementById('denValue');
        
        // 绘制披萨
        function drawPizza() {
            const num = parseInt(numeratorSlider.value);
            const den = parseInt(denominatorSlider.value);
            
            // 清空画布
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            const centerX = canvas.width / 2;
            const centerY = canvas.height / 2;
            const radius = 150;
            
            // 绘制披萨底
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
            ctx.fillStyle = '#f4d03f';
            ctx.fill();
            ctx.strokeStyle = '#e67e22';
            ctx.lineWidth = 5;
            ctx.stroke();
            
            // 绘制切片分割线
            ctx.strokeStyle = '#d35400';
            ctx.lineWidth = 2;
            for (let i = 0; i < den; i++) {
                const angle = (i / den) * 2 * Math.PI - Math.PI / 2;
                ctx.beginPath();
                ctx.moveTo(centerX, centerY);
                ctx.lineTo(
                    centerX + radius * Math.cos(angle),
                    centerY + radius * Math.sin(angle)
                );
                ctx.stroke();
            }
            
            // 填充已吃的部分
            ctx.fillStyle = '#e74c3c';
            for (let i = 0; i < num; i++) {
                ctx.beginPath();
                ctx.moveTo(centerX, centerY);
                const startAngle = (i / den) * 2 * Math.PI - Math.PI / 2;
                const endAngle = ((i + 1) / den) * 2 * Math.PI - Math.PI / 2;
                ctx.arc(centerX, centerY, radius - 5, startAngle, endAngle);
                ctx.closePath();
                ctx.fill();
            }
            
            // 绘制芝士效果
            ctx.fillStyle = '#f7dc6f';
            for (let i = 0; i < den; i++) {
                const angle = ((i + 0.5) / den) * 2 * Math.PI - Math.PI / 2;
                const x = centerX + (radius * 0.7) * Math.cos(angle);
                const y = centerY + (radius * 0.7) * Math.sin(angle);
                ctx.beginPath();
                ctx.arc(x, y, 8, 0, 2 * Math.PI);
                ctx.fill();
            }
            
            // 更新分数显示
            updateFractionDisplay(num, den);
        }
        
        // 更新分数显示
        function updateFractionDisplay(num, den) {
            document.getElementById('fracNum').textContent = num;
            document.getElementById('fracDen').textContent = den;
            
            const decimal = (num / den).toFixed(4);
            const percentage = ((num / den) * 100).toFixed(2);
            
            document.getElementById('decimal').textContent = decimal;
            document.getElementById('percentage').textContent = percentage + '%';
            
            // 更新信息文本
            updateInfoText(num, den);
        }
        
        // 更新信息文本
        function updateInfoText(num, den) {
            const infoTexts = [
                "分数表示整体的一部分。分子表示取了多少份，分母表示总共分成了多少份。",
                "当分子等于分母时，分数等于1，表示整个披萨！",
                "当分子为0时，表示还没有吃任何披萨。",
                "等值分数：1/2 = 2/4 = 3/6，它们表示相同的大小！",
                "真分数：分子小于分母（如 3/4）。假分数：分子大于或等于分母（如 5/4）。"
            ];
            
            let index = 0;
            if (num === den) index = 1;
            else if (num === 0) index = 2;
            else if (num * 2 === den || num * 3 === den * 2) index = 3;
            else if (num > den) index = 4;
            
            document.getElementById('infoText').textContent = '💡 ' + infoTexts[index];
        }
        
        // 更新分数
        function updateScore(points) {
            score += points;
            document.getElementById('score').textContent = score;
            
            // 检查徽章
            checkBadges();
        }
        
        // 检查徽章
        function checkBadges() {
            if (score >= 50 && !badges.has('badge1')) {
                badges.add('badge1');
                document.getElementById('badge1').classList.add('unlocked');
            }
            if (streak >= 5 && !badges.has('badge2')) {
                badges.add('badge2');
                document.getElementById('badge2').classList.add('unlocked');
            }
            if (correctAttempts >= 10 && totalAttempts > 0 && 
                correctAttempts === totalAttempts && !badges.has('badge3')) {
                badges.add('badge3');
                document.getElementById('badge3').classList.add('unlocked');
            }
            if (score >= 200 && !badges.has('badge4')) {
                badges.add('badge4');
                document.getElementById('badge4').classList.add('unlocked');
            }
            if (streak >= 3 && !badges.has('badge5')) {
                badges.add('badge5');
                document.getElementById('badge5').classList.add('unlocked');
            }
        }
        
        // 生成挑战
        function generateChallenge() {
            const den = Math.floor(Math.random() * 8) + 2; // 2-10
            const num = Math.floor(Math.random() * (den + 1)); // 0-den
            
            // 设置滑块
            numeratorSlider.value = num;
            denominatorSlider.value = den;
            numValue.textContent = num;
            denValue.textContent = den;
            
            drawPizza();
            
            // 生成选项
            const correctAnswer = `${num}/${den}`;
            const options = [correctAnswer];
            
            while (options.length < 4) {
                const wrongNum = Math.floor(Math.random() * 10);
                const wrongDen = Math.floor(Math.random() * 8) + 2;
                const wrongAnswer = `${wrongNum}/${wrongDen}`;
                if (!options.includes(wrongAnswer) && wrongAnswer !== correctAnswer) {
                    options.push(wrongAnswer);
                }
            }
            
            // 打乱选项
            options.sort(() => Math.random() - 0.5);
            
            // 显示选项
            const optionsDiv = document.getElementById('challengeOptions');
            optionsDiv.innerHTML = '';
            options.forEach(option => {
                const btn = document.createElement('button');
                btn.className = 'btn';
                btn.textContent = option;
                btn.onclick = () => checkAnswer(option, correctAnswer);
                optionsDiv.appendChild(btn);
            });
            
            document.getElementById('challengeFeedback').innerHTML = '';
        }
        
        // 检查答案
        function checkAnswer(selected, correct) {
            totalAttempts++;
            const feedbackDiv = document.getElementById('challengeFeedback');
            
            if (selected === correct) {
                correctAttempts++;
                streak++;
                const points = 20 + (streak > 3 ? 10 : 0);
                updateScore(points);
                
                feedbackDiv.innerHTML = `<p style="color: green; font-size: 1.2em;">🎉 正确! +${points}分</p>`;
                document.querySelector('.container').classList.add('celebrate');
                setTimeout(() => {
                    document.querySelector('.container').classList.remove('celebrate');
                }, 500);
            } else {
                streak = 0;
                feedbackDiv.innerHTML = `<p style="color: red; font-size: 1.2em;">❌ 错误! 正确答案是 ${correct}</p>`;
            }
            
            // 更新显示
            document.getElementById('streak').textContent = streak;
            document.getElementById('accuracy').textContent = 
                Math.round((correctAttempts / totalAttempts) * 100) + '%';
            
            // 延迟后生成新挑战
            setTimeout(generateChallenge, 2000);
        }
        
        // 事件监听
        numeratorSlider.addEventListener('input', (e) => {
            numValue.textContent = e.target.value;
            drawPizza();
        });
        
        denominatorSlider.addEventListener('input', (e) => {
            denValue.textContent = e.target.value;
            // 确保分子不超过分母
            if (parseInt(numeratorSlider.value) > parseInt(e.target.value)) {
                numeratorSlider.value = e.target.value;
                numValue.textContent = e.target.value;
            }
            numeratorSlider.max = e.target.value;
            drawPizza();
        });
        
        // 初始化
        drawPizza();
        generateChallenge();
    </script>
</body>
</html>
EOF
}

# 生成游乐场HTML文件
case "$TOPIC" in
    "fraction"|"分数")
        generate_fraction_playground > "$OUTPUT_PATH"
        ;;
    *)
        # 默认生成分数游乐场
        generate_fraction_playground > "$OUTPUT_PATH"
        print_warning "未知主题 '$TOPIC'，使用默认主题 'fraction'"
        ;;
esac

# 检查文件是否生成成功
if [ -f "$OUTPUT_PATH" ]; then
    print_success "游乐场文件生成成功!"
    print_info "文件路径: $OUTPUT_PATH"
    print_info "文件大小: $(du -h "$OUTPUT_PATH" | cut -f1)"
else
    print_error "文件生成失败"
    exit 1
fi

print_success "完成! 🎉"
