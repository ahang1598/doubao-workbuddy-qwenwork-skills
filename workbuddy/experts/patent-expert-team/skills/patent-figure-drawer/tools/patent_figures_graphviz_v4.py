# -*- coding: utf-8 -*-
"""
专利附图生成 V4（Graphviz版，扩展至图1-图7）
沿用用户既有"专利附图生成 V3（Graphviz版）"管线与国知局合规样式
（白底黑线、JPEG/TIFF、300DPI、图号不在图片中）。
图1-3 与 V3 一致；图4-7 按本发明说明书附图说明补齐。
依赖：graphviz python 包 + 系统 Graphviz(dot)。
"""
import os
import sys
from PIL import Image
import graphviz

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "04_附图")
DPI = "300"

STYLE = {
    "bgcolor": "white",
    "fontname": "SimHei",
    "fontsize": "12",
    "color": "black",
    "fontcolor": "black",
    "penwidth": "1.2",
    "style": "filled",
    "fillcolor": "white",
    "shape": "box",
    "margin": "0.15,0.08",
}


def make_node(g, name, label, shape="box"):
    attrs = {**STYLE, "shape": shape}
    g.node(name, label, **attrs)


def make_edge(g, a, b, label="", style="solid"):
    g.edge(a, b, label=label, style=style, color="black", fontcolor="black",
           fontname="SimHei", fontsize="10", penwidth="1.2")


def new_graph(name):
    g = graphviz.Digraph(name, format="png")
    g.attr(rankdir="TB", bgcolor="white", fontname="SimHei", dpi=DPI,
           nodesep="0.4", ranksep="0.6", splines="spline")
    g.attr("node", **STYLE)
    g.attr("edge", color="black", penwidth="1.2")
    return g


# ============ 图1 系统架构图 ============
def fig1():
    g = new_graph("arch")
    with g.subgraph(name="cluster_L1") as c:
        c.attr(label="感知层", style="rounded", color="black", fontname="SimHei", fontsize="14")
        make_node(c, "S1", "CSI主模块"); make_node(c, "S2", "IMU六轴")
        make_node(c, "S3", "主动光学\n逆向反射"); make_node(c, "S4", "热成像\n/毫米波")
    with g.subgraph(name="cluster_L2") as c:
        c.attr(label="中枢处理层", style="rounded", color="black", fontname="SimHei", fontsize="14")
        make_node(c, "P1", "数据预处理"); make_node(c, "P2", "调度引擎")
        make_node(c, "C1", "CSI-IMU\n融合判定"); make_node(c, "C2", "CSI-光学\n确证")
        make_node(c, "C3", "CSI-热成像\n确证"); make_node(c, "C4", "趋势分析")
    with g.subgraph(name="cluster_L3") as c:
        c.attr(label="响应层", style="rounded", color="black", fontname="SimHei", fontsize="14")
        make_node(c, "R1", "响应执行"); make_node(c, "R2", "本地存储"); make_node(c, "R3", "云端服务器")
    with g.subgraph(name="cluster_L4") as c:
        c.attr(label="用户交互层", style="rounded", color="black", fontname="SimHei", fontsize="14")
        make_node(c, "U1", "用户设置"); make_node(c, "U2", "移动端App")
    for s in ["S1", "S2", "S3", "S4"]:
        make_edge(g, s, "P1")
    make_edge(g, "P1", "P2")
    make_edge(g, "P2", "C1", "微动异常"); make_edge(g, "P2", "C2", "射频异常")
    make_edge(g, "P2", "C3", "静止异物"); make_edge(g, "P2", "C4", "趋势")
    for c in ["C1", "C2", "C3", "C4"]:
        make_edge(g, c, "R1")
    make_edge(g, "R1", "R2"); make_edge(g, "R1", "R3")
    make_edge(g, "R1", "U1"); make_edge(g, "R3", "U2")
    make_edge(g, "U1", "P2", "配置", "dashed")
    g.render(os.path.join(OUT, "system_architecture_gv"), cleanup=True)
    print("[OK] fig1 system_architecture_gv.png")


# ============ 图2 防入侵流程图 ============
def fig2():
    g = new_graph("invasion")
    g.attr(nodesep="0.5", ranksep="0.5")
    make_node(g, "A", "系统启动")
    make_node(g, "B", "CSI低功耗监测\n(1~10Hz宏观方差)")
    make_node(g, "C", "宏观方差\n超阈值?", "diamond")
    make_node(g, "D", "唤醒全量CSI采集\n(50~200Hz)")
    make_node(g, "E", "CSI预处理\n+微动特征提取")
    make_node(g, "F", "IMU比对判定", "diamond")
    make_node(g, "G", "判定为环境噪声")
    make_node(g, "H", "自适应更新\nCSI基线")
    make_node(g, "I", "判定为外部入侵")
    make_edge(g, "A", "B"); make_edge(g, "B", "C")
    make_edge(g, "C", "B", "否", "dashed")
    make_edge(g, "C", "D", "是")
    make_edge(g, "D", "E"); make_edge(g, "E", "F")
    make_edge(g, "F", "G", "本体在动")
    make_edge(g, "G", "H"); make_edge(g, "H", "B", "基线更新", "dashed")
    make_edge(g, "F", "I", "本体静止")
    make_edge(g, "I", "B", "报警", "dashed")
    g.render(os.path.join(OUT, "invasion_flow_gv"), cleanup=True)
    print("[OK] fig2 invasion_flow_gv.png")


# ============ 图3 防偷拍流程图 ============
def fig3():
    g = new_graph("spycam")
    g.attr(nodesep="0.5", ranksep="0.5")
    make_node(g, "A", "防偷拍模式启动")
    make_node(g, "B", "CSI扫描环境\nWi-Fi/蓝牙信道")
    make_node(g, "C", "建立合法\n设备基线")
    make_node(g, "D", "发现异常信号?", "diamond")
    make_node(g, "E", "继续监测")
    make_node(g, "F", "嗅探异常\nMAC/数据流")
    make_node(g, "G", "CSI估算异常源\n区域拓扑")
    make_node(g, "H", "红光LED阵列\n定向照射")
    make_node(g, "I", "光电传感器\n捕捉逆向反光")
    make_node(g, "J", "确证偷拍器")
    make_edge(g, "A", "B"); make_edge(g, "B", "C"); make_edge(g, "C", "D")
    make_edge(g, "D", "E", "否", "dashed")
    make_edge(g, "E", "B", "重新扫描", "dashed")
    make_edge(g, "D", "F", "是")
    make_edge(g, "F", "G"); make_edge(g, "G", "H")
    make_edge(g, "H", "I"); make_edge(g, "I", "J")
    g.render(os.path.join(OUT, "spycam_flow_gv"), cleanup=True)
    print("[OK] fig3 spycam_flow_gv.png")


# ============ 图4 分级唤醒状态机图 ============
def fig4():
    g = new_graph("state")
    g.attr(nodesep="0.5", ranksep="0.7")
    make_node(g, "S0", "低功耗监测\n(1~10Hz)")
    make_node(g, "S1", "宏观方差\n阈值判断")
    make_node(g, "S2", "全量CSI采集\n(50~200Hz)")
    make_node(g, "S3", "异常检测\n与事件分类")
    make_node(g, "S4", "调度引擎\n唤醒辅助模块")
    make_node(g, "S5", "融合判定\n加权投票")
    make_node(g, "S6", "响应执行")
    make_edge(g, "S0", "S1")
    make_edge(g, "S1", "S2", "超阈值")
    make_edge(g, "S2", "S3")
    make_edge(g, "S3", "S4", "L1/L2/L3")
    make_edge(g, "S4", "S5")
    make_edge(g, "S5", "S6", "确证异常")
    make_edge(g, "S6", "S0", "确证后返回\n低功耗", "dashed")
    make_edge(g, "S3", "S0", "本体在动\n自适应更新基线", "dashed")
    g.render(os.path.join(OUT, "state_machine_gv"), cleanup=True)
    print("[OK] fig4 state_machine_gv.png")


# ============ 图5 加权投票融合逻辑图 ============
def fig5():
    g = new_graph("fusion")
    g.attr(nodesep="0.6", ranksep="0.6")
    make_node(g, "CSI", "CSI主模块\n权重 w_CSI\n置信度 C_CSI")
    make_node(g, "A1", "辅助模块1\nwi, ci, fi")
    make_node(g, "A2", "辅助模块2\nwi, ci, fi")
    make_node(g, "Ai", "辅助模块i\nwi, ci, fi")
    make_node(g, "FUS", "加权投票\n融合判定层")
    make_node(g, "FORM", "S = w_CSI·C_CSI\n+ Σ(wi·ci·fi)\nL2/L3级自适应\n动态调整权重",
              shape="box")
    for n in ["CSI", "A1", "A2", "Ai"]:
        make_edge(g, n, "FUS")
    make_edge(g, "FUS", "FORM")
    g.render(os.path.join(OUT, "weighted_fusion_gv"), cleanup=True)
    print("[OK] fig5 weighted_fusion_gv.png")


# ============ 图6 硬件中断同步时序图（HTML table） ============
def fig6():
    g = graphviz.Digraph("timing", format="png")
    g.attr(bgcolor="white", fontname="SimHei", dpi=DPI)
    g.attr("node", **STYLE)
    lane = (
        '<table border="1" cellborder="1" cellspacing="0" cellpadding="4">'
        '<tr><td colspan="7"><b>硬件中断同步时序</b></td></tr>'
        '<tr><td><b>CSI帧头</b></td><td>F1</td><td>F2</td><td>F3</td>'
        '<td>F4</td><td>F5</td><td>F6</td></tr>'
        '<tr><td><b>硬件中断</b></td><td>L1每帧</td><td>L1每帧</td><td>L1每帧</td>'
        '<td>L1每帧</td><td>L2每5帧</td><td>L1每帧</td></tr>'
        '<tr><td><b>辅助唤醒</b></td><td>—</td><td>—</td><td>唤醒</td>'
        '<td>—</td><td>—</td><td>L3按需</td></tr>'
        '</table>'
    )
    g.node("T", label=f"<{lane}>", shape="none", fillcolor="white")
    g.render(os.path.join(OUT, "interrupt_timing_gv"), cleanup=True)
    print("[OK] fig6 interrupt_timing_gv.png")


# ============ 图7 CSI信号处理流程图 ============
def fig7():
    g = new_graph("csi")
    g.attr(nodesep="0.5", ranksep="0.5")
    make_node(g, "A", "原始CSI数据\n56子载波振幅+相位矩阵")
    make_node(g, "B", "预处理\nHampel滤波去噪")
    make_node(g, "C", "特征提取\n振幅宏观方差/相位斜率/\n子载波相关性")
    make_node(g, "D", "事件分类\n(L1/L2/L3三级)", "diamond")
    make_node(g, "E", "能力等级标识输出")
    make_node(g, "F", "调度引擎决策\n唤醒辅助模块")
    make_node(g, "G", "分级降采样\n功耗优化")
    make_edge(g, "A", "B"); make_edge(g, "B", "C"); make_edge(g, "C", "D")
    make_edge(g, "D", "E"); make_edge(g, "E", "F")
    make_edge(g, "F", "G", "低功耗", "dashed")
    make_edge(g, "G", "F", "降采样", "dashed")
    g.render(os.path.join(OUT, "csi_signal_gv"), cleanup=True)
    print("[OK] fig7 csi_signal_gv.png")


def png_to_tiff(png_path):
    base = png_path[:-4]
    img = Image.open(png_path)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.save(base + ".jpg", "JPEG", quality=95, dpi=(300, 300))
    img.save(base + ".tif", "TIFF", dpi=(300, 300))
    print(f"[CONV] {os.path.basename(base)} -> jpg + tif")


def main():
    os.makedirs(OUT, exist_ok=True)
    fig1(); fig2(); fig3(); fig4(); fig5(); fig6(); fig7()
    print("[RENDER DONE] PNG 生成完毕，转 TIFF...")
    for f in ["system_architecture_gv", "invasion_flow_gv", "spycam_flow_gv",
              "state_machine_gv", "weighted_fusion_gv", "interrupt_timing_gv",
              "csi_signal_gv"]:
        p = os.path.join(OUT, f + ".png")
        if os.path.exists(p):
            png_to_tiff(p)
    print("[DONE] 图1-图7 全部生成（Graphviz V4，白底黑线 TIFF@300DPI）")


if __name__ == "__main__":
    main()
