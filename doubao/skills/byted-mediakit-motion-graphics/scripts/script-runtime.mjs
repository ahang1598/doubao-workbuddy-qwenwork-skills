import fs from 'node:fs';
import {createToolTelemetry} from './runtime-core.cjs';

let telemetry;
function controller() {
  if(telemetry)return telemetry;
  const {version}=JSON.parse(fs.readFileSync(new URL('../package.json',import.meta.url),'utf8'));
  const previous=process.env.VE_SKILL_ID;
  try {
    process.env.VE_SKILL_ID=`byted-mediakit-motion-graphics/${version}`;
    telemetry=createToolTelemetry({
      toolName:'byted-mediakit-motion-graphics',toolVersion:version,
      deviceIdDirectory:'velo-cli',
      sensitiveParamNames:['browser','effect']
    });
  } finally {
    if(previous===undefined)delete process.env.VE_SKILL_ID;
    else process.env.VE_SKILL_ID=previous;
  }
  return telemetry;
}

export function setAccountId(accountId) {controller().setAccountId(accountId);}

export async function runScript(handler) {
  let failed=false,originalError;
  try {
    return await controller().runScript(async()=>{
      try {return await handler();}
      catch(error) {
        failed=true;originalError=error;
        // Send only a fixed category; retain the original error for local diagnostics.
        const category=['AbortError','TypeError','RangeError','SyntaxError'].includes(error?.name)?error.name:'Error';
        const safeError=new Error(category);safeError.name=category;
        throw safeError;
      }
    });
  } catch(error) {throw failed?originalError:error;}
}
