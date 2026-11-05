import { dirname, resolve } from 'node:path';
import { readJson, writeJson } from './cli-utils.mjs';
import {
  failOnErrors,
  validateContract,
  verifyContractArtifacts,
  withReadingRepresentatives,
} from './engine.mjs';
import { runMapTask } from './map-task.mjs';
import { createTaskPlan } from './map-task-spec.mjs';

const object = value =>
  value !== null && typeof value === 'object' && !Array.isArray(value);
const requireInput = (condition, message) => {
  if (!condition)
    throw Object.assign(new Error(message), { code: 'MAP_REQUEST_INVALID' });
};

export function applyPresentation(base, overrides = {}) {
  requireInput(
    object(overrides),
    'presentation 必须为展示偏好对象或 Plan 文件路径',
  );
  for (const key of ['contractRevision', 'planVersion', 'mapSpecId'])
    requireInput(
      overrides[key] === undefined || overrides[key] === base[key],
      `presentation.${key} 不能改写输入身份`,
    );
  for (const key of ['organization', 'views'])
    requireInput(
      overrides[key] === undefined || object(overrides[key]),
      `presentation.${key} 必须为对象`,
    );
  for (const key of ['dimension', 'evidenceRefs'])
    requireInput(
      overrides.organization?.[key] === undefined ||
        JSON.stringify(overrides.organization[key]) ===
          JSON.stringify(base.organization[key]),
      `presentation.organization.${key} 不能覆盖已声明的任务组织`,
    );
  for (const key of ['overview', 'viewPurposes'])
    requireInput(
      overrides.organization?.[key] === undefined ||
        object(overrides.organization[key]),
      `presentation.organization.${key} 必须为对象`,
    );
  // 展示偏好只覆盖已填写字段，不丢失基础 Plan 中已有的阅读依据。
  const viewPurposes = structuredClone(base.organization.viewPurposes);
  for (const [id, purpose] of Object.entries(
    overrides.organization?.viewPurposes || {},
  )) {
    requireInput(
      object(purpose),
      `presentation.organization.viewPurposes.${id} 必须为对象`,
    );
    viewPurposes[id] = { ...viewPurposes[id], ...purpose };
  }
  const result = {
    ...structuredClone(base),
    ...structuredClone(overrides),
    organization: {
      ...base.organization,
      ...overrides.organization,
      viewPurposes,
    },
    views: Object.fromEntries(
      [
        ...new Set([
          ...Object.keys(base.views),
          ...Object.keys(overrides.views || {}),
        ]),
      ].map(id => {
        const view = overrides.views?.[id];
        requireInput(
          view === undefined || object(view),
          `presentation.views.${id} 必须为对象`,
        );
        return [id, { ...base.views[id], ...view }];
      }),
    ),
  };
  const overview = overrides.organization?.overview;
  if (
    overview &&
    (!overview.mode || overview.mode === base.organization.overview?.mode)
  )
    result.organization.overview = {
      ...base.organization.overview,
      ...overview,
    };
  if (
    base.organization.overview?.mode === 'collection' &&
    overrides.organization?.overview?.mode === 'content'
  ) {
    const viewId =
      overrides.organization.overview.viewId ||
      base.organization.overview.viewId;
    if (viewId === base.organization.overview.viewId) {
      result.organization.overview = {
        ...base.organization.overview,
        ...overrides.organization.overview,
        reason:
          overrides.organization.overview.reason ||
          '显式选择内容总览，保留空间内容与分组导航',
      };
      delete result.organization.overview.spatialReason;
      if (overrides.views?.[viewId]?.componentNodes === undefined)
        result.views[viewId].componentNodes = base.views[
          viewId
        ].componentNodes.filter(node => node.componentId !== 'collection-card');
      if (overrides.views?.[viewId]?.collectionEntries === undefined)
        result.views[viewId].collectionEntries = [];
    }
  }
  return structuredClone(result);
}

export async function resolveMapRequest(
  requestFile,
  outputDir,
  { runTask = runMapTask, onPlaces, onTelemetry } = {},
) {
  const request = await readJson(requestFile);
  requireInput(object(request), '任务输入必须为对象');
  requireInput(
    Boolean(request.spec) !== Boolean(request.tool),
    'spec 文件引用与 tool 工具任务必须且只能选择一种',
  );
  const fromFile = typeof request.spec === 'string';
  requireInput(
    request.spec === undefined || (fromFile && request.spec.trim()),
    'spec 必须为非空文件路径',
  );
  requireInput(
    request.presentation === undefined ||
      object(request.presentation) ||
      (typeof request.presentation === 'string' && request.presentation.trim()),
    'presentation 必须为对象或非空 Plan 路径',
  );
  const allowed = new Set(
    fromFile
      ? ['spec', 'organization', 'reason', 'evidenceRefs', 'presentation']
      : [
          'id',
          'title',
          'summary',
          'tool',
          'parameters',
          'organization',
          'reason',
          'views',
          'selection',
          'round_trip',
          'overviewPreference',
          'presentation',
        ],
  );
  requireInput(
    Object.keys(request).every(key => allowed.has(key)),
    '任务包含未知字段，请把展示偏好放入 presentation',
  );
  const relative = file => resolve(dirname(resolve(requestFile)), file);
  const output = {
    spec: resolve(outputDir, 'canonical-map-spec.json'),
    plan: resolve(outputDir, 'presentation-plan.json'),
  };
  const sources = [
    resolve(requestFile),
    ...(fromFile ? [relative(request.spec)] : []),
    ...(typeof request.presentation === 'string'
      ? [relative(request.presentation)]
      : []),
  ];
  requireInput(
    Object.values(output).every(file => !sources.includes(file)),
    '输出目录不能覆盖原始任务、Spec 或 Plan',
  );
  verifyContractArtifacts();
  let spec;
  let base;
  if (fromFile) {
    spec = await readJson(relative(request.spec));
    failOnErrors(validateContract('mapSpec', spec));
    if (typeof request.presentation !== 'string') {
      requireInput(
        typeof request.organization === 'string' &&
          typeof request.reason === 'string' &&
          request.reason.trim(),
        '事实文件需要 organization 与 reason，或引用完整 Plan 文件',
      );
      const evidenceRefs =
        request.evidenceRefs ??
        (spec.task.evidence.length <= 1
          ? spec.task.evidence.map(item => item.id)
          : undefined);
      requireInput(
        Array.isArray(evidenceRefs),
        '多个意图依据时须显式选择 evidenceRefs',
      );
      base = createTaskPlan({ ...request, evidenceRefs }, spec);
    } else {
      requireInput(
        !['organization', 'reason', 'evidenceRefs'].some(key =>
          Object.hasOwn(request, key),
        ),
        '引用完整 Plan 时不再重复声明组织依据',
      );
    }
  } else {
    const { presentation, ...task } = request;
    const result = await runTask(task, resolve(outputDir, 'provider'), { onPlaces, onTelemetry });
    spec = await readJson(result.spec);
    base = await readJson(result.plan);
  }
  spec = withReadingRepresentatives(spec);
  const plan =
    typeof request.presentation === 'string'
      ? await readJson(relative(request.presentation))
      : applyPresentation(base, request.presentation);
  requireInput(
    plan?.mapSpecId === spec.id,
    'Presentation Plan 与事实文件身份不一致',
  );
  failOnErrors([
    ...validateContract('mapSpec', spec),
    ...validateContract('presentationPlan', plan),
  ]);
  await writeJson(output.spec, spec);
  await writeJson(output.plan, plan);
  return output;
}
