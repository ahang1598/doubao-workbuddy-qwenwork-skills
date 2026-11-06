#!/usr/bin/env node

/**
 * 家庭简报数据收集脚本
 * 整合所有数据获取步骤为单一脚本执行
 *
 * 使用方法:
 * node family-brief-data-collector.js
 * node family-brief-data-collector.js --home-id {家庭ID}
 *
 */

import { exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const execAsync = promisify(exec);

// ES module 兼容: 获取 __dirname 和 __filename
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 配置路径
const CONFIG = {
    basePath: path.resolve(__dirname, '../../..'),
    outputDir: path.resolve(__dirname, '../out_put/family_brief'),
    commonSkillBin: path.resolve(__dirname, '../../../common-skill/bin'),
    routerSkillBin: path.resolve(__dirname, '../../../router-skill/bin')
};

// ==================== 直接导入模块函数 ====================
import { getHomesInfo } from '../../../common-skill/bin/get_homes_info.js';
import { getDeviceServiceSnapshot } from '../../../common-skill/bin/get_devices_info.js';
import { getDeviceHistories } from '../../../common-skill/bin/get_device_histories.js';
import { hagSkillServicePostBody, hagControl, generateTraceId } from '../../../utils/hag-connect/utils.js';

// 执行命令并返回结果
async function execCommand(cmd) {
    try {
        const result = await execAsync(cmd, {
            encoding: 'utf-8',
            cwd: CONFIG.basePath,
            maxBuffer: 50 * 1024 * 1024
        });
        return { success: true, data: result.stdout };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

// 创建输出目录
function ensureOutputDir() {
    if (!fs.existsSync(CONFIG.outputDir)) {
        fs.mkdirSync(CONFIG.outputDir, { recursive: true });
    }
}



// 保存数据到文件
function saveData(filename, data) {
    const filepath = path.join(CONFIG.outputDir, filename);
    fs.writeFileSync(filepath, typeof data === 'object' ? JSON.stringify(data, null, 2) : data);
    return filepath;
}

// 第一步：获取家庭信息
async function fetchHomesInfo() {
    console.log('[1/12] 获取家庭信息...');
    try {
        const result = await getHomesInfo();
        console.log('  [OK] 获取家庭信息成功');
        return result;
    } catch (error) {
        console.log('  [FAIL] 获取家庭信息失败:', error.message);
        return null;
    }
}

// 第三步：获取所有设备详细信息
async function fetchDevicesDetail(devicesInfo) {
    console.log('[3/12] 获取设备详细信息...');

    if (!devicesInfo || !Array.isArray(devicesInfo)) {
        console.log('  [SKIP] 设备信息为空，跳过详细信息获取');
        return [];
    }

    const devIds = [];
    devicesInfo.forEach((device) => {
        const devId = device.devId || device.deviceId;
        if (devId) {
            devIds.push(devId);
        }
    });

    const BATCH_SIZE = 200;
    const totalDevices = devIds.length;
    const batchCount = Math.ceil(totalDevices / BATCH_SIZE);

    console.log(`  [INFO] 共 ${totalDevices} 个设备，需分 ${batchCount} 批查询`);

    // 并行执行所有批次查询
    const batchPromises = [];
    for (let i = 0; i < batchCount; i++) {
        const startIndex = i * BATCH_SIZE;
        const endIndex = Math.min(startIndex + BATCH_SIZE, totalDevices);
        const batchDevIds = devIds.slice(startIndex, endIndex);

        batchPromises.push((async (batchIndex, start, end) => {
            console.log(`  [FETCHING] 正在查询第 ${batchIndex + 1}/${batchCount} 批 (${start + 1}-${end} 个设备)...`);

            try {
                const data = await getDeviceServiceSnapshot(batchDevIds);
                console.log(`  [OK] 第 ${batchIndex + 1}/${batchCount} 批查询成功`);
                return data;
            } catch (error) {
                console.log(`  [FAIL] 第 ${batchIndex + 1}/${batchCount} 批查询失败:`, error.message);
                return [];
            }
        })(i, startIndex, endIndex));
    }

    const allResults = await Promise.all(batchPromises);
    console.log(`  [OK] 设备详细信息获取完成`);
    const flattenedResults = allResults.flat();
    return flattenedResults;
}

// 获取儿童上网保护数据（接收路由设备列表）
async function getChildProtectData(routerDevices) {
    if (!routerDevices || !Array.isArray(routerDevices) || routerDevices.length === 0) {
        return null;
    }

    // 使用 hagControl API 直接调用
    const childProtectDataPromises = routerDevices.map(async (router, index) => {
        const devId = router.devId;
        const prodId = router.prodId;

        if (!devId || !prodId) {
            console.log(`  [SKIP] 路由 ${index + 1}/${routerDevices.length} 缺少 devId 或 prodId`);
            return null;
        }

        try {
            // 调用儿童上网保护接口
            const res = await hagControl({
                devId,
                prodId,
                mode: 'ACK',
                operation: 'GET',
                sid: '.sys/gateway/ntwk/childHomepage'
            }, false);

            // 解析嵌套响应结构：res.data 是字符串 "{\"payload\":\"[...]\"}"
            let childDevices = [];
            try {
                const innerData = typeof res.data === 'string' ? JSON.parse(res.data) : res.data;
                const payloadStr = innerData?.payload || '[]';
                const payloadData = typeof payloadStr === 'string' ? JSON.parse(payloadStr) : payloadStr;
                childDevices = Array.isArray(payloadData) ? payloadData : [];
            } catch (parseError) {
                console.log(`  [WARN] 解析儿童保护数据失败: ${parseError.message}`);
            }

            // 提取每个儿童的今日上网情况
            const childrenInfo = childDevices.map(child => {
                const todayTime = child?.today?.time || {};
                return {
                    deviceId: child?.device || '',
                    name: child?.actualName || child?.hostName || '未知设备',
                    macAddress: child?.address || '',
                    totalTime: todayTime.total || 0,      // 今日上网总时长（秒）
                    gameTime: todayTime.game || 0,         // 游戏时长（秒）
                    videoTime: todayTime.video || 0,       // 视频时长（秒）
                    studyTime: todayTime.study || 0,       // 学习时长（秒）
                    socialTime: todayTime.social || 0,     // 社交时长（秒）
                    otherTime: todayTime.other || 0        // 其他时长（秒）
                };
            });

            console.log(`  [OK] 路由 ${index + 1}/${routerDevices.length} 儿童保护数据获取成功`);
            return {
                routerId: devId,
                routerName: router.devName,
                children: childrenInfo
            };
        } catch (error) {
            console.log(`  [FAIL] 路由 ${index + 1}/${routerDevices.length} 获取失败:`, error.message);
            return null;
        }
    });

    const childProtectDataResults = await Promise.all(childProtectDataPromises);
    const childProtectData = childProtectDataResults.filter(item => item !== null);
    console.log(`  [OK] 儿童保护数据获取完成`);
    return childProtectData;
}

// 获取门锁历史记录（接收门锁设备列表）
async function getLockHistory(lockDevices) {
    if (!lockDevices || !Array.isArray(lockDevices) || lockDevices.length === 0) {
        return null;
    }

    // 并行查询所有门锁设备
    const lockHistoryDataPromises = lockDevices.map(async (lock, index) => {
        const devId = lock.devId || lock.deviceId;
        if (!devId) return null;

        try {
            const data = await getDeviceHistories({ devId, sid: 'eventData', date: 'today' });
            console.log(`  [OK] 门锁 ${index + 1}/${lockDevices.length} 历史记录获取成功`);
            return {
                devId: devId,
                data: data
            };
        } catch (error) {
            console.log(`  [FAIL] 门锁 ${index + 1}/${lockDevices.length} 获取失败:`, error.message);
            return null;
        }
    });

    const lockHistoryDataResults = await Promise.all(lockHistoryDataPromises);
    const lockHistoryData = lockHistoryDataResults.filter(item => item !== null);

    console.log(`  [OK] 门锁历史记录获取完成`);
    return lockHistoryData;
}

// 第八步：获取睡眠数据
async function getSleepData() {
    console.log('[8/10] 获取睡眠数据...');
    const cmd = `node ${path.join(CONFIG.commonSkillBin, 'pha-claw.js')} get_sleep --date today`;
    const result = await execCommand(cmd);

    if (result.success) {
        console.log(`  [OK] 睡眠数据获取完成`);
        return JSON.parse(result.data);
    } else {
        console.log('  [FAIL] 获取睡眠数据失败');
        return null;
    }
}
// 第九步：获取活动数据
async function getActivityData() {
    console.log('[9/10] 获取活动数据...');
    const cmd = `node ${path.join(CONFIG.commonSkillBin, 'pha-claw.js')} get_activity_data --date today`;
    const result = await execCommand(cmd);

    if (result.success) {
        console.log(`  [OK] 活动数据获取完成`);
        return JSON.parse(result.data);
    } else {
        console.log('  [FAIL] 获取活动数据失败');
        return null;
    }
}

// 第十步：获取情绪数据
async function getEmotionData() {
    console.log('[10/10] 获取情绪数据...');
    const cmd = `node ${path.join(CONFIG.commonSkillBin, 'pha-claw.js')} get_emotion --date today`;
    const result = await execCommand(cmd);

    if (result.success) {
        console.log(`  [OK] 情绪数据获取完成`);
        return JSON.parse(result.data);
    } else {
        console.log('  [FAIL] 获取情绪数据失败');
        return null;
    }
}
// 主函数
async function main() {
    console.log('========================================');
    console.log('  家庭简报数据收集脚本');
    console.log('========================================\n');

    ensureOutputDir();

    // 解析命令行参数
    const args = process.argv.slice(2);
    let specifiedHomeId = null;
    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--home-id' && args[i + 1]) {
            specifiedHomeId = args[i + 1];
            break;
        }
    }

    const startTime = Date.now();

    // 第一阶段：获取家庭列表（确定 homeId）
    console.log('=== 第一阶段：获取家庭列表 ===');
    const homesInfo = await fetchHomesInfo();

    // 确定要查询的家庭 ID
    let targetHomeId = specifiedHomeId;
    if (!targetHomeId && homesInfo?.data?.homes?.length === 1) {
        targetHomeId = homesInfo.data.homes[0].homeId;
    }

    // 第二阶段：调用 getFamilyBriefData 获取家庭简报聚合数据
    console.log('\n=== 第二阶段：获取家庭简报聚合数据 ===');
    const familyBriefData = await fetchFamilyBriefData(targetHomeId, '');

    // 从 familyBriefData 中提取业务数据对象（兼容多层嵌套 + 字符串化结构）
    function extractBusinessData(familyBriefData) {
        try {
            let current = familyBriefData?.data ?? familyBriefData;
            // 逐层剥离 {errorCode,errorMsg,data} 包装，并处理字符串化数据
            for (let i = 0; i < 5; i++) {
                if (typeof current === 'string') {
                    current = JSON.parse(current);
                }
                if (current && typeof current === 'object' && 'data' in current) {
                    current = current.data;
                } else {
                    break;
                }
            }
            // 若 data 仍为字符串包裹，再尝试解析一次
            if (typeof current === 'string') {
                current = JSON.parse(current);
            }
            return current || {};
        } catch (e) {
            return {};
        }
    }
    const familyBriefBiz = extractBusinessData(familyBriefData) || {};

    // 从 familyBriefData 中提取分类设备
    const classifiedDevices = familyBriefBiz.classifiedDevices || {};
    const routerDevices = classifiedDevices['路由设备'] || [];
    const lockDevices = classifiedDevices['门锁设备'] || [];
    const envDevices = classifiedDevices['环境设备'] || [];

    // 打印基础索引信息
    const homeInfo = familyBriefBiz.homeInfo || {};
    const deviceStatistic = familyBriefBiz.deviceStatistic || {};
    console.log('\n【基础索引】' + (homeInfo.homeName || '未知') + '，设备' + (deviceStatistic.total || 0) + '台，在线' + (deviceStatistic.onlineCount || 0) + '台，离线' + (deviceStatistic.offlineCount || 0) + '台');
    console.log('【设备分类】门锁' + lockDevices.length + '台、路由' + routerDevices.length + '台、环境' + envDevices.length + '台');
    console.log('【事件概况】共' + ((familyBriefBiz.events || []).length) + '条事件');

    // 第三阶段：根据分类设备分别获取详细数据
    console.log('\n=== 第三阶段：获取分类设备详细数据 ===');

    // 3.1 获取儿童上网保护数据（路由设备）
    console.log('[3.1] 获取儿童上网保护数据...');
    let childProtectData = null;
    if (routerDevices.length > 0) {
        childProtectData = await getChildProtectData(routerDevices);
    } else {
        console.log('  [SKIP] 无路由设备');
    }

    // 3.2 获取门锁历史记录（门锁设备）
    console.log('[3.2] 获取门锁历史记录...');
    let lockHistory = null;
    if (lockDevices.length > 0) {
        lockHistory = await getLockHistory(lockDevices);
    } else {
        console.log('  [SKIP] 无门锁设备');
    }

    // 3.3 获取环境设备快照（仅在线的环境设备）
    console.log('[3.3] 获取环境设备快照...');
    let envDevicesSnapshot = [];
    const onlineEnvDevices = envDevices.filter(d => d.online);
    if (onlineEnvDevices.length > 0) {
        envDevicesSnapshot = await fetchDevicesDetail(onlineEnvDevices);
    } else {
        console.log('  [SKIP] 无在线环境设备');
    }

    // 第四阶段：并行获取个人健康数据
    console.log('\n=== 第四阶段：并行获取个人健康数据 ===');
    const [sleepData, activityData, emotionData] = await Promise.all([
        getSleepData(),
        getActivityData(),
        getEmotionData()
    ]);

    // 汇总所有数据
    const allData = {
        timestamp: new Date().toISOString(),
        '00_summary': {
            homesInfo: homesInfo !== null,
            familyBriefData: familyBriefData !== null,
            childProtectData: childProtectData !== null,
            lockHistory: lockHistory !== null,
            envDevicesSnapshot: envDevicesSnapshot.length > 0,
            sleepData: sleepData !== null,
            activityData: activityData !== null,
            emotionData: emotionData !== null
        },
        '01_homes_info': homesInfo,
        '02_family_brief_data': familyBriefData,
        '03_child_protect': childProtectData,
        '04_lock_history': lockHistory,
        '05_env_devices_snapshot': envDevicesSnapshot,
        '06_sleep_data': sleepData,
        '07_activity_data': activityData,
        '08_emotion_data': emotionData
    };

    const endTime = Date.now();
    const duration = ((endTime - startTime) / 1000).toFixed(2);

    console.log('\n========================================');
    console.log('  数据收集完成');
    console.log('========================================');
    console.log(`[TIME] 总耗时: ${duration}秒`);
    console.log('\n数据获取统计:');
    const dataSources = allData['00_summary'];
    console.log(`  [OK] 家庭列表: ${dataSources.homesInfo ? '成功' : '失败'}`);
    console.log(`  [OK] 家庭简报聚合数据: ${dataSources.familyBriefData ? '成功' : '失败'}`);
    console.log(`  [OK] 儿童保护: ${childProtectData !== null ? '成功' : '失败/无设备'}`);
    console.log(`  [OK] 门锁历史: ${dataSources.lockHistory ? '成功' : '失败/无设备'}`);
    console.log(`  [OK] 环境设备快照: ${dataSources.envDevicesSnapshot ? `${envDevicesSnapshot.length}台设备` : '失败/无设备'}`);
    console.log(`  [OK] 睡眠数据: ${dataSources.sleepData ? '成功' : '失败'}`);
    console.log(`  [OK] 活动数据: ${dataSources.activityData ? '成功' : '失败'}`);
    console.log(`  [OK] 情绪数据: ${dataSources.emotionData ? '成功' : '失败'}`);

    // 流式JSON输出: 一行一个JSON对象
    console.log('--- START JSON OUTPUT ---');

    // 输出汇总信息
    console.log(JSON.stringify({
        type: 'summary',
        timestamp: allData.timestamp,
        dataSources: allData['00_summary']
    }));

    // 输出家庭列表
    if (homesInfo !== null) {
        console.log(JSON.stringify({
            type: 'homes_info',
            data: homesInfo
        }));
    }

    // 输出家庭简报聚合数据
    if (familyBriefData !== null) {
        console.log(JSON.stringify({
            type: 'family_brief_data',
            data: familyBriefData
        }));
    }

    // 输出儿童保护数据
    if (childProtectData !== null) {
        console.log(JSON.stringify({
            type: 'child_protect',
            data: childProtectData
        }));
    }

    // 输出门锁历史
    if (lockHistory !== null) {
        console.log(JSON.stringify({
            type: 'lock_history',
            data: lockHistory
        }));
    }

    // 输出环境设备快照
    if (envDevicesSnapshot.length > 0) {
        console.log(JSON.stringify({
            type: 'env_devices_snapshot_start',
            total: envDevicesSnapshot.length
        }));
        for (const snapshot of envDevicesSnapshot) {
            console.log(JSON.stringify({
                type: 'device_snapshot',
                data: snapshot
            }));
        }
        console.log(JSON.stringify({
            type: 'env_devices_snapshot_end',
            total: envDevicesSnapshot.length
        }));
    }

    // 输出睡眠数据
    if (sleepData !== null) {
        console.log(JSON.stringify({
            type: 'sleep_data',
            data: sleepData
        }));
    }

    // 输出活动数据
    if (activityData !== null) {
        console.log(JSON.stringify({
            type: 'activity_data',
            data: activityData
        }));
    }

    // 输出情绪数据
    if (emotionData !== null) {
        console.log(JSON.stringify({
            type: 'emotion_data',
            data: emotionData
        }));
    }

    console.log('--- END JSON OUTPUT ---');
    console.log('========================================\n');
}

// 运行
if (import.meta.url === `file://${process.argv[1]}`) {
    main();
}

// ==================== getFamilyBriefData 接口 ====================
// 功能：获取家庭简报汇总数据，通过 getFamilyBriefData 聚合接口
// 参数：homeId 或 homeName（二选一），modules、deviceBlacklist、classifyRules、responseLimit
// 返回：{ errorCode, errorMsg, data: { homeInfo, classifiedDevices, deviceStatistic, events } }
export async function getFamilyBriefData(params = {}, verbose = false) {
    const traceId = generateTraceId();
    process.stderr.write(`[trace-id] ${traceId}\n`);

    const {
        homeId,
        homeName = '',
        modules = ['deviceStatistic', 'events'],
        deviceBlacklist = {},
        classifyRules = {},
        responseLimit = {}
    } = params;

    if (!homeId && !homeName) {
        throw new Error('homeId or homeName is required');
    }

    try {
        // 构建实际请求参数
        const actualParams = {
            homeName,
            homeId,
            modules,
            deviceBlacklist,
            classifyRules,
            responseLimit
        };

        // 构建双层 payload 格式（根据接口规范）
        // 外层: { type, payload } - payload 是字符串化的内层 JSON
        // 内层: { type, payload } - payload 是字符串化的 actualParams
        const requestBody = {
            type: 'getFamilyBriefData',
            payload: JSON.stringify(actualParams)
        };

        // 使用 hagSkillServicePostBody 直接发送请求
        const response = await hagSkillServicePostBody(requestBody, verbose);

        const errorCode = response?.errorCode;
        const errorMsg = response?.errorMsg || '';
        const data = response?.data || null;

        if (errorCode !== '0') {
            throw new Error(`API 返回错误: ${errorCode} - ${errorMsg}`);
        }

        // 按指定格式重组返回数据（与输出报文格式一致）
        const result = {
            errorCode,
            errorMsg,
            data: data || null
        };

        if (verbose && result.data) {
            console.error(`[verbose] 获取家庭简报汇总数据成功`);
            console.error(`[verbose] 家庭名称: ${result.data.homeInfo?.homeName || '未知'}`);
            console.error(`[verbose] 设备统计: 总数=${result.data.deviceStatistic?.total || 0}, 在线=${result.data.deviceStatistic?.onlineCount || 0}, 离线=${result.data.deviceStatistic?.offlineCount || 0}`);
            console.error(`[verbose] 事件数量: ${result.data.events?.length || 0}`);
            const classified = result.data.classifiedDevices || {};
            console.error(`[verbose] 分类设备: 门锁${classified['门锁设备']?.length || 0}台, 路由${classified['路由设备']?.length || 0}台, 环境${classified['环境设备']?.length || 0}台`);
        }

        return result;

    } catch (error) {
        console.error(`[error] 获取家庭简报汇总数据失败: ${error.message}`);
        throw error;
    }
}

// 预置的黑名单配置（根据文档）
const DEVICE_BLACKLIST = {
    prodIds: ['ZG28', 'ZG29', '113X', '113Y', '113Z', '114A', '114B', '114C', '2ABX', '2JTZ', '25EB', '2EWN', '21Z6', 'Y200'],
    devTypes: ['051', 'A31', '06D', '06E'],
    prodIdPatterns: [],
    deviceTypeNamePatterns: ['infrared']
};

// 预置的设备分类规则（根据文档）
const CLASSIFY_RULES = {
    '门锁设备': { devType: 'A0B' },
    '路由设备': { deviceTypeName: '路由' },
    '环境设备': { deviceTypeName: '温湿度|空气|净化|加湿|除湿|新风|空调' }
};

// 预置的响应限制（根据文档）
const RESPONSE_LIMIT = {
    maxSizeBytes: 50000,
    classifiedDevicesPerCategory: 10,
    offlineTopN: 20,
    eventLimit: 50
};

// 获取家庭简报聚合数据（简化调用接口）
export async function fetchFamilyBriefData(homeId, homeName = '') {
    console.log('[1/x] 获取家庭简报聚合数据...');
    try {
        const result = await getFamilyBriefData({
            homeId,
            homeName,
            modules: ['deviceStatistic', 'events'],
            deviceBlacklist: DEVICE_BLACKLIST,
            classifyRules: CLASSIFY_RULES,
            responseLimit: RESPONSE_LIMIT
        }, false);
        console.log('  [OK] 获取家庭简报聚合数据成功');
        return result;
    } catch (error) {
        console.log('  [FAIL] 获取家庭简报聚合数据失败:', error.message);
        return null;
    }
}

export {
    fetchHomesInfo,
    fetchDevicesDetail,
    getChildProtectData,
    getLockHistory,
    getSleepData,
    getActivityData,
    getEmotionData
};