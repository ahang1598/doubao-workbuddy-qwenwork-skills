#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const usage = `用法：
  node scripts/sanitize-feishu-report.js <report.xml> [output.xml]

清除飞书报告 XML 中原始、转义、双重转义、数字实体或全角形式的 HTML 上标标签，同时保留标签内文字；并移除旧版可见模板指令 callout。不会修改 citation 组件。省略 output.xml 时将直接更新输入文件。`;

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
  console.error(`读取报告 XML 失败：${error.message}`);
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
  console.error("清理后仍存在上标标记；交付前请删除残留的 HTML/CSS 上标形式。citation 组件可以保持不变。");
  process.exit(1);
}

try {
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, sanitized, "utf8");
} catch (error) {
  console.error(`写入清理后的报告 XML 失败：${error.message}`);
  process.exit(2);
}

console.log(`已写入清理后的报告 XML：${output}；共移除 ${supMatches} 个上标标签和 ${instructionMatches} 个可见模板指令 callout。`);
