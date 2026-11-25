# Evidence contract

## Delta dossier

```text
delta id:
mechanism:
state: EXPERIMENT_REQUIRED | ACCEPT | REJECT | RESTORE | REMEASURE

variant identity (one per side)
- revision/worktree and code hash:
- declared comparison axis:
- mutant derivation, if applicable:

controlled context (held equal except the declared axis)
- dependency/runtime:
- configuration and modes:
- input/seed and request or reader chunking:
- measurement boundary:
- reset/warmup:
- runner:
- sampling plan, valid/invalid policy, statistics and budget:

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
- same oracle: baseline pass / incorrect candidate fail / equivalent candidate pass:
- representative mutant or known-invalid counterexample must fail:
- diagnostic snapshots (separate from acceptance gate):

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

- Require equal controlled context except the declared comparison axis. Bind each artifact to its own side's revision and code hash; a mutant has its own derivation. Revisions need not equal across sides. Reject missing required comparison fields, even when both sides omit them.
- Preserve raw observations before derived summaries.
- Apply the same baseline-derived acceptance oracle to both implementations. A snapshot of a known defect can document it, but must not make that defect pass the equivalence gate or reject an equivalent repaired candidate. Mutant self-tests passing does not mean candidate acceptance.
- Reject normalization that erases a protected difference.
- State arithmetic and state transitions with literal operands and computed old/new relations.
- Restrict `ACCEPT` to the measured workload and boundary. Missing acceptance evidence requires `EVIDENCE_REQUIRED`; this does not prevent delivery of authorized tools or source-based rejection of a semantic defect.
