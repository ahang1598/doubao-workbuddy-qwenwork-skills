#!/usr/bin/env node

/**
 * smart-writer 字数统计工具
 * 用法: node count-chars.js <文件路径>
 * 
 * 统计维度：中文字符、英文单词、数字、emoji、总字数、段落数、预计阅读时间
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
  const resolved = fs.realpathSync ? 
    path.resolve(filePath) : 
    path.resolve(process.cwd(), filePath);
  
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
// 统计函数
// ============================================================

/**
 * 清理 Markdown 标记
 */
function cleanMarkdown(text) {
  return text
    .replace(/^#{1,6}\s+/gm, '')       // 标题标记
    .replace(/\*{1,2}([^*]+)\*{1,2}/g, '$1') // 加粗/斜体
    .replace(/!\[.*?\]\(.*?\)/g, '')    // 图片
    .replace(/\[([^\]]+)\]\(.*?\)/g, '$1') // 链接（保留文字）
    .replace(/```[\s\S]*?```/g, '')     // 代码块
    .replace(/`([^`]+)`/g, '$1')        // 行内代码（保留文字）
    .replace(/^>\s+/gm, '')             // 引用标记
    .replace(/^[-*+]\s+/gm, '')         // 无序列表标记
    .replace(/^\d+\.\s+/gm, '')         // 有序列表标记
    .replace(/---+/g, '')               // 分隔线
    .replace(/\|/g, ' ');               // 表格分隔符
}

/**
 * 详细字数统计
 */
function countDetailed(text) {
  const cleaned = cleanMarkdown(text);

  const chineseChars = (cleaned.match(/[\u4e00-\u9fff]/g) || []).length;
  const chinesePunctuation = (cleaned.match(/[\u3000-\u303f\uff00-\uffef]/g) || []).length;
  const englishWords = (cleaned.match(/[a-zA-Z]+/g) || []).length;
  const numbers = (cleaned.match(/\d+/g) || []).length;

  const cleanedForEmoji = cleaned
    .replace(/[─━│┌┐└┘├┤┬┴┼╌╍╎╏═║╔╗╚╝╠╣╦╩╬▔▕▀▁▂▃▄▅▆▇█▉▊▋▌▍▎▏]/g, '')
    .replace(/[◆◇◈○●◎■□▪▫▲△▼▽◀▶►◄♠♣♥♦]/g, '');
  const emojiRegex = /[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{1F900}-\u{1F9FF}]|[\u{2702}-\u{27B0}\u{27BF}]|[\u{2600}-\u{26FF}]/gu;
  const emojiCount = (cleanedForEmoji.match(emojiRegex) || []).length;

  // 总字数（中文字符 + 英文单词 + 数字，不含标点和 emoji）
  const totalWords = chineseChars + englishWords + numbers;

  // 段落统计
  const paragraphs = text.split(/\n\s*\n/).filter(p => p.trim().length > 0);
  const paragraphCount = paragraphs.length;

  // 预计阅读时间（中文阅读速度约 400-600 字/分钟，取 500）
  const readingTimeMinutes = Math.ceil(totalWords / 500);

  // 小标题统计
  const headings = (text.match(/^#{1,6}\s+.+$/gm) || []);
  const headingCount = headings.length;

  // 图片/配图需求统计
  const imageCount = (text.match(/!\[.*?\]\(.*?\)/g) || []).length;
  const imageSlotCount = (text.match(/【配图需求.*?】/g) || []).length;

  return {
    chineseChars,
    chinesePunctuation,
    englishWords,
    numbers,
    emojiCount,
    totalWords,
    paragraphCount,
    headingCount,
    imageCount,
    imageSlotCount,
    readingTimeMinutes,
  };
}

// ============================================================
// CLI 入口
// ============================================================

function main() {
  const filePath = process.argv[2];

  if (!filePath) {
    console.log('用法: node count-chars.js <文件路径>');
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
  const stats = countDetailed(content);

  // 提取标题
  const titleMatch = content.match(/^#\s+(.+)$/m);
  const title = titleMatch ? titleMatch[1].trim() : '(未检测到)';

  // 输出报告
  console.log('\n📊 字数统计报告');
  console.log('─'.repeat(50));
  console.log(`📝 标题: ${title}`);
  console.log('─'.repeat(50));

  console.log('\n📏 字数明细:');
  console.log(`  中文字符:    ${stats.chineseChars} 字`);
  console.log(`  英文单词:    ${stats.englishWords} 词`);
  console.log(`  数字:        ${stats.numbers} 个`);
  console.log(`  中文标点:    ${stats.chinesePunctuation} 个`);
  console.log(`  emoji:       ${stats.emojiCount} 个`);
  console.log(`  ─────────────────────`);
  console.log(`  📊 总字数:    ${stats.totalWords} 字（不含标点和 emoji）`);

  console.log('\n📄 结构统计:');
  console.log(`  段落数:      ${stats.paragraphCount}`);
  console.log(`  小标题数:    ${stats.headingCount}`);
  console.log(`  图片/链接:   ${stats.imageCount} 个`);
  console.log(`  配图需求位:  ${stats.imageSlotCount} 个`);

  console.log(`\n⏱️ 预计阅读时间: ${stats.readingTimeMinutes} 分钟`);

  // 平台适配建议
  console.log('\n📱 平台适配参考:');
  const platforms = [
    { name: '微信公众号', min: 1000, max: 5000 },
    { name: '今日头条', min: 800, max: 3000 },
    { name: '百家号', min: 800, max: 3000 },
    { name: '小红书', min: 300, max: 1000 },
    { name: '微博', min: 140, max: 2000 },
  ];

  for (const platform of platforms) {
    let status;
    if (stats.totalWords < platform.min) {
      status = `❌ 不足 (需 ≥ ${platform.min})`;
    } else if (stats.totalWords > platform.max) {
      status = `⚠️ 超标 (需 ≤ ${platform.max})`;
    } else {
      status = '✅ 合适';
    }
    console.log(`  ${platform.name}: ${status}`);
  }

  console.log('');
}

main();
