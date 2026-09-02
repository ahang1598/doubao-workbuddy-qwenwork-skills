# 协商记录格式模板

> criminal-plea-negotiation | DOCX 模板 | v2.1.0
> 排版规范见 docx-format-spec.md §8.3

## 模板结构

```
协商记录

时间：YYYY年MM月DD日 HH:mm
地点：[协商地点——如XX检察院XX办公室]
参与人：检察官[姓名]、辩护律师[姓名]、当事人[姓名]

协商内容：

[第1段] 辩方提出的量刑意见及依据……
[第2段] 检察院回应及理由……
[第3段] 双方达成的共识/分歧……

协商结果：[达成共识/未达成/部分达成]
[如达成] 量刑建议调整为：[具体内容]
[如未达成] 下一步计划：[具体内容]

录音录像：☐已同步录音录像 / ☐未录音录像

排版参数：
- 标题："协商记录"——黑体三号加粗
- 信息字段：楷体三号，每字段1段
- 协商内容：仿宋三号，首行缩进2字符
- checkbox：☐ / ☑（Unicode 2610 / 2611）
```

## 填写指南

| 字段 | 填写要求 | 注意事项 |
|------|---------|---------|
| 时间 | 精确到分钟 | 协商开始时间 |
| 地点 | 具体到办公室 | 便于后续核查 |
| 参与人 | 全部在场人员 | 含检察官+律师+当事人 |
| 协商内容 | 分段叙述 | 每个要点独立1段 |
| 协商结果 | 三选一 | 达成共识/未达成/部分达成 |
| 录音录像 | 必填 | 高检发〔2026〕5号第38条要求 |

## 关键注意事项

1. **同步录音录像为强制要求**（高检发〔2026〕5号第38条）：量刑沟通、听取意见、签署具结书应当同步录音录像
2. **协商记录不是法律文书**：仅作为律师工作记录，不具有法律效力
3. **如实记录**：无论协商是否成功，均应如实记录
4. **保密义务**：协商记录涉及当事人隐私，不得向无关方披露
5. **具结书签署须标注录音录像状态**：未录音录像属程序违规

## python-docx 渲染提示

```python
from docx import Document

def create_negotiation_record(doc, record_data):
    """创建协商记录
    
    record_data = {
        "time": "2026年6月12日 14:30",
        "location": "XX检察院第三检察部办公室",
        "participants": "检察官张XX、辩护律师李XX、当事人王XX",
        "content": [
            "辩方提出的量刑意见及依据……",
            "检察院回应及理由……",
            "双方达成的共识/分歧……"
        ],
        "result": "部分达成",
        "adjustment": "量刑建议从8-10年调整为6-8年",
        "recording": True
    }
    """
    # 标题
    title = doc.add_paragraph("协商记录")
    # 黑体三号加粗
    
    # 信息字段
    doc.add_paragraph(f"时间：{record_data['time']}")
    doc.add_paragraph(f"地点：{record_data['location']}")
    doc.add_paragraph(f"参与人：{record_data['participants']}")
    
    # 协商内容
    doc.add_paragraph("协商内容：")
    for para in record_data["content"]:
        doc.add_paragraph(para)
    
    # 协商结果
    doc.add_paragraph(f"协商结果：{record_data['result']}")
    if record_data.get("adjustment"):
        doc.add_paragraph(f"量刑建议调整为：{record_data['adjustment']}")
    
    # 录音录像
    recording_status = "☑已同步录音录像" if record_data["recording"] else "☐未录音录像"
    doc.add_paragraph(f"录音录像：{recording_status}")
```
