// ==================== MateTV设备判断工具 ====================
// 功能：根据prodId列表判断设备是否为MateTV设备

const MATETV_PROD_IDS = ['V0FM', 'V0FN', 'V0FO', 'V0FP', 'V0FQ', 'V0FR', 'V0FS', 'V0FT', 'V0H2', 'V0H3', 'V0H4', 'V0H5', 'V0H6', 'V0H7', 'V0H8', 'V0H9', 'V0HH', 'V0HI', 'V0HJ'];

export function isMateTV(prodId) {
  if (!prodId || typeof prodId !== 'string') {
    return false;
  }
  return MATETV_PROD_IDS.includes(prodId.toUpperCase());
}
  
export function isSmartScreen(deviceType) {
  if (!deviceType || typeof deviceType !== 'string') {
    return false;
  }
  return deviceType === '09C';
}

export function filterMateTVDevices(originData) {
  if (!originData || !Array.isArray(originData)) {
    return [];
  }
  const deviceData = originData.find(item => item.tool === 'get_devices_info');
  if (!deviceData || !deviceData.data || !Array.isArray(deviceData.data.devices)) {
    return [];
  }
  return deviceData.data.devices
    .filter(device => isMateTV(device.prodId))
    .map(({ deviceId, deviceName, roomName, prodId }) => ({
      deviceId,
      deviceName,
      roomName,
      prodId
    }));
}

export function getDeviceServiceInfo(originData, devId, sid) {
  if (!originData || !Array.isArray(originData)) {
    return null;
  }
  const snapshotData = originData.find(item => item.tool === 'get_device_service_snapshot');
  if (!snapshotData || !snapshotData.data || !Array.isArray(snapshotData.data.snapshots)) {
    return null;
  }
  const deviceSnapshot = snapshotData.data.snapshots.find(d => d.deviceId === devId);
  if (!deviceSnapshot || !Array.isArray(deviceSnapshot.services)) {
    return null;
  }
  const service = deviceSnapshot.services.find(s => s.serviceId === sid);
  return service ? service.data : null;
}

export { MATETV_PROD_IDS };
