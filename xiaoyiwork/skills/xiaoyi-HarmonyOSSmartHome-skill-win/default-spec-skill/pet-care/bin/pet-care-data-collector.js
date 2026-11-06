#!/usr/bin/env node

/**
 * 宠物照护数据收集脚本
 * 统一获取宠物照护所需的所有原始数据
 *
 * 使用方法:
 * node pet-care-data-collector.js <command>
 *
 * 命令:
 *   get_pet_care_data  获取宠物照护全量原始数据
 */

import { Command } from 'commander';
import { getDevicesInfo, getDeviceServiceSnapshot } from '../../../common-skill/bin/get_devices_info.js';
import { getControlRecords } from '../../../common-skill/bin/get_control_records.js';

// ==================== 宠物设备识别 ====================

const PET_DEVICE_KEYWORDS = {
  catLitter: ['pet toilet', 'smart pet toilet', 'litter', '猫砂盆', '猫砂', '猫厕所'],
  feeder: ['smart feeder', 'pet feeder', 'feeder', '喂食器'],
  petTracker: ['tracker', 'pet tracker', 'gps', '定位', '宠物定位'],
  tempHumiditySensor: ['temperature humidity sensor', 'humidity sensor', 'temperature sensor', 'environment sensor', '温湿度', '湿度传感器'],
  airConditioner: ['air conditioner', 'on hook air conditioner', '空调'],
  camera: ['smart camera', 'ai camera', 'camera', 'visioner', 'ptz camera', 'panoramic camera', '摄像头', '网络摄像头']
};

const DEVICE_TYPE_MAP = {
  'temp': 'tempHumiditySensor',
  'humidity': 'tempHumiditySensor',
  'sensor': 'tempHumiditySensor',
  'AC': 'airConditioner',
  'airConditioner': 'airConditioner',
  'camera': 'camera',
  'IPC': 'camera'
};

const PET_DEVICE_EXCLUDE_KEYWORDS = ['freelace', 'freebuds', '耳机', '手表', 'watch'];

function recognizeDeviceCategory(device) {
  if (!device) return null;

  const { prodId, deviceType, deviceName, productName } = device;
  const searchText = `${prodId || ''} ${deviceType || ''} ${deviceName || ''} ${productName || ''}`.toLowerCase();

  for (const excludeKw of PET_DEVICE_EXCLUDE_KEYWORDS) {
    if (searchText.includes(excludeKw.toLowerCase())) {
      return null;
    }
  }

  for (const [category, keywords] of Object.entries(PET_DEVICE_KEYWORDS)) {
    for (const keyword of keywords) {
      if (searchText.includes(keyword.toLowerCase())) {
        return category;
      }
    }
  }

  if (deviceType && DEVICE_TYPE_MAP[deviceType]) {
    return DEVICE_TYPE_MAP[deviceType];
  }

  return null;
}

function recognizePetDevices(devicesInfo) {
  const result = {
    catLitter: [],
    feeder: [],
    petTracker: [],
    tempHumiditySensor: [],
    airConditioner: [],
    camera: [],
    totalCount: 0
  };

  if (!devicesInfo || !devicesInfo.devices) {
    return result;
  }

  for (const device of devicesInfo.devices) {
    const category = recognizeDeviceCategory(device);
    if (category && result[category]) {
      result[category].push({
        deviceId: device.deviceId || device.devId || '',
        deviceName: device.deviceName || device.deviceName || '',
        roomName: device.roomName || '未分类',
        category: category,
        prodId: device.prodId || '',
        online: true
      });
    }
  }

  result.totalCount = result.catLitter.length +
    result.feeder.length +
    result.petTracker.length +
    result.tempHumiditySensor.length +
    result.airConditioner.length +
    result.camera.length;

  return result;
}

// ==================== 统一数据获取函数 ====================

async function fetchPetCareData(verbose = false) {
  if (verbose) console.error('[verbose] 开始采集宠物照护数据...');
  const startTime = Date.now();

  if (verbose) console.error('[step 1/3] 获取设备列表...');
  const devicesInfo = await getDevicesInfo({});
  const petDevices = recognizePetDevices(devicesInfo);
  if (verbose) console.error(`  识别到 ${petDevices.totalCount} 个宠物相关设备`);

  const allDeviceIds = [];
  const deviceInfoMap = {};

  for (const device of (petDevices.catLitter || [])) {
    allDeviceIds.push(device.deviceId);
    deviceInfoMap[device.deviceId] = { ...device, category: 'catLitter' };
  }
  for (const device of (petDevices.feeder || [])) {
    allDeviceIds.push(device.deviceId);
    deviceInfoMap[device.deviceId] = { ...device, category: 'feeder' };
  }
  for (const device of (petDevices.tempHumiditySensor || [])) {
    allDeviceIds.push(device.deviceId);
    deviceInfoMap[device.deviceId] = { ...device, category: 'tempHumiditySensor' };
  }
  for (const device of (petDevices.airConditioner || [])) {
    allDeviceIds.push(device.deviceId);
    deviceInfoMap[device.deviceId] = { ...device, category: 'airConditioner' };
  }
  for (const device of (petDevices.camera || [])) {
    allDeviceIds.push(device.deviceId);
    deviceInfoMap[device.deviceId] = { ...device, category: 'camera' };
  }
  for (const device of (petDevices.petTracker || [])) {
    allDeviceIds.push(device.deviceId);
    deviceInfoMap[device.deviceId] = { ...device, category: 'petTracker' };
  }

  if (verbose) console.error('[step 2/3] 获取设备快照...');
  let rawSnapshots = [];
  if (allDeviceIds.length > 0) {
    try {
      const snapshotResult = await getDeviceServiceSnapshot(allDeviceIds);
      rawSnapshots = snapshotResult.snapshots || [];
      if (verbose) console.error(`  获取到 ${rawSnapshots.length} 个设备快照`);
    } catch (error) {
      console.error('[error] 获取设备快照失败:', error.message);
    }
  }

  if (verbose) console.error('[step 3/3] 获取控制记录...');
  let controlRecords = [];
  try {
    const controlResult = await getControlRecords({ homeId: petDevices.homeId, lastDays: '1' });
    controlRecords = controlResult?.data?.data || controlResult?.data || [];
    if (verbose) console.error(`  获取到 ${controlRecords.length} 条控制记录`);
  } catch (error) {
    console.error('[warning] 获取控制记录失败:', error.message);
  }

  const groupedSnapshots = {
    catLitter: [],
    feeder: [],
    tempHumiditySensor: [],
    airConditioner: [],
    camera: [],
    petTracker: []
  };

  for (const snapshot of rawSnapshots) {
    const deviceId = snapshot.deviceId;
    const deviceInfo = deviceInfoMap[deviceId];
    const category = deviceInfo?.category;
    if (category && groupedSnapshots[category]) {
      groupedSnapshots[category].push(snapshot);
    }
  }

  const endTime = Date.now();
  const duration = ((endTime - startTime) / 1000).toFixed(2);
  if (verbose) console.error(`[verbose] 数据采集完成，耗时 ${duration}秒`);

  return {
    timestamp: new Date().toISOString(),
    homeId: petDevices.homeId,
    devices: petDevices,
    snapshots: groupedSnapshots,
    controlRecords: controlRecords,
    duration: `${duration}秒`
  };
}

// ==================== CLI 入口 ====================

const program = new Command();

program
  .name('pet-care-data-collector')
  .description('宠物照护数据收集脚本 - 统一获取原始数据')
  .version('1.0.0')
  .option('--verbose', '显示详细日志')
  .option('--tools <json>', '执行多个工具（JSON 数组）')
  .action(async (opts) => {
    // 支持 --tools 参数（兼容 pet-care-claw.js 调用方式）
    if (opts.tools) {
      try {
        const tools = JSON.parse(opts.tools);
        const data = await fetchPetCareData(opts.verbose);
        const output = tools.map(tool => ({ tool: tool.name, data }));
        console.log(JSON.stringify(output, null, 2));
      } catch (jsonError) {
        console.error('错误：tools参数不是有效的JSON格式');
        process.exit(1);
      }
      return;
    }

    // 默认执行 get_pet_care_data
    const data = await fetchPetCareData(opts.verbose);
    console.log('--- START JSON OUTPUT ---');
    console.log(JSON.stringify({ type: 'pet_care_data', data }));
    console.log('--- END JSON OUTPUT ---');
  });

program.parse();
