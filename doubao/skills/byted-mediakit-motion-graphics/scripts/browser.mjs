import fs from 'node:fs';
import path from 'node:path';

export function browserPath(value) {
  if(typeof value!=='string'||!value.trim())throw new Error('Provide --browser <browser executable path>');
  const file=path.resolve(value);
  if(!fs.existsSync(file)||!fs.statSync(file).isFile())throw new Error(`Browser executable not found: ${file}`);
  fs.accessSync(file,fs.constants.X_OK);
  return file;
}

// HyperFrames receives the explicit CLI path in its child process only.
export function browserEnv(browser,env=process.env) {
  const result={...env,HYPERFRAMES_BROWSER_PATH:browserPath(browser)};
  delete result.PRODUCER_HEADLESS_SHELL_PATH;
  return result;
}
