"""Public capability registry and on-demand help; no geometry imports."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _ApiDoc:
    target: object
    topic: str
    purpose: str
    returns: str
    semantics: tuple[str, ...]
    example: str
    limits: tuple[str, ...] = ()
    common: bool = True
    style: bool = False
    rank: int = 100
    is_property: bool = False


_DRAWING_APIS: dict[str, _ApiDoc] = {}


def _drawing_api(topic, **metadata):
    def register(target):
        name = target.__qualname__.replace("SvgwriteAliases.", "Drawing.")
        if name in _DRAWING_APIS:
            raise ValueError(f"Duplicate public drawing API: {name}")
        _DRAWING_APIS[name] = _ApiDoc(target, topic=topic, **metadata)
        return target

    return register


_HELP_TOPICS = {
    "curves": (
        "曲线与轮廓",
        "平滑穿点、参数采样、截取与轮廓求交。",
        "Curve 描述一条连续路径；PathFrame 是位置/切线/法线快照。轮廓端口可用于方向化连线。",
    ),
    "shapes": (
        "基本对象与组合",
        "创建局部几何和文字。",
        "返回 Geometry，可用 Drawing.add 加入画布或导出局部 SVG；局部几何变换返回副本。",
    ),
    "repeat": ("沿路径排列", "按弧长重复或变化部件。", "路径可直接传 SVG d 字符串；需要指定采样精度时使用 Curve。"),
    "ribbon": ("带状轮廓", "构造等宽、变宽或闭合带。", ""),
    "extrude": ("轮廓厚度", "为凸轮廓生成可见侧面。", ""),
    "section": (
        "剖面与放大",
        "通过窗口裁取已有结构或纹理。",
        "cutaway 窗口可用 Box 或同坐标系的 Geometry 填充轮廓；构造结果是几何快照，不会自动生成内部结构。",
    ),
    "anchors": (
        "锚点与相对定位",
        "放置对象并建立位置绑定。",
        "Geometry=局部几何，Node=画布实例，Anchor=动态位置引用。"
        "传 Anchor 保持联动，传坐标固定位置；resolve/Node.bounds 返回快照。"
        "offset/shifted 使用画布坐标，绑定在读取边界或重新导出时计算。",
    ),
    "layout": (
        "排布",
        "行/列/网格占位、对齐分布、环形、两列配对与自动标签。",
        "返回画布坐标快照，不加入画布、不选样式；按返回位置调用 Drawing.add。"
        "ring 生成沿圆周的连接弧；bipartite_order 减少两列连线交叉；spread_ports 把同一边的多条连线错开。",
    ),
    "connect": (
        "连线与标注",
        "连接接口或添加引导标签。",
        "端点与路点可随对象更新；orthogonal 可避开指定矩形区域，bezier 支持端点法线。",
    ),
    "parts": (
        "复合部件",
        "可选的现成零件：通用对象（细胞、膜、受体、分子、晶格、器件叠层、网络层、模块框…），库里没有的自己画。",
        'style="rich" 加渐变纹理，"flat" 全原生；库里没有的对象自己画，再用 finish 专题的工具补细节。',
    ),
    "finish": (
        "精细化工具",
        "给自己画的对象补教科书级细节：任意路径的磷脂双层、球体明暗、面体渐变、重叠圆合并、同色系推导。",
        "返回画布坐标的 Geometry，用 d.add(key, geometry) 原样叠在自己画的原生形状上；渐变留在局部 SVG，底层形状仍可编辑。",
    ),
    "export": (
        "导出与写入",
        "d.to_slide(x=, y=, width=) 一步得到可编辑片段，交给 publish_slide 写入页面。",
        "publish_slide(page_xml, d.to_slide(...), chart_slide(...), presentation=deck_id)：page_xml 是带 "
        'xmlns="https://www.larkoffice.com/sml/2.0" 的单页 <slide>（标题、正文等原生元素），片段可传多个；'
        "它合页并开启服务端 lint 写入，转换内部的形状重叠自动豁免，只返回需修的问题。",
    ),
    "math": (
        "坐标与函数曲线",
        "映射数学坐标，采样并分段。",
        "CoordinateMap 处理数据到 SVG 的坐标；sample_function 返回数值快照，"
        "用 FunctionSample.to_geometry 接入现有构造。点、刻度、阈值和切线应共用映射；"
        "连续数值不能按数据列表序号均分位置。"
        "角度先明确两侧向量与正方向，图上角弧和公式使用同一坐标约定。"
        "公式、定义域、已知断点及导数由调用方确定。",
    ),
    "inspect": (
        "按需诊断",
        "查询边界、端口与转换原因。",
        "Drawing.inspect 看布局和绑定，inspect_svg 看转换决策与 Slides 选择框；均为主动查询。",
    ),
    "resources": ("SVG 资源定义", "按需加入 defs、渐变或裁切资源。", "样式由当前任务提供，没有配色主题或预制页面。"),
}


_DEFAULT_HELP_TOPICS = tuple(key for key in _HELP_TOPICS if key != "resources")


_HELP_ALIASES = {
    "诊断": "inspect",
    "检查边界": "inspect",
    "对象边界": "Drawing.inspect",
    "转换原因": "inspect_svg",
    "路点": "Drawing.connect",
    "方向连线": "Drawing.connect",
    "轮廓端口": "Node.contour_at",
    "collision": "Drawing.inspect",
    "文字换行": "wrap_label",
    "换行": "wrap_label",
    "标注位置": "Drawing.place_label",
    "标签候选": "Drawing.label_candidates",
    "自动标签": "Drawing.place_label",
    "放标签": "Drawing.place_label",
    "连线标签": "Drawing.label_connector",
    "线上标注": "Drawing.label_connector",
    "重排标签": "Drawing.relayout_labels",
    "标签检查": "Drawing.check_labels",
    "精细化": "finish",
    "质感": "finish",
    "明暗": "finish",
    "高光": "finish",
    "双分子层": "bilayer",
    "部件": "parts",
    "组件": "parts",
    "复合部件": "parts",
    "CRISPR": "duplex",
    "R-loop": "duplex",
    "双链": "duplex",
    "切口": "duplex",
    "碱基编辑": "duplex",
    "RNA": "nucleic_strand",
    "单链": "nucleic_strand",
    "gRNA": "nucleic_strand",
    "免疫突触": "cell_interface",
    "突触": "cell_interface",
    "细胞接触": "cell_interface",
    "检查点": "cell_interface",
    "配体受体": "cell_interface",
    "外膜": "cell_envelope",
    "LPS": "cell_envelope",
    "脂多糖": "cell_envelope",
    "周质": "cell_envelope",
    "肽聚糖": "cell_envelope",
    "细菌包膜": "cell_envelope",
    "细胞壁": "cell_envelope",
    "外排泵": "cell_envelope",
    "AcrAB-TolC": "cell_envelope",
    "孔蛋白": "cell_envelope",
    "转运蛋白": "transporter",
    "转运体": "transporter",
    "离子通道": "transporter",
    "离子泵": "transporter",
    "ATP酶": "transporter",
    "反向转运": "transporter",
    "同向转运": "transporter",
    "水通道": "transporter",
    "ABC转运体": "transporter",
    "植物细胞": "cell",
    "液泡": "cell",
    "液泡膜": "cell",
    "叶绿体": "cell",
    "根横切": "root_section",
    "根": "root_section",
    "凯氏带": "root_section",
    "根毛": "root_section",
    "内皮层": "root_section",
    "质外体": "root_section",
    "共质体": "root_section",
    "中柱": "root_section",
    "生物膜": "biofilm_section",
    "持留菌": "biofilm_section",
    "群体感应": "biofilm_section",
    "催化层": "layer_stack",
    "气体扩散层": "layer_stack",
    "GDL": "layer_stack",
    "流场": "layer_stack",
    "MEA": "layer_stack",
    "燃料电池": "layer_stack",
    "电解池": "layer_stack",
    "质子交换膜": "layer_stack",
    "针孔": "interface_section",
    "分层": "interface_section",
    "裂纹": "interface_section",
    "蛋白复合体": "protein_complex",
    "Cas9": "protein_complex",
    "酶": "protein_complex",
    "细胞": "cell",
    "受体": "receptor",
    "通道": "transporter",
    "膜": "membrane",
    "双层膜": "membrane",
    "原子": "atom",
    "离子": "atom",
    "晶格": "lattice",
    "层状": "lattice",
    "器件截面": "layer_stack",
    "叠层": "layer_stack",
    "颗粒": "particle",
    "晶粒": "polycrystal",
    "位错": "edge_dislocation",
    "刃位错": "edge_dislocation",
    "dislocation": "edge_dislocation",
    "孪晶": "twin_lattice",
    "孪晶界": "twin_lattice",
    "twin": "twin_lattice",
    "层错": "close_packed",
    "堆垛": "close_packed",
    "密排": "close_packed",
    "FCC": "close_packed",
    "HCP": "close_packed",
    "stacking fault": "close_packed",
    "晶界": "polycrystal",
    "多晶": "polycrystal",
    "polycrystal": "polycrystal",
    "地球": "globe",
    "极地投影": "globe",
    "急流": "jet_stream",
    "阻塞高压": "jet_stream",
    "大气剖面": "atmosphere_section",
    "极涡": "atmosphere_section",
    "珊瑚": "coral_polyp",
    "珊瑚白化": "coral_polyp",
    "虫黄藻": "symbiont",
    "共生藻": "symbiont",
    "界面": "interface_section",
    "截面": "interface_section",
    "枝晶": "interface_section",
    "空洞": "interface_section",
    "异质结截面": "interface_section",
    "腐蚀": "interface_section",
    "能带": "energy_diagram",
    "能级": "energy_diagram",
    "能带图": "energy_diagram",
    "能级图": "energy_diagram",
    "异质结": "energy_diagram",
    "能带排列": "energy_diagram",
    "能带弯曲": "energy_diagram",
    "导带": "energy_diagram",
    "价带": "energy_diagram",
    "带隙": "energy_diagram",
    "禁带": "energy_diagram",
    "费米能级": "energy_diagram",
    "功函数": "energy_diagram",
    "肖特基": "energy_diagram",
    "肖特基结": "energy_diagram",
    "pn结": "energy_diagram",
    "光催化": "energy_diagram",
    "Z型": "energy_diagram",
    "S型": "energy_diagram",
    "band": "energy_diagram",
    "band diagram": "energy_diagram",
    "CB": "energy_diagram",
    "VB": "energy_diagram",
    "Z-scheme": "energy_diagram",
    "S-scheme": "energy_diagram",
    "type-II": "energy_diagram",
    "Schottky": "energy_diagram",
    "Fermi level": "energy_diagram",
    "信号通路": "signaling_cascade",
    "通路图": "signaling_cascade",
    "级联": "signaling_cascade",
    "磷酸化": "signaling_cascade",
    "负反馈": "signaling_cascade",
    "pathway": "signaling_cascade",
    "cascade": "signaling_cascade",
    "signaling": "signaling_cascade",
    "药物靶点": "signaling_cascade",
    "肝": "liver_sinusoid",
    "肝脏": "liver_sinusoid",
    "肝窦": "liver_sinusoid",
    "Disse": "liver_sinusoid",
    "肝小叶": "liver_sinusoid",
    "星状细胞": "liver_sinusoid",
    "肝星状细胞": "liver_sinusoid",
    "HSC": "liver_sinusoid",
    "Kupffer": "liver_sinusoid",
    "库普弗细胞": "liver_sinusoid",
    "纤维化": "liver_sinusoid",
    "肝纤维化": "liver_sinusoid",
    "肌成纤维细胞": "cell",
    "范式": "trial_sequence",
    "实验范式": "trial_sequence",
    "试次": "trial_sequence",
    "n-back": "trial_sequence",
    "trial": "trial_sequence",
    "paradigm": "trial_sequence",
    "刺激序列": "trial_sequence",
    "任务流程": "trial_sequence",
    "脑网络": "brain",
    "脑连接": "brain",
    "功能连接": "brain",
    "connectivity": "brain",
    "连接组": "brain",
    "编号": "badge",
    "序号": "badge",
    "badge": "badge",
    "徽章": "badge",
    "数字圆圈": "badge",
    "脑": "brain",
    "大脑": "brain",
    "脑干": "brain",
    "孤束核": "brain",
    "神经元": "neuron",
    "神经": "neuron",
    "迷走神经": "neuron",
    "神经节": "neuron",
    "髓鞘": "neuron",
    "肠壁": "intestinal_wall",
    "绒毛": "intestinal_wall",
    "肠上皮": "intestinal_wall",
    "肠道菌群": "intestinal_wall",
    "肠内分泌细胞": "intestinal_wall",
    "心脏": "heart",
    "心室": "heart",
    "心房": "heart",
    "瓣膜": "heart",
    "肾单位": "nephron",
    "肾小球": "nephron",
    "肾小管": "nephron",
    "血脑屏障": "bbb_unit",
    "BBB": "bbb_unit",
    "神经血管单元": "bbb_unit",
    "紧密连接": "bbb_unit",
    "U-Net": "encoder_decoder",
    "UNet": "encoder_decoder",
    "TransUNet": "encoder_decoder",
    "Swin-UNet": "encoder_decoder",
    "编码器": "encoder_decoder",
    "解码器": "encoder_decoder",
    "编码器-解码器": "encoder_decoder",
    "编解码": "encoder_decoder",
    "encoder": "encoder_decoder",
    "decoder": "encoder_decoder",
    "跳跃连接": "encoder_decoder",
    "skip connection": "encoder_decoder",
    "分割网络": "encoder_decoder",
    "图像分割": "encoder_decoder",
    "下采样": "encoder_decoder",
    "上采样": "encoder_decoder",
    "CNN": "tensor_block",
    "卷积": "tensor_block",
    "特征图": "tensor_block",
    "张量": "tensor_block",
    "feature map": "tensor_block",
    "tensor": "tensor_block",
    "注意力": "transformer_block",
    "自注意力": "transformer_block",
    "attention": "transformer_block",
    "Transformer": "transformer_block",
    "patch": "patch_embed",
    "ViT": "patch_embed",
    "图像分块": "patch_embed",
    "token": "patch_embed",
    "位置编码": "patch_embed",
    "CLS": "patch_embed",
    "嵌入": "patch_embed",
    "embedding": "patch_embed",
    "土壤": "soil_aggregate",
    "团聚体": "soil_aggregate",
    "孔隙": "soil_aggregate",
    "孔隙水": "soil_aggregate",
    "沉积物": "soil_aggregate",
    "多孔介质": "soil_aggregate",
    "根际": "soil_aggregate",
    "土壤微生物": "soil_aggregate",
    "水膜": "soil_aggregate",
    "黏粒": "soil_aggregate",
    "缺氧": "soil_aggregate",
    "缺氧核心": "soil_aggregate",
    "厌氧": "soil_aggregate",
    "soil": "soil_aggregate",
    "aggregate": "soil_aggregate",
    "sediment": "soil_aggregate",
    "氧梯度": "biofilm_section",
    "O2梯度": "biofilm_section",
    "水体": "water_column_section",
    "湖泊": "water_column_section",
    "海洋剖面": "water_column_section",
    "水柱": "water_column_section",
    "温跃层": "water_column_section",
    "线圈": "coil",
    "螺线管": "coil",
    "solenoid": "coil",
    "coil": "coil",
    "环形线圈": "coil",
    "单匝线圈": "coil",
    "通电线圈": "coil",
    "电磁铁": "coil",
    "铁芯": "coil",
    "电流计": "circuit_symbol",
    "灵敏电流计": "circuit_symbol",
    "检流计": "circuit_symbol",
    "电流表": "circuit_symbol",
    "电压表": "circuit_symbol",
    "galvanometer": "circuit_symbol",
    "ammeter": "circuit_symbol",
    "voltmeter": "circuit_symbol",
    "滑动变阻器": "circuit_symbol",
    "电阻": "circuit_symbol",
    "电容": "circuit_symbol",
    "电感": "circuit_symbol",
    "电路元件": "circuit_symbol",
    "磁场": "field_marks",
    "匀强磁场": "field_marks",
    "⊗": "field_marks",
    "⊙": "field_marks",
    "垂直纸面": "field_marks",
    "磁感应强度": "field_marks",
    "field_marks": "field_marks",
    "导轨": "rails_rod",
    "导体棒": "rails_rod",
    "金属棒": "rails_rod",
    "切割磁感线": "rails_rod",
    "动生电动势": "rails_rod",
    "rail": "rails_rod",
    "rails": "rails_rod",
    "电磁感应": "rails_rod",
    "电路": "circuit_loop",
    "电路图": "circuit_loop",
    "回路": "circuit_loop",
    "RL": "circuit_loop",
    "RC": "circuit_loop",
    "RLC": "circuit_loop",
    "RL电路": "circuit_loop",
    "RC电路": "circuit_loop",
    "circuit": "circuit_loop",
    "磁铁": "magnet",
    "条形磁铁": "magnet",
    "磁感线": "magnet",
    "弹簧": "spring",
    "透镜": "lens",
    "神经网络": "nn_layer",
    "全连接": "dense_links",
    "模块框": "block",
    "流程框": "block",
    "波形": "wave",
    "信号": "wave",
    "图例": "legend_row",
    "文字框": "text_box",
    "节点框": "text_box",
    "自适应框": "text_box",
    "按文字定尺寸": "text_box",
    "平滑曲线": "smooth_curve",
    "穿点曲线": "smooth_curve",
    "参数曲线": "sample_parametric",
    "曲线": "curves",
    "截取曲线": "Curve.trim",
    "轮廓求交": "Curve.ray",
    "轮廓": "Geometry.contour",
    "基础形状": "shapes",
    "几何": "shapes",
    "组合": "shapes",
    "样式": "shapes",
    "矩形": "rect",
    "圆角矩形": "rect",
    "圆": "ellipse",
    "椭圆": "ellipse",
    "多边形": "polygon",
    "路径": "path",
    "文字": "label",
    "分组": "group",
    "沿曲线排列": "repeat",
    "沿路径排列": "repeat",
    "排列": "repeat",
    "带状轮廓": "ribbon",
    "变宽带": "ribbon",
    "厚度": "extrude",
    "拉伸厚度": "extrude",
    "剖面": "section",
    "裁切": "cutaway",
    "局部放大": "zoom",
    "放大": "zoom",
    "锚点": "anchors",
    "相对定位": "anchors",
    "对齐": "align",
    "布局": "layout",
    "排布": "layout",
    "移动": "Node.move_to",
    "绑定": "Node.pin",
    "一行": "row",
    "横排": "row",
    "一列": "column",
    "竖排": "column",
    "网格": "grid",
    "等距分布": "distribute",
    "均分": "distribute",
    "环形": "ring",
    "环形布局": "ring",
    "循环图": "ring",
    "圆周排列": "ring",
    "配对": "bipartite_order",
    "两列连线": "bipartite_order",
    "减少交叉": "bipartite_order",
    "端口分配": "spread_ports",
    "多条连线": "spread_ports",
    "错开端口": "spread_ports",
    "树布局": "tree_layout",
    "树形布局": "tree_layout",
    "旋转": "Node.set_transform",
    "缩放": "Node.set_transform",
    "端口": "Node.port",
    "非等比缩放": "Geometry.stretched",
    "拉伸轮廓": "Geometry.stretched",
    "连线": "connect",
    "箭头": "marker",
    "端点": "marker",
    "arrow": "marker",
    "marker": "marker",
    "抑制": "marker",
    "抑制箭头": "marker",
    "激活": "marker",
    "结合": "marker",
    "横杠": "marker",
    "标注": "Drawing.callout",
    "引导线": "Drawing.callout",
    "导出": "export",
    "保存": "Drawing.write",
    "合页": "export",
    "并页": "export",
    "compose_slide": "export",
    "publish_slide": "export",
    "写入": "export",
    "渐变": "resources",
    "资源": "resources",
    "defs": "resources",
    "坐标映射": "CoordinateMap",
    "坐标": "math",
    "函数采样": "sample_function",
    "数值轴": "math",
    "不等距横轴": "math",
    "阈值图": "math",
    "函数图像": "derivatives",
    "导数图像": "derivatives",
    "导数": "derivatives",
    "切线": "derivatives",
    "derivative": "derivatives",
    "圆外切点": "circle_tangent_points",
    "圆切线": "circle_tangent_points",
    "圆弧": "circular_arc",
    "arc": "circular_arc",
    "角标": "circular_arc",
    "角度标记": "circular_arc",
    "扇形": "annular_sector",
    "环段": "annular_sector",
    "蛋白结合": "protein",
    "蛋白过程": "protein",
    "生物蛋白过程": "protein",
    "生物过程": "protein",
    "自由轮廓": "freeform",
    "手写路径": "freeform",
    "范围标注": "ranges",
    "区间标注": "ranges",
    "长度标注": "ranges",
    "关节姿态": "joint_pose",
    "折叠姿态": "joint_pose",
    "姿态": "joint_pose",
    "关节角度": "joint_pose",
    "角度": "math",
    "角度标注": "math",
    "SVG片段": "raw_svg",
    "多元素部件": "raw_svg",
    "局部混用": "svg_fragment",
    "导出片段": "Geometry.to_svg_fragment",
    "原生文字": "native_sml",
    "原生线段": "native_sml",
    "native_text": "native_sml",
    "native_line": "native_sml",
    "射线": "rays",
    "光路": "rays",
    "纹理": "texture_clip",
    "纹理裁切": "texture_clip",
    "装配": "assembly",
    "部件接触": "assembly",
    "接触动作": "contact_action",
    "握持": "contact_action",
    "滚动接触": "contact_action",
}


_HELP_ALIASES.update(
    {  # membrane bioenergetics (_membrane_parts)
        "呼吸链": "transport_chain",
        "电子传递链": "transport_chain",
        "ETC": "transport_chain",
        "光合链": "transport_chain",
        "类囊体": "transport_chain",
        "氧化磷酸化": "transport_chain",
        "质子梯度": "transport_chain",
        "复合物": "membrane_complex",
        "膜蛋白复合物": "membrane_complex",
        "质子泵": "membrane_complex",
        "光系统": "membrane_complex",
        "ATP合酶": "atp_synthase",
        "ATP synthase": "atp_synthase",
        "F0F1": "atp_synthase",
        "F₀F₁": "atp_synthase",
        "旋转马达": "atp_synthase",
        "V-ATPase": "atp_synthase",
        "H⁺": "ion_marker",
        "H+": "ion_marker",
        "质子": "ion_marker",
        "ion": "ion_marker",
        "离子标记": "ion_marker",
    }
)

_HELP_TASKS = {
    "native_sml": (
        "补原生文字或线段",
        (
            "从 atomize_svg_to_slide 包导入 native_text/native_line；返回 SML 元素字符串，可作为片段传给 publish_slide。",
            "Box 或 (x, y, width, height)、端点及字号使用 Slides 画布坐标，不经过 SVG mapping；native_line 的 width 为非负整数。",
            "字体与颜色沿用当前页面的设计；HEX/CSS 纯色会规范化为 SML。",
            "native_text 自动包 content/p 并转义纯文本；框和字号由作者决定，不测量、缩字或自动适配。",
        ),
        (),
    ),
    "svg_fragment": (
        "局部几何混入手写 SVG",
        (
            "Geometry.to_svg_fragment 返回元素字符串，可 append 到已有 SVG 字符串列表，不必改用整套 Drawing。",
            "含内部 ID 时传唯一的 id_prefix，并保证导出 ID 不与整图其他 ID 冲突；保留局部坐标与变换，不附带 Python 端口或锚点绑定。",
        ),
        ("Geometry.to_svg_fragment",),
    ),
    "contact_action": (
        "从接触关系构造动作",
        (
            "先在物体局部坐标确定接触点/面、运动轴与行进方向，再一起投影到当前画面；箭头、作用痕迹和手形从这组关系生成。",
            "手指或工具轮廓用 path 自由绘制，with_ports 标出真实触点；Node.pin 连接对应端口。pin 只约束位置，姿态仍由作者设置。",
            "先连接完整部件，再用 group 的绘制顺序表达前后遮挡；不要把应相接的部件分别画短后凭目测摆近。",
            "纹理或作用痕迹与承载面共用坐标；需要裁切时用 cutaway。裁切是快照，几何变化后重建。工具不推断握姿、滚动规律或物理接触。",
        ),
        ("path", "Geometry.with_ports", "Node.port", "Node.pin", "Node.set_transform", "group", "cutaway"),
    ),
    "assembly": (
        "同一接口的部件组合",
        (
            "复用同一部件轮廓与尺寸，在真实接口处用 Geometry.with_ports 设置命名端口，保存位置及需要的方向。",
            '用 member.pin(support.port("socket"), own_anchor="port:contact") 保持接点联动；pin 只绑定位置，姿态与尺度由作者用 Node.set_transform 设置。',
            "extrude 可为凸轮廓生成平行厚度；前后遮挡由作者按 group 绘制顺序组织。cutaway 用同坐标系窗口裁取已有几何，不自动造孔或判定配合。",
            "换视图沿用部件尺寸，按新投影重算轮廓、厚度与端口；局部图复用原组合。裁切为快照，源轮廓变化后重建并用 Node.set_geometry 更新。",
        ),
        (
            "Geometry.with_ports",
            "Node.port",
            "Node.pin",
            "Node.set_transform",
            "Node.set_geometry",
            "extrude",
            "cutaway",
            "group",
        ),
    ),
    "texture_clip": (
        "按轮廓裁切纹理",
        (
            "用 path 等接口绘制当前对象的轮廓；手绘笔触用 group(*strokes) 组合，再用 cutaway(texture, outline) 裁切。",
            "纹理与窗口共用局部坐标；窗口取几何填充区域，支持平移、旋转、缩放及组合，组合取并集，孔洞沿用 fill-rule 或显式 clip-rule。描边、滤镜不扩大窗口。",
            "用 group(outline, clipped_texture) 组合后加入 Drawing，整体放置和变换；Node.geometry 不包含实例的画布变换。",
            "cutaway 返回快照，不绑定另一个 Node；轮廓变化后重建并用 Node.set_geometry 更新。复杂裁切可能保留为 SVG。",
        ),
        ("path", "group", "cutaway", "Drawing.add", "Node.set_geometry"),
    ),
    "rays": (
        "射线与光路几何",
        (
            "先按当前物理或结构关系确定两点 A、B，以非零向量 B-A 保存射线方向。",
            "A/B 若是数据坐标，可用 CoordinateMap.point 映射两点后相减，或用 vector 映射原始差向量；两种方式选一，不重复映射方向。",
            "边界或目标几何用 Geometry.contour 取轮廓，以同坐标系的起点和方向调用该轮廓的 Curve.ray，以返回的 PathFrame.point 作为交点。",
            "用同一方向和交点生成实际 path/Curve；延伸、后续求交与标注复用这份几何，不在另一分支另算不同斜率。",
            "Curve.ray 查射线与所选有限轮廓的前向交点，支持 nearest/farthest，无交点时报错；轮廓是快照，源几何变化后重新取得。物理定律由调用方确定。",
        ),
        (
            "CoordinateMap.point",
            "CoordinateMap.vector",
            "rect",
            "Geometry.contour",
            "Curve.ray",
            "Curve.to_geometry",
            "path",
        ),
    ),
    "derivatives": (
        "函数与导数图像",
        (
            "先确定公式、定义域、导数和要解释的关系；坐标轴位置、对比方式与强调点由当前内容决定。",
            "用同一 CoordinateMap 换算曲线、刻度和投影；切点用 point(x, f(x))，切线方向用 vector(1, slope)。",
            "sample_function 采样函数或已知导数，已知断点传 breaks；to_geometry 后可给切点加命名端口，再绑定标签。",
            "当前不自动求导或生成坐标轴；可用 Python 计算刻度，通过 path/label 自由组合。",
        ),
        (
            "CoordinateMap",
            "CoordinateMap.point",
            "CoordinateMap.vector",
            "sample_function",
            "FunctionSample.to_geometry",
            "Geometry.with_ports",
            "Drawing.callout",
        ),
    ),
    "protein": (
        "蛋白结合与过程示意",
        (
            "依据用户材料或可靠资料确定参与者、结合位点和状态变化，再选择视角与表达方式。",
            "轮廓可手写 path 或用 smooth_curve 穿点构造；with_ports 保存已知位点，contour_toward 可沿轮廓求连接点。",
            "膜等重复结构可沿自定路径排列；箭头与标注连接端口，局部解释需要时再裁切或放大。",
            "工具只维护几何关系，不推断生物机制、蛋白结构或构象变化；没有结构依据时使用明确的示意表达。",
        ),
        (
            "path",
            "smooth_curve",
            "Geometry.with_ports",
            "Node.contour_toward",
            "Node.port",
            "Node.pin",
            "repeat_along_path",
            "Drawing.connect",
            "Drawing.callout",
        ),
    ),
    "freeform": (
        "自由 SVG 轮廓接入几何与锚点",
        (
            "同一张图可混合手写轮廓、计算生成的路径与库构造；工具选择不规定构图或样式。",
            "path(d, **paint) 接收 SVG 路径 d，返回 Geometry；多部件用 group，资源用 Drawing.add_defs。",
            "with_ports 的位置与路径使用同一局部坐标；Curve.frame/ray 还提供方向。Drawing.add 后以 node.port 获取动态接口。",
            "Node.anchor 是外接框锚点；真实轮廓上的接触位置应定义端口。path 不接收整份 SVG/XML 文本。",
            "已有多元素 g 字符串可查“SVG片段”，用 Geometry 与显式 Box 接入。",
        ),
        (
            "path",
            "group",
            "Geometry",
            "Geometry.with_ports",
            "Drawing.add",
            "Node.port",
            "Node.pin",
            "Drawing.add_defs",
        ),
    ),
    "ranges": (
        "范围与区间标注",
        (
            "先明确对象和区间两端；沿线长度取中心线，不能用外接框或外轮廓周长代替。",
            "trim 强调选定段，frame 取两端与中点；刻线可沿 frame.normal 绘制，callout 指向区间。",
            "s0/s1 是源 SVG 弧长；标注数值和单位由调用方提供，不自动换算物理单位。",
            "路径、强调段和端口放在同一局部几何中；Node 变换时端口随动，改变源路径时需重建区间。",
        ),
        ("Curve.trim", "Curve.frame", "group", "Geometry.with_ports", "Drawing.callout"),
    ),
    "joint_pose": (
        "关节与姿态构造",
        (
            "自由轮廓用 with_ports 给真实转轴命名；复用部件保持端口距离，pin 连接对应端口。",
            "pin 只绑定位置，不继承目标旋转或缩放；rotation 是画布绝对方向，SVG 正旋转为顺时针。",
            "下例局部转轴连线沿 +x；theta 为第一部件画布方向，alpha 为关节内夹角（0–180 度），side 为 +1/-1 折叠侧。",
            "按要表达的状态选择夹角与方向；等长只维护尺寸，不能单独决定收拢或伸展姿态。",
        ),
        ("path", "Geometry.with_ports", "Node.port", "Node.pin", "Node.set_transform"),
    ),
    "raw_svg": (
        "多元素 SVG 片段接入端口绑定",
        (
            "已有部件函数可继续返回可信静态 g 字符串；ET.fromstring 解析后用 Geometry 包装，无须改写为单个 path。",
            "显式 Box 与 contact_xy 使用片段根坐标系，片段内（含根上的）transform 已计入；不自动猜边界或物理单位。",
            "内部 defs 随分组保留；group / Drawing.to_svg 重写实例内部 ID 及 url(#id)、href、已声明的 xlink:href。共享 defs 用 Drawing.add_defs。",
            "生成方保证 ID 唯一和引用完整；不引用另一 Geometry 的内部 ID，不带脚本、事件、外链、样式表/class 或嵌套 svg 视口。",
            "这是可信片段的包装方式，不是安全净化器；构造和导出不会执行脚本或联网，也不会自动过滤这些内容。",
        ),
        ("Geometry", "Box", "Geometry.with_ports", "Node.port", "Node.pin", "Drawing.add_defs"),
    ),
}


_HELP_TASK_EXAMPLES = {
    "native_sml": (
        "from scripts.svg_lib.atomize_svg_to_slide import publish_slide, native_text, native_line\n"
        "r = publish_slide(page_xml,\n"
        "    native_text(text, (x, y, width, height), font_size=size,\n"
        "                font_family=font, color=text_color),\n"
        "    native_line(start, end, color=line_color, width=line_width), presentation=deck_id)"
    ),
    "svg_fragment": (
        "part = curve.to_geometry(**paint)\n"
        "parts.append(part.to_svg_fragment())\n"
        "# resource_part 含内部 ID；每个实例使用不同前缀。\n"
        'parts.append(resource_part.to_svg_fragment(id_prefix="part1"))'
    ),
    "ranges": (
        "curve = Curve(path_d)\n"
        "part = group(curve.to_geometry(**path_paint),\n"
        "             curve.trim(s0, s1).to_geometry(**range_paint))\n"
        "part = part.with_ports(start=curve.frame(s0), end=curve.frame(s1),\n"
        "                       mid=curve.frame((s0+s1)/2))\n"
        "node = drawing.add(name, part, at=origin)\n"
        'drawing.callout(name+"-note", text, node.port("mid"),\n'
        "                at=label_at, font_size=size)"
    ),
    "joint_pose": (
        "part = path(outline_d, **paint).with_ports(start=(0, 0), end=(length, 0))\n"
        'first = drawing.add(first_name, part, at=pivot, own_anchor="port:start")\n'
        "first.set_transform(rotation=theta)\n"
        'second = drawing.add(second_name, part, at=first.port("end"),\n'
        '                     own_anchor="port:start")\n'
        "second.set_transform(rotation=theta + side*(180-alpha))"
    ),
    "raw_svg": (
        "import xml.etree.ElementTree as ET\n"
        "from scripts.svg_lib.svg_drawing import Geometry, Box\n"
        "part = Geometry(ET.fromstring(component_svg), Box(x, y, width, height))\n"
        "part = part.with_ports(contact=contact_xy)\n"
        "node = drawing.add(name, part)\n"
        'node.pin(target.port(target_port), own_anchor="port:contact")'
    ),
}


_UNSUPPORTED_HELP = {
    "自动避障": "connect 的 orthogonal 路由支持指定 Box/Node 区域的自动避障；当前不提供全局自动布局。",
    "避障": "connect 的 orthogonal 路由支持指定 Box/Node 区域的自动避障；当前不提供全局自动布局。",
    "自动构图": "当前不提供自动构图或页面模板；可用 shapes、layout、anchors 自行组合。",
    "主题": "当前不提供主题或固定配色；通过各接口的样式参数传入当前设计。",
    "配色": "当前不提供主题或固定配色；通过各接口的样式参数传入当前设计。",
    "模板": "当前不提供成图模板；可查 drawing_help() 选择需要的构造操作。",
}


_STYLE_HELP = (
    "样式：**style 使用 SVG 属性，参数名中的下划线转为连字符；"
    "常用 fill、stroke、stroke_width、opacity，文字另可用 "
    "font_weight、font_style、text_anchor、letter_spacing。"
)


def _help_signature(name, doc):
    import inspect

    if doc.is_property:
        return f"{name} → {doc.returns}（只读属性）"
    signature = inspect.signature(doc.target)
    parameters = [
        p.replace(annotation=inspect.Parameter.empty)
        for p in signature.parameters.values()
        if p.name not in ("self", "cls")
    ]
    signature = signature.replace(parameters=parameters, return_annotation=inspect.Signature.empty)
    return f"{name}{signature} → {doc.returns}"


def _api_help(name):
    doc = _DRAWING_APIS[name]
    lines = [f"【接口 {name}】", f"用途：{doc.purpose}", _help_signature(name, doc), "语义："]
    lines.extend("- " + line for line in doc.semantics)
    if doc.style:
        lines.append(_STYLE_HELP)
    lines.extend(["操作片段（变量由当前图提供）：", "```python", doc.example, "```"])
    if doc.limits:
        lines.append("边界：")
        lines.extend("- " + line for line in doc.limits)
    return "\n".join(lines)


_PART_CATALOG = (
    (
        "生命科学",
        (
            "cell",
            "membrane",
            "receptor",
            "transporter",
            "antibody",
            "nucleus",
            "mitochondrion",
            "vessel",
            "virus",
            "neuron",
            "dna",
            "duplex",
            "nucleic_strand",
            "protein_complex",
            "cytokine",
            "heart",
            "nephron",
            "bbb_unit",
            "root_section",
            "signaling_cascade",
            "liver_sinusoid",
            "membrane_complex",
            "atp_synthase",
            "ion_marker",
        ),
    ),
    (
        "化学与材料",
        (
            "atom",
            "molecule",
            "lattice",
            "particle",
            "porous_framework",
            "porous_electrode",
            "microplastic",
            "layer_stack",
            "interface_section",
            "energy_diagram",
        ),
    ),
    (
        "工程、物理与 CS",
        (
            "block",
            "nn_layer",
            "dense_links",
            "tensor_block",
            "wave",
            "lens",
            "laser_beam",
            "circuit_symbol",
            "circuit_loop",
            "coil",
            "field_marks",
            "rails_rod",
            "spring",
            "magnet",
            "device",
            "image_grid",
            "vector_packet",
            "patch_embed",
        ),
    ),
    ("地学、天文与生态", ("globe", "star", "planet", "water_column_section", "soil_aggregate", "organism")),
    ("通用", ("legend_row", "badge", "trial_sequence")),
)
# Narrow, topic-specific compositions: kept callable and searchable by name/alias, but not listed in the catalogue.
_PART_SCENES = (
    "cell_interface",
    "cell_envelope",
    "biofilm_section",
    "transport_chain",
    "battery_cell",
    "transformer_block",
    "encoder_decoder",
    "intestinal_wall",
    "brain",
    "atmosphere_section",
    "jet_stream",
    "coral_polyp",
    "symbiont",
    "transit_geometry",
)


def _short_purpose(doc, limit=34):
    text = doc.purpose.split("：")[0].split("（")[0]
    return text if len(text) <= limit else text[:limit] + "…"


def _parts_help():
    title, purpose, note = _HELP_TOPICS["parts"]
    lines = [
        f"【主题 parts｜{title}】",
        purpose,
        note,
        '放置：d.place(part, at=中心)；受体/探针立在轮廓上：d.mount(part, on=node.contour_at(t, normal="outward"))。',
    ]
    for group, names in _PART_CATALOG:
        items = [f"{n}（{_short_purpose(_DRAWING_APIS[n])}）" for n in names if n in _DRAWING_APIS]
        lines.append(f"- {group}：" + "、".join(items))
    scenes = [n for n in _PART_SCENES if n in _DRAWING_APIS]
    if scenes:
        lines.append("场景组合（只在题目正好对上时用；通常用上面的通用部件组合更灵活）：" + "、".join(scenes))
    lines.append('查参数与示例：drawing_help("cell")；一次查多个：drawing_help("cell", "receptor")。')
    return "\n".join(lines)


def _topic_help(topic):
    if topic == "parts":
        return _parts_help()
    title, purpose, note = _HELP_TOPICS[topic]
    members = [(name, doc) for name, doc in _DRAWING_APIS.items() if doc.topic == topic]
    members.sort(key=lambda item: (item[1].rank, item[0]))
    common = [(name, doc) for name, doc in members if doc.common]
    advanced = [name for name, doc in members if not doc.common]
    lines = [f"【主题 {topic}｜{title}】", purpose]
    if note:
        lines.append(note)
    if len(common) <= 2:
        lines.extend(_api_help(name) for name, _ in common)
    else:
        lines.append("常用接口（完整说明可直接查询接口名）：")
        for name, doc in common:
            lines.extend(["- " + _help_signature(name, doc), "  " + doc.purpose])
        if any(doc.style for _, doc in common):
            lines.append(_STYLE_HELP)
    if advanced:
        lines.append("按需进阶：" + ", ".join(advanced))
    if topic == "export":
        lines.extend(
            [
                "写入页面（落点和宽度由当前页面决定）：",
                "```python",
                "from scripts.svg_lib.atomize_svg_to_slide import publish_slide",
                "r = publish_slide(page_xml, drawing.to_slide(x=x0, y=y0, width=target_width), presentation=deck_id)",
                "```",
                "更完整的转换/页面约定见 references/xml/svg-writing-guide.md「合页与写入：publish_slide」一节。",
            ]
        )
    return "\n".join(lines)


_QUICK = (
    "Drawing",
    "Drawing.place",
    "Drawing.svg_at",
    "Drawing.box_at",
    "Drawing.text_at",
    "Drawing.rect_at",
    "Drawing.ellipse_at",
    "Drawing.path_at",
    "Drawing.arrow",
    "Drawing.line",
    "Drawing.mount",
    "Drawing.callout",
    "Node.contour_at",
    "Node.port",
    "Node.replace_svg",
    "Drawing.check",
    "Drawing.summary",
    "Drawing.to_slide",
)


def _short_signature(name):
    import inspect

    if name == "Drawing":
        return "Drawing(width, height)"
    doc = _DRAWING_APIS.get(name)
    if doc is None:
        return None
    try:
        sig = str(inspect.signature(doc.target)).replace("(self, ", "(").replace("(self)", "()")
    except (TypeError, ValueError):
        sig = "(...)"
    return name.replace("Drawing.", "d.").replace("Node.", "node.") + sig


def _all_help():
    lines = ['SVG drawing｜全部公共接口名（按主题；签名与参数用 drawing_help("接口名")，可一次传多个）']
    for topic, (title, _, _) in _HELP_TOPICS.items():
        members = sorted(
            ((n, d) for n, d in _DRAWING_APIS.items() if d.topic == topic), key=lambda x: (x[1].rank, x[0])
        )
        if not members:
            continue
        lines.append(f"- {topic}｜{title}：" + ", ".join(n for n, _ in members))
    return "\n".join(lines)


def _help_index():
    lines = ["SVG drawing｜当前安装模块的公共能力", "最常用接口（签名即用法；at 一律是中心坐标）："]
    for name in _QUICK:
        sig = _short_signature(name)
        if sig:
            purpose = _DRAWING_APIS[name].purpose.split("：")[0].split("（")[0] if name in _DRAWING_APIS else "画布"
            lines.append(f"  {sig}  # {purpose}")
    lines.append('按主题查询（drawing_help("主题") 列出该主题全部签名；drawing_help("all") 列出全部接口签名）：')
    for topic in _DEFAULT_HELP_TOPICS:
        title, purpose, _ = _HELP_TOPICS[topic]
        lines.append(f"- {topic}：{title}；{purpose}")
    lines.extend(
        [
            '查询：drawing_help("anchors")；drawing_help("Node.pin")；drawing_help("repeat", "connect")',
            '中文别名：drawing_help("沿曲线排列")。仅输出帮助，不执行绘图。',
            '任务提示：drawing_help("导数")、drawing_help("蛋白结合")、drawing_help("自由轮廓")、'
            'drawing_help("范围标注")、drawing_help("关节姿态")、drawing_help("SVG片段")、drawing_help("射线")。',
        ]
    )
    return "\n".join(lines)


def _help_lookup(query):
    key = query.strip().casefold()
    if key in ("", "help", "--help", "-h"):
        return "index", ""
    if key in ("all", "全部", "签名", "signatures"):
        return "all", ""
    if key in _UNSUPPORTED_HELP:
        return "unsupported", key
    aliases = {alias.casefold(): value for alias, value in _HELP_ALIASES.items()}
    key = aliases.get(key, key).casefold()
    # A precise public API name takes precedence over a same-named topic.
    apis = {name.casefold(): name for name in _DRAWING_APIS}
    if key in apis:
        return "api", apis[key]
    if key in _HELP_TOPICS:
        return "topic", key
    if key in _HELP_TASKS:
        return "task", key
    # Allow unique short method names, while retaining class-qualified IDs.
    short = [name for name in _DRAWING_APIS if name.rsplit(".", 1)[-1].casefold() == key]
    if len(short) == 1:
        return "api", short[0]
    return "unknown", query.strip()


def _unknown_help(query):
    import difflib

    candidates = list(_HELP_TOPICS) + list(_DRAWING_APIS) + list(_HELP_ALIASES) + list(_HELP_TASKS)
    lookup = {name.casefold(): name for name in candidates}
    close = difflib.get_close_matches(query.casefold(), lookup, n=8, cutoff=0.5)
    suggestions = []
    for key in close:
        kind, name = _help_lookup(lookup[key])
        if kind in ("api", "topic", "task") and name not in suggestions:
            suggestions.append(name)
    lines = [f"未找到公开能力：{query!r}。没有执行任何绘图操作。"]
    if suggestions:
        lines.append("可以查询：" + ", ".join(suggestions[:3]))
    else:
        lines.append("可运行 drawing_help() 查看能力目录。")
    return "\n".join(lines)


def _task_help(name):
    title, hints, apis = _HELP_TASKS[name]
    lines = [f"【任务提示 {name}｜{title}】"]
    lines.extend("- " + hint for hint in hints)
    if name in _HELP_TASK_EXAMPLES:
        lines.extend(["操作片段（路径、部件和参数由当前图提供）：", "```python", _HELP_TASK_EXAMPLES[name], "```"])
    if apis:
        lines.append("按需查询接口（仅推荐操作，不提供成图模板）：")
        lines.extend(f"- {api}：{_DRAWING_APIS[api].purpose}" for api in apis)
    return "\n".join(lines)


def drawing_help(*names: str) -> str:
    """Return a short index, topic help or exact public-API help."""
    if not names:
        return _help_index()
    from .. import svg_drawing  # noqa: F401  registers every public API even when this module is imported directly

    sections = []
    seen = set()
    for query in names:
        if not isinstance(query, str):
            raise TypeError("drawing_help topics must be strings")
        kind, name = _help_lookup(query)
        if (kind, name) in seen:
            continue
        seen.add((kind, name))
        if kind == "index":
            sections.append(_help_index())
        elif kind == "all":
            sections.append(_all_help())
        elif kind == "api":
            sections.append(_api_help(name))
        elif kind == "topic":
            sections.append(_topic_help(name))
        elif kind == "task":
            sections.append(_task_help(name))
        elif kind == "unsupported":
            sections.append(_UNSUPPORTED_HELP[name])
        else:
            sections.append(_unknown_help(name))
    parts = sorted({n for k, n in seen if k == "api" and n in svg_drawing.__all__ and not n[0].isupper()})
    if parts or ("topic", "parts") in seen:
        names_ = ", ".join(["Drawing", *parts]) if parts else "Drawing, cell, membrane, …"
        sections.append(f"导入：from scripts.svg_lib.svg_drawing import {names_}")
    return "\n\n".join(sections)
