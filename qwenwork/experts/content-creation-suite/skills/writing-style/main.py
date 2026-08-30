#!/usr/bin/env python3
"""
Style Learning Guide - Entry Point for WuKong Platform
This script handles dependency checks and routes user requests to the appropriate analysis modules.
"""

import sys
import os
import json
import subprocess

# --- Step 1: Dependency Self-Check ---
def check_environment():
    """Check if all required libraries are installed."""
    required_libs = ['numpy', 'pandas', 'Pillow', 'PyYAML', 'matplotlib']
    missing_libs = []
    
    for lib in required_libs:
        try:
            __import__(lib)
        except ImportError:
            missing_libs.append(lib)
            
    if missing_libs:
        print(json.dumps({
            "status": "error",
            "code": "ENV_NOT_READY",
            "message": f"Missing dependencies: {', '.join(missing_libs)}. Please ensure requirements.txt is installed."
        }))
        sys.exit(1)
        
    return True

# --- Step 2: Core Logic Routing ---
def run_scanner(base_path=None):
    """Run the material scanner and return structured data.

    base_path 可选：
      - 若传入则作为知识管家根目录使用
      - 不传则由 scanner 自动识别（向上递归找 1-素材/ + 3-AI档案/ 双目录）
    """
    script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'material_scanner.py')
    cmd = [sys.executable, script_path]
    if base_path:
        cmd.extend(['--base', base_path])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {"status": "error", "message": result.stderr}
    return json.loads(result.stdout)

def main():
    # Check environment first
    if not check_environment():
        return

    # Simple CLI interface for platform testing
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "message": "Usage: python main.py <command> [args]"}))
        return

    command = sys.argv[1]

    if command == "scan":
        # 知识管家根路径可选：不传则 scanner 自动向上查找
        base_path = sys.argv[2] if len(sys.argv) > 2 else None
        result = run_scanner(base_path)
        print(json.dumps(result, ensure_ascii=False))

    elif command == "analyze":
        # Placeholder for full analysis logic
        print(json.dumps({"status": "success", "message": "Analysis module triggered."}))

    else:
        print(json.dumps({"status": "error", "message": f"Unknown command: {command}"}))

if __name__ == "__main__":
    main()
