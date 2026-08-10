import fs from 'node:fs';
import path from 'node:path';

// 规模档位解析：把「目标字数 / 计划章节数」映射到 S/M/L/XL 写作策略档，
// 供写作契约门在长稿场景给出对应的分批与深度建议。
// 仅实现本仓 style-contract-gate 实际依赖的能力，不含未使用的分卷换算。

const TIER_LADDER = ['S', 'M', 'L', 'XL'];

/** 读取 references/volume-tiers.json（兼容 Windows BOM）。 */
export function loadScaleTiers(bundleRoot) {
  const configPath = path.resolve(bundleRoot, 'references', 'volume-tiers.json');
  const raw = fs.readFileSync(configPath, 'utf8').replace(/^\uFEFF/, '');
  return JSON.parse(raw);
}

// 在 {S_max, M_max, L_max} 阶梯里给一个正数定档；非正数或缺失落到最低档 S。
function classify(value, ceilings) {
  if (!Number.isFinite(value) || value <= 0) return 'S';
  for (let index = 0; index < TIER_LADDER.length - 1; index += 1) {
    const tier = TIER_LADDER[index];
    const ceiling = Number(ceilings?.[`${tier}_max`]);
    if (Number.isFinite(ceiling) && value <= ceiling) return tier;
  }
  return 'XL';
}

// 取两个档位里更高的那个（XL > L > M > S）。
function higherTier(left, right) {
  return TIER_LADDER.indexOf(left) >= TIER_LADDER.indexOf(right) ? left : right;
}

/**
 * 综合目标字数与计划章节数定写作策略档。两者都缺（非正）时返回 null。
 * @returns {{ tier: string, byWords: string, byChapters: string, policy: string } | null}
 */
export function pickWritingStrategyTier(targetWords, plannedChapters, tiers) {
  const words = Number(targetWords);
  const chapters = Number(plannedChapters);
  const hasWords = Number.isFinite(words) && words > 0;
  const hasChapters = Number.isFinite(chapters) && chapters > 0;
  if (!hasWords && !hasChapters) return null;

  const strategy = tiers.skillWritingStrategy;
  const byWords = hasWords ? classify(words, strategy.byTargetWords) : 'S';
  const byChapters = hasChapters ? classify(chapters, strategy.byPlannedChapters) : 'S';
  const tier = higherTier(byWords, byChapters);
  return { tier, byWords, byChapters, policy: strategy.policyByTier?.[tier] || '' };
}
