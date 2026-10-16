"""Internal implementation of svg_drawing; import the public facade instead."""


def __getattr__(name):
    """``from scripts.svg_lib.drawing_lib import cell`` resolves to the public svg_drawing facade."""
    if name.startswith("_"):
        raise AttributeError(name)
    import importlib

    facade = importlib.import_module(
        "scripts.svg_lib.svg_drawing"
        if __name__.startswith("scripts.")
        else __name__.rsplit(".", 1)[0] + ".svg_drawing"
    )
    if name in getattr(facade, "__all__", ()) or hasattr(facade, name):
        return getattr(facade, name)
    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}; public parts import as "
        f"`from scripts.svg_lib.svg_drawing import Drawing, ...` (see drawing_help('parts'))"
    )
