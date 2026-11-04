import { resolve } from 'node:path';
import { amapRuntimeConfig } from '../runtime/amap-runtime-config.mjs';
import { readJson } from './cli-utils.mjs';

const nonEmptyEntries = value =>
  Object.fromEntries(
    Object.entries(value).filter(([, item]) => item !== '' && item != null),
  );

export async function loadAMapRuntimeConfig(options = {}) {
  const root = options.root;
  const localConfig = resolve(root, 'runtime/amap-config.local.json');
  const configFile =
    options.config || process.env.MAP_CREATE_AMAP_CONFIG || localConfig;
  let fileConfig = {};
  try {
    fileConfig = await readJson(configFile);
  } catch (error) {
    const usingImplicitLocalConfig =
      configFile === localConfig &&
      !options.config &&
      !process.env.MAP_CREATE_AMAP_CONFIG;
    if (!usingImplicitLocalConfig || error?.code !== 'ENOENT') throw error;
  }
  const environmentConfig = nonEmptyEntries({
    key: process.env.MAP_CREATE_AMAP_KEY,
    securityJsCode: process.env.MAP_CREATE_AMAP_SECURITY_CODE,
    serviceHost: process.env.MAP_CREATE_AMAP_SERVICE_HOST,
  });
  const config = {
    ...amapRuntimeConfig,
    ...fileConfig,
    ...environmentConfig,
  };
  if (!config.key || !(config.serviceHost || config.securityJsCode))
    throw new Error(
      '宿主尚未注入高德 JSAPI 配置；请由部署环境配置，不要向最终用户索取',
    );
  return config;
}
