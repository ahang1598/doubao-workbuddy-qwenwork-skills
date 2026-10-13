"use strict";

const EVIDENCE_FIELDS = [
  "AnalysisTexts", "AnalysisImages", "AnalysisAudios", "CustomSensitiveResults",
  "SystemSensitiveResults", "OCRTextRecognitionResults", "OCRBottomSubtitleResults",
  "OCRResults", "SensitiveWords",
];

// Match the OpenAPI report's evidence counting rule without rendering a local report.
function getRuleFindingCount(rawRule) {
  const status = rawRule?.FinalMachineStatus ?? rawRule?.final_machine_status ?? rawRule?.MachineStatus;
  if (Number(status) === 2 && String(status).trim() !== "") {
    const details = rawRule?.MachineDetails ?? rawRule?.machine_details;
    if (!details || typeof details !== "object") return null;
    const seen = new Set();
    let count = 0;
    for (const key of [...EVIDENCE_FIELDS, ...Object.keys(details)]) {
      if (seen.has(key)) continue;
      seen.add(key);
      if (Array.isArray(details[key])) count += details[key].filter(item => item && typeof item === "object").length;
    }
    return count || null;
  }
  if ((typeof status === "number" || typeof status === "string") && String(status).trim() !== ""
      && [0, 1].includes(Number(status))) return 0;
  return null;
}

module.exports = { getRuleFindingCount };
