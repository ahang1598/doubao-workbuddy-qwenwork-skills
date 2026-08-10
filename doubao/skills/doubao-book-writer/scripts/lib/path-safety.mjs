import fs from 'node:fs';
import path from 'node:path';

export function isPathInside(root, candidate) {
  const relation = path.relative(root, candidate);
  return relation === '' || (!relation.startsWith('..') && !path.isAbsolute(relation));
}

function nearestExisting(candidate) {
  let current = candidate;
  while (!fs.existsSync(current)) {
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return current;
}

export function resolveSafePath(root, input, { mustExist = false, forbidden = [] } = {}) {
  if (typeof input !== 'string' || !input.trim()) throw new Error('PATH_TRAVERSAL: path is required');
  const canonicalRoot = fs.realpathSync(path.resolve(root));
  const absolute = path.resolve(canonicalRoot, input);
  if (!isPathInside(canonicalRoot, absolute)) throw new Error(`PATH_TRAVERSAL: path is outside workspace: ${input}`);
  const existing = nearestExisting(absolute);
  const canonicalExisting = fs.realpathSync(existing);
  if (!isPathInside(canonicalRoot, canonicalExisting)) throw new Error(`PATH_TRAVERSAL: path escapes workspace through a link: ${input}`);
  if (mustExist && !fs.existsSync(absolute)) throw new Error(`PATH_NOT_FOUND: ${input}`);
  if (mustExist) {
    const canonicalTarget = fs.realpathSync(absolute);
    if (!isPathInside(canonicalRoot, canonicalTarget)) throw new Error(`PATH_TRAVERSAL: path escapes workspace through a link: ${input}`);
  }
  const relative = path.relative(canonicalRoot, absolute).replace(/\\/g, '/');
  for (const prefix of forbidden.map((value) => String(value).replace(/\\/g, '/').replace(/\/$/, ''))) {
    if (relative === prefix || relative.startsWith(`${prefix}/`)) throw new Error(`FORBIDDEN_PATH: ${input}`);
  }
  return absolute;
}
