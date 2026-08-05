#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const usage = `Usage:
  node scripts/sanitize-feishu-report.js <report.xml> [output.xml]

Removes raw or escaped HTML superscript tags from Feishu report XML while keeping the text inside the tags. Also removes legacy visible template-instruction callouts. If output.xml is omitted, the input file is updated in place.`;

if (process.argv.includes("--help") || process.argv.includes("-h")) {
  console.log(usage);
  process.exit(0);
}

const input = process.argv[2];
const output = process.argv[3] || input;

if (!input) {
  console.error(usage);
  process.exit(2);
}

let xml;
try {
  xml = fs.readFileSync(input, "utf8");
} catch (error) {
  console.error(`Failed to read report XML: ${error.message}`);
  process.exit(2);
}

const rawTagPattern = new RegExp("<\\/?\\s*sup\\b[^>]*>", "gi");
const escapedOpenTagPattern = new RegExp("&lt;\\s*sup\\b[^&]*?&gt;", "gi");
const escapedCloseTagPattern = new RegExp("&lt;\\s*\\/\\s*sup\\s*&gt;", "gi");
const visibleInstructionCalloutPattern = new RegExp(
  "<callout\\b[^>]*>\\s*<p>\\s*<b>\\s*(?:正文引用链接要求|本节图表要求|写法要求|参考文献链接要求)：\\s*<\\/b>[\\s\\S]*?<\\/p>\\s*<\\/callout>",
  "gi",
);

const supMatches =
  (xml.match(rawTagPattern) || []).length +
  (xml.match(escapedOpenTagPattern) || []).length +
  (xml.match(escapedCloseTagPattern) || []).length;
const instructionMatches = (xml.match(visibleInstructionCalloutPattern) || []).length;

const sanitized = xml
  .replace(rawTagPattern, "")
  .replace(escapedOpenTagPattern, "")
  .replace(escapedCloseTagPattern, "")
  .replace(visibleInstructionCalloutPattern, "");

try {
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, sanitized, "utf8");
} catch (error) {
  console.error(`Failed to write sanitized report XML: ${error.message}`);
  process.exit(2);
}

console.log(`Sanitized report XML written: ${output}; removed ${supMatches} superscript tag(s) and ${instructionMatches} visible template-instruction callout(s).`);
