#!/usr/bin/env node

/**
 * 手动喂食控制模块
 * 远程触发喂食器出粮
 *
 * 功能：
 * - 手动触发喂食器出粮
 * - 查询喂食记录
 * - 获取喂食器当前状态
 *
 * 使用方法：
 * node feeder-control.js
 * node feeder-control.js --feed
 * node feeder-control.js --device-id xxxxx
 */

import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import { fileURLToPath } from 'url';
import { fetchPetDevices } from './pet-device-recognizer.js';
import { fetchPetDeviceSnapshots } from './pet-data-collector.js';

const execAsync = promisify(exec);

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const BASE_PATH = path.resolve(__dirname, '../../..');
const COMMON_SKILL_BIN = path.resolve(__dirname, '../../../common-skill/bin');

// ==================== 常量定义 ====================

/**
 * 喂食器控制服务ID（常见）
 * 不同品牌可能不同，这里列出常见的服务ID
 */
/**
 * 喂食器控制服务ID（按优先级排序）
 * 双子星喂食器可视版1 (prodId: A3C4) 实际控制入口为 "action"
 * 注意: 此设备为共享设备，需确认控制权限
 */
const FEEDER_SERVICE_IDS = [
  'action',         // ← 实际控制入口（双子星喂食器 A3C4）
  'feed',           // 通用喂食器
  'food',           // 食物相关
  'portion',        // 出粮量
  'dispense',       // 分发
  'feeder',         // 喂食器
  'petFeeder'       // 宠物喂食器
];

/**
 * 喂食器控制命令（常见字段名）
 */
const FEED_COMMANDS = [
  'feed',           // 立即喂食
  'start',          // 开始
  'dispense',       // 分发
  'trigger',        // 触发
  'portion'         // 出粮
];

/**
 * 错误码定义
 */
const ERROR_CODES = {
  SUCCESS: 'SUCCESS',
  DEVICE_OFFLINE: 'DEVICE_OFFLINE',
  TIMEOUT: 'TIMEOUT',
  NO_FEEDER: 'NO_FEEDER',
  CONTROL_FAILED: 'CONTROL_FAILED',
  INVALID_PARAMS: 'INVALID_PARAMS'
};

/**
 * @typedef {Object} FeederControlResult
 * @property {string} code - 状态码
 * @property {string} message - 状态消息
 * @property {string} deviceId - 设备ID
 * @property {string} deviceName - 设备名称
 * @property {string} roomName - 房间名称
 * @property {boolean} success - 是否成功
 * @property {string|null} feedTime - 喂食时间
 * @property {number|null} portionSize - 出粮量
 * @property {boolean} online - 是否在线
 */

/**
 * 执行设备控制命令
 * @param {string} deviceId - 设备ID
 * @param {string} prodId - 产品ID
 * @param {string} serviceId - 服务ID
 * @param {object} commandData - 控制命令数据
 * @param {string} operation - 操作类型 (POST/GET)
 * @returns {Promise<object>} 命令执行结果
 */
async function executeControlCommand(deviceId, prodId, serviceId, commandData, operation = 'POST') {
  const cmd = `node ${path.join(COMMON_SKILL_BIN, 'smarthome-claw.js')} control_device --dev-id "${deviceId}" --prod-id "${prodId}" --operation "${operation}" --sid "${serviceId}" --data '${JSON.stringify(commandData)}'`;

  try {
    const { stdout, stderr } = await execAsync(cmd, {
      encoding: 'utf-8',
      cwd: BASE_PATH,
      timeout: 10000
    });

    // 尝试解析输出
    try {
      const parsed = JSON.parse(stdout);
      // 获取 control_device 返回的数据（它在数组中）
      const controlData = Array.isArray(parsed) ? parsed[0]?.data?.data : parsed;
      
      // 检查内层 error_code — 即使是外层 success=true，内层可能还是失败
      const innerErrorCode = controlData?.response?.data?.error_code;
      const innerErrorDesc = controlData?.response?.data?.error_desc;
      
      if (innerErrorCode && innerErrorCode !== 0 && innerErrorCode !== '0') {
        return {
          success: false,
          error: `API拒绝: ${innerErrorDesc || `error_code=${innerErrorCode}`}`,
          code: ERROR_CODES.CONTROL_FAILED,
          data: parsed
        };
      }
      
      // 外层 errorCode 检查
      const outerErrorCode = controlData?.response?.errorCode;
      if (outerErrorCode && outerErrorCode !== '0' && outerErrorCode !== 0) {
        return {
          success: false,
          error: `控制命令失败: errorCode=${outerErrorCode}`,
          code: ERROR_CODES.CONTROL_FAILED,
          data: parsed
        };
      }

      return { success: true, data: parsed };
    } catch (e) {
      // 如果不是 JSON，检查是否有错误
      if (stderr && stderr.toLowerCase().includes('error')) {
        return { success: false, error: stderr };
      }
      return { success: true, data: stdout };
    }
  } catch (error) {
    if (error.code === 'ETIMEDOUT' || error.code === 'ECONNRESET') {
      return { success: false, error: '命令执行超时', code: ERROR_CODES.TIMEOUT };
    }
    return { success: false, error: error.message };
  }
}

/**
 * 查找喂食器设备
 * @param {PetDevicesResult} petDevices - 宠物设备列表
 * @param {string} deviceId - 指定的设备ID（可选）
 * @returns {object|null} 喂食器设备信息
 */
function findFeederDevice(petDevices, deviceId) {
  if (!petDevices || !petDevices.feeder || petDevices.feeder.length === 0) {
    return null;
  }

  // 如果指定了设备ID，查找对应设备
  if (deviceId) {
    return petDevices.feeder.find(f => f.deviceId === deviceId) || null;
  }

  // 默认返回第一个喂食器
  return petDevices.feeder[0];
}

/**
 * 触发喂食器出粮
 * @param {string} deviceId - 设备ID
 * @param {string} prodId - 产品ID
 * @param {number} portionSize - 出粮量（克）
 * @returns {Promise<FeederControlResult>} 控制结果
 */
async function triggerFeeding(deviceId, prodId, portionSize = 20) {
  const result = {
    code: ERROR_CODES.SUCCESS,
    message: '喂食器已出粮',
    deviceId: deviceId,
    deviceName: '',
    roomName: '',
    success: true,
    feedTime: new Date().toISOString(),
    portionSize: portionSize,
    online: true
  };

  // 生成控制命令组合（按优先级）
  // 精确匹配优先：sid=action, data={"action":1}
  // 再降级尝试通用组合
  const commandCombinations = [];

  for (const sid of FEEDER_SERVICE_IDS) {
    // 对于 action 服务，正确的命令是 {"action": 1}
    if (sid === 'action') {
      commandCombinations.push({ sid, command: { action: 1 } });
      commandCombinations.push({ sid, command: { action: 1, portion: portionSize } });
    } else {
      for (const cmd of FEED_COMMANDS) {
        commandCombinations.push({ sid, command: { [cmd]: 1, portion: portionSize } });
        commandCombinations.push({ sid, command: { [cmd]: 1 } });
        commandCombinations.push({ sid, command: { feed: 1, amount: portionSize } });
      }
    }
  }

  // 添加一些通用的组合
  commandCombinations.push({ sid: 'feeder', command: { feed: 1 } });
  commandCombinations.push({ sid: 'feed', command: { on: 1 } });
  commandCombinations.push({ sid: 'dispense', command: { dispense: 1, amount: portionSize } });

  let lastError = null;

  for (const { sid, command } of commandCombinations) {
    try {
      const execResult = await executeControlCommand(deviceId, prodId, sid, command, 'POST');

      if (execResult.success) {
        result.code = ERROR_CODES.SUCCESS;
        result.message = `喂食器已出粮${portionSize}克`;
        return result;
      } else {
        lastError = execResult.error;
      }
    } catch (e) {
      lastError = e.message;
    }
  }

  // 所有组合都失败
  result.code = ERROR_CODES.CONTROL_FAILED;
  result.message = `喂食器控制失败: ${lastError || '未知错误'}`;
  result.success = false;

  return result;
}

/**
 * 获取喂食器状态
 * @param {string} deviceId - 设备ID
 * @param {string} prodId - 产品ID
 * @returns {Promise<object>} 喂食器状态
 */
async function getFeederStatus(deviceId, prodId) {
  // 尝试 GET 操作获取状态
  for (const sid of FEEDER_SERVICE_IDS) {
    try {
      const execResult = await executeControlCommand(deviceId, prodId, sid, {}, 'GET');

      if (execResult.success && execResult.data) {
        return {
          code: ERROR_CODES.SUCCESS,
          message: '获取状态成功',
          data: execResult.data
        };
      }
    } catch (e) {
      // 继续尝试其他服务ID
    }
  }

  return {
    code: ERROR_CODES.CONTROL_FAILED,
    message: '无法获取喂食器状态',
    data: null
  };
}

/**
 * 执行喂食控制
 * @param {string} deviceId - 指定的设备ID（可选）
 * @param {number} portionSize - 出粮量（克）
 * @returns {Promise<FeederControlResult>} 控制结果
 */
async function controlFeeder(deviceId = null, portionSize = 20) {
  // 获取宠物设备列表
  const petDevices = await fetchPetDevices();

  // 查找喂食器
  const feederDevice = findFeederDevice(petDevices, deviceId);

  if (!feederDevice) {
    return {
      code: ERROR_CODES.NO_FEEDER,
      message: '未找到喂食器设备',
      deviceId: deviceId,
      deviceName: '',
      roomName: '',
      success: false,
      feedTime: null,
      portionSize: null,
      online: false
    };
  }

  // 获取设备详细信息（包括 prodId）
  const { getDevicesInfo } = await import('../../../common-skill/bin/get_devices_info.js');
  const devicesInfo = await getDevicesInfo({});
  const deviceDetail = devicesInfo.devices.find(d =>
    (d.deviceId || d.devId) === feederDevice.deviceId
  );

  const prodId = deviceDetail?.prodId || feederDevice.prodId || '';

  // 检查设备在线状态
  const snapshots = await fetchPetDeviceSnapshots(petDevices);
  const feederSnapshot = snapshots.feeder.find(f => f.deviceId === feederDevice.deviceId);

  if (feederSnapshot && !feederSnapshot.online) {
    return {
      code: ERROR_CODES.DEVICE_OFFLINE,
      message: '喂食器当前离线，无法执行喂食，请检查设备连接',
      deviceId: feederDevice.deviceId,
      deviceName: feederDevice.deviceName,
      roomName: feederDevice.roomName,
      success: false,
      feedTime: null,
      portionSize: null,
      online: false
    };
  }

  // 触发喂食
  const feedResult = await triggerFeeding(feederDevice.deviceId, prodId, portionSize);
  // 补充设备名称和房间信息
  feedResult.deviceName = feederDevice.deviceName;
  feedResult.roomName = feederDevice.roomName;
  return feedResult;
}

/**
 * 打印喂食控制结果
 * @param {FeederControlResult} result - 控制结果
 */
function printFeederControlResult(result) {
  console.log('\n========== 喂食控制结果 ==========');

  if (result.code === ERROR_CODES.NO_FEEDER) {
    console.log('状态: ❌ 未找到喂食器设备');
    console.log('建议: 请确认是否已添加智能喂食器设备');
  } else if (result.code === ERROR_CODES.DEVICE_OFFLINE) {
    console.log('状态: ❌ 喂食器离线');
    console.log(`设备: ${result.deviceName} (${result.roomName})`);
    console.log('建议: 请检查喂食器电源和网络连接');
  } else if (result.success) {
    console.log('状态: ✅ 喂食成功');
    console.log(`设备: ${result.deviceName} (${result.roomName})`);
    console.log(`出粮量: ${result.portionSize}克`);
    console.log(`时间: ${result.feedTime ? new Date(result.feedTime).toLocaleString('zh-CN') : '未知'}`);
  } else {
    console.log('状态: ❌ 喂食失败');
    console.log(`设备: ${result.deviceName} (${result.roomName})`);
    console.log(`原因: ${result.message}`);
  }

  console.log('==================================\n');
}

// ==================== CLI 入口 ====================

async function main() {
  const args = process.argv.slice(2);

  // 解析命令行参数
  let deviceId = null;
  let portionSize = 20;
  let shouldFeed = false;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--device-id' && args[i + 1]) {
      deviceId = args[i + 1];
    } else if (args[i] === '--portion' && args[i + 1]) {
      portionSize = parseInt(args[i + 1], 10) || 20;
    } else if (args[i] === '--feed') {
      shouldFeed = true;
    }
  }

  // 如果没有指定 --feed 参数，默认执行喂食
  if (!shouldFeed && !args.some(a => a.startsWith('--'))) {
    shouldFeed = true;
  }

  if (shouldFeed) {
    console.log(`[info] 正在触发喂食 (出粮量: ${portionSize}克)...`);
    const result = await controlFeeder(deviceId, portionSize);
    printFeederControlResult(result);

    // 输出 JSON 格式结果
    console.log('--- START JSON OUTPUT ---');
    console.log(JSON.stringify({
      type: 'feeder_control',
      data: result
    }));
    console.log('--- END JSON OUTPUT ---');
  } else {
    // 查询状态
    console.log('[info] 正在查询喂食器状态...');
    // TODO: 实现状态查询
    console.log('[info] 状态查询功能待实现');
  }
}

// 运行
if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}

export {
  ERROR_CODES,
  triggerFeeding,
  getFeederStatus,
  controlFeeder,
  findFeederDevice
};