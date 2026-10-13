# -*- coding: utf-8 -*-
"""律师函本地 Word 生成器（阶段六兜底，无需 docx skill）。

读取一份 JSON 数据，产出格式规范的律师函 .docx，覆盖三类函件通用结构：
律所抬头 / 标题 / 发函号 / 摘要 / 委托声明 / 基本事实 / 法律分析(三段论) /
法律意见(诉求) / 声明结语 / 联系方式 / 落款 / 附件 / 待补充信息清单。

特性：
- 跨平台字体 fallback：正文=宋体，标题=黑体（避免"方正小标宋简体"在 mac/linux 静默走样）。
- 金额自动配中文大写（调用同目录 amount_cn.py）。
- 缺失字段自动填 `【待补充：字段名】` 并汇总到文末「待补充信息清单」。
- 是否示例稿由 is_sample 控制，为真时文首标注"示例稿·主体虚构"。

用法：
    python3 gen_letter_docx.py <数据.json> <输出.docx>

JSON 字段（均可选，缺失即占位）：
{
  "is_sample": true,                     // 是否示例稿
  "law_firm": "浙江正衡律师事务所",       // 律所全称
  "letter_no": "〔2026〕正衡律函字第0136号",
  "letter_type": "催告协商类|警告震慑型|权利声明型",
  "subject": "催告支付……欠付款项",        // 摘要事项
  "recipient": "宁波海拓贸易有限公司（法定代表人：李强）",
  "client": "杭州云溪网络科技有限公司",
  "lawyer": "张明",
  "matter": "贵公司拖欠软件系统采购款一事",
  "facts": ["段落1", "段落2"],            // 基本事实，逐段
  "legal_major": "法律规范（大前提）",
  "legal_minor": "本案中……（小前提）",
  "legal_conclusion": "因此……（结论）",
  "demands": ["诉求1", "诉求2"],          // 法律意见/诉求条目
  "amounts": [{"label":"所欠合同价款","value":250000},
              {"label":"逾期违约金","value":8250}],  // 自动求和+大写
  "deadline_days": 7,
  "consequence": "逾期未履行的后果告知……",
  "payee": {"name":"","bank":"","account":""},  // 收款账户（可选）
  "contact": {"lawyer":"张明","phone":"","email":"","addr":"","zip":""},
  "date": "2026年7月20日",
  "attachments": ["《合同》复印件1份", "转账凭证1份"]
}
"""
import sys, os, json
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from amount_cn import to_cn_upper
except Exception:
    def to_cn_upper(x):
        return "【金额大写转换不可用】"

from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

BODY_FONT = "宋体"      # 跨平台通用正文字体
TITLE_FONT = "黑体"     # 跨平台通用标题字体（替代方正小标宋简体）

_missing = []  # 收集占位字段


def ph(value, field):
    """缺失即返回占位符并登记。"""
    if value in (None, "", [], {}):
        tag = f"【待补充：{field}】"
        _missing.append(field)
        return tag
    return value


def _set_font(run, name, size=None, bold=False):
    run.font.name = name
    run.font.bold = bold
    if size:
        run.font.size = Pt(size)
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = rpr.makeelement(qn('w:rFonts'), {})
        rpr.append(rfonts)
    rfonts.set(qn('w:eastAsia'), name)


def build(data: dict, out_path: str):
    doc = Document()
    normal = doc.styles['Normal']
    normal.font.name = BODY_FONT
    normal.element.rPr.rFonts.set(qn('w:eastAsia'), BODY_FONT)
    normal.font.size = Pt(12)

    def para(text, align=WD_ALIGN_PARAGRAPH.LEFT, bold=False, size=12,
             font=BODY_FONT, indent=True, space_after=6):
        p = doc.add_paragraph()
        p.alignment = align
        if indent and align == WD_ALIGN_PARAGRAPH.LEFT:
            p.paragraph_format.first_line_indent = Pt(24)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.5
        r = p.add_run(text)
        _set_font(r, font, size=size, bold=bold)
        return p

    # 示例稿标注
    if data.get("is_sample"):
        para("（本文为示例稿，主体信息均为虚构，正式使用前请替换为真实信息）",
             align=WD_ALIGN_PARAGRAPH.CENTER, size=10, indent=False, space_after=4)

    # 律所抬头 + 标题
    para(ph(data.get("law_firm"), "律所全称"), align=WD_ALIGN_PARAGRAPH.CENTER,
         bold=True, size=18, font=TITLE_FONT, indent=False, space_after=4)
    para("律师函", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=22,
         font=TITLE_FONT, indent=False, space_after=8)

    # 发函号
    para(ph(data.get("letter_no"), "发函编号"), align=WD_ALIGN_PARAGRAPH.RIGHT,
         bold=True, size=11, indent=False, space_after=6)

    # 摘要
    para(f"关于{ph(data.get('subject'), '主张事项')}之事宜", bold=True, size=13,
         indent=False, space_after=4)
    para(f"致：{ph(data.get('recipient'), '收件人全称')}", bold=True, size=13,
         indent=False, space_after=10)

    # 委托声明
    firm = ph(data.get("law_firm"), "律所全称")
    client = ph(data.get("client"), "委托人全称")
    lawyer = ph(data.get("lawyer"), "承办律师姓名")
    matter = ph(data.get("matter"), "委托事项")
    para(f"{firm}（以下称“本所”）系依法在中华人民共和国设立的从事法律服务的专业机构。"
         f"本所受{client}（以下称“委托人”）的委托，指派{lawyer}律师就{matter}，"
         f"根据委托人提供的案件材料，依据事实与法律向贵方致函如下：")

    # 一、基本事实
    para("一、基本事实", bold=True, indent=False, space_after=4)
    facts = data.get("facts") or []
    if not facts:
        para(ph(None, "基本事实（时间线/合同/违约情节）"))
    for f in facts:
        para(f)

    # 二、法律分析（三段论）
    para("二、法律分析", bold=True, indent=False, space_after=4)
    para(ph(data.get("legal_major"), "大前提·法律规范"))
    para(ph(data.get("legal_minor"), "小前提·案件事实代入"))
    para(ph(data.get("legal_conclusion"), "结论·法律观点"))

    # 三、法律意见（诉求 + 金额）
    para("三、法律意见", bold=True, indent=False, space_after=4)
    days = data.get("deadline_days", "【待补充：履行期限天数】")
    if days == "【待补充：履行期限天数】":
        _missing.append("履行期限天数")
    para(f"本所现要求贵方在收到本函之日起{days}日内履行下列事项：")
    demands = data.get("demands") or []
    if not demands:
        para(ph(None, "具体诉求条目"), indent=False)
    for i, d in enumerate(demands, 1):
        para(f"{i}. {d}", indent=False, space_after=2)

    # 金额汇总
    amounts = data.get("amounts") or []
    if amounts:
        total = 0
        for a in amounts:
            v = a.get("value", 0)
            total += v
            para(f"· {a.get('label','款项')}：人民币{v:,.2f}元（大写：{to_cn_upper(v)}）",
                 indent=False, space_after=2)
        para(f"合计：人民币{total:,.2f}元（大写：{to_cn_upper(total)}）。",
             bold=True, indent=False, space_after=6)

    # 收款账户
    payee = data.get("payee") or {}
    if any(payee.values()):
        para("收款账户：", indent=False, space_after=2)
        para(f"户名：{payee.get('name','【待补充：户名】')}　"
             f"开户行：{payee.get('bank','【待补充：开户行】')}　"
             f"账号：{payee.get('account','【待补充：账号】')}",
             indent=False, space_after=6)

    # 后果告知
    para(ph(data.get("consequence"), "逾期后果告知"))

    # 声明结语
    para("本律师函所依据的事实及证据系由委托人提供，委托人已承诺对其真实性、完整性、准确性负责。"
         "贵方如对本函涉及事实有异议，或对问题解决有其他建议，请直接与本所律师联系沟通。"
         "本律师函不得被理解为委托人对其权利的放弃或对其义务的增加。")
    para("特此函告！", bold=True, indent=False, space_after=12)

    # 联系方式
    c = data.get("contact") or {}
    para(f"经办律师：{c.get('lawyer', lawyer)}律师　电话：{c.get('phone','【待补充：电话】')}　"
         f"邮箱：{c.get('email','【待补充：邮箱】')}", indent=False, space_after=2)
    para(f"地址：{c.get('addr','【待补充：律所地址】')}　邮编：{c.get('zip','【待补充：邮编】')}",
         indent=False, space_after=16)

    # 落款
    for line in [firm + "（公章）", f"经办律师：{lawyer}（签名）",
                 ph(data.get("date"), "发函日期")]:
        para(line, align=WD_ALIGN_PARAGRAPH.RIGHT, indent=False, space_after=2)

    # 附件
    atts = data.get("attachments") or []
    if atts:
        para("附件：", bold=True, indent=False, space_after=2)
        for i, a in enumerate(atts, 1):
            para(f"{i}. {a}", indent=False, space_after=2)

    # 待补充清单
    if _missing:
        doc.add_page_break()
        para("⚠️ 待补充信息清单（正式使用前必须补齐）", bold=True, size=14,
             font=TITLE_FONT, indent=False, space_after=6)
        for i, m in enumerate(dict.fromkeys(_missing), 1):  # 去重保序
            para(f"{i}. {m}", indent=False, space_after=2)

    doc.save(out_path)
    return out_path, list(dict.fromkeys(_missing))


def main():
    if len(sys.argv) < 3:
        print("用法: python3 gen_letter_docx.py <数据.json> <输出.docx>")
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as fp:
        data = json.load(fp)
    out, missing = build(data, sys.argv[2])
    print("SAVED:", out)
    if missing:
        print("待补充字段:", "、".join(missing))
    else:
        print("信息完整，无待补充字段。")


if __name__ == "__main__":
    main()
