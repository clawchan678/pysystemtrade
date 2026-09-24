# pysystemtrade — Architectural & Methodological Audit

Audited commit: `pst-group/pysystemtrade` @ **`8958c49`** (`8958c49c38b1e4a8c07f0e4375d5e9cb68a087f7`, branch `develop`).
All citations below are `path:lines @ 8958c49` unless stated otherwise.
Evidence tags: VERIFIED / DOCUMENTED / INFERRED / HYPOTHESIS / UNVERIFIED (spec §12). The counterfactual tag `swap_evidence` is kept separate (spec §13).

Status: **P0 complete (Phases 1–8, all approved). P1A in progress: Phases 11 and 12 complete** (session 5, intermediate stop chosen by the operator; not the P1A stop). Next: Phase 9, then 14, 13, 10.

---

## Executive Summary (pre-P2; max 20 bullets)

1. **Architecture.** A `System` is a container of named `SystemStage` objects plus one `simData` and one `Config`. Each stage computes **whole-history pandas time series on demand** (a lazy, pull-based tree) and memoises them in a per-System cache. VERIFIED (`systems/basesystem.py:42-118`, `systems/system_cache.py:527-587`).
2. **Pipeline.** The standard pipeline is rawdata → rules → forecastScaleCap → combForecast → positionSize → portfolio → accounts. VERIFIED (`systems/provided/futures_chapter15/basesystem.py`). Buffering is split: the portfolio stage computes the buffer edges, and the path-dependent buffered position exists only in the accounts stage (backtest) or in production order generation (live). VERIFIED. **Phase 8 flow corrections (§9):** vol (R02) feeds the rules *and* sizing; zeros → NaN at the rule output; FDM precedes a second combined cap or mapping; the risk overlay (optional) comes after the IDM; buffering is split (edges in the portfolio stage, the path in accounts or live order generation); costs sit only in accounts and reach positions only through research estimates (speed limit, estimated weights, IDM); live stores notional `iloc[-1]` edges → order generation → overrides and limits (E06) → stacks/broker (E05). No circular dependency was found in the research feedback loops (INFERRED from the call graph). VERIFIED (code).
3. **Caching.** Cache keys are (stage, method name, instrument code, stringified positional args, kwargs). **Config and data are not part of the key**, so changing config after computation returns stale values. This is DOCUMENTED (`docs/backtesting.md:1452-1456`) and VERIFIED in code.
4. **Base-system cache ignores arguments.** Methods decorated with `base_system_cache` (e.g. `System.get_instrument_list`) are keyed with `use_arg_names=False`, so later calls with different arguments return the first cached result. VERIFIED + TESTED (EXP-02). NOT_DOCUMENTED.
5. **Protected items.** Slow estimates (e.g. forecast scalars) are cached as "protected" and survive `delete_all_items()` by default. This is a DOCUMENTED stale-state vector (`docs/backtesting.md:1590-1609`).
6. **Signal Contract (core).** A rule is `f(*data_series, **kwargs)` called once per (instrument, rule variation) over the full history. Its return value is coerced with `pd.Series(...)`. The forecast is signed (positive = long), continuous, scaled to an average absolute value of 10, and capped at ±20. Position is linear in the forecast. VERIFIED. Full contract in §5.
7. **Zero is not "flat".** `TradingRule.call` converts **every exact 0.0** in a rule's output to NaN (`syscore/pandas/strategy_functions.py:122-139`). Combination then forward-fills forecasts (`systems/forecast_combine.py:458`). The result: a rule that goes flat keeps its last non-zero forecast. TESTED (EXP-01: 3505 zero rows became a constant combined forecast of +10). NOT_DOCUMENTED.
8. **Rule return type divergence.** The docs say rule functions "must return a Tx1 pandas dataframe" (`docs/backtesting.md:544`). The implementation calls `pd.Series(result)` (`systems/forecasting.py:102`), which raises on a DataFrame under pandas 2.1.3. TESTED at the coercion step (EXP-03).
9. **Forecast-scalar estimation.** The estimate is an expanding mean (window 250000) of the cross-sectional median of |forecast|, with zeros excluded and `backfill=True` by default. The source comments this as "SLIGHTLY CHEATING" (`sysquant/estimators/forecast_scalar.py:10,44-48`). This is a pre-sample backfill, also DOCUMENTED as "strictly speaking this is cheating" (`docs/backtesting.md:2451`; Phase 7 correction). Flagged for Phase 14 (PF-1). VERIFIED.
10. **Research defaults.** Every estimation switch defaults to OFF (fixed scalars, weights, FDM and IDM), and costs default to cash costs (`use_SR_costs: False`). VERIFIED (`sysdata/config/defaults.yaml:131,150,171,236,256,300`). The "speed limit" (rule removal by SR-cost ceiling) exists, but its default thresholds are 999/9999, i.e. effectively off (`defaults.yaml:182,190`). VERIFIED.
11. **Estimation windowing.** `generate_fitting_dates` sets `fit_end = period_start` for expanding and rolling fits (`sysquant/fitting_dates.py:181-201`). No causal violation was identified at the date-window level. Deeper checks come in Phase 14.
12. **Backtest fill timing.** With the default `delayfill=True`, positions are shifted one row, and `calculate_pandl` applies a second `shift(1)` against price differences. A position decided at close t therefore earns returns from close t+1 onward (`pandl_calculation.py:150-158,223-235`). VERIFIED static; the empirical trace is Phase 16.
13. **Frequency.** Provided rules and all calibration statistics assume business-day data: `resample("1B").last()` (`syscore/pandas/frequency.py:169-170`), weights resampled to 1B, turnover annualised by business days, and vol scaled by √(business days). VERIFIED. The P&L supports business-day or hourly positions; any other frequency hits a warning path (`systems/accounts/account_inputs.py:35-60`).
14. **Research/live coupling.** Production re-runs the same backtest `System` daily and stores `buffers.iloc[-1]` as the live optimal position band (`sysproduction/strategy_code/run_system_classic.py:146-183`). VERIFIED. Order generation then trades to `round(edge)`, with **trade-to-edge hard-coded** regardless of `buffer_trade_to_edge` (`sysexecution/strategies/classic_buffered_positions.py:141-160`). VERIFIED; the divergence from backtest behaviour applies when the config is False.
15. **Doc divergences.** The docs say "the project doesn't yet include a live trading system" (`docs/backtesting.md:1643`), but a full `sysproduction`/`sysexecution`/`sysbrokers` stack exists. Minor stale docstrings and doctests: `mixed_vol_calc` vol-floor parameters are not implemented (`vol.py:121-181`), and `ForecastScaleCapFixed` does not exist. VERIFIED. The full register is DV1–DV10. Phase 8 added DV11 (the docs' stage-wiring diagram names `rawdata.get_daily_returns_volatility`, which does not exist) and DV12 (doc examples reference `systems.futures.rules` and `rawdata.daily_prices`, which do not exist). Phases 11–12 added DV13 (the docs place a `Slippage` column in `instrument_config.csv`; the shipped file has none and spread comes from `spreadcosts.csv`), UD3 (`minimum_position_limit` returns `False`, reaching only the dynamic-optimised live strategy) and UD4 (commission = max of the three types, which is undocumented).
16. **State and estimation (Phase 7, §8).** The 20-quantity table shows:
    - most estimates are causal at the date level: exponential estimators take rows strictly before `period_start`, and weights and correlations apply from `period_start`;
    - end-of-sample or full-sample quantities are the cost vol deflator (active by default), the SR cost per trade, and turnover;
    - the forecast scalar backfills its first estimate;
    - `fit_start` is ignored by every default (exponential) estimator, so `rolling`/`rollyears` has no effect there;
    - the fit-period grid is anchored to the sample end, so historic periods shift when data is added;
    - the backtest capital default is `fixed` while the production default is `full`;
    - positions use the unshifted capital multiplier while account capital is `shift(1)`;
    - production re-estimates the whole history every run and uses only the last row.
    Twelve pre-flags (PF-1…PF-12) are left unclassified for Phase 14.
17. **Testing status.** Only two targeted controlled experiments (EXP-01, EXP-02) and one coercion check (EXP-03) have run. Phases 7, 8, 11 and 12 were static (Phase 7 added one pandas signature check); their flow and cost questions were NOT TESTED because static reading was sufficient. Two INFERRED effects are left for Phase 15 (O-P11-1 tilt strength; how a `False` maximum is handled). The repo test suite has not been run yet (Phase 18).
18. **Evidence gaps (after Phase 12).**
    - **Closed:** G1 (optimiser numerics, cleaning, pooled correlation, all read; R03/R05/R06 stay INFERRED per U5) and G7 (the call-site effect of `minimum_position_limit`, UD3).
    - **Partly closed:** P09 core read (PARTIALLY AUDITED — RESOURCE PRIORITY: constraints set-up, data preparation, accounts and live strategy internals not read).
    - **Still open:** E05 (stacks, algos, IB), D01 (roll/contract data), G8 (production scheduling), live commission feedback (limited search).
    - Absence claims for market impact and cost curves rest on name-based searches, so they are UNVERIFIED beyond the searched terms.
19. **Methodology (Phases 5–6, 11–12).**
    - All 41 rows are tiered (Tier 1: 16 cards covering 26 IDs).
    - Weights: the default handcraft optimiser = binary clustering (0.5/0.5 × sub-portfolio DM) with a *top-level-only* parametric Sharpe-ratio tilt that uses hard-coded avg SR 0.5 and std 0.15. Its `years_of_data` counts stacked pooled rows (O-P11-1). Markowitz methods are max-SR SLSQP, long-only, weights sum to 1.
    - Pooled estimators stack instruments with microsecond offsets (the code warns this is unsuitable for high-frequency data).
    - Costs: linear spread plus the max of the three commission types; roll pseudo-fills × 0.5; a vol deflator anchored to the sample end (PF-2); no market-impact or cost-curve model found.
    - In the default configuration costs change P&L only; they reach positions only via estimated weights, the speed limit (OFF) or P09.
    - Buffer width is not cost-dependent.
    - P09 is a per-date greedy integer optimiser (tracking error + shadow cost, TE buffer) with end-anchored costs (PF-13 candidate).
    - The risk overlay is OFF by default and not documented in `docs/`.
    - Overrides and limits exist only in production.
    - The §13.6 list names daily-bar, cost-linearity and single-fill-price assumptions that may change for intraday trading (identified only).
20. **Evidence discipline.** Phases 11–12 changed P09 (impl_evidence UNVERIFIED → VERIFIED on direct reading, which is not a U5 case; stateful Y; swap Y/PARTIAL, INFERRED) and `last_phase` (11/12). The operator-approved DISC-1/DISC-2 text corrections are in §2, Card 12 and §8.1 Q17, logged in §13.9. Phase 8 changed only `last_phase` (→ 8 on the rows traced in §9) and raised two discrepancies about earlier sections for the operator (DISC-1/DISC-2, not edited), all logged in §9.9. Phase 7 changed one CSV evidence value (P07 UNVERIFIED → VERIFIED on code read) and set `last_phase` to 7 for the rows it covered, all logged in §8.6. Phase 5 changed `impl_evidence` only for P04 and E02 (UNVERIFIED → VERIFIED, after reading their code) and corrected one Phase 4 doc_status label (P04). Phase 5 had also moved R04 and R07 from INFERRED to VERIFIED; both were **reverted to INFERRED** per the operator's literal reading of spec §12 (session 2, U5), because §12 forbids that upgrade. This is logged in §6.5. No counterfactual was relabelled.

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
**Engines.** The simulation engine is the System/Stage tree (vectorised, whole-history). There is no separate event loop. In the default configuration the only path-dependent per-period loop is the buffered position path P06 (`account_buffering_subsystem.py:106-165`). Other per-period loops exist: the risk-series date loop (`sysquant/portfolio_risk.py:30-58`, used only when the risk overlay is configured; each date is independent), the per-fit-period loops in the optimiser and diversification multipliers (`optimise_over_time.py:54-77`; `diversification_multipliers.py:44-60`, used only when estimation is on), and the sequential `half_compounding` capital loop (`syscore/capital.py:34-46`, path-dependent, off by default). *(Corrected in session 5, DISC-1; see §13.9.)* The live engine is a daily re-run of the same System, followed by stack-based execution. INFERRED from the inspected code; Phase 9 will confirm.

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

Canonical file: `pysystemtrade_framework_inventory.csv` (40 rows at the Phase 5 gate; 41 after Phase 6 added E06). **Phase 5 status: COMPLETE.**

The CSV schema (spec §32) has no tier column. Tiers are recorded here only, so the schema is not altered.

### 6.1 Operator decisions carried into Phase 5 (approved at the Phase 4 gate)

- **FDM split.** A08 (FDM application) stays ALPHA because it sits in the forecast-combination pipeline. R04 (FDM estimation) stays RESEARCH because it is calibrated from forecast correlations and weights.
- **P06 buffered position is PORTFOLIO_RISK.** It is classified by semantic role. *Implementation-location caveat:* the path-dependent code lives under `systems/accounts/*`, the accounting stage, not in `systems/portfolio.py`.
- **E01 backtest P&L is EXECUTION.** *Qualification:* this is **simulated** execution (inferred fills from a position series, next-bar convention, modelled costs). It is not live broker execution. Live order generation and broker execution are E03/E04/E05.

### 6.2 Tier assignment (all 40 rows)

| Tier | Inventory IDs | Treatment |
|---|---|---|
| **Tier 1** (16 cards covering 26 IDs) | C01, C02, C03 · A01, A02 · A04 (+R01) · A05 · A06 · R02 · A08, R04 (+R03) · P01 · P02, P03 (+R06) · R07 · P05, P06 · E02 · R11 (+R09) · P04 · E04 (+E03) | Full card (§6.4). R01, R03, R06, R09 and E03 are covered inside the card of the component they calibrate or feed |
| **Tier 1 finding (not a component)** | SC | Signal Contract, §5 |
| **Tier 2** | C04, C05, D01, A03, A07, R05, R08, R10, P07, P08, P09, E01, E05, E06 (added in Phase 6) | CSV row + note (§6.3) |
| **Tier 3** | none of the 40 rows | Peripheral packages are not inventoried: `syslogging`, `syslogdiag`, `dashboard`, `sysproduction/reporting`, backup/cleaner scripts, `syscontrol` scheduling. They do not materially affect alpha, estimation, portfolio, risk or execution logic (INFERRED from package listing, §2) |

Card count: 16, within the ~15–20 guideline of spec §28. ID arithmetic: 26 Tier 1 IDs + 1 Signal Contract row (SC) + 13 Tier 2 IDs = 40 rows at the Phase 5 gate. Phase 6 added E06 (Tier 2), giving 41 rows. Combined cards are used where components share one implementation path. The count reflects cards, not IDs.

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
| E06 Production overrides & limits (added in Phase 6) | Overrides (a multiplier in [0,1], close, reduce-only, no-trading; the most conservative wins), per-instrument and per-strategy position limits, and rolling trade limits. All are applied in production order handling downstream of the System, with no backtest equivalent. See §7.10. | `sysobjects/production/override.py:102-215`; `position_limits.py:21-150`; `trade_limits.py:7-110`; `strategy_order_handling.py:113-195` VERIFIED |
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
- **Doc/impl divergence:** N identified for scaling itself. *Phase 7 correction (§8.6):* the backfill is DOCUMENTED (`backtesting.md:2451`), so it is not a divergence; its causal classification is Phase 14. Stale doctests: DV6.
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
- **swap_evidence:** **TESTED** (CSV value set in Phase 4 and approved at the gate; unchanged). The TESTED label rests on EXP-01, which ran an event-style signal containing exact zeros through combination. It covers the Case B flat-handling mechanism only. The Case A verdict and the rest of the Case B reasoning (fractional blends) are INFERRED. **impl_evidence:** VERIFIED.

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
- **Implemented behaviour:** as above. The DM formula was read directly in `diversification_multipliers.py` (observation retained); R04's evidence classification remains **INFERRED** per the operator's literal reading of spec §12 (session 2, U5). Pooled correlation internals are INFERRED (not read).
- **Doc/impl divergence:** N identified.
- **Case A:** survives unchanged. The FDM is re-estimated or refixed for the new forecast correlations.
- **Case B:** survives partially. Correlations of held (ffilled) or sparse series are distorted, so the risk interpretation of the FDM is unclear.
- **swap_evidence:** INFERRED. **impl_evidence:** A08 VERIFIED; R04 **INFERRED** (a Phase 5 upgrade to VERIFIED was reverted per the operator's literal reading of spec §12 (session 2, U5); see §6.5); R03 INFERRED (unchanged).

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
- **Implemented behaviour:** as above. The strict `< fit_end` selection was read directly in `exponential_correlation.py:180-190` (observation retained); the classification remains **INFERRED** per the operator's literal reading of spec §12 (session 2, U5).
- **Doc/impl divergence:** N identified.
- **Case A:** survives unchanged. **Case B:** survives partially, because the IDM variant correlates event-system subsystem P&L (INFERRED). The risk variant uses price returns and survives unchanged.
- **swap_evidence:** INFERRED. **impl_evidence:** **INFERRED** (a Phase 5 upgrade to VERIFIED was reverted per the operator's literal reading of spec §12 (session 2, U5); see §6.5); the cleaning path is UNVERIFIED.

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
- **State:** P05 stateless; **P06 stateful**, the only path-dependent loop in the backtest **in the default configuration**. The sequential `half_compounding` capital loop (`syscore/capital.py:34-46`, off by default) and the P09 date loop (`optimised_positions_stage.py:53-78`, alternative system) are also path-dependent. *(Corrected in session 5, DISC-2; see §13.9.)*
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

Each change below is backed by source read during Phase 5. No HYPOTHESIS or INFERRED *claim* was promoted to VERIFIED. **Session 2 correction (U5):** the operator ruled that §12 applies literally, so the R04 and R07 upgrades from INFERRED to VERIFIED were reverted. The observations from reading their source are kept; only the classification changed back. Only the `impl_evidence` of components whose code was newly inspected changed.

| ID | Field | Phase 4 → Phase 5 | Basis |
|---|---|---|---|
| R04 | impl_evidence | INFERRED → VERIFIED → **INFERRED (reverted)** | Source read: `sysquant/estimators/diversification_multipliers.py` (DM formula, period weights, smoothing). Reverted per the operator's literal reading of spec §12 (session 2, U5): direct inspection is not grounds for an INFERRED → VERIFIED upgrade |
| R07 | impl_evidence | INFERRED → VERIFIED → **INFERRED (reverted)** | Source read: `correlation_over_time.py`, `generic_estimator.py:30-140`, `exponential_correlation.py:124-190` (strict `< fit_end`); cleaning path UNVERIFIED. Reverted per the operator's literal reading of spec §12 (session 2, U5) |
| P04 | impl_evidence | UNVERIFIED → VERIFIED | Read `risk_overlay.py` and `portfolio.py:178-229,948-1160`; the default-off mechanism is confirmed via `defaults.yaml:305-309` and `configdata.py:103-108` |
| P04 | stateful | UNKNOWN → N | Computed from position and risk series; no persisted state in the backtest |
| P04 | doc_status | DOCUMENTED → NOT_DOCUMENTED | `docs/*.md` searched for `risk overlay\|risk_overlay`: one passing mention only (`backtesting.md:1656`). **Correction of a Phase 4 labelling error** |
| E02 | impl_evidence | UNVERIFIED → VERIFIED | Read `instruments.py:244-360`, `pandl_cash_costs.py`, `account_costs.py`, `strategy_functions.py:164-179` (`pandl_SR_cost.py` not read) |
| E02 | divergence | UNKNOWN → Y | DV9 config-key name |
| R11 | divergence | UNKNOWN → Y | DV8 config-key name |
| R02 | divergence | Y (DV4) | Unchanged value; DV7 added as a further basis |
| (all 40 rows) | last_phase | 4 → 5 | Tier assigned in Phase 5 (Tier 1 rows also carded) |

Unchanged on purpose: R03, R05 and R06 stay INFERRED (optimiser and pooled-correlation internals not read). D01, P07, P09 and E05 stay UNVERIFIED. All `swap_evidence` values are unchanged from Phase 4: A06 = TESTED (EXP-01), A07 = HYPOTHESIS, P09 = UNVERIFIED, all others INFERRED.

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
- **Documented vs implemented:** consistent (`backtesting.md:2388-2460`, `introduction.md:355`). The backfill and the zero exclusion are VERIFIED in code. *Phase 7 correction (§8.6):* the backfill **is** documented (`backtesting.md:2451`, "strictly speaking this is cheating"); the zero exclusion is not.
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

### 7.12 Phase 6 inventory change log (explicit)

| ID | Field | Change | Basis |
|---|---|---|---|
| E06_PROD_OVERRIDES_LIMITS | (new row) | Added. Tier 2, EXECUTION, impl_evidence VERIFIED (new component, code read, not an upgrade) | §7.10 |
| R05 | divergence | UNKNOWN → Y | DV10 (optimisation methods docs vs register) |
| A04, A05, A08, R01–R07, R09, R11, P03, P05, P06, P09, E01, E04 | last_phase | → 6 | Covered in §7 |
| R03, R04, R05, R06, R07 | impl_evidence | **unchanged (INFERRED)** | Source read in Phase 6, recorded as observations only (U5 / §12) |

## 8. State and Estimation Audit

**Phase 7 status: COMPLETE** (session 3). Spec §37. All citations are `@ 8958c49`. Everything here is static source reading, apart from one one-line signature check (`inspect.signature(pd.Series.ewm)` under pandas 2.1.3 in the scratch venv). No experiment was run: every question in this phase could be answered from the code (spec §22).

**Evidence discipline.**
- **U5 ruling.** Source read in this phase is recorded as *observation* with `file:line` provenance. It does **not** move any INFERRED row to VERIFIED. R03, R04, R05, R06 and R07 stay INFERRED.
- **Pre-flags only.** Timing concerns are recorded as **pre-flags** (PF-n, §8.4). They carry no causal classification (NO ISSUE IDENTIFIED / POSSIBLE ISSUE / CONFIRMED ISSUE); that is Phase 14's job.
- **Timing convention.** "Available when" uses the framework's own convention (SC11): a value stamped *t* on the business-day (1B-last) index is known at the close of *t*. With the default `delayfill=True`, a position decided at close *t* earns returns from close *t+1* onward.

**New source read this phase** (on top of Phases 3–6):
- volatility and scalar estimators: `sysquant/estimators/vol.py:84-199`; `forecast_scalar.py:1-50`;
- fitting dates and correlation estimators: `fitting_dates.py:1-223`; `correlation_over_time.py`; `generic_estimator.py:1-160`; `correlation_estimator.py`; `exponential_correlation.py:1-190`; `correlations.py:109-133,303-400,444-456`; `pooled_correlation.py`;
- mean/stdev and diversification multipliers: `mean_estimator.py:60-90`; `stdev_estimator.py:40-66`; `diversification_multipliers.py:1-95`;
- optimiser and weights: `optimise_over_time.py:1-81`; `portfolio_optimiser.py:60-140`; `pre_processing.py` (cost path, skimmed); `forecast_combine.py:195-263,1100-1165`; `strategy_functions.py:11-33,164-179,213-240`;
- carry and raw data: `systems/rawdata.py:100-275,440-740`; `sysobjects/carry_data.py:8-60`; `systems/provided/rules/carry.py:21`;
- costs: `systems/accounts/pandl_calculators/pandl_SR_cost.py` (whole file, 135 lines); `account_costs.py:1-130,290-345`; `account_instruments.py:96-175` (grep);
- capital: `syscore/capital.py` (whole file); `systems/accounts/account_with_multiplier.py` (whole file); `systems/portfolio.py:76-121,935-1180`; `sysquant/portfolio_risk.py:1-104`; `syscore/pandas/find_data.py:9-81`;
- production state: `sysproduction/strategy_code/run_system_classic.py:40-200`; `sysdata/production/capital.py:228-420`; `sysobjects/production/capital.py:102-170`; `sysexecution/strategies/classic_buffered_positions.py:36-140`; `sysproduction/data/optimal_positions.py:95-130`; `sysproduction/data/config.py:52-65`.

### 8.1 State and estimation table (spec §37)

Column abbreviations: **R/E/F** = Rolling / Expanding / Fixed. **OOS** = how a value at date *t* relates to data after *t*. "Default" means `sysdata/config/defaults.yaml` @ 8958c49.

| # | Quantity | Source | Window | Update Frequency | Method | Available When | R/E/F | OOS Behavior | Missing Data | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| Q1 | Price volatility (price units) | `rawdata.py:153-219` → `vol.py:mixed_vol_calc` (`:121-181`) | EWM-std span 35 (min_periods 10) + slow EWM mean span 10×256 = 2560 bd (no min_periods); 0.7/0.3 blend (`defaults.yaml:112-121`) | Every business day, as a whole-history series | Price-difference EWM std on the 1B-last back-adjusted price, blended with its own slow EWM mean, floored at 1e-10 | Close *t* (includes the return at *t*) | Rolling (exponential); the slow component behaves like an expanding mean until ~2560 bd of history exist (INFERRED from `ewm(adjust=True)`, no min_periods, `vol.py:170-171`) | Uses data ≤ *t* only. `backfill` defaults to False (`vol.py:128`), so there is no pre-sample fill | NaN for the first 10 non-NaN returns. `apply_min_vol` sets values below 1e-10 to 1e-10 in place (`vol.py:84-87`) | VERIFIED (R02) |
| Q2 | Percentage vol | `rawdata.py:242-270` | as Q1 | Business-daily | `100 × vol / abs(raw PRICE (1B-last, ffill))`; the denominator is the *raw* contract price, not the back-adjusted one (`:701-722`) | Close *t* | as Q1 | ≤ *t* | Denominator ffilled; aligned `join="right"` on vol | VERIFIED |
| Q3 | Forecast correlations (for the FDM) | `forecast_combine.py:1167-1296`; `pooled_correlation.py`; `exponential_correlation.py` | EWM span 250 × n_instruments (pooled `length_adjustment`), min_periods 20 × n; weekly (`"W"`) forecast **levels** (`defaults.yaml:152-164`) | One matrix per fit period. Fit periods are 365 days apart (`interval_frequency` default `"12M"` → `"365D"`, `fitting_dates.py:157-175`) | Whole-dataset `ewm(...).corr(pairwise)`, computed once. For each period, the last matrix with index **strictly < `fit_end` (= `period_start`)** (`exponential_correlation.py:180-190`). Then cleaning, floor at zero | From `period_start`; built from data < `period_start` | Expanding by config. In the exponential path `fit_start` is **not used** (O1) | Causal at date level (strict <). Cleaning uses data in `[fit_start:fit_end]` inclusive, for column presence only (O3) | Dummy first period → "boring" matrix (`create_boring_corr_matrix`). Missing entries → the matrix's average correlation, or offdiag 0.99 (`correlations.py:303-400`) | INFERRED (R03, U5) with observations |
| Q4 | Instrument correlations (IDM) | `portfolio.py:376-420`; `correlation_over_time.py:9-60` | EWM span 25 on weekly subsystem-P&L returns (cumsum → ffill → `resample("W").last()` → diff); min_periods 20 (`defaults.yaml:237-247`) | One matrix per 365-day fit period | as Q3 | From `period_start` (data < `period_start`) | Expanding by config; `fit_start` unused in the exponential path | as Q3. The input subsystem P&L includes costs (see Q12/Q13) | as Q3 | INFERRED (R07, U5) |
| Q5 | Instrument correlations (risk overlay) | `portfolio.py:1082-1098`; `defaults.yaml:311-324` | EWM span 75, min_periods 10, on `"7D"` returns of daily % returns; `interval_frequency "W"`; `date_method: rolling`, `rollyears: 5`; clip 0.99 | One matrix per 7-day fit period | as Q3. Looked up by `most_recent_correlation_before_date`: the period with `period_start ≤ date` (`correlations.py:444-456`; `fitting_dates.py:35-47`) | Weekly, from `period_start` | Configured as **rolling 5 periods**, but the exponential estimator ignores `fit_start`, so the effective window is the EWM span alone (O1) | ≤ `period_start` | Before the first period: identity-like matrix with offdiag 0.0 (`portfolio_risk.py:89-104`) | INFERRED (R07) + observation |
| Q6 | Forecast weights | Fixed: config (`forecast_combine.py:908-1006`). Estimated (R05): `optimise_over_time.py:14-81` + `portfolio_optimiser.py` | Estimated: expanding, weekly net returns; exponential mean/stdev/corr with `ew_lookback` 50000 (`defaults.yaml:184-214`) | Raw weights: one row per 365-day fit period, indexed at `period_start` (`optimise_over_time.py:77`). Applied: `fix_weights_vs_position_or_forecast` (ffill reindex, `strategy_functions.py:213-240`) → `resample("1B").mean()` → EWM span 125 → renormalise (`forecast_combine.py:195-263`) | Handcraft (default) on net returns (gross − constant SR cost) | From `period_start`, then smoothed with lag (EWM 125 bd) | Fixed by default (`use_forecast_weight_estimates: False`); expanding when estimated | Exponential estimators use strict `< fit_end` (`mean_estimator.py:70-83` via `find_data.py:73-81`). Net returns embed an end-anchored SR cost (PF-4) | Before the first fit: 1/N (`portfolio_optimiser.py:63-65`). Rules without a forecast yet get weight 0, then renormalise | Fixed path VERIFIED (A06); estimated INFERRED (R05) |
| Q7 | Instrument weights | Fixed: config. Estimated (R06): `portfolio.py:622-700` | Estimated: expanding, weekly subsystem returns, `ew_lookback` 500000 for corr (`defaults.yaml:261-293`) | as Q6 (EWM span 125 bd) | Handcraft with `equalise_SR: True` | From `period_start`, smoothed | Fixed by default; expanding when estimated | as Q6 | Instruments without a position get weight 0 and the rest renormalise; the IDM is **not** adjusted (DOCUMENTED `backtesting.md:2648`) | P02 VERIFIED; R06 INFERRED |
| Q8 | Forecast scalar | Fixed: `forecast_scale_cap.py:366-452` (default 1.0). Estimated (R01): `forecast_scale_cap.py:166-282`; `forecast_scalar.py:5-50` | Window 250000 rows (effectively expanding), min_periods 500 (`defaults.yaml:133-139`) | Every row of the forecast index | `10 / mean(median_i abs(f_i))`. Zeros → NaN; cross-section ffilled before the median; pooled over instruments with the rule | Row *t* includes \|f\| at *t* (the current forecast is part of its own scalar, weight ≈ 1/n) | Fixed by default; expanding when estimated | **`backfill=True`**: rows before `min_periods` get the *first* estimate, which is built from the first 500 rows of data (PF-1). DOCUMENTED as "strictly speaking this is cheating" (`backtesting.md:2451`) | NaN before the first estimate unless backfilled; reindexed to the forecast with ffill (`:229`) | VERIFIED (R01) |
| Q9 | Forecast cap / floor | `forecast_scale_cap.py:30-74,454-499`; `forecast_combine.py:1352-1385` | n/a | Constant | `clip(±20)` | Always | Fixed | Parameter only; no data dependence | NaN passes through | VERIFIED (A05) |
| Q10 | FDM | Fixed default 1.0. Estimated: `forecast_combine.py:1100-1165` → `diversification_multipliers.py:9-95` | Per fit period (Q3 periods); EWM span 125 on the daily series | Per fit period, then daily smoothing | `min(1/√(wᵀCw), 2.5)`. *w* = last row of the **smoothed daily** forecast weights at or before `period_start` (label slice `[:period_start]`, `:45`). NaN → 1.0 | From `period_start`, smoothed | Fixed by default; expanding when estimated | *C* uses data < `period_start`; *w* ≤ `period_start` | Leading NaN → 1.0 (`:67`); empty weight slice → 1.0 | A08 VERIFIED; R04 INFERRED (U5) |
| Q11 | IDM | Fixed default 1.0. Estimated: `portfolio.py:273-374` → same DM function | as Q10, with Q4 matrices and smoothed instrument weights | as Q10 | as Q10 | as Q10 | Fixed by default | as Q10 | as Q10 | P03 VERIFIED; R07 INFERRED |
| Q12 | Cash costs (per fill) and vol deflator | `pandl_cash_costs.py`; `strategy_functions.py:164-172` | Deflator: rolling 180-day std of 1B price diffs (min_periods 3), ffilled | Per fill | `cost × vol_180(t) / vol_180(last date of sample)` when `vol_normalise_currency_costs: True` (default) | Needs the **final** sample value | Rolling numerator / **fixed end-anchored denominator** | Every historic cost depends on the last row of the sample (PF-2). In production the "last row" is today | NaN deflator for the first 2 rows (min_periods 3) | VERIFIED (E02) |
| Q13 | SR cost per trade; SR-cost P&L | `account_costs.py:295-345`; `pandl_SR_cost.py:1-135`; `account_instruments.py:116-175` | Price and vol averaged over the **last year** of data | One constant per instrument | `SR_cost = cost(1 block at last-year average price) / (last-year average annual vol × multiplier)`. The SR-cost P&L charges `−turnover × SR_cost × annualised vol of the average position`, spread per period, **bfilled** during warm-up (`pandl_SR_cost.py:108-135`) | Needs the last year of the sample | Fixed (end-anchored) | Whole-history charge built from end-of-sample quantities (PF-3). `use_SR_costs: False` by default for P&L; always used for forecast-weight estimation | bfill of the annualised cost in warm-up, but only where a position exists (`:117-123`) | VERIFIED (E02) |
| Q14 | Turnover | `strategy_functions.py:11-33`; `account_costs.py:211-293` | **Full sample** | One number per (instrument, rule) or per instrument | `256 × mean(abs(Δ(x_1B / y)))`. *y* = average-position series smoothed by `ewm(250)`, positional → **com** = 250 (O6); for forecasts *y* = 10. Pooled turnover is a length-weighted average across instruments | Needs the whole sample | Fixed (full-sample) | Used by the speed limit (R11), SR costs and net returns for optimisation (PF-4) | `diff().abs().mean()` skips NaN | VERIFIED (R09) |
| Q15 | Carry estimates | `rawdata.py:456-689`; `sysobjects/carry_data.py:8-60`; `rules/carry.py:21` | `raw_carry`: none. `smoothed_carry` / asset-class median: `ewm(90)`, **com** = 90 (≈ span 181) | Business-daily | `annualised roll = (PRICE − CARRY) / contract-date differential`, computed on the raw (intraday-timestamped) multiple prices, then `resample("1B").mean()`, then divided by annualised vol (Q1). The asset-class median is the cross-sectional median of smoothed carry across the asset class ∩ the system universe; not ffilled before the median, ffilled after reindexing | Close *t* (day-*t* mean of the raw roll; vol at *t*) | Rolling (exponential) | ≤ *t* at the level of this code. Which contract is PRICE/CARRY historically comes from roll data built outside the System (D01, UNVERIFIED) (PF-8) | `PRICE − CARRY == 0` → NaN (`carry_data.py:37`), the same zero-as-missing semantics as SC9. The differential is floored at 1 day | VERIFIED (code); D01 inputs UNVERIFIED |
| Q16 | Vol scalar / subsystem position | `positionsizing.py:86-326,480-485` | Inherits Q1/Q2 | Business-daily | `capital × 16% / √256 / (block × %vol × fx) × forecast / 10` | Close *t* | n/a (derived) | ≤ *t* | ffill reindex of the vol scalar onto the forecast index | VERIFIED (P01) |
| Q17 | Buffer edges and buffered position | P05 `buffering.py:35-173`; P06 `account_buffering_subsystem.py:106-208` | Width = 0.1 × \|average position at forecast 10\| | Per row | Edges = ffilled position ± width. P06 is a sequential loop: start at the first optimal (NaN → 0); move to the edge (trade-to-edge) when outside the band; hold on NaN | Close *t*; P06 at *t* depends on the path up to *t* | Path state (the only path-dependent loop in the default configuration; `half_compounding`, off by default, is also sequential and path-dependent, see Q18 *(corrected in session 5, DISC-2)*) | ≤ *t*. In production only `buffers.iloc[-1]` is used (Q20) | NaN inputs → hold the previous position | VERIFIED (P05/P06) |
| Q18 | Capital and account value (backtest) | `syscore/capital.py:19-48`; `account_with_multiplier.py:108-159`; `portfolio.py:76-121,935-945` | Cumulative from the start | Business-daily | `fixed_capital` (**default**, `defaults.yaml:226`): multiplier 1. `full_compounding`: `cumprod(1 + pct_pnl/100)`, where the % P&L is that of the *fixed-capital* portfolio. `half_compounding`: a sequential loop capped at 1.0 | Multiplier at *t* includes P&L at *t* | Expanding (cumulative) | **Positions** use the *unshifted* multiplier (`portfolio.py:93-97`); **account-curve capital** uses `shift(1)` (`account_with_multiplier.py:131`) (O4 / PF-6). Only P&L ≤ *t* is used | ffill of the multiplier | VERIFIED (P07; this phase) |
| Q19 | Risk estimates (risk overlay) | `portfolio.py:948-1180`; `sysquant/portfolio_risk.py:17-104`; `stdev_estimator.py:55-66` | %vol: Q2 annualised, ffilled. Shocked vol: rolling 10×256 bd 99% quantile, min_periods 3 | Per row of the portfolio-weight index (a daily loop, `portfolio_risk.py:30-58`) | `σ_p = √(wᵀΣw)` with Σ from Q5 and %vol at the date. Sum of absolute risk; leverage = Σ\|w\|. Scalar = min over measures of `L/max(L, m)` | Close *t* | Rolling | Shocked vol uses **`bfill=True`**, which fills only the first `min_periods − 1 = 2` rows (PF-7). `get_stdev_on_date` uses the first row for dates before the index start (`stdev_estimator.py:41-45`) | Correlation lookup failure → offdiag 0.0 matrix | VERIFIED (P04 formula and risk series; the overlay is OFF by default) |
| Q20 | Execution state (production) | `run_system_classic.py:52-200`; `sysdata/production/capital.py:228-420`; `sysobjects/production/capital.py:102-170`; `classic_buffered_positions.py:36-200`; E06 objects | Persisted (database) | Per production run (daily). Capital is updated per broker-account-value event | (i) Capital: `production_capital_method` `full` by default (`defaults.yaml:74`), updated from broker P&L, with a 10% `check_limit` gate. (ii) Each run builds a **fresh System over the full history** with *current* capital as a constant `notional_trading_capital`, and stores `get_buffers_for_position(...).iloc[-1]` (notional edges) plus reference price, contract and `datetime.now()`. (iii) Order generation reads the stored edges and actual positions and trades to `round(edge)`. (iv) Overrides, position limits and trade limits (rolling `period_days` counters) are applied downstream (§7.10) | Stored at run time; read at order-generation time | Re-estimated from scratch every run (later recalculation of all history; only the last row is used) | Each live decision uses data up to the run. No backtest equivalent for overrides and limits (PF-9, PF-10) | An age check on the stored `ref_date` was **not observed** in `get_optimal_positions` / `trade_given_optimal_and_actual_positions`. "Stale" in `optimal_positions.py` means *config-listed* instruments or strategies (`config.py:52-65`) (absence UNVERIFIED, limited search) | VERIFIED static (E03/E04/E06); no production run (spec §10) |

Rolling vs expanding (spec §37 "rolling statistics / expanding statistics"). Configured choices:
- **Expanding:** forecast scalar, forecast and instrument correlations for the DMs, forecast and instrument weights.
- **Rolling / exponential:** vol, carry smoothing, the cost-deflator numerator, shocked vol, the risk-overlay correlations.
- **Fixed full-sample or end-anchored:** turnover, SR cost per trade, the cost-deflator denominator.
- **Neither setting governs the estimate** in the default exponential estimators (O1): the EWM span plus the strict `< fit_end` cut-off do.

### 8.2 Per-quantity assessment

| # | When it becomes available | Future or full-sample data? | Warm-up / backfill | Possible OOS contamination (pre-flag, unclassified) | Adaptive degrees of freedom |
|---|---|---|---|---|---|
| Q1–Q2 Vol | After 10 non-NaN returns | No future data observed. Full sample is not used | 10-obs warm-up. No backfill by default | None observed at this level | Fixed hyper-parameters (35, 10y, 0.3). Not estimated |
| Q3–Q5 Correlations | From the first `period_start` after the dummy period (≈ 1 fit interval) | Estimate: strict `< period_start`. Cleaning presence check: inclusive `[fit_start:fit_end]` (O3) | Dummy first period gives a "boring" matrix. `min_periods` × pooled length | PF-5 (the cleaning inclusive bound, 1 row); PF-11 (the period grid is anchored to the sample end, O2) | Estimated; spans and floors are fixed config |
| Q6–Q7 Weights | From `period_start`; the EWM-125 lag delays full effect | Weights: data < `period_start`. **Net returns subtract a constant cost built from full-sample turnover and end-of-sample SR cost** | 1/N in the dummy period | PF-4 | Estimated per 365-day period (handcraft clustering, SR tilt with years of data); method, cost_multiplier (2.0/1.0) and spans are fixed config |
| Q8 Scalar | Row 500 of the (pooled) cross-section; earlier rows backfilled | **Yes, pre-sample backfill** of the first estimate (rows 1–499 use an estimate built from rows 1–500). Same-row inclusion afterwards | `backfill=True` | PF-1 | Estimated (expanding); the target of 10 and min_periods 500 are fixed |
| Q9 Cap | Always | No | n/a | None | Fixed (20) |
| Q10–Q11 DMs | From `period_start` | *C* < `period_start`; *w* ≤ `period_start` (smoothed weights) | Leading NaN → 1.0; EWM-125 ramp from 1.0 | Inherits PF-4/PF-5/PF-11 through *C* and *w* | Estimated; `dm_max` 2.5 and span 125 fixed. Source FIXME: weight-frequency vs span mismatch (`diversification_multipliers.py:15`) |
| Q12 Deflator | Needs the final row | **Yes, end-of-sample anchor** | NaN for 2 rows | PF-2 | None (a formula) |
| Q13 SR cost | Needs the final year | **Yes, last-year anchor** | bfill of the annualised charge in warm-up | PF-3 | None |
| Q14 Turnover | Needs the full sample | **Yes, full-sample** | n/a | PF-4 (feeds R11 rule selection, SR costs, net returns) | None, but it drives a selection decision when R11 is active (default OFF: 999/9999) |
| Q15 Carry | Close *t* | No future data in this code; roll-calendar construction is D01 (UNVERIFIED) | EWM (com 90) without min_periods | PF-8 (D01) | Fixed smoothing (90 as com; O6) |
| Q16 Vol scalar | Close *t* | Inherits Q1 | Inherits Q1 | None additional | Fixed vol target |
| Q17 Buffers | Close *t* | No | Starts at the first optimal (NaN → 0) | None additional in the backtest. Live uses only the last row | Fixed buffer size (0.10) |
| Q18 Capital | Close *t* | No | Starts at 1.0 | PF-6 (timing asymmetry between positions and account capital); backtest default `fixed` vs live default `full` (O5) | Choice of compounding function (config) |
| Q19 Risk | Close *t* | Shocked vol: 2-row bfill | bfill; the first row is used for pre-index dates | PF-7 | Limits are config; the overlay is OFF by default |
| Q20 Execution | Per run | Each run re-estimates everything on history to date | n/a | PF-9 (daily full recalculation: historical backtest values are restated each run); PF-10 (no age check on stored optimal positions observed) | Discretionary overrides and limits (outside the systematic calculation) |

### 8.3 New observations (Phase 7)

- **O1: `fit_start` is unused in the exponential estimators.** `genericEstimator` computes the EWM over the entire dataset once (`generic_estimator.py:128-153`). The exponential correlation, mean and stdev then select by `fit_end` only (`exponential_correlation.py:124-129,180-190`; `mean_estimator.py:70-83`; `stdev_estimator.py:113`). So `date_method: rolling` / `rollyears` change nothing when `using_exponent: True`, which is every default estimator (`defaults.yaml:157,203-215,242,279-291,316`). `rolling` affects only the non-exponential path (`correlation_estimator.py:59`, and `fit_start` in cleaning and data length). In `_fit_dates_for_period_index`, `rollyears` counts *periods*, not years (`yearidx_to_use = max(0, period_index - rollyears)`, `fitting_dates.py:194`). For the risk correlations (`interval_frequency: "W"`, `rollyears: 5`) the non-exponential path would therefore mean 5 weeks. VERIFIED (code read); its effect on estimates is INFERRED.
- **O2: the fit-period grid is anchored to the sample end.** `pd.date_range(end_date, start_date, freq="-365D")` (`fitting_dates.py:173`) generates period starts backward from the last date. Extending the data by one day shifts every historic `period_start`, so all estimated weights, correlations and DMs are re-timed whenever data is added (a *later-recalculation* property). VERIFIED (code); impact INFERRED.
- **O3: inclusive vs strict cut-offs.**
  - Exponential estimates take rows **strictly before** `fit_end`.
  - The non-exponential estimators, cleaning must-haves, weight cleaning and `data_length` use pandas label slices `[fit_start:fit_end]`, which **include** a row stamped exactly `fit_end = period_start` (`correlation_estimator.py:59`; `correlations.py:115-117`; `portfolio_optimiser.py:80,131`; `mean_estimator.py:133`; `stdev_estimator.py:169`).
  - Because `period_start` is an arbitrary timestamp from the 365-day grid, an exact match with a weekly label is incidental. VERIFIED (code).
- **O4: capital timing asymmetry.** `get_actual_position` multiplies notional positions by the **unshifted** capital multiplier (`portfolio.py:93-97`, via `portfolio.capital_multiplier` → `accounts.capital_multiplier`, `:935-945`). `get_actual_capital` applies `shift(1)` (`account_with_multiplier.py:131`). VERIFIED (code). Whether this matters causally is for Phase 14/16.
- **O5: research/live compounding default differs.** The backtest default is `syscore.capital.fixed_capital` (`defaults.yaml:226`; DOCUMENTED `backtesting.md:3908-3922`). The production default is `production_capital_method: 'full'` (`defaults.yaml:74`; DOCUMENTED `production.md:2908,2976`). In production the System receives current capital as a *constant* `notional_trading_capital` (`run_system_classic.py:52-60,76-100,123-143`), and only the last row is used. Live `half` caps capital at the stored maximum (`sysobjects/production/capital.py:146-167`); backtest `half_compounding` caps the multiplier at 1.0 (`syscore/capital.py:36-48`). VERIFIED (code + docs).
- **O6: `ewm(n)` positional arguments mean `com`, not `span`.** `smoothed_carry`, the asset-class median carry (`rawdata.py:633,658`), the carry rule (`rules/carry.py:21`) and the turnover normaliser (`strategy_functions.py:27`) call `.ewm(n)`. In pandas 2.1.3 the first positional parameter is `com` (checked: `inspect.signature(pd.Series.ewm)` → `['self','com','span',…]`). So `smooth_days=90` is com 90 (≈ span 181). Other rules use `span=` explicitly. VERIFIED (code + signature). Intent is not documented; recorded without judgement.
- **O7: shocked-vol backfill** (`stdev_estimator.py:55-66`): `bfill=True` with `min_periods = ceil(2/0.99) = 3`, so only the first two rows are backfilled. VERIFIED.
- **O8: the correlation cleaning path (G7) was read.** Cleaning fills missing entries from the *same* matrix's average correlation, or with offdiag 0.99. "Must-have" status comes from data in `[fit_start:fit_end]` (`correlations.py:109-133,303-400`). No use of data after `fit_end` was observed. VERIFIED (code). This partly closes G1/G7; R03/R07 classification unchanged (U5).
- **O9: risk-series internals were read (G2).** `calc_portfolio_risk_series` loops over dates. For each date it uses weights at that date, the correlation for the period with `period_start ≤ date`, and %vol at that date (`portfolio_risk.py:30-104`; `find_data.py:9-28`). VERIFIED. G2 is closed.
- **O10: `pandl_SR_cost.py` was read (G3).** The SR-cost P&L is a smooth per-period charge proportional to the vol of the *average* position, not to actual trades. The annual SR cost comes from full-sample turnover × end-anchored SR cost per trade (`account_instruments.py:116-160`). The charge is bfilled over warm-up where a position exists. VERIFIED. G3 is closed.
- **O11: the forecast-scalar backfill is documented.** `docs/backtesting.md:2451` says: "This backfills the first scalar value found back into the past so we don't lose any data; strictly speaking this is cheating …". This **corrects** the Phase 6 statement in §7.3 that the docs do not describe the backfill (see §8.6).
- **O12: production stores notional edges.** It stores `portfolio.get_buffers_for_position` (notional, with capital injected), not `get_actual_buffers_for_position`, and stamps `date=datetime.datetime.now()` (`run_system_classic.py:176-200`). VERIFIED.

### 8.4 Pre-flag register for Phase 14 (NOT CLASSIFIED)

| PF | Quantity | Mechanism | Evidence | Default active? |
|---|---|---|---|---|
| PF-1 | Forecast scalar | `backfill=True`: pre-min_periods rows get the first estimate (built from rows 1–500) | `forecast_scalar.py:13,47-48`; DOCUMENTED `backtesting.md:2451` | Only if `use_forecast_scale_estimates: True` (default False) |
| PF-2 | Cash-cost vol deflator | Denominator = vol at the last sample date | `strategy_functions.py:164-172` | **Yes** (`vol_normalise_currency_costs: True`) |
| PF-3 | SR cost per trade | Last-year average price and vol | `account_costs.py:319-345` | In SR-cost P&L (off by default) and **always** in forecast-weight estimation or the speed limit when those are on |
| PF-4 | Turnover → SR cost → net returns / speed limit | Full-sample turnover; a constant cost is subtracted from every fit period | `strategy_functions.py:11-33`; `pre_processing.py:155-200`; `forecast_combine.py:788-864` | When weights are estimated or R11 is active (both default OFF) |
| PF-5 | Cleaning / non-exponential estimators | Inclusive `fit_end` label slice (≤ 1 row at `period_start`) | O3 | Cleaning is on by default for the DM correlations |
| PF-6 | Capital multiplier | Positions use the unshifted multiplier; account capital uses `shift(1)` | O4 | Only with a compounding function (default `fixed_capital`) |
| PF-7 | Shocked vol | 2-row bfill; pre-index dates use the first row | O7; `stdev_estimator.py:41-45` | Only when `risk_overlay` is configured (default OFF) |
| PF-8 | Carry / roll data | Historic PRICE/CARRY contract choice and roll calendar are built outside the System | D01 (UNVERIFIED) | Yes, for carry rules |
| PF-9 | Production recalculation | Every run recomputes all history (and the O2 grid shifts). Backtests of a given date are not reproducible across runs unless data is frozen | O2; `run_system_classic.py:52-71` | Yes (production) |
| PF-10 | Stored optimal positions | No age check on `ref_date` observed in the order-generation path | §8.1 Q20 (limited search) | Production |
| PF-11 | Fit-period grid | Anchored to the sample end | O2 | Whenever estimation is on |
| PF-12 | Instrument universe | `remove_short_history` uses full-history length (carried from Phase 3); the pooled scalar and correlations use the ex-post universe | `basesystem.py:373-390`; `forecast_scale_cap.py:288-320` | `remove_short_history` default False; pooling over the configured universe by default |

### 8.5 Evidence-gap updates

- **G1** (optimiser internals, pooled correlation, cleaning): cleaning read (O8) and period selection read (O3). Pooled-correlation stacking was read in Phase 6. R03/R05/R06 classification stays INFERRED (U5). **Remaining:** per-method optimiser numerics (Phase 11).
- **G2** (risk-series internals): **CLOSED** (O9).
- **G3** (`pandl_SR_cost.py`): **CLOSED** (O10).
- **G6** (D01, P07, P09): **P07 closed** (code read, Q18). D01 and P09 remain UNVERIFIED / PARTIALLY AUDITED.
- **G7** (cleaning path; `minimum_position_limit` bool): cleaning read (O8). The `minimum_position_limit` call-site effect is still UNVERIFIED.
- **New G8:** the production scheduler (`syscontrol`) timing of `run_systems` vs `run_strategy_order_generator`, and whether any age or staleness check on stored optimal positions exists elsewhere in production, is UNVERIFIED. Searched: `sysexecution/`, `sysproduction/strategy_code/`, `sysproduction/run_strategy_order_generator.py`, `sysproduction/data/optimal_positions.py` for `stale|too old|max_age|days_old`.

### 8.6 Phase 7 change log (explicit; nothing changed silently)

**CSV changes:**

| ID | Field | Change | Basis |
|---|---|---|---|
| P07_CAPITAL_MULTIPLIER | impl_evidence | UNVERIFIED → **VERIFIED** | Code read this phase: `syscore/capital.py` (whole), `account_with_multiplier.py` (whole), `portfolio.py:76-121,935-945`. This is an UNVERIFIED → VERIFIED change on direct reading, the same basis as P04/E02 in Phase 5. It is not an INFERRED → VERIFIED upgrade, so U5 does not apply |
| A03, A05, A06, A08, R01–R09, R11, P01–P07, E01, E02, E03, E04, E06 | last_phase | → 7 | Covered in §8.1–8.4 |
| R03, R04, R05, R06, R07 | impl_evidence | **unchanged (INFERRED)** | New source read recorded as observations only (U5 / §12) |
| E06_PROD_OVERRIDES_LIMITS | all | unchanged (Tier 2 / VERIFIED) | No reason from the audit to change it (U7) |

No other CSV field changed. There is no tier column, and transfer labels stay `NOT YET ASSESSED`.

**Report-text corrections:**

| Location | Before | After | Basis |
|---|---|---|---|
| §7.3 "Documented vs implemented" | "The backfill and the zero exclusion are VERIFIED in code; the docs do not describe them." | The backfill **is** documented (`backtesting.md:2451`); the zero exclusion is not | O11 (docs search `backfill` in `docs/backtesting.md`) |
| Card 4 "Doc/impl divergence" | "backfill not checked against docs" | The backfill is DOCUMENTED at `backtesting.md:2451`; no divergence | O11 |

R01 `doc_status` (DOCUMENTED) and `divergence` (UNKNOWN) are unchanged. The divergence field for R01 covers more than the backfill (zero exclusion is undocumented, but "undocumented" is not a divergence), so UNKNOWN stays.

## 9. Dependency / Information Flow

**Phase 8 status: COMPLETE** (session 4). Spec §38. All citations are `@ 8958c49`. The work was static source reading only; no experiment was run (§9.8).

**Evidence discipline.**
- **U5 ruling.** New source read is recorded as observations with provenance. R03–R07 stay INFERRED.
- **Timing.** Timing uses the §8.1 "Available When" column and the SC11 convention: a value stamped *t* on the 1B index is known at the close of *t*. With `delayfill=True` (default), a position decided at close *t* is filled at the *t+1* price and earns returns from close *t+1* onward (`pandl_calculation.py:150-158,223-235`).
- **Causal availability.** Only the §8.4 pre-flags **PF-n** are cited, and they remain **unclassified** (Phase 14).
- **Alpha-specific.** "Alpha-spec." is copied from the CSV `alpha_specific` column: only A03 = Y; every other row = N. It was not changed.
- **Partly-read areas.** Edges that touch E05, D01, P09 or G8 are marked; those gaps are **not** filled here.

**Source read this phase** (on top of Phases 3–7):
- `forecast_combine.py:598-665,874-907,1314-1351`;
- `positionsizing.py:291-375`;
- `portfolio.py:622-724,854-905`;
- `accounts/account_subsystem.py:14-200` (grep and read);
- `accounts/account_forecast.py:150-222`;
- `accounts/account_buffering_subsystem.py:24-70`;
- `syscore/capital.py:19-48`;
- `docs/backtesting.md:616-628,1846-1870`.

### 9.1 Corrected flow (implementation, default configuration)

```
BACKTEST (one System, pulled lazily from any leaf; all series whole-history, cached)

 DATA  simData (csv/db): back-adjusted price, raw contract price (multiple prices), FX, instrument meta/costs
   │   daily_prices = back-adjusted.resample("1B").last()                        [C05; D01 inputs UNVERIFIED]
   ▼
 DATA PROCESSING  RawData: daily_returns (Δ price) ─► VOL R02 (mixed_vol_calc) ─┬─► % vol (÷ raw denominator price)
                  carry (PRICE−CARRY roll / vol), normalised prices ...        │
   │                                                                           │ (vol used twice: in rules and in sizing)
   ▼                                                                           │
 TRADING RULE  A01/A02: f(*system-method data, **kwargs) per (instrument, rule) ◄┘  (e.g. ewmac(price, vol))
   │  output → replace zeros with NaN → pd.Series                              [SC9, EXP-01]
   ▼
 RAW FORECAST ─► SCALING A04 (× fixed scalar | estimated R01, pooled, backfill PF-1)
   ▼
 FORECAST CAP A05  clip(±20) per rule
   ▼
 FORECAST COMBINATION A06: ffill forecasts; weights (fixed | R05) aligned, 1B-mean, EWM125, renormalised
   │                        [speed limit R11 removes expensive rules, default OFF]
   ├─► × FDM (fixed 1.0 | R04 from R03 correlations of weekly forecast levels)        A08
   ▼
 COMBINED CAP / MAPPING  _cap_combined_forecast (default) | map_forecast_value if config.forecast_mapping[instrument]  A05/A07
   ▼
 POSITION SIZING P01: vol_scalar = (capital × %target / √256) / (block_value × %vol × fx)
   │                  subsystem position = vol_scalar × combined_forecast / 10 ; long-only floor P08
   ▼
 PORTFOLIO P02/P03/P04: notional = subsystem × instrument_weight (fixed | R06, EWM125)
   │                                          × IDM (fixed 1.0 | from R07 corr of weekly subsystem P&L)
   │                                          × risk scalar (only if config.risk_overlay; default OFF)
   ├─► BUFFER EDGES P05 (portfolio stage): notional ± 0.1 × |vol_scalar × w × IDM|
   ▼
 ACCOUNTS (backtest only)
   ├─ buffered path P06: sequential loop over edges (rounded), trade-to-edge                [stateful]
   ├─ actual position = notional × capital multiplier P07 (fixed default; unshifted, PF-6)
   ├─ P&L E01: delayfill shift(1) → fills at t+1 price → pos.shift(1) × Δprice
   └─ COSTS E02: cash costs per inferred fill (+ roll pseudo-fills, vol deflator PF-2) | SR costs (PF-3)

LIVE (production, per run)
 fresh System (current capital as notional constant) → portfolio.get_buffers_for_position(...).iloc[-1]
   → stored bufferedOptimalPositions (lower, upper, ref price, contract, now())           [E03]
   → order generation: actual vs edges → target round(edge) (trade-to-edge hard-coded)     [E04]
   → overrides → position limits (instrument orders) → contract orders → trade limits → broker orders   [E06 → E05]
   → stacks / algos / IB                                                                   [E05 UNVERIFIED; scheduling G8]
```

### 9.2 Spec §38 chain vs implementation

| Spec step | Implementation | Correction | Evidence |
|---|---|---|---|
| DATA → DATA PROCESSING | `simData.daily_prices` = back-adjusted `resample("1B").last()`; RawData derives returns, vol, % vol, carry | Price is resampled to business days at the data boundary. % vol uses the **raw** contract price as denominator. Carry uses multiple prices built outside the System (D01) | `sim_data.py:98-127`; `rawdata.py:104-128,153-270,456-689` VERIFIED; D01 UNVERIFIED |
| TRADING RULE | Rule inputs are system methods named in config (`futuresconfig.yaml`: `rawdata.get_daily_prices`, `rawdata.daily_returns_volatility`) | **VOLATILITY is not after combination only:** R02 feeds the rules (normalisation) *before* raw forecasts, and position sizing after combination | `trading_rules.py:113-165`; `systems/provided/futures_chapter15/futuresconfig.yaml:10-40`; `positionsizing.py:389-425` VERIFIED |
| RAW FORECAST | `Rules.get_raw_forecast` = `pd.Series(replace_all_zeros_with_nan(f(...)))` | Insert **zeros → NaN** at the rule output (SC9) | `trading_rules.py:98-111`; `forecasting.py:77-104` VERIFIED; EXP-01 TESTED |
| FORECAST SCALING → CAP | `raw × scalar`, then `clip(floor, cap)` per rule | As in the spec | `forecast_scale_cap.py:30-106` VERIFIED |
| FORECAST COMBINATION | ffill → weights (aligned, 1B, EWM125, renormalised) → Σ → **× FDM** → **combined cap or mapping** | Add FDM *and a second cap/mapping* after combination. Mapping replaces the default cap per instrument | `forecast_combine.py:55-169,1314-1351,1376-1385` VERIFIED |
| VOLATILITY / RISK | Two separate places: (i) the vol scalar in position sizing (R02 → P01); (ii) the optional portfolio risk overlay after the IDM (P04) | Split into *vol targeting* (before instrument weights) and the *risk overlay* (after the IDM, default OFF) | `positionsizing.py:164-326,480-485`; `portfolio.py:178-229,948-969` VERIFIED |
| INSTRUMENT WEIGHT → PORTFOLIO CONSTRUCTION | `subsystem × w_i` then `× IDM` then `× risk scalar` | As in the spec, with the IDM and risk scalar applied multiplicatively in that order | `portfolio.py:178-270` VERIFIED |
| BUFFERING | Edges in the **portfolio** stage (P05); path in the **accounts** stage (P06, backtest) or **order generation** (E04, live) | Buffering is split across stages. The spec's single BUFFERING box is two components in different stages. *Location caveat (U3):* P06 code lives in `systems/accounts/*` | `portfolio.py:102-176`; `account_buffering_system.py:54-116`; `classic_buffered_positions.py:141-160` VERIFIED |
| COSTS | Costs are computed **only in accounts** (E02), on inferred fills or as an SR drag. They do **not** enter the position calculation directly. They feed back into positions only through research: SR cost × turnover → speed limit (R11) and net returns for estimated weights (R05/R06), and cash-cost subsystem P&L → R06/R07 | COSTS is not between BUFFERING and POSITION. It sits beside P&L, with feedback edges into research (§9.4) | `account_instruments.py:15-221`; `forecast_combine.py:503-548,788-864`; `pre_processing.py:108-200` VERIFIED |
| POSITION | Backtest: notional → **× capital multiplier (P07)** = actual position; buffered separately in accounts. Live: notional edges only (no P07) | Add the capital multiplier (backtest). Live uses `notional_trading_capital` = current capital instead (O5/O12) | `portfolio.py:76-121,935-945`; `run_system_classic.py:52-200` VERIFIED |
| EXECUTION | Backtest: simulated fills (E01). Live: E03 → E04 → E06 → E05 | EXECUTION is two paths: simulated (E01) vs live (E03–E06). E05 internals are UNVERIFIED | §9.5 |

### 9.3 Forward dependency table (backtest, default configuration unless noted)

Columns: **Info** = information passed; **State** = persistent or path state carried; **Est.** = estimates passed; **Timing** from §8.1 "Available When"; **Causal** = §8.4 pre-flags (unclassified); **Alpha-spec.** = CSV `alpha_specific` of the *downstream* component.

| # | From → To | Info | State | Est. | Timing | Causal | Alpha-spec. | Evidence |
|---|---|---|---|---|---|---|---|---|
| D1 | DATA (C05, D01) → RawData | back-adjusted daily price (1B-last), raw contract price, multiple prices (PRICE/CARRY), FX, instrument meta | none (read-only data; cached) | none | close *t* | PF-8 (roll/contract choice built outside the System, D01) | N | `sim_data.py:98-137`; `rawdata.py:56-128,456-490` VERIFIED; D01 UNVERIFIED |
| D2 | RawData → R02 vol | daily price differences | none | — | close *t* (includes the return at *t*) | none observed (Q1) | N | `rawdata.py:153-219`; `vol.py:121-181` VERIFIED |
| D3 | RawData/R02 → rules A01/A02 | price, price-unit vol, carry, normalised prices (per config `data` strings) | none (rule is stateless, SC5) | vol estimate | close *t* | PF-8 (carry) | N (interface); A03 rules Y | `trading_rules.py:113-165`; `futuresconfig.yaml` VERIFIED |
| D4 | A01 → A02 raw forecast | rule output coerced to Series; **exact 0.0 → NaN** | none | — | close *t* (the rule's own causality is not enforced, SC11) | none at framework level | N | `trading_rules.py:98-111` VERIFIED; EXP-01 TESTED |
| D5 | A02 → A04 scaling (+R01) | raw forecast; the pooled cross-section when estimating | protected cache for the estimated scalar | scalar (fixed 1.0 or expanding) | fixed: always. Estimated: row *t* includes \|f_t\| | **PF-1** (backfill; estimation OFF by default); PF-12 (pooled over the ex-post universe) | N | `forecast_scale_cap.py:76-320`; `forecast_scalar.py:5-50` VERIFIED |
| D6 | A04 → A05 cap | scaled forecast | none | cap parameter | always | none | N | `forecast_scale_cap.py:30-74` VERIFIED |
| D7 | A05 → A06 combination | capped forecasts per rule (**ffilled**) | none | raw weights (fixed or R05) → 1B, EWM125 smoothed | weights from `period_start`, EWM-lagged; forecasts close *t* | PF-4 (when weights are estimated); PF-11 (grid); SC9/SC10 ffill (not a pre-flag; TESTED) | N | `forecast_combine.py:151-263,436-458` VERIFIED |
| D8 | R11 speed limit → A06 weights | list of cheap rules (the weight columns kept) | none | full-sample turnover × end-anchored SR cost | whole-sample decision | **PF-3, PF-4** (thresholds 999/9999 = OFF by default) | N | `forecast_combine.py:503-548,735-864` VERIFIED |
| D9 | A06 → A08 FDM → combined cap/mapping (A05/A07) | Σ w·f; FDM series (reindexed, ffill) | none | FDM (fixed 1.0 or from R04/R03) | FDM from `period_start` (C < `period_start`; w ≤ `period_start`) | PF-5, PF-11 (estimation OFF by default) | N | `forecast_combine.py:55-131,1008-1165,1314-1385` VERIFIED; R03/R04 INFERRED (U5) |
| D10 | combined forecast + R02 % vol + FX + block value → P01 | combined forecast; % vol; FX (reindexed ffill); block value = denominator price × point value × 0.01 | none | vol scalar | close *t* | none additional (Q16) | N | `positionsizing.py:86-326,389-425,480-485,512-540` VERIFIED |
| D11 | P01 → P02 instrument weights | subsystem position | none | weights (fixed or R06), fitted to position availability, 1B-mean, EWM125, renormalised | weights from `period_start`, EWM-lagged | PF-4, PF-11 (when estimated) | N | `portfolio.py:251-270,422-473` VERIFIED; R06 INFERRED |
| D12 | P02 → P03 IDM | notional position without IDM | none | IDM (fixed 1.0 or from R07) | from `period_start` | PF-5, PF-11 (when estimated) | N | `portfolio.py:231-249,273-374` VERIFIED; R07 INFERRED |
| D13 | P03 → P04 risk overlay (optional) | notional before risk scaling; portfolio weights; % vol; shocked vol; instrument-return correlations (Q5) | none | risk scalar | close *t* | PF-7 (shocked-vol bfill); overlay OFF by default (`missingData` path) | N | `portfolio.py:178-229,948-1180` VERIFIED |
| D14 | notional → P05 buffer edges | notional position; vol scalar; weight; IDM; `buffer_size` | none | — | close *t* | none additional | N | `portfolio.py:125-176`; `buffering.py:35-173` VERIFIED |
| D15 | P05 → P06 buffered path (accounts) | edges and optimal notional (rounded when `roundpositions`) | **path state:** the previous buffered position | — | close *t*; depends on the path ≤ *t* | none additional | N | `account_buffering_system.py:54-116`; `account_buffering_subsystem.py:106-208` VERIFIED |
| D16 | notional + P07 → actual position | notional; capital multiplier (from the fixed-capital portfolio % P&L) | cumulative capital (compounding variants) | — | multiplier at *t* includes P&L at *t* | **PF-6** (unshifted for positions vs `shift(1)` for account capital); `fixed_capital` default | N | `portfolio.py:76-101,935-945`; `syscore/capital.py:19-48`; `account_with_multiplier.py:108-159` VERIFIED |
| D17 | P06 → E01 P&L | buffered position; price (1B back-adjusted, reindexed to the position index); FX; point value; capital | none (vectorised) | — | position at *t* is filled at *t+1* and earns from *t+1* (SC11) | none additional (Phase 16 traces this) | N | `account_instruments.py:15-221`; `pandl_calculation.py:141-235` VERIFIED |
| D18 | E01 fills → E02 costs | inferred fills (Δposition at the aligned price); rolls per year; instrument cost meta | none | cost deflator; SR cost per trade | deflator needs the final sample row; SR cost needs the last year | **PF-2** (active by default); **PF-3** | N | `pandl_cash_costs.py`; `pandl_SR_cost.py`; `account_costs.py:295-345` VERIFIED |

### 9.4 Research feedback edges (active only when the corresponding estimation or ceiling is ON; all default OFF)

| # | Edge | Info passed | Est. passed | Timing | Causal | Alpha-spec. | Evidence |
|---|---|---|---|---|---|---|---|
| F1 | **R10 forecast P&L proxy → R05 forecast weights** | Per-rule P&L of the *individual capped* forecast, traded as notional `forecast/10 × vol-targeted average position`, with `delayfill` and a **constant SR cost** ("We NEVER use cash costs for forecasts"). Pooled over instruments with the same *cheap* rules | net weekly returns (gross − SR cost × `cost_multiplier` 2.0) → handcraft weights per 365-day period | weights indexed at `period_start`; fit on data before it | **PF-3, PF-4, PF-11**; PF-12 (pooled universe) | N | `forecast_combine.py:598-665,690-705,874-906`; `account_forecast.py:150-329`; `pre_processing.py:108-200` VERIFIED (R10); R05 INFERRED |
| F2 | **Subsystem P&L → R06 instrument weights** | `pandl_across_subsystems_given_instrument_list(..., roundpositions=True)`: P&L of the **subsystem-level buffered** position (`get_buffered_subsystem_position` → P01 + subsystem buffers), with **cash costs** by default (`use_SR_costs: False`) and `delayfill=True`. Plus subsystem turnover | net weekly returns → handcraft (`equalise_SR: True`) | from `period_start` | **PF-2** (cash-cost deflator inside the P&L), PF-3/PF-4 (turnover-based SR costs in pre-processing), PF-11 | N | `portfolio.py:622-724,854-905`; `account_subsystem.py:14-200`; `account_buffering_subsystem.py:24-104` VERIFIED; R06 INFERRED |
| F3 | **Subsystem P&L → R07 IDM correlations** | the same subsystem P&L as F2 → cumsum → weekly → diff → EWM(25) correlation | correlation list → IDM | from `period_start` (strict `<`) | PF-2 (inside the P&L), PF-5, PF-11 | N | `portfolio.py:376-420`; `correlation_over_time.py` VERIFIED; R07 INFERRED |
| F4 | **Turnover / SR cost → speed limit R11 and net returns** | full-sample forecast turnover (pooled, length-weighted) × end-anchored SR cost per trade + holding cost | cheap-rule list (D8); cost drag in F1/F2 | whole-sample | **PF-3, PF-4** | N | `account_costs.py:1-293`; `forecast_combine.py:735-864`; `pre_processing.py:155-200` VERIFIED |
| F5 | **Portfolio % P&L → P07 capital multiplier → positions** (compounding variants only) | % P&L of `accounts.portfolio()` (the fixed-capital portfolio) → cumprod (full) or capped loop (half) | multiplier series | includes P&L at *t* | PF-6 | N | `syscore/capital.py:19-48` VERIFIED |

Feedback structure. There is **no circular dependency**: forecast weights (F1) use individual forecasts; instrument weights and the IDM (F2/F3) use subsystem positions, which depend on forecast weights; the capital multiplier (F5) uses the fixed-capital portfolio. Each loop feeds an estimate *forward* into a later stage (INFERRED from the call graph above; not tested).

### 9.5 Production flow (E03 → E04 → E06 → E05)

| # | Edge | Info | State | Timing | Causal | Evidence |
|---|---|---|---|---|---|---|
| L1 | Production data + capital → fresh System (E03) | the full history from the production DB via the sim-data wrapper; **current** capital as the constant `notional_trading_capital`; base currency | persisted capital (`production_capital_method: full`) | per run | **PF-9** (full recalculation each run; O2 grid shift) | `run_system_classic.py:52-143` VERIFIED |
| L2 | E03 → stored optimal positions | `portfolio.get_buffers_for_position(code).iloc[-1]` (**notional** edges; no P07, no P06), reference price `get_daily_prices(...).iloc[-1]`, reference contract, `datetime.now()` | DB record per instrument/strategy | stored at run time | PF-10 (no age check observed) | `run_system_classic.py:146-200` VERIFIED |
| L3 | stored edges + actual positions → order generation (E04) | if actual < lower: target `round(lower)`; if actual > upper: target `round(upper)`; else none | actual positions (DB) | at order-generation run (scheduling vs L1 is **G8, UNVERIFIED**) | PF-10 | `classic_buffered_positions.py:36-200` VERIFIED |
| L4 | E04 → E06 overrides then position limits | proposed instrument order; cumulative override; per-instrument and per-strategy limits | override DB and config; position-limit DB | at order generation | none (discretionary controls; no backtest equivalent, O-level fact from §7.10) | `strategy_order_handling.py:86-195`; `override.py:102-215`; `position_limits.py:99-150` VERIFIED |
| L5 | instrument order → contract orders → E06 trade limits → broker orders (E05) | contract order; rolling `period_days` trade counters | trade-limit DB (counters) | at broker-order creation | none | `create_broker_orders_from_contract_orders.py:137-170`; `trade_limits.py:7-110` VERIFIED; **the rest of E05 (stacks, algos, IB) is UNVERIFIED** |

### 9.6 Phase 8 observations

- **P8-O1: two independent buffer implementations feed research vs positions.** The portfolio-level buffered path (P06 via `get_buffered_position`) drives instrument P&L. The *subsystem-level* buffered path (`PositionSizing.get_buffers_for_subsystem_position` → `get_buffered_subsystem_position`) drives the subsystem P&L that feeds instrument weights and the IDM (F2/F3). The subsystem buffers are computed without instrument weight or IDM (`buffering.py` defaults `arg_not_supplied` → 1.0, `:153-163`). VERIFIED (code). Research implications are INFERRED.
- **P8-O2: cost regimes differ by feedback edge.** F1 (forecast weights) always uses SR costs. F2/F3 (instrument weights, IDM) use cash costs by default, including the end-anchored deflator (PF-2). The live position path uses no cost at all except through these estimates. VERIFIED (code: `account_forecast.py:191-194`; `account_subsystem.py:88-100`; `defaults.yaml:300`).
- **P8-O3: vol reaches sizing through two denominators.** % vol = 100 × price-unit vol / |raw price|, and block value = raw price × point value × 0.01. Their product returns price-unit vol × point value (`positionsizing.py:248-326`; `rawdata.py:242-270`). The raw-price denominator cancels algebraically (INFERRED from the formulas; not tested), so the sizing risk unit is back-adjusted price-difference vol × point value.
- **P8-O4: the combined-forecast cap is replaced, not supplemented, by mapping.** When `config.forecast_mapping[instrument]` exists, `map_forecast_value` is used with `capped_value = forecast_cap`, and `_cap_combined_forecast` is not called (`forecast_combine.py:1314-1351`). VERIFIED (code). Mapping internals are Tier 2 (A07, INFERRED).
- **P8-O5: live uses notional edges from a System whose capital is today's capital.** The backtest path, by contrast, is `notional × multiplier` (P07). Research and live therefore scale capital in different places (restates O5/O12 at the flow level). VERIFIED.

### 9.7 Discrepancies found in earlier sections (for operator review; NOT edited)

*Session 5 status:* DISC-1 and DISC-2 were accepted by the operator as errors and corrected as text-only fixes in §2, Card 12 and §8.1 Q17. Before/after text is logged in §13.9; no CSV value changed.

| # | Location | Statement | Finding | Evidence |
|---|---|---|---|---|
| DISC-1 | §2 "Engines" | "the only per-period loop is the buffer application" (labelled INFERRED) | Other per-period loops exist: `half_compounding` (a sequential capital loop, `syscore/capital.py:34-46`), the risk-series date loop (`portfolio_risk.py:30-58`, §8 O9), and per-fit-period loops in the optimiser and DM (`optimise_over_time.py:54-77`; `diversification_multipliers.py:44-60`) | VERIFIED (code) |
| DISC-2 | Card 12 "State"; §8.1 Q17 | P06 is "the only path-dependent loop" / "the only stateful loop in the backtest" | `half_compounding` is also a sequential, path-dependent loop (the multiplier is capped at 1.0 and depends on prior values). It is not the default (`fixed_capital`), and §8.1 Q18 itself describes it as a sequential loop, so §8 is internally inconsistent on this point | `syscore/capital.py:34-46` VERIFIED |

### 9.8 Experiments

NOT TESTED — REASON: every §9 edge was settled by static reading of the call sites cited (spec §22: static first). No end-to-end numerical flow trace was run. The empirical position → lag → fill → P&L trace belongs to Phase 16, and causal testing to Phase 15.

### 9.9 Phase 8 change log (explicit)

| Item | Change | Basis |
|---|---|---|
| CSV `last_phase` | → 8 for the 35 rows that appear as nodes in §9.1–§9.5: C05, D01, A01, A02, A03, A04, A05, A06, A07, A08, R01–R11, P01–P08, E01–E06. Unchanged (6 rows): C01, C02, C03, C04, SC, P09 | Traced in Phase 8 |
| CSV other fields | **unchanged** (including `alpha_specific`, `impl_evidence`; R03–R07 stay INFERRED; D01/P09/E05 stay UNVERIFIED; E06 unchanged) | U5; operator instructions |
| Divergence register | DV11, DV12 added (docs), see register | §9 reading of `docs/backtesting.md` |
| Earlier sections | not edited; DISC-1, DISC-2 raised for the operator | §9.7 |

## 10. Simulation / Backtest Architecture
NOT YET AUDITED (P1A Phase 9).

## 11. Data / Contract / Roll Architecture
NOT YET AUDITED (P1A Phase 10).

## 12. Forecast / Weight / Portfolio Methodology

**Phase 11 status: COMPLETE** (session 5). Spec §39. All citations are `@ 8958c49`. The work was static source reading only; no experiment was run (§12.6).

**Evidence discipline.**
- **U5.** New source read is recorded as observation. R03–R07 stay INFERRED.
- **Pre-flags.** PF-1…PF-12 stay unclassified; new candidates are numbered PF-13+ and are also unclassified.
- **Rationale.** "Rationale" is taken **only** from repository docs or code comments. Where the repo gives none, it is recorded as UNVERIFIED.
- **Scope.** This section concentrates on the open gaps (G1, G7, P09). Mechanisms already covered are summarised by reference to Cards §6.4, §7, §8.1 and §9, not re-derived.

### 12.1 Mechanism summary: forecast → risk → position

| Mechanism | Formula (implemented) | Inputs | Estimation / update | Rationale (repo only) | Documented vs implemented | Evidence |
|---|---|---|---|---|---|---|
| Forecast generation | `pd.Series(zeros→NaN(f(*data, **kwargs)))` per (instrument, rule) | system-method data (price, vol, carry) | stateless, whole history | "normalise the forecast into something proportional to Sharpe Ratio" (`backtesting.md:1954`) | DV1 (Tx1 DataFrame), UD1 (zeros) | Card 3; §5 SC1–SC16 VERIFIED |
| Scaling | `raw × scalar`; estimated `10 / expanding mean(median_i\|f\|)` | raw forecasts (pooled) | fixed 1.0, or estimated per row with `backfill` (PF-1) | "Scale forecasts so they have the right average absolute value" (`backtesting.md:2394`) | consistent; the backfill is documented (`:2451`) | Card 4 VERIFIED |
| Caps | `clip(±20)` per rule and on the combined forecast (or mapping) | scaled or combined forecast | constant | "Cap forecasts at a maximum value" (`:2396`); mapping assumes a Gaussian distribution (`:2581`) | consistent | Card 5; §9 P8-O4 VERIFIED |
| Combination | `Σ w_r·ffill(f_r)` | capped forecasts, weights | weights fixed, or R05 per 365-day period → 1B → EWM125 | method docstring (`forecast_combine.py:60-63`); docs `:2461-2535` | consistent | Card 6 VERIFIED; R05 INFERRED |
| FDM | `min(1/√(wᵀCw), 2.5)` → EWM125 | weights, R03 correlations | fixed 1.0 or per fit period | `diversification_multipliers.py` docstring ("1 / [ ( W x H x WT ) 1/2 ]") | consistent | Card 8; A08 VERIFIED, R04 INFERRED |
| Position sizing / vol targeting | `capital × %target/√256 / (point value × price-unit vol × fx) × f/10` (P8-O3) | combined forecast, R02, FX, point value | business-daily | "scale our positions according to our percentage volatility target" (`:2607-2611`) | consistent | Card 9 VERIFIED |
| Instrument weights | `renorm(EWM125(1B(fix_weights(w_raw))))` | subsystem positions; R06 | fixed, or per 365-day period | docs `:2626-2663`; handcraft rationale: see §12.2 | consistent | Card 10; R06 INFERRED |
| IDM | as FDM, on R07 correlations of weekly subsystem P&L | instrument weights, R07 | per fit period | docs `:3421-3467` | the docs note the IDM is not adjusted for zeroed weights (`:2648`) | Card 10–11; R07 INFERRED |
| Correlations | whole-dataset EWM corr; last matrix strictly `< fit_end`; cleaning; floor at zero | forecast levels (weekly, pooled, stacked) / subsystem returns | per fit period | stacking docstring: unsuitable for high-frequency data (`list_of_df.py:83-87`) | consistent | §7.2; §8 O1/O3/O8; R03/R07 INFERRED |
| Portfolio construction | `subsystem × w × IDM × (risk scalar)` → buffer edges; P09 as an alternative (§12.4) | as above | as above | docs `:2626-2700` | DV3 (live trade-to-edge) | Cards 10, 12, 15; §9 VERIFIED |

### 12.2 G1: per-method optimiser numerics (read this phase)

- **Shared Markowitz core** (`sysquant/optimisation/shared.py:15-191`):
  - Estimates are first equalised.
  - Weights then maximise `SR = w·μ / √(wᵀΣw)` with `scipy.optimize.minimize(method="SLSQP")`, bounds `[0,1]`, the equality constraint `Σw = 1`, a 1/N start and `tol=1e-5`.
  - Σ = diag(σ)·C·diag(σ).
  - The helpers `fix_mus`/`fix_sigma`/`un_fix_weights` exist in the module but are **not called** on this path. Assets with missing estimates are removed beforehand (`call_optimiser.py:21-42`, `estimates.py:subset_with_available_data`). VERIFIED (code).
- **Equalisation** (`sysquant/estimators/estimates.py:118-205`, `vol_equaliser` at `:191`):
  - `vol_equaliser` sets every σ to the in-sample average and rescales μ to keep each Sharpe ratio (doctest `([1.,2.],[2.,4.]) → ([1.5,1.5],[3.,3.])`).
  - `SR_equaliser` sets `μ_i = target_SR × σ_i`, so all assets get the same SR (default 0.5).
  - With both on, the optimiser sees identical μ/σ and only the correlation matters. VERIFIED (code).
- **Methods:**
  - **equal_weights:** 1/N over assets with valid estimates.
  - **one_period:** equalise (per config) → max-SR.
  - **shrinkage:** correlation shrunk toward its average by `shrinkage_corr`, and means shrunk toward the target SR by `shrinkage_SR`, then `optimise_given_estimates(**weighting_kwargs)`. Because `equalise_SR` is also passed through to `optimise_given_estimates`, a config with `equalise_SR: True` would replace the shrunk means with equal-SR means (VERIFIED code path). The docs note the related case: "if you equalise Sharpe by shrinking with a factor of 1.0, then this will override the effect of any pooling or changes to cost calculation" (`backtesting.md:3379-3392`). The defaults use `equalise_SR: False` for forecast weights.
  - **handcraft:**
    - ≤ 2 assets: 1/N.
    - Otherwise: recursive clustering into **two** groups (`FIXED_CLUSTER_SIZE = 2`), 0.5/0.5 between groups, each group's weights × its own DM.
    - Sub-portfolios are always solved with `equalise_SR=True` (`handcraft.py:194-210`, the call at `:206`). **The SR tilt is applied once, at the top level only.**
  - All VERIFIED (code).
- **SR tilt numerics** (`SR_adjustment.py:77-251`):
  - For each asset, `relative_SR = SR_i − mean(SR)`.
  - The multiplier comes from a *parametric* "mini bootstrap": a 2-asset max-SR problem solved at CDF points {0.2, 0.4, 0.6, 0.8} of a normal distribution. The mean is `relative_SR × 0.15` and the s.d. is `ω = √(2 × (0.15/√years)² × (1 − ρ̄))`, with hard-coded `avg_SR = 0.5` and `std = 0.15`. Weights are averaged and the ratio to 1/N taken; if its sign disagrees with `SR_diff` it is set to 1.0.
  - Weights × multipliers are then renormalised. VERIFIED (code).
  - The rationale appears in the docstring only ("parametric bootstrap of portfolio weights", `:118`).
- **Years of data under pooling** (new observation, O-P11-1):
  - `data_length` is the row count of the **stacked** pooled net returns in `[fit_start:fit_end]` (`portfolio_optimiser.py:127-131`).
  - `data_length_years = data_length / periods_per_year` (`estimates.py:59-64`).
  - With *n* instruments pooled, the row count is ≈ *n* × periods, so the SR tilt is computed as if there were ≈ *n* × calendar years of data. VERIFIED (code). The effect on the tilt's strength is INFERRED, not tested.
  - The estimator lookbacks *are* adjusted for pooling (`length_adjustment = pooled_length`, `:46-48,168-190`); `data_length` is not.
- **Cleaning** (`cleaning.py:7-139`):
  - Assets with data in `[fit_start:fit_end]` are "must-haves".
  - Missing must-have weights get an equal share of `fraction × (#missing / #assets)`, with `fraction = 0.5` by default. Other weights are scaled by `1 − that`, then everything is renormalised.
  - Non-must-have NaN gets 0. Doctests confirm the arithmetic. VERIFIED (code).
- **Pooled forecast correlation:** read in Phase 6 (§7.2) and Phase 7 (O8). No new finding; R03 stays INFERRED.
- **G1 status:** **CLOSED at code level** (optimiser numerics, cleaning and pooled correlation all read). Classification of R03/R05/R06 is unchanged (INFERRED, U5).

### 12.3 G7: call-site effect of `minimum_position_limit`

- **The single call site** is `sysproduction/data/controls.py:578-592`, `dataPositionLimits.get_maximum_position_contracts_for_instrument_strategy`. It carries the source comment `## FIXME: THIS WON'T WORK IF THERE ARE MULTIPLE STRATEGIES TRADING AN INSTRUMENT`.
- **Its only callers** are in `sysexecution/strategies/dynamic_optimised_positions.py:289-322`, i.e. the **dynamic-optimised live strategy**.
  - Its wrapper returns 0 for a `Close` override.
  - It returns `ARBITRARILY_LARGE_CONTRACT_LIMIT` only when `maximum is NO_LIMIT`.
  - Otherwise it returns the value as-is.
- **Effect** in the case "instrument has **no** limit, instrument-strategy **has** limit L":
  - `minimum_position_limit` returns `other_position_limit.no_limit`, i.e. **`False`** (`position_limits.py:21-28,42-44`).
  - `False is NO_LIMIT` is false, so the strategy passes `False` as that instrument's maximum position to the optimiser, instead of L.
  - The return value is VERIFIED (code). How the greedy optimiser then treats `False` (numerically 0) is **INFERRED**, not tested.
- **Classic-strategy path:** not affected. `strategy_order_handling.py` applies limits via `apply_position_limit_to_order` (§7.10), which does not call this function.
- **Documented behaviour:** "The dynamic optimisation strategy will also use position limits in its optimisation in production (not in backtests …)" (`docs/production.md:2038`).
- **G7 status: CLOSED** (the call-site effect is established at code level). Recorded as **UD3** (undocumented behaviour).

### 12.4 P09 dynamic optimisation (read this phase; depth limited by budget)

- **Entry:** `optimisedPositions` stage (`systems/provided/dynamic_small_system_optimise/optimised_positions_stage.py:35-399`).
- **Backtest loop** (`:53-78`): for each date in the common index, it solves an integer problem with `previous_positions` = the previous date's solution (all zeros at the start). This is a **sequential, path-dependent loop**; its state is the previous positions. On an exception it keeps the previous positions (`:91-98`). VERIFIED.
- **Inputs per date** (`:102-133`):
  - "optimal" contracts = the classic portfolio stage's notional positions (`portfolio.get_position_contracts_for_relevant_date`);
  - covariance (instrument-return correlations × stdev, shrunk by `shrink_instrument_returns_correlation` 0.5);
  - per-contract value;
  - costs per contract as a proportion of capital;
  - constraints (reduce-only, long-only, maxima);
  - speed control (`shadow_cost` 50, `tracking_error_buffer` 0.0125; `defaults.yaml` `small_system`).
- **Objective** (`optimisation.py:219-283`):

  `TE(w) + shadow_cost × Σ|cost_i × (w_i − w_prev,i)| + constraint penalty`,

  where `TE(w) = √((w − w*)ᵀ Σ (w − w*))` in weight space.
- **Algorithm:**
  - Step 1: if the tracking error of the *prior* weights is below the buffer, keep the prior positions (no trade) (`:107-140`).
  - Step 2: otherwise, a **greedy** search from the start weights (zeros or constraint minima). On each pass it tries one extra contract per instrument in the direction of the optimum and keeps the best improvement. It stops when no single step improves the objective, or at the limits (`greedy_algo.py:6-90`).
  - Step 3: the trade from prior to greedy is scaled by `adj = (TE_prior − buffer) / TE_prior` (floored at 0) and rounded in contract space (`buffering.py:15-60`).
  - Weights divided by per-contract value give integer contracts (`optimisation.py:79-84`).
  - All VERIFIED (code).
- **Cost inputs (new pre-flag candidate PF-13):**
  - The cost per contract uses the **final** raw price and **final** FX rate (`optimised_positions_stage.py:244-262`) and the current contract value.
  - It is multiplied by the vol deflator `calculate_cost_deflator` (the end-anchored denominator, as PF-2). A NaN deflator is set to **10000.0** (`:211-218`), i.e. prohibitive costs during deflator warm-up.
  - VERIFIED (code). Unclassified (Phase 14).
- **Rationale (repo):**
  - the docs describe it as for "systems with sparse positions" (`backtesting.md:3034,3056`) and as producing "A simple optimal position, eg trade until the position is +5 contracts" (`production.md:980`);
  - the log strings describe the tracking-error buffer ("is the prior portfolio pretty close to optimal already??");
  - any fuller design rationale is UNVERIFIED (not found in the repo docs searched: `docs/*.md` for `dynamic`).
- **Not read** (**PARTIALLY AUDITED — RESOURCE PRIORITY**):
  - `set_up_constraints.py` details (minima/maxima derivation beyond the names);
  - `data_for_optimisation.py`;
  - `accounts_stage.py` P&L internals;
  - covariance shrinkage internals;
  - the live strategy path beyond the G7 call site (`sysexecution/strategies/dynamic_optimised_positions.py`).

### 12.5 New observations and pre-flag candidates (Phase 11)

| ID | Observation | Evidence |
|---|---|---|
| O-P11-1 | The SR tilt's `years_of_data` counts stacked pooled rows (≈ *n*× calendar years) | `portfolio_optimiser.py:127-131`; `estimates.py:59-64` VERIFIED; effect INFERRED |
| O-P11-2 | Handcraft applies the SR tilt only at the top level; sub-portfolios are equal-SR | `handcraft.py:98-112,194-210` VERIFIED |
| O-P11-3 | With `equalise_SR: True` (the instrument-weight default) the SR tilt is skipped and only correlations drive the weights; the forecast-weight default (`equalise_SR: False`) applies the tilt | `handcraft.py:98-112`; `defaults.yaml:196,271` VERIFIED |
| O-P11-4 | P09's backtest is a sequential, path-dependent loop over dates (in addition to P06), but it is not part of the default System | `optimised_positions_stage.py:53-78` VERIFIED |
| PF-13 (candidate, unclassified) | P09 costs use the final price, final FX and the end-anchored deflator; the warm-up deflator is set to 10000 | `optimised_positions_stage.py:188-262` VERIFIED |

### 12.6 Experiments

NOT TESTED — REASON: every Phase 11 question (optimiser numerics, the G7 return value, P09 control flow) was settled by static reading (spec §22). The two *effects* recorded as INFERRED — how strongly O-P11-1 changes the SR tilt, and how the greedy optimiser handles a `False` maximum — would need controlled runs. They are left for Phase 15, subject to operator approval.

## 13. Cost / Turnover / Buffering / Speed Limits

**Phase 12 status: COMPLETE** (session 5). Spec §39. All citations are `@ 8958c49`. The work was static source reading only (§13.7). Builds on Cards 12–14, §8 Q12–Q14/Q17, §9 D8/D14–D18/F1–F5 and P8-O1/O2; those are summarised here, not re-derived. PF-n stay unclassified.

### 13.1 Trace: forecast/rule → desired position → turnover → transaction cost → portfolio decision

```
rule forecast ──(A04–A08)──► combined forecast ──(P01–P04)──► desired (notional) position
      │                                                               │
      │ forecast turnover R09 = 256·mean|Δ(f_1B/10)| (full sample)    │ buffer edges P05 (width 0.1 × |avg pos|; NOT cost-dependent)
      ▼                                                               ▼
 SR cost = turnover × SR_cost_per_trade(E02, last-year) + holding     buffered path P06 (backtest) │ round(edge) E04 (live)
      │                                                               │
      ├─► speed limit R11: drop rule if SR cost > ceiling (999/9999 = OFF)   ├─► fills (Δ buffered, rounded position) at t+1 price (E01)
      ├─► net returns for R05 forecast weights (SR costs × cost_multiplier 2.0)│
      │                                                               ▼
      │                                               cash cost per fill (E02) + roll pseudo-fills × 0.5, × vol deflator (PF-2)
      │                                                               │
      └──────────── subsystem P&L (cash costs, subsystem buffers) ────┴─► R06 instrument weights, R07 IDM correlations (F2/F3)
P09 (not default): trade-off TE vs shadow_cost × Σ|cost × trade| per date, integer greedy, TE buffer (§12.4)
```

In the default configuration (all estimation OFF, R11 OFF, `use_SR_costs: False`), costs change **P&L only**. They reach positions only when estimated weights, the speed limit or P09 are switched on. VERIFIED (§9.2 COSTS row; defaults).

### 13.2 Cost components

| Component | Implemented | Instrument-specific? | Documented | Evidence |
|---|---|---|---|---|
| Spread / slippage | `|qty| × price_slippage × point value`, where `price_slippage` = `SpreadCost` from `spreadcosts.csv` (sim) or the Mongo spread-cost store (production) | Yes (per instrument) | "Slippage, in price points. Half the bid-ask spread, unless trading in large size …" (`backtesting.md:3042`) | `instruments.py:344-392`; `futures_sim_data.py:132-215`; `data/futures/csvconfig/spreadcosts.csv` VERIFIED |
| Commissions | `max(per_block × |qty|, per_trade, percentage × |qty| × price × point value)`; a source comment says "YOU WILL NEED TO CHANGE THIS IF YOUR BROKER HAS A MORE COMPLEX STRUCTURE" | Yes (`instrumentconfig.csv`: PerBlock, Percentage, PerTrade) | The three types are listed (`:3043-3045`). **The combination rule (the maximum) is not documented** (UD4) | `instruments.py:365-373` VERIFIED |
| Market impact / size-dependent cost | **Not implemented in the cost formula.** The per-fill cost is linear in \|qty\| (slippage and per-block) plus a fixed or percentage term; there is no term that grows faster than quantity | — | The docs caveat "unless trading in large size" (`:3042`) but give no impact model | Formula VERIFIED (`instruments.py:344-392`). Absence of any separate impact module: repo-wide search of `*.py`, `*.yaml`, `*.md` for `market.?impact`, `price.?impact`, `impact_cost`, `square.?root` found no model (the one hit, `production.md:2026`, concerns trade-limit sizing). Search is name-based, so absence beyond these terms is **UNVERIFIED** |
| Cost curves (non-linear cost vs size) | **None found** | — | — | Search for `cost.?curve`, `nonlinear cost`, `non-linear cost`, `cost_function`: the only hit is `sysquant/returns.py:322` (a variable name for the cost return series). Absence beyond the terms is UNVERIFIED |
| Roll (holding) costs | Cash method: pseudo-fills at `rolls_per_year` equal dates, qty = average \|position\| over the period × `multiply_roll_costs_by` (0.5), open and close. SR method: `2 × rolls_per_year × SR_cost_per_trade` | `rolls_per_year` per instrument (roll config) | "Both cost methods now account for holding - rollover costs" (`:3036`) | `pandl_cash_costs.py` (`_pseudo_fills_for_year`); `account_costs.py:183-188` VERIFIED |
| Vol normalisation of costs | `cost × vol_180(t) / vol_180(last)` (PF-2), default ON | — | "normally standardised for historic volatility" (`:3038`) | `strategy_functions.py:164-172` VERIFIED |
| SR cost per trade | cost of 1 block at the last-year average price / (last-year average annual vol × point value) (PF-3) | Yes | docs `:3058-3066` (usage) | `account_costs.py:295-345` VERIFIED |

### 13.3 Turnover and its control

- **Measured turnover:**
  - forecast turnover `256 × mean|Δ(f_1B/10)|` (full sample, PF-4);
  - subsystem and instrument turnover normalised by an average-position series smoothed with `ewm(250)` (com, O6).
  - VERIFIED (Card 14, §8 Q14).
- **Turnover controls present:**
  - (i) **buffering**: a no-trade band, fixed width 0.1 × average position, trade-to-edge; the width does **not** depend on costs (`buffering.py:90-173`; `buffer_size` constant in config);
  - (ii) the **speed limit** (R11): rule exclusion by SR cost, OFF by default;
  - (iii) **EWM-125 smoothing** of forecast weights, instrument weights, FDM and IDM (dampens changes that come from weight re-estimation);
  - (iv) **P09**: shadow cost on trades and a tracking-error buffer (not default);
  - (v) **live trade limits** (E06, rolling per-period contract counters) and **position limits**.
  - All VERIFIED (code, cited in §7/§9).
- **Not a turnover control:** forecast smoothing. The framework does not smooth rule outputs; any smoothing is inside the rule itself (e.g. EWMAC spans). VERIFIED (§5 SC4).

### 13.4 Cost influence on decisions

| Decision | Cost input | Active by default? | Evidence |
|---|---|---|---|
| Positions (classic) | none directly | — | §9.2 |
| Rule inclusion (R11) | full-sample turnover × end-anchored SR cost | No (999/9999) | Card 14 |
| Forecast weights (R05) | constant SR cost × `cost_multiplier` 2.0 subtracted from returns; optional `apply_cost_weight` post-adjustment | No (estimation OFF) | §7.1; F1 |
| Instrument weights / IDM (R06/R07) | cash-cost subsystem P&L (deflated) | No (estimation OFF) | F2/F3; P8-O2 |
| P09 positions | shadow_cost × Σ\|cost × trade\| with final-price costs (PF-13) | No (alternative system) | §12.4 |
| Live trades | none (costs are not in E04's trade rule); trade limits cap size | — | `classic_buffered_positions.py:141-200` |

### 13.5 Research / live consistency

| Item | Backtest | Live | Status | Evidence |
|---|---|---|---|---|
| Buffer exit rule | `buffer_trade_to_edge` config (default True) | hard-coded trade-to-edge `round(edge)` | **DV3** (diverges when the config is False) | Card 12/16 |
| Rounding | `.round()` of optimal and edges (P06) | `round(edge)` | consistent (round-half-even semantics in both, INFERRED) | §7.9 |
| Fill price | next-row (t+1) daily price, `delayfill` | execution algos on live prices (E05 UNVERIFIED) | not comparable statically | SC11; G4 |
| Spread cost | one configured constant per instrument, applied to all history × vol deflator | live: spread sampled from bid/ask plus realised slippage, reported; configured value updatable via interactive control (`auto_update_spread_costs`) | research uses the *current* configured value for the whole history (INFERRED consequence of a single constant) | `sysproduction/reporting/data/costs.py:140-250`; `interactive_controls.py:959,1098` VERIFIED |
| Commission | configured `instrumentconfig.csv` / DB | broker commissions compared with configured values in a report | reporting only; no automatic feedback observed (limited search) | `sysproduction/reporting/data/commissions.py:18-210` VERIFIED (existence); feedback absence UNVERIFIED |
| Roll costs | pseudo-fills × 0.5 at equal dates | actual roll trades (roll orders in the stack handler, E05) | modelling vs actual; not compared statically | `pandl_cash_costs.py`; `sysexecution/stack_handler/roll_orders.py` (listing only) |
| Capital scaling | P07 multiplier (fixed default) | current capital as the notional constant | O5/P8-O5 | §8, §9 |
| Overrides / limits | none | E06 | no backtest equivalent (F16) | §7.10 |

### 13.6 Assumptions that may change materially for intraday trading (identified only; no replacement designed)

1. **Daily bar granularity:** 1B resampling of prices, turnover and weights; `delayfill` = one daily bar (SC11/SC12). VERIFIED.
2. **Cost linearity:** no market impact and no cost curve (§13.2). Cost per contract is independent of trade size, time of day and liquidity. VERIFIED formula; absence UNVERIFIED beyond the search.
3. **Constant spread per instrument** over the whole history (× a 180-day vol deflator). No intraday spread variation is modelled. VERIFIED.
4. **Fills at a single price per bar** (next daily price). No partial fills, queue position, intrabar sequencing or latency in the backtest. VERIFIED (`pandl_calculation.py:223-235`; `fills.py:63-90`).
5. **Turnover annualisation** by 256 business days, and SR costs derived from daily vol (√256). VERIFIED.
6. **Buffer width tied to the average position at forecast 10** (a vol-scaled daily quantity), not to costs or intraday volatility. VERIFIED.
7. **Roll costs** modelled as a fixed number of evenly spaced events per year. VERIFIED.
8. **Live execution** via algos on a daily decision (E05 UNVERIFIED): stored edges are stamped `now()` with no age check observed (PF-10).

### 13.7 Experiments

NOT TESTED — REASON: every Phase 12 question was answered by static reading of the cost formulas, call sites and config (spec §22). The quantitative size of cost effects (e.g. how PF-2 changes historical costs) is a Phase 15 question.

### 13.8 Documentation / implementation items raised (see register)

- **DV13:** the docs say `instrument_config.csv` has cost headings including `Slippage` (`backtesting.md:848`). The shipped file `instrumentconfig.csv` has `PerBlock, Percentage, PerTrade` but **no** `Slippage`; slippage comes from `spreadcosts.csv` (`SpreadCost`) via `get_spread_cost` (`futures_sim_data.py:132-215`). VERIFIED.
- **UD4:** commission = **maximum** of the per-block, per-trade and percentage commissions (`instruments.py:365-373`, `max` at `:373`). The docs list the three types without stating how they combine. Searched `docs/backtesting.md` (costs section `:3025-3077`) and `docs/instruments.md` for `max`/`maximum`/`largest`. VERIFIED (code); undocumented.

### 13.9 Session 5 change log (Phases 11–12; explicit)

**Report-text corrections (operator-approved DISC-1 / DISC-2; text only, no CSV value changed):**

| Location | Before | After |
|---|---|---|
| §2 "Engines" (DISC-1) | There is no separate event loop; the only per-period loop is the buffer application (`account_buffering_subsystem.py:106-165`). | There is no separate event loop. In the default configuration the only path-dependent per-period loop is the buffered position path P06 (`account_buffering_subsystem.py:106-165`). Other per-period loops exist: the risk-series date loop (`sysquant/portfolio_risk.py:30-58`, used only when the risk overlay is configured; each date is independent), the per-fit-period loops in the optimiser and diversification multipliers (`optimise_over_time.py:54-77`; `diversification_multipliers.py:44-60`, used only when estimation is on), and the sequential `half_compounding` capital loop (`syscore/capital.py:34-46`, path-dependent, off by default). *(Corrected in session 5, DISC-1; see §13.9.)* |
| Card 12 "State" (DISC-2) | - **State:** P05 stateless; **P06 stateful**, the only path-dependent loop in the backtest. | - **State:** P05 stateless; **P06 stateful**, the only path-dependent loop in the backtest **in the default configuration**. The sequential `half_compounding` capital loop (`syscore/capital.py:34-46`, off by default) and the P09 date loop (`optimised_positions_stage.py:53-78`, alternative system) are also path-dependent. *(Corrected in session 5, DISC-2; see §13.9.)* |
| §8.1 Q17 "R/E/F" cell (DISC-2) | Path state (the only stateful loop in the backtest) | Path state (the only path-dependent loop in the default configuration; `half_compounding`, off by default, is also sequential and path-dependent, see Q18 *(corrected in session 5, DISC-2)*) |
| §9.7 header | (no status line) | a one-line session 5 status note pointing here |

**CSV changes:**

| ID | Field | Change | Basis |
|---|---|---|---|
| P09_DYNAMIC_OPTIMISATION | impl_evidence | UNVERIFIED → **VERIFIED** | Core code read this phase (§12.4: stage loop, objective, greedy, TE buffer, cost inputs). This is an UNVERIFIED → VERIFIED change on direct reading (same basis as P04/E02/P07), not INFERRED → VERIFIED, so U5 does not apply. Remaining files are PARTIALLY AUDITED — RESOURCE PRIORITY (§12.4) |
| P09 | stateful | UNKNOWN → Y | Sequential date loop with previous positions (`optimised_positions_stage.py:53-78`) |
| P09 | survives_if_contract_met / _violated | UNKNOWN / UNKNOWN → Y / PARTIAL | Counterfactual: P09 consumes the classic notional positions (A: unchanged); under B it inherits the upstream forecast semantics (SC9/SC10) while its TE buffer handles sparse positions |
| P09 | swap_evidence | UNVERIFIED → INFERRED | The counterfactual reasoning above; not tested |
| P09 | contract_dependency | text updated | §12.4 summary |
| A01, A02, A04–A08, R01–R08, P01–P04, P09, E06 | last_phase | → 11 | Covered in §12 |
| R09, R10, R11, P05, P06, E01–E04 | last_phase | → 12 | Covered in §13 |

Unchanged on purpose: every other field. R03–R07 stay INFERRED (U5). E06 is unchanged (Tier 2 / VERIFIED; UD3 is an *undocumented* behaviour, not a divergence, so `divergence` stays N). D01 and E05 stay UNVERIFIED. `alpha_specific` is unchanged (only A03 = Y). Transfer labels stay `NOT YET ASSESSED`.

**Register additions:** DV13, UD3, UD4 (see the divergence register). **New pre-flag candidate:** PF-13 (§12.5), unclassified.

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
Evidence gaps G1–G8 and unresolved issues U1–U7 are listed in `audit_progress.md` (Phase 7 gap updates: §8.5). Comparison questions: NOT YET AUDITED (P2).

### Documentation / implementation divergence register (running)

| ID | Documentation | Implementation | Evidence |
|---|---|---|---|
| DV1 | "Functions must return a Tx1 pandas dataframe" (`backtesting.md:544`) | `pd.Series(result)` coercion; DataFrame raises (`forecasting.py:102`) | TESTED (EXP-03, coercion step) |
| DV2 | "project doesn't yet include a live trading system" (`backtesting.md:1643`) | `sysproduction`, `sysexecution`, `sysbrokers` exist | VERIFIED |
| DV3 | Position buffering "trade to the optimal position" with `buffer_trade_to_edge: False` (`backtesting.md:2668-2677`) | Live order generation always trades to `round(edge)` (`classic_buffered_positions.py:148-155`); the backtest honours the config (`account_buffering_system.py:100-116`) | VERIFIED (code); live/backtest divergence INFERRED when the config is False |
| DV4 | `mixed_vol_calc` docstring lists vol_floor / floor_min_quant / floor_days | Not implemented (`vol.py:121-181`) | VERIFIED |
| DV5 | Docs place the `TradingRule` class in `systems/forecasting.py` (`backtesting.md:2038`) | It is in `systems/trading_rules.py` | VERIFIED (minor) |
| DV6 | Doctests reference `ForecastScaleCapFixed` / `ForecastCombineFixed`; the fixed scalar doctest expects a float | Classes do not exist; the method returns a Series (`forecast_scale_cap.py:366-398`) | VERIFIED (minor) |
| DV7 | Default vol function is `robust_vol_calc` with a 5%-quantile / 500-day vol floor (`backtesting.md:1965-1985`, `:4209-4216`) | Default is `mixed_vol_calc` (`defaults.yaml:113`): EWM 35d blended 30% with 10-year slow vol, no quantile floor (`vol.py:121-181`) | VERIFIED |
| DV8 | Post-optimisation cost ceiling key `post_ceiling_cost_SR` (`backtesting.md:3276,3280,3419,4384`) | Code reads `forecast_post_ceiling_cost_SR` (`forecast_combine.py:757`; `defaults.yaml:182`) | VERIFIED (minor, naming) |
| DV9 | Cost pooling key `forecast_cost_estimate` (`backtesting.md:3073,3285,4654`) | Code reads `forecast_cost_estimates` (`account_costs.py:58-59,215`; `defaults.yaml`) | VERIFIED (minor, naming) |
| DV10 | "There are five methods provided" for optimisation; bootstrapping listed, then described as "no longer implemented" (`backtesting.md:3347-3378`) | Four methods registered: equal_weights, shrinkage, handcraft, one_period (`call_optimiser.py:10-15`); `bootstrap` raises "not recognised" (`:65`) | VERIFIED (minor) |
| DV11 | Stage-wiring diagram: the rule's inputs are `system.data.get_raw_price` and `system.rawdata.get_daily_returns_volatility` (`docs/backtesting.md:1864-1865`) | `RawData` has `daily_returns_volatility` (`rawdata.py:154`); `get_daily_returns_volatility` exists only on the accounts stage (`account_inputs.py:76`). The default rule config uses `rawdata.get_daily_prices` + `rawdata.daily_returns_volatility` (`futuresconfig.yaml:10-40`) | VERIFIED (minor) |
| DV12 | Rule examples use `function="systems.futures.rules.ewmac"` and `data=["rawdata.daily_prices", ...]` (`docs/backtesting.md:616-628`; 11 occurrences of `systems.futures.rules`) | There is no `systems/futures` package (the rules are in `systems/provided/rules/`), and `RawData` has `get_daily_prices` (`rawdata.py:57`), not `daily_prices`. Searched: `ls systems/futures`; `grep def daily_prices systems/rawdata.py` | VERIFIED (minor) |
| DV13 | `instrument_config.csv` headings include cost column `Slippage` (`backtesting.md:848`) | The shipped `data/futures/csvconfig/instrumentconfig.csv` has `PerBlock, Percentage, PerTrade` and **no** `Slippage`; slippage comes from `spreadcosts.csv` (`SpreadCost`) via `get_spread_cost` (`futures_sim_data.py:132-215`) | VERIFIED (minor) |
| UD1 | (undocumented) | Zeros → NaN → ffill (SC9) | TESTED (EXP-01) |
| UD2 | (undocumented) | base_system_cache ignores arguments | TESTED (EXP-02) |
| UD3 | (undocumented) | `positionLimit.minimum_position_limit` returns `other.no_limit` (a bool, `False`) when the instrument has no limit but the instrument-strategy does; reaches only the dynamic-optimised live strategy's maximum-position input (`controls.py:578-592`; `dynamic_optimised_positions.py:289-322`). Downstream numeric treatment INFERRED | VERIFIED (return value) |
| UD4 | (undocumented) | Commission = **max**(per-block × \|qty\|, per-trade, percentage × value), not a sum (`instruments.py:365-373`); the docs list the three types without the combination rule (searched the `backtesting.md` costs section and `instruments.md` for max/maximum/largest) | VERIFIED |
