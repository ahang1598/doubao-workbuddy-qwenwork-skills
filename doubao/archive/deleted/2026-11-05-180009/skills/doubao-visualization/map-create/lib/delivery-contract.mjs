import {
  assertDeliveryPolicy,
  assertStartupCoverage,
} from '../acceptance/startup-check.mjs';
import { checkerIdentity } from '../acceptance/acceptance-identity.mjs';
import { assertCompleteCoverage } from '../acceptance/check-policy.mjs';
import { digest } from './cdn-assets.mjs';
import { protocolHash } from './engine.mjs';

// Only top-level fenced blocks count; a renderer example inside another code
// fence is not a delivered map. Keep the map bytes unchanged when hashing.
function terminalRenderer(reply) {
  if (typeof reply !== 'string') return undefined;
  let fence;
  const blocks = [];
  for (const match of reply.matchAll(/^([^\n]*)(?:\n|$)/gm)) {
    const line = match[1];
    if (fence) {
      const closing = line.match(/^ {0,3}(`{3,}|~{3,})[ \t]*$/);
      if (closing && closing[1][0] === fence.marker[0] &&
          closing[1].length >= fence.marker.length) {
        if (fence.renderer)
          blocks.push({ start: fence.start, end: match.index + line.length });
        fence = undefined;
      }
    } else {
      const opening = line.match(/^ {0,3}(`{3,}|~{3,})(.*)$/);
      if (opening)
        fence = {
          marker: opening[1],
          start: match.index,
          renderer: line === '\x60\x60\x60html type="renderer"',
        };
    }
  }
  if (blocks.length !== 1 || fence) return undefined;
  const block = blocks[0];
  if (reply.slice(block.end).trim()) return undefined;
  // The final newline belongs to the envelope; chat hosts may omit it.
  return reply.slice(block.start, block.end) + '\n';
}

export function assertDeliveryReply(reply, workflow) {
  const renderer = terminalRenderer(reply);
  if (
    workflow?.status !== 'passed' ||
    workflow.delivery?.format !== 'html type="renderer"' ||
    workflow.delivery.inputIdentity !== workflow.inputIdentity ||
    !renderer ||
    digest(renderer) !== workflow.delivery.sha256
  )
    throw new Error(
      'DELIVERY_REPLY_MISMATCH: 回复末尾须包含唯一且与本次已发布工作流原文一致的 renderer 代码块',
    );
}

export function wrapCheckedArtifact(html, artifact, report) {
  assertDeliveryPolicy(report);
  if (report.htmlSha256 !== digest(html))
    throw new Error('受检 HTML 与待交付 HTML 的 SHA-256 不一致');
  if (
    report.manifestSha256 !== artifact.manifestSha256 ||
    Object.values(artifact.manifest.assets).some(
      (asset) => !asset.url.startsWith('https://'),
    )
  )
    throw new Error('资源清单未发布或与验收不一致');
  const graph = artifact.graph;
  if (
    graph.contractRevision !== 3 ||
    report.checkerSha256 !== checkerIdentity() ||
    report.graphSha256 !== protocolHash(graph) ||
    report.protocolEvidence?.identities?.graphSha256 !== protocolHash(graph)
  )
    throw new Error('确定性验收报告与当前 Graph 或检查器不匹配');
  if (report.mode === 'startup') {
    assertStartupCoverage(report, graph.initialViewId || graph.views[0]?.id);
  } else {
    assertCompleteCoverage(
      report,
      graph.views.map((view) => view.id),
    );
    if (
      graph.views.some(
        (view) =>
          report.productJourneys?.filter(
            (journey) =>
              journey.viewId === view.id && journey.navigation === 'passed',
          ).length !== 1,
      )
    )
      throw new Error('用户交互路径验收不完整');
  }
  const content = html.endsWith('\n') ? html.slice(0, -1) : html;
  if (/^```/m.test(content))
    throw new Error(
      'RENDERER_FENCE_COLLISION: HTML 内容与 renderer 围栏冲突，不能降级交付链接',
    );
  return '\x60\x60\x60html type="renderer"\n' + content + '\n\x60\x60\x60\n';
}
