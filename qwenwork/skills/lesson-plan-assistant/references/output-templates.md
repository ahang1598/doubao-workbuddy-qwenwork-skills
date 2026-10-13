# Word文档生成模板参考

> **QoderWork 适配说明**：本文档为教案 Word 文档的内容结构和样式规范参考。在 QoderWork 中，通过内置 `docx` 技能（用 Skill 工具激活）生成文档，把以下结构作为输入传递给 docx 技能即可，无需手动安装 python-docx 或直接运行以下代码。以下 python-docx 代码仅用于说明文档结构和样式要求。

## 教案Word文档模板

```python
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

def create_lesson_plan_doc(title, subject, grade, lesson_type, content_data):
    """创建教案Word文档"""
    doc = Document()

    # 设置中文字体
    doc.styles['Normal'].font.name = '宋体'
    doc.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    doc.styles['Normal'].font.size = Pt(12)

    # 标题
    heading = doc.add_heading(f'《{title}》教学设计', level=0)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    heading_run = heading.runs[0]
    heading_run.font.size = Pt(18)
    heading_run.font.bold = True
    heading_run.font.color.rgb = RGBColor(0, 0, 0)

    # 副标题
    subtitle = doc.add_paragraph(f'{subject} · {grade} · {lesson_type}')
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.runs[0].font.size = Pt(11)
    subtitle.runs[0].font.color.rgb = RGBColor(102, 102, 102)

    doc.add_paragraph()  # 空行

    # 一、基本信息
    doc.add_heading('一、基本信息', level=1)
    info_table = doc.add_table(rows=2, cols=2)
    info_table.style = 'Table Grid'

    # 填充基本信息表格
    cells = info_table.rows[0].cells
    cells[0].text = f'课题：{title}'
    cells[1].text = f'课型：{lesson_type}'
    cells = info_table.rows[1].cells
    cells[0].text = f'学科：{subject}'
    cells[1].text = f'年级：{grade}'

    doc.add_paragraph()

    # 二、目标确立依据
    doc.add_heading('二、目标确立依据', level=1)

    # （一）课标分析
    doc.add_heading('（一）课标分析', level=2)
    doc.add_heading('1. 课标摘录', level=3)
    doc.add_paragraph('查阅《义务教育课程标准（2022年版）》，找出与本节课相关的内容要求：')
    doc.add_paragraph('• 【此处根据实际课题填写课标内容】')

    doc.add_heading('2. 课标分解', level=3)
    doc.add_paragraph('学什么：【具体知识点】')
    doc.add_paragraph('学到什么程度：【能、会、理解、掌握等行为动词】')
    doc.add_paragraph('怎么学：【学习方法与步骤】')

    # （二）教材分析
    doc.add_heading('（二）教材分析', level=2)
    doc.add_paragraph('1. 教材定位：【在教材体系中的位置】')
    doc.add_paragraph('2. 知识联系：')
    doc.add_paragraph('  • 已学知识：【相关前置知识】')
    doc.add_paragraph('  • 正学知识：【本节课核心内容】')
    doc.add_paragraph('  • 将学知识：【后续延伸内容】')
    doc.add_paragraph('3. 编排特点：【教材呈现方式和教学建议】')

    # （三）学情分析
    doc.add_heading('（三）学情分析', level=2)
    doc.add_paragraph('1. 优势分析：【学生已有基础】')
    doc.add_paragraph('2. 不足分析：【学习困难点】')
    doc.add_paragraph('3. 重难点确定：')
    doc.add_paragraph('  • 教学重点：【具体知识点或技能】')
    doc.add_paragraph('  • 教学难点：【学生较难理解的内容】')

    # 三、教学目标
    doc.add_heading('三、教学目标', level=1)
    doc.add_heading('（一）知识目标', level=2)
    doc.add_paragraph('【具体知识点掌握要求】')

    doc.add_heading('（二）能力目标', level=2)
    doc.add_paragraph('【观察、实践、思维、协作、表达等能力培养目标】')

    doc.add_heading('（三）素养目标', level=2)
    doc.add_paragraph('【核心素养培养：文化基础、自主发展、社会参与】')

    doc.add_heading('（四）思政目标', level=2)
    doc.add_paragraph('【思想政治教育元素融入】')

    # 四、教学方法
    doc.add_heading('四、教学方法', level=1)
    doc.add_paragraph('讲授法、讨论法、演示法、探究法、练习法、任务驱动法等')

    # 五、教学过程
    doc.add_heading('五、教学过程（40分钟）', level=1)

    # （一）导入新课
    doc.add_heading('（一）导入新课（3分钟）', level=2)
    doc.add_paragraph('导入方式：【复习导入/情境导入/问题导入】')
    doc.add_paragraph('具体操作：【详细描述导入过程】')
    doc.add_paragraph('设计意图：激发学习兴趣和好奇心，建立新旧知识联系，自然引入课题')

    # （二）讲授新课
    doc.add_heading('（二）讲授新课（32分钟）', level=2)

    # 任务驱动
    doc.add_heading('任务驱动（25分钟）', level=3)

    # 学习任务一
    doc.add_paragraph('学习任务一：【任务名称】（8分钟）').runs[0].font.bold = True
    doc.add_paragraph('任务描述：【具体任务要求】')
    doc.add_paragraph('活动设计：')
    doc.add_paragraph('  1. 【步骤1】')
    doc.add_paragraph('  2. 【步骤2】')
    doc.add_paragraph('  3. 【步骤3】')

    # 评价量表表格
    doc.add_paragraph('评价量表：')
    eval_table = doc.add_table(rows=4, cols=4)
    eval_table.style = 'Table Grid'
    headers = ['评价维度', '优秀（4-5分）', '良好（3分）', '需改进（1-2分）']
    for i, header in enumerate(headers):
        eval_table.rows[0].cells[i].text = header
        eval_table.rows[0].cells[i].paragraphs[0].runs[0].font.bold = True

    doc.add_paragraph('技术应用：【智慧中小学平台功能/数字化工具】')
    doc.add_paragraph('预期效果：【学生能达到的学习效果】')

    # 课堂练习
    doc.add_heading('课堂练习（5分钟）', level=3)
    doc.add_paragraph('练习题1：【题目内容，紧扣教学目标】')
    doc.add_paragraph('练习题2：【题目内容，针对教学难点】')

    # 板书设计
    doc.add_heading('板书设计（2分钟）', level=3)
    board_para = doc.add_paragraph()
    board_para.add_run('【板书内容结构】\n').font.name = 'Courier New'
    board_para.add_run('主标题\n').font.name = 'Courier New'
    board_para.add_run('├─ 要点1\n').font.name = 'Courier New'
    board_para.add_run('│   ├─ 子要点1.1\n').font.name = 'Courier New'
    board_para.add_run('│   └─ 子要点1.2\n').font.name = 'Courier New'
    board_para.add_run('└─ 要点2').font.name = 'Courier New'

    # （三）课堂小结
    doc.add_heading('（三）课堂小结（3分钟）', level=2)
    doc.add_paragraph('1. 知识回顾：引导学生回顾主要知识点，强调重点和难点')
    doc.add_paragraph('2. 方法总结：总结学习方法，强调注意事项')
    doc.add_paragraph('3. 激励评价：对优秀表现给予表扬，对进步之处给予鼓励')

    # （四）布置作业
    doc.add_heading('（四）布置作业（2分钟）', level=2)
    doc.add_paragraph('1. 必做题：')
    doc.add_paragraph('  • 【基础题1】：巩固基础知识')
    doc.add_paragraph('  • 【基础题2】：练习基本技能')
    doc.add_paragraph('2. 选做题：')
    doc.add_paragraph('  • 【提高题1】：拓展思维能力')
    doc.add_paragraph('3. 实践作业：')
    doc.add_paragraph('  • 【实践任务】：联系生活实际')

    # 六、整节课学习评价
    doc.add_heading('六、整节课学习评价', level=1)
    doc.add_heading('（一）评价方式', level=2)
    doc.add_paragraph('过程性评价（60%）：课堂参与度（20%）、任务完成质量（30%）、小组合作表现（10%）')
    doc.add_paragraph('结果性评价（40%）：课堂练习正确率（20%）、作业完成质量（20%）')

    doc.add_heading('（二）评价标准', level=2)
    standard_table = doc.add_table(rows=5, cols=3)
    standard_table.style = 'Table Grid'
    headers = ['等级', '分数范围', '标准描述']
    for i, header in enumerate(headers):
        standard_table.rows[0].cells[i].text = header
        standard_table.rows[0].cells[i].paragraphs[0].runs[0].font.bold = True

    # 七、教学资源
    doc.add_heading('七、教学资源', level=1)
    doc.add_paragraph('1. 教材：【教材名称及版本】')
    doc.add_paragraph('2. 教具：多媒体课件、实物模型、实验器材、教学挂图')
    doc.add_paragraph('3. 数字化资源：智慧中小学平台资源、教学视频/动画、在线互动工具')
    doc.add_paragraph('4. 参考资料：相关书籍、学术论文、优质教案集')

    # 八、教学反思
    doc.add_heading('八、教学反思', level=1)
    doc.add_paragraph('（课后填写）')
    doc.add_paragraph('1. 教学目标达成情况：')
    doc.add_paragraph('2. 教学过程实施效果：')
    doc.add_paragraph('3. 学生学习反馈：')
    doc.add_paragraph('4. 技术应用效果：')
    doc.add_paragraph('5. 改进建议：')

    # 保存文档
    output_path = f'~/.qwenworkcn/workspace/<chatId>/outputs/{title}_教学设计.docx'
    doc.save(output_path)
    return output_path
```

## Word文档样式设置

```python
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

def set_chinese_font(run, font_name='宋体', font_size=12, bold=False):
    """设置中文字体"""
    run.font.name = font_name
    run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
    run.font.size = Pt(font_size)
    run.font.bold = bold

def add_heading_custom(doc, text, level=1):
    """添加自定义标题"""
    heading = doc.add_heading(level=level)
    run = heading.add_run(text)

    if level == 0:  # 文档标题
        set_chinese_font(run, '黑体', 18, True)
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif level == 1:  # 一级标题
        set_chinese_font(run, '黑体', 14, True)
    elif level == 2:  # 二级标题
        set_chinese_font(run, '黑体', 12, True)
    else:  # 三级标题
        set_chinese_font(run, '黑体', 12, False)

    return heading

def add_paragraph_custom(doc, text, bold=False, indent=True):
    """添加自定义段落"""
    para = doc.add_paragraph()
    run = para.add_run(text)
    set_chinese_font(run, '宋体', 12, bold)

    if indent:
        para.paragraph_format.first_line_indent = Inches(0.3)

    return para
```

## 生成并交付Word文档

> **QoderWork 适配说明**：以下为文档生成与交付的 QoderWork 规范方式，不使用 `open`/`subprocess` 自动打开，而是通过 `present_files` 工具向用户展示文件链接。

```
1. 激活 docx 内置技能（Skill 工具）
2. 把教案内容结构（上文八模块）和样式要求传递给 docx 技能
3. 生成的 .docx 保存到 ~/.qwenworkcn/workspace/<chatId>/outputs/
4. 用 present_files 工具把 .docx 文件以可点击链接形式呈现给用户
```

## 模板使用规则

1. **替换占位符**: 所有 `【占位符】` 需替换为实际内容
2. **保持结构完整**: 不得删除必要的文档结构（八模块）
3. **字体规范**: 标题使用黑体，正文使用宋体
4. **字号规范**: 文档标题18pt，一级标题14pt，正文12pt
5. **表格样式**: 使用标准表格样式，表头加粗
6. **段落缩进**: 正文段落首行缩进2字符
7. **页边距**: 上下2.54cm，左右3.17cm（标准A4）
8. **文件命名**: `{课题名称}_教学设计.docx`
9. **编号规则**: 统一使用手动输入序号（如 `1. `、`• `），**禁止使用** Word自动编号样式（`style='List Number'` 或 `style='List Bullet'`），避免重复序号问题
