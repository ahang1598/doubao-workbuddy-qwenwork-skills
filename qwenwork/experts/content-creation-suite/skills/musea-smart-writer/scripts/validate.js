#!/usr/bin/env node

/**
 * smart-writer 多平台验证脚本
 * 用法: node validate.js --file <文件路径> --platform <平台名>
 * 
 * 支持平台: wechat, toutiao, baijiahao, xhs, weibo
 */

const fs = require('fs');
const path = require('path');

// ============================================================
// 安全路径校验
// ============================================================

// 允许的文件扩展名
const ALLOWED_EXTENSIONS = ['.md', '.markdown', '.txt'];
// 禁止访问的敏感目录
const SENSITIVE_DIRS = ['/etc', '/var', '/usr', '/bin', '/sbin', '/boot', '/root', '/proc', '/sys', '/dev'];

/**
 * 校验文件路径安全性，防止路径遍历和任意文件读取
 * @param {string} filePath - 待校验的文件路径
 * @param {string} description - 文件描述（用于错误提示）
 * @returns {string} 解析后的安全绝对路径
 * @throws {Error} 路径不合法时抛出
 */
function validatePath(filePath, description = '文件') {
  if (!filePath || !filePath.trim()) {
    throw new Error(`${description}路径不能为空`);
  }

  // 解析为绝对路径（消除 ../ 等相对路径）
  const resolved = path.resolve(process.cwd(), filePath);

  // 如果文件存在，用 realpathSync 解析符号链接
  let realResolved = resolved;
  if (fs.existsSync(resolved)) {
    realResolved = fs.realpathSync(resolved);
  }

  // 检查路径遍历：确保路径在当前工作目录或用户目录下
  const cwd = process.cwd();
  const homeDir = require('os').homedir();

  const pathAllowed = (
    realResolved.startsWith(cwd + path.sep) || realResolved === cwd ||
    realResolved.startsWith(homeDir + path.sep) || realResolved === homeDir
  );

  if (!pathAllowed) {
    throw new Error(
      `${description}路径不安全：不允许访问工作目录或用户目录之外的文件。` +
      `路径：${filePath} -> ${realResolved}`
    );
  }

  // 检查是否在敏感目录中
  for (const sensitive of SENSITIVE_DIRS) {
    if (realResolved.startsWith(sensitive + path.sep) || realResolved === sensitive) {
      throw new Error(`${description}路径不安全：禁止访问系统敏感目录 ${sensitive}`);
    }
  }

  // 检查文件扩展名
  const ext = path.extname(realResolved).toLowerCase();
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    throw new Error(
      `${description}扩展名不合法：'${ext}'，允许的扩展名：${ALLOWED_EXTENSIONS.join(', ')}`
    );
  }

  return realResolved;
}

// ============================================================
// 平台规范定义
// ============================================================

const PLATFORM_RULES = {
  wechat: {
    name: '微信公众号',
    minChars: 1000,
    maxChars: 5000,
    titleMinLen: 10,
    titleMaxLen: 64,
    titleRecommendMax: 28,
    maxParagraphChars: 200,
    requireCTA: true,
    maxConsecutiveEmoji: 3,
    emojiDensity: 'moderate', // low, moderate, high
  },
  toutiao: {
    name: '今日头条',
    minChars: 800,
    maxChars: 3000,
    titleMinLen: 10,
    titleMaxLen: 30,
    titleRecommendMax: 30,
    maxParagraphChars: 150,
    requireCTA: true,
    maxConsecutiveEmoji: 3,
    emojiDensity: 'moderate',
  },
  baijiahao: {
    name: '百家号',
    minChars: 800,
    maxChars: 3000,
    titleMinLen: 10,
    titleMaxLen: 30,
    titleRecommendMax: 30,
    maxParagraphChars: 200,
    requireCTA: true,
    maxConsecutiveEmoji: 3,
    emojiDensity: 'low',
  },
  xhs: {
    name: '小红书',
    minChars: 300,
    maxChars: 1000,
    titleMinLen: 3,
    titleMaxLen: 20,
    titleRecommendMax: 20,
    maxParagraphChars: 100,
    requireCTA: true,
    requireHashtags: true,
    minHashtags: 3,
    maxHashtags: 5,
    maxConsecutiveEmoji: 3,
    emojiDensity: 'high',
  },
  weibo: {
    name: '微博',
    minChars: 140,
    maxChars: 2000,
    titleMinLen: 0,
    titleMaxLen: 100,
    titleRecommendMax: 100,
    maxParagraphChars: 100,
    requireCTA: true,
    requireTopicTag: true,
    maxConsecutiveEmoji: 3,
    emojiDensity: 'moderate',
  },
};

// ============================================================
// 工具函数
// ============================================================

/**
 * 统计中文字符数（排除标点、空格、Markdown 标记）
 */
function countChineseChars(text) {
  const cleaned = text
    .replace(/^#{1,6}\s+/gm, '')       // 移除 Markdown 标题标记
    .replace(/\*{1,2}([^*]+)\*{1,2}/g, '$1') // 移除加粗/斜体标记
    .replace(/!\[.*?\]\(.*?\)/g, '')    // 移除图片链接
    .replace(/\[.*?\]\(.*?\)/g, '')     // 移除链接
    .replace(/```[\s\S]*?```/g, '')     // 移除代码块
    .replace(/`[^`]+`/g, '')            // 移除行内代码
    .replace(/[-—·…·◆│├└┤┬┼]/g, '')    // 移除特殊分隔符
    .replace(/---+/g, '')               // 移除分隔线
    .replace(/\s+/g, '');               // 移除空白

  // 匹配中文字符、英文单词和数字
  const chineseChars = (cleaned.match(/[\u4e00-\u9fff]/g) || []).length;
  const englishWords = (cleaned.match(/[a-zA-Z]+/g) || []).length;
  const numbers = (cleaned.match(/\d+/g) || []).length;

  return chineseChars + englishWords + numbers;
}

/**
 * 提取标题（第一个 # 标题）
 */
function extractTitle(text) {
  const titleMatch = text.match(/^#\s+(.+)$/m);
  return titleMatch ? titleMatch[1].trim() : null;
}

/**
 * 提取段落列表
 */
function extractParagraphs(text) {
  const lines = text.split('\n');
  const paragraphs = [];
  let currentParagraph = '';

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed === '' || trimmed.startsWith('#') || trimmed === '---' || trimmed === '···') {
      if (currentParagraph.trim()) {
        paragraphs.push(currentParagraph.trim());
      }
      currentParagraph = '';
    } else {
      currentParagraph += trimmed + ' ';
    }
  }
  if (currentParagraph.trim()) {
    paragraphs.push(currentParagraph.trim());
  }

  return paragraphs;
}

/**
 * 真正的 emoji 正则（仅匹配常见表情符号，排除 Unicode 绘图字符和通用符号）
 */
function getEmojiRegex() {
  return /[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{1F900}-\u{1F9FF}]|[\u{2702}-\u{27B0}\u{27BF}]|[\u{2600}-\u{26FF}]|[\u{FE00}-\u{FE0F}]|\u{200D}|\u{20E3}|[\u{E0020}-\u{E007F}]/gu;
}

/**
 * 统计 emoji（先清理 Markdown 中的 Unicode 绘图字符再统计）
 */
function countEmoji(text) {
  // 先移除 Markdown 表格绘图字符和装饰分隔符
  const cleaned = text
    .replace(/[─━│┌┐└┘├┤┬┴┼╌╍╎╏═║╔╗╚╝╠╣╦╩╬▔▕▀▁▂▃▄▅▆▇█▉▊▋▌▍▎▏]/g, '')
    .replace(/[◆◇◈○●◎■□▪▫▲△▼▽◀▶►◄♠♣♥♦]/g, '');
  const matches = cleaned.match(getEmojiRegex()) || [];
  return matches.length;
}

/**
 * 检测连续 emoji
 */
function findConsecutiveEmoji(text) {
  const cleaned = text
    .replace(/[─━│┌┐└┘├┤┬┴┼╌╍╎╏═║╔╗╚╝╠╣╦╩╬▔▕▀▁▂▃▄▅▆▇█▉▊▋▌▍▎▏]/g, '')
    .replace(/[◆◇◈○●◎■□▪▫▲△▼▽◀▶►◄♠♣♥♦]/g, '');
  const emojiRegex = getEmojiRegex();
  let maxConsecutive = 0;
  let current = 0;
  let lastEnd = -2;

  let match;
  while ((match = emojiRegex.exec(cleaned)) !== null) {
    // 允许 emoji 之间有少量空白（最多 2 个字符间距）
    if (match.index <= lastEnd + 2) {
      current++;
    } else {
      current = 1;
    }
    maxConsecutive = Math.max(maxConsecutive, current);
    lastEnd = match.index + match[0].length;
  }

  return maxConsecutive;
}

/**
 * 检测 CTA（互动引导）
 */
function hasCTA(text) {
  const ctaPatterns = [
    /评论/, /留言/, /讨论/, /说说/,
    /关注/, /转发/, /分享/, /收藏/,
    /点赞/, /在看/, /点个赞/,
    /你怎么看/, /你觉得/, /你有/,
    /欢迎.*?交流/, /一起.*?聊/,
    /👇/, /评论区/,
  ];
  return ctaPatterns.some(pattern => pattern.test(text));
}

/**
 * 检测微博话题标签
 */
function hasTopicTag(text) {
  return /#[^#]+#/.test(text);
}

/**
 * 检测小红书标签
 */
function countHashtags(text) {
  const hashtags = text.match(/#\S+/g) || [];
  // 过滤掉微博双标签格式
  return hashtags.filter(tag => !/#[^#]+#/.test(tag)).length;
}

// ============================================================
// 验证引擎
// ============================================================

function validate(content, platform) {
  const rules = PLATFORM_RULES[platform];
  if (!rules) {
    return { success: false, errors: [`未知平台: ${platform}`], warnings: [] };
  }

  const errors = [];
  const warnings = [];

  // 1. 字数检查
  const charCount = countChineseChars(content);
  if (charCount < rules.minChars) {
    errors.push(`❌ 字数不足: ${charCount} 字（最少 ${rules.minChars} 字）`);
  }
  if (charCount > rules.maxChars) {
    errors.push(`❌ 字数超标: ${charCount} 字（最多 ${rules.maxChars} 字）`);
  }

  // 2. 标题检查
  const title = extractTitle(content);
  if (title) {
    const titleLen = title.length;
    if (titleLen < rules.titleMinLen) {
      warnings.push(`⚠️ 标题过短: ${titleLen} 字（建议至少 ${rules.titleMinLen} 字）`);
    }
    if (titleLen > rules.titleMaxLen) {
      errors.push(`❌ 标题过长: ${titleLen} 字（最多 ${rules.titleMaxLen} 字）`);
    }
    if (titleLen > rules.titleRecommendMax) {
      warnings.push(`⚠️ 标题较长: ${titleLen} 字（建议 ≤ ${rules.titleRecommendMax} 字）`);
    }
  } else {
    warnings.push('⚠️ 未检测到标题（# 开头的一级标题）');
  }

  // 3. 段落长度检查
  const paragraphs = extractParagraphs(content);
  const longParagraphs = paragraphs.filter(
    p => countChineseChars(p) > rules.maxParagraphChars
  );
  if (longParagraphs.length > 0) {
    warnings.push(
      `⚠️ ${longParagraphs.length} 个段落超过 ${rules.maxParagraphChars} 字，建议拆分`
    );
  }

  // 4. CTA 检查
  if (rules.requireCTA && !hasCTA(content)) {
    warnings.push('⚠️ 未检测到互动引导（CTA），建议在结尾添加');
  }

  // 5. emoji 检查
  const consecutiveEmoji = findConsecutiveEmoji(content);
  if (consecutiveEmoji > rules.maxConsecutiveEmoji) {
    errors.push(
      `❌ 检测到连续 ${consecutiveEmoji} 个 emoji（最多连续 ${rules.maxConsecutiveEmoji} 个）`
    );
  }

  const emojiCount = countEmoji(content);
  const emojiPerKChar = (emojiCount / (charCount / 1000)).toFixed(1);
  if (rules.emojiDensity === 'low' && emojiPerKChar > 5) {
    warnings.push(`⚠️ emoji 密度偏高: ${emojiPerKChar}/千字（${rules.name} 建议克制使用）`);
  }
  if (rules.emojiDensity === 'high' && emojiPerKChar < 3 && charCount > 200) {
    warnings.push(`⚠️ emoji 密度偏低: ${emojiPerKChar}/千字（${rules.name} 建议增加 emoji）`);
  }

  // 6. 平台特殊检查
  if (rules.requireTopicTag && !hasTopicTag(content)) {
    errors.push('❌ 微博文章缺少话题标签（#话题名# 格式）');
  }

  if (rules.requireHashtags) {
    const hashtagCount = countHashtags(content);
    if (hashtagCount < rules.minHashtags) {
      warnings.push(
        `⚠️ 标签不足: ${hashtagCount} 个（建议 ${rules.minHashtags}-${rules.maxHashtags} 个）`
      );
    }
  }

  return {
    success: errors.length === 0,
    charCount,
    title: title || '(未检测到)',
    paragraphCount: paragraphs.length,
    emojiCount,
    errors,
    warnings,
  };
}

// ============================================================
// CLI 入口
// ============================================================

function main() {
  const args = process.argv.slice(2);

  let filePath = null;
  let platform = null;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--file' && args[i + 1]) {
      filePath = args[++i];
    } else if (args[i] === '--platform' && args[i + 1]) {
      platform = args[++i];
    }
  }

  if (!filePath || !platform) {
    console.log('用法: node validate.js --file <文件路径> --platform <平台名>');
    console.log('');
    console.log('支持平台: wechat, toutiao, baijiahao, xhs, weibo');
    process.exit(1);
  }

  // 安全校验文件路径
  let validatedPath;
  try {
    validatedPath = validatePath(filePath, '输入文件');
  } catch (e) {
    console.error(`❌ 路径校验失败: ${e.message}`);
    process.exit(1);
  }

  if (!fs.existsSync(validatedPath)) {
    console.error(`❌ 文件不存在: ${validatedPath}`);
    process.exit(1);
  }

  const content = fs.readFileSync(validatedPath, 'utf-8');
  const result = validate(content, platform);

  // 输出结果
  const platformName = PLATFORM_RULES[platform]?.name || platform;
  console.log(`\n📋 验证报告 — ${platformName}`);
  console.log('─'.repeat(50));
  console.log(`📝 标题: ${result.title}`);
  console.log(`📊 字数: ${result.charCount} 字`);
  console.log(`📄 段落数: ${result.paragraphCount}`);
  console.log(`😊 emoji 数: ${result.emojiCount}`);
  console.log('─'.repeat(50));

  if (result.errors.length > 0) {
    console.log('\n🚫 错误（必须修复）:');
    result.errors.forEach(err => console.log(`  ${err}`));
  }

  if (result.warnings.length > 0) {
    console.log('\n⚠️ 警告（建议优化）:');
    result.warnings.forEach(warn => console.log(`  ${warn}`));
  }

  if (result.success && result.warnings.length === 0) {
    console.log('\n✅ 全部通过！文章符合平台规范。');
  } else if (result.success) {
    console.log('\n✅ 基本通过（无错误），但有优化建议。');
  } else {
    console.log('\n❌ 验证未通过，请修复以上错误。');
  }

  console.log('');
  process.exit(result.success ? 0 : 1);
}

main();
