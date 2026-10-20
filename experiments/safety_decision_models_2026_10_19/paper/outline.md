# Paper outline (Round 2 short empirical draft)

## Central claim (abstract only)

Under one pre-registered protocol, typed decision models and a managed guardrail sit on different miss, false-positive, and cost points; on JailbreakBench headline guardrail miss is mostly the category crosswalk, registered strength moves miss only 1.00 to 0.98 to 0.96 at FPR 0, and stacks help only where the guardrail still catches harm. Introduction states protocol boundaries; conclusion gives one deployment implication (do not restate the claim).

## Pre-registered vs post-hoc

| Item | Status |
|------|--------|
| Guardrail crosswalk (JBB → Prompt Attack only) | Pre-registered |
| Guardrail medium strength headlines | Pre-registered |
| Union / intersection / cascade (Jev + medium crosswalk) | Pre-registered |
| Jev/Clef thresholds on development pool | Pre-registered procedure |
| Any-filter max-band on JailbreakBench (cached bands) | **Post-hoc / exploratory sensitivity** |
| Post-hoc any-filter stacks at medium | **Post-hoc** (not refit) |

## Main text structure (`draft.tex`)

1. Abstract: claim + strength sweep; registered JBB vs exploratory any-filter CIs; harm/cost numbers.
2. Introduction: trade-off, families, gap; **pre-reg vs post-hoc boundary** (not claim clone); scope; run ids.
3. Related work, Systems, Datasets (claim sets vs appendix grid), Methods (bootstrap estimand note).
4. Results: JBB (**Fig. 1**), harm splits (**Fig. 2**), stacks + complementarity labels (**Fig. 3**), cost/latency + appendix figure names.
5. Discussion: crosswalk reporting rule, union when guardrail still blocks, one non-claim.
6. Limitations, Ethics, Conclusion (one implication).

**Main figures (three only):** `jbb_crosswalk.png`, `harm_splits.png`, `stack_frontier.png`. Cost scatter stays appendix (`cost_vs_miss.png`).

## Appendix scope

`tab:core-pack`, `tab:threshold-contrast`, thresholds/cascade, stacks/post-hoc tables, `tab:rq1-bootstrap` (distinct estimand), calibration, complementarity / operating_points / reliability / cost_vs_miss figures. **Removed:** duplicate `tab:core-pack-primary` longtable, `tab:figure-list` PNG inventory.

## Not compiled by `draft.tex`

`sections/stacking.tex`, `sections/sensitivity.tex`, `sections/latency.tex` (retained on disk; material largely in appendix).

## Numbers source

`RESULTS.md`, `outputs/figures/narrative_20261020/narrative_metrics.json`, `outputs/metrics/20261020T040920Z_90c5fd13.json`. Harness: `20261020T033822Z_0f24960e` PASS.
