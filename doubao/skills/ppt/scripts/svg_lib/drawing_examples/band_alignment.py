"""场景模板「能带排列对照」：同一对半导体，左右两面板只改变电荷转移路径（type-II vs S 型 / Z 型）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # skill 根目录；复制到工作目录后改成绝对路径

from scripts.svg_lib.svg_drawing import Drawing, energy_diagram

INK = "#1F2A44"
A = {"name": "半导体 A", "cb": -0.3, "vb": 2.9, "color": "#4A7EBB"}
B = {"name": "半导体 B", "cb": -1.1, "vb": 1.6, "color": "#D9822B"}
REFS = [("H⁺/H₂", 0.0), ("O₂/H₂O", 1.23)]


def build():
    d = Drawing(1300, 600)
    panels = [
        ("A", "type-II：e⁻ 与 h⁺ 分到两侧", dict(transfer="type2"), {"cb_text": "还原"}, {"vb_text": "氧化"}),
        ("B", "S 型：弱 e⁻/h⁺ 在界面复合", dict(transfer="s"), {"vb_text": "氧化"}, {"cb_text": "还原"}),
    ]
    for i, (tag, title, kw, extra_a, extra_b) in enumerate(panels):
        cx = 325 + i * 650
        g = energy_diagram(
            [{**A, **extra_a}, {**B, **extra_b}], ref_levels=REFS, font_size=17, band_width=130, height=300, **kw
        )
        ed = d.place(g, at=(cx, 330), key=f"bands{tag}")
        d.text_at((ed.bounds.x, 24), f"{tag}  {title}", font_size=20, font_weight="bold", fill=INK, anchor="start")
    d.line((650, 50), (650, 580), stroke="#C9C4D2", stroke_width=1.5)
    return d


if __name__ == "__main__":
    d = build()
    print(d.check())
    d.preview("band_alignment.png")
    # 写入：publish_slide(page_xml, d.to_slide(x=40, y=96, width=880), presentation=DECK, page=N, screenshot=False)
