# 输出模板

> 详细模板文件：[templates/resume_template.md](../templates/resume_template.md)、[templates/resume-template.html](../templates/resume-template.html)、[templates/interview_prep_template.md](../templates/interview_prep_template.md)

## 简历输出格式规范

### Markdown 格式要求

- 章节标题使用二级标题（##）
- 列表项使用短横线（-）
- 关键信息可适当加粗
- 控制在1-2页内容量

### 简历文件命名

```
{姓名}_{目标岗位}_简历.pdf
```

### 简历输出提示语

完成 HTML 简历输出后，必须提示用户：

1. 浏览器中按 `Ctrl+P`（Mac: `Cmd+P`）导出 PDF
2. 可根据不同岗位定制简历内容
3. 如需调整排版，说"收紧"/"放宽"即可微调

## HTML 简历输出格式规范

### 设计风格

- **简约现代**：蓝白配色（主色 `#2563eb`），白色背景，深灰文字
- **字体**：系统字体栈（PingFang SC / Microsoft YaHei / sans-serif）
- **布局**：单列居中，max-width 800px，padding 48px 56px
- **打印**：`@media print` + `print-color-adjust: exact` 保证背景色不丢失

### HTML 结构规范

```html
<div class="resume">
  <div class="header">
    <h1>姓名</h1>
    <div class="contact">联系方式</div>
    <div class="intent">求职意向</div>
  </div>
  <div class="section">
    <div class="section-title">教育背景</div>
    <div class="entry">...</div>
  </div>
  <div class="section">
    <div class="section-title">工作经历</div>
    <div class="entry">...</div>
  </div>
  <div class="section">
    <div class="section-title">技能</div>
    <div class="skills-grid">...</div>
  </div>
</div>
```

### 排版调整指令

| 用户说 | 调整项                | 具体修改                                              |
| ------ | --------------------- | ----------------------------------------------------- |
| "收紧" | padding + line-height | `.resume { padding: 36px 40px }` + `line-height: 1.5` |
| "放宽" | padding               | `.resume { padding: 56px 64px }`                      |
| "紧凑" | font-size + margin    | 字号缩小1px，间距缩小4px                              |

### 导出 PDF 流程

1. 将 HTML 文件写入当前工作目录（或 outputs 目录）并通过 `present_files` 呈现给用户
2. 提示用户在浏览器中打开该 HTML 文件
3. 提示用户：`Ctrl+P` / `Cmd+P` → 选择"另存为PDF" → 保存
4. 打印设置建议：边距选"无"，勾选"背景图形"

## 面试准备文档输出格式

### 文档结构

```markdown
# 面试准备 - {目标岗位}

## 一、技术知识点复习清单

### {技术领域1}

**必会基础** ⭐⭐⭐

- [ ] 知识点1
- [ ] 知识点2

**进阶考点** ⭐⭐

- [ ] 知识点3

**深入理解** ⭐

- [ ] 知识点4

## 二、模拟面试题

### A. 技术基础题

#### 问题1：{问题描述}

**考察点**：...
**参考要点**：1. ... 2. ... 3. ...
**常见误区**：❌ ... ❌ ...
**难度**：⭐⭐

### B. 实践应用题

...

### C. 情景分析题

...

## 三、行为面试题

### 问题1：{问题描述}

**考察维度**：...
**STAR框架**：S → T → A → R
**优秀回答示例**：...

## 四、常见问题准备

1. 自我介绍
2. 优缺点
3. 离职原因
4. 职业规划

## 五、反问面试官的问题

...
```

## 优化建议输出格式

### 整体结构

```markdown
# 简历优化报告

## 整体评价

{一句话总结}

## 改进建议

### 高优先级

1. {建议}
2. {建议}

### 中优先级

1. {建议}

### 低优先级

1. {建议}

## 修改对比版

{原内容与修改后内容的对比，使用~~删除线~~和**加粗**标注}

## 最终优化版

{完整的优化后简历}
```
