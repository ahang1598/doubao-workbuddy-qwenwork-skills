"""学术示意图范式「全景 + 局部放大」：左侧整体结构交代位置，右侧放大关键界面讲机制。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # skill 根目录；复制到工作目录后改成绝对路径

from scripts.svg_lib.svg_drawing import Drawing, battery_cell, interface_section, legend_row

INK, ACC = "#0F2E33", "#C2457A"


def build():
    d = Drawing(1000, 460)
    d.text_at((20, 20), "A  全电池结构", font_size=20, font_weight="bold", fill=INK, anchor="start")
    d.text_at((540, 20), "B  快充析锂：负极 | 电解液界面", font_size=20, font_weight="bold", fill=INK, anchor="start")
    bat = d.place(battery_cell(380, 220, direction="charge", font_size=14), at=(240, 230), key="bat")
    sx, _ = d.resolve(bat.port("separator"))
    ax, ay = d.resolve(bat.port("anode"))
    win = d.rect_at(
        ((sx + ax) / 2, ay),
        (ax - sx) * 0.9,
        110,
        fill="none",
        stroke=ACC,
        stroke_width=2,
        stroke_dasharray="6 4",
        key="win",
    )
    sec = d.place(
        interface_section(
            [
                ("电解液 / 隔膜", 150, "#EAF3FA"),
                ("SEI", 18, "#B9A27C", "mosaic"),
                ("石墨负极", 110, "#5E7FB8", "polycrystal"),
            ],
            length=300,
            stack="right",
            font_size=14,
            features=[("dendrite", 1, 0.4, -140), ("crack", 1, 0.8, -30), ("flux", 0, 0.15, 44, {"label": "Li⁺"})],
        ),
        at=(760, 240),
        key="sec",
    )
    box = d.rect_at((760, 240), 300, 320, fill="none", stroke=ACC, stroke_width=2, key="box")
    d.line(win.anchor("top_right"), box.anchor("top_left"), stroke=ACC, stroke_width=1.2, dashed=True)
    d.line(win.anchor("bottom_right"), box.anchor("bottom_left"), stroke=ACC, stroke_width=1.2, dashed=True)
    d.callout("tip", "析出锂枝晶伸向隔膜", sec.port("dendrite0_tip"), at=(830, 410), font_size=15)
    d.callout("gap", "SEI 破裂、反复修复", sec.port("crack0_mouth"), at=(560, 410), font_size=15)
    d.place(legend_row([("box", "放大区域", ACC)], font_size=14), at=(20, 445), anchor="left", key="lg")
    return d


if __name__ == "__main__":
    d = build()
    print(d.check())
    d.preview("overview_zoom.png")
    # 写入：publish_slide(page_xml, d.to_slide(x=40, y=96, width=880), presentation=DECK, page=N, screenshot=False)
