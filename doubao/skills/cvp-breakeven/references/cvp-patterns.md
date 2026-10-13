# CVP Decision Patterns (worked)

## 1. Basic Breakeven With Target Profit
Price 500, variable 320, fixed 5,400,000. Contribution 180; CM ratio 36%.
- Breakeven = 30,000 units / 15,000,000 revenue.
- After-tax target 1,260,000 at 30% tax → pre-tax 1,800,000 → volume = (5,400,000+1,800,000)/180 = **40,000 units**.

## 2. Step Cost Trap
Same product, but each 10,000 units of capacity needs a supervisor (600,000).
Profit at 30,000 units with 3 supervisors: contribution 5,400,000 − fixed 5,400,000 − 1,800,000 = **−1,800,000 (loss!)** — the naive breakeven ignored the steps. Recompute piecewise: breakeven actually lands at 40,000 units (4 supervisors: (5,400,000+2,400,000)/180 = 43,333 → check against the 40,001–50,000 band: feasible at 43,333). Always test the breakeven against the step band it falls in.

## 3. Special Order
Capacity 100,000; running at 70,000. Export order: 15,000 units at 360 (below full cost of 410 = 320 var + 90 allocated fixed). Incremental freight 12/unit.
- Incremental contribution = (360 − 320 − 12) × 15,000 = **420,000 → accept**, since spare capacity and separable market.
- Same order at 95,000 utilization: displaces 10,000 regular units → opportunity cost 1,800,000 vs. order contribution 420,000 → **reject**.

## 4. Mix Shift Reality
Two products: A (contribution 200, 60% of mix), B (contribution 80, 40%). WACM = 152; fixed 3,040,000 → BE 20,000 total units.
Actual mix shifts to 40/60: WACM = 128 → BE rises to 23,750. Volume hit 21,000 — above old breakeven, below the new one → loss despite "beating breakeven." Track contribution-weighted volume, not raw units.

## 5. Operating Leverage Comparison
Two structures, same 1,000,000 profit at current volume:
- Automated: contribution 4,000,000, DOL 4.0
- Manual: contribution 1,600,000, DOL 1.6
Volume −15% → automated profit −60% (400,000); manual −24% (760,000). High fixed-cost structures are bets on volume; say so when proposing automation.

## 6. Price vs. Volume Sensitivity Asymmetry
At CM ratio 36%: a 5% price cut needs `5/(36−5) ≈ 16%` volume growth just to hold contribution. The generic discounting request almost never clears this bar — make sales prove the elasticity.
