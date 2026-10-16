"""场景模板「膜 + 跨膜转运蛋白通路」：两层膜（质膜 / 液泡膜）上的转运蛋白与离子流向。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # skill 根目录；复制到工作目录后改成绝对路径

from scripts.svg_lib.svg_drawing import Drawing, membrane, transporter, cytokine, legend_row

INK, PM, TONO, NA = "#1F2A44", "#8A7BB8", "#5E9E57", "#2E6FB0"


def build():
    d = Drawing(1000, 470)
    d.text_at(
        (20, 22), "植物根细胞耐盐：Na⁺ 排出胞外、区隔进液泡", font_size=20, font_weight="bold", fill=INK, anchor="start"
    )
    Y_PM, Y_TONO = 150, 320
    d.add("pm", membrane(f"M 150 {Y_PM} L 960 {Y_PM}", color=PM, thickness=22))
    d.add("tono", membrane(f"M 150 {Y_TONO} L 960 {Y_TONO}", color=TONO, thickness=22))
    for y, text in ((70, "胞外"), (Y_PM, "质膜"), (235, "胞质"), (Y_TONO, "液泡膜"), (405, "液泡")):
        d.text_at((20, y), text, font_size=15, fill=INK, anchor="start")
    # 质膜：H⁺-ATP 酶建立质子梯度，SOS1（Na⁺/H⁺ 反向转运体）借梯度把 Na⁺ 排出；HKT1 让 Na⁺ 进入
    ha = d.place(transporter("pump", ions=("H⁺",), direction="out", atp=True), at=(290, Y_PM), anchor="tail", key="ha")
    sos1 = d.place(
        transporter("antiporter", ions=("Na⁺", "H⁺"), direction="out"), at=(560, Y_PM), anchor="tail", key="sos1"
    )
    hkt = d.place(transporter("channel", ions=("Na⁺",)), at=(820, Y_PM), anchor="tail", key="hkt")
    # 液泡膜在胞质下方：flip=True 让 out（液泡腔侧）朝下；NHX 把 Na⁺ 区隔进液泡，TIP 水通道蛋白调节膨压
    nhx = d.place(
        transporter("antiporter", ions=("Na⁺", "H⁺"), direction="out", flip=True),
        at=(560, Y_TONO),
        anchor="tail",
        key="nhx",
    )
    tip = d.place(transporter("aquaporin", ions=("H₂O",), flip=True), at=(290, Y_TONO), anchor="tail", key="tip")
    na_out = d.place(cytokine(4, r=6, color=NA), at=(470, 62), key="na_out")
    na_cyt = d.place(cytokine(3, r=6, color=NA), at=(860, 250), key="na_cyt")
    na_vac = d.place(cytokine(4, r=6, color=NA), at=(470, 410), key="na_vac")
    d.arrow(hkt.port("in"), na_cyt, stroke=NA, dashed=True, stroke_width=2.2)
    d.arrow(sos1.port("ion_out0"), na_out, stroke=NA, stroke_width=2.6)
    d.arrow(nhx.port("ion_out0"), na_vac, stroke=NA, stroke_width=2.6)
    d.callout("c1", "H⁺-ATP 酶", ha.port("out"), at=(200, 62), font_size=15)
    d.callout("c2", "SOS1：Na⁺/H⁺ 反向转运", sos1.anchor("bottom"), at=(600, 250), font_size=15)
    d.callout("c3", "HKT1 通道", hkt.port("out"), at=(880, 50), font_size=15)
    d.callout("c4", "NHX：Na⁺ 进液泡", nhx.anchor("right"), at=(720, 400), font_size=15)
    d.callout("c5", "TIP 水通道蛋白", tip.anchor("left"), at=(150, 400), font_size=15)
    d.place(
        legend_row([("arrow", "主动转运", NA), ("dashed", "被动进入", NA)], font_size=14),
        at=(20, 452),
        anchor="left",
        key="lg",
    )
    return d


if __name__ == "__main__":
    d = build()
    print(d.check(), d.review())
    d.preview("membrane_transport.png")
    # 写入：publish_slide(page_xml, d.to_slide(x=40, y=90, width=880), presentation=DECK, page=N, screenshot=False)
