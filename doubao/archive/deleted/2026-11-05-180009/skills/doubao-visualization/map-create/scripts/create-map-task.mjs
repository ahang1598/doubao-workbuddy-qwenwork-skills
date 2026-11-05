import { args, readJson, safeError } from '../lib/cli-utils.mjs';
import { runMapTask } from '../lib/map-task.mjs';

try {
  const options = args();
  if (!options.request || !options.out)
    throw new Error(
      '用法：create-map-task.mjs --request map-task.json --out 工作目录',
    );
  console.log(
    JSON.stringify(
      await runMapTask(await readJson(options.request), options.out),
    ),
  );
} catch (error) {
  console.error(JSON.stringify({ status: 'failed', error: safeError(error) }));
  process.exitCode = 1;
}
