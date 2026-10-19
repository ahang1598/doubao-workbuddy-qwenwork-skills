'use strict';
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const {randomUUID} = require('node:crypto');
const FILE = '.task-context.json';
const ID = /^[0-9a-f]{32}$/i;

function readContext(directory, usageOnly = false) {
  const filename = path.join(directory, usageOnly ? '.usage-context.json' : FILE);
  let fd;
  try {
    const entry = fs.lstatSync(filename);
    if (!entry.isFile() || entry.isSymbolicLink()) throw Error('invalid task context');
    fd = fs.openSync(filename, fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0) | (fs.constants.O_NONBLOCK || 0));
    const info = fs.fstatSync(fd);
    if (!info.isFile() || info.size > 1024) throw Error('invalid task context');
    const value = JSON.parse(fs.readFileSync(fd, 'utf8'));
    if (!value || Array.isArray(value) || (!usageOnly && (typeof value.task_id !== 'string' || !ID.test(value.task_id))) || (value.started !== undefined && typeof value.started !== 'boolean') ||
        ![undefined, 'lite', 'formal'].includes(value.mode)) throw Error('invalid task context');
    return {...(!usageOnly ? {task_id:value.task_id, ...(value.funnel_schema_version === 1 ? {funnel_schema_version:1} : {})} : {}), ...(value.started !== undefined ? {started:value.started} : {}), ...(value.mode ? {mode:value.mode} : {})};
  } catch (error) { if (error.code === 'ENOENT') return undefined; throw error; }
  finally { if (fd !== undefined) fs.closeSync(fd); }
}

function reserveTask(directory) {
  const expanded = directory?.replace(/^~(?=$|[/\\])/, os.homedir());
  const root = expanded ? path.resolve(expanded) : fs.mkdtempSync(path.join(os.tmpdir(), 'live-inspect-lite-'));
  const skill = path.resolve(__dirname, '..');
  if (root === skill || root.startsWith(skill + path.sep)) throw Error('task directory must be outside Skill');
  let ancestor = root;
  while (!fs.existsSync(ancestor)) {
    const parent = path.dirname(ancestor);
    if (parent === ancestor) throw Error('task directory is unavailable');
    ancestor = parent;
  }
  const resolved = path.join(fs.realpathSync(ancestor), path.relative(ancestor, root));
  if (resolved === skill || resolved.startsWith(skill + path.sep)) throw Error('task directory must be outside Skill');
  fs.mkdirSync(root, {recursive:true, mode:0o700});
  if (fs.lstatSync(root).isSymbolicLink() || !fs.lstatSync(root).isDirectory()) throw Error('invalid task directory');
  const real = fs.realpathSync(root);
  if (real === skill || real.startsWith(skill + path.sep)) throw Error('task directory must be outside Skill');
  let value = readContext(root);
  // Legacy tasks retain their database identity; Python publishes it after opening the task.
  if (!value && (fs.existsSync(path.join(root, 'inspection.db')) || fs.existsSync(path.join(root, 'batch.json')))) return undefined;
  if (!value) {
    const temporary = path.join(root, FILE + '.' + randomUUID());
    try {
      fs.writeFileSync(temporary, JSON.stringify({task_id:randomUUID().replaceAll('-', ''), funnel_schema_version:1}), {flag:'wx', mode:0o600});
      try { fs.linkSync(temporary, path.join(root, FILE)); } catch (error) { if (error.code !== 'EEXIST') throw error; }
    } finally { try { fs.unlinkSync(temporary); } catch {} }
    value = readContext(root);
  }
  return {task_id:value.task_id, task_dir:real};
}

async function claimTask(context, mode, {newRequest = false, select = true} = {}) {
  const usageOnly = !context.task_id;
  const filename = path.join(context.task_dir, usageOnly ? '.usage-context.json' : FILE), lock = filename + '.lock';
  const deadline = Date.now() + 500;
  let fd;
  while (fd === undefined) {
    try { fd = fs.openSync(lock, 'wx', 0o600); }
    catch (error) {
      if (error.code !== 'EEXIST' || Date.now() >= deadline) throw error;
      await new Promise(resolve => setTimeout(resolve, 25));
    }
  }
  try {
    const state = readContext(context.task_dir, usageOnly) || {};
    if (!usageOnly && state.task_id !== context.task_id) throw Error('task binding mismatch');
    const events = [];
    if (!state.started || newRequest) { events.push(['skill-start.mjs']); state.started = true; }
    if (newRequest && !mode) delete state.mode;
    if (mode && select) {
      if (state.mode !== mode || newRequest) events.push(['version-selected.mjs', '--mode', mode]);
      state.mode = mode;
    }
    const temporary = filename + '.' + randomUUID();
    try {
      fs.writeFileSync(temporary, JSON.stringify(state), {flag:'wx', mode:0o600});
      fs.renameSync(temporary, filename);
    } finally { try { fs.unlinkSync(temporary); } catch {} }
    return events;
  } finally { fs.closeSync(fd); fs.unlinkSync(lock); }
}
module.exports = {reserveTask, readContext, claimTask};
