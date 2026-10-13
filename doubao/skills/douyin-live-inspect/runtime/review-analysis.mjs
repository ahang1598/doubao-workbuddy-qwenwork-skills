import { constants } from 'node:fs';
import { open } from 'node:fs/promises';
import { extname } from 'node:path';
import { buildReviewReportViewModel } from './ecommerce-review-report.mjs';

const LIMIT = 2 * 1024 * 1024;
function invalid(reason, details = {}) {
  return Object.assign(new Error('Invalid analysis input'), { code: 'INVALID_INPUT', reason, ...details });
}
// Node versions sometimes omit an offset from SyntaxError. This syntax-only
// walker locates the failure; JSON.parse remains the sole source of values.
function jsonErrorOffset(text) {
  let at = 0;
  const stop = () => { throw at; };
  const space = () => { while (/[\x20\t\r\n]/.test(text[at] || 'x')) at++; };
  const string = () => {
    if (text[at++] !== '"') stop();
    while (at < text.length) {
      const char = text[at++];
      if (char === '"') return;
      if (char.charCodeAt(0) < 32) { at--; stop(); }
      if (char === '\\') {
        const escape = text[at++];
        if (escape === 'u') {
          for (let i = 0; i < 4; i++) { if (!/[0-9a-f]/i.test(text[at] || 'x')) stop(); at++; }
        } else if (!escape || !'"\\/bfnrt'.includes(escape)) { at--; stop(); }
      }
    }
    stop();
  };
  const value = (depth = 0) => {
    space(); if (depth > 512) stop();
    const char = text[at];
    if (char === '"') return string();
    if (char === '{' || char === '[') {
      at++; space(); const end = char === '{' ? '}' : ']';
      if (text[at] === end) { at++; return; }
      while (at < text.length) {
        if (char === '{') { space(); if (text[at] !== '"') stop(); string(); space(); if (text[at] !== ':') stop(); at++; }
        value(depth + 1); space();
        if (text[at] === end) { at++; return; }
        if (text[at] !== ',') stop(); at++;
      }
      stop();
    }
    const token = /^(?:true|false|null|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)/.exec(text.slice(at));
    if (!token) stop(); at += token[0].length;
  };
  try { value(); space(); stop(); } catch (offset) { return typeof offset === 'number' ? offset : at; }
}
export function parseAnalysisJson(bytes) {
  let text;
  try { text = new TextDecoder('utf-8', { fatal: true }).decode(bytes); }
  catch { throw invalid('invalid_utf8'); }
  try { return JSON.parse(text); }
  catch (cause) {
    // Only extract numeric locations; parser messages may contain private text.
    const position = /position (\d+)/.exec(cause.message)?.[1] ?? jsonErrorOffset(text);
    const location = /line (\d+) column (\d+)/.exec(cause.message);
    const prefix = position === undefined ? null : text.slice(0, Number(position));
    const line = location ? Number(location[1]) : prefix !== null ? prefix.split('\n').length : undefined;
    const column = location ? Number(location[2]) : prefix !== null ? prefix.length - prefix.lastIndexOf('\n') : undefined;
    throw invalid('invalid_json', { line, column });
  }
}
export async function readAnalysis(input) {
  if (input.review !== undefined && input.review_file !== undefined) throw invalid('conflicting_inputs');
  let review = input.review;
  if (input.review_file !== undefined) {
    if (typeof input.review_file !== 'string' || extname(input.review_file).toLowerCase() !== '.json') throw invalid('invalid_file_type');
    let handle;
    try {
      try { handle = await open(input.review_file, constants.O_RDONLY | constants.O_NOFOLLOW); }
      catch { throw invalid('file_unreadable'); }
      const info = await handle.stat();
      if (!info.isFile()) throw invalid('invalid_file_type');
      if (!info.size || info.size > LIMIT) throw invalid('invalid_file_size');
      const bytes = await handle.readFile();
      if (bytes.length > LIMIT) throw invalid('invalid_file_size');
      review = parseAnalysisJson(bytes);
    } catch (error) { throw error.code === 'INVALID_INPUT' ? error : invalid('file_unreadable'); }
    finally { await handle?.close(); }
  }
  const expect = (condition, field, expected) => { if (!condition) throw invalid('invalid_structure', { field, expected }); };
  expect(review && typeof review === 'object' && !Array.isArray(review), 'review', 'object');
  expect(review.module_code === 'content_analysis', 'review.module_code', 'content_analysis');
  for (const key of ['conclusion', 'summary', 'data_scope_note']) expect(typeof review[key] === 'string' && review[key].trim(), `review.${key}`, 'non-empty string');
  for (const key of ['highlights', 'problems', 'recommended_structure', 'recommendations', 'segments']) expect(Array.isArray(review[key]), `review.${key}`, 'array');
  for (const [index, row] of review.segments.entries()) {
    expect(row && typeof row === 'object', `review.segments[${index}]`, 'object');
    for (const key of ['start_time', 'end_time']) expect(Number.isSafeInteger(row[key]) && row[key] >= 0, `review.segments[${index}].${key}`, 'non-negative integer');
    expect(typeof row.content === 'string' && row.content.trim(), `review.segments[${index}].content`, 'non-empty string');
  }
  try { buildReviewReportViewModel(review); }
  catch (error) {
    if (error.code === 'RAW_DATA_REJECTED') throw error;
    // Existing semantic validators remain authoritative, without leaking values.
    const index = /segment (\d+)/.exec(error.message)?.[1];
    throw invalid('invalid_structure', { field: index ? `review.segments[${Number(index) - 1}]` : 'review', expected: 'valid content analysis' });
  }
  return review;
}
export function analysisErrorDetails(error) {
  return Object.fromEntries(['reason', 'line', 'column', 'field', 'expected'].filter(key => error[key] !== undefined).map(key => [key, error[key]]));
}
