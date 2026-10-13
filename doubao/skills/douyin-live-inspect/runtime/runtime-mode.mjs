import { existsSync } from 'node:fs';
import os from 'node:os';
import { execFileSync } from 'node:child_process';
import { join } from 'node:path';

const CLOUD_FLAGS = [
  'SANDBOX_TYPE', 'DOUBAO_SANDBOX_TYPE', 'FAAS_SANDBOXD_INJECTION_KEY',
  'TCE_SANDBOX_ID', 'SANDBOXD_ALLOW_HOST_NS', '_BYTEFAAS_POD_NAME',
];

function command(command, args, exec = execFileSync) {
  try { return `${exec(command, args, { encoding: 'utf8', timeout: 1000, stdio: ['ignore', 'pipe', 'ignore'] })}`.trim(); }
  catch { return ''; }
}

export function detectRuntimeMode({ env = process.env, platform = process.platform, hostname = os.hostname(), exists = existsSync, exec = execFileSync } = {}) {
  if (env.CUA_USE_ISOLATED_ENV === '0') return { mode: 'local', reason: 'explicit_local' };
  if (env.CUA_USE_ISOLATED_ENV === '1') return { mode: 'cloud', reason: 'explicit_isolated' };
  if (CLOUD_FLAGS.some((name) => `${env[name] || ''}`.trim())) return { mode: 'cloud', reason: 'cloud_marker' };

  const probe = [
    env.CUA_BASE_PACK_DIR, env.CUA_DLC_DIR, env.PYTHONPATH,
    env.LOCALAPPDATA, env.APPDATA,
  ].filter(Boolean).join('\n');
  if (/\/Applications\/DoubaoWork\.app|Library[\\/]Application Support[\\/]DoubaoWork|[\\/]DoubaoWork(?:[\\/]|$)/i.test(probe)) {
    return { mode: 'local', reason: 'doubao_desktop_path' };
  }
  if (/^(?:sandbox|shard|ip-)/i.test(hostname)) return { mode: 'cloud', reason: 'sandbox_hostname' };

  if (platform === 'linux') {
    if (/^(?:docker|kvm|qemu|podman|containerd)$/.test(command('systemd-detect-virt', [], exec))) {
      return { mode: 'cloud', reason: 'virtualized_linux' };
    }
    if (command('df', ['-P', '/'], exec).split(/\r?\n/).at(-1)?.trim().split(/\s+/)[0] === 'overlay') {
      return { mode: 'cloud', reason: 'overlay_root' };
    }
  } else if (platform === 'darwin') {
    if (command('sysctl', ['-n', 'kern.hv_vmm_present'], exec) === '1') return { mode: 'cloud', reason: 'virtualized_macos' };
    if (/^Virtual/i.test(command('sysctl', ['-n', 'hw.model'], exec))) return { mode: 'cloud', reason: 'virtual_macos_model' };
  }

  const home = `${env.HOME || env.USERPROFILE || ''}`;
  if (home && [join(home, 'Documents'), join(home, 'DoubaoWork'), join(home, '.nvm')].some(exists)) {
    return { mode: 'local', reason: 'local_user_directory' };
  }
  if (!['darwin', 'win32'].includes(platform)) return { mode: 'cloud', reason: 'non_desktop_os' };
  return { mode: 'unknown', reason: 'no_positive_signal' };
}
