// ==================== router-claw.js 主入口 ====================
// 功能：路由器技能总调度入口
// 版本：2.2.0 (新增 --all-homes, --home-id, --non-interactive 参数支持)

// Node.js 内置模块
import { Command } from 'commander';
import { randomUUID } from 'crypto';
import fs from 'fs';
import zlib from 'zlib';
import { promisify } from 'util';
import path from 'path';
import { fileURLToPath } from 'url';

// 第三方模块 (如有时，在此处添加)

// 项目内部模块 - 工具类
import { hagControl, generateTraceId, generateTimestamp } from '../../utils/hag-connect/utils.js';
import { getDevicesOnlineStatus } from '../../common-skill/bin/get_devices_info.js';

// 项目内部模块 - 应用信息
import { g_saAppInfo } from './sa_app_info.js';

// 项目内部模块 - 核心功能
import {
  handleAllowGames,
  handleAllowVideos,
  handleAllowSocial,
  handleAllowShopping,
  handleAllowInstall,
  handleGetRouterDeviceByProdid,
  handleGetAppInfo,
  handleGetAllApps,
  getCategoryName,
  getRouterInfo,
  transformChildProtectData,
  isForbidPeriodAlreadyDenied,
  needDeleteConflictingRules,
  generateBlockToAllowCommands,
} from './router-functions.js';

// ==================== 路由器配置 ====================
const PROGRAM_NAME = 'router-claw';
const VERSION = '2.2.0';
const DEFAULT_SKILL_ID = 'xiaoyi_router';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

let TARGET_HOME_ID = null;
let QUERY_ALL_HOMES = false;
let BATCH_MODE = false;  // 是否使用 --batch-mode 兜底模式
let ROUTER_DEVICE_ID = null;
let ROUTER_PROD_ID = null;

// 路由器 API 路径配置
const ROUTER_PATHS = {
  get_host_info: '.sys/gateway/system/HostInfo?filterAndroid=true&isSupportHostZip=true',
  check_presence: '.sys/gateway/system/HostInfo?filterAndroid=true&isSupportHostZip=true', // 复用 HostInfo 路径，输出脱敏
  get_child_protect: '.sys/gateway/ntwk/childHomepage',
  get_wan_status: '.sys/gateway/ntwk/wan?type=active',
  get_wandetect: '.sys/gateway/ntwk/wandetect',
  get_channel_info: '.sys/gateway/ntwk/channelinfo',
  get_5g_optimize: '.sys/gateway/ntwk/wlandbho',
  get_ipv6: '.sys/gateway/ntwk/ipv6_enable',
  get_user_behavior: '.sys/gateway/system/userbehavior',
  get_router_status: '.sys/gateway/system/processstatus',
  get_wifi_config: null, // 自定义实现，调用wlandbho和WlanBasic两个接口
  set_ipv6: '.sys/gateway/ntwk/ipv6_enable',
  add_child_device: '.sys/gateway/ntwk/childManage',
  del_child_device: '.sys/gateway/ntwk/childHomepage',
  set_net_time: '.sys/gateway/ntwk/childFrame',
  set_block_time: '.sys/gateway/ntwk/childFrame',
  set_app_control: '.sys/gateway/ntwk/childModelApps',
  set_net_off: '.sys/gateway/ntwk/childHomepage',
  set_net_duration: '.sys/gateway/ntwk/childDailyUpdate',
  deny_games: '.sys/gateway/ntwk/childModelApps',
  deny_videos: '.sys/gateway/ntwk/childModelApps',
  deny_social: '.sys/gateway/ntwk/childModelApps',
  deny_shopping: '.sys/gateway/ntwk/childModelApps',
  deny_install: '.sys/gateway/ntwk/childModelApps',
  deny_app: '.sys/gateway/ntwk/childModelApps',
  only_deny_app: '.sys/gateway/ntwk/childModelApps',
  allow_games: '.sys/gateway/ntwk/childModelApps',
  allow_videos: '.sys/gateway/ntwk/childModelApps',
  allow_social: '.sys/gateway/ntwk/childModelApps',
  allow_shopping: '.sys/gateway/ntwk/childModelApps',
  allow_install: '.sys/gateway/ntwk/childModelApps',
  // 应用信息查询（本地功能，不调用路由器API）
  get_app_info: null, // 本地功能
  get_all_apps: null, // 本地功能
  get_router_device_by_prodid: null, // 本地功能
  // 访客WiFi
  get_guest_wifi: '.sys/gateway/ntwk/guest_network',
  set_guest_wifi: '.sys/gateway/ntwk/guest_network',
  //信道优化
  set_channel_update: '.sys/gateway/ntwk/channelinfo?type=1',
  set_5g_optimize: null, // 自定义实现，不使用此配置
  set_user_behavior: '.sys/gateway/system/userbehavior',
  set_power_mode: '.sys/gateway/ntwk/wlanradio',
  get_power_mode: '.sys/gateway/ntwk/wlanradio',
  get_link_rate: '.sys/gateway/device/hostmap',
  get_eth_negotiation: '.sys/gateway/ntwk/ethnegotiation',
  get_game_history: '.sys/gateway/hilink/higame_games_v2?allGames=true',
  get_week_report: '.sys/gateway/app/weeklyreport',
  set_Game_acceleration: '.sys/gateway/hilink/higamecontrol',
  set_wifi_timeswitch: '.sys/gateway/ntwk/wlantimeswitch',
  smart_dev_connect: '.sys/gateway/ntwk/smart_dev_manual_connect',
  set_upload_log: '.sys/gateway/system/diagnose_crash',
  set_online_upg: '.sys/gateway/system/onlineupg',
  set_reboot: '.sys/gateway/service/reboot.cgi',
  set_antisteal_mode: '.sys/gateway/ntwk/homesec_stealnet',
  set_homesec_abfa: '.sys/gateway/ntwk/homesec_abfa',
  set_auth_Device: '.sys/gateway/ntwk/access_auth',
  set_Device_ratelimit: '.sys/gateway/app/qosclass_host',
  get_lan_host: '.sys/gateway/ntwk/lan_host',
  set_led_status: '.sys/gateway/hilink/ledstatus'
};

// ==================== 工具函数 ====================
/**
 * 统一的 allow 操作处理函数
 * @param {Function} handlerFunc - 处理函数 (handleAllowGames/Video/Social/Shopping/Install)
 * @param {string} devId - 设备ID
 * @param {string} prodId - 产品ID
 * @param {string} deviceId - 儿童保护设备ID
 * @param {boolean} verbose - 调试模式
 * @param {number} retryCount - 重试次数
 * @returns {Object} - 包含results数组或retry标记
 */
async function handleAllowOperation(handlerFunc, devId, prodId, deviceId, verbose, retryCount) {
  const { payload1, payload2, step1Name, step2Name } = await handlerFunc(devId, prodId, deviceId, verbose);
  
  let res1;
  let res2;
  try {
    res1 = await hagControl(payload1, verbose);
    res2 = await hagControl(payload2, verbose);
    
    const step1Success = res1?.success === true || (res1?.data?.status === 'success') || (res1?.data?.code === 0);
    const step2Success = res2?.success === true || (res2?.data?.status === 'success') || (res2?.data?.code === 0);
    
    const step1Message = step1Success ? `✓ ${step1Name} 操作成功` : `❌ ${step1Name} 操作失败: ${res1?.data?.message || '未知错误'}`;
    const step2Message = step2Success ? `✓ ${step2Name} 操作成功` : `❌ ${step2Name} 操作失败: ${res2?.data?.message || '未知错误'}`;
    
    return {
      results: [
        { tool: step1Name, success: step1Success, data: res1, message: step1Message },
        { tool: step2Name, success: step2Success, data: res2, message: step2Message }
      ]
    };
  } catch (err) {
    if (err.code === 401 && retryCount < MAX_RETRY) {
      console.log('[info] token 已过期，正在自动刷新...');
      return { retry: true };
    }
    throw err;
  }
}

/**
 * 对WiFi密码进行脱敏处理
 * @param {Object} wlanData - WlanBasic返回的原始数据
 * @returns {Object} - 密码字段被替换为***的数据
 */
function maskWifiPassword(wlanData) {
  if (!wlanData || typeof wlanData !== 'object') {
    return wlanData;
  }

  // 需要脱敏的密码字段
  const passwordFields = ['WpaPreSharedKey', 'WpaPreSharedKeyTemp', 'WepKey', 'PreSharedKey', 'Key'];

  const maskedData = JSON.parse(JSON.stringify(wlanData));

  function processObject(obj) {
    if (!obj || typeof obj !== 'object') {
      return;
    }

    // 处理数组
    if (Array.isArray(obj)) {
      obj.forEach((item, index) => {
        if (item && typeof item === 'object') {
          processObject(item);
        }
      });
      return;
    }

    // 处理对象
    for (const key of Object.keys(obj)) {
      if (passwordFields.includes(key) && obj[key] && typeof obj[key] === 'string') {
        // 密码字段替换为***
        obj[key] = '***';
      } else if (typeof obj[key] === 'object') {
        processObject(obj[key]);
      }
    }
  }

  processObject(maskedData);
  return maskedData;
}

/**
 * 对WAN状态返回数据中的Username和Password进行脱敏处理
 * @param {Object} wanData - get_wan_status返回的原始数据
 * @returns {Object} - Username和Password字段被替换为***的数据
 */
function maskWanSensitiveFields(wanData) {
  if (!wanData || typeof wanData !== 'object') {
    return wanData;
  }

  // 需要脱敏的字段
  const sensitiveFields = ['Username', 'Password'];

  const maskedData = JSON.parse(JSON.stringify(wanData));

  function processObject(obj) {
    if (!obj || typeof obj !== 'object') {
      return;
    }

    // 处理数组
    if (Array.isArray(obj)) {
      obj.forEach((item) => {
        if (item && typeof item === 'object') {
          processObject(item);
        }
      });
      return;
    }

    // 处理对象
    for (const key of Object.keys(obj)) {
      if (sensitiveFields.includes(key) && obj[key] && typeof obj[key] === 'string') {
        obj[key] = '***';
      } else if (typeof obj[key] === 'object') {
        processObject(obj[key]);
      }
    }
  }

  processObject(maskedData);
  return maskedData;
}

/**
 * 解密 HostInfo 的 gzip+base64 数据
 */
const gunzip = promisify(zlib.gunzip);

async function decodeHostInfo(content) {
  try {
    const buffer = Buffer.from(content, 'base64');
    const result = await gunzip(buffer);
    return JSON.parse(result.toString());
  } catch (e) {
    console.error('[decode] 解析设备信息失败:', e.message);
    return null;
  }
}

// ==================== 自动配置路由器设备id（智能识别） ====================
async function autoConfigureEnv(verbose = false, options = {}) {
  const targetHomeId = options.homeId || TARGET_HOME_ID;
  const batchMode = options.batchMode || false;

  console.log('\n========== 需要配置路由器设备信息 ==========');
  console.log('将自动为您查找和配置路由器设备...\n');

  try {
    // 第1步：检查是否有最近的设备信息缓存和路由器设备信息
    const cacheDir = path.join(__dirname, '../../common-skill/out_put/get_devices_info');
    const deviceCacheFile = path.join(cacheDir, 'devices_info.txt');
    
    let devicesInfo = null;
    let fromCache = false;
    let routerDeviceInfo = null;
    
    // 加载路由器设备信息映射表
    try {
      routerDeviceInfo = (await import('./router_device_info.js')).default;
      console.log(`✓ 已加载 ${routerDeviceInfo.length} 个路由器设备映射`);
    } catch (infoError) {
      console.error('⚠️  路由器设备信息映射加载失败');
    }

    // 检查设备信息缓存
    if (fs.existsSync(deviceCacheFile)) {
      try {
        console.log('✓ 发现设备信息缓存，正在读取...');
        const cachedData = fs.readFileSync(deviceCacheFile, 'utf-8');
        devicesInfo = JSON.parse(cachedData);
        fromCache = true;
        console.log(`✓ 从缓存中读取到 ${devicesInfo.length || 0} 个设备`);
      } catch (cacheError) {
        console.error('⚠️  缓存文件读取失败，将重新获取设备信息');
      }
    }

    // 如果没有缓存，重新获取设备信息
    if (!devicesInfo) {
      console.log('步骤1: 获取设备信息...');
      
      const devicesResult = await import('../../common-skill/bin/get_devices_info.js');
      const getDevicesResult = await devicesResult.getDevicesInfo(false);
      devicesInfo = getDevicesResult.devices;
      console.log(`✓ 获取到 ${devicesInfo.length} 个设备`);
    }

    // 第2步：智能识别家庭和路由器
    let selectedHome = null;
    
    if (fromCache) {
      console.log('步骤2: 分析已缓存的设备信息...');
    } else {
      console.log('步骤2: 正在获取家庭信息并分析设备...');
    }

    // 从设备信息中识别家庭
    const homeMap = new Map();
    devicesInfo.forEach(device => {
      const homeId = device.homeId;
      if (homeId && homeId.trim()) {
        if (!homeMap.has(homeId)) {
          homeMap.set(homeId, {
            homeId: homeId,
            homeName: device.homeName || '未命名家庭',
            devices: []
          });
        }
        homeMap.get(homeId).devices.push(device);
      }
    });

    const homes = Array.from(homeMap.values());
    
    // 排序保证 --batch-mode 选择的确定性
    homes.sort((a, b) => a.homeId.localeCompare(b.homeId));

    if (homes.length === 0) {
      throw new Error('未能从设备信息中识别到有效的家庭信息');
    }

    // 如果指定了目标家庭ID，直接使用
    if (targetHomeId) {
      selectedHome = homes.find(h => h.homeId === targetHomeId);
      if (!selectedHome) {
        throw new Error(`未找到指定的家庭ID: ${targetHomeId}`);
      }
      console.log(`✓ 使用指定家庭: ${selectedHome.homeName}`);
    }
    // 如果只有一个家庭，直接选择
    else if (homes.length === 1) {
      selectedHome = homes[0];
      console.log(`✓ 自动选择家庭: ${selectedHome.homeName}`);
    }
    // --batch-mode：使用第一个家庭
    else if (batchMode) {
      selectedHome = homes[0];
      console.log(`✓ --batch-mode，自动选择第一个家庭: ${selectedHome.homeName}`);
    }
    // 没有指定家庭且有多个家庭，报错提示
    else {
      const homeList = homes.map((h, i) => `${i + 1}. ${h.homeName} (ID: ${h.homeId})`).join('\n');
      throw new Error(`发现 ${homes.length} 个家庭，请使用 --home-id 指定:\n${homeList}`);
    }

    // 第3步：基于 bin/router_device_info.js 智能识别路由器设备
    const routerDevices = selectedHome.devices.filter(device => {
      if (!device.prodId || !device.deviceId) {
        return false;
      }

      const prodId = device.prodId?.toUpperCase() || '';
      // 检查是否在路由器设备信息映射表中
      if (routerDeviceInfo) {
        const isInDeviceInfo = routerDeviceInfo.some(routerInfo => {
          return routerInfo[0] === device.deviceId?.toUpperCase() || routerInfo[1] === prodId;
        });
        if (isInDeviceInfo) {
          return true;
        }
      }
      
      // 通过名称判断是否是路由器
      const deviceName = (device.deviceName || '').toLowerCase();
      const productName = (device.productName || '').toLowerCase();
      const isRouterByName = deviceName.includes('路由') || deviceName.includes('router') || deviceName.includes('gateway') ||
                           productName.includes('路由') || productName.includes('router') || productName.includes('gateway');
      return isRouterByName;
    });

    // 如果指定了目标家庭（--home-id 模式），过滤离线的路由器
    if (targetHomeId && routerDevices.length > 0) {
      console.log('步骤3.5: 获取路由器在线状态...');
      try {
        const routerDeviceIds = routerDevices.map(r => r.deviceId);
        const onlineStatusResult = await getDevicesOnlineStatus(routerDeviceIds, verbose);
        const onlineDeviceIds = new Set(
          onlineStatusResult.statuses
            .filter(s => s.status === 'online')
            .map(s => s.deviceId)
        );

        const offlineRouters = routerDevices.filter(r => !onlineDeviceIds.has(r.deviceId));
        offlineRouters.forEach(r => {
          console.log(`  - 已过滤离线路由器: ${r.deviceName}`);
        });

        const onlineRouterDevices = routerDevices.filter(r => onlineDeviceIds.has(r.deviceId));
        console.log(`✓ 在线路由器: ${onlineRouterDevices.length}/${routerDevices.length}`);

        if (onlineRouterDevices.length === 0) {
          throw new Error(`家庭 "${selectedHome.homeName}" 下没有在线的路由器设备`);
        }

        // 用在线路由器列表替换原列表
        routerDevices.length = 0;
        routerDevices.push(...onlineRouterDevices);
      } catch (statusError) {
        if (verbose) {
          console.error(`[verbose] 获取路由器在线状态失败: ${statusError.message}`);
        }
        console.error(`⚠️  获取路由器在线状态失败: ${statusError.message}`);
      }
    }

    console.log(`\n在家中 "${selectedHome.homeName}" 发现 ${routerDevices.length} 个可能的路由器设备:`);
    
    if (routerDevices.length === 0) {
      console.log('未发现 obvious 路由器设备，将显示所有设备供选择:');
      selectedHome.devices.forEach(async (device, index) => {
        const routerInfo = device.prodId ? await getRouterInfo(device.deviceId?.toUpperCase() || '', device.prodId?.toUpperCase() || '') : null;
        const routerName = routerInfo ? ` (${routerInfo.name})` : '';
        console.log(`${index + 1}. ${device.deviceName} - ${device.productName || '无产品信息'}${routerName} (ID: ${device.deviceId}, 产品ID: ${device.prodId})`);
      });
    } else {
      routerDevices.forEach(async (device, index) => {
        const routerInfo = await getRouterInfo(device.deviceId?.toUpperCase() || '', device.prodId?.toUpperCase() || '');
        let deviceDisplay = `${index + 1}. ${device.deviceName} - ${device.productName || '无产品信息'}`;
        
        if (routerInfo) {
          deviceDisplay += ` [${routerInfo.name}]`;
          if (routerInfo.model) {
            deviceDisplay += ` (${routerInfo.model})`;
          }
        } else if (device.prodId) {
          deviceDisplay += ` (产品ID: ${device.prodId})`;
        }
        
        console.log(deviceDisplay);
      });
    }

    console.log('\n智慧建议:');
    
    // 第4步：智能选择路由器
    let selectedDevice = null;

    // 路由器排序保证确定性
    routerDevices.sort((a, b) => a.deviceId.localeCompare(b.deviceId));

    if (routerDevices.length > 0) {
      // 优先选择有映射信息的路由器
      const prioritizedDevices = [];
      for (const device of routerDevices) {
        const routerInfo = await getRouterInfo(device.deviceId?.toUpperCase() || '', device.prodId?.toUpperCase() || '');
        if (routerInfo !== null) {
          prioritizedDevices.push(device);
        }
      }

      const suggestedDevice = prioritizedDevices[0] || routerDevices[0];

      const routerInfo = await getRouterInfo(suggestedDevice.deviceId?.toUpperCase() || '', suggestedDevice.prodId?.toUpperCase() || '');
      const routerDisplay = routerInfo ? `${routerInfo.name}` : suggestedDevice.deviceName;
      const modelDisplay = routerInfo ? ` (${routerInfo.model})` : '';

      console.log(`-> 建议使用: ${routerDisplay}${modelDisplay}`);

      // --batch-mode 或只有一个路由器：直接使用
      if (batchMode || routerDevices.length === 1) {
        selectedDevice = suggestedDevice;
        if (batchMode) {
          console.log(`✓ --batch-mode，自动选择该路由器`);
        } else {
          console.log(`✓ 自动选择唯一的路由器`);
        }
      } else {
        // 多个路由器且不是 batch-mode，报错提示
        const routerList = routerDevices.map((d, i) => {
          return `${i + 1}. ${d.deviceName} (ID: ${d.deviceId}, 产品ID: ${d.prodId})`;
        }).join('\n');
        throw new Error(`发现 ${routerDevices.length} 个路由器，请使用 --router-id --prod-id 指定:\n${routerList}`);
      }
    } else {
      // 没有识别到路由器
      if (batchMode) {
        // --batch-mode：选择第一个设备
        selectedDevice = selectedHome.devices[0];
        console.log(`✓ --batch-mode，自动选择第一个设备: ${selectedDevice.deviceName}`);
      } else {
        throw new Error('未识别到路由器设备，请使用 --router-id --prod-id 指定');
      }
    }

    if (!selectedDevice) {
      throw new Error('未选择路由器，请重试');
    }

    // 从映射表中获取路由器信息
    const routerInfo = await getRouterInfo(selectedDevice.deviceId?.toUpperCase() || '', selectedDevice.prodId?.toUpperCase() || '');
    const routerDisplay = routerInfo ? `${routerInfo.name}` : selectedDevice.deviceName;
    const modelDisplay = routerInfo ? ` (${routerInfo.model})` : '';

    console.log(`\n✓ 已选择路由器: ${routerDisplay}${modelDisplay}`);
    console.log(`  - 设备ID (devid): ${selectedDevice.deviceId}`);
    console.log(`  - 产品ID (prodid): ${selectedDevice.prodId || '无'}`);

    // 第5步：设置路由器设备id和产品id变量
    const devId = selectedDevice.deviceId;
    const prodId = selectedDevice.prodId || '';

    return { devId, prodId };

  } catch (error) {
    console.error(`\n❌ 自动配置失败: ${error.message}`);
    console.error('\n请按以下步骤手动配置:');
    console.error('1. node common-skill/bin/smarthome-claw.js get_homes_info');
    console.error('2. node common-skill/bin/smarthome-claw.js get_devices_info'); 
    console.error('3. 根据输出的设备信息，使用--router-id <路由器设备ID> --prod-id <产品ID> 指定设备');

    throw new Error('自动配置路由器设备id失败，请按照日志提示手动配置');
  }
}

// ==================== 遍历所有家庭所有路由器 ====================
async function callRouterClawAllHomes(tools, skillId, verbose = false) {
  // 拦截 SET 操作，--all-homes 仅支持查询
  const SET_PREFIXES = ['set_', 'deny_', 'allow_', 'add_', 'del_'];
  const setTools = tools.filter(t => SET_PREFIXES.some(p => t.name.startsWith(p)));
  if (setTools.length > 0) {
    console.error(JSON.stringify({
      error: 'SET_NOT_ALLOWED_IN_ALL_HOMES',
      message: `--all-homes 模式仅支持查询操作，不支持: ${setTools.map(t => t.name).join(', ')}`
    }));
    process.exit(1);
  }

  if (verbose) {
    console.log('[verbose] --all-homes 模式：遍历所有家庭所有路由器');
  }

  // 第1步：获取所有设备信息
  console.log('\n========== --all-homes 模式 ==========');
  console.log('步骤1: 获取所有设备信息...');

  let devicesInfo = null;

  // 尝试从缓存读取
  const cacheDir = path.join(__dirname, '../../common-skill/out_put/get_devices_info');
  const deviceCacheFile = path.join(cacheDir, 'devices_info.txt');

  if (fs.existsSync(deviceCacheFile)) {
    try {
      const cachedData = fs.readFileSync(deviceCacheFile, 'utf-8');
      devicesInfo = JSON.parse(cachedData);
      console.log(`✓ 从缓存获取到 ${devicesInfo.length} 个设备`);
    } catch (cacheError) {
      console.error('⚠️  缓存读取失败，将重新获取');
    }
  }

  // 如果没有缓存，重新获取
  if (!devicesInfo) {
    const devicesResult = await import('../../common-skill/bin/get_devices_info.js');
    const getDevicesResult = await devicesResult.getDevicesInfo(false);
    devicesInfo = getDevicesResult.devices;
    console.log(`✓ 获取到 ${devicesInfo.length} 个设备`);
  }

  // 第2步：按 homeId 分组获取所有家庭
  console.log('步骤2: 识别所有家庭...');

  const homeMap = new Map();
  devicesInfo.forEach(device => {
    const homeId = device.homeId;
    if (homeId && homeId.trim()) {
      if (!homeMap.has(homeId)) {
        homeMap.set(homeId, {
          homeId: homeId,
          homeName: device.homeName || '未命名家庭',
          devices: []
        });
      }
      homeMap.get(homeId).devices.push(device);
    }
  });

  const homes = Array.from(homeMap.values());

  if (homes.length === 0) {
    throw new Error('未能识别到有效的家庭信息');
  }

  console.log(`✓ 发现 ${homes.length} 个家庭`);

  // 第3步：加载路由器设备信息映射表
  let routerDeviceInfo = null;
  try {
    routerDeviceInfo = (await import('./router_device_info.js')).default;
  } catch (infoError) {
    if (verbose) {
      console.error('[verbose] 路由器设备信息映射加载失败');
    }
  }

  // 第4步：遍历每个家庭，筛选路由器设备
  console.log('步骤3: 筛选每个家庭的路由器设备...');
  // homeId, homeName, devId, prodId, deviceName
  const allRouterDevices = [];

  for (const home of homes) {
    const routerDevices = home.devices.filter(device => {
      if (!device.prodId || !device.deviceId) {
        return false;
      }

      const prodId = device.prodId?.toUpperCase() || '';

      // 检查是否在路由器设备信息映射表中
      if (routerDeviceInfo) {
        const isInDeviceInfo = routerDeviceInfo.some(routerInfo => {
          return routerInfo[0] === device.deviceId?.toUpperCase() || routerInfo[1] === prodId;
        });
        if (isInDeviceInfo) {
          return true;
        }
      }

      // 通过名称判断
      const deviceName = (device.deviceName || '').toLowerCase();
      const productName = (device.productName || '').toLowerCase();
      const isRouterByName = deviceName.includes('路由') || deviceName.includes('router') ||
        deviceName.includes('gateway') ||
        productName.includes('路由') || productName.includes('router') || productName.includes('gateway');
      return isRouterByName;
    });

    for (const router of routerDevices) {
      allRouterDevices.push({
        homeId: home.homeId,
        homeName: home.homeName,
        devId: router.deviceId,
        prodId: router.prodId,
        deviceName: router.deviceName
      });
    }
  }

  if (allRouterDevices.length === 0) {
    console.error('⚠️  未发现任何路由器设备');
    console.log(JSON.stringify([], null, 2));
    return;
  }

  console.log(`✓ 发现 ${allRouterDevices.length} 个路由器设备分布在 ${homes.length} 个家庭中`);

  // 第4.5步：获取路由器在线状态并过滤离线的路由器
  console.log('步骤3.5: 获取路由器在线状态...');
  try {
    const routerDeviceIds = allRouterDevices.map(r => r.devId);
    const onlineStatusResult = await getDevicesOnlineStatus(routerDeviceIds, verbose);
    const onlineDeviceIds = new Set(
      onlineStatusResult.statuses
        .filter(s => s.status === 'online')
        .map(s => s.deviceId)
    );

    const offlineRouters = allRouterDevices.filter(r => !onlineDeviceIds.has(r.devId));
    offlineRouters.forEach(r => {
      console.log(`  - 已过滤离线路由器: ${r.homeName} - ${r.deviceName}`);
    });

    const onlineRouterDevices = allRouterDevices.filter(r => onlineDeviceIds.has(r.devId));
    console.log(`✓ 在线路由器: ${onlineRouterDevices.length}/${allRouterDevices.length}`);

    if (onlineRouterDevices.length === 0) {
      console.error('⚠️  没有在线的路由器设备');
      console.log(JSON.stringify([], null, 2));
      return;
    }

    // 将过滤后的在线路由器列表替换原列表
    allRouterDevices.length = 0;
    allRouterDevices.push(...onlineRouterDevices);
  } catch (statusError) {
    if (verbose) {
      console.error(`[verbose] 获取路由器在线状态失败: ${statusError.message}`);
    }
    console.error('⚠️  获取路由器在线状态失败，将继续对所有路由器执行操作');
  }

  // 第5步：对每个路由器执行工具
  console.log('步骤4: 依次查询每个路由器的儿童上网保护信息...');

  const results = [];

  for (const router of allRouterDevices) {
    if (verbose) {
      console.log(`[verbose] 查询 ${router.homeName} - ${router.deviceName} (devId: ${router.devId})`);
    } else {
      console.log(`- ${router.homeName} - ${router.deviceName}`);
    }

    // 为当前路由器执行工具
    for (const tool of tools) {
      try {
        const payload = {
          devId: router.devId,
          prodId: router.prodId,
          mode: 'ACK',
          operation: tool.name.startsWith('set_') ? 'SET' : 'GET',
          sid: ROUTER_PATHS[tool.name] || tool.name
        };

        const res = await hagControl(payload, verbose);

        // 处理结果：转换 appId 为应用名称
        if (tool.name === 'get_child_protect' && res?.data?.payload) {
          let payloadData = typeof res.data.payload === 'string'
            ? JSON.parse(res.data.payload)
            : res.data.payload;
          payloadData = transformChildProtectData(payloadData);
          res.data.data = payloadData;
        }

        // 脱敏处理：对 get_guest_wifi 的密码字段和 get_wan_status 的 Username/Password 进行脱敏
        if (tool.name === 'get_guest_wifi' || tool.name === 'get_wan_status') {
          let payloadContainer = null;
          if (res?.data?.data?.payload) {
            payloadContainer = res.data.data;
          } else if (res?.data?.payload) {
            payloadContainer = res.data;
          }
          if (payloadContainer && typeof payloadContainer.payload === 'string') {
            try {
              const payloadObj = JSON.parse(payloadContainer.payload);
              let maskedPayload;
              if (tool.name === 'get_wan_status') {
                maskedPayload = maskWanSensitiveFields(payloadObj);
              } else {
                maskedPayload = maskWifiPassword(payloadObj);
              }
              if (maskedPayload && JSON.stringify(maskedPayload) !== payloadContainer.payload) {
                payloadContainer.payload = JSON.stringify(maskedPayload);
              }
            } catch (_) {
              // payload 解析失败，保持原样
            }
          }
        }

        results.push({
          homeId: router.homeId,
          homeName: router.homeName,
          deviceId: router.devId,
          deviceName: router.deviceName,
          tool: tool.name,
          success: true,
          data: res
        });
      } catch (err) {
        if (verbose) {
          console.error(`[verbose] 查询失败: ${err.message}`);
        }
        results.push({
          homeId: router.homeId,
          homeName: router.homeName,
          deviceId: router.devId,
          deviceName: router.deviceName,
          tool: tool.name,
          success: false,
          error: err.message
        });
      }
    }
  }

  // 第6步：输出结果
  console.log('\n========== 查询结果汇总 ==========');
  console.log(JSON.stringify(results, null, 2));

  return results;
}

// ==================== 遍历指定家庭的所有在线路由器 ====================
async function callRouterClawForHome(homeId, tools, skillId, verbose = false) {
  console.log(`\n========== --home-id 模式: ${homeId} ==========`);

  // 第1步：获取设备信息
  let devicesInfo = null;
  const cacheDir = path.join(__dirname, '../../common-skill/out_put/get_devices_info');
  const deviceCacheFile = path.join(cacheDir, 'devices_info.txt');

  if (fs.existsSync(deviceCacheFile)) {
    try {
      devicesInfo = JSON.parse(fs.readFileSync(deviceCacheFile, 'utf-8'));
      console.log(`✓ 从缓存获取到 ${devicesInfo.length} 个设备`);
    } catch (e) { /* 忽略 */ }
  }
  if (!devicesInfo) {
    const devicesResult = await import('../../common-skill/bin/get_devices_info.js');
    devicesInfo = (await devicesResult.getDevicesInfo(false)).devices;
    console.log(`✓ 获取到 ${devicesInfo.length} 个设备`);
  }

  // 第2步：筛选指定家庭的设备
  const homeDevices = devicesInfo.filter(d => d.homeId === homeId);
  if (homeDevices.length === 0) {
    console.error(JSON.stringify({
      error: 'HOME_NOT_FOUND',
      message: `未找到家庭: ${homeId}`
    }));
    process.exit(1);
  }
  const homeName = homeDevices[0].homeName || '未命名家庭';
  console.log(`✓ 家庭: ${homeName}, 设备数: ${homeDevices.length}`);

  // 第3步：筛选路由器设备
  let routerDeviceInfo = null;
  try {
    routerDeviceInfo = (await import('./router_device_info.js')).default;
  } catch (e) { /* 忽略 */ }

  const routerDevices = homeDevices.filter(device => {
    if (!device.prodId || !device.deviceId) return false;
    const prodId = device.prodId?.toUpperCase() || '';
    if (routerDeviceInfo) {
      const match = routerDeviceInfo.some(r => r[0] === device.deviceId?.toUpperCase() || r[1] === prodId);
      if (match) return true;
    }
    const name = (device.deviceName || '').toLowerCase();
    const product = (device.productName || '').toLowerCase();
    return name.includes('路由') || name.includes('router') || name.includes('gateway') ||
           product.includes('路由') || product.includes('router') || product.includes('gateway');
  });

  if (routerDevices.length === 0) {
    console.error(JSON.stringify({
      error: 'NO_ROUTER_FOUND',
      message: `家庭 "${homeName}" 下没有路由器设备`
    }));
    process.exit(1);
  }
  console.log(`✓ 发现 ${routerDevices.length} 个路由器设备`);

  // 第4步：过滤离线路由器
  try {
    const ids = routerDevices.map(r => r.deviceId);
    const statusResult = await getDevicesOnlineStatus(ids, verbose);
    const onlineIds = new Set(statusResult.statuses.filter(s => s.status === 'online').map(s => s.deviceId));
    const offline = routerDevices.filter(r => !onlineIds.has(r.deviceId));
    offline.forEach(r => console.log(`  - 已过滤离线: ${r.deviceName}`));
    const online = routerDevices.filter(r => onlineIds.has(r.deviceId));
    if (online.length === 0) {
      console.error(JSON.stringify({
        error: 'NO_ONLINE_ROUTER',
        message: `家庭 "${homeName}" 下没有在线的路由器设备`
      }));
      process.exit(1);
    }
    console.log(`✓ 在线路由器: ${online.length}/${routerDevices.length}`);
    routerDevices.length = 0;
    routerDevices.push(...online);
  } catch (e) {
    if (verbose) console.error(`[verbose] 在线状态检查失败: ${e.message}`);
    console.error('⚠️ 在线状态检查失败，将继续对所有路由器执行操作');
  }

  // 第5步：对每个在线路由器调用完整的 callRouterClaw
  const allResults = [];
  for (const router of routerDevices) {
    console.log(`\n--- 执行: ${homeName} - ${router.deviceName} ---`);
    ROUTER_DEVICE_ID = router.deviceId;
    ROUTER_PROD_ID = router.prodId;
    const results = await callRouterClaw(tools, skillId, verbose);
    if (results) {
      allResults.push({
        homeName,
        deviceName: router.deviceName,
        devId: router.deviceId,
        results
      });
    }
  }

  // 第6步：输出汇总
  console.log('\n========== 查询结果汇总 ==========');
  console.log(JSON.stringify(allResults, null, 2));
  return allResults;
}

// ==================== 核心调度函数 ====================
async function callRouterClaw(tools, skillId, verbose = false, retryCount = 0) {
  const MAX_RETRY = 1; // 最多重试 1 次，避免无限循环

  // ========== 处理 --all-homes 模式：遍历所有家庭所有路由器 ==========
  if (QUERY_ALL_HOMES) {
    console.log('[debug] 走 --all-homes 分支');
    return await callRouterClawAllHomes(tools, skillId, verbose);
  }

  // ========== 优先检查 ROUTER_DEVICE_ID（由 callRouterClawForHome 设置）==========
  // 必须在 TARGET_HOME_ID 之前，否则 callRouterClawForHome 调用 callRouterClaw 时
  // 会因 TARGET_HOME_ID 仍存在而无限递归
  if (ROUTER_DEVICE_ID && ROUTER_PROD_ID) {
    console.log(`[debug] 走 --router-id 分支: ${ROUTER_DEVICE_ID}`);
  } else if (TARGET_HOME_ID) {
    // ========== 处理 --home-id 模式：遍历该家庭所有在线路由器 ==========
    console.log(`[debug] 走 --home-id 分支: ${TARGET_HOME_ID}`);
    return await callRouterClawForHome(TARGET_HOME_ID, tools, skillId, verbose);
  } else {
    console.log('[debug] 走默认分支（batch-mode/savedConfig）');
  }

  // ========== 参数优先级：router-id > batch-mode > savedConfig ==========
  let devId = null;
  let prodId = null;

  // 1. 如果指定了 --router-id，直接使用
  if (ROUTER_DEVICE_ID) {
    devId = ROUTER_DEVICE_ID;
    prodId = ROUTER_PROD_ID;

    // 参数完整性校验
    if (!prodId) {
      console.error(JSON.stringify({
        error: 'MISSING_PROD_ID',
        message: '使用 --router-id 时必须同时指定 --prod-id'
      }));
      process.exit(1);
    }

    // 路由器在线状态预检
    try {
      const onlineResult = await getDevicesOnlineStatus([devId], verbose);
      const isOnline = onlineResult.statuses?.some(s => s.deviceId === devId && s.status === 'online');
      if (!isOnline) {
        console.error(JSON.stringify({
          error: 'DEVICE_OFFLINE',
          message: '路由器设备当前离线',
          devId: devId
        }));
        process.exit(1);
      }
    } catch (e) {
      if (verbose) console.log(`[verbose] 在线状态检查失败，继续执行: ${e.message}`);
    }

    if (verbose) {
      console.log(`[verbose] 使用 --router-id 指定: ${devId}`);
      console.log(`[verbose] 使用 --prod-id 指定: ${prodId}`);
    }
  }
  // 2. --batch-mode：自动选第一个家庭第一个路由器
  else if (BATCH_MODE) {
    try {
      console.log('[info] --batch-mode 模式，自动配置...');
      const configured = await autoConfigureEnv(verbose, { batchMode: true });
      devId = configured.devId;
      prodId = configured.prodId;
      console.log('[info] ✓ 自动配置完成');
    } catch (autoConfigError) {
      console.error(autoConfigError.message);
      process.exit(1);
    }
  }

  if (verbose) {
    console.log(`[verbose] DEV_ID = ${devId}`);
    console.log(`[verbose] PROD_ID = ${prodId}`);
  }

  // 缺少路由器配置时报错
  if (!devId || !prodId) {
    console.error(JSON.stringify({
      error: 'MISSING_ROUTER_CONFIG',
      message: '缺少路由器配置，请优先阅读 router-skill/SKILL.md 中"AI 调用规范"章节，严格遵循参数使用规则'
    }));
    process.exit(1);
  }

  const results = [];
  
  // 检查哪些操作需要后续查询验证
  const needsVerification = tools.filter(tool => 
    tool.name === 'set_net_time' || 
    tool.name === 'set_net_duration' ||
    tool.name === 'set_net_off'
  );
  
  // 为需要验证的操作添加查询任务
  const allTools = [...tools];
  needsVerification.forEach(setTool => {
    const queryTool = {
      name: 'get_child_protect', 
      args: setTool.args
    };
    // 查询任务只添加一次
    if (!tools.some(t => t.name === 'get_child_protect')) {
      allTools.push(queryTool);
    }
  });
  
  // ========== 特殊工具预处理（需要调用多个API或自定义逻辑） ==========
  const specialTools = ['get_wifi_config'];
  const processedTools = new Set();

  // 先处理特殊工具
  for (const tool of allTools) {
    const { name, args } = tool;

    if (name === 'get_wifi_config') {
      processedTools.add(name);
      // get_wifi_config 需要调用两个 GET 接口：
      // 1. GET .sys/gateway/ntwk/wlandbho - 获取5G优选开关配置
      // 2. GET .sys/gateway/ntwk/WlanBasic - 获取SSID配置

      // 调用第一个接口获取5G优选配置
      const res1 = await hagControl({
        devId,
        prodId,
        mode: 'ACK',
        operation: 'GET',
        sid: '.sys/gateway/ntwk/wlandbho'
      }, args.verbose);

      // 调用第二个接口获取SSID配置
      const res2 = await hagControl({
        devId,
        prodId,
        mode: 'ACK',
        operation: 'GET',
        sid: '.sys/gateway/ntwk/WlanBasic'
      }, args.verbose);

      // 对WlanBasic返回结果中的密码字段进行脱敏处理
      // 注意：payload 是 JSON 字符串，需要先解析才能被 maskWifiPassword 递归遍历到内部密码字段
      let wlanBasicData = res2?.data?.data || res2?.data || {};
      if (wlanBasicData.payload && typeof wlanBasicData.payload === 'string') {
        try {
          wlanBasicData.payload = JSON.parse(wlanBasicData.payload);
        } catch (_) {}
      }
      const maskedWlanBasic = maskWifiPassword(wlanBasicData);

      // 合并两个接口的返回结果
      results.push({
        tool: name,
        success: true,
        data: {
          // 5G优选开关配置
          wlandbho: res1?.data?.data || res1?.data || {},
          // SSID配置（密码已脱敏）
          WlanBasic: maskedWlanBasic
        }
      });
      continue;
    }
  }

  // ========== 主循环处理普通工具 ==========
  for (const tool of allTools) {
    const { name, args } = tool;

    // 跳过已处理的特殊工具
    if (processedTools.has(name)) {
      continue;
    }

    const sid = ROUTER_PATHS[name];

    if (!sid) {
      // 本地操作（不走路由API）
      if (name === 'config_presence') {
        if (args?.detect) {
          // 自动探测：先查询 get_host_info，返回在线设备列表供用户选择配置
          const detectPayload = {
            devId, prodId,
            sid: ROUTER_PATHS.get_host_info,
            mode: 'ACK',
            operation: 'GET'
          };
          try {
            const detectRes = await hagControl(detectPayload, args.verbose);
            let deviceList = null;
            if (detectRes?.data?.payload) {
              const raw = detectRes.data.payload;
              if (typeof raw === 'string') {
                try {
                  deviceList = JSON.parse(raw);
                } catch (pe) {
                  console.error(`[verbose] config_presence 解析 payload 失败: ${pe.message}`, String(raw).slice(0, 200));
                }
              } else if (raw?.content) {
                const b = Buffer.from(raw.content, 'base64');
                const r = await gunzip(b);
                deviceList = JSON.parse(r.toString());
              } else {
                console.error('[verbose] config_presence: payload 结构异常:', JSON.stringify(raw));
              }
            } else {
              console.error('[verbose] config_presence: detectRes.data.payload 为空', JSON.stringify(detectRes));
            }
            if (Array.isArray(deviceList)) {
              const mobiles = deviceList.filter(d => {
                const icon = d.IconType || '';
                return icon === 'mobile' || icon === 'phone' || (d.WlanActive === true && !d.HiLinkDevice);
              }).map(d => ({
                HostName: d.HostName,
                Active: d.Active,
                MACAddress: d.MACAddress || ''
              }));
              results.push({
                tool: name,
                success: true,
                data: {
                  message: '请从以下在线设备中配置家庭成员。将配置保存到 TOOLS.md',
                  devices: mobiles
                },
                message: `✓ config_presence 自动探测完成，发现 ${mobiles.length} 台终端设备`,
                timestamp: new Date().toISOString()
              });
            } else {
              results.push({
                tool: name,
                success: true,
                data: { message: '未发现终端设备', devices: [] },
                message: '✓ config_presence 自动探测完成，未发现终端设备',
                timestamp: new Date().toISOString()
              });
            }
          } catch (e) {
            results.push({
              tool: name,
              success: false,
              data: { message: `探测失败: ${e.message}` },
              message: `❌ config_presence 探测失败`,
              timestamp: new Date().toISOString()
            });
          }
        }
        continue;
      } else if (name === 'get_app_info') {
      // 本地查询，不调路由器 API
      const appResult = await handleGetAppInfo(args.app_id || args.appId || String(args.id));
      results.push({
        tool: name,
        success: appResult.success,
        data: appResult.data,
        message: appResult.message
      });
      continue;
    } else if (name === 'get_all_apps') {
      // 本地查询，不调路由器 API
      const appsResult = await handleGetAllApps();
      results.push({
        tool: name,
        success: appsResult.success,
        data: appsResult.data,
        message: appsResult.message
      });
      continue;
    }
      console.error(`[warning] 未知工具：${name}`);
      continue;
    }

    let payload = {
      devId,
      prodId,
      sid,
      mode: 'ACK',  // 路由器使用 ACK 模式
      operation: 'GET'  // 默认 GET
    };

    // ========== 信息查询 GET ==========
    const GET_OPERATIONS = [
      'get_host_info', 'get_child_protect', 'get_wan_status', 'get_wandetect',
      'get_channel_info', 'get_5g_optimize', 'get_ipv6', 'get_user_behavior',
      'get_router_status', 'get_guest_wifi', 'get_power_mode', 'get_link_rate',
      'get_eth_negotiation', 'get_game_history', 'get_lan_host', 'get_week_report',
      'check_presence'
    ];
    if (GET_OPERATIONS.includes(name)) {
      payload.operation = 'GET';
    }

    // ========== 控制操作 POST ==========
    else if (name === 'set_guest_wifi') {
      payload.operation = 'POST';
      // 构建访客WiFi配置数据（访客WiFi强制为开放网络，不支持密码设置）
      // ValidTime 取值：1=4小时, 2=一天, 3=不限时
      const enable = args.data?.enable !== undefined ? args.data.enable : true;
      const ssid = args.data?.ssid || 'Guest_WiFi';
      // 校验 ValidTime 是否在有效范围 [1, 2, 3] 内，不在则默认设置为 2（一天）
      const validTimeValues = [1, 2, 3];
      let validTime = args.data?.validTime;
      if (validTime === undefined || validTime === null || !validTimeValues.includes(validTime)) {
        validTime = 2;
      }
      // 访客WiFi强制为开放网络，忽略用户传入的密码参数
      const secOpt = 'none';
      const wpaKey = '';

      payload.data = {
        data: {
          config2g: {
            FrequencyBand: '2.4GHz',
            ID: 'InternetGatewayDevice.X_Config.Wifi.Radio.1.Ssid.2.',
            SecOpt: secOpt,
            WpaPreSharedKey: wpaKey,
            Enable: enable,
            WifiSsid: ssid,
            ValidTime: validTime
          },
          config5g: {
            FrequencyBand: '5GHz',
            ID: 'InternetGatewayDevice.X_Config.Wifi.Radio.2.Ssid.2.',
            SecOpt: secOpt,
            WpaPreSharedKey: wpaKey,
            Enable: enable,
            WifiSsid: ssid,
            ValidTime: validTime
          }
        }
      };
    } else if (name === 'set_channel_update') {
      payload.operation = 'POST';
      payload.data = {
        data: {
          action: 'UpdateAll',
          ChannelDeploy: 0
        }
      };
    } else if (name === 'set_5g_optimize') {
      // set_5g_optimize 简化版：只需要调用 wlandbho 接口
      // 第一步：GET .sys/gateway/ntwk/wlandbho - 查询当前配置
      // 第二步：POST .sys/gateway/ntwk/wlandbho - 下发 DbhoEnable

      const dbhoEnable = args.data?.DbhoEnable !== undefined ? args.data.DbhoEnable : true;

      // ========== 第一步：GET查询当前配置 ==========
      const queryRes = await hagControl({
        devId,
        prodId,
        mode: 'ACK',
        operation: 'GET',
        sid: '.sys/gateway/ntwk/wlandbho'
      }, args.verbose);

      // ========== 第二步：POST下发开关配置 ==========
      const postPayload = {
        devId,
        prodId,
        mode: 'ACK',
        operation: 'POST',
        sid: '.sys/gateway/ntwk/wlandbho',
        data: {
          data: {
            DbhoEnable: dbhoEnable
          }
        }
      };

      const postRes = await hagControl(postPayload, args.verbose);

      // 返回结果
      results.push({
        tool: name,
        success: postRes?.success || false,
        message: postRes?.success ? '5G优选设置成功' : '5G优选设置失败',
        data: { query: queryRes, set: postRes }
      });
      return;
    } else if (name === 'set_ipv6') {
      payload.operation = 'POST';
      const enable = args.data?.Enable !== undefined ? args.data.Enable : true;
      payload.data = {
        data: {
          Enable: enable
        }
      };
    } else if (name === 'set_user_behavior') {
      payload.operation = 'POST';
      const enable = args.data?.Enable !== undefined ? args.data.Enable : true;
      payload.data = {
        data: {
          Enable: enable
        }
      };
    } else if (name === 'set_power_mode') {
      payload.operation = 'POST';
      // 校验 PowerMode 是否在有效范围 [0, 1, 2] 内，不在则默认设置为 2（穿墙模式）
      const validPowerModes = [0, 1, 2];
      let PowerMode = args.data?.PowerMode;
      if (PowerMode === undefined || PowerMode === null || !validPowerModes.includes(PowerMode)) {
        PowerMode = 2;
      }
      payload.data = {
        data: {
          Enable5G: true,
          InitEnable5G: true,
          Enable2G: true,
          InitEnable2G: true,
          PowerMode: PowerMode
        }
      };
    } else if (name === 'set_Game_acceleration') {
      payload.operation = 'POST';
      const hiGameControlEnable = args.data?.HiGameControlEnable !== undefined ? args.data.HiGameControlEnable : "true";
      payload.data = {
        data: {
          HiGameControlEnable: hiGameControlEnable
        }
      };
    } else if (name === 'set_wifi_timeswitch') {
      payload.operation = 'POST';
      payload.data = {
        action:args.action,
        data: {
          datelist:args.data
        }
      };
    } else if (name === 'smart_dev_connect') {
      payload.operation = 'POST';
      payload.data = {
        action:"add",
        data:args.data
      };
    } else if (name === 'set_upload_log') {
      payload.operation = 'POST';
      payload.data = {
        data:args.data,
        action:"update"
      };
    } else if (name === 'set_online_upg' || name === 'set_reboot'|| name === 'set_Device_ratelimit') {
      payload.operation = 'POST';
      payload.data = {
        action:args.action,
        data:args.data
      };
    } else if (name === 'set_antisteal_mode') {
      payload.operation = 'POST';
      // 校验 StealNetModel 是否在有效范围 [0, 1, 2] 内，不在则默认设置为 0（黑名单模式）
      const validStealNetModels = [0, 1, 2];
      let stealNetModel = args.data?.StealNetModel;
      if (stealNetModel === undefined || stealNetModel === null || !validStealNetModels.includes(stealNetModel)) {
        stealNetModel = 0;
      }
      payload.data = {
        update:"update",
        data: {
          StealNetModel: stealNetModel
        }
      };
    } else if (name === 'set_homesec_abfa') {
      payload.operation = 'POST';
      const abfaEnable = args.data?.AbfaEnable !== undefined ? args.data.AbfaEnable : true;
      payload.data = {
        action:"update",
        data: {
          AbfaEnable: abfaEnable
        }
      };
    } else if (name === 'set_auth_Device') {
      payload.operation = 'POST';
      // 校验 operFlag 是否在有效范围 [1, 2, 5] 内，不在则默认设置为 1（设备加入授权）
      const validoperFlags = [1, 2, 5];
      let operFlag = args.data?.operFlag;
      if (operFlag === undefined || operFlag === null || !validoperFlags.includes(operFlag)) {
        operFlag = 1;
      }
      payload.data = {
        data: {
          enable:true,
          operFlag: operFlag,
          mac: args.data.mac
        }
      };
    } else if (name === 'set_led_status') {
      payload.operation = 'POST';
      const action = args.data?.Action !== undefined ? args.data.Action : 1;
      payload.data = {
        data: {
          Action: action,
          Mac: args.data.Mac
        }
      };
    } else if (name === 'add_child_device') {
      const action = 'create';
      payload.operation = 'POST';
      payload.sid = ROUTER_PATHS.add_child_device;
      payload.data = {
        action: action,
        data: {
          action: action,
          devices: args.data?.devices || [],
          names: args.data?.names || [],
          privacyStatus: args.data?.privacyStatus || 0,
          type: args.data?.type || 0,
          urlStatus: args.data?.urlStatus || 0
        }
      };
    } else if (name === 'del_child_device') {
      const action = 'delete';
      payload.operation = 'POST';
      payload.sid = ROUTER_PATHS.del_child_device;
      payload.data = {
        action: action,
        data: {
          device: args.data?.device || '1'
        }
      };
    } else if (name === 'set_net_time') {
      const action = args.action || 'newCreate';
      payload.operation = 'POST';
      payload.sid = `.sys/gateway/ntwk/childFrame?devid=${String(args.deviceId || '1')}`;
      payload.data = {
        action: action,
        data: args.data
      };
    } else if (name === 'set_block_time') {
      // 不允许上网时段反向转换为允许上网时段
      // 参数: forbidStart, forbidEnd, weekdays
      // weekdays: weekday(工作日), weekend(周末), everyday(每天)
      const forbidStart = args.forbidStart || args.data?.forbidStart;
      const forbidEnd = args.forbidEnd || args.data?.forbidEnd;
      const weekdays = args.weekdays || args.data?.weekdays || 'everyday';
      const deviceId = args.deviceId || '1';

      if (!forbidStart || !forbidEnd) {
        console.error('错误: 需要提供 forbidStart 和 forbidEnd 参数');
        process.exit(1);
      }

      // ========== 第一步：查询已有配置 ==========
      let existingRules = [];
      try {
        const queryPayload = {
          devId,
          prodId,
          mode: 'ACK',
          operation: 'GET',
          sid: ROUTER_PATHS.get_child_protect
        };
        const queryRes = await hagControl(queryPayload, args.verbose);
        if (queryRes?.data?.data?.timeFrame) {
          existingRules = queryRes.data.data.timeFrame || [];
        }
      } catch (e) {
        console.log('提示: 无法获取已有配置，将创建新配置');
      }

      // ========== 第二步：分析并生成操作命令 ==========
      // 检查禁止时段是否本来就完全在"不允许"范围内
      if (isForbidPeriodAlreadyDenied(forbidStart, forbidEnd, existingRules, weekdays)) {
        console.log(`提示: ${forbidStart}~${forbidEnd} (${weekdays}) 时段本身就不在允许上网范围内，无需额外配置`);
        return;
      }

      // 生成操作命令列表
      let tools = generateBlockToAllowCommands(deviceId, forbidStart, forbidEnd, weekdays);

      // 检查是否需要删除冲突的允许时段
      if (needDeleteConflictingRules(forbidStart, forbidEnd, existingRules, weekdays)) {
        const everydayConfig = { monday: 1, tuesday: 1, wednesday: 1, thursday: 1, friday: 1, saturday: 1, sunday: 1 };
        tools.unshift({
          name: 'set_net_time',
          args: {
            action: 'newDelete',
            data: { id: 'all', enable: 0, timeFrom: '00:00', timeTo: '23:59', today: 1, device: deviceId, ...everydayConfig },
            deviceId
          }
        });
      }

      // 批量执行
      for (const tool of tools) {
        await callRouterClaw([tool], args.skillId, args.verbose);
      }
      return;
    } else if (name === 'set_app_control') {
      const action = 'update';
      payload.operation = 'POST';
      payload.sid = `.sys/gateway/ntwk/childModelApps?devid=${String(args.deviceId || '1')}&type=${args.type || 1}`;
      payload.data = {
        action: action,
        data: args.data
      };
    } else if (name === 'set_net_off') {
      const action = 'delayUpdate';
      payload.operation = 'POST';
      payload.sid = '.sys/gateway/ntwk/childHomepage';
      payload.data = {
        action: action,
        data: args.data
      };
    } else if (name === 'set_net_duration') {
      const action = args.action || 'update';
      payload.operation = 'POST';
      payload.sid = '.sys/gateway/ntwk/childDailyUpdate';
      payload.data = {
        action: action,
        data: args.data || { daily: { monday: 90000, tuesday: 90000, wednesday: 90000, thursday: 90000, friday: 90000, saturday: 90000, sunday: 90000 }, device: "1" }
      };
    }

    // ========== 应用管理禁止操作 POST ==========
    else if (name === 'deny_games') {
      payload.operation = 'POST';
      payload.sid = '.sys/gateway/ntwk/childModelApps';
      payload.data = {
        action: 'update',
        data: {
          device: args.deviceId || '1',
          apps: ["153","221","152","220","118","287","151","218","286","252","251","285","250","284","114","283","249","147","113","215","282","248","112","281","145","247","213","280","144","246","108","279","107","175","278","244","106","140","243","209","277","105","207","276","104","206","275","171","239","103","170","238","102","203","169","101","100","201","233","131","199","232","130","163","231","230","196","195","228","193","123","191","192","122","156","225","155","189","224","154","255","254","216","181","180","179","178","211","210","271","270","167","133","234","268","166","267","165","266","265","197","264","161","160","158","227","261","157","226","260","259","222","257","187","256","186","185","253","117","184","150","116","217","149","182","148","146","214","109","142","177","139","274","240","204","273","135","202","134","200","132","198","164","129","162","126","125","124","121","223","258","120","188"],
          denyAll: 0,
          type: 1
        }
      };
    } else if (name === 'deny_videos') {
      payload.operation = 'POST';
      payload.sid = '.sys/gateway/ntwk/childModelApps';
      payload.data = {
        action: 'update',
        data: {
          device: args.deviceId || '1',
          apps: ["320","314","348","347","313","346","311","309","339","338","337","335","802","804","803","324","323","322","321","319","318","312","310","308","303","336","334","333","332","331","330","328","327","350","349","342","341","340","345","344","343"],
          denyAll: 0,
          type: 2
        }
      };
    } else if (name === 'deny_social') {
      payload.operation = 'POST';
      payload.sid = '.sys/gateway/ntwk/childModelApps';
      payload.data = {
        action: 'update',
        data: {
          device: args.deviceId || '1',
          apps: ["401","400","408","407","406"],
          denyAll: 0,
          type: 3
        }
      };
    } else if (name === 'deny_shopping') {
      payload.operation = 'POST';
      payload.sid = '.sys/gateway/ntwk/childModelApps';
      payload.data = {
        action: 'update',
        data: {
          device: args.deviceId || '1',
          apps: ["503","502","501","500","512","508","511","510","509"],
          denyAll: 0,
          type: 4
        }
      };
    } else if (name === 'deny_install') {
      payload.operation = 'POST';
      payload.sid = '.sys/gateway/ntwk/childModelApps';
      payload.data = {
        action: 'update',
        data: {
          device: args.deviceId || '1',
          apps: ["8","7","6","5","4","3","2","1"],
          denyAll: 0,
          type: 5
        }
      };
    } else if (name === 'deny_app') {
      /*分三步：第一步：先在sa_app_info.js中查询要禁止的app的appid和属于什么类型
      第二步：get --.sys/gateway/ntwk/childModelApps --查询相同type中有哪些之前就被禁止的app
      第三步：post --.sys/gateway/ntwk/childModelApps --是覆盖式禁止，所以必须加上之前相同type被禁止的app*/
      // 第一步：需要根据 categ 在 g_saAppInfo 中查询对应的 type
      const appsInput = args.data?.apps|| [];
      const appsArray = Array.isArray(appsInput) ? appsInput : [appsInput];
      const deviceId = String(args.data?.device || '1');
      // 根据 categ 查询对应的 type（应用分类）
      let appType = args.data?.categ || 1; // 默认游戏类型
      if (args.data.categ) {
        // 尝试从 g_saAppInfo 中查找第一个匹配APP的type
        for (const appId of appsArray) {
          const appInfo = g_saAppInfo.find(item => String(item[1]) === String(appId));
          if (appInfo) {
            // g_saAppInfo 中第三个元素是 categ，需要转换为 type
            // categ: 4->游戏(1), 16->视频(2), 128/256->社交(3), 512->购物(4), 2->安装(5), 4096/8192->学习(7)
            const categ = appInfo[2];
            const categToType = { 4: 1, 8: 2, 16: 2, 32 : 2, 128: 3, 256: 3, 512: 4, 1024: 4, 2: 5, 4096: 7, 8192: 7 };
            appType = categToType[categ] || 1;
            break;
          }
        }
      }
    // ========== 第二步：查询已有配置 ==========
      const queryPayload = {
        devId,
        prodId,
        mode: 'ACK',
        operation: 'GET',
        sid: `.sys/gateway/ntwk/childModelApps?devid=${String(args.data?.device || '1')}&type=${appType || 1}`
      };
      const queryRes = await hagControl(queryPayload, args.verbose);
      let existingApps = [];
      try {
          const payloadStr = queryRes?.data?.payload;
          if (payloadStr) {
              existingApps = JSON.parse(payloadStr).apps || [];
          }
      } catch (e) {
          // 解析失败
      }
      const validapps = [...new Set(appsArray.concat(existingApps || []))]; // 合并并去重
    // ========== 第三步：POST下发禁用配置 ==========
      payload.operation = 'POST';
      payload.sid = '.sys/gateway/ntwk/childModelApps';
      payload.data = {
        action: 'update',
        data: {
          device: deviceId,
          apps: validapps,
          denyAll: 0,
          type: appType
        }
      };
    } else if (name === 'only_deny_app') {
      // 1、某类app只禁止特定APP，覆盖之前禁止的相同type的app；2、所有app只禁止特定app，需要其他类app恢复使用
      // 需要根据 appid 在 g_saAppInfo 中查询对应的 type
      const appsInput = args.data?.apps || [];
      const appsArray = Array.isArray(appsInput) ? appsInput : [appsInput];
      const deviceId = String(args.data?.device || '1');

      // 根据 appid 查询对应的 type（应用分类）
      let appType = args.data?.categ || 1; // 默认游戏类型
      if (args.data.categ) {
        // 尝试从 g_saAppInfo 中查找第一个匹配APP的type
        for (const appId of appsArray) {
          const appInfo = g_saAppInfo.find(item => String(item[1]) === String(appId));
          if (appInfo) {
            // g_saAppInfo 中第三个元素是 categ，需要转换为 type
            // categ: 4->游戏(1), 16->视频(2), 128/256->社交(3), 512->购物(4), 2->安装(5), 4096/8192->学习(7)
            const categ = appInfo[2];
            const categToType = { 4: 1, 8: 2, 16: 2, 32 : 2, 128: 3, 256: 3, 512: 4, 1024: 4, 2: 5, 4096: 7, 8192: 7 };
            appType = categToType[categ] || 1;
            break;
          }
        }
      }

      payload.operation = 'POST';
      payload.sid = '.sys/gateway/ntwk/childModelApps';
      payload.data = {
        action: 'update',
        data: {
          device: deviceId,
          apps: appsArray,
          denyAll: 0,
          type: appType
        }
      };
    }

    // ========== 应用管理取消操作 POST（两步） ==========
    else if (name === 'allow_games') {
      const deviceId = String(args.deviceId || '1');
      const result = await handleAllowOperation(handleAllowGames, devId, prodId, deviceId, verbose, retryCount);
      if (result.retry) return callRouterClaw(tools, skillId, verbose, retryCount + 1);
      results.push(...result.results);
    } else if (name === 'allow_videos') {
      const deviceId = String(args.deviceId || '1');
      const result = await handleAllowOperation(handleAllowVideos, devId, prodId, deviceId, verbose, retryCount);
      if (result.retry) return callRouterClaw(tools, skillId, verbose, retryCount + 1);
      results.push(...result.results);
    } else if (name === 'allow_social') {
      const deviceId = String(args.deviceId || '1');
      const result = await handleAllowOperation(handleAllowSocial, devId, prodId, deviceId, verbose, retryCount);
      if (result.retry) return callRouterClaw(tools, skillId, verbose, retryCount + 1);
      results.push(...result.results);
    } else if (name === 'allow_shopping') {
      const deviceId = String(args.deviceId || '1');
      const result = await handleAllowOperation(handleAllowShopping, devId, prodId, deviceId, verbose, retryCount);
      if (result.retry) return callRouterClaw(tools, skillId, verbose, retryCount + 1);
      results.push(...result.results);
    } else if (name === 'allow_install') {
      const deviceId = String(args.deviceId || '1');
      const result = await handleAllowOperation(handleAllowInstall, devId, prodId, deviceId, verbose, retryCount);
      if (result.retry) return callRouterClaw(tools, skillId, verbose, retryCount + 1);
      results.push(...result.results);
    } else if (name === 'get_router_device_by_prodid') {
      const routerResult = await handleGetRouterDeviceByProdid(args.prodid || args.deviceId || 'K1AP');
      results.push({
        tool: name,
        success: routerResult.success,
        data: routerResult.data,
        message: routerResult.message
      });
      continue;
    }

    let res;
    try {
      // 使用 hagControl 发送请求
      res = await hagControl(payload, verbose);
    } catch (err) {
      if (err.code === 401 && retryCount < MAX_RETRY) {
        console.log('[info] token 已过期，正在自动刷新...');
        return callRouterClaw(tools, skillId, verbose, retryCount + 1);
      }
      throw err;
    }

    // 自动解码 HostInfo 的 gzip+base64 数据，并统计在线/离线设备数量
    if ((name === 'get_host_info' || name === 'check_presence') && res?.data?.payload) {
      // res.data.payload 可能是 JSON 字符串数组，也可能是含 content 字段的 gzip 压缩对象
      const rawPayload = res.data.payload;
      let deviceList = null;

      if (typeof rawPayload === 'string') {
        // 情况1：直接是 JSON 字符串数组（如 "[{...}]"）
        try {
          deviceList = JSON.parse(rawPayload);
          if (Array.isArray(deviceList)) {
            res.data.payload = deviceList;
          } else {
            deviceList = null;
          }
        } catch {
          // 非 JSON 字符串，忽略
        }
      } else if (typeof rawPayload === 'object' && rawPayload?.content) {
        // 情况2：gzip+base64 压缩数据
        const decoded = await decodeHostInfo(rawPayload.content);
        if (decoded) {
          res.data.payload = decoded;
          deviceList = decoded;
        }
      }

      // 统计在线/离线设备数量
      if (Array.isArray(deviceList)) {
        const total = deviceList.length;
        const online = deviceList.filter(d => d.Active === true).length;
        const offline = total - online;
        res.data.hostInfoSummary = {
          totalDevices: total,
          onlineDevices: online,
          offlineDevices: offline
        };
      }
    }

    // 隐私脱敏：check_presence 只暴露设备名、在线状态和接入时间
    if (name === 'check_presence' && res?.data?.payload && Array.isArray(res.data.payload)) {
      // 从 --family-map 参数读取配置，只使用 HostName 匹配
      // 格式：{ "女儿": "HUAWEI nova 14 Ultra", "儿子": "一加 Ace 5", ... }
      const familyMapArgs = args?.family_map || {};

      // 第一步：用 HostName 过滤设备（不做 MAC 匹配，因为随机 MAC 不稳定）
      let matchedByHostname = res.data.payload.filter(device => {
        // 如果传了 --name，只匹配指定的家庭成员
        if (args?.name && familyMapArgs[args.name]) {
          const config = familyMapArgs[args.name];
          const targetHostname = typeof config === 'string' ? config : config.hostname;
          return device.HostName === targetHostname;
        }
        // 如果没传 --name，但配置了家庭成员，显示所有配置的设备
        if (Object.keys(familyMapArgs).length > 0) {
          return Object.keys(familyMapArgs).some(role => {
            const config = familyMapArgs[role];
            const targetHostname = typeof config === 'string' ? config : config.hostname;
            return device.HostName === targetHostname;
          });
        }
        // 没有配置时，只保留手机类设备（过滤掉路由器、音响等）
        return device.IconType === 'mobile' || device.IconType === 'phone';
      });

      // 第二步：同型号设备冲突检测
      if (args?.name && matchedByHostname.length > 1) {
        // 多个同名设备，添加冲突提示结果，不返回具体设备
        results.push({
          tool: name,
          success: false,
          data: {
            ambiguous: true,
            message: `检测到多个同名设备（${args.name}），无法确认具体是哪一台`,
            matchedDevices: matchedByHostname.map(d => ({ HostName: d.HostName, Active: d.Active }))
          },
          message: `⚠️ 检测到多个同名设备（${args.name}），无法确认具体是哪一台，请提供更多信息（如 MAC 地址）`,
          timestamp: new Date().toISOString()
        });
        // 清除原有的 payload，避免干扰
        res.data.payload = [];
      } else {
        // 正常返回匹配结果
        res.data.payload = matchedByHostname.map(device => ({
          HostName: device.HostName,
          Active: device.Active,
          AccessRecord: device.AccessRecord || ''
        }));
      }

      // 更新统计信息为过滤后的设备数量
      if (res.data.hostInfoSummary) {
        const total = res.data.payload.length;
        const online = res.data.payload.filter(d => d.Active === true).length;
        res.data.hostInfoSummary = {
          totalDevices: total,
          onlineDevices: online,
          offlineDevices: total - online
        };
      }
    }

    // 自动转换 get_child_protect 的 appId 为应用名称
    if (name === 'get_child_protect' && res?.data?.payload) {
      // 先解析 payload 字符串
      let payloadData = typeof res.data.payload === 'string'
        ? JSON.parse(res.data.payload)
        : res.data.payload;

        // 转换应用ID为应用名称
        payloadData = transformChildProtectData(payloadData);

        // 将转换后的数据存回 data 字段
        res.data.data = payloadData;
      }
    // 对设置操作的结果进行验证
    let isOperationSuccessful = false;
    let verificationMessage = '';
    
    if (name === 'set_net_time' || name === 'set_net_duration' || name === 'set_net_off' ||
        name === 'add_child_device' || name === 'del_child_device') {
      // 设置操作成功响应的特征
      if (res?.success === true || (res?.data?.status === 'success') || (res?.data?.errcode === 0)) {
        isOperationSuccessful = true;
        verificationMessage = `✓ ${name} 操作执行成功`;
        
        // 检查是否有后续查询操作
        const queryTool = allTools.find(t => t.name === 'get_child_protect');
        if (queryTool) {
          try {
            const queryPayload = {
              devId,
              prodId,
              mode: 'ACK',
              operation: 'GET',
              sid: ROUTER_PATHS.get_child_protect
            };
            
            const queryRes = await hagControl(queryPayload, false);
            let latestConfig = '';
            
            // 转换查询结果中的appId为应用名称
            if (queryRes?.data?.data) {
              queryRes.data.data = transformChildProtectData(queryRes.data.data);
              latestConfig = JSON.stringify(queryRes.data.data, null, 2);
            } else {
              latestConfig = JSON.stringify(queryRes, null, 2);
            }
            
            verificationMessage += `\n📱 最新设备配置：\n${latestConfig}`;
          } catch (queryError) {
            verificationMessage += `\n⚠️  自动查询最新配置失败: ${queryError.message}`;
          }
        } else {
          verificationMessage += '\n💡 建议查询最新配置以确认设置生效';
        }
      } else {
        isOperationSuccessful = false;
        const errorInfo = res?.data?.message || res?.data?.error || res?.message || '未知错误';
        verificationMessage = `❌ ${name} 操作执行失败\n错误信息: ${errorInfo}`;
      }
    } else {
      // 查询操作成功响应的特征
      isOperationSuccessful = true;
      verificationMessage = `✓ ${name} 查询成功`;
    }

    // 对返回数据中的敏感字段进行脱敏处理
    // get_wan_status 的 payload 在 res.data.data.payload，get_guest_wifi 的 payload 在 res.data.payload
    let maskedRes = res;
    const needsMask = (name === 'get_wan_status' || name === 'get_guest_wifi');
    if (needsMask) {
      // 统一定位 payload 所在层级
      let payloadContainer = null;
      if (res?.data?.data?.payload) {
        payloadContainer = res.data.data;
      } else if (res?.data?.payload) {
        payloadContainer = res.data;
      }
      if (payloadContainer && typeof payloadContainer.payload === 'string') {
        try {
          const payloadObj = JSON.parse(payloadContainer.payload);
          let maskedPayload;
          if (name === 'get_wan_status') {
            maskedPayload = maskWanSensitiveFields(payloadObj);
          } else if (name === 'get_guest_wifi') {
            maskedPayload = maskWifiPassword(payloadObj);
          }
          if (maskedPayload && JSON.stringify(maskedPayload) !== payloadContainer.payload) {
            const newContainer = { ...payloadContainer, payload: JSON.stringify(maskedPayload) };
            if (res?.data?.data?.payload) {
              maskedRes = { ...res, data: { ...res.data, data: newContainer } };
            } else {
              maskedRes = { ...res, data: newContainer };
            }
          }
        } catch (_) {
          // payload 解析失败，保持原样
        }
      }
    }

    results.push({ 
      tool: name, 
      success: isOperationSuccessful, 
      data: maskedRes,
      message: verificationMessage,
      timestamp: new Date().toISOString()
    });
  }

  console.log(JSON.stringify(results, null, 2));
  return results;
}

// ==================== 注册命令 ====================
function registerCommands(program) {
  const toolNamesNeedAction = [
    'set_net_time', 
    'set_wifi_timeswitch', 
    'set_online_upg', 
    'set_reboot', 
    'set_Device_ratelimit', 
    'set_net_duration'];
  const toolNamesNeedData = ['add_child_device', 'del_child_device'];
  const toolNamesNeedProdid = ['get_router_device_by_prodid'];
  const toolNamesNeedAppId = ['get_app_info'];
  const toolNamesNeedBlockTime = ['set_block_time'];
  const toolNamesNeedName = ['check_presence'];
  const toolNames = Object.keys(ROUTER_PATHS);

  // config_presence 处理（本地操作，不走 ROUTER_PATHS，需单独注册命令）
  // 仅支持 --router-id + --prod-id 精确指定路由器，不支持 home-id/all-homes/batch-mode
  program
    .command('config_presence')
    .description('配置家庭成员-设备映射（自动探测在线设备）')
    .option('--detect', '自动探测当前在线设备')
    .requiredOption('--router-id <id>', '路由器设备 ID（必填）')
    .option('--prod-id <id>', '产品ID（与 --router-id 配合使用）')
    .option('--skill-id <id>', '技能 ID', DEFAULT_SKILL_ID)
    .option('-v, --verbose', '调试日志')
    .action(async (opts) => {
      ROUTER_DEVICE_ID = String(opts.routerId);
      if (opts.prodId) ROUTER_PROD_ID = String(opts.prodId);
      const args = {};
      if (opts.detect) args.detect = true;
      await callRouterClaw([{ name: 'config_presence', args }], opts.skillId, opts.verbose);
    });

  for (const toolName of toolNames) {
    let command = program
      .command(toolName)
      .description(`路由器操作：${toolName}`)
      .option('--device-id <id>', '儿童保护设备 ID（子设备）', '1')
      .option('--router-id <id>', '路由器设备 ID')
      .option('--prod-id <id>', '产品ID（与 --router-id 配合使用）')
      .option('--data <json>', '控制参数 (JSON 字符串)')
      .option('--type <num>', '应用分类 1 游戏/2 影音/3 社交/4 购物/5 安装/7 学习')
      .option('--skill-id <id>', '技能 ID', DEFAULT_SKILL_ID)
      .option('--home-id <id>', '家庭 ID（跳过交互选择）')
      .option('--all-homes', '遍历所有家庭查询')
      .option('--batch-mode', '批量模式（非交互，自动选择默认值）')
      .option('-v, --verbose', '调试日志')
      .option('--family-map <json>', '家庭成员-设备映射 (JSON)，用于 check_presence', (val) => JSON.parse(val))
      .action(async (opts) => {
        // 设置全局配置
        if (opts.homeId) {
          TARGET_HOME_ID = opts.homeId;
        }
        if (opts.allHomes === true) {
          QUERY_ALL_HOMES = true;
        }
        if (opts.batchMode === true) {
          BATCH_MODE = true;
        }

        let args = {};
        if (opts.data) {
          args.data = JSON.parse(opts.data);
          // Merge data fields into top-level args so both --data and --flag approaches work
          if (args.data.device) args.deviceId = String(args.data.device);
          if (args.data.apps) args.apps = args.data.apps;
          if (args.data.type) args.type = args.data.type;
        }
        if (opts.deviceId) args.deviceId = String(opts.deviceId);
        if (opts.routerId) {
          args.routerId = String(opts.routerId);
          ROUTER_DEVICE_ID = String(opts.routerId);
        }
        if (opts.prodId) {
          args.prodId = String(opts.prodId);
          ROUTER_PROD_ID = String(opts.prodId);
        }
        if (opts.type) args.type = opts.type;
        if (toolNamesNeedAction.includes(toolName) && opts.action) {
          args.action = opts.action;
        }
        if (toolNamesNeedProdid.includes(toolName) && opts.prodid) {
          args.prodid = opts.prodid;
        }
        if (toolNamesNeedAppId.includes(toolName) && opts.appId) {
          args.appId = opts.appId;
        }
        if (toolNamesNeedBlockTime.includes(toolName)) {
          if (opts.forbidStart) args.forbidStart = opts.forbidStart;
          if (opts.forbidEnd) args.forbidEnd = opts.forbidEnd;
          if (opts.weekdays) args.weekdays = opts.weekdays;
        }
        if (toolNamesNeedName.includes(toolName)) {
          if (opts.name) args.name = opts.name;
          if (opts.familyMap) args.family_map = opts.familyMap;
        }
        if (opts.detect) args.detect = true;

        await callRouterClaw([{ name: toolName, args }], opts.skillId, opts.verbose);
      });

    if (toolNamesNeedAction.includes(toolName)) {
      command.option('--action <type>', '操作类型 create/update/delete');
    }
    if (toolNamesNeedProdid.includes(toolName)) {
      command.option('--prodid <id>', '产品ID / 产品型号');
    }
    if (toolNamesNeedAppId.includes(toolName)) {
      command.option('--app-id <id>', '应用ID');
    }
    if (toolNamesNeedBlockTime.includes(toolName)) {
      command.option('--forbid-start <time>', '不允许上网开始时间 (HH:MM)');
      command.option('--forbid-end <time>', '不允许上网结束时间 (HH:MM)');
      command.option('--weekdays <type>', '日期类型: weekday(工作日) / weekend(周末) / everyday(每天)');
    }
    if (toolNamesNeedName.includes(toolName)) {
      command.option('--name <name>', '家人称呼，如：女儿、儿子');
    }
  }
}

// ==================== 启动程序 ====================
const program = new Command();
program
  .name(PROGRAM_NAME)
  .description('路由器儿童上网保护控制工具（hag-connect 版 + 模块化功能）')
  .version(VERSION)
  .option('--tools <json>', '批量执行工具')
  .allowUnknownOption()  // 允许未知选项，让子命令处理
  .enablePositionalOptions();  // 启用位置选项，让子命令选项正确解析

registerCommands(program);
program.parse();