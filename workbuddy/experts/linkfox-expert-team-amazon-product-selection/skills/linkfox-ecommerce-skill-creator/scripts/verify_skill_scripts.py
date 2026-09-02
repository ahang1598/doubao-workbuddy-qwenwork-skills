#!/usr/bin/env python3
"""
verify_skill_scripts.py — 对 skill 目录下的 scripts/*.py 跑三步回环验证。

借鉴 browser-act-skill-forge Phase 3b：
1. 第 1 步：python script.py {args} → 退出码 0 + stdout 是有效 JSON / JS 字符串
2. 第 2 步：真实跑通（依赖测试用例的"正常用例"，对比预期字段或非空判断）
3. 第 3 步：错误参数 → 返回 {"error": true, "message": ...}，不崩溃

测试用例从 examples/test-cases.md 或 examples/trial-prompts.md 解析。
格式约定见 references/verification-guide.md。

退出码：
  0 - 全部通过
  1 - 任意一步失败
  2 - 测试用例缺失或目录结构错
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional


def parse_test_cases(test_file: Path) -> dict[str, dict[str, list[str]]]:
    """解析 test-cases.md，按脚本名归类正常 / 错误用例。

    简化格式：

    ## scripts/foo.py

    ### 正常用例
    - arg1 arg2 → expect-non-empty
    - arg1 --flag value → expect-field:title

    ### 错误用例
    - INVALID-arg → expect-error
    """
    if not test_file.exists():
        return {}

    text = test_file.read_text(encoding="utf-8")
    cases: dict[str, dict[str, list[str]]] = {}
    current_script: Optional[str] = None
    current_section: Optional[str] = None

    for line in text.splitlines():
        m_script = re.match(r"^##\s+scripts/([\w\-]+\.py)\s*$", line.strip())
        if m_script:
            current_script = m_script.group(1)
            cases.setdefault(current_script, {"normal": [], "error": []})
            current_section = None
            continue

        if re.match(r"^###\s+(正常用例|Normal cases?|Normal)\s*$", line.strip(), re.IGNORECASE):
            current_section = "normal"
            continue
        if re.match(r"^###\s+(错误用例|Error cases?|Error)\s*$", line.strip(), re.IGNORECASE):
            current_section = "error"
            continue

        m_case = re.match(r"^-\s*(.+)$", line.strip())
        if m_case and current_script and current_section:
            cases[current_script][current_section].append(m_case.group(1))

    return cases


def parse_args_string(spec: str) -> tuple[list[str], dict]:
    """从 'arg1 arg2 → expect-...' 解析参数和期望。"""
    if "→" in spec:
        args_part, expect_part = spec.split("→", 1)
    elif "->" in spec:
        args_part, expect_part = spec.split("->", 1)
    else:
        return spec.strip().split(), {"type": "non-empty"}

    args = args_part.strip().split()
    expect_part = expect_part.strip()

    if expect_part == "expect-non-empty" or expect_part == "non-empty":
        return args, {"type": "non-empty"}
    if expect_part == "expect-error" or expect_part == "error":
        return args, {"type": "error"}
    m = re.match(r"expect-field:(\w+)", expect_part)
    if m:
        return args, {"type": "field", "field": m.group(1)}
    m = re.match(r"expect-contains:(.+)", expect_part)
    if m:
        return args, {"type": "contains", "value": m.group(1).strip()}

    return args, {"type": "non-empty"}


def run_script(script_path: Path, args: list[str], cwd: Path, timeout: int = 30) -> tuple[int, str, str]:
    """跑一次脚本，返回 (returncode, stdout, stderr)。"""
    try:
        proc = subprocess.run(
            [sys.executable, str(script_path), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd),
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as e:
        return -1, "", f"timeout after {timeout}s"


def check_step1_structure(stdout: str) -> tuple[bool, str]:
    """第 1 步：stdout 是有效 JSON 或非空 JS 字符串。"""
    stdout = stdout.strip()
    if not stdout:
        return False, "empty stdout"
    try:
        json.loads(stdout)
        return True, "valid JSON"
    except json.JSONDecodeError:
        if "(" in stdout and ")" in stdout and len(stdout) > 10:
            return True, "non-JSON but non-empty (assumed JS string for type D)"
        return False, "stdout is neither valid JSON nor a non-trivial JS string"


def check_step2_match(stdout: str, expect: dict) -> tuple[bool, str]:
    """第 2 步：检查正常用例的预期。"""
    stdout = stdout.strip()
    expect_type = expect.get("type", "non-empty")

    if expect_type == "non-empty":
        return (len(stdout) > 0), "non-empty check"

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        if expect_type == "field":
            return False, f"expected JSON field {expect['field']}, got non-JSON"
        return len(stdout) > 0, "fallback non-empty (non-JSON output)"

    if isinstance(data, dict) and data.get("error"):
        return False, f"normal case unexpectedly returned error: {data.get('message')}"

    if expect_type == "field":
        field = expect["field"]
        if isinstance(data, dict) and field in data and data[field] is not None:
            return True, f"field '{field}' present and non-null"
        return False, f"field '{field}' missing or null"

    if expect_type == "contains":
        return (expect["value"] in stdout), f"contains check: {expect['value']!r}"

    return True, "ok"


def check_step3_error(stdout: str, returncode: int) -> tuple[bool, str]:
    """第 3 步：错误参数应返回 {"error": true, ...}，不应崩溃 stack trace。"""
    stdout = stdout.strip()
    if not stdout:
        return False, "empty stdout (script may have crashed without error JSON)"
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return False, "error case did not return valid JSON"
    if isinstance(data, dict) and data.get("error") is True and "message" in data:
        return True, f"error returned gracefully: {data.get('message')}"
    return False, "error case did not return {error: true, message: ...} structure"


def verify_one_script(script_path: Path, cases: dict, cwd: Path) -> dict:
    """对一个脚本跑三步验证，返回结果字典。"""
    result = {
        "script": script_path.name,
        "step1": {"status": "skipped", "details": []},
        "step2": {"status": "skipped", "details": []},
        "step3": {"status": "skipped", "details": []},
    }

    normal_cases = cases.get("normal", [])
    error_cases = cases.get("error", [])

    if not normal_cases and not error_cases:
        result["step1"]["status"] = "no-test-cases"
        result["step1"]["details"].append(
            f"No test cases found for {script_path.name} in test-cases.md"
        )
        return result

    if normal_cases:
        all_pass = True
        for case in normal_cases:
            args, expect = parse_args_string(case)
            rc, stdout, stderr = run_script(script_path, args, cwd)
            ok_struct, msg_struct = check_step1_structure(stdout)
            ok_match, msg_match = check_step2_match(stdout, expect) if ok_struct else (False, "skipped due to step1 fail")
            entry = f"args={args!r} | step1: {'PASS' if ok_struct else 'FAIL'} ({msg_struct}) | step2: {'PASS' if ok_match else 'FAIL'} ({msg_match})"
            if rc != 0 and rc != -1:
                entry += f" | exit code {rc} stderr={stderr.strip()[:200]}"
            if not (ok_struct and ok_match):
                all_pass = False
            result["step1"]["details"].append(entry)
            result["step2"]["details"].append(entry)
        result["step1"]["status"] = "pass" if all_pass else "fail"
        result["step2"]["status"] = "pass" if all_pass else "fail"

    if error_cases:
        all_pass = True
        for case in error_cases:
            args, expect = parse_args_string(case)
            rc, stdout, stderr = run_script(script_path, args, cwd)
            ok_err, msg_err = check_step3_error(stdout, rc)
            entry = f"args={args!r} | step3: {'PASS' if ok_err else 'FAIL'} ({msg_err})"
            if not ok_err:
                all_pass = False
            result["step3"]["details"].append(entry)
        result["step3"]["status"] = "pass" if all_pass else "fail"
    else:
        result["step3"]["status"] = "no-error-cases"
        result["step3"]["details"].append("No error cases declared in test-cases.md")

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_path", help="skill 目录路径")
    parser.add_argument(
        "--test-cases",
        help="测试用例文件路径，默认 examples/test-cases.md 或 examples/trial-prompts.md",
    )
    parser.add_argument(
        "--strict-no-cases",
        action="store_true",
        help="缺测试用例视为失败（默认是警告）",
    )
    args = parser.parse_args()

    skill_path = Path(args.skill_path).resolve()
    if not skill_path.exists():
        print(f"Skill path not found: {skill_path}", file=sys.stderr)
        sys.exit(2)

    scripts_dir = skill_path / "scripts"
    if not scripts_dir.exists():
        print(f"No scripts/ directory in {skill_path} — nothing to verify (type C skipped)")
        sys.exit(0)

    py_scripts = sorted(
        p for p in scripts_dir.glob("*.py")
        if p.name not in {
            "response_io.py",
            "linkfox_paths.py",
            "quick_validate.py",
            "verify_skill_scripts.py",
        }
        and not p.name.startswith("_")
    )
    if not py_scripts:
        print(f"No business scripts/*.py in {scripts_dir} — nothing to verify")
        sys.exit(0)

    if args.test_cases:
        test_file = Path(args.test_cases)
    else:
        test_file = skill_path / "examples" / "test-cases.md"
        if not test_file.exists():
            test_file = skill_path / "examples" / "trial-prompts.md"

    cases_by_script = parse_test_cases(test_file) if test_file.exists() else {}

    if not cases_by_script:
        msg = (
            f"No test cases found at {test_file}. "
            f"Create examples/test-cases.md per references/verification-guide.md"
        )
        if args.strict_no_cases:
            print(msg, file=sys.stderr)
            sys.exit(2)
        print(f"WARNING: {msg}")

    overall_pass = True
    results = []
    for script in py_scripts:
        cases = cases_by_script.get(script.name, {"normal": [], "error": []})
        result = verify_one_script(script, cases, skill_path)
        results.append(result)
        for step in ("step1", "step2", "step3"):
            if result[step]["status"] == "fail":
                overall_pass = False

    for r in results:
        print(f"\n=== {r['script']} ===")
        for step in ("step1", "step2", "step3"):
            print(f"  [{step}] {r[step]['status']}")
            for d in r[step]["details"]:
                print(f"      {d}")

    print("\n" + ("PASS" if overall_pass else "FAIL"))
    sys.exit(0 if overall_pass else 1)


if __name__ == "__main__":
    main()
