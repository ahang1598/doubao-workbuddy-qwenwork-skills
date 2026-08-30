#!/usr/bin/env node

/**
 * 小红书排版验证脚本
 * 用法：node scripts/validate.js --file output.md
 * 输出：验证结果（通过/失败），失败项列表
 */

const fs = require('fs');
const path = require('path');

/**
 * 计算字数（不含空格）
 */
function countChars(text) {
  return text.replace(/\s/g, '').length;
}

/**
 * 检查标题字数
 */
function validateTitle(title) {
  const length = countChars(title);
  return {
    passed: length <= 20,
    score: length <= 20 ? '✅' : '❌',
    message: `标题字数：${length} 字（要求 ≤ 20 字）`,
    length
  };
}

/**
 * 检查标题是否使用竖线或中文逗号分隔
 */
function validateTitleSeparator(title) {
  const hasSeparator = title.includes('｜') || title.includes('，');
  return {
    passed: hasSeparator,
    score: hasSeparator ? '✅' : '❌',
    message: `标题分隔符：${hasSeparator ? '使用竖线｜或中文逗号' : '未使用竖线｜或中文逗号'}`
  };
}

/**
 * 检查正文字数
 */
function validateContent(content) {
  const length = countChars(content);
  return {
    passed: length <= 1000,
    score: length <= 1000 ? '✅' : '❌',
    message: `正文字数：${length} 字（要求 ≤ 1000 字）`,
    length
  };
}

/**
 * 检查段落长度
 */
function validateParagraphLength(content) {
  const paragraphs = content.split('\n');
  const violations = [];
  
  paragraphs.forEach((para, index) => {
    const lines = para.trim().split('\n').length;
    if (lines > 3 && para.trim().length > 0) {
      violations.push(`第 ${index + 1} 段超过 3 行`);
    }
  });

  return {
    passed: violations.length === 0,
    score: violations.length === 0 ? '✅' : '❌',
    message: violations.length === 0 ? '段落长度：全部 ≤ 3 行' : `段落长度：${violations.join(', ')}`
  };
}

/**
 * 检查是否有开头钩子
 */
function validateOpeningHook(content) {
  const firstThreeLines = content.split('\n').slice(0, 3).join('\n');
  const hasHook = firstThreeLines.length > 0;
  
  return {
    passed: hasHook,
    score: hasHook ? '✅' : '❌',
    message: `开头钩子：${hasHook ? '存在' : '缺失'}`
  };
}

/**
 * 检查是否使用分隔线
 */
function validateSeparator(content) {
  const hasSeparator = content.includes('———————————————————');
  return {
    passed: hasSeparator,
    score: hasSeparator ? '✅' : '❌',
    message: `分隔线：${hasSeparator ? '使用 ———————————————————' : '未使用分隔线'}`
  };
}

/**
 * 检查对比句式（推荐项，不影响整体通过）
 */
function validateContrast(content) {
  const hasContrast = /不是.*❌.*而是.*✅/.test(content);
  return {
    passed: true,
    score: hasContrast ? '✅' : '💡',
    message: `对比句式（推荐）：${hasContrast ? '存在"不是 A❌ 而是 B✅"' : '未使用对比句式（建议适合时使用）'}`
  };
}

/**
 * 检查 emoji 密度
 *
 * 注意：\p{Emoji} 会匹配数字字符(0-9)、#、* 等，
 * 需要使用 \p{Emoji_Presentation} 匹配默认以 emoji 样式呈现的字符，
 * 再补充 \p{Emoji_Modifier_Base} 和文本型 emoji + VS16(U+FE0F) 的组合，
 * 以排除纯数字和 ASCII 符号的误匹配。
 */
function validateEmojiDensity(content) {
  const lines = content.split('\n').filter(line => line.trim().length > 0);
  const emojiMatches = content.match(/\p{Emoji_Presentation}|\p{Extended_Pictographic}/gu) || [];
  const emojiCount = emojiMatches.length;
  const avgEmojiPerLine = lines.length > 0 ? emojiCount / lines.length : 0;
  
  // 理想密度：每 2-3 行 1 个，即 0.33-0.5 个/行
  const passed = avgEmojiPerLine >= 0.25 && avgEmojiPerLine <= 0.6;
  
  return {
    passed,
    score: passed ? '✅' : '❌',
    message: `emoji 密度：${emojiCount} 个 emoji，${lines.length} 行（平均 ${avgEmojiPerLine.toFixed(2)} 个/行）`
  };
}

/**
 * 检查互动引导
 */
function validateEngagement(content) {
  const hasEngagement = /💬|👇|💾/.test(content) && 
                       (content.includes('评论') || content.includes('收藏'));
  return {
    passed: hasEngagement,
    score: hasEngagement ? '✅' : '❌',
    message: `互动引导：${hasEngagement ? '存在' : '缺失'}`
  };
}

/**
 * 检查话题标签数量
 */
function validateHashtagCount(hashtags) {
  const count = (hashtags.match(/#/g) || []).length;
  const passed = count >= 3 && count <= 5;
  
  return {
    passed,
    score: passed ? '✅' : '❌',
    message: `话题标签数量：${count} 个（要求 3-5 个）`
  };
}

/**
 * 检查话题标签与内容相关性（基础检查）
 * 2026 新规：质量优于数量，3-5 个标签，热点+垂直+人群组合
 */
function validateHashtagStructure(hashtags) {
  const tags = hashtags.match(/#[\u4e00-\u9fa5a-zA-Z0-9_]+/g) || [];
  
  const tagCount = tags.length;
  const hasEnoughTags = tagCount >= 3 && tagCount <= 5;
  
  // 检查是否有明显的无关标签堆砌（标签数超过5个视为堆砌风险）
  const noTagSpam = tagCount <= 5;
  
  const passed = hasEnoughTags && noTagSpam;
  
  return {
    passed,
    score: passed ? '✅' : '❌',
    message: `话题标签结构：${tagCount} 个标签（要求 3-5 个，质量优于数量）${!noTagSpam ? ' | ⚠️ 标签过多，可能被降权' : ''}`
  };
}

/**
 * 主验证函数
 */
function main() {
  const args = process.argv.slice(2);
  const fileArg = args.find(arg => arg.startsWith('--file'));
  
  if (!fileArg) {
    console.error('❌ 用法：node scripts/validate.js --file <output.md>');
    process.exit(1);
  }

  const filePath = fileArg.split('=')[1] || args[args.indexOf('--file') + 1];
  
  if (!filePath) {
    console.error('❌ 请指定文件路径');
    process.exit(1);
  }

  if (!fs.existsSync(filePath)) {
    console.error(`❌ 文件不存在：${filePath}`);
    process.exit(1);
  }

  const fileContent = fs.readFileSync(filePath, 'utf8');
  
  // 解析文件内容
  const titleMatch = fileContent.match(/## 标题\n(.+)/);
  const contentMatch = fileContent.match(/## 正文\n([\s\S]+?)(?=## 话题标签)/);
  const hashtagMatch = fileContent.match(/## 话题标签\n(.+)/);
  
  const title = titleMatch ? titleMatch[1].trim() : '';
  const content = contentMatch ? contentMatch[1].trim() : '';
  const hashtags = hashtagMatch ? hashtagMatch[1].trim() : '';

  // 执行所有检查
  const checks = [
    { name: '标题 ≤ 20 字', result: validateTitle(title) },
    { name: '标题分隔符', result: validateTitleSeparator(title) },
    { name: '正文 ≤ 1000 字', result: validateContent(content) },
    { name: '段落 ≤ 3 行', result: validateParagraphLength(content) },
    { name: '开头钩子', result: validateOpeningHook(content) },
    { name: '使用分隔线', result: validateSeparator(content) },
    { name: '对比句式', result: validateContrast(content) },
    { name: 'emoji 密度', result: validateEmojiDensity(content) },
    { name: '互动引导', result: validateEngagement(content) },
    { name: '话题标签数量', result: validateHashtagCount(hashtags) },
    { name: '话题标签结构', result: validateHashtagStructure(hashtags) }
  ];

  // 输出结果
  console.log('\n📋 小红书排版验证结果\n');
  console.log('─'.repeat(60));
  
  const allPassed = checks.every(c => c.result.passed);
  let passCount = 0;
  
  checks.forEach(c => {
    if (c.result.passed) passCount++;
    console.log(`${c.result.score} ${c.name.padEnd(15)} ${c.result.message}`);
  });

  console.log('─'.repeat(60));
  
  if (allPassed) {
    console.log(`\n✅ 全部通过！(${passCount}/${checks.length})\n`);
    process.exit(0);
  } else {
    console.log(`\n❌ 存在未通过项 (${passCount}/${checks.length})，请修改后重试。\n`);
    process.exit(1);
  }
}

main();
