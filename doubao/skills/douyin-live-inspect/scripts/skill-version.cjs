"use strict";

const fs = require("node:fs");
const path = require("node:path");

// Shared by packaging and Lite telemetry; independent of repository dependencies.
function readSkillVersion(skillDir = path.resolve(__dirname, "..")) {
  const source = fs.readFileSync(path.join(skillDir, "SKILL.md"), "utf8");
  const frontmatter = source.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/)?.[1];
  const metadata = frontmatter?.match(/^metadata:[ \t]*\r?\n((?:[ \t]+[^\n]*\n?)*)/m)?.[1];
  const entries = metadata?.match(/^  version:[^\r\n]*$/gm) || [];
  const scalar = entries.length === 1 ? entries[0].slice("  version:".length).trim() : "";
  const value = scalar.match(/^(?:"([^"\r\n]*)"|'([^'\r\n]*)'|([^'"\s]+))$/)?.slice(1).find(v => v !== undefined);
  const numeric = "(?:0|[1-9][0-9]*)";
  const identifier = `(?:${numeric}|[0-9]*[A-Za-z-][0-9A-Za-z-]*)`;
  const semver = new RegExp(`^${numeric}\\.${numeric}\\.${numeric}(?:-${identifier}(?:\\.${identifier})*)?(?:\\+[0-9A-Za-z-]+(?:\\.[0-9A-Za-z-]+)*)?$`);
  if (!value || value.length > 256 || !semver.test(value)) {
    throw new Error("Skill metadata.version must be a valid semantic version");
  }
  return value;
}

module.exports = { readSkillVersion };
