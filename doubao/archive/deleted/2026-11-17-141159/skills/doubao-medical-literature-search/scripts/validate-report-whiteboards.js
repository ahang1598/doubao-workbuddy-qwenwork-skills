#!/usr/bin/env node

const fs = require("fs");

const usage = `用法：
  node scripts/validate-report-whiteboards.js <report.xml>

检查 <whiteboard type="mermaid"> 白板中的 XML/HTML 片段和可能导致飞书解析失败的 Mermaid 语法，并检查禁用的上标、ref 标签及可见模板指令。
本脚本只接受飞书文档 XML：允许前置注释，但首个元素必须是 <title>。PPT 或幻灯片 XML 应使用对应的交付校验流程。
允许 citation 组件；不检查内部工具名、文献标题或章节标题是否带链接，也不校验参考文献表。用户指定自适应结构时，可以按需省略章节和 Mermaid 白板。`;

if (process.argv.includes("--help") || process.argv.includes("-h")) {
  console.log(usage);
  process.exit(0);
}

const file = process.argv[2];
if (!file) {
  console.error(usage);
  process.exit(2);
}
let xml;
try {
  xml = fs.readFileSync(file, "utf8");
} catch (error) {
  console.error(`读取报告 XML 失败：${error.message}`);
  process.exit(2);
}

const rootTagMatch = xml.match(
  /^\s*(?:<\?xml[\s\S]*?\?>\s*)?(?:<!--[\s\S]*?-->\s*)*<([A-Za-z][A-Za-z0-9:_-]*)\b/,
);
const rootTag = rootTagMatch
  ? rootTagMatch[1].split(":").pop().toLowerCase()
  : "";
if (["presentation", "slides", "slide", "deck", "ppt"].includes(rootTag)) {
  console.error(
    `输入文件的根元素 <${rootTag}> 表明这是 PPT 或幻灯片 XML。本脚本只接受飞书文档 XML；不要为了通过校验而修改章节名或重复添加链接，请改用 PPT 交付校验流程。`,
  );
  process.exit(2);
}
if (rootTag !== "title") {
  console.error(
    `飞书文档 XML 在可选前置注释之后必须以 <title> 作为首个元素；当前识别到 ${rootTag ? `<${rootTag}>` : "无法识别的根元素"}。生成 XML 前请先读取 assets/feishu-doc-template.xml。`,
  );
  process.exit(2);
}

const whiteboardPattern = /<whiteboard\b(?=[^>]*\btype=["']mermaid["'])[^>]*>([\s\S]*?)<\/whiteboard>/gi;
const diagramHeaderPattern = /^(graph|flowchart|sequenceDiagram|stateDiagram(?:-v2)?|classDiagram|erDiagram|journey|gantt|pie|mindmap|timeline|quadrantChart)\b/;
const xmlTagPattern = /<\/?[A-Za-z][^>]*>/;
const invalidLightColorPattern = /\b(?:fill|stroke|color|background(?:-color)?)\s*:\s*#?light-(?:blue|green|yellow|orange|red)\b/i;
const invalidHexPattern = /\b(?:fill|stroke|color|background(?:-color)?)\s*:\s*#(?![0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?\b)[A-Za-z0-9_-]+/i;
const escapedHtmlBreakPattern = /&lt;\s*br\b/i;
const markdownFencePattern = /```/;
const forbiddenSupPattern = /(?:<|&(?:amp;)*lt;|&(?:amp;)*#0*60;|&(?:amp;)*#x0*3c;|＜)\s*\/?\s*sup\b/i;
const forbiddenRefTagPattern = /(?:<|&(?:amp;)*lt;|&(?:amp;)*#0*60;|&(?:amp;)*#x0*3c;|＜)\s*\/?\s*ref\b/i;
const superscriptStylePattern = /\b(?:vertical-align|baseline-shift|font-variant-position)\s*[:=]\s*["']?\s*super\b/i;
const visibleTemplateInstructionPattern = /正文引用链接要求|本节图表要求|参考文献链接要求|写法要求|生成说明|要求：正文页提及|所有\s+G\/SR\/R\/N\s+节点必须/;

function lineNumberAt(offset) {
  return xml.slice(0, offset).split(/\r?\n/).length;
}

function firstMeaningfulLine(content) {
  return content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find((line) => line && !line.startsWith("%%"));
}

function stripXmlComments(content) {
  return content.replace(/<!--[\s\S]*?-->/g, " ");
}

let failures = 0;
let count = 0;
let match;
const visibleXml = stripXmlComments(xml);

if (forbiddenSupPattern.test(xml) || superscriptStylePattern.test(xml)) {
  failures += 1;
  console.error("报告 XML 包含原始、转义或样式化的上标标记；请删除并改用正文中的可点击来源名称或普通引用编号。citation 组件仍可保留。");
}

if (forbiddenRefTagPattern.test(xml)) {
  failures += 1;
  console.error("报告 XML 包含原始或转义后的 ref 标签；请改用可点击来源名称、允许的 citation 组件或普通引用编号。");
}

const visibleInstructionMatch = visibleTemplateInstructionPattern.exec(visibleXml);
if (visibleInstructionMatch) {
  failures += 1;
  console.error(`报告 XML 向用户展示了模板指令“${visibleInstructionMatch[0]}”；请删除模板或 QA 提示，只保留临床或文献内容。`);
}

while ((match = whiteboardPattern.exec(xml)) !== null) {
  count += 1;
  const fullBlock = match[0];
  const content = match[1];
  const blockLine = lineNumberAt(match.index);
  const firstLine = firstMeaningfulLine(content);

  const problems = [];
  if (!firstLine || !diagramHeaderPattern.test(firstLine)) {
    problems.push("首个非空行必须是 Mermaid 图声明，例如 mindmap、timeline 或 flowchart TD");
  }
  if (xmlTagPattern.test(content)) {
    problems.push("Mermaid 白板内容包含原始 XML/HTML 标签；请删除 <br/>、<span>、<b> 等标签，并使用纯文本节点");
  }
  if (escapedHtmlBreakPattern.test(content)) {
    problems.push("Mermaid 白板内容包含转义后的 HTML 换行标签；请将长文本拆分为多个节点");
  }
  if (invalidLightColorPattern.test(content)) {
    problems.push("Mermaid 样式使用了 light-yellow 等飞书 callout 颜色名；请改用十六进制颜色或删除样式行");
  }
  if (invalidHexPattern.test(content)) {
    problems.push("Mermaid 样式包含无效的十六进制颜色");
  }
  if (markdownFencePattern.test(fullBlock)) {
    problems.push("白板块中不得包含 Markdown 代码围栏");
  }

  if (problems.length > 0) {
    failures += 1;
    console.error(`第 ${count} 个白板在第 ${blockLine} 行附近存在问题：`);
    problems.forEach((problem) => console.error(`  - ${problem}`));
  }
}

if (failures > 0) {
  console.error(`报告 XML 校验未通过：共发现 ${failures} 个问题；已检查 ${count} 个 Mermaid 白板块。`);
  process.exit(1);
}

console.log(`白板校验通过：已检查 ${count} 个 Mermaid 白板块。`);
