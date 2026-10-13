#!/usr/bin/env python3
"""
技能验证脚本
检查SKILL.md是否符合skill-creator规范要求
"""

import json
import os
import sys
from pathlib import Path


def validate_frontmatter(content):
    """验证YAML frontmatter"""
    if not content.startswith('---'):
        return False, "缺少frontmatter开始标记"

    end_index = content.find('---', 3)
    if end_index == -1:
        return False, "缺少frontmatter结束标记"

    frontmatter = content[3:end_index].strip()

    # 检查必需字段
    required_fields = ['name', 'description']
    for field in required_fields:
        if field + ':' not in frontmatter:
            return False, f"缺少必需字段: {field}"

    # 检查description长度
    desc_line = [line for line in frontmatter.split(
        '\n') if line.startswith('description:')]
    if desc_line:
        desc = desc_line[0].replace('description:', '').strip()
        if len(desc) < 20:
            return False, "description太短，应包含触发条件"
        if len(desc) > 300:
            return False, "description太长，建议精简到300字符以内"

    return True, "Frontmatter验证通过"


def validate_structure(content):
    """验证技能结构"""
    required_sections = [
        '触发条件',
        '工作流程',
        '输出规范',
    ]

    missing = []
    for section in required_sections:
        if section not in content:
            missing.append(section)

    if missing:
        return False, f"缺少必要章节: {', '.join(missing)}"

    return True, "结构验证通过"


def validate_description_quality(description):
    """验证description质量"""
    issues = []

    # 检查是否包含触发关键词
    trigger_keywords = ['当用户', '触发', '包括']
    has_trigger = any(kw in description for kw in trigger_keywords)
    if not has_trigger:
        issues.append("description应说明触发条件")

    # 检查是否包含不触发的场景
    if '不适用于' not in description and '不触发' not in description:
        issues.append("建议说明不触发的场景")

    # 检查长度
    if len(description) < 50:
        issues.append("description太简短，无法准确路由")

    return len(issues) == 0, issues


def validate_evals(evals_path):
    """验证测试用例"""
    if not os.path.exists(evals_path):
        return False, "缺少testcases.json文件"

    try:
        with open(evals_path, 'r', encoding='utf-8') as f:
            evals = json.load(f)

        if not isinstance(evals, list):
            return False, "testcases.json应该是数组格式"

        if len(evals) == 0:
            return False, "testcases.json为空，建议添加测试用例"

        # 检查每个测试用例的必需字段
        required_fields = ['id', 'prompt', 'expected_behavior']
        for i, test_case in enumerate(evals):
            for field in required_fields:
                if field not in test_case:
                    return False, f"测试用例 {i} 缺少字段: {field}"

        return True, f"测试用例验证通过（共{len(evals)}个）"

    except json.JSONDecodeError as e:
        return False, f"evals.json格式错误: {str(e)}"


def main():
    """主验证流程"""
    skill_dir = Path(__file__).parent.parent

    print("=" * 60)
    print("技能验证报告")
    print("=" * 60)
    print()

    # 1. 检查SKILL.md存在
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        print("❌ 错误: 找不到SKILL.md文件")
        sys.exit(1)

    print("✅ SKILL.md文件存在")

    # 2. 读取内容
    with open(skill_md, 'r', encoding='utf-8') as f:
        content = f.read()

    # 3. 验证frontmatter
    valid, msg = validate_frontmatter(content)
    if valid:
        print(f"✅ {msg}")
    else:
        print(f"❌ {msg}")
        sys.exit(1)

    # 4. 验证结构
    valid, msg = validate_structure(content)
    if valid:
        print(f"✅ {msg}")
    else:
        print(f"⚠️  {msg}")

    # 5. 验证description
    desc_start = content.find('description:')
    if desc_start != -1:
        desc_end = content.find('\n', desc_start)
        description = content[desc_start +
                              len('description:'):desc_end].strip()
        valid, issues = validate_description_quality(description)
        if valid:
            print("✅ Description质量良好")
        else:
            print("⚠️  Description改进建议:")
            for issue in issues:
                print(f"   - {issue}")

    # 6. 验证测试用例
    evals_path = skill_dir / "tests" / "testcases.json"
    valid, msg = validate_evals(evals_path)
    if valid:
        print(f"✅ {msg}")
    else:
        print(f"⚠️  {msg}")

    # 7. 检查模板文件
    templates_dir = skill_dir / "templates"
    if templates_dir.exists():
        templates = list(templates_dir.glob("*.md"))
        print(f"✅ 找到{len(templates)}个模板文件")
        for t in templates:
            print(f"   - {t.name}")
    else:
        print("ℹ️  未找到templates目录（可选）")

    # 8. 文件大小检查
    file_size = os.path.getsize(skill_md)
    lines = content.count('\n')
    print(f"\n📊 统计信息:")
    print(f"   - 文件大小: {file_size} bytes")
    print(f"   - 行数: {lines}")

    if lines > 500:
        print("   ⚠️  建议: SKILL.md超过500行，考虑将部分内容移至references/")
    else:
        print("   ✅ 行数适中")

    print("\n" + "=" * 60)
    print("验证完成")
    print("=" * 60)


if __name__ == '__main__':
    main()
