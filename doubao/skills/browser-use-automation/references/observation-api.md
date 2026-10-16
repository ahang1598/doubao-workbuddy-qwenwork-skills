# Observation API Reference

Observation API purposes, parameters, return types, and examples.

Choose by the information needed for the next decision, not by always starting with Snapshot:

| Current knowledge and next decision | API | Result shape |
|---|---|---|
| page structure or next control is unknown | `snapshot()` | page structure and action refs; defaults below |
| only actionable targets are needed | `snapshot(view="interactive")` | strong actions plus required context |
| page content and controls are needed | `snapshot(view="all")` | broader semantic tree with action refs |
| target text or intent is already known | `find()` | exact-first semantic refs with local structure |
| read a document or one known region | `get_page_text()` | rendered text only |
| read one known element | `text()`, `get()` | one text/property value |
| compare repeated records without losing field pairing | `read_all()` | bounded row dictionaries |
| read an article, reference page, or other document content | `extract_content()` | document-ordered content blocks plus Markdown |
| request only selected document content types | `extract_content(types=...)` | filtered heading, paragraph, list, link, or table blocks |
| need the legacy type-grouped article structure | `content_export()` | separate headings, paragraphs, links, and tables |
| reuse a semantic target as CSS | `get_css_locator()` | ordered unique CSS locators |

## Shared semantics

- Examples assume `import aha_browser_use as bu` has already run in the Browser Use cell.
- `Ref` identifies an observed element, for example `n21`. Pass it back unchanged; re-observe if stale.
- `FindResult` behaves like `list[Ref]`; `.first` returns the first ref or `None`.
- Find nodes expose `node.get("visible")`: `True` / `False` when geometry is known,
  `None` otherwise. `[not-visible]` marks `False`; the target may need scrolling or
  a menu/panel/tab to be opened. Visibility alone does not guarantee interaction.
- `CssLocator` carries `selector`, `frame_path`, and `match`. It is reusable input, not a promise
  that the page will continue matching after navigation or DOM changes.
- `ElementTarget = Ref | CssLocator` is the public node/CSS target union used by supported reads,
  actions, and scoped observations. APIs also accept a raw `nN` string where documented.
- `CssLocatorList` behaves like `list[CssLocator]`; `.first` is the primary unique locator or
  `None` when no unique locator is available.
- `snapshot()` and `find()` do not emit observation text automatically. Both results print as their
  bounded observation text; `find()` remains iterable as refs. Print the result when that text is
  needed. `extract_content()` is structured but prints as bounded Markdown.
  Other APIs return ordinary Python values; print only the fields needed for the next decision.
- `find()` ranks exact matches first and includes nearby context to distinguish candidates.
  Iterate the result or use `.match_refs` for matches; `.all_refs` also includes contextual refs.
- `max_chars` bounds one returned result or model-visible observation; the explicit-ref form of
  `read_all()` documents its per-element exception below. It does not scroll, load lazy content,
  or make hidden content observable. Increase it only when truncation metadata shows relevant
  content was omitted.
- Invalid inputs and failed operations raise exceptions; unavailable capabilities use
  `BrowserUseError(code="UNSUPPORTED")`.

## API reference

### CSS locator helper

```python
def css(
    selector: str,
    *,
    frame_path: tuple[str, ...] = (),
    match: str = "unique",
) -> CssLocator:
    """Create a CSS locator for scoped reads or actions.

    match: "unique" requires one match; "first" selects the first; "all" selects multiple.
    frame_path: () for the main document; iframe paths and Shadow DOM scopes are unsupported.
    """
    ...
```

#### Usage example

```python
main = bu.css("main", match="first")
rows = bu.css("article, [role=listitem]", match="all")
```

`snapshot(within=...)` and `extract_content(within=...)` accept all three match policies.
`all` returns non-overlapping regions in document order. Scoped reads include offscreen content
without scrolling; a target with no observable content reports an error.

### Structure and semantic targets

```python
def snapshot(
    *,
    view: Literal["outline", "interactive", "all"] = "outline",
    within: ElementTarget | str = "viewport",  # "full", "viewport", REF or CSS
    max_chars: int = 3200,  # clamped to 1000..4000
) -> SnapshotResult: ...


def find(
    query: str,  # `|` = OR, `&` = AND
    *,
    limit: int = 10,  # clamped to 1..1000
    search_type: Literal["text", "interaction", "all"] = "all",
    max_chars: int = 8000,  # clamped to 1000..30000
) -> FindResult: ...
```

`within` selects the range: `"full"` for the whole rendered page, `"viewport"` for the current
viewport, or a ref/CSS locator for its subtree, including offscreen descendants.

Omitted arguments use the defaults in the signature; explicit values override them independently.
`None` is not a valid Snapshot argument.
`within="viewport"` may also include horizontally offscreen input/selection controls.
An observed control is not necessarily ready for interaction.

Return shapes (duck types):

```python
class ObservationNode(Mapping[str, Any]):
    data: Mapping[str, Any]             # raw node fields
    ref: Ref | None
    node_id: str
    parent_ref: Ref | None
    depth: int
    popup: bool
    children: tuple[ObservationNode, ...]
    children_refs: tuple[Ref, ...]
    scope_index: int | None             # index into SnapshotResult.scope_refs
    role: str
    name: str
    text: str
    value: str
    bounds: dict | None
    interaction: dict
    form_control: dict
    link: dict
    scroller: dict
    def serialize(self) -> str: ...      # this node plus descendants, Snapshot format


class QueryMatch(TypedDict):
    nodeId: str
    ref: Ref
    matchedTerms: list[str]
    matchedFields: list[str]


class SnapshotResult(str):
    observation: str
    text: str
    mode: Literal["full"]
    changes: tuple[SnapshotChange, ...] # empty in normal mode
    removed_refs: tuple[Ref, ...]        # empty in normal mode
    full_text: str                     # current bounded full text, same as str(result)
    data: Mapping[str, Any]             # raw result fields
    document_generation: int
    scope: str
    root: ObservationNode | None
    popup_root: ObservationNode | None
    roots: tuple[ObservationNode, ...]
    nodes: tuple[ObservationNode, ...]
    by_ref: dict[str, ObservationNode]
    refs: tuple[Ref, ...]               # all structured refs
    shown_refs: tuple[Ref, ...]         # refs present in str(result)
    scope_refs: tuple[Ref, ...]         # retained within roots, document ordered
    scope_truncated: bool
    url: str
    title: str
    view: str
    viewport: dict
    page_state: dict
    popup: dict
    stats: dict
    may_be_incomplete: bool
    def node(self, ref: Ref) -> ObservationNode | None: ...


class SnapshotChange(TypedDict):
    nodeId: str                        # look up the current node in result.by_ref
    kind: Literal["added", "updated", "moved"]  # + / ~ / >; current node content
    parent: str                        # empty for document root; "popup" for popup root
    after: str                         # previous sibling; empty for first child


class FindResult(list[Ref]):
    first: Ref | None
    data: Mapping[str, Any]             # raw result fields
    document_generation: int
    scope: str
    roots: tuple[ObservationNode, ...]   # contextual query-result roots
    nodes: tuple[ObservationNode, ...]   # matches plus locator-backed context
    by_ref: dict[str, ObservationNode]
    all_refs: tuple[Ref, ...]           # every match and context ref
    metadata: Mapping[str, Any]
    matches: tuple[QueryMatch, ...]      # ranked semantic matches
    match_refs: tuple[Ref, ...]
    url: str
    title: str
    viewport: dict
    stats: dict
    may_be_incomplete: bool
    def __str__(self) -> str: ...        # bounded @find observation text
    def node(self, ref: Ref) -> ObservationNode | None: ...
```

`max_chars` limits the printable Snapshot/Find text, not the structured nodes.

#### Changes after an action

```python
before = bu.snapshot(within="full", view="interactive")
print(before)
# Act on a ref from this observation, then inspect the current page.
after = bu.snapshot(within="full", view="interactive")
print(after)
```

- Snapshot always returns full observation text for the selected scope, within `max_chars`.
  `result.full_text` is the same printable text; `nodes` and `by_ref` provide the structured observation.

#### Snapshot example

```python
print(bu.snapshot())
```

```text
@page scope=d4 view=outline within=viewport total_nodes=642 shown=4/86 title="Shop" url=https://example.com viewport=1280x720
@focused none
n1 doc [y=0/1680]
 n12 a "Catalog" -> /catalog
 n18 searchbox "Site search" [edit ph="Search"]
 n21 button "Place order"
@more rows=82 reason=chars max_chars=3200
```

Output notation:

- `n...` is an element ref; `scope` identifies the document, not an element.
- `total_nodes` counts source nodes; `shown=A/B` means A of B text rows are displayed.
  `@more` marks omitted output, `node_more` omitted nodes, and `incomplete=true` a possibly incomplete observation.
- Short roles (`doc`, `a`, `ul`, etc.) describe semantics, not guaranteed CSS tag names.
  `ObservationNode.role` provides the full role.
- `focused`, `expanded` / `collapsed`, `disabled`, `edit`, `checked`, `required` are states; `type` is the form subtype;
  `ph` is placeholder text; `->` is a link target; `ctx` is matching context.
- `options=[*text=>value|!text=>value]+N`: `*` selected, `!` disabled, `*!` both, `+N` omitted choices.
  Equal text/value appears once; backslash escapes separators.
- `x=current/max` and `y=current/max` show scroll position and range.

#### Find example

```python
matches = bu.find(
    "Place order | Checkout",
    search_type="interaction",
    limit=5,
    max_chars=4000,
)
print(matches)
ref = matches.first
```

```text
@find scope=d4 nodes=2 cap=5 shown=2/2 matches=2 search=interaction title="Shop" url=https://example.com viewport=1280x720
n21 button "Place order"
n57 button "Place order and continue"
```

`matches=N+` means more semantic matches exist than `limit` returned. When several candidates are
plausible, refine the query or inspect their surrounding structure before acting on `.first`.

#### Process structured results

```python
snapshot = bu.snapshot(max_chars=1000)
buttons = [
    {"ref": node.ref, "name": node.name, "parent": node.parent_ref}
    for node in snapshot.nodes
    if node.role == "button" and node.interaction.get("clickable")
]
print(buttons[:10])

cards = bu.snapshot(within=bu.css("article", match="all"), view="all")
print([
    {"scope": node.scope_index, "ref": node.ref, "text": node.text}
    for node in cards.nodes
    if node.text
][:20])

# Reprint one structured subtree in the same compact format as Snapshot.
node = cards.node(cards.refs[0])
if node:
    print(node.serialize())
```

### Text and element properties

```python
def get_page_text(
    *,
    within: ElementTarget | str | None = None,
    max_chars: int = 8000,
) -> str:
    """Read rendered text from the document or one scoped subtree.

    Args:
        within: Optional fresh ref or ``unique``/``first``/``all`` CSS locator.
            Defaults to the whole document. ``all`` reads up to 200 outermost,
            non-overlapping matches in document order.
        max_chars: Returned-text budget from 1 to 40000. Defaults to 8000.

    Returns:
        str: Rendered text without semantic structure or action refs. Text from
            multiple CSS matches is separated by one blank line.
    """
    ...


def text(ref: Ref, *, max_chars: int = 4000) -> str:
    """Read one element's rendered text, falling back to its value.

    Args:
        ref: Fresh current-document element ref.
        max_chars: Returned-text budget from 1 to 40000. Defaults to 4000.

    Returns:
        str: Rendered text, control value when text is empty, or ``""`` when
            neither is available.
    """
    ...


def get(ref: Ref, attr: str) -> str | bool | None:
    """Read one property or DOM attribute from an element.

    Args:
        ref: Fresh current-document element ref.
        attr: Property or attribute name. Supported properties are ``text``,
            ``value``, ``href``, ``src``, ``tag``, ``tagName``, ``role``, ``type``,
            ``name``, ``id``, ``title``, ``alt``, ``placeholder``, ``aria_label``,
            ``checked``, ``disabled``, ``selected``, ``readOnly``, and ``visible``.
            ``ariaLabel`` and ``readonly`` are accepted aliases. Any other name is
            read as a DOM attribute.

    Returns:
        str | bool | None: Property value, Boolean state, or ``None`` when absent.
    """
    ...
```

#### Usage example

```python
main = bu.get_page_text(
    within=bu.css("main", match="first"),
    max_chars=6000,
)
label = bu.text("n21")
href = bu.get("n33", "href")
print({"main": main, "label": label, "href": href})

sections = bu.get_page_text(
    within=bu.css("article, section.results", match="all"),
    max_chars=12000,
)
print(sections)
```

### High-density structured reads

```python
def read_all(
    selector_or_refs: ElementTarget | str | list[Ref] | tuple[Ref, ...],
    fields: list[str] | tuple[str, ...] | dict[str, dict] | None = None,
    limit: int = 50,
    *,
    max_chars: int = 12000,
) -> ReadAllResult:
    """Read repeated records while preserving fields from the same outer row.

    Args:
        selector_or_refs: Outer records as a CSS selector, CSS locator, one ref,
            or a sequence of refs. A non-ref string is treated as CSS with
            ``match="all"``.
        fields: Fields to read. ``None`` defaults to ``["text", "href"]``. A
            field list reads properties from each outer element. A mapping of 1
            to 32 output names reads descendants inside each outer element. Every
            mapping value requires ``selector`` and accepts optional ``field``
            (default ``"text"``) and ``limit`` (default 1). Field names follow
            ``get()`` semantics, except ``text`` falls back to DOM ``textContent``
            only when ``innerText`` is empty. Field limits range from 1 to 20.
            Limit 1 returns a scalar or ``None``; larger limits return a list or
            ``[]``. Mapped output names ``index``, ``nodeId``,
            ``documentGeneration``, ``ref``, and
            ``truncated`` are reserved.
        limit: Maximum outer records, from 1 to 300. Defaults to 50.
        max_chars: Character budget from 1 to 40000. Defaults to 12000. It is
            shared by one CSS batch; for an explicit ref sequence it applies to
            each element read.

    Returns:
        ReadAllResult: List-like rows containing only ``ref`` and the requested
            fields. Repeated text has compacted whitespace. ``print(result)``
            renders a compact CSV table while indexing and iteration still return
            ordinary row dictionaries.
    """
    ...


class ReadAllResult(list[dict]):
    columns: tuple[str, ...]
    def __str__(self) -> str: ...  # compact CSV with one row per result


def content_export(max_chars: int = 3000) -> dict:
    """Export article-like content without refs or layout data.

    Args:
        max_chars: Maximum returned content characters, from 200 to 40000.
            Defaults to 3000.

    Returns:
        dict: Article metadata and content: ``title``, ``url``, ``language``,
            ``truncated``, ``chars``, ``headings=[{level, text}]``,
            ``paragraphs=[str]``, ``links=[{text, href}]``, and
            ``tables=[{caption, rows}]``. It contains no action refs.
    """
    ...


def extract_content(
    types: Literal["all", "heading", "paragraph", "list", "link", "table"]
        | Sequence[Literal["heading", "paragraph", "list", "link", "table"]] = "all",
    max_chars: int = 4000,
    *,
    within: ElementTarget | str | None = None,
) -> ContentExtractionResult:
    """Extract content in document order from the page or known regions.

    ``max_chars`` is clamped to 100..40000 and controls only the default
    Markdown view. ``within`` accepts a fresh ref or a CSS locator, including
    ``match="all"`` for repeated regions. The result is directly iterable as
    a flat sequence of content blocks. Printed headings, paragraphs, lists,
    and tables show link text; standalone links print ``text → URL``.
    Full URLs remain available in ``result.url`` and ``block.links``.
    """
    ...


class ContentBlock:
    type: str
    text: str
    links: tuple[dict[str, str], ...]    # flat {"text": ..., "href": ...} anchors
    scope_index: int | None
    scope_ref: Ref | None
    truncated: bool
    caption: str                         # table only; otherwise ""
    rows: tuple[tuple[str, ...], ...]    # table cells as plain text
    header_rows: tuple[int, ...]         # indexes into rows
    depth: int                           # one-based content nesting depth
    ordered: bool                        # list only; otherwise false
    def markdown(self) -> str: ...       # this block in extract_content Markdown format
    def to_dict(self) -> dict[str, Any]: ...


class ContentExtractionResult(Sequence[ContentBlock]):
    blocks: tuple[ContentBlock, ...]
    types: tuple[str, ...]
    scope_refs: tuple[Ref, ...]
    scope_truncated: bool
    title: str
    url: str
    truncated: bool
    incomplete: bool
    source_nodes: int
    captured_nodes: int
    captured_bytes: int
    def __iter__(self) -> Iterator[ContentBlock]: ...
    def __getitem__(self, index: int | slice) -> ContentBlock | tuple[ContentBlock, ...]: ...
    def blocks_for(self, scope: int | Ref) -> tuple[ContentBlock, ...]: ...
    def markdown(self, max_chars: int | None = None) -> str: ...
    def to_dict(self) -> dict[str, Any]: ...
```

Use one `read_all()` call for repeated records to preserve field pairing. If data is clipped, narrow the outer selector,
fields, or region before increasing the budget. Each `read_all()` row keeps the outer container's
`ref`; mapped descendant fields return values, not child refs.

`ReadAllResult` behaves like `list[dict]`. Its CSV column order is `ref` followed by requested
fields. `None` prints as an empty cell, booleans as `true`/`false`, and multi-value fields use ` | `
inside one CSV cell.

#### Repeated-record example

```python
rows = bu.read_all(
    "article, [role=listitem]",
    fields={
        "title": {"selector": "h2, h3", "field": "text"},
        "prices": {"selector": ".price", "field": "text", "limit": 2},
        "url": {"selector": "a[href]", "field": "href"},
    },
    limit=20,
    max_chars=12000,
)
print(rows)
```

```text
ref,title,prices,url
n72,Item A,$19 | $17,https://example.com/a
```

#### Form-control value example

Use `value` for the current value of an input, textarea, or select; `text` reads rendered element
text, with an empty-text fallback to DOM text that may contain a textarea's initial content.

```python
controls = bu.read_all(
    "form input, form textarea, form select",
    fields=["tag", "name", "value"],
    limit=50,
)
print(controls)
```

```text
ref,tag,name,value
n81,input,email,ada@example.com
```

#### Article-export example

```python
article = bu.content_export(max_chars=6000)
print({
    "title": article["title"],
    "headings": article["headings"],
    "paragraphs": article["paragraphs"],
})
```

```python
{
    "title": "Guide",
    "headings": [{"level": 1, "text": "Guide"}],
    "paragraphs": ["..."],
}
```

#### Scoped content example

```python
articles = bu.extract_content(
    types=["heading", "paragraph", "link"],
    max_chars=6000,
    within=bu.css("article", match="all"),
)
print(articles)  # bounded Markdown in document order
print(articles[0])  # this block as heading/list/table/link-aware Markdown
print([
    {"scope": block.scope_ref, "type": block.type, "text": block.text}
    for block in articles
])
first_article = articles.blocks_for(0)

for block in articles:
    for link in block.links:
        print(link["text"], "→", link["href"])
```

`scope_refs[index]` identifies the region for blocks with that `scope_index`.

### Ref to CSS conversion

```python
def get_css_locator(ref: Ref, *, max_candidates: int = 8) -> CssLocatorList:
    """Generate unique CSS locators for one current-document ref.

    Args:
        ref: Fresh current-document element ref.
        max_candidates: Maximum candidates, from 1 to 16. Defaults to 8.

    Returns:
        CssLocatorList: Unique candidates in preference order. ``.first``
            is the primary locator or ``None`` when no unique candidate exists.
    """
    ...
```

Pass a returned locator directly to reads, actions, or scoped observations.

#### Usage example

```python
locators = bu.get_css_locator("n21", max_candidates=8)
if locators.first is not None:
    print(locators.first.selector)
```

An empty result means no unique CSS locator is available.
