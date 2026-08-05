#!/usr/bin/env node

const fs = require("fs");

const usage = `Usage:
  node scripts/validate-report-whiteboards.js [--attachments none|present] <report.xml>

Checks report XML/Markdown/PPT XML for forbidden superscript/footnote-style markup, source-link risks in evidence chapters, invalid citation-style components, visible internal tool names, attachment-state hallucinations, reference table shape/link coverage, no visible local CSV absolute paths in document bodies, and <whiteboard type="mermaid"> blocks with XML/HTML fragments or Mermaid syntax patterns that commonly make Feishu whiteboard parsing fail. If an evidence chapter is flagged, review that chapter and add clickable links to every cited guideline, consensus, paper, trial, drug label, or regulator source.`;

if (process.argv.includes("--help") || process.argv.includes("-h")) {
  console.log(usage);
  process.exit(0);
}

let attachmentState = null;
const positionalArgs = [];

for (let index = 2; index < process.argv.length; index += 1) {
  const arg = process.argv[index];
  if (arg === "--attachments") {
    attachmentState = process.argv[index + 1];
    index += 1;
    continue;
  }
  if (arg.startsWith("--attachments=")) {
    attachmentState = arg.split("=")[1];
    continue;
  }
  positionalArgs.push(arg);
}

if (attachmentState && !["none", "present"].includes(attachmentState)) {
  console.error("Invalid --attachments value; use none or present.");
  process.exit(2);
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
  console.error(`Failed to read report XML: ${error.message}`);
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
const forbiddenSupPattern = /(?:<\/?sup\b[^>]*>|&lt;\s*\/?\s*sup\b[^&]*(?:&gt;)?|\bsuperscript\b|vertical-align\s*:\s*super)/i;
const visibleTemplateInstructionPattern = /本节目标|图表要求|正文来源写法|正文引用必须|正文引用格式示例|仅\s*`?attachment_state=present`?\s*时|生成\s*docx\s*时|不得把研究名写成无链接小标题|不得把指南\/共识名写成无链接小标题|除非用户明确要求特定参考文献格式|每轮检索结果必须先写入\s*CSV|G\/R\/S\s*节点必须来自\s*CSV|不要用空\s*CSV|不得写成直接医嘱/;
const citationComponentPattern = /<cite\b[^>]*\btype=["']citation["'][^>]*>[\s\S]*?<\/cite>/gi;
const forbiddenVisibleToolPattern = /\b(?:medical_search|scholar_search|general_search|web\.fetch|WebFetch|lark-doc|lark-ppt|tool|search_context)\b|<t[hd][^>]*>\s*(?:tool|query|search_context)\s*<\/t[hd]>|\|\s*(?:tool|query|search_context)\s*\||检索工具|工具返回|harness\s*过程/gi;
const unresolvedPlaceholderPattern = /\{\{[^}]+\}\}/;
const httpUrlPattern = /https?:\/\/[^\s<>"')\]}，。；、]+/i;
const clickableEvidenceLinkPattern = /(?:<a\b[^>]*\bhref=["']https?:\/\/[^"']+["'][^>]*>[\s\S]*?<\/a>|<bookmark\b[^>]*\bhref=["']https?:\/\/[^"']+["'][^>]*>|\]\(https?:\/\/[^)]+\))/i;
const clickableEvidenceLinkGlobalPattern = /(?:<a\b[^>]*\bhref=["']https?:\/\/[^"']+["'][^>]*>[\s\S]*?<\/a>|<bookmark\b[^>]*\bhref=["']https?:\/\/[^"']+["'][^>]*>|\]\(https?:\/\/[^)]+\))/gi;
const visibleBareCsvPathPattern = /(?:^|[\s:：>])\/(?:Users|home|var|tmp|Volumes)\/[^\s<>)]+\.csv\b/i;
const visibleCsvPathAnchorTextPattern = /(?:<a\b[^>]*>[^<]*\/[^<]*\.csv\s*<\/a>|\[[^\]\n]*\/[^\]\n]*\.csv\]\((?:file:\/\/)?\/[^)]+\.csv\))/i;
const noAttachmentForbiddenPatterns = [
  { pattern: /上传资料与质量|上传资料质量与病例提取|上传报告|上传附件|上传资料[:：]/i, label: "claims uploaded material was analyzed" },
  { pattern: /影像\/报告关键提取|报告关键提取|从报告提取|从上传报告提取|从真实附件读取/i, label: "claims extraction from an uploaded report" },
  { pattern: /附件质量|资料质量评估|质量分级|可用于分析\/部分可用\/不可可靠解读/i, label: "uses attachment quality grading without a real attachment" },
  { pattern: /OCR\s*(?:提取|可读|识别)|(?:上传|附件|报告单|检查单|病历|影像).{0,12}OCR|OCR.{0,12}(?:上传|附件|报告单|检查单|病历|影像)/i, label: "claims patient-attachment OCR was used without a real attachment" },
  { pattern: /真实附件|真实上传资料|上传\s*(?:CT|MRI|影像|化验单|检查单|病历|病理|基因|用药清单)/i, label: "mentions a real uploaded attachment in no-attachment mode" },
];

function plainText(value) {
  return value
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function stripXmlComments(value) {
  return value.replace(/<!--[\s\S]*?-->/g, " ");
}

function referenceStartIndex(content) {
  const startPatterns = [
    /<h1[^>]*>[^<]*(?:完整)?参考文献[^<]*<\/h1>/i,
    /<h2[^>]*>[^<]*(?:核心证据|辅助参考|仅摘要)[^<]*<\/h2>/i,
    /^\s*#{1,3}\s*(?:十[、.]\s*)?(?:完整)?参考文献\b/im,
    /参考文献与台账/i,
  ];
  let start = -1;
  for (const pattern of startPatterns) {
    const match = pattern.exec(content);
    if (match && (start === -1 || match.index < start)) {
      start = match.index;
    }
  }
  return start;
}

function findReferenceSection(content) {
  const start = referenceStartIndex(content);
  if (start === -1) return null;

  const rest = content.slice(start);
  const endMatch = /<h1[^>]*>[^<]*免责声明[^<]*<\/h1>|^\s*#{1,3}\s*.*免责声明\b/im.exec(rest);
  return endMatch ? rest.slice(0, endMatch.index) : rest;
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

function countClickableEvidenceLinks(content) {
  return (content.match(clickableEvidenceLinkGlobalPattern) || []).length;
}

function validateBodyEvidenceLinks(content) {
  const problems = [];
  const contentWithoutWhiteboards = stripMermaidWhiteboards(content);
  const start = referenceStartIndex(contentWithoutWhiteboards);
  const body = start === -1 ? contentWithoutWhiteboards : contentWithoutWhiteboards.slice(0, start);

  const sectionSpecs = [
    { label: "guidelines/consensus evidence", pattern: /指南|共识/, minLinks: 3 },
    { label: "key research evidence", pattern: /关键研究|研究证据|论文证据/, minLinks: 3 },
  ];

  sectionSpecs.forEach(({ label, pattern, minLinks }) => {
    const section = headingSection(body, pattern);
    if (!section) {
      problems.push(`${label} section was not found; ensure the expected evidence chapter exists and cited sources are rendered as clickable links`);
      return;
    }
    const linkCount = countClickableEvidenceLinks(section);
    if (linkCount < minLinks) {
      problems.push(`${label} section may contain cited key literature without hyperlinks; review the chapter and make every guideline/consensus/paper/trial/source mention clickable (fallback found ${linkCount} source link(s))`);
    }
  });

  return problems;
}

function validateCitationComponents(content) {
  const problems = [];
  const components = [...content.matchAll(citationComponentPattern)];
  components.forEach((match, index) => {
    if (!clickableEvidenceLinkPattern.test(match[0])) {
      problems.push(`citation component ${index + 1} must contain a clickable source link`);
    }
  });
  return problems;
}

function referenceItems(section) {
  const items = [];
  for (const match of section.matchAll(/<li\b[^>]*>[\s\S]*?<\/li>/gi)) {
    items.push(match[0]);
  }
  for (const match of section.matchAll(/<tr\b[^>]*>[\s\S]*?<\/tr>/gi)) {
    if (!/<th\b/i.test(match[0])) items.push(match[0]);
  }
  section.split(/\r?\n/).forEach((line) => {
    if (/^\s*(?:[-*]|\d+[.)])\s+/.test(line) || /^\s*\|/.test(line)) {
      if (!/^\s*\|\s*-+/.test(line) && !/标题\s*\|.*来源/.test(line)) {
        items.push(line);
      }
    }
  });
  return items
    .map((item) => item.trim())
    .filter((item) => item && !/literature_log_csv_path|完整文献检索台账 CSV|本地文献台账/.test(item));
}

function tableBlocks(section) {
  const blocks = [];
  for (const match of section.matchAll(/<table\b[^>]*>[\s\S]*?<\/table>/gi)) {
    blocks.push({ type: "xml", value: match[0] });
  }

  const markdownTableLines = section
    .split(/\r?\n/)
    .filter((line) => /^\s*\|.+\|\s*$/.test(line));
  if (markdownTableLines.length >= 3) {
    blocks.push({ type: "markdown", value: markdownTableLines.join("\n") });
  }
  return blocks;
}

function tableHeaders(block) {
  if (block.type === "xml") {
    const firstRow = /<tr\b[^>]*>[\s\S]*?<\/tr>/i.exec(block.value);
    if (!firstRow) return "";
    return plainText(firstRow[0]);
  }
  return plainText(block.value.split(/\r?\n/)[0] || "");
}

function tableHeaderCells(block) {
  if (block.type === "xml") {
    const firstRow = /<tr\b[^>]*>[\s\S]*?<\/tr>/i.exec(block.value);
    if (!firstRow) return [];
    return [...firstRow[0].matchAll(/<t[hd]\b[^>]*>[\s\S]*?<\/t[hd]>/gi)]
      .map((match) => plainText(match[0]))
      .filter(Boolean);
  }
  const line = block.value.split(/\r?\n/)[0] || "";
  return line
    .split("|")
    .map((cell) => plainText(cell))
    .filter(Boolean);
}

function tableDataRows(block) {
  if (block.type === "xml") {
    return [...block.value.matchAll(/<tr\b[^>]*>[\s\S]*?<\/tr>/gi)]
      .map((match) => match[0])
      .filter((row) => !/<th\b/i.test(row));
  }
  return block.value
    .split(/\r?\n/)
    .slice(2)
    .filter((line) => /\S/.test(line));
}

function findReferenceTitle(content) {
  const patterns = [
    /<h1\b[^>]*>([^<]*参考文献[^<]*)<\/h1>/i,
    /^\s*#\s+(.+参考文献.+)$/im,
  ];
  for (const pattern of patterns) {
    const match = pattern.exec(content);
    if (match) return plainText(match[1]);
  }
  return "";
}

function validateReferenceSection(content, section) {
  const problems = [];
  const title = findReferenceTitle(content);
  if (!title || !/参考文献/.test(title) || !/链接/.test(title)) {
    problems.push(`reference section title must mention links, found: ${title || "none"}`);
  }

  const blocks = tableBlocks(section);
  if (blocks.length === 0) {
    problems.push("reference section must use tables for core evidence, auxiliary references, and screening records");
  }
  const referenceLinkCount = countClickableEvidenceLinks(section);
  if (referenceLinkCount < 6) {
    problems.push(`reference section may be missing original/abstract links; review all displayed references and add clickable source links (fallback found ${referenceLinkCount} source link(s))`);
  }

  const invalidReferenceHeaderBlocks = blocks
    .map((block, index) => ({ index, cells: tableHeaderCells(block) }))
    .filter(({ cells }) => {
      if (cells.length !== 3) return true;
      const headers = cells.join("|");
      return !/标题/.test(headers) || !/来源/.test(headers) || !/链接/.test(headers);
    });
  if (invalidReferenceHeaderBlocks.length > 0) {
    problems.push("final reference tables must use exactly three columns: 标题 | 来源 | 链接, unless the user explicitly requested a citation style");
    invalidReferenceHeaderBlocks.slice(0, 5).forEach(({ index, cells }) => {
      problems.push(`reference table ${index + 1} headers: ${cells.join(" | ") || "none"}`);
    });
  }

  const exposedInternalColumns = blocks
    .map((block) => tableHeaders(block))
    .filter((headers) => /(?:^|\s)(?:tool|query|search_context)(?:\s|$)|检索工具|工具名称/i.test(headers));
  if (exposedInternalColumns.length > 0) {
    problems.push("reference tables must not expose internal columns such as tool, query, or search_context");
  }

  const dataRows = blocks.flatMap(tableDataRows);
  if (blocks.length > 0 && dataRows.length === 0) {
    problems.push("reference tables must contain at least one data row");
  }

  if (visibleBareCsvPathPattern.test(section) || visibleCsvPathAnchorTextPattern.test(section)) {
    problems.push("reference section must not expose local CSV absolute paths; attach the CSV after creating the Feishu document and keep local CSV paths out of both the document body and final reply");
  }

  if (/CSV\s*(?:可见版|台账)|文献检索\s*CSV\s*可见版/i.test(content)) {
    problems.push("do not create a separate CSV visible ledger section; attach the CSV file after document creation instead of expanding it in the document body");
  }

  return problems;
}
const presentAttachmentRequiredPatterns = [
  { pattern: /上传资料质量与病例提取|上传资料与质量|真实上传资料|资料类型/i, label: "attachment source/type" },
  { pattern: /质量|可用于分析|部分可用|不可可靠解读/i, label: "attachment quality" },
  { pattern: /局限|不可可靠解读|需补充|模糊|缺页|遮挡|不可读|非原始/i, label: "attachment limitation" },
];

function lineNumberAt(offset) {
  return xml.slice(0, offset).split(/\r?\n/).length;
}

function firstMeaningfulLine(content) {
  return content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find((line) => line && !line.startsWith("%%"));
}

function firstLineForPattern(content, pattern) {
  const lines = content.split(/\r?\n/);
  for (let index = 0; index < lines.length; index += 1) {
    if (pattern.test(lines[index])) {
      return { number: index + 1, text: lines[index].trim() };
    }
  }
  return null;
}

let failures = 0;
let count = 0;
let match;
const visibleXml = stripXmlComments(xml);

if (forbiddenSupPattern.test(xml)) {
  failures += 1;
  console.error("Report contains a superscript-style tag or escaped superscript markup; use inline source links, evidence_id text, and the reference table instead.");
}

const visibleInstructionMatch = visibleTemplateInstructionPattern.exec(visibleXml);
if (visibleInstructionMatch) {
  failures += 1;
  console.error(`Report displays a template instruction "${visibleInstructionMatch[0]}"; remove template/QA wording from the user-facing document and keep only clinical content.`);
}

const citationProblems = validateCitationComponents(xml);
if (citationProblems.length > 0) {
  failures += 1;
  console.error("Citation component validation failed:");
  citationProblems.forEach((problem) => console.error(`  - ${problem}`));
}

if (unresolvedPlaceholderPattern.test(xml)) {
  failures += 1;
  const placeholder = unresolvedPlaceholderPattern.exec(xml)[0];
  console.error(`Report still contains unresolved template placeholder ${placeholder}; replace all placeholders with real values and links before delivery.`);
}

const visibleToolMatches = [...xml.matchAll(forbiddenVisibleToolPattern)];
if (visibleToolMatches.length > 0) {
  failures += 1;
  const uniqueTerms = [...new Set(visibleToolMatches.map((match) => match[0]))].join(", ");
  console.error(`Report contains visible internal tool/process wording (${uniqueTerms}); use reader-facing source categories such as 指南/共识来源、学术文献来源、药品/监管安全来源、原文阅读.`);
}

const references = findReferenceSection(xml);
if (!references) {
  failures += 1;
  console.error("Report is missing a final reference section; include complete references with original/abstract links.");
} else {
  const items = referenceItems(references);
  if (items.length === 0) {
    failures += 1;
    console.error("Reference section has no detectable reference items.");
  }
}

if (attachmentState === "none") {
  const problems = [];
  noAttachmentForbiddenPatterns.forEach(({ pattern, label }) => {
    const hit = firstLineForPattern(xml, pattern);
    if (hit) {
      problems.push(`${label} near line ${hit.number}: ${hit.text}`);
    }
  });
  if (problems.length > 0) {
    failures += 1;
    console.error("Attachment-state validation failed: --attachments none forbids uploaded-report/attachment extraction claims.");
    problems.forEach((problem) => console.error(`  - ${problem}`));
  }
}

if (attachmentState === "present") {
  const missing = presentAttachmentRequiredPatterns
    .filter(({ pattern }) => !pattern.test(xml))
    .map(({ label }) => label);
  if (missing.length > 0) {
    failures += 1;
    console.error("Attachment-state validation failed: --attachments present requires uploaded material source, quality, and limitation details.");
    missing.forEach((label) => console.error(`  - missing ${label}`));
  }
}

const looksLikeSlides = /<slide\b|<presentation\b|<deck\b|<ppt\b/i.test(xml);
if (!looksLikeSlides) {
  const bodyLinkProblems = validateBodyEvidenceLinks(xml);
  if (bodyLinkProblems.length > 0) {
    failures += 1;
    console.error("Body evidence-link validation failed:");
    bodyLinkProblems.forEach((problem) => console.error(`  - ${problem}`));
  }
}

if (!looksLikeSlides && references) {
  const referenceProblems = validateReferenceSection(xml, references);
  if (referenceProblems.length > 0) {
    failures += 1;
    console.error("Reference section table/link validation failed:");
    referenceProblems.forEach((problem) => console.error(`  - ${problem}`));
  }
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

if (count === 0) {
  console.log("Report XML validation passed: no forbidden superscript/footnote-style markup; no Mermaid whiteboard blocks found.");
  process.exit(0);
}

console.log(`Report XML validation passed: no forbidden superscript/footnote-style markup; ${count} Mermaid whiteboard block(s) checked.`);
