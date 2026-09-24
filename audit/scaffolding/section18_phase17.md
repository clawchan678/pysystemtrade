## 18. Degrees of Freedom / Research Safeguards

Phase 17 status: COMPLETE (session 8; operator-authorised Phase 17 only; Phases 18–19 not started). Static inspection only: no experiment was run, no optimisation was performed, and `audit/repo` stayed at `8958c49`, clean. Line references are to `sysdata/config/defaults.yaml` (DEF) and `systems/provided/futures_chapter15/futuresconfig.yaml` (CH15) @ 8958c49 unless stated. This section reports what exists, not what should exist.

### 18.1 Classification vocabulary (spec §40)

- **Fixed:** a constant set in config or code, not derived from data during a run.
- **Estimated:** computed from data during a run by an estimator, with no objective being optimised.
- **Optimized:** chosen during a run by maximising or minimising an objective.
- **Heuristic:** a hard-coded or default rule or constant whose derivation is not in the repository.
- **Adaptive:** changes over time in response to data or state.

Many items have a default mode and an optional mode; both are listed. Where the shipped fixed values came from is **UNVERIFIED** (§15.3 N9: "defined in chapter 15 of my book", `docs/backtesting.md:217`; the book is not repository evidence, spec §6).

### 18.2 Parameter inventory

| Area | Parameter(s) | Default value / location | Classification (default → optional) | Evidence |
|---|---|---|---|---|
| Trading-rule parameters | EWMAC `Lfast/Lslow` (2/8 … 64/256); carry `smooth_days` 90; provided-rule defaults (breakout `lookback` 10, accel/mr_wings `Lfast` 4, cs_mr/rel_mom `horizon` 250, factors `smooth` 90, `ewmac_calc_vol` `vol_days` 35) | CH15:9-70; `systems/provided/rules/*.py` signatures | **Fixed** (set in config or as function defaults; no in-repo search or fitting of rule parameters found) | VERIFIED (config, signatures) |
| Forecast parameters | `average_absolute_forecast` 10; rule set per instrument = `trading_rules` | DEF:143; CH15 | **Fixed** | VERIFIED |
| Forecast scaling | per-rule `forecast_scalar` (10.6 … 1.87; carry 30) | CH15; DEF:125 (1.0) | **Fixed** → **Estimated** when `use_forecast_scale_estimates: True` (expanding mean of pooled \|forecast\|, min_periods 500, `backfill` True: PF-1) | VERIFIED; PF-1 TESTED (§16.4) |
| Forecast caps | `forecast_cap` 20 | DEF:141; CH15 | **Fixed** (heuristic constant) | VERIFIED |
| Forecast combination | `forecast_weights` (4 rules; carry 0.50); `forecast_div_multiplier` 1.31 | CH15:75-80 | Weights **Fixed** → **Optimized** (handcraft by default; `method`, DEF:194) when `use_forecast_weight_estimates`. FDM **Fixed** → **Estimated** (correlation → DM, `dm_max` 2.5 **heuristic** cap, EWMA 125) | VERIFIED; PF-3/4, PF-11, O-P11-1 TESTED (§16) |
| Optimiser internals | handcraft SR tilt constants avg SR 0.5, std 0.15; `FIXED_CLUSTER_SIZE` 2; cleaning `fraction` 0.5; `cost_multiplier` 2.0 / 1.0; `shrinkage_SR` 0.9, `shrinkage_corr` 0.5; `equalise_SR`, `equalise_vols` | `SR_adjustment.py:77-251`; `handcraft.py`; DEF:188,196-200,266-275 | **Heuristic** (hard-coded or default constants inside an optimizer) | VERIFIED (§12.2) |
| Volatility windows | `mixed_vol_calc`: `days` 35, `min_periods` 10, `slow_vol_years` 10, `proportion_of_slow_vol` 0.3, `vol_abs_min` 1e-10 | DEF:112-120 | Windows **Fixed**; the vol series itself is **Estimated** and **Adaptive** (moves position size with vol) | VERIFIED |
| Correlation windows | forecast corr `ew_lookback` 250, weekly, expanding; instrument corr 25, expanding; optimiser corr 50,000 / 500,000; risk corr 75, rolling | DEF:152-160, 202-205, 238-244, 278-281, 312-317 | **Fixed** hyper-parameters of **Estimated** quantities (used only when the estimate is on) | VERIFIED |
| Instrument weighting | `instrument_weights` (6 instruments); `instrument_div_multiplier` 1.89 | CH15:90-97 | **Fixed** → **Optimized** (handcraft, `equalise_SR: True`, DEF:262-271) / IDM **Estimated** (`dm_max` 2.5 heuristic) | VERIFIED |
| Fit calendar | `date_method` expanding / rolling / in_sample; `rollyears` 20; yearly grid anchored to the sample end | DEF:156,192,241,268,315; `fitting_dates.py` | **Fixed** choice; the grid position depends on the sample end (PF-11, a design property) | VERIFIED; PF-11 TESTED (§16.5, §16.12) |
| Portfolio parameters | `notional_trading_capital` 250,000 (CH15) / 1,000,000 (DEF:222); `base_currency` USD; `capital_multiplier` `fixed_capital` | CH15:85-87; DEF:222-226 | **Fixed** → **Adaptive** with `full_compounding` / `half_compounding` (PF-6). Production default is `full` (DEF:74) | VERIFIED |
| Risk targets | `percentage_vol_target` 20 (CH15) / 16 (DEF:221); risk overlay limits (commented out, 99999) | CH15:84; DEF:221,305-309 | Target **Fixed**; risk overlay OFF → **Adaptive** scaling when configured (P04) | VERIFIED |
| Buffering | `buffer_method` forecast, `buffer_size` 0.10, `buffer_trade_to_edge` True; P09 `tracking_error_buffer` 0.0125, `shadow_cost` 50 | DEF:296-298, 326-329 | **Fixed** (heuristic constants). The buffered position is path-dependent (P06) | VERIFIED |
| Costs | per-instrument spread and commissions (`instrumentconfig.csv`, `spreadcosts.csv`); `multiply_roll_costs_by` 0.5; `vol_normalise_currency_costs` True; `use_SR_costs` False | csvconfig; DEF:300-302 | Inputs **Fixed** (data files; provenance outside the repository). Roll-cost multiplier **Heuristic**. Cost deflator **Adaptive** (vol-scaled, end-anchored: PF-2) | VERIFIED; PF-2 TESTED (§16.3) |
| Instrument selection | universe = `instrument_weights` keys (or all data); `duplicate_instruments`, `exclude_instrument_lists` (`ignore_instruments`, `trading_restrictions`, `bad_markets`) | CH15; DEF:337-395; `basesystem.py:150-275` | **Fixed** lists. Their production tooling is **heuristic**: `remove_markets_report` recommends `bad_markets` from *current* SR cost > `MAX_SR_COST` 0.01 and volume < `MIN_VOLUME_CONTRACTS_DAILY` 100 / `MIN_VOLUME_RISK_DAILY` 1.5 (`sysproduction/reporting/data/constants.py:7-10`; `duplicate_remove_markets.py`). The lists apply to the whole history (PF-12b) | VERIFIED |
| Rule selection | `trading_rules` list; speed limit `forecast_post_ceiling_cost_SR` 999 and `ceiling_cost_SR` 9999 (effectively off); `remove_short_history` (no in-repo caller passes True) | DEF:182,190; `forecast_combine.py:735-864`; `basesystem.py` | **Fixed** list; cost-ceiling exclusion is **Heuristic** (a threshold on the end-anchored SR cost, PF-3/PF-4) when enabled | VERIFIED |
| Adaptive behaviour (other) | vol-scaled position sizing; optional vol attenuation (`volAttenForecastScaleCap`: multiplier `2 − 1.5 × quantile` of vol vs its 2500-day mean, EWMA 10); optional risk overlay; optional compounding; optional P09 per-date optimisation | `positionsizing.py`; `attenuate_vol/vol_attenuation_forecast_scale_cap.py:8-82`; P04; P07; P09 | **Adaptive**. Vol attenuation's quantile uses only prior rows (`quantile_of_points_in_data_series`, `strategy_functions.py:182-193`: `[:irow]`); its constants 2, 1.5, 2500 and 10 are **heuristic** | VERIFIED (code) |

### 18.3 Safeguards inventory

| Risk | Safeguard found? | Location / evidence |
|---|---|---|
| Look-ahead | **Partial.** Fit windows end at `period_start` (expanding/rolling, `fitting_dates.py:181-201`); `delayfill=True` by default in every accounts caller (§15 N2, §17); vol, correlations and rules use rows ≤ t (§15). No generic look-ahead check or guard over user rules was found. Known exceptions: PF-1, PF-2, PF-3/PF-4 (TESTED), PF-7, PF-13, N7 (`in_sample`, documented option), PF-11 (calendar). | §15, §16, §17. The docs label the scalar backfill "cheating" (`backtesting.md:2451`) |
| Data snooping | **None found** (no hold-out split, reserved test period or walk-forward driver in code). The optional estimation is itself expanding out-of-sample fitting (not a snooping control). | `git grep -i -E "walk.forward|out.of.sample|out_of_sample"` outside tests: no hits |
| Repeated experimentation | **None found** (no experiment registry, run log or counter). Config and code are not versioned or stamped. | §14.1 (versioning), O-P13-1 |
| Parameter mining | **None found** (no parameter-sweep driver and no multiple-testing adjustment). Rule parameters are fixed in config; nothing in the repo records how they were chosen (N9 UNVERIFIED). | `git grep` for multiple-testing / Bonferroni / deflated / reality-check terms: only the P09 cost "deflated" variable |
| Strategy selection bias | **None found** (no correction for selecting among strategies; `strategy_list` in production config is a manual list). | §14.1 |
| Instrument selection bias | **None found.** The universe and exclusion lists are config written with current knowledge and applied to all history (PF-12b); `bad_markets` recommendations use current costs and volumes. | DEF:337-395; `remove_markets_report.py`; PF-12 |
| Date-range selection | **None found.** A `start_date` config is supported (`sim_data.py:297-317`); there is no end-date control and no check on the chosen range. | `sim_data.py` |
| Regime selection | **None found** (`git grep -i regime` outside tests: no hits). Vol attenuation adapts to vol level, but it is not a regime-selection safeguard. | grep |
| Post-hoc methodology changes | **None found** (no config/code version stamp, content hash or change log tied to results; production keeps pickled state and merged config for 30 days only). | §14.1; `sysproduction/data/backtest.py:191-215` |

### 18.4 Robustness / statistics tooling (what exists)

| Tool | Exists? | Location / evidence |
|---|---|---|
| Sensitivity analysis | **Not found** (`git grep -i -E "sensitiv|robustness|stress"` outside tests: no hits in code) | grep |
| Bootstrap | **Not implemented as a method.** The docs say "Bootstrapping is no longer implemented" (`docs/backtesting.md:3377`); a stale doctest still sets `method="bootstrap"` (`forecast_combine.py:582`). The only "bootstrap" in code is the *parametric* mini-bootstrap in the SR tilt (normal CDF points, no resampling; `SR_adjustment.py:108-118`; `full_handcrafting.py:241-251`) | VERIFIED (DV10) |
| Monte Carlo | **Not found.** `monte_runs: 100` exists in config (DEF:276) and in the same doctest (`forecast_combine.py:583`), but no code reads it (`git grep monte_runs`) | VERIFIED |
| Significance testing | **Exists (limited):** `accountCurve.t_test()` and `account_t_test(acc1, acc2)` (`account_curve_analysis.py:16-40`); the docs warn its assumptions may be violated (`backtesting.md:3022`); the documented import path is wrong (DV14) | VERIFIED (§14.1) |
| Robustness checks | **Not found** beyond `systemDiag` scaling and parameter checks and account-curve statistics (`stats()`, drawdowns) | §14.1 |
| Randomness | none outside tests (`np.random`, `import random`: no hits), so there is no seed control to assess | grep |

### 18.5 Observations (Phase 17)

- **O-P17-1:** every degree of freedom in the default system is **fixed** in config. The "optimized" and "estimated" modes are opt-in. The fixed values' derivation is not in the repository (N9, UNVERIFIED).
- **O-P17-2:** the only statistical-inference tool in code is a t-test. The configured `monte_runs` has no reader, and bootstrap is documented as removed.
- **O-P17-3:** instrument-selection tooling (bad-market recommendations) uses current cost and liquidity, and the lists apply to all history. This restates PF-12b; it is not a new classification.

### 18.6 Phase 17 change log (explicit)

- Report: this section (§18). Status line and Executive Summary bullet 19 updated (bullet count unchanged). §17.5 O-P16-2 status formalised (report-only; see below).
- CSV: `last_phase` → 17 on the rows whose parameters were classified here from source: C04_CONFIG, A04_FORECAST_SCALING, A05_FORECAST_CAP, R02_VOL_ESTIMATION, P01_POSITION_SIZING, P05_BUFFER_CALC. No evidence value changed (U5: C04 stays INFERRED); no row added.
- Progress file: phase table, next task, session log, usage line; O-P16-2 status recorded.
