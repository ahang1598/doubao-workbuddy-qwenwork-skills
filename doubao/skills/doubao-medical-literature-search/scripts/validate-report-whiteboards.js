#!/usr/bin/env node

const fs = require("fs");

const usage = `Usage:
  node scripts/validate-report-whiteboards.js <report.xml>

Checks <whiteboard type="mermaid"> blocks for XML/HTML fragments and Mermaid syntax patterns that commonly make Feishu whiteboard parsing fail.
Also checks hard report rules: no sup tags, no displayed internal search tool names, no displayed raw "tool" column, no expanded CSV preview/checklist inside the report body, required evidence-visualization sections are present, concise search method fields are present in the scope section, source-link risks in evidence chapters are surfaced, and final reference tables use 标题/来源/类型/年份/链接 with source-link coverage. If an evidence chapter is flagged, review that chapter and add clickable links to every cited guideline, consensus, paper, trial, textbook, drug label, or regulator source.`;

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

const whiteboardPattern = /<whiteboard\b(?=[^>]*\btype=["']mermaid["'])[^>]*>([\s\S]*?)<\/whiteboard>/gi;
const mermaidWhiteboardBlockPattern = /<whiteboard\b(?=[^>]*\btype=["']mermaid["'])[^>]*>[\s\S]*?<\/whiteboard>/gi;
const diagramHeaderPattern = /^(graph|flowchart|sequenceDiagram|stateDiagram(?:-v2)?|classDiagram|erDiagram|journey|gantt|pie|mindmap|timeline|quadrantChart)\b/;
const xmlTagPattern = /<\/?[A-Za-z][^>]*>/;
const invalidLightColorPattern = /\b(?:fill|stroke|color|background(?:-color)?)\s*:\s*#?light-(?:blue|green|yellow|orange|red)\b/i;
const invalidHexPattern = /\b(?:fill|stroke|color|background(?:-color)?)\s*:\s*#(?![0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?\b)[A-Za-z0-9_-]+/i;
const escapedHtmlBreakPattern = /&lt;\s*br\b/i;
const markdownFencePattern = /```/;
const forbiddenSupPattern = /<\/?sup\b[^>]*>/i;
const escapedSupPattern = /&lt;\s*\/?\s*sup\b/i;
const internalSearchToolPattern = /\b(?:medical_search|scholar_search|general_search|[A-Za-z][A-Za-z0-9-]*_search)\b/;
const rawToolColumnPattern = /(?:^|[>\s])tool(?:[<\s]|$)/i;
const visibleTemplateInstructionPattern = /正文引用链接要求|本节图表要求|参考文献链接要求|写法要求|生成说明|要求：正文页提及|所有\s+G\/SR\/R\/N\s+节点必须|每个节点必须能回到\s*CSV/;
const searchMethodPattern = /检索问题与范围[\s\S]{0,1500}检索来源[\s\S]{0,500}核心关键词[\s\S]{0,500}检索效率/;
const milestoneTimelinePattern = /关键研究里程碑时间线图|里程碑时间线图/;
const logicGraphPattern = /论文关系\/核心逻辑梳理图|核心逻辑梳理图|论文关系梳理图/;
const referenceHeadingPattern = /<h1[^>]*>[^<]*(?:参考文献|References)[^<]*<\/h1>/i;
const nextHeadingPattern = /<h1[^>]*>/i;
const tableBlockPattern = /<table\b[^>]*>[\s\S]*?<\/table>/gi;
const tableRowPattern = /<tr\b[^>]*>[\s\S]*?<\/tr>/gi;
const tableHeaderPattern = /<th\b/i;
const tableCellPattern = /<t[hd]\b[^>]*>[\s\S]*?<\/t[hd]>/gi;
const listItemPattern = /<li\b[^>]*>[\s\S]*?<\/li>/gi;
const paragraphPattern = /<p\b[^>]*>[\s\S]*?<\/p>/gi;
const strictAnchorGlobalPattern = /<a\b[^>]*\bhref=["']https?:\/\/[^"']+["'][^>]*>/gi;
const templateAnchorGlobalPattern = /<a\b[^>]*\bhref=["'](?:https?:\/\/[^"']+|\{\{\s*url\s*\}\})["'][^>]*>/gi;
const numberedReferencePattern = /^(?:\d{1,3}\.|(?:G|SR|R|N|S|T|C)\d+\.?)\s+\S/;
const forbiddenCsvInDocumentPattern = /CSV\s*(?:交付检查表|预览表|全量内容|原样内容)|原始文献台账 CSV|literature_log_csv_path/i;

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

function stripMermaidWhiteboards(content) {
  return content.replace(mermaidWhiteboardBlockPattern, " ");
}

function referenceStartIndex(content) {
  const match = referenceHeadingPattern.exec(content);
  return match ? match.index : -1;
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
  return "";
}

function countAnchors(content) {
  const pattern = isTemplateFile ? templateAnchorGlobalPattern : strictAnchorGlobalPattern;
  return (content.match(pattern) || []).length;
}

function validateBodyEvidenceLinks(content) {
  const problems = [];
  const withoutWhiteboards = stripMermaidWhiteboards(content);
  const referenceStart = referenceStartIndex(withoutWhiteboards);
  const body = referenceStart === -1 ? withoutWhiteboards : withoutWhiteboards.slice(0, referenceStart);

  const sectionSpecs = [
    { label: "guidelines/consensus evidence", pattern: /指南|共识/, minLinks: isTemplateFile ? 1 : 3 },
    { label: "systematic review/key studies", pattern: /系统综述|关键研究|研究证据|论文证据/, minLinks: isTemplateFile ? 1 : 3 },
  ];

  sectionSpecs.forEach(({ label, pattern, minLinks }) => {
    const section = headingSection(body, pattern);
    if (!section) {
      problems.push(`${label} section was not found; ensure the expected evidence chapter exists and cited sources are rendered as clickable links`);
      return;
    }
    const linkCount = countAnchors(section);
    if (linkCount < minLinks) {
      problems.push(`${label} section may contain cited key literature without hyperlinks; review the chapter and make every guideline/consensus/paper/trial/source mention clickable (fallback found ${linkCount} source link(s))`);
    }
  });

  return problems;
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

if (forbiddenSupPattern.test(xml) || escapedSupPattern.test(xml)) {
  failures += 1;
  console.error("Report XML contains raw or escaped sup tags; use inline reference text, evidence_id, links, or the reference table instead.");
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

if (!searchMethodPattern.test(xml)) {
  failures += 1;
  console.error("Report XML should include concise search source, core keyword, and search-efficiency fields inside the scope section.");
}

const forbiddenCsvInDocumentMatch = forbiddenCsvInDocumentPattern.exec(xml);
if (forbiddenCsvInDocumentMatch) {
  failures += 1;
  console.error(`Report XML should not expand or preview CSV content inside the document body; remove "${forbiddenCsvInDocumentMatch[0]}". Attach the CSV after document creation; do not expose its local path or directory in the document body or final reply.`);
}

const visibleInstructionMatch = visibleTemplateInstructionPattern.exec(visibleXml);
if (visibleInstructionMatch) {
  failures += 1;
  console.error(`Report XML displays a template instruction "${visibleInstructionMatch[0]}"; remove template/QA wording from the user-facing document and keep only clinical/literature content.`);
}

if (!milestoneTimelinePattern.test(xml)) {
  failures += 1;
  console.error("Report XML should include a key-research milestone timeline section.");
}

if (!logicGraphPattern.test(xml)) {
  failures += 1;
  console.error("Report XML should include a paper-relationship/core-logic graph section.");
}

const bodyLinkProblems = validateBodyEvidenceLinks(xml);
if (bodyLinkProblems.length > 0) {
  failures += 1;
  console.error("Body evidence-link validation failed:");
  bodyLinkProblems.forEach((problem) => console.error(`  - ${problem}`));
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
  });
  const referenceLinkCount = countAnchors(referenceSection);
  const minReferenceLinks = isTemplateFile ? 1 : 6;
  if (referenceLinkCount < minReferenceLinks) {
    failures += 1;
    console.error(`Reference section may be missing original/abstract links; review all displayed references and add clickable source links (fallback found ${referenceLinkCount} source link(s)).`);
  }
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
    problems.push("first non-empty line should be a Mermaid diagram declaration such as graph TD or flowchart TD");
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

if (count < 2) {
  console.error(`Report XML should include at least 2 Mermaid whiteboard graph blocks; found ${count}.`);
  process.exit(1);
}

console.log(`Whiteboard validation passed: ${count} Mermaid whiteboard block(s) checked.`);
