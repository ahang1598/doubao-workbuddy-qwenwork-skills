#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const INDEX_FILENAME = "journal-rank-index.json";
const stopWords = new Set([
  "a", "an", "and", "de", "der", "des", "di", "du", "for", "in", "of",
  "on", "the", "to", "und", "von", "with", "zeitschrift",
]);

const usage = `Usage:
  node scripts/match-journal-rank.js --journal "N Engl J Med"
  node scripts/match-journal-rank.js --json '["NEJM", "中华内科杂志"]'
  node scripts/match-journal-rank.js --report-json report-data.json --in-place
  node scripts/match-journal-rank.js --index /path/to/journal-rank-index.json --report-json report-data.json --in-place
  node scripts/match-journal-rank.js --report-json report-data.json --output ranked-report-data.json
  node scripts/match-journal-rank.js --csv literature-log.csv --in-place
  node scripts/match-journal-rank.js --csv literature-log.csv --output ranked.csv

Matches journal names against the bundled 2025 CAS quartile / PKU Core index.
Report JSON mode reads report_items[].journal_name and writes journal_rank_2025.
CSV mode reads journal_or_institution by default and writes journal_rank_2025.
Non-journal records are skipped. Fuzzy matches are accepted only at high confidence.
The bundled index is discovered automatically. --index is an optional override. `;

function ancestorCandidates(startPath, levels = 4) {
  const candidates = [];
  let current = path.resolve(startPath);
  for (let level = 0; level <= levels; level += 1) {
    candidates.push(path.join(current, "assets", INDEX_FILENAME));
    candidates.push(path.join(current, INDEX_FILENAME));
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return candidates;
}

function resolveIndex(indexOverride) {
  const candidates = [
    indexOverride,
    process.env.JOURNAL_RANK_INDEX,
    ...ancestorCandidates(__dirname),
    ...ancestorCandidates(process.cwd()),
  ].filter(Boolean);

  for (const candidate of [...new Set(candidates.map((value) => path.resolve(value)))]) {
    if (!fs.existsSync(candidate) || !fs.statSync(candidate).isFile()) continue;
    let payload;
    try {
      payload = JSON.parse(fs.readFileSync(candidate, "utf8"));
    } catch (error) {
      throw new Error(`Journal rank index is invalid: ${candidate} (${error.message})`);
    }
    if (!payload || !Array.isArray(payload.records)) {
      throw new Error(`Journal rank index is missing records: ${candidate}`);
    }
    return { path: candidate, payload };
  }
  return null;
}

function normalize(value) {
  return String(value ?? "")
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .replace(/&/g, " and ")
    .replace(/[’'`]/g, "")
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim()
    .replace(/^the\s+/u, "")
    .replace(/\s+/g, " ");
}

function compact(value) {
  return normalize(value).replace(/\s+/g, "");
}

function significantTokens(value) {
  return normalize(value).split(" ").filter((token) => token && !stopWords.has(token));
}

function acronym(value) {
  const tokens = significantTokens(value);
  return tokens.length >= 2 ? tokens.map((token) => token[0]).join("") : "";
}

function asIndexes(value) {
  if (value === undefined) return [];
  return Array.isArray(value) ? value : [value];
}

function unique(values) {
  return [...new Set(values)];
}

function candidateForms(input) {
  const raw = String(input ?? "")
    .replace(/<[^>]+>/g, " ")
    .replace(/https?:\/\/\S+/gi, " ")
    .trim();
  if (!raw) return [];

  const forms = [raw];
  const withoutParenthetical = raw
    .replace(/[（(][^()（）]{1,120}[）)]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (withoutParenthetical) forms.push(withoutParenthetical);
  for (const part of raw.split(/[|;；]/u)) forms.push(part.trim());
  for (const match of raw.matchAll(/[（(]([^()（）]{2,120})[）)]/gu)) forms.push(match[1].trim());

  const withoutCitationTail = raw
    .replace(/[,，。.]?\s*(?:19|20)\d{2}\b.*$/u, "")
    .replace(/\b(?:vol(?:ume)?|卷)\b.*$/iu, "")
    .trim();
  if (withoutCitationTail) forms.push(withoutCitationTail);

  return unique(forms.map((form) => form.replace(/^[\s:：,，.-]+|[\s:：,，.-]+$/gu, "")).filter(Boolean));
}

function tokensPrefixCompatible(query, candidate) {
  const queryTokens = significantTokens(query);
  const candidateTokens = significantTokens(candidate);
  if (queryTokens.length < 2 || queryTokens.length !== candidateTokens.length) return false;
  return queryTokens.every((token, index) => {
    const other = candidateTokens[index];
    return token === other || other.startsWith(token) || token.startsWith(other);
  });
}

function bigrams(value) {
  const text = compact(value);
  if (text.length < 2) return text ? [text] : [];
  const result = [];
  for (let index = 0; index < text.length - 1; index += 1) result.push(text.slice(index, index + 2));
  return result;
}

function diceSimilarity(left, right) {
  const a = bigrams(left);
  const b = bigrams(right);
  if (!a.length || !b.length) return 0;
  const counts = new Map();
  for (const token of a) counts.set(token, (counts.get(token) ?? 0) + 1);
  let overlap = 0;
  for (const token of b) {
    const count = counts.get(token) ?? 0;
    if (count > 0) {
      overlap += 1;
      counts.set(token, count - 1);
    }
  }
  return (2 * overlap) / (a.length + b.length);
}

function parseCsvRows(input) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let index = 0; index < input.length; index += 1) {
    const char = input[index];
    const next = input[index + 1];
    if (char === '"') {
      if (quoted && next === '"') {
        cell += '"';
        index += 1;
      } else quoted = !quoted;
    } else if (char === "," && !quoted) {
      row.push(cell);
      cell = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && next === "\n") index += 1;
      row.push(cell);
      if (row.some((value) => value !== "")) rows.push(row);
      row = [];
      cell = "";
    } else cell += char;
  }
  row.push(cell);
  if (row.some((value) => value !== "")) rows.push(row);
  return rows;
}

function escapeCsv(value) {
  const text = String(value ?? "");
  return /[",\r\n]/u.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function serializeCsv(rows, withBom) {
  const body = `${rows.map((row) => row.map(escapeCsv).join(",")).join("\r\n")}\r\n`;
  return `${withBom ? "\uFEFF" : ""}${body}`;
}

function parseArgs(argv) {
  const options = { journals: [], column: "journal_or_institution", fuzzy: true };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--journal") options.journals.push(argv[++index]);
    else if (arg === "--json") options.json = argv[++index];
    else if (arg === "--report-json") options.reportJson = argv[++index];
    else if (arg === "--csv") options.csv = argv[++index];
    else if (arg === "--column") options.column = argv[++index];
    else if (arg === "--output") options.output = argv[++index];
    else if (arg === "--index") options.index = argv[++index];
    else if (arg === "--in-place") options.inPlace = true;
    else if (arg === "--no-fuzzy") options.fuzzy = false;
    else if (arg === "--help" || arg === "-h") options.help = true;
    else throw new Error(`Unknown argument: ${arg}`);
  }
  return options;
}

let index;
let recordCompacts;

function resultFromIndex(input, recordIndex, status, confidence = 1) {
  const [matchedJournal, levels] = index.records[recordIndex];
  return {
    input,
    status,
    matchedJournal,
    journalRank2025: levels.join("；"),
    confidence: Number(confidence.toFixed(3)),
  };
}

function disambiguateByExactInput(input, indexes) {
  const strict = String(input).normalize("NFKC").toLowerCase().trim();
  return indexes.filter((recordIndex) => index.records[recordIndex][0].normalize("NFKC").toLowerCase().trim() === strict);
}

function matchJournal(input, allowFuzzy = true) {
  const forms = candidateForms(input);
  if (!forms.length) {
    return { input, status: "not_found", matchedJournal: null, journalRank2025: "", confidence: 0 };
  }

  for (const form of forms) {
    const postings = asIndexes(index.exact[normalize(form)]);
    if (postings.length === 1) return resultFromIndex(input, postings[0], "exact");
    const strict = disambiguateByExactInput(form, postings);
    if (strict.length === 1) return resultFromIndex(input, strict[0], "exact");
  }

  for (const form of forms) {
    const postings = asIndexes(index.compact[compact(form)]);
    if (postings.length === 1) return resultFromIndex(input, postings[0], "alias");
  }

  for (const form of forms) {
    const normalized = normalize(form);
    if (/^[a-z0-9]{2,10}$/u.test(normalized)) {
      const brand = asIndexes(index.brand[normalized]);
      if (brand.length === 1) return resultFromIndex(input, brand[0], "alias");
    }

    const aliasKeys = unique([compact(form), acronym(form)].filter((key) => key && key.length <= 14));
    for (const key of aliasKeys) {
      const postings = asIndexes(index.acronym[key]);
      if (postings.length === 1) return resultFromIndex(input, postings[0], "alias");
      const compatible = postings.filter((recordIndex) => tokensPrefixCompatible(form, index.records[recordIndex][0]));
      if (compatible.length === 1) return resultFromIndex(input, compatible[0], "alias", 0.98);
    }
  }

  if (!allowFuzzy) {
    return { input, status: "not_found", matchedJournal: null, journalRank2025: "", confidence: 0 };
  }

  const query = forms.reduce((best, form) => compact(form).length > compact(best).length ? form : best, forms[0]);
  if (compact(query).length < 5) {
    return { input, status: "not_found", matchedJournal: null, journalRank2025: "", confidence: 0 };
  }

  const top = [];
  for (let recordIndex = 0; recordIndex < index.records.length; recordIndex += 1) {
    const score = diceSimilarity(query, recordCompacts[recordIndex]);
    if (score < 0.65) continue;
    top.push({ recordIndex, score });
  }
  top.sort((a, b) => b.score - a.score);
  const best = top[0];
  const second = top[1];
  if (best && best.score >= 0.94 && (!second || best.score - second.score >= 0.04)) {
    return resultFromIndex(input, best.recordIndex, "fuzzy", best.score);
  }

  if (best && best.score >= 0.75) {
    return {
      input,
      status: "ambiguous",
      matchedJournal: null,
      journalRank2025: "",
      confidence: Number(best.score.toFixed(3)),
      candidates: top.slice(0, 3).map(({ recordIndex, score }) => ({
        journal: index.records[recordIndex][0],
        rank: index.records[recordIndex][1].join("；"),
        confidence: Number(score.toFixed(3)),
      })),
    };
  }

  return { input, status: "not_found", matchedJournal: null, journalRank2025: "", confidence: 0 };
}

function isNonJournalPublication(publicationType) {
  return /指南|共识|说明书|监管|政策|标准|教材|专著|数据库|临床路径|guideline|consensus|regulatory|news|preprint/iu.test(String(publicationType ?? ""));
}

function enrichCsv(filePath, options) {
  const input = fs.readFileSync(filePath, "utf8");
  const withBom = input.charCodeAt(0) === 0xFEFF;
  const rows = parseCsvRows(input.replace(/^\uFEFF/u, ""));
  if (!rows.length) throw new Error("CSV is empty.");

  const headers = rows[0].map((header) => header.trim());
  let sourceIndex = headers.indexOf(options.column);
  if (sourceIndex < 0 && options.column === "journal_or_institution") {
    sourceIndex = headers.indexOf("journal_or_source");
  }
  if (sourceIndex < 0) throw new Error(`CSV is missing source column: ${options.column}`);
  const publicationTypeIndex = headers.indexOf("publication_type");

  let rankIndex = headers.indexOf("journal_rank_2025");
  if (rankIndex < 0) {
    headers.push("journal_rank_2025");
    rankIndex = headers.length - 1;
  }
  rows[0] = headers;

  const counts = {};
  for (const row of rows.slice(1)) {
    while (row.length < headers.length) row.push("");
    const source = row[sourceIndex];
    const nonJournal = publicationTypeIndex >= 0 && isNonJournalPublication(row[publicationTypeIndex]);
    const result = nonJournal
      ? { status: "not_applicable", journalRank2025: "" }
      : matchJournal(source, options.fuzzy);
    row[rankIndex] = result.journalRank2025;
    counts[result.status] = (counts[result.status] ?? 0) + 1;
  }

  const destination = options.inPlace ? filePath : options.output;
  if (!destination) throw new Error("CSV mode requires --in-place or --output <path>.");
  const serialized = serializeCsv(rows, withBom);
  if (options.inPlace) {
    const tempPath = `${filePath}.journal-rank.tmp`;
    fs.writeFileSync(tempPath, serialized, "utf8");
    fs.renameSync(tempPath, filePath);
  } else fs.writeFileSync(destination, serialized, "utf8");

  return { file: destination, records: rows.length - 1, counts, rankingYear: index.meta.rankingYear };
}

function writeJsonAtomically(destination, payload) {
  const serialized = `${JSON.stringify(payload, null, 2)}\n`;
  if (destination.endsWith(".tmp")) throw new Error("Output path must not end with .tmp.");
  const tempPath = `${destination}.journal-rank.tmp`;
  fs.writeFileSync(tempPath, serialized, "utf8");
  fs.renameSync(tempPath, destination);
}

function enrichReportJson(filePath, options) {
  const payload = JSON.parse(fs.readFileSync(filePath, "utf8"));
  if (!Array.isArray(payload.report_items)) {
    throw new Error("Report JSON must contain report_items array.");
  }

  const counts = {};
  for (const item of payload.report_items) {
    if (!item || typeof item !== "object" || Array.isArray(item)) {
      throw new Error("Each report_items entry must be an object.");
    }
    delete item.journal_rank_2025;
    const journalName = String(item.journal_name ?? "").trim();
    const publicationType = [
      item.category,
      item.publication_type,
      item.record_type,
      item.type,
    ].filter(Boolean).join(" ");
    const nonJournal = !journalName || isNonJournalPublication(publicationType);
    const result = nonJournal
      ? { status: "not_applicable", journalRank2025: "" }
      : matchJournal(journalName, options.fuzzy);
    if (result.journalRank2025) item.journal_rank_2025 = result.journalRank2025;
    counts[result.status] = (counts[result.status] ?? 0) + 1;
  }

  const destination = options.inPlace ? filePath : options.output;
  if (!destination) {
    throw new Error("Report JSON mode requires --in-place or --output <path>.");
  }
  writeJsonAtomically(destination, payload);
  return {
    file: destination,
    records: payload.report_items.length,
    counts,
    rankingYear: index.meta.rankingYear,
  };
}

try {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    console.log(usage);
    process.exit(0);
  }
  const resolvedIndex = resolveIndex(options.index);
  if (!resolvedIndex) {
    console.log(JSON.stringify({
      skipped: true,
      reason: "journal_rank_index_unavailable",
      message: "期刊分区索引不可用，已跳过分区富化；请继续生成报告并省略 journal_rank_2025。",
    }, null, 2));
    process.exit(0);
  }
  index = resolvedIndex.payload;
  recordCompacts = index.records.map(([title]) => compact(title));
  if (options.csv) {
    console.log(JSON.stringify(enrichCsv(options.csv, options), null, 2));
    process.exit(0);
  }
  if (options.reportJson) {
    console.log(JSON.stringify(enrichReportJson(options.reportJson, options), null, 2));
    process.exit(0);
  }

  const inputs = [...options.journals];
  if (options.json) {
    const parsed = JSON.parse(options.json);
    inputs.push(...(Array.isArray(parsed) ? parsed : [parsed]));
  }
  if (!inputs.length) {
    const stdin = fs.readFileSync(0, "utf8").trim();
    if (stdin) {
      try {
        const parsed = JSON.parse(stdin);
        inputs.push(...(Array.isArray(parsed) ? parsed : [parsed]));
      } catch {
        inputs.push(...stdin.split(/\r?\n/u).map((line) => line.trim()).filter(Boolean));
      }
    }
  }
  if (!inputs.length) throw new Error(usage);
  console.log(JSON.stringify(inputs.map((input) => matchJournal(input, options.fuzzy)), null, 2));
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
