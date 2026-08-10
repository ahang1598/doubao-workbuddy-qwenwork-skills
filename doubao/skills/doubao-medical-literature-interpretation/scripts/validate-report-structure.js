#!/usr/bin/env node

const fs = require("fs");

function usage() {
  console.error(
    "Usage: node scripts/validate-report-structure.js [--template] <interpretation.xml>",
  );
}

let templateMode = false;
let inputPath = null;

for (const arg of process.argv.slice(2)) {
  if (arg === "--template") {
    templateMode = true;
  } else if (!inputPath) {
    inputPath = arg;
  } else {
    usage();
    process.exit(2);
  }
}

if (!inputPath) {
  usage();
  process.exit(2);
}

let xml;
try {
  xml = fs.readFileSync(inputPath, "utf8");
} catch (error) {
  console.error(`Cannot read ${inputPath}: ${error.message}`);
  process.exit(2);
}

function plainText(value) {
  return value
    .replace(/<[^>]+>/g, "")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

function extractWhiteboards(value) {
  return Array.from(
    value.matchAll(/<whiteboard\b([^>]*)>([\s\S]*?)<\/whiteboard>/gi),
    (match) => ({
      attributes: match[1],
      body: match[2].trim(),
      index: match.index,
      raw: match[0],
      type:
        match[1].match(/\btype\s*=\s*["']([^"']+)["']/i)?.[1]?.toLowerCase() ||
        "",
    }),
  );
}

function whiteboardProblem(whiteboard) {
  if (!whiteboard.body) return "whiteboard is empty";

  if (whiteboard.type === "mermaid") {
    const supportedDeclaration =
      /^(?:mindmap\b|flowchart\s+(?:TD|TB|BT|LR|RL)\b|graph\s+(?:TD|TB|BT|LR|RL)\b|timeline\b|stateDiagram(?:-v2)?\b|sequenceDiagram\b|erDiagram\b|journey\b|gantt\b)/i;
    if (!supportedDeclaration.test(whiteboard.body)) {
      return "Mermaid whiteboard has an unsupported or missing declaration";
    }
    if (/```|<\/?[a-z][^>]*>/i.test(whiteboard.body)) {
      return "Mermaid whiteboard must not contain Markdown fences or HTML";
    }
    return null;
  }

  if (whiteboard.type === "svg") {
    return /^<svg\b[\s\S]*<\/svg>$/i.test(whiteboard.body)
      ? null
      : "SVG whiteboard must contain one complete <svg>";
  }

  if (whiteboard.type === "plantuml") {
    return /^@startuml\b[\s\S]*@enduml$/i.test(whiteboard.body)
      ? null
      : "PlantUML whiteboard must contain @startuml through @enduml";
  }

  return "whiteboard type must be mermaid, svg, or plantuml";
}

function validateWhiteboards(problems, whiteboards) {
  const validWhiteboards = [];

  for (const [index, whiteboard] of whiteboards.entries()) {
    const problem = whiteboardProblem(whiteboard);
    if (problem) {
      problems.push(`whiteboard ${index + 1}: ${problem}`);
    } else {
      validWhiteboards.push(whiteboard);
    }
  }

  if (validWhiteboards.length < 2) {
    problems.push(
      `full report requires at least two valid whiteboards, found ${validWhiteboards.length}`,
    );
  }
  return validWhiteboards;
}

const problems = [];
const titleMatches = Array.from(
  xml.matchAll(/<title(?:\s[^>]*)?>([\s\S]*?)<\/title>/gi),
);
if (titleMatches.length !== 1) {
  problems.push(
    `document must contain exactly one <title>, found ${titleMatches.length}`,
  );
} else if (!plainText(titleMatches[0][1])) {
  problems.push("document <title> must not be empty");
}

if (!templateMode && /\{\{[\s\S]*?\}\}/.test(xml)) {
  problems.push("unresolved {{...}} template placeholder");
}

for (const { label, pattern } of [
  { label: "HTML <sup> tag", pattern: /<\s*\/?\s*sup\b/i },
  { label: "escaped &lt;sup&gt; tag", pattern: /&lt;\s*\/?\s*sup\b/i },
]) {
  if (pattern.test(xml)) {
    problems.push(`contains forbidden ${label}; use visible Unicode text`);
  }
}

if (templateMode) {
  if (
    !xml.includes("{{顶部总结内容完整XML")
  ) {
    problems.push(
      "template must contain the flexible top-summary content placeholder",
    );
  }
  if (
    !xml.includes("{{正文与结尾完整XML")
  ) {
    problems.push(
      "template must contain the flexible full-body content placeholder",
    );
  }
}

const actualWhiteboards = extractWhiteboards(xml);
const validWhiteboards = templateMode
  ? []
  : validateWhiteboards(problems, actualWhiteboards);

if (problems.length > 0) {
  console.error(
    "Medical literature interpretation report failed basic structure validation:",
  );
  for (const problem of problems) {
    console.error(`- ${problem}`);
  }
  process.exit(1);
}

console.log(
  JSON.stringify(
    {
      valid: true,
      template_mode: templateMode,
      whiteboard_count: actualWhiteboards.length,
      valid_whiteboard_count: templateMode
        ? "template-placeholders"
        : validWhiteboards.length,
      heading_validation: "disabled",
      metadata_label_validation: "disabled",
      callout_validation: "disabled",
      note:
        "Mechanical checks passed. Heading structure, metadata wording, and callout count are intentionally not validated.",
    },
    null,
    2,
  ),
);
