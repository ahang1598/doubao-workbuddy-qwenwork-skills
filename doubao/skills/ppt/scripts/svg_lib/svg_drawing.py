"""Public entry point for composable SVG drawing and on-demand help."""

from .drawing_lib._geometry import (
    Point,
    Box,
    Geometry,
    Curve,
    PathFrame,
    rect,
    ellipse,
    polygon,
    group,
    path,
    label,
)
from .drawing_lib._curves import smooth_curve
from .drawing_lib._construction import (
    circular_arc,
    annular_sector,
    circle_tangent_points,
    repeat_along_path,
    ribbon,
    extrude,
    cutaway,
    zoom,
)
from .drawing_lib._plotting import CoordinateMap, FunctionSample, sample_function, sample_parametric
from .drawing_lib._scene import Anchor, Edge, ContourAnchor, Node, Connector, Drawing, svg_geometry  # noqa: F401  (facade attribute)
from .drawing_lib._inspection import inspect_svg
from .drawing_lib._text import wrap_label
from .drawing_lib._labels import text_box
from .drawing_lib._markers import marker
from .drawing_lib._bio_parts import (
    cell,
    receptor,
    membrane,
    nucleus,
    mitochondrion,
    vessel,
    dna,
    cytokine,
    antibody,
    virus,
    duplex,
    nucleic_strand,
    protein_complex,
    transporter,
)
from .drawing_lib._matter_parts import atom, lattice, particle, porous_framework, microplastic, porous_electrode
from .drawing_lib._device_parts import layer_stack, interface_section, battery_cell, molecule
from .drawing_lib._synapse_parts import cell_interface
from .drawing_lib._envelope_parts import cell_envelope, biofilm_section
from .drawing_lib._membrane_parts import membrane_complex, transport_chain, atp_synthase, ion_marker
from .drawing_lib._energy_parts import energy_diagram
from .drawing_lib._defect_parts import close_packed, twin_lattice, edge_dislocation, polycrystal, dislocation_symbol
from .drawing_lib._tech_parts import (
    nn_layer,
    dense_links,
    block,
    wave,
    legend_row,
    tensor_block,
    transformer_block,
    encoder_decoder,
    patch_embed,
    lens,
    laser_beam,
    circuit_symbol,
    spring,
    magnet,
    device,
    image_grid,
    vector_packet,
)
from .drawing_lib._em_parts import coil, field_marks, rails_rod, circuit_loop
from .drawing_lib._earth_parts import (
    globe,
    globe_point,
    jet_stream,
    atmosphere_section,
    coral_polyp,
    symbiont,
    water_column_section,
    water_point,
    soil_aggregate,
    organism,
    star,
    planet,
    transit_geometry,
)
from .drawing_lib._organ_parts import brain, neuron, intestinal_wall, heart, nephron, bbb_unit, root_section
from .drawing_lib._pathway_parts import signaling_cascade, badge
from .drawing_lib._liver_parts import liver_sinusoid
from .drawing_lib._paradigm_parts import trial_sequence
from .drawing_lib._finish import bilayer, sphere_shading, soft_shading, circle_union, shade  # noqa: F401  (documented public helpers)
from .drawing_lib._tree_layout import TreeLayout, tree_layout
from .drawing_lib._layout import (
    Placement,
    PortSpread,
    RingLayout,
    row,
    column,
    grid,
    align,
    distribute,
    ring,
    bipartite_order,
    spread_ports,
)
from .drawing_lib._help import drawing_help

# Retain existing diagnostic hooks; these are not public authoring APIs.
from .drawing_lib._help import _DRAWING_APIS, _HELP_TOPICS, _HELP_TASKS  # noqa: F401

__all__ = [
    "Point",
    "Box",
    "Geometry",
    "Curve",
    "PathFrame",
    "smooth_curve",
    "rect",
    "ellipse",
    "polygon",
    "group",
    "path",
    "label",
    "circular_arc",
    "annular_sector",
    "circle_tangent_points",
    "repeat_along_path",
    "ribbon",
    "extrude",
    "cutaway",
    "zoom",
    "CoordinateMap",
    "FunctionSample",
    "sample_function",
    "sample_parametric",
    "Anchor",
    "Edge",
    "ContourAnchor",
    "Node",
    "Connector",
    "Drawing",
    "drawing_help",
    "inspect_svg",
    "wrap_label",
    "text_box",
    "marker",
    "TreeLayout",
    "tree_layout",
    "cell",
    "receptor",
    "membrane",
    "nucleus",
    "mitochondrion",
    "vessel",
    "dna",
    "cytokine",
    "antibody",
    "virus",
    "atom",
    "lattice",
    "layer_stack",
    "interface_section",
    "battery_cell",
    "molecule",
    "particle",
    "nn_layer",
    "dense_links",
    "block",
    "wave",
    "legend_row",
    "porous_framework",
    "microplastic",
    "porous_electrode",
    "star",
    "planet",
    "transit_geometry",
    "device",
    "image_grid",
    "vector_packet",
    "water_column_section",
    "water_point",
    "organism",
    "duplex",
    "nucleic_strand",
    "protein_complex",
    "transporter",
    "cell_interface",
    "cell_envelope",
    "biofilm_section",
    "energy_diagram",
    "membrane_complex",
    "transport_chain",
    "atp_synthase",
    "ion_marker",
    "close_packed",
    "twin_lattice",
    "edge_dislocation",
    "polycrystal",
    "dislocation_symbol",
    "tensor_block",
    "transformer_block",
    "encoder_decoder",
    "patch_embed",
    "soil_aggregate",
    "lens",
    "laser_beam",
    "circuit_symbol",
    "spring",
    "magnet",
    "coil",
    "field_marks",
    "rails_rod",
    "circuit_loop",
    "globe",
    "globe_point",
    "jet_stream",
    "atmosphere_section",
    "coral_polyp",
    "symbiont",
    "brain",
    "neuron",
    "intestinal_wall",
    "heart",
    "nephron",
    "bbb_unit",
    "root_section",
    "signaling_cascade",
    "badge",
    "liver_sinusoid",
    "trial_sequence",
    "Placement",
    "PortSpread",
    "RingLayout",
    "row",
    "column",
    "grid",
    "align",
    "distribute",
    "ring",
    "bipartite_order",
    "spread_ports",
]


if __name__ == "__main__":
    import sys

    print(drawing_help(*sys.argv[1:]))


_ELSEWHERE = {
    # name → where it actually lives (the import a caller should write)
    "chart_slide": "from scripts.gen_svg_charts import chart_slide",
    "chart_help": "from scripts.gen_svg_charts import chart_help",
    "chart_fit": "from scripts.gen_svg_charts import chart_fit",
    "publish_slide": "from scripts.svg_lib.atomize_svg_to_slide import publish_slide",
    "native_text": "from scripts.svg_lib.atomize_svg_to_slide import native_text",
    "native_table": "from scripts.svg_lib.atomize_svg_to_slide import native_table",
    "native_bullets": "from scripts.svg_lib.atomize_svg_to_slide import native_bullets",
    "page_frame": "from scripts.svg_lib.atomize_svg_to_slide import page_frame",
    "native_line": "from scripts.svg_lib.atomize_svg_to_slide import native_line",
    "compose_slide": "from scripts.svg_lib.atomize_svg_to_slide import compose_slide",
    "Drawing": "from scripts.svg_lib.svg_drawing import Drawing",
    "drawing_help": "from scripts.svg_lib.svg_drawing import drawing_help",
    "svg_at": "svg_at is a Drawing method: d = Drawing(w, h); d.svg_at(at, svg, size=...)",
    "box_at": "box_at is a Drawing method: d.box_at(at, text, font_size=...)",
    "text_at": "text_at is a Drawing method: d.text_at(at, text, font_size=...)",
    "arrow": "arrow is a Drawing method: d.arrow(node_a, node_b)",
    "relation_help": "from scripts.gen_svg_relations import relation_help",
    "make_relation_atomized": "from scripts.gen_svg_relations import make_relation_atomized",
}


def __getattr__(name):
    """A name imported from the neighbouring module resolves to the real one (the wrong import line still works)."""
    hint = _ELSEWHERE.get(name)
    if hint and hint.startswith("from "):
        import importlib

        module, attr = hint[5:].split(" import ")
        return getattr(importlib.import_module(module), attr)
    if hint:
        raise ImportError(f"{name!r} is not importable from {__name__}; {hint}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
