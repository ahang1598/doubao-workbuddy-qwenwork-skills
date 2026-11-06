#!/usr/bin/env node

/*
 * |-----------------------------------------------------------
 * | Copyright (c) 2026 huawei.com, Inc. All Rights Reserved
 * |-----------------------------------------------------------
 * | File: index.js
 * | Created: 2026-03-17
 * | Updated: 2026-05-06
 * | Description: 图片搜索技能 CLI 入口
 * |   支持原始URL输出模式 和 下载到本地模式 (--download <dir>)
 * |-----------------------------------------------------------
 */

const { searchImages } = require('./image_search.js');
const fs = require('fs');
const path = require('path');
const os = require('os');
const http = require('http');
const https = require('https');
const crypto = require('crypto');

const TLS_COMPAT_ERROR_CODES = new Set([
    'CERT_HAS_EXPIRED',
    'DEPTH_ZERO_SELF_SIGNED_CERT',
    'ERR_SSL_CERT_ALTNAME_INVALID',
    'ERR_SSL_PROTOCOL_ERROR',
    'EPROTO',
    'SELF_SIGNED_CERT_IN_CHAIN',
    'UNABLE_TO_GET_ISSUER_CERT',
    'UNABLE_TO_GET_ISSUER_CERT_LOCALLY',
    'UNABLE_TO_VERIFY_LEAF_SIGNATURE'
]);

/**
 * 生成默认下载目录路径
 * @returns {string} 默认下载目录 <系统临时目录>/xiaoyi-image-search/{随机8位}
 */
function getDefaultDownloadDir() {
    const sn = crypto.randomBytes(4).toString('hex'); // 8位十六进制随机字符串
    // Windows 桌面用系统临时目录（%TEMP%），Linux 沙箱为 /tmp
    return path.join(os.tmpdir(), 'xiaoyi-image-search', sn);
}

/** Direct-delivery mode: persist images below the current task workspace. */
function getWorkspaceDownloadDir(query) {
    const safeQuery = String(query || '图片')
        .replace(/[<>:"/\\|?*\x00-\x1f]/g, '_')
        .replace(/[. ]+$/g, '')
        .slice(0, 40) || '图片';
    const sn = crypto.randomBytes(4).toString('hex');
    return path.join(process.cwd(), '图片搜索', `${safeQuery}-${sn}`);
}

function isTrustedHuaweiStorageUrl(rawUrl) {
    try {
        const hostname = new URL(rawUrl).hostname.toLowerCase();
        return hostname === 'huaweicloud.com'
            || hostname.endsWith('.huaweicloud.com')
            || hostname === 'myhuaweicloud.com'
            || hostname.endsWith('.myhuaweicloud.com')
            || hostname === 'hwcloudtest.cn'
            || hostname.endsWith('.hwcloudtest.cn');
    } catch (_) {
        return false;
    }
}

function isTlsCompatibilityError(error) {
    return Boolean(error && TLS_COMPAT_ERROR_CODES.has(error.code));
}

/** 执行单次图片下载；仅内部兼容重试可传 allowInsecureTls=true。 */
function requestDownload(url, dest, allowInsecureTls = false, redirectCount = 0) {
    return new Promise((resolve, reject) => {
        const protocol = url.startsWith('https') ? https : http;
        const requestOptions = url.startsWith('https') ? { rejectUnauthorized: !allowInsecureTls } : {};
        protocol.get(url, requestOptions, (response) => {
            // 处理重定向
            if (response.statusCode >= 300 && response.statusCode < 400 && response.headers.location) {
                response.resume();
                if (redirectCount >= 5) {
                    reject(new Error('图片下载重定向过多'));
                    return;
                }
                const nextUrl = new URL(response.headers.location, url).toString();
                const keepCompatibility = allowInsecureTls && isTrustedHuaweiStorageUrl(nextUrl);
                return requestDownload(nextUrl, dest, keepCompatibility, redirectCount + 1).then(resolve).catch(reject);
            }
            if (response.statusCode < 200 || response.statusCode >= 300) {
                response.resume();
                reject(new Error(`图片下载 HTTP ${response.statusCode}`));
                return;
            }
            const file = fs.createWriteStream(dest);
            response.pipe(file);
            file.on('finish', () => {
                file.close();
                resolve(dest);
            });
            file.on('error', (err) => {
                try { fs.unlinkSync(dest); } catch (_) {}
                reject(err);
            });
        }).on('error', (err) => {
            try { fs.unlinkSync(dest); } catch (_) {}
            reject(err);
        });
    });
}

/**
 * 从 URL 下载文件到本地。默认严格校验 TLS；仅当可信的华为
 * OSMS/OBS 地址遇到证书链或握手兼容错误时，对当次下载关闭校验重试一次。
 */
async function downloadFile(url, dest) {
    try {
        return await requestDownload(url, dest);
    } catch (error) {
        try { fs.unlinkSync(dest); } catch (_) {}
        if (!isTrustedHuaweiStorageUrl(url) || !isTlsCompatibilityError(error)) throw error;
        console.error(`TLS 校验失败，正在对 OSMS/OBS 图片进行兼容重试: ${error.code || error.message}`);
        return requestDownload(url, dest, true);
    }
}

/**
 * 下载模式输出格式（不返回原图URL，只返回本地路径）
 * 输出为表格行形式：标题 | 尺寸 | 本地路径 | 来源页面
 */
function formatDownloadOutput(image, index, localPath) {
    const title = (image.img_title || '(无标题)').replace(/\|/g, '\\|');
    const size = `${image.img_width || '?'} x ${image.img_height || '?'}`;
    const path = (localPath || '(下载失败)').replace(/\|/g, '\\|');
    const source = (image.img_from_url || '(无)').replace(/\|/g, '\\|');

    return `| ${index} | ${title} | ${size} | \`${path}\` | ${source} |`;
}

/**
 * 原始URL输出格式（向后兼容）
 * 输出为表格行形式：序号 | 标题 | 尺寸 | 原图URL | 缩略图 | 来源页面
 */
function formatUrlResult(image, index) {
    const title = (image.img_title || '(无标题)').replace(/\|/g, '\\|');
    const size = `${image.img_width || '?'} x ${image.img_height || '?'}`;
    const oriUrl = (image.img_ori_url || '(无)').replace(/\|/g, '\\|');
    const thumbUrl = (image.img_thumb_url || '(无)').replace(/\|/g, '\\|');
    const source = (image.img_from_url || '(无)').replace(/\|/g, '\\|');

    return `| ${index} | ${title} | ${size} | ${oriUrl} | ${thumbUrl} | ${source} |`;
}

/**
 * 主处理函数
 * @param {string} query - 搜索关键词
 * @param {number} numResults - 返回结果数量
 * @param {string} store - 图片存储方式
 * @param {string|null} downloadDir - 下载目录（提供则下载到本地，否则输出URL）
 */
async function main(query, numResults, store, downloadDir) {
    const maxRetries = 3;
    let attempt = 0;
    let lastError = null;

    while (attempt < maxRetries) {
        try {
            console.error(`=== 图片搜索开始 (第${attempt + 1}次尝试) ===`);
            const images = await searchImages(query, numResults, store);

            if (downloadDir) {
                // === 下载模式（流式：逐张下载并立即输出） ===
                fs.mkdirSync(downloadDir, { recursive: true });
                console.error(`正在下载图片到: ${downloadDir}`);

                // 输出下载目录路径（方便 claw 提取用于后续清理）
                console.log(`<<<DOWNLOAD_DIR:${downloadDir}>>>`);

                // 输出表头
                console.log('| 序号 | 标题 | 尺寸 | 本地路径 | 来源页面 |');
                console.log('|:---|:---|:---|:---|:---|');

                for (let i = 0; i < images.length; i++) {
                    const img = images[i];
                    const ext = '.jpg';
                    const filename = `image_${String(i + 1).padStart(2, '0')}${ext}`;
                    const dest = path.join(downloadDir, filename);

                    let localPath = null;
                    if (img.img_ori_url) {
                        try {
                            await downloadFile(img.img_ori_url, dest);
                            localPath = dest;
                        } catch (err) {
                            console.error(`下载第${i + 1}张图片失败: ${err.message}`);
                        }
                    }

                    // 立即输出该图片的行信息
                    console.log(formatDownloadOutput(img, i + 1, localPath));
                }
                console.error(`\n图片搜索完成，关键词: "${query}"，共 ${images.length} 条结果`);
            } else {
                // === URL 输出模式（向后兼容） ===
                console.error(`图片搜索完成，关键词: "${query}"，共 ${images.length} 条结果\n`);

                // 输出表头
                console.log('| 序号 | 标题 | 尺寸 | 原图URL | 缩略图 | 来源页面 |');
                console.log('|:---|:---|:---|:---|:---|:---|');

                for (let i = 0; i < images.length; i++) {
                    console.log(formatUrlResult(images[i], i + 1));
                }
                console.error(`\n提示: 原图URL为OSMS预签名链接，可直接下载使用`);
            }
            return;
        } catch (error) {
            lastError = error;
            console.error(`图片搜索失败 (第${attempt + 1}次): ${error.message}`);
            attempt++;
            if (attempt < maxRetries) {
                console.error('正在重试...');
            }
        }
    }
    console.error(`图片搜索失败: ${lastError ? lastError.message : '未知错误'}`);
    process.exit(1);
}

// 命令行接口
if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length < 1) {
        console.error('用法: node index.js <query> [num_results] [store] [--download <dir>] [--workspace] [--url]');
        console.error('  query       - 搜索关键词（必填）');
        console.error('  num_results - 返回结果数量（默认5）');
        console.error('  store       - 存储方式（默认 osms）');
        console.error('  --download  - 下载模式，将图片保存到指定目录（可选，默认使用系统临时目录/xiaoyi-image-search/{sn}）');
        console.error('  --workspace - 直接交付模式，保存到当前任务工作空间的 图片搜索/ 子目录');
        console.error('  --url       - URL输出模式，返回原图链接（向后兼容）');
        console.error('');
        console.error('示例:');
        console.error('  node index.js "黄山"                  # 默认下载模式，自动保存到系统临时目录/xiaoyi-image-search/{sn}');
        console.error('  node index.js "黄山" 4                # 搜索4张，默认下载模式');
        console.error('  node index.js "黄山" --download <目录> # 指定下载目录');
        console.error('  node index.js "黄山" --workspace       # 保存为任务工作空间中的最终交付文件');
        console.error('  node index.js "黄山" --url            # URL输出模式（旧行为）');
        process.exit(1);
    }

    const query = args[0];
    let numResults = 5;
    let store = 'osms';
    let downloadDir = getDefaultDownloadDir(); // 默认启用下载模式
    let useUrlMode = false; // 是否使用URL模式
    let useWorkspaceMode = false;

    for (let i = 1; i < args.length; i++) {
        if (args[i] === '--download') {
            const nextArg = args[++i];
            if (nextArg && !nextArg.startsWith('--')) {
                downloadDir = nextArg;
            } else {
                // --download 后面没有目录参数，使用默认值，回退索引
                i--;
            }
        } else if (args[i] === '--url') {
            useUrlMode = true;
        } else if (args[i] === '--workspace') {
            useWorkspaceMode = true;
        } else if (/^\d+$/.test(args[i])) {
            numResults = parseInt(args[i], 10);
        } else {
            store = args[i];
        }
    }

    // 如果指定了 --url，则禁用下载模式
    if (useUrlMode) {
        downloadDir = null;
    } else if (useWorkspaceMode) {
        downloadDir = getWorkspaceDownloadDir(query);
    }

    main(query, numResults, store, downloadDir).catch(error => {
        console.error(`处理失败: ${error.message}`);
        process.exit(1);
    });
}

module.exports = { main };
