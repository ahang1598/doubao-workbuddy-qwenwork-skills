#!/usr/bin/env node

/**
 * 小红书字数计算工具
 * 用法：node scripts/count-chars.js --text "你的文本"
 * 或：node scripts/count-chars.js --file output.md
 * 输出：字数统计（含 emoji 和标点，不含空格）
 */

const fs = require('fs');

/**
 * 计算字数（不含空格）
 */
function countChars(text) {
  return text.replace(/\s/g, '').length;
}

/**
 * 计算 emoji 数量
 */
function countEmojis(text) {
  return (text.match(/[\p{Emoji}]/gu) || []).length;
}

/**
 * 计算行数
 */
function countLines(text) {
  return text.split('\n').filter(line => line.trim().length > 0).length;
}

/**
 * 主函数
 */
function main() {
  const args = process.argv.slice(2);
  
  let text = '';
  
  // 处理 --text 参数
  const textArg = args.find(arg => arg.startsWith('--text'));
  if (textArg) {
    text = textArg.split('=')[1] || args[args.indexOf('--text') + 1];
  }
  
  // 处理 --file 参数
  const fileArg = args.find(arg => arg.startsWith('--file'));
  if (fileArg) {
    const filePath = fileArg.split('=')[1] || args[args.indexOf('--file') + 1];
    if (!filePath || !fs.existsSync(filePath)) {
      console.error(`❌ 文件不存在：${filePath}`);
      process.exit(1);
    }
    text = fs.readFileSync(filePath, 'utf8');
  }
  
  if (!text) {
    console.error('❌ 用法：');
    console.error('  node scripts/count-chars.js --text "你的文本"');
    console.error('  node scripts/count-chars.js --file output.md');
    process.exit(1);
  }

  const totalChars = countChars(text);
  const emojiCount = countEmojis(text);
  const lineCount = countLines(text);
  const withoutEmoji = countChars(text.replace(/[\p{Emoji}]/gu, ''));

  console.log('\n📊 字数统计\n');
  console.log('─'.repeat(50));
  console.log(`总字数（含 emoji）    : ${totalChars} 字`);
  console.log(`总字数（不含 emoji）  : ${withoutEmoji} 字`);
  console.log(`emoji 数量            : ${emojiCount} 个`);
  console.log(`有效行数              : ${lineCount} 行`);
  console.log(`平均每行字数          : ${(totalChars / lineCount).toFixed(1)} 字`);
  console.log(`emoji 密度            : ${(emojiCount / lineCount).toFixed(2)} 个/行`);
  console.log('─'.repeat(50));

  // 检查是否符合小红书限制
  if (totalChars <= 1000) {
    console.log(`✅ 正文符合小红书限制（≤ 1000 字）`);
  } else {
    console.log(`❌ 正文超过小红书限制，需删减 ${totalChars - 1000} 字`);
  }
  
  console.log('');
}

main();
