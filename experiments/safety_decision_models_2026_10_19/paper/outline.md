# Paper outline (short empirical draft)

## Central claim (abstract + introduction)

Under one pre-registered protocol, typed decision models and a managed guardrail sit on different miss–false-positive–cost points; on JailbreakBench the guardrail's headline miss is mostly the category crosswalk, not the strength setting; stacks help only where that guardrail still catches harm.

## Section order (`draft.tex`)

1. **Abstract** — central claim; harness + core pack run ids; JBB crosswalk vs post-hoc any-filter; harm split headline; cost/latency one line.
2. **Introduction** — screening trade-off; two families; prior-work gap; central claim (bold); scope (no downstream chat); harness sentence; pointer to sections.
3. **Related work** — one short section (benchmarks, Jev harness, Clef, guardrails, calibration).
4. **Systems** — four arms, crosswalk, stacks (cached).
5. **Datasets** — eleven sets, dev tuning, key splits; appendix for counts.
6. **Methods** — cache, thresholds, pre-registered vs post-hoc guardrail rule, stacks, metrics, bootstrap note.
7. **Results** — narrative subsections (no RQ headings):
   - JailbreakBench crosswalk → **Fig. `jbb_crosswalk.png` (main)**
   - Harm splits → **Fig. `harm_splits.png` (main)**
   - Stacks + complementarity/kappa sentence → **Fig. `stack_frontier.png` (main)**
   - Operating points & cost (short) → appendix figures referenced
8. **Discussion** — deployment rules only (crosswalk, no pooled miss, union/cascade, not a product cert).
9. **Limitations**
10. **Ethics** — short paragraph (no prompt text; miss is not chat-model compliance)
11. **Conclusion**
12. **Appendix** — `tab:core-pack`, `tab:threshold-contrast` (moved from old results), long grids, stacks, post-hoc tables, **Fig. complementarity, cost_vs_miss, operating_points, reliability**
13. **References** (after appendix, `FloatBarrier`)

## Pre-registered vs post-hoc

| Item | Status |
|------|--------|
| Guardrail crosswalk (JBB → Prompt Attack only) | Pre-registered |
| Guardrail medium strength headlines | Pre-registered |
| Union / intersection / cascade stacks (Jev + medium crosswalk) | Pre-registered |
| Jev/Clef thresholds on development pool | Pre-registered procedure |
| Any-filter max-band guardrail on JailbreakBench | **Post-hoc** (label every mention) |
| Post-hoc any-filter stacks at medium | **Post-hoc** (not refit) |

## Figures

| Figure | Main text | Path |
|--------|-----------|------|
| JBB crosswalk | Yes | `../outputs/figures/narrative_20261020/jbb_crosswalk.png` |
| Harm splits | Yes | `../outputs/figures/narrative_20261020/harm_splits.png` |
| Stack frontier | Yes | `../outputs/figures/narrative_20261020/stack_frontier.png` |
| Complementarity | Appendix | `../outputs/figures/narrative_20261020/complementarity.png` |
| Cost vs miss | Appendix | `../outputs/figures/narrative_20261020/cost_vs_miss.png` |
| Operating points | Appendix | `../outputs/figures/narrative_20261020/operating_points.png` |
| Reliability | Appendix | `../outputs/figures/narrative_20261020/reliability.png` |

Dropped from main text: cascade flowchart, `guardrail_bands`, old pooled reliability (GoEmotions), old `latency_cost_vs_miss`, six-RQ walk.

## Numbers source

`RESULTS.md`, `outputs/figures/narrative_20261020/narrative_metrics.json`, `outputs/metrics/20261020T040920Z_90c5fd13.json`.

Harness: `20261020T033822Z_0f24960e` PASS; core pack: `20261020T040920Z_90c5fd13`.
