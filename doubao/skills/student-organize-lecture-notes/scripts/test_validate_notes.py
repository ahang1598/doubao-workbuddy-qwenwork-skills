#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("validate_notes.py")
SPEC = importlib.util.spec_from_file_location("validate_notes", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


VALID_POSTCLASS = """# 课程笔记｜高等数学｜导数的定义

## 课程信息
日期：2026-09-01。使用课件和录音。

## 一、核心结论
导数描述函数在一点附近的瞬时变化率。[课件 p.3]

## 二、知识结构
极限是导数定义的前置概念。[录音 00:02:10]

## 三、详细笔记
差商取极限得到导数；必须先检查极限存在。[课件 p.4]

## 四、例题、案例或实验
材料给出多项式求导示例；完整条件见课件。[课件 p.6]

## 五、术语、公式或关键表达
符号 f'(x) 表示导函数。[课件 p.4]

## 六、课堂任务与 DDL
本次材料未明确。

## 七、待核对与疑问
左右导数是否都讲到仍需核对。[待核对]

## 八、复习与主动回忆
### 10–20 分钟复习清单
1. 默写导数定义。
2. 说明极限与导数的关系。
3. 检查左右导数条件。

### 主动回忆题
1. 导数定义中的极限变量是什么？
2. 为什么极限不存在时不能说可导？
3. 可导与连续有什么关系？

### 答案要点
1. 增量趋近于零。
2. 差商没有唯一极限。
3. 可导推出连续，反向一般不成立。
""" + ("补充复习说明。" * 80)


VALID_PRECLASS = """# 课前预习卡｜大学物理｜动量定理

## 预习依据与置信度
材料等级：A
- [课程材料] 课程大纲指定第二章第 3 节。
- [推断] 建议复习矢量分解。

## 本次预习目标
1. 能说明冲量与动量变化的关系。
2. 能识别系统与外力。

## 必备前置知识
- 牛顿第二定律、矢量和定积分。

## 概念地图
- 力—时间积累 → 冲量 → 动量变化。

## 预习重点与难点
- [课程材料] 区分瞬时力和一段时间内的冲量。
- [推断] 重点检查正方向和系统边界。

## 带着这些问题上课
1. 动量定理对变力是否成立？
2. 内力什么时候可以不单独计算？
3. 选取不同系统会怎样改变外力项？

## 15 分钟预习安排
1. 0–4 分钟回忆矢量和积分。
2. 4–9 分钟阅读大纲指定页。
3. 9–13 分钟画概念关系。
4. 13–15 分钟记录疑问。

## 课前诊断
1. 自测题：恒力作用时冲量如何计算？

### 答案要点
1. 力与作用时间的乘积，并保留方向。

## 待确认与补充材料
- [待确认] 教师是否要求使用质心系。
""" + ("预习时只建立结构，不提前替代课堂推导。" * 20)


VALID_VISUAL = """# 视觉识别稿｜大学物理课堂板书

## 材料与页面
| 标签 | 文件/页码 | 类型 | 可读性 | 问题 |
|---|---|---|---|---|
| 手写笔记 1 | IMG_01/1 | 手写 | 大部分清晰 | 右下角反光 |

## 分区转写
### [手写笔记 1-R1]
[已确认] 标题为“动量定理”。

### [手写笔记 1-R2]
[待核对] 末项可能为外力冲量；下标不清。

## 公式、图表与版式
- [手写笔记 1-R3] 左侧力—时间图箭头指向右侧积分式。

## 待核对
| 区域 | 候选/可见内容 | 原因 | 核对方式 |
|---|---|---|---|
| R2 | 外力冲量 | 下标模糊 | 对照课件公式 |

## 识别审计
- 已复核公式正负号和积分上下限。
- 无法辨认：右下角一处边注。
- 交叉来源：课件第 8 页。
""" + ("版式关系已按区域记录。" * 15)


class ValidateNotesTests(unittest.TestCase):
    def test_valid_postclass_passes_strict(self) -> None:
        report = MODULE.validate(VALID_POSTCLASS, strict=True, artifact="postclass")
        self.assertTrue(report["ok"], report["errors"])

    def test_postclass_missing_heading_fails(self) -> None:
        report = MODULE.validate(
            VALID_POSTCLASS.replace("## 七、待核对与疑问", "## 其他"),
            strict=False,
            artifact="postclass",
        )
        self.assertFalse(report["ok"])

    def test_placeholder_fails_all_modes(self) -> None:
        for artifact, text in [
            ("postclass", VALID_POSTCLASS),
            ("preclass", VALID_PRECLASS),
            ("visual", VALID_VISUAL),
        ]:
            with self.subTest(artifact=artifact):
                report = MODULE.validate(text + "\nTODO", strict=False, artifact=artifact)
                self.assertFalse(report["ok"])

    def test_postclass_no_source_marker_fails(self) -> None:
        text = MODULE.POSTCLASS_SOURCE_PATTERN.sub("", VALID_POSTCLASS)
        report = MODULE.validate(text, strict=False, artifact="postclass")
        self.assertFalse(report["ok"])

    def test_valid_preclass_passes_strict(self) -> None:
        report = MODULE.validate(VALID_PRECLASS, strict=True, artifact="preclass")
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["material_level"], "A")

    def test_preclass_without_material_level_fails(self) -> None:
        text = VALID_PRECLASS.replace("材料等级：A", "材料情况：充分")
        report = MODULE.validate(text, strict=False, artifact="preclass")
        self.assertFalse(report["ok"])

    def test_valid_visual_passes_strict(self) -> None:
        report = MODULE.validate(VALID_VISUAL, strict=True, artifact="visual")
        self.assertTrue(report["ok"], report["errors"])

    def test_visual_without_status_fails(self) -> None:
        text = MODULE.VISUAL_STATUS_PATTERN.sub("", VALID_VISUAL)
        report = MODULE.validate(text, strict=False, artifact="visual")
        self.assertFalse(report["ok"])


if __name__ == "__main__":
    unittest.main()
