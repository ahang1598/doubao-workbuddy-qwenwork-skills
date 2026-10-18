#!/usr/bin/env node

import { randomUUID } from "node:crypto";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { crc32 } from "node:zlib";

const TEMPLATE_PREFIX = "artifact-template-";
const WRITE_LOCK_NAME = ".artifact-template-write-lock";
const LOCK_OWNER_FILENAME = "owner-pid";
const LOCK_OWNER_GRACE_MS = 30_000;
const MAX_SKILL_NAME_LENGTH = 64;
const PNG_SIGNATURE = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
const USAGE =
  "Usage: create-template-skill.mjs --reference-path <path> --preview-path <path> --display-name <name> --description <description> [--kind <kind>] [--gallery-kind <kind>] [--mode update --skill-name <name>]";
const templateKinds = new Map([
  [
    "document",
    {
      kind: "document",
      extension: ".docx",
      output: "a document",
      outputs: "documents",
      preservation:
        "Preserve page setup, sections, styles, lists, tables, headers, footers, and recurring page elements.",
      workflow: getOfficeWorkflow("documents", "document"),
    },
  ],
  [
    "presentation",
    {
      kind: "presentation",
      extension: ".pptx",
      output: "a presentation",
      outputs: "presentations",
      preservation:
        "Preserve source slides, layouts, masters, typography, geometry, images, charts, tables, and recurring slide chrome.",
      workflow: getOfficeWorkflow("presentations", "presentation"),
    },
  ],
  [
    "spreadsheet",
    {
      kind: "spreadsheet",
      extension: ".xlsx",
      output: "a spreadsheet",
      outputs: "spreadsheets",
      preservation:
        "Preserve sheet structure, formulas, names, number formats, dimensions, tables, charts, validation, conditional formatting, and frozen panes.",
      workflow: getOfficeWorkflow("spreadsheets", "spreadsheet"),
    },
  ],
  [
    "image",
    {
      kind: "image",
      extension: ".png",
      output: "an image",
      outputs: "images",
      preservation:
        "Preserve the reference image's composition, visual hierarchy, palette, typography, material treatment, lighting, and recurring brand elements.",
      workflow: getImageTemplateWorkflow("imagegen"),
    },
  ],
  [
    "email",
    {
      kind: "email",
      extension: ".txt",
      output: "an email",
      outputs: "emails",
      preservation:
        "Preserve the reference email's voice, information hierarchy, pacing, subject, body, calls to action, and signature conventions.",
      workflow: `2. Read the retained plain-text email and use it as the structural and voice reference.
3. Draft a new plain-text email that preserves the reference's subject, body, calls to action, and signature conventions.
4. Treat the user's prompt and available sources as the content input. Do not invent facts or send the email merely because this skill was invoked.
5. Review the draft for fidelity, completeness, and ready-to-copy plain-text formatting, then return it.`,
    },
  ],
  [
    "slack",
    {
      kind: "slack",
      extension: ".txt",
      output: "a Slack message",
      outputs: "Slack messages",
      preservation:
        "Preserve the reference Slack message's voice, length, structure, formatting, emoji usage, mentions, links, and call-to-action conventions.",
      workflow: `2. Read the retained plain-text Slack message and use it as the structural and voice reference.
3. Draft a new Slack message that follows the reference's length, structure, formatting, and call-to-action conventions.
4. Treat the user's prompt and available sources as the content input. Do not invent facts or post the message merely because this skill was invoked.
5. Review the draft for fidelity, completeness, and ready-to-copy plain-text formatting, then return it.`,
    },
  ],
]);
const inferredTemplateKindByExtension = new Map([
  [".docx", "document"],
  [".pptx", "presentation"],
  [".xlsx", "spreadsheet"],
  [".png", "image"],
]);

async function createTemplateSkill(
  rawRequest,
  codexHome = getDefaultCodexHome(),
) {
  const request = await validateRequest(rawRequest);
  const skillsRoot = path.join(codexHome, "skills");
  const releaseLock = await acquireWriteLock(
    path.join(codexHome, WRITE_LOCK_NAME),
  );
  try {
    const identity =
      request.mode === "update"
        ? await getUpdateIdentity(skillsRoot, request, request.template)
        : await getCreateIdentity(skillsRoot, request.displayName);
    const skillPath = path.join(skillsRoot, identity.skillName);
    const stagedSkill = await stageTemplateSkill({
      description: request.description,
      displayName: identity.displayName,
      parentDirectory: skillsRoot,
      previewPath: request.previewPath,
      referencePath: request.referencePath,
      skillName: identity.skillName,
      sourceSkillPath: request.mode === "update" ? skillPath : null,
      template: request.template,
    });
    try {
      if (request.mode === "update") {
        await replaceTemplateSkill(stagedSkill, skillPath);
      } else {
        await fs.rename(stagedSkill, skillPath);
      }
    } catch (error) {
      await fs.rm(stagedSkill, { force: true, recursive: true });
      throw error;
    }
    return {
      displayName: identity.displayName,
      kind: request.template.kind,
      ...(request.template.galleryKind == null
        ? {}
        : { galleryKind: request.template.galleryKind }),
      skillName: identity.skillName,
      skillPath,
    };
  } finally {
    await releaseLock();
  }
}

async function validateRequest(rawRequest) {
  const mode = rawRequest.mode ?? "create";
  if (mode !== "create" && mode !== "update") {
    throw new Error("--mode must be 'create' or 'update'.");
  }
  const displayName = getRequiredString(
    rawRequest,
    "displayName",
    "--display-name",
  );
  const description = getRequiredString(
    rawRequest,
    "description",
    "--description",
  );
  assertSingleLine(displayName, "--display-name", 64);
  assertSingleLine(description, "--description", 600);
  const referencePath = path.resolve(
    getRequiredString(rawRequest, "referencePath", "--reference-path"),
  );
  const previewPath = path.resolve(
    getRequiredString(rawRequest, "previewPath", "--preview-path"),
  );
  const extension = path.extname(referencePath).toLowerCase();
  const requestedKind = getOptionalString(rawRequest, "kind", "--kind");
  const requestedGalleryKind = getOptionalString(
    rawRequest,
    "galleryKind",
    "--gallery-kind",
  );
  if (extension === ".txt" && requestedKind == null) {
    throw new Error("--kind must be 'email' or 'slack' for a .txt reference.");
  }
  const kind = requestedKind ?? inferredTemplateKindByExtension.get(extension);
  const baseTemplate = kind == null ? null : templateKinds.get(kind);
  if (baseTemplate == null) {
    if (requestedKind != null) {
      throw new Error(
        "--kind must be 'document', 'presentation', 'spreadsheet', 'image', 'email', or 'slack'.",
      );
    }
    throw new Error(
      "--reference-path must end in .docx, .pptx, .xlsx, .png, or .txt.",
    );
  }
  if (baseTemplate.kind !== "image" && requestedGalleryKind != null) {
    throw new Error("--gallery-kind is only valid for image templates.");
  }
  const galleryKind =
    baseTemplate.kind === "image"
      ? (requestedGalleryKind ?? "imagegen")
      : null;
  const template =
    galleryKind == null
      ? baseTemplate
      : {
          ...baseTemplate,
          galleryKind,
          workflow: getImageTemplateWorkflow(galleryKind),
        };
  if (extension !== template.extension) {
    throw new Error(
      `--kind ${template.kind} requires a ${template.extension} reference.`,
    );
  }
  await Promise.all([
    assertRegularFile(referencePath, "--reference-path"),
    assertRegularFile(previewPath, "--preview-path"),
  ]);
  if (path.extname(previewPath).toLowerCase() !== ".png") {
    throw new Error("--preview-path must end in .png.");
  }
  if (!hasValidPngStructure(await fs.readFile(previewPath))) {
    throw new Error("--preview-path must contain a valid PNG.");
  }
  if (
    template.kind === "image" &&
    !hasValidPngStructure(await fs.readFile(referencePath))
  ) {
    throw new Error("--reference-path must contain a valid PNG.");
  }

  const skillName = getOptionalString(rawRequest, "skillName", "--skill-name");
  if (mode === "update") {
    if (skillName == null) {
      throw new Error("--skill-name is required for an explicit update.");
    }
    assertSkillName(skillName);
  } else if (skillName != null) {
    throw new Error("--skill-name is only valid when --mode is 'update'.");
  }

  return {
    description,
    displayName,
    mode,
    previewPath,
    referencePath,
    skillName,
    template,
  };
}

function getDefaultCodexHome() {
  const homeDir = path.resolve(
    process.env.HOME ?? process.env.USERPROFILE ?? os.homedir(),
  );
  return path.resolve(process.env.CODEX_HOME ?? path.join(homeDir, ".codex"));
}

async function getCreateIdentity(skillsRoot, displayName) {
  const slug = getSlug(displayName);
  for (let index = 1; ; index += 1) {
    const suffix = index === 1 ? "" : `-${index}`;
    const baseLength = MAX_SKILL_NAME_LENGTH - suffix.length;
    const skillName =
      `${TEMPLATE_PREFIX}${slug}`.slice(0, baseLength).replace(/-+$/u, "") +
      suffix;
    if (!(await pathExists(path.join(skillsRoot, skillName)))) {
      return {
        displayName: index === 1 ? displayName : `${displayName} ${index}`,
        skillName,
      };
    }
  }
}

async function getUpdateIdentity(skillsRoot, request, template) {
  const skillPath = path.join(skillsRoot, request.skillName);
  const sidecarPath = path.join(skillPath, "artifact-template.json");
  const sidecar = JSON.parse(await fs.readFile(sidecarPath, "utf8"));
  const sidecarGalleryKind =
    sidecar.kind === "image" ? (sidecar.galleryKind ?? "imagegen") : null;
  if (
    sidecar.schemaVersion !== 1 ||
    sidecar.kind !== template.kind ||
    sidecarGalleryKind !== (template.galleryKind ?? null)
  ) {
    throw new Error(
      `${request.skillName} is not a version 1 ${template.galleryKind ?? template.kind} artifact template.`,
    );
  }
  return { displayName: request.displayName, skillName: request.skillName };
}

async function stageTemplateSkill({
  description,
  displayName,
  parentDirectory,
  previewPath,
  referencePath,
  skillName,
  sourceSkillPath,
  template,
}) {
  await fs.mkdir(parentDirectory, { recursive: true });
  const stagedSkill = await fs.mkdtemp(
    path.join(parentDirectory, `.${skillName}-stage-`),
  );
  const referenceFilename = `reference${template.extension}`;
  try {
    if (sourceSkillPath != null) {
      await fs.cp(sourceSkillPath, stagedSkill, { recursive: true });
    }
    await Promise.all([
      fs.mkdir(path.join(stagedSkill, "agents"), { recursive: true }),
      fs.mkdir(path.join(stagedSkill, "assets"), { recursive: true }),
    ]);
    await Promise.all([
      fs.writeFile(
        path.join(stagedSkill, "SKILL.md"),
        getTemplateSkillMarkdown({
          description,
          displayName,
          skillName,
          template,
        }),
      ),
      fs.writeFile(
        path.join(stagedSkill, "agents", "openai.yaml"),
        getTemplateOpenAiYaml({ displayName, skillName, template }),
      ),
      fs.writeFile(
        path.join(stagedSkill, "artifact-template.json"),
        `${JSON.stringify(
          {
            schemaVersion: 1,
            kind: template.kind,
            ...(template.galleryKind == null
              ? {}
              : { galleryKind: template.galleryKind }),
            reference: `assets/${referenceFilename}`,
            preview: "assets/preview.png",
          },
          null,
          2,
        )}\n`,
      ),
      fs.copyFile(
        referencePath,
        path.join(stagedSkill, "assets", referenceFilename),
      ),
      fs.copyFile(previewPath, path.join(stagedSkill, "assets", "preview.png")),
    ]);
    return stagedSkill;
  } catch (error) {
    await fs.rm(stagedSkill, { force: true, recursive: true });
    throw error;
  }
}

function getTemplateSkillMarkdown({
  description,
  displayName,
  skillName,
  template,
}) {
  const triggerDescription = `Create ${template.output} using the ${displayName} template and its retained reference file. Use when the user selects this template, names ${displayName}, or explicitly invokes $${skillName}. ${description}`;
  return `---
name: ${skillName}
description: ${JSON.stringify(triggerDescription)}
---

# ${displayName}

Create ${template.output} from this template. Keep the reference file unchanged.

## Workflow

1. Read \`artifact-template.json\` and resolve its paths relative to this skill directory.
${template.workflow}

## Fidelity

${template.preservation}

User instructions control requested content and explicit deviations. The retained reference controls layout and formatting where the user has not requested a change.
`;
}

function getOfficeWorkflow(pluginName, output) {
  return `2. Load [@${pluginName}](plugin://${pluginName}@openai-primary-runtime) and invoke its reference/template workflow with the retained file.
3. Treat the user's prompt and available sources as the content input. Do not invent facts merely to fill a template slot.
4. Clone or import the reference instead of replacing its visual system with generic defaults.
5. Render and verify the finished ${output}, then return the final artifact.`;
}

function getImageTemplateWorkflow(galleryKind) {
  switch (galleryKind) {
    case "imagegen":
      return `2. Invoke $imagegen with the retained PNG as a reference image and the user's requested content as the edit or generation brief.
3. Treat the user's prompt and available sources as the content input. Do not invent factual claims merely to fill the composition.
4. Preserve the reference's visual language unless the user explicitly requests a deviation.
5. Visually inspect the generated image for fidelity and defects, then return the final image.`;
    case "product-design":
      return `2. Load [@Product Design](plugin://product-design@openai-curated-remote) and use the retained PNG as the visual template for the user's requested product-design workflow.
3. Treat the user's prompt and available sources as the content input. Do not invent factual claims merely to fill the composition.
4. Preserve the reference's visual language unless the user explicitly requests a deviation.
5. Follow the Product Design workflow through visual verification, then return its final result.`;
    default:
      throw new Error(
        "--gallery-kind must be 'imagegen' or 'product-design'.",
      );
  }
}

function getTemplateOpenAiYaml({ displayName, skillName, template }) {
  const candidate = `Create ${template.outputs} with the ${displayName} template`;
  const shortDescription =
    candidate.length <= 64
      ? candidate
      : `Create ${template.output} from this saved template`;
  return `interface:
  display_name: ${JSON.stringify(displayName)}
  short_description: ${JSON.stringify(shortDescription)}
  icon_large: "./assets/preview.png"
  default_prompt: ${JSON.stringify(`Use $${skillName} to create ${template.output} with this template.`)}
policy:
  allow_implicit_invocation: true
`;
}

async function replaceTemplateSkill(stagedPath, finalPath) {
  const backupPath = `${finalPath}.backup-${randomUUID()}`;
  await fs.rename(finalPath, backupPath);
  try {
    await fs.rename(stagedPath, finalPath);
  } catch (error) {
    try {
      await fs.rename(backupPath, finalPath);
    } catch (rollbackError) {
      throw new AggregateError(
        [error, rollbackError],
        "Template update failed and rollback was incomplete.",
      );
    }
    throw error;
  }
  await fs.rm(backupPath, { force: true, recursive: true });
}

async function acquireWriteLock(lockPath) {
  await fs.mkdir(path.dirname(lockPath), { recursive: true });
  let canRecover = true;
  while (true) {
    try {
      await fs.mkdir(lockPath);
      break;
    } catch (error) {
      if (error?.code !== "EEXIST") {
        throw error;
      }
      if (canRecover && (await isWriteLockStale(lockPath))) {
        await fs.rm(lockPath, { force: true, recursive: true });
        canRecover = false;
        continue;
      }
      throw new Error(
        `Another artifact template write is already in progress at ${lockPath}.`,
      );
    }
  }
  try {
    await fs.writeFile(
      path.join(lockPath, LOCK_OWNER_FILENAME),
      `${process.pid}\n`,
    );
  } catch (error) {
    await fs.rm(lockPath, { force: true, recursive: true });
    throw error;
  }
  return () => fs.rm(lockPath, { force: true, recursive: true });
}

async function isWriteLockStale(lockPath) {
  const owner = await fs
    .readFile(path.join(lockPath, LOCK_OWNER_FILENAME), "utf8")
    .catch((error) => {
      if (error?.code === "ENOENT") {
        return null;
      }
      throw error;
    });
  const ownerPid = Number(owner);
  if (Number.isSafeInteger(ownerPid) && ownerPid > 0) {
    try {
      process.kill(ownerPid, 0);
      return false;
    } catch (error) {
      if (error?.code === "ESRCH") {
        return true;
      }
      if (error?.code === "EPERM") {
        return false;
      }
      throw error;
    }
  }
  return Date.now() - (await fs.stat(lockPath)).mtimeMs > LOCK_OWNER_GRACE_MS;
}

function getSlug(displayName) {
  const slug = displayName
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/gu, "-")
    .replace(/^-+|-+$/gu, "");
  if (slug.length === 0) {
    throw new Error(
      "--display-name must contain at least one ASCII letter or number.",
    );
  }
  return slug;
}

function assertSkillName(skillName) {
  if (
    skillName.length > MAX_SKILL_NAME_LENGTH ||
    !/^artifact-template-[a-z0-9]+(?:-[a-z0-9]+)*$/u.test(skillName)
  ) {
    throw new Error(
      "--skill-name must be a valid artifact-template skill name.",
    );
  }
}

function assertSingleLine(value, label, maxLength) {
  if (/[<>]/u.test(value)) {
    throw new Error(`${label} must not contain angle brackets.`);
  }
  if (value.length > maxLength || /[\0\r\n]/u.test(value)) {
    throw new Error(
      `${label} must be one line of at most ${maxLength} characters.`,
    );
  }
}

function hasValidPngStructure(bytes) {
  if (
    bytes.length < PNG_SIGNATURE.length ||
    !bytes.subarray(0, PNG_SIGNATURE.length).equals(PNG_SIGNATURE)
  ) {
    return false;
  }
  let offset = PNG_SIGNATURE.length;
  let firstChunk = true;
  while (offset + 12 <= bytes.length) {
    const dataLength = bytes.readUInt32BE(offset);
    const dataStart = offset + 8;
    const crcOffset = dataStart + dataLength;
    const nextOffset = crcOffset + 4;
    if (nextOffset > bytes.length) {
      return false;
    }
    const type = bytes.toString("ascii", offset + 4, dataStart);
    if (firstChunk && (type !== "IHDR" || dataLength !== 13)) {
      return false;
    }
    if (
      crc32(bytes.subarray(offset + 4, crcOffset)) !==
      bytes.readUInt32BE(crcOffset)
    ) {
      return false;
    }
    if (type === "IEND") {
      return dataLength === 0 && nextOffset === bytes.length;
    }
    firstChunk = false;
    offset = nextOffset;
  }
  return false;
}

async function assertRegularFile(filePath, label) {
  const stat = await fs.stat(filePath);
  if (!stat.isFile()) {
    throw new Error(`${label} must point to a file.`);
  }
}

function getRequiredString(value, key, label) {
  const entry = value[key];
  if (typeof entry !== "string" || entry.trim().length === 0) {
    throw new Error(`${label} must be a non-empty string.`);
  }
  return entry.trim();
}

function getOptionalString(value, key, label) {
  const entry = value[key];
  if (entry == null) {
    return null;
  }
  if (typeof entry !== "string" || entry.trim().length === 0) {
    throw new Error(`${label} must be a non-empty string when provided.`);
  }
  return entry.trim();
}

async function pathExists(filePath) {
  return fs
    .access(filePath)
    .then(() => true)
    .catch((error) => {
      if (error?.code === "ENOENT") {
        return false;
      }
      throw error;
    });
}

const requestFlagToKey = new Map([
  ["--mode", "mode"],
  ["--skill-name", "skillName"],
  ["--kind", "kind"],
  ["--gallery-kind", "galleryKind"],
  ["--reference-path", "referencePath"],
  ["--preview-path", "previewPath"],
  ["--display-name", "displayName"],
  ["--description", "description"],
]);

function getRequestFromArguments(args) {
  if (args.length === 0 || args.length % 2 !== 0) {
    throw new Error(USAGE);
  }

  const request = {};
  for (let index = 0; index < args.length; index += 2) {
    const flag = args[index];
    const key = requestFlagToKey.get(flag);
    if (key == null || Object.hasOwn(request, key)) {
      throw new Error(USAGE);
    }
    request[key] = args[index + 1];
  }
  return request;
}

async function main() {
  const request = getRequestFromArguments(process.argv.slice(2));
  const result = await createTemplateSkill(request);
  process.stdout.write(`${JSON.stringify(result)}\n`);
}

if (
  process.argv[1] != null &&
  fileURLToPath(import.meta.url) === path.resolve(process.argv[1])
) {
  main().catch((error) => {
    process.stderr.write(
      `${error instanceof Error ? error.message : String(error)}\n`,
    );
    process.exitCode = 1;
  });
}
