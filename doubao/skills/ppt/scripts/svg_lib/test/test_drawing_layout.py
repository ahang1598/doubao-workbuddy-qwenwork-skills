"""Drawing layout helpers: labels, rows/grids/rings, tree layout and the shipped schematic examples."""

import tempfile
import unittest
import math
import re
import sys
from pathlib import Path
from collections import deque
from copy import deepcopy
from dataclasses import is_dataclass

SCRIPTS = Path(__file__).resolve().parents[2]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from ..svg_drawing import (
    Box,
    Drawing,
    drawing_help,
    label,
    rect,
    text_box,
    align,
    bipartite_order,
    column,
    distribute,
    grid,
    ring,
    row,
    spread_ports,
    TreeLayout,
    tree_layout,
)
from ..drawing_examples import band_alignment, compare_panels, membrane_transport, overview_zoom
from ..atomize_svg_to_slide import atomize_svg_to_slide, set_mapping
from ..drawing_lib._help import _DRAWING_APIS
from ..drawing_lib._labels import _connector_segments
from ..drawing_lib._review import suggest_parts
from ..drawing_lib._routing import crosses
from ..drawing_lib._scene import _Layout
from ..svg_drawing import cell, mitochondrion, nucleus, receptor


# ====================================================================================================
# Contracts for text-sized nodes and automatic label placement.
# ====================================================================================================


def overlap(a, b):
    w = min(a.x + a.width, b.x + b.width) - max(a.x, b.x)
    h = min(a.y + a.height, b.y + b.height) - max(a.y, b.y)
    return w > 1e-9 and h > 1e-9


class TextBoxTest(unittest.TestCase):
    def test_text_box_padding_ports_wrapping_shapes_and_errors(self):
        g = text_box("PD-1 / PD-L1 结合", font_size=16, padding=(12, 8))
        text = label("PD-1 / PD-L1 结合", font_size=16).bounds
        self.assertAlmostEqual(g.bounds.width, text.width + 24, places=6)
        self.assertAlmostEqual(g.bounds.height, text.height + 16, places=6)
        self.assertEqual(g.ports["right"], (g.bounds.width, g.bounds.height / 2))
        self.assertEqual(g.port_directions["top"], (0, -1))
        g = text_box("SHP-2 去磷酸化 CD28，抑制 TCR 下游信号", font_size=14, max_width=150, padding=10)
        self.assertLessEqual(g.bounds.width, 150 + 20 + 1e-6)
        self.assertGreaterEqual(len([e for e in g.element if e.tag == "text"]), 2)
        wide = text_box("A", font_size=14, min_width=120, min_height=40)
        self.assertEqual((wide.bounds.width, wide.bounds.height), (120, 40))
        pill = text_box("cell", font_size=14, shape="pill", box_style={"fill": "#E23D8A"})
        self.assertEqual(float(pill.element[0].get("rx")), pill.bounds.height / 2)
        ell = text_box("cell", font_size=14, shape="ellipse")
        self.assertEqual(ell.element[0].tag, "ellipse")
        with self.assertRaises(ValueError):
            text_box("x", font_size=14, shape="star")

    def test_text_box_atomizes_to_native_shape_and_text(self):
        d = Drawing(300, 120)
        d.add(
            "n",
            text_box("激活 T 细胞", font_size=16, box_style={"fill": "#F6EEF5", "stroke": "#7A2E83"}),
            at=(150, 60),
            own_anchor="center",
        )
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "n.svg"
            source.write_text(d.to_svg(), encoding="utf-8")
            set_mapping(300, 120, 0, 0, 300, 120)
            xml = atomize_svg_to_slide(source)
        self.assertIn('<shape type="rect"', xml)
        self.assertIn('<shape type="text"', xml)
        self.assertIn("激活 T 细胞", xml)
        self.assertNotIn("<embed", xml)


class PlaceLabelTest(unittest.TestCase):
    def scene(self):
        d = Drawing(700, 360)
        a = d.add("a", text_box("Source", font_size=16), at=(110, 90), own_anchor="center")
        b = d.add(
            "b",
            text_box("Target node with longer text", font_size=14, max_width=150),
            at=(420, 90),
            own_anchor="center",
        )
        blocker = d.add("blk", rect(110, 60), at=(600, 60), own_anchor="top_left")
        d.connect("ab", a.port("right"), b.port("left"))
        return d, a, b, blocker

    def test_labels_avoid_nodes_follow_anchors_and_reject_unknown_sides(self):
        d, a, b, blocker = self.scene()
        note = d.place_label("note", label("Key site: ITSM", font_size=13), b.port("right"))
        self.assertTrue(note.placement["clear"], note.placement)
        for other in (a, b, blocker):
            self.assertFalse(overlap(note.bounds, other.bounds), other.key)
        d, _, b, _ = self.scene()
        note = d.place_label("note", label("tag", font_size=13), b.port("top"), sides=["top"])
        before = note.bounds
        b.move_to(300, 200, own_anchor="center")
        after = note.bounds
        self.assertNotEqual((before.x, before.y), (after.x, after.y))
        crowded = Drawing(60, 40)
        crowded.add("wall", rect(60, 40), at=(0, 0), own_anchor="top_left")
        tag = crowded.place_label("t", label("too long label", font_size=13), (30, 20), avoid=[Box(0, 0, 60, 40)])
        self.assertFalse(tag.placement["clear"])
        d, _, b, _ = self.scene()
        with self.assertRaises(ValueError):
            d.place_label("n", label("x", font_size=12), b.port("top"), sides=["inside"])


class LabelConnectorTest(unittest.TestCase):
    def test_connector_labels_on_straight_vertical_and_orthogonal_routes(self):
        d = Drawing(500, 300)
        a = d.add("a", text_box("A", font_size=16), at=(80, 150), own_anchor="center")
        b = d.add("b", text_box("B", font_size=16), at=(420, 150), own_anchor="center")
        d.connect("ab", a.port("right"), b.port("left"))
        tag = d.label_connector("ab-l", "ab", label("activates", font_size=13))
        self.assertTrue(tag.placement["clear"], tag.placement)
        line = dict(d.items)["ab"]
        self.assertFalse(any(crosses(p, q, tag.bounds) for p, q in _connector_segments(line, _Layout(d))))
        mid_x = tag.bounds.x + tag.bounds.width / 2
        self.assertAlmostEqual(mid_x, 250, delta=40)
        d = Drawing(400, 400)
        a = d.add("a", text_box("A", font_size=16), at=(100, 60), own_anchor="center")
        b = d.add("b", text_box("B", font_size=16), at=(300, 320), own_anchor="center")
        d.connect("ab", a.port("bottom"), b.port("left"), route="orthogonal", start_direction="normal")
        tag = d.label_connector("l", "ab", label("inhibits", font_size=13))
        self.assertTrue(tag.placement["clear"], tag.placement)
        with self.assertRaises(ValueError):
            d.label_connector("x", "missing", label("x", font_size=12))
        with self.assertRaises(ValueError):
            d.label_connector("y", "ab", label("x", font_size=12), position=1.5)


class EdgeLabelAndCalloutTest(unittest.TestCase):
    def test_edge_labels_feedback_loops_and_callout_styles(self):
        d = Drawing(800, 300)
        a = d.box_at((100, 120), "A", font_size=16, stroke="#333")
        b = d.box_at((400, 120), "B", font_size=16, stroke="#333")
        d.arrow(a, b, key="ab", label="激活")
        tag = d.nodes["ab-label"]
        self.assertEqual(d.check(), [])
        b.move_to(400, 60)  # diagonal now: label moves out of the line's box too
        box = tag.bounds
        self.assertTrue(80 < box.x + box.width / 2 < 420, box)
        self.assertEqual(d.check(), [])
        d.arrow(a, b, key="ba", label="抑制", label_side="below", head="inhibit")
        with self.assertRaises(ValueError):
            d.arrow(a, b, key="bad", label="x", label_side="inside")
        d = Drawing(800, 300)
        nodes = [d.box_at((100 + 300 * i, 120), n, font_size=16, stroke="#333") for i, n in enumerate("ABC")]
        tall = d.box_at((250, 200), "tall\nnode\nhere", font_size=16, stroke="#333")
        d.arrow(nodes[0], nodes[1])
        d.arrow(nodes[1], nodes[2])
        loop = d.arrow(nodes[2], nodes[0], route="loop", side="bottom", dashed=True, label="负反馈", key="fb")
        import re

        path = re.search(r'<path d="([^"]*)"[^>]*id="fb"', d.to_svg()).group(1)
        ys = [float(v) for v in re.findall(r"L [\d.]+ ([\d.]+)", path)]
        self.assertGreater(min(ys[:2]), tall.bounds.y + tall.bounds.height)  # lane clears the deepest node
        self.assertEqual(len(ys), 3)
        self.assertGreater(d.nodes["fb-label"].bounds.y, ys[0])  # label outside the loop
        self.assertEqual(d.check(), [])
        self.assertEqual(loop.route, "loop")
        d = Drawing(400, 300)
        t = d.rect_at((200, 150), 80, 60, fill="#EEE", stroke="#333")
        d.callout(
            "n",
            "注释",
            t,
            at=(20, 20),
            font_size=12,
            fill="#C0392B",
            bold=True,
            line_color="#2A6F4E",
            line_width=1.5,
            dashed=True,
        )
        svg = d.to_svg()
        self.assertIn('fill="#C0392B" font-weight="bold"', svg)
        self.assertRegex(svg, r'stroke="#2A6F4E" stroke-width="1.5" stroke-dasharray="4 3" id="n-leader"')
        with self.assertRaises(TypeError) as err:
            d.callout("m", "x", t, at=(20, 250), font_size=12, colour="#000")
        self.assertIn("line_color", str(err.exception))


# ====================================================================================================
# Geometric contracts for layout helpers: placements, rings, pairing and ports.
# ====================================================================================================


def overlaps(a, b):
    return a.x < b.x + b.width and b.x < a.x + a.width and a.y < b.y + b.height and b.y < a.y + a.height


class RowColumnGridTest(unittest.TestCase):
    def test_row_column_and_grid_layouts(self):
        p = row({"a": (40, 20), "b": (60, 40), "c": (30, 10)}, gap=10, origin=(5, 7), align="center")
        a, b, c = p.boxes["a"], p.boxes["b"], p.boxes["c"]
        self.assertEqual((a.x, b.x, c.x), (5, 55, 125))
        self.assertEqual([round(box.y + box.height / 2, 9) for box in (a, b, c)], [27, 27, 27])
        self.assertEqual(p.bounds, Box(5, 7, 150, 40))
        p = column([(20, 10), (20, 30)], gap=0, slot=40, align="left")
        self.assertEqual(p.boxes[0].y, 15)
        self.assertEqual(p.boxes[1].y, 45)
        with self.assertRaises(ValueError):
            column([(20, 50)], slot=40)
        p = grid([(10, 10), (30, 10), (10, 20), (10, 10)], columns=2, col_gap=5, row_gap=5, align="left", valign="top")
        self.assertEqual(p.boxes[1].x, 15)
        self.assertEqual(p.boxes[3].x, 15)
        self.assertEqual(p.boxes[2].y, 15)
        for i, a in p.boxes.items():
            for j, b in p.boxes.items():
                if i < j:
                    self.assertFalse(overlaps(a, b))
        for call in (
            lambda: row([]),
            lambda: row([(1, 1)], gap=-1),
            lambda: grid([(1, 1)], columns=0),
            lambda: row([(1, 1)], align="diagonal"),
        ):
            with self.assertRaises((ValueError, TypeError)):
                call()


class AlignDistributeTest(unittest.TestCase):
    def nodes(self, positions):
        d = Drawing(500, 300)
        return d, [
            d.add(f"n{i}", rect(w, h), at=(x, y), own_anchor="top_left") for i, (x, y, w, h) in enumerate(positions)
        ]

    def test_align_and_distribute(self):
        _, ns = self.nodes([(0, 10, 20, 20), (50, 40, 20, 60), (90, 5, 20, 10)])
        align(*ns, edge="top")
        self.assertEqual({n.bounds.y for n in ns}, {10})
        align(*ns, edge="center_x", to=200)
        self.assertEqual({n.bounds.x + n.bounds.width / 2 for n in ns}, {200})
        _, ns = self.nodes([(0, 0, 20, 10), (30, 0, 40, 10), (75, 0, 10, 10), (200, 0, 20, 10)])
        distribute(*ns, axis="x")
        boxes = [n.bounds for n in ns]
        gaps = [b.x - (a.x + a.width) for a, b in zip(boxes, boxes[1:])]
        self.assertAlmostEqual(max(gaps) - min(gaps), 0, places=9)
        self.assertEqual((boxes[0].x, boxes[-1].x), (0, 200))


class RingTest(unittest.TestCase):
    def test_ring_centres_arcs_open_ring_and_overlap(self):
        sizes = {f"s{i}": (30, 30) for i in range(7)}
        lay = ring(sizes, center=(200, 200), radius=150, gap=6)
        for x, y in lay.centers.values():
            self.assertAlmostEqual(math.hypot(x - 200, y - 200), 150, places=9)
        self.assertEqual(len(lay.arcs), 7)
        self.assertAlmostEqual(lay.centers["s0"][1], 50)
        reach = math.hypot(30, 30) / 2
        for d in lay.arcs:
            nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?(?:e-?\d+)?", d)]
            for x, y in ((nums[0], nums[1]), (nums[-2], nums[-1])):
                self.assertAlmostEqual(math.hypot(x - 200, y - 200), 150, places=6)
                nearest = min(math.dist((x, y), c) for c in lay.centers.values())
                self.assertGreaterEqual(nearest, reach + 6 - 1e-6)
        self.assertEqual(len(ring([(10, 10)] * 4, center=(0, 0), radius=50, closed=False).arcs), 3)
        with self.assertRaisesRegex(ValueError, "overlap"):
            ring([(80, 80)] * 8, center=(0, 0), radius=60)

    def test_ring_arcs_atomize_as_native_curves(self):
        from ..svg_drawing import path

        d = Drawing(400, 400)
        d.add_defs(
            '<marker id="m" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10Z" fill="#333333"/></marker>'
        )
        lay = ring([(20, 20)] * 5, center=(200, 200), radius=120)
        for i, arc in enumerate(lay.arcs):
            d.add(f"a{i}", path(arc, fill="none", stroke="#333333", stroke_width=2, marker_end="url(#m)"))
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "ring.svg"
            source.write_text(d.to_svg(), encoding="utf-8")
            set_mapping(400, 400, 0, 0, 400, 400)
            xml = atomize_svg_to_slide(source)
        self.assertNotIn("<embed", xml)
        self.assertEqual(xml.count('<shape type="custom"'), 10)


class BipartiteTest(unittest.TestCase):
    def test_bipartite_order_removes_crossings_and_keeps_fixed_side(self):
        left = ["a", "b", "c", "d"]
        right = ["w", "x", "y", "z"]
        edges = [("a", "z"), ("b", "y"), ("c", "x"), ("d", "w")]
        lo, ro = bipartite_order(left, right, edges)
        lpos = {k: i for i, k in enumerate(lo)}
        rpos = {k: i for i, k in enumerate(ro)}
        pairs = [(lpos[a], rpos[b]) for a, b in edges]
        crossings = sum(1 for i, (p, q) in enumerate(pairs) for r, s in pairs[i + 1 :] if (p - r) * (q - s) < 0)
        self.assertEqual(crossings, 0)
        lo, _ = bipartite_order(["a", "b"], ["x", "y"], [("a", "y"), ("b", "x")], fixed="left")
        self.assertEqual(lo, ("a", "b"))
        with self.assertRaises(ValueError):
            bipartite_order(["a"], ["x"], [("a", "q")])


class SpreadPortsTest(unittest.TestCase):
    def build(self, ys):
        d = Drawing(500, 700)
        hub = d.add("hub", rect(80, 120), at=(40, 340), own_anchor="top_left")
        targets = {f"t{i}": d.add(f"t{i}", rect(70, 24), at=(300, y), own_anchor="top_left") for i, y in enumerate(ys)}
        anchors = {k: n.anchor("left") for k, n in targets.items()}
        return d, hub, anchors, spread_ports(hub, "right", anchors)

    def segments(self, d, spread, anchors):
        out = {}
        for k, a in anchors.items():
            pts = [d.resolve(spread.ports[k])] + spread.waypoints(k, a) + [d.resolve(a)]
            out[k] = list(zip(pts, pts[1:]))
        return out

    def test_spread_ports_order_follow_and_non_crossing_routes(self):
        d, hub, anchors, spread = self.build([300, 330, 420, 470, 520])
        ys = [d.resolve(spread.ports[f"t{i}"])[1] for i in range(5)]
        self.assertEqual(ys, sorted(ys))
        self.assertEqual(len(set(ys)), 5)
        self.assertTrue(all(d.resolve(p)[0] == 120 for p in spread.ports.values()))
        d, hub, anchors, spread = self.build([300, 400])
        before = d.resolve(spread.ports["t0"])
        hub.move_to(10, 0, own_anchor="top_left")
        after = d.resolve(spread.ports["t0"])
        self.assertEqual((before[0] - after[0], before[1] - after[1]), (30, 340))
        for ys in ([330 + i * 34 for i in range(5)], [300, 330, 420, 470, 520], [600, 610, 620]):
            d, _, anchors, spread = self.build(ys)
            segs = self.segments(d, spread, anchors)
            verticals = [(k, s) for k, ss in segs.items() for s in ss if abs(s[0][0] - s[1][0]) < 1e-9]
            xs = [s[0][0] for _, s in verticals]
            self.assertEqual(len(xs), len(set(round(x, 6) for x in xs)), ys)

            def cross(p, q):
                (a, b), (c, e) = p, q

                def orient(u, v, w):
                    return (v[0] - u[0]) * (w[1] - u[1]) - (v[1] - u[1]) * (w[0] - u[0])

                return orient(a, b, c) * orient(a, b, e) < 0 and orient(c, e, a) * orient(c, e, b) < 0

            keys = list(segs)
            for i, k in enumerate(keys):
                for m in keys[i + 1 :]:
                    self.assertFalse(any(cross(p, q) for p in segs[k] for q in segs[m]), (ys, k, m))


class LayoutHelpTest(unittest.TestCase):
    def test_layout_topic_and_aliases(self):
        self.assertIn("【主题 layout｜", drawing_help("layout"))
        self.assertEqual(drawing_help("环形"), drawing_help("ring"))
        self.assertEqual(drawing_help("减少交叉"), drawing_help("bipartite_order"))
        self.assertEqual(drawing_help("端口分配"), drawing_help("spread_ports"))
        self.assertEqual(drawing_help("自动标签"), drawing_help("Drawing.place_label"))
        self.assertEqual(drawing_help("连线标签"), drawing_help("Drawing.label_connector"))
        self.assertEqual(drawing_help("节点框"), drawing_help("text_box"))
        self.assertIn("- layout：", drawing_help())


class CheckAndReviewHintsTest(unittest.TestCase):
    def test_check_and_review_hints(self):
        d = Drawing(700, 400)
        mac = d.place(cell(150, 110, kind="macrophage"), at=(250, 200), key="mac")
        d.place(cell(70, kind="neutrophil"), at=(400, 200), key="neu")
        d.place(nucleus(30), at=(230, 200), key="nuc")  # fully inside: containment
        d.mount(receptor(), on=mac.contour_at(0.3, normal="outward"), key="r")
        found = [p["keys"] for p in d.check() if p["kind"] == "parts_overlap"]
        self.assertEqual(found, [["mac", "neu"]])
        d = Drawing(400, 300)
        d.rect_at((0, 0), 120, 80, fill="#EEE", key="r")
        hint = next(p["hint"] for p in d.check() if p["kind"] == "off_canvas")
        self.assertIn("at=(60, 40)", hint)
        self.assertIn("insert=", hint)
        self.assertEqual(suggest_parts("不存在的东西"), [])
        self.assertIn("layer_stack", suggest_parts("燃料电池 MEA"))

        for text in ("土壤团聚体", "能带弯曲", "encoder 编码器", "细菌"):  # unregistered parts are skipped
            for name in suggest_parts(text):
                self.assertIn(name.split("(")[0], _DRAWING_APIS)
        d = Drawing(700, 400)
        d.svg_at(
            (300, 200),
            '<ellipse rx="160" ry="110" fill="#F3EEF8" stroke="#7A6AA8"/>'
            '<ellipse cx="-60" rx="40" ry="30" fill="#E6D9F0"/>'
            '<text x="134" y="-55" font-size="14" text-anchor="middle">胞质</text>',
            key="host",
        )
        m = d.place(mitochondrion(24), at=(340, 200), key="mito")
        d.callout("n1", "线粒体", m.anchor("center"), at=(560, 60), font_size=14, route="straight")
        self.assertEqual(d.check(), [])
        d.text_at((480, 124), "外部", font_size=14, key="other")  # an unrelated label is still protected
        self.assertIn(["n1-leader", "other"], [p["keys"] for p in d.check()])
        d = Drawing(800, 400)
        for i in range(4):
            d.rect_at((100 + i * 8, 150 + i * 8), 60, 90, fill="#F2B880", stroke="#333", key=f"fm{i}")
        bug = d.box_at((400, 100), "细菌", font_size=16, stroke="#333")
        mac = d.box_at((600, 100), "巨噬细胞", font_size=16, stroke="#333")
        d.arrow(bug, mac)
        d.arrow(mac, bug, route="loop", side="top")
        notes = {n["kind"]: n for n in d.review()}
        self.assertIn("fm0", notes["fake_3d_stack"]["keys"])
        self.assertIn("tensor_block", notes["fake_3d_stack"]["hint"])
        parts = [n["parts"] for n in d.review() if n["kind"] == "plain_subject"]
        self.assertIn(['cell(kind="bacterium")', "biofilm_section"], parts)
        self.assertIn(['cell(kind="macrophage")'], parts)


# ====================================================================================================
# Independent geometry contracts for tree_layout; no renderer is required.
# ====================================================================================================

DIRECTIONS = ("down", "up", "right", "left")


EPSILON = 1e-8


def cross_interval(box, direction):
    if direction in ("down", "up"):
        return box.x, box.x + box.width
    return box.y, box.y + box.height


def forward_interval(box, direction):
    """Coordinates increase in the requested direction, preserving dimensions."""
    if direction == "down":
        return box.y, box.y + box.height
    if direction == "up":
        return -(box.y + box.height), -box.y
    if direction == "right":
        return box.x, box.x + box.width
    return -(box.x + box.width), -box.x


def declared_nodes_and_depths(root, children):
    """Only graph bookkeeping: no placement, span, or box calculation."""
    depths = {root: 0}
    queue = deque([root])
    while queue:
        parent = queue.popleft()
        for child in children.get(parent, ()):
            depths[child] = depths[parent] + 1
            queue.append(child)
    return depths


def subtree_nodes(root, children):
    pending = [root]
    while pending:
        node = pending.pop()
        yield node
        pending.extend(children.get(node, ()))


def input_dimensions(value):
    if isinstance(value, Box):
        return value.width, value.height
    return value


class TreeLayoutGeometryTest(unittest.TestCase):
    def assert_metadata(self, result, root, children, sizes, direction):
        self.assertIsInstance(result, TreeLayout)
        self.assertTrue(is_dataclass(result))
        self.assertEqual(result.direction, direction)
        expected_depths = declared_nodes_and_depths(root, children)
        self.assertEqual(dict(result.depths), expected_depths)
        self.assertEqual(set(result.boxes), set(expected_depths))
        expected_edges = {(parent, child) for parent in expected_depths for child in children.get(parent, ())}
        # Edge traversal order is intentionally not prescribed by this test.
        actual_edges = [tuple(edge) for edge in result.edges]
        self.assertEqual(len(actual_edges), len(expected_edges))
        self.assertEqual(set(actual_edges), expected_edges)
        for node, box in result.boxes.items():
            self.assertIsInstance(box, Box)
            width, height = input_dimensions(sizes[node])
            self.assertAlmostEqual(box.width, width)
            self.assertAlmostEqual(box.height, height)
            self.assertTrue(all(math.isfinite(v) for v in (box.x, box.y, box.width, box.height)))

    def assert_bounds(self, result, origin):
        boxes = list(result.boxes.values())
        left = min(box.x for box in boxes)
        top = min(box.y for box in boxes)
        right = max(box.x + box.width for box in boxes)
        bottom = max(box.y + box.height for box in boxes)
        self.assertIsInstance(result.bounds, Box)
        self.assertAlmostEqual(left, origin[0])
        self.assertAlmostEqual(top, origin[1])
        self.assertAlmostEqual(result.bounds.x, left)
        self.assertAlmostEqual(result.bounds.y, top)
        self.assertAlmostEqual(result.bounds.width, right - left)
        self.assertAlmostEqual(result.bounds.height, bottom - top)

    def assert_layer_clearance(self, result, level_gap):
        layers = {}
        for node, depth in result.depths.items():
            layers.setdefault(depth, []).append(forward_interval(result.boxes[node], result.direction))
        for depth, intervals in layers.items():
            # Nodes share the near boundary of their depth band, even when
            # their physical dimensions differ or the direction is reversed.
            starts = [start for start, _ in intervals]
            self.assertAlmostEqual(min(starts), max(starts))
            if depth + 1 in layers:
                far_edge = max(end for _, end in intervals)
                next_start = min(start for start, _ in layers[depth + 1])
                self.assertAlmostEqual(next_start - far_edge, level_gap)

    def assert_sibling_subtrees_separated(self, result, children, sibling_gap):
        for parent in result.boxes:
            siblings = children.get(parent, ())
            for first, second in zip(siblings, siblings[1:]):
                first_far = max(
                    cross_interval(result.boxes[node], result.direction)[1] for node in subtree_nodes(first, children)
                )
                second_near = min(
                    cross_interval(result.boxes[node], result.direction)[0] for node in subtree_nodes(second, children)
                )
                self.assertGreaterEqual(
                    second_near - first_far + EPSILON, sibling_gap, (parent, first, second, first_far, second_near)
                )

    def assert_non_overlapping_boxes(self, result):
        nodes = list(result.boxes)
        for index, first in enumerate(nodes):
            a = result.boxes[first]
            for second in nodes[index + 1 :]:
                b = result.boxes[second]
                overlap_x = min(a.x + a.width, b.x + b.width) - max(a.x, b.x)
                overlap_y = min(a.y + a.height, b.y + b.height) - max(a.y, b.y)
                self.assertFalse(overlap_x > EPSILON and overlap_y > EPSILON, (first, second, a, b))

    def test_r5_gap_survives_crossing_two_internal_subtrees(self):
        children = {"P6": ("P0", "P5"), "P0": ("P1", "P7", "P2"), "P5": ("P4", "P3", "P8")}
        sizes = {"P6": (100, 60), "P0": (157, 60), "P5": (157, 60)}
        sizes.update({node: (106, 100) for node in ("P1", "P7", "P2", "P4", "P3", "P8")})
        for direction in DIRECTIONS:
            with self.subTest(direction=direction):
                result = tree_layout(
                    "P6", children, sizes, origin=(13, -7), sibling_gap=16, level_gap=46, direction=direction
                )
                self.assert_metadata(result, "P6", children, sizes, direction)
                self.assertEqual(list(result.leaf_order), ["P1", "P7", "P2", "P4", "P3", "P8"])
                self.assert_sibling_subtrees_separated(result, children, 16)
                p2_far = cross_interval(result.boxes["P2"], direction)[1]
                p4_near = cross_interval(result.boxes["P4"], direction)[0]
                self.assertGreaterEqual(p4_near - p2_far + EPSILON, 16)
                # The old renderer reserved 2 units at each connector end.
                # Adequate real separation must leave a forward segment.
                self.assertGreater((p4_near - 2) - (p2_far + 2), 0)
                self.assert_layer_clearance(result, 46)
                self.assert_bounds(result, (13, -7))

    def test_varying_sizes_and_unbalanced_branches_obey_global_depth_bands(self):
        children = {"root": ["a", "b", "c"], "a": ["a1", "a2"], "b": ["b1"], "b1": ["b11", "b12"], "a1": []}
        sizes = {
            "root": (130, 20),
            "a": (40, 60),
            "b": (90, 7),
            "c": (75, 25),
            "a1": (15, 10),
            "a2": (44, 70),
            "b1": (17, 12),
            "b11": (45, 2),
            "b12": (14, 85),
        }
        for direction in DIRECTIONS:
            with self.subTest(direction=direction):
                result = tree_layout(
                    "root", children, sizes, origin=(-23.5, 81.25), sibling_gap=9.5, level_gap=6.25, direction=direction
                )
                self.assert_metadata(result, "root", children, sizes, direction)
                self.assertEqual(list(result.leaf_order), ["a1", "a2", "b11", "b12", "c"])
                self.assert_sibling_subtrees_separated(result, children, 9.5)
                self.assert_layer_clearance(result, 6.25)
                self.assert_non_overlapping_boxes(result)
                self.assert_bounds(result, (-23.5, 81.25))

    def test_single_node_deep_chain_and_hashable_ids(self):
        for direction in DIRECTIONS:
            with self.subTest(direction=direction):
                result = tree_layout(
                    "only", {}, {"only": (31, 17)}, origin=(5, 9), sibling_gap=1000, level_gap=2000, direction=direction
                )
                self.assert_metadata(result, "only", {}, {"only": (31, 17)}, direction)
                self.assertEqual(result.bounds, Box(5, 9, 31, 17))
                self.assertEqual(result.boxes["only"], result.bounds)
                self.assertEqual(list(result.leaf_order), ["only"])
                self.assertEqual(list(result.edges), [])
        count = 1501
        children = {node: [node + 1] for node in range(count - 1)}
        sizes = {node: (3, 5) for node in range(count)}
        result = tree_layout(0, children, sizes, origin=(7, 11), sibling_gap=24, level_gap=2, direction="down")
        self.assertEqual(len(result.boxes), count)
        self.assertEqual(len(result.edges), count - 1)
        self.assertEqual(result.depths[count - 1], count - 1)
        self.assertEqual(list(result.leaf_order), [count - 1])
        self.assertEqual(result.bounds, Box(7, 11, 3, count * 5 + (count - 1) * 2))
        for node in range(count - 1):
            first, second = result.boxes[node], result.boxes[node + 1]
            self.assertAlmostEqual(second.y - (first.y + first.height), 2)

    def test_tree_layout_geometry_bounds_reflection_and_ids(self):
        cases = [
            ({"r": (10, 11), "a": (20, 5), "b": (30, 17)}, (57, 41), (53, 29)),
            ({"r": (400, 300), "a": (20, 10), "b": (30, 17)}, (400, 330), (443, 300)),
        ]
        for sizes, vertical, horizontal in cases:
            for direction in DIRECTIONS:
                with self.subTest(sizes=sizes, direction=direction):
                    result = tree_layout(
                        "r", {"r": ["a", "b"]}, sizes, sibling_gap=7, level_gap=13, direction=direction
                    )
                    expected = vertical if direction in ("down", "up") else horizontal
                    self.assertAlmostEqual(result.bounds.width, expected[0])
                    self.assertAlmostEqual(result.bounds.height, expected[1])
                    self.assert_bounds(result, (0, 0))
                    self.assert_non_overlapping_boxes(result)
        children = {"r": ["a", "b"], "a": ["c"]}
        sizes = {"r": (35, 13), "a": (18, 42), "b": (29, 7), "c": (11, 23)}
        origin = (-5, 18)
        for forward, reverse in (("down", "up"), ("right", "left")):
            with self.subTest(pair=(forward, reverse)):
                first = tree_layout("r", children, sizes, origin=origin, direction=forward)
                second = tree_layout("r", children, sizes, origin=origin, direction=reverse)
                self.assertEqual(first.bounds, second.bounds)
                self.assertEqual(list(first.leaf_order), list(second.leaf_order))
                for node in sizes:
                    a, b = first.boxes[node], second.boxes[node]
                    self.assertEqual((a.width, a.height), (b.width, b.height))
                    if forward == "down":
                        self.assertAlmostEqual(a.x, b.x)
                        self.assertAlmostEqual(a.y + b.y + a.height, 2 * origin[1] + first.bounds.height)
                    else:
                        self.assertAlmostEqual(a.y, b.y)
                        self.assertAlmostEqual(a.x + b.x + a.width, 2 * origin[0] + first.bounds.width)
        root, first, last, deep = None, 17, ("last", 2), frozenset({"deep"})
        children = {root: (last, first), last: [deep]}
        sizes = {root: (20, 11), first: (13, 7), last: (19, 17), deep: (9, 5)}
        for direction in DIRECTIONS:
            with self.subTest(direction=direction):
                result = tree_layout(root, children, sizes, direction=direction)
                self.assert_metadata(result, root, children, sizes, direction)
                self.assertEqual(list(result.leaf_order), [deep, first])
                self.assert_sibling_subtrees_separated(result, children, 24)
        children = {"r": ["a", "b"], "a": ()}
        sizes = {
            "r": Box(999, -800, 40, 16),
            "a": (17, 30),
            "b": Box(-500, 600, 12, 9),
            # Unreachable size entries are ignored, including invalid values.
            "unused": (float("nan"), -4),
        }
        before_children, before_sizes = deepcopy(children), dict(sizes)
        result = tree_layout("r", children, sizes, origin=(30, -90), direction="left")
        ordinary = tree_layout(
            "r", children, {"r": (40, 16), "a": (17, 30), "b": (12, 9)}, origin=(30, -90), direction="left"
        )
        self.assertEqual(dict(result.boxes), dict(ordinary.boxes))
        self.assertEqual(result.bounds, ordinary.bounds)
        self.assertEqual(children, before_children)
        self.assertEqual(sizes.keys(), before_sizes.keys())
        for node in before_sizes:
            self.assertIs(sizes[node], before_sizes[node])
        self.assertNotIn("unused", result.boxes)

    def test_boxes_attach_measured_geometry_via_existing_top_left_anchor(self):
        from ..svg_drawing import Drawing, rect

        parts = {
            "r": rect(60, 20, x=-30, y=2, stroke="black", stroke_width=2),
            "a": rect(24, 34, x=11, y=-9),
            "b": rect(41, 17, x=-4, y=5),
        }
        for direction in DIRECTIONS:
            with self.subTest(direction=direction):
                result = tree_layout(
                    "r",
                    {"r": ["a", "b"]},
                    {key: part.bounds for key, part in parts.items()},
                    origin=(10, 15),
                    direction=direction,
                )
                drawing = Drawing(500, 500)
                for key, box in result.boxes.items():
                    node = drawing.add(key, parts[key], at=box.anchor("top_left"), own_anchor="top_left")
                    for attr in ("x", "y", "width", "height"):
                        self.assertAlmostEqual(getattr(node.bounds, attr), getattr(box, attr))


class TreeLayoutValidationTest(unittest.TestCase):
    def assert_rejected(self, root, children, sizes, **kwargs):
        # Validation errors may distinguish malformed types from invalid values.
        with self.assertRaises((TypeError, ValueError)):
            tree_layout(root, children, sizes, **kwargs)

    def test_tree_layout_validation(self):
        ten = (10, 10)
        cases = [
            ({"r": ["r"]}, {"r": ten}),  # self cycle
            ({"r": ["a"], "a": ["b"], "b": ["r"]}, {n: ten for n in "rab"}),  # longer cycle
            ({"r": ["a", "a"]}, {"r": ten, "a": ten}),  # duplicate child
            ({"r": ["a", "b"], "a": ["c"], "b": ["c"]}, {n: ten for n in "rabc"}),  # two parents
            ({}, {}),  # missing root size
            ({"r": ["a"]}, {"r": ten}),  # missing child size
            ({"r": [], "unused": []}, {"r": ten, "unused": ten}),  # disconnected, even when empty
            ({"r": [], "unused": ["orphan"]}, {n: ten for n in ("r", "unused", "orphan")}),
            ({"r": [["not-hashable"]]}, {"r": ten}),
            ({}, {"r": Box(0, 0, 0, 10)}),
        ]
        cases += [({"r": v}, {"r": ten, "a": ten}) for v in ("a", b"a", {"a"}, frozenset({"a"}), {"a": 1}, iter(["a"]))]
        for value in (0, -1, float("inf"), float("-inf"), float("nan")):
            cases += [({}, {"r": (value, 10)}), ({}, {"r": (10, value)})]
        cases += [({}, {"r": size}) for size in ((), (10,), (10, 20, 30), (None, 10), {10, 20}, {10: 20, 30: 40})]
        cases.append(({}, {"r": iter([10, 20])}))
        for children, sizes in cases:
            with self.subTest(children=children, sizes=sizes):
                self.assert_rejected("r", children, sizes)
        self.assert_rejected("r", {"r": ["a", "b"]}, {node: (1e308, 10) for node in ("r", "a", "b")})
        result = tree_layout("r", {"r": ["a"]}, {"r": (5, 5), "a": (7, 5)}, sibling_gap=1e308)
        self.assertEqual(result.bounds.width, 7)
        for direction in ("diagonal", "", None):
            with self.subTest(direction=direction):
                self.assert_rejected("r", {}, {"r": (10, 10)}, direction=direction)


class TreeLayoutPrecisionTest(unittest.TestCase):
    def assert_precision_rejected(self, children, sizes, **options):
        with self.assertRaisesRegex(ValueError, "Translate or rescale"):
            tree_layout("r", children, sizes, **options)

    def test_tree_layout_precision(self):
        for direction in DIRECTIONS:
            vertical = direction in ("down", "up")
            wide, tall = ((1e20, 10), (10, 1e20)) if vertical else ((10, 1e20), (1e20, 10))
            for children, sizes, options in (
                ({"r": ["a", "b"]}, {n: (10, 10) for n in "rab"}, {"origin": (1e20, 1e20)}),  # large origin
                ({"r": ["a", "b"]}, {"r": wide, "a": (10, 10), "b": (10, 10)}, {}),  # huge parent span
                ({"r": ["a", "b"]}, {n: wide for n in "rab"}, {"sibling_gap": 24}),  # sibling gap lost
                ({"r": ["a"]}, {"r": tall, "a": tall}, {"level_gap": 24}),  # level gap lost
            ):
                with self.subTest(direction=direction, options=options, sizes=sizes):
                    self.assert_precision_rejected(children, sizes, direction=direction, **options)
        for direction in DIRECTIONS:
            with self.subTest(direction=direction):
                size = (1e20, 10) if direction in ("down", "up") else (10, 1e20)
                result = tree_layout(
                    "r",
                    {"r": ["a", "b"]},
                    {node: size for node in ("r", "a", "b")},
                    sibling_gap=0,
                    level_gap=0,
                    direction=direction,
                )
                first = cross_interval(result.boxes["a"], direction)
                second = cross_interval(result.boxes["b"], direction)
                self.assertEqual(first[1], second[0])
        for direction in DIRECTIONS:
            for gap in (0, 1e-200):
                with self.subTest(direction=direction, gap=gap):
                    result = tree_layout(
                        "r",
                        {"r": ["a", "b"]},
                        {node: (1e-200, 1e-200) for node in ("r", "a", "b")},
                        sibling_gap=gap,
                        level_gap=gap,
                        direction=direction,
                    )
                    first = cross_interval(result.boxes["a"], direction)
                    second = cross_interval(result.boxes["b"], direction)
                    self.assertTrue(math.isclose(second[0] - first[1], gap, rel_tol=1e-7))
                    self.assertGreater(result.bounds.width, 0)
                    self.assertGreater(result.bounds.height, 0)
        children = {"r": ["a", "b"], "a": ["c", "d"]}
        sizes = {"r": (101.3, 27.9), "a": (13.7, 42.1), "b": (29.3, 17.1), "c": (9.1, 31.7), "d": (17.3, 23.9)}
        for direction in DIRECTIONS:
            for origin in ((0, 0), (1000.3, -2100.7), (1e6 + 0.3, -1e6 - 0.7)):
                with self.subTest(direction=direction, origin=origin):
                    result = tree_layout(
                        "r", children, sizes, origin=origin, sibling_gap=0, level_gap=0, direction=direction
                    )
                    self.assertEqual(list(result.leaf_order), ["c", "d", "b"])
                    self.assertEqual((result.bounds.x, result.bounds.y), origin)
                    self.assertEqual(len(result.boxes), 5)


class TreeLayoutHelpTest(unittest.TestCase):
    def test_public_api_help_describes_the_callable_and_chinese_task_name_resolves(self):
        text = drawing_help("tree_layout")
        self.assertNotIn("未找到公开能力", text)
        for word in ("tree_layout(", "TreeLayout", "children", "sizes", "sibling_gap", "level_gap", "direction"):
            self.assertIn(word, text)
        text = drawing_help("树布局")
        self.assertNotIn("未找到公开能力", text)
        self.assertIn("tree_layout", text)


# ====================================================================================================
# The academic schematic templates referenced in the docs must keep running cleanly.
# ====================================================================================================


class DrawingExamplesTest(unittest.TestCase):
    def test_templates_pass_self_check_and_convert(self):
        for module in (compare_panels, overview_zoom, membrane_transport, band_alignment):
            with self.subTest(module=module.__name__):
                d = module.build()
                self.assertEqual(d.check(), [])
                self.assertIn("<shape", d.to_slide(x=40, y=96, width=880))
