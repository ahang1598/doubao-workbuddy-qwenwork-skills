---
name: "patent-packager"
description: "专利申报材料打包与交付。当需要将交底书、幻觉检查交付物、溯源索引、附图等打包为申报材料包时调用。"
allowed-tools: Read, Write, Bash, Glob

version: "2.0.1"
---

# 申报打包器

## 一、适用场景

- 交底书及所有附属文件撰写完成后的最终打包
- 需要按规范目录结构组织申报材料
- 需要生成ZIP包供提交或存档

## 二、标准目录结构

```
上报材料打包/
├── 01_交底书/
│   ├── [专利名称].md              # 交底书MD源文件
│   ├── [专利名称].docx            # 交底书Word文档
│   └── cnipa_ai_input.txt         # CNIPA电子申报输入文件
├── 02_幻觉检查交付物/
│   ├── 交付物1_引用捕捞清单.md
│   ├── 交付物2_工具初筛报告.md
│   ├── 交付物3_三合一缩表.md
│   ├── 交付物4_人工抽查备忘录.md
│   └── 交付物5_零幻觉验收报告.md
├── 03_溯源与框架/
│   ├── 索引溯源系统.md
│   ├── Johari_Window_思维框架.md
│   └── 交底书修订对话记录.md
├── 04_附图/
│   ├── system_architecture.png    # 系统架构图
│   ├── invasion_flow.png          # 入侵检测流程图
│   └── spycam_flow.png            # 防偷拍流程图
└── 上报材料打包.zip                # 最终ZIP包
```

## 三、打包流程

### 3.1 文件筛选原则

**只打包最终版本，排除中间版本**：
- 同一交底书的多个时间戳版本 → 只保留最新
- 同一DOCX的多个迭代 → 只保留最终
- 临时脚本（replace_checkboxes.py等） → 不打包

### 3.2 打包脚本模板

```python
import shutil
import os

def package_files(src_dir, dst_dir, patent_name):
    """打包专利申报材料"""

    # 清理并创建目录
    if os.path.exists(dst_dir):
        shutil.rmtree(dst_dir)
    os.makedirs(dst_dir)

    # 创建子目录
    subdirs = ['01_交底书', '02_幻觉检查交付物', '03_溯源与框架', '04_附图']
    for d in subdirs:
        os.makedirs(os.path.join(dst_dir, d))

    # 1. 交底书
    copy_file(src_dir, f'{patent_name}.md',
              dst_dir, '01_交底书')
    copy_file(src_dir, f'{patent_name}.docx',
              dst_dir, '01_交底书')

    # 2. 幻觉检查交付物（5份）
    for i in range(1, 6):
        fname = get_delivery_name(i)
        copy_file(src_dir, fname, dst_dir, '02_幻觉检查交付物')

    # 3. 溯源与框架
    copy_file(src_dir, '索引溯源系统.md', dst_dir, '03_溯源与框架')
    copy_file(src_dir, 'Johari_Window_思维框架.md', dst_dir, '03_溯源与框架')
    copy_file(src_dir, '交底书修订对话记录.md', dst_dir, '03_溯源与框架')

    # 4. 附图
    figures_src = os.path.join(src_dir, 'figures')
    for f in os.listdir(figures_src):
        shutil.copy2(os.path.join(figures_src, f),
                     os.path.join(dst_dir, '04_附图', f))

    # 打包为ZIP
    shutil.make_archive(dst_dir, 'zip', dst_dir)

    # 统计输出
    print_stats(dst_dir)
```

### 3.3 交付物文件名映射

```python
def get_delivery_name(index):
    names = {
        1: '交付物1_引用捕捞清单.md',
        2: '交付物2_工具初筛报告.md',
        3: '交付物3_三合一缩表.md',
        4: '交付物4_人工抽查备忘录.md',
        5: '交付物5_零幻觉验收报告.md',
    }
    return names.get(index)
```

## 四、打包后自检

```
□ ZIP包可正常解压
□ 交底书MD和DOCX都在01_交底书目录
□ 5份交付物都在02_幻觉检查交付物目录
□ 索引溯源系统和Johari框架在03_溯源与框架目录
□ 所有附图在04_附图目录
□ 无中间版本文件混入
□ 无临时脚本文件混入
```

## 五、本项目实战数据

| 项目 | 数值 |
|------|------|
| 最终文件数 | 14个 |
| 总文件大小 | 1,560 KB |
| ZIP包大小 | 1,409 KB |
| 交底书MD | 77.8 KB |
| 交底书DOCX | 847.3 KB |
| 附图 | 3张PNG（561.7 KB） |
| 交付物 | 5份MD（31.4 KB） |
| 框架文件 | 3份MD（34.9 KB） |

## 六、输入输出定义

### 输入
| 参数 | 类型 | 说明 |
|------|------|------|
| 最终交底书 | file | 修复后的交底书MD和DOCX |
| 幻觉检查交付物 | files | 5份交付物 |
| 溯源索引系统 | file | 索引溯源系统.md |
| 附图 | files | 系统架构图、流程图等 |

### 输出
| 参数 | 类型 | 说明 |
|------|------|------|
| 上报材料打包.zip | file | 按规范目录结构打包的ZIP文件 |
| 打包清单 | list | 包含的文件清单及大小 |

## 七、人机交互节点

| 节点 | 位置 | 用户操作 | 通过条件 |
|------|------|----------|----------|
| 最终验收（关卡C） | 打包清单输出后 | 确认打包清单无误 | 用户确认通过 |

## 八、工具局限性与Workaround

| 局限性 | 影响 | Workaround | 实战经验 |
|--------|------|------------|----------|
| 中间版本文件混入打包 | 同一交底书多个时间戳版本 | 只保留最新时间戳版本；打包前核对文件列表 | 本项目目录中有多个中间版本 |
| PowerShell变量符号被环境吃掉 | 脚本中$变量无法传递 | 用Python脚本替代PowerShell | 打包脚本用Python完成 |
| ZIP包中文文件名乱码 | 部分解压工具不支持UTF-8文件名 | 用ASCII文件名或7-Zip解压 | 本项目ZIP用英文目录名 |
| DOCX文件可能需重新生成 | 修复MD后DOCX未同步更新 | 每次MD修复后重新生成DOCX | 本项目修复URL后DOCX需更新 |

**核心原则**：打包前必须确认所有文件是最新版本，MD修改后必须重新生成DOCX。

## 九、国知局系统上报材料PDF核查（2026年实战经验融入）

### 9.1 上报材料PDF清单（7份标准文件）

| 序号 | 文件名 | 内容 | 页数 |
|------|--------|------|------|
| 1 | 发明专利请求书 | 申请人/发明人/代理人信息 | 4页 |
| 2 | 权利要求书 | 独立+从属权利要求 | 1页 |
| 3 | 说明书 | 5个标准章节 | 3页 |
| 4 | 说明书附图 | 图1/图2/图3 | 3页 |
| 5 | 说明书摘要 | ≤300字技术要点 | 1页 |
| 6 | 实质审查请求书 | 实质审查请求 | 1页 |
| 7 | 其他证明文件 | 费减备案证明等 | 视情况 |

### 9.2 PDF内容自动化核查脚本

```python
# PyMuPDF（fitz）PDF内容核查脚本
import fitz  # PyMuPDF

def extract_pdf_content(pdf_path):
    """
    提取PDF文本内容（解决GB18030编码乱码）
    注意：pdfplumber对国知局PDF中文提取乱码，必须用PyMuPDF
    """
    doc = fitz.open(pdf_path)
    content = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        content.append(f"=== 第{page_num+1}页 ===\n{text}")
    doc.close()
    return "\n".join(content)

def check_pdf_completeness(pdf_dir):
    """批量核查上报材料PDF"""
    import os
    results = {}
    for filename in os.listdir(pdf_dir):
        if filename.endswith('.pdf'):
            pdf_path = os.path.join(pdf_dir, filename)
            content = extract_pdf_content(pdf_path)
            results[filename] = {
                'pages': content.count('=== 第'),
                'has_content': len(content) > 100,
                'content_preview': content[:200]
            }
    return results
```

### 9.3 核查要点清单

| 检查项 | 检查方法 | 常见问题 |
|--------|---------|---------|
| 发明名称一致性 | 5份文件标题完全一致 | 摘要或附图标题不一致 |
| 发明人身份证号 | 请求书中已填写 | 2026年新规，漏填被退回 |
| 申请人地址完整性 | 含省/市/区/街道/门牌号 | 只到区级被退回 |
| 权利要求项数 | 与请求书声明一致 | PDF提取错误显示截断 |
| 附图编号连续 | 图1/图2/图3 | 编号跳跃或重复 |
| 摘要字数 | ≤300中文字 | 超限被退回 |
| 段落编号连续 | [0001]-[00NN]无跳跃 | 编号断裂 |

### 9.4 PDF提取工具选型（核心红线）

```
✅ 推荐工具：PyMuPDF（fitz）
   - 安装：pip install PyMuPDF
   - 优势：正确提取GB18030编码中文
   - 优势：保留页面结构，支持批量处理

❌ 禁用工具：pdfplumber
   - 问题：对国知局PDF中文提取全部乱码（mojibake）
   - 原因：国知局PDF使用GB18030编码，pdfplumber默认UTF-8解码
   - 实测：提取的中文全部显示为"锛堢敳锛"等乱码
```

### 9.5 实战经验记录

> **案例**：本项目上报7份PDF，初始用pdfplumber提取核查，中文全部乱码（GB18030编码问题）。改用PyMuPDF（fitz）后正确提取，完成逐页逐字段核查。
>
> **核查发现的问题**：
> 1. 申请人地址只到"黄陂区"缺街道门牌号 → 已修正
> 2. 发明人(2)(3)勾选"不公布姓名"但实际只有1个发明人 → 需手动去掉
> 3. 实质审查请求书PCT备注字段非PCT申请 → 系统固定模板，不影响审查
>
> **核心教训**：国知局PDF必须用PyMuPDF提取，pdfplumber会乱码。打包后必须逐页核查，不能只看文件名。

## 十、打包清单完整性校验（2026年实战经验融入）

### 10.1 上报材料完整清单

```
□ 发明专利请求书（含申请人/发明人/代理人/地址/身份证号）
□ 权利要求书（独立+从属，无插图）
□ 说明书（5个标准章节，段落编号连续）
□ 说明书附图（白底黑线，JPEG/TIFF，300DPI）
□ 说明书摘要（≤300字，指定摘要附图）
□ 实质审查请求书（非PCT申请无PCT备注）
□ 费减备案证明（如请求费减）
□ 其他证明文件（视情况）
```

### 10.2 费减备案材料清单

```
□ 费减备案号（先备案再申请）
□ 企业所得税年度纳税申报表封面（A类2017版，盖公章）
□ 企业所得税年度纳税申报主表 A100000
□ 企业所得税年度纳税申报基础信息表 A000000
□ 上年度应纳税所得额≤300万元（小型微利企业标准）
```

### 10.3 逻辑一致性校验

| 校验项 | 校验逻辑 | 错误示例 |
|--------|---------|---------|
| 费减备案号 vs 请求书 | 请求书勾选费减则必须有备案号 | 勾选费减但无备案号 |
| 发明人数量 vs 请求书 | 实际发明人数=请求书发明人位置数 | 实际1人但请求书有3个位置 |
| 附图编号 vs 附图说明 | 说明书附图说明与实际附图编号一致 | 说明书写图1-5但只有3张图 |
| 摘要附图 vs 说明书附图 | 摘要指定附图必须在说明书附图中 | 摘要指定图1但附图无图1 |

## 可选工具与参考文档（使用者按需调用）

> 以下工具和参考文档已集成到本skill目录中，使用者根据需要决定是否调用。不需要就跳过，需要就调用。

### 工具脚本（tools/目录）

| 工具 | 来源 | 用途 | 调用方式 |
|------|------|------|----------|
| `build_patent_package.py` | nature-paper-to-patent | 专利申请包构建（从draft.json生成完整申请包） | `python tools/build_patent_package.py draft.json --output-dir outputs --prefix patent` |
| `render_patent_docx.py` | nature-paper-to-patent | 专利DOCX渲染（权利要求书/说明书/摘要独立DOCX） | `python tools/render_patent_docx.py draft.json --output-dir outputs` |
