# Lineage exploration

`inventory` / `explore-lineage` are **shortcuts**, not gates. Agents may always use `get` / `search` / `cat` / `get lineage` freely. Only hard ban: nested Bash loops enumerating every catalog/schema/table.

## When to draw a diagram

| Trigger | Command |
|---------|---------|
| Stocktake / handover / “how does data flow” | `explore-lineage --from-inventory --catalog <C> --format pipeline` |
| Upstream/downstream / impact | `explore-lineage` or `get lineage` |
| Layer architecture (ODS→DWD→DWS) | `--format pipeline` or `--format mermaid` |
| Deliverable report | paste `--format pipeline` or `--format mermaid` output |

**Order**: `inventory` (read `not_covered_by_default`) → `explore-lineage` → single-hop `get lineage` on hotspots.

## Formats

| `--format` | Output |
|------------|--------|
| `json` (default) | Edge graph; add `--include-sync` for sync match + `accuracy` |
| `mermaid` | Layered lineage diagram |
| `pipeline` | End-to-end diagram (sync enrichment on, tighter API caps) |

## Examples

```bash
wedatacli explore-lineage --from-inventory --catalog olist --format pipeline
wedatacli explore-lineage --from-inventory --catalog olist --format mermaid
wedatacli explore-lineage --catalog olist --schema olist_dwd --table dwd_order_detail_di --direction upstream --depth 2
wedatacli get lineage --catalog olist --schema olist_dwd --table dwd_order_detail_di -d INPUT
```

## Reading results

- `edges` / `nodes_by_layer` — table-to-table flow by warehouse layer
- `intake_paths` — cross-catalog upstream
- `zero_hop_notes` — often normal semantics (e.g. ODS `INPUT=0` = raw intake)
- `accuracy` / `gaps` — read before claiming completeness in reports

## Common pitfalls

1. ODS `INPUT=0` — check `intake_paths` or integration tasks, not a broken lineage API.
2. `*_dataset` vs `ods_*` — retry sibling `ods_*` table if OUTPUT is empty.
3. Depth capped at 2 — deeper graphs, ETL `ProcessName`, external-table pre-gate, or §2.14 governance table → `unity-catalog-manage` (`scripts/lineage.py`).
