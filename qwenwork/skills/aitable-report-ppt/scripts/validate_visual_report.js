#!/usr/bin/env node
/* Generic structural and interaction validator for generated visual reports. */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

function loadPlaywright() {
  const candidates = [
    'playwright',
    process.env.CODEX_NODE_MODULES && path.join(process.env.CODEX_NODE_MODULES, 'playwright'),
  ].filter(Boolean);
  for (const candidate of candidates) {
    try { return require(candidate); } catch (_) {}
  }
  throw new Error('Playwright not found. Install it or set CODEX_NODE_MODULES.');
}

function args() {
  const values = process.argv.slice(2);
  if (!values[0]) throw new Error('Usage: validate_visual_report.js <report.html> [report-spec.json] [--oracle verification-oracle.json] [--preview] [--output result.json] [--screenshots dir]');
  const result = { html: path.resolve(values[0]), spec: null, oracle: null, output: null, screenshots: null, preview: false };
  let index = 1;
  if (values[index] && !values[index].startsWith('--')) result.spec = path.resolve(values[index++]);
  while (index < values.length) {
    const flag = values[index++];
    if (flag === '--output') result.output = path.resolve(values[index++]);
    else if (flag === '--screenshots') result.screenshots = path.resolve(values[index++]);
    else if (flag === '--oracle') result.oracle = path.resolve(values[index++]);
    else if (flag === '--preview') result.preview = true;
    else throw new Error(`Unknown argument: ${flag}`);
  }
  return result;
}

function memberDigest(keys) {
  const joined = [...keys].sort().join('\n');
  return 'sha256:' + crypto.createHash('sha256').update(joined, 'utf8').digest('hex');
}

function withinTolerance(actual, expected, tolerance) {
  if (expected === null || expected === undefined) return actual === null || actual === undefined;
  if (typeof expected !== 'number') return actual === expected;
  if (typeof actual !== 'number') return false;
  const type = (tolerance && tolerance.type) || 'exact';
  if (type === 'exact') return actual === expected;
  if (type === 'relative') return Math.abs(actual - expected) <= tolerance.value * Math.abs(expected);
  if (type === 'absolute') return Math.abs(actual - expected) <= tolerance.value;
  return false;
}

/* Oracle comparison: expected values come from the page-external Python
 * oracle; the page's verificationSnapshot() reports observations only. The
 * verdict is rendered HERE — the runtime never grades itself. */
function compareWithOracle(checks, snapshot, oracle) {
  /* runtime_asset_sha256 was declared by every page but compared by nobody, so
   * a report could inline a stale runtime and still pass the fingerprint gate. */
  const FP_KEYS = ['snapshot_sha256', 'report_spec_sha256', 'semantics_version',
    'runtime_contract_version', 'runtime_asset_sha256'];
  const pageFp = snapshot.fingerprints || {};
  const mismatched = FP_KEYS.filter(key => String(pageFp[key]) !== String(oracle[key]));
  assert(checks, 'oracle: FINGERPRINT_MATCH', mismatched.length === 0,
    mismatched.map(key => `${key}: page=${pageFp[key]} oracle=${oracle[key]}`));
  if (mismatched.length) return; // FINGERPRINT_MISMATCH: refuse to compare stale rulers

  for (const [id, expected] of Object.entries(oracle.metrics || {})) {
    if (expected.source !== 'computed') continue;
    const observed = snapshot.metrics && snapshot.metrics[id];
    assert(checks, `oracle: metric ${id}`,
      observed && observed.source === 'computed' && withinTolerance(observed.value, expected.expected, expected.tolerance),
      { expected: expected.expected, actual: observed && observed.value });
  }
  for (const [id, expected] of Object.entries(oracle.charts || {})) {
    if (!Array.isArray(expected.categories)) continue;
    const observed = snapshot.charts && snapshot.charts[id];
    const match = observed
      && JSON.stringify(observed.categories) === JSON.stringify(expected.categories)
      && Array.isArray(observed.values) && observed.values.length === expected.values.length
      && observed.values.every((value, i) => withinTolerance(value, expected.values[i], { type: 'exact' }));
    assert(checks, `oracle: chart ${id}`, match, { expected, actual: observed });
  }
  for (const [id, expected] of Object.entries(oracle.drilldowns || {})) {
    const observed = snapshot.drilldowns && snapshot.drilldowns[id];
    assert(checks, `oracle: drill ${id} count`, observed && observed.count === expected.expected_count,
      { expected: expected.expected_count, actual: observed && observed.count });
    if (expected.member_digest && observed && Array.isArray(observed.memberKeys)) {
      assert(checks, `oracle: drill ${id} member digest`, memberDigest(observed.memberKeys) === expected.member_digest,
        { expected: expected.member_digest, actual: memberDigest(observed.memberKeys) });
    }
  }
}

/* A check may end in one of three states, not two. "Cannot be decided from
 * CSS alone" is not a pass and not a defect — reporting it as either is a
 * guess wearing a verdict's clothes. These surface as manual_required so a
 * person looks, and they keep the run from being called green. */
function manualRequiredNames(checks) {
  return checks.filter(c => c.evidence && c.evidence.manual_required === true).map(c => c.name);
}

function assert(checks, name, passed, evidence) {
  checks.push({ name, passed: Boolean(passed), evidence });
}

/* Hash the runtime that is actually inside the HTML.
 *
 * The fingerprint gate used to compare the page's declared hash against the
 * oracle's declared hash — two claims, never the thing itself. A build that
 * inlined an old runtime while writing the new hash satisfied both. Reading
 * the bytes back out of the delivered file is the only version of this check
 * that cannot be satisfied by agreement between two labels.
 *
 * The inliner escapes `</script` as `<\/script` on the way in, so that has to
 * be undone before hashing or the digest can never match by construction. */
function inlinedRuntimeHash(htmlPath) {
  const html = fs.readFileSync(htmlPath, 'utf8');
  const match = html.match(/<script[^>]*data-inlined="runtime"[^>]*>([\s\S]*?)<\/script>/);
  if (!match) return null;
  const source = match[1].replace(/<\\\/script/g, '</script');
  return crypto.createHash('sha256').update(source, 'utf8').digest('hex');
}

/* ── Rendered-state gates ───────────────────────────────────────────────────
 * These check what the reader actually gets, not what the DOM intends.
 *
 * Two earlier versions of this file scored a defective report as green. The
 * first only measured overflow, so shrinking everything was the cheapest way
 * to pass. The second measured emptiness but forced every slide visible in
 * order to measure it — which erased the very state it was supposed to judge —
 * and read font-size without ever asking whether the text could be seen or
 * clicked. Both failures share one shape: the observer changed or ignored the
 * state, then graded its own convenient version of it.
 *
 * So: navigate for real, wait for the page to settle on its own, and judge the
 * final pixels. Floors are DISPLAYED px on the canonical desktop viewport
 * (authored value x stage scale); chart heights stay in authored stage px
 * because that is what a theme writes.
 */
const CANONICAL_DESKTOP = { width: 1280, height: 720 };
const READABILITY = {
  font: { body: 16, table: 14, axis: 14, label: 14, chrome: 12 },
  /* Contrast is never exempted by role or "accent colour" — an accent that is
   * legible on navy and invisible on cream is two different colours as far as
   * a reader is concerned. Only displayed size moves the bar. */
  contrast: { normal: 4.5, large: 3.0, largePx: 24, largeBoldPx: 18.66, boldWeight: 700 },
  density: {
    minSlideCoverage: 0.25,
    minAverageCoverage: 0.35,
    maxEmptyBandRatio: 0.35,
    minPrimaryChartTwoCol: 360,
    minPrimaryChartFullWidth: 420,
    maxSparseShare: 0.25,
  },
  sparseRoles: ['cover', 'section', 'chapter', 'statement', 'closing'],
  settle: { maxAnimationMs: 1500, deadlineMs: 2000, sampleGapMs: 100 },
};

/* Wait for one slide to reach its own final state. A fixed sleep cannot tell
 * "still animating" from "stuck forever", so this waits on the animations the
 * page actually declares, then proves the result held still. */
async function settleSlide(page, index, settle) {
  return page.evaluate(async ({ i, cfg }) => {
    const raf2 = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
    const rt = window.__visualReport;
    if (rt && rt.showSlide) rt.showSlide(i);
    await raf2();                       // frame 1 commits classes, frame 2 creates transitions

    const slide = document.querySelectorAll('section.slide,.slide')[i];
    if (!slide) return { settled: false, reason: 'slide-missing' };

    const meaningful = el => !el.closest('[data-visual-role="decorative"]');
    const anims = typeof slide.getAnimations === 'function'
      ? slide.getAnimations({ subtree: true }) : [];
    const endless = [];
    const finite = [];
    for (const a of anims) {
      const timing = a.effect && a.effect.getTiming ? a.effect.getTiming() : {};
      const target = a.effect && a.effect.target;
      const forever = timing.iterations === Infinity;
      if (forever || a.playState === 'paused') {
        // A decorative shimmer may loop; a paused animation on content cannot.
        if (target && meaningful(target)) endless.push({ playState: a.playState, forever });
      } else finite.push(a);
    }

    const overlong = finite.filter(a => (a.effect.getComputedTiming().endTime || 0) > cfg.maxAnimationMs);
    const deadline = new Promise(r => setTimeout(() => r('deadline'), cfg.deadlineMs));
    const done = Promise.all(finite.map(a => a.finished.catch(() => {}))).then(() => 'finished');
    const outcome = await Promise.race([done, deadline]);
    await raf2();

    // Two samples: if anything meaningful is still moving, it has not settled.
    const fingerprint = () => {
      const parts = [];
      slide.querySelectorAll('*').forEach(el => {
        if (el.children.length || !meaningful(el)) return;
        const r = el.getBoundingClientRect();
        let op = 1, p = el;
        while (p && p !== document.body) { op *= parseFloat(getComputedStyle(p).opacity); p = p.parentElement; }
        parts.push(`${Math.round(r.x)},${Math.round(r.y)},${Math.round(r.width)},${op.toFixed(2)}`);
      });
      return slide.className + '|' + parts.join(';');
    };
    const first = fingerprint();
    await new Promise(r => setTimeout(r, cfg.sampleGapMs));
    const second = fingerprint();
    /* ECharts animates inside a canvas via its own clock, so none of it shows
     * up in getAnimations(). Waiting only on DOM animations would measure a
     * chart mid-draw and call it settled. */
    /* Poll until the chart animations actually end, rather than sampling once:
     * a single look could not tell "100ms left to run" from "never finishes",
     * and reported both as unsettled. */
    const countClips = () => {
      let n = 0;
      if (!window.echarts) return n;
      slide.querySelectorAll('[data-chart-id],[data-chart],.chart').forEach(el => {
        const inst = window.echarts.getInstanceByDom(el);
        const zr = inst && inst.getZr && inst.getZr();
        const clips = zr && zr.animation && typeof zr.animation.getClips === 'function'
          ? zr.animation.getClips() : null;
        if (clips && clips.length) n += clips.length;
      });
      return n;
    };
    let chartClips = countClips();
    const clipDeadline = performance.now() + cfg.deadlineMs;
    while (chartClips > 0 && performance.now() < clipDeadline) {
      await new Promise(r => setTimeout(r, 100));
      chartClips = countClips();
    }
    const stillRunning = (typeof slide.getAnimations === 'function'
      ? slide.getAnimations({ subtree: true }) : [])
      .filter(a => a.playState === 'running' && a.effect
        && a.effect.getTiming().iterations !== Infinity
        && a.effect.target && meaningful(a.effect.target)).length;

    /* Environment failure is a claim about the browser, not the report, so it
     * needs browser-level evidence. Without that, an animation that never ends
     * is the report's defect even if it only shows up in one engine. */
    const env = {
      documentVisible: document.visibilityState === 'visible',
      rafAdvancing: await new Promise(r => { const t0 = performance.now();
        requestAnimationFrame(() => r(performance.now() > t0)); }),
    };
    return {
      /* overlong used to be recorded and then ignored, so an animation that
       * outlived the budget was noted in the evidence and passed anyway. */
      settled: outcome === 'finished' && first === second && stillRunning === 0
        && !endless.length && !overlong.length && chartClips === 0,
      reason: outcome === 'deadline' ? 'animation-deadline'
        : first !== second ? 'still-moving'
        : endless.length ? 'endless-or-paused-animation-on-content'
        : overlong.length ? 'animation-longer-than-budget'
        : stillRunning ? 'animations-still-running'
        : chartClips ? 'chart-canvas-still-animating' : null,
      env,
      evidence: { endless, overlong: overlong.length, animationCount: anims.length, chartClips },
    };
  }, { i: index, cfg: settle });
}

/* Measure the slide as it now stands. Nothing here mutates the page. */
async function measureActiveSlide(page, index, cfg) {
  return page.evaluate(({ i, cfg }) => {
    const slide = document.querySelectorAll('section.slide,.slide')[i];
    const sr = slide.getBoundingClientRect();
    const stage = document.querySelector('#deckStage,.deck-stage');
    const m = stage ? new DOMMatrixReadOnly(getComputedStyle(stage).transform) : null;
    const scale = m && m.a ? m.a : 1;

    const num = s => (String(s).match(/[-\d.]+/g) || [0, 0, 0, 1]).map(Number);
    const relLum = ([r, g, b]) => { const f = [r, g, b].map(v => { v /= 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
      return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]; };
    const over = (fg, bg) => { const a = fg[3] === undefined ? 1 : fg[3];
      return [0, 1, 2].map(k => fg[k] * a + bg[k] * (1 - a)); };
    /* Composite every translucent background down to one opaque colour, and
     * report when the stack is not solid. A gradient or image leaves
     * backgroundColor transparent, so computing against it would silently
     * score the text against white — a false pass, which is worse than saying
     * "cannot decide". Those are surfaced as manual_required instead. */
    const surfaceOf = el => { let p = el, stack = [], nonSolid = null;
      while (p && p !== document.documentElement) {
        const cs = getComputedStyle(p);
        if (!nonSolid && cs.backgroundImage && cs.backgroundImage !== 'none')
          nonSolid = cs.backgroundImage.slice(0, 40);
        /* A gradient painted by ::before/::after covers the element just as
         * effectively as its own background, and Signal-style themes do exactly
         * that. Missing it would mean scoring text against a colour that is not
         * what the reader sees. */
        if (!nonSolid) for (const pseudo of ['::before', '::after']) {
          const ps = getComputedStyle(p, pseudo);
          if (ps && ps.content && ps.content !== 'none'
            && ps.backgroundImage && ps.backgroundImage !== 'none') {
            nonSolid = pseudo + ' ' + ps.backgroundImage.slice(0, 32);
            break;
          }
        }
        const c = num(cs.backgroundColor);
        const a = c[3] === undefined ? 1 : c[3];
        if (a > 0) stack.push(c);
        if (a === 1) break;
        p = p.parentElement;
      }
      let base = [255, 255, 255];
      for (let k = stack.length - 1; k >= 0; k--) base = over(stack[k], base);
      return { color: base, nonSolid }; };
    const ratio = (fg, bg) => { const [hi, lo] = [relLum(fg), relLum(bg)].sort((a, b) => b - a);
      return (hi + 0.05) / (lo + 0.05); };

    const roleOf = el => {
      const marked = el.closest('[data-visual-role],[data-text-role]');
      if (marked) return marked.getAttribute('data-visual-role') || marked.getAttribute('data-text-role');
      if (el.closest('table')) return 'table';
      if (el.closest('footer,[class*="foot"],[class*="page-num"],[class*="slide-number"]')) return 'chrome';
      return 'body';
    };
    const effectiveOpacity = el => { let o = 1, p = el;
      while (p && p !== document.body) { o *= parseFloat(getComputedStyle(p).opacity); p = p.parentElement; }
      return o; };
    const hiddenByChain = el => { let p = el;
      while (p && p !== document.body) { const cs = getComputedStyle(p);
        if (cs.display === 'none' || cs.visibility === 'hidden') return true; p = p.parentElement; }
      return false; };

    const tooSmall = [], lowContrast = [], invisible = [], unresolved = [],
          abusedRoles = [], placeholders = [], stretched = [];

    /* A list whose rows are stretched to fill a tall container reads as broken
     * even though every existing floor is satisfied: the text is legible, each
     * individual gap is under the empty-band cap, and the rows span enough grid
     * columns to clear the coverage floor. The defect is spread evenly, so
     * "not enough anywhere" never becomes "too little somewhere".
     *
     * Its signature is exact: the rendered gap between siblings dwarfs the gap
     * the CSS asked for. 18px declared, 156px rendered — that difference is the
     * container distributing leftover height, not a designed rhythm. */
    slide.querySelectorAll('ul,ol,[class*="list"],[class*="grid"],[class*="stack"]').forEach(box => {
      const kids = [...box.children].filter(k => k.getBoundingClientRect().height > 4);
      if (kids.length < 2) return;
      const declaredGap = parseFloat(getComputedStyle(box).rowGap || getComputedStyle(box).gap) || 0;
      const rects = kids.map(k => k.getBoundingClientRect());
      const gaps = [];
      for (let i = 1; i < rects.length; i++) gaps.push(rects[i].top - rects[i - 1].bottom);
      if (!gaps.length) return;
      const median = gaps.slice().sort((a, b) => a - b)[Math.floor(gaps.length / 2)];
      const tallest = Math.max(...rects.map(r => r.height));
      // Two independent signs, both required: far beyond the declared gap, and
      // wider than the rows themselves.
      const overDeclared = declaredGap > 0 && median > declaredGap * 3 && median > 40 * scale;
      const overContent = median > tallest * 1.2;
      if (overDeclared && overContent) {
        stretched.push({ container: box.className.toString().slice(0, 28), variant: 'gaps',
          declaredGap: +declaredGap.toFixed(1), renderedGap: Math.round(median / scale),
          rowHeight: Math.round(tallest / scale), rows: kids.length });
        return;
      }
      /* Same cause, opposite symptom. Leftover height in a container flows to
       * one of two places: into the gaps between rows (above), or into the row
       * boxes themselves (grid-auto-rows:1fr, align-items:stretch). In the
       * second case the gap stays exactly as declared and only the boxes
       * inflate, so the test above cannot see it — yet the page looks equally
       * broken, each line of text marooned in its own tall empty box.
       *
       * A Range over the node's contents measures what the row actually holds;
       * scrollHeight would just report the stretched box back to us. */
      /* A tall box is only wasted space if nothing occupies it. A heat-map cell
       * is 299px tall holding one short label, and that is correct: the cell is
       * a painted tile whose area carries the value through its colour. A
       * stretched text row is the same shape with nothing on the surface.
       *
       * Geometry cannot separate them; paint can. If the row has its own
       * background or border, its area is doing work — leave it alone. */
      const painted = kids.some(k => {
        const cs = getComputedStyle(k);
        // computed backgroundColor is always rgb()/rgba(); `transparent`
        // resolves to rgba(0,0,0,0), so alpha alone decides.
        const bg = num(cs.backgroundColor);
        const opaque = bg.length > 3 ? bg[3] > 0.05 : true;
        const bordered = ['Top', 'Right', 'Bottom', 'Left'].some(side =>
          parseFloat(cs['border' + side + 'Width']) > 0.5 &&
          cs['border' + side + 'Style'] !== 'none');
        return opaque || bordered;
      });
      if (painted) return;
      const slack = rects.map((r, i) => {
        const range = slide.ownerDocument.createRange();
        range.selectNodeContents(kids[i]);
        const inner = range.getBoundingClientRect();
        range.detach();
        return inner.height > 4 ? r.height - inner.height : 0;
      });
      const medianSlack = slack.slice().sort((a, b) => a - b)[Math.floor(slack.length / 2)];
      const medianRow = rects.map(r => r.height).sort((a, b) => a - b)[Math.floor(rects.length / 2)];
      if (medianSlack > 60 * scale && medianSlack > medianRow * 0.55) {
        stretched.push({ container: box.className.toString().slice(0, 28), variant: 'rows',
          declaredGap: +declaredGap.toFixed(1), rowHeight: Math.round(medianRow / scale),
          emptyInsideRow: Math.round(medianSlack / scale), rows: kids.length });
      }
    });
    /* Legibility checks cannot see wrongness, only illegibility: a cell reading
     * "undefined" has perfect size and contrast and sailed through 66 green
     * checks. These literals are never intended content — they are a value that
     * failed to arrive, rendered as if it had. */
    /* Substring, not whole-string: an exact match let "undefined%", "值：NaN"
     * and "null 条" through — the leak is just as real when it is glued to
     * a unit or a label. */
    const LEAKED = /\b(undefined|NaN|Infinity)\b|\[object Object\]|(?:^|[^\w])null(?:$|[^\w])/;

    /* `decorative` skips the font, contrast and coverage checks entirely, so it
     * is the cheapest way to make a failing page pass. A theme has already been
     * seen reaching for `chrome` to lower a bar; leaving this one unconstrained
     * is not a hypothetical risk. A decorative subtree must actually be
     * decoration: no readable text, no data, and inert to the reader. */
    slide.querySelectorAll('[data-visual-role="decorative"]').forEach(node => {
      const cs = getComputedStyle(node);
      const reasons = [];
      if ((node.textContent || '').trim().length) reasons.push('contains text');
      if (node.querySelector('table,canvas,[data-chart-id],[data-chart],[data-metric-id],[data-drill-chip],[data-drill-tag]'))
        reasons.push('contains data or an interactive target');
      if (node.getAttribute('aria-hidden') !== 'true') reasons.push('not aria-hidden');
      if (cs.pointerEvents !== 'none') reasons.push('still receives pointer events');
      if (reasons.length)
        abusedRoles.push({ tag: node.tagName, cls: node.className.toString().slice(0, 28), reasons });
    });
    const COLS = 48, ROWS = 27, grid = new Uint8Array(COLS * ROWS);

    slide.querySelectorAll('*').forEach(el => {
      const cs = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) return;
      if (hiddenByChain(el)) return;
      const vrole = el.closest('[data-visual-role]')?.getAttribute('data-visual-role');
      const decorative = vrole === 'decorative';
      const opacity = effectiveOpacity(el);

      /* Judge an element's OWN text, not its descendants'. Testing only
       * childless elements skipped the plain half of mixed content like
       * `<p>text <em>emphasis</em></p>`, and a length>=2 rule meant a single
       * character — or text deliberately split into one-character spans —
       * never got checked at all. */
      const ownText = (() => { let s = '';
        for (const n of el.childNodes) if (n.nodeType === 3) s += n.nodeValue;
        return s.trim(); })();
      {
        const text = ownText;
        if (text.length >= 1 && !decorative) {
          const role = roleOf(el);
          const shown = parseFloat(cs.fontSize) * scale;
          const floor = cfg.font[role] ?? cfg.font.body;
          if (shown + 0.5 < floor)
            tooSmall.push({ role, shown: +shown.toFixed(1), floor, text: text.slice(0, 22) });
          if (LEAKED.test(text))
            placeholders.push({ text, tag: el.tagName, cls: el.className.toString().slice(0, 24) });
          // Invisible text is worse than small text and must not be excused.
          if (opacity < 0.95)
            invisible.push({ text: text.slice(0, 22), effectiveOpacity: +opacity.toFixed(2) });
          const weight = parseInt(cs.fontWeight, 10) || 400;
          const isLarge = shown >= cfg.contrast.largePx
            || (weight >= cfg.contrast.boldWeight && shown >= cfg.contrast.largeBoldPx);
          const need = isLarge ? cfg.contrast.large : cfg.contrast.normal;
          const surface = surfaceOf(el);
          // Text alpha counts too: rgba(0,0,0,.2) is not black to a reader.
          const cr = ratio(over(num(cs.color), surface.color), surface.color);
          if (surface.nonSolid)
            unresolved.push({ text: text.slice(0, 22), background: surface.nonSolid,
              computedAgainstSolid: +cr.toFixed(2) });
          else if (cr + 0.05 < need)
            lowContrast.push({ text: text.slice(0, 22), shown: +shown.toFixed(1),
              color: cs.color, contrast: +cr.toFixed(2), need });
        }
      }

      const leafish = !el.children.length || /^(CANVAS|SVG|IMG|TABLE|TR)$/.test(el.tagName);
      /* validation.md says chrome is excluded from coverage; the code excluded
       * only <footer>, so anything a theme marked as chrome still counted as
       * content and inflated the fill number. */
      const isChrome = roleOf(el) === 'chrome';
      if (leafish && !decorative && !isChrome && opacity >= 0.95 && !el.closest('footer')) {
        const c0 = Math.max(0, Math.floor((r.left - sr.left) / sr.width * COLS));
        const c1 = Math.min(COLS - 1, Math.floor((r.right - sr.left) / sr.width * COLS));
        const r0 = Math.max(0, Math.floor((r.top - sr.top) / sr.height * ROWS));
        const r1 = Math.min(ROWS - 1, Math.floor((r.bottom - sr.top) / sr.height * ROWS));
        for (let y = r0; y <= r1; y++) for (let x = c0; x <= c1; x++) grid[y * COLS + x] = 1;
      }
    });

    let filled = 0, run = 0, maxRun = 0;
    for (let y = 0; y < ROWS; y++) {
      let any = false;
      for (let x = 0; x < COLS; x++) if (grid[y * COLS + x]) { any = true; break; }
      if (any) { filled++; if (run > maxRun) maxRun = run; run = 0; } else run++;
    }
    if (run > maxRun) maxRun = run;

    /* Anything the reader is told to click must actually receive the click.
     * A target under 4px was previously skipped — which quietly excused the
     * exact failure mode this gate exists for, a hit area too small to hit. */
    const obstructed = [];
    const targets = slide.querySelectorAll(
      '[data-chart-id],[data-chart],.chart,[data-metric-id],[data-drill-chip],[data-drill-tag]');
    targets.forEach(t => {
      const b = t.getBoundingClientRect();
      const name = t.getAttribute('data-chart-id') || t.getAttribute('data-chart')
        || t.getAttribute('data-metric-id') || t.getAttribute('data-drill-tag')
        || t.className.toString().slice(0, 24);
      if (b.width < 4 || b.height < 4) {
        obstructed.push({ target: name, covering: `hit area only ${Math.round(b.width)}x${Math.round(b.height)}px` });
        return;
      }
      const hit = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
      if (hit && !t.contains(hit) && hit !== t)
        obstructed.push({ target: t.getAttribute('data-chart-id') || t.getAttribute('data-chart')
          || t.getAttribute('data-metric-id') || t.className.toString().slice(0, 24),
          covering: hit.tagName + '.' + hit.className.toString().slice(0, 24) });
      if (getComputedStyle(t).pointerEvents === 'none')
        obstructed.push({ target: t.getAttribute('data-chart-id') || 'chart', covering: 'pointer-events:none' });
    });

    const charts = [...slide.querySelectorAll('[data-chart-id],[data-chart],.chart')].map(c => ({
      id: c.getAttribute('data-chart-id') || c.getAttribute('data-chart') || null,
      authoredHeight: Math.round(c.getBoundingClientRect().height / scale),
      widthRatio: c.getBoundingClientRect().width / sr.width,
      /* Measured while THIS slide is the active one. Sampling every chart in
       * one global pass would read charts on inactive slides as dimmed —
       * they are hidden by design, not by a defect. */
      effectiveOpacity: +effectiveOpacity(c).toFixed(2),
      isHeatmap: Boolean(c.querySelector('[data-heatmap-cell]')),
    }));

    return { slide: i + 1, scale: +scale.toFixed(4),
      coverage: +(grid.reduce((a, b) => a + b, 0) / (COLS * ROWS)).toFixed(3),
      emptyBandRatio: +(maxRun / ROWS).toFixed(3),
      tooSmall, lowContrast, invisible, unresolved, abusedRoles, placeholders, stretched, obstructed, charts };
  }, { i: index, cfg });
}

async function inspectRenderedState(page, config, checks, label, screenshotDir) {
  const spec = config.spec || {};
  const density = spec.modes?.presentation?.density || null;
  const sections = Array.isArray(spec.sections) ? spec.sections : [];
  const rolesDeclared = sections.some(s => s.slide_role);
  const sparseIndices = [];
  sections.forEach((section, index) => {
    const role = String(section.slide_role || section.presentation_layout || '').toLowerCase();
    /* Exact match, not substring: `includes` let a role named
     * "uncovered-analysis" match "cover" and quietly exempt an analysis slide
     * from every density floor. */
    if (READABILITY.sparseRoles.indexOf(role) !== -1) sparseIndices.push(index);
  });

  const slideCount = await page.evaluate(() => document.querySelectorAll('section.slide,.slide').length);
  if (!slideCount) return;

  const perSlide = [], unsettled = [];
  for (let i = 0; i < slideCount; i++) {
    const state = await settleSlide(page, i, READABILITY.settle);
    if (!state.settled) unsettled.push({ slide: i + 1, ...state });
    const measured = await measureActiveSlide(page, i, READABILITY);
    measured.sparse = rolesDeclared ? sparseIndices.includes(i) : i === 0;
    perSlide.push(measured);
    if (screenshotDir) {
      fs.mkdirSync(screenshotDir, { recursive: true });
      await page.screenshot({ path: path.join(screenshotDir, `${label}-slide-${String(i + 1).padStart(2, '0')}.png`) });
    }
  }

  const envBroken = unsettled.filter(u => u.env && (!u.env.documentVisible || !u.env.rafAdvancing));
  if (envBroken.length) {
    checks.push({ name: `${label}: rendered-state inspection inconclusive`, passed: false,
      evidence: { manual_required: true, reason: 'browser could not animate or paint', slides: envBroken } });
    return;
  }
  assert(checks, `${label}: every slide settles to a final state`, unsettled.length === 0,
    unsettled.map(u => ({ slide: u.slide, reason: u.reason, ...u.evidence })));

  const flat = key => perSlide.flatMap(s => s[key].map(v => ({ slide: s.slide, ...v })));
  const small = flat('tooSmall'), faint = flat('lowContrast'),
        unseen = flat('invisible'), blocked = flat('obstructed'),
        undecided = flat('unresolved'), abused = flat('abusedRoles'),
        leaked = flat('placeholders'), spread = flat('stretched');

  /* Text over a gradient or image cannot be scored from CSS alone. Reporting
   * it as passing would be a guess dressed as a verdict, so it is escalated
   * for a human instead of being resolved either way by default. */
  if (undecided.length) {
    checks.push({ name: `${label}: contrast undecidable over non-solid background`, passed: false,
      evidence: { manual_required: true, count: undecided.length, sample: undecided.slice(0, 6) } });
  }

  assert(checks, `${label}: list rows are not stretched to fill their container`, spread.length === 0,
    { violations: spread.length, sample: spread.slice(0, 6),
      note: 'rendered row gap far exceeds the declared gap and the rows themselves — the container is distributing leftover height' });
  assert(checks, `${label}: no placeholder or error literals rendered`, leaked.length === 0,
    { violations: leaked.length, sample: leaked.slice(0, 8),
      note: 'undefined / null / NaN / [object Object] in visible text means a value never arrived' });
  assert(checks, `${label}: text meets displayed font floors`, small.length === 0,
    { violations: small.length, sample: small.slice(0, 8) });
  assert(checks, `${label}: text meets contrast floors`, faint.length === 0,
    { violations: faint.length, sample: faint.slice(0, 8) });
  assert(checks, `${label}: no text hidden by a transparent ancestor`, unseen.length === 0,
    { violations: unseen.length, sample: unseen.slice(0, 8) });
  assert(checks, `${label}: decorative role is not used to skip checks`, abused.length === 0,
    { violations: abused.length, sample: abused.slice(0, 6),
      rule: 'data-visual-role="decorative" requires: no text, no data/interactive content, aria-hidden=true, pointer-events:none' });
  assert(checks, `${label}: interactive targets are not obstructed`, blocked.length === 0,
    { violations: blocked.length, sample: blocked.slice(0, 8) });

  const chartFonts = await page.evaluate(cfg => {
    const out = [];
    if (!window.echarts) return out;
    const stage = document.querySelector('#deckStage,.deck-stage');
    const m = stage ? new DOMMatrixReadOnly(getComputedStyle(stage).transform) : null;
    const scale = m && m.a ? m.a : 1;
    document.querySelectorAll('[data-chart-id],[data-chart],.chart').forEach(el => {
      const inst = window.echarts.getInstanceByDom(el);
      if (!inst) return;
      const o = inst.getOption() || {};
      const pick = v => (Array.isArray(v) ? v[0] : v) || {};
      /* The SMALLEST text in the chart decides whether the chart is readable.
       * Taking the first value that happened to be defined let an x axis at
       * 21px vouch for a y axis at 10px. ECharts falls back to 12px wherever a
       * size is unset, so an absent value is a real 12px, not "unknown". */
      const sizes = [];
      const push = v => { const n = Number(v); if (isFinite(n) && n > 0) sizes.push(n); };
      const fallback = o.textStyle?.fontSize ?? 12;
      for (const axis of [].concat(o.xAxis || [], o.yAxis || []))
        push(axis?.axisLabel?.fontSize ?? fallback);
      for (const legend of [].concat(o.legend || []))
        push(legend?.textStyle?.fontSize ?? fallback);
      for (const series of [].concat(o.series || []))
        if (series?.label?.show) push(series.label.fontSize ?? fallback);
      if (!sizes.length) push(fallback);
      const authored = Math.min.apply(null, sizes);
      /* Chart text lives in a canvas, so the DOM contrast pass never sees it.
       * The user's original complaint included faded axis labels — checking
       * only its size would let the same defect through again. Colour comes
       * from the option; the surface is whatever the canvas sits on. */
      const colors = [];
      const pushColor = c => { if (typeof c === 'string' && c) colors.push(c); };
      for (const axis of [].concat(o.xAxis || [], o.yAxis || []))
        pushColor(axis?.axisLabel?.color ?? o.textStyle?.color);
      for (const legend of [].concat(o.legend || []))
        pushColor(legend?.textStyle?.color ?? o.textStyle?.color);
      // 数据标签同样是 canvas 里的可见文字，此前完全没纳入。
      for (const series of [].concat(o.series || []))
        if (series?.label?.show) pushColor(series.label.color ?? o.textStyle?.color);
      /* Parse hex as well as rgb()/rgba(): ECharts options are usually hex, and
       * a digit-scraping parser found no digits in "#fdfdfd", fell back to
       * black, and scored near-invisible label text as maximum contrast. An
       * unparseable colour must be reported, never defaulted — the default was
       * silently the safest possible answer. */
      const num2 = str => {
        const raw = String(str).trim();
        const hex = raw.match(/^#((?:[0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8}))$/i);
        if (hex) {
          let h = hex[1];
          if (h.length === 3 || h.length === 4) h = h.split('').map(c => c + c).join('');
          const v = [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16));
          const a = h.length === 8 ? parseInt(h.slice(6, 8), 16) / 255 : 1;
          return [v[0], v[1], v[2], a];
        }
        /* hsl(200,50%,50%) scraped as digits becomes [200,50,50] and is then
         * treated as RGB — a completely different colour, scored confidently.
         * Convert it properly, and refuse anything else rather than guess. */
        const hsl = raw.match(/^hsla?\(([^)]+)\)$/i);
        if (hsl) {
          const parts = hsl[1].split(/[,\s/]+/).filter(Boolean);
          if (parts.length < 3) return null;
          /* turn/rad/grad are legal hue units; reading them as degrees turns
           * 0.5turn (180°) into 0.5° — a completely different colour, scored
           * with full confidence. Convert them, refuse anything unrecognised. */
          const hueRaw = parts[0].trim();
          const hueUnit = hueRaw.match(/(turn|rad|grad|deg)$/i);
          let hueDeg = parseFloat(hueRaw);
          if (!isFinite(hueDeg)) return null;
          if (hueUnit) {
            const unit = hueUnit[1].toLowerCase();
            if (unit === 'turn') hueDeg *= 360;
            else if (unit === 'rad') hueDeg = hueDeg * 180 / Math.PI;
            else if (unit === 'grad') hueDeg *= 0.9;
          } else if (/[a-z%]/i.test(hueRaw)) {
            return null;                    // unknown unit — do not guess
          }
          const h = ((hueDeg % 360) + 360) % 360 / 360;
          const sat = parseFloat(parts[1]) / 100;
          const light = parseFloat(parts[2]) / 100;
          const alpha = parts[3] === undefined ? 1
            : (parts[3].endsWith('%') ? parseFloat(parts[3]) / 100 : parseFloat(parts[3]));
          if ([h, sat, light].some(n => !isFinite(n))) return null;
          const q = light < 0.5 ? light * (1 + sat) : light + sat - light * sat;
          const pp = 2 * light - q;
          const channel = tc => {
            let x = tc; if (x < 0) x += 1; if (x > 1) x -= 1;
            if (x < 1 / 6) return pp + (q - pp) * 6 * x;
            if (x < 1 / 2) return q;
            if (x < 2 / 3) return pp + (q - pp) * (2 / 3 - x) * 6;
            return pp;
          };
          return sat === 0
            ? [light * 255, light * 255, light * 255, alpha]
            : [channel(h + 1 / 3) * 255, channel(h) * 255, channel(h - 1 / 3) * 255, alpha];
        }
        const rgb = raw.match(/^rgba?\(([^)]+)\)$/i);
        if (rgb) {
          const nums = rgb[1].split(/[,\s/]+/).filter(Boolean).map(Number);
          if (nums.length >= 3 && nums.slice(0, 3).every(isFinite)) return nums.slice(0, 4);
        }
        return null;                      // unknown notation — say so, do not guess
      };
      const lum2 = ([r, g, b]) => { const f = [r, g, b].map(x => { x /= 255;
        return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
        return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]; };
      /* Composite the whole stack, and let the chart's own backgroundColor win
       * where it sets one — taking only the first fully opaque CSS layer
       * ignored every translucent card painted on top of it, which is exactly
       * where a light-on-light combination hides. */
      let nonSolidBg = null;
      const layers = [];
      let node2 = el;
      while (node2 && node2 !== document.documentElement) {
        const cs2 = getComputedStyle(node2);
        if (!nonSolidBg && cs2.backgroundImage && cs2.backgroundImage !== 'none')
          nonSolidBg = cs2.backgroundImage.slice(0, 32);
        const c = num2(cs2.backgroundColor);
        if (c && (c[3] === undefined ? 1 : c[3]) > 0) layers.push(c);
        if (c && (c[3] === undefined ? 1 : c[3]) === 1) break;
        node2 = node2.parentElement;
      }
      /* A translucent chart background still tints everything under it; taking
       * it only when fully opaque discarded exactly the cases where the tint
       * pushes text toward its backdrop. Non-string (gradient object) means
       * this cannot be resolved from the option at all. */
      if (o.backgroundColor && typeof o.backgroundColor !== 'string') {
        nonSolidBg = nonSolidBg || 'option.backgroundColor is a gradient object';
      } else if (o.backgroundColor) {
        const own = num2(o.backgroundColor);
        if (own) layers.unshift(own);
        else nonSolidBg = nonSolidBg || `unparsable option.backgroundColor: ${o.backgroundColor}`;
      }
      let bg = [255, 255, 255];
      for (let k = layers.length - 1; k >= 0; k--) {
        const a = layers[k][3] === undefined ? 1 : layers[k][3];
        bg = [0, 1, 2].map(i => layers[k][i] * a + bg[i] * (1 - a));
      }
      const unparsed = [];
      const contrast = colors.map(col => {
        const fg = num2(col);
        if (!fg) { unparsed.push(col); return null; }
        const a = fg[3] === undefined ? 1 : fg[3];
        const composited = [0, 1, 2].map(k => fg[k] * a + bg[k] * (1 - a));
        const [hi, lo] = [lum2(composited), lum2(bg)].sort((x, y) => y - x);
        return +((hi + 0.05) / (lo + 0.05)).toFixed(2);
      });
      out.push({ id: el.getAttribute('data-chart-id') || el.getAttribute('data-chart') || null,
        authored, shown: +(authored * scale).toFixed(1), measured: sizes.length,
        colors, contrast, unparsed, nonSolidBg });
    });
    return out;
  }, READABILITY);
  const smallCharts = chartFonts.filter(c => c.shown + 0.5 < READABILITY.font.axis);
  assert(checks, `${label}: chart axis text meets font floor`, smallCharts.length === 0,
    { floor: READABILITY.font.axis, offenders: smallCharts });
  /* Colours were collected but never judged — the same half-finished shape as
   * declaring a hash and never comparing it. Axis text that is legible in the
   * option and invisible on the page is the defect the user actually reported. */
  const faintChartText = chartFonts.filter(c => Array.isArray(c.contrast)
    && c.contrast.some(v => v !== null && v + 0.05 < READABILITY.contrast.normal));
  const chartsOnPattern = chartFonts.filter(c => c.nonSolidBg);
  if (chartsOnPattern.length) {
    checks.push({ name: `${label}: chart contrast undecidable over non-solid background`,
      passed: false,
      evidence: { manual_required: true,
        offenders: chartsOnPattern.map(c => ({ id: c.id, background: c.nonSolidBg })) } });
  }
  const unparsedChartColors = chartFonts.filter(c => (c.unparsed || []).length);
  if (unparsedChartColors.length) {
    checks.push({ name: `${label}: chart colour notation not understood`, passed: false,
      evidence: { manual_required: true,
        offenders: unparsedChartColors.map(c => ({ id: c.id, colors: c.unparsed })) } });
  }
  assert(checks, `${label}: chart text meets contrast floors`, faintChartText.length === 0,
    { floor: READABILITY.contrast.normal,
      offenders: faintChartText.map(c => ({ id: c.id, colors: c.colors, contrast: c.contrast })) });

  const fadedCharts = perSlide.flatMap(s => s.charts
    .filter(c => c.effectiveOpacity < 0.95)
    .map(c => ({ slide: s.slide, id: c.id, effectiveOpacity: c.effectiveOpacity })));
  assert(checks, `${label}: charts are not dimmed by a transparent ancestor`, fadedCharts.length === 0,
    { offenders: fadedCharts });

  if (density === 'reading-first') {
    const d = READABILITY.density;
    const dense = perSlide.filter(s => !s.sparse);
    if (!rolesDeclared) checks.push({ name: `${label}: slide_role declared for density exemptions`,
      passed: true, evidence: 'warning: spec declares no slide_role; only slide 1 treated as sparse' });

    if (rolesDeclared && perSlide.length >= 4) {
      const share = (perSlide.length - dense.length) / perSlide.length;
      assert(checks, `${label}: sparse slides within share cap`, share <= d.maxSparseShare + 1e-9,
        { sparseShare: +share.toFixed(2), cap: d.maxSparseShare });
    }
    const thin = dense.filter(s => s.coverage < d.minSlideCoverage);
    assert(checks, `${label}: every analysis slide meets minimum coverage`, thin.length === 0,
      { floor: d.minSlideCoverage, offenders: thin.map(s => ({ slide: s.slide, coverage: s.coverage })) });
    const avg = dense.length ? dense.reduce((a, s) => a + s.coverage, 0) / dense.length : 1;
    assert(checks, `${label}: average coverage across analysis slides`, avg >= d.minAverageCoverage,
      { average: +avg.toFixed(3), floor: d.minAverageCoverage });
    const banded = dense.filter(s => s.emptyBandRatio > d.maxEmptyBandRatio);
    assert(checks, `${label}: no oversized empty band`, banded.length === 0,
      { cap: d.maxEmptyBandRatio, offenders: banded.map(s => ({ slide: s.slide, band: s.emptyBandRatio })) });
    const shortCharts = [];
    dense.forEach(s => s.charts.forEach(c => {
      // 热力图的高度由格子尺寸决定，不适用"主图最小高度"这条。
      if (c.isHeatmap) return;
      const floor = c.widthRatio > 0.7 ? d.minPrimaryChartFullWidth : d.minPrimaryChartTwoCol;
      if (c.authoredHeight + 1 < floor)
        shortCharts.push({ slide: s.slide, id: c.id, authoredHeight: c.authoredHeight, floor });
    }));
    assert(checks, `${label}: primary charts meet minimum height`, shortCharts.length === 0,
      { offenders: shortCharts });
  }
}
/* Where a chart drill-down must be clicked, derived from the chart itself.
 *
 * A browser case used to carry an arbitrary CSS selector, so "this chart is
 * drillable" could be demonstrated by clicking a chip somewhere else on the
 * page. That is how a deck ended up with 122 tiny tags: they existed to satisfy
 * the validator, not the reader. The declared trigger is the contract, so the
 * click target is computed from `ref_id` + `category` and nothing else.
 *
 * Returns null when the chart is not an axis chart (pie sectors are their own
 * hit area and keep the selector path) or the category cannot be located. */
async function chartClickPoint(page, chartId, category) {
  return page.evaluate(({ id, cat }) => {
    const el = document.querySelector(`[data-chart-id="${id}"],[data-chart="${id}"]`);
    if (!el || !window.echarts) return null;
    const inst = window.echarts.getInstanceByDom(el);
    if (!inst) return null;
    const option = inst.getOption() || {};
    const stageEl = document.querySelector('#deckStage,.deck-stage');
    const mm = stageEl ? new DOMMatrixReadOnly(getComputedStyle(stageEl).transform) : null;
    const stageScale = mm && mm.a ? mm.a : 1;
    const box = el.getBoundingClientRect();
    const axis = (option.xAxis || [])[0];
    const categories = (axis && axis.data) || [];

    if (!categories.length) {
      /* Item geometry (pie / donut). Clicking the element's centre is wrong —
       * on a donut that is the hole, and on a pie it is whichever sector
       * happens to sit at the middle. Compute the requested sector's own
       * midpoint from the option so the click lands inside that sector. */
      const series = (option.series || [])[0];
      if (!series || !Array.isArray(series.data)) return null;
      const values = series.data.map(d => Number(d && d.value !== undefined ? d.value : d) || 0);
      const names = series.data.map(d => String(d && d.name !== undefined ? d.name : ''));
      /* A whole-chart drill on a pie has no category; clicking its largest
       * sector is a definite point inside the chart, where clicking the centre
       * would land in a donut's hole. */
      const idx = (cat === undefined || cat === null || cat === '')
        ? values.indexOf(Math.max(...values))
        : names.findIndex(n => n === String(cat));
      if (idx < 0) return { error: 'category-not-in-chart', categories: names.slice(0, 12) };
      const total = values.reduce((a, b) => a + b, 0);
      if (!total) return null;
      const before = values.slice(0, idx).reduce((a, b) => a + b, 0);
      const midFraction = (before + values[idx] / 2) / total;
      const startAngle = series.startAngle === undefined ? 90 : series.startAngle;
      const clockwise = series.clockwise !== false;
      const angle = (startAngle + (clockwise ? -1 : 1) * midFraction * 360) * Math.PI / 180;
      // Radius/centre are percentages of the chart's own unscaled box.
      const localW = box.width / stageScale, localH = box.height / stageScale;
      const pct = (v, base) => typeof v === 'string' && v.endsWith('%')
        ? parseFloat(v) / 100 * base : Number(v) || 0;
      const radii = Array.isArray(series.radius) ? series.radius : [0, series.radius || '75%'];
      /* ECharts resolves a percentage radius against min(width,height)/2,
       * not against min(width,height). Passing the larger base doubled every
       * radius and put the computed point outside the pie altogether. */
      const ref = Math.min(localW, localH) / 2;
      const rMid = (pct(radii[0], ref) + pct(radii[1], ref)) / 2;
      const centre = Array.isArray(series.center) ? series.center : ['50%', '50%'];
      const cx = pct(centre[0], localW), cy = pct(centre[1], localH);
      return { x: box.left + (cx + rMid * Math.cos(angle)) * stageScale,
               y: box.top + (cy - rMid * Math.sin(angle)) * stageScale };
    }

    /* A drill-down may cover the whole chart rather than one category (the
     * runtime routes such a click to the category-less fallback). Demanding a
     * category here would fail that legitimate case with
     * "category-not-in-chart", so an undeclared category means "click inside
     * the plot area" and the middle band is as good as any. */
    const index = cat === undefined || cat === null || cat === ''
      ? Math.floor(categories.length / 2)
      : categories.findIndex(c => String(c) === String(cat));
    if (index < 0) return { error: 'category-not-in-chart', categories: categories.slice(0, 12) };
    const local = inst.convertToPixel({ xAxisIndex: 0 }, index);
    if (local === null || local === undefined || isNaN(local)) return null;
    /* convertToPixel works in the chart's own unscaled space; the stage is CSS
     * scaled, so the viewport coordinate needs the same factor applied. */
    return { x: box.left + local * stageScale, y: box.top + box.height / 2 };
  }, { id: chartId, cat: category });
}

/* Compare what the page SHOWS against the oracle.
 *
 * Everything else in the oracle chain compares one computation to another: the
 * runtime's numbers against Python's numbers. Both can be right while the page
 * prints something else entirely — twelve heat-map cells were rewritten to 999
 * and all 110 checks stayed green, because nothing had ever read the rendered
 * text. Computation and display are different artifacts; only the second one
 * is delivered. */
async function compareRenderedValues(page, checks, oracle, label, spec) {
  const shown = await page.evaluate(() => {
    const digits = node => {
      const raw = (node.textContent || '').replace(/[,\s]/g, '');
      const match = raw.match(/-?\d+(?:\.\d+)?/);
      return match ? Number(match[0]) : null;
    };
    const cells = [...document.querySelectorAll('[data-heatmap-cell][data-drilldown-id]')]
      .map(cell => ({ drilldownId: cell.getAttribute('data-drilldown-id'), value: digits(cell),
        x: cell.getAttribute('data-cell-x'), y: cell.getAttribute('data-cell-y'),
        chartId: cell.closest('[data-chart-id],[data-chart]')?.getAttribute('data-chart-id')
          || cell.closest('[data-chart-id],[data-chart]')?.getAttribute('data-chart') || null }));
    const metrics = [...document.querySelectorAll('[data-metric-id]')]
      .map(node => ({ metricId: node.getAttribute('data-metric-id'), value: digits(node) }));
    return { cells, metrics };
  });

  /* Where the cell's truth comes from depends on what the matrix measures.
   * Member count is the value only for a counting heat-map; an attainment-rate
   * grid needs its own declared numbers. Comparing a rate against a record
   * count would have both sides confidently agreeing on the wrong thing. */
  const chartById = new Map((spec?.charts || []).map(c => [c.id, c]));
  const cellMismatches = shown.cells
    .map(cell => {
      const chart = chartById.get(cell.chartId) || {};
      const declared = (chart.cells || [])
        .find(entry => String(entry.x) === cell.x && String(entry.y) === cell.y);
      /* Priority matters, and it was backwards. Where the oracle has authority
       * — a counting heat-map — it wins outright, and a declared cells[] entry
       * may only agree with it. Letting the spec override the oracle would mean
       * a wrong number in the spec silently becomes the expected number, and
       * the page matching that wrong number counts as a pass. */
      const oracleCount = (oracle.drilldowns || {})[cell.drilldownId];
      const isCount = (chart.aggregation || {}).function === 'count';
      if (isCount) {
        if (!oracleCount || typeof oracleCount.expected_count !== 'number') return null;
        const truth = oracleCount.expected_count;
        if (declared && Number(declared.value) !== truth) {
          return { ...cell, expected: truth, declared: declared.value, source: 'oracle.count',
            reason: 'chart.cells[] contradicts the oracle; the oracle is authoritative for a counting heat-map' };
        }
        return cell.value === truth ? null : { ...cell, expected: truth, source: 'oracle.count' };
      }
      if (declared !== undefined && declared !== null) {
        const want = Number(declared.value);
        return isFinite(want) && cell.value === want
          ? null : { ...cell, expected: declared.value, source: 'spec.cells' };
      }
      // 非 count 口径又没有声明值：没有真值可比，不能默认放行。
      return { ...cell, expected: null, source: 'none',
        reason: 'non-count heat-map must declare chart.cells[] values; nothing to compare against' };
    })
    .filter(Boolean);
  if (shown.cells.length) {
    assert(checks, `${label}: rendered cell values match the oracle`, cellMismatches.length === 0,
      { checked: shown.cells.length, offenders: cellMismatches.slice(0, 8) });
  }

  const metricMismatches = shown.metrics
    .map(metric => {
      const expected = (oracle.metrics || {})[metric.metricId];
      if (!expected || typeof expected.expected !== 'number' || metric.value === null) return null;
      const tolerance = Math.max(Math.abs(expected.expected) * 1e-9, 1e-6);
      return Math.abs(metric.value - expected.expected) <= tolerance
        ? null : { ...metric, expected: expected.expected };
    })
    .filter(Boolean);
  if (shown.metrics.length) {
    assert(checks, `${label}: rendered metric values match the oracle`, metricMismatches.length === 0,
      { checked: shown.metrics.length, offenders: metricMismatches.slice(0, 8) });
  }
}

async function inspectPage(browser, config, viewport, label) {
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
  const runtimeErrors = [];
  /* A page error carries no frame, so it is attributed by phase instead.
   * Everything the report does on its own — loading, mounting, paging through
   * every slide — happens before any drill opens third-party content. An error
   * raised only after that belongs to the embedded surface; one raised before
   * is the report's own and stays a hard failure. Verified against this deck:
   * a full pass over all ten slides with no drill produces zero page errors. */
  let interactionPhase = 'own';
  page.on('pageerror', error => {
    const entry = `pageerror: ${error.message}`;
    (interactionPhase === 'own' ? runtimeErrors : afterDrillErrors).push(entry);
  });
  /* Console output carries a source location, and an embedded record page
   * logs its own failures through the same channel as the report. Without
   * attributing by origin, a third-party sign-in page's policy warnings and
   * refused connections were charged to a report that did nothing wrong. */
  page.on('console', message => {
    if (message.type() !== 'error') return;
    const from = (message.location && message.location().url) || '';
    const ownPage = !from || from.startsWith('file://');
    /* Remote-origin console output is only excusable once we know the page's
     * frames really are the declared record surface — an iframe the report
     * never declared gets no such benefit. Classification is deferred to the
     * end, where that fact is available. */
    (ownPage ? runtimeErrors : remoteConsole).push(`console: ${message.text()}`);
  });
  /* Attribution needs structure, not a substring of an error message. Whether a
   * 401 means "a signed-in human must look" or "this report is broken" depends
   * entirely on WHAT failed: a record embedded in a sub-frame is expected to be
   * auth-gated; the page's own script or image is not. Classifying by the text
   * alone certified every 401 as someone else's problem. */
  const authGated = [];
  const embeddedErrors = [];
  const remoteConsole = [];
  const afterDrillErrors = [];
  const maybeRecordFrames = [];
  const failedLoads = [];
  page.on('response', response => {
    const status = response.status();
    /* 404/500 never fire requestfailed, so capturing only 401/403 meant a
     * missing or broken resource entered neither bucket and vanished. */
    if (status < 400) return;
    const request = response.request();
    /* Attribution follows the FRAME the request came from, not its resource
     * type. A record frame that redirects to a sign-in page issues all its
     * subsequent XHRs from inside that frame; keying on `document` sent those
     * to the page's own bucket and failed a perfectly good report three ways.
     * The frame is the unit of ownership — everything it loads is its. */
    const record = { url: response.url().slice(0, 120), status,
      resourceType: request.resourceType(), subframe: request.frame() !== page.mainFrame() };
    /* Only a sub-frame document that the spec actually expects to embed a
     * record counts as "a human must sign in". Any other iframe on the page is
     * not covered by that promise, so it stays a hard failure. */
    /* Sub-frame alone is too weak a signal: any iframe the page happens to
     * contain would be excused. A record frame is one that the drill component
     * actually mounted, so the URL has to appear inside .avd-root. Whether it
     * is auth-gated is decided later, once the DOM can be inspected. */
    (record.subframe ? maybeRecordFrames : failedLoads).push(record);
  });
  page.on('requestfailed', request => {
    const failure = request.failure();
    const record = { url: request.url().slice(0, 120), resourceType: request.resourceType(),
      error: failure && failure.errorText, subframe: request.frame() !== page.mainFrame() };
    (record.subframe ? maybeRecordFrames : failedLoads).push(record);
  });
  await page.goto(`file://${config.html}`, { waitUntil: 'load' });
  /* Font metrics decide the legibility gate, so measuring before webfonts
   * settle would score a fallback face instead of the shipped one. */
  await page.evaluate(() => (document.fonts ? document.fonts.ready : null)).catch(() => {});
  await page.waitForTimeout(1200);

  const checks = [];
  const base = await page.evaluate(() => {
    /* A DOM heat-map carries data-chart-id but is deliberately not an ECharts
     * instance — counting it here would make "every chart initialised" fail for
     * exactly the rendering we require. */
    const chartEls = Array.from(document.querySelectorAll('[data-chart-id],.chart,.chart-wide,.present-chart'))
      .filter(el => !el.querySelector('[data-heatmap-cell]'));
    const instances = window.echarts
      ? chartEls.filter(element => window.echarts.getInstanceByDom(element)).length
      : null;
    return {
      title: document.title,
      bodyText: document.body.innerText,
      chapters: document.querySelectorAll('.reading-chapter,.reading-section').length,
      activeChapters: document.querySelectorAll('.reading-chapter.active,.reading-section.active').length,
      slides: document.querySelectorAll('.slide').length,
      activeSlides: document.querySelectorAll('.presentation-root.open .slide.active').length,
      charts: chartEls.length,
      chartInstances: instances,
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth,
    };
  });
  assert(checks, `${label}: title`, Boolean(base.title.trim()), base.title);
  /* Runtime errors are judged at the very end of the run, not here: page
   * handlers keep pushing into runtimeErrors long after this point, and an
   * assertion taken now freezes `passed` while the evidence array keeps
   * growing — which is how a report shipped reporting "no runtime errors"
   * while carrying fourteen of them in its own evidence. */
  assert(checks, `${label}: chart initialization`, base.chartInstances === null || base.chartInstances === base.charts, `${base.chartInstances}/${base.charts}`);

  if (!config.preview && label === 'desktop') {
    // API-first mode: runtime-equipped reports expose window.__visualReport;
    // legacy reports fall through to the DOM checks below unchanged.
    const snapshot = await page.evaluate(() => {
      if (!window.__visualReport || !window.__visualReport.ready) return null;
      try { return window.__visualReport.verificationSnapshot(); } catch (error) { return { error: String(error && error.message) }; }
    });
    if (snapshot) {
      assert(checks, `${label}: runtime verification API`, !snapshot.error, snapshot.error);
      /* Compare the declared fingerprint against the bytes actually shipped,
       * not against another declaration of the same number. */
      const declared = (snapshot.fingerprints || {}).runtime_asset_sha256;
      const actual = inlinedRuntimeHash(config.html);
      if (declared || actual) {
        assert(checks, `${label}: declared runtime hash matches the inlined runtime`,
          Boolean(actual) && actual === declared,
          { declared: declared || null, actualInlined: actual || null,
            note: actual ? undefined : 'no <script data-inlined="runtime"> block found in the HTML' });
      }
      if (config.oracle && !snapshot.error) {
        compareWithOracle(checks, snapshot, config.oracle);
        await compareRenderedValues(page, checks, config.oracle, label, config.spec);
      }
    } else if (config.oracle) {
      assert(checks, `${label}: runtime API required by oracle`, false,
        'window.__visualReport not found — cannot verify a legacy report against an oracle');
    }
    /* Legibility and density are scored only on the canonical desktop viewport:
     * the fixed 16:9 stage shrinks on a phone by design, so applying displayed
     * font floors there would fail every conforming deck. */
    await inspectRenderedState(page, config, checks, label, config.screenshots);
  }

  if (config.preview) {
    const preview = await page.evaluate(() => {
      const stage = document.querySelector('#deckStage,.deck-stage,.preview-stage,.slide') || document.body.firstElementChild;
      const rect = stage?.getBoundingClientRect();
      return {
        stageExists: Boolean(stage && rect && rect.width && rect.height),
        ratio: rect && rect.height ? rect.width / rect.height : null,
        slideCount: document.querySelectorAll('.slide').length,
        drillRoots: document.querySelectorAll('.avd-root,[data-drilldown],.drilldown-modal').length,
        iframes: document.querySelectorAll('iframe').length,
        interactiveTriggers: document.querySelectorAll('[data-open],[data-action*="drill"],[onclick*="drill" i]').length,
        actionButtons: document.querySelectorAll('button,a[role="button"]').length,
        bodyText: document.body.innerText,
        scrollWidth: document.documentElement.scrollWidth,
        scrollHeight: document.documentElement.scrollHeight,
        innerWidth,
        innerHeight,
      };
    });
    const forbiddenHints=['点击查看','查看明细','打开明细','下钻','原始记录'];
    assert(checks, `${label}: preview stage exists`, preview.stageExists, preview);
    assert(checks, `${label}: preview is fixed 16:9`, preview.ratio != null && Math.abs(preview.ratio - 16/9) < 0.02, preview.ratio);
    assert(checks, `${label}: preview is one page`, preview.slideCount <= 1, preview.slideCount);
    assert(checks, `${label}: preview has no drill-down`, preview.drillRoots === 0, preview.drillRoots);
    assert(checks, `${label}: preview has no iframe`, preview.iframes === 0, preview.iframes);
    assert(checks, `${label}: preview has no drill trigger`, preview.interactiveTriggers === 0, preview.interactiveTriggers);
    assert(checks, `${label}: preview has no fake action controls`, preview.actionButtons === 0, preview.actionButtons);
    assert(checks, `${label}: preview has no drill hint`, forbiddenHints.every(text=>!preview.bodyText.includes(text)), forbiddenHints.filter(text=>preview.bodyText.includes(text)));
    if (label === 'desktop') assert(checks, `${label}: preview has no overflow`, preview.scrollWidth <= preview.innerWidth + 1 && preview.scrollHeight <= preview.innerHeight + 1, preview);
    if (config.screenshots) {
      fs.mkdirSync(config.screenshots,{recursive:true});
      await page.screenshot({path:path.join(config.screenshots,`${label}.png`),fullPage:false});
    }
    await page.close();
    return {label,viewport,checks,manual_required:manualRequiredNames(checks)};
  }
  if (label === 'phone' && config.spec?.modes?.reading?.enabled) {
    assert(checks, `${label}: no horizontal overflow`, base.scrollWidth <= base.innerWidth + 1, `${base.scrollWidth}/${base.innerWidth}`);
  }

  if (config.spec?.modes?.reading?.enabled) {
    assert(checks, `${label}: continuous reading explicitly requested`, config.spec.modes.reading.requested_by_user === true, config.spec.modes.reading);
    assert(checks, `${label}: reading content exists`, base.chapters > 0, base.chapters);
  }

  const forbidden = config.spec?.validation?.forbidden_text || [];
  for (const text of forbidden) {
    assert(checks, `${label}: forbidden text absent`, !base.bodyText.includes(text), text);
  }

  const presentButton = page.locator('#presentModeBtn,[data-action="open-presentation"]').first();
  const hasStage = await page.locator('#deckStage,.deck-stage').count();
  if (config.spec?.modes?.presentation?.enabled && hasStage) {
    if (await presentButton.count()) {
      await presentButton.click();
      await page.waitForTimeout(350);
    }
    const presentation = await page.evaluate(() => {
      const stage = document.querySelector('#deckStage,.deck-stage');
      if (!stage) return { exists: false };
      const rect = stage.getBoundingClientRect();
      const root = document.querySelector('#presentationRoot,.presentation-root');
      return {
        exists: true,
        open: root ? Boolean(root.classList.contains('open') || root.getAttribute('aria-hidden') === 'false') : true,
        ratio: rect.width / rect.height,
        within: rect.left >= -0.5 && rect.top >= -0.5 && rect.right <= innerWidth + 0.5 && rect.bottom <= innerHeight + 0.5,
        slides: document.querySelectorAll('.slide').length,
        active: document.querySelectorAll('.slide.active').length,
      };
    });
    assert(checks, `${label}: presentation opens`, presentation.exists && presentation.open, presentation);
    assert(checks, `${label}: fixed 16:9 stage`, presentation.exists && Math.abs(presentation.ratio - 16 / 9) < 0.01, presentation.ratio);
    assert(checks, `${label}: stage inside viewport`, presentation.within, presentation);
    assert(checks, `${label}: one active slide`, presentation.slides === 0 || presentation.active === 1, presentation);

    if (label === 'desktop') {
      const layout = await page.evaluate(async () => {
        const slides = Array.from(document.querySelectorAll('.slide'));
        const issues = [];
        for (let index = 0; index < slides.length; index++) {
          if (window.__visualReport?.showSlide) window.__visualReport.showSlide(index);
          else if (window.__xyPresentation?.showSlide) window.__xyPresentation.showSlide(index);
          else {
            slides.forEach((slide, i) => slide.classList.toggle('active', i === index));
          }
          await new Promise(resolve => setTimeout(resolve, 60));
          const slide = slides[index];
          // Theme-agnostic overflow check: in-flow content that exceeds the
          // slide box shows up in scroll dimensions even under overflow:hidden.
          // Never rely on guessed theme class names — a theme that doesn't use
          // them must not silently skip this check.
          if (slide.scrollHeight > slide.clientHeight + 2 || slide.scrollWidth > slide.clientWidth + 2) {
            issues.push(index + 1);
            continue;
          }
          const box = slide.getBoundingClientRect();
          const content = slide.querySelector('.slide-inner,.cover-layout,.slide-content');
          if (!content) continue;
          const inner = content.getBoundingClientRect();
          if (inner.left < box.left - 1 || inner.top < box.top - 1 || inner.right > box.right + 1 || inner.bottom > box.bottom + 1) {
            issues.push(index + 1);
          }
        }
        return issues;
      });
      assert(checks, `${label}: slide content within stage`, layout.length === 0, layout);
    }
  }

  const nonAggregateDrills=(config.spec?.drilldowns||[]).filter(item=>item.mode!=='aggregate_only');
  if (label === 'desktop' && nonAggregateDrills.length) {
    const drillStructure = await page.evaluate(() => {
      const root = document.querySelector('.avd-root');
      const stage = document.querySelector('#deckStage,.deck-stage');
      return {
        exists: Boolean(root),
        outsideStage: Boolean(root && stage && !stage.contains(root)),
        hasList: Boolean(root?.querySelector('.avd-list-view')),
        hasDetail: Boolean(root?.querySelector('.avd-detail-view')),
      };
    });
    assert(checks, 'drill: standard component exists', drillStructure.exists, drillStructure);
    assert(checks, 'drill: component mounted outside fixed stage', drillStructure.outsideStage, drillStructure);
    assert(checks, 'drill: list and detail levels exist', drillStructure.hasList && drillStructure.hasDetail, drillStructure);
  }

  const drills = config.spec?.validation?.browser?.drills || [];
  const drillById = new Map((config.spec?.drilldowns || []).map(d => [d.id, d]));

  /* A heat-map cell is addressed by two dimensions (region x month), which a
   * single string `category` cannot express, and an ECharts canvas gives no
   * per-cell element to click or to check for obstruction. Rendering the grid
   * as DOM cells makes every cell a real target with its own hit area and its
   * own filter — the existing machinery then covers it with no new trigger
   * shape. So: heat-maps are DOM, and a canvas one is rejected here rather
   * than silently shipping cells nobody can verify. */
  /* The requirement is per-cell addressability, not a ban on a library. A
   * canvas gives no element to click, measure or check for obstruction, so a
   * heat-map whose cells are meant to be drillable must expose real elements —
   * DOM or SVG, either is fine. A display-only heat-map that has explicitly
   * opted out of drill-down has nothing to address and may stay canvas. */
  const interactiveHeatmaps = (config.spec?.charts || [])
    .filter(c => c.type === 'heatmap' && c.drilldown_required !== false)
    .map(c => c.id);
  if (label === 'desktop' && interactiveHeatmaps.length) {
    const cellReport = await page.evaluate(ids => ids.map(id => {
      const el = document.querySelector(`[data-chart-id="${id}"],[data-chart="${id}"]`);
      if (!el) return { id, found: false };
      const cells = el.querySelectorAll('[data-heatmap-cell]');
      const svgCells = el.querySelectorAll('svg [data-cell-x][data-cell-y], svg rect[data-heatmap-cell]');
      return { id, found: true, cells: cells.length + svgCells.length,
        addressable: (cells.length + svgCells.length) > 0 };
    }), interactiveHeatmaps);
    const unaddressable = cellReport.filter(r => !r.addressable);
    assert(checks, 'chart: drillable heat-map cells are individually addressable',
      unaddressable.length === 0,
      { offenders: unaddressable,
        rule: 'a drillable heat-map needs one element per cell (data-heatmap-cell, or SVG cells '
          + 'carrying data-cell-x/data-cell-y); pure canvas offers no per-cell hit area. '
          + 'A display-only heat-map may stay canvas with drilldown_required:false.' });

    /* Addressable is necessary but far from sufficient. A grid can be missing a
     * cell, repeat a coordinate, or carry a filter that constrains one field
     * twice — each renders a plausible-looking matrix whose cells do not mean
     * what the axes claim. The spec is the contract; the DOM must match it
     * cell for cell, both directions. */
    const declaredCells = {};
    const astProblems = [];
    for (const drill of (config.spec?.drilldowns || [])) {
      const trigger = drill.trigger || {};
      if (trigger.type !== 'chart' || !interactiveHeatmaps.includes(trigger.ref_id)) continue;
      const ast = (drill.membership || {}).filter_ast || {};
      const eqs = (ast.op === 'and' ? ast.children || [] : []).filter(c => c && c.op === 'eq');
      if (eqs.length !== 2) {
        astProblems.push({ id: drill.id, reason: `expected two eq clauses, found ${eqs.length}` });
        continue;
      }
      if (eqs[0].field === eqs[1].field) {
        astProblems.push({ id: drill.id, reason: `both clauses constrain "${eqs[0].field}"; a cell needs two dimensions` });
        continue;
      }
      (declaredCells[trigger.ref_id] = declaredCells[trigger.ref_id] || []).push(
        { id: drill.id, x: String(eqs[0].value), y: String(eqs[1].value) });
    }
    assert(checks, 'chart: heat-map cell filters constrain two distinct fields',
      astProblems.length === 0, { offenders: astProblems });

    const gridMatch = await page.evaluate(declared => Object.entries(declared).map(([id, cells]) => {
      const el = document.querySelector(`[data-chart-id="${id}"],[data-chart="${id}"]`);
      const dom = [...(el ? el.querySelectorAll('[data-heatmap-cell]') : [])]
        .map(c => `${c.getAttribute('data-cell-x')}|${c.getAttribute('data-cell-y')}`);
      const want = cells.map(c => `${c.x}|${c.y}`);
      const domSet = new Set(dom);
      return { id,
        missingInDom: want.filter(k => !domSet.has(k)),
        extraInDom: dom.filter(k => !want.includes(k)),
        duplicates: dom.filter((k, i) => dom.indexOf(k) !== i) };
    }), declaredCells);
    const gridProblems = gridMatch.filter(g =>
      g.missingInDom.length || g.extraInDom.length || g.duplicates.length);
    assert(checks, 'chart: heat-map grid matches its declared cells',
      gridProblems.length === 0, { offenders: gridProblems });

    /* Coordinates and wiring can disagree without either looking wrong on its
     * own: the label says (A, M1) while the drill-down bound to it filters for
     * (A, M2). The set of coordinates still matches, the cell is still
     * addressable — but clicking it opens another cell's records. Each cell's
     * own label must equal the filter it will run. */
    const wiring = await page.evaluate(expected => {
      const out = [];
      document.querySelectorAll('[data-heatmap-cell][data-drilldown-id]').forEach(cell => {
        const id = cell.getAttribute('data-drilldown-id');
        const want = expected[id];
        if (!want) { out.push({ id, reason: 'cell points at an undeclared drilldown' }); return; }
        const x = cell.getAttribute('data-cell-x'), y = cell.getAttribute('data-cell-y');
        if (String(want.x) !== String(x) || String(want.y) !== String(y))
          out.push({ id, labelled: `${x}|${y}`, filters: `${want.x}|${want.y}` });
      });
      return out;
    }, Object.fromEntries(Object.values(declaredCells).flat().map(c => [c.id, { x: c.x, y: c.y }])));
    assert(checks, 'chart: heat-map cell labels match the filter they run',
      wiring.length === 0, { offenders: wiring.slice(0, 8) });
  }

  /* Contract 1.1 moved axis-chart activation from the series click to the plot
   * grid. Driving a 1.0 page with the 1.1 click model produces clicks that land
   * nowhere, and the failure surfaces 30 seconds later as an unrelated timeout
   * on the close button. Check the version first and say so plainly. */
  const MIN_RUNTIME_CONTRACT = '1.1';
  const pageContract = await page.evaluate(() =>
    (window.__visualReport && window.__visualReport.contractVersion) || null);
  /* Semantic compare, not parseFloat: numerically 1.10 < 1.9, and a future 2.0
   * is not automatically compatible with a validator written for 1.x — a major
   * bump is exactly where the click model may change again. */
  const contractOk = (() => {
    if (pageContract === null) return false;
    const [pMajor, pMinor] = String(pageContract).split('.').map(n => parseInt(n, 10) || 0);
    const [rMajor, rMinor] = MIN_RUNTIME_CONTRACT.split('.').map(n => parseInt(n, 10) || 0);
    return pMajor === rMajor && pMinor >= rMinor;
  })();
  if (label === 'desktop' && drills.length) {
    assert(checks, 'drill: page runtime meets the validator contract', contractOk,
      { page: pageContract, required: `>= ${MIN_RUNTIME_CONTRACT}`,
        note: 'regenerate the report with the current runtime; its chart click model differs' });
  }

  if (label === 'desktop' && contractOk) {
    const declared=new Set(nonAggregateDrills.map(item=>item.id));
    const covered=new Set(drills.map(item=>item.drilldown_id).filter(Boolean));
    const missing=[...declared].filter(id=>!covered.has(id));
    assert(checks,'drill: every non-aggregate trigger has a browser case',missing.length===0,{declared:[...declared],covered:[...covered],missing});
    interactionPhase = 'drills';
    for (const test of drills) {
      /* Start each case from a known state. The cases share one page, so a
       * drill left open by an earlier failure would still be on screen when
       * the next case measures its modal — turning one real failure into a
       * run of misleading ones, with the true cause buried. */
      const dirty = await page.evaluate(() => {
        const root = document.querySelector('.avd-root');
        if (!root || !root.classList.contains('avd-open')) return false;
        const close = root.querySelector('.avd-close');
        if (close) close.click();
        return true;
      });
      if (dirty) {
        await page.waitForTimeout(150);
        const stillOpen = await page.evaluate(() =>
          Boolean(document.querySelector('.avd-root.avd-open')));
        assert(checks, `drill: state reset before ${test.name || test.drilldown_id}`, !stillOpen,
          { reason: 'a previous drill-down stayed open; results after this point would be unreliable' });
        if (stillOpen) break;
      }
      // A drill case may declare which slide (0-based) its trigger lives on;
      // the validator navigates there first, so triggers no longer need to be
      // duplicated onto the last visible page just to be clickable.
      if (test.slide != null) {
        await page.evaluate(index => {
          if (window.__visualReport?.showSlide) window.__visualReport.showSlide(index);
        }, test.slide);
        await page.waitForTimeout(200);
      }
      /* The declared trigger — not the supplied selector — decides where to
       * click. For an axis chart the point is computed from the chart's own
       * axis, so an off-chart chip cannot stand in for it. */
      const declaredTrigger = (drillById.get(test.drilldown_id) || {}).trigger || {};
      let clicked = 'selector';
      if (declaredTrigger.type === 'chart' && declaredTrigger.ref_id) {
        const point = await chartClickPoint(page, declaredTrigger.ref_id,
          declaredTrigger.category !== undefined ? declaredTrigger.category : test.category);
        if (point && point.error) {
          assert(checks, `drill: ${test.name || test.drilldown_id} category exists in chart`, false, point);
          continue;
        }
        if (point) { await page.mouse.click(point.x, point.y); clicked = 'chart-geometry'; }
      }
      if (clicked === 'selector') {
        if (declaredTrigger.type === 'chart') {
          /* Axis geometry should have produced a point. Falling through here
           * means the chart is item geometry (pie/donut) — allowed — or the
           * chart could not be found, which is itself worth recording. */
          const inside = await page.evaluate(({ sel, id }) => {
            const t = document.querySelector(sel);
            const c = document.querySelector(`[data-chart-id="${id}"],[data-chart="${id}"]`);
            return Boolean(t && c && c.contains(t));
          }, { sel: test.trigger, id: declaredTrigger.ref_id });
          assert(checks, `drill: ${test.name || test.drilldown_id} is triggered from its own chart`,
            inside, { selector: test.trigger, chart: declaredTrigger.ref_id,
              note: 'a chart drill-down must be opened from the chart, not from a separate control' });
        }
        /* A trigger that cannot be clicked — covered by an overlay, given
         * pointer-events:none, or shrunk to a couple of pixels — is a finding
         * about the report, not a reason to abort the run with a stack trace.
         * Playwright's default 30s wait would end the whole validation and
         * report nothing at all. */
        try {
          await page.locator(test.trigger).first().click({ timeout: 3000 });
        } catch (error) {
          assert(checks, `drill: ${test.name || test.drilldown_id} trigger is clickable`, false,
            { trigger: test.trigger,
              reason: 'trigger never became clickable — covered, disabled, or too small' });
          continue;
        }
      }
      await page.waitForTimeout(180);
      const state = await page.evaluate(({ modal, rows }) => ({
        /* Walk the ancestor chain: a modal with opacity:1 inside a container
         * faded to 0 is invisible to the reader but looked "visible" when only
         * its own computed style was consulted. */
        visible: (() => {
          const node = document.querySelector(modal);
          if (!node) return false;
          let opacity = 1, p = node;
          while (p && p !== document.body) {
            const cs = getComputedStyle(p);
            if (cs.display === 'none' || cs.visibility === 'hidden') return false;
            opacity *= parseFloat(cs.opacity);
            p = p.parentElement;
          }
          return opacity > 0.05;
        })(),
        rows: document.querySelectorAll(rows).length,
      }), test);
      assert(checks, `drill: ${test.name || test.trigger}`, state.visible && (test.expected_count == null || state.rows === test.expected_count), state);
      if(test.open_row){
        await page.locator(test.open_row).first().click();await page.waitForTimeout(180);
        const detail=await page.evaluate(test=>({
          iframeSrc:test.iframe?document.querySelector(test.iframe)?.getAttribute('src')||'':null,
          backVisible:test.back?Boolean(document.querySelector(test.back))&&!document.querySelector(test.back).hidden:null,
          forbiddenVisible:(test.hidden_selectors||[]).filter(selector=>{const node=document.querySelector(selector);return node&&!node.hidden&&getComputedStyle(node).display!=='none';}),
        }),test);
        if(test.expect_iframe)assert(checks,`drill: ${test.name||test.trigger} opens real record`,Boolean(detail.iframeSrc),detail);
        if(test.back)assert(checks,`drill: ${test.name||test.trigger} has back`,detail.backVisible,detail);
        assert(checks,`drill: ${test.name||test.trigger} hides duplicate chrome`,detail.forbiddenVisible.length===0,detail);
        if(test.back)await page.locator(test.back).first().click();
      }
      /* A short timeout with a named failure. The default 30s wait on an
       * invisible close button says "timeout" when the real fact is that the
       * drill-down never opened — the run dies with a stack trace instead of a
       * finding. */
      if (test.close) {
        try {
          await page.locator(test.close).first().click({ timeout: 3000 });
        } catch (error) {
          assert(checks, `drill: ${test.name || test.drilldown_id} can be closed`, false,
            { close: test.close, reason: 'close control never became clickable — the drill-down likely never opened' });
        }
      }
    }
  }

  if (config.screenshots) {
    fs.mkdirSync(config.screenshots, { recursive: true });
    await page.screenshot({ path: path.join(config.screenshots, `${label}.png`), fullPage: false });
  }
  /* Final tally, split by who owns the failure.
   *
   * A drill-down that embeds a real record loads a third-party page the
   * validator is not signed in to, so a 401/403 there is the expected shape of
   * "this needs a logged-in human", not a defect in the report. Counting it as
   * a hard error makes every truthful full-mode report fail; ignoring it would
   * hide genuine load failures. It is exactly the third state. */
  /* A console line for an auth-gated sub-frame document is already accounted
   * for by `authGated`, so drop it from the raw error list to avoid counting
   * the same event as both a defect and a manual check. */
  /* Now that the run is over, ask the page which frames the drill component
   * actually mounted. Only those, and only when a drill case declared
   * expect_iframe, are someone-must-sign-in; every other frame failure is the
   * report loading something it never promised. */
  const frameSurvey = await page.evaluate(() => {
    const all = [...document.querySelectorAll('iframe')];
    return { total: all.length, outsideDrill: all.filter(f => !f.closest('.avd-root')).length };
  });
  const declaresIframe = (config.spec?.validation?.browser?.drills || []).some(d => d.expect_iframe);
  /* Every iframe on the page belongs to the drill component, and the spec says
   * a record is meant to be embedded there — so a sub-frame that cannot
   * authenticate is a sign-in problem, whatever it was fetching. If any iframe
   * sits outside the drill component, ownership is ambiguous and nothing is
   * excused; `no undeclared embedded frames` reports that separately. */
  const allFramesAreRecordFrames = frameSurvey.total > 0 && frameSurvey.outsideDrill === 0;
  const looksLikeAuth = record =>
    record.status === 401 || record.status === 403 || /login|oauth2|sso|challenge/i.test(record.url);
  for (const record of maybeRecordFrames) {
    if (declaresIframe && allFramesAreRecordFrames && looksLikeAuth(record)) authGated.push(record);
    else failedLoads.push(record);
  }

  const authUrls = new Set(authGated.map(a => a.url));
  const recordSurface = declaresIframe && allFramesAreRecordFrames;
  // 下钻后才出现的错误，只有在确实存在记录 frame 时才归到内嵌一侧。
  if (recordSurface) {
    embeddedErrors.push(...afterDrillErrors, ...remoteConsole);
  } else {
    runtimeErrors.push(...afterDrillErrors, ...remoteConsole);
  }
  const ownErrors = runtimeErrors.filter(e =>
    !(authGated.length && /Failed to load resource/i.test(e) && /\b(401|403)\b/.test(e)));
  assert(checks, `${label}: runtime errors`, ownErrors.length === 0, ownErrors);

  /* Everything that failed to load and is NOT an expected auth-gated record
   * frame is the report's own problem: a 401 on its own script or image means
   * the page is broken, not that a human needs to sign in. */
  const ownFailedLoads = failedLoads.filter(f => !f.subframe);
  assert(checks, `${label}: own resources load`, ownFailedLoads.length === 0,
    { count: ownFailedLoads.length, sample: ownFailedLoads.slice(0, 4) });

  /* Every sub-frame failure that did not qualify as an expected sign-in must
   * still land somewhere. Excluding them from the page's own bucket while the
   * frame checks below only looked at documents let non-document sub-frame
   * failures fall out of both and disappear — the exact silent gap this file
   * keeps having to close. */
  const leftoverSubframe = failedLoads.filter(f => f.subframe);

  /* A sub-frame document that failed for a NON-auth reason (DNS, connection
   * refused, blocked) was excluded from the hard bucket but never entered the
   * manual one — it escaped both and vanished. Anything that neither passed nor
   * was explicitly deferred is exactly the silent gap this whole exercise keeps
   * finding. */
  const subframeFailures = leftoverSubframe;
  /* Three different facts were being folded into one bucket. Separating them
   * keeps each failure's name equal to what actually went wrong:
   *  - auth failure on a frame the spec never promised to embed → the page is
   *    loading something it did not declare;
   *  - anything else on a sub-frame → the source is unreachable, which is a
   *    broken link, not a sign-in prompt. */
  const undeclaredFrames = subframeFailures.filter(f => f.status === 401 || f.status === 403);
  const unreachableFrames = subframeFailures.filter(f => !(f.status === 401 || f.status === 403));
  assert(checks, `${label}: no undeclared embedded frames`, undeclaredFrames.length === 0,
    { count: undeclaredFrames.length, sample: undeclaredFrames.slice(0, 4),
      note: 'an auth-gated frame is only a manual check when a drill case declares expect_iframe' });
  assert(checks, `${label}: embedded record frames reach their source`,
    unreachableFrames.length === 0,
    { count: unreachableFrames.length, sample: unreachableFrames.slice(0, 4),
      note: 'a record frame that cannot be reached at all is a broken link, not a sign-in prompt' });

  if (authGated.length || embeddedErrors.length) {
    checks.push({ name: `${label}: embedded record sources need a signed-in check`, passed: false,
      evidence: { manual_required: true, count: authGated.length,
        embeddedConsole: embeddedErrors.slice(0, 4), sample: authGated.slice(0, 4),
        note: 'auth-gated record frames cannot be verified headlessly; confirm them in a signed-in browser' } });
  }
  await page.close();
  return { label, viewport, checks, manual_required: manualRequiredNames(checks) };
}

(async () => {
  const config = args();
  if (!fs.existsSync(config.html)) throw new Error(`HTML not found: ${config.html}`);
  if (config.spec) config.spec = JSON.parse(fs.readFileSync(config.spec, 'utf8'));
  if (config.oracle) config.oracle = JSON.parse(fs.readFileSync(config.oracle, 'utf8'));
  const { chromium } = loadPlaywright();
  const launchOptions = { headless: true };
  const chrome = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  if (fs.existsSync(chrome)) launchOptions.executablePath = chrome;
  const browser = await chromium.launch(launchOptions);
  let runs;
  try {
    runs = [
      // Canonical desktop viewport. frontend-slides-engine.md requires 1280x720;
      // the font floors are displayed-pixel values measured at this size, so
      // changing it silently changes what "readable" means.
      await inspectPage(browser, config, CANONICAL_DESKTOP, 'desktop'),
      await inspectPage(browser, config, { width: 390, height: 844 }, 'phone'),
    ];
  } finally {
    await browser.close();
  }
  const checks = runs.flatMap(run => run.checks);
  const result = {
    /* manual_required is neither a pass nor a defect: it means the tooling
     * could not decide. It must not be silently folded into either bucket. */
    valid: checks.every(check => check.passed),
    status: (() => {
      const manual = manualRequiredNames(checks);
      const hard = checks.filter(c => !c.passed && !(c.evidence && c.evidence.manual_required === true));
      if (hard.length) return 'failed';
      return manual.length ? 'manual_required' : 'passed';
    })(),
    manual_required: manualRequiredNames(checks),
    mode: config.preview?'theme_preview':'formal_report',
    html: config.html,
    checked_at: new Date().toISOString(),
    passed: checks.filter(check => check.passed).length,
    failed: checks.filter(check => !check.passed).length,
    runs,
  };
  const text = JSON.stringify(result, null, 2);
  if (config.output) fs.writeFileSync(config.output, text + '\n');
  console.log(text);
  process.exit(result.valid ? 0 : 1);
})().catch(error => { console.error(error.stack || error); process.exit(1); });
