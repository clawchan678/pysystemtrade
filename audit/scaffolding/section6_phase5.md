Canonical file: `pysystemtrade_framework_inventory.csv` (40 rows, validated after Phase 5). **Phase 5 status: COMPLETE.**

The CSV schema (spec §32) has no tier column. Tiers are recorded here only, so the schema is not altered.

### 6.1 Operator decisions carried into Phase 5 (approved at the Phase 4 gate)

- **FDM split.** A08 (FDM application) stays ALPHA because it sits in the forecast-combination pipeline. R04 (FDM estimation) stays RESEARCH because it is calibrated from forecast correlations and weights.
- **P06 buffered position is PORTFOLIO_RISK.** It is classified by semantic role. *Implementation-location caveat:* the path-dependent code lives under `systems/accounts/*`, the accounting stage, not in `systems/portfolio.py`.
- **E01 backtest P&L is EXECUTION.** *Qualification:* this is **simulated** execution (inferred fills from a position series, next-bar convention, modelled costs). It is not live broker execution. Live order generation and broker execution are E03/E04/E05.

### 6.2 Tier assignment (all 40 rows)

| Tier | Inventory IDs | Treatment |
|---|---|---|
| **Tier 1** (16 cards covering 27 IDs) | C01, C02, C03 · A01, A02 · A04 (+R01) · A05 · A06 · R02 · A08, R04 (+R03) · P01 · P02, P03 (+R06) · R07 · P05, P06 · E02 · R11 (+R09) · P04 · E04 (+E03) | Full card (§6.4). R01, R03, R06, R09 and E03 are covered inside the card of the component they calibrate or feed |
| **Tier 1 finding (not a component)** | SC | Signal Contract, §5 |
| **Tier 2** | C04, C05, D01, A03, A07, R05, R08, R10, P07, P08, P09, E01, E05 | CSV row + note (§6.3) |
| **Tier 3** | none of the 40 rows | Peripheral packages are not inventoried: `syslogging`, `syslogdiag`, `dashboard`, `sysproduction/reporting`, backup/cleaner scripts, `syscontrol` scheduling. They do not materially affect alpha, estimation, portfolio, risk or execution logic (INFERRED from package listing, §2) |

Card count: 16, within the ~15–20 guideline of spec §28. Combined cards are used where components share one implementation path. The count reflects cards, not IDs.

### 6.3 Tier 2 notes

| ID | Note | Evidence |
|---|---|---|
| C04 Config | Attribute-style `Config` object backed by YAML and dicts. Project defaults come from `defaults.yaml`; an optional private config is loaded in `system_init`. `get_element` raises `missingData` for absent keys, and that exception is how optional features (e.g. the risk overlay) are switched off. Default merging internals are not yet read (Phase 13). | `sysdata/config/configdata.py:103-115` VERIFIED; merge logic UNVERIFIED |
| C05 simData | Data interface seen by stages. `daily_prices` = back-adjusted price `resample("1B").last()`; `get_raw_price` is natural frequency; hourly prices are available. csv and db variants exist. | `sysdata/sim/sim_data.py:98-137`, `syscore/pandas/frequency.py:169-170` VERIFIED |
| D01 Price/roll data | Multiple prices, adjusted (Panama) prices and roll calendars are built by `sysinit` and production updaters. Back-adjustment is DOCUMENTED (`backtesting.md:1954`); the implementation is not read (Phase 10). | UNVERIFIED (impl) |
| A03 Provided rules | Library of rule functions (ewmac, carry, breakout, accel, momentum, mean reversion, relative momentum, factors). Each is a pure function of daily price, vol or carry series. They are the alpha-specific part being replaced in the swap analysis. | `systems/provided/rules/*.py`, e.g. `ewmac.py:79-120` VERIFIED |
| A07 Forecast mapping | Optional non-linear map applied instead of plain capping to the combined forecast. The docs state that it assumes a Gaussian raw forecast. Implementation parameters are not yet read. | `systems/forecast_mapping.py:6-94`; `backtesting.md:2536-2581` DOCUMENTED |
| R05 Forecast-weight optimisation | Default OFF. When on, it runs `genericOptimiser` (method `handcraft`) on forecast P&L (R10) with weekly frequency, expanding fit windows and SR costs. Optimiser internals are deferred to Phase 6 (handcrafted vs optimised). | `defaults.yaml:171-214`; `forecast_combine.py:554-660` INFERRED |
| R08 Fitting dates | Builds [fit_start, fit_end, period_start, period_end] windows. `fit_end = period_start`, so estimates apply only after their fit window (expanding, rolling or in-sample modes). | `sysquant/fitting_dates.py:181-201` VERIFIED |
| R10 Forecast P&L proxy | Converts a forecast to a notional position (forecast/10 × vol-targeted average position) and computes P&L with SR costs and `delayfill`. It feeds weight estimation and cost reporting. | `systems/accounts/account_forecast.py:225-329` VERIFIED |
| P07 Capital multiplier | `capital_multiplier` in the accounts stage scales notional positions to actual positions. The default is `syscore.capital.fixed_capital`. Compounding variants exist but are not read. | `portfolio.py:76-101,936-946`; `defaults.yaml` `capital_multiplier` VERIFIED (wiring) |
| P08 Long-only | Per-instrument list in config. Negative subsystem positions are set to 0. The default list holds placeholder names only. | `positionsizing.py:135-154` VERIFIED |
| P09 Dynamic optimisation | Alternative portfolio construction (greedy optimisation over integer contracts, with its own buffering). **PARTIALLY AUDITED**: listing only. | `systems/provided/dynamic_small_system_optimise/*` UNVERIFIED |
| E01 Backtest P&L | *Simulated execution.* Positions are shifted one row when `delayfill` is on (default), rounded when `roundpositions` is on, and fills are inferred from position changes at the aligned price. `calculate_pandl` = `pos.shift(1) × Δprice`. Full timing trace is Phase 16. | `pandl_calculation.py:141-158,223-235`; `pandl_using_fills.py:49-70`; `sysobjects/fills.py:63-90` VERIFIED |
| E05 Order stacks / algos / broker | Instrument → contract → broker order stacks, execution algos and IB client (`ib_async`). Downstream of position targets. Static listing only (Phase 19, optional). | `sysexecution/*`, `sysbrokers/IB/*` UNVERIFIED |

### 6.4 Tier 1 component cards

Conventions. "Doc" means repository documentation in `docs/`, not docstrings. Evidence tags follow spec §12. Case A/B verdicts are counterfactual; `swap_evidence` is kept separate from `impl_evidence`. All citations are `@ 8958c49`.

---

#### Card 1 — C03 System cache

- **Source / symbol:** `systems/system_cache.py`: `systemCache`, `cacheRef`, `calc_or_cache` (`:527-587`), `cache_ref` (`:589-640`), decorators `stage_access_cache_decorator` (`:718-750`), `base_system_cache` (`:753-782`), aliases `input/dont_cache/diagnostic/output` (`:785-792`).
- **Layer:** CROSS_LAYER (it memoises every stage's outputs in both backtest and production runs).
- **Purpose / problem solved:** avoids recomputing expensive whole-history series and estimates when many downstream calls request the same intermediate.
- **Failure mode prevented:** repeated slow estimation (bootstrapping, correlations), and inconsistency from recomputing the same quantity twice within one System.
- **Inputs:** the decorated function, the calling stage, positional and keyword arguments. **Outputs:** the cached value or a freshly computed one.
- **Formulation:** key = `(stage.name, func.__name__, instrument_code, keyname=str(other positional args), flags="k=v,...")`. The instrument code is the matching positional argument found by popping from the end (`:655-683`).
- **Configuration:** `backtest_compress` (pickle compression). Caching can be switched on or off per System (`set_caching_on/off`).
- **Update frequency:** on demand. Values persist for the life of the System object, or until deleted.
- **State:** **stateful** (a dict of `cacheElement` entries with `protected` and `not_pickable` flags).
- **Data dependencies:** none directly; it wraps stage methods.
- **Assumptions:** (i) cached functions are pure given their arguments; (ii) config and data are immutable after construction, because neither is part of the key.
- **Alpha-specific:** N.
- **Documented behaviour:** caching, protected items, deletion helpers, pickling, and "recreate the System after changing config or data" (`backtesting.md:1431-1640`). Mutated config is not seen because of caching (`:1452-1456`). DOCUMENTED.
- **Implemented behaviour:** as documented, plus three undocumented properties:
  - (a) `base_system_cache` ignores arguments (`use_arg_names=False`, `:774-776`), TESTED in EXP-02;
  - (b) the unpickled cache is not validated against the current config or data (`:230-265`), INFERRED;
  - (c) `input`/`dont_cache` methods recompute every call.
- **Doc/impl divergence:** Y (UD2: argument-blind base cache; not documented).
- **Case A:** survives unchanged. It memoises any pure whole-history function.
- **Case B:** survives partially. It can memoise a vectorised event series. It cannot support a rule that needs per-bar feedback of its own fills or positions, because the cache assumes stateless pure functions (SC4/SC5).
- **swap_evidence:** INFERRED. **impl_evidence:** VERIFIED.

#### Card 2 — C01 System + C02 Stage machinery

- **Source / symbol:** `systems/basesystem.py:System` (`:25-118`, instrument list `:151-390`); `systems/stage.py:SystemStage` (`:6-53`).
- **Layer:** CROSS_LAYER.
- **Purpose / problem solved:** a uniform container binding stages, data and config. It gives stages a shared namespace (`self.parent.<stage>`) and one cache.
- **Failure mode prevented:** ad-hoc wiring. A stage can be replaced by another with the same name and output methods (DOCUMENTED "stage API", `backtesting.md:1846-1890`).
- **Inputs:** `stage_list`, `simData`, `Config`. **Outputs:** a System with stage attributes and `get_instrument_list()`.
- **Formulation:** not applicable.
- **Configuration:** `instrument_weights` or `instruments` (universe), plus `duplicate_instruments`, `ignore_instruments`, `trading_restrictions` and `bad_markets` exclusion lists (`basesystem.py:289-371`).
- **Update frequency:** constructed once per run. Production constructs a new System per strategy run (`run_system_classic.py:52-71`).
- **State:** a System holds its cache (stateful). Stages hold a parent link; `Rules` also stores parsed rules outside the cache (`forecasting.py:106-127`).
- **Data dependencies:** `simData`; `length_of_history_in_days_for_instrument` for the short-history filter.
- **Assumptions:** stages interact only through method calls. Dependencies between stages are implicit, not declared.
- **Alpha-specific:** N.
- **Documented behaviour:** a System consists of stages, data and config (`backtesting.md:1283-1430`). DOCUMENTED.
- **Implemented behaviour:** as documented. The instrument universe resolves in order: config weights → `config.instruments` → data (`:205-222`). The optional `remove_short_history` filter uses full-sample history length (`:373-390`, default off). This is flagged for Phase 14/17.
- **Doc/impl divergence:** N identified.
- **Case A:** survives unchanged. **Case B:** survives unchanged as a container. The limitations sit in individual stages.
- **swap_evidence:** INFERRED. **impl_evidence:** VERIFIED.

#### Card 3 — A01 TradingRule + A02 Rules stage (trading-rule interface / forecast generation)

- **Source / symbol:** `systems/trading_rules.py:TradingRule` (`:21-170`; `call` `:98-111`); `systems/forecasting.py:Rules.get_raw_forecast` (`:77-104`), `trading_rules()` (`:106-127`), `process_trading_rules` (`:166-245`).
- **Layer:** ALPHA (pipeline entry).
- **Purpose / problem solved:** a uniform wrapper so any function over system-provided data becomes a named rule variation producing a raw forecast per instrument.
- **Failure mode prevented:** rule-specific plumbing in downstream stages. Downstream sees only `(instrument_code, rule_variation_name) → Series`.
- **Inputs:** a function (callable or dotted string), a `data` list of dotted system-method strings, `other_args` (kwargs; `_`-prefixed args are routed to data calls). **Outputs:** a raw forecast `pd.Series` (cached, `@output`).
- **Formulation:** `raw = pd.Series(replace_zeros_with_nan(f(*[m(instrument_code, **a) for m, a in data], **other_args)))`.
- **Configuration:** `trading_rules` in config (dict, list, TradingRule, tuple or string forms), or passed to `Rules(...)`.
- **Update frequency:** computed once per System over the whole history.
- **State:** stateless (SC4/SC5). Parsed rule objects are stored on the stage.
- **Data dependencies:** whatever system methods are named. Provided rules use `rawdata.get_daily_prices` and `rawdata.daily_returns_volatility`.
- **Assumptions:** the function is causal, i.e. the value at t uses data ≤ t. This is not enforced by the framework (SC11).
- **Alpha-specific:** N for the interface (A03 rules are Y).
- **Documented behaviour:** rules as function + data + kwargs; "Functions must return a Tx1 pandas dataframe" (`backtesting.md:509-546,2006-2098`). DOCUMENTED.
- **Implemented behaviour:** output is coerced by `pd.Series(result)` (`forecasting.py:102`), so a DataFrame raises (EXP-03). **Every exact 0.0 becomes NaN** (`trading_rules.py:109` → `strategy_functions.py:122-139`), TESTED in EXP-01.
- **Doc/impl divergence:** Y (DV1 return type; DV5 class location; UD1 zero handling not documented).
- **Case A:** survives unchanged. The call shape is generic.
- **Case B:** survives partially. The call shape accepts an event series, but zero-as-flat is destroyed (SC9). The Tx1 DataFrame form fails. Exits must be derived inside the rule from price data only, because there is no position or fill feedback.
- **swap_evidence:** INFERRED; the zero mechanism is TESTED (EXP-01). **impl_evidence:** VERIFIED.

#### Card 4 — A04 Forecast scaling (+R01 forecast-scalar estimation)

- **Source / symbol:** `systems/forecast_scale_cap.py`: `get_scaled_forecast` (`:76-106`), `get_forecast_scalar` (`:143-156`), fixed scalar (`:366-452`), estimated scalar (`:166-282`), cross-sectional forecasts (`:288-320`); `sysquant/estimators/forecast_scalar.py:forecast_scalar` (`:5-50`).
- **Layer:** ALPHA (application); R01 estimation is RESEARCH.
- **Purpose / problem solved:** puts forecasts from heterogeneous rules on a common scale, so that an average absolute value of 10 means "average conviction".
- **Failure mode prevented:** rules with different natural units dominating the combination or producing arbitrary position sizes.
- **Inputs:** raw forecast; scalar (fixed or estimated). **Outputs:** scaled forecast Series.
- **Formulation:** `scaled = raw × scalar`.
  - Fixed: `scalar = trading_rules[r].forecast_scalar`, else `forecast_scalars[r]`, else `forecast_scalar` (default 1.0; `defaults.yaml:125`).
  - Estimated: `x_t = median_i |f_{i,t}|` over pooled instruments (zeros set to NaN, cross-section forward-filled); `scalar_t = 10 / mean(x_{≤t})` with window 250000 (effectively expanding) and min_periods 500; `backfill=True` fills the pre-min_periods region with the first estimate (`forecast_scalar.py:30-48`).
- **Configuration:** `use_forecast_scale_estimates` (default False), `forecast_scalar_estimate` {pool_instruments True, window, min_periods, backfill True}, `average_absolute_forecast` 10 (`defaults.yaml:125-143`).
- **Update frequency:** daily series (expanding estimate at every row of the forecast index). The fixed scalar is constant.
- **State:** the estimated scalar is a cached **protected** estimate (`:166-167,234-235`).
- **Data dependencies:** raw forecasts of all instruments using the rule (when pooled); `get_instrument_list`.
- **Assumptions:** |forecast| has a stable long-run mean; pooling across instruments is valid; zeros are uninformative.
- **Alpha-specific:** N.
- **Documented behaviour:** scale so the average absolute value is right; pooled estimation is the default (`backtesting.md:2388-2460`); target 10 (`introduction.md:355`). DOCUMENTED.
- **Implemented behaviour:** as documented, plus the backfill of the first estimate (source comment "SLIGHTLY CHEATING", `forecast_scalar.py:10`) and zero exclusion. VERIFIED.
- **Doc/impl divergence:** N identified for scaling itself (backfill not checked against docs; Phase 14). Stale doctests: DV6.
- **Case A:** survives unchanged. A new scalar is fixed or re-estimated with the same method.
- **Case B:** survives partially. The scalar is estimated on non-zero bars only, so a sparse signal is scaled to |10| while active. The scalar no longer represents average risk over time.
- **swap_evidence:** INFERRED. **impl_evidence:** VERIFIED.

#### Card 5 — A05 Forecast cap / floor

- **Source / symbol:** `systems/forecast_scale_cap.py:get_capped_forecast` (`:30-74`), `get_forecast_cap` (`:454-481`), `get_forecast_floor` (`:483-499`); combined-level cap `systems/forecast_combine.py:_cap_combined_forecast` (`:1376-1385`), `get_forecast_cap/floor` (`:1352-1374`).
- **Layer:** ALPHA.
- **Purpose / problem solved:** limits the influence of extreme forecasts. Applied per rule after scaling, and again to the combined forecast after FDM.
- **Failure mode prevented:** outsized positions from forecast outliers or scalar mis-estimation.
- **Inputs:** scaled forecast (or combined forecast). **Outputs:** clipped Series.
- **Formulation:** `clip(x, floor, cap)`; `cap = forecast_cap` (default 20); `floor = forecast_floor`, default `-cap`.
- **Configuration:** `forecast_cap` (`defaults.yaml:141`), `forecast_floor` (optional), forecast-mapping config for the combined level.
- **Update frequency:** constant parameters applied element-wise.
- **State:** stateless.
- **Data dependencies:** none.
- **Assumptions:** forecasts are on the scaled (avg |10|) scale, so ±20 means twice average conviction.
- **Alpha-specific:** N.
- **Documented behaviour:** "Cap forecasts at a maximum value" (`backtesting.md:2394-2396`); a cap of 20 is recommended (`introduction.md:355`). DOCUMENTED.
- **Implemented behaviour:** as documented. NaN passes through clip unchanged, so the zero→NaN values survive capping (EXP-01: capped NaN count = 3505). VERIFIED.
- **Doc/impl divergence:** N.
- **Case A:** survives unchanged.
- **Case B:** survives partially. For a fixed ±k signal the cap is either inactive (k ≤ 20) or truncates to a constant. Its purpose of limiting extreme conviction does not apply to a discrete signal.
- **swap_evidence:** INFERRED. **impl_evidence:** VERIFIED.

#### Card 6 — A06 Forecast combination

- **Source / symbol:** `systems/forecast_combine.py`: `get_combined_forecast` (`:55-108`), `get_combined_forecast_without_multiplier` (`:135-149`), `get_weighted_forecasts_without_multiplier` (`:151-169`), `get_forecast_weights` (`:171-193`), `get_unsmoothed_forecast_weights` (`:195-263`), `get_forecasts_given_rule_list` (`:436-458`), fixed weights (`:908-1006`), expensive-rule removal (`:503-548`); helpers `fix_weights_vs_position_or_forecast` and `weights_sum_to_one` (`syscore/pandas/strategy_functions.py:213-240,36-60`).
- **Layer:** ALPHA.
- **Purpose / problem solved:** blends several rule variations into one instrument forecast.
- **Failure mode prevented:** reliance on a single rule; weight jumps (EWM smoothing); rules without history receiving weight.
- **Inputs:** capped forecasts per rule; raw weights (fixed from config, 1/N if absent, or estimated via R05); FDM (A08). **Outputs:** combined forecast Series.
- **Formulation:**
  1. `F = ffill(concat(capped forecasts))`.
  2. Raw monthly weights are aligned to F, set to 0 where a rule's forward-filled forecast is NaN (i.e. before its first value), resampled to `1B` mean, smoothed with EWM (span `forecast_weight_ewma_span` = 125), then renormalised to sum to 1.
  3. `combined = Σ_r w_r × F_r`, then × FDM (reindexed, ffill), then capped or mapped.
- **Configuration:** `forecast_weights` (fixed, possibly auto-grouped), `use_forecast_weight_estimates` (False), `forecast_weight_ewma_span` 125, `forecast_post_ceiling_cost_SR` 999 (`defaults.yaml:171-182`).
- **Update frequency:** business-day weights; forecasts at their native index.
- **State:** stateless (cached).
- **Data dependencies:** capped forecasts, weights, FDM; SR costs if the speed limit is active.
- **Assumptions:** linear additivity of forecasts; each rule contributes on every bar after its first value (ffill); business-day smoothing.
- **Alpha-specific:** N.
- **Documented behaviour:** "We forward fill all forecasts. We then adjust forecast weights so that they are 1.0 in every period; after setting to zero when no forecast is available. Finally we multiply up, and apply the FDM. Then we cap." This is the method docstring (`forecast_combine.py:60-63`, a code comment, not `docs/`). Fixed and estimated weights are in `backtesting.md:2461-2535` (DOCUMENTED).
- **Implemented behaviour:** as described. Because of SC9, "no forecast available" also covers exact zeros, which are then forward-filled. TESTED (EXP-01).
- **Doc/impl divergence:** N for the combination formula; zero handling UD1.
- **Case A:** survives unchanged.
- **Case B:** partial; exits need redesign. Forward-filling holds the last non-zero forecast through intended flat periods (EXP-01: combined forecast constant at +10 over 3505 intended-flat bars). A linear blend of discrete signals yields fractional positions that no individual rule intended.
- **swap_evidence:** INFERRED; the ffill-through-zero mechanism is TESTED. **impl_evidence:** VERIFIED.

#### Card 7 — R02 Volatility estimation

- **Source / symbol:** `systems/rawdata.py:daily_returns_volatility` (`:153-219`), `get_daily_percentage_volatility` (`:242-270`), `daily_returns` (`:104-128`); `sysquant/estimators/vol.py:mixed_vol_calc` (`:121-181`).
- **Layer:** RESEARCH.
- **Purpose / problem solved:** an estimate of price-difference vol, used by rules (normalisation) and by position sizing (via percentage vol).
- **Failure mode prevented:** positions that ignore changing risk; jumps from purely short-window vol (slow-vol blend); division by zero (absolute minimum).
- **Inputs:** daily price differences of the back-adjusted, 1B-resampled price (`name_returns_attr_in_rawdata: daily_returns`). **Outputs:** daily vol Series in price units; percentage vol = 100 × vol / |denominator price| (raw contract price, `daily_denominator_price`).
- **Formulation:** `v = EWM-std(returns, span=35, min_periods=10)`; `slow = EWM-mean(v, span=10 × 256)`; `vol = 0.3 × slow + 0.7 × v`; floor at `vol_abs_min`; optional `backfill` (default False) (`vol.py:167-181`; `defaults.yaml:112-121`).
- **Configuration:** `volatility_calculation` {func mixed_vol_calc, days 35, min_periods 10, slow_vol_years 10, proportion_of_slow_vol 0.3, vol_abs_min 1e-10, multiplier_to_get_daily_vol 1.0}.
- **Update frequency:** business-daily.
- **State:** stateless (EWM over history; cached).
- **Data dependencies:** back-adjusted price; raw (denominator) price for percentage vol.
- **Assumptions:** daily returns; exponential weighting; blending with long-run vol improves stability. The function signature default (`slow_vol_years=20`) differs from the config (10), and the config wins.
- **Alpha-specific:** N.
- **Documented behaviour:** "The default function used is a robust EWMA volatility calculator" with `func: robust_vol_calc`, a 35-day span and a vol floor at the 5% quantile over 500 days (`backtesting.md:1947-1990`, also `:4198-4226`). DOCUMENTED.
- **Implemented behaviour:** the default is `mixed_vol_calc` (`defaults.yaml:113`). There is no quantile vol floor; there is a 30% blend with 10-year slow vol. VERIFIED.
- **Doc/impl divergence:** **Y**. DV7: the documented default function and floor differ from the configured default. DV4: stale docstring.
- **Case A:** survives unchanged (price-based). **Case B:** survives unchanged.
- **swap_evidence:** INFERRED. **impl_evidence:** VERIFIED.

#### Card 8 — A08 FDM application + R04 FDM estimation (+R03 forecast correlations)

- **Source / symbol:** application `forecast_combine.py:get_raw_combined_forecast_before_mapping` (`:111-131`), switch `:1008-1024`, fixed `:1026-1098`, estimated `:1100-1165`, correlations `:1167-1212,1254-1296`; `sysquant/estimators/diversification_multipliers.py:diversification_multiplier_from_list`, `diversification_mult_single_period`; R03 `sysquant/estimators/pooled_correlation.py` (not deep-read).
- **Layer:** A08 ALPHA; R04/R03 RESEARCH (operator-approved split).
- **Purpose / problem solved:** restores the combined forecast's average absolute value, which falls below 10 when imperfectly correlated forecasts are averaged.
- **Failure mode prevented:** systematic under-sizing caused by diversification across rules.
- **Inputs:** combined forecast without multiplier; forecast weights; forecast correlation matrices (pooled over instruments with the same rules; weekly; expanding). **Outputs:** FDM Series; multiplied combined forecast.
- **Formulation:** for each fit period, `FDM = min(1/√(wᵀ C w), dm_max = 2.5)`, using the latest weights up to and including `period_start` (label slice `weight_df[:start]`). The result is set to 1.0 if the risk is NaN or below 1e-7. It is reindexed to daily (ffill; leading NaN → 1.0) and EWM-smoothed (span 125). Applied as `combined × FDM` (ffill).
- **Configuration:** `forecast_div_multiplier` (fixed, default 1.0), `use_forecast_div_mult_estimates` (False), `forecast_div_mult_estimate` {ewma_span 125, dm_max 2.5}, `forecast_correlation_estimate` {pooled, W, expanding, ew_lookback 250, min_periods 20, cleaning, floor_at_zero} (`defaults.yaml:145-167`).
- **Update frequency:** correlations per fit period (the interval frequency is not read for forecasts; UNVERIFIED); FDM smoothed daily.
- **State:** correlation matrices are cached (`protected`, `not_pickable`).
- **Data dependencies:** capped forecasts of the pooled instruments; smoothed forecast weights.
- **Assumptions:** forecasts are comparable continuous series, so their correlation describes the diversification of the combined forecast; the weights are those in force at the period start.
- **Alpha-specific:** N.
- **Documented behaviour:** fixed or estimated FDM (`backtesting.md:2468-2535,3421-3467`). DOCUMENTED.
- **Implemented behaviour:** as above; the DM formula is VERIFIED (`diversification_multipliers.py`). Pooled correlation internals are INFERRED (not read).
- **Doc/impl divergence:** N identified.
- **Case A:** survives unchanged. The FDM is re-estimated or refixed for the new forecast correlations.
- **Case B:** survives partially. Correlations of held (ffilled) or sparse series are distorted, so the risk interpretation of the FDM is unclear.
- **swap_evidence:** INFERRED. **impl_evidence:** A08 VERIFIED; R04 **VERIFIED** (upgraded in Phase 5 after reading `diversification_multipliers.py`, see the §6.5 log); R03 INFERRED (unchanged).

#### Card 9 — P01 Position sizing (vol targeting)

- **Source / symbol:** `systems/positionsizing.py`: `get_subsystem_position` (`:86-133`), `get_average_position_at_subsystem_level` (`:164-204`), `get_instrument_value_vol` (`:206-246`), `get_instrument_currency_vol` (`:248-289`), `get_block_value` (`:291-326`), `get_daily_cash_vol_target` (`:480-485`), vol target dict (`:427-510`).
- **Layer:** PORTFOLIO_RISK.
- **Purpose / problem solved:** converts a forecast into contracts such that a forecast of 10 gives the annual cash-vol target for one instrument trading the whole capital (the "subsystem").
- **Failure mode prevented:** positions whose risk varies with instrument vol, contract size or FX.
- **Inputs:** combined forecast; daily % vol (R02); block value (price × multiplier × 1%); FX rate; capital and vol target. **Outputs:** subsystem position (contracts, unrounded).
- **Formulation:**
  - `daily_cash_vol_target = capital × pct_vol_target / 100 / √256`;
  - `instr_ccy_vol = block_value × daily_%vol`; `instr_value_vol = instr_ccy_vol × fx`;
  - `vol_scalar = daily_cash_vol_target / instr_value_vol`;
  - `position = vol_scalar × forecast / 10`;
  - long-only instruments are floored at 0.
- **Configuration:** `percentage_vol_target` 16, `notional_trading_capital` 1e6, `base_currency` USD (`defaults.yaml:221-223`), `long_only_instruments`.
- **Update frequency:** business-daily (the forecast index; the vol scalar is reindexed with ffill).
- **State:** stateless.
- **Data dependencies:** R02, prices, FX, instrument multipliers.
- **Assumptions:** fixed notional capital in this stage (compounding is handled later by P07); position is linear in the forecast; √256 annualisation.
- **Alpha-specific:** N.
- **Documented behaviour:** "scale our positions according to our percentage volatility target ... we treat our target, and therefore our account size, as fixed" (`backtesting.md:2607-2625`). DOCUMENTED.
- **Implemented behaviour:** as documented. VERIFIED.
- **Doc/impl divergence:** N.
- **Case A:** survives unchanged.
- **Case B:** survives partially. It can size a fixed-risk entry (±k → ±k/10 × average position), but the entry and exit timing it receives is corrupted upstream (SC9/SC10). It has no stop or target semantics.
- **swap_evidence:** INFERRED. **impl_evidence:** VERIFIED.

#### Card 10 — P02 Instrument weights + P03 IDM (+R06 instrument-weight estimation)

- **Source / symbol:** `systems/portfolio.py`: `get_notional_position_without_idm` (`:251-270`), `get_notional_position_before_risk_scaling` (`:231-249`), IDM switch/estimate/fixed (`:273-374`), `get_instrument_weights` (`:422-448`), fitted to positions (`:450-473`), raw weights (`:489-555`), estimated weights (`:622-700`); `sysquant/estimators/diversification_multipliers.py`.
- **Layer:** PORTFOLIO_RISK (application); R06 estimation is RESEARCH.
- **Purpose / problem solved:** allocates the risk budget across instruments (weights) and scales up to restore the portfolio vol target lost to cross-instrument diversification (IDM).
- **Failure mode prevented:** concentration and uncontrolled allocation; portfolio vol below target due to diversification.
- **Inputs:** subsystem positions; raw weights (fixed from config, equal if absent, or estimated); instrument correlation list (R07). **Outputs:** notional position before risk scaling.
- **Formulation:**
  - `w = renorm(EWM_125(resample_1B_mean(fix_weights_vs_position(w_raw, subsystem_positions))))`;
  - `notional = subsystem_pos × w_i × IDM`;
  - `IDM_t = EWM_125(min(1/√(wᵀ C w), 2.5))` per fit period, using weights up to `period_start`;
  - fixed IDM = `instrument_div_multiplier` (default 1.0).
- **Configuration:** `instrument_weights`, `use_instrument_weight_estimates` (False), `instrument_weight_ewma_span` 125, `instrument_weight_estimate` {handcraft, W, expanding, …}, `instrument_div_multiplier` 1.0, `use_instrument_div_mult_estimates` (False), `instrument_div_mult_estimate` {ewma_span 125, dm_max 2.5} (`defaults.yaml:230-290`).
- **Update frequency:** business-daily weights and IDM; estimated inputs per fit period.
- **State:** stateless (cached; correlation matrices protected).
- **Data dependencies:** subsystem positions and returns (via R07); P&L across subsystems for estimation.
- **Assumptions:** weights zeroed for instruments without positions and renormalised (docs note that the multiplier is *not* adjusted accordingly, `backtesting.md:2648`); the correlation of subsystem returns represents diversification.
- **Alpha-specific:** N.
- **Documented behaviour:** fixed or estimated weights and IDM; equal weights and IDM 1.0 if omitted (`backtesting.md:2626-2663`). DOCUMENTED.
- **Implemented behaviour:** as documented. Estimation internals (R06 optimiser) are not read, so R06 stays INFERRED.
- **Doc/impl divergence:** N identified.
- **Case A:** survives unchanged. **Case B:** weights survive unchanged; the IDM survives partially, because its correlation basis becomes subsystem returns of an event system with a different meaning (INFERRED).
- **swap_evidence:** INFERRED. **impl_evidence:** P02/P03 VERIFIED; R06 INFERRED (unchanged).

#### Card 11 — R07 Instrument correlation estimation (IDM and risk overlay inputs)

- **Source / symbol:** `sysquant/estimators/correlation_over_time.py`: `correlation_over_time_for_returns`, `correlation_over_time`; `sysquant/estimators/correlation_estimator.py`; `sysquant/estimators/generic_estimator.py` (`:30-140`); `sysquant/estimators/exponential_correlation.py` (`:124-190`); callers `portfolio.py:get_instrument_correlation_matrix` (`:376-420`, IDM) and `get_list_of_instrument_returns_correlations` (`:1082-1098`, risk).
- **Layer:** RESEARCH.
- **Purpose / problem solved:** a time series of correlation matrices, each estimated only from data before the period it applies to.
- **Failure mode prevented:** using contemporaneous or future correlations in the IDM or risk calculation (by construction of `fit_end`).
- **Inputs:** for the IDM, subsystem P&L (`pandl_across_subsystems`); for risk, instrument daily % returns. **Outputs:** `CorrelationList` (matrices + fit dates).
- **Formulation:** returns → cumulative index (ffill) → resample to `frequency` (IDM "W"; risk "7D") → diff. Fit dates come from `generate_fitting_dates` (expanding for the IDM, rolling 5y for risk). The exponential estimator computes EWM correlation over the whole dataset once, then takes the **last matrix with date strictly < `fit_end`** (`exponential_correlation.py:180-190`). Optional cleaning, floor-at-zero, clip and shrink follow.
- **Configuration:** `instrument_correlation_estimate` {W, expanding, ew_lookback 25, min_periods 20, cleaning True, floor_at_zero True}; `instrument_returns_correlation` {7D, rolling, rollyears 5, ew_lookback 75, clip 0.99, offdiag 0.0} (`defaults.yaml:237-247,311-324`).
- **Update frequency:** one matrix per fit period (interval frequency "12M" by default in `correlation_over_time`; "W" for the risk config).
- **State:** cached, protected, not picklable.
- **Data dependencies:** R02-based subsystem P&L; raw percentage returns.
- **Assumptions:** EWM correlation of weekly returns; cleaning replaces missing entries (the cleaning path takes `self.data`, and whether it uses future data is **UNVERIFIED**, deferred to Phase 14).
- **Alpha-specific:** N.
- **Documented behaviour:** "Estimating correlations and diversification multipliers" (`backtesting.md:3421-3467`). DOCUMENTED.
- **Implemented behaviour:** as above. The strict `< fit_end` selection is VERIFIED.
- **Doc/impl divergence:** N identified.
- **Case A:** survives unchanged. **Case B:** survives partially, because the IDM variant correlates event-system subsystem P&L (INFERRED). The risk variant uses price returns and survives unchanged.
- **swap_evidence:** INFERRED. **impl_evidence:** **VERIFIED** (upgraded in Phase 5 after reading the estimator sampling path, see §6.5); the cleaning path is UNVERIFIED.

#### Card 12 — P05 Buffer calculation + P06 buffered-position path

- **Source / symbol:** `systems/buffering.py` (`calculate_buffers` `:35-88`, forecast method `:90-118,146-173`, position method `:120-137`, none `:139-144`, `apply_buffers_to_position` `:25-32`); portfolio wiring `systems/portfolio.py:get_buffers_for_position` (`:125-154`), `get_buffers` (`:156-176`); path `systems/accounts/account_buffering_system.py:get_buffered_position` (`:54-98`); `systems/accounts/account_buffering_subsystem.py:apply_buffer` (`:106-165`), `apply_buffer_single_period` (`:167-208`).
- **Layer:** PORTFOLIO_RISK. **Implementation-location caveat (operator-approved):** the path-dependent logic (P06) lives in the accounting stage under `systems/accounts/*`, not in `systems/portfolio.py`. The portfolio stage computes only the buffer edges (P05).
- **Purpose / problem solved:** a no-trade zone around the optimal position to reduce turnover and costs.
- **Failure mode prevented:** trading on small changes in the optimal position (cost drag).
- **Inputs:** notional position; vol scalar; instrument weight; IDM; config. **Outputs:** P05 gives `top_pos`/`bot_pos` edges; P06 gives the buffered position series.
- **Formulation:**
  - forecast method: `width = buffer_size × |vol_scalar × w_i × IDM|` (the average position at forecast 10);
  - position method: `width = buffer_size × |position|`;
  - none: width = 0.001;
  - edges = `ffill(pos) ± ffill(width)`;
  - path: start at the first optimal position (NaN → 0). For each row, if the last position is above the top edge, go to the top edge (trade_to_edge) or to optimal; if below the bottom edge, go to the bottom edge or to optimal; otherwise hold. If any input is NaN, hold. With `roundpositions`, the optimal position and both edges are rounded first.
- **Configuration:** `buffer_method` forecast, `buffer_size` 0.10, `buffer_trade_to_edge` True (`defaults.yaml:296-298`).
- **Update frequency:** per row of the notional position index (business-daily).
- **State:** P05 stateless; **P06 stateful**, the only path-dependent loop in the backtest.
- **Data dependencies:** P01/P02/P03 outputs.
- **Assumptions:** a symmetric static width; trading to the edge reduces costs; integer contracts via rounding.
- **Alpha-specific:** N.
- **Documented behaviour:** position vs forecast buffering, recommended settings, rounding of limits; "in a live trading system buffering is done downstream of the system module" (`backtesting.md:2664-2700`). DOCUMENTED.
- **Implemented behaviour:** as documented in the backtest. Live: production reads only the last row of the P05 edges and order generation trades to `round(edge)` regardless of `buffer_trade_to_edge` (Card 16). VERIFIED.
- **Doc/impl divergence:** Y (DV3: live always trades to edge).
- **Case A:** survives unchanged.
- **Case B:** survives partially. A static width around a target jumping between 0 and ±k delays or truncates entries and exits (trade-to-edge). NaN inputs hold the last position.
- **swap_evidence:** INFERRED. **impl_evidence:** VERIFIED.

#### Card 13 — E02 Cost model (cash costs and SR costs)

- **Source / symbol:** `sysobjects/instruments.py:instrumentCosts` (`:244-360`: slippage, per-block, percentage and per-trade commission; `calculate_sr_cost`); `systems/accounts/pandl_calculators/pandl_cash_costs.py` (cost per fill, roll pseudo-fills, vol deflator); `pandl_SR_cost.py` (not deep-read); `systems/accounts/account_costs.py` (SR cost per trade `:295-340`, holding cost `:183-188`); `syscore/pandas/strategy_functions.py:calculate_cost_deflator` (`:164-172`).
- **Layer:** EXECUTION (simulated cost model; not broker-reported costs).
- **Purpose / problem solved:** deducts realistic trading and rolling costs from backtest P&L, and expresses costs in SR units for rule and weight decisions.
- **Failure mode prevented:** overstated net performance; selecting rules that are too expensive to trade.
- **Inputs:** fills inferred from buffered, rounded positions (E01); instrument cost metadata (spread, commissions); prices; rolls per year. **Outputs:** cost series (cash) or an annual SR drag (SR method).
- **Formulation:**
  - Cash cost per fill = `|qty| × slippage × multiplier` + `max(per_block × |qty|, per_trade, pct × |qty| × price × multiplier)`.
  - Rolling costs: at `rolls_per_year` equally spaced dates, open and close pseudo-fills of the average |position| over the prior period × `multiply_roll_costs_by` (0.5).
  - With `vol_normalise_currency_costs` (default **True**), costs are multiplied by `vol_180d(t) / vol_180d(last date of the sample)`.
  - SR cost per trade = cost of one block at the **average price of the last year of data** / (annual price vol averaged over the **last year of data** × multiplier). SR drag = turnover × SR cost per trade + 2 × rolls_per_year × SR cost per trade.
- **Configuration:** `use_SR_costs` False, `vol_normalise_currency_costs` True, `multiply_roll_costs_by` 0.5 (`defaults.yaml:300-302`), `forecast_cost_estimates` {use_pooled_costs False, use_pooled_turnover True}.
- **Update frequency:** per fill (cash); a single constant (SR cost per trade).
- **State:** stateless (cached pseudo-fill lists on the calculator object).
- **Data dependencies:** instrument config CSV (costs, multipliers), spread data, prices, R02.
- **Assumptions:** linear slippage in contracts (no market impact); costs scale with price vol over history; current (end-of-sample) cost levels are representative.
- **Alpha-specific:** N.
- **Documented behaviour:** SR vs actual costs; SR costs are always used for forecasts; actual costs are "normally standardised for historic volatility" (`vol_normalise_currency_costs`); cost components listed (`backtesting.md:3025-3077,4640-4657`). DOCUMENTED.
- **Implemented behaviour:** as documented. The deflator and the SR cost per trade are anchored to the **end of the sample** (`strategy_functions.py:168-170`; `account_costs.py:319-340`). This is VERIFIED static; its causal classification is deferred to Phase 14 (pre-flag, not yet classified).
- **Doc/impl divergence:** Y (minor, DV9). The docs name the config key `forecast_cost_estimate` (`backtesting.md:3073,3285,4654`); code and defaults use `forecast_cost_estimates` (`account_costs.py:58-59,215`, `defaults.yaml`).
- **Case A:** survives unchanged. **Case B:** survives unchanged as a cost-per-quantity model. The quantities it is fed are distorted upstream, and there is no intrabar or stop-order cost model.
- **swap_evidence:** INFERRED. **impl_evidence:** **VERIFIED** (upgraded in Phase 5 from UNVERIFIED after reading `instruments.py`, `pandl_cash_costs.py` and `account_costs.py`, see §6.5); `pandl_SR_cost.py` internals are not read.

#### Card 14 — R11 Speed limit / cost ceiling (+R09 turnover)

- **Source / symbol:** `systems/forecast_combine.py`: `_remove_expensive_rules_from_weights` (`:529-548`), `cheap_trading_rules_post_processing` (`:744-764`), `cheap_trading_rules` (`:766-786`), `_cheap_trading_rules_generic` (`:788-832`), `get_SR_cost_for_instrument_forecast` (`:834-864`); `systems/accounts/account_costs.py` (forecast turnover `:211-293`); `syscore/pandas/strategy_functions.py:turnover` (`:11-33`).
- **Layer:** RESEARCH.
- **Purpose / problem solved:** excludes rule variations whose expected annual cost in SR units exceeds a ceiling. It applies after weights are fixed or estimated (`forecast_post_ceiling_cost_SR`) and, separately, before optimisation (`ceiling_cost_SR`).
- **Failure mode prevented:** allocating to fast rules whose costs consume their expected return.
- **Inputs:** capped forecasts; SR cost per trade (E02). **Outputs:** the list of cheap rules; forecast weights restricted to cheap rules (then renormalised downstream).
- **Formulation:**
  - `turnover = 256 × mean(|Δ(forecast_1B / 10)|)`, a **single full-sample number**, optionally pooled across instruments with the same rules (length-weighted);
  - `SR_cost = turnover × SR_cost_per_trade + holding_cost`;
  - keep a rule iff `SR_cost ≤ ceiling`. If none survive, all weights are set to 0 and a warning is logged.
- **Configuration:** `forecast_post_ceiling_cost_SR` 999; `forecast_weight_estimate.ceiling_cost_SR` 9999 (`defaults.yaml:182,190`). Both are effectively OFF by default.
- **Update frequency:** a static decision over the whole backtest (one float per instrument/rule).
- **State:** stateless.
- **Data dependencies:** forecasts, instrument costs, R02, prices.
- **Assumptions:** cost drag is proportional to forecast turnover; turnover is stationary; daily resampling.
- **Alpha-specific:** N.
- **Documented behaviour:** `ceiling_cost_SR` and "`post_ceiling_cost_SR` can be used to remove rules that are too expensive" (`backtesting.md:3264-3290,3419`). DOCUMENTED.
- **Implemented behaviour:** as described. The config key is `forecast_post_ceiling_cost_SR`. Turnover and SR cost are full-sample and end-of-sample quantities (VERIFIED static; causal classification deferred to Phase 14).
- **Doc/impl divergence:** Y (DV8: the documented key `post_ceiling_cost_SR` vs the code key `forecast_post_ceiling_cost_SR`).
- **Case A:** survives unchanged.
- **Case B:** survives partially. Turnover measured on forward-filled (held) series understates the true turnover of an event system, so costs are understated and rules pass the ceiling too easily.
- **swap_evidence:** INFERRED. **impl_evidence:** VERIFIED (R11, R09).

#### Card 15 — P04 Risk overlay

- **Source / symbol:** `systems/risk_overlay.py:get_risk_multiplier` (`:4-73`), `multiplier_given_series_and_limit` (`:76-86`); `systems/portfolio.py:get_risk_scalar` (`:948-969`), risk inputs (`:971-1160`), application in `get_notional_position` (`:178-229`).
- **Layer:** PORTFOLIO_RISK.
- **Purpose / problem solved:** a portfolio-wide multiplier in [0, 1] that scales all positions down when estimated risk, shocked-vol risk, the sum of absolute risk, or leverage exceeds limits.
- **Failure mode prevented:** "Expected risk that is too high; weird correlation shocks combined with extreme positions; jumpy volatility" (docstring, `risk_overlay.py:19-23`).
- **Inputs:** original (pre-overlay) portfolio weights; instrument % vol (normal and shocked); instrument-returns correlation list (R07 risk variant); leverage; `percentage_vol_target`. **Outputs:** risk scalar Series applied to notional positions.
- **Formulation:** for each measure m with limit L (`max_risk_fraction_normal_risk × target/100`, `max_risk_fraction_stdev_risk × target/100`, `max_risk_limit_sum_abs_risk × target/100`, `max_risk_leverage`): `mult_m = L / max(L, m_t)`. Then `scalar = min_m mult_m`.
- **Configuration:** `risk_overlay` block. It is **commented out in `defaults.yaml:305-309`**, so `get_element` raises `missingData` and `get_notional_position` skips the overlay (`portfolio.py:214-219`). The overlay is **OFF by default**.
- **Update frequency:** per row of the common portfolio-weight index (daily).
- **State:** stateless (computed from position and risk series).
- **Data dependencies:** P01–P03 positions, R02, R07.
- **Assumptions:** proportional de-risking across all instruments; a vol-shock model (`seriesOfStdevEstimates.shocked()`, not read).
- **Alpha-specific:** N.
- **Documented behaviour:** only a passing mention in `docs/` ("risk overlays", `backtesting.md:1656`). Searched `docs/*.md` for `risk overlay|risk_overlay`. **NOT_DOCUMENTED** in `docs/` (the behaviour is described only in the code docstring).
- **Implemented behaviour:** as above. `calc_portfolio_risk_series` internals are not read (UNVERIFIED detail).
- **Doc/impl divergence:** UNKNOWN (no documentation to diverge from).
- **Case A:** survives unchanged. **Case B:** survives unchanged. It operates on positions and price risk; the positions it receives inherit upstream distortions.
- **swap_evidence:** INFERRED. **impl_evidence:** **VERIFIED** for the overlay formula and wiring (upgraded in Phase 5 from UNVERIFIED, see §6.5); risk-series internals UNVERIFIED.

#### Card 16 — E04 Live order generation (+E03 production system runner)

- **Source / symbol:** `sysproduction/strategy_code/run_system_classic.py` (`runSystemClassic.run_backtest` `:52-71`, `production_classic_futures_system` `:123-143`, `updated_buffered_positions` `:146-174`, `get_position_buffers_from_system` `:176-183`, `construct_position_entry` `:186-200`); `sysexecution/strategies/classic_buffered_positions.py` (`get_required_orders` `:36-46`, `get_optimal_positions` `:48-118`, `trade_given_optimal_and_actual_positions` `:141-200`).
- **Layer:** EXECUTION (**live** order generation, as distinct from E01's simulated fills).
- **Purpose / problem solved:** turns the latest backtest output into target position bands, then into instrument orders given actual current positions.
- **Failure mode prevented:** trading within the buffer; divergence between the research calculation and the live calculation (the same System code is reused).
- **Inputs:** a fresh System built from the production sim-data wrapper, the strategy config and current capital (`dataCapital`); the stored optimal positions; actual positions. **Outputs:** stored `bufferedOptimalPositions` (lower, upper, reference price, contract, date); a list of instrument orders.
- **Formulation:**
  - E03: `lower, upper = system.portfolio.get_buffers_for_position(code).iloc[-1]`, i.e. the **notional** position edges, with capital injected as `notional_trading_capital`.
  - E04: if `actual < lower` then target = `round(lower)`; if `actual > upper` then target = `round(upper)`; else no trade. The order is `target − actual`.
- **Configuration:** strategy config file, capital, and production control config.
- **Update frequency:** per production run (daily scheduling via `syscontrol`, not read).
- **State:** **stateful**: persisted optimal positions, actual positions and order stacks (database).
- **Data dependencies:** production price and FX data, capital, positions (MongoDB/Parquet, not connected in this audit).
- **Assumptions:** daily re-run; the last row of the backtest is the live decision; trade to the rounded edge.
- **Alpha-specific:** N.
- **Documented behaviour:** "in a live trading system buffering is done downstream of the system module, in a process which can also see the actual current positions" (`backtesting.md:2698-2700`); the production docs are not read (Phase 19). DOCUMENTED (partial).
- **Implemented behaviour:** as above. Trade-to-edge is **hard-coded** (`classic_buffered_positions.py:152-155`) while the backtest honours `buffer_trade_to_edge`. VERIFIED.
- **Doc/impl divergence:** Y (DV3; DV2 "no live system" statement).
- **Case A:** survives unchanged.
- **Case B:** survives partially. It propagates the same upstream semantics (held forecasts, bands) and has no entry/exit, stop or target order channel at this layer.
- **swap_evidence:** INFERRED. **impl_evidence:** VERIFIED (static; no production run, per the safety rules).

### 6.5 Phase 5 evidence-change log (explicit; nothing upgraded silently)

Each change below is backed by source read during Phase 5. No HYPOTHESIS or INFERRED *claim* was promoted to VERIFIED. Only the `impl_evidence` of components whose code was newly inspected changed.

| ID | Field | Phase 4 → Phase 5 | Basis |
|---|---|---|---|
| R04 | impl_evidence | INFERRED → VERIFIED | Read `sysquant/estimators/diversification_multipliers.py` (DM formula, period weights, smoothing) |
| R07 | impl_evidence | INFERRED → VERIFIED | Read `correlation_over_time.py`, `generic_estimator.py:30-140`, `exponential_correlation.py:124-190` (strict `< fit_end`). Cleaning path remains UNVERIFIED |
| P04 | impl_evidence | UNVERIFIED → VERIFIED | Read `risk_overlay.py` and `portfolio.py:178-229,948-1160`; the default-off mechanism is confirmed via `defaults.yaml:305-309` and `configdata.py:103-108` |
| P04 | stateful | UNKNOWN → N | Computed from position and risk series; no persisted state in the backtest |
| P04 | doc_status | DOCUMENTED → NOT_DOCUMENTED | `docs/*.md` searched for `risk overlay\|risk_overlay`: one passing mention only (`backtesting.md:1656`). **Correction of a Phase 4 labelling error** |
| E02 | impl_evidence | UNVERIFIED → VERIFIED | Read `instruments.py:244-360`, `pandl_cash_costs.py`, `account_costs.py`, `strategy_functions.py:164-179` (`pandl_SR_cost.py` not read) |
| E02 | divergence | UNKNOWN → Y | DV9 config-key name |
| R11 | divergence | UNKNOWN → Y | DV8 config-key name |
| R02 | divergence | Y (DV4) | Unchanged value; DV7 added as a further basis |
| (all Tier 1 rows) | last_phase | 4 → 5 | Card written |

Unchanged on purpose: R03, R05 and R06 stay INFERRED (optimiser and pooled-correlation internals not read). D01, P07, P09 and E05 stay UNVERIFIED. All `swap_evidence` values are unchanged (INFERRED; EXP-01 remains the only TESTED mechanism and is labelled as such in the cards).
