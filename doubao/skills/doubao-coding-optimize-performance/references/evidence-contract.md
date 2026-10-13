# Evidence contract

## Delta dossier

```text
delta id:
mechanism:
state: EXPERIMENT_REQUIRED | ACCEPT | REJECT | RESTORE | REMEASURE

fingerprint
- revision/worktree:
- dependency/runtime:
- configuration and modes:
- input/seed and request or reader chunking:
- measurement boundary:
- reset/warmup:
- runner:
- single changed variable:

source basis
- entry/callers:
- literal state transitions:
- owner and evidence type:
- selected versus adjacent implementation:

protected semantics
- content/cardinality/order/duplicates:
- identity/aliasing/mutability:
- time/visibility/side effects:
- empty/unknown:
- error/partial/recovery:
- configured output and metadata:

oracle integrity
- baseline characterization command + raw artifact + result:
- minimum counterexample:
- deliberate mutant:
- mutant must fail:

measurement
- workload × configuration matrix:
- alternating pair command and raw samples:
- preregistered thresholds and source:
- profile attribution artifact:

verdict
- semantic result:
- measurement result:
- proven scope:
- revoke/restore condition:
```

## Integrity rules

- Require exact fingerprint equality across baseline characterization, semantic oracle, mutant, and paired measurement.
- Preserve raw observations before derived summaries.
- Treat a test of the candidate's desired behavior as a candidate test, not a baseline oracle.
- Reject normalization that erases a protected difference.
- State arithmetic and state transitions with literal operands and computed old/new relations.
- Restrict `ACCEPT` to the measured workload and boundary. Use `EVIDENCE_REQUIRED` when any ticket is absent.
