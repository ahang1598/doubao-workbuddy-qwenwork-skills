"""Shared wedatacli wrapper for unity-catalog-manage recipes."""

from __future__ import annotations

_RECIPE_NOTES = """
Shared wedatacli wrapper for unity-catalog-manage recipes.

Contract highlights (verified against l0-cli/wedatacli.sh):
  * `wedatacli.sh` is on PATH; overridable via env WEDATACLI_BIN.
  * WorkspaceId is auto-injected by the CLI itself (reads ~/.wedata/config.json
    or TENCENTCLOUD_WORKSPACE_ID and prints `[auto-inject] WorkspaceId="..."`
    on stderr). Recipes MUST NOT re-read the config file — that would
    duplicate CLI logic and drift when CLI switches config sources.
    Rule: pass `WorkspaceId` in payload ONLY when the caller explicitly wants
    to override the CLI default (e.g. cross-workspace probe); otherwise omit.
  * All List*/Search* Actions spill to /tmp/wedatacli-<Action>-<epoch>-<pid>.json
    when stdout > 16 KiB (WEDATA_MAX_STDOUT_BYTES). This wrapper handles
    both inline JSON and the spill envelope transparently.
  * stderr always contains `[Trace][WARN] ...` chatter; we drop it and
    parse stdout only.
  * `query-sql` uses `--sql` / `--sql-file`; SUCCESS response includes
    `CsvPath` — result rows live in the CSV, not the JSON.

Return contract: every helper returns already-parsed dict/list; on
non-recoverable CLI errors raises `WedataCliError` (never returns None or
half-parsed shapes — reduces retry-driven token burn).
"""


import csv
import json
import os
import re as _re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Iterable


class WedataCliError(RuntimeError):
    """Raised on non-recoverable CLI failure (non-zero rc or malformed JSON)."""

    def __init__(self, action: str, rc: int, stdout: str, stderr: str) -> None:
        self.action = action
        self.rc = rc
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(
            f"wedatacli {action} rc={rc}\n"
            f"stderr(tail)={stderr[-400:]}\n"
            f"stdout(head)={stdout[:400]}"
        )


def _bin() -> str:
    override = os.environ.get("WEDATACLI_BIN")
    if override:
        return override
    found = shutil.which("wedatacli.sh") or shutil.which("wedatacli")
    if found:
        return found
    # Fallback: source-tree sibling layout. Contract: `l0-cli/` is a sibling of
    # `scenarios/`. From this file (…/scenarios/data-development/skills/
    # unity-catalog-manage/scripts/common.py), five `..` reach that shared
    # parent, then descend into `l0-cli/wedatacli.sh`. Parent directory name
    # is not relied upon.
    here = os.path.dirname(os.path.abspath(__file__))
    fallback = os.path.normpath(os.path.join(here, "..", "..", "..", "..", "..", "l0-cli", "wedatacli.sh"))
    if os.path.exists(fallback):
        return fallback
    raise WedataCliError("bin-lookup", 127, "", "wedatacli.sh not on PATH")


def _run(argv: list[str], stdin_bytes: bytes | None = None) -> str:
    """Run wedatacli, return stdout as text. stderr is discarded (trace noise)."""
    proc = subprocess.run(
        argv,
        input=stdin_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    stdout = proc.stdout.decode("utf-8", errors="replace")
    stderr = proc.stderr.decode("utf-8", errors="replace")
    if proc.returncode != 0:
        raise WedataCliError(argv[1] if len(argv) > 1 else "?", proc.returncode, stdout, stderr)
    return stdout


def _load_json_or_spill(raw: str) -> Any:
    """Handle both inline JSON and the {truncated,file,...} spill envelope.

    Never `read_file`s the raw file — instead loads it with `json.load` locally
    (still one whole-file read, but keeps LLM context clean).
    """
    raw = raw.strip()
    if not raw:
        raise WedataCliError("parse", 0, raw, "empty stdout")
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        raise WedataCliError("parse", 0, raw, f"json decode: {e}") from None
    if isinstance(obj, dict) and obj.get("truncated") and obj.get("file"):
        with open(obj["file"], "r", encoding="utf-8") as fp:
            obj = json.load(fp)
    return obj


def call_action(action: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Invoke a Wedata Action (e.g. ListLineages), return parsed Response.Data.

    Contracts:
      * payload is passed as a single positional JSON string.
      * Auto-handles spill.
      * Raises WedataCliError on CLI-level failure; caller checks Response.Error
        for business-level failure inside the returned envelope.
    """
    raw = _run([_bin(), action, json.dumps(payload, ensure_ascii=False)])
    envelope = _load_json_or_spill(raw)
    if not isinstance(envelope, dict):
        raise WedataCliError(action, 0, raw, f"unexpected envelope type {type(envelope)}")
    response = envelope.get("Response") if "Response" in envelope else envelope
    return response or {}


def get_tables(catalog: str, schema: str, keyword: str | None = None) -> list[str]:
    """`wedatacli get tables --catalog C --schema S` → list of table names.

    Uses the friendly `get tables` subcommand (backed by ListTableNames) which
    is materially cheaper than a raw `ListTables` for name-only inventory.
    """
    argv = [_bin(), "get", "tables", "--catalog", catalog, "--schema", schema]
    if keyword:
        argv += ["--keyword", keyword]
    raw = _run(argv)
    obj = _load_json_or_spill(raw) if raw.lstrip().startswith(("{", "[")) else None
    if isinstance(obj, dict):
        # `get tables` returns lowercase keys: {resource, catalog, schema, total, items:[{name,uri}]}
        # Fall back to CamelCase in case a future version aligns with Action shape.
        items = (
            obj.get("items")
            or obj.get("Items")
            or (obj.get("Data") or {}).get("Items")
            or []
        )
        names: list[str] = []
        for it in items:
            n = it.get("name") or it.get("Name")
            if n:
                names.append(n)
        return names
    # Text mode fallback: one name per non-empty, non-header line.
    names = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "NAME", "Name", "Catalog")):
            continue
        if line.startswith("[Trace]"):
            continue
        # First whitespace-separated token is the table name.
        names.append(line.split()[0])
    return names


@dataclass
class QuerySqlResult:
    status: str
    task_id: str | None
    csv_path: str | None
    schema: list[dict[str, str]]
    cost_ms: int | None
    message: str | None

    def rows(self, limit: int | None = None) -> list[dict[str, str]]:
        if not self.csv_path or not os.path.exists(self.csv_path):
            return []
        out: list[dict[str, str]] = []
        with open(self.csv_path, "r", encoding="utf-8", newline="") as fp:
            reader = csv.DictReader(fp)
            for i, row in enumerate(reader):
                if limit is not None and i >= limit:
                    break
                out.append(row)
        return out


def query_sql(sql: str, timeout: str = "5m") -> QuerySqlResult:
    """`wedatacli query-sql --sql "<SQL>" --output json`.

    Runs the SQL through dataclaw-tool-server (sql.query) and returns a
    QuerySqlResult with CsvPath and Schema populated. `rows()` reads the CSV
    on demand.
    """
    raw = _run(
        [
            _bin(),
            "query-sql",
            "--sql",
            sql,
            "--output",
            "json",
            "--no-progress",
            "--timeout",
            timeout,
        ]
    )
    obj = _load_json_or_spill(raw)
    if not isinstance(obj, dict):
        raise WedataCliError("query-sql", 0, raw, f"unexpected envelope type {type(obj)}")
    return QuerySqlResult(
        status=obj.get("Status") or "",
        task_id=obj.get("TaskId"),
        csv_path=obj.get("CsvPath"),
        schema=obj.get("Schema") or [],
        cost_ms=obj.get("CostMs"),
        message=obj.get("Message"),
    )


def chunked(seq: Iterable[Any], size: int) -> Iterable[list[Any]]:
    buf: list[Any] = []
    for x in seq:
        buf.append(x)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf


# ---------------------------------------------------------------------------
# Domain primitives (shared across recipes)
#
# These wrap the most-hallucinated Actions with their real contract locked
# down. Every caller in this package should prefer these over hand-rolling
# `call_action(...)` payloads — that's how we prevent contract drift from
# leaking into individual recipes.
#
# WorkspaceId policy: the CLI auto-injects it, so all helpers below leave
# WorkspaceId out of the payload by default. Callers pass `workspace_id`
# only when they explicitly need to override the CLI default (cross-workspace
# probes, multi-tenant tooling, etc.). This keeps recipes robust when the
# CLI later switches config sources (env vars, IAM, cloud metadata, ...).
# ---------------------------------------------------------------------------


def get_table(
    catalog: str,
    schema: str,
    table: str,
    workspace_id: str | None = None,
    fetch_option: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """`GetTable` -> returns the inner `Table` object (unwraps the extra layer).

    Contract (contract-verified against the runtime CLI):
      * Primary key is the 4-tuple {WorkspaceId, CatalogName, SchemaName,
        TableName}. WorkspaceId is auto-injected by the CLI, so callers pass
        catalog/schema/table only. AssetGuid / FullName are NOT accepted.
      * Response structure is `Response.Data.Table.*` (extra nesting). This
        helper unwraps it so callers see {Name, Comment, Columns, ...}
        directly.
      * Returns {} when the response is empty; raises WedataCliError for
        CLI-level failure or business Error.
    """
    payload: dict[str, Any] = {
        "CatalogName": catalog,
        "SchemaName": schema,
        "TableName": table,
    }
    if workspace_id:
        payload["WorkspaceId"] = str(workspace_id)
    if fetch_option:
        payload["FetchOption"] = fetch_option
    response = call_action("GetTable", payload)
    error = response.get("Error")
    if error:
        raise WedataCliError(
            "GetTable",
            0,
            json.dumps(response, ensure_ascii=False)[:400],
            error.get("Message") or json.dumps(error),
        )
    data = response.get("Data") or {}
    return data.get("Table") or {}


def search_asset(
    keyword: str,
    workspace_id: str | None = None,
    asset_types: list[str] | None = None,
    max_results: int = 20,
    next_page_token: str | None = None,
) -> dict[str, Any]:
    """`SearchAsset` with contract firewall.

    Contract (verified):
      * WorkspaceId is auto-injected by the CLI as a STRING; callers should
        NOT pass it unless overriding the default. If the caller does pass
        `workspace_id`, we cast to str() to avoid the numeric-unmarshal trap
        (`json: cannot unmarshal number into Go struct field
        SearchAssetRequest.WorkspaceId of type string`).
      * `TotalCount` is always null; use NextPageToken to know if more.
      * MaxResults hard-capped at 100 server-side.
      * `AssetTypes` optional filter, e.g. ["TABLE"], ["VIEW","MODEL"].

    Returns Data unwrapped: {"Items": [...], "NextPageToken": "..."}.
    """
    if max_results < 1 or max_results > 100:
        raise ValueError("SearchAsset MaxResults must be within [1, 100]")
    payload: dict[str, Any] = {
        "Keyword": keyword,
        "MaxResults": int(max_results),
    }
    if workspace_id:
        payload["WorkspaceId"] = str(workspace_id)
    if asset_types:
        payload["AssetTypes"] = asset_types
    if next_page_token:
        payload["NextPageToken"] = next_page_token
    response = call_action("SearchAsset", payload)
    error = response.get("Error")
    if error:
        raise WedataCliError(
            "SearchAsset",
            0,
            json.dumps(response, ensure_ascii=False)[:400],
            error.get("Message") or json.dumps(error),
        )
    data = response.get("Data") or {}
    return {
        "Items": data.get("Items") or [],
        "NextPageToken": data.get("NextPageToken") or "",
    }


def list_labels(
    workspace_id: str | None = None,
    keyword: str | None = None,
    label_types: list[int] | None = None,
    page_size: int = 50,
    max_pages: int = 20,
    shared: bool = True,
) -> dict[str, Any]:
    """`ListLabels` -- paginated dump with contract firewall.

    Contract (verified):
      * Pagination is nested: `Page:{PageNumber,PageSize}`, NOT top-level.
      * Response items are under `Data.Labels` (NOT `Data.Items`).
      * Always pass `Shared=true` per SKILL section 2.11 (workspace-visible tags).
      * `KeyWord` is spelled with capital K AND W (matches --describe).
      * `Types` is an int array: 1 business / 2 category / 3 BI / 4 masking / ...
      * WorkspaceId is auto-injected by the CLI; caller passes `workspace_id`
        only for explicit cross-workspace override.

    Returns aggregated {"TotalCount": int, "Labels": [ ... ]}.
    """
    payload_base: dict[str, Any] = {"Shared": bool(shared)}
    if workspace_id:
        payload_base["WorkspaceId"] = str(workspace_id)
    if keyword:
        payload_base["KeyWord"] = keyword
    if label_types:
        payload_base["Types"] = list(label_types)

    labels: list[dict[str, Any]] = []
    total = 0
    for page in range(1, max_pages + 1):
        payload = dict(payload_base)
        payload["Page"] = {"PageNumber": page, "PageSize": page_size}
        response = call_action("ListLabels", payload)
        error = response.get("Error")
        if error:
            raise WedataCliError(
                "ListLabels",
                0,
                json.dumps(response, ensure_ascii=False)[:400],
                error.get("Message") or json.dumps(error),
            )
        data = response.get("Data") or {}
        chunk = data.get("Labels") or []
        total = data.get("TotalCount", total) or total
        labels.extend(chunk)
        if not chunk or len(chunk) < page_size:
            break
    return {"TotalCount": total or len(labels), "Labels": labels}


# ---------------------------------------------------------------------------
# Linked-catalog (external-table) detection
#
# The Linked-Catalog gate is driven by the TARGET TABLE's owning catalog.
# It is triggered ONLY by two user-facing entrypoints:
#   * AI metadata completion (`GetCommentCompletion` +
#     `UpdateTableComment` / `UpdateTableColumnComment` /
#     `UpdateTableColumnsComment`) — SKILL.md §2.12.
#   * Table lineage (`ListLineages` / `scripts/lineage.py`) — SKILL.md §2.14.
#
# Resolution source (verified 2026-08-19, four-form real-env test):
#   `wedatacli get catalogs` (lowercase list) → per-item `source` field.
#     - source == "CONNECTION"  → Linked Catalog (直连)      → REFUSE
#     - source == "METALAKE"    → internal managed catalog  → PROCEED
#   This is the ONLY authoritative signal. The following paths are BANNED
#   because they all fail on Linked Catalogs in real env:
#     * `GetCatalog` Action (PascalCase) / `wedatacli get catalog --name`
#       → `CatalogNotFound` for Linked Catalogs; not usable.
#     * `wedatacli get catalog` (positional singular)
#       → `unknown or unexpected argument`; resource does not exist.
#     * `search table --verbose` field `connection_id`
#       → also populated for METALAKE tables (points at the ingestion
#         connection, not the catalog kind); unreliable.
#
# All other unity-catalog paths remain safe (SearchAsset / favorites /
# audit SQL / labels / tags / owner / cold-table inventory / ListTables /
# GetTable read paths do NOT short-circuit).
# ---------------------------------------------------------------------------


def list_catalogs(workspace_id: str | None = None) -> dict[str, str]:
    """`wedatacli get catalogs` → `{catalog_name: source}` (source in {CONNECTION, METALAKE, ...}).

    `source` is the authoritative Linked-Catalog signal (see module header).
    Raises WedataCliError if the CLI call fails; returns {} only when the
    CLI legitimately reports zero catalogs.
    """
    argv = [_bin(), "get", "catalogs"]
    raw = _run(argv)
    obj = _load_json_or_spill(raw) if raw.lstrip().startswith(("{", "[")) else None
    items: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        items = (
            obj.get("items")
            or obj.get("Items")
            or (obj.get("Data") or {}).get("Items")
            or []
        )
    elif isinstance(obj, list):
        items = obj
    out: dict[str, str] = {}
    for it in items:
        name = it.get("name") or it.get("Name") or it.get("CatalogName")
        src = it.get("source") or it.get("Source") or ""
        if name:
            out[str(name)] = str(src).upper()
    return out


def is_linked_catalog(
    catalog: str,
    workspace_id: str | None = None,
) -> dict[str, Any]:
    """Return `{linked, source, CatalogName}` for the given catalog.

    `linked=True` iff `list_catalogs()[catalog] == "CONNECTION"`. If the
    catalog is not present in `get catalogs`, raise WedataCliError — the
    caller MUST NOT proceed as `linked=False` (would silently bypass the
    gate on typos). Field naming: `source` is lowercase to match the
    `get catalogs` CLI output and `list_catalogs()`; `CatalogName` stays
    PascalCase to match the underlying Action field. Callers handle the
    refusal one-liner per entrypoint:
      * §2.12 AI metadata completion:
        `⚠ 外部表暂不支持智能元数据补齐能力（Linked Catalog: <CatalogName>）。`
      * §2.14 table lineage:
        `⚠ 外部表暂不支持表血缘分析能力（Linked Catalog: <CatalogName>）。`
    """
    catalogs = list_catalogs(workspace_id=workspace_id)
    if catalog not in catalogs:
        raise WedataCliError(
            "get catalogs",
            0,
            json.dumps(sorted(catalogs.keys())[:20], ensure_ascii=False),
            f"catalog {catalog!r} not found in workspace catalog list",
        )
    source = catalogs[catalog]
    # Field naming: `source` matches the lowercase key emitted by `get
    # catalogs` (and by `list_catalogs()`); `CatalogName` stays PascalCase to
    # match the underlying Action field. Consumers should read `source`.
    return {
        "linked": source == "CONNECTION",
        "source": source,
        "CatalogName": catalog,
    }


_ALLOWED_SEARCH_MODES = {"hybrid", "exact", "semantic"}


def _search_table_verbose(
    keyword: str, schema: str | None = None, mode: str = "hybrid"
) -> list[dict[str, Any]]:
    """`wedatacli search table <keyword> [--schema S] --mode <M> --verbose` → hit list.

    `mode` follows the CLI's own `search table --mode {hybrid|exact|semantic}`
    flag (verified 2026-08-19). Callers pass `mode="semantic"` for natural-
    language phrases (form ④) so the recall path is correct; default `hybrid`
    covers 2-part and single-name inputs (forms ②③). Each returned hit
    exposes `fields.catalog` and `fields.full_table_name`, which is what
    `resolve_and_pregate` uses to derive the owning catalog.
    """
    if mode not in _ALLOWED_SEARCH_MODES:
        raise ValueError(f"mode must be one of {sorted(_ALLOWED_SEARCH_MODES)}")
    argv = [_bin(), "search", "table", keyword, "--mode", mode, "--verbose"]
    if schema:
        argv += ["--schema", schema]
    raw = _run(argv)
    obj = _load_json_or_spill(raw) if raw.lstrip().startswith(("{", "[")) else None
    if isinstance(obj, dict):
        return obj.get("hits") or obj.get("Hits") or obj.get("items") or obj.get("Items") or []
    if isinstance(obj, list):
        return obj
    return []


def search_table_candidates(
    keyword: str,
    schema: str | None = None,
    mode: str = "hybrid",
    limit: int = 5,
) -> list[dict[str, str]]:
    """Return `[{catalog, full_table_name}]` slim candidates for non-3-part input.

    Wraps `_search_table_verbose`; used by `resolve_and_pregate` to feed the
    catalog-driven pre-gate. `mode` is passed through so semantic phrases
    (form ④) can request `--mode semantic` explicitly rather than relying
    on the hybrid default.
    """
    hits = _search_table_verbose(keyword, schema=schema, mode=mode)
    out: list[dict[str, str]] = []
    for h in hits:
        fields = h.get("fields") or h.get("Fields") or {}
        cat = fields.get("catalog") or fields.get("Catalog") or ""
        full = fields.get("full_table_name") or fields.get("FullTableName") or ""
        if cat and full:
            out.append({"catalog": str(cat), "full_table_name": str(full)})
            if len(out) >= limit:
                break
    return out


def _looks_semantic(user_input: str) -> bool:
    """Heuristic: treat input as a natural-language phrase (form ④).

    An identifier-shaped single-segment input (letters/digits/underscore/hyphen)
    is form ③ (single table name). Anything else — whitespace, CJK
    characters, punctuation like `?`/`？` — is form ④ semantic. Callers may
    override by passing `mode=` to `resolve_and_pregate` explicitly.
    """
    if not user_input:
        return False
    return _re.search(r"[^0-9A-Za-z_\-]", user_input) is not None


def resolve_and_pregate(
    user_input: str,
    workspace_id: str | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    """Four-form unified entry: input → FQN resolution → Linked-Catalog verdict.

    Handles the four real-env forms verified 2026-08-19:
      ① 3-part `catalog.schema.table` → take catalog directly (zero probes).
      ② 2-part `schema.table`         → `search table T --schema S --mode hybrid --verbose`.
      ③ single identifier `table`     → `search table T --mode hybrid --verbose`.
      ④ semantic phrase               → `search table "<phrase>" --mode semantic --verbose`.

    Form ③ vs ④ distinction: if the caller passes `mode` explicitly
    (`"hybrid"|"exact"|"semantic"`), that wins. Otherwise the heuristic in
    `_looks_semantic()` classifies any non-3-part input containing whitespace
    / CJK / punctuation as ④ (semantic → `--mode semantic`), and pure
    identifier-shape single tokens as ③ (→ `--mode hybrid`). Recipes and
    main-agent callers should pass `mode=` when they already know which
    form the user gave; the heuristic is only a fallback.

    Returns:
      `{verdict, candidates, catalogs, refusal?}`
      * `verdict` ∈ {"proceed", "refuse", "ambiguous", "not_found"}.
      * `candidates`: list of `{catalog, full_table_name, source}` (empty
        for form ①).
      * `catalogs`: `{catalog: source}` snapshot used for the decision.
      * `refusal`: preformatted one-liner (only when `verdict=="refuse"`);
        caller substitutes the entrypoint-specific verb.

    Decision matrix (7 cases covered):
      | Form | Distinct catalogs of candidates | Verdict |
      | 3-part | (single, known)     | METALAKE→proceed / CONNECTION→refuse / not-in-list→not_found |
      | non-3  | all CONNECTION      | refuse (safe reject; single-line) |
      | non-3  | all METALAKE (1 cat)| proceed (single unambiguous internal target) |
      | non-3  | all METALAKE (>1)   | ambiguous (list candidates, ask user to pick) |
      | non-3  | mixed CONNECTION/METALAKE | ambiguous (list only METALAKE candidates) |
      | non-3  | zero hits           | not_found (ask user for missing segment) |
    """
    catalogs = list_catalogs(workspace_id=workspace_id)
    parts = user_input.split(".") if user_input else []

    # Form ① — 3-part FQN.
    if len(parts) == 3 and all(parts):
        cat = parts[0]
        if cat not in catalogs:
            return {
                "verdict": "not_found",
                "candidates": [],
                "catalogs": catalogs,
            }
        src = catalogs[cat]
        if src == "CONNECTION":
            return {
                "verdict": "refuse",
                "candidates": [{"catalog": cat, "full_table_name": user_input, "source": src}],
                "catalogs": catalogs,
                "refusal": f"⚠ 外部表暂不支持该能力（Linked Catalog: {cat}）。",
            }
        return {
            "verdict": "proceed",
            "candidates": [{"catalog": cat, "full_table_name": user_input, "source": src}],
            "catalogs": catalogs,
        }

    # Forms ②③④ — search-driven resolution. Resolve mode:
    #   * explicit `mode` from the caller wins;
    #   * form ② always uses hybrid (schema+table);
    #   * for ③ vs ④, fall back to `_looks_semantic` heuristic.
    if mode is not None:
        resolved_mode = mode
    elif len(parts) == 2 and all(parts):
        resolved_mode = "hybrid"
    else:
        resolved_mode = "semantic" if _looks_semantic(user_input) else "hybrid"

    if len(parts) == 2 and all(parts):
        hits = search_table_candidates(parts[1], schema=parts[0], mode=resolved_mode)
    else:
        hits = search_table_candidates(user_input, mode=resolved_mode)

    if not hits:
        return {"verdict": "not_found", "candidates": [], "catalogs": catalogs}

    enriched: list[dict[str, str]] = []
    for h in hits:
        src = catalogs.get(h["catalog"], "")
        enriched.append({**h, "source": src})

    internal = [h for h in enriched if h["source"] == "METALAKE"]
    external = [h for h in enriched if h["source"] == "CONNECTION"]

    if internal and external:
        # Mixed: surface only the internal candidates for user pick.
        return {"verdict": "ambiguous", "candidates": internal, "catalogs": catalogs}
    if external and not internal:
        cat_names = sorted({h["catalog"] for h in external})
        return {
            "verdict": "refuse",
            "candidates": external,
            "catalogs": catalogs,
            "refusal": f"⚠ 外部表暂不支持该能力（Linked Catalog: {', '.join(cat_names)}）。",
        }
    # All METALAKE: single-catalog single-table → proceed; otherwise ambiguous.
    unique = {h["full_table_name"] for h in internal}
    if len(unique) == 1:
        return {"verdict": "proceed", "candidates": internal[:1], "catalogs": catalogs}
    return {"verdict": "ambiguous", "candidates": internal, "catalogs": catalogs}



