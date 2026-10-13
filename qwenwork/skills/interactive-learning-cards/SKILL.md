---
name: interactive-learning-cards
description: 为教师创建课堂专用的交互式学习应用。包含闪卡、测验和浏览模式。基于记忆科学原理设计，支持学生自主学习和课堂互动练习。当老师需要制作学科知识点卡片、课堂练习题、复习工具或家校共育学习资源时使用此技能。不要在简单文档生成、纯文本整理或非教学场景时触发。
install_source: official
install_method: download
skill_id: official_3WFnNPKP
enabled_at: 1791893803615
version: 1.0.0
name_zh: 互动学习卡片
---

# 互动学习应用技能

创建具有多种学习模式、精美 UI 和流畅动画的交互式学习应用。基于记忆科学原理设计，支持闪卡、测验以及浏览三种模式。

## 严格禁止

- 不要使用双引号包裹包含中文引号的字符串，必须使用反引号 (`)
- 不要编造示例数据，必须使用真实可验证的内容
- 不要创建超过 50 张卡片的单个学习集（应分类管理）
- 不要在问题或答案中使用模糊表述，必须清晰准确
- 不要混合多种题型于同一卡片，每张卡片只测试一个知识点
- 不要忽略键盘快捷键的实现，必须支持基础导航

## 模板选择决策树

**用户说"闪卡/记忆卡片/背诵":**
- 默认模板 → `modern.html`（简洁现代风格）
- 要求古典/传统风格 → `classical.html`（中式学者风）

**用户说"测验/测试/练习":**
- 启用 Quiz Mode → 所有模板都支持
- 需要自动评分 → 确保设置 correct 选项索引

**用户说"复习/浏览/查看所有":**
- 启用 Browse Mode → 网格视图展示所有卡片

**关键区分:**
- flashcard = 翻转卡片，主动回忆
- quiz = 选择题，被动识别
- browse = 浏览模式，快速查阅

## 核心工作流

```javascript
// 1. 定义学习数据 - 使用反引号避免引号冲突
const cards = [
  {
    id: "1",                    // 唯一标识
    category: `词汇`,            // 分类标签
    question: `问题内容`,        // 问题/正面
    answer: `答案内容`,          // 答案/反面
    difficulty: `easy`          // 初始难度：easy/medium/hard
  }
];

// 2. 测验模式数据（可选）
const quizQuestions = [
  {
    question: `问题文本`,
    options: [`A. 选项 1`, `B. 选项 2`, `C. 选项 3`, `D. 选项 4`],
    correct: 1  // 正确选项索引 (0-based)
  }
];

// 3. 初始化应用
function init() {
  renderCard();    // 渲染当前卡片
  updateStats();   // 更新统计信息
}
```

## 数据格式规范

### 正确示例

```javascript
// [正确] 使用反引号，可安全包含中文引号
{
  question: `「初唐四杰」包括谁？`,
  answer: `王勃、杨炯、卢照邻、骆宾王`,
  category: `文学常识`
}

// [正确] 测验选项格式
{
  question: `乘法运算 3×4=?`,
  options: [`A. 7`, `B. 12`, `C. 9`, `D. 15`],
  correct: 1
}
```

### 错误示例

```javascript
// [错误] 双引号嵌套导致语法错误
{
  question: ""初唐四杰"包括谁？",  // ❌ 会报错
}

// [错误] 缺少必要字段
{
  question: `问题`,
  // ❌ 缺少 answer 字段
}

// [错误] 数据类型错误
{
  correct: `1`  // ❌ 应该是数字不是字符串
}
```

## 中文引号处理规范

### 问题描述

当问题或答案中包含中文引号（""）时，使用双引号包裹会导致 JavaScript 语法错误。

### 解决方案优先级

**方案 1（推荐）：使用反引号**
```javascript
question: `「滕王阁序」的作者是谁？`
answer: `唐代诗人「王勃」`
```

**方案 2：使用书名号替代**
```javascript
question: "《滕王阁序》的作者是谁？"
answer: "唐代诗人《王勃》"
```

**方案 3：转义引号**
```javascript
question: "\"滕王阁序\"的作者是谁？"
answer: "唐代诗人\"王勃\""
```

## 学习模式说明

### 闪卡模式
- **用途**: 主动回忆训练，最适合记忆类学习
- **交互**: 点击卡片翻转查看答案
- **评分**: 4 级难度评价（重来/困难/良好/简单）
- **快捷键**: 空格翻转，方向键导航，数字键评分

### 测验模式
- **用途**: 被动识别测试，适合快速检验
- **交互**: 单选或多选题，即时反馈
- **评分**: 自动判断正误
- **快捷键**: 字母键选择选项

### 浏览模式
- **用途**: 快速查阅所有知识点
- **交互**: 网格视图，点击跳转
- **评分**: 无评分功能

## 完整示例

### 示例 1：古诗词学习
```javascript
const cards = [
  {
    id: "1",
    category: `唐诗`,
    question: `《滕王阁序》的作者是谁？`,
    answer: `唐代诗人王勃，字子安，与杨炯、卢照邻、骆宾王并称「初唐四杰」`,
    difficulty: `medium`
  },
  {
    id: "2",
    category: `名句`,
    question: `「落霞与孤鹜齐飞」的下一句？`,
    answer: `秋水共长天一色`,
    difficulty: `easy`
  }
];
```

### 示例 2：数学概念
```javascript
const cards = [
  {
    id: "1",
    category: `乘法概念`,
    question: `什么是乘法？`,
    answer: `乘法是相同数相加的简便方法。例如 3+3+3+3=12 可写成 3×4=12`,
    difficulty: `easy`
  },
  {
    id: "2",
    category: `乘法规律`,
    question: `任何数乘以 0 等于什么？`,
    answer: `任何数乘以 0 都等于 0，因为 0 个任何东西都是没有的`,
    difficulty: `easy`
  }
];
```

## 上下文传递

| 操作 | 从返回中提取 | 用于下一步 |
|------|-------------|-----------|
| 定义 cards 数组 | 所有卡片对象 | 渲染闪卡和测验 |
| 设置 currentMode | 当前模式字符串 | 切换界面显示 |
| 更新 currentIndex | 当前卡片索引 | 导航和进度显示 |
| 记录 progress | 用户评分数据 | 统计和复习计划 |

## 错误处理

1. **语法错误**: 遇到 Unexpected identifier → 检查是否正确使用反引号
2. **函数未定义**: ReferenceError → 确认所有 onclick 函数都已定义
3. **数据缺失**: 页面空白 → 检查 cards 数组是否正确初始化
4. **样式异常**: UI 错乱 → 确认 CDN 资源加载成功

## 最佳实践

1. **卡片设计原则**
   - 一问一答，单一知识点
   - 问题清晰无歧义
   - 答案简洁但完整
   - 合理使用分类标签

2. **用户体验优化**
   - 提供进度指示
   - 实现键盘快捷键
   - 添加鼓励性反馈
   - 保持界面简洁

3. **内容组织建议**
   - 按主题或难度分类
   - 每组 20-50 张卡片为宜
   - 定期复习和更新
   - 收集用户反馈改进

## 详细参考

- [templates/modern.html](./templates/modern.html) - 现代风格模板源码
- [templates/classical.html](./templates/classical.html) - 古典风格模板源码
- [examples/vocabulary.html](./examples/vocabulary.html) - 词汇学习完整示例
- [examples/history.html](./examples/history.html) - 历史知识完整示例
- [examples/science.html](./examples/science.html) - 科学知识完整示例
