#!/usr/bin/env python3
"""Field-aware three-stage genetic search for PandaAI native formulas."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from pathlib import Path
from typing import Any

from pandaai_field_catalog import DEFAULT_FIELDS, NAME_RE
from pandaai_quant_operators import validate as validate_expression
from pandaai_quant_operators import wrap as wrap_operator


WINDOWS = (3, 5, 10, 20, 40, 60, 120)
FAMILIES = ("raw", "signed_power", "ratio", "spread", "product")
PAIR_FAMILIES = {"ratio", "spread", "product"}
TS_OPS = ("DELTA", "TS_MEAN", "STDDEV", "TS_MIN", "TS_MAX", "TS_RANK",
          "TS_ZSCORE", "DECAYLINEAR", "SLOPE")
CS_OPS = ("RANK", "SCALE", "ZSCORE")


def canonical(expression: str) -> str:
    return "".join(expression.lower().split())


def expression_hash(expression: str) -> str:
    return hashlib.sha256(canonical(expression).encode()).hexdigest()


def candidate_id(expression: str, direction: int) -> str:
    return hashlib.sha256(f"{canonical(expression)}|{direction}".encode()).hexdigest()[:12]


def load_fields(catalog: Path | None, direct: str | None) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    if catalog:
        data = json.loads(catalog.read_text(encoding="utf-8-sig"))
        fields.extend(data.get("fields", data) if isinstance(data, dict) else data)
    if direct:
        fields.extend({"name": x.strip(), "category": "direct", "type": "unknown",
                       "description": "", "source": "direct"} for x in direct.split(","))
    if not fields:
        fields.extend(DEFAULT_FIELDS)
    output, seen = [], set()
    for item in fields:
        name = str(item.get("name", "")).strip()
        if not NAME_RE.fullmatch(name) or name.lower() in seen:
            continue
        dtype = str(item.get("type", "unknown")).lower()
        if dtype not in {"double", "float", "number", "numeric", "int", "integer", "unknown"}:
            continue
        seen.add(name.lower())
        output.append({"name": name, "category": str(item.get("category", "uncategorized")),
                       "type": dtype, "description": str(item.get("description", "")),
                       "source": str(item.get("source", "catalog"))})
    if not output:
        raise ValueError("field pool is empty after validation")
    return output


def normalize(genome: dict[str, Any], field_names: list[str], rng: random.Random) -> dict[str, Any]:
    genome["stage"] = int(genome["stage"])
    if genome["field"] not in field_names:
        genome["field"] = rng.choice(field_names)
    if genome["family"] in PAIR_FAMILIES:
        choices = [x for x in field_names if x != genome["field"]]
        genome["other_field"] = genome.get("other_field") if genome.get("other_field") in choices else (rng.choice(choices) if choices else genome["field"])
    else:
        genome["other_field"] = None
    if genome["stage"] == 1:
        genome.update(ts_op="none", cs_op="none")
    elif genome["stage"] == 2:
        genome["ts_op"] = genome.get("ts_op") if genome.get("ts_op") in TS_OPS else rng.choice(TS_OPS)
        genome["cs_op"] = "none"
    else:
        genome["ts_op"] = genome.get("ts_op") if genome.get("ts_op") in TS_OPS else rng.choice(TS_OPS)
        genome["cs_op"] = genome.get("cs_op") if genome.get("cs_op") in CS_OPS else rng.choice(CS_OPS)
    genome["window"] = int(genome.get("window") or rng.choice(WINDOWS))
    genome["direction"] = int(genome.get("direction", rng.choice((0, 1))))
    return genome


def random_genome(rng: random.Random, stage: int, fields: list[dict[str, Any]]) -> dict[str, Any]:
    names = [x["name"] for x in fields]
    categories = sorted({x["category"] for x in fields})
    category = rng.choice(categories)
    candidates = [x["name"] for x in fields if x["category"] == category]
    return normalize({"stage": stage, "family": rng.choice(FAMILIES),
                      "field": rng.choice(candidates), "other_field": rng.choice(names),
                      "window": rng.choice(WINDOWS), "ts_op": "none", "cs_op": "none",
                      "direction": rng.choice((0, 1))}, names, rng)


def render(genome: dict[str, Any]) -> str:
    x, y, family = genome["field"], genome.get("other_field"), genome["family"]
    base = {"raw": x, "signed_power": f"SIGNEDPOWER({x},0.5)",
            "ratio": f"({x})/(ABS({y})+0.000001)", "spread": f"({x})-({y})",
            "product": f"({x})*({y})"}[family]
    if genome["stage"] >= 2:
        base = wrap_operator(genome["ts_op"], base, window=genome["window"])
    if genome["stage"] >= 3:
        base = wrap_operator(genome["cs_op"], base)
    check = validate_expression(base)
    if not check["valid"]:
        raise ValueError(f"invalid generated expression: {check}")
    return base


def fitness(metrics: dict[str, Any]) -> float:
    def number(*names: str) -> float:
        for name in names:
            value = metrics.get(name)
            if isinstance(value, (int, float)) and math.isfinite(value):
                return float(value)
        return 0.0
    return round(4*abs(number("IC_mean", "ic_mean")) + 3*abs(number("Rank_IC", "rank_ic"))
                 + abs(number("IC_IR", "ic_ir")) + max(0, number("monotonicity", "单调性"))
                 + 0.15*max(-3, min(3, number("sharpe", "Sharpe", "夏普比率")))
                 - 0.5*abs(number("max_drawdown", "最大回撤"))
                 - 0.25*max(0, min(1, number("p_value", "p-value"))), 8)


def record(genome: dict[str, Any], generation: int, meta: dict[str, dict[str, Any]]) -> dict[str, Any]:
    formula = render(genome)
    used = [genome["field"]] + ([genome["other_field"]] if genome.get("other_field") else [])
    return {"schema_version": 2, "candidate_id": candidate_id(formula, genome["direction"]),
            "expression_hash": expression_hash(formula), "generation": generation,
            "stage": genome["stage"], "genome": genome, "family": genome["family"],
            "fields": [{k: meta[name].get(k) for k in ("name", "category", "type", "description", "source")} for name in used],
            "factor_direction": genome["direction"], "formula": formula,
            "status": "proposed", "metrics": {}, "fitness": None}


def read_ledger(path: Path | None) -> list[dict[str, Any]]:
    if not path or not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def scored(records: list[dict[str, Any]], stage: int) -> list[dict[str, Any]]:
    rows = [x for x in records if x.get("schema_version") == 2 and x.get("stage") == stage and x.get("metrics")]
    for item in rows:
        item["fitness"] = fitness(item["metrics"])
    return sorted(rows, key=lambda x: x["fitness"], reverse=True)


def mutate(genome: dict[str, Any], rng: random.Random, fields: list[dict[str, Any]], rate: float) -> dict[str, Any]:
    child, names = dict(genome), [x["name"] for x in fields]
    options = {"family": FAMILIES, "field": names, "other_field": names,
               "window": WINDOWS, "ts_op": TS_OPS, "cs_op": CS_OPS, "direction": (0, 1)}
    keys = ["family", "field", "other_field", "window", "direction"]
    if child["stage"] >= 2: keys.append("ts_op")
    if child["stage"] >= 3: keys.append("cs_op")
    for key in keys:
        if rng.random() < rate:
            child[key] = rng.choice(options[key])
    return normalize(child, names, rng)


def crossover(a: dict[str, Any], b: dict[str, Any], stage: int, rng: random.Random,
              fields: list[dict[str, Any]]) -> dict[str, Any]:
    keys = ("family", "field", "other_field", "window", "ts_op", "cs_op", "direction")
    return normalize({"stage": stage, **{key: rng.choice((a.get(key), b.get(key))) for key in keys}},
                     [x["name"] for x in fields], rng)


def generate(args: argparse.Namespace, fields: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rng, previous = random.Random(args.seed), read_ledger(args.ledger)
    meta = {x["name"]: x for x in fields}
    seen = {x.get("expression_hash") for x in previous}
    parents = scored(previous, args.parent_stage or args.stage)
    if args.stage > 1 and not parents:
        raise ValueError(f"stage {args.stage} requires a scored stage-{args.parent_stage or args.stage} ledger")
    genomes: list[dict[str, Any]] = []
    if parents:
        elites = [x["genome"] for x in parents[:max(2, min(args.elites, len(parents)))]]
        for elite in elites:
            genomes.append(normalize({**elite, "stage": args.stage}, list(meta), rng))
        while len(genomes) < args.population * 10:
            genomes.append(mutate(crossover(rng.choice(elites), rng.choice(elites), args.stage, rng, fields), rng, fields, args.mutation_rate))
    else:
        genomes = [random_genome(rng, 1, fields) for _ in range(args.population * 30)]
    output, dropped = [], 0
    for genome in genomes:
        item = record(genome, args.generation, meta)
        if item["expression_hash"] in seen:
            dropped += 1; continue
        seen.add(item["expression_hash"]); output.append(item)
        if len(output) == args.population: break
    if len(output) < args.population:
        raise RuntimeError(f"could generate only {len(output)}/{args.population} unique candidates")
    categories = {f["category"] for item in output for f in item["fields"]}
    return output, {"unique_candidates": len(output), "duplicates_dropped": dropped,
                    "field_pool_size": len(fields), "field_categories_used": sorted(categories),
                    "families": sorted({x["family"] for x in output})}


def main() -> None:
    parser = argparse.ArgumentParser(description="Field-aware three-stage PandaAI genetic miner")
    parser.add_argument("--stage", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument("--population", type=int, default=8)
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--field-catalog", type=Path)
    parser.add_argument("--fields", help="Comma-separated direct field names")
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--parent-stage", type=int, choices=(1, 2, 3))
    parser.add_argument("--elites", type=int, default=4)
    parser.add_argument("--mutation-rate", type=float, default=0.25)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 1 <= args.population <= 100: parser.error("--population must be 1..100")
    if not 0 <= args.mutation_rate <= 1: parser.error("--mutation-rate must be 0..1")
    population, audit = generate(args, load_fields(args.field_catalog, args.fields))
    rendered = json.dumps({"engine": "field-aware-three-stage-genetic", "stage": args.stage,
                           "generation": args.generation, "audit": audit,
                           "population": population}, ensure_ascii=False, indent=2) + "\n"
    if args.output: args.output.write_text(rendered, encoding="utf-8")
    else: print(rendered, end="")


if __name__ == "__main__":
    main()
