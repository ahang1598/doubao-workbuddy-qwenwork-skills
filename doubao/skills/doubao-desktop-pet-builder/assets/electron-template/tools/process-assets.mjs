import { access, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import sharp from 'sharp';
import { semanticCutout } from './semantic-cutout.mjs';

function argsOf(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 2) result[argv[index].replace(/^--/, '')] = argv[index + 1];
  return result;
}

const args = argsOf(process.argv.slice(2));
const inputDir = path.resolve(args.input ?? 'incoming-assets');
const outputDir = path.resolve(args.output ?? path.join('src', 'assets', 'pet'));
const trayDir = path.resolve(args.tray ?? path.join('src', 'assets', 'tray'));
const specPath = path.resolve(args.spec ?? 'pet-spec.json');
const spec = JSON.parse(await readFile(specPath, 'utf8'));
const backgroundMode = spec.assetPipeline?.backgroundMode;
const segmentationBackend = spec.assetPipeline?.segmentationBackend;
const subjectKind = spec.assetPipeline?.subjectKind;
const threshold = Number(spec.assetPipeline?.backgroundTolerance);
const feather = Number(spec.assetPipeline?.edgeFeather);
const safeMargin = Number(spec.assetPipeline?.safeMargin);
const targetOccupancy = Number(spec.assetPipeline?.targetOccupancy);
const generationBackground = spec.assetPipeline?.generationBackground;
if (backgroundMode !== 'semantic-cutout') throw new Error('pet-spec assetPipeline.backgroundMode must be semantic-cutout');
if (!['auto', 'apple-vision', 'rembg'].includes(segmentationBackend)) throw new Error('pet-spec segmentationBackend must be auto, apple-vision or rembg');
if (!['auto', 'illustration', 'photo'].includes(subjectKind)) throw new Error('pet-spec subjectKind must be auto, illustration or photo');
if (!['transparent-grid', 'solid-chroma'].includes(generationBackground)) throw new Error('pet-spec generationBackground must be transparent-grid or solid-chroma');
if (![threshold, feather, safeMargin, targetOccupancy].every(Number.isFinite)) throw new Error('pet-spec assetPipeline values must be numbers');

const selectedStateId = args.state;
const states = selectedStateId ? spec.states.filter((state) => state.id === selectedStateId) : spec.states;
if (selectedStateId && states.length !== 1) throw new Error(`Unknown asset state: ${selectedStateId}`);
const names = new Set(states.flatMap((state) => state.frames));
if (!selectedStateId) names.add(spec.character.coreAsset);
await mkdir(outputDir, { recursive: true });
await mkdir(trayDir, { recursive: true });

const reports = [];
const failures = [];
const extracted = new Map();
const semanticOutputDir = path.resolve('.build', 'semantic-cutouts');
const semanticCacheVersion = 'v2.2-lean-1';
let semanticCacheHits = 0;
let semanticRequests = 0;
const REPAIRS = {
  SUBJECT_TOUCHES_BORDER: 'The source is clipped. Regenerate this frame with the complete subject inside the canvas; padding cannot restore missing pixels.',
  SOLID_BLOCK: 'Semantic cutout did not isolate the subject. Retry with the correct subjectKind/backend or regenerate on a simple flat background.',
  SEGMENTATION_BACKEND_UNAVAILABLE: 'Use macOS 14+ Apple Vision or install the pinned rembg backend; do not bypass asset QA.',
  BACKGROUND_UNSTABLE: 'Regenerate with real transparency or one stable light simulated-transparency grid; do not change backgroundTolerance.',
  FOREGROUND_EMPTY: 'Regenerate from the confirmed core IP with a clearly separated complete subject.',
  NORMALIZATION_TOO_LARGE: 'Regenerate this state from the same core IP with a fixed camera, body scale, and foot baseline.',
  NORMALIZATION_OVERFLOW: 'Regenerate with consistent framing and more clear margin; do not shrink unrelated states.',
  ASSET_READ_FAILED: 'Restore the referenced source PNG or correct its exact case-sensitive path.',
  ASSET_PROCESSING_FAILED: 'Inspect the source frame and regenerate only this failed state if deterministic correction is unsafe.',
};

function diagnosticFrom(error) {
  const message = error instanceof Error ? error.message : String(error);
  const rawCode = error && typeof error === 'object' && 'code' in error ? error.code : undefined;
  const explicitCode = typeof rawCode === 'string' && REPAIRS[rawCode] ? rawCode : undefined;
  let code = explicitCode || 'ASSET_PROCESSING_FAILED';
  if (!explicitCode && rawCode === 'ENOENT') code = 'ASSET_READ_FAILED';
  if (!explicitCode && /touches the source border/i.test(message)) code = 'SUBJECT_TOUCHES_BORDER';
  else if (!explicitCode && /solid opaque block/i.test(message)) code = 'SOLID_BLOCK';
  else if (!explicitCode && /semantic cutout backend|segmentation backend/i.test(message)) code = 'SEGMENTATION_BACKEND_UNAVAILABLE';
  else if (!explicitCode && /border palette|background|gradient|color clusters|coverage/i.test(message)) code = 'BACKGROUND_UNSTABLE';
  else if (!explicitCode && /foreground is empty|subject is empty/i.test(message)) code = 'FOREGROUND_EMPTY';
  else if (!explicitCode && /normalized frame exceeds canvas/i.test(message)) code = 'NORMALIZATION_OVERFLOW';
  return { code, message, repair: REPAIRS[code] || REPAIRS.ASSET_PROCESSING_FAILED };
}

function codedError(code, message) {
  const error = new Error(message);
  error.code = code;
  return error;
}

function borderIndexes(width, height) {
  const result = [];
  for (let x = 0; x < width; x += 1) {
    result.push(x);
    if (height > 1) result.push((height - 1) * width + x);
  }
  for (let y = 1; y + 1 < height; y += 1) {
    result.push(y * width);
    if (width > 1) result.push(y * width + width - 1);
  }
  return result;
}

async function assertDecodableImage(name, file) {
  const bytes = await readFile(file);
  const head = bytes.subarray(0, 16);
  const hex = [...head].map((value) => value.toString(16).padStart(2, '0')).join(' ');
  const isPng = bytes.length >= 8 && head[0] === 0x89 && head[1] === 0x50 && head[2] === 0x4e && head[3] === 0x47;
  const isJpeg = bytes.length >= 3 && head[0] === 0xff && head[1] === 0xd8 && head[2] === 0xff;
  const isWebp = bytes.length >= 12 && head[0] === 0x52 && head[1] === 0x49 && head[2] === 0x46 && head[3] === 0x46
    && head[8] === 0x57 && head[9] === 0x45 && head[10] === 0x42 && head[11] === 0x50;
  if (bytes.length < 128 || (!isPng && !isJpeg && !isWebp)) {
    throw codedError(
      'ASSET_PROCESSING_FAILED',
      `${name}: not a decodable PNG/JPEG/WebP image (path: ${file}, bytes: ${bytes.length}, header: ${hex}). `
      + 'The source is likely a failed download placeholder (e.g. {} JSON, HTML, or an empty file); re-download or regenerate this frame.',
    );
  }
  return bytes;
}

function expectedCutoutBackend() {
  if (process.platform === 'darwin') {
    if (!['auto', 'apple-vision'].includes(segmentationBackend)) {
      throw codedError(
        'SEGMENTATION_BACKEND_UNAVAILABLE',
        `Configured backend ${segmentationBackend} conflicts with macOS; this lean route requires Apple Vision and will not fall back`,
      );
    }
    return 'apple-vision';
  }
  if (process.platform === 'win32') {
    if (!['auto', 'rembg'].includes(segmentationBackend)) {
      throw codedError(
        'SEGMENTATION_BACKEND_UNAVAILABLE',
        `Configured backend ${segmentationBackend} conflicts with Windows; this lean route requires controlled temporary rembg`,
      );
    }
    if (subjectKind === 'illustration') return 'rembg:isnet-anime';
    if (subjectKind === 'photo') return 'rembg:birefnet-general';
    return 'rembg:isnet-general-use';
  }
  throw codedError(
    'SEGMENTATION_BACKEND_UNAVAILABLE',
    `Semantic cutout supports macOS and Windows, not ${process.platform}`,
  );
}

async function extractForeground(name) {
  const originalSource = path.join(inputDir, name);
  const originalBytes = await assertDecodableImage(name, originalSource);
  const original = await sharp(originalSource).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  const originalPixels = original.info.width * original.info.height;
  let nonOpaquePixels = 0;
  for (let index = 0; index < originalPixels; index += 1) {
    if (original.data[index * 4 + 3] < 250) nonOpaquePixels += 1;
  }

  let source = originalSource;
  let semantic = {
    requested: false,
    backend: nonOpaquePixels / originalPixels >= 0.005 ? 'existing-alpha' : undefined,
    attempts: [],
    cached: false,
  };
  if (!semantic.backend) {
    semanticRequests += 1;
    const expectedBackend = expectedCutoutBackend();
    const cacheKey = createHash('sha256')
      .update(originalBytes)
      .update(`\0${semanticCacheVersion}\0${process.platform}\0${segmentationBackend}\0${subjectKind}`)
      .digest('hex')
      .slice(0, 24);
    const semanticOutput = path.join(semanticOutputDir, cacheKey, name);
    let cached = false;
    try {
      await access(semanticOutput);
      const metadata = await sharp(semanticOutput).metadata();
      if (!metadata.hasAlpha) throw new Error('cached cutout has no alpha channel');
      cached = true;
      semanticCacheHits += 1;
    } catch {
      await rm(semanticOutput, { force: true });
      const result = await semanticCutout({
        input: originalSource,
        output: semanticOutput,
        backend: segmentationBackend,
        subjectKind,
      });
      semantic = {
        requested: true,
        backend: result.backend,
        attempts: result.attempts,
        cached: false,
      };
    }
    source = semanticOutput;
    if (cached) {
      semantic = {
        requested: true,
        backend: expectedBackend,
        attempts: [],
        cached: true,
      };
    }
  }

  const loaded = source === originalSource
    ? original
    : await sharp(source).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  const { data, info } = loaded;
  const { width, height } = info;
  if (width < 64 || height < 64) throw new Error(`${name}: source is too small`);
  const pixelCount = width * height;
  const touchingBorderPixels = borderIndexes(width, height)
    .reduce((total, index) => total + (data[index * 4 + 3] >= 16 ? 1 : 0), 0);
  if (touchingBorderPixels > 0) {
    throw codedError(
      'SUBJECT_TOUCHES_BORDER',
      `${name}: semantic foreground touches the source border (${touchingBorderPixels} pixels); regenerate the complete subject with real margin. Padding cannot restore clipped content.`,
    );
  }

  const detected = {
    transparentInput: true,
    palette: [],
    coverage: 1,
    clusterCount: 0,
  };
  const output = Buffer.from(data);
  let minX = width;
  let minY = height;
  let maxX = -1;
  let maxY = -1;
  let foregroundPixels = 0;
  let backgroundLikeForeground = 0;
  for (let index = 0; index < pixelCount; index += 1) {
    const offset = index * 4;
    if (data[offset + 3] < 16) { output[offset + 3] = 0; continue; }
    const x = index % width;
    const y = Math.floor(index / width);
    if (output[offset + 3] >= 16) {
      foregroundPixels += 1;
      minX = Math.min(minX, x); maxX = Math.max(maxX, x); minY = Math.min(minY, y); maxY = Math.max(maxY, y);
    }
  }
  if (foregroundPixels / pixelCount < 0.01) throw new Error(`${name}: foreground is empty or background conflicts with subject`);
  const cropWidth = maxX - minX + 1;
  const cropHeight = maxY - minY + 1;
  const rectangularFill = foregroundPixels / Math.max(1, cropWidth * cropHeight);
  if (rectangularFill > 0.94 && cropWidth >= width * 0.2 && cropHeight >= height * 0.2) {
    throw codedError(
      'SOLID_BLOCK',
      `${name}: foreground remains a solid opaque block (${(rectangularFill * 100).toFixed(1)}% filled bounding box)`,
    );
  }
  return {
    name, data: output, width, height, minX, minY, maxX, maxY,
    cropWidth,
    cropHeight,
    detected,
    semantic,
    foregroundRatio: foregroundPixels / pixelCount,
    backgroundLikeForegroundRatio: backgroundLikeForeground / pixelCount,
    rectangularFill,
  };
}

for (const name of names) {
  try { extracted.set(name, await extractForeground(name)); }
  catch (error) {
    const failure = { ok: false, name, ...diagnosticFrom(error) };
    failures.push(failure);
    if (failure.code === 'SEGMENTATION_BACKEND_UNAVAILABLE') break;
  }
}

const maximum = Math.min(512 - safeMargin * 2, Math.floor(512 * targetOccupancy));
function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

async function visibleBounds(input) {
  const { data, info } = await sharp(input).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  let minX = info.width; let minY = info.height; let maxX = -1; let maxY = -1;
  for (let y = 0; y < info.height; y += 1) for (let x = 0; x < info.width; x += 1) {
    if (data[(y * info.width + x) * 4 + 3] < 16) continue;
    minX = Math.min(minX, x); minY = Math.min(minY, y); maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
  }
  if (maxX < minX || maxY < minY) throw new Error('normalized subject is empty');
  return { minX, minY, maxX, maxY, width: maxX - minX + 1, height: maxY - minY + 1 };
}

if (!failures.length) {
  for (const state of states) {
    const stateAssets = state.frames.map((frame) => extracted.get(frame));
    if (stateAssets.some((asset) => !asset)) { failures.push({ ok: false, name: state.id, error: `${state.id}: missing extracted frame` }); continue; }
    const groupWidth = Math.max(...stateAssets.map((asset) => asset.cropWidth));
    const groupHeight = Math.max(...stateAssets.map((asset) => asset.cropHeight));
    const sharedScale = Math.min(maximum / groupWidth, maximum / groupHeight, 1);
    const prepared = [];
    for (const asset of stateAssets) {
      try {
        const initialWidth = Math.max(1, Math.round(asset.cropWidth * sharedScale));
        const initialHeight = Math.max(1, Math.round(asset.cropHeight * sharedScale));
        const initial = await sharp(asset.data, { raw: { width: asset.width, height: asset.height, channels: 4 } })
          .extract({ left: asset.minX, top: asset.minY, width: asset.cropWidth, height: asset.cropHeight })
          .resize(initialWidth, initialHeight, { fit: 'fill', kernel: sharp.kernel.lanczos3 })
          .png().toBuffer();
        const bounds = await visibleBounds(initial);
        const visible = await sharp(initial).extract({ left: bounds.minX, top: bounds.minY, width: bounds.width, height: bounds.height }).png().toBuffer();
        prepared.push({ asset, visible, bounds });
      } catch (error) {
        failures.push({ ok: false, name: asset.name, ...diagnosticFrom(error) });
      }
    }
    if (prepared.length !== stateAssets.length) continue;
    const referenceWidth = median(prepared.map((item) => item.bounds.width));
    const referenceHeight = median(prepared.map((item) => item.bounds.height));
    for (const item of prepared) {
      const { asset } = item;
      try {
        const lockedBody = state.id === 'idle' || state.triggers.includes('ambient:blink');
        const correction = lockedBody
          ? referenceHeight / item.bounds.height
          : Math.sqrt((referenceWidth * referenceHeight) / (item.bounds.width * item.bounds.height));
        const maximumCorrection = lockedBody ? 1.3 : 1.5;
        if (correction < 1 / maximumCorrection || correction > maximumCorrection) {
          throw codedError(
            'NORMALIZATION_TOO_LARGE',
            `${asset.name}: required scale correction ${correction.toFixed(3)} exceeds the safe ${maximumCorrection.toFixed(2)} limit`,
          );
        }
        const correctedWidth = Math.max(1, Math.round(item.bounds.width * correction));
        const correctedHeight = Math.max(1, Math.round(item.bounds.height * correction));
        // Re-apply the same occupancy ceiling used for the first group scale-down so the
        // processor never emits a frame that qa-assets then rejects as OCCUPANCY_TOO_LARGE.
        // If this clamp introduces real frame-to-frame drift, qa-assets still surfaces
        // SCALE_DRIFT, so an inconsistent frame is regenerated rather than silently masked.
        const occupancyScale = Math.min(1, maximum / correctedWidth, maximum / correctedHeight);
        const boundedWidth = Math.max(1, Math.round(correctedWidth * occupancyScale));
        const boundedHeight = Math.max(1, Math.round(correctedHeight * occupancyScale));
        const corrected = await sharp(item.visible)
          .resize(boundedWidth, boundedHeight, { fit: 'fill', kernel: sharp.kernel.lanczos3 })
          .png().toBuffer();
        const correctedBounds = await visibleBounds(corrected);
        const cropped = await sharp(corrected).extract({
          left: correctedBounds.minX,
          top: correctedBounds.minY,
          width: correctedBounds.width,
          height: correctedBounds.height,
        }).png().toBuffer();
        const targetWidth = correctedBounds.width;
        const targetHeight = correctedBounds.height;
        const anchorX = Math.round(state.anchor.x * 511);
        const anchorY = Math.round(state.anchor.y * 511);
        const left = Math.round(anchorX - targetWidth / 2);
        const top = Math.round(anchorY - targetHeight);
        if (left < 0 || top < 0 || left + targetWidth > 512 || top + targetHeight > 512) throw new Error(`${asset.name}: normalized frame exceeds canvas; regenerate with consistent framing`);
        const destination = path.join(outputDir, asset.name);
        await mkdir(path.dirname(destination), { recursive: true });
        await sharp({ create: { width: 512, height: 512, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } })
          .composite([{ input: cropped, left, top }]).png({ compressionLevel: 9, adaptiveFiltering: true }).toFile(destination);
        reports.push({
          ok: true,
          name: asset.name,
          state: state.id,
          cutoutBackend: asset.semantic.backend,
          cutoutCached: asset.semantic.cached,
          cutoutAttempts: asset.semantic.attempts,
          cutoutFallbackError: asset.semantic.error,
          backgroundInput: asset.detected.transparentInput ? 'real-alpha' : generationBackground,
          backgroundPalette: asset.detected.palette.map((color) => `#${color.map((value) => value.toString(16).padStart(2, '0')).join('').toUpperCase()}`),
          borderCoverage: asset.detected.coverage,
          sourceSize: [asset.width, asset.height],
          foregroundRatio: asset.foregroundRatio,
          backgroundLikeForegroundRatio: asset.backgroundLikeForegroundRatio,
          rectangularFill: asset.rectangularFill,
          sourceBounds: [asset.minX, asset.minY, asset.maxX, asset.maxY],
          sharedScale,
          normalizationCorrection: correction,
          referenceVisibleSize: [referenceWidth, referenceHeight],
          groupSourceMaximum: [groupWidth, groupHeight],
          outputBounds: [left, top, left + targetWidth - 1, top + targetHeight - 1],
        });
      } catch (error) {
        failures.push({ ok: false, name: asset.name, ...diagnosticFrom(error) });
      }
    }
  }
}

const coreIsRuntimeFrame = spec.states.some((state) => state.frames.includes(spec.character.coreAsset));
if (!failures.length && !selectedStateId && !coreIsRuntimeFrame) {
  const asset = extracted.get(spec.character.coreAsset);
  if (!asset) {
    failures.push({ ok: false, name: spec.character.coreAsset, code: 'ASSET_READ_FAILED', message: 'Core IP was not extracted', repair: REPAIRS.ASSET_READ_FAILED });
  } else {
    try {
      const sharedScale = Math.min(maximum / asset.cropWidth, maximum / asset.cropHeight, 1);
      const width = Math.max(1, Math.round(asset.cropWidth * sharedScale));
      const height = Math.max(1, Math.round(asset.cropHeight * sharedScale));
      const visible = await sharp(asset.data, { raw: { width: asset.width, height: asset.height, channels: 4 } })
        .extract({ left: asset.minX, top: asset.minY, width: asset.cropWidth, height: asset.cropHeight })
        .resize(width, height, { fit: 'fill', kernel: sharp.kernel.lanczos3 })
        .png().toBuffer();
      const bounds = await visibleBounds(visible);
      const cropped = await sharp(visible).extract({
        left: bounds.minX,
        top: bounds.minY,
        width: bounds.width,
        height: bounds.height,
      }).png().toBuffer();
      const left = Math.round(256 - bounds.width / 2);
      const top = Math.round(0.95 * 511 - bounds.height);
      if (left < 0 || top < 0 || left + bounds.width > 512 || top + bounds.height > 512) {
        throw codedError('NORMALIZATION_OVERFLOW', `${asset.name}: normalized core IP exceeds canvas`);
      }
      const destination = path.join(outputDir, asset.name);
      await mkdir(path.dirname(destination), { recursive: true });
      await sharp({ create: { width: 512, height: 512, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } })
        .composite([{ input: cropped, left, top }])
        .png({ compressionLevel: 9, adaptiveFiltering: true })
        .toFile(destination);
      reports.push({
        ok: true,
        name: asset.name,
        state: 'core-ip',
        cutoutBackend: asset.semantic.backend,
        cutoutCached: asset.semantic.cached,
        cutoutAttempts: asset.semantic.attempts,
        cutoutFallbackError: asset.semantic.error,
        backgroundInput: asset.detected.transparentInput ? 'real-alpha' : generationBackground,
        sourceSize: [asset.width, asset.height],
        foregroundRatio: asset.foregroundRatio,
        rectangularFill: asset.rectangularFill,
        sourceBounds: [asset.minX, asset.minY, asset.maxX, asset.maxY],
        sharedScale,
        outputBounds: [left, top, left + bounds.width - 1, top + bounds.height - 1],
      });
    } catch (error) {
      failures.push({ ok: false, name: asset.name, ...diagnosticFrom(error) });
    }
  }
}

let trayIcon;
const selectedIncludesCore = states.some((state) => state.frames.includes(spec.character.coreAsset));
if (!failures.length && (!selectedStateId || selectedIncludesCore)) {
  const trayPath = path.join(trayDir, 'tray-icon.png');
  const corePath = path.join(outputDir, spec.character.coreAsset);
  const trimmed = await sharp(corePath).trim({ threshold: 8 }).resize(28, 28, { fit: 'contain', kernel: sharp.kernel.lanczos3 }).png().toBuffer();
  await sharp({ create: { width: 32, height: 32, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } })
    .composite([{ input: trimmed, left: 2, top: 2 }]).png({ compressionLevel: 9 }).toFile(trayPath);
  const metadata = await sharp(trayPath).metadata();
  trayIcon = { path: path.relative(process.cwd(), trayPath).replaceAll('\\', '/'), width: metadata.width, height: metadata.height };
}

const reportPath = path.join(outputDir, 'asset-processing-report.json');
await writeFile(reportPath, `${JSON.stringify({
  schemaVersion: spec.schemaVersion,
  scope: selectedStateId || 'all',
  backgroundMode,
  segmentationBackend,
  subjectKind,
  generationBackground,
  threshold,
  feather,
  safeMargin,
  targetOccupancy,
  trayIcon,
  assets: [...reports, ...failures],
}, null, 2)}\n`, 'utf8');
console.log(`Processed ${reports.length}/${names.size} assets. Report: ${reportPath}`);
if (semanticRequests) {
  console.log(`Semantic cutout cache: ${semanticCacheHits}/${semanticRequests} hit(s).`);
}
if (failures.length) {
  for (const failure of failures) console.error(`[${failure.code}] ${failure.message}\n  repair: ${failure.repair}`);
  process.exit(1);
}
