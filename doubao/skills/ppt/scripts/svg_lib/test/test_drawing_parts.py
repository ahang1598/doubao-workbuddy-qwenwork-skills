"""Drawing shortcuts and domain part library (bio, matter, earth, organs, energy, EM, membranes, ...)."""

import math
import re
import unittest
import xml.etree.ElementTree as ET
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from ..svg_drawing import Drawing, drawing_help
from ._helpers import assert_centered, assert_parts_centered_native, built_part, first_drawn, quiet_slide
from ..drawing_lib._labels import _connector_points
from ..drawing_lib._routing import crosses
from ..drawing_lib._scene import _Layout
from ..svg_drawing import (
    atmosphere_section,
    atom,
    atp_synthase,
    badge,
    battery_cell,
    bbb_unit,
    bilayer,
    biofilm_section,
    block,
    brain,
    cell_envelope,
    cell_interface,
    circle_union,
    circuit_loop,
    circuit_symbol,
    close_packed,
    coil,
    coral_polyp,
    dense_links,
    device,
    dislocation_symbol,
    duplex,
    edge_dislocation,
    encoder_decoder,
    energy_diagram,
    field_marks,
    globe,
    globe_point,
    heart,
    image_grid,
    interface_section,
    intestinal_wall,
    ion_marker,
    jet_stream,
    laser_beam,
    lattice,
    layer_stack,
    legend_row,
    lens,
    magnet,
    membrane,
    membrane_complex,
    microplastic,
    molecule,
    nephron,
    neuron,
    nn_layer,
    nucleic_strand,
    organism,
    particle,
    patch_embed,
    planet,
    polycrystal,
    porous_electrode,
    porous_framework,
    protein_complex,
    rails_rod,
    receptor,
    shade,
    signaling_cascade,
    soft_shading,
    soil_aggregate,
    sphere_shading,
    spring,
    star,
    symbiont,
    tensor_block,
    transformer_block,
    transit_geometry,
    transport_chain,
    trial_sequence,
    twin_lattice,
    vector_packet,
    water_column_section,
    water_point,
    wave,
)


# ====================================================================================================
# Contracts for one-call drawing shortcuts and semi-editable chart placement.
# ====================================================================================================


class ShortcutTest(unittest.TestCase):
    def scene(self):
        d = Drawing(600, 300)
        cell = d.ellipse_at((180, 150), 140, 90, fill="#F3EEF8", stroke="#9A88C9")
        recv = d.rect_at(cell.contour_at(0.0, normal="outward"), 14, 28, rx=4, fill="#5B1061")
        hub = d.box_at((470, 150), "SHP-2", font_size=16, fill="#9B2D6F", text_fill="#FFFFFF", shape="pill")
        return d, cell, recv, hub

    def test_shortcut_arrows_native_export_and_help(self):
        d, cell, recv, hub = self.scene()
        d.arrow(recv, hub, stroke="#9B2D6F")
        d.arrow(hub, cell, head="inhibit", stroke="#C0392B", curve=30)
        d.line(cell, hub, stroke="#333333", dashed=True)
        svg = d.to_svg()
        self.assertEqual(len(re.findall(r"<marker ", svg)), 2)
        self.assertIn("stroke-dasharray", svg)
        start = d.resolve(d._endpoint(hub, cell))
        box = hub.bounds
        self.assertAlmostEqual(start[0], box.x, delta=1.0)
        d, cell, recv, hub = self.scene()
        d.arrow(recv, hub, stroke="#9B2D6F")
        d.arrow(hub, cell, head="inhibit", stroke="#C0392B", route="orthogonal")
        d.text_at((300, 20), "标题", font_size=18)
        xml = d.to_slide(x=40, y=60, width=600)
        self.assertNotIn("<embed", xml)
        self.assertIn("SHP-2", xml)
        self.assertIn("标题", xml)
        d, _, recv, hub = self.scene()
        with self.assertRaises(ValueError):
            d.arrow(recv, hub, head="star")
        text = drawing_help("shapes")
        for name in ("rect_at", "box_at", "text_at"):
            self.assertIn(name, text)
        self.assertIn("Drawing.arrow", drawing_help("connect"))


class PartsTest(unittest.TestCase):
    def test_place_centres_parts_and_check_flags_straddling_text(self):
        from ..svg_drawing import cell, atom, block, lattice, layer_stack, nn_layer, legend_row

        d = Drawing(600, 400)
        for i, part in enumerate(
            (
                cell(40, 30),
                atom("Na"),
                block("Encoder"),
                lattice([[("O", "#ccc")] * 3]),
                layer_stack([("Ag", 20, "#ccc")]),
                nn_layer(3),
                legend_row([("dot", "a", "#000")]),
            )
        ):
            node = d.place(part, at=(300, 200), key=f"p{i}")
            cx, cy = d.resolve(node.anchor("center"))
            self.assertAlmostEqual(cx, 300, places=6)
            self.assertAlmostEqual(cy, 200, places=6)
        d = Drawing(600, 300)
        d.place(cell(40, 30), at=(200, 150), key="a")
        d.place(cell(40, 30), at=(270, 150), key="b")
        d.text_at((200, 150), "核", font_size=12, key="inside")
        d.text_at((240, 185), "耗竭 / 失能", font_size=11, key="lab")
        kinds = {(p["kind"], tuple(p["keys"])) for p in d.check()}
        self.assertIn(("text_straddles_frame", ("lab", "a")), kinds)
        self.assertFalse(any(k == "frames_overlap" for k, _ in kinds))  # publish_slide waives shape-on-shape
        self.assertNotIn(("text_straddles_frame", ("inside", "a")), kinds)

    def test_nn_layers_parts_native_and_mount_outward(self):
        from ..svg_drawing import (
            cell,
            receptor,
            membrane,
            atom,
            lattice,
            layer_stack,
            particle,
            nn_layer,
            block,
            wave,
            legend_row,
        )

        d = Drawing(960, 540)
        c = d.add("cell", cell(110, 70, style="flat"), at=(140, 120), own_anchor="center")
        r = d.mount(receptor(kind="antibody", style="flat"), on=c.contour_at(0.0, normal="outward"))
        layout = _Layout(d)
        tail, head = layout.point(r.port("tail")), layout.point(r.port("head"))
        self.assertGreater(head[0], tail[0] + 30)
        d.add("mem", membrane("M 300 60 C 380 40 460 40 540 60", style="flat"), at=(0, 0))
        d.add("na", atom("Na", style="flat"), at=(600, 60), own_anchor="center")
        d.add("lat", lattice([[("O", "#A9BBD6")] * 6, [("Na", "#E24C3B"), None] * 3], style="flat"), at=(650, 30))
        d.add("stack", layer_stack([("Ag", 16, "#B8BEC6"), ("钙钛矿", 44, "#3B3A55")], style="flat"), at=(40, 250))
        d.add("p", particle(50, grains=4, shell=6, cracks=1, style="flat"), at=(420, 320), own_anchor="center")
        l1 = d.add("l1", nn_layer(3, name="in", style="flat"), at=(560, 240))
        l2 = d.add("l2", nn_layer(4, name="h", style="flat"), at=(660, 220))
        dense_links(d, l1, l2)
        d.add(
            "blk",
            block("Encoder", subtitle="x6", header_fill="#4A6FA5", style="flat"),
            at=(860, 330),
            own_anchor="center",
        )
        d.add("wv", wave(200, 20, kind="damped", style="flat"), at=(320, 440))
        d.add("lg", legend_row([("arrow", "激活", "#2A6F4E"), ("inhibit", "抑制", "#C0392B")]), at=(560, 490))
        xml = quiet_slide(d, width=960)
        self.assertNotIn("<embed", xml)
        self.assertIn("钙钛矿", xml)
        for style in ("rich", "flat"):
            g = nn_layer(9, max_drawn=7, style=style)
            self.assertEqual(
                sorted(k for k in g.ports if k.startswith("in_")), ["in_0", "in_1", "in_2", "in_3", "in_4", "in_8"]
            )
            self.assertIn("out_8", g.ports)
            self.assertLess(g.ports["in_0"][0], g.ports["out_0"][0])
            self.assertAlmostEqual(g.ports["in_0"][1], g.ports["out_0"][1])
        d = Drawing(400, 300)
        a = d.place(nn_layer(3), at=(100, 150), key="a")
        b = d.place(nn_layer(2), at=(250, 150), key="b")
        dense_links(d, a, b)
        dense_links(d, b, a, weights=[[0.9, -0.5, 0.1], [0, 1, -1]])
        keys = [k for k, _ in d.items]
        self.assertIn("a-b-2-1", keys)
        self.assertIn("b-a-1-2", keys)

    def test_rich_cells_immune_kinds_lysing_and_viruses(self):
        from ..svg_drawing import cell, receptor
        from ..svg_drawing import virus

        d = Drawing(600, 400)
        t = d.place(cell(80, kind="t_cell"), at=(200, 200), key="t")
        d.mount(receptor(kind="car"), on=t.contour_at(0.9, normal="outward"), inset=2)
        d.place(cell(90, 70, kind="tumor"), at=(450, 200), key="tu")
        xml = d.to_slide(x=0, y=0, width=600)
        self.assertEqual(xml.count("<embed"), 4)  # cytoplasm + nucleus look per cell
        self.assertGreaterEqual(xml.count('type="custom"'), 2)
        for kind in ("generic", "t_cell", "tumor", "bacterium"):
            for style in ("rich", "flat"):
                g = cell(60, 45, kind=kind, style=style)
                self.assertAlmostEqual(g.bounds.x + g.bounds.width / 2, 0, places=6)
        d = Drawing(1400, 500)
        kinds = ("macrophage", "dendritic", "neutrophil", "epithelial", "plasma", "generic", "bacterium")
        for i, kind in enumerate(kinds):
            for j, state in enumerate(("normal", "lysing")):
                g = cell(45, kind=kind, state=state, style=("rich", "flat")[j])
                self.assertIn("nucleus", g.ports)
                n = d.place(g, at=(100 + i * 190, 130 + j * 240), key=f"{kind}{j}")
                d.mount(receptor(kind="gpcr"), on=n.contour_at(0.75, normal="outward"), inset=3)
        ep = cell(40, kind="epithelial")
        self.assertLess(ep.ports["apical"][1], ep.ports["nucleus"][1])
        self.assertLess(ep.ports["nucleus"][1], ep.ports["basal"][1])
        for fibers in (False, True):
            d.place(virus(40, kind="icosahedral", fibers=fibers), at=(500 + fibers * 200, 250), key=f"ico{fibers}")
        self.assertEqual(d.check(), [])
        d.to_slide(x=0, y=0, width=960)
        with self.assertRaises(ValueError):
            cell(40, state="dead")
        with self.assertRaises(ValueError):
            virus(40, kind="rod")

    def _tech_parts(self, style):
        parts = [
            nn_layer(4, style=style),
            nn_layer(12, name="h", style=style),
            tensor_block(64, 32, 32, style=style),
            transformer_block(style=style),
            transformer_block(kind="decoder", style=style),
            lens(100, style=style),
            lens(100, kind="concave", axis=True, focal=60, style=style),
            laser_beam(200, waist=0.4, style=style),
            spring(150, style=style),
            magnet(style=style),
            magnet(60, 80, kind="horseshoe", style=style),
            magnet(field_lines=True, style=style),
            legend_row([("arrow", "a", "#333"), ("ring", "b", "#333")]),
        ]
        parts += [block("M", kind=k, style=style) for k in ("module", "data", "doc", "op")]
        parts += [
            wave(120, 20, kind=k, axes=True, style=style)
            for k in ("sine", "square", "pulse", "damped", "packet", "sawtooth")
        ]
        parts += [
            circuit_symbol(k, name="X", value="1", style=style)
            for k in tuple(
                "resistor resistor_iec capacitor inductor source_dc source_ac battery diode ground switch lamp".split()
            )
        ]
        return parts

    def test_tech_parts_centered_outlined_and_flat_native(self):
        for style in ("rich", "flat"):
            parts = self._tech_parts(style)
            for g in parts:
                assert_centered(self, g)
            d = Drawing(4000, 400)
            for i, g in enumerate(parts):
                d.place(g, at=(100 + i * 110, 200), key=f"t{i}")
            xml = quiet_slide(d, width=960)
            if style == "flat":
                self.assertNotIn("<embed", xml)
            else:
                self.assertIn("<embed", xml)
            self.assertIn("Add &amp; Norm", xml)
        for g in (
            tensor_block(8, 20, 20),
            block("A"),
            block("db", kind="data"),
            lens(80),
            magnet(),
            nn_layer(3, style="flat"),
        ):
            self.assertEqual(first_drawn(g).get("data-outline"), "1")


class BioPartsTest(unittest.TestCase):
    def factories(self):
        from ..svg_drawing import nucleus, mitochondrion, vessel, dna, cytokine, antibody, virus

        return {
            "nucleus": lambda s: nucleus(50, style=s),
            "mito": lambda s: mitochondrion(140, style=s),
            "mito_rot": lambda s: mitochondrion(80, angle=-25, style=s),
            "vessel": lambda s: vessel(300, 50, wbc=1, style=s),
            "vessel_x": lambda s: vessel(radius=50, kind="cross", style=s),
            "dna": lambda s: dna(240, width=50, style=s),
            "ladder": lambda s: dna(160, width=36, kind="ladder", style=s),
            "cytokine": lambda s: cytokine(6, r=7, style=s),
            "dimer": lambda s: cytokine(4, r=6, kind="dimer", style=s),
            "antibody": lambda s: antibody(height=50, style=s),
            "virus": lambda s: virus(40, style=s),
            "phage": lambda s: virus(26, kind="phage", style=s),
        }

    def test_bio_parts_contract_and_membrane_bilayer(self):
        d = Drawing(960, 540)
        for i, (name, make) in enumerate(self.factories().items()):
            for style in ("rich", "flat"):
                g = make(style)
                assert_centered(self, g, name)
            if name == "antibody":
                continue
            node = d.place(make("rich"), at=(80 + i * 60, 270), key=f"n{i}")
            x, y = d.resolve(node.contour_at(0.3, normal="outward"))
            b = node.bounds
            self.assertTrue(b.x - 1 <= x <= b.x + b.width + 1 and b.y - 1 <= y <= b.y + b.height + 1, name)
        for name, make in self.factories().items():
            for style in ("flat", "rich"):
                d = Drawing(400, 300)
                d.place(make(style), at=(200, 150), key="p")
                xml = quiet_slide(d, width=400)
                embeds = xml.count("<embed")
                if style == "flat":
                    self.assertEqual(embeds, 0, name)
                elif name != "antibody":
                    self.assertTrue(1 <= embeds <= 2, (name, embeds))
                self.assertIn("<shape", xml)
        d = Drawing(600, 200)
        g = membrane("M 20 100 C 200 40 400 160 580 100", thickness=24, cholesterol=True)
        self.assertLess(g.bounds.x, 25)
        self.assertGreater(g.bounds.x + g.bounds.width, 575)
        node = d.add("mem", g)
        x, y = d.resolve(node.port("end"))
        self.assertAlmostEqual(x, 580, places=3)
        self.assertIn("#E8B54A", d.to_svg())  # cholesterol rings present
        d.add("m2", membrane("M 20 180 L 580 180", style="flat"))
        flat = Drawing(600, 200)
        flat.add("m", membrane("M 20 100 L 580 100", style="flat"))
        self.assertNotIn("<embed", quiet_slide(flat, width=600))
        self.assertEqual(d.check(), [])


class CellInterfaceTest(unittest.TestCase):
    PAIRS = [
        {"top": "TCR", "bottom": "pMHC", "top_kind": "bar", "bottom_kind": "bar"},
        {"top": "PD-1", "bottom": "PD-L1", "bound": True, "blocked_by": "抗 PD-1"},
        {"top": "LAG-3", "bottom": "MHC-II"},
        {"top": "TIGIT", "bottom": "CD155"},
        {"top": "CD226", "bottom": "CD155", "bound": False},
    ]

    def test_ports_geometry_styles_and_conversion(self):
        for kind, pairs in (
            ("immune", self.PAIRS),
            ("neural", [{"bottom": "AMPA"}, {"bottom": "mGluR", "bottom_kind": "gpcr"}]),
        ):
            for style in ("rich", "flat"):
                g = built_part(self, lambda: cell_interface(pairs, width=820, kind=kind, style=style))
                self.assertTrue(
                    {"cleft", "top_cytoplasm", "bottom_cytoplasm", "bottom0_tip", "bottom0_base"} <= set(g.ports)
                )
                d = Drawing(900, 420)
                d.place(g, at=(450, 210), key="syn")
                self.assertEqual(d.check(), [], (kind, style))
                xml = quiet_slide(d, width=900)
                self.assertEqual("<embed" in xml, style == "rich")
                self.assertIn("突触" if kind == "neural" else "PD-L1", xml)
        g = cell_interface(self.PAIRS)
        p = g.ports
        for i in range(5):
            self.assertLess(p[f"top{i}_base"][1], p[f"top{i}_tip"][1])  # receptor hangs down
            self.assertGreater(p[f"bottom{i}_base"][1], p[f"bottom{i}_tip"][1])  # ligand rises up
        self.assertAlmostEqual(p["top0_tip"][1], p["bottom0_tip"][1], places=6)  # bound pair meets
        self.assertGreater(p["bottom4_tip"][1] - p["top4_tip"][1], 10)  # unbound pair stays apart
        self.assertIn("block1", p)
        self.assertEqual(g.port_directions["top1_base"], (0.0, -1.0))
        d = Drawing(900, 380)
        syn = d.place(g, at=(450, 230), key="syn")
        box = d.box_at((620, 30), "SHP2", font_size=14, fill="#9B2D6F", text_fill="#FFFFFF")
        d.arrow(syn.port("top1_base"), box, head="inhibit")
        self.assertEqual(d.check(), [])
        self.assertIn("ellipse", ET.tostring(receptor(kind="igsf", domains=3).element, encoding="unicode"))
        self.assertIn("cell_interface", drawing_help("免疫突触"))
        with self.assertRaises(ValueError):
            cell_interface([{"top": "X", "top_kind": "blob"}])


class EnvelopeBiofilmTest(unittest.TestCase):
    PROTEINS = [
        {"kind": "tripartite_pump", "at": 0.2, "label": "AcrAB–TolC"},
        {"kind": "porin", "at": 0.55, "label": "OmpF"},
        {"kind": "abc", "at": 0.85, "label": "MacAB"},
    ]

    def test_cell_envelope_and_biofilm(self):
        for gram, prots in (
            ("negative", self.PROTEINS),
            ("positive", [{"kind": "mfs", "at": 0.3, "label": "NorA"}, {"kind": "channel", "at": 0.7}]),
        ):
            for style in ("rich", "flat"):
                g = built_part(self, lambda: cell_envelope(820, gram=gram, proteins=prots, drugs=True, style=style))
                need = {"outside", "periplasm", "inner_membrane", "cytoplasm", "p0", "p0_entry", "p0_exit", "p1_exit"}
                self.assertTrue(need <= set(g.ports), gram)
                self.assertEqual("outer_membrane" in g.ports, gram == "negative")
                d = Drawing(860, g.bounds.height + 20)
                env = d.place(g, at=(430, (g.bounds.height + 20) / 2), key="env")
                d.arrow(env.port("p0_entry"), env.port("p0_exit"), curve=-30, stroke="#D23B3B")
                self.assertEqual(d.check(), [], (gram, style))
                xml = quiet_slide(d, width=860)
                self.assertEqual("<embed" in xml, style == "rich")
                self.assertIn("胞质", xml)
                self.assertIn("外膜" if gram == "negative" else "细胞壁", xml)
        p = cell_envelope(820, proteins=self.PROTEINS).ports
        self.assertLess(p["p0_exit"][1], p["outer_membrane"][1])  # TolC opens to the outside
        self.assertGreater(p["p0_entry"][1], p["outer_membrane"][1])  # AcrB entry below the OM
        self.assertLess(p["p2_exit"][1], p["inner_membrane"][1] + 1)  # ABC exports to the periplasm
        for h in ("外排泵", "LPS", "周质", "孔蛋白", "外膜"):
            self.assertIn("cell_envelope", drawing_help(h))
        with self.assertRaises(ValueError):
            cell_envelope(proteins=[{"kind": "pump"}])
        with self.assertRaises(ValueError):
            cell_envelope(gram="positive", proteins=[{"kind": "porin"}])
        for style in ("rich", "flat"):
            for gradient in ("oxygen", "nutrient"):
                g = built_part(self, lambda: biofilm_section(760, 300, gradient=gradient, style=style), centered=False)
                self.assertAlmostEqual(g.bounds.x + g.bounds.width / 2, 0, places=6)
                self.assertTrue({"surface", "channel", "top", "core", "persister", "colony0"} <= set(g.ports))
                d = Drawing(800, 360)
                bf = d.place(g, at=(400, 180), key="bf")
                d.callout("p", "持留菌", bf.port("persister"), at=(740, 40), font_size=13)
                self.assertEqual(d.check(), [], (style, gradient))
                xml = quiet_slide(d, width=800)
                self.assertEqual("<embed" in xml, style == "rich")
                self.assertIn("缺氧" if gradient == "oxygen" else "营养匮乏", xml)
        g = biofilm_section(760, 300)
        self.assertGreater(g.ports["surface"][1], g.ports["top"][1])
        self.assertGreater(g.ports["persister"][1], g.ports["top"][1])
        self.assertNotIn("persister", ET.tostring(biofilm_section(features=("channels",)).element, encoding="unicode"))
        for h in ("生物膜", "持留菌"):
            self.assertIn("biofilm_section", drawing_help(h))
        with self.assertRaises(ValueError):
            biofilm_section(features=("spores",))

    def test_encoder_decoder_and_patch_embed(self):
        levels = [(64, 256), (128, 128), (256, 64), (512, 32), (1024, 16)]
        for kw in ({}, {"bottleneck": "transformer"}, {"layout": "flat", "io": None}, {"skip": "add", "legend": False}):
            for style in ("rich", "flat"):
                g = encoder_decoder(levels, style=style, **kw)
                self.assertAlmostEqual(g.bounds.x + g.bounds.width / 2, 0, places=6)
                self.assertEqual(first_drawn(g).get("data-outline"), "1")
                self.assertTrue(
                    {"input", "output", "bottleneck", "enc0", "enc4", "dec0", "dec3", "skip0", "skip3"} <= set(g.ports),
                    kw,
                )
                d = Drawing(g.bounds.width + 40, g.bounds.height + 40)
                d.place(g, at=(d.width / 2, d.height / 2), key="net")
                self.assertEqual(d.check(), [], (kw, style))
                xml = quiet_slide(d, width=900)
                self.assertEqual("<embed" in xml, style == "rich")
                self.assertIn("1024", xml)
        u = encoder_decoder(levels)
        # resolution sets the level: deeper encoder levels sit lower in the U, the output ends level with the input
        self.assertLess(u.ports["enc0"][1], u.ports["enc2"][1])
        self.assertAlmostEqual(u.ports["input"][1], u.ports["output"][1], places=6)
        self.assertIn(
            "Multi-Head", ET.tostring(encoder_decoder(levels, bottleneck="transformer").element, encoding="unicode")
        )
        self.assertIn("skip, add", ET.tostring(encoder_decoder(levels, skip="add").element, encoding="unicode"))
        for bad in ({"layout": "v"}, {"skip": "mul"}, {"bottleneck": "lstm"}):
            with self.assertRaises(ValueError):
                encoder_decoder(levels, **bad)
        with self.assertRaises(ValueError):
            encoder_decoder([(64, 32)])
        for style in ("rich", "flat"):
            for kw in ({}, {"grid": (3, 3), "image": "photo", "proj_label": None, "pos": False, "cls": False}):
                g = patch_embed(style=style, **kw)
                self.assertAlmostEqual(g.bounds.y + g.bounds.height / 2, 0, places=6)
                d = Drawing(1000, 460)
                pe = d.place(g, at=(330, 300), key="pe")
                enc = d.place(transformer_block(n=12), at=(860, 230), key="enc")
                d.arrow(pe.port("tokens_right"), enc.port("input"), route="orthogonal")
                self.assertEqual(d.check(), [], kw)
                quiet_slide(d, width=960)
        g = patch_embed(grid=(4, 4), max_tokens=6)
        self.assertTrue({"image", "tokens", "tokens_right", "cls", "token0", "token15", "proj"} <= set(g.ports))
        self.assertNotIn("token5", g.ports)  # elided behind the ellipsis
        self.assertLess(g.ports["tokens"][1], g.ports["proj"][1])  # tokens sit above the projection bar
        for h, name in (
            ("U-Net", "encoder_decoder"),
            ("编码器", "encoder_decoder"),
            ("特征图", "tensor_block"),
            ("注意力", "transformer_block"),
            ("patch", "patch_embed"),
            ("Transformer", "transformer_block"),
        ):
            self.assertIn(name, drawing_help(h))
        self.assertIn("patch_embed", drawing_help("parts"))

    def test_soil_aggregate(self):
        for kw in (
            {},
            {"root": True},
            {"kind": "sediment", "size": (520, 300), "anoxic": 0.3},
            {"anoxic": 0, "legend": False},
        ):
            for style in ("rich", "flat"):
                g = built_part(self, lambda: soil_aggregate(style=style, **kw), centered=False)
                self.assertAlmostEqual(g.bounds.x + g.bounds.width / 2, 0, places=6)
                self.assertTrue(
                    set("oxic anoxic pore water water_film grain clay om microbe_oxic microbe_anoxic".split())
                    <= set(g.ports),
                    kw,
                )
                W, H = g.bounds.width + 320, g.bounds.height + 40
                d = Drawing(W, H)
                a = d.place(g, at=(g.bounds.width / 2 + 20, H / 2), key="soil")
                d.callout("c1", "有氧过程", a.port("oxic"), at=(W - 150, 30), font_size=13)
                d.callout("c2", "缺氧过程", a.port("anoxic"), at=(W - 150, H / 2), font_size=13)
                self.assertEqual(d.check(), [], (kw, style))
                xml = quiet_slide(d, width=900)
                self.assertEqual("<embed" in xml, style == "rich")
        agg = soil_aggregate()
        self.assertIn("boundary", agg.ports)
        ox, an = agg.ports["oxic"], agg.ports["anoxic"]
        self.assertGreater(math.hypot(ox[0] - an[0], ox[1] - an[1]), 100)  # oxic rim is far from the anoxic centre
        self.assertIn("root", soil_aggregate(root=True).ports)
        sed = soil_aggregate(kind="sediment", size=(520, 300))
        self.assertLess(sed.ports["surface"][1], sed.ports["oxic"][1])
        self.assertLess(sed.ports["oxic"][1], sed.ports["anoxic"][1])
        self.assertNotIn("空气", ET.tostring(sed.element, encoding="unicode"))
        for bad in ({"kind": "rock"}, {"anoxic": 1.2}):
            with self.assertRaises(ValueError):
                soil_aggregate(**bad)
        for h in ("土壤", "团聚体", "孔隙", "沉积物", "缺氧"):
            self.assertIn("soil_aggregate", drawing_help(h))
        self.assertIn("biofilm_section", drawing_help("氧梯度"))
        self.assertIn("water_column_section", drawing_help("水体"))

    def test_mea_textures_and_membrane_defects(self):
        L = [
            ("阳极流场板", 34, "#8A9099", "flowfield"),
            ("阳极 GDL", 30, "#5D6168", "fiber"),
            ("阳极催化层", 16, "#2F3238", "catalyst"),
            ("质子交换膜", 30, "#E9EEF2", "membrane"),
            ("阴极催化层", 18, "#2F3238", "catalyst"),
            ("阴极 GDL", 30, "#5D6168", "fiber"),
            ("阴极流场板", 34, "#8A9099", "flowfield"),
        ]
        for style in ("rich", "flat"):
            g = layer_stack(L, width=440, style=style)
            self.assertTrue({"layer_3_mid", "layer_3_left", "layer_6"} <= set(g.ports))
            d = Drawing(760, 280)
            d.place(g, at=(330, 140), key="mea")
            self.assertEqual(d.check(), [])
            xml = quiet_slide(d, width=760)
            self.assertIn("质子交换膜", xml)
            self.assertEqual("<embed" in xml, style == "rich")
        self.assertGreater(
            len(ET.tostring(layer_stack(L).element)), len(ET.tostring(layer_stack(L, style="flat").element)) * 3
        )
        with self.assertRaises(ValueError):
            layer_stack([("x", 10, "#FFFFFF", "felt")])
        sec = interface_section(
            [("CL", 30, "#3A3E46"), ("PEM", 70, "#E3ECF1"), ("CL", 30, "#3A3E46")],
            length=400,
            features=[("crack", 0, 0.2, None, {"through": True}), ("pinhole", 0, 0.5), ("delamination", 1, 0.78, 100)],
        )
        p = sec.ports
        self.assertTrue({"crack0_tip", "crack0_mouth", "pinhole0", "delamination0"} <= set(p))
        self.assertAlmostEqual(
            p["crack0_tip"][1], p["interface1"][1], delta=1.5
        )  # through-plane crack spans the membrane
        self.assertAlmostEqual(p["delamination0"][1], p["interface1"][1], places=6)
        for h in ("催化层", "气体扩散层", "流场"):
            self.assertIn("layer_stack", drawing_help(h))


class MatterPartsATest(unittest.TestCase):
    def test_matter_parts_contract_and_old_signatures(self):
        rows = [[("Na", "#E24C3B"), ("Cl", "#3FA34D")] * 3, [("Cl", "#3FA34D"), None] * 3]
        makers = {
            "atom": lambda s: atom("Na", charge="+", style=s),
            "lattice": lambda s: lattice(
                rows, bonds=True, unit_cell=(0, 0, 2, 1), depth=1, show_vacancies=True, style=s
            ),
            "particle": lambda s: particle(60, grains=7, shell=6, cracks=2, coating=4, style=s),
        }
        for name, make in makers.items():
            for style in ("rich", "flat"):
                g = make(style)
                assert_centered(self, g, name)
                self.assertEqual(first_drawn(g).get("data-outline"), "1", name)
                d = Drawing(400, 300)
                d.place(g, at=(200, 150), key="p")
                self.assertEqual(d.check(), [])
                xml = quiet_slide(d, width=400)
                if style == "flat":
                    self.assertNotIn("<embed", xml, name)
                    self.assertNotIn("Gradient", ET.tostring(g.element, encoding="unicode"), name)
                else:
                    self.assertIn("<embed", xml, name)
        a = atom("Na", r=14, fill="#E24C3B", stroke="none", text_fill="#FFFFFF", font_size=12)
        self.assertAlmostEqual(a.bounds.width, 28, places=6)
        lat = lattice(
            [[("O", "#A9BBD6")] * 4, [("Na", "#E24C3B"), None] * 2], pitch=26, layer_gap=22, r=8, offsets=[0, 0.5]
        )
        self.assertGreater(lat.bounds.width, 26 * 3)
        p = particle(
            70, fill="#E8E2D6", stroke="#6B6F78", grains=5, shell=8, shell_fill="#B9C8E0", cracks=2, accent="#D6453A"
        )
        self.assertAlmostEqual(p.bounds.width, 140, places=6)
        self.assertIn("shell", p.ports)
        self.assertGreater(lattice([["C", "C"]]).bounds.width, 24)


class FlowchartRoutingTest(unittest.TestCase):
    def test_orthogonal_links_between_rows_use_top_bottom_and_avoid_other_boxes(self):
        d = Drawing(600, 360)
        top = d.box_at((300, 90), "随机分配", font_size=14, stroke="#333")
        left = d.box_at((140, 170), "处理组社区 MFI 进入、开放贷款", font_size=13, stroke="#333")
        right = d.box_at((460, 170), "对照组社区 暂不进入", font_size=13, stroke="#333")
        mid = d.box_at((300, 250), "基线与终线调查", font_size=13, stroke="#333")
        links = [
            d.arrow(top, left, route="orthogonal"),
            d.arrow(left, mid, route="orthogonal"),
            d.arrow(right, mid, route="orthogonal"),
        ]
        self.assertEqual([(l.start.name, l.end.name) for l in links], [("bottom", "top")] * 3)
        layout = _Layout(d)
        for link in links:
            pts = _connector_points(link, layout)
            others = [n for n in (top, left, right, mid) if n not in (link.start.node, link.end.node)]
            for n in others:
                b = layout.bounds(n)
                self.assertFalse(any(crosses(p, q, b.padded(-2)) for p, q in zip(pts, pts[1:])), n.key)
        self.assertEqual(d.check(), [])


class NucleicAcidPartsTest(unittest.TestCase):
    def test_duplex_strand_and_protein_ports_flat_native_and_convert(self):
        for style in ("rich", "flat"):
            dna = duplex(
                600,
                bubble=(0.35, 0.6),
                nick=0.62,
                flap=(0.62, 40),
                highlight=[(0.42, "#C2457A")],
                pam=(0.65, 0.7),
                style=style,
            )
            self.assertTrue({"bubble", "bubble_top", "nick", "flap_tip", "pam", "hl0", "top_5"} <= set(dna.ports))
            self.assertAlmostEqual(dna.bounds.x + dna.bounds.width / 2, 0, places=6)
            cas = protein_complex(260, 150, label="nCas9", fused=("RT", "#6C5BA7"), nickase=True, style=style)
            self.assertTrue({"groove", "fused", "linker"} <= set(cas.ports))
            svg = ET.tostring(dna.element, encoding="unicode") + ET.tostring(cas.element, encoding="unicode")
            self.assertEqual("Gradient" in svg, style == "rich")
            self.assertEqual(
                ET.tostring(dna.element),
                ET.tostring(
                    duplex(
                        600,
                        bubble=(0.35, 0.6),
                        nick=0.62,
                        flap=(0.62, 40),
                        highlight=[(0.42, "#C2457A")],
                        pam=(0.65, 0.7),
                        style=style,
                    ).element
                ),
            )
            d = Drawing(900, 360)
            d.place(cas, at=(450, 150), key="cas")
            node = d.place(dna, at=(450, 220), key="dna")
            x, y = d.resolve(node.port("bubble_bottom"))
            d.add(
                "sg",
                nucleic_strand(
                    f"M {x - 60} {y - 10} L {x + 60} {y - 10}", segments=[(0, 0.6, "#C2457A", "间隔区")], style=style
                ),
            )
            self.assertEqual(d.check(), [])
            self.assertIn("5′", quiet_slide(d, x=30, y=90, width=900))
        with self.assertRaises(ValueError):
            duplex(400, flap=(0.5, 30))


class EarthPartsTest(unittest.TestCase):
    def makers(self):
        return {
            "globe": lambda s: globe(120, sea_ice=76, jet=dict(waves=4, highs=[10], lows=[-80]), style=s),
            "side": lambda s: globe(80, view="side", lon0=-30, points={"gl": (72, -40)}, style=s),
            "jet": lambda s: jet_stream(120, waves=5, highs=[0], lows=[36], style=s),
            "section": lambda s: atmosphere_section(360, 220, warming=True, style=s),
            "coral": lambda s: coral_polyp(240, style=s),
            "bleached": lambda s: coral_polyp(240, bleached=True, style=s),
            "symbiont": lambda s: symbiont(50, stressed=True, style=s),
        }

    def test_centered_ports_deterministic_and_flat_native(self):
        # the jet overlay is native in both styles
        makers = self.makers()
        self.assertEqual(
            assert_parts_centered_native(self, makers, embeds=lambda name: (0 if name == "jet" else 1, 2)), len(makers)
        )

    def test_semantic_ports(self):
        g = globe(100, jet=dict(waves=4, highs=[0], lows=[-90]))
        for k in ("pole", "equator", "H0", "L0", "ridge0", "trough3"):
            self.assertIn(k, g.ports)
        self.assertLess(math.hypot(*g.ports["H0"]), math.hypot(*g.ports["L0"]))  # blocking high poleward of the low
        self.assertEqual(globe_point(100, 90, 0), (0.0, 0.0))
        self.assertIn("gl", globe(80, view="side", points={"gl": (72, -40)}).ports)
        s = atmosphere_section(400, 240)
        self.assertLess(s.ports["vortex"][1], s.ports["jet"][1])  # vortex above the jet core
        self.assertGreater(s.ports["pole"][0], s.ports["equator"][0])
        healthy, pale = coral_polyp(240), coral_polyp(240, bleached=True)
        for k in tuple(
            "mouth oral_disc tentacle_tip0 tentacle_tip3 gastrodermis calicoblastic skeleton symbiont0".split()
        ):
            self.assertIn(k, healthy.ports)
        n = lambda g: sum(k.startswith("symbiont") for k in g.ports)
        self.assertLess(n(pale), n(healthy) / 2)
        self.assertIn("expelled0", pale.ports)
        self.assertLess(healthy.ports["tentacle_tip0"][1], healthy.ports["mouth"][1])
        self.assertGreater(healthy.ports["skeleton"][1], healthy.ports["calicoblastic"][1])
        for k in ("symbiosome", "chloroplast", "pyrenoid", "nucleus", "accumulation_body"):
            self.assertIn(k, symbiont(40).ports)
        with self.assertRaises(ValueError):
            coral_polyp(200, tentacles=3)
        with self.assertRaises(ValueError):
            globe(100, view="side", jet=True)


class GenericPartsTest(unittest.TestCase):
    """porous_framework / molecule presets / microplastic / water column / organisms / system icons."""

    def makers(self):
        m = {
            "electrode": lambda s: porous_electrode(360, 220, style=s),
            "electrode_deg": lambda s: porous_electrode(
                360, 220, features=["carbon_whisker", "sulfur", "agglomeration", "crack"], style=s
            ),
            "electrode_coke": lambda s: porous_electrode(300, 200, features=["coke"], electrolyte=False, style=s),
            "iface_whisker": lambda s: interface_section(
                [("gas", 80, "#EEF4FA"), ("Ni", 50, "#8C97A3", "polycrystal")],
                length=240,
                features=[("whisker", 0, 0.3, -60), ("adsorbate", 0, 0.75, -80, {"coverage": 0.5})],
                style=s,
            ),
            "star": lambda s: star(80, kind="m_dwarf", spots=2, style=s),
            "planet_gg": lambda s: planet(50, kind="gas_giant", style=s),
            "planet_rock": lambda s: planet(50, kind="rocky", light=0, style=s),
            "transit": lambda s: transit_geometry(460, 220, impact=0.3, style=s),
            "mof_sq": lambda s: porous_framework(
                "square", cells=(3, 2), open_metal_sites=True, functional_groups="NH2", guests=["CO2"] * 3, style=s
            ),
            "mof_hex": lambda s: porous_framework("hex", cells=(3, 2), guests={0: ["CH4"], 2: ["H2O", "H2O"]}, style=s),
            "mof_cage": lambda s: porous_framework("cage", guests={0: ["CO2", "CO2"]}, open_metal_sites=True, style=s),
            "mof_ch": lambda s: porous_framework(
                "channel", cells=(4, 1), node_shape="cluster", guests=["N2", "CO2"], style=s
            ),
            "water": lambda s: water_column_section(420, 260, thermocline=True, particles=12, plants=2, style=s),
            "grid": lambda s: image_grid(5, kind="recon", arrows=True, captions=["a", "", "", "", "b"], style=s),
            "vec": lambda s: vector_packet(6, name="Δw", encrypted=True, noise=True, style=s),
        }
        m.update(
            {f"mol_{k}": (lambda k: lambda s: molecule(k, style=s))(k) for k in ("CO2", "CH4", "carbamate", "benzene")}
        )
        m.update(
            {
                f"mp_{k}": (lambda k: lambda s: microplastic(k, 80, aged=True, biofilm=True, style=s))(k)
                for k in ("fragment", "fiber", "film", "bead")
            }
        )
        m.update(
            {
                f"org_{k}": (lambda k: lambda s: organism(k, 90, flip=k == "fish", style=s))(k)
                for k in ("fish", "daphnia", "copepod", "algae", "bivalve", "worm", "plant", "mouse", "human")
            }
        )
        m.update(
            {
                f"dev_{k}": (lambda k: lambda s: device(k, 50, lock=k == "server", name=k, style=s))(k)
                for k in ("phone", "laptop", "server", "database", "cloud", "hospital", "edge", "camera", "gpu")
            }
        )
        return m

    def test_centered_deterministic_flat_native_and_reviewed_as_detailed(self):
        makers = self.makers()
        self.assertEqual(assert_parts_centered_native(self, makers, paired=True, first_outline=False), len(makers))

    def test_generic_parts_semantic_ports_and_porous_electrodes(self):
        mof = porous_framework(
            "square", cells=(3, 2), open_metal_sites=True, functional_groups="NH2", guests=["CO2"] * 6
        )
        for k in ("pore0", "pore5", "node0", "edge0", "oms0", "fg0", "guest5"):
            self.assertIn(k, mof.ports)
        self.assertEqual(sum(k.startswith("pore") for k in mof.ports), 6)
        self.assertIn("inlet", porous_framework("channel", cells=(3, 1)).ports)
        with self.assertRaises(ValueError):
            porous_framework("kagome")
        # CO2 linear, H2O bent at 104.5°, CH4 four H around C
        co2 = molecule("CO2").ports
        self.assertAlmostEqual(co2["atom_0"][1], co2["atom_2"][1], places=6)
        h2o = molecule("H2O").ports
        (ox, oy), (ax, ay), (bx, by) = h2o["atom_0"], h2o["atom_1"], h2o["atom_2"]
        ang = math.degrees(math.atan2(ay - oy, ax - ox) - math.atan2(by - oy, bx - ox))
        self.assertAlmostEqual(abs(ang), 104.5, places=3)
        self.assertEqual(sum(k.startswith("atom") for k in molecule("CH4").ports), 5)
        self.assertIn("atom_1", molecule([("O", -40, 0, "#E24C3B"), ("C", 0, 0, "#333")], [(0, 1, 2)]).ports)
        with self.assertRaises(ValueError):
            molecule("XeF9")
        mp = microplastic("fragment", aged=True, biofilm=True)
        for k in ("biofilm", "bacteria0", "crack0", "pit0", "surface"):
            self.assertIn(k, mp.ports)
        w = water_column_section(400, 300, thermocline=True, plants=2)
        P = w.ports
        self.assertLess(P["surface"][1], P["thermocline"][1])
        self.assertLess(P["thermocline"][1], P["bed"][1])
        self.assertLess(P["bed"][1], P["sediment"][1])
        self.assertIn("plant1", P)
        self.assertAlmostEqual(water_point(400, 300, 0.5, 0)[1], P["surface"][1], delta=3)
        f, ff = organism("fish", 100), organism("fish", 100, flip=True)
        self.assertGreater(f.ports["head"][0], f.ports["tail"][0])
        self.assertLess(ff.ports["head"][0], ff.ports["tail"][0])
        for kind, k in (
            ("daphnia", "eggs"),
            ("bivalve", "siphon"),
            ("worm", "clitellum"),
            ("mouse", "ear"),
            ("human", "liver"),
        ):
            self.assertIn(k, organism(kind).ports, kind)
        self.assertIn("screen", device("phone").ports)
        self.assertIn("img4", image_grid(5).ports)
        self.assertIn("badge", vector_packet(4, encrypted=True).ports)
        self.assertEqual(sum(k.startswith("cell") for k in vector_packet(values=[0.1, -0.5, 0.9]).ports), 3)
        e = porous_electrode(400, 240)
        for k in ("top", "electrolyte", "pore0", "phaseA0", "phaseB0", "tpb0"):
            self.assertIn(k, e.ports)
        self.assertLess(e.ports["top"][1], e.ports["electrolyte"][1])  # gas side above the electrolyte
        n_tpb = sum(k.startswith("tpb") for k in e.ports)
        self.assertGreater(n_tpb, 5)
        self.assertFalse(any(k.startswith("tpb") for k in porous_electrode(400, 240, tpb=False).ports))
        dense = sum(k.startswith("pore") for k in porous_electrode(400, 240, porosity=0.1).ports)
        open_ = sum(k.startswith("pore") for k in porous_electrode(400, 240, porosity=0.5).ports)
        self.assertGreater(open_, dense)
        w = porous_electrode(400, 240, features=[("carbon_whisker", {"count": 2})])
        self.assertIn("whisker1_tip", w.ports)
        self.assertLess(w.ports["whisker0_tip"][1], w.ports["whisker0_base"][1])  # tip growth: particle lifted away
        ag = porous_electrode(400, 240, features=["agglomeration"])
        self.assertIn("agglomerate0", ag.ports)
        self.assertLess(sum(k.startswith("phaseA") for k in ag.ports), sum(k.startswith("phaseA") for k in e.ports))
        for f in ("sulfur", "coke", "crack"):
            self.assertIn(
                {"sulfur": "sulfur0", "coke": "coke0", "crack": "crack0"}[f],
                porous_electrode(400, 240, features=[f]).ports,
            )
        with self.assertRaises(ValueError):
            porous_electrode(400, 240, features=["rust"])
        sec = interface_section(
            [("gas", 80, "#EEF4FA"), ("Ni", 50, "#8C97A3")],
            length=240,
            features=[("whisker", 0, 0.3, -60), ("adsorbate", 0, 0.5, -100, {"coverage": 1})],
        )
        self.assertLess(sec.ports["whisker0_tip"][1], sec.ports["whisker0_base"][1])
        self.assertIn("adsorbate0", sec.ports)
        self.assertIn("spot1", star(80, spots=2).ports)
        with self.assertRaises(ValueError):
            star(80, kind="pulsar")
        p = planet(50, light=180)
        self.assertLess(p.ports["dayside"][0], p.ports["nightside"][0])  # star on the left → dayside on the left
        self.assertLess(p.ports["atmosphere_top"][1], p.ports["top"][1] + 1)
        t = transit_geometry(640, 280, impact=0.3)
        for k in ("star", "planet", "atmosphere", "limb", "observer", "inset"):
            self.assertIn(k, t.ports)
        sx, px, ox = t.ports["star"][0], t.ports["planet"][0], t.ports["observer"][0]
        self.assertLess(sx, px)
        self.assertLess(px, ox)  # star → planet → observer in one line
        self.assertAlmostEqual(t.ports["limb"][0], px, places=6)  # grazing ray passes over the terminator
        self.assertGreater(abs(t.ports["limb"][1] - t.ports["planet"][1]), 0)
        self.assertNotIn("inset", transit_geometry(640, 280, inset=False).ports)
        text = drawing_help("parts")
        for name in tuple(
            "porous_framework microplastic water_column_section organism device image_grid vector_packet porous_electrode star planet transit_geometry".split()
        ):
            self.assertIn(name, text)


class OrganPartsTest(unittest.TestCase):
    def makers(self):
        return {
            "sagittal": lambda s: brain(260, regions=["nts", "hypothalamus"], style=s),
            "lateral": lambda s: brain(260, view="lateral", regions={"temporal": "#5E8FC2"}, style=s),
            "multipolar": lambda s: neuron(300, style=s),
            "pseudo": lambda s: neuron(260, kind="pseudounipolar", style=s),
            "gut": lambda s: intestinal_wall(380, style=s),
            "heart": lambda s: heart(260, labels=True, style=s),
            "nephron": lambda s: nephron(240, highlight=("pct",), style=s),
            "bbb": lambda s: bbb_unit(240, style=s),
        }

    def test_organ_heart_nephron_and_bbb_anatomy(self):
        makers = self.makers()
        self.assertEqual(
            assert_parts_centered_native(self, makers, embeds=lambda name: (1, 3), no_complex=True), len(makers)
        )
        b = brain(300)
        for k in tuple("prefrontal hippocampus amygdala hypothalamus brainstem nts vagus cerebellum thalamus".split()):
            self.assertIn(k, b.ports)
        self.assertLess(b.ports["prefrontal"][0], b.ports["cerebellum"][0])  # anterior is left
        self.assertGreater(b.ports["nts"][1], b.ports["hypothalamus"][1])  # medulla below the diencephalon
        self.assertIn("motor", brain(300, view="lateral").ports)
        with self.assertRaises(ValueError):
            brain(300, regions=["motor"])  # not on the midline view
        p = neuron(260, kind="pseudounipolar")
        for k in ("soma", "axon_end", "ganglion", "peripheral_end", "central", "node0", "dendrite0"):
            self.assertIn(k, p.ports)
        self.assertLess(
            p.ports["peripheral_end"][0], p.ports["soma"][0] < p.ports["axon_end"][0] and p.ports["axon_end"][0]
        )
        m = neuron(300)
        self.assertGreaterEqual(sum(k.startswith("dendrite") for k in m.ports), 8)
        self.assertNotIn("node0", neuron(300, myelin=False).ports)
        g = intestinal_wall(400)
        for k in tuple(
            "lumen mucus epithelium eec eec_base goblet tight_junction lamina_propria capillary vagal_terminal vagal_fiber immune muscularis microbe0 villus_tip0".split()
        ):
            self.assertIn(k, g.ports)
        self.assertLess(g.ports["lumen"][1], g.ports["mucus"][1])
        self.assertLess(g.ports["mucus"][1], g.ports["lamina_propria"][1])
        self.assertLess(g.ports["lamina_propria"][1], g.ports["muscularis"][1])
        self.assertLess(math.dist(g.ports["eec_base"], g.ports["vagal_terminal"]), 20)
        self.assertGreaterEqual(sum(k.startswith("microbe") for k in g.ports), 20)
        self.assertNotIn("eec", intestinal_wall(400, cells=("enterocyte", "goblet")).ports)
        with self.assertRaises(ValueError):
            intestinal_wall(400, cells=("neuron",))
        h = heart(300)
        for k in tuple(
            "ra rv la lv septum apex aorta pa svc ivc pv mitral tricuspid aortic_valve pulmonary_valve".split()
        ):
            self.assertIn(k, h.ports)
        self.assertLess(h.ports["ra"][0], h.ports["la"][0])  # patient's left on image right
        self.assertGreater(h.ports["apex"][1], h.ports["lv"][1])  # apex points down
        self.assertLess(h.ports["aorta"][1], h.ports["la"][1])
        self.assertNotIn("<text", ET.tostring(h.element, encoding="unicode"))
        k = nephron(300)
        for p in tuple(
            "glomerulus bowman afferent efferent pct loop_desc loop_asc dct macula_densa cd cortex medulla".split()
        ):
            self.assertIn(p, k.ports)
        self.assertLess(k.ports["cortex"][1], k.ports["medulla"][1])
        self.assertLess(math.dist(k.ports["macula_densa"], k.ports["glomerulus"]), 60)  # DCT returns to its corpuscle
        self.assertIn("#D9822B", ET.tostring(nephron(300, highlight=("pct",)).element, encoding="unicode"))
        with self.assertRaises(ValueError):
            nephron(300, highlight=("ureter",))
        u = bbb_unit(300)
        for p in ("lumen", "endothelium", "tight_junction", "pericyte", "endfoot", "brain", "tight_junction2"):
            self.assertIn(p, u.ports)
        self.assertNotIn("tight_junction2", bbb_unit(300, cells=2).ports)
        with self.assertRaises(ValueError):
            bbb_unit(300, cells=4)


class PathwayLiverParadigmTest(unittest.TestCase):
    def quiet(self, g, size=(960, 600), native=False):
        d = Drawing(*size)
        d.place(g, at=(size[0] / 2, size[1] / 2), key="p")
        self.assertEqual(d.check(), [])
        xml = quiet_slide(d, width=size[0])
        self.assertIn("<shape", xml)
        if native:
            self.assertNotIn("<embed", xml)
        return xml

    def test_signaling_badges_stellate_trials_and_brain_networks(self):
        from ..svg_drawing import cell, liver_sinusoid

        g = signaling_cascade(
            ["A", {"name": "B", "phospho": True, "partner": "C"}],
            ligand="L",
            receptor="R",
            receptor_phospho=True,
            nucleus_targets=["G1", "G2"],
            feedback=[("G2", "receptor")],
            branches=[{"from": "receptor", "steps": ["X"]}],
            inhibitors=[("Drug", "A")],
        )
        p = g.ports
        for k in ("ligand", "receptor", "A", "B", "X", "G1", "G2", "nucleus", "dna", "Drug", "membrane", "A_right"):
            self.assertIn(k, p)
        self.assertLess(p["ligand"][1], p["membrane"][1])
        self.assertLess(p["membrane"][1], p["receptor"][1])
        self.assertLess(p["A"][1], p["B"][1])
        self.assertLess(p["B"][1], p["dna"][1])  # cascade runs down into the nucleus
        self.assertLess(p["X"][0], p["A"][0])  # branch column beside the trunk
        self.assertGreater(p["Drug"][0], p["A_right"][0])  # drug outside its target
        svg = ET.tostring(g.element, encoding="unicode")
        self.assertIn("#C0392B", svg)  # feedback / drug drawn in the inhibition colour
        self.quiet(g)
        self.quiet(
            signaling_cascade(["RAS", "RAF"], ligand="EGF", receptor="EGFR", receptor_kind="gpcr", style="flat"),
            native=True,
        )
        self.assertNotIn("nucleus", signaling_cascade(["A"], receptor="R").ports)
        with self.assertRaises(ValueError):
            signaling_cascade(["A"], feedback=[("Z", "A")])
        with self.assertRaises(ValueError):
            signaling_cascade(["A"], orientation="horizontal")
        d = Drawing(400, 200)
        for i in range(3):
            d.place(badge(str(i + 1)), at=(60 + 60 * i, 60), key=f"b{i}")
            d.ellipse_at((60 + 60 * i, 140), r=11, fill="#5B1061", key=f"c{i}")
            d.text_at((60 + 60 * i, 140), str(i + 1), font_size=16, fill="#FFFFFF", font_weight="bold", key=f"t{i}")
        d.ellipse_at((300, 140), r=11, fill="#5B1061", key="x")
        d.text_at((316, 140), "步骤", font_size=14, key="y")  # real straddle is still reported
        self.assertEqual([p["keys"] for p in d.check()], [["y", "x"]])
        with self.assertRaises(ValueError):
            badge("long text")
        q, a = cell(50, kind="stellate"), cell(80, kind="myofibroblast")
        self.assertIn("lipid", q.ports)
        self.assertIn("process0", q.ports)
        self.assertIn("stress_fiber", a.ports)
        self.assertIn("collagen", a.ports)
        self.quiet(q, (300, 300))
        self.quiet(cell(50, kind="stellate", style="flat"), (300, 300), native=True)
        s = liver_sinusoid(500)
        for k in tuple(
            "lumen endothelium fenestra disse hepatocyte hepatocyte2 kupffer stellate lipid inflow outflow".split()
        ):
            self.assertIn(k, s.ports)
        self.assertLess(s.ports["hepatocyte"][1], s.ports["disse"][1])
        self.assertLess(s.ports["disse"][1], s.ports["lumen"][1])
        f = liver_sinusoid(500, stellate="activated", fibrosis=0.8)
        self.assertIn("collagen", f.ports)
        self.assertNotIn("kupffer", liver_sinusoid(500, kupffer=False).ports)
        self.quiet(s)
        self.quiet(liver_sinusoid(500, style="flat"), native=True)
        with self.assertRaises(ValueError):
            liver_sinusoid(500, stellate="fibrotic")
        screens = [
            {"label": "注视", "dur": "500 ms", "content": "+"},
            {"label": "刺激", "dur": "500 ms", "content": "K"},
            {"label": "反应", "dur": "≤2000 ms", "kind": "response", "content": "按键"},
        ]
        g = trial_sequence(screens, repeat="×20")
        p = g.ports
        self.assertLess(p["screen0"][0], p["screen2"][0])
        self.assertLess(p["screen0"][1], p["screen2"][1])  # diagonal: right and down
        self.assertLess(p["time_start"][0], p["time_end"][0])
        xml = self.quiet(g, native=True)
        self.assertIn("500 ms", xml)
        r = trial_sequence(screens + [{"kind": "symbol", "content": "arrow_left"}], layout="row", screen=(96, 64))
        self.assertAlmostEqual(r.ports["screen0"][1], r.ports["screen3"][1])
        self.quiet(r, native=True)
        with self.assertRaises(ValueError):
            trial_sequence([{"kind": "symbol", "content": "star"}])
        g = brain(
            360,
            view="lateral",
            regions=["dlpfc"],
            nodes=[("dlpfc", "DLPFC", 0.8), ("ipl", "IPL", -0.4)],
            edges=[("DLPFC", "IPL", 0.6, "-")],
        )
        self.assertIn("node_DLPFC", g.ports)
        svg = ET.tostring(g.element, encoding="unicode")
        self.assertIn("#2E6FB0", svg)  # negative edge / node in blue
        self.assertIn("DLPFC", svg)
        self.quiet(g)
        with self.assertRaisesRegex(ValueError, 'view="lateral"'):
            brain(300, regions=["dlpfc"])
        with self.assertRaises(ValueError):
            brain(300, edges=[("a", "b")])


class MatterPartsBTest(unittest.TestCase):
    def test_layer_stack_thin_labels_flat_parts_and_legacy_tuples(self):
        g = layer_stack([("Au", 3, "#E2B33C"), ("吸收层", 30, "#5A4A7A")], width=140)
        texts = [t.text for t in g.element.iter() if t.tag.split("}")[-1] == "text"]
        self.assertIn("Au", texts)
        port = g.ports["layer_0"]
        self.assertGreater(port[0], 70)  # side label end lies right of the stack (width/2 from center)
        d = Drawing(960, 540)
        parts = (
            layer_stack(
                [("Ag", 4, "#B8BEC6", "metal"), ("钙钛矿", 40, "#3B3A55", "grain")],
                light=True,
                scale_bar=True,
                style="flat",
            ),
            battery_cell(380, 180, direction="charge", style="flat"),
            molecule(
                [("O", -40, 0, "#E24C3B"), ("C", 0, 0, "#333333"), ("O", 40, 0, "#E24C3B")],
                [(0, 1, 2), (1, 2, 2)],
                style="flat",
            ),
        )
        for i, (part, at) in enumerate(zip(parts, ((200, 150), (620, 250), (200, 430)))):
            node = d.place(part, at=at, key=f"m{i}")
            cx, cy = d.resolve(node.anchor("center"))
            self.assertAlmostEqual(cx, at[0], places=6)
            self.assertAlmostEqual(cy, at[1], places=6)
        xml = quiet_slide(d, width=960)
        self.assertNotIn("<embed", xml)
        for word in ("隔膜", "正极", "负极", "Ag"):
            self.assertIn(word, xml)
        g = layer_stack([("Ag", 16, "#B8BEC6"), ("钙钛矿", 44, "#3B3A55")])
        self.assertIn("layer_1", g.ports)
        assert_centered(self, g)


class EnergyDiagramTest(unittest.TestCase):
    MATS = [
        {"name": "A", "cb": -0.3, "vb": 2.9, "color": "#4A7EBB", "vb_text": "ox"},
        {"name": "B", "cb": -1.1, "vb": 1.6, "color": "#D9822B", "cb_text": "red"},
    ]
    REFS = [("H⁺/H₂", 0.0), ("O₂/H₂O", 1.23)]

    def scene(self, g):
        d = Drawing(round(g.bounds.width + 40), round(g.bounds.height + 40))
        return d, d.place(g, at=(d.width / 2, d.height / 2), key="ed")

    def test_energy_diagram_alignments_contacts_and_on_edge_exemption(self):
        for transfer, style in (("type2", "rich"), ("z", "flat"), ("s", "rich"), (None, "rich")):
            g = energy_diagram(self.MATS, ref_levels=self.REFS, transfer=transfer, style=style)
            assert_centered(self, g)
            self.assertTrue(
                {"A.cb", "A.vb", "B.cb", "B.vb", "A.top", "B.bottom", "ref0", "ref1"} <= set(g.ports), transfer
            )
            self.assertLess(g.ports["B.cb"][1], g.ports["A.cb"][1])  # more negative potential sits higher
            self.assertLess(g.ports["ref0"][1], g.ports["ref1"][1])
            self.assertEqual("interface0" in g.ports, transfer == "s")  # S-scheme implies contact + band bending
            d, ed = self.scene(g)
            d.arrow(ed.port("A.cb"), ed.port("B.cb"), stroke="#333333")
            self.assertEqual(d.check(), [], transfer)
            xml = quiet_slide(d, x=40, y=96, width=880)
            self.assertIn("<shape", xml)
            self.assertIn("H⁺/H₂", xml)
            if style == "rich":
                self.assertIn("<embed", xml)  # gradients stay a local SVG layer
        g = energy_diagram(
            [{"name": "n-Si", "cb": -4.05, "vb": -5.17, "ef": -4.25}, {"name": "Au", "ef": -5.1}],
            axis="vacuum",
            contact=True,
            vacuum=True,
        )
        self.assertTrue({"Au.ef", "n-Si.cb", "interface0"} <= set(g.ports))
        self.assertGreater(g.ports["Au.ef"][1], g.ports["n-Si.cb"][1])  # deeper Fermi level is lower
        self.assertEqual(self.scene(g)[0].check(), [])
        self.assertEqual(
            ET.tostring(g.element),
            ET.tostring(
                energy_diagram(
                    [{"name": "n-Si", "cb": -4.05, "vb": -5.17, "ef": -4.25}, {"name": "Au", "ef": -5.1}],
                    axis="vacuum",
                    contact=True,
                    vacuum=True,
                ).element
            ),
        )
        for h in ("能带", "能级", "异质结", "band", "CB", "VB", "Z-scheme", "肖特基", "费米能级"):
            self.assertIn("energy_diagram", drawing_help(h), h)
        self.assertIn("energy_diagram", drawing_help("parts"))
        for bad in ([{"name": "X", "cb": -1}], [{"name": "X"}], []):
            with self.assertRaises(ValueError):
                energy_diagram(bad)
        with self.assertRaises(ValueError):
            energy_diagram(self.MATS, transfer="type3")
        d = Drawing(400, 200)
        d.rect_at((200, 100), 200, 30, fill="#4A7EBB", key="band")
        e = d.box_at((200, 85), "e⁻", font_size=12, fill="#1F3A68", text_fill="#FFFFFF", shape="pill", key="e")
        d.arrow((340, 30), (250, 85), key="b")  # an arrow tip on the band's edge, not on a declared element
        self.assertEqual({p["kind"] for p in d.check()}, {"text_straddles_frame", "head_on_edge"})
        e.geometry.element.set("data-on-edge", "1")
        self.assertEqual([p["kind"] for p in d.check()], ["head_on_edge"])


class CrystalDefectPartsTest(unittest.TestCase):
    def test_crystal_defect_parts_build_and_physics(self):
        cases = [
            (close_packed(), set()),
            (close_packed("ABCABABCABC"), {"fault"}),
            (twin_lattice(), {"boundary", "twin", "matrix"}),
            (edge_dislocation(), {"core", "slip", "top", "burgers"}),
            (polycrystal(dislocations=4), {"g0", "g13", "twin0"}),
            (dislocation_symbol(), {"core"}),
            (close_packed("ABAB", style="flat"), set()),
        ]
        for g, ports in cases:
            self.assertAlmostEqual(g.bounds.x + g.bounds.width / 2, 0, places=6)
            self.assertTrue(ports <= set(g.ports), (ports, sorted(g.ports)))
            d = Drawing(round(g.bounds.width + 60), round(g.bounds.height + 60))
            d.place(g, at=(d.width / 2, d.height / 2), key="p")
            self.assertEqual(d.check(), [])
            self.assertIn("<shape", quiet_slide(d, x=40, y=96, width=min(880, d.width)))
        self.assertNotIn("fault", close_packed("ABCABCABC").ports)  # perfect FCC
        self.assertNotIn("fault", close_packed("ABABAB").ports)  # perfect HCP
        self.assertIn("fault", close_packed("ABABCBCB").ports)  # C layer breaks ABAB
        self.assertIn("fault2", close_packed("ABCABABCABCBCABC").ports)  # two faults
        g = edge_dislocation()
        self.assertLess(g.ports["top"][1], g.ports["core"][1])  # extra half-plane above the core
        self.assertAlmostEqual(g.ports["slip"][1], g.ports["core"][1])
        with self.assertRaises(ValueError):
            close_packed("AAB")


class EmPartsTest(unittest.TestCase):
    def scene(self, g):
        d = Drawing(round(g.bounds.width + 60), round(g.bounds.height + 60))
        return d, d.place(g, at=(d.width / 2, d.height / 2), key="p")

    def convert(self, d):
        return quiet_slide(d, x=40, y=96, width=min(880, d.width))

    def test_em_parts_ports_physics_and_composed_scene(self):
        parts = [
            coil(8),
            coil(8, core="iron", current="cw", field_lines=True),
            coil(6, winding="left", current="ccw", style="flat"),
            coil(kind="loop", view="face", current="cw"),
            coil(kind="loop", shape="rect", view="face", current="ccw"),
            coil(kind="loop", current="cw"),
            coil(12, kind="toroid", current="cw"),
            field_marks(300, 180),
            field_marks(240, 160, direction="out", keepout=(-40, -30, 80, 60)),
            rails_rod(),
            rails_rod(380, 140, load="galvanometer", field="out", velocity="left", current="cw"),
            rails_rod(load=None, field=None, velocity=None),
            circuit_loop(
                300,
                180,
                [
                    ("battery", "left", {"name": "ε"}),
                    ("switch", "top"),
                    ("resistor", "right", {"name": "R"}),
                    ("inductor", "bottom", {"name": "L"}),
                ],
                current="cw",
            ),
            circuit_loop(260, 160, ["source_dc", "resistor", "capacitor"], current="ccw", junctions=[("top", 0.3)]),
        ]
        for g in parts:
            assert_centered(self, g)
            d, _ = self.scene(g)
            self.assertEqual(d.check(), [])
            self.assertIn("<shape", self.convert(d))
        g = coil(8, length=200, current="cw")  # right-handed, cw seen from the b end → B points to -x
        self.assertTrue({"lead_a", "lead_b", "end_a", "end_b", "axis", "north", "south"} <= set(g.ports))
        self.assertEqual(g.ports["north"], g.ports["end_a"])
        self.assertEqual(
            coil(8, length=200, current="ccw").ports["north"], coil(8, length=200, current="ccw").ports["end_b"]
        )
        self.assertEqual(
            coil(8, current="cw", winding="left").ports["north"], coil(8, current="cw", winding="left").ports["end_a"]
        )  # B follows the seen circulation
        self.assertEqual(
            coil(8, current="a_to_b").ports["north"], coil(8, current="a_to_b").ports["end_b"]
        )  # right-handed helix
        self.assertEqual(
            coil(8, current="a_to_b", winding="left").ports["north"],
            coil(8, current="a_to_b", winding="left").ports["end_a"],
        )
        self.assertGreater(g.ports["lead_a"][1], g.ports["axis"][1])
        r = rails_rod(400, 160, rod_at=0.5)
        self.assertAlmostEqual(r.ports["rod_bottom"][1] - r.ports["rod_top"][1], 160)
        self.assertAlmostEqual(r.ports["rod_top"][0] - r.ports["load"][0], 200)
        c = circuit_loop(300, 200, [("battery", "left"), ("resistor", "right"), ("resistor", "top")])
        self.assertTrue({"tl", "br", "battery", "battery.a", "resistor", "resistor2", "resistor2.b"} <= set(c.ports))
        self.assertAlmostEqual(c.ports["br"][0] - c.ports["tl"][0], 300)
        self.assertAlmostEqual(c.ports["battery"][0], c.ports["tl"][0])
        self.assertIn("hole", field_marks(200, 100, keepout=(-20, -20, 40, 40)).ports)
        for bad in (
            lambda: coil(kind="helix"),
            lambda: field_marks(100, 100, direction="up"),
            lambda: rails_rod(load="motor"),
            lambda: circuit_loop(100, 100, [("resistor", "middle")]),
            lambda: circuit_loop(100, 100, ["resistor"], current="up"),
        ):
            with self.assertRaises(ValueError):
                bad()
        for k in ("galvanometer", "ammeter", "voltmeter", "rheostat", "inductor_core"):
            g = circuit_symbol(k, name="X")
            self.assertAlmostEqual(g.ports["b"][0] - g.ports["a"][0], 90)
        self.assertIn("wiper", circuit_symbol("rheostat").ports)
        self.assertNotEqual(
            ET.tostring(circuit_symbol("galvanometer", deflect=1).element),
            ET.tostring(circuit_symbol("galvanometer").element),
        )
        d = Drawing(960, 540)
        L = d.place(coil(9, length=250, diameter=96, current="cw"), at=(640, 210), key="coil")
        d.place(magnet(170, 44, field_lines=True), at=(300, 210), key="mag")
        g = d.place(circuit_symbol("galvanometer", deflect=1, name="G"), at=(640, 410), key="G")
        d.line(L.port("lead_a"), g.port("a"), route="orthogonal", key="w1")
        d.line(L.port("lead_b"), g.port("b"), route="orthogonal", key="w2")
        self.assertEqual(d.check(), [])
        self.convert(d)
        for q, name in (
            ("螺线管", "coil"),
            ("电流计", "circuit_symbol"),
            ("⊗", "field_marks"),
            ("导体棒", "rails_rod"),
            ("RL", "circuit_loop"),
            ("回路", "circuit_loop"),
        ):
            self.assertIn(f"【接口 {name}】", drawing_help(q), q)
        self.assertIn("field_lines=True", drawing_help("magnet"))


class MembraneBioenergeticsTest(unittest.TestCase):
    ETC = [
        {"name": "I", "shape": "L", "cofactors": ["FMN", "Fe-S"], "pumps": 4, "reaction": "NADH → NAD⁺"},
        "Q",
        {"name": "III", "shape": "dimer", "cofactors": ["heme b", "Fe-S"], "pumps": 4},
        {"kind": "peripheral", "name": "cyt c"},
        {"name": "IV", "cofactors": ["CuA", "heme a"], "pumps": 2, "e_sites": ("top", "bottom")},
        {"kind": "atp_synthase"},
    ]

    def scene(self, g):
        d = Drawing(round(g.bounds.width + 20), round(g.bounds.height + 20))
        return d, d.place(g, at=(d.width / 2, d.height / 2), key="g")

    def convert(self, d):
        return quiet_slide(d, x=40, y=100, width=880)

    def test_membrane_chain_parts_and_ion_markers(self):
        g = transport_chain(self.ETC, sides=("膜间隙", "基质"), terminal="½O₂ + 2H⁺ → H₂O", width=860, gradient=6)
        self.assertTrue(
            {"m0_e_out", "Q_e_in", "III_top", "IV_out", "m5_f1", "m5_proton_in", "membrane"} <= set(g.ports)
        )
        self.assertLess(g.ports["III_out"][1], g.ports["III_in"][1])  # protons pumped to the top (P) side
        d, _ = self.scene(g)
        self.assertEqual(d.check(), [])
        xml = self.convert(d)
        for s in ("膜间隙", "基质", "4H⁺", "½O₂ + 2H⁺ → H₂O", "cyt c", "NADH → NAD⁺"):
            self.assertIn(s, xml)
        # same chain machinery, different topic: nothing mitochondrial is hard-coded
        thy = transport_chain(
            [
                {"name": "PSII", "shape": "dimer", "cofactors": ["P680"]},
                {"kind": "lipid", "name": "PQ"},
                {"name": "b6f", "shape": "dimer", "pumps": 4},
                {"kind": "peripheral", "name": "PC", "cofactor": "Cu"},
                {"name": "PSI", "cofactors": ["P700"], "e_sites": ("top", "bottom")},
                {"kind": "atp_synthase", "n_c": 14},
            ],
            sides=("类囊体腔", "基质"),
            width=860,
        )
        self.assertEqual(self.scene(thy)[0].check(), [])
        self.assertNotIn("膜间隙", ET.tostring(thy.element, encoding="unicode"))
        for f1_side, flow in (("bottom", "synthesis"), ("top", "hydrolysis")):
            a = atp_synthase(n_c=12, f1_side=f1_side, flow=flow)
            self.assertTrue({"proton_in", "proton_out", "f1", "fo", "top", "tail"} <= set(a.ports))
            self.assertEqual(a.ports["f1"][1] > 0, f1_side == "bottom")
            self.assertEqual(self.scene(a)[0].check(), [])
        for shape in ("L", "dimer", "globular", "channel"):
            c = membrane_complex("X", shape=shape, cofactors=["Fe-S"], pumps=2)
            self.assertTrue({"e_in", "e_out", "in", "out", "tail", "cof0"} <= set(c.ports), shape)
            self.assertEqual(self.scene(c)[0].check(), [], shape)
        with self.assertRaises(ValueError):
            membrane_complex(shape="cube")
        with self.assertRaises(ValueError):
            transport_chain([{"kind": "complex"}] * 12, width=300)
        for fs in (10, 11, 14):
            for s in ("H⁺", "Na⁺", "Ca²⁺", "HCO₃⁻"):
                d = Drawing(200, 100)
                d.place(ion_marker(s, font_size=fs, r=4), at=(100, 50), key="i")
                d.rect_at((100, 30), 80, 20, fill="#4A7EBB", key="band")  # sitting on an edge is fine
                self.assertEqual(d.check(), [], s)
                xml = d.to_slide(x=0, y=0, width=200, summary=False)
                circ = re.search(
                    r'type="ellipse" topLeftX="([\d.]+)" topLeftY="([\d.]+)" width="([\d.]+)" height="([\d.]+)"', xml
                )
                text = re.search(
                    r'type="text" topLeftX="([\d.]+)" topLeftY="([\d.]+)" width="([\d.]+)" height="([\d.]+)"', xml
                )
                cx, cy, cw, ch = map(float, circ.groups())
                tx, ty, tw, th = map(float, text.groups())
                self.assertTrue(cx <= tx and tx + tw <= cx + cw and cy <= ty and ty + th <= cy + ch, (s, fs))
        for h in tuple(
            "呼吸链 电子传递链 ETC 光合链 类囊体 ATP合酶 F0F1 旋转马达 质子泵 H⁺ 质子梯度 膜蛋白复合物 ion".split()
        ):
            self.assertRegex(drawing_help(h), "transport_chain|membrane_complex|atp_synthase|ion_marker", h)


class InterfaceSectionTest(unittest.TestCase):
    LAYERS = [
        ("Li", 60, "#C3C9D2", "metal"),
        ("SEI", 14, "#B9A27C", "mosaic"),
        ("Li₆PS₅Cl", 120, "#E6DCC6", "polycrystal"),
    ]
    FEATURES = [
        ("dendrite", 0, 0.4, 100),
        ("void", 0, 0.75, -36),
        ("crack", 1, 0.15, 40),
        ("particle", 1, 0.55, 5),
        ("flux", 0, 0.2, 36, {"label": "Li⁺"}),
    ]

    def make(self, **kw):
        return interface_section(self.LAYERS, length=220, features=self.FEATURES, **kw)

    def test_interface_section_ports_seed_styles_and_errors(self):
        for stack in ("down", "right"):
            g = self.make(stack=stack)
            assert_centered(self, g)
            for name in tuple(
                "layer2 interface0 interface1 dendrite0_base dendrite0_tip void0 crack0_tip particle0 flux0".split()
            ):
                self.assertIn(name, g.ports, (stack, name))
            axis = 1 if stack == "down" else 0  # growth axis: dendrite tip lies deeper than its base
            self.assertGreater(g.ports["dendrite0_tip"][axis], g.ports["interface1"][axis] + 20)
            self.assertLess(g.ports["void0"][axis], g.ports["interface0"][axis])  # negative size grows into layer 0
        self.assertEqual(self.make().element.tag, "g")
        self.assertEqual(first_drawn(self.make()).get("data-outline"), "1")
        a, b = ET.tostring(self.make().element), ET.tostring(self.make().element)
        self.assertEqual(a, b)
        self.assertNotEqual(a, ET.tostring(self.make(seed=11).element))
        flat = self.make(style="flat", stack="right")
        self.assertNotIn("Gradient", ET.tostring(flat.element, encoding="unicode"))
        for style in ("flat", "rich"):
            d = Drawing(600, 360)
            sec = d.place(self.make(style=style, stack="right"), at=(300, 190), key="sec")
            d.callout("tip", "枝晶尖端", sec.port("dendrite0_tip"), at=(500, 345), font_size=13, own_anchor="center")
            xml = quiet_slide(d, width=600)
            self.assertEqual(xml.count("<embed") == 0, style == "flat", style)
            for word in ("Li₆PS₅Cl", "SEI", "Li⁺", "枝晶尖端"):
                self.assertIn(word, xml)
        with self.assertRaises(ValueError):
            interface_section(self.LAYERS, features=[("dendrite", 2, 0.5)])
        with self.assertRaises(ValueError):
            interface_section(self.LAYERS, features=[("bubble", 0, 0.5)])


class FinishToolsTest(unittest.TestCase):
    def test_finish_tools_dress_free_drawn_shapes(self):
        d = Drawing(600, 300)
        d.path_at(
            "M 20 100 C 150 100 200 180 300 180 C 400 180 450 100 580 100", fill="none", stroke="none", key="pm_line"
        )
        d.add(
            "pm", bilayer("M 20 100 C 150 100 200 180 300 180 C 400 180 450 100 580 100", thickness=14, cholesterol=3)
        )
        circle = "M 450 220 m -40 0 a 40 40 0 1 0 80 0 a 40 40 0 1 0 -80 0 Z"
        d.add("lipo", bilayer(circle, thickness=10))
        d.ellipse_at((120, 230), 20, fill="#C0504D", key="ball")
        d.add("ball_look", sphere_shading((120, 230), 20, "#C0504D"))
        d.add("soft", soft_shading("M 200 200 L 300 200 L 300 260 L 200 260 Z", "#EEE6FA"))
        d.add("np", circle_union([((330, 240), 12), ((346, 236), 10)], fill="#4A7DB5"))
        self.assertEqual(d.check(), [])
        self.assertEqual(shade("#808080", 1), "#FFFFFF")
        xml = d.to_slide(x=0, y=0, width=600)
        self.assertGreaterEqual(xml.count("<embed"), 3)
        self.assertIn('type="custom"', xml)


class LayoutSummaryTest(unittest.TestCase):
    def test_summary_reports_computed_layout_in_slide_units(self):
        d = Drawing(900, 420)
        a = d.box_at((150, 200), "A", font_size=16, stroke="#333")
        b = d.box_at((175, 200), "B", font_size=16, stroke="#333")
        c = d.box_at((700, 100), "C", font_size=16, stroke="#333")
        d.arrow(a, b, stroke_width=1)
        d.arrow(a, c, stroke_width=1.5)
        text = d.summary(width=300)
        self.assertIn("缩放 0.33", text)
        self.assertIn("实际长", text)
        warns = d.summary(width=300, warnings_only=True)
        self.assertTrue(any("只有 3px" in w or "只有 2px" in w or "只有 4px" in w for w in warns))
        self.assertTrue(any("线宽" in w for w in warns))
        self.assertTrue(any("抬到" in w for w in warns))
        self.assertEqual(Drawing(400, 200).summary(width=400, warnings_only=True), [])


class PlantTransportTest(unittest.TestCase):
    def test_plant_transporters_cells_and_root_section(self):
        from ..svg_drawing import transporter, cell, membrane
        from ..svg_drawing import root_section

        for kind in ("channel", "pump", "antiporter", "symporter", "abc", "aquaporin"):
            for style in ("rich", "flat"):
                g = transporter(kind, ions=("Na⁺", "H⁺"), atp=True, style=style)
                self.assertEqual(first_drawn(g).get("data-outline"), "1", kind)
                self.assertEqual(
                    ET.tostring(g.element),
                    ET.tostring(transporter(kind, ions=("Na⁺", "H⁺"), atp=True, style=style).element),
                )
                self.assertLess(g.ports["out"][1], g.ports["center"][1], kind)
                self.assertGreater(g.ports["in"][1], g.ports["center"][1], kind)
                f = transporter(kind, ions=("Na⁺", "H⁺"), flip=True, style=style)
                self.assertGreater(f.ports["out"][1], f.ports["in"][1], kind)
        a = transporter("antiporter", ions=("Na⁺", "H⁺")).ports
        self.assertTrue({"ion_out0", "ion_in0", "ion_out1", "ion_in1"} <= set(a))
        self.assertGreater(
            transporter("pump", membrane_thickness=40).bounds.height,
            transporter("pump", membrane_thickness=14).bounds.height,
        )
        d = Drawing(700, 360)
        d.add("pm", membrane("M 20 120 L 680 120", thickness=22))
        d.place(transporter("pump", ions=("H⁺",), direction="out", atp=True), at=(200, 120), anchor="tail", key="ha")
        c = d.place(cell(110, 70, kind="plant"), at=(520, 250), key="c")
        d.mount(transporter("symporter", membrane_thickness=8), on=c.contour_at(0.4, normal="outward"), key="s")
        d.mount(
            transporter("antiporter", membrane_thickness=8), on=c.contour_at(0.6, subpath=1, normal="left"), key="nhx"
        )
        self.assertEqual(d.check(), [])
        self.assertEqual(d.review(), [])
        self.assertIn("ATP → ADP + Pi", quiet_slide(d, width=700))
        for h in ("transporter", "反向转运", "水通道"):
            self.assertIn("transporter", drawing_help(h))
        with self.assertRaises(ValueError):
            transporter("uniporter")
        for style in ("rich", "flat"):
            g = cell(160, 110, kind="plant", style=style)
            self.assertEqual(first_drawn(g).get("data-outline"), "1")
            self.assertTrue(
                {"wall", "vacuole", "tonoplast", "cytoplasm", "nucleus", "chloroplast", "plasmodesma"} <= set(g.ports)
            )
            self.assertGreater(g.contour(0).length, g.contour(1).length)  # plasma membrane encloses the tonoplast
            self.assertEqual(ET.tostring(g.element), ET.tostring(cell(160, 110, kind="plant", style=style).element))
            r = root_section(300, pathways=True, style=style)
            self.assertAlmostEqual(r.bounds.x + r.bounds.width / 2, 0, places=6)
            self.assertEqual(first_drawn(r).get("data-outline"), "1")
            need = set("epidermis cortex endodermis casparian stele xylem phloem soil root_hair apoplast_block".split())
            self.assertTrue(need <= set(r.ports))
            d = Drawing(600, 360)
            n = d.place(r, at=(170, 180), key="root")
            d.callout("cs", "凯氏带", n.port("casparian"), at=(480, 80), font_size=13)
            self.assertEqual(d.check(), [], style)
            xml = quiet_slide(d, width=600)
            self.assertEqual("<embed" in xml, style == "rich")
        p = root_section(300).ports
        dist = lambda k: math.hypot(*p[k])
        self.assertLess(dist("xylem"), dist("endodermis"))
        self.assertLess(dist("endodermis"), dist("cortex"))
        self.assertLess(dist("cortex"), dist("epidermis"))
        self.assertNotIn("apoplast", p)
        for h in ("凯氏带", "根横切"):
            self.assertIn("root_section", drawing_help(h))
        with self.assertRaises(ValueError):
            root_section(arms=9)


class ReplaceSvgTest(unittest.TestCase):
    def test_replace_svg_and_svg_given_at_creation(self):
        from ..svg_drawing import cell

        d = Drawing(600, 300)
        a = d.place(cell(60, 45, style="flat"), at=(150, 150), key="a")
        b = d.box_at((450, 150), "Target", font_size=16, stroke="#333", key="b")
        link = d.arrow(a, b, key="ab")
        a.replace_svg(
            '<path d="M -50 0 C -50 -40 50 -40 50 0 C 50 30 -50 30 -50 0 Z" fill="#F3EEF8"/>'
            '<circle cx="10" cy="-5" r="12" fill="#C9B3E4"/>',
            ports={"tip": (50, 0)},
        )
        layout = _Layout(d)
        start = layout.point(link.start)
        self.assertAlmostEqual(start[1], 150, delta=1)
        self.assertGreater(start[0], 200)  # lands on the new outline, not the old box edge
        self.assertAlmostEqual(layout.bounds(a).x + layout.bounds(a).width / 2, 150, delta=0.5)
        self.assertIn("tip", a.geometry.ports)
        w0 = a.bounds.width
        a.replace_svg(a.svg_source(), fit="own")
        self.assertAlmostEqual(a.bounds.width, w0, delta=1)
        self.assertEqual(d.check(), [])
        with self.assertRaises(ValueError):
            a.replace_svg('<image href="x.png" width="10" height="10"/>')


class SvgNodeTest(unittest.TestCase):
    def test_svg_given_at_creation(self):
        from ..svg_drawing import cell

        d = Drawing(700, 320)
        t = d.place(cell(70, kind="t_cell"), at=(180, 160), key="t")
        tu = d.place(
            '<path d="M-90 0 C-90 -60 90 -60 90 0 C90 50 -90 50 -90 0 Z" fill="#F7ECE6"/>',
            at=(520, 160),
            size=(190, 150),
            key="tu",
        )
        m = d.svg_at((350, 280), '<rect x="-40" y="-16" width="80" height="32" rx="16" fill="#F2C9B5"/>', size=(90, 36))
        swapped = d.place(cell(50, kind="tumor"), at=(560, 60), svg='<circle r="40" fill="#EEE"/>')
        link = d.arrow(t, tu)
        end = _Layout(d).point(link.end)
        self.assertAlmostEqual(end[0], 430, delta=6)  # on the hand-written outline, not its box edge (425)
        self.assertAlmostEqual(tu.bounds.width, 190, delta=1)
        self.assertAlmostEqual(m.bounds.width, 90, delta=4)
        self.assertAlmostEqual(swapped.bounds.width, 110, delta=2)  # fitted into the part's own box
        self.assertEqual(d.check(), [])


class MarkerExpansionTest(unittest.TestCase):
    def test_no_marker_survives_in_any_arrow_form(self):
        d = Drawing(600, 300)
        a = d.box_at((100, 100), "A", font_size=16, stroke="#333")
        b = d.box_at((500, 100), "B", font_size=16, stroke="#333")
        d.arrow(a, b, opacity=0.5)
        d.arrow(a, b, opacity=0.6, curve=40, dashed=True, tail="inhibit")
        d.svg_at(
            (300, 220),
            '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" '
            'orient="auto"><path d="M0 0 L10 5 L0 10 Z" fill="#c00"/></marker></defs>'
            '<path d="M -80 0 Q 0 -40 80 0" fill="none" stroke="#c00" stroke-width="2" '
            'stroke-dasharray="5 4" marker-end="url(#ah)"/>',
            size=(200, 60),
        )
        xml = d.to_slide(x=0, y=0, width=600, summary=False)
        self.assertNotIn("<marker", xml)
        self.assertNotIn("marker-end", xml)
        self.assertIn('opacity="0.5"', xml.replace('opacity=".5"', 'opacity="0.5"'))
