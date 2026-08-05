#!/usr/bin/env node

const fs = require("fs");

const usage = `Usage:
  node scripts/validate-literature-log.js <literature-log.csv>

Validates the local literature search log CSV used before screening evidence into reports.`;

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
  "record_id",
  "search_batch",
  "query",
  "title",
  "journal_or_source",
  "year",
  "publication_type",
  "abstract_or_summary",
  "url",
  "doi",
  "source_level_initial",
  "full_text_status",
  "screening_decision",
  "decision_reason",
  "topic_relevance",
  "theme_or_use",
  "citation_role",
  "evidence_id",
  "anchor_text",
  "supports_conclusion",
  "diagram_use",
  "used_in_report"
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
if (headers.includes("tool")) {
  console.error("CSV header must not include a user-visible 'tool' column. Keep internal tool names out of the literature log and describe external search sources in the report scope section instead.");
  process.exit(1);
}
if (headers.includes("search_source_display")) {
  console.error("CSV header must not include search_source_display. Describe external search sources in the report's 检索问题与范围 section instead.");
  process.exit(1);
}
if (headers.includes("screening_category")) {
  console.error("CSV header must not include screening_category. Merge evidence category/type into publication_type.");
  process.exit(1);
}

const indexByHeader = Object.fromEntries(headers.map((header, index) => [header, index]));
const dataRows = rows.slice(1);
if (dataRows.length === 0) {
  console.error("CSV has headers but no literature records. Append search results to the literature log before delivery.");
  process.exit(1);
}
const requiredCellHeaders = [
  "record_id",
  "search_batch",
  "query",
  "title",
  "journal_or_source",
  "publication_type",
  "abstract_or_summary",
  "url",
  "screening_decision",
  "topic_relevance"
];

function value(row, header) {
  return String(row[indexByHeader[header]] || "").trim();
}

function isHttpUrl(input) {
  return /^https?:\/\/\S+/i.test(input);
}

let failures = 0;
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

  const decision = value(row, "screening_decision");
  const reason = value(row, "decision_reason");
  if (decision && decision !== "待筛选" && !reason) {
    console.error(`Row ${displayRow}: decision_reason is required once screening_decision is not 待筛选.`);
    failures += 1;
  }

  if (decision === "纳入核心") {
    for (const header of ["evidence_id", "anchor_text", "supports_conclusion", "citation_role"]) {
      if (!value(row, header)) {
        console.error(`Row ${displayRow}: ${header} is required when screening_decision is 纳入核心.`);
        failures += 1;
      }
    }
  }

  if (value(row, "diagram_use") && !value(row, "evidence_id")) {
    console.error(`Row ${displayRow}: evidence_id is required when diagram_use is filled.`);
    failures += 1;
  }
});

if (failures > 0) {
  console.error(`Literature log validation failed: ${failures} issue(s).`);
  process.exit(1);
}

console.log(`Literature log validation passed: ${dataRows.length} record(s) checked.`);
