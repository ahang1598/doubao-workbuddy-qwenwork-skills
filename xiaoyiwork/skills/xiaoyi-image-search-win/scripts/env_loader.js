/*
 * |-----------------------------------------------------------
 * | Copyright (c) 2026 huawei.com, Inc. All Rights Reserved
 * |-----------------------------------------------------------
 * | File: env_loader.js
 * | Created: 2026-03-17
 * | Description: 环境变量加载器，支持从 .env 文件加载配置
 * |-----------------------------------------------------------
 */

const fs = require('fs');
const os = require('os');
const path = require('path');

// 固定值
const FIXED_VALUES = {
    ACP2SERVICE_ENV_KEY: 'ACP2SERVICE_ENV',
    // 旧沙箱默认 env 文件在用户主目录下（Windows 桌面为 %USERPROFILE%\.openclaw\.xiaoyienv）
    DEFAULT_ENV: path.join(os.homedir(), '.openclaw', '.xiaoyienv'),
};

/**
 * 加载环境变量文件
 * @param {string} envFilePath - 环境变量文件路径
 * @returns {object} 配置对象
 */
function loadEnvFile(envFilePath) {
    const config = {};

    if (!fs.existsSync(envFilePath)) {
        // 桌面形态默认无旧沙箱 env 文件，属正常情况，静默返回（配置从进程环境变量读取）
        return config;
    }

    try {
        const content = fs.readFileSync(envFilePath, 'utf8');
        const lines = content.split('\n');

        for (const line of lines) {
            // 跳过注释和空行
            const trimmedLine = line.trim();
            if (!trimmedLine || trimmedLine.startsWith('#')) {
                continue;
            }

            // 处理 export 关键字（如：export SERVICE_URL=...）
            let lineToParse = trimmedLine;
            if (lineToParse.startsWith('export ')) {
                lineToParse = lineToParse.substring(7).trim();
            }

            // 解析键值对 - 支持带连字符的变量名
            const match = lineToParse.match(/^([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*(.*)$/);
            if (match) {
                const key = match[1];
                let value = match[2];

                // 去除引号
                if ((value.startsWith('"') && value.endsWith('"')) ||
                    (value.startsWith("'") && value.endsWith("'"))) {
                    value = value.substring(1, value.length - 1);
                }

                // 去除尾部的注释
                const commentIndex = value.indexOf('#');
                if (commentIndex !== -1) {
                    value = value.substring(0, commentIndex).trim();
                }

                config[key] = value.trim();
            }
        }

        console.error(`从 ${envFilePath} 加载了 ${Object.keys(config).length} 个环境变量`);
    } catch (error) {
        console.error(`加载环境变量文件失败: ${error.message}`);
    }

    return config;
}

/**
 * 获取环境变量配置
 * 优先级: 1. ACP2SERVICE_ENV 变量指定的env，2. .env文件中的变量 3系统环境变量
 * @returns {object} 配置对象
 */
function getEnvConfig() {
    const config = {};
    // 我们需要检查所有可能的变量名
    const allPossibleVars = [
        // 新鉴权方式变量
        'SERVICE_URL',
        'SERVICE-URL',
        'PERSONAL_UID',
        'PERSONAL-UID',
        'PERSONAL_API_KEY',
        'PERSONAL-API-KEY',
        // 桌面形态管道代理本机防借用令牌（主进程注入）
        'CLAW_SKILL_TOKEN',
    ];
    // 1.检查系统环境变量
    for (const envVar of allPossibleVars) {
        if (process.env[envVar]) {
            config[envVar] = process.env[envVar];
        }
    }
    // 2.加载.env文件
    const envConfig = loadEnvFile(FIXED_VALUES.DEFAULT_ENV);
    for (const envVar of allPossibleVars) {
        if (envConfig[envVar]) {
            config[envVar] = envConfig[envVar];
        }
    }
    // 3.加载ACP2SERVICE_ENV指定文件
    if (process.env[FIXED_VALUES.ACP2SERVICE_ENV_KEY]) {
        const acpEnvConfig = loadEnvFile(process.env[FIXED_VALUES.ACP2SERVICE_ENV_KEY]);
        for (const envVar of allPossibleVars) {
            if (acpEnvConfig[envVar]) {
                config[envVar] = acpEnvConfig[envVar];
            }
        }
    }
    return config;
}

module.exports = {
    loadEnvFile,
    getEnvConfig
};
