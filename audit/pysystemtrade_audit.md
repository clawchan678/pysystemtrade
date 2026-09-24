# pysystemtrade — Architectural & Methodological Audit

Audited commit: `pst-group/pysystemtrade` @ **`8958c49`** (`8958c49c38b1e4a8c07f0e4375d5e9cb68a087f7`, branch `develop`).
All citations below are `path:lines @ 8958c49` unless stated otherwise.
Evidence tags: VERIFIED / DOCUMENTED / INFERRED / HYPOTHESIS / UNVERIFIED (spec §12). The counterfactual tag `swap_evidence` is kept separate (spec §13).

Status: **P0 Phases 1–4 complete; STOPPED at the Phase 4 review gate.**

---

## Executive Summary (pre-P2; max 20 bullets)

1. **Architecture.** A `System` is a container of named `SystemStage` objects plus one `simData` and one `Config`. Each stage computes **whole-history pandas time series on demand** (a lazy, pull-based tree) and memoises them in a per-System cache. VERIFIED (`systems/basesystem.py:42-118`, `systems/system_cache.py:527-587`).
2. **Pipeline.** The standard pipeline is rawdata → rules → forecastScaleCap → combForecast → positionSize → portfolio → accounts. VERIFIED (`systems/provided/futures_chapter15/basesystem.py`). Buffering is split: the portfolio stage computes the buffer edges, and the path-dependent buffered position exists only in the accounts stage (backtest) or in production order generation (live). VERIFIED.
3. **Caching.** Cache keys are (stage, method name, instrument code, stringified positional args, kwargs). **Config and data are not part of the key**, so changing config after computation returns stale values. This is DOCUMENTED (`docs/backtesting.md:1452-1456`) and VERIFIED in code.
4. **Base-system cache ignores arguments.** Methods decorated with `base_system_cache` (e.g. `System.get_instrument_list`) are keyed with `use_arg_names=False`, so later calls with different arguments return the first cached result. VERIFIED + TESTED (EXP-02). NOT_DOCUMENTED.
5. **Protected items.** Slow estimates (e.g. forecast scalars) are cached as "protected" and survive `delete_all_items()` by default. This is a DOCUMENTED stale-state vector (`docs/backtesting.md:1590-1609`).
6. **Signal Contract (core).** A rule is `f(*data_series, **kwargs)` called once per (instrument, rule variation) over the full history. Its return value is coerced with `pd.Series(...)`. The forecast is signed (positive = long), continuous, scaled to an average absolute value of 10, and capped at ±20. Position is linear in the forecast. VERIFIED. Full contract in §5.
7. **Zero is not "flat".** `TradingRule.call` converts **every exact 0.0** in a rule's output to NaN (`syscore/pandas/strategy_functions.py:122-139`). Combination then forward-fills forecasts (`systems/forecast_combine.py:458`). The result: a rule that goes flat keeps its last non-zero forecast. TESTED (EXP-01: 3505 zero rows became a constant combined forecast of +10). NOT_DOCUMENTED.
8. **Rule return type divergence.** The docs say rule functions "must return a Tx1 pandas dataframe" (`docs/backtesting.md:544`). The implementation calls `pd.Series(result)` (`systems/forecasting.py:102`), which raises on a DataFrame under pandas 2.1.3. TESTED at the coercion step (EXP-03).
9. **Forecast-scalar estimation.** The estimate is an expanding mean (window 250000) of the cross-sectional median of |forecast|, with zeros excluded and `backfill=True` by default. The source comments this as "SLIGHTLY CHEATING" (`sysquant/estimators/forecast_scalar.py:10,44-48`). This is a pre-sample backfill; flagged for Phase 14. VERIFIED.
10. **Research defaults.** Every estimation switch defaults to OFF (fixed scalars, weights, FDM and IDM), and costs default to cash costs (`use_SR_costs: False`). VERIFIED (`sysdata/config/defaults.yaml:131,150,171,236,256,300`). The "speed limit" (rule removal by SR-cost ceiling) exists, but its default thresholds are 999/9999, i.e. effectively off (`defaults.yaml:182,190`). VERIFIED.
11. **Estimation windowing.** `generate_fitting_dates` sets `fit_end = period_start` for expanding and rolling fits (`sysquant/fitting_dates.py:181-201`). No causal violation was identified at the date-window level. Deeper checks come in Phase 14.
12. **Backtest fill timing.** With the default `delayfill=True`, positions are shifted one row, and `calculate_pandl` applies a second `shift(1)` against price differences. A position decided at close t therefore earns returns from close t+1 onward (`pandl_calculation.py:150-158,223-235`). VERIFIED static; the empirical trace is Phase 16.
13. **Frequency.** Provided rules and all calibration statistics assume business-day data: `resample("1B").last()` (`syscore/pandas/frequency.py:169-170`), weights resampled to 1B, turnover annualised by business days, and vol scaled by √(business days). VERIFIED. The P&L supports business-day or hourly positions; any other frequency hits a warning path (`systems/accounts/account_inputs.py:35-60`).
14. **Research/live coupling.** Production re-runs the same backtest `System` daily and stores `buffers.iloc[-1]` as the live optimal position band (`sysproduction/strategy_code/run_system_classic.py:146-183`). VERIFIED. Order generation then trades to `round(edge)`, with **trade-to-edge hard-coded** regardless of `buffer_trade_to_edge` (`sysexecution/strategies/classic_buffered_positions.py:141-160`). VERIFIED; the divergence from backtest behaviour applies when the config is False.
15. **Doc divergence.** The docs say "the project doesn't yet include a live trading system" (`docs/backtesting.md:1643`), but a full `sysproduction`/`sysexecution`/`sysbrokers` stack exists. VERIFIED.
16. **Stale docstrings.** `mixed_vol_calc` documents vol-floor parameters that are not implemented (`sysquant/estimators/vol.py:121-181`). Doctests reference non-existent classes (`ForecastScaleCapFixed`). The fixed forecast-scalar doctest expects a float while the method returns a Series. VERIFIED (minor).
17. **Testing status.** Only two targeted controlled experiments (EXP-01, EXP-02) and one coercion check (EXP-03) have run. The repo test suite has not been run yet (Phase 18).
18. **Evidence gaps.** Instrument weights/IDM, the risk overlay, cost-model internals, dynamic optimisation, and the production stack are classified only (see `audit_progress.md` G1–G5).

---

## 1. Audit Scope / Version / Provenance

- Target: https://github.com/pst-group/pysystemtrade. The default branch reported by Git is `develop`; `develop` is the audited branch. Pinned HEAD `8958c49` (2026-09-21), `git describe` `1.8.2-344-g8958c49c`, pyproject version 1.8.2. VERIFIED.
- README identity and history (moved to the pst-group org in January 2026, owned by Andy Geach and Rob Carver) match the intended target. DOCUMENTED (`README.md` "History").
- Audit date: 2026-09-24. Persistence Mode B (fork branch `clawchan678/pysystemtrade:claude/jolly-galileo-jv9j4g`, directory `audit/`). The fork HEAD equals upstream HEAD. The audit reads only the fresh scratch clone `audit/repo`.
- Environment: Python 3.11.15 venv; pandas 2.1.3, numpy 1.26.4 (pinned <2 by the auditor). Details are in `audit_progress.md`.
- Provenance discrepancy: the operator files `PYSYSTEMTRADE_AUDIT_MASTER.md` and `CLAUDE.md` were not on disk. The spec was taken from the session prompt.

## 2. Repository Architecture

Package sizes (Python files / lines) @ 8958c49: `systems` 106/19.4k · `sysproduction` 109/21.7k · `sysdata` 114/12.2k · `sysexecution` 42/9.3k · `sysobjects` 33/7.1k · `sysquant` 40/6.3k · `syscore` 34/5.8k · `sysbrokers` 45/5.6k · `sysinit` 35/4.0k · `syscontrol` 8/1.3k. VERIFIED.

| Area | Location | Role (evidence) |
|---|---|---|
| Data objects | `sysobjects/` (adjusted_prices, multiple_prices, roll_calendars, contracts, instruments, spot_fx_prices, spreads, fills) | Domain objects for futures data and state. VERIFIED (listing) |
| Data storage | `sysdata/{csv,parquet,mongodb,arctic,production,futures,fx}` | Storage back-ends. csv data is bundled in `data/futures`. VERIFIED (listing) |
| Ingestion / initialisation | `sysinit/futures/*` (build roll calendars, multiple and adjusted prices, seed from IB, Barchart) | One-off and batch data building. VERIFIED (listing) |
| Daily price updates | `sysproduction/update_historical_prices.py`, `update_multiple_adjusted_prices.py`, `update_fx_prices.py` | Production ingestion. VERIFIED (listing) |
| Sim data interface | `sysdata/sim/sim_data.py:simData`, `futures_sim_data.py`, `csv_futures_sim_data.py`, `db_futures_sim_data.py` | What stages see as `system.data`. `daily_prices` = `resample("1B").last()` of the back-adjusted price (`sim_data.py:98-127`). VERIFIED |
| Continuous futures / carry | back-adjusted price (`get_backadjusted_futures_price`), `rawdata.raw_carry` etc. (`systems/rawdata.py:456-635`) | Panama-stitched prices for returns; carry from multiple prices. DOCUMENTED (`backtesting.md:1954`) / VERIFIED (method existence) |
| Trading rules | `systems/trading_rules.py`, `systems/forecasting.py`, `systems/provided/rules/*` | Rule interface and provided rules |
| Forecast scaling/cap | `systems/forecast_scale_cap.py`, `sysquant/estimators/forecast_scalar.py` | |
| Forecast combination / FDM / mapping | `systems/forecast_combine.py`, `systems/forecast_mapping.py`, `sysquant/estimators/diversification_multipliers.py` | |
| Volatility | `systems/rawdata.py:daily_returns_volatility`, `sysquant/estimators/vol.py` | |
| Position sizing | `systems/positionsizing.py` | |
| Instrument weights / IDM / risk overlay | `systems/portfolio.py`, `systems/risk_overlay.py`, `systems/risk.py`, `sysquant/optimisation/*`, `sysquant/portfolio_risk.py` | |
| Buffering | `systems/buffering.py` (edges); `systems/accounts/account_buffering_*.py` (path) | |
| Accounting / P&L / costs | `systems/accounts/*`, `pandl_calculators/*`, `curves/*`, `order_simulator/*` | |
| Alternative portfolio construction | `systems/provided/dynamic_small_system_optimise/*` | Dynamic optimisation (PARTIALLY AUDITED) |
| Live strategy | `sysproduction/run_systems.py` → `strategy_code/run_system_classic.py` | Daily backtest re-run → optimal positions |
| Order generation / execution | `sysproduction/run_strategy_order_generator.py` → `sysexecution/strategies/*`; `sysexecution/{order_stacks,stack_handler,algos}` | Instrument → contract → broker order stacks |
| Broker | `sysbrokers/IB/*` (ib_async) | IB integration (static only; never connected) |
| Process control | `syscontrol/*` | Scheduling and monitoring |
| Configuration | `sysdata/config/configdata.py:Config`, `sysdata/config/defaults.yaml`, `private/private_config.yaml` (absent), per-system YAML (e.g. `systems/provided/futures_chapter15/futuresconfig.yaml`) | DOCUMENTED (`backtesting.md:963-1280`) |
| Logging | `syslogging/` | |
| Tests | `tests/`, `*/tests/`, doctests (pyproject `--doctest-modules`, selected `testpaths`) | Phase 18 |

**Entry points.** Backtest: `systems.provided.futures_chapter15.basesystem.futures_system()` (and other `systems/provided/*`). Production: `sysproduction/run_*.py` scripts under `syscontrol` scheduling. VERIFIED (listing and code).
**Engines.** The simulation engine is the System/Stage tree (vectorised, whole-history). There is no separate event loop; the only per-period loop is the buffer application (`account_buffering_subsystem.py:106-165`). The live engine is a daily re-run of the same System, followed by stack-based execution. INFERRED from the inspected code; Phase 9 will confirm.

## 3. System / Stage / Caching Architecture (Tier 1)

**System** (`systems/basesystem.py:25-118`), VERIFIED:
- Constructor inputs are `stage_list`, `data: simData` and `config: Config`. It calls `config.system_init()` and `data.system_init(self)`, then attaches each stage as an attribute named `stage.name`, with duplicate names rejected (`:85-118`). Finally it creates `systemCache(self)`.
- Its only "own" logic is instrument-universe selection: `get_instrument_list` reads config `instrument_weights` → `config.instruments` → `data.get_instrument_list()` (`:205-222`), then applies removal filters for duplicates, ignored, bad-market, trading-restriction and short-history instruments (`:289-322`).
- Methodological flag: `get_list_of_short_history` uses `data.length_of_history_in_days_for_instrument` over the full dataset (`:373-390`). If enabled (default `remove_short_history=False`), instrument selection would use future information. Flag for Phase 14/17. INFERRED.

**Stage** (`systems/stage.py:6-53`), VERIFIED. A stage is a plain object with a `name`, a parent link set in `system_init`, and a logger. Stages communicate only by calling `self.parent.<other_stage>.<method>(instrument_code, ...)`. DOCUMENTED as input / diagnostic / output "wiring" (`docs/backtesting.md:1846-1890`). Dependencies are therefore implicit method calls, not declared.

**Cache** (`systems/system_cache.py`), VERIFIED:
- Decorators: `input = dont_cache = null_decorator`; `diagnostic = output = stage_access_cache_decorator` (`:785-792`). "Input" methods are *not* cached; outputs and diagnostics are.
- Key: `cacheRef(stage_name, func.__name__, instrument_code, flags=str(kwargs), keyname=str(other positional args))` (`:589-640`). The instrument code is found by matching positional arguments against `system.get_instrument_list()` (`:643-683`).
- `calc_or_cache` returns the cached value when present, otherwise computes and stores it (`:527-587`). Caching can be switched off (`set_caching_off`).
- `protected=True` items (e.g. `_get_forecast_scalar_estimated`, `forecast_scale_cap.py:166-167`) survive `delete_*` calls unless `delete_protected=True` (`:443-457`).
- Pickling (`:196-265`) excludes `not_pickable` items (e.g. account curves, correlation lists).

**Lazy evaluation.** Nothing is computed at construction. Requesting a leaf (e.g. `portfolio.get_notional_position`) recursively pulls and caches every upstream series. DOCUMENTED (`backtesting.md:1435`) and VERIFIED.

**Cache invalidation / stale-state risks:**
- (i) Config and data are excluded from keys. Mutating `system.config` after computation returns stale results. DOCUMENTED (`backtesting.md:1452-1456`) and VERIFIED.
- (ii) Protected estimates persist across `delete_all_items()`. This is DOCUMENTED as intentional (`backtesting.md:1590-1609`), with a warning about implicit overfitting.
- (iii) `base_system_cache` uses `instrument_classify=False, use_arg_names=False` (`:753-782`). Every call to `get_instrument_list` or `get_list_of_markets_not_trading_but_with_data` shares one key regardless of arguments. TESTED (EXP-02). NOT_DOCUMENTED.
- (iv) `Rules.trading_rules()` parses rules once and stores them on the stage object (`forecasting.py:106-127`), outside the cache. Changing `config.trading_rules` after first use has no effect even after the cache is cleared. INFERRED from code.
- (v) The instrument-code match takes the *last* matching positional argument (it pops from the end), not the first as the docstring says (`:655-683`). INFERRED minor.
- (vi) The unpickled cache is not checked against the current config or data (`:230-265`). INFERRED.

**Reproducibility.** Results are a deterministic function of (code, config, data) *only if* the System is freshly constructed. The docs recommend recreating the System after any change (`backtesting.md:1435`). INFERRED.

**Live implications.** Production constructs a fresh System per run (`run_system_classic.py:52-71,123-143`), which avoids cross-run stale cache. The docs describe an intraday cache-deletion workflow (`backtesting.md:1641-1657`) that was not found wired into production. That is an absence claim: UNVERIFIED (searched only `sysproduction/strategy_code`).

**Reusable infrastructure.** System, Stage and cache are signal-agnostic memoisation over pure whole-history functions. INFERRED.

## 4. Alpha / Research / Portfolio_Risk / Execution Decomposition

Canonical machine-readable version: `pysystemtrade_framework_inventory.csv` (40 rows). Summary layer table:

| Layer | Components (inventory IDs) | Notes |
|---|---|---|
| ALPHA | A01 TradingRule.call · A02 Rules stage · A03 provided rules · A04 forecast scaling · A05 forecast cap/floor (individual + combined) · A06 forecast combination · A07 forecast mapping · A08 FDM application | Only **A03** is alpha-specific (Y). A01/A02/A04–A08 sit in the alpha pipeline but are signal-agnostic machinery (alpha_specific = N) |
| RESEARCH | R01 forecast-scalar estimation · R02 volatility estimation · R03 forecast correlation · R04 FDM estimation · R05 forecast-weight optimisation · R06 instrument-weight optimisation · R07 instrument correlation / IDM estimation · R08 fitting dates · R09 turnover / SR-cost estimates · R10 forecast P&L proxy · R11 cost-ceiling "speed limit" | All default OFF except R02 (always on) and R09/R10 (used when estimating or reporting) |
| PORTFOLIO_RISK | P01 position sizing (vol scalar) · P02 instrument-weight application · P03 IDM application · P04 risk overlay · P05 buffer edges · P06 buffered-position path (accounts stage) · P07 capital multiplier · P08 long-only · P09 dynamic optimisation | P06 is the only path-dependent step in the backtest |
| EXECUTION | E01 backtest P&L / simulated fills · E02 cost model · E03 production system runner · E04 order generation · E05 order stacks / algos / IB broker | E01/E02 are *simulated* execution |
| CROSS_LAYER | C01 System · C02 Stage · C03 cache · C04 config · C05 simData · D01 price/roll data · SC Signal Contract | Infrastructure or data used by every layer and by both backtest and production |

Classification rationale for the contested items:
- **Scaling, cap and combination are ALPHA by position, not by dependence.** None of them references a specific rule. They operate on any `pd.Series` (`forecast_scale_cap.py:30-106`, `forecast_combine.py:55-170`). VERIFIED.
- **FDM split.** The application is a scalar multiply inside combForecast (`forecast_combine.py:111-131`). The estimation uses forecast correlations and weights (`:1100-1165`), so it is RESEARCH. The spec's examples list FDM under PORTFOLIO_RISK; this is recorded as a classification uncertainty (U3).
- **P06 buffered position** lives in `systems/accounts/*` but is portfolio decision logic, so it is labelled PORTFOLIO_RISK. E01 P&L is labelled EXECUTION because it simulates fills and costs.

## 5. Signal Contract

Determined only from pysystemtrade @ 8958c49. It answers: *what must a rule satisfy for scaling, combination, sizing and buffering to function as designed?*

| # | Contract element | Observed contract | Evidence |
|---|---|---|---|
| SC1 | Call shape | `function(*data, **other_args)`. `data` is a list of dotted system-method strings (e.g. `"rawdata.get_daily_prices"`, `"rawdata.daily_returns_volatility"`). Each is called as `method(instrument_code, **data_args)`. The default data is the instrument price. | `systems/trading_rules.py:98-170`; `syscore/objects.py:70-89`; DOCUMENTED `backtesting.md:2006-2098` — VERIFIED |
| SC2 | Object / data type | The return value is passed through `replace_all_zeros_with_nan` and then `pd.Series(result)`. **A 1-D `pd.Series` with a `DatetimeIndex` is required in practice.** A Tx1 `DataFrame` (the documented type) fails coercion. Return type is annotated `pd.Series`. | `forecasting.py:77-104`; EXP-03 — VERIFIED / TESTED (coercion step) |
| SC3 | Instrument dimension | One series per (instrument_code, rule_variation_name). The rule is invoked separately for each instrument. Cross-sectional information must be fetched through data methods (e.g. `rawdata.normalised_price_for_asset_class`). | `forecasting.py:77-104`; `rawdata.py:416-441` — VERIFIED |
| SC4 | Evaluation mode | **Vectorised whole history.** The rule is called once and returns the entire history; the result is cached. There is no incremental or bar-by-bar call, and no state is passed between calls. | `forecasting.py:98-104`; `system_cache.py:527-587` — VERIFIED |
| SC5 | Statefulness | Stateless from the framework's view. The rule receives no current position, fill, P&L or entry price. There is no feedback path from accounts or execution back into rules. | Absence searched in `TradingRule._get_data_from_system` (`trading_rules.py:113-165`): the data comes only from system methods named in config. VERIFIED for the call path; any stage method could in principle be named as data, which is INFERRED |
| SC6 | Sign convention | Positive = long, negative = short. Position = `vol_scalar × forecast / avg_abs_forecast`. | `positionsizing.py:117-131` — VERIFIED |
| SC7 | Scale / range | The scaled forecast is expected to have an average absolute value of `average_absolute_forecast` (default 10). Scaling multiplies by a fixed scalar (default `forecast_scalar: 1.0`) or an estimated scalar `10 / expanding_mean(|x|)`. Individual forecasts are clipped to [floor, cap] (default ±20), as is the combined forecast after FDM. | `forecast_scale_cap.py:30-106,366-499`; `forecast_scalar.py:5-50`; `forecast_combine.py:1376-1385`; `defaults.yaml:125,141,143` — VERIFIED; DOCUMENTED `introduction.md:355`, `backtesting.md:2388-2400` |
| SC8 | Continuity / meaning | Economically, the forecast is continuous and proportional to expected risk-adjusted return ("normalise the forecast into something proportional to Sharpe Ratio"). Magnitude encodes conviction, and position is linear in it. Forecast mapping assumes a Gaussian raw forecast. The code accepts any float. | DOCUMENTED `backtesting.md:1954,2581`; linear sizing VERIFIED `positionsizing.py:128` |
| SC9 | **Zero semantics** | **Exact 0.0 is treated as missing**: every zero is replaced by NaN at the rule output. Zeros are also excluded from scalar estimation. After forward-filling (SC10), "flat" is represented as "hold the last non-zero forecast". A rule can only express flat as a small non-zero value. | `strategy_functions.py:122-139` (called at `trading_rules.py:109`); `forecast_scalar.py:33-35`; EXP-01 — TESTED. NOT_DOCUMENTED (docs searched for "zero"/"nan") |
| SC10 | Missing values | NaN is allowed. In combination, forecasts are **forward-filled** (`forecast_combine.py:458`). Rules whose history has not started get weight 0, and weights are renormalised to sum to 1 (`strategy_functions.py:213-240`, `:36-60`). Once a rule has started, later NaNs never remove its weight; it is held via ffill. The buffer path returns the last position when optimal or edges are NaN (`account_buffering_subsystem.py:194-195`). | VERIFIED |
| SC11 | Timing | The forecast value at timestamp t is interpreted as known at t (end of bar for daily 1B-last prices). Causality inside the rule is **the rule's responsibility**; the framework applies no lag at the rule stage. The lag is applied in P&L: with `delayfill=True` (default), exposure from a forecast at close t starts at close t+1. | `pandl_calculation.py:150-158,223-235`; `sim_data.py:125`; `frequency.py:169-170` — VERIFIED static (Phase 16 will trace empirically) |
| SC12 | Frequency | Provided rules and data are business-day. The framework reindexes weights, vol scalars, FDM and IDM onto the forecast index with ffill, so any `DatetimeIndex` passes mechanically. However, forecast weights are resampled to `"1B"` (`forecast_combine.py:258-260`), turnover is computed on a 1B resample × business days per year (`strategy_functions.py:11-33`), vol targets use √(business days) (`positionsizing.py:480-484`), and P&L price lookup accepts only business-day or hourly positions (otherwise a warning path, `account_inputs.py:35-60`). **Contract: daily (business-day) frequency is assumed by all calibration statistics.** | VERIFIED |
| SC13 | Continuous availability | Downstream assumes the forecast is always "on" once it starts. Ffill and weights summing to 1 over available rules imply a rule contributes on every bar after its first value. | `forecast_combine.py:195-285,436-458` — VERIFIED |
| SC14 | What downstream expects | **Forecasts, not positions, orders or trades.** There is no channel for entry/exit events, stops, targets, holding-period logic or order types. The position is a pure function of forecast × vol scalar × instrument weight × IDM (× risk scalar), then buffered. | `positionsizing.py:86-131`; `portfolio.py:178-270`; `account_buffering_system.py:54-116` — VERIFIED |
| SC15 | Downstream assumptions | (a) Mean-abs scaling is meaningful: the scalar assumes a stationary |forecast| distribution. (b) Forecast correlations drive FDM, so linear diversification assumes comparable, continuous forecasts. (c) The forecast P&L proxy for weights/costs treats forecast/10 × average position as the traded position (`account_forecast.py:225-329`). (d) Turnover is measured as |Δ(forecast/10)| on a daily resample. (e) Forecast-method buffers have width 0.1 × average position at forecast 10 (`buffering.py:146-173`). | VERIFIED (implementation) / INFERRED (assumption framing) |
| SC16 | Event-driven / discontinuous inputs | Mechanically accepted, but: (i) exits to 0 are erased (SC9) and the prior value is held; (ii) sparse signals are scaled only on active bars, which inflates magnitude when active; (iii) held values understate turnover and cost; (iv) buffers around a jumpy target delay or partially fill entries and exits; (v) there is no mechanism for exit rules, stops or path-dependent state. | EXP-01 TESTED for (i); (ii)–(v) INFERRED from code |

### Conditional signal-swap analysis (counterfactual; not observed implementation)

**Case A: the replacement satisfies SC1–SC16** (a continuous, signed, daily `pd.Series`, non-zero except by accident, roughly stationary magnitude). `swap_evidence` = INFERRED for all rows unless stated otherwise.

| Component | Verdict | Reasoning |
|---|---|---|
| System, Stage, cache, config, simData, price/roll data | Survive unchanged | No reference to rule identity. The cache memoises any pure function. |
| TradingRule / Rules stage | Survive unchanged | The call shape is generic (SC1). |
| Provided rules (A03) | **Inapplicable** | They are the signal being replaced. |
| Scaling, cap, combination, mapping, FDM application | Survive unchanged | They operate on any Series (VERIFIED). A new scalar must be fixed in config or estimated (R01). |
| Scalar, correlation, FDM, forecast-weight, instrument-weight and IDM estimation; fitting dates | Survive unchanged | Parameter values are re-estimated; the method is unchanged. |
| Turnover / SR cost, cost ceiling, forecast P&L proxy | Survive unchanged | These are generic in forecast units. |
| Position sizing, weights, IDM, risk overlay, buffers, buffered path, capital, long-only | Survive unchanged | These depend only on forecast units and price vol. |
| Backtest P&L, cost model, production runner, order generation, stacks, broker | Survive unchanged | Downstream of positions. |
| Dynamic optimisation (P09) | UNKNOWN | Not audited. |

**Case B: the replacement violates the contract** (a discrete, event-driven, path-dependent signal with its own entry/exit logic, e.g. +1/−1 on entry, 0 when flat, exits driven by stops or targets). `swap_evidence` = INFERRED unless stated otherwise; EXP-01 is TESTED for the zero-handling mechanism only.

| Component | Verdict | Reasoning (dependency on the contract) |
|---|---|---|
| System / Stage / config / simData / data | Survive unchanged (container) | They are signal-agnostic. |
| Cache (C03) | Survives partially | It can memoise a vectorised event series. It cannot support a rule that needs per-bar feedback of its own position or fills (SC4, SC5). |
| TradingRule / Rules stage (A01/A02) | Survive partially | The call shape accepts the series, but **zero-as-flat is converted to NaN** (SC9). The rule would have to encode flat as a non-zero epsilon, and a Tx1 DataFrame output fails (SC2). Path-dependent exits must be computed inside the rule from price data alone, because no fill or position feedback exists (SC5). |
| Forecast scaling (A04 / R01) | Survives partially | The mean-abs scalar is estimated on non-zero bars only (`forecast_scalar.py:33-35`), so an active event signal is scaled to average |10| while active. The scale no longer maps to average risk over time. |
| Forecast cap (A05) | Survives partially | For a fixed ±k signal the cap is either inactive or truncates to a constant; its purpose (limiting extreme conviction) disappears. |
| Combination (A06) | Survives partially → requires redesign for exits | **Ffill holds the last non-zero forecast through a flat period** (EXP-01 TESTED: combined forecast constant at +10 across 3505 intended-flat bars). A linear blend of discrete signals yields fractional positions that none of the rules intended. |
| FDM (A08 / R04) and forecast correlations (R03) | Survive partially | Correlations of held and sparse series are distorted, so an FDM calibrated this way has an unclear risk meaning. |
| Forecast mapping (A07) | Survives partially (HYPOTHESIS) | The Gaussian assumption (docs) is violated by a discrete distribution. |
| Forecast-weight optimisation / P&L proxy / turnover / cost ceiling (R05, R09–R11) | Survive partially | The P&L proxy trades forecast/10 × average position, which is not the rule's own entry/exit path once zeros are ffilled. Turnover on held series is understated, so costs are understated. |
| Vol estimation (R02) | Survives unchanged | Price-based. |
| Position sizing (P01) | Survives partially | It can size a fixed-risk entry (±k → ±k/10 × average position), but the entry/exit timing it receives is corrupted upstream (SC9/SC10). It has no stop or target semantics. |
| Instrument weights, IDM, risk overlay, capital, long-only (P02–P04, P07, P08) | Survive (weights/capital/long-only unchanged); IDM partial | They operate on positions. The IDM's correlation basis changes meaning (subsystem returns of an event system), which is INFERRED. |
| Buffering (P05/P06) | Survives partially | The static width at forecast 10 around a target that jumps between 0 and ±k delays or truncates entries and exits (trade-to-edge). NaN inputs hold the last position. |
| Backtest P&L (E01) | Survives partially | Next-close fill only; no intrabar stop or target fills. |
| Cost model (E02), order stacks and broker (E05) | Survive unchanged | Downstream of quantities. |
| Production runner / order generation (E03/E04) | Survive partially | They propagate the same upstream semantics; trade-to-edge is hard-coded. |
| Dynamic optimisation (P09) | UNKNOWN | Not audited. |

## 6. Master Framework Inventory

Canonical file: `pysystemtrade_framework_inventory.csv` (40 rows, validated). Tier assignment and full Tier 1 component cards: **NOT YET AUDITED** (Phase 5). Tier 1 candidates: C01, C02, C03, SC, A01/A02, A04, A05, A06, A08/R04, R01, R02, R07, P01, P02, P03, P04, P05/P06, E02, R11, E04.

## 7. pysystemtrade-Specific Framework Concepts
NOT YET AUDITED (Phase 6).

## 8. State and Estimation Audit
NOT YET AUDITED (Phase 7). Pre-flags: forecast-scalar backfill (`forecast_scalar.py:48`); vol `backfill` default False (`vol.py:128`); full-sample turnover (`strategy_functions.py:31`); full-history instrument-length filter (`basesystem.py:373-390`, default off).

## 9. Dependency / Information Flow
NOT YET AUDITED (Phase 8). Preliminary corrected flow, VERIFIED at call-site level: DATA (1B-last back-adjusted price) → RAWDATA (returns, vol) → RULE → [zeros→NaN] → SCALE → CAP → COMBINE (ffill, weights 1B-smoothed, FDM, cap/map) → POSITION SIZING (vol scalar) → PORTFOLIO (instrument weight × IDM × risk scalar) → BUFFER EDGES → {backtest: ACCOUNTS buffered path → delayfill P&L + costs | live: last-row edges → order generation → stacks → broker}.

## 10. Simulation / Backtest Architecture
NOT YET AUDITED (P1A Phase 9).

## 11. Data / Contract / Roll Architecture
NOT YET AUDITED (P1A Phase 10).

## 12. Forecast / Weight / Portfolio Methodology
NOT YET AUDITED (P1A Phase 11).

## 13. Cost / Turnover / Buffering / Speed Limits
NOT YET AUDITED (P1A Phase 12).

## 14. Configuration / Experiment Infrastructure
NOT YET AUDITED (P1A Phase 13).

## 15. Static Causality / Look-Ahead Audit
NOT YET AUDITED (P1A Phase 14).

## 16. Empirical Causality Testing
NOT YET AUDITED (P1B Phase 15). EXP-01/02 are contract and caching checks, not causality tests.

## 17. Position / Lag / P&L Timing
NOT YET AUDITED (P1B Phase 16).

## 18. Degrees of Freedom / Research Safeguards
NOT YET AUDITED (P1B Phase 17).

## 19. Testing / Validation Infrastructure
NOT YET AUDITED (P1B Phase 18).

## 20. Live / Production Architecture
NOT YET AUDITED (P1B Phase 19, optional). Entry-level facts are in §2 and Executive Summary items 14–15.

## 21–26. Transfer analysis, operational readiness, inventory views, matrix, synthesis
NOT YET AUDITED (P2). No transfer conclusions are drawn before P2.

## 27. Open Questions / Evidence Gaps / Stage-2 Comparison Questions
Evidence gaps G1–G5 and unresolved issues U1–U4 are listed in `audit_progress.md`. Comparison questions: NOT YET AUDITED (P2).

### Documentation / implementation divergence register (running)

| ID | Documentation | Implementation | Evidence |
|---|---|---|---|
| DV1 | "Functions must return a Tx1 pandas dataframe" (`backtesting.md:544`) | `pd.Series(result)` coercion; DataFrame raises (`forecasting.py:102`) | TESTED (EXP-03, coercion step) |
| DV2 | "project doesn't yet include a live trading system" (`backtesting.md:1643`) | `sysproduction`, `sysexecution`, `sysbrokers` exist | VERIFIED |
| DV3 | Position buffering "trade to the optimal position" with `buffer_trade_to_edge: False` (`backtesting.md:2668-2677`) | Live order generation always trades to `round(edge)` (`classic_buffered_positions.py:148-155`); the backtest honours the config (`account_buffering_system.py:100-116`) | VERIFIED (code); live/backtest divergence INFERRED when the config is False |
| DV4 | `mixed_vol_calc` docstring lists vol_floor / floor_min_quant / floor_days | Not implemented (`vol.py:121-181`) | VERIFIED |
| DV5 | Docs place the `TradingRule` class in `systems/forecasting.py` (`backtesting.md:2038`) | It is in `systems/trading_rules.py` | VERIFIED (minor) |
| DV6 | Doctests reference `ForecastScaleCapFixed` / `ForecastCombineFixed`; the fixed scalar doctest expects a float | Classes do not exist; the method returns a Series (`forecast_scale_cap.py:366-398`) | VERIFIED (minor) |
| UD1 | (undocumented) | Zeros → NaN → ffill (SC9) | TESTED (EXP-01) |
| UD2 | (undocumented) | base_system_cache ignores arguments | TESTED (EXP-02) |
