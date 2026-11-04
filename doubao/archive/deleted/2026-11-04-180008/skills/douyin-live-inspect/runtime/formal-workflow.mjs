// Observe only already validated API results; no additional request or raw payload persistence.
import flow from './workflow-telemetry.cjs';
export async function observeOperation(operation, input, response, options={}) {
 try {
  if(!/^(quality|content)\//.test(operation))return;
  const result=response?.data?.response?.data?.Result;
  const create=/\+.*task-create$/.test(operation),get=/\+.*task-get$/.test(operation),report=/\+.*report-get$/.test(operation);
  if(!create&&!get&&!report)return;
  if(!response?.ok){
   const code=response?.error?.code;
   await flow.problem(create?'startup':report?'quality':'inspection',code||'OPERATION_FAILED',create&&response?.error?.write_occurred===false&&!['AUTH_REQUIRED','SETUP_PENDING','REQUEST_TIMEOUT','NETWORK_ERROR','REPORT_NOT_READY'].includes(code),options);return;
  }
  const identity={environment:'online',profile:response.meta?.profile||input.profile,account_id:response.meta?.account_id||input.account_id,
   project_name:input.project_name,task_id:create?result?.TaskId??result?.TaskID:input.task_id};
  if(create){
   if(!identity.task_id)return flow.problem('startup','CREATE_UNCERTAIN',false,options);
   await flow.formal(identity,{created:true},options);
  }else if(get){
   const status=Number(result?.Status);
   if([3,4].includes(status))await flow.formal(identity,{inspection:'completed'},options);
   else if(status===5)await flow.formal(identity,{inspection:'failed',failure_stage:'inspection',failure_reason:'TASK_FAILED'},options);
   else if([1,2].includes(status))await flow.formal(identity,{inspection:'running'},options);
  }else if(report){
   if(result && Object.hasOwn(result,'TaskResult') && result.TaskResult!==null && result.TaskResult!=='')await flow.formal(identity,{quality:'ready'},options);
   else await flow.problem('quality','REPORT_NOT_READY',false,options);
  }
 }catch{/* telemetry cannot alter API results */}
}
