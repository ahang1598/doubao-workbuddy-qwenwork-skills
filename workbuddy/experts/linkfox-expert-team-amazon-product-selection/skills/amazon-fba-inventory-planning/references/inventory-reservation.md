# Inventory Reservation State Machine (预占状态机)

Execution-layer design for multi-channel shared pools (local / overseas hub / MFN).  
Pairs with ATP math (`multi-channel-inventory.md`) and concurrency controls (`inventory-concurrency.md`).

## Goals

- Lock stock quickly after demand is real enough to promise
- Auto-release unpaid / cancelled holds (TTL)
- Idempotent under retries
- Clear path through ship, shortage, and close

## States

| State | Meaning |
|-------|---------|
| **NONE** | No reservation |
| **RESERVED** | Hold placed; awaiting payment / confirmation |
| **COMMITTED** | Paid or accepted for fulfillment; picking eligible |
| **SHIPPED** | Shipped (full or handled at line level) |
| **RELEASED** | Hold released (timeout, cancel) |
| **SHORTAGE** | Cannot fulfill as reserved |
| **CLOSED** | Terminal |

### Main transitions

```text
NONE → RESERVED → COMMITTED → SHIPPED → CLOSED
              ↘ RELEASED → CLOSED
COMMITTED → SHORTAGE → RELEASED / CLOSED (after resolve)
```

## Event → Transition Table

| From | Event | To | Stock effect |
|------|-------|----|--------------|
| NONE | ReserveRequested (ATP OK) | RESERVED | ATP−, reserved+ |
| NONE | ReserveRequested (ATP short) | NONE | Reject |
| RESERVED | PaymentTimeout / BuyerCancel | RELEASED | ATP+, reserved− |
| RESERVED | PaymentCaptured / OrderConfirmed | COMMITTED | No qty change |
| COMMITTED | Shipped | SHIPPED | on_hand−, reserved− |
| COMMITTED | CancelBeforeShip | RELEASED | ATP+, reserved− |
| COMMITTED | PickShortage | SHORTAGE | Release unfulfilled qty to ATP; adjust on_hand if shrink |
| RESERVED | ExtendTTL | RESERVED | expires_at only |
| * | Duplicate event (same idempotency key) | unchanged | No double ledger |

## TTL (RESERVED only)

| Channel | Typical TTL |
|---------|-------------|
| DTC unpaid | 15–60 min |
| Marketplace pulled, unshipped | Until ship cutoff policy |
| Wholesale confirmed | Contract lock window |
| Peak / promo | Shorter TTL to reduce parking |

Scheduler: `status=RESERVED AND expires_at < now` → PaymentTimeout → RELEASED.

## Data (minimum)

**Reservation line:** reservation_id, order_id, line_id, sku, warehouse_id, qty, qty_shipped, qty_released, status, expires_at, channel, idempotency_key  

**Ledger:** sku, warehouse_id, delta_atp, delta_reserved, delta_on_hand, reason, ref_id, idempotency_key, ts  

## Partial ship

Track at line level:

```text
qty = qty_shipped + qty_open + qty_released
```

Ship only reduces open qty; remainder may stay COMMITTED or RELEASED on shortage cancel.

## Channel sync order

1. State change + ledger commit succeed  
2. Recompute ATP  
3. Apply channel buffers → publish qty  
4. Push channels (async retry on failure)  

Never push channel availability before center ledger commit.

## Reconciliation (daily)

- Open RESERVED/COMMITTED qty vs unshipped orders  
- Ledger sums vs balance sheet  
- Center ATP vs channel displayed qty (within tolerance)

## Principle

> RESERVED locks ATP; TTL prevents permanent parking; idempotency prevents double deduct; RELEASE/SHIP close the loop.
