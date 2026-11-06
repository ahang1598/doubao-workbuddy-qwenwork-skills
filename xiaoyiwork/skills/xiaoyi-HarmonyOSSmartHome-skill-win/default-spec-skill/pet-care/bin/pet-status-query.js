#!/usr/bin/env node

/**
 * 宠物状态查询模块
 * 汇总所有宠物设备状态，返回统一格式
 */

import { fetchPetCareData } from './pet-care-data-collector.js';

// ==================== 常量定义 ====================

/**
 * 错误码定义
 */
const ERROR_CODES = {
  DEVICE_OFFLINE: 'DEVICE_OFFLINE',
  PARTIAL_OFFLINE: 'PARTIAL_OFFLINE',
  TEMP_UNAVAILABLE: 'TEMP_UNAVAILABLE',
  NO_FEEDER: 'NO_FEEDER',
  SUCCESS: 'SUCCESS'
};

/**
 * @typedef {Object} PetStatusResult
 * @property {string} code - 状态码
 * @property {string} message - 状态消息
 * @property {CatLitterStatus|null} catLitter - 猫砂盆状态
 * @property {FeederStatus|null} feeder - 喂食器状态
 * @property {TemperatureStatus|null} temperature - 温度状态
 * @property {PetLocationStatus|null} petLocation - 宠物位置状态
 * @property {AirConditionerStatus|null} airConditioner - 空调状态
 * @property {string} timestamp - 查询时间
 */

/**
 * @typedef {Object} CatLitterStatus
 * @property {string} deviceName - 设备名称
 * @property {string} roomName - 房间名称
 * @property {number|null} useCount - 今日使用次数
 * @property {string|null} lastUseTime - 最后使用时间
 * @property {boolean} online - 是否在线
 */

/**
 * @typedef {Object} FeederStatus
 * @property {string} deviceName - 设备名称
 * @property {string} roomName - 房间名称
 * @property {number|null} feedCount - 今日出粮次数
 * @property {string|null} lastFeedTime - 最后出粮时间
 * @property {number|null} portionSize - 每次出粮量
 * @property {boolean} online - 是否在线
 */

/**
 * @typedef {Object} TemperatureStatus
 * @property {number|null} value - 温度值
 * @property {number|null} humidity - 湿度值
 * @property {string} source - 数据来源
 * @property {boolean} isAbnormal - 是否异常
 * @property {boolean} online - 是否在线
 * @property {boolean} shouldTurnOnAc - 是否应该开启空调
 */

/**
 * @typedef {Object} PetLocationStatus
 * @property {string} location - 位置描述
 * @property {string} source - 数据来源
 * @property {boolean} online - 是否在线
 */

/**
 * @typedef {Object} AirConditionerStatus
 * @property {string} deviceId - 设备ID
 * @property {string} deviceName - 设备名称
 * @property {string} roomName - 房间名称
 * @property {boolean} powerState - 电源状态
 * @property {number|null} currentTemp - 当前温度
 * @property {number|null} targetTemp - 目标温度
 * @property {boolean} online - 是否在线
 */

/**
 * 格式化时间字符串
 * @param {string|Date|null} time - 时间
 * @returns {string} 格式化后的时间字符串
 */
function formatTime(time) {
  if (!time) return '未知';

  try {
    const date = new Date(time);
    if (isNaN(date.getTime())) return time;

    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();

    if (isToday) {
      return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    } else {
      return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    }
  } catch (e) {
    return String(time);
  }
}

/**
 * 生成宠物状态查询结果
 * @param {PetDevicesResult} petDevices - 宠物设备列表
 * @param {PetDeviceSnapshots} snapshots - 宠物设备快照
 * @param {TemperatureMonitorResult} tempResult - 温度监控结果
 * @returns {PetStatusResult} 宠物状态查询结果
 */
export function generatePetStatusResult(petDevices, snapshots, tempResult) {
  const result = {
    code: ERROR_CODES.SUCCESS,
    message: '查询成功',
    catLitter: null,
    feeder: null,
    temperature: null,
    petLocation: null,
    airConditioner: null,
    timestamp: new Date().toISOString()
  };

  // 统计离线设备
  let offlineCount = 0;
  let totalPetDevices = 0;

  // 猫砂盆状态
  if (snapshots.catLitter && snapshots.catLitter.length > 0) {
    const catLitter = snapshots.catLitter[0];
    result.catLitter = {
      deviceName: catLitter.deviceName,
      roomName: catLitter.roomName,
      useCount: catLitter.useCount,
      lastUseTime: formatTime(catLitter.lastUseTime),
      online: catLitter.online
    };
    if (!catLitter.online) offlineCount++;
    totalPetDevices++;
  } else if (petDevices.catLitter && petDevices.catLitter.length > 0) {
    totalPetDevices++;
    offlineCount++;
  }

  // 喂食器状态
  if (snapshots.feeder && snapshots.feeder.length > 0) {
    const feeder = snapshots.feeder[0];
    result.feeder = {
      deviceName: feeder.deviceName,
      roomName: feeder.roomName,
      feedCount: feeder.feedCount,
      lastFeedTime: formatTime(feeder.lastFeedTime),
      portionSize: feeder.portionSize,
      online: feeder.online
    };
    if (!feeder.online) offlineCount++;
    totalPetDevices++;
  } else if (petDevices.feeder && petDevices.feeder.length > 0) {
    totalPetDevices++;
    offlineCount++;
  }

  // 温度状态（使用温度监控模块的结果）
  if (tempResult.value !== null) {
    result.temperature = {
      value: tempResult.value,
      humidity: tempResult.humidity,
      source: tempResult.source,
      isAbnormal: tempResult.status === 'abnormal',
      online: tempResult.online,
      shouldTurnOnAc: tempResult.shouldTurnOnAc
    };
  }

  // 宠物位置
  if (snapshots.petLocation && snapshots.petLocation.length > 0) {
    const location = snapshots.petLocation[0];
    result.petLocation = {
      location: location.location,
      source: location.source,
      online: location.online
    };
  }

  // 空调状态
  if (snapshots.airConditioner && snapshots.airConditioner.length > 0) {
    const ac = snapshots.airConditioner[0];
    result.airConditioner = {
      deviceId: ac.deviceId,
      deviceName: ac.deviceName,
      roomName: ac.roomName,
      powerState: ac.powerState,
      currentTemp: ac.currentTemp,
      targetTemp: ac.targetTemp,
      online: ac.online
    };
  }

  // 设置错误码
  if (totalPetDevices === 0 && petDevices.totalCount === 0) {
    result.code = ERROR_CODES.DEVICE_OFFLINE;
    result.message = '未发现宠物设备';
  } else if (offlineCount === totalPetDevices && totalPetDevices > 0) {
    result.code = ERROR_CODES.DEVICE_OFFLINE;
    result.message = '宠物设备当前离线，无法获取状态，请检查设备连接';
  } else if (offlineCount > 0) {
    result.code = ERROR_CODES.PARTIAL_OFFLINE;
    result.message = '部分宠物设备离线，数据可能不完整';
  }

  return result;
}

/**
 * 从云端获取宠物状态
 * @returns {Promise<PetStatusResult>} 宠物状态查询结果
 */
export async function fetchPetStatus() {
  console.log('[info] 正在获取宠物状态...');

  const careData = await fetchPetCareData();

  return generatePetStatusResult(careData.devices, careData.snapshots, careData.temperature);
}

/**
 * 获取宠物状态（适配 pet-care-claw.js 调用）
 * @param {boolean} [verbose=false] - 是否打印详细日志
 * @returns {Promise<PetStatusResult>} 宠物状态查询结果
 */
export async function getPetStatus(verbose = false) {
  if (verbose) console.error('[verbose] 调用 getPetStatus');
  return fetchPetStatus();
}

/**
 * 获取宠物设备列表（适配 pet-care-claw.js 调用）
 * @param {boolean} [verbose=false] - 是否打印详细日志
 * @returns {Promise<PetDevicesResult>} 分类后的宠物设备
 */
export async function getPetDevices(verbose = false) {
  if (verbose) console.error('[verbose] 调用 getPetDevices');
  const { fetchPetDevices } = await import('./pet-device-recognizer.js');
  return fetchPetDevices();
}

export {
  formatTime,
  ERROR_CODES
};