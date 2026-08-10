#!/usr/bin/env node

const fs = require("fs");

const usage = `Usage:
  node scripts/validate-report-whiteboards.js <report.xml>

Checks <whiteboard type="mermaid"> blocks for XML/HTML fragments and Mermaid syntax patterns that commonly make Feishu whiteboard parsing fail.
This validator accepts Feishu document XML only: after optional leading comments, the first element must be <title>. PPT/slide XML must use its own delivery validation.
It also checks hard report rules: no raw, encoded, or style-based HTML superscript markup; citation components remain allowed. It checks displayed internal search tool names, raw "tool" columns, and final reference tables using 标题/来源/类型/年份/链接 with source-link coverage. It does not inspect whether literature titles or chapter headings themselves are hyperlinks. Report chapters and Mermaid whiteboards may be omitted when the document follows a user-specified adaptive structure.`;

if (process.argv.includes("--help") || process.argv.includes("-h")) {
  console.log(usage);
  process.exit(0);
}

const file = process.argv[2];
if (!file) {
  console.error(usage);
  process.exit(2);
}
const isTemplateFile = /template/i.test(file);

let xml;
try {
  xml = fs.readFileSync(file, "utf8");
} catch (error) {
  console.error(`Failed to read report XML: ${error.message}`);
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
    `Input root <${rootTag}> identifies PPT/slide XML. This validator only accepts Feishu document XML; do not rename chapters or add duplicate links to satisfy it. Validate this file through the PPT delivery workflow instead.`,
  );
  process.exit(2);
}
if (rootTag !== "title") {
  console.error(
    `Feishu document XML must use <title> as the first element after optional leading comments; found ${rootTag ? `<${rootTag}>` : "no recognizable root element"}. Read assets/feishu-doc-template.xml before generating the XML.`,
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
const superscriptStylePattern = /\b(?:vertical-align|baseline-shift|font-variant-position)\s*[:=]\s*["']?\s*super\b/i;
const internalSearchToolPattern = /\b(?:medical_search|scholar_search|general_search|[A-Za-z][A-Za-z0-9-]*_search)\b/;
const rawToolColumnPattern = /(?:^|[>\s])tool(?:[<\s]|$)/i;
const visibleTemplateInstructionPattern = /正文引用链接要求|本节图表要求|参考文献链接要求|写法要求|生成说明|要求：正文页提及|所有\s+G\/SR\/R\/N\s+节点必须/;
const referenceHeadingPattern = /<h1[^>]*>[^<]*(?:参考文献|References)[^<]*<\/h1>/i;
const nextHeadingPattern = /<h1[^>]*>/i;
const tableBlockPattern = /<table\b[^>]*>[\s\S]*?<\/table>/gi;
const tableRowPattern = /<tr\b[^>]*>[\s\S]*?<\/tr>/gi;
const tableHeaderPattern = /<th\b/i;
const tableCellPattern = /<t[hd]\b[^>]*>[\s\S]*?<\/t[hd]>/gi;
const strictAnchorGlobalPattern = /<a\b[^>]*\bhref=["']https?:\/\/[^"']+["'][^>]*>/gi;
const templateAnchorGlobalPattern = /<a\b[^>]*\bhref=["'](?:https?:\/\/[^"']+|\{\{\s*url\s*\}\})["'][^>]*>/gi;

function lineNumberAt(offset) {
  return xml.slice(0, offset).split(/\r?\n/).length;
}

function firstMeaningfulLine(content) {
  return content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find((line) => line && !line.startsWith("%%"));
}

function plainText(block) {
  return block.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function stripXmlComments(content) {
  return content.replace(/<!--[\s\S]*?-->/g, " ");
}

function countAnchors(content) {
  const pattern = isTemplateFile ? templateAnchorGlobalPattern : strictAnchorGlobalPattern;
  return (content.match(pattern) || []).length;
}

function tableHeaderCells(tableBlock) {
  const firstRow = /<tr\b[^>]*>[\s\S]*?<\/tr>/i.exec(tableBlock);
  if (!firstRow) return [];
  return [...firstRow[0].matchAll(tableCellPattern)]
    .map((match) => plainText(match[0]))
    .filter(Boolean);
}

let failures = 0;
let count = 0;
let match;
const visibleXml = stripXmlComments(xml);

if (forbiddenSupPattern.test(xml) || superscriptStylePattern.test(xml)) {
  failures += 1;
  console.error("Report XML contains raw, encoded, or style-based superscript markup; remove it and use inline linked source names or the reference table instead. Citation components remain allowed.");
}

const internalToolMatch = internalSearchToolPattern.exec(xml);
if (internalToolMatch) {
  failures += 1;
  console.error(`Report XML displays an internal search tool name "${internalToolMatch[0]}"; show external databases/sources such as PubMed, PMC, Cochrane, journal pages, guideline sites, or regulator pages instead.`);
}

const rawToolMatch = rawToolColumnPattern.exec(xml);
if (rawToolMatch) {
  failures += 1;
  console.error('Report XML displays a raw "tool" column/label; use user-facing source labels such as 检索来源/数据库 or external database names instead.');
}

const visibleInstructionMatch = visibleTemplateInstructionPattern.exec(visibleXml);
if (visibleInstructionMatch) {
  failures += 1;
  console.error(`Report XML displays a template instruction "${visibleInstructionMatch[0]}"; remove template/QA wording from the user-facing document and keep only clinical/literature content.`);
}

const referenceHeading = referenceHeadingPattern.exec(xml);
if (referenceHeading) {
  const afterReferenceHeading = xml.slice(referenceHeading.index + referenceHeading[0].length);
  const nextHeading = nextHeadingPattern.exec(afterReferenceHeading);
  const referenceSection = nextHeading
    ? afterReferenceHeading.slice(0, nextHeading.index)
    : afterReferenceHeading;
  const referenceTables = [...referenceSection.matchAll(tableBlockPattern)].map((table) => table[0]);
  if (referenceTables.length === 0) {
    failures += 1;
    console.error("Reference section should use tables with columns: 标题 | 来源 | 类型 | 年份 | 链接.");
  }
  referenceTables.forEach((table, index) => {
    const headers = tableHeaderCells(table);
    const joined = headers.join("|");
    if (headers.length !== 5 || !/标题/.test(joined) || !/来源/.test(joined) || !/类型/.test(joined) || !/年份/.test(joined) || !/链接/.test(joined)) {
      failures += 1;
      console.error(`Reference table ${index + 1} should use exactly five columns: 标题 | 来源 | 类型 | 年份 | 链接. Found: ${headers.join(" | ") || "none"}`);
    }
    const rows = [...table.matchAll(tableRowPattern)].map((row) => row[0]);
    rows.slice(1).forEach((row, rowIndex) => {
      if (countAnchors(row) < 1) {
        failures += 1;
        console.error(`Reference table ${index + 1}, row ${rowIndex + 2} must contain a clickable source link.`);
      }
    });
  });
} else {
  failures += 1;
  console.error("Report XML should include a complete reference section.");
}

while ((match = whiteboardPattern.exec(xml)) !== null) {
  count += 1;
  const fullBlock = match[0];
  const content = match[1];
  const blockLine = lineNumberAt(match.index);
  const firstLine = firstMeaningfulLine(content);

  const problems = [];
  if (!firstLine || !diagramHeaderPattern.test(firstLine)) {
    problems.push("first non-empty line should be a Mermaid diagram declaration such as mindmap, timeline, or flowchart TD");
  }
  if (xmlTagPattern.test(content)) {
    problems.push("whiteboard Mermaid content contains raw XML/HTML tags; remove <br/>, <span>, <b>, etc. and keep labels plain text");
  }
  if (escapedHtmlBreakPattern.test(content)) {
    problems.push("whiteboard Mermaid content contains escaped HTML line breaks; split long labels into separate nodes instead");
  }
  if (invalidLightColorPattern.test(content)) {
    problems.push("Mermaid style uses Feishu callout color names such as light-yellow; use hex colors or omit style lines");
  }
  if (invalidHexPattern.test(content)) {
    problems.push("Mermaid style contains an invalid hex color");
  }
  if (markdownFencePattern.test(fullBlock)) {
    problems.push("whiteboard blocks must not contain Markdown code fences");
  }

  if (problems.length > 0) {
    failures += 1;
    console.error(`Whiteboard ${count} near line ${blockLine}:`);
    problems.forEach((problem) => console.error(`  - ${problem}`));
  }
}

if (failures > 0) {
  console.error(`Report XML validation failed: ${failures} issue(s); ${count} Mermaid whiteboard block(s) checked.`);
  process.exit(1);
}

console.log(`Whiteboard validation passed: ${count} Mermaid whiteboard block(s) checked.`);
