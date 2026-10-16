"""学术示意图范式「对照」：同一结构左右两面板，只改变一个条件（未治疗 vs 阻断、野生型 vs 突变、正常 vs 疾病）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # skill 根目录；复制到工作目录后改成绝对路径

from scripts.svg_lib.svg_drawing import Drawing, cell_interface, legend_row

INK, MAIN, ACC, ACT, MUTE = "#2A1A4A", "#5B1061", "#C0392B", "#2A6F4E", "#7A7A7A"


def build():
    d = Drawing(1000, 460)
    for tag, cx, title, blocked in [("A", 250, "未治疗：PD-1 结合 PD-L1", False), ("B", 750, "抗 PD-1 阻断后", True)]:
        d.text_at((cx - 230, 20), f"{tag}  {title}", font_size=20, font_weight="bold", fill=INK, anchor="start")
        pair = {"top": "PD-1", "bottom": "PD-L1", "color": MAIN, "ligand_color": ACC}
        if blocked:
            pair["blocked_by"] = "抗 PD-1"
        syn = d.place(
            cell_interface(
                [{"top": "TCR", "bottom": "pMHC"}, pair],
                width=420,
                gap=56,
                font_size=15,
                top_label="T 细胞",
                bottom_label="肿瘤细胞",
                top_color="#3A5A8C",
                bottom_color="#A34450",
            ),
            at=(cx, 290),
            key=f"syn{tag}",
        )
        sig = d.box_at(
            (cx, 80),
            "TCR 信号恢复 → 杀伤" if blocked else "SHP-2 去磷酸化 TCR 信号",
            font_size=16,
            fill="#E6F1EB" if blocked else "#F3EEF8",
            stroke=ACT if blocked else MAIN,
            key=f"sig{tag}",
        )
        d.arrow(
            syn.port("top1_base"),
            sig,
            stroke=MUTE if blocked else ACC,
            head="arrow" if blocked else "inhibit",
            dashed=blocked,
            stroke_width=2.5,
            route="orthogonal",
            key=f"link{tag}",
        )
    d.line((500, 40), (500, 430), stroke="#C9C4D2", stroke_width=1.5)
    d.place(
        legend_row([("arrow", "激活", ACT), ("inhibit", "抑制", ACC), ("dashed", "解除抑制", MUTE)], font_size=14),
        at=(20, 445),
        anchor="left",
        key="lg",
    )
    return d


if __name__ == "__main__":
    d = build()
    print(d.check())
    d.preview("compare_panels.png")
    # 写入：publish_slide(page_xml, d.to_slide(x=40, y=96, width=880), presentation=DECK, page=N, screenshot=False)
