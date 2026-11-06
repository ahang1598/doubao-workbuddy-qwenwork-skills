#!/usr/bin/env node

/**
 * Markdown 转 HTML 转换脚本
 * 用于将深度研究报告转换为美观的 HTML 页面
 *
 * 用法：
 *   node md2html.js <input.md> [output.html]
 *   node md2html.js report.md                    # 输出到 report.html
 *   node md2html.js report.md output.html        # 指定输出文件
 *   node md2html.js report.md --theme dark       # 使用深色主题
 */

const fs = require('fs');
const path = require('path');

// AgentServer starts each exec in the current task workspace. Keep report artifacts there;
// XIAOYI_REPORTS_ROOT is retained as an explicit override for compatible runtimes.
const REPORTS_ROOT = path.resolve(process.env.XIAOYI_REPORTS_ROOT || path.join(process.cwd(), 'reports'));

function fail(message) {
  console.error(`错误：${message}`);
  process.exit(1);
}

function isWithinDirectory(candidatePath, allowedRoot) {
  const relative = path.relative(allowedRoot, candidatePath);
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

function resolveAllowedInputPath(inputFile) {
  const absoluteInputPath = path.resolve(inputFile);

  if (path.extname(absoluteInputPath) !== '.md') {
    fail('只允许读取 .md 文件');
  }

  if (!fs.existsSync(absoluteInputPath)) {
    fail('文件不存在: ' + inputFile);
  }

  const realInputPath = fs.realpathSync(absoluteInputPath);

  if (!isWithinDirectory(realInputPath, REPORTS_ROOT)) {
    fail('输入文件必须位于允许目录内: ' + REPORTS_ROOT);
  }

  return realInputPath;
}

function resolveAllowedOutputPath(outputFile) {
  const absoluteOutputPath = path.resolve(outputFile);
  const outputDir = path.dirname(absoluteOutputPath);

  if (!fs.existsSync(outputDir)) {
    fail('输出目录不存在: ' + outputDir);
  }

  const realOutputDir = fs.realpathSync(outputDir);

  if (!isWithinDirectory(realOutputDir, REPORTS_ROOT)) {
    fail('输出文件必须位于允许目录内: ' + REPORTS_ROOT);
  }

  return path.join(realOutputDir, path.basename(absoluteOutputPath));
}

// 主题配置
const themes = {
  light: {
    bodyBg: '#ffffff',
    text: '#1a1a1a',
    heading: '#1a1a1a',
    link: '#2563eb',
    linkHover: '#1d4ed8',
    code: '#f3f4f6',
    codeText: '#1f2937',
    blockquote: '#f9fafb',
    blockquoteBorder: '#d1d5db',
    muted: '#666666',
    tableHeader: '#f9fafb',
    tableBorder: '#e5e7eb',
    tableStripe: '#fafafa',
    tableHover: '#f0f4ff',
    hr: '#e5e7eb',
    shadow: 'rgba(0, 0, 0, 0.1)',
    scrollHint: 'rgba(0, 0, 0, 0.08)',
    footer: '#888888'
  },
  dark: {
    bodyBg: '#1a1a1a',
    text: '#e5e5e5',
    heading: '#ffffff',
    link: '#60a5fa',
    linkHover: '#93c5fd',
    code: '#2d2d2d',
    codeText: '#e5e5e5',
    blockquote: '#2d2d2d',
    blockquoteBorder: '#4a4a4a',
    muted: '#b3b3b3',
    tableHeader: '#2d2d2d',
    tableBorder: '#4a4a4a',
    tableStripe: '#222222',
    tableHover: '#2d2d3d',
    hr: '#4a4a4a',
    shadow: 'rgba(0, 0, 0, 0.3)',
    scrollHint: 'rgba(255, 255, 255, 0.06)',
    footer: '#9ca3af'
  }
};

/**
 * 逐行解析 Markdown，正确处理表格等块级元素
 */
function parseMarkdown(md) {
  const lines = md.split('\n');
  const output = [];
  let i = 0;

  // 辅助：对文本进行行内格式化
  function inlineFormat(text) {
    // 转义 HTML
    text = text.replace(/&/g, '&amp;');
    text = text.replace(/</g, '&lt;');
    text = text.replace(/>/g, '&gt;');
    // 图片（必须在链接之前）
    text = text.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1">');
    // 链接
    text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
    // 行内代码
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
    // 粗斜体
    text = text.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
    text = text.replace(/___(.+?)___/g, '<strong><em>$1</em></strong>');
    // 粗体
    text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/__(.+?)__/g, '<strong>$1</strong>');
    // 斜体
    text = text.replace(/\*(.+?)\*/g, '<em>$1</em>');
    text = text.replace(/_(.+?)_/g, '<em>$1</em>');
    return text;
  }

  // 判断是否为表格行
  function isTableRow(line) {
    return /^\|.+\|$/.test(line.trim());
  }

  // 判断是否为分隔行
  function isSeparatorRow(line) {
    const trimmed = line.trim().replace(/^\|/, '').replace(/\|$/, '');
    return trimmed.split('|').every(c => /^\s*[-:]+\s*$/.test(c));
  }

  // 解析表格行的单元格
  function parseCells(line) {
    return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim());
  }

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // --- 空行 ---
    if (trimmed === '') {
      i++;
      continue;
    }

    // --- 代码块 ---
    if (trimmed.startsWith('```')) {
      const lang = trimmed.slice(3).trim();
      const codeLines = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        // 转义 HTML
        codeLines.push(
          lines[i].replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        );
        i++;
      }
      i++; // 跳过结束的 ```
      output.push(`<pre><code class="language-${lang}">${codeLines.join('\n')}</code></pre>`);
      continue;
    }

    // --- 表格（关键修复：逐块收集连续的表格行）---
    if (isTableRow(trimmed)) {
      const tableRows = [];
      while (i < lines.length && isTableRow(lines[i].trim())) {
        tableRows.push(lines[i].trim());
        i++;
      }

      // 至少需要 2 行（表头 + 分隔行）才算有效表格
      if (tableRows.length >= 2 && isSeparatorRow(tableRows[1])) {
        const headerCells = parseCells(tableRows[0]);
        const headerHtml = headerCells.map(c => `<th>${inlineFormat(c)}</th>`).join('');

        const bodyRows = tableRows.slice(2); // 跳过表头和分隔行
        const bodyHtml = bodyRows.map(row => {
          const cells = parseCells(row);
          return '<tr>' + cells.map(c => `<td>${inlineFormat(c)}</td>`).join('') + '</tr>';
        }).join('\n');

        output.push(
          '<div class="table-wrapper">' +
          '<table>' +
          `<thead><tr>${headerHtml}</tr></thead>` +
          `<tbody>${bodyHtml}</tbody>` +
          '</table>' +
          '</div>'
        );
      } else {
        // 不是有效表格，当普通文本处理
        tableRows.forEach(row => {
          output.push(`<p>${inlineFormat(row)}</p>`);
        });
      }
      continue;
    }

    // --- 标题 ---
    const headingMatch = trimmed.match(/^(#{1,6})\s+(.+)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      output.push(`<h${level}>${inlineFormat(headingMatch[2])}</h${level}>`);
      i++;
      continue;
    }

    // --- 水平线 ---
    if (/^(---+|\*\*\*+|___+)$/.test(trimmed)) {
      output.push('<hr>');
      i++;
      continue;
    }

    // --- 引用块 ---
    if (trimmed.startsWith('> ') || trimmed === '>') {
      const quoteLines = [];
      while (i < lines.length && (lines[i].trim().startsWith('> ') || lines[i].trim() === '>')) {
        quoteLines.push(lines[i].trim().replace(/^>\s?/, ''));
        i++;
      }
      output.push(`<blockquote>${quoteLines.map(l => inlineFormat(l)).join('<br>')}</blockquote>`);
      continue;
    }

    // --- 无序列表 ---
    if (/^[-*+]\s+/.test(trimmed)) {
      const listItems = [];
      while (i < lines.length && /^[-*+]\s+/.test(lines[i].trim())) {
        listItems.push(lines[i].trim().replace(/^[-*+]\s+/, ''));
        i++;
      }
      output.push('<ul>' + listItems.map(item => `<li>${inlineFormat(item)}</li>`).join('') + '</ul>');
      continue;
    }

    // --- 有序列表 ---
    if (/^\d+\.\s+/.test(trimmed)) {
      const listItems = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        listItems.push(lines[i].trim().replace(/^\d+\.\s+/, ''));
        i++;
      }
      output.push('<ol>' + listItems.map(item => `<li>${inlineFormat(item)}</li>`).join('') + '</ol>');
      continue;
    }

    // --- 普通段落 ---
    output.push(`<p>${inlineFormat(trimmed)}</p>`);
    i++;
  }

  return output.join('\n');
}

// 生成 HTML 页面
function generateHtml(markdown, options = {}) {
  const theme = themes[options.theme || 'light'];
  const title = options.title || '深度研究报告';
  const content = parseMarkdown(markdown);

  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title}</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans SC", sans-serif;
      line-height: 1.8;
      color: ${theme.text};
      background-color: ${theme.bodyBg};
      padding: 40px 20px;
    }

    .container {
      max-width: 900px;
      margin: 0 auto;
      background: ${theme.bodyBg};
      padding: 40px 60px;
      box-shadow: 0 4px 20px ${theme.shadow};
      border-radius: 12px;
    }

    /* 标题 */
    h1, h2, h3, h4, h5, h6 {
      color: ${theme.heading};
      margin: 1.5em 0 0.8em;
      font-weight: 600;
      line-height: 1.3;
    }

    h1 {
      font-size: 2.2em;
      border-bottom: 3px solid ${theme.link};
      padding-bottom: 0.3em;
      margin-bottom: 1em;
    }

    h2 {
      font-size: 1.6em;
      border-bottom: 1px solid ${theme.hr};
      padding-bottom: 0.3em;
      margin-top: 2em;
    }

    h3 { font-size: 1.3em; color: ${theme.link}; }
    h4 { font-size: 1.1em; }

    p { margin: 1em 0; }

    a {
      color: ${theme.link};
      text-decoration: none;
      border-bottom: 1px solid transparent;
      transition: border-color 0.2s;
    }
    a:hover {
      color: ${theme.linkHover};
      border-bottom-color: ${theme.linkHover};
    }

    strong { font-weight: 600; }
    em { font-style: italic; }

    /* 引用 */
    blockquote {
      margin: 1.5em 0;
      padding: 15px 20px;
      background: ${theme.blockquote};
      border-left: 4px solid ${theme.blockquoteBorder};
      border-radius: 0 8px 8px 0;
      color: ${theme.muted};
    }
    blockquote p { margin: 0; }

    /* 代码 */
    pre {
      background: ${theme.code};
      padding: 20px;
      border-radius: 8px;
      overflow-x: auto;
      margin: 1.5em 0;
      font-size: 0.9em;
    }

    code {
      font-family: "Fira Code", "JetBrains Mono", Consolas, Monaco, monospace;
      background: ${theme.code};
      color: ${theme.codeText};
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.9em;
    }
    pre code { background: none; padding: 0; }

    /* 表格容器：横向滚动 */
    .table-wrapper {
      width: 100%;
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
      margin: 1.5em 0;
      border-radius: 8px;
      border: 1px solid ${theme.tableBorder};
      position: relative;
    }

    /* 表格本体 */
    table {
      width: 100%;
      min-width: 400px;
      border-collapse: collapse;
      font-size: 0.95em;
    }

    thead {
      position: sticky;
      top: 0;
      z-index: 1;
    }

    th {
      background: ${theme.tableHeader};
      font-weight: 600;
      white-space: nowrap;
      padding: 12px 16px;
      text-align: left;
      border-bottom: 2px solid ${theme.tableBorder};
    }

    td {
      padding: 10px 16px;
      text-align: left;
      border-bottom: 1px solid ${theme.tableBorder};
      word-break: break-word;
    }

    /* 斑马纹 */
    tbody tr:nth-child(even) {
      background: ${theme.tableStripe};
    }

    tbody tr:hover {
      background: ${theme.tableHover};
    }

    /* 列表 */
    ul, ol {
      margin: 1em 0;
      padding-left: 2em;
    }
    li { margin: 0.5em 0; }

    hr {
      border: none;
      border-top: 1px solid ${theme.hr};
      margin: 2em 0;
    }

    img {
      max-width: 100%;
      height: auto;
      border-radius: 8px;
      margin: 1em 0;
    }

    /* 页眉 */
    .report-header {
      text-align: center;
      padding: 20px 0 30px;
      border-bottom: 1px solid ${theme.hr};
      margin-bottom: 30px;
    }
    .report-header .author {
      font-size: 0.9em;
      color: ${theme.link};
      font-weight: 500;
    }
    .report-header .author-icon {
      margin-right: 8px;
    }

    /* 页脚 */
    .report-footer {
      text-align: center;
      padding: 30px 0 20px;
      border-top: 1px solid ${theme.hr};
      margin-top: 40px;
      color: ${theme.footer};
      font-size: 0.9em;
    }
    .report-footer .author {
      color: ${theme.link};
      font-weight: 500;
    }

    /* 打印 */
    @media print {
      body { padding: 0; background: white; color: black; }
      .container { box-shadow: none; padding: 0; max-width: 100%; }
      a { color: black; text-decoration: underline; }
      .table-wrapper { overflow: visible; border: none; }
      table { min-width: 0; font-size: 0.85em; }
      th, td { padding: 6px 8px; }
      .report-header, .report-footer { border-color: #ccc; }
    }

    /* 移动端适配 */
    @media (max-width: 768px) {
      body { padding: 10px 4px; }
      .container { padding: 16px 12px; }
      h1 { font-size: 1.6em; }
      h2 { font-size: 1.3em; }

      /* 表格移动端优化 */
      .table-wrapper {
        margin-left: -12px;
        margin-right: -12px;
        border-radius: 0;
        border-left: none;
        border-right: none;
        /* 滚动渐变提示 */
        background:
          linear-gradient(to right, ${theme.bodyBg} 30%, transparent),
          linear-gradient(to left, ${theme.bodyBg} 30%, transparent),
          linear-gradient(to right, ${theme.scrollHint}, transparent 30px),
          linear-gradient(to left, ${theme.scrollHint}, transparent 30px);
        background-position: left center, right center, left center, right center;
        background-size: 40px 100%, 40px 100%, 40px 100%, 40px 100%;
        background-repeat: no-repeat;
        background-attachment: local, local, scroll, scroll;
      }

      table {
        font-size: 0.85em;
      }

      th, td {
        padding: 8px 10px;
      }

      /* 固定首列 */
      th:first-child,
      td:first-child {
        position: sticky;
        left: 0;
        z-index: 1;
        background: ${theme.bodyBg};
        border-right: 2px solid ${theme.tableBorder};
      }
      th:first-child {
        background: ${theme.tableHeader};
        z-index: 2;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <header class="report-header">
      <div class="author"><span class="author-icon">🎨</span>小艺报告专家 · 内容由AI生成仅供参考</div>
    </header>
    ${content}
    <footer class="report-footer">
      <div class="author"><span class="author-icon">🎨</span>小艺报告专家 · 内容由AI生成仅供参考</div>
    </footer>
  </div>
  </body>
</html>`;
}

// 主函数
function main() {
  const args = process.argv.slice(2);

  if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
    console.log(`
Markdown 转 HTML 转换工具

用法：
  node md2html.js <input.md> [output.html] [options]

参数：
  input.md    输入的 Markdown 文件
  output.html 输出的 HTML 文件（可选，默认为 input.html）

选项：
  --theme <name>  主题: light (默认) 或 dark
  --title <title> 页面标题
  --help, -h      显示帮助信息

示例：
  node md2html.js report.md
  node md2html.js report.md output.html
  node md2html.js report.md --theme dark --title "研究报告"
`);
    process.exit(0);
  }

  // 解析参数
  let inputFile = null;
  let outputFile = null;
  let theme = 'light';
  let title = '深度研究报告';

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--theme') {
      theme = args[++i];
    } else if (args[i] === '--title') {
      title = args[++i];
    } else if (!args[i].startsWith('-')) {
      if (!inputFile) {
        inputFile = args[i];
      } else if (!outputFile) {
        outputFile = args[i];
      }
    }
  }

  if (!inputFile) {
    fail('请指定输入文件');
  }

  const safeInputFile = resolveAllowedInputPath(inputFile);

  if (!outputFile) {
    outputFile = safeInputFile.replace(/\.md$/, '.html');
  }

  const safeOutputFile = resolveAllowedOutputPath(outputFile);

  const markdown = fs.readFileSync(safeInputFile, 'utf-8');

  // 从文件内容提取标题
  const titleMatch = markdown.match(/^#\s+(.+)$/m);
  if (titleMatch) {
    title = titleMatch[1].replace(/[：:].*$/, '').trim();
  }

  const html = generateHtml(markdown, { theme, title });
  fs.writeFileSync(safeOutputFile, html, 'utf-8');

  console.log('✅ 转换完成！');
  console.log('   输入: ' + safeInputFile);
  console.log('   输出: ' + safeOutputFile);
  console.log('   主题: ' + theme);
}

main();
