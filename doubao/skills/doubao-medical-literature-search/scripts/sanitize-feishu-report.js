#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const usage = `Usage:
  node scripts/sanitize-feishu-report.js <report.xml> [output.xml]

Removes raw, escaped, double-escaped, numeric-entity, or full-width HTML superscript tags from Feishu report XML while keeping their text. Also removes legacy visible template-instruction callouts. Citation components are not modified. If output.xml is omitted, the input file is updated in place.`;

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

const superscriptTagPatterns = [
  new RegExp("<\\s*\\/?\\s*sup\\b[^>]*>", "gi"),
  new RegExp("&(?:amp;)*lt;\\s*\\/?\\s*sup\\b(?:(?!&(?:amp;)*gt;)[\\s\\S])*?&(?:amp;)*gt;", "gi"),
  new RegExp("&(?:amp;)*#0*60;\\s*\\/?\\s*sup\\b(?:(?!&(?:amp;)*#0*62;)[\\s\\S])*?&(?:amp;)*#0*62;", "gi"),
  new RegExp("&(?:amp;)*#x0*3c;\\s*\\/?\\s*sup\\b(?:(?!&(?:amp;)*#x0*3e;)[\\s\\S])*?&(?:amp;)*#x0*3e;", "gi"),
  new RegExp("＜\\s*\\/?\\s*sup\\b[^＞]*＞", "gi"),
];
const residualSuperscriptPattern = /(?:<|&(?:amp;)*lt;|&(?:amp;)*#0*60;|&(?:amp;)*#x0*3c;|＜)\s*\/?\s*sup\b/i;
const superscriptStylePattern = /\b(?:vertical-align|baseline-shift|font-variant-position)\s*[:=]\s*["']?\s*super\b/i;
const visibleInstructionCalloutPattern = new RegExp(
  "<callout\\b[^>]*>\\s*<p>\\s*<b>\\s*(?:正文引用链接要求|本节图表要求|写法要求|参考文献链接要求)：\\s*<\\/b>[\\s\\S]*?<\\/p>\\s*<\\/callout>",
  "gi",
);

const instructionMatches = (xml.match(visibleInstructionCalloutPattern) || []).length;

let supMatches = 0;
let sanitized = xml;
superscriptTagPatterns.forEach((pattern) => {
  supMatches += (sanitized.match(pattern) || []).length;
  sanitized = sanitized.replace(pattern, "");
});
sanitized = sanitized.replace(visibleInstructionCalloutPattern, "");

if (residualSuperscriptPattern.test(sanitized) || superscriptStylePattern.test(sanitized)) {
  console.error("Superscript markup remains after sanitization; remove the residual HTML/CSS superscript form before delivery. Citation components may remain unchanged.");
  process.exit(1);
}

try {
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, sanitized, "utf8");
} catch (error) {
  console.error(`Failed to write sanitized report XML: ${error.message}`);
  process.exit(2);
}

console.log(`Sanitized report XML written: ${output}; removed ${supMatches} superscript tag(s) and ${instructionMatches} visible template-instruction callout(s).`);
