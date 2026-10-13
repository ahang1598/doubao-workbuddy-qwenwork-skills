# 英语老师技能 - 技术实施规范

本文档详细说明生成交互式英语学习教具的技术要求。

---

## 关键技术栈

### HTML5 Canvas API
用于绘制词汇卡片、语法图表和互动游戏。

**基本用法示例**：
```javascript
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

// 绘制单词卡片
function drawWordCard(word, x, y) {
    ctx.fillStyle = '#4CAF50';
    ctx.fillRect(x, y, 200, 150);
    ctx.fillStyle = 'white';
    ctx.font = '24px Arial';
    ctx.fillText(word, x + 50, y + 80);
}
```

### 事件监听器
实现用户交互的实时更新。

**常见事件**：
- `input` - 输入框、滑块变化
- `click` - 按钮、可点击元素
- `dragstart/dragover/drop` - 拖拽练习
- `keydown` - 打字练习、快捷键

### RequestAnimationFrame
实现流畅动画（60fps）。

**动画循环模式**：
```javascript
function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    update();
    draw();
    requestAnimationFrame(animate);
}
```

### 响应式设计
确保在所有设备上正常工作。

**CSS 技术**：
- Flexbox - 一维布局
- CSS Grid - 二维布局
- 媒体查询 - 断点适配

---

## 标准工件结构

每个生成的 HTML 游乐场必须包含以下部分：

### 1. 页眉区域
```html
<header>
    <h1>📖 单词记忆游戏</h1>
    <div class="score-panel">
        <span>得分：<strong id="score">0</strong></span>
        <span>连胜：<strong id="streak">0</strong></span>
        <span>等级：<strong id="level">A1</strong></span>
    </div>
</header>
```

### 2. 可视化区域
```html
<div class="learning-area">
    <canvas id="mainCanvas" width="800" height="600"></canvas>
    <!-- 或 SVG -->
    <svg id="grammarSvg" viewBox="0 0 800 600"></svg>
</div>
```

### 3. 交互式控件
```html
<div class="controls">
    <label>
        难度：
        <select id="difficulty">
            <option value="A1">A1 初级</option>
            <option value="A2">A2 初级进阶</option>
            <option value="B1" selected>B1 中级</option>
            <option value="B2">B2 中高级</option>
        </select>
    </label>
    <button id="startBtn">开始学习</button>
    <button id="hintBtn">💡 提示</button>
</div>
```

### 4. 解释与反馈
```html
<div class="explanation">
    <h3>当前学习：</h3>
    <p class="word-display" id="wordDisplay">apple</p>
    <p class="phonetic">/ˈæp.əl/</p>
    <p class="definition">n. 苹果</p>
    <div class="feedback" id="feedback"></div>
</div>
```

### 5. 游戏化元素
```html
<div class="gamification">
    <div class="achievements" id="achievements"></div>
    <div class="progress-bar">
        <div class="progress" id="progress" style="width: 0%"></div>
    </div>
    <div class="xp-display">经验值：<span id="xp">0</span>/100</div>
</div>
```

---

## 代码组织模式

### 单文件结构
所有代码必须内联在一个 HTML 文件中：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>英语游乐场</title>
    <style>
        /* 内联 CSS */
    </style>
</head>
<body>
    <!-- HTML 内容 -->
    
    <script>
        // 内联 JavaScript
    </script>
</body>
</html>
```

### JavaScript 模块模式
```javascript
(function() {
    // 私有变量
    let score = 0;
    let streak = 0;
    let currentLevel = 'A1';
    
    // 初始化
    function init() {
        setupEventListeners();
        loadVocabulary();
    }
    
    // 事件监听器设置
    function setupEventListeners() {
        document.getElementById('startBtn').addEventListener('click', startGame);
        document.getElementById('hintBtn').addEventListener('click', showHint);
    }
    
    // 加载词汇
    function loadVocabulary() {
        // 根据难度加载词汇
    }
    
    // 启动游戏
    function startGame() {
        // 游戏逻辑
    }
    
    // 启动
    init();
})();
```

---

## 响应式设计指南

### 画布尺寸自适应
```javascript
function resizeCanvas() {
    const container = document.querySelector('.learning-area');
    const canvas = document.getElementById('mainCanvas');
    
    canvas.width = container.clientWidth;
    canvas.height = Math.min(400, window.innerHeight * 0.5);
    
    draw();
}

window.addEventListener('resize', resizeCanvas);
```

### 触摸设备优化
```javascript
// 同时支持鼠标和触摸
canvas.addEventListener('mousedown', handlePointerDown);
canvas.addEventListener('touchstart', (e) => {
    e.preventDefault();
    const touch = e.touches[0];
    handlePointerDown({
        clientX: touch.clientX,
        clientY: touch.clientY
    });
});
```

---

## 无障碍访问

### ARIA 标签
```html
<canvas 
    id="gameCanvas" 
    role="img" 
    aria-label="单词记忆游戏界面，当前显示单词 apple">
</canvas>

<button 
    id="hintBtn" 
    aria-label="显示提示，帮助记忆单词">
    💡 提示
</button>
```

### 键盘导航
```javascript
// 支持 Tab 键和 Enter 键
document.querySelectorAll('button, input, select').forEach(el => {
    el.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            el.click();
        }
    });
});
```

---

## 性能优化

### 防抖处理
```javascript
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 使用
window.addEventListener('resize', debounce(resizeCanvas, 100));
```

### 资源预加载
```javascript
class ResourceLoader {
    constructor() {
        this.cache = new Map();
    }
    
    async preload(resources) {
        for (const url of resources) {
            if (!this.cache.has(url)) {
                const response = await fetch(url);
                this.cache.set(url, await response.text());
            }
        }
    }
    
    get(url) {
        return this.cache.get(url);
    }
}
```

---

## 常见可视化模式

### 单词卡片翻转动画
```javascript
function flipCard(cardElement, frontContent, backContent) {
    cardElement.classList.add('flipping');
    
    setTimeout(() => {
        cardElement.innerHTML = backContent;
        cardElement.classList.remove('flipping');
    }, 300);
}
```

### 时态时间轴绘制
```javascript
function drawTenseTimeline(tense) {
    const ctx = canvas.getContext('2d');
    
    // 绘制时间轴线
    ctx.beginPath();
    ctx.moveTo(50, 300);
    ctx.lineTo(750, 300);
    ctx.stroke();
    
    // 标注过去、现在、将来
    ctx.fillText('Past', 100, 320);
    ctx.fillText('Present', 400, 320);
    ctx.fillText('Future', 700, 320);
    
    // 根据时态绘制标记
    drawTenseMarker(tense);
}
```

### 进度条动画
```javascript
function animateProgress(element, from, to, duration) {
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        const easeOut = 1 - Math.pow(1 - progress, 3);
        const currentValue = from + (to - from) * easeOut;
        
        element.style.width = `${currentValue}%`;
        element.textContent = `${Math.round(currentValue)}%`;
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}
```

---

## 调试技巧

### 控制台日志
```javascript
const DEBUG = true;
function log(...args) {
    if (DEBUG) {
        console.log('[EnglishPlayground]', ...args);
    }
}
```

### 错误处理
```javascript
try {
    // 可能出错的代码
} catch (error) {
    console.error('游乐场错误:', error);
    showUserMessage('发生错误，请刷新页面重试');
}
```

---

## 测试清单

生成游乐场后，验证以下各项：

- [ ] 在 Chrome/Firefox/Safari 中正常工作
- [ ] 在手机竖屏模式下可用
- [ ] 在平板横屏模式下布局合理
- [ ] 所有交互控件响应正常
- [ ] 动画流畅（无明显卡顿）
- [ ] 键盘可以操作所有功能
- [ ] 没有外部依赖（纯离线运行）
- [ ] 代码无语法错误（通过浏览器控制台检查）
- [ ] 英语例句地道准确
- [ ] 中文翻译正确清晰

---

## 安全注意事项

- 不使用 `eval()` 执行用户输入
- 不加载外部脚本或样式
- 不使用 localStorage 存储敏感信息
- 所有计算在客户端完成，无需网络请求

---

## 资源推荐

### MDN Web Docs
- [Canvas API](https://developer.mozilla.org/zh-CN/docs/Web/API/Canvas_API)
- [RequestAnimationFrame](https://developer.mozilla.org/zh-CN/docs/Web/API/window/requestAnimationFrame)
- [CSS Flexbox](https://developer.mozilla.org/zh-CN/docs/Web/CSS/CSS_Flexible_Box_Layout)

### 示例代码
参考 `examples/` 目录中的完整示例：
- `word-memory-game.html` - 单词记忆游戏
- `grammar-explorer.html` - 语法探索器
- `pronunciation-trainer.html` - 发音训练器

---

## 特殊功能实现

### 语音播放（使用 Web Speech API）
```javascript
function speakWord(word) {
    const utterance = new SpeechSynthesisUtterance(word);
    utterance.lang = 'en-US';
    utterance.rate = 0.8; // 稍慢便于学习
    speechSynthesis.speak(utterance);
}
```

### 拖拽匹配练习
```javascript
function setupDragDrop() {
    const draggables = document.querySelectorAll('.draggable');
    const dropzones = document.querySelectorAll('.dropzone');
    
    draggables.forEach(draggable => {
        draggable.addEventListener('dragstart', (e) => {
            e.dataTransfer.setData('text/plain', draggable.dataset.word);
        });
    });
    
    dropzones.forEach(dropzone => {
        dropzone.addEventListener('drop', (e) => {
            const word = e.dataTransfer.getData('text/plain');
            checkMatch(word, dropzone.dataset.answer);
        });
    });
}
```

### 打字练习计时器
```javascript
class TypingTimer {
    constructor(duration, onComplete) {
        this.duration = duration; // 秒
        this.onComplete = onComplete;
        this.remaining = duration;
        this.interval = null;
    }
    
    start() {
        this.interval = setInterval(() => {
            this.remaining--;
            this.updateDisplay();
            
            if (this.remaining <= 0) {
                this.stop();
                this.onComplete();
            }
        }, 1000);
    }
    
    stop() {
        clearInterval(this.interval);
    }
    
    updateDisplay() {
        const minutes = Math.floor(this.remaining / 60);
        const seconds = this.remaining % 60;
        document.getElementById('timer').textContent = 
            `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }
}
```

---

## 内容质量标准

### 例句要求
- ✅ 地道自然，符合母语者表达习惯
- ✅ 难度适配 CEFR 水平
- ✅ 包含实用场景
- ✅ 避免歧义和复杂结构
- ✅ 标注重点词汇和语法

### 翻译要求
- ✅ 准确传达原意
- ✅ 语言简洁明了
- ✅ 必要时添加注释
- ✅ 文化差异处说明

### 发音指导
- ✅ 提供 IPA 音标
- ✅ 标注重音位置
- ✅ 指出常见发音错误
- ✅ 提供对比练习

---

## 扩展建议

### 短期优化 🔥
- 添加更多互动游戏类型
- 完善语音识别功能
- 增加真实对话场景

### 长期优化 🚀
- 集成 AI 发音评分
- 开发多人协作学习
- 创建个性化学习路径算法
