import net from 'node:net';

export function parsePort(value, name) {
  const port = Number(value);
  if (!Number.isInteger(port) || port < 1024 || port > 65535) {
    throw new Error(`${name} must be an integer TCP port between 1024 and 65535`);
  }
  return port;
}

export async function isPortAvailable(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.unref();
    server.once('error', () => resolve(false));
    server.listen({ port, exclusive: true }, () => {
      server.close(() => resolve(true));
    });
  });
}

export async function findAvailablePort(preferred, excluded = new Set()) {
  for (let candidate = preferred; candidate <= 65535; candidate += 1) {
    if (!excluded.has(candidate) && await isPortAvailable(candidate)) return candidate;
  }
  throw new Error(`No available TCP port found starting at ${preferred}`);
}

async function selectPort(name, configured, fallback, excluded) {
  const explicit = configured !== undefined && configured !== '';
  const preferred = parsePort(explicit ? configured : fallback, name);
  if (explicit) {
    if (excluded.has(preferred) || !await isPortAvailable(preferred)) {
      throw new Error(`${name}=${preferred} is already in use; choose another port or unset it for automatic selection`);
    }
    return preferred;
  }
  try {
    return await findAvailablePort(preferred, excluded);
  } catch {
    throw new Error(`No available TCP port found for ${name} starting at ${preferred}`);
  }
}

export async function selectDevelopmentPorts(env = process.env, includeSmoke = false) {
  const selected = new Set();
  const dev = await selectPort('PET_DEV_PORT', env.PET_DEV_PORT, 3000, selected);
  selected.add(dev);
  const logger = await selectPort('PET_LOGGER_PORT', env.PET_LOGGER_PORT, 9000, selected);
  selected.add(logger);
  const smoke = includeSmoke
    ? await selectPort('PET_SMOKE_PORT', env.PET_SMOKE_PORT, 9223, selected)
    : undefined;
  return { dev, logger, ...(smoke ? { smoke } : {}) };
}
