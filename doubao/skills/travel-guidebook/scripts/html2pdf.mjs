/**
 * HTML → PDF 导出脚本（Playwright + Chromium）
 *
 * 用法：
 *   node html2pdf.mjs input.html              # 指定输入文件
 *   node html2pdf.mjs input.html output.pdf   # 指定输入和输出
 */

import { chromium } from "playwright";
import { resolve } from "path";
import { existsSync } from "fs";

const inputFile = process.argv[2];
if (!inputFile) {
  console.error("用法: node html2pdf.mjs <input.html> [output.pdf]");
  process.exit(1);
}
const outputFile = process.argv[3] || inputFile.replace(/\.html?$/, ".pdf");

const inputPath = resolve(inputFile);
if (!existsSync(inputPath)) {
  console.error(`文件不存在: ${inputPath}`);
  process.exit(1);
}

const fileUrl = `file://${inputPath}`;

console.log(`输入: ${inputPath}`);
console.log(`输出: ${resolve(outputFile)}`);
console.log("正在启动 Chromium...");

const browser = await chromium.launch();
const page = await browser.newPage();

// 等待字体和图标 CDN 加载
await page.goto(fileUrl, { waitUntil: "networkidle", timeout: 30000 });

// 额外等待字体渲染完成
await page.waitForTimeout(2000);

console.log("正在生成 PDF...");

await page.pdf({
  path: resolve(outputFile),
  format: "A4",
  printBackground: true,
  margin: {
    top: "2cm",
    bottom: "2.5cm",
    left: "1.8cm",
    right: "1.8cm",
  },
  displayHeaderFooter: true,
  headerTemplate: "<span></span>",
  footerTemplate: `
    <div style="width:100%; text-align:center; font-size:9pt; color:#87867f; font-family:'JetBrains Mono',monospace;">
      <span class="pageNumber"></span>
    </div>
  `,
});

await browser.close();

console.log(`✅ PDF 导出完成: ${resolve(outputFile)}`);
