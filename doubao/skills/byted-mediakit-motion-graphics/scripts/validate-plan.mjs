import {cli,loadConfig,assert} from './common.mjs';
cli(args=>{const {config:c}=loadConfig(args[0]);assert(c.planInfo,'Complete plan.json is required');console.log(JSON.stringify({ok:true,planHash:c.planInfo.hash,density:c.planInfo.stats}));});
