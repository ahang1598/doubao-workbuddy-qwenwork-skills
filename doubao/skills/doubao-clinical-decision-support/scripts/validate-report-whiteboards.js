#!/usr/bin/env node

const fs = require("fs");

const usage = `用法：
  node scripts/validate-report-whiteboards.js <report.xml>

检查报告 XML、Markdown 或 PPT XML 中的重复标题、callout 非法 type 属性、禁用的上标或 ref 标签、证据章节链接风险、citation 组件，以及 Mermaid 白板缺失、源码外露和常见语法错误。不检查内部工具名、附件状态或参考文献表。若证据章节被提示，请检查该章提及的指南、共识、论文、试验、说明书或监管来源是否均有可点击链接。`;

if (process.argv.includes("--help") || process.argv.includes("-h")) {
  console.log(usage);
  process.exit(0);
}

const positionalArgs = [];

for (let index = 2; index < process.argv.length; index += 1) {
  const arg = process.argv[index];
  if (arg === "--attachments") {
    index += 1;
    continue;
  }
  if (arg.startsWith("--attachments=")) {
    continue;
  }
  positionalArgs.push(arg);
}

const file = positionalArgs[0];
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

const whiteboardPattern = /<whiteboard\b[^>]*\btype=["']mermaid["'][^>]*>([\s\S]*?)<\/whiteboard>/gi;
const mermaidWhiteboardBlockPattern = /<whiteboard\b[^>]*\btype=["']mermaid["'][^>]*>[\s\S]*?<\/whiteboard>/gi;
const diagramHeaderPattern = /^(graph|flowchart|sequenceDiagram|stateDiagram(?:-v2)?|classDiagram|erDiagram|journey|gantt|pie|mindmap|timeline|quadrantChart)\b/;
const xmlTagPattern = /<\/?[A-Za-z][^>]*>/;
const invalidLightColorPattern = /\b(?:fill|stroke|color|background(?:-color)?)\s*:\s*#?light-(?:blue|green|yellow|orange|red)\b/i;
const invalidHexPattern = /\b(?:fill|stroke|color|background(?:-color)?)\s*:\s*#(?![0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?\b)[A-Za-z0-9_-]+/i;
const escapedHtmlBreakPattern = /&lt;\s*br\b/i;
const markdownFencePattern = /```/;
const literalBackslashNewlinePattern = /\\n/;
const codeBlockTagPattern = /<(?:pre|code|codeblock|code-block)\b/i;
const rawMermaidDeclarationPattern = /(?:^|\r?\n)\s*(?:graph|flowchart)\s+(?:TD|TB|BT|RL|LR)\b/im;
const forbiddenSupPattern = /(?:<\/?sup\b[^>]*>|&lt;\s*\/?\s*sup\b[^&]*(?:&gt;)?|\bsuperscript\b|vertical-align\s*:\s*super)/i;
const forbiddenRefTagPattern = /(?:<\/?ref\b[^>]*>|&(?:amp;)*lt;\s*\/?\s*ref\b[^&]*(?:&(?:amp;)*gt;)?|&(?:amp;)*#0*60;\s*\/?\s*ref\b[^&]*(?:&(?:amp;)*#0*62;)?|&(?:amp;)*#x0*3c;\s*\/?\s*ref\b[^&]*(?:&(?:amp;)*#x0*3e;)?)/i;
const titleTagPattern = /<title\b[^>]*>[\s\S]*?<\/title>/gi;
const unsupportedCalloutTypePattern = /<callout\b[^>]*\btype\s*=\s*["'][^"']*["'][^>]*>/gi;
const visibleTemplateInstructionPattern = /本节目标|图表要求|正文来源写法|正文引用必须|正文引用格式示例|生成\s*docx\s*时|不得把研究名写成无链接小标题|不得把指南\/共识名写成无链接小标题|除非用户明确要求特定参考文献格式|不得写成直接医嘱/;
const citationComponentPattern = /<cite\b[^>]*\btype=["']citation["'][^>]*>[\s\S]*?<\/cite>/gi;
const unresolvedPlaceholderPattern = /\{\{[^}]+\}\}/;
const clickableEvidenceLinkPattern = /(?:<a\b[^>]*\bhref=["']https?:\/\/[^"']+["'][^>]*>[\s\S]*?<\/a>|<bookmark\b[^>]*\bhref=["']https?:\/\/[^"']+["'][^>]*>|\]\(https?:\/\/[^)]+\))/i;
const clickableEvidenceLinkGlobalPattern = /(?:<a\b[^>]*\bhref=["']https?:\/\/[^"']+["'][^>]*>[\s\S]*?<\/a>|<bookmark\b[^>]*\bhref=["']https?:\/\/[^"']+["'][^>]*>|\]\(https?:\/\/[^)]+\))/gi;
function plainText(value) {
  return value
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function stripXmlComments(value) {
  return value.replace(/<!--[\s\S]*?-->/g, (match) => match.replace(/[^\r\n]/g, " "));
}

function headingSection(content, headingPattern) {
  const xmlMatches = [...content.matchAll(/<h1\b[^>]*>[\s\S]*?<\/h1>/gi)];
  for (let index = 0; index < xmlMatches.length; index += 1) {
    const match = xmlMatches[index];
    if (headingPattern.test(plainText(match[0]))) {
      const start = match.index;
      const end = index + 1 < xmlMatches.length ? xmlMatches[index + 1].index : content.length;
      return content.slice(start, end);
    }
  }

  const markdownMatches = [...content.matchAll(/^\s*#{1,2}\s+(.+)$/gim)];
  for (let index = 0; index < markdownMatches.length; index += 1) {
    const match = markdownMatches[index];
    if (headingPattern.test(plainText(match[1]))) {
      const start = match.index;
      const end = index + 1 < markdownMatches.length ? markdownMatches[index + 1].index : content.length;
      return content.slice(start, end);
    }
  }

  return "";
}

function stripMermaidWhiteboards(content) {
  return content.replace(mermaidWhiteboardBlockPattern, " ");
}

function hasHeading(content, headingPattern) {
  const xmlHeadings = [...content.matchAll(/<h[1-6]\b[^>]*>[\s\S]*?<\/h[1-6]>/gi)];
  if (xmlHeadings.some((match) => headingPattern.test(plainText(match[0])))) {
    return true;
  }
  const markdownHeadings = [...content.matchAll(/^\s*#{1,6}\s+(.+)$/gim)];
  return markdownHeadings.some((match) => headingPattern.test(plainText(match[1])));
}

function countClickableEvidenceLinks(content) {
  return (content.match(clickableEvidenceLinkGlobalPattern) || []).length;
}

function validateBodyEvidenceLinks(content) {
  const problems = [];
  const body = stripMermaidWhiteboards(content);

  const sectionSpecs = [
    { label: "指南与共识证据", pattern: /指南|共识/, minLinks: 3 },
    { label: "关键研究证据", pattern: /关键研究|研究证据|论文证据/, minLinks: 3 },
  ];

  sectionSpecs.forEach(({ label, pattern, minLinks }) => {
    const section = headingSection(body, pattern);
    if (!section) {
      problems.push(`未找到“${label}”章节；请确认需要的证据章节存在，并为其中引用的来源添加可点击链接`);
      return;
    }
    const linkCount = countClickableEvidenceLinks(section);
    if (linkCount < minLinks) {
      problems.push(`“${label}”章节可能存在未添加超链接的关键文献；请检查该章提及的指南、共识、论文、试验或其他来源，并补充可点击链接（当前识别到 ${linkCount} 个来源链接）`);
    }
  });

  return problems;
}

function validateCitationComponents(content) {
  const problems = [];
  const components = [...content.matchAll(citationComponentPattern)];
  components.forEach((match, index) => {
    if (!clickableEvidenceLinkPattern.test(match[0])) {
      problems.push(`第 ${index + 1} 个 citation 组件必须包含可点击的来源链接`);
    }
  });
  return problems;
}

function lineNumberAt(offset) {
  return xml.slice(0, offset).split(/\r?\n/).length;
}

function firstMeaningfulLine(content) {
  return content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find((line) => line && !line.startsWith("%%"));
}

let failures = 0;
let count = 0;
let match;
const visibleXml = stripXmlComments(xml);
const visibleOutsideWhiteboards = stripMermaidWhiteboards(visibleXml);
const expectedDiagramWhiteboards = [
  { label: "临床决策逻辑图", pattern: /决策逻辑图/ },
].filter(({ pattern }) => hasHeading(visibleXml, pattern));
const actualDiagramWhiteboardCount = [...visibleXml.matchAll(whiteboardPattern)].length;

if (expectedDiagramWhiteboards.length > actualDiagramWhiteboardCount) {
  failures += 1;
  console.error(`报告包含 ${expectedDiagramWhiteboards.length} 个 Mermaid 图标题，但只有 ${actualDiagramWhiteboardCount} 个 <whiteboard type="mermaid"> 白板块。请将图表保留在白板容器中，不要替换为代码块。`);
  expectedDiagramWhiteboards.forEach(({ label }) => console.error(`  - 缺少对应白板：${label}`));
}

const exposedFenceMatch = markdownFencePattern.exec(visibleOutsideWhiteboards);
const exposedCodeBlockMatch = codeBlockTagPattern.exec(visibleOutsideWhiteboards);
const exposedRawMermaidMatch = rawMermaidDeclarationPattern.exec(visibleOutsideWhiteboards);
if (exposedFenceMatch || exposedCodeBlockMatch || exposedRawMermaidMatch) {
  failures += 1;
  const reason = exposedFenceMatch
    ? "Markdown 代码围栏"
    : exposedCodeBlockMatch
      ? "代码块标签"
      : "裸露的 Mermaid 声明";
  console.error(`报告在 Mermaid 白板外暴露了图表或 XML 源码（${reason}）；请使用 <whiteboard type="mermaid">，或改用面向读者的表格、列表。`);
}

const titleTags = [...visibleXml.matchAll(titleTagPattern)];
if (titleTags.length > 1) {
  failures += 1;
  console.error(`报告包含 ${titleTags.length} 个 <title> 标签；只能保留一个标题来源。XML 已包含 <title> 时，不要再向 lark-cli docs +create 传入 --title。`);
}

const unsupportedCalloutTypes = [...visibleXml.matchAll(unsupportedCalloutTypePattern)];
if (unsupportedCalloutTypes.length > 0) {
  failures += 1;
  console.error(`报告包含 ${unsupportedCalloutTypes.length} 个带有不支持的 type 属性的 <callout> 标签；请使用 <callout emoji="x" background-color="light-yellow">，不要添加 type。`);
}

if (forbiddenSupPattern.test(xml)) {
  failures += 1;
  console.error("报告包含上标标签或转义后的上标标记；请改用正文中的可点击来源名称或普通引用编号。");
}

if (forbiddenRefTagPattern.test(xml)) {
  failures += 1;
  console.error("报告包含原始或转义后的 ref 标签；请改用可点击来源名称、允许的 citation 组件或普通引用编号。");
}

const visibleInstructionMatch = visibleTemplateInstructionPattern.exec(visibleXml);
if (visibleInstructionMatch) {
  failures += 1;
  console.error(`报告向用户展示了模板指令“${visibleInstructionMatch[0]}”；请删除模板或 QA 提示，只保留临床内容。`);
}

const citationProblems = validateCitationComponents(xml);
if (citationProblems.length > 0) {
  failures += 1;
  console.error("citation 组件校验未通过：");
  citationProblems.forEach((problem) => console.error(`  - ${problem}`));
}

if (unresolvedPlaceholderPattern.test(xml)) {
  failures += 1;
  const placeholder = unresolvedPlaceholderPattern.exec(xml)[0];
  console.error(`报告仍包含未替换的模板占位符 ${placeholder}；交付前请替换为真实内容和链接。`);
}

const looksLikeSlides = /<slide\b|<presentation\b|<deck\b|<ppt\b/i.test(xml);
if (!looksLikeSlides) {
  const bodyLinkProblems = validateBodyEvidenceLinks(xml);
  if (bodyLinkProblems.length > 0) {
    failures += 1;
    console.error("正文证据链接校验未通过：");
    bodyLinkProblems.forEach((problem) => console.error(`  - ${problem}`));
  }
}

while ((match = whiteboardPattern.exec(visibleXml)) !== null) {
  count += 1;
  const fullBlock = match[0];
  const content = match[1];
  const blockLine = lineNumberAt(match.index);
  const firstLine = firstMeaningfulLine(content);
  const isMindmap = /^mindmap\b/.test(firstLine || "");

  if (isMindmap) {
    continue;
  }

  const problems = [];
  if (!firstLine || !diagramHeaderPattern.test(firstLine)) {
    problems.push("首个非空行必须是 Mermaid 图声明，例如 mindmap 或 flowchart TD");
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
  if (literalBackslashNewlinePattern.test(content)) {
    problems.push("Mermaid 节点文字包含字面量 \\n；请使用简短的单行标签，或把内容拆分为多个节点");
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

if (count === 0) {
  console.log("报告 XML 校验通过：未发现禁用的上标或 ref 标签；文档中没有 Mermaid 白板块。");
  process.exit(0);
}

console.log(`报告 XML 校验通过：未发现禁用的上标或 ref 标签；已检查 ${count} 个 Mermaid 白板块。`);
