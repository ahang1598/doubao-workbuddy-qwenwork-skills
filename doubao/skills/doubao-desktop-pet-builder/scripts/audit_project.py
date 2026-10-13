#!/usr/bin/env python3
"""Read-only static audit for Electron desktop-pet projects."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

from template_contract import CONTRACT_FILES_BY_VERSION


SKIP_DIRS = {"node_modules", ".git", ".webpack", ".build", "out", "release", "dist", "build", "qa"}
TEXT_SUFFIXES = {".js", ".cjs", ".mjs", ".ts", ".tsx", ".html", ".json"}
RULES = [
    ("critical", "node-integration", re.compile(r"nodeIntegration\s*:\s*true"), "renderer enables Node integration"),
    ("critical", "context-isolation", re.compile(r"contextIsolation\s*:\s*false"), "context isolation is disabled"),
    ("critical", "web-security", re.compile(r"webSecurity\s*:\s*false"), "web security is disabled"),
    ("high", "ipc-exposure", re.compile(r"exposeInMainWorld\([^\n]+ipcRenderer"), "preload may expose raw ipcRenderer"),
    ("high", "hardcoded-drive", re.compile(r"[\"'][A-Za-z]:\\\\"), "hard-coded Windows drive path"),
    ("high", "unsafe-html", re.compile(r"\.innerHTML\s*="), "innerHTML assignment requires taint review"),
    ("medium", "primary-display-only", re.compile(r"getPrimaryDisplay\s*\("), "primary-display-only positioning may break multi-monitor behavior"),
    ("medium", "file-path", re.compile(r"\bFile\.path\b|\.path\s*\)"), "browser File.path assumption requires Electron version review"),
    ("high", "nonexistent-api", re.compile(r"dialog\.showInputBox\s*\("), "Electron has no dialog.showInputBox API"),
    ("high", "nonrecursive-assets", re.compile(r"require\.context\(\s*['\"]\.\.\/\.\.\/assets\/pet['\"]\s*,\s*false\s*,"), "runtime asset import does not recurse into spec subdirectories"),
    ("high", "ignored-log-failure", re.compile(r"catch\s*\{[^}]{0,240}日志写入失败不影响主功能", re.DOTALL), "logging failure is swallowed while the app may still be reported ready"),
    ("critical", "disabled-tls-verification", re.compile(r"NODE_TLS_REJECT_UNAUTHORIZED\s*[:=]\s*['\"]?0|strict-ssl\s*[:=]\s*false|curl\b[^\n]{0,160}\s-k(?:\s|$)"), "TLS certificate verification is disabled"),
]
MOJIBAKE = re.compile(r"\ufffd|锛|鈥|灏忛噾|妗屽疇|鍠傚皬|鎽告懜")


def source_files(root: Path, excluded: set[str]):
    for path in root.rglob("*"):
        relative_parts = path.relative_to(root).parts
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES and not any(part in SKIP_DIRS or part in excluded for part in relative_parts):
            yield path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path)
    parser.add_argument("--exclude", action="append", default=[], help="top-level directory name to exclude")
    args = parser.parse_args()
    root = args.project.resolve()
    if not root.is_dir():
        print(f"Project does not exist: {root}", file=sys.stderr)
        return 2

    findings: list[dict[str, object]] = []
    scanned = 0
    for path in source_files(root, set(args.exclude)):
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for severity, rule, pattern, message in RULES:
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append({"severity": severity, "rule": rule, "message": message, "file": str(path.relative_to(root)), "line": line})
        if MOJIBAKE.search(text) and "mojibakePattern" not in text and "MOJIBAKE =" not in text:
            findings.append({"severity": "high", "rule": "mojibake", "message": "probable UTF-8/GBK mojibake", "file": str(path.relative_to(root)), "line": 1})
        for match in re.finditer(r"process\.on\(\s*['\"]uncaughtException['\"][\s\S]{0,1200}?\n\s*\}\s*\);", text):
            body = match.group(0)
            if not re.search(r"\b(?:app|process)\.exit\s*\(|\bfatalExit\s*\(|\bthrow\b|\.finally\s*\(", body):
                line = text.count("\n", 0, match.start()) + 1
                findings.append({"severity": "high", "rule": "exception-swallow", "message": "uncaught exception handler may swallow crashes", "file": str(path.relative_to(root)), "line": line})

    package_path = root / "package.json"
    checks = {
        "packageJson": package_path.is_file(),
        "lockFile": any((root / name).is_file() for name in ("package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml")),
        "petSpec": (root / "pet-spec.json").is_file(),
        "tests": any((root / name).exists() for name in ("tests", "test", "playwright.config.ts", "playwright.config.js")),
    }
    scripts: dict[str, str] = {}
    if package_path.is_file():
        try:
            package = json.loads(package_path.read_text(encoding="utf-8"))
            scripts = package.get("scripts", {}) if isinstance(package.get("scripts"), dict) else {}
            dependencies = {
                **(package.get("dependencies", {}) if isinstance(package.get("dependencies"), dict) else {}),
                **(package.get("devDependencies", {}) if isinstance(package.get("devDependencies"), dict) else {}),
            }
            electron_version = dependencies.get("electron")
            if isinstance(electron_version, str):
                if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", electron_version):
                    findings.append({"severity": "high", "rule": "unpinned-electron", "message": "Electron must use an exact version so its platform artifact and checksum stay deterministic", "file": "package.json", "line": 1})
                allow_scripts = package.get("allowScripts")
                allow_scripts = allow_scripts if isinstance(allow_scripts, dict) else {}
                if allow_scripts.get(f"electron@{electron_version}") is not True:
                    findings.append({"severity": "high", "rule": "blocked-electron-postinstall", "message": "the exact Electron postinstall script is not explicitly allowed", "file": "package.json", "line": 1})
        except (OSError, json.JSONDecodeError):
            findings.append({"severity": "critical", "rule": "invalid-package", "message": "package.json is not valid JSON", "file": "package.json", "line": 1})
    npmrc_path = root / ".npmrc"
    if npmrc_path.is_file():
        npmrc = npmrc_path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"(?im)^\s*strict-ssl\s*=\s*false\s*$", npmrc):
            findings.append({"severity": "critical", "rule": "disabled-tls-verification", "message": ".npmrc disables TLS certificate verification", "file": ".npmrc", "line": 1})
    for name in ("check", "test", "test:e2e", "test:dev-smoke", "qa:assets", "qa:experience", "qa:ui", "preflight", "package:win", "make:win", "portable:win", "make:mac", "portable:mac"):
        if name not in scripts:
            findings.append({"severity": "medium", "rule": "missing-script", "message": f"missing npm script: {name}", "file": "package.json", "line": 1})
    dev_script = scripts.get("dev", "")
    if dev_script and not re.search(r"tools[/\\]run-dev\.mjs", dev_script):
        findings.append({"severity": "high", "rule": "uncontrolled-dev-script", "message": "dev must use the controlled tools/run-dev.mjs source runner", "file": "package.json", "line": 1})
    if re.search(r"\b(?:package|make)(?::|\b)", dev_script):
        findings.append({"severity": "high", "rule": "packaging-in-dev", "message": "dev must not package or make an application", "file": "package.json", "line": 1})
    if re.search(r"remote-debugging-port", dev_script):
        findings.append({"severity": "high", "rule": "debug-port-in-normal-dev", "message": "normal dev must not leave a remote debugging port enabled", "file": "package.json", "line": 1})
    check_script = scripts.get("check", "")
    for required_gate, gate_file in (("qa:assets", "qa-assets.mjs"), ("qa:experience", "qa-experience.mjs")):
        if check_script and required_gate not in check_script and gate_file not in check_script:
            findings.append({"severity": "high", "rule": "incomplete-default-check", "message": f"default check does not run {required_gate}", "file": "package.json", "line": 1})
    for script_name, script_value in scripts.items():
        for match in re.finditer(r"(?:^|&&\s*)(?:node|tsx)(?:\s+--test)?\s+([^\s;&|]+)", script_value):
            target = match.group(1)
            if target.startswith("-") or any(token in target for token in ("*", "$", "%")):
                continue
            if not (root / target).is_file():
                findings.append({"severity": "high", "rule": "missing-script-target", "message": f"npm script {script_name} references missing file: {target}", "file": "package.json", "line": 1})

    provenance_path = root / ".doubao-pet-builder.json"
    provenance: dict[str, object] = {}
    if not provenance_path.is_file():
        findings.append({"severity": "high", "rule": "missing-builder-provenance", "message": "project lacks the builder template contract marker; do not claim it was generated by the standard scaffold", "file": ".doubao-pet-builder.json", "line": 1})
    else:
        try:
            loaded = json.loads(provenance_path.read_text(encoding="utf-8"))
            provenance = loaded if isinstance(loaded, dict) else {}
        except (OSError, json.JSONDecodeError):
            findings.append({"severity": "high", "rule": "invalid-builder-provenance", "message": "builder template contract marker is invalid", "file": ".doubao-pet-builder.json", "line": 1})
    contract_version = provenance.get("templateContractVersion")
    contract_files = CONTRACT_FILES_BY_VERSION.get(contract_version)
    if contract_files:
        critical_hashes = provenance.get("criticalFileHashes")
        critical_hashes = critical_hashes if isinstance(critical_hashes, dict) else {}
        for relative in contract_files:
            target = root / relative
            if not target.is_file():
                findings.append({"severity": "high", "rule": "incomplete-template-contract", "message": f"contract v{contract_version} file is missing: {relative}", "file": relative, "line": 1})
                continue
            expected_hash = critical_hashes.get(relative)
            actual_hash = hashlib.sha256(target.read_bytes()).hexdigest()
            if expected_hash != actual_hash:
                findings.append({"severity": "high", "rule": "template-contract-drift", "message": f"critical generated file differs from its scaffold hash: {relative}", "file": relative, "line": 1})

        required_tests = [
            "tests/unit/state-machine.test.ts",
            "tests/unit/persistence.test.ts",
            "tests/unit/drag.test.ts",
            "tests/unit/typing-listener.test.ts",
            "tests/unit/experience.test.ts",
            "tests/e2e/app.e2e.ts",
            "tests/e2e/soak.e2e.ts",
        ]
        if contract_version >= 4:
            required_tests.append("tests/unit/dev-ports.test.mjs")
        for relative in required_tests:
            if not (root / relative).is_file():
                findings.append({"severity": "high", "rule": "missing-contract-test", "message": f"contract v{contract_version} test is missing: {relative}", "file": relative, "line": 1})
    elif contract_version is not None:
        findings.append({
            "severity": "high",
            "rule": "unsupported-template-contract",
            "message": f"unsupported template contract version: {contract_version}",
            "file": ".doubao-pet-builder.json",
            "line": 1,
        })

    renderer_config_path = root / "webpack.renderer.config.js"
    renderer_config = ""
    if renderer_config_path.is_file():
        renderer_config = renderer_config_path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"devtool\s*:\s*['\"][^'\"]*eval[^'\"]*['\"]", renderer_config):
            findings.append({"severity": "critical", "rule": "eval-renderer-devtool", "message": "eval-based renderer devtool is incompatible with strict CSP", "file": "webpack.renderer.config.js", "line": 1})
        elif not re.search(r"devtool\s*:\s*['\"]source-map['\"]", renderer_config):
            findings.append({"severity": "high", "rule": "missing-safe-renderer-devtool", "message": "renderer must explicitly use devtool: source-map", "file": "webpack.renderer.config.js", "line": 1})
    else:
        findings.append({"severity": "high", "rule": "missing-renderer-config", "message": "webpack.renderer.config.js is missing", "file": "webpack.renderer.config.js", "line": 1})

    strict_csp = False
    for html_path in root.rglob("*.html"):
        if any(part in SKIP_DIRS for part in html_path.relative_to(root).parts):
            continue
        html = html_path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"script-src\s+'self'", html, re.IGNORECASE):
            strict_csp = True
        if re.search(r"unsafe-eval", html, re.IGNORECASE):
            findings.append({"severity": "critical", "rule": "unsafe-eval-csp", "message": "renderer CSP must not allow unsafe-eval; fix Webpack devtool instead", "file": str(html_path.relative_to(root)), "line": 1})
    if strict_csp and re.search(r"devtool\s*:\s*['\"][^'\"]*eval[^'\"]*['\"]", renderer_config):
        findings.append({"severity": "critical", "rule": "csp-webpack-conflict", "message": "strict script-src self will block the configured eval renderer bundle", "file": "webpack.renderer.config.js", "line": 1})

    main_path = root / "src" / "main.ts"
    preload_path = root / "src" / "preload.ts"
    main_text = main_path.read_text(encoding="utf-8", errors="replace") if main_path.is_file() else ""
    preload_text = preload_path.read_text(encoding="utf-8", errors="replace") if preload_path.is_file() else ""
    if "runtime:renderer-ready" not in main_text or "runtime:renderer-ready" not in preload_text:
        findings.append({"severity": "high", "rule": "missing-three-renderer-ready", "message": "pet, dashboard and reminder must report renderer bootstrap readiness", "file": "src/main.ts", "line": 1})
    if "console-message" not in main_text:
        findings.append({"severity": "high", "rule": "missing-renderer-console-gate", "message": "main process must fail on renderer CSP/bootstrap console errors", "file": "src/main.ts", "line": 1})
    if provenance.get("templateContractVersion") == 3:
        runtime_contracts = (
            ("requestSingleInstanceLock", "missing-single-instance", "single-instance lifecycle lock is missing"),
            ("before-quit", "missing-graceful-exit", "normal exit persistence gate is missing"),
            ("readValidatedJson", "missing-persistence-validation", "startup persistence validation is missing"),
            ("nextReminderDelay", "missing-long-reminder-scheduling", "long reminder segmented scheduling is missing"),
        )
        for token, rule, message in runtime_contracts:
            if token not in main_text:
                findings.append({"severity": "high", "rule": rule, "message": message, "file": "src/main.ts", "line": 1})
        pet_renderer = root / "src" / "renderer" / "pet" / "index.ts"
        pet_text = pet_renderer.read_text(encoding="utf-8", errors="replace") if pet_renderer.is_file() else ""
        pet_html_path = root / "src" / "renderer" / "pet" / "index.html"
        pet_html = pet_html_path.read_text(encoding="utf-8", errors="replace") if pet_html_path.is_file() else ""
        pet_css_path = root / "src" / "renderer" / "pet" / "index.css"
        pet_css = pet_css_path.read_text(encoding="utf-8", errors="replace") if pet_css_path.is_file() else ""
        if "dragstart" not in pet_text or 'draggable="false"' not in pet_html or "-webkit-user-drag: none" not in f"{pet_html}\n{pet_css}":
            findings.append({"severity": "high", "rule": "native-image-drag", "message": "pet image native drag suppression is missing", "file": "src/renderer/pet/index.ts", "line": 1})

    spec_path = root / "pet-spec.json"
    if spec_path.is_file():
        try:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            if spec.get("schemaVersion") != 5:
                findings.append({"severity": "high", "rule": "legacy-spec", "message": "pet-spec is not v5; recreate with the v2 builder before claiming semantic cutout or UI readiness", "file": "pet-spec.json", "line": 1})
            pipeline = spec.get("assetPipeline")
            if not isinstance(pipeline, dict) or pipeline.get("backgroundMode") != "semantic-cutout":
                findings.append({"severity": "high", "rule": "legacy-background", "message": "asset pipeline must use v5 semantic-cutout; border flood-fill alone cannot remove opaque background blocks", "file": "pet-spec.json", "line": 1})
            elif pipeline.get("generationBackground") not in {"transparent-grid", "solid-chroma"}:
                findings.append({"severity": "high", "rule": "invalid-generation-background", "message": "generationBackground must be transparent-grid or solid-chroma", "file": "pet-spec.json", "line": 1})
            if isinstance(pipeline, dict) and ("backgroundKey" in pipeline or pipeline.get("backgroundTolerance", 0) > 48):
                findings.append({"severity": "high", "rule": "background-fit-hack", "message": "legacy backgroundKey or excessive tolerance can hide gradients and ground shadows; regenerate the source instead", "file": "pet-spec.json", "line": 1})
            sizing = spec.get("experience", {}).get("petSizing", {}) if isinstance(spec.get("experience"), dict) else {}
            if not isinstance(sizing, dict) or not (180 <= sizing.get("baseWindowPx", 0) <= 260) or sizing.get("defaultScale") not in {0.65, 0.8, 1, 1.2}:
                findings.append({"severity": "high", "rule": "pet-size-contract", "message": "pet sizing must declare a 180-260 px base window and a supported default scale", "file": "pet-spec.json", "line": 1})
            states = spec.get("states", []) if isinstance(spec.get("states"), list) else []
            runtime_frames = {frame for state in states if isinstance(state, dict) for frame in state.get("frames", [])}
            if spec.get("character", {}).get("coreAsset") in runtime_frames:
                findings.append({"severity": "high", "rule": "core-asset-is-runtime-frame", "message": "coreAsset must remain an independent identity master, not an animation frame", "file": "pet-spec.json", "line": 1})
            if states and all(len(state.get("frames", [])) <= 1 for state in states if isinstance(state, dict)):
                findings.append({"severity": "high", "rule": "static-states", "message": "all states are single-frame; the pet has no asset animation", "file": "pet-spec.json", "line": 1})
            for state in states:
                if isinstance(state, dict) and not state.get("triggers"):
                    findings.append({"severity": "high", "rule": "unreachable-state", "message": f"state has no declared trigger: {state.get('id', '<unknown>')}", "file": "pet-spec.json", "line": 1})
            interactions = spec.get("experience", {}).get("interactions", []) if isinstance(spec.get("experience"), dict) else []
            interaction_state_ids: set[str] = set()
            for interaction in interactions if isinstance(interactions, list) else []:
                if not isinstance(interaction, dict):
                    continue
                if not str(interaction.get("emoji", "")).strip():
                    findings.append({"severity": "high", "rule": "missing-menu-emoji", "message": f"interaction has no semantic menu emoji: {interaction.get('id', '<unknown>')}", "file": "pet-spec.json", "line": 1})
                state_id = interaction.get("stateId")
                if isinstance(state_id, str):
                    interaction_state_ids.add(state_id)
            for state in states:
                if not isinstance(state, dict):
                    continue
                state_id = str(state.get("id", ""))
                frame_count = len(state.get("frames", [])) if isinstance(state.get("frames"), list) else 0
                triggers = state.get("triggers", []) if isinstance(state.get("triggers"), list) else []
                if state_id == "idle" and frame_count < 4:
                    findings.append({"severity": "high", "rule": "short-idle", "message": "idle needs 4-6 frames before CSS breathing is added", "file": "pet-spec.json", "line": 1})
                if state_id == "blink" and frame_count != 5:
                    findings.append({"severity": "high", "rule": "short-blink", "message": "blink must use exactly 5 aligned frames", "file": "pet-spec.json", "line": 1})
                visible = state_id in interaction_state_ids or any(str(trigger).startswith(("pointer:", "reminder:", "edge:", "random:")) for trigger in triggers)
                movement = state.get("direction") in {"left", "right"} or any(str(trigger).startswith("movement:") for trigger in triggers)
                if visible and frame_count < 5:
                    findings.append({"severity": "high", "rule": "short-visible-action", "message": f"visible action needs 5-6 frames: {state_id}", "file": "pet-spec.json", "line": 1})
                if movement and frame_count < 6:
                    findings.append({"severity": "high", "rule": "short-movement", "message": f"movement action needs 6-8 frames: {state_id}", "file": "pet-spec.json", "line": 1})
            e2e_path = root / "tests" / "e2e" / "app.e2e.ts"
            if e2e_path.is_file():
                e2e_text = e2e_path.read_text(encoding="utf-8", errors="replace")
                display_name = spec.get("character", {}).get("displayName")
                if "圆圆" in e2e_text and display_name != "圆圆":
                    findings.append({"severity": "high", "rule": "hardcoded-e2e-fixture", "message": "E2E hard-codes the template character name instead of reading the current spec", "file": "tests/e2e/app.e2e.ts", "line": 1})
                state_ids = {state.get("id") for state in states if isinstance(state, dict)}
                for hardcoded_state in re.findall(r"dataset\.state\s*===\s*['\"]([^'\"]+)['\"]", e2e_text):
                    if hardcoded_state not in state_ids:
                        findings.append({"severity": "high", "rule": "hardcoded-e2e-state", "message": f"E2E waits for a state absent from the current spec: {hardcoded_state}", "file": "tests/e2e/app.e2e.ts", "line": 1})
            expected = {spec.get("character", {}).get("coreAsset"), *(frame for state in states if isinstance(state, dict) for frame in state.get("frames", []))}
            expected.discard(None)
            asset_root = root / "src" / "assets" / "pet"
            if asset_root.is_dir():
                actual = {path.relative_to(asset_root).as_posix() for path in asset_root.rglob("*.png")}
                for name in sorted(expected - actual):
                    findings.append({"severity": "high", "rule": "missing-runtime-asset", "message": f"spec asset is missing or case-mismatched: {name}", "file": "pet-spec.json", "line": 1})
                for name in sorted(actual - expected):
                    findings.append({"severity": "high", "rule": "orphan-runtime-asset", "message": f"runtime PNG has no state or coreAsset reference: {name}", "file": str(Path("src/assets/pet") / name), "line": 1})
            tray_icon = root / "src" / "assets" / "tray" / "tray-icon.png"
            if not tray_icon.is_file():
                findings.append({"severity": "high", "rule": "missing-tray-icon", "message": "processed 32x32 PNG tray icon is missing", "file": "src/assets/tray/tray-icon.png", "line": 1})

            for relative in (Path("src/renderer/dashboard/index.css"), Path("src/renderer/reminder/index.css")):
                css_path = root / relative
                if not css_path.is_file():
                    continue
                css = css_path.read_text(encoding="utf-8", errors="replace")
                root_block = re.search(r"html\s*,\s*body\s*\{([^}]*)\}", css, re.DOTALL)
                if not root_block or not re.search(r"overflow\s*:\s*hidden", root_block.group(1)):
                    findings.append({"severity": "high", "rule": "native-page-scrollbar", "message": "page root must hide native Windows scrollbars; scroll only inside styled containers", "file": str(relative).replace("\\", "/"), "line": 1})
            main_path = root / "src" / "main.ts"
            if main_path.is_file():
                main_text = main_path.read_text(encoding="utf-8", errors="replace")
                if "nativeImage.createFromDataURL" in main_text:
                    findings.append({"severity": "high", "rule": "fragile-tray-icon", "message": "tray icon is generated from a data URL; use the validated PNG derived from core-ip", "file": "src/main.ts", "line": 1})
        except (OSError, json.JSONDecodeError):
            findings.append({"severity": "critical", "rule": "invalid-spec", "message": "pet-spec.json is not valid JSON", "file": "pet-spec.json", "line": 1})

    lock_path = root / ".build" / "activity.lock"
    if lock_path.is_file():
        try:
            owner = json.loads(lock_path.read_text(encoding="utf-8"))
            pid = owner.get("pid")
            alive = False
            if isinstance(pid, int) and pid > 0:
                try:
                    os.kill(pid, 0)
                    alive = True
                except OSError:
                    alive = False
            if not alive:
                findings.append({"severity": "high", "rule": "stale-activity-lock", "message": f"activity lock points to a dead pid: {pid}", "file": ".build/activity.lock", "line": 1})
        except (OSError, json.JSONDecodeError):
            findings.append({"severity": "high", "rule": "invalid-activity-lock", "message": "activity lock is unreadable and should be recovered by the controlled runner", "file": ".build/activity.lock", "line": 1})

    for temporary in root.rglob("*"):
        if not temporary.is_file() or any(part in SKIP_DIRS for part in temporary.relative_to(root).parts):
            continue
        if temporary.name.startswith("runtime-failed") or temporary.name.endswith(".tmp"):
            findings.append({"severity": "high", "rule": "stale-runtime-temporary", "message": "runtime left a failure marker or temporary persistence file", "file": str(temporary.relative_to(root)), "line": 1})

    release_root = root / "release"
    if release_root.is_dir():
        for candidate in release_root.rglob("*"):
            if not candidate.is_symlink():
                continue
            try:
                target = os.readlink(candidate)
            except OSError:
                continue
            if os.path.isabs(target):
                findings.append({"severity": "high", "rule": "absolute-release-symlink", "message": "release bundle contains an absolute symlink and is not portable", "file": str(candidate.relative_to(root)), "line": 1})

    report = {"project": str(root), "scannedFiles": scanned, "checks": checks, "findings": findings}
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 1 if any(item["severity"] in {"critical", "high"} for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
