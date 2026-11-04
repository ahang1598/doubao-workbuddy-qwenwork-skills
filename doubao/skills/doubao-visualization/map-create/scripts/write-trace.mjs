import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { args, readJson, safeError } from '../lib/cli-utils.mjs';
import { writeTrace } from '../trace/writer.mjs';

const options = args();
try {
  if (!options.dir || !options.spec || !options.plan || !options.graph)
    throw new Error(
      '用法：node write-trace.mjs --dir trace --spec spec.json --plan plan.json --graph graph.json [--compiler-report report.json] [--html map.html] [--check-report check.json]',
    );
  const artifacts = {
    'canonical-map-spec.json': await readJson(options.spec),
    'presentation-plan.json': await readJson(options.plan),
    'render-graph.json': await readJson(options.graph),
  };
  if (options['compiler-report'])
    artifacts['compiler-report.json'] = await readJson(
      options['compiler-report'],
    );
  if (options.html) {
    const html = await readFile(options.html, 'utf8');
    artifacts['map-html.json'] = {
      sha256: createHash('sha256').update(html).digest('hex'),
      bytes: Buffer.byteLength(html),
    };
  }
  if (options['check-report'])
    artifacts['check-report.json'] = await readJson(options['check-report']);
  if (options.request)
    artifacts['request-summary.json'] = await readJson(options.request);
  if (options.evidence)
    artifacts['evidence.json'] = await readJson(options.evidence);
  const manifest = await writeTrace(options.dir, artifacts, {
    traceId: options['trace-id'],
    parentTraceId: options['parent-trace-id'],
  });
  process.stdout.write(
    `${JSON.stringify({ status: 'written', manifest }, null, 2)}\n`,
  );
} catch (error) {
  process.stderr.write(
    `${JSON.stringify({ status: 'failed', error: safeError(error) })}\n`,
  );
  process.exitCode = 1;
}
