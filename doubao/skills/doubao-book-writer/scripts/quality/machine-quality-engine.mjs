import fs from 'node:fs';
import path from 'node:path';
import { globSync } from '../lib/simple-glob.mjs';
import { prepareQualityScanSurface, normalizeRel, scanSkipGlobs, locateQualityReference } from '../lib/quality-runtime.mjs';
import { countImperativeHits, loadImperativeLexicon } from '../lib/directive-lexicon.mjs';
import { resolveSafePath } from '../lib/path-safety.mjs';

const CONNECTORS = ['在此基础上', '总而言之', '由此可见', '总的来说', '需要指出的是', '值得注意的是', '综上所述', '而且', '再者', '其次', '同时', '另外', '此外'];
const ABSOLUTE_CLAIMS = [
  new RegExp('\\u5168\\u7403\\u6700[\\u5927\\u5c0f\\u5f3a\\u5f31]', 'u'),
  new RegExp('\\u884c\\u4e1a\\u7b2c\\u4e00', 'u'),
  new RegExp('\\u552f\\u4e00[\\u4e00\\u652f\\u6301\\u63d0\\u4f9b]', 'u'),
  new RegExp('\\u5b8c\\u5168\\u65e0\\u6cd5', 'u'),
  new RegExp('\\u7edd\\u5bf9[\\u4e0d\\u65e0]', 'u'),
  new RegExp('100%(?:\\u4fdd\\u8bc1|\\u786e\\u4fdd|\\u6b63\\u786e)', 'u'),
];
const REPLACEMENTS = Object.freeze({
  层面: '方面', 视角: '角度', 维度: '方面', 整合: '合并', 融合: '结合', 联动: '一起动作', 协同: '配合',
  中台: '中间平台', 生态: '协作体系', 矩阵: '组合', 组合拳: '组合策略', 卡点: '关键点', 卡位: '抢位',
  势能: '优势', 心智: '认知', 拉齐: '统一', 对齐: '统一', 拉通: '连起来', 打通: '连起来',
  颗粒度: '细致程度', 闭环: '完整流程', 沉淀: '积累', 全链路: '全流程', 链路: '流程',
  底层能力: '基础能力', 底座: '基础', 抓手: '切入点', 赋能: '让……能做……',
});
const REPLACEMENT_ENTRIES = Object.freeze(Object.entries(REPLACEMENTS).sort((left, right) => right[0].length - left[0].length));

function parse(argv, defaultBundleRoot) {
  const args = { bundleRoot: defaultBundleRoot, workspace: process.cwd(), inputs: [], glob: null, globCwd: null, extraGlobInputs: [], profile: null, userSetGlob: false, manuscriptDoubleGlob: false, dashDensity: false, checkSectionIds: false, intPercentDensity: false, enforce: false, enforceStrict: false, failOnS6Warn: false, failOnS5Buzz: false, failOnLongSentenceWarn: false, failOnAbsoluteClaims: false, vcrHeuristicWarn: false, standalone: false, autoFix: false, write: false, json: false, jsonOut: null, directiveBudget: false, warnImperative: false };
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--bundle-root') args.bundleRoot = argv[++index] || args.bundleRoot;
    else if (token === '--workspace') args.workspace = argv[++index] || args.workspace;
    else if (token === '--inputs' || token === '--input') args.inputs.push(argv[++index]);
    else if (token === '--glob') { args.glob = argv[++index]; args.userSetGlob = true; }
    else if (token === '--profile') args.profile = argv[++index];
    else if (token === '--json-out') args.jsonOut = argv[++index] || null;
    else if (token === '--inputs-file') args.inputsFile = argv[++index] || null;
    else {
      const flags = { '--dash-density': 'dashDensity', '--check-section-ids': 'checkSectionIds', '--int-percent-density': 'intPercentDensity', '--enforce': 'enforce', '--fail-on-s6-warn': 'failOnS6Warn', '--fail-on-s5-buzz': 'failOnS5Buzz', '--fail-on-long-sentence-warn': 'failOnLongSentenceWarn', '--fail-on-absolute-claims': 'failOnAbsoluteClaims', '--vcr-heuristic-warn': 'vcrHeuristicWarn', '--standalone': 'standalone', '--auto-fix': 'autoFix', '--write': 'write', '--json': 'json', '--directive-budget': 'directiveBudget', '--warn-imperative': 'warnImperative' };
      if (token === '--enforce-strict') { args.enforce = true; args.enforceStrict = true; }
      else if (flags[token]) args[flags[token]] = true;
    }
  }
  args.bundleRoot = path.resolve(args.bundleRoot);
  args.workspace = path.resolve(args.workspace);
  if (args.profile === 'manuscript' && !args.userSetGlob) { args.manuscriptDoubleGlob = true; args.warnImperative = true; }
  if (args.profile === 'reference-doc' && !args.userSetGlob) {
    args.glob = '{references,sub-skills}/**/*.md';
    args.globCwd = args.bundleRoot;
    const entryDoc = path.join(args.bundleRoot, 'SKILL.md');
    if (fs.existsSync(entryDoc)) args.extraGlobInputs.push(entryDoc);
  }
  if (args.profile === 'manuscript-full') Object.assign(args, { manuscriptDoubleGlob: true, userSetGlob: false, warnImperative: true, enforce: true, enforceStrict: true, checkSectionIds: true, failOnS6Warn: true, failOnS5Buzz: true, failOnLongSentenceWarn: true, failOnAbsoluteClaims: true, vcrHeuristicWarn: true, directiveBudget: true });
  return args;
}

function filesFor(args) {
  const files = new Set(args.inputs.filter(Boolean).map((file) => path.resolve(args.workspace, file)));
  if (args.inputsFile) {
    try { fs.readFileSync(path.resolve(args.inputsFile), 'utf8').split(/\r?\n/).map((line) => line.trim()).filter(Boolean).forEach((file) => files.add(path.resolve(args.workspace, file))); } catch { /* optional list */ }
  }
  const root = args.globCwd || args.workspace;
  const patterns = args.manuscriptDoubleGlob ? ['manuscript/**/*.md', 'deliverables/**/*.md'] : (args.glob ? [args.glob] : []);
  for (const pattern of patterns) globSync(pattern, { cwd: root, absolute: true, ignore: scanSkipGlobs }).forEach((file) => files.add(file));
  args.extraGlobInputs.forEach((file) => files.add(path.resolve(file)));
  return [...files].filter((file) => fs.existsSync(file));
}

function loadBuzzwords(bundleRoot) {
  let configured = [];
  try { configured = JSON.parse(fs.readFileSync(locateQualityReference(bundleRoot, 'cliche-catalog.json'), 'utf8')).terms || []; } catch { /* fallback below */ }
  return [...new Set([...configured, '首当其冲', '举足轻重', '至关重要', '尤为重要', '不得不提', '值得注意的是', '毋庸置疑', '不言而喻', '多维度', '综合考量', '系统梳理', '全面解析', '深度剖析', '深入分析', '深入探讨'])];
}

function countTerms(text, terms) {
  return Object.fromEntries(terms.map((term) => [term, text.split(term).length - 1]).filter(([, count]) => count > 0));
}

function duplicateIds(text) {
  const ids = text.split(/\r?\n/).map((line) => line.match(/^#{2,3}\s+(\d+\.\d+(?:\.\d+)?)/)?.[1]).filter(Boolean);
  return [...new Set(ids.filter((id, index) => ids.indexOf(id) !== index))];
}

function vcrIssues(text) {
  const magnitude = new RegExp('[\\d,.]+\\s*(?:%|\\u4e07|\\u4ebf|\\u5343\\u4e07)', 'u');
  const sourceMark = new RegExp('〔\\u6765\\u6e90[：:]|【\\u6765\\u6e90[：:]|（\\u6765\\u6e90[：:]|\\[\\u6765\\u6e90[：:]', 'u');
  return text.split(/\r?\n/).flatMap((line, index) => magnitude.test(line) && !sourceMark.test(line) ? [`line ${index + 1}: numeric claim lacks source mark`] : []).slice(0, 5);
}

function measure(text, lexicon, buzzwords) {
  const compact = Math.max(1, text.replace(/\s+/g, '').length);
  const sentenceLengths = text.split(/[。！？\n]/).map((item) => item.replace(/\s+/g, '').length).filter(Boolean);
  const connectors = countTerms(text, CONNECTORS);
  let adverbText = text;
  for (const phrase of lexicon.protectedPhrases || []) adverbText = adverbText.replaceAll(phrase, '');
  const adverbs = countTerms(adverbText, lexicon.safeAdverbs || []);
  const imperative = countImperativeHits(text, lexicon);
  return {
    chars: compact,
    dashDensity: Number((((text.match(/——/g) || []).length * 1000) / compact).toFixed(2)),
    intPercentDensity: Number((((text.match(/\d+%/g) || []).length * 1000) / compact).toFixed(2)),
    longSentenceRatio: Number(((sentenceLengths.filter((length) => length > 40).length * 100) / Math.max(sentenceLengths.length, 1)).toFixed(2)),
    duplicateSectionIds: duplicateIds(text),
    absoluteClaims: ABSOLUTE_CLAIMS.filter((pattern) => pattern.test(text)).map(String),
    vcrIssues: vcrIssues(text),
    connectors,
    connectorDensity: Number((Object.values(connectors).reduce((sum, value) => sum + value, 0) * 1000 / compact).toFixed(2)),
    adverbs,
    adverbDensity: Number((Object.values(adverbs).reduce((sum, value) => sum + value, 0) * 1000 / compact).toFixed(2)),
    imperative,
    imperativeTotal: Object.values(imperative).reduce((sum, value) => sum + value, 0),
    buzz: buzzwords.filter((term) => text.includes(term)),
  };
}

function classify(metrics, args, fileName) {
  const issues = [];
  const warnings = [];
  const add = (blocking, message) => (blocking ? issues : warnings).push(message);
  if (metrics.dashDensity > 3) add(args.enforce || args.enforceStrict, `[S6-dash] ${fileName}: em dash density ${metrics.dashDensity}/k > 3（hard limit）`);
  else if (metrics.dashDensity > 1) add(args.failOnS6Warn || args.enforceStrict, `[S6-dash] ${fileName}: em dash density ${metrics.dashDensity}/k > 1（review band）`);
  if ((args.checkSectionIds || args.enforce || args.enforceStrict) && metrics.duplicateSectionIds.length) add(args.enforce || args.enforceStrict, `[编号重复] ${fileName}: ${metrics.duplicateSectionIds.join(', ')}`);
  if (args.intPercentDensity && metrics.intPercentDensity > 10) warnings.push(`[numeric-percent] ${fileName}: ${metrics.intPercentDensity}/k，比例数字偏密`);
  if ((args.failOnS5Buzz || args.enforce || args.enforceStrict) && metrics.buzz.length) add(args.failOnS5Buzz || args.enforceStrict, `[cliche] ${fileName}: ${metrics.buzz.slice(0, 5).join('、')}${metrics.buzz.length > 5 ? '…' : ''}`);
  if ((args.failOnLongSentenceWarn || args.enforce || args.enforceStrict) && metrics.longSentenceRatio > 8) add(args.failOnLongSentenceWarn || args.enforceStrict, `[sentence-length] ${fileName}: overlong ratio ${metrics.longSentenceRatio}% > 8%`);
  if ((args.failOnAbsoluteClaims || args.enforce || args.enforceStrict) && metrics.absoluteClaims.length) add(args.failOnAbsoluteClaims || args.enforceStrict, `[absolute-claim] ${fileName}: ${metrics.absoluteClaims.length} rule(s) matched`);
  if (args.vcrHeuristicWarn) metrics.vcrIssues.forEach((issue) => warnings.push(`[VCR-P2] ${fileName}: ${issue}`));
  if (args.warnImperative && metrics.imperativeTotal > 0) warnings.push(`[directive-a] ${fileName}: total=${metrics.imperativeTotal}（${Object.entries(metrics.imperative).map(([term, count]) => `${term}×${count}`).join('、')}）；按 sentence-discipline.md 的全书预算复核`);
  return { issues, warnings };
}

function escapeRegex(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function autoFix(text, lexicon) {
  const changes = [];
  let fenced = false;
  const lines = text.split(/\r?\n/).map((line, index) => {
    const before = line;
    if (/^```/.test(line.trim())) { fenced = !fenced; return line; }
    if (fenced) return line;
    line = line.replace(new RegExp(`(^|[。！？；\\s])(?:${CONNECTORS.join('|')})([，、：:]?)`, 'g'), (_, lead) => lead || '');
    for (const [from, to] of Object.entries(lexicon.imperativeAutoFixMap || {})) if (!['必须', '务必', '一定'].includes(from) && to) line = line.replace(new RegExp(escapeRegex(from), 'g'), to);
    for (const [from, to] of REPLACEMENT_ENTRIES) line = line.replaceAll(from, to);
    line = line.replace(/——+/g, '，').replace(/，{2,}/g, '，').replace(/。{2,}/g, '。').replace(/，。/g, '。').replace(/^[，：]/, '');
    if (line !== before) changes.push({ line: index + 1, before, after: line });
    return line;
  });
  return { text: lines.join('\n'), changes };
}

function diffMarkdown(changed, workspace) {
  const body = changed.map(({ filePath, candidatePath, changes }) => `## ${normalizeRel(filePath, workspace)}\n\n- 候选文件：\`${candidatePath.replace(/\\/g, '/')}\`\n- 修改数：${changes.length}\n\n${changes.map((item) => `- 第 ${item.line} 行\n  - 原文：${item.before || '（空）'}\n  - 建议：${item.after || '（空）'}`).join('\n')}`).join('\n\n---\n\n');
  return `# auto-fix diff\n\n> 默认不覆盖原文；使用 \`--write\` 才会回写。\n\n${body}\n`;
}

function backupBeforeWrite(filePath, workspace, backupRoot, ordinal) {
  const relative = normalizeRel(filePath, workspace);
  const safeRelative = relative === '..' || relative.startsWith('../') || path.isAbsolute(relative)
    ? `${ordinal}-${path.basename(filePath)}`
    : relative;
  const target = path.join(backupRoot, safeRelative);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(filePath, target, fs.constants.COPYFILE_EXCL);
  return target;
}

export function runMachineQualityCli(argv, defaultBundleRoot) {
  const args = parse(argv, defaultBundleRoot);
  const files = filesFor(args);
  if (files.length === 0) { console.error('machine-quality: no markdown inputs; pass --inputs or --glob'); return 2; }
  if (args.autoFix || args.write) {
    try {
      for (const file of files) resolveSafePath(args.workspace, file, { mustExist: true, forbidden: ['.doubao-book-writer'] });
    } catch (error) {
      console.error(`machine-quality: ${error.message}`);
      return 2;
    }
  }
  const bootstrap = args.standalone || !fs.existsSync(path.join(args.workspace, '.doubao-book-writer'));
  const runtime = bootstrap ? prepareQualityScanSurface(args.workspace, { files }) : { qcOutputDir: path.join(args.workspace, 'qc-output') };
  fs.mkdirSync(runtime.qcOutputDir, { recursive: true });
  const lexicon = loadImperativeLexicon(args.bundleRoot);
  const buzzwords = loadBuzzwords(args.bundleRoot);
  const results = [];
  const issues = [];
  const warnings = [];
  const changed = [];
  const writeBackupRoot = args.autoFix && args.write
    ? path.join(args.workspace, '.doubao-book-writer', 'backups', `quality-auto-fix-${Date.now()}`)
    : null;
  let directiveBookTotal = 0;
  for (const filePath of files) {
    const text = fs.readFileSync(filePath, 'utf8');
    const metrics = measure(text, lexicon, buzzwords);
    directiveBookTotal += metrics.imperativeTotal;
    const buckets = classify(metrics, args, path.basename(filePath));
    issues.push(...buckets.issues); warnings.push(...buckets.warnings);
    const result = { filePath, metrics, issues: buckets.issues, warnings: buckets.warnings };
    if (args.autoFix) {
      const fixed = autoFix(text, lexicon);
      if (fixed.changes.length > 0) {
        const candidatePath = path.join(runtime.qcOutputDir, 'auto-fix', normalizeRel(filePath, args.workspace));
        fs.mkdirSync(path.dirname(candidatePath), { recursive: true });
        fs.writeFileSync(candidatePath, fixed.text, 'utf8');
        const backupPath = args.write
          ? backupBeforeWrite(filePath, args.workspace, writeBackupRoot, changed.length + 1)
          : null;
        if (args.write) fs.writeFileSync(filePath, fixed.text, 'utf8');
        changed.push({ filePath, candidatePath, changes: fixed.changes });
        result.autoFix = { candidatePath, backupPath, changeCount: fixed.changes.length, appliedToSource: Boolean(args.write) };
      }
    }
    results.push(result);
    if (!args.json) {
      if (args.dashDensity || (!args.checkSectionIds && !args.intPercentDensity)) console.log(`${path.basename(filePath)}: dashPerK=${metrics.dashDensity.toFixed(2)}`);
      if (args.intPercentDensity) console.log(`${path.basename(filePath)}: integerPercentPerK=${metrics.intPercentDensity.toFixed(2)}`);
    }
  }
  if (args.directiveBudget && directiveBookTotal > 3) issues.push(`[directive-budget] total=${directiveBookTotal}, limit=3；请把强制语气改为条件、风险或理由表述，再加 --warn-imperative 复验`);
  let diffPath = null;
  if (args.autoFix && changed.length > 0) { diffPath = path.join(runtime.qcOutputDir, 'auto-fix-diff.md'); fs.writeFileSync(diffPath, diffMarkdown(changed, args.workspace), 'utf8'); }
  const summary = { timestamp: new Date().toISOString(), standalone: bootstrap, workspace: args.workspace, total: results.length, directiveBookTotal, issueCount: issues.length, warningCount: warnings.length, issues, warnings, autoFix: args.autoFix ? { diffPath, changedFiles: changed.length, write: Boolean(args.write) } : null, results };
  const reportPath = path.resolve(args.jsonOut || path.join(runtime.qcOutputDir, 'quality-audit-machine.json'));
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.writeFileSync(reportPath, `${JSON.stringify(summary, null, 2)}\n`, 'utf8');
  summary.reportPath = reportPath;
  if (args.json) console.log(JSON.stringify(summary, null, 2));
  else {
    warnings.forEach((warning) => console.log(`  ⚠ ${warning}`));
    issues.forEach((issue) => console.log(`  ✗ ${issue}`));
    if (issues.length === 0 && warnings.length === 0) console.log('machine-quality: ✅ 通过');
    if (diffPath) console.log(`machine-quality: 🛠 已生成 auto-fix diff → ${diffPath}`);
    console.log(`machine-quality: 报告 → ${reportPath}`);
  }
  return issues.length > 0 ? 1 : 0;
}
