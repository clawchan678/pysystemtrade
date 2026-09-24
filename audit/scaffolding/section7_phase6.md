## 7. pysystemtrade-Specific Framework Concepts

**Phase 6 status: COMPLETE.** Spec §36 asks each concept to be verified, not assumed. For each one this section records: existence, location, function, documented vs implemented behaviour, assumptions, evidence and tier. Where a concept is already fully carded in §6.4, the card is cited rather than repeated. Deep causal testing is deferred to Phases 14–15; timing observations here are labelled pre-flags, not classified findings.

Evidence discipline (U5 ruling): source read in Phase 6 is recorded as *observation* with file/line provenance. It does **not** change the `impl_evidence` of any row currently INFERRED (§12 prohibits INFERRED → VERIFIED). Rows that were UNVERIFIED, or are new in Phase 6, may carry VERIFIED where their code was read.

### 7.1 Handcrafted vs optimised weights

- **Existence:** yes. Four optimisation methods are registered; bootstrapping is absent.
- **Location:**
  - `sysquant/optimisation/generic_optimiser.py:genericOptimiser` (`:9-98`);
  - `optimise_over_time.py:optimiseWeightsOverTime` (`:14-81`);
  - `portfolio_optimiser.py:portfolioOptimiser` (`:26-190`);
  - `optimisers/call_optimiser.py` (`REGISTER_OF_OPTIMISERS`, `:10-15`);
  - `optimisers/handcraft.py` (`:21-250`), `optimisers/shrinkage.py`, `optimisers/one_period.py`, `optimisers/equal_weights.py`;
  - `SR_adjustment.py`, `cleaning.py`, `shared.py`, `pre_processing.py`;
  - `sysquant/estimators/clustering_correlations.py:cluster_correlation_matrix` (`:16-29`).
  - Callers: `systems/forecast_combine.py:get_monthly_raw_forecast_weights_estimated` (forecast weights, R05) and `systems/portfolio.py:get_raw_estimated_instrument_weights` (`:622-700`, instrument weights, R06).
- **Function (observed):**
  1. `genericOptimiser` builds **net** returns: gross returns less a constant annual SR cost drag (`pre_processing.py:get_dict_of_net_returns`). Costs are optionally scaled by `cost_multiplier` and optionally pooled.
  2. `optimiseWeightsOverTime` generates fit periods (`generate_fitting_dates`, expanding by default). For each period `portfolioOptimiser.calculate_weights_for_period` estimates correlation, mean and stdev from `fit_start:fit_end` and dispatches to the method.
  3. Weights are indexed by `period_start` (`optimise_over_time.py:74-77`).
  4. Assets with missing estimates get NaN weights (`call_optimiser.py:25-42`) and are then *cleaned* (`cleaning.py`, `portfolio_optimiser.py:74-85`) or zeroed.
  5. Optional post-processing `apply_cost_weight` adjusts weights by relative SR cost (`generic_optimiser.py:83-98`, `SR_adjustment.py`).
- **Methods (observed):**
  - `equal_weights`: 1/N.
  - `one_period`: Markowitz max-SR (`shared.py:optimise_given_estimates`).
  - `shrinkage`: correlations shrunk to their average and means to a target SR, then Markowitz.
  - `handcraft` (default in `defaults.yaml:194,263`): if ≤ 2 assets, 1/N risk weights; otherwise recursive **two-way clustering** of the correlation matrix (`FIXED_CLUSTER_SIZE = 2`, "Do not change", `handcraft.py:51`). Each half gets 0.5, multiplied by the sub-portfolio's diversification multiplier (`handcraft.py:194-250`). If `equalise_SR` is False, weights are then tilted by relative Sharpe ratio using `adjust_weights_for_SR` with the average correlation and **years of data** (`handcraft.py:146-171`). `equalise_vols=False` raises "Non equalised vols not supported" (`handcraft.py:38-49`).
- **Configured defaults:**
  - Forecast weights: `method: handcraft`, `equalise_SR: False`, `cost_multiplier: 2.0`, `apply_cost_weight: False`, `pool_gross_returns: True`, weekly, expanding (`defaults.yaml:184-214`).
  - Instrument weights: `handcraft`, `equalise_SR: True`, `cost_multiplier: 1.0`, weekly, expanding (`:261-293`).
  - Both estimation switches are OFF by default (`use_*_weight_estimates: False`), so default backtests use fixed or equal weights.
- **Documented behaviour:** "There are five methods provided ... Personally I'd use handcrafting, which is the default". Bootstrapping is listed as "recommended, but slow" and then as "no longer implemented" (`docs/backtesting.md:3345-3405`, "five methods" at `:3347`). The docs also require that `equalise_vols` "*must* be true" for handcrafting (`:3402`). DOCUMENTED.
- **Implemented behaviour:** four registered methods (`call_optimiser.py:10-15`); requesting `bootstrap` raises "Optimiser ... not recognised" (`:62-66`). The handcraft `equalise_vols` constraint is enforced by exception, consistent with the docs. Observation recorded (see the evidence note above).
- **Divergence:** **DV10**, minor. The docs say "five methods provided", but only four exist; the bootstrap entry is self-described as not implemented.
- **Assumptions:** returns are vol-equalised before optimisation (`equalise_vols`); the Sharpe-ratio tilt is credible only in proportion to years of data; weights estimated on a fit window apply from `period_start` onward.
- **Pre-flag (Phase 14):** `fit_end = period_start` (R08). The fit window itself looks causal at date level. Net returns use SR costs whose per-trade cost is end-of-sample anchored (Card 13), and the cost-ceiling turnover is full-sample (Card 14). NOT CLASSIFIED.
- **Evidence:** R05, R06 remain **INFERRED** (U5 ruling), with the source observations above. **Tier:** R05 Tier 2; R06 inside Tier 1 Card 10.

### 7.2 Pooling across instruments

- **Existence:** yes. Pooling appears in five places:

| Pooled quantity | Location | Mechanism (observed) | Default |
|---|---|---|---|
| Forecast scalar | `forecast_scale_cap.py:166-320`; `forecast_scalar.py:5-50` | Cross-sectional **median** of |forecast| across all instruments using the rule (ffilled), then an expanding mean | `pool_instruments: True` (`defaults.yaml:134`); the estimation switch is OFF |
| Forecast correlations (FDM) | `forecast_combine.py:1167-1296`; `sysquant/estimators/pooled_correlation.py:9-37`; `syscore/pandas/list_of_df.py:77-110` | Per-instrument forecast **levels** are ffilled, resampled weekly with `.last()`, reindexed to a common index, then **stacked** into one frame with microsecond offsets per instrument; `correlation_over_time(..., length_adjustment = n_instruments)` | `pool_instruments: True` (`:153`); FDM estimation OFF |
| Gross returns for forecast weights | `sysquant/optimisation/pre_processing.py:get_pooled_gross_returns_dict`; `sysquant/returns.py:121-137` | Gross forecast returns of all instruments with the same (cheap) rules are summed weekly, reindexed and stacked in the same way; `pooled_length` adjusts estimator lookbacks | `pool_gross_returns: True` (`:186`) |
| Forecast turnover (cost) | `account_costs.py:211-293`; `pre_processing.py:_calculate_pooled_turnover_costs` | Length-weighted average of the full-sample turnover across instruments with the same rules; `nanmean` in the optimiser path | `use_pooled_turnover: True` |
| Forecast SR cost | `account_costs.py:_get_SR_transaction_costs_for_rule_with_pooled_costs` | Length-weighted average of cost × turnover | `use_pooled_costs: False` |

- **Instrument selection for pooling:** instruments with the same rule set (`has_same_rules_as_code`), or the same *cheap* rule set when weights are estimated (`has_same_cheap_rules_as_code`, `forecast_combine.py:1190-1196`).
- **Documented behaviour:** pooled forecast scalars are the default (`backtesting.md:2442-2455`); pooling gross returns and pooled turnover are recommended, and "Pooling across instruments is only available when calculating forecast weights" (`:3278-3292`); cost pooling (`:3066-3077`). DOCUMENTED.
- **Implemented behaviour:** as documented. Instrument weights never pool: `pool_instruments` is "not used for instrument weights" (docs `:3257`), and `pre_processing` returns single-asset data when there is one account curve (`:57-60,92-93`). Observation recorded.
- **Assumptions:** forecasts from different instruments with the same rule are exchangeable draws (a common scalar and correlation structure). The code documents a limit of its own stacking method: "WARNING: SO THIS METHOD WON'T WORK WITH HIGH FREQUENCY DATA! THIS WILL ALSO DESTROY ANY AUTOCORRELATION PROPERTIES" (`list_of_df.py:83-87`, code docstring, not `docs/`).
- **Divergence:** none identified.
- **Evidence:** R01 VERIFIED (Card 4); R03 remains **INFERRED** (U5), with the observations above; R09 VERIFIED (Card 14). **Tier:** R01, R03 and R09 sit inside Tier 1 cards (4, 8, 14).

### 7.3 Forecast scalar / target / cap

- **Existence:** yes. See **Card 4** (scaling and estimation) and **Card 5** (cap and floor).
- **Summary:** the target average |forecast| is `average_absolute_forecast = 10` (`defaults.yaml:143`), used by scaling, position sizing (`positionsizing.py:156-158`), the forecast P&L proxy and turnover. Cap = 20; floor = −cap by default. The fixed scalar is 1.0 unless configured. The estimated scalar is an expanding pooled median-|f| mean with `backfill=True`.
- **Documented vs implemented:** consistent (`backtesting.md:2388-2460`, `introduction.md:355`). The backfill and the zero exclusion are VERIFIED in code; the docs do not describe them.
- **Assumptions:** a stationary |forecast| distribution; a common target for all rules.
- **Pre-flag (Phase 14):** `backfill=True` fills pre-min_periods rows with the first estimate (`forecast_scalar.py:47-48`). NOT CLASSIFIED.
- **Evidence:** A04, A05, R01 VERIFIED. **Tier:** 1.

### 7.4 FDM

- **Existence:** yes. See **Card 8**.
- **Summary:** `FDM = min(1/√(wᵀCw), 2.5)` per fit period, EWM(125)-smoothed. C is the pooled correlation of weekly forecast *levels* (§7.2). Fixed default 1.0; estimation OFF by default. Applied before the combined-forecast cap.
- **Documented vs implemented:** consistent (`backtesting.md:2468-2535,3421-3467`).
- **Assumptions:** correlation of forecast levels is an adequate proxy for the correlation of the positions they generate; weights at `period_start` are representative.
- **Evidence:** A08 VERIFIED; R04 **INFERRED** (U5). **Tier:** 1.

### 7.5 IDM

- **Existence:** yes. See **Cards 10–11**.
- **Summary:** the same DM formula applied to instrument weights and to the correlation of **weekly subsystem P&L** (`portfolio.py:376-420`; `instrument_correlation_estimate`: expanding, ew_lookback 25, floor_at_zero). Fixed default 1.0; estimation OFF by default. Weights are zeroed and renormalised for instruments without positions, without adjusting the IDM (DOCUMENTED, `backtesting.md:2648`).
- **Assumptions:** subsystem-return correlation describes portfolio diversification; the `dm_max` of 2.5 bounds leverage.
- **Evidence:** P03 VERIFIED; R07 **INFERRED** (U5). **Tier:** 1.

### 7.6 Volatility estimation and long-run blending

- **Existence:** yes. See **Card 7**.
- **Summary:** `vol = 0.7 × EWMstd_35d + 0.3 × EWMmean(EWMstd_35d, span 10 × 256)`, with an absolute floor of 1e-10. This is price-difference vol on the back-adjusted daily (1B-last) price. Percentage vol divides by the raw contract price.
- **Documented vs implemented:** **DV7**. The docs name `robust_vol_calc` with a 5%-quantile/500-day floor as the default; the configured default is `mixed_vol_calc` with long-run blending and no quantile floor.
- **Assumptions:** daily data; the √256 annualisation convention (`positionsizing.py:480-484`); long-run blending with a 10-year slow component (EWM span 2560 business days). With shorter histories the slow component is itself an EWM over available data (INFERRED from `ewm` semantics, no min_periods on the slow EWM, `vol.py:170-171`).
- **Evidence:** R02 VERIFIED. **Tier:** 1.

### 7.7 Cost-based speed limits

- **Existence:** yes, in two forms:
  - (a) **rule exclusion by SR-cost ceiling** in the classic system (**Card 14**);
  - (b) a `get_speed_control` / shadow-cost mechanism in the dynamic optimisation system (`optimised_positions_stage.py:154-165`; `defaults.yaml` `small_system.shadow_cost: 50`, `tracking_error_buffer: 0.0125`). Form (b) is not read beyond its existence (P09, PARTIALLY AUDITED).
- **Summary of (a):** keep rule r for instrument i iff `turnover_full_sample(r) × SR_cost_per_trade(i) + holding_cost(i) ≤ ceiling`. `forecast_post_ceiling_cost_SR` (999) applies to fixed or estimated weights; `ceiling_cost_SR` (9999) applies before optimisation. **Effectively OFF by default.**
- **Documented vs implemented:** consistent in behaviour; **DV8** in key naming.
- **Assumptions:** cost drag is linear in turnover; turnover is stationary; end-of-sample cost levels.
- **Pre-flag (Phase 14):** full-sample turnover and last-year cost anchoring make the exclusion decision a whole-sample decision. NOT CLASSIFIED.
- **Evidence:** R11, R09 VERIFIED. **Tier:** 1.

### 7.8 Buffering

- **Existence:** yes. See **Card 12** (and Card 16 for live).
- **Summary:** forecast-method (default) width = 0.10 × |average position at forecast 10|. In the backtest the path trades to the edge (default), with rounding of the optimal position and both edges. In production only the last-row edges are stored, and order generation trades to `round(edge)` with trade-to-edge hard-coded.
- **Documented vs implemented:** **DV3** (live hard-codes trade-to-edge).
- **Assumptions:** a symmetric static band; integer contracts via rounding.
- **Evidence:** P05, P06, E04 VERIFIED. **Tier:** 1. *Implementation-location caveat:* P06 lives in `systems/accounts/*`.

### 7.9 Integer / lumpy position handling

- **Existence:** yes, in four places. All code read this phase or in Phase 5.

| Where | Mechanism (observed) | Evidence |
|---|---|---|
| Backtest buffered path | With `roundpositions=True` (the default in `pandl_for_instrument`), the optimal position and both edges are `.round()`ed before the buffer loop | `account_buffering_subsystem.py:141-144`; `account_instruments.py:19` |
| Backtest P&L | `_process_positions` rounds the (delayed) positions when `roundpositions` is on; the cash-cost path warns that `roundpositions=False` overstates fixed costs | `pandl_calculation.py:150-158`; `account_instruments.py:185-189` |
| Live order generation | `required_position = round(lower_or_upper_edge)` | `classic_buffered_positions.py:152-155` |
| Override application | `int(np.floor(desired_position × override_multiplier))`; floor, not round | `sysobjects/production/override.py:155-175` (floor at `:174`) |
| Dynamic optimisation (P09) | Greedy integer search: repeatedly add or subtract one contract per instrument while the objective improves (`greedy_algo.py:6-60`) | PARTIALLY AUDITED |

- **Documented behaviour:** "buffering can work on both rounded and unrounded positions. In the case of rounded positions we round the lower limit of the buffer, and the upper limit" (`backtesting.md:2688`); per-trade commission needs `roundpositions=True` (`:3045`). DOCUMENTED.
- **Implemented behaviour:** consistent. Python `round()` / pandas `.round()` use round-half-to-even (INFERRED from language semantics, not tested), whereas overrides use `floor`. So override-scaled positions truncate toward −∞ for long and short positions alike (INFERRED from `np.floor` semantics).
- **Assumptions:** positions are whole contracts. The classic system has no minimum-position or small-account logic outside P09.
- **Evidence:** VERIFIED (code read); rounding-mode consequences INFERRED. **Tier:** covered by Tier 1 Cards 12/16 and Tier 2 P09.

### 7.10 Production overrides and limits

- **Existence:** yes. There are three live controls, all applied **downstream of the System** in production order handling. None exists in the backtest; searched `systems/` for `override` and `position_limit`, with no match in the backtest stages (INFERRED absence, limited search).
- **(a) Overrides**, `sysobjects/production/override.py`:
  - Values: a float in [0, 1] (multiplier), `Close` (= 0), `No trading`, `Reduce only`, `No override` (= 1).
  - Combination with `*`: the most restrictive object wins; float multipliers multiply (`:134-147`).
  - Application to a proposed instrument trade (`:102-132,155-215`):
    - float: new position = `floor(desired × m)`;
    - reduce-only: sign flips become a pure close, increases become 0;
    - no-trading: trade = 0.
  - Sources: the DB plus config-derived overrides for instruments marked bad, duplicate, ignored or untradeable (`sysproduction/data/controls.py:233-290`; DOCUMENTED `docs/instruments.md:363-374`: "We always apply the most conservative override").
  - Applied in `strategy_order_handling.py:113-170` before position limits.
- **(b) Position limits**, `sysobjects/production/position_limits.py`:
  - Per-instrument and per-instrument-strategy absolute contract limits.
  - A proposed single-leg trade is cut so that |position| ≤ limit (and trades reduce toward the limit if already above it; doctest `:136-150`).
  - The most conservative of the two resulting orders is taken (`sysproduction/data/controls.py:525-563`).
  - Applied after overrides (`strategy_order_handling.py:174-195`).
  - Observation: `positionLimit.minimum_position_limit` returns `other_position_limit.no_limit` (a bool) when `self.no_limit` is true (`position_limits.py:21-28`). Its effect depends on call sites, which were not traced: UNVERIFIED. Recorded as an observation only; not fixed.
- **(c) Trade limits**, `sysobjects/production/trade_limits.py`:
  - A maximum number of contracts traded per (instrument[, strategy]) over a rolling `period_days`, with reset logic (`:7-110`).
  - Applied when creating broker orders from contract orders (`sysexecution/stack_handler/create_broker_orders_from_contract_orders.py:137-170`).
  - DOCUMENTED (`docs/production.md:1191,1297`).
- **Documented behaviour:** overrides and trade control (`docs/production.md:2040-2056`; `docs/instruments.md:363-410`); position and trade limits in interactive controls (`docs/production.md:305`). DOCUMENTED.
- **Implemented behaviour:** consistent with the documentation for overrides, as observed. The docs describe the multiplier as applied to "the desired [position]"; the code applies `floor(desired × m)` to the desired *new position* (original position + proposed trade). Consistent.
- **Assumptions:** discretionary controls sit outside the systematic calculation. The backtest cannot reproduce live overrides or limits, so research/live differences arise whenever they bind (INFERRED).
- **Evidence:** VERIFIED (static; no production run, per spec §10). **Tier:** new inventory row **E06_PROD_OVERRIDES_LIMITS**, Tier 2 (EXECUTION).

### 7.11 Phase 6 summary of new findings

1. **DV10:** the optimisation docs say five methods; four are registered, and bootstrapping is documented as no longer implemented.
2. **Handcrafting:** a fixed binary clustering with a 0.5/0.5 split, a DM uplift per sub-portfolio, and an SR tilt that depends on years of data. `equalise_vols=False` is unsupported (enforced).
3. **Pooling:** all pooled estimators except the forecast scalar use **stacking with microsecond offsets**. The code states this is unsuitable for high-frequency data and destroys autocorrelation (code docstring).
4. **Forecast correlations** for the FDM are computed on weekly forecast **levels**, while instrument correlations for the IDM use weekly subsystem **returns**.
5. **Integer handling** mixes `round` (backtest, live buffers) and `floor` (overrides). Only P09 has integer-aware optimisation.
6. **Overrides, position limits and trade limits exist only in production**, downstream of the System. The backtest has no equivalent.
7. A `minimum_position_limit` return-type observation is recorded (effect UNVERIFIED).
8. **Speed control also exists in the dynamic system** (shadow cost, tracking-error buffer), not audited in depth (P09).
