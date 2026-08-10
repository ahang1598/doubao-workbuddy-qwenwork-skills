import fs from 'node:fs';

export const WORKFLOW_STAGE_TO_PROGRESS_STAGE = Object.freeze({
  'project-intake': 'S0',
  'outline-planning': 'S1',
  'manuscript-writing': 'S3',
  'revision-quality': 'S4',
  'document-delivery': 'S5',
  final: 'S5',
});

const FRONTMATTER_PATTERN = /^(\uFEFF?---\s*\r?\n)([\s\S]*?)(\r?\n---(?:\s*\r?\n|\s*$))/;

export function parseProgressFrontmatter(content) {
  const match = String(content).match(FRONTMATTER_PATTERN);
  if (!match) return { ok: false, values: {}, message: 'progress.md must start with YAML frontmatter enclosed by --- lines' };
  const values = {};
  for (const line of match[2].split(/\r?\n/)) {
    const field = line.match(/^([A-Za-z][A-Za-z0-9_-]*):\s*(.*?)\s*$/);
    if (field) values[field[1]] = field[2].replace(/^['"]|['"]$/g, '');
  }
  return { ok: true, values };
}

export function updateProgressFrontmatter(filePath, updates, { content: suppliedContent } = {}) {
  if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
    return { ok: false, message: 'progress.md is missing' };
  }
  const content = suppliedContent ?? fs.readFileSync(filePath, 'utf8');
  const parsed = parseProgressFrontmatter(content);
  if (!parsed.ok) return parsed;
  const newline = content.includes('\r\n') ? '\r\n' : '\n';
  const match = content.match(FRONTMATTER_PATTERN);
  const lines = match[2].split(/\r?\n/);
  for (const [key, value] of Object.entries(updates)) {
    const index = lines.findIndex(line => new RegExp(`^${key}:\\s*`).test(line));
    const replacement = `${key}: ${value}`;
    if (index >= 0) lines[index] = replacement;
    else lines.push(replacement);
  }
  const updated = `${match[1]}${lines.join(newline)}${match[3]}${content.slice(match[0].length)}`;
  fs.writeFileSync(filePath, updated, 'utf8');
  return { ok: true, values: { ...parsed.values, ...updates } };
}
