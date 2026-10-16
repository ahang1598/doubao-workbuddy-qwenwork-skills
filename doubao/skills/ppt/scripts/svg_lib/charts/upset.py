"""UpSet: exact set intersections with aligned size bars and membership matrix."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from fractions import Fraction
from itertools import combinations
from xml.sax.saxutils import quoteattr

from .._common import _rgba_with_alpha
from . import _academic_rigor as rigor
from ._chart_layout import ChartLayout, finite, number_label, wrap_lines
from ._shared import tr


def _count(value, name):
    if isinstance(value, int) and not isinstance(value, bool):
        if not 0 <= value <= 2**53:
            raise ValueError(f"{name} must be a nonnegative count <= 2**53 for exact numeric rendering")
        return value
    number = finite(value, name, minimum=0)
    if not number.is_integer() or number > 2**53:
        raise ValueError(f"{name} must be a nonnegative integer count <= 2**53")
    return int(number)


def _names(values, name):
    labels = list(values)
    if any(not isinstance(s, str) or not s.strip() for s in labels):
        raise ValueError(f"{name} must contain nonempty string set names")
    if len(set(labels)) != len(labels):
        raise ValueError(f"{name} contains duplicate set names")
    return labels


def _prepare_upset(sets, intersections, set_sizes, mode):
    """Return names, full counts and full set sizes before any display limit."""
    if mode not in {"exclusive", "inclusive"}:
        raise ValueError("mode must be exclusive or inclusive")
    if (sets is None) == (intersections is None):
        raise ValueError("provide either member sets or explicit intersections")
    if sets is not None:
        if not isinstance(sets, Mapping) or not sets:
            raise ValueError("sets must be a nonempty mapping of names to member iterables")
        if set_sizes is not None:
            raise ValueError("set_sizes is only needed with explicit intersections")
        names = _names(sets, "sets")
        members = {}
        for name, values in sets.items():
            if isinstance(values, (str, bytes)):
                raise TypeError(f"set {name!r} requires an iterable of member identifiers, not a string")
            try:
                members[name] = set(values)
            except TypeError as exc:
                raise ValueError(f"set {name!r} members must be hashable identifiers") from exc
        atom_membership = {}
        for name, values in members.items():
            for member in values:
                atom_membership.setdefault(member, []).append(name)
        atoms = Counter(frozenset(labels) for labels in atom_membership.values())
        counts = Counter()
        if mode == "exclusive":
            counts.update(atoms)
        else:
            # Count every nonempty inclusive intersection without double counting
            # the members inside an atom. Empty intersections carry no bars.
            if any(len(atom) > 16 for atom in atoms):
                raise ValueError(
                    "inclusive mode with >16 coincident sets is too large; provide precomputed intersections"
                )
            for atom, count in atoms.items():
                ordered = [name for name in names if name in atom]
                for size in range(1, len(ordered) + 1):
                    for subset in combinations(ordered, size):
                        counts[frozenset(subset)] += count
        ordered_counts = dict(
            sorted(counts.items(), key=lambda item: tuple(names.index(s) for s in names if s in item[0]))
        )
        return names, ordered_counts, {name: len(values) for name, values in members.items()}

    counts = {}
    names = []
    for i, record in enumerate(intersections):
        if not isinstance(record, Mapping) or set(record) != {"sets", "size"}:
            raise ValueError(f"intersection {i} must contain exactly sets and size")
        if isinstance(record["sets"], (str, bytes)):
            raise TypeError(f"intersection {i} sets must be a sequence of names")
        labels = _names(record["sets"], f"intersection {i}")
        if not labels:
            raise ValueError("the empty-set/universe intersection is not an UpSet column")
        key = frozenset(labels)
        if key in counts:
            raise ValueError(f"duplicate intersection: {labels}")
        counts[key] = _count(record["size"], f"intersection {i} size")
        for label in labels:
            if label not in names:
                names.append(label)
    if not names:
        raise ValueError("intersections must contain at least one named intersection")
    if set_sizes is not None:
        if not isinstance(set_sizes, Mapping):
            raise ValueError("set_sizes must be a mapping of names to integer counts")
        size_names = _names(set_sizes, "set_sizes")
        if set(names) - set(size_names):
            raise ValueError("set_sizes must include every named set")
        names = size_names
        sizes = {name: _count(set_sizes[name], f"set_sizes[{name!r}]") for name in names}
    elif mode == "exclusive":
        sizes = {
            name: _count(sum(count for subset, count in counts.items() if name in subset), f"derived set size {name!r}")
            for name in names
        }
    else:
        missing = [name for name in names if frozenset((name,)) not in counts]
        if missing:
            raise ValueError(
                "inclusive counts cannot be summed to recover set sizes; provide set_sizes or all singleton counts"
            )
        sizes = {name: counts[frozenset((name,))] for name in names}
    for name in names:
        lower = (
            sum(count for subset, count in counts.items() if name in subset)
            if mode == "exclusive"
            else max((count for subset, count in counts.items() if name in subset), default=0)
        )
        if lower > sizes[name]:
            raise ValueError(f"intersections exceed the size of set {name!r}")
    if mode == "inclusive":
        for subset, value in counts.items():
            if len(subset) == 1 and value != sizes[next(iter(subset))]:
                raise ValueError("inclusive singleton counts must equal their set sizes")
        # Supplied set totals are known singleton intersections even when the user did not request singleton columns.
        facts = dict(counts)
        facts.update({frozenset((name,)): size for name, size in sizes.items()})
        _validate_inclusive(names, facts)
    return names, counts, sizes


def _validate_inclusive(names, counts):
    """Certify nonnegative integer atoms, without assigning unknown facts zero."""
    active = [name for name in names if counts[frozenset((name,))] > 0]
    active_set = set(active)
    facts = {}
    for subset, count in counts.items():
        if not subset <= active_set:
            if count:
                raise ValueError("inclusive intersections involving an empty set must be zero")
        else:
            facts[subset] = count
    parent = {name: name for name in active}

    def find(name):
        while parent[name] != name:
            parent[name] = parent[parent[name]]
            name = parent[name]
        return name

    for subset in facts:
        ordered = [name for name in active if name in subset]
        for name in ordered[1:]:
            parent[find(name)] = find(ordered[0])
    components = {}
    for name in active:
        components.setdefault(find(name), []).append(name)
    for component in components.values():
        position = {name: i for i, name in enumerate(component)}
        known = {
            sum(1 << position[name] for name in subset): count
            for subset, count in facts.items()
            if subset <= set(component)
        }
        n = len(component)
        if all(value == 0 for mask, value in known.items() if mask & (mask - 1)):
            feasible = True  # Disjoint sets are an explicit witness at any size.
        elif len(known) == (1 << n) - 1 and n <= 16:
            atoms = [0] + [known[mask] for mask in range(1, 1 << n)]
            for i in range(n):
                for mask in range(1, len(atoms)):
                    if not mask & (1 << i):
                        atoms[mask] -= atoms[mask | (1 << i)]
            feasible = all(value >= 0 for value in atoms[1:])
        else:
            if n > 8:
                raise ValueError(
                    "partial inclusive counts support at most 8 connected nonempty sets; "
                    "provide member sets or complete intersection counts for larger groups"
                )
            feasible = _inclusive_atom_witness(n, known) is not None
        if not feasible:
            raise ValueError(
                "inclusive counts are inconsistent: no nonnegative integer exclusive atoms satisfy all known facts"
            )


def _inclusive_atom_witness(n, known):
    """Return an exact integer membership certificate, or prove infeasibility."""
    pending = [{}]
    work = {"pivots": 0}
    nodes = 0
    while pending:
        nodes += 1
        if nodes > 2048:
            raise ValueError("partial inclusive integer feasibility exceeded the exact search node limit")
        bounds = pending.pop()
        witness = _inclusive_lp_witness(n, known, bounds=bounds, work=work)
        if witness is None:
            continue
        fractional = []
        for mask, value in witness.items():
            ratio = Fraction(value)
            if ratio.denominator != 1:
                remainder = ratio - ratio.numerator // ratio.denominator
                constrained_by = sum(mask & fact == fact for fact in known)
                fractional.append((min(remainder, 1 - remainder), constrained_by, -mask, mask))
        if not fractional:
            certificate = {mask: int(value) for mask, value in witness.items()}
            if not _valid_atom_witness(known, certificate, bounds=bounds, integer=True):
                raise ArithmeticError("integer inclusive feasibility certificate failed verification")
            return certificate

        atom = max(fractional)[3]
        value = Fraction(witness[atom])
        lower_integer = value.numerator // value.denominator
        old_lower, old_upper = bounds.get(atom, (0, None))
        branches = []
        if old_lower <= lower_integer:
            left = dict(bounds)
            left[atom] = (old_lower, min(old_upper, lower_integer) if old_upper is not None else lower_integer)
            branches.append(left)
        if old_upper is None or lower_integer + 1 <= old_upper:
            right = dict(bounds)
            right[atom] = (max(old_lower, lower_integer + 1), old_upper)
            branches.append(right)
        # Search the nearest integer side first; ties favor retaining a shared
        # atom, which can satisfy several intersection equations at once.
        if value - lower_integer >= Fraction(1, 2):
            branches.reverse()
        pending.extend(reversed(branches))
    return None


def _valid_atom_witness(known, witness, *, bounds=None, integer=False):
    """Independently verify exact equations, nonnegativity, bounds and integrality."""
    if any(
        value < 0 or (integer and (not isinstance(value, int) or isinstance(value, bool))) for value in witness.values()
    ):
        return False
    if any(
        sum(value for mask, value in witness.items() if mask & fact == fact) != target for fact, target in known.items()
    ):
        return False
    return all(
        witness.get(mask, 0) >= lower and (upper is None or witness.get(mask, 0) <= upper)
        for mask, (lower, upper) in (bounds or {}).items()
    )


def _inclusive_lp_witness(n, known, *, bounds=None, work=None):
    """Exact rational Phase-I relaxation, including branch lower/upper bounds."""
    bounds = bounds or {}
    work = work if work is not None else {"pivots": 0}
    if any(lower < 0 or (upper is not None and lower > upper) for lower, upper in bounds.values()):
        return None
    zero_facts = [mask for mask, value in known.items() if value == 0]
    masks = [mask for mask in range(1, 1 << n) if not any(mask & zero == zero for zero in zero_facts)]
    allowed = set(masks)
    if any(lower > 0 and atom not in allowed for atom, (lower, _) in bounds.items()):
        return None
    shifts = {atom: lower for atom, (lower, _) in bounds.items() if lower}
    masks = [atom for atom in masks if bounds.get(atom, (0, None))[0] != bounds.get(atom, (0, None))[1]]
    equations = {}
    for fact, value in known.items():
        value -= sum(lower for atom, lower in shifts.items() if atom & fact == fact)
        if value < 0:
            return None
        columns = tuple(j for j, atom in enumerate(masks) if atom & fact == fact)
        if not columns:
            if value:
                return None
            continue
        if columns in equations and equations[columns] != value:
            return None
        equations[columns] = value
    variable_count = len(masks)
    for column, atom in enumerate(masks):
        lower, upper = bounds.get(atom, (0, None))
        if upper is not None:
            equations[(column, variable_count)] = upper - lower
            variable_count += 1
    rows, rhs, basis, reduced = [], [], [], {}
    for i, (columns, value) in enumerate(equations.items()):
        artificial = variable_count + i
        rows.append(dict.fromkeys(columns, 1))
        rows[-1][artificial] = 1
        rhs.append(value)
        basis.append(artificial)
        for column in columns:
            reduced[column] = reduced.get(column, 0) - 1
    objective = sum(rhs)
    for _ in range(4096):
        if objective == 0:
            witness = dict(shifts)
            for column, value in zip(basis, rhs):
                if column < len(masks) and value:
                    atom = masks[column]
                    witness[atom] = witness.get(atom, 0) + value
            if not _valid_atom_witness(known, witness, bounds=bounds):
                raise ArithmeticError("inclusive feasibility certificate failed verification")
            return witness
        entering = min((column for column, cost in reduced.items() if cost < 0), default=None)
        if entering is None:
            return None  # Optimal Phase-I objective is strictly positive.
        eligible = [i for i, row in enumerate(rows) if row.get(entering, 0) > 0]
        if not eligible:
            raise ArithmeticError("Phase-I objective unexpectedly unbounded")
        work["pivots"] += 1
        if work["pivots"] > 40000:
            raise ValueError("partial inclusive integer feasibility exceeded the exact search pivot limit")
        leaving = min(eligible, key=lambda i: (Fraction(rhs[i]) / rows[i][entering], basis[i]))
        divisor = rows[leaving][entering]
        pivot = {column: Fraction(value) / divisor for column, value in rows[leaving].items()}
        pivot_rhs = Fraction(rhs[leaving]) / divisor
        rows[leaving], rhs[leaving], basis[leaving] = pivot, pivot_rhs, entering
        for i, row in enumerate(rows):
            factor = row.get(entering, 0)
            if i == leaving or not factor:
                continue
            for column, value in pivot.items():
                updated = row.get(column, 0) - factor * value
                if updated:
                    row[column] = updated
                else:
                    row.pop(column, None)
            rhs[i] -= factor * pivot_rhs
        cost = reduced[entering]
        for column, value in pivot.items():
            updated = reduced.get(column, 0) - cost * value
            if updated:
                reduced[column] = updated
            else:
                reduced.pop(column, None)
        objective += cost * pivot_rhs
    raise ValueError("partial inclusive feasibility exceeded the exact solver's iteration limit")


def make_upset(
    sets=None,
    *,
    intersections=None,
    set_sizes=None,
    mode="exclusive",
    sort_by="size",
    set_order=None,
    max_intersections=None,
    width=1100,
    height=720,
    title=None,
    subtitle=None,
    figure_label=None,
    palette=None,
    font_family=None,
):
    """Return an UpSet SVG from member sets or explicit intersection counts.

    ``sets`` maps names to iterables of hashable member IDs (duplicates removed).
    Or pass ``intersections=[{'sets':['A','B'], 'size':12}, ...]``. With default
    ``mode='exclusive'``, A+B means members in A and B and in no other named set.
    With ``mode='inclusive'``, A+B includes members also found in further sets;
    columns consequently overlap and must not be summed into a union size.

    Explicit exclusive counts are treated as a complete partition when
    ``set_sizes`` is omitted. To plot a supplied subset, pass full ``set_sizes``.
    Explicit inclusive counts require full ``set_sizes`` or every singleton
    count, because adding inclusive intersections would double count members.
    ``sort_by`` is size (descending), degree (ascending) or input. ``set_order``
    is a permutation of all names; default is descending full set size.
    ``max_intersections`` limits displayed columns after full aggregation and
    sorting; set-size bars always retain their full, untruncated counts.
    Individual and derived set counts must be integer values <= 2**53.
    Partial inclusive data is checked by exact nonnegative-integer-atom feasibility,
    up to 8 connected nonempty sets; complete counts support up to 16 per group.
    Exceptionally complex partial data can hit an explicit search-work limit.
    Member-set input does not use this partial-data solver.
    Background is inherited from slides.
    """
    if sort_by not in {"size", "degree", "input"}:
        raise ValueError("sort_by must be size, degree or input")
    if max_intersections is not None:
        max_intersections = _count(max_intersections, "max_intersections")
        if max_intersections == 0:
            raise ValueError("max_intersections must be positive")
    names, all_counts, sizes = _prepare_upset(sets, intersections, set_sizes, mode)
    if set_order is not None:
        order = _names(set_order, "set_order")
        if set(order) != set(names):
            raise ValueError("set_order must be a permutation of all set names")
    else:
        order = sorted(names, key=lambda name: (-sizes[name], names.index(name)))
    rows = [(key, count) for key, count in all_counts.items() if count > 0]

    def membership_key(item):
        return tuple(i for i, name in enumerate(order) if name in item[0])

    if sort_by == "size":
        rows.sort(key=lambda item: (-item[1], len(item[0]), membership_key(item)))
    elif sort_by == "degree":
        rows.sort(key=lambda item: (len(item[0]), -item[1], membership_key(item)))
    full_columns = len(rows)
    if max_intersections is not None:
        rows = rows[:max_intersections]
    layout = ChartLayout(width, height, palette, font_family, n_items=max(len(order), len(rows)))
    pal = layout.pal
    top = layout.header(title, subtitle, figure_label)
    labels_width = min(
        240, max(95, layout.width * 0.2), max(layout.measure(name, layout.font_sizes["label"]) + 8 for name in names)
    )
    bar_width = min(170, max(95, layout.width * 0.15))
    left = 32
    size_labels = {name: number_label(size, compact=True) for name, size in sizes.items()}
    count_width = max(layout.measure(label, layout.font_sizes["ytick"]) for label in size_labels.values())
    # A dedicated measured count column stays clear of both the bars and names.
    # This avoids the old outside-bar fallback overflowing the left canvas.
    counts_right = left + bar_width + 10 + count_width
    names_x = counts_right + 18
    matrix_left = names_x + labels_width + 28
    matrix_right = layout.width - 30
    matrix_width = matrix_right - matrix_left
    compact = layout.height < 600
    narrow = matrix_width < 190
    if narrow:
        # Narrow canvases drop the set-size bar panel; exact set sizes stay in the count column.
        left, bar_width = 20, 0
        counts_right = left + count_width
        names_x = counts_right + 12
        matrix_left = names_x + labels_width + 14
        matrix_right = layout.width - 16
        matrix_width = matrix_right - matrix_left
    if matrix_width < 190 and not narrow or matrix_width < 120:
        raise ValueError("UpSet canvas is too narrow; increase width")
    note = (
        tr("Exclusive intersections: filled dots = present; other named sets = absent.")
        if mode == "exclusive"
        else "Inclusive intersections: filled dots = required; other sets unrestricted. Columns may overlap."
    )
    if full_columns > len(rows):
        note += f" Showing {len(rows)} of {full_columns} nonempty intersections; set sizes remain complete."
    if sets is None and set_sizes is not None:
        note += " Full set sizes supplied separately."
    footer_h = (
        len(wrap_lines(note, layout.width - 60, layout.font_sizes["foot"], layout.font))
        * layout.font_sizes["foot"]
        * 1.35
    )
    footer_top = layout.height - 27 - footer_h
    name_lines = [wrap_lines(name, labels_width - 8, layout.font_sizes["label"], layout.font) for name in order]
    row_min = 22 if compact else 29
    row_heights = [max(row_min, len(lines) * layout.font_sizes["label"] * 1.35 + 6) for lines in name_lines]
    matrix_height = sum(row_heights)
    footer_gap, scale_gap, chart_min = (16, 14 if narrow else 40, 110) if compact else (38, 40, 135)
    required = (
        top + layout.font_sizes["group"] * 1.35 + layout.font_sizes["ytick"] * 3 + 220 + matrix_height + footer_h + 80
    )
    if compact:
        required = (
            top
            + layout.font_sizes["group"] * 1.35
            + 12
            + chart_min
            + scale_gap
            + footer_gap
            + matrix_height
            + footer_h
            + 27
        )
    layout.height = max(layout.height, required)
    footer_top = layout.height - 27 - footer_h
    matrix_top = footer_top - footer_gap - matrix_height
    chart_top = top + layout.font_sizes["group"] * 1.35 + 12
    chart_bottom = matrix_top - scale_gap
    if chart_bottom - chart_top < chart_min:
        raise ValueError("UpSet rows/labels need more vertical room; increase height or shorten set names")
    col_width = matrix_width / max(1, len(rows))
    count_fs = layout.font_sizes["ytick"]
    count_width = max((layout.measure(number_label(v, compact=True), count_fs) for _, v in rows), default=15)
    if rows and col_width < (count_width + 5 if narrow else max(24, count_width + 9)):
        raise ValueError("UpSet intersection columns are too narrow; increase width or set max_intersections")
    layout.text(tr("Set size") if not narrow else tr("Set (size)"), left, top, fs=layout.font_sizes["group"], bold=True)
    layout.text(tr("Intersection size"), matrix_left, top, fs=layout.font_sizes["group"], bold=True)
    max_count = max((count for _, count in rows), default=1)
    ticks, _, limit = rigor.nice_axis(0, max_count, 4)
    ticks = [tick for tick in ticks if float(tick).is_integer()]
    y0, y1 = chart_top + count_fs * 1.6, chart_bottom
    grid_positions = []
    for tick in ticks:
        y = y1 - (y1 - y0) * tick / limit
        grid_positions.append(y)
        layout.parts.append(
            f'<line x1="{matrix_left:.2f}" y1="{y:.2f}" '
            f'x2="{matrix_right:.2f}" y2="{y:.2f}" stroke={quoteattr(pal["grid"])} stroke-width=".8"/>'
        )
    # y axis sits above the membership labels, sharing x with the matrix boundary.
    layout.parts.append(
        rigor.draw_y_axis(matrix_left, y0, y1, ticks, 0, limit, pal=pal, fs_tick=layout.font_sizes["ytick"])
    )
    bar_w = min(40, col_width * 0.66)
    for column, (subset, count) in enumerate(rows):
        x = matrix_left + col_width * (column + 0.5)
        h = (y1 - y0) * count / limit
        layout.parts.append(
            f'<rect x="{x - bar_w / 2:.2f}" y="{y1 - h:.2f}" '
            f'width="{bar_w:.2f}" height="{h:.2f}" fill={quoteattr(pal["accent"])}/>'
        )
        label_top = y1 - h - count_fs * 1.35 - 6
        # Count labels above a near-tick bar must not be struck by that gridline.
        crossing = [gy for gy in grid_positions if label_top - 2 <= gy <= label_top + count_fs * 1.1 + 2]
        while crossing:
            label_top = min(crossing) - count_fs * 1.1 - 4
            crossing = [gy for gy in grid_positions if label_top - 2 <= gy <= label_top + count_fs * 1.1 + 2]
        layout.text(number_label(count, compact=True), x, label_top, fs=count_fs, anchor="middle")
    set_limit = max(sizes.values(), default=0) or 1
    endpoint = number_label(set_limit, compact=True)
    if (
        layout.measure(endpoint, layout.font_sizes["xtick"]) + layout.measure("0", layout.font_sizes["xtick"]) + 12
        > bar_width
    ):
        # This is only the scale; exact full counts remain in the measured
        # count column. Scientific scale labels can round without altering data.
        for precision in (3, 2, 1):
            endpoint = "≈ " + format(set_limit, f".{precision}g")
            if (
                layout.measure(endpoint, layout.font_sizes["xtick"])
                + layout.measure("0", layout.font_sizes["xtick"])
                + 12
                <= bar_width
            ):
                break
    if not narrow:
        layout.text(
            endpoint,
            left,
            matrix_top - layout.font_sizes["xtick"] * 1.35 - 10,
            fs=layout.font_sizes["xtick"],
            color=pal["ink6"],
        )
        layout.text(
            "0",
            left + bar_width,
            matrix_top - layout.font_sizes["xtick"] * 1.35 - 10,
            fs=layout.font_sizes["xtick"],
            color=pal["ink6"],
            anchor="end",
        )
    centers = {}
    cursor = matrix_top
    for i, (name, row_h) in enumerate(zip(order, row_heights)):
        cy = cursor + row_h / 2
        centers[name] = cy
        if i % 2 == 0:
            layout.parts.append(
                f'<rect x="{names_x - 8:.2f}" y="{cursor:.2f}" '
                f'width="{matrix_right - names_x + 8:.2f}" height="{row_h:.2f}" '
                f"fill={quoteattr(_rgba_with_alpha(layout.ink, 0.045))}/>"
            )
        h = min(17, row_h * 0.5)
        w = bar_width * sizes[name] / set_limit
        if not narrow:
            layout.parts.append(
                f'<rect x="{left + bar_width - w:.2f}" y="{cy - h / 2:.2f}" '
                f'width="{w:.2f}" height="{h:.2f}" fill={quoteattr(pal["secondary"])}/>'
            )
        # Names and exact counts occupy separate measured columns.
        label_top = cy - len(name_lines[i]) * layout.font_sizes["label"] * 1.35 / 2
        layout.text(name, names_x, label_top, fs=layout.font_sizes["label"], width=labels_width - 8)
        layout.text(
            size_labels[name],
            counts_right,
            cy - layout.font_sizes["ytick"] * 0.6,
            fs=layout.font_sizes["ytick"],
            anchor="end",
        )
        cursor += row_h
    for column, (subset, count) in enumerate(rows):
        x = matrix_left + col_width * (column + 0.5)
        active = [centers[name] for name in order if name in subset]
        if len(active) > 1:
            layout.parts.append(
                f'<line x1="{x:.2f}" y1="{min(active):.2f}" '
                f'x2="{x:.2f}" y2="{max(active):.2f}" '
                f'stroke={quoteattr(layout.ink)} stroke-width="2"/>'
            )
        for name in order:
            fill = layout.ink if name in subset else _rgba_with_alpha(layout.ink, 0.14)
            radius = min(4.6, col_width * 0.3)
            layout.parts.append(
                f'<circle cx="{x:.2f}" cy="{centers[name]:.2f}" r="{radius:.2f}" fill={quoteattr(fill)}/>'
            )
    if not rows:
        layout.text(
            "No nonempty intersections",
            (matrix_left + matrix_right) / 2,
            (y0 + y1) / 2,
            fs=layout.font_sizes["label"],
            anchor="middle",
            color=pal["ink6"],
        )
    layout.text(note, 30, footer_top, fs=layout.font_sizes["foot"], color=pal["ink6"], width=layout.width - 60)
    return layout.svg(
        f"UpSet with {mode} semantics; row order: {', '.join(order)}; "
        f"showing {len(rows)} of {full_columns} nonempty intersections."
    )
