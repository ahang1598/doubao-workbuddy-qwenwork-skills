#!/usr/bin/env node

/**
 * 温度监控模块
 * 获取室内温度，判断是否超过26°C，提供空调联动建议
 *
 * 功能：
 * - 多源融合获取温度（温湿度传感器 > 空调温度传感器）
 * - 判断温度是否异常（>26°C）
 * - 提供空调控制建议
 *
 * 使用方法：
 * node temperature-monitor.js
 */

import { fetchPetDevices, recognizePetDevices, TEMP_ABNORMAL_THRESHOLD } from './pet-device-recognizer.js';
import { fetchPetDeviceSnapshots } from './pet-data-collector.js';

// ==================== 常量定义 ====================

/**
 * 温度异常阈值（摄氏度）
 */
const TEMP_THRESHOLD = TEMP_ABNORMAL_THRESHOLD;

/**
 * 温度状态描述
 */
const TEMP_STATUS = {
  NORMAL: 'normal',
  ABNORMAL: 'abnormal',
  UNAVAILABLE: 'unavailable'
};

/**
 * @typedef {Object} TemperatureMonitorResult
 * @property {number|null} value - 温度值
 * @property {number|null} humidity - 湿度值
 * @property {string} source - 数据来源
 * @property {string} status - 温度状态 (normal|abnormal|unavailable)
 * @property {string} deviceId - 设备ID
 * @property {string} deviceName - 设备名称
 * @property {boolean} online - 是否在线
 * @property {boolean} shouldTurnOnAc - 是否应该开启空调
 * @property {object|null} acSuggestion - 空调建议
 */

/**
 * @typedef {Object} AcSuggestion
 * @property {string} deviceId - 空调设备ID
 * @property {string} deviceName - 空调名称
 * @property {string} roomName - 房间名称
 * @property {number} suggestedTemp - 建议温度
 * @property {string} reason - 建议原因
 */

/**
 * 从温度数据列表中选择最佳温度源
 * @param {TemperatureData[]} temperatureList - 温度数据列表
 * @returns {TemperatureData|null} 最佳温度数据
 */
function selectBestTemperatureSource(temperatureList) {
  if (!temperatureList || temperatureList.length === 0) {
    return null;
  }

  // 按优先级选择：
  // 1. 温湿度传感器（有湿度数据优先）
  // 2. 空调温度传感器

  // 优先选择有湿度数据的温湿度传感器
  const sensorWithHumidity = temperatureList.find(t =>
    t.source === '温湿度传感器' &&
    t.value !== null &&
    t.online
  );

  if (sensorWithHumidity) {
    return sensorWithHumidity;
  }

  // 其次选择温湿度传感器（即使没有湿度数据）
  const sensorWithoutHumidity = temperatureList.find(t =>
    t.source === '温湿度传感器' &&
    t.value !== null &&
    t.online
  );

  if (sensorWithoutHumidity) {
    return sensorWithoutHumidity;
  }

  // 最后选择空调温度传感器
  const acSensor = temperatureList.find(t =>
    t.source === '空调温度传感器' &&
    t.value !== null &&
    t.online
  );

  if (acSensor) {
    return acSensor;
  }

  // 如果都没有在线的，选择任意有温度数据的
  return temperatureList.find(t => t.value !== null) || null;
}

/**
 * 判断温度是否异常
 * @param {number|null} temperature - 温度值
 * @returns {boolean} 是否异常
 */
function isTemperatureAbnormal(temperature) {
  if (temperature === null || temperature === undefined) {
    return false;
  }
  return temperature > TEMP_THRESHOLD;
}

/**
 * 获取温度监控结果
 * @param {PetDeviceSnapshots} snapshots - 宠物设备快照
 * @param {PetDevicesResult} petDevices - 宠物设备列表
 * @returns {TemperatureMonitorResult} 温度监控结果
 */
export function getTemperatureMonitorResult(snapshots, petDevices) {
  const result = {
    value: null,
    humidity: null,
    source: '',
    status: TEMP_STATUS.UNAVAILABLE,
    deviceId: '',
    deviceName: '',
    online: false,
    shouldTurnOnAc: false,
    acSuggestion: null
  };

  if (!snapshots || !snapshots.temperature || snapshots.temperature.length === 0) {
    return result;
  }

  // 选择最佳温度源
  const bestTemp = selectBestTemperatureSource(snapshots.temperature);

  if (!bestTemp || bestTemp.value === null) {
    return result;
  }

  // 填充结果
  result.value = bestTemp.value;
  result.humidity = bestTemp.humidity;
  result.source = bestTemp.source;
  result.deviceId = bestTemp.deviceId;
  result.deviceName = bestTemp.deviceName;
  result.online = bestTemp.online;
  result.status = isTemperatureAbnormal(bestTemp.value) ? TEMP_STATUS.ABNORMAL : TEMP_STATUS.NORMAL;

  // 如果温度异常，检查是否有空调可以联动
  if (result.status === TEMP_STATUS.ABNORMAL) {
    // 找到可用的空调设备
    const availableAc = (snapshots.airConditioner || [])
      .filter(ac => ac.online)
      .filter(ac => !ac.powerState); // 只考虑关闭状态的空调

    if (availableAc.length > 0) {
      const ac = availableAc[0];
      result.shouldTurnOnAc = true;
      result.acSuggestion = {
        deviceId: ac.deviceId,
        deviceName: ac.deviceName,
        roomName: ac.roomName,
        suggestedTemp: TEMP_THRESHOLD, // 建议设置为26°C
        reason: `当前室内温度${bestTemp.value}°C，超过${TEMP_THRESHOLD}°C阈值，建议开启空调降温`
      };
    }
  }

  return result;
}

/**
 * 从云端获取温度监控结果
 * @returns {Promise<TemperatureMonitorResult>} 温度监控结果
 */
export async function fetchTemperatureMonitorResult() {
  // 获取宠物设备列表
  const petDevices = await fetchPetDevices();

  // 获取设备快照
  const snapshots = await fetchPetDeviceSnapshots(petDevices);

  // 计算温度监控结果
  return getTemperatureMonitorResult(snapshots, petDevices);
}

/**
 * 打印温度监控结果
 * @param {TemperatureMonitorResult} result - 温度监控结果
 */
function printTemperatureMonitorResult(result) {
  console.log('\n========== 温度监控结果 ==========');

  if (result.status === TEMP_STATUS.UNAVAILABLE) {
    console.log('状态: 温度数据暂不可用');
    console.log('建议: 请检查是否安装了温湿度传感器或空调设备');
  } else {
    const statusEmoji = result.status === TEMP_STATUS.ABNORMAL ? '⚠️ ' : '✓ ';
    const statusText = result.status === TEMP_STATUS.ABNORMAL ? '异常' : '正常';

    console.log(`温度: ${result.value}°C ${statusEmoji}${statusText}`);
    console.log(`数据来源: ${result.source} (${result.online ? '在线' : '离线'})`);

    if (result.humidity !== null) {
      console.log(`湿度: ${result.humidity}%`);
    }

    if (result.shouldTurnOnAc && result.acSuggestion) {
      console.log('\n【空调联动建议】');
      console.log(`  建议开启: ${result.acSuggestion.deviceName}`);
      console.log(`  所在房间: ${result.acSuggestion.roomName}`);
      console.log(`  建议温度: ${result.acSuggestion.suggestedTemp}°C`);
      console.log(`  原因: ${result.acSuggestion.reason}`);
    }
  }

  console.log('==================================\n');
}

// ==================== CLI 入口 ====================

async function main() {
  console.log('[info] 正在获取温度监控数据...');

  try {
    const result = await fetchTemperatureMonitorResult();
    printTemperatureMonitorResult(result);

    // 输出 JSON 格式结果
    console.log('--- START JSON OUTPUT ---');
    console.log(JSON.stringify({
      type: 'temperature_monitor',
      data: result
    }));
    console.log('--- END JSON OUTPUT ---');
  } catch (error) {
    console.error('[error] 获取温度监控数据失败:', error.message);
    process.exit(1);
  }
}

// 运行
if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}

export {
  TEMP_THRESHOLD,
  TEMP_STATUS,
  selectBestTemperatureSource,
  isTemperatureAbnormal
};