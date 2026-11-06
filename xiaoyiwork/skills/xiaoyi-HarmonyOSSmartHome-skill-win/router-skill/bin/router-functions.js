// ==================== 路由器功能模块 ====================
// 版本：1.0.0
// 功能：将路由器操作的核心功能模块化

// 项目内部模块 - 应用信息
import { g_saAppInfo } from './sa_app_info.js';

// ==================== 模块缓存 ====================
// 缓存路由器设备信息模块，避免重复加载
let routerDeviceInfoCache = null;

/**
 * 获取路由器设备信息缓存（单例模式）
 */
async function getRouterDeviceInfo() {
  if (!routerDeviceInfoCache) {
    routerDeviceInfoCache = (await import('./router_device_info.js')).default;
  }
  return routerDeviceInfoCache;
}

// ==================== 应用管理操作模块 ====================
/**
 * 游戏应用恢复权限操作（两步）
 */
export async function handleAllowGames(devId, prodId, deviceId, verbose = false) {
  // 第一步：调用 Homepage 接口
  const payload1 = {
    devId,
    prodId,
    mode: 'ACK',
    operation: 'POST',
    sid: '.sys/gateway/ntwk/childHomepage',
    data: {
      action: 'gameUpdate',
      data: {
        device: deviceId,
        game: 1,
        video: 0,
        social: 0,
        payEnable: 0,
        appDownload: 0,
        urlEnable: 0,
        denyEnable: 0,
        delayEnable: 0,
        allow: 0,
        increaseTime: 0
      }
    }
  };
  
  // 第二步：调用 childModelApps 接口清空应用列表
  const payload2 = {
    devId,
    prodId,
    mode: 'ACK',
    operation: 'POST',
    sid: '.sys/gateway/ntwk/childModelApps',
    data: {
      action: 'update',
      data: {
        device: deviceId,
        apps: [],
        denyAll: 0,
        type: 1
      }
    }
  };
  
  return { payload1, payload2, step1Name: 'allow_games_step1', step2Name: 'allow_games_step2' };
}

/**
 * 视频应用恢复权限操作（两步）
 */
export async function handleAllowVideos(devId, prodId, deviceId, verbose = false) {
  const payload1 = {
    devId,
    prodId,
    mode: 'ACK',
    operation: 'POST',
    sid: '.sys/gateway/ntwk/childHomepage',
    data: {
      action: 'videoUpdate',
      data: {
        device: deviceId,
        game: 0,
        video: 1,
        social: 0,
        payEnable: 0,
        appDownload: 0,
        urlEnable: 0,
        denyEnable: 0,
        delayEnable: 0,
        allow: 0,
        increaseTime: 0
      }
    }
  };
  
  const payload2 = {
    devId,
    prodId,
    mode: 'ACK',
    operation: 'POST',
    sid: '.sys/gateway/ntwk/childModelApps',
    data: {
      action: 'update',
      data: {
        device: deviceId,
        apps: [],
        denyAll: 0,
        type: 2
      }
    }
  };
  
  return { payload1, payload2, step1Name: 'allow_videos_step1', step2Name: 'allow_videos_step2' };
}

/**
 * 社交通讯应用恢复权限操作（两步）
 */
export async function handleAllowSocial(devId, prodId, deviceId, verbose = false) {
  const payload1 = {
    devId,
    prodId,
    mode: 'ACK',
    operation: 'POST',
    sid: '.sys/gateway/ntwk/childHomepage',
    data: {
      action: 'socialUpdate',
      data: {
        device: deviceId,
        game: 0,
        video: 0,
        social: 1,
        payEnable: 0,
        appDownload: 0,
        urlEnable: 0,
        denyEnable: 0,
        delayEnable: 0,
        allow: 0,
        increaseTime: 0
      }
    }
  };
  
  const payload2 = {
    devId,
    prodId,
    mode: 'ACK',
    operation: 'POST',
    sid: '.sys/gateway/ntwk/childModelApps',
    data: {
      action: 'update',
      data: {
        device: deviceId,
        apps: [],
        denyAll: 0,
        type: 3
      }
    }
  };
  
  return { payload1, payload2, step1Name: 'allow_social_step1', step2Name: 'allow_social_step2' };
}

/**
 * 购物支付应用恢复权限操作（两步）
 */
export async function handleAllowShopping(devId, prodId, deviceId, verbose = false) {
  const payload1 = {
    devId,
    prodId,
    mode: 'ACK',
    operation: 'POST',
    sid: '.sys/gateway/ntwk/childHomepage',
    data: {
      action: 'payUpdate',
      data: {
        device: deviceId,
        game: 0,
        video: 0,
        social: 0,
        payEnable: 1,
        appDownload: 0,
        urlEnable: 0,
        denyEnable: 0,
        delayEnable: 0,
        allow: 0,
        increaseTime: 0
      }
    }
  };
  
  const payload2 = {
    devId,
    prodId,
    mode: 'ACK',
    operation: 'POST',
    sid: '.sys/gateway/ntwk/childModelApps',
    data: {
      action: 'update',
      data: {
        device: deviceId,
        apps: [],
        denyAll: 0,
        type: 4
      }
    }
  };
  
  return { payload1, payload2, step1Name: 'allow_shopping_step1', step2Name: 'allow_shopping_step2' };
}

/**
 * 安装应用恢复权限操作（两步）
 */
export async function handleAllowInstall(devId, prodId, deviceId, verbose = false) {
  const payload1 = {
    devId,
    prodId,
    mode: 'ACK',
    operation: 'POST',
    sid: '.sys/gateway/ntwk/childHomepage',
    data: {
      action: 'installUpdate',
      data: {
        device: deviceId,
        game: 0,
        video: 0,
        social: 0,
        payEnable: 0,
        appDownload: 1,
        urlEnable: 0,
        denyEnable: 0,
        delayEnable: 0,
        allow: 0,
        increaseTime: 0
      }
    }
  };
  
  const payload2 = {
    devId,
    prodId,
    mode: 'ACK',
    operation: 'POST',
    sid: '.sys/gateway/ntwk/childModelApps',
    data: {
      action: 'update',
      data: {
        device: deviceId,
        apps: [],
        denyAll: 0,
        type: 5
      }
    }
  };
  
  return { payload1, payload2, step1Name: 'allow_install_step1', step2Name: 'allow_install_step2' };
}

// ==================== 本地功能模块 ====================
/**
 * 根据产品ID获取路由器设备信息
 */
export async function handleGetRouterDeviceByProdid(prodid = 'K1AP') {
  try {
    // 使用缓存的模块数据（直接是数组）
    const routerDeviceInfoArray = await getRouterDeviceInfo();

    // 查找匹配的 prodid
    const match = routerDeviceInfoArray.find(info =>
      info[1].toLowerCase() === String(prodid).toLowerCase()
    );

    let deviceInfo;
    if (match) {
      deviceInfo = {
        isRouter: true,
        prodId: match[1],
        device: match[0],
        chineseName: match[2],
        englishName: match[3],
        fromLocal: true,
        totalCount: routerDeviceInfoArray.length,
        note: '使用本地路由设备信息映射'
      };
    } else {
      deviceInfo = {
        isRouter: false,
        prodId: String(prodid),
        chineseName: '未识别的设备',
        englishName: 'Unrecognized Device',
        fromLocal: false,
        suggestion: '请检查prodid是否正确，查看支持的路由器设备列表'
      };
    }
    
    return {
      success: deviceInfo.isRouter,
      data: deviceInfo,
      message: deviceInfo.isRouter ? 
        `路由器识别成功: ${deviceInfo.chineseName} (${deviceInfo.englishName})` : 
        '该prodid在路由器设备映射表中未找到'
    };
  } catch (error) {
    return {
      success: false,
      data: null,
      message: `加载路由器设备信息映射表失败: ${error.message}`
    };
  }
}

/**
 * 根据应用ID查询具体应用信息
 */
export async function handleGetAppInfo(appId) {
  if (!appId) {
    return {
      success: false,
      data: null,
      message: '请提供要查询的应用ID'
    };
  }
  
  try {
    const appInfo = g_saAppInfo.find(app => 
      String(app[1]) === String(appId)
    );
    
    if (appInfo) {
      return {
        success: true,
        data: {
          appName: appInfo[0],
          appId: appInfo[1],
          categ: appInfo[2],
          message: `应用查询成功: ${appInfo[0]} (ID: ${appInfo[1]}, 分类: ${appInfo[2]})`
        }
      };
    } else {
      return {
        success: false,
        data: null,
        message: `未找到ID为 ${appId} 的应用`
      };
    }
  } catch (error) {
    return {
      success: false,
      data: null,
      message: `应用信息查询失败: ${error.message}`
    };
  }
}

/**
 * 查询所有可用的应用列表
 */
export async function handleGetAllApps() {
  try {
    const categorizedApps = {};
    
    // 按分类整理应用
    g_saAppInfo.forEach(app => {
      const categ = app[2];
      const categoryName = getCategoryName(categ);
      
      if (!categorizedApps[categoryName]) {
        categorizedApps[categoryName] = [];
      }
      
      categorizedApps[categoryName].push({
        name: app[0],
        id: app[1],
        categ: app[2]
      });
    });
    
    return {
      success: true,
      data: {
        totalApps: g_saAppInfo.length,
        categories: categorizedApps,
        message: `共找到 ${g_saAppInfo.length} 个应用，按分类显示`
      }
    };
  } catch (error) {
    return {
      success: false,
      data: null,
      message: `应用列表查询失败: ${error.message}`
    };
  }
}

// ==================== 工具函数模块 ====================
/**
 * 根据应用分类ID获取分类名称
 */
export function getCategoryName(categ) {
  const categoryMap = {
    1: '默认节点',
    2: '应用商店',
    4: '游戏',
    8: '应用服务',
    16: '视频类',
    32: '直播类',
    128: '社交类',
    256: '办公类',
    512: '购物类',
    1024: '支付类',
    2048: 'WiFi相关',
    4096: '教育类',
    8192: '学习类'
  };
  
  return categoryMap[categ] || `未知分类(${categ})`;
}

/**
 * 从映射表中获取路由器信息
 */
export async function getRouterInfo(deviceId, prodId) {
  try {
    // 使用缓存的模块数据
    const routerDeviceInfo = await getRouterDeviceInfo();
    const routerInfo = routerDeviceInfo.find(info =>
      info[0] === deviceId || info[1] === prodId
    );
    
    if (routerInfo) {
      return {
        name: routerInfo[2],      // 中文名称
        model: routerInfo[3],     // 英文名称
        deviceId: routerInfo[0],  // 设备标识
        prodId: routerInfo[1]     // 产品ID
      };
    }
    return null;
  } catch (error) {
    // 如果加载映射表失败，返回null
    return null;
  }
}

/**
 * 转换儿童保护数据，将appId转换为应用名称，将timeSummary.allowed转换为易读字符串
 */
export function transformChildProtectData(data) {
  // 统一处理数据可能是数组或对象的情况
  const dataArray = Array.isArray(data) ? data : [data];

  dataArray.forEach(device => {
    // 转换 timeSummary.allowed 字段（秒转换为易读字符串）
    if (device.timeSummary?.allowed !== undefined) {
      device.timeSummary.allowedText = convertSecondsToReadable(device.timeSummary.allowed);
    }

    // 处理today中的应用记录
    if (device.today?.appSorts) {
      device.today.appSorts = device.today.appSorts.map(app => ({
        ...app,
        appName: getAppNameById(app.appId)  // 自动添加应用名称
      }));
    }
    // 处理week中的应用记录
    if (device.week?.appSorts) {
      device.week.appSorts = device.week.appSorts.map(app => ({
        ...app,
        appName: getAppNameById(app.appId)
      }));
    }
    // 处理day中的应用记录
    if (device.day?.appSorts) {
      device.day.appSorts = device.day.appSorts.map(app => ({
        ...app,
        appName: getAppNameById(app.appId)
      }));
    }
  });

  return Array.isArray(data) ? dataArray : dataArray[0];
}

/**
 * 将秒数转换为易读字符串
 * @param {number} seconds - 秒数
 * @returns {string} 易读字符串，如 "6小时/天" 或 "无限制"
 */
function convertSecondsToReadable(seconds) {
  if (seconds === 90000 || seconds >= 86400) {
    return '无限制';
  }
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0 && minutes > 0) {
    return `${hours}小时${minutes}分钟/天`;
  } else if (hours > 0) {
    return `${hours}小时/天`;
  } else if (minutes > 0) {
    return `${minutes}分钟/天`;
  }
  return '0分钟/天';
}

/**
 * 根据应用ID获取应用名称
 */
function getAppNameById(appId) {
  if (!appId) return '未知应用';
  
  try {
    const appInfo = g_saAppInfo.find(app => {
      return String(app[1]) === String(appId);
    });
    
    if (appInfo) {
      return appInfo[0]; // 返回应用名称
    } else {
      return String(appId); // 直接返回应用ID
    }
  } catch (error) {
    return String(appId);
  }
}

// ==================== 不允许上网时段反向转换模块 ====================

/**
 * 时间字符串转分钟数
 * @param {string} time - 时间字符串 (HH:MM)
 * @returns {number} 分钟数
 * @throws {Error} 时间格式无效或超出范围时抛出错误
 */
function parseTimeToMinutes(time) {
  // 校验时间字符串格式
  if (!time || typeof time !== 'string') {
    throw new Error('时间字符串不能为空');
  }

  const timeRegex = /^(\d{1,2}):(\d{2})$/;
  const match = time.match(timeRegex);

  if (!match) {
    throw new Error(`无效的时间格式 "${time}"，应为 HH:MM`);
  }

  const hours = parseInt(match[1], 10);
  const minutes = parseInt(match[2], 10);

  // 校验数值范围
  if (hours < 0 || hours > 24) {
    throw new Error(`小时数 ${hours} 超出有效范围 (0-24)`);
  }

  if (minutes < 0 || minutes > 59) {
    throw new Error(`分钟数 ${minutes} 超出有效范围 (0-59)`);
  }

  // 24:00 等同于 00:00（第二天），这里将其规范化为 24*60=1440
  // 但在时段计算中，24:00 应该视为 24:00（即当天的最后一刻）
  if (hours === 24 && minutes > 0) {
    throw new Error(`24点之后需要使用 00:00`);
  }

  return hours * 60 + minutes;
}

/**
 * 检查禁止时段是否已经完全在"不允许"范围内（与已有允许时段无重叠）
 * @param {string} forbidStart - 禁止开始时间
 * @param {string} forbidEnd - 禁止结束时间
 * @param {Array} existingRules - 已有上网时段配置
 * @param {string} weekType - weekday/weekend/everyday
 * @returns {boolean} true表示无需额外配置
 */
export function isForbidPeriodAlreadyDenied(forbidStart, forbidEnd, existingRules, weekType) {
  if (!existingRules || existingRules.length === 0) {
    return false; // 无配置，需要添加
  }

  const forbidStartMin = parseTimeToMinutes(forbidStart);
  const forbidEndMin = parseTimeToMinutes(forbidEnd);

  for (const rule of existingRules) {
    // 只检查启用状态且日期匹配的规则
    if (rule.enable !== 1) continue;

    // 检查日期是否匹配
    let dateMatch = false;
    if (weekType === 'weekday') {
      dateMatch = rule.monday || rule.tuesday || rule.wednesday || rule.thursday || rule.friday;
    } else if (weekType === 'weekend') {
      dateMatch = rule.saturday || rule.sunday;
    } else {
      dateMatch = true; // everyday 匹配所有
    }
    if (!dateMatch) continue;

    // 检查时间是否有重叠（已有允许时段）
    const ruleStart = parseTimeToMinutes(rule.timeFrom);
    const ruleEnd = parseTimeToMinutes(rule.timeTo);

    // 如果禁止时段与已有允许时段有重叠，说明需要处理
    if (forbidStartMin < ruleEnd && forbidEndMin > ruleStart) {
      return false; // 有重叠，需要重新配置
    }
  }
  return true; // 无重叠，禁止时段本来就不在允许范围内
}

/**
 * 检查是否需要删除冲突的允许时段配置
 * @param {string} forbidStart - 禁止开始时间
 * @param {string} forbidEnd - 禁止结束时间
 * @param {Array} existingRules - 已有上网时段配置
 * @param {string} weekType - weekday/weekend/everyday
 * @returns {boolean} true表示需要删除冲突规则
 */
export function needDeleteConflictingRules(forbidStart, forbidEnd, existingRules, weekType) {
  if (!existingRules || existingRules.length === 0) return false;

  const forbidStartMin = parseTimeToMinutes(forbidStart);
  const forbidEndMin = parseTimeToMinutes(forbidEnd);

  for (const rule of existingRules) {
    if (rule.enable !== 1) continue;

    // 检查日期是否匹配
    let dateMatch = false;
    if (weekType === 'weekday') {
      dateMatch = rule.monday || rule.tuesday || rule.wednesday || rule.thursday || rule.friday;
    } else if (weekType === 'weekend') {
      dateMatch = rule.saturday || rule.sunday;
    } else {
      dateMatch = true;
    }
    if (!dateMatch) continue;

    // 检查时间是否有重叠
    const ruleStart = parseTimeToMinutes(rule.timeFrom);
    const ruleEnd = parseTimeToMinutes(rule.timeTo);

    // 如果禁止时段完全覆盖了已有允许时段，需要删除该规则
    if (forbidStartMin <= ruleStart && forbidEndMin >= ruleEnd) {
      return true;
    }
  }
  return false;
}

/**
 * 生成不允许上网时段的反向设置命令
 * @param {string} deviceId - 设备ID
 * @param {string} forbidStart - 禁止开始时间 (HH:MM)
 * @param {string} forbidEnd - 禁止结束时间 (HH:MM)
 * @param {string} weekdays - weekday(工作日)/weekend(周末)/everyday(每天)
 * @returns {Array} 命令列表
 */
export function generateBlockToAllowCommands(deviceId, forbidStart, forbidEnd, weekdays) {
  const tools = [];

  // 使用已有的 parseTimeToMinutes 函数进行时间解析（含有效性校验）
  const startMinutes = parseTimeToMinutes(forbidStart);
  const endMinutes = parseTimeToMinutes(forbidEnd);

  // 构建请求数据
  const buildAllowData = (timeFrom, timeTo, weekConfig) => ({
    id: "",
    enable: 1,
    timeFrom: timeFrom,
    timeTo: timeTo,
    today: 0,
    device: deviceId,
    ...weekConfig
  });

  const weekdayConfig = { monday: 1, tuesday: 1, wednesday: 1, thursday: 1, friday: 1, saturday: 0, sunday: 0 };
  const weekendConfig = { monday: 0, tuesday: 0, wednesday: 0, thursday: 0, friday: 0, saturday: 1, sunday: 1 };
  const everydayConfig = { monday: 1, tuesday: 1, wednesday: 1, thursday: 1, friday: 1, saturday: 1, sunday: 1 };

  if (weekdays === 'weekday') {
    // 工作日反向设置，周末24小时允许
    if (startMinutes > 0) {
      tools.push({ name: 'set_net_time', args: { action: 'newCreate', data: buildAllowData('00:00', forbidStart, weekdayConfig), deviceId } });
    }
    if (endMinutes < 24 * 60) {
      tools.push({ name: 'set_net_time', args: { action: 'newCreate', data: buildAllowData(forbidEnd, '24:00', weekdayConfig), deviceId } });
    }
    // 周末24小时允许
    tools.push({ name: 'set_net_time', args: { action: 'newCreate', data: buildAllowData('00:00', '24:00', weekendConfig), deviceId } });

  } else if (weekdays === 'weekend') {
    // 工作日24小时允许，周末反向设置
    tools.push({ name: 'set_net_time', args: { action: 'newCreate', data: buildAllowData('00:00', '24:00', weekdayConfig), deviceId } });
    if (startMinutes > 0) {
      tools.push({ name: 'set_net_time', args: { action: 'newCreate', data: buildAllowData('00:00', forbidStart, weekendConfig), deviceId } });
    }
    if (endMinutes < 24 * 60) {
      tools.push({ name: 'set_net_time', args: { action: 'newCreate', data: buildAllowData(forbidEnd, '24:00', weekendConfig), deviceId } });
    }

  } else {
    // 每天反向设置
    if (startMinutes > 0) {
      tools.push({ name: 'set_net_time', args: { action: 'newCreate', data: buildAllowData('00:00', forbidStart, everydayConfig), deviceId } });
    }
    if (endMinutes < 24 * 60) {
      tools.push({ name: 'set_net_time', args: { action: 'newCreate', data: buildAllowData(forbidEnd, '24:00', everydayConfig), deviceId } });
    }
  }

  return tools;
}