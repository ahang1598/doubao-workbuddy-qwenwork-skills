# High-Concurrency Inventory Deduction Strategies

How to reserve/deduct ATP safely when many requests hit the same SKU at once.

## Problem

```text
A reads ATP=1; B reads ATP=1; both deduct → oversell
```

Also: hot SKUs, multi-channel writers, retry storms, sync lag.

## Layered Strategy

| Layer | Technique | Purpose |
|-------|-----------|---------|
| L0 | Idempotency keys | No double deduct on retry |
| L1 | Atomic check-and-deduct | No oversell |
| L2 | Sharding / buckets | Reduce hot-row contention |
| L3 | Rate limit / queue | Protect system |
| L4 | Pre-split for mega-sales | Extreme peaks |
| L5 | Reconcile + compensate | Final safety net |

## L0 — Idempotency (mandatory)

```text
key = order_id + line_id + action   # RESERVE | RELEASE | SHIP
```

Store first result; duplicates return the same outcome without re-applying stock deltas.

## L1 — Atomic deduct

### DB conditional update (default for moderate QPS)

```sql
UPDATE inventory
SET atp = atp - :qty,
    reserved = reserved + :qty
WHERE sku = :sku AND warehouse_id = :wh
  AND atp >= :qty;
-- rowcount 0 ⇒ fail
```

### Pessimistic row lock

`SELECT … FOR UPDATE` then update — simple, poor hot-SKU throughput.

### Redis atomic + async ledger (high QPS)

- Lua/DECRBY style: check + decr in one atomic step  
- On success, async write DB ledger  
- Requires recovery, replay, and reconciliation  

**Center rule:** judgment and deduct must be one atomic step (no TOCTOU).

## L2 — Hot-key scatter

**Buckets:** split ATP into N segments; hash order/user to a bucket; retry other buckets if empty while total ATP > 0.

**Channel quotas:** hard split per channel; rebalance periodically.

**Multi-warehouse rows:** natural scatter; publish aggregated ATP carefully.

## L3 — Admission control

- Per-SKU rate limits  
- sold_out cache to shed reads (must expire on restock)  
- Queue / token bucket for flash sales  
- Degrade non-critical channels under overload  

## L4 — Campaign inventory

Pre-allocate units into a campaign bucket → queue → atomic deduct from campaign pot → remainder returns to public ATP after event.

## Recommended combos

| Scale | Pattern |
|-------|---------|
| Normal multi-channel | DB conditional update + idempotency + async channel push |
| Hot SKUs | Redis atomic ATP + buckets + sold_out cache + DB ledger + reconcile |
| Flash sale | Pre-split campaign stock + queue + atomic campaign deduct |

## Consistency preference

- **Strong** reserve on shared-hub ATP when marketplace penalties are severe (e.g. Amazon MFN)  
- Channel *display* may lag seconds–minutes (eventual)  
- RELEASE path must be as atomic as RESERVE (avoid reserved leaks)

## Metrics

- Oversell count (~0)  
- Conflict / retry rate  
- P99 reserve latency on hot SKUs  
- TTL release on-time rate  
- ATP vs channel display gap  
- Ledger vs balance variance  

## Anti-patterns

- Read then write in two steps without lock/condition  
- Redis-only with no ledger  
- No idempotency  
- Single hot row under spike  
- Reserve without reliable RELEASE  
- Push channel qty before center commit  

## Principle

> Atomicity prevents oversell; idempotency prevents double hits; sharding carries QPS; TTL/release frees parks; reconciliation closes gaps.

See also: `inventory-reservation.md` (lifecycle), `multi-channel-inventory.md` (ATP).
