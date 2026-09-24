## 16. Empirical Causality Testing

Phase 15 status: COMPLETE (session 8; P1B Phase 15 only, operator-authorised; Phases 16–19 not started). Six experiments (EXP-06…EXP-11) and one descriptive breakdown (EXP-08b), all in the scratch environment. `audit/repo` stayed at `8958c49`, clean. No repository file was modified; two variants use an in-process patch inside the experiment script only (EXP-09, EXP-10), declared in their headers.

### 16.1 Set-up and method

- **Test system.** The shipped default: `systems/provided/futures_chapter15/basesystem.py:futures_system()` with `futuresconfig.yaml` (six instruments SOFR, US10, EUROSTX, V2X, MXP, CORN; fixed scalars, weights, FDM 1.31, IDM 1.89; `delayfill=True`; cash costs; `fixed_capital`) on `csvFuturesSimData` over the shipped CSVs (data end 2024-03-28). Non-default switches are set per experiment and recorded below and in `audit_progress.md` (estimation flags).
- **Truncation.** "Truncated at C" = copies of the adjusted-price, multiple-price and FX CSVs filtered to rows ≤ C 23:59 (git-ignored scratch, `scaffolding/home/p15data/`); instrument metadata, costs and config are unchanged. The start of every series is unchanged, so warm-ups are identical.
- **Matched comparison.** Values are compared only at timestamps present in both runs and ≤ C (`n_diff` = rows whose values differ by > 1e-9 or whose NaN status differs).
- **Cutoffs.** Declared before running: 2009-12-31 and 2019-12-31. 2009-12-31 could not run (EUROSTX starts 2014-03-13 → `missingData` raised from the SR-cost call inside `cheap_trading_rules_post_processing`, which the fixed-weight path also executes). It was replaced once by 2016-12-30, the first year end with all six instruments live. No other cutoff was tried, except the grid-aligned C_A = 2017-03-31 in EXP-08, which is derived from the grid formula (below), not chosen by outcome.
- **What a difference means here (spec §40).** Differences were separated as follows:
  - *Boundary-row index effect.* With full data, an instrument with no price on C itself (EUROSTX and V2X on 2019-12-31) still has a forward-filled row at C; with truncated data its index ends at its last price. Only shared timestamps are compared, and this row is reported separately. It is not future information: the forward-filled value is the last price ≤ C.
  - *Estimation-window / sample-size effects.* Expanding estimators (the defaults) use rows < `period_start`; a truncated run has exactly the same rows before each shared `period_start`. Differences at shared refit dates therefore cannot come from window length.
  - *Warm-up.* Identical start dates in both runs.
  - *Future information.* What remains after the above, confirmed by a control arm where one exists.
- **Causal levels (operator definition).** L1 internal calculation; L2 forecast; L3 position; L4 P&L / costs / fills.
- **Materiality.** The spec defines no threshold. Numbers are reported; no item is labelled "material". All magnitudes are for this system, these data and these cutoffs only.

### 16.2 Results summary

| Finding | Config | §15 static classification | Test | L1 | L2 | L3 | L4 | Final classification |
|---|---|---|---|---|---|---|---|---|
| PF-2 cost deflator | **default** | CONFIRMED ISSUE (costs / net P&L; position impact conditional) | EXP-06 | yes (deflator) | **no** | **no** | costs, net P&L only; gross unchanged | **CONFIRMED ISSUE** (default; costs and net P&L only) — TESTED |
| Default position path (§15.1) | default | NO ISSUE IDENTIFIED (static) | EXP-06 | — | no | no | gross no | **NO ISSUE IDENTIFIED** — now TESTED at two cutoffs for this system |
| PF-1 scalar backfill | non-default (`use_forecast_scale_estimates`) | CONFIRMED ISSUE (conditional; warm-up rows) | EXP-07 | yes | yes | yes | yes | **CONFIRMED ISSUE ONLY WHEN NON-DEFAULT OPTION ENABLED** — TESTED |
| PF-3/PF-4 SR cost × full-sample turnover | non-default (`use_forecast_weight_estimates`) | CONFIRMED ISSUE (conditional) | EXP-08 A + control B | yes | yes | yes | yes | **CONFIRMED ISSUE ONLY WHEN NON-DEFAULT OPTION ENABLED** — TESTED (PF-3 and PF-4 jointly; not separable in this test) |
| PF-11 end-anchored fit grid | non-default (any estimation; tested for forecast weights) | POSSIBLE ISSUE | EXP-08 C + control B, EXP-08b | yes | yes | yes | yes | **CONFIRMED ISSUE ONLY WHEN NON-DEFAULT OPTION ENABLED** — TESTED; the post-T input is the sample end *date* only (no post-T price or return enters any estimate) |
| PF-15 per-contract value bfill | non-default (P09) | POSSIBLE ISSUE | EXP-10 | yes (values) | no | **no** | **no** | **NO ISSUE IDENTIFIED** for positions and P&L (TESTED; L1 only) |
| O-P11-1 years_of_data (stacked rows) | non-default (`use_forecast_weight_estimates`, handcraft tilt) | not a causality item (§12.2; effect INFERRED) | EXP-09 | yes | yes | yes | yes | Causality: **NO ISSUE IDENTIFIED** (no post-T input). Definitional effect: TESTED |
| O-P9-1 gross P&L vs fill prices | non-default (order simulator, hourly limit orders) | N14 look-ahead: NO ISSUE IDENTIFIED; accounting effect INFERRED | EXP-11 | — | no | no | gross P&L | Look-ahead: **NO ISSUE IDENTIFIED** (unchanged). Accounting effect: TESTED |
| O-P9-2 slippage flag by side | non-default (as above) | recorded without judgement | EXP-11 | — | no | no | costs | TESTED (cost split measured; no judgement) |

### 16.3 EXP-06 — PF-2 (default configuration)

- *Question:* does removing post-C observations change forecasts, positions, gross P&L, costs or net P&L at dates ≤ C, and by how much?
- *Why static inspection is insufficient:* §15.2 gives the formula (`vol_180(t)/vol_180(last row)`), not its size.
- *Smallest experiment:* default system, full vs truncated at C ∈ {2016-12-30, 2019-12-31}; control pair with `vol_normalise_currency_costs=False`.
- *Expected evidence:* L2/L3/gross identical; costs scaled by one constant per instrument.
- *Stopping condition:* one table per cutoff. Script `scaffolding/experiments/exp06_pf2_cost_deflator.py`, output `exp06_output.txt`.
- **Results (deflator ON):**
  - Forecasts, rounded buffered positions and gross P&L: **0 differing rows** at shared timestamps for all six instruments at both cutoffs.
  - Costs: every differing cost row differs by **one constant factor per instrument** (min = max). Full/truncated cost ratio at 2016-12-30: SOFR 0.6892, US10 0.8381, EUROSTX 1.1364, V2X 1.9804, MXP 1.4859, CORN 1.0247; at 2019-12-31: SOFR 0.6595, US10 0.8295, EUROSTX 0.8483, V2X 1.1347, MXP 0.7516, CORN 1.2085. A single constant per instrument is what a change in the deflator's denominator alone produces (vol at C vs vol at the sample end).
  - Portfolio costs ≤ C: 2016-12-30: −64,299.75 (full) vs −64,549.58 (truncated), ratio 0.9961; 2019-12-31: −72,564.26 vs −77,805.79, ratio 0.9326. As % of gross: 3.28% vs 3.29%; 3.57% vs 3.83%.
  - Portfolio net P&L ≤ C: 1,897,180 vs 1,896,930 (2016); 1,959,060 vs 1,953,820 (2019). Net Sharpe ratio ≤ C: 0.4911 vs 0.4911 (2016); 0.4856 vs 0.4843 (2019). Gross Sharpe ratio identical (0.5078; 0.5036).
  - Per-instrument offsets partly cancel at portfolio level (e.g. 2016: SOFR costs −13,038 vs −18,916; V2X −6,114 vs −3,087).
- **Control (deflator OFF):** 0 differing rows for forecasts, positions, gross, costs and net at both cutoffs (cost ratio 1.000000 everywhere).
- **Boundary row:** EUROSTX and V2X carry one extra forward-filled row at 2019-12-31 in the full run (no price that day); values at all shared timestamps are identical.
- **Default fixed-weight path:** `cheap_trading_rules_post_processing` computes SR costs per rule even with fixed weights; with the default ceiling (999) no rule was excluded at either cutoff (forecasts identical).
- **Classification:** PF-2 stays **CONFIRMED ISSUE** (default ON), now TESTED. Causal level: **L4 only (costs, net P&L)**; L2 and L3 unchanged in the default configuration. The §15.1 default-position answer (NO ISSUE IDENTIFIED) is supported empirically at the two cutoffs for this system (TESTED; it remains a sample, not a proof over all dates).

### 16.4 EXP-07 — PF-1 (non-default: `use_forecast_scale_estimates=True`)

- *Question:* which rows receive a scalar built from later rows (the bfill), and does that change forecasts, positions and P&L there?
- *Why static inspection is insufficient:* which rows and instruments are reached under pooling, and the size, are not visible statically.
- *Smallest experiment:* (a) `backfill: True` (baseline) vs `backfill: False`, full data. With `backfill: False` every scalar at t uses rows ≤ t only (rolling mean of rows ≤ t; same-date cross-sectional median), i.e. it is the causality-safe construction. (b) Control: baseline, full vs truncated at 2019-12-31.
- *Expected evidence:* (a) differences confined to the first ~500 pooled rows; (b) none at shared timestamps.
- *Stopping condition:* these two comparisons. Script `exp07_pf1_scalar_backfill.py`, output `exp07_output.txt`.
- **Results (a):**
  - L1: the scalar differs on **509 rows (1972-10-18…1974-09-30), CORN only**, for all four weighted rules (backfilled values: carry 14.0521, ewmac16_64 3.9722, ewmac32_128 3.1492, ewmac64_256 2.5416). The other five instruments start after the pooled warm-up, so their scalars are identical.
  - L2: CORN combined forecast differs on 499 rows (1972-11-01…1974-09-30); with `backfill: False` those rows have no forecast.
  - L3: CORN position differs on 502 rows (to 1974-10-03, three rows beyond the forecast difference: the buffered path P06 carries the earlier position).
  - L4: on the differing rows, gross P&L 419,295.00 (backfill) vs −2,187.50 (no backfill); net 417,496.80 vs −1,767.60; costs differ to 1975-07-02 (the roll pseudo-fill cost is sized by the mean |position| of the preceding interval, N12; INFERRED from that mechanism). Full-sample portfolio Sharpe ratio: gross 0.5141 vs 0.4380, net 0.4919 vs 0.4146; all of the difference comes from 1972-11…1975-07.
- **Results (b):** at shared timestamps ≤ 2019-12-31, positions: 0 differing rows. Scalars differ on one row only (2019-12-31, ewmac64_256, 2.03892046 vs 2.03892047: the boundary row, where the full run's cross-sectional median includes the EU instruments' forward-filled row); forecasts differ by ≤ 2.5e-8 on that row. Cost and net differences in (b) are PF-2 (default ON in this arm; isolated in EXP-06).
- **Classification:** **CONFIRMED ISSUE ONLY WHEN NON-DEFAULT OPTION ENABLED** (unchanged in substance from §15.2), now TESTED at **L1–L4**, confined to the pooled warm-up (here: CORN, 1972-10…1975-07).

### 16.5 EXP-08 — PF-3/PF-4 and PF-11 (non-default: `use_forecast_weight_estimates=True`)

All arms: forecast weights estimated with the default `forecast_weight_estimate` block (handcraft, pooled gross returns, pooled turnover, expanding, weekly); `vol_normalise_currency_costs=False` in every arm, so PF-2 cannot enter the P&L comparisons (forecast weights use SR costs, not cash costs). With estimation on, all seven configured rules enter the optimisation.

- **Grid alignment.** The full-data grid is `2024-03-31 − 365k days` (+5 µs pooled offset; §8 O2). A truncated run ends on a Sunday weekly label, so a truncated grid coincides with the full grid only when a grid point is a Sunday: k = 7 → 2017-04-02 → **C_A = 2017-03-31**. Verified: the 44 period starts ≤ C_A are identical in both runs. **C_M = 2019-12-31** (pre-declared) is not aligned (truncated grid …2017-01-05, 2018-01-05, 2019-01-05 vs full …2017-04-02, 2018-04-02, 2019-04-02).
- *Questions:* A (PF-3/PF-4) with the grid identical, does removing post-C data change the weights in force ≤ C? B (control) with the grid identical and optimiser costs removed (`cost_multiplier: 0.0`), is the difference zero? C (PF-11) with costs removed, does a grid-moving cutoff change the weights in force ≤ C?
- *Why static inspection is insufficient:* §15.2 shows the end anchors, not whether they move any weight or position.
- *Smallest experiment:* five runs (full/C_A at cost_multiplier 2.0; full/C_A at 0.0; C_M at 0.0).
- *Expected evidence:* A non-zero; B zero; C non-zero if the grid position matters.
- *Stopping condition:* these runs. Script `exp08_pf3_pf4_pf11_forecast_weights.py`, output `exp08_output.txt`; breakdown `exp08b_pf11_breakdown.py`, `exp08b_output.txt`.
- **A — PF-3/PF-4 (grid-aligned, costs on):**
  - L1 inputs: SR cost per trade (last-year price and vol) full/truncated ratio SOFR 0.7283, US10 0.8017, EUROSTX 0.9680, V2X 1.0473, MXP 1.3680, CORN 0.7923. Pooled forecast turnover (full-sample) changes little, e.g. carry 1.268 vs 1.198, ewmac64_256 5.016 vs 4.918, ewmac2_8 88.908 vs 89.534.
  - L1 weights: raw weights differ in **43 of 44** periods ≤ C_A (the first, "fit without data" 1/N period is identical); max |Δ| SOFR 0.1596, US10 0.0530, EUROSTX 0.0223, V2X 0.0173, MXP 0.0669, CORN 0.0760.
  - L2: combined forecasts differ on most rows (e.g. CORN 10,540/11,598; max |Δ| 1.89 forecast units; SOFR max 3.25).
  - L3: positions differ: SOFR 1,871/8,616 rows (max 2 contracts), US10 477/9,025 (1), EUROSTX 28/797 (1), V2X 83/1,108 (1), MXP 943/5,621 (1), CORN 5,415/11,598 (5).
  - L4: portfolio ≤ C_A gross 2,189,462.6 vs 2,158,006.5; costs −171,244.0 vs −159,899.2; net 2,018,218.6 vs 1,998,107.3 (+1.0%). Sharpe ratio ≤ C_A gross 0.6286 vs 0.6184, net 0.5794 vs 0.5726.
- **B — control (grid-aligned, optimiser costs 0):** **0 differing rows** for raw weights, daily weights, forecasts, positions, gross, costs and net for all six instruments. With the grid held identical, no other post-C input reaches the forecast weights; A's differences are therefore attributable to the optimiser's cost inputs (PF-3 × PF-4). The two are multiplied into one cost SR per rule, so this test does not separate them; the L1 numbers show the SR cost per trade moved far more than turnover.
- **C — PF-11 (grid moved, optimiser costs 0):**
  - L1: period starts differ (above); daily (smoothed) forecast weights differ on every row; max |Δ| SOFR/US10/MXP 0.2251 (2009-04-03), EUROSTX 0.0105, V2X 0.0076, CORN 0.5074 (1975-01-16). Raw weights cannot be compared at matched timestamps because the refit dates differ.
  - L2: forecasts differ (max |Δ| CORN 25.85 forecast units, early years; MXP 10.24; SOFR 6.50).
  - L3: positions differ: SOFR 1,774/9,333 rows (max 7), US10 1,410/9,742 (3), EUROSTX 9/1,513 (1), V2X 201/1,824 (1), MXP 1,047/6,338 (7), CORN 5,695/12,315 (64).
  - EXP-08b breakdown: the largest effects are in the first fitted years (CORN 1975: weight |Δ| 0.51, position |Δ| 64), but they persist: 2000-01-01…C weight |Δ| up to 0.2251 and position |Δ| up to 4 (CORN), 7 (MXP), 3 (SOFR) contracts.
  - L4: portfolio ≤ C_M gross 2,260,607.0 vs 2,232,467.4; net 2,025,017.0 vs 2,018,701.7; Sharpe ratio ≤ C_M gross 0.6271 vs 0.6065, net 0.5617 vs 0.5484.
- **Classification:**
  - PF-3/PF-4: **CONFIRMED ISSUE ONLY WHEN NON-DEFAULT OPTION ENABLED** (unchanged in substance), now TESTED at **L1–L4**.
  - PF-11: §15.2 recorded **POSSIBLE ISSUE** ("post-T calendar information places the refits; no post-T market data found; effect not established"). Empirically, removing post-C data changes weights, forecasts, positions and P&L at dates ≤ C (C), while holding the grid fixed removes every difference (B). The position at T therefore depends on the sample end date, which is information after T; B shows it is the only such input once costs are removed. Reclassified to **CONFIRMED ISSUE ONLY WHEN NON-DEFAULT OPTION ENABLED**, qualified: the post-T information is the refit *calendar* only; every estimate still uses data before its own `period_start`. Tested for forecast weights only; instrument weights, FDM and IDM use the same grid code (§8 O2) but were not run (INFERRED to behave alike).

### 16.6 EXP-09 — O-P11-1 (non-default: `use_forecast_weight_estimates=True`)

- *Question:* the handcraft SR tilt takes `years_of_data` = rows of the stacked pooled returns / 52. Does that change fitted weights, forecasts, positions, P&L?
- *Why static inspection is insufficient:* §12.2 could only infer the tilt strength.
- *Smallest experiment:* full data; baseline as shipped vs the same run with `portfolioOptimiser.data_length_for_period` divided by `net_returns.pooled_length` (calendar years), patched inside the scratch script only. `data_length` has one consumer on this path (handcraft `years_of_data`, `handcraft.py:151`; `git grep data_length`). This is a measurement counterfactual, not a proposed change.
- *Expected evidence / stopping condition:* one comparison. Script `exp09_op11_1_years_of_data.py`, output `exp09_output.txt`.
- **Results:**
  - L1: last fit (fit_end 2023-04-01): 15,792 stacked rows → **303.7 "years"** (baseline) vs 2,632 rows → **50.6 years** (variant; pooled_length 6). Raw weights differ in **50 of 51** periods; max |Δ| SOFR 0.1857, US10 0.1127, EUROSTX 0.1158, V2X 0.2450, MXP 0.1187, CORN 0.1082. By the last period the differences are ≤ 0.012 (largest: V2X ewmac4_16 0.005 vs 0.017).
  - L2: forecasts differ (e.g. CORN max |Δ| 4.82, US10 4.49).
  - L3: positions differ: SOFR 1,075/10,440 rows (max 2), US10 859/10,849 (2), EUROSTX 17/2,621 (1), V2X 267/2,932 (1), MXP 239/7,445 (1), CORN 4,366/13,422 (9).
  - L4: full-sample portfolio net 2,198,900.8 (baseline) vs 2,160,651.6; Sharpe ratio gross 0.6073 vs 0.6052, net 0.5677 vs 0.5647.
- **Classification:** not a look-ahead: no post-T input is involved. Causality: **NO ISSUE IDENTIFIED**. The definitional effect of counting stacked rows is **TESTED** (L1–L4 in this configuration); it is recorded without judgement on which definition is intended.

### 16.7 EXP-10 — PF-15 (non-default: P09 dynamic optimisation)

- *Question:* `Portfolios.get_per_contract_value_as_proportion_of_capital_df` bfills each instrument's first value into the rows before its data start (source comment "slight cheating"). Do those post-T values change any P09 position, or P&L?
- *Why static inspection is insufficient:* §15.2 left open whether the objective uses the value of an instrument whose optimal position is not yet defined.
- *Smallest experiment:* P09 system = the stage list of `systems/provided/rob_system/run_system.py` (Risk, accountForOptimisedStage, optimisedPositions, Portfolios, PositionSizing, raw data, ForecastCombine, ForecastScaleCap, Rules), with the chapter-15 raw data, scale/cap, config and shipped CSVs instead of the database and the rob_system config; `small_system` settings from `defaults.yaml`. Baseline as shipped vs a variant where **only the bfilled rows** are set to 2× the bfilled value (in-process patch in the script only). If positions are identical, the post-T values do not reach any decision. Leaving the rows NaN was not used: NaN handling by the greedy optimiser is outside Phase 15 scope and could fail for unrelated reasons.
- *Stopping condition:* one comparison. Script `exp10_pf15_per_contract_bfill.py`, output `exp10_output.txt`; about 3 minutes per run (13,422 dates in the per-date loop).
- **Results:**
  - L1: the variant changes the per-contract values on the pre-start rows of five instruments: US10 2,573 rows (1972-10-18…1982-08-27), SOFR 2,982 (…1984-03-22), MXP 5,977 (…1995-09-14), V2X 10,490 (…2013-01-01), EUROSTX 10,801 (…2014-03-12); CORN 0 (the first instrument).
  - L3: P09 positions differ on **0 rows** for all six instruments (max |Δ| 0).
  - L4: gross, costs and net: **0 differing rows** (net 1,231,415.84 in both).
  - Descriptive: no instrument has a non-zero baseline P09 position before its data start.
- **Classification:** §15.2 recorded **POSSIBLE ISSUE** ("whether they change any P09 position was not established"). Empirically, the backfilled post-T values change an internal input (L1) but no position or P&L in this system (L3/L4 none). Current state: **NO ISSUE IDENTIFIED** for positions and P&L (TESTED; this system, one invariance variant at 2×). The L1 dependence itself remains as recorded; other universes or P09 settings were not tested.

### 16.8 EXP-11 — O-P9-1 / O-P9-2 (non-default: order simulator, hourly limit orders)

- *Question:* O-P9-1 — gross P&L uses the simulator price series, not fill prices; for limit fills (filled at the order-time price only if the next price is strictly better) what is the gap between the framework's gross P&L and the same trades valued at their fill prices? O-P9-2 — cost per fill by side.
- *Why static inspection is insufficient:* the size and sign need data.
- *Smallest experiment:* the provided hourly example (`systems/provided/example/hourly_with_order_simulation.py`, `use_limit_orders=True`, its YAML unchanged) on the shipped CSVs (which contain hourly rows) instead of the database; instrument US10 only; one run. Identity (positions start at 0): framework gross = Σ_t pos_{t−1}(P_t − P_{t−1}) = pos_T·P_T − Σ_i q_i·P(fill row i); at fill prices: pos_T·P_T − Σ_i q_i·f_i.
- *Stopping condition:* one run. Script `exp11_op9_limit_fill_accounting.py`, output `exp11_output.txt`. Small enough not to need a wider order-simulator audit.
- **Results:**
  - 21,301 hourly price rows (2013-10-02…2024-03-28); 1,843 non-zero fills (919 buys, 924 sells); value per point 1,000.
  - Framework gross P&L **31,515.62 USD**; the identity reconstruction at simulator prices gives the same 31,515.62 (O-P9-1 mechanism confirmed).
  - The same trades valued at their fill prices: **−129,875.00 USD**. Gap **−161,390.62 USD** (−512% of the framework's gross).
  - All 1,843 fills (100%) are at a price worse for the trader than the fill-row price. This follows from the fill rule: a buy limit fills only if the next price is below the limit, and the fill is at the limit.
  - O-P9-2: buy fills 919, slippage flag True on 0, mean raw cost 1.67 USD per contract (commission only); sell fills 924, flag True on 924, mean 9.67 USD per contract (commission + slippage).
- **Classification:** look-ahead (N14): **NO ISSUE IDENTIFIED**, unchanged: the fill decision uses the price at the fill row, which is when the fill is evaluated. O-P9-1: the accounting effect is **TESTED** (L4, gross P&L; positions unaffected). O-P9-2: **TESTED** (costs). Both are recorded without judgement on intent, for this example, instrument and period only. O-P9-3 is not tested (§16.9).

### 16.9 Findings not tested in Phase 15 (static classification stands)

| Item | Static classification (§15 / §11) | Reason not tested |
|---|---|---|
| PF-2 via estimated instrument weights / IDM; PF-6 (compounding via PF-2); PF-13 (P09 final-price costs) | CONFIRMED ISSUE (conditional) | Not in the operator's Phase 15 question list; PF-2's own mechanism is isolated in EXP-06. Not run to keep Phase 15 small |
| PF-7 shocked-vol backfill | CONFIRMED ISSUE (conditional; first two rows and pre-index dates) | Not in the question list; confined to two rows by construction |
| PF-8 roll dates / shipped history | POSSIBLE ISSUE / UNVERIFIED (§11.10) | G11: raw contract prices are not shipped, so availability-based roll dating cannot be re-run on the shipped data |
| PF-12 universe (a)/(b) | CONFIRMED (a, no in-repo caller) / POSSIBLE (b) | (a) not reachable with default arguments; (b) is ex-post selection, not a data path a truncation test can isolate |
| PF-14 daily→hourly alignment | CONFIRMED ISSUE (conditional; mechanism TESTED, EXP-04) | Not in the question list; effect size not measured |
| N7 `in_sample` | CONFIRMED ISSUE when chosen (by design) | Full-sample fitting by definition; nothing to measure beyond PF-11/PF-3 machinery |
| N8 (i)/(ii) | CONFIRMED (P&L only / reporting only) | Not in the question list |
| N9 shipped fixed parameters | UNVERIFIED | Provenance is outside the repository; not testable here |
| N10 protected/stale cache | POSSIBLE ISSUE (workflow) | A user-workflow property, not a data path |
| O-P9-3 hourly use of a daily-labelled rule | recorded (VERIFIED code; consequences INFERRED) | A documentation/semantics observation; measuring it would require choosing alternative rule parameters (tuning), which Phase 15 excludes |
| G7 greedy `False` maximum (Phase 11 candidate) | INFERRED | Not in the question list |

### 16.10 Reclassification register (original conclusions preserved)

§15 is **not edited**; this table records what Phase 15 changes. Where §15 and this table differ, this table is the current state.

| Item | §15 conclusion (kept) | Phase 15 evidence | Current state |
|---|---|---|---|
| PF-2 | CONFIRMED ISSUE (default; costs / net P&L) | EXP-06: L4 only; constant per-instrument cost factor; control zero | unchanged; TESTED |
| Default position path (§15.1) | NO ISSUE IDENTIFIED (static; not verified causal) | EXP-06: 0 forecast/position/gross differences at two cutoffs | unchanged; TESTED for this system and cutoffs |
| PF-1 | CONFIRMED ISSUE (conditional) | EXP-07: L1–L4 in the pooled warm-up (CORN 1972–1975) | unchanged; TESTED |
| PF-3/PF-4 | CONFIRMED ISSUE (conditional) | EXP-08 A/B: L1–L4; control isolates the cost inputs | unchanged; TESTED (jointly) |
| PF-11 | POSSIBLE ISSUE | EXP-08 B/C, 08b: L1–L4 when the grid moves; zero when it does not | **changed → CONFIRMED ISSUE ONLY WHEN NON-DEFAULT OPTION ENABLED** (calendar-only post-T input) |
| PF-15 | POSSIBLE ISSUE | EXP-10: L1 only (values on 2,573–10,801 pre-start rows); 0 position / P&L differences | **changed → NO ISSUE IDENTIFIED** for positions and P&L (TESTED; L1 dependence remains) |
| O-P11-1 | effect INFERRED (§12.2) | EXP-09: L1–L4 | effect TESTED; causality NO ISSUE IDENTIFIED |
| O-P9-1 / O-P9-2 | effects INFERRED / recorded (§10.4) | EXP-11 | effects TESTED; N14 look-ahead NO ISSUE IDENTIFIED unchanged |

### 16.11 Phase 15 change log (explicit)

- Report: this section (§16) written; §15 not edited (supersessions in §16.10); Executive Summary bullets 11, 17 and 20 and the status line updated.
- CSV: `last_phase` → 15 on the six rows whose findings were tested: E02_COST_MODEL (PF-2), R01_FORECAST_SCALAR_EST (PF-1), R05_FORECAST_WEIGHT_OPT (PF-3/PF-4, PF-11, O-P11-1), R08_FITTING_DATES (PF-11), R09_TURNOVER_SR_COST (PF-3/PF-4), P09_DYNAMIC_OPTIMISATION (PF-15). No evidence value changed (U5: R03–R07 stay INFERRED; experiments test effects, not the components' implementation labels). No row added (the order simulator stays outside the inventory, DISC-3).
- Progress file: phase table, empirical tests (EXP-06…EXP-11), estimation flags per test, next task, session log, usage UNRECORDED.
