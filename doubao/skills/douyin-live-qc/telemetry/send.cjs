// Only validated QC facts cross the SDK boundary. The child receives no business argv.
const fs = require('node:fs');
const path = require('node:path');
const { randomUUID } = require('node:crypto');
const {captureEvent} = require('./observer-client.cjs');
const contract = require('./contract.json');
const product = 'douyin-live-qc';
const version = fs.readFileSync(path.join(__dirname, '../SKILL.md'), 'utf8')
  .split(/^---\s*$/m)[1]?.match(/^metadata:\s*\n(?:[ \t]+.*\n)*?[ \t]+version: *"([\d]+\.[\d]+\.[\d]+)"\s*$/m)?.[1];
const id = value => typeof value === 'string' && /^[0-9a-f]{32}$/.test(value);
const count = value => Number.isSafeInteger(value) && value >= 0;
const optional = (validate, value) => value === undefined || validate(value);
const steps = Object.keys(contract.steps);
function valid(command, x) {
  if (!x || !id(x.flow_id) || !count(x.flow_started_at) || !count(x.flow_revision) || !x.flow_revision) return false;
  let keys = ['flow_id', 'flow_started_at', 'flow_revision'];
  if (command === 'qc.workflow.snapshot') {
    keys.push('entry_type', 'current_stage', 'current_result', 'doubao_user_id', ...contract.counts);
    if (x.step !== undefined) {
      keys.push('step', 'outcome', 'reason', 'attempt_id', 'task_id');
      if (!Object.hasOwn(contract.steps, x.step) || !contract.steps[x.step].includes(x.outcome) ||
          !['failure','partial','empty','unknown'].includes(x.outcome) || !contract.reasons.includes(x.reason) ||
          !id(x.attempt_id) || !optional(id,x.task_id)) return false;
    }
    if (!contract.entry_types.includes(x.entry_type) ||
        !['entry', 'complete', ...steps].includes(x.current_stage) ||
        !['started', ...Object.values(contract.steps).flat()].includes(x.current_result) ||
        !optional(v => typeof v === 'string' && /^[0-9]{1,64}$/.test(v), x.doubao_user_id) ||
        !contract.counts.every(k => count(x[k]))) return false;
  } else return false;
  return Object.keys(x).every(k => keys.includes(k));
}
async function send(events) {
  if (!version || Number(process.versions.node.split('.')[0]) < 20 ||
      /^(1|true)$/i.test((process.env.BYTEDLIVE_TELEMETRY_DISABLED || '').trim())) return;
  const sdk = require('./vendor/tooling-telemetry.cjs');
  const reporter = sdk.createToolTelemetry({ toolName: product, toolVersion: version, region: 'cn' }).getReporter();
  await Promise.all(events.map(async ({command, facts}) => {
    if (!valid(command, facts)) return;
    const extra = JSON.stringify({product, ...facts});
    if (Array.from(extra).length > 1024) return;
    const event = {
      command, cli_name: product, cli_version: version, skill_name: product, skill_version: version,
      invocation_id: randomUUID(), result: facts.outcome === 'failure' ? 'failure' : 'success',
      os: process.platform, arch: process.arch, node_major: process.versions.node.split('.')[0], extra
    };
    captureEvent(event);
    await reporter.report(event);
  }));
}
if (require.main === module) {
  try { send(JSON.parse(fs.readFileSync(0, 'utf8'))).catch(() => {}); } catch {}
}
module.exports = {send};
