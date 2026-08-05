#!/usr/bin/env node

const fs = require("fs");

const usage = `Usage:
  node scripts/validate-evidence-table.js <evidence-table.json>

Input may be an array, or an object with "evidence", "references", or "items" array.
The script checks required fields, clickable URLs, and citation-use fields for literature evidence reports.`;

if (process.argv.includes("--help") || process.argv.includes("-h")) {
  console.log(usage);
  process.exit(0);
}

const file = process.argv[2];
if (!file) {
  console.error(usage);
  process.exit(2);
}

function readJson(path) {
  try {
    return JSON.parse(fs.readFileSync(path, "utf8"));
  } catch (error) {
    console.error(`Failed to read JSON: ${error.message}`);
    process.exit(2);
  }
}

function pickArray(data) {
  if (Array.isArray(data)) return data;
  for (const key of ["evidence", "references", "items"]) {
    if (Array.isArray(data[key])) return data[key];
  }
  return null;
}

const fieldGroups = [
  ["evidence_id", "证据编号"],
  ["类型", "type", "publication_type"],
  ["标题", "title"],
  ["来源/期刊", "来源", "source", "journal"],
  ["年份", "year"],
  ["来源级别", "source_level"],
  ["链接", "原文链接", "url", "link", "href"],
  ["阅读状态", "read_status", "reading_status", "full_text_status"],
  ["证据级别", "evidence_level", "certainty"],
  ["关键结果/推荐", "关键发现", "key_finding", "core_finding"],
  ["主题相关性", "topic_relevance"],
  ["引用用途", "citation_role", "use_in_report"],
  ["局限性", "limitations"]
];

function hasValue(item, keys) {
  return keys.some((key) => {
    const value = item[key];
    return value !== undefined && value !== null && String(value).trim() !== "";
  });
}

function firstValue(item, keys) {
  for (const key of keys) {
    const value = item[key];
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      return String(value).trim();
    }
  }
  return "";
}

function containsClickableUrl(value) {
  return /https?:\/\/[^\s<>"']+/i.test(value);
}

const data = readJson(file);
const rows = pickArray(data);
if (!rows) {
  console.error('Expected an array, or an object with "evidence", "references", or "items" array.');
  process.exit(2);
}

let failures = 0;
rows.forEach((row, index) => {
  if (!row || typeof row !== "object" || Array.isArray(row)) {
    console.error(`Row ${index + 1}: expected an object.`);
    failures += 1;
    return;
  }
  const missing = fieldGroups.filter((keys) => !hasValue(row, keys)).map((keys) => keys[0]);
  if (missing.length > 0) {
    console.error(`Row ${index + 1}: missing ${missing.join(", ")}`);
    failures += 1;
  }
  const linkValue = firstValue(row, ["链接", "原文链接", "url", "link", "href"]);
  if (linkValue && !containsClickableUrl(linkValue)) {
    console.error(`Row ${index + 1}: link field must contain a clickable http(s) URL, not only DOI/PMID/text.`);
    failures += 1;
  }
});

if (failures > 0) {
  console.error(`Evidence table validation failed: ${failures} row(s) have missing required fields.`);
  process.exit(1);
}

console.log(`Evidence table validation passed: ${rows.length} row(s) checked.`);
