#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const usage = `Usage:
  node scripts/make-literature-log-excel-safe.js <input.csv> [output.csv]

Creates an Excel-friendly UTF-8-with-BOM CSV copy. If output.csv is omitted,
writes <input-stem>-excel.csv next to the input file.`;

if (process.argv.includes("--help") || process.argv.includes("-h")) {
  console.log(usage);
  process.exit(0);
}

const input = process.argv[2];
if (!input) {
  console.error(usage);
  process.exit(2);
}

const output = process.argv[3] || path.join(
  path.dirname(input),
  `${path.basename(input, path.extname(input))}-excel${path.extname(input) || ".csv"}`
);

let text;
try {
  text = fs.readFileSync(input, "utf8");
} catch (error) {
  console.error(`Failed to read CSV: ${error.message}`);
  process.exit(2);
}

const withoutBom = text.replace(/^\uFEFF/, "");
const normalized = withoutBom.replace(/\r?\n/g, "\r\n");

try {
  fs.writeFileSync(output, `\uFEFF${normalized}`, "utf8");
} catch (error) {
  console.error(`Failed to write Excel-safe CSV: ${error.message}`);
  process.exit(2);
}

console.log(`Excel-safe CSV written: ${output}`);
