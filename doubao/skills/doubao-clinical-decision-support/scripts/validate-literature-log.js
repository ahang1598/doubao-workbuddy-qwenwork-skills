#!/usr/bin/env node

const fs = require("fs");

const usage = `Usage:
  node scripts/validate-literature-log.js <literature-log.csv>

Validates the single-source literature log CSV used for searching, screening, evidence synthesis, citations, diagrams, and delivery.`;

if (process.argv.includes("--help") || process.argv.includes("-h")) {
  console.log(usage);
  process.exit(0);
}

const file = process.argv[2];
if (!file) {
  console.error(usage);
  process.exit(2);
}

let text;
try {
  text = fs.readFileSync(file, "utf8");
} catch (error) {
  console.error(`Failed to read CSV: ${error.message}`);
  process.exit(2);
}

function parseCsvRows(input) {
  const rows = [];
  let row = [];
  let cell = "";
  let inQuotes = false;

  for (let index = 0; index < input.length; index += 1) {
    const char = input[index];
    const next = input[index + 1];

    if (char === '"') {
      if (inQuotes && next === '"') {
        cell += '"';
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === "," && !inQuotes) {
      row.push(cell);
      cell = "";
    } else if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") index += 1;
      row.push(cell);
      if (row.some((value) => value.trim() !== "")) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }

  row.push(cell);
  if (row.some((value) => value.trim() !== "")) rows.push(row);
  return rows;
}

const requiredHeaders = [
  "evidence_id",
  "search_context",
  "title",
  "source_and_year",
  "publication_type",
  "abstract_or_summary",
  "url",
  "evidence_level",
  "status",
  "anchor_text",
  "key_excerpt_or_location",
  "appraisal_and_applicability",
  "use_in_report"
];

const rows = parseCsvRows(text);
if (rows.length === 0) {
  console.error("CSV is empty.");
  process.exit(1);
}

const headers = rows[0].map((header, index) => {
  const normalized = index === 0 ? header.replace(/^\uFEFF/, "") : header;
  return normalized.trim();
});
const missingHeaders = requiredHeaders.filter((header) => !headers.includes(header));
if (missingHeaders.length > 0) {
  console.error(`Missing required header(s): ${missingHeaders.join(", ")}`);
  process.exit(1);
}

const indexByHeader = Object.fromEntries(headers.map((header, index) => [header, index]));
const dataRows = rows.slice(1);
if (dataRows.length === 0) {
  console.error("CSV has headers but no literature records. Append search results before screening or delivery.");
  process.exit(1);
}

const requiredCellHeaders = [
  "evidence_id",
  "search_context",
  "title",
  "source_and_year",
  "publication_type",
  "abstract_or_summary",
  "url",
  "status"
];

function value(row, header) {
  return String(row[indexByHeader[header]] || "").trim();
}

function isHttpUrl(input) {
  return /^https?:\/\/\S+/i.test(input);
}

let failures = 0;
const seenEvidenceIds = new Set();
dataRows.forEach((row, rowIndex) => {
  const displayRow = rowIndex + 2;
  for (const header of requiredCellHeaders) {
    if (!value(row, header)) {
      console.error(`Row ${displayRow}: missing ${header}`);
      failures += 1;
    }
  }

  const url = value(row, "url");
  if (url && !isHttpUrl(url)) {
    console.error(`Row ${displayRow}: url must be a clickable http(s) URL.`);
    failures += 1;
  }

  const evidenceId = value(row, "evidence_id");
  if (evidenceId) {
    if (seenEvidenceIds.has(evidenceId)) {
      console.error(`Row ${displayRow}: duplicate evidence_id ${evidenceId}.`);
      failures += 1;
    }
    seenEvidenceIds.add(evidenceId);
  }

  const status = value(row, "status");
  if (status && !/^(待筛选|纳入核心|纳入辅助|排除|待核验)\/.+/.test(status)) {
    console.error(`Row ${displayRow}: status must use 筛选结果/阅读深度, for example 纳入核心/全文.`);
    failures += 1;
  }

  if (status.startsWith("纳入核心/")) {
    for (const header of [
      "evidence_level",
      "anchor_text",
      "key_excerpt_or_location",
      "appraisal_and_applicability",
      "use_in_report"
    ]) {
      if (!value(row, header)) {
        console.error(`Row ${displayRow}: ${header} is required when status starts with 纳入核心/.`);
        failures += 1;
      }
    }

    if (/(未打开|无法访问|仅摘要)/.test(status)) {
      console.error(`Row ${displayRow}: 纳入核心 records require an opened full text, guideline body, label, or other verifiable primary page.`);
      failures += 1;
    }
  }
});

if (failures > 0) {
  console.error(`Literature log validation failed: ${failures} issue(s).`);
  process.exit(1);
}

console.log(`Literature log validation passed: ${dataRows.length} record(s) checked.`);
