import fs from 'node:fs';
import { locateQualityReference } from './quality-runtime.mjs';

// 命令词词表：加载机检词表（带内置兜底），并统计正文里的命令式措辞频次。
// 用于机器质检对「绝不能/务必/必须」等命令表达的密度控制。

const BUILTIN_LEXICON = Object.freeze({
  schemaVersion: 'fallback-1',
  safeAdverbs: ['格外', '尤其', '前所未有', '全面地', '极其', '彻底', '大幅', '显著', '非常'],
  imperativeClassA: ['务必', '无论如何', '一定', '绝不能', '必须'],
  protectedPhrases: ['高度复杂', '深度工作', '高度专业', '深度阅读', '高度不确定', '深度学习'],
  imperativeAutoFixMap: { 一定: '通常', 必须: '需要', 务必: '建议', 绝不能: '应避免', 无论如何: '综合来看' },
  safeAdverbAutoFixMap: {},
});

function asList(value, fallback) {
  return Array.isArray(value) ? [...value] : [...fallback];
}

/** 读取命令词词表，与内置默认合并；文件缺失/损坏时退回内置词表。 */
export function loadImperativeLexicon(bundleRoot) {
  const sourcePath = locateQualityReference(bundleRoot, 'directive-lexicon.json');
  let configured = {};
  try {
    configured = JSON.parse(fs.readFileSync(sourcePath, 'utf8').replace(/^\uFEFF/, ''));
  } catch {
    configured = {};
  }
  return {
    ...BUILTIN_LEXICON,
    ...configured,
    safeAdverbs: asList(configured.safeAdverbs, BUILTIN_LEXICON.safeAdverbs),
    imperativeClassA: asList(configured.imperativeClassA, BUILTIN_LEXICON.imperativeClassA),
    protectedPhrases: asList(configured.protectedPhrases, BUILTIN_LEXICON.protectedPhrases),
    imperativeAutoFixMap: { ...BUILTIN_LEXICON.imperativeAutoFixMap, ...configured.imperativeAutoFixMap },
    safeAdverbAutoFixMap: { ...configured.safeAdverbAutoFixMap },
    _sourcePath: sourcePath,
  };
}

// 「一定」等词在这些语境里不算命令，扫描前先抹掉，避免误报。
const NON_IMPERATIVE_PATTERNS = [
  /不一定/gu,
  /不必须/gu,
  /(?:有|需有|需要|具备|保持|维持|达到|经过|留出)一定(?:的)?(?:规模|程度|数量|比例|范围|水平|基础|条件|阶段|时期|时间|距离|角度|限度|份额|经验|弹性|空间)?/gu,
  /在一定(?:程度|范围)(?:上|内)?/gu,
  /占一定比例/gu,
];

// 去掉代码块、注释与非命令语境，得到用于命令词统计的纯净文本。
function stripNonImperative(raw) {
  let text = String(raw)
    .replace(/```[\s\S]*?```/gu, ' ')
    .replace(/<!--[\s\S]*?-->/gu, ' ');
  for (const pattern of NON_IMPERATIVE_PATTERNS) text = text.replace(pattern, ' ');
  return text;
}

function toLiteralRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/gu, '\\$&');
}

/** 统计文本里各命令词（imperativeClassA）的出现次数，长词优先，返回 {词: 次数}。 */
export function countImperativeHits(text, lexicon) {
  const cleaned = stripNonImperative(text);
  const terms = [...new Set(lexicon.imperativeClassA || [])]
    .filter(Boolean)
    .sort((left, right) => right.length - left.length);
  const tally = {};
  for (const term of terms) {
    const matches = cleaned.match(new RegExp(toLiteralRegex(term), 'gu'));
    if (matches?.length) tally[term] = matches.length;
  }
  return tally;
}
