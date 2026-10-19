#!/usr/bin/env node
// Called only after the host actually delivers a verified report (or failure explanation).
import flow from '../runtime/workflow-telemetry.cjs';
try {
 let raw='';for await(const chunk of process.stdin){raw+=chunk;if(Buffer.byteLength(raw)>4096)throw Error('input too large');}
 const input=JSON.parse(raw);
 await flow.ack(input,input.report_kind,input.outcome);
 process.stdout.write(JSON.stringify({ok:true,command:'workflow-delivery'})+'\n');
}catch{process.stdout.write(JSON.stringify({ok:false,error:{code:'DELIVERY_NOT_CONFIRMED',message:'原流程、任务状态或报告就绪证据不匹配；保留原任务续办。'}})+'\n');process.exitCode=2;}
