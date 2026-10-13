# 技术实施规范

本文档详细说明生成交互式数学教具的技术要求。

---

## 关键技术栈

### HTML5 Canvas API
用于绘制动态图表和可视化效果。

**基本用法示例**：
```javascript
const canvas = document.getElementById('myCanvas');
const ctx = canvas.getContext('2d');

// 绘制图形
ctx.beginPath();
ctx.arc(100, 100, 50, 0, Math.PI * 2);
ctx.fillStyle = '#4CAF50';
ctx.fill();
```

### 事件监听器
实现用户交互的实时更新。

**常见事件**：
- `input` - 滑块、输入框变化
- `click` - 按钮、可点击元素
- `mousemove` - 拖拽、悬停效果
- `touchstart/touchmove` - 移动端触摸

### RequestAnimationFrame
实现流畅动画（60fps）。

**动画循环模式**：
```javascript
function animate() {
    // 清除画布
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // 更新状态
    update();
    
    // 重新绘制
    draw();
    
    // 继续动画
    requestAnimationFrame(animate);
}
```

### 响应式设计
确保在所有设备上正常工作。

**CSS 技术**：
- Flexbox - 一维布局
- CSS Grid - 二维布局
- 媒体查询 - 断点适配

**移动优先断点**：
```css
/* 手机（默认） */
.container { padding: 10px; }

/* 平板 */
@media (min-width: 768px) {
    .container { padding: 20px; }
}

/* 台式机 */
@media (min-width: 1024px) {
    .container { max-width: 1200px; margin: 0 auto; }
}
```

---

## 标准工件结构

每个生成的 HTML 游乐场必须包含以下部分：

### 1. 页眉区域
```html
<header>
    <h1>🎯 二次函数探索器</h1>
    <div class="score-panel">
        <span>得分：<strong id="score">0</strong></span>
        <span>连胜：<strong id="streak">0</strong></span>
    </div>
</header>
```

### 2. 可视化区域
```html
<div class="visualization">
    <canvas id="mainCanvas" width="800" height="600"></canvas>
    <!-- 或 SVG -->
    <svg id="mainSvg" viewBox="0 0 800 600"></svg>
</div>
```

### 3. 交互式控件
```html
<div class="controls">
    <label>
        a: <input type="range" id="sliderA" min="-5" max="5" step="0.1" value="1">
        <span id="valueA">1</span>
    </label>
    <button id="resetBtn">重置</button>
    <button id="challengeBtn">挑战模式</button>
</div>
```

### 4. 解释与反馈
```html
<div class="explanation">
    <h3>当前函数：</h3>
    <p class="equation">y =<span id="eqA">1</span>x² +<span id="eqB">0</span>x + <span id="eqC">0</span></p>
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
    <title>数学游乐场</title>
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
    
    // 初始化
    function init() {
        setupEventListeners();
        startAnimationLoop();
    }
    
    // 事件监听器设置
    function setupEventListeners() {
        document.getElementById('sliderA').addEventListener('input', updateEquation);
        document.getElementById('resetBtn').addEventListener('click', reset);
    }
    
    // 更新函数
    function updateEquation() {
        const a = parseFloat(document.getElementById('sliderA').value);
        document.getElementById('valueA').textContent = a.toFixed(1);
        draw();
    }
    
    // 绘图函数
    function draw() {
        const ctx = document.getElementById('mainCanvas').getContext('2d');
        // 绘图逻辑...
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
    const container = document.querySelector('.visualization');
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
    id="graphCanvas" 
    role="img" 
    aria-label="二次函数图像，当前 a=1, b=0, c=0">
</canvas>

<button 
    id="resetBtn" 
    aria-label="重置所有参数到初始值">
    重置
</button>
```

### 键盘导航
```javascript
// 支持 Tab 键和 Enter 键
document.querySelectorAll('button, input').forEach(el => {
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

### 对象池模式（大量粒子时）
```javascript
class ParticlePool {
    constructor(size) {
        this.pool = [];
        for (let i = 0; i < size; i++) {
            this.pool.push({ x: 0, y: 0, active: false });
        }
    }
    
    get() {
        return this.pool.find(p => !p.active);
    }
    
    release(particle) {
        particle.active = false;
    }
}
```

---

## 常见可视化模式

### 函数图像绘制
```javascript
function plotFunction(fn, color = '#000') {
    const ctx = canvas.getContext('2d');
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    
    for (let x = -10; x<= 10; x += 0.1) {
        const screenX = mapX(x);
        const screenY = mapY(fn(x));
        
        if (x === -10) {
            ctx.moveTo(screenX, screenY);
        } else {
            ctx.lineTo(screenX, screenY);
        }
    }
    
    ctx.stroke();
}
```

### 动态几何构造
```javascript
function drawTriangle(p1, p2, p3) {
    ctx.beginPath();
    ctx.moveTo(p1.x, p1.y);
    ctx.lineTo(p2.x, p2.y);
    ctx.lineTo(p3.x, p3.y);
    ctx.closePath();
    ctx.stroke();
    
    // 标注顶点
    [p1, p2, p3].forEach((p, i) => {
        ctx.fillText(`P${i+1}`, p.x + 10, p.y - 10);
    });
}
```

### 动画过渡
```javascript
function animateValue(element, start, end, duration) {
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // 缓动函数
        const easeOut = 1 - Math.pow(1 - progress, 3);
        
        const current = start + (end - start) * easeOut;
        element.textContent = current.toFixed(2);
        
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
        console.log('[MathPlayground]', ...args);
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
- `fraction-visualizer.html` - 分数可视化器
- `quadratic-explorer.html` - 二次函数探索器
- `derivative-visualizer.html` - 导数可视化器
