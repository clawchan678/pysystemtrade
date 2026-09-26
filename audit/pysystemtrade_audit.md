# pysystemtrade — Architectural & Methodological Audit

Audited commit: `pst-group/pysystemtrade` @ **`8958c49`** (`8958c49c38b1e4a8c07f0e4375d5e9cb68a087f7`, branch `develop`).
All citations below are `path:lines @ 8958c49` unless stated otherwise.
Evidence tags: VERIFIED / DOCUMENTED / INFERRED / HYPOTHESIS / UNVERIFIED (spec §12). The counterfactual tag `swap_evidence` is kept separate (spec §13).

Status: **P0 complete (Phases 1–8, all approved). P1A COMPLETE (Phases 9–14). P1B COMPLETE — P1B STOP** (session 8, operator-authorised phase by phase: Phase 15 §16 (PF-11 wording corrected, §16.12), Phase 16 §17, Phase 17 §18, Phase 18 §19; **Phase 19 SKIPPED — RESOURCE PRIORITY**, §20). **P2 COMPLETE** (session 9: Phases 20, 21, 23, 24 → §21, §22, §24, §25; Phases 22, 25, 26 → §23, §26, §27). Executive Summary current as of P2 close (bullets 21–22). P2 reviewed and closed (session 9). Next: none — audit complete.

---

## Executive Summary (max 22 bullets; P2 complete, see 21-22)

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
11. **Estimation windowing and causality (Phase 14, §15).** `generate_fitting_dates` sets `fit_end = period_start` for expanding and rolling fits (`sysquant/fitting_dates.py:181-201`); no causal violation was identified at the date-window level. Answer to the central question at time T: **Phase 10 (§11.10):** PF-8 (carry/roll data) is now **POSSIBLE ISSUE**, superseding §15's UNVERIFIED:
    - back-adjusted levels and carry values: NO ISSUE IDENTIFIED for the provided rules;
    - framework-built roll dates depend on full-dataset price availability: POSSIBLE ISSUE;
    - the shipped historical CSVs' construction: UNVERIFIED;
    - retrospective static metadata, e.g. the SGX Pointsize edit applied to all history: POSSIBLE ISSUE.
    - **default classic backtest:** no post-T input to the *position* was identified (NO ISSUE IDENTIFIED; static, not verified causal). The end-anchored cost deflator makes backtest *costs and net P&L* use the last sample date (PF-2, **CONFIRMED ISSUE**, default ON);
    - **estimation on:** post-T inputs reach positions (PF-1 scalar backfill, PF-3/PF-4 end-of-sample SR cost × full-sample turnover, PF-2 via instrument weights/IDM, the documented `in_sample` date method N7: CONFIRMED ISSUE, conditional); the end-anchored fit grid PF-11 is a POSSIBLE ISSUE;
    - **other non-default paths:** compounding (PF-6 via PF-2), shocked-vol backfill (PF-7), P09 final-price costs (PF-13) and daily→hourly alignment (PF-14, mechanism TESTED by EXP-04) are CONFIRMED ISSUE, conditional; the P09 per-contract-value backfill (PF-15) is a POSSIBLE ISSUE;
    - **live decision at T:** NO ISSUE IDENTIFIED (end anchors equal today);
    - **UNVERIFIED:** the provenance of the shipped fixed parameters (N9). Roll/back-adjustment (PF-8, D01) was UNVERIFIED at Phase 14; Phase 10 was completed in session 7 and resolved it (PF-8 → POSSIBLE ISSUE; D01 VERIFIED for in-repo code; §11.10–§11.11).
    - **Phase 15 (§16, empirical; §15 not edited, supersessions in §16.10):** PF-2 TESTED: costs and net P&L only; forecasts, positions and gross P&L unchanged at two cutoffs, which also supports the default-position answer for this system. PF-1 and PF-3/PF-4 TESTED: they change weights or scalars, forecasts, positions and P&L (unchanged: CONFIRMED ISSUE ONLY WHEN NON-DEFAULT OPTION ENABLED). **PF-11 stays POSSIBLE ISSUE**: the dependence of refit dates on the sample end date is TESTED (L1–L4, a design property), and future market data entering estimates is NO ISSUE IDENTIFIED (fixed-refit-date control: zero differences). An interim CONFIRMED relabel was reverted (§16.12). **PF-15 POSSIBLE → NO ISSUE IDENTIFIED** for P09 positions and P&L; it changes an internal input only. O-P11-1 and O-P9-1/O-P9-2 effects TESTED; neither is look-ahead.
12. **Simulation engine and fill timing (Phase 9, §10).** The backtest is vectorised, whole-history, daily-bar, lazy and memoised: no clock or event loop. Fills are inferred from position changes at one price per row. With the default `delayfill=True`, positions are shifted one row, and `calculate_pandl` applies a second `shift(1)` against price differences, so a position decided at close t is filled at the t+1 price and earns returns from close t+1 onward (`pandl_calculation.py:150-158,223-235`; VERIFIED static; the empirical trace is Phase 16). P&L is reported in BDay bins; no cash, margin or financing state was found (absence UNVERIFIED beyond the searched terms). An undocumented order-simulator accounts stage (UD5) replaces fill inference with a per-row market/hourly-limit order loop, bypasses buffering, and prices gross P&L at bar prices rather than fill prices (O-P9-1; effect TESTED in Phase 15, §16.8). **Phase 16 trace (§17; US10, three rule-selected dates):** a position decided at close t is filled at the close of t+1 at price(t+1) and earns from (t+1, t+2]. There is no same-day exposure, which matches the documented "trade at the next days closing price". The roll day creates no fill; its P&L is the old contract's pre-roll move plus the new contract's post-roll move. Roll costs fall on equally spaced pseudo-fill dates, not roll days. The last row's decision is never filled in the backtest. No new doc/implementation divergence was found in the sample.
13. **Frequency.** Provided rules and all calibration statistics assume business-day data: `resample("1B").last()` (`syscore/pandas/frequency.py:169-170`), weights resampled to 1B, turnover annualised by business days, and vol scaled by √(business days). VERIFIED. The P&L supports business-day or hourly positions; any other frequency hits a warning path (`systems/accounts/account_inputs.py:35-60`).
14. **Research/live coupling.** Production re-runs the same backtest `System` daily and stores `buffers.iloc[-1]` as the live optimal position band (`sysproduction/strategy_code/run_system_classic.py:146-183`). VERIFIED. Order generation then trades to `round(edge)`, with **trade-to-edge hard-coded** regardless of `buffer_trade_to_edge` (`sysexecution/strategies/classic_buffered_positions.py:141-160`). VERIFIED; the divergence from backtest behaviour applies when the config is False.
15. **Doc divergences.** The docs say "the project doesn't yet include a live trading system" (`docs/backtesting.md:1643`), but a full `sysproduction`/`sysexecution`/`sysbrokers` stack exists. Minor stale docstrings and doctests: `mixed_vol_calc` vol-floor parameters are not implemented (`vol.py:121-181`), and `ForecastScaleCapFixed` does not exist. VERIFIED. The full register is DV1–DV10. Phase 8 added DV11 (the docs' stage-wiring diagram names `rawdata.get_daily_returns_volatility`, which does not exist) and DV12 (doc examples reference `systems.futures.rules` and `rawdata.daily_prices`, which do not exist). Phases 11–12 added DV13 (the docs place a `Slippage` column in `instrument_config.csv`; the shipped file has none and spread comes from `spreadcosts.csv`), UD3 (`minimum_position_limit` returns `False`, reaching only the dynamic-optimised live strategy) and UD4 (commission = max of the three types, which is undocumented). Session 6 added UD5 (the order simulator is undocumented) and DV14 (the documented `syscore.accounting` import path for `account_t_test` does not exist).
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
17. **Testing status.** Before P1B: EXP-01/02 (contract and caching checks), EXP-03 (coercion step), EXP-04 (Phase 14, PF-14 mechanism, synthetic) and EXP-05 (Phase 10, Panama mutation, synthetic). Phases 7, 8, 9, 11, 12 and 13 were static. **Phase 15 (§16, session 8)** ran EXP-06…EXP-11 on the shipped chapter-15 system and shipped CSVs, using pre-declared truncation cutoffs, a grid-aligned cutoff and control arms. Effect sizes are now measured for PF-2, PF-1, PF-3/PF-4, PF-11, PF-15, O-P11-1 and O-P9-1/O-P9-2, each reported by causal level (L1 internal, L2 forecast, L3 position, L4 P&L/costs). They hold for this system, these data and these cutoffs only, and no item is labelled material. Not tested: PF-6, PF-7, PF-8 (G11), PF-12, PF-13, PF-14 effect size, N7–N10, O-P9-3 and the greedy `False` maximum (§16.9). **Phase 18 (§19):** the repo's configured suite passes (quick: 101 passed, 40 skipped, 3 xfailed; slow: 17 passed). But 66 defined tests are silently never collected because `@unittest.SkipTest` is misused as a decorator. The 17 end-to-end example tests have no assertions. The only cost-value test (`test_accounts`) is outside `testpaths` and fails at import, through a name-shadowing star-import chain in the repository's own code (VERIFIED here; INFERRED version-independent; §19 O-P18-3). None of PF-1, PF-2, PF-3/PF-4, PF-11 or PF-15 would be caught by the repository's own tests; only Phase 15-style experiments detect them.
18. **Evidence gaps (after Phase 10).** D01 closed for the in-repo code (VERIFIED, §11.11). Still UNVERIFIED: the shipped historical CSVs' construction, the live roll-status trigger internals, and the effect size of availability-based roll dating. Earlier status:
    - **Closed:** G1 (optimiser numerics, cleaning, pooled correlation, all read; R03/R05/R06 stay INFERRED per U5) and G7 (the call-site effect of `minimum_position_limit`, UD3).
    - **Partly closed:** P09 core read (PARTIALLY AUDITED — RESOURCE PRIORITY: constraints set-up, data preparation, accounts and live strategy internals not read).
    - **Still open:** E05 (stacks, algos, IB), D01 (roll/contract data; since closed for in-repo code by Phase 10, completed in session 7, as stated at the start of this bullet), G8 (production scheduling), live commission feedback (limited search), the order-simulator effects (O-P9-1/O-P9-2; now TESTED in Phase 15, §16.8, for the provided hourly example) and hourly-data availability in the bundled data (G11), and the provenance of the shipped fixed parameters (N9).
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
    - The §13.6 list names daily-bar, cost-linearity and single-fill-price assumptions that may change for intraday trading, and §10.6 adds engine-level ones (full recomputation per bar, one-row delay, daily-to-intraday ffill alignment) (identified only).
    - Configuration (Phase 13, §14): YAML precedence is backtest config > private config > `defaults.yaml` (nested dicts merged; a `None` value cannot override a default). No config or code versioning was found; exported estimated parameters are last values (O-P13-1); in-repo experiment comparison is account curves plus a t-test (no registry or multiple-testing control found).
    - Degrees of freedom (Phase 17, §18): every degree of freedom in the default system is fixed in config (derivation UNVERIFIED, N9); estimated or optimized modes are opt-in. Safeguards: look-ahead is partially guarded (fit windows end at `period_start`; `delayfill`), with the known exceptions in §15/§16. No safeguard was found against data snooping, repeated experimentation, parameter mining, strategy, instrument, date-range or regime selection, or post-hoc methodology change. Tooling: a t-test only. Bootstrap is documented as removed, and `monte_runs` has no reader.
20. **Evidence discipline.** Session 8 (Phase 15) changed only `last_phase` in the CSV (→ 15 on E02, R01, R05, R08, R09, P09; logged §16.11) and no evidence value (U5 still holds). It reclassified PF-11 and PF-15 in §16.10 without editing §15. Session 6 (Phases 9, 14, 13) changed only `last_phase` in the CSV (→ 9, 14, 13; logged in §10.9, §15.7, §14.6), added no rows (41 kept; the order simulator is not inventoried, DISC-3 raised for the operator, not edited) and changed no evidence value (U5: C04 and R03–R07 stay INFERRED). Phases 11–12 changed P09 (impl_evidence UNVERIFIED → VERIFIED on direct reading, which is not a U5 case; stateful Y; swap Y/PARTIAL, INFERRED) and `last_phase` (11/12). The operator-approved DISC-1/DISC-2 text corrections are in §2, Card 12 and §8.1 Q17, logged in §13.9. Phase 8 changed only `last_phase` (→ 8 on the rows traced in §9) and raised two discrepancies about earlier sections for the operator (DISC-1/DISC-2, not edited), all logged in §9.9. Phase 7 changed one CSV evidence value (P07 UNVERIFIED → VERIFIED on code read) and set `last_phase` to 7 for the rows it covered, all logged in §8.6. Phase 5 changed `impl_evidence` only for P04 and E02 (UNVERIFIED → VERIFIED, after reading their code) and corrected one Phase 4 doc_status label (P04). Phase 5 had also moved R04 and R07 from INFERRED to VERIFIED; both were **reverted to INFERRED** per the operator's literal reading of spec §12 (session 2, U5), because §12 forbids that upgrade. This is logged in §6.5. No counterfactual was relabelled. Session 7 (Phase 10) changed D01 impl_evidence UNVERIFIED → VERIFIED (direct reading, not U5) and `last_phase` → 10 on C05/D01, logged in §11.13. §15 was not edited; the PF-8 supersession is recorded in §11.10. Session 9 (P2, Deliverables 1-2) filled in swing_transfer_label / intraday_transfer_label on all 41 CSV rows (no other field changed, no last_phase change — P2 is synthesis, not a new audited phase) and made two report-text corrections found during Deliverable 2 review: (a) §24.1's Case B recap, which had misstated five components against the CSV's own values (P03, R02, R08, P04, E06), and its Case A sentence, which gave P09 as UNKNOWN, were corrected to match the CSV exactly (plain correction, not a reclassification — the CSV data was already right); (b) §5's Case A/B tables, which still read P09 as UNKNOWN/Not audited from Phase 4, were updated to Y/PARTIAL to reflect the Phase 11 finding recorded in the CSV since session 5 (§13.9), logged as DISC-4. Neither correction changed the CSV or any evidence value.
21. **Transfer analysis (P2, Phases 20-24; §21/§22/§24/§25).** Swing (spec §5: ≤1 decision/day, daily-or-slower data) is the cadence the audited default configuration already runs at, not a different one: 39 of 41 rows are CONCEPTUALLY PORTABLE — UNTESTED for swing; only P09 and E05 are TRANSFER NOT JUSTIFIED, for insufficient audit depth (P09's internals only partially read; Phase 19 skipped for E05), not evidence against transfer. Intraday (sub-daily bars/ticks) is a genuine frequency change: 8 rows CONCEPTUALLY PORTABLE — UNTESTED, 27 POTENTIALLY PORTABLE — REQUIRES REDESIGN, 3 DAILY-DEPENDENT (A03's day-denominated rule parameters; E01's single next-close fill; E03's whole-history-per-decision production loop — all structural, not parametric), 3 TRANSFER NOT JUSTIFIED (P09, E05, A07). Two structural gaps have no CSV row: no market-impact/cost-curve model found in the audited cost machinery (absence UNVERIFIED beyond the searched terms, §13.2), and no stop/target/intrabar-exit channel (SC14). The repository's own source warns its pooled-correlation stacking method "won't work with high frequency data" (DOCUMENTED, in-source, `syscore/pandas/list_of_df.py`). All labels are classifications, not recommendations (spec §43); no component is ranked.
22. **Swing operational readiness (P2, Phase 22; §23).** Research/reference usability at swing cadence is the better-evidenced half: data, contract, roll, carry and FX machinery was read in Phase 10 (§11). Its known limits are specific: retrospective static instrument metadata and availability-based research roll dates (both POSSIBLE ISSUE), unverified shipped-history construction, and no margin or financing model found in the backtest (absence UNVERIFIED beyond the searched terms). Live operational readiness is mostly not assessable: Phase 19 (live / production architecture) was SKIPPED — RESOURCE PRIORITY, so the live side of broker integration, margin, monitoring and deployment rests on file-existence listings only (VERIFIED (listing) establishes a file exists, not its behaviour); only the research-to-live flow up to broker-order creation is VERIFIED (§9.5). This audit supports no claim that live swing operation works, or that it does not.

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

Canonical machine-readable version: `pysystemtrade_framework_inventory.csv` (41 rows; E06 added in Phase 6). Summary layer table:

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
| Dynamic optimisation (P09) | Y | Consumes classic notional positions unchanged (per Phase 11, §12.4); set in the CSV at session 5, see §13.9. (Corrected in P2 Deliverable 2 review; see DISC-4.) |

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
| Dynamic optimisation (P09) | PARTIAL | Inherits upstream forecast semantics (SC9/SC10); has its own TE buffer (§12.4). (Corrected in P2 Deliverable 2 review; see DISC-4.) |

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

**Phase 9 status: COMPLETE** (session 6). Spec §39. All citations are `@ 8958c49`. The work was static source reading only; no experiment was run (§10.8). It builds on §2 "Engines", §3, §5 SC11/SC12, §8.1, §9 and §13.5–13.6; those are cited, not re-derived.

**Evidence discipline.** U5 applies: new source read is recorded as observation; R03–R07 stay INFERRED. PF-n are cited here but classified only in §15.

**Source read this phase** (on top of Phases 3–12):
- accounts entry points: `systems/accounts/accounts_stage.py` (whole); `account_portfolio.py` (whole); `account_instruments.py` (whole); `account_subsystem.py:14-56`; `account_with_multiplier.py:19-40` (grep of the rest); `account_inputs.py:13-120`;
- P&L calculators: `pandl_calculators/pandl_calculation.py` (whole); `pandl_using_fills.py` (whole); `pandl_generic_costs.py` (whole); `pandl_cash_costs.py` (whole); `sysobjects/fills.py:63-103`;
- order simulator: `order_simulator/pandl_order_simulator.py` (whole); `simple_orders.py` (whole); `fills_and_orders.py` (whole); `account_curve_order_simulator.py` (whole); `hourly_market_orders.py` (whole); `hourly_limit_orders.py` (whole); `systems/provided/example/daily_with_order_simulation.{py,yaml}`, `hourly_with_order_simulator.yaml`;
- reporting: `curves/account_curve.py:20-40,200-245` (+ method list); `curves/account_curve_group.py:1-80`;
- data frequency: `sysdata/sim/sim_data.py:98-142`; `syscore/pandas/frequency.py:1-92,169-170,233-265`; `syscore/dateutils.py:595-660`; `positionsizing.py:86-131`; `account_buffering_subsystem.py:100-170`.

### 10.1 End-to-end trace (spec §39: raw data → … → performance)

| Step | Where | What happens | Time index | Evidence |
|---|---|---|---|---|
| Raw data | `simData.get_raw_price` → `daily_prices` | back-adjusted price (raw rows may carry intraday timestamps; daily closes are stamped at the notional closing time 23:00) → `resample("1B").last()` | 1B labels (one per business day) | `sim_data.py:98-127`; `frequency.py:169-170`; `dateutils.py:601-605` VERIFIED |
| Hourly data (optional) | `simData.hourly_prices` | intraday rows only (rows at exactly 23:00 are dropped) → `resample("H").last()` → `dropna()` | hourly labels | `sim_data.py:129-142`; `frequency.py:45-92` VERIFIED |
| Signal | Rules stage (A01/A02) | one call per (instrument, rule) over the whole history; zeros → NaN | index of the rule's input data | §5 SC1–SC4, SC9 VERIFIED |
| Forecast | A04–A08 | scale, cap, ffill, weight, FDM, combined cap/mapping | forecast index; weights, FDM reindexed with ffill | §9.1 D5–D9 VERIFIED |
| Portfolio | P01–P04 | vol scalar reindexed onto the forecast index with ffill (`positionsizing.py:126`); × instrument weight, × IDM, × optional risk scalar | forecast index | §9.1 D10–D13 VERIFIED |
| Position | P05/P06 (+P07) | buffer edges; sequential buffered path (starts at the first optimal, NaN → 0); `buffer_method: none` → plain `round()` of the notional (`account_buffering_system.py:79-84`) | same | `account_buffering_subsystem.py:106-170` VERIFIED |
| Fill | E01 (`pandlCalculationWithFills`) | positions `shift(1)` if `delayfill`, then `round()`; fills = non-zero, non-NaN `diff()` of that series, priced at the (ffilled) price of the fill row | fill at row *t+1* for a decision at *t* | `pandl_calculation.py:150-159`; `pandl_using_fills.py:48-70`; `fills.py:93-103` VERIFIED |
| Cost | E02 | per inferred fill + roll pseudo-fills (opening and closing at `rolls_per_year` equal dates, qty = mean \|position\| over the preceding interval × `multiply_roll_costs_by`) × vol deflator (PF-2); or the SR-cost drag | fill dates | `pandl_cash_costs.py:68-203`; §13.2 VERIFIED |
| Account | `pandlCalculation` | gross = `positions.shift(1) × Δprice` (after ffill of both) × point value × FX (ffill-reindexed); net = gross + costs (`add(..., fill_value=0)`); % = ÷ capital (fixed notional by default, or `get_actual_capital` = capital × multiplier `shift(1)` in `portfolio_with_multiplier`) | price index | `pandl_calculation.py:77-126,223-235`; `pandl_generic_costs.py:29-108`; `account_with_multiplier.py:19-40,108-131` VERIFIED |
| P&L | `accountCurve` | a `pd.Series` subclass: the calculator's series summed into `Frequency.BDay` bins by default (`resample(...).sum()`) | business days | `account_curve.py:20-40`; `pandl_calculation.py:64-75` VERIFIED |
| Performance | `accountCurve` / `accountCurveGroup` | Sharpe = (sum ÷ years) ÷ (period std × √periods per year); drawdown on `cumsum()`; Sortino, skew, hit rate, t-test etc.; the portfolio is the *sum* of instrument calculators (`summed_pandl_calculator`, `weighted=True`) | BDay, or weekly/monthly/annual views | `account_curve.py:200-392` (statistics methods); `account_curve_group.py:16-80`; `account_portfolio.py:20-66` VERIFIED |

### 10.2 Spec §39 dimensions

| Dimension | Implemented | Evidence |
|---|---|---|
| Time advancement | **None in the default engine.** There is no clock or bar loop. Every stage returns the whole history as one pandas object; "time" is the index. Only P06 (and, when enabled, `half_compounding`, the risk-series loop, the per-fit-period estimator loops, P09 and the order simulator §10.4) iterate over rows or periods | §2 Engines; §3; `account_buffering_subsystem.py:146-157` VERIFIED |
| Recalculation | Lazy and pull-based: requesting a leaf (e.g. `accounts.portfolio()`) recursively computes and caches every upstream series. Nothing is recomputed incrementally. A new bar requires a new System (or cache deletion) and a full-history recomputation | §3 (Lazy evaluation) VERIFIED; `backtesting.md:1435` DOCUMENTED |
| Caching | Per-System memo keyed on (stage, method, instrument, args); config and data are not in the key; protected items survive deletion; `base_system_cache` ignores arguments | §3; EXP-02 TESTED |
| Estimation | Whole-history estimators produce per-row series or per-fit-period values that are reindexed onto the daily index (§8.1). Estimation is part of the same lazy tree, not a separate walk-forward driver | §8.1 Q3–Q14 |
| Signal availability | Forecast at label *t* is treated as known at *t* (SC11). The framework does not lag the forecast; lagging is done in P&L | SC11 VERIFIED |
| Position timing | Position at label *t* is decided with data labelled ≤ *t*; with `delayfill=True` it is held from *t+1* | `pandl_calculation.py:150-159` VERIFIED |
| Fills | Inferred from position changes (vectorised), one fill per changed row, at the single aligned price of that row. No partial fills, queue, latency or intrabar path | `fills.py:93-103`; §13.6 item 4 VERIFIED |
| Costs | Attached to fills (cash) or as a smooth SR drag; never fed back into the same run's positions (default) | §13.1–§13.4 VERIFIED |
| Account state | P&L in points → instrument currency → base currency → % of capital. **No cash balance, margin, financing or interest model was found** (searched `systems/` for `margin`; `systems/accounts` for `interest`, `cash_balance`, `funding`: no hits; absence UNVERIFIED beyond these terms). Capital is either the fixed notional or a multiplier path (P07) | `pandl_calculation.py:77-126` VERIFIED |
| Risk | Ex-ante: vol targeting (P01) and the optional risk overlay (P04). Ex-post: the curve statistics above. No risk-based stop or intra-period risk check exists in the backtest (the backtest has no intra-period time) | §9.1 D10/D13; `account_curve.py` VERIFIED |
| P&L | `positions.shift(1) × price.diff()` after `delayfill` shift: a position decided at close *t* is filled at the *t+1* price and earns returns from close *t+1* onward (default) | `pandl_calculation.py:223-235` VERIFIED static (Phase 16 traces it) |
| Reporting | `accountCurve` statistics; `accountCurveGroup` per-instrument / per-rule views; gross / net / costs curves | `account_curve.py`; `account_curve_group.py` VERIFIED |

### 10.3 Architecture classification (spec §39 vocabulary)

- **Vectorised, whole-history, daily-bar driven, pull-based (lazy), memoised.** VERIFIED (§3, §10.2).
- **Hybrid in two places.** (i) P06 is a stateful per-row loop inside an otherwise vectorised tree (default); (ii) the optional order simulator (§10.4) replaces vectorised fill inference with a per-row stateful order/fill loop. VERIFIED.
- **Not event-driven.** No event queue, callbacks, clock or order book was found in `systems/`; the order simulator iterates over an index but does not dispatch events. VERIFIED for the files read; wider absence is INFERRED.
- **Stateless at the rule level, stateful only in path loops.** Rules receive no position or fill state (SC5). Path state exists only in P06, `half_compounding`, P09 and the order simulator (all but P06 non-default). VERIFIED.
- **Frequency.** Daily (1B) by default. An hourly path exists: `get_hourly_prices`, P&L price lookup for hourly positions (`account_inputs.py:35-60`), and the hourly order simulators. Calibration statistics remain business-day based (SC12). VERIFIED.
- **Live engine.** A daily re-run of the same System, with the last row used as the decision (§9.5). This is the same vectorised engine, not a separate live event engine. VERIFIED.

### 10.4 Alternative accounts stage: the order simulator (not in the inventory; undocumented)

- **What it is.** `AccountWithOrderSimulator(Account)` overrides `pandl_for_instrument`, `pandl_for_subsystem`, `get_buffered_position` and `get_buffered_subsystem_position` (`account_curve_order_simulator.py:14-175`). The header comment of the example says: "HOW TO USE A PROPER ORDER SIMULATOR RATHER THAN VECTORISED P&L" (`daily_with_order_simulation.py:1-2`). VERIFIED.
- **Loop.** `generate_positions_orders_and_fills_from_series_data` walks the index up to the penultimate row. At row *i* it reads the unrounded optimal position at *i*, submits `round(optimal_i) − current` as an order dated *i*, and fills it at row *i+1* at the *i+1* price (market orders). The position series is the cumulative fill path (`pandl_order_simulator.py:169-269`). Stateful, path-dependent. VERIFIED.
- **Buffering is bypassed.** The simulator's input is `get_notional_position` (instrument) or `get_subsystem_position` (subsystem), unbuffered (`account_curve_order_simulator.py:157-165`); the example configs set `buffer_method: 'none'` with the comment "not used with order sim" (`daily_with_order_simulation.yaml:5`). VERIFIED.
- **Restrictions.** It raises unless `roundpositions=True`, `delayfill=True` and cash costs are used (`:178-188`). VERIFIED.
- **Hourly variants.** `HourlyOrderSimulatorOfMarketOrders` uses hourly prices; `HourlyOrderSimulatorOfLimitOrders` submits a limit at the *current* price and fills at that limit only if the *next* price is strictly better (buy: limit > next; sell: limit < next), otherwise no fill (`hourly_limit_orders.py:36-65`; `fills_and_orders.py:64-88`). VERIFIED.
- **Observations (VERIFIED code; effects INFERRED, not tested):**
  - O-P9-1: gross P&L is computed from the positions implied by the fills against the simulator's price series (`order_simulator.prices()`), not against the fill prices. The `merge_fill_prices_with_prices` helper exists but is not called on this path (`pandl_using_fills.py:36-46,94-114`; `account_curve_order_simulator.py:99-137`). So a limit fill's price difference versus the bar price is reflected only in costs, not in gross P&L (INFERRED from the call path).
  - O-P9-2: the limit-fill `price_requires_slippage_adjustment` flag is `False` for buys and `True` for sells (`fills_and_orders.py:70-86`). Recorded without judgement; the intent is not documented.
  - O-P9-3: the example header refers to "a simple trend system using daily data"; the rule `ewmac_forecast_with_defaults` used in the hourly example config is docstring-labelled "Assumes that 'price' is daily data" and "ONLY USED FOR EXAMPLES" (`rules/ewmac.py:4-12`), while the hourly config feeds it `rawdata.get_hourly_prices`. Its Lfast/Lslow are then in hours. VERIFIED (code and config); consequences INFERRED.
- **Documentation.** `docs/*.md` searched for `order simulat`, `order_simulat`, `vectorised`, `vectorized`, `event.driven`, `event driven`: no hits. Recorded as **UD5** (undocumented).
- **Inventory.** Not a CSV row (the CSV is held at 41 rows by operator decision). It sits in `systems/accounts/order_simulator/*`, next to E01/P06, and is noted here and in the register only. See §10.9.

### 10.5 Mixed-frequency alignment (input for §15)

- Daily series are labelled at 00:00 of day *t* but hold the last price of day *t* (1B resample of rows stamped up to 23:00). In a daily-only System all series share these labels, so SC11 ("value at *t* known at close *t*") is internally consistent.
- When the forecast index is hourly (hourly rules), daily-derived series are aligned onto it by `reindex(..., method="ffill")`: the vol scalar (`positionsizing.py:126`), weights, FDM, IDM (§10.1). A daily value labelled 00:00 of day *t* is then applied to every hourly bar of day *t*, including bars before that day's close. This is recorded as **PF-14 (new candidate)** and classified in §15. VERIFIED (alignment code); the label position of `resample("1B")` is checked in §15 (EXP-04).

### 10.6 Assumptions relevant to higher-frequency transfer (identified only; no replacement designed)

1. **Whole-history recomputation per decision.** No incremental update path; each new bar means recomputing (or re-running) the full tree. Live does exactly this once per run (PF-9). VERIFIED.
2. **Single price per bar** for fills, P&L and costs; fills at the next bar's price; no partial fills, queue, latency or intrabar sequencing (also §13.6 item 4). VERIFIED.
3. **One-bar delay is the only execution lag** (`delayfill` shifts by one *row*, whatever the row frequency). VERIFIED.
4. **Business-day calibration** of vol, turnover, SR costs and weights (SC12) even when the forecast index is hourly; performance statistics default to BDay bins. VERIFIED.
5. **Daily-to-intraday alignment by ffill of 00:00 labels** (§10.5, PF-14). VERIFIED code.
6. **Buffering is a per-row path over the decision index**; in the order simulator it is bypassed (trade every change in the rounded optimum). VERIFIED.
7. **No account state beyond capital** (no margin or financing; absence UNVERIFIED beyond the searched terms).
8. **No event channel.** Stops, targets, entry/exit events cannot be expressed at the engine level (SC14/SC16). VERIFIED.

### 10.7 Documentation / implementation items

- **UD5** (new): the order-simulator accounts stage and its hourly market/limit variants are undocumented in `docs/` (search above). VERIFIED.
- No new DV item. The docs' description of a daily-lagged P&L is consistent with the code (`delayfill` docstrings: "Lag fills by one day", `account_portfolio.py:14`; for hourly positions the lag is one hourly row, INFERRED from `_process_positions`).

### 10.8 Experiments

NOT TESTED — REASON: every Phase 9 question (loop structure, fill inference, P&L formula, reporting frequency, order-simulator control flow) was settled by static reading (spec §22). The quantitative effect of O-P9-1/O-P9-2 would need a controlled run with hourly data, which is not bundled in the csv sim data (hourly data availability was not checked; UNVERIFIED). Left for Phase 15/16 subject to operator approval.

### 10.9 Phase 9 change log (explicit)

| Item | Change | Basis |
|---|---|---|
| CSV `last_phase` | → 9 for C01, C02, C03, C05, E01 (the engine rows traced in §10.1–§10.3) | Traced in Phase 9 |
| CSV other fields | **unchanged** (R03–R07 stay INFERRED; D01/E05 stay UNVERIFIED; E06 unchanged; transfer labels `NOT YET ASSESSED`) | U5; operator instructions |
| CSV rows | **none added** (41 rows kept). The order simulator (§10.4) is *not* inventoried; raised for the operator as DISC-3 below | Operator: CSV fixed at 41 rows |
| Divergence register | UD5 added | §10.4 |
| Pre-flags | PF-14 candidate added (unclassified here) | §10.5 |
| Earlier sections | not edited | — |

**Discrepancy for the operator (NOT edited):**

| # | Location | Statement | Finding |
|---|---|---|---|
| DISC-3 | §2 "Engines"; §4 layer table; Card 12 | §2 says "In the default configuration the only path-dependent per-period loop is the buffered position path P06" and lists the other loops; §4 says "P06 is the only path-dependent step in the backtest" | Both are correct for the default configuration, but neither list names the order simulator's per-row fill loop (`pandl_order_simulator.py:169-212`), which is a further path-dependent loop in an alternative accounts stage (non-default). §4's unqualified wording ("the only path-dependent step in the backtest") is not limited to the default configuration. VERIFIED (code) |

## 11. Data / Contract / Roll Architecture

**Phase 10 status: COMPLETE** (session 7). Spec §39. All citations are `@ 8958c49` unless stated. The work was static reading plus one small synthetic experiment (EXP-05).

**Rules applied.**
- U5 applies: R03–R07 stay INFERRED.
- Causality labels use the Phase 14 vocabulary (§15).
- Earlier sections are **not** edited. Where Phase 10 changes the reading of an earlier item (PF-8, D01), the relationship is recorded here (§11.8) and in the progress file.

### 11.1 Data source architecture

| Question | Finding | Evidence |
|---|---|---|
| Where market data enters | `simData` subclasses: `csvFuturesSimData` (default: shipped CSVs under `data/futures/`), `dbFuturesSimData` (Mongo/Parquet), and a production wrapper | `sysdata/sim/csv_futures_sim_data.py`, `db_futures_sim_data.py`; `docs/data.md:116` ("For simulation, we could just use the provided CSV files (1), and this is the default") VERIFIED / DOCUMENTED |
| Objects and fields | **Adjusted prices** (`futuresAdjustedPrices`, one series). **Multiple prices** (`futuresMultiplePrices`: `PRICE, PRICE_CONTRACT, CARRY, CARRY_CONTRACT, FORWARD, FORWARD_CONTRACT`). Spot FX series. Instrument metadata (`Pointsize, Currency, AssetClass, PerBlock, Percentage, PerTrade`). Spread costs. Roll parameters (`HoldRollCycle, RollOffsetDays, CarryOffset, PricedRollCycle, ExpiryOffset`) | `sysobjects/adjusted_prices.py:14-60`; `multiple_prices.py:70-110`; `data/futures/csvconfig/*.csv` headers VERIFIED |
| Metadata association | By `instrument_code` key; a single static row per instrument (§11.8) | `futures_sim_data.py:132-245` VERIFIED |
| Frequency | Stored series are irregular timestamps (e.g. SOFR multiple prices stamped `23:00:00`). `daily_prices` = `resample("1B").last()`; hourly access exists (`hourly_prices`) | `data/futures/multiple_prices_csv/SOFR.csv` header rows; `sim_data.py:98-137` VERIFIED |
| Timestamp convention | The value at a timestamp is the observed (closing or sampled) price at that time. The 1B-last label is the business day (SC11). No explicit "close time" field was found | INFERRED from the data and the resample code |
| Missing observations | No filling in the multiple-price builder (§11.3). Downstream ffills are the ones already recorded in §8/§9. `interpolate_data_during_day` has **no callers** (repo-wide `*.py` search) | `syscore/pandas/frequency.py:192-216`; search VERIFIED |
| Pre-System transformation | The back-adjusted series is precomputed and stored; the System reads it, it does not build it | `futures_sim_data.py:68-80,213-222` VERIFIED |

### 11.2 Futures contract handling and roll mechanics

There are **two distinct roll mechanisms**:

- **(R1) Historical / backfill roll calendar (research data).** Built by `sysinit` tools (`rollCalendar.create_from_prices`, `sysobjects/roll_calendars.py:36-52`; `sysinit/futures/build_roll_calendars.py`).
  1. **Approximate roll date** = approximate expiry (from the contract date + static `ExpiryOffset`) + static `RollOffsetDays` (`rolls.py:417-421`; `rollconfig.csv`, e.g. `AEX … -5,1,…,19`). The held and priced contracts follow the static `HoldRollCycle` / `PricedRollCycle`; the carry contract is the next (+1) or previous (−1) priced contract per static `CarryOffset` (`roll_parameters_with_price_data.py:206-224`; `rolls.py:409-415`).
  2. **Adjustment** (`build_roll_calendars.py:415-500`): the roll date is moved to the **closest date, earlier or later**, on which the current, next and carry contract prices are **all non-NaN** in the full price dataset. The inputs are static parameters plus **price availability** (NaN or not) over the whole dataset; **no price values, volumes or open interest** are used (VERIFIED, code).
  3. Alternatively, a calendar can be **backed out of existing multiple prices** (`back_out_roll_calendar_from_multiple_prices`, `roll_calendars.py:53-66`). The docs say the shipped calendars were generated this way from shipped multiple prices (`docs/data.md:261,339`, DOCUMENTED).
- **(R2) Live roll (production).** A roll-status process: `interactive_update_roll_status.py` (`roll_adjusted_and_multiple_prices`, `:767-800`), with auto-update parameters in config (`roll_status_auto_update`: relative-volume threshold 1.0, `near_expiry_days` 10, `auto_roll_expired`; `defaults.yaml`). Adjusted prices are re-stitched at the roll, with operator confirmation by default. Between rolls, adjusted prices are appended without re-adjustment (`update_with_multiple_prices_no_roll`, `adjusted_prices.py:53-67,141-192`; caller `sysproduction/update_multiple_adjusted_prices.py:161`). The volume-based decision internals were **not read**, so R2's exact trigger logic is **UNVERIFIED**; that it uses volume and expiry parameters is VERIFIED only from config names.
- **Research/live roll consistency.** R1 (static offset + availability) and R2 (volume/expiry status process) are different mechanisms, so historical roll dates in research data need not match how live rolls are decided (INFERRED; not compared on data).

### 11.3 Multiple prices (PRICE / CARRY / FORWARD) construction

`create_multiple_price_stack_from_raw_data` (`sysinit/futures/build_multiple_prices_from_raw_data.py:60-340`):
- For each roll period `(previous roll + offset, next roll]`, it takes the **raw closing prices** of the current, next (FORWARD) and carry contracts, sliced to the period.
- A grep of the builder for `ffill|bfill|fillna|shift|interp|resample` found no filling. So the value in each column at date *t* is that contract's own observed price at *t* (VERIFIED, code).
- **Which contract** is in each column at *t* is set by the roll calendar (R1).

### 11.4 Continuous futures (back-adjustment)

- **Method: Panama (additive / difference) back-adjustment only.** No ratio adjustment and no alternative stitcher was found (the stitcher's docstring says "If you want to change then override this method"). Searched `sysobjects/adjusted_prices.py` and callers of `stitch_multiple_prices` (`sysinit/futures/adjustedprices_from_db_multiple_to_db.py:54`, `sysproduction/reporting/data/rolls.py:184`). DOCUMENTED (`docs/backtesting.md:1954`, "Panama method").
- **Algorithm** (`adjusted_prices.py:70-138`): walk the multiple prices; on a row whose `PRICE_CONTRACT` differs from the previous row's, compute `roll_differential = previous_row.FORWARD − previous_row.PRICE` and **add it to every earlier adjusted value**, then append the new contract's price. If the differential is NaN, raise. VERIFIED.
- **EXP-05** (`scaffolding/experiments/exp05_panama_mutation.py`, synthetic, framework's own stitcher):
  - *Purpose:* does a later roll change earlier adjusted values, and earlier differences?
  - *Setup:* 12 business days; contract A → B on day 6, B → C on day 11. The day-10 history is stitched before the second roll (11 rows) and again after it (12 rows).
  - *Result:* every day-0…10 level shifts by the **same constant, 8** (= day-10 `FORWARD − PRICE` = 121 − 113). **Every earlier one-day difference is unchanged.** The roll-day difference equals the new contract's own move (−3 = B(day 6) − B_fwd(day 5)).
  - *Interpretation:* historical **levels are mutated** by later rolls; **differences over any interval ending at or before T are not**, because only roll differentials between the two dates enter them, and those were observed by the later date.
  - *Evidence:* **TESTED** (mechanism, synthetic data). The general statement for any series is VERIFIED from the code.

### 11.5 Carry

- **Meaning** (repo): carry = annualised roll yield, `(PRICE − CARRY) / contract-date differential`, normalised by price-difference vol. Implemented as `rawdata.raw_carry`, then smoothed or asset-class median versions; consumed by the carry rule (`systems/provided/rules/carry.py`). §8 Q15 has the formula details (VERIFIED in Phase 7).
- **Source:** the `PRICE`/`CARRY` columns and contract identifiers of the multiple prices (§11.3). This is stored data, not computed in the System.
- **Timing of the values:** PRICE and CARRY at *t* are both contracts' observed prices at *t*; the differential uses contract identifiers (dates) only. So the carry *value* at *t* uses no price after *t* (VERIFIED, code; §8 Q15).
- **Decision impact:** **yes.** The default chapter-15 config includes carry rules fed by `rawdata.raw_carry` (`futuresconfig.yaml:66-67`), so carry enters forecasts and positions.
- **Contract choice:** the CARRY contract per date comes from the roll calendar (R1: a static `CarryOffset` rule plus data availability), or from the shipped multiple-price CSVs (§11.7).

### 11.6 FX

- Spot FX series come from `fx_prices_csv` (sim) or the DB, via `get_fx_for_instrument` (`sim_data.py:144-170`). Base-currency = instrument-currency rates return 1.0 (doctest).
- Alignment downstream is `reindex(..., ffill)` onto the position or vol index (`positionsizing.py:206-246,512-540`).
- A search of `sysdata/sim/*.py`, `sysobjects/spot_fx_prices.py`, `multiple_prices.py`, `adjusted_prices.py`, `rawdata.py` and `frequency.py` for `bfill|backfill|interpolate` found no backward fill in the FX path.
- **NO ISSUE IDENTIFIED.**

### 11.7 Provenance of the default (shipped) data

- **Default backtests read shipped CSVs** (`docs/data.md:116`).
- The shipped multiple prices were "built myself" by the author (`docs/data.md:339`), and the shipped roll calendars were generated *from* those multiple prices (`:261`).
- Example: SOFR multiple prices start `1984-03-23`, while the shipped SOFR roll calendar starts `2020-03-31` (file heads). So the pre-2020 contract selection in the shipped data **cannot be reproduced from shipped inputs**.
- Its construction rule (R1 or otherwise) is **external to the repository**: **UNVERIFIED**.
- Shipped data was last changed in commit `44208025` (2024-05-01, `git log` on the CSV directories).

### 11.8 Instrument metadata

- `Pointsize`, `Currency` and the cost fields are **one static row per instrument** with **no date dimension** (`futures_sim_data.py:169-185`: `block_move_value = meta_data.Pointsize`).
- Changes are made by editing the CSV and apply to **all history**. Example: commit `073422ae` (2026-04-26) "Update SGX STI futures multiplier from 10 to 2", which changed `SGX,…,10,…` → `SGX,…,2,…` in `instrumentconfig.csv`.
- Expiry is approximated from the contract date + static `ExpiryOffset` (roll config).
- Metadata is therefore **current, not historically versioned** (VERIFIED). Effect on positions: contract counts scale ∝ 1/Pointsize while P&L ∝ Pointsize, so the unrounded notional risk is unchanged. Rounding, per-block commissions and live execution are affected (INFERRED, not tested).

### 11.9 Historical price mutation (spec checklist)

| Mechanism | (1) Values changed | (2) Trigger | (3) Determining information | (4) Available at the original timestamp? | (5) Feeds forecast / position? | (6) Verdict |
|---|---|---|---|---|---|---|
| Panama back-adjustment (default price series) | all adjusted **levels** before a roll | each later roll | `FORWARD − PRICE` on the day before the roll | **No** for the level shift (a later roll); **yes** for any difference whose endpoints straddle only earlier rolls | Yes: rules (`get_daily_prices`), vol, P&L. But the default rules use differences or ranges (EWMAC, breakout, accel; §15 PF-8 note), and % vol divides by the **raw** price (Q2) | **Data representation**, not a timing issue, for difference-invariant consumers (EXP-05). **POSSIBLE ISSUE** only for any consumer of adjusted *levels*: none found among the provided rules (searched `systems/provided/rules/*.py` for `np.log`, `/ price`, `pct_change`, `.div(`); user rules are not covered |
| Roll-date selection (R1) | which contract feeds PRICE/CARRY/FORWARD around a roll | calendar (re)build | static offsets + **full-dataset price availability** (nearest date with all prices, either direction) | Availability of *later* dates can move a roll **earlier** (post-T availability information); no price values or volume are used | Yes (PRICE via adjusted prices; CARRY via carry rules) | **POSSIBLE ISSUE** (timing dependency on data availability; effect not established) |
| Shipped historical multiple prices | contract selection pre-calendar | external build | unknown (external) | unknown | Yes (default backtests) | **UNVERIFIED** |
| Instrument metadata edits | Pointsize/costs for all history | a CSV edit | the current contract spec | No (a later spec applied backward) | Yes (sizing, costs) | **POSSIBLE ISSUE** (retrospective metadata; risk-neutral for unrounded notional, INFERRED) |
| Live rolls (R2) | adjusted levels at the roll | a live roll | the day's prices | Yes (decided at the roll) | Yes (live) | **NO ISSUE IDENTIFIED** (look-ahead); trigger internals UNVERIFIED |

### 11.10 PF-8 — carry / roll data (resolution)

- **Classification:** **POSSIBLE ISSUE**, with components:
  - (a) back-adjustment levels: **NO ISSUE IDENTIFIED** for the provided difference-based rules;
  - (b) carry value formula: **NO ISSUE IDENTIFIED** (values at *t* only);
  - (c) framework-built roll calendar (R1): **POSSIBLE ISSUE**, because roll dates use full-dataset price *availability*;
  - (d) the default shipped historical multiple prices: **UNVERIFIED** (external construction).
- **Evidence:**
  - `adjusted_prices.py:70-138` and EXP-05 (TESTED);
  - `build_multiple_prices_from_raw_data.py:60-340` (no fills);
  - `build_roll_calendars.py:415-500` and `rolls.py:417-421`;
  - `roll_parameters_with_price_data.py:206-224`;
  - §8 Q15;
  - `docs/data.md:116,261,339`.
- **Code path:**
  - shipped CSV / DB multiple and adjusted prices → `csvFuturesSimData.get_backadjusted_futures_price` / `get_multiple_prices` → `rawdata.get_daily_prices`, `raw_carry` → rules (EWMAC, breakout, accel, carry) → forecasts → positions;
  - separately, `sysinit` tools build calendars, multiple prices and adjusted prices offline.
- **Can it affect a trading decision?** Yes. Carry rules and all price rules consume these series in the default config.
- **Is future information required?**
  - Not for carry values or for the price differences used by the provided rules.
  - Potentially for **roll timing** (data availability after T), in framework-built calendars.
  - Unknown for the shipped history.
- **Remaining uncertainty:**
  - the construction of the shipped pre-calendar history;
  - the size of the effect of availability-based roll dating;
  - user-written rules that use adjusted price levels;
  - the R2 trigger internals.
- **Relationship to earlier findings:** this **supersedes** the §15 PF-8 classification (UNVERIFIED — "only checkable in Phase 10"). §15 is not edited; this section is authoritative for PF-8 from session 7.

### 11.11 D01 — data / contract gap (resolution)

- **What D01 asked:** the construction of multiple prices, adjusted (Panama) prices and roll calendars built outside the System (`sysinit`, production updaters). The CSV row D01 was `impl_evidence = UNVERIFIED` (Phase 4 onward; G6).
- **Phase 10 evidence:**
  - the Panama stitcher, read and TESTED (EXP-05);
  - the multiple-price builder, read (no fills);
  - roll calendar generation and adjustment, read;
  - the carry-contract rule, read;
  - live no-roll append and roll re-stitch entry points, located;
  - shipped-data provenance, DOCUMENTED as author-built.
- **Classification:** D01 **impl_evidence UNVERIFIED → VERIFIED** for the in-repo construction code. This is direct reading, an UNVERIFIED → VERIFIED change, not a U5 case; it is logged in §11.13.
- **Remaining uncertainty (UNVERIFIED):**
  - how the shipped historical CSVs were built;
  - the internals of the live roll-status decision (R2);
  - Parquet/Mongo storage paths (not read).
- **G6 status:** D01 part addressed. P09 was already handled in Phase 11.

### 11.12 Experiments

- **EXP-05:** as above (TESTED, synthetic).
- **NOT TESTED — REASON** for everything else:
  - The effect of availability-based roll dating on real data would need rebuilding calendars from raw contract prices, which are not shipped (only multiple and adjusted prices are). The effect size therefore stays UNVERIFIED.
  - The metadata-edit effect was not run; it is a formula-level inference.

### 11.13 Session 7 change log (explicit)

| ID | Field | Change | Basis |
|---|---|---|---|
| D01_PRICE_ROLL_DATA | impl_evidence | UNVERIFIED → **VERIFIED** | §11.2–§11.4, §11.11; UNVERIFIED → VERIFIED on direct reading (not U5) |
| C05_SIMDATA, D01_PRICE_ROLL_DATA | last_phase | → 10 | Covered in §11 |

No other CSV field changed. D01 `divergence` stays UNKNOWN: no conflict was found in the doc lines read, but they are too limited to support N. R03–R07 stay INFERRED. E05 stays UNVERIFIED. E06 is unchanged. Transfer labels stay `NOT YET ASSESSED`. **No new DV/UD entries:** the retrospective metadata and roll-dating properties are recorded as findings, not documentation divergences.

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

**Phase 13 status: COMPLETE (targeted)** (session 6). Spec §39 ("keep targeted"). All citations are `@ 8958c49`. The work was static source reading only; no experiment was run (§14.5). Configuration facts already established (C04 in §6, the cache/config interaction in §3, the estimation flags in `audit_progress.md`, the defaults in §8) are cited, not re-derived.

**Source read this phase:** `sysdata/config/configdata.py` (whole); `fill_config_dict_with_defaults.py` (whole); `private_config.py` (whole); `defaults.py` (whole); `sysdata/config/defaults.yaml:1-40,345-395`; `systems/diagoutput.py:140-285`; `sysproduction/data/backtest.py:185-240`; `syscore/objects.py:29-44`; `systems/accounts/curves/account_curve_analysis.py:10-40`; `data/futures/csvconfig/*.csv` (headers); `docs/backtesting.md:268-285,363,963-1125,1255-1275,3016-3024`; `docs/production.md:301`.

### 14.1 Spec §39 items

| Item | Implemented | Evidence |
|---|---|---|
| **Configurable components** | Almost every stage parameter is a config element read through `self.config.<name>` or `get_element_or_default`: trading rules (function + data + args), scalars, caps, weights, FDM/IDM, every estimator (`func`, window, `date_method`, pooling, cleaning), vol function and spans, buffers, costs flags, capital multiplier function, risk overlay, instrument lists and exclusion lists, production settings. Functions are named by dotted strings and resolved at run time (`resolve_function`) | `configdata.py:37-270`; `syscore/objects.py:29-44`; `defaults.yaml` VERIFIED |
| **Strategy representation (research)** | A strategy *is* a `System`: a Python list of stage objects + one `simData` + one `Config` (§3). Provided systems are Python factory functions (e.g. `futures_system()`) plus a YAML file | §3; `systems/provided/*` VERIFIED |
| **Strategy representation (production)** | `strategy_list` in (private) config maps a strategy name to `load_backtests: {object, function}` and `reporting_code: {function}`; `strategy_capital_allocation` with `strategy_weights` (must be in private config); per-strategy backtest config files | `defaults.yaml:9-24` (commented template) VERIFIED |
| **Instrument representation** | Sim: `data/futures/csvconfig/instrumentconfig.csv` (Pointsize, Currency, AssetClass, PerBlock, Percentage, PerTrade, Region), `spreadcosts.csv` (SpreadCost), `rollconfig.csv` (HoldRollCycle, RollOffsetDays, CarryOffset, PricedRollCycle, ExpiryOffset); production equivalents in the database. The *universe* is config (`instrument_weights` keys → `instruments` → all instruments in data) minus config exclusion lists (§15 PF-12) | csv headers; `futures_sim_data.py:132-247`; `basesystem.py:205-222` VERIFIED |
| **Portfolio representation** | `instrument_weights` dict + `instrument_div_multiplier` in config (fixed), or the estimation blocks; `notional_trading_capital`, `percentage_vol_target`, `base_currency`; `capital_multiplier.func` | `defaults.yaml`; §6 Cards 9–10 VERIFIED |
| **Parameter storage** | (i) YAML files: the backtest config (one or a list; later items override earlier; a `base_config` key loads a parent first), `private/private_config.yaml` (directory overridable by `PYSYS_PRIVATE_CONFIG_DIR`), and `sysdata/config/defaults.yaml`. (ii) Estimated parameters live only in the System cache (protected items, §3) unless exported: `systemDiag.yaml_config_with_estimated_parameters` writes the **last** value of forecast scalars, forecast weights, FDM, mapping, instrument weights and IDM to YAML (values taken with `values[-1]` / `.iloc[-1]`). (iii) The whole cache can be pickled (`system.cache.pickle/unpickle`). (iv) Production stores a pickled backtest state and the effective config per run (`store_backtest_state`) | `configdata.py:122-175,218-262`; `private_config.py:9-38`; `diagoutput.py:140-285`; `system_cache.py:196-265`; `sysproduction/data/backtest.py:191-215` VERIFIED |
| **Precedence** | `fill_with_defaults` (run by `System.__init__` → `config.system_init()`): backtest config first, then private, then defaults, merged recursively for nested dicts. A key whose config value is `None` is **replaced** by the default (`if config_value is None: config_value = default_value`), so a YAML `null` cannot switch a default off. Lists and scalars are replaced wholesale. The passed `Config` object is mutated in place. DOCUMENTED (`backtesting.md:273-281,363,1079-1124`), apart from the `None` rule | `fill_config_dict_with_defaults.py:1-25`; `configdata.py:218-237` VERIFIED |
| **Reproducibility** | Results are a deterministic function of (code, effective config, data) for a *fresh* System (§3). No random number generation was found outside tests (`git grep "np.random\|import random"` in `systems sysquant syscore sysdata`, tests excluded: no hits). Threats: (a) the private config and `defaults.yaml` silently enter every backtest; (b) config and data are not in cache keys, and protected items survive deletion (§3); (c) the fit-period grid moves when data is added (O2/PF-11); (d) production re-runs over growing data (PF-9); (e) functions named by string resolve to whatever code is installed | §3; §8 O2; `configdata.py:218-237` VERIFIED; (a)–(e) consequences INFERRED |
| **Configuration versioning** | **None found.** No config version field, content hash, or code-version (git SHA) stamp was found in `Config`, `store_backtest_state` or the cache pickle (searched `systems sysquant sysdata/config sysproduction/data/backtest.py syscore` for `git rev`, `rev-parse`, `__version__`, `config_version`, `code_version`; no hits outside tests). Production backtest state files carry only a datetime marker and strategy name, and are deleted after `backtest_max_age: 30` days (`clean_truncate_backtest_states.py`). Absence beyond the searched terms is UNVERIFIED | `sysproduction/data/backtest.py:191-215`; `defaults.yaml:26-28` VERIFIED |
| **Code / config interaction** | Config names code: rule functions, estimator functions, vol function, capital multiplier function, production `object`/`function` strings (`resolve_function`). A misspelled key is silently absent: `get_element_or_default` returns the default, and `__setattr__` accepts any new element name. The documented key names that differ from the code (DV8, DV9) would therefore be ignored without error (INFERRED from the lookup code). Changing `config.trading_rules` after first use has no effect because rules are parsed once (§3 (iv)) | `configdata.py:103-116,201-216`; §3; DV8/DV9 VERIFIED; silent-ignore consequence INFERRED |
| **Experiment comparison** | In-framework tools: account curves and groups (per instrument, per rule, gross/net/costs; `accountCurve.stats()`), `accurve.t_test()`, and `account_t_test(acc1, acc2)` (a two-sided t-test on normalised returns over the common period, `account_curve_analysis.py:16-40`); `systemDiag` checks of scaling and the estimated parameters. There is **no** experiment registry, run database, parameter-sweep driver or multiple-testing adjustment in the files read (searched as above; absence UNVERIFIED beyond them). The docs warn that "the assumptions underlying a t-test may be violated for financial data" (`backtesting.md:3022`) | `account_curve.py`; `account_curve_analysis.py:16-40`; `diagoutput.py` VERIFIED |

### 14.2 Observations (Phase 13)

- **O-P13-1 (exported parameters are last values).** `yaml_config_with_estimated_parameters` exports the *final* estimate of each parameter. The docs describe the export as saving "the final optimised parameters into fixed weights for live trading" and say "You can then merge the resulting YAML file into your simulated YAML file" (`backtesting.md:1259,1275`; also `production.md:301`). This is recorded without judgement: for live use the last values are the current values; merged into a *simulated* backtest they are end-of-sample values applied to the whole history (the in-sample consequence is INFERRED, not tested). Links to §15 N9. The export code takes `.iloc[-1]` / `.values[-1]` (`diagoutput.py:167-170,193,210,226,241`).
- **O-P13-2 (private config reaches backtests).** A file outside the repository (`private/private_config.yaml` or `$PYSYS_PRIVATE_CONFIG_DIR`) overrides `defaults.yaml` in every sim backtest. DOCUMENTED (`backtesting.md:281,363`). The saved production config (`system.config.save`) records the merged result, which preserves the effective values but not their source. VERIFIED (code).
- **O-P13-3 (`None` cannot override a default).** Recorded above; not documented in the precedence section searched (`backtesting.md:1079-1124`, which describes filling *missing* keys only). VERIFIED (code).

### 14.3 Documentation / implementation items

- **DV14 (new):** the docs say "The function `from syscore.accounting import account_t_test` can be used for this purpose" (`docs/backtesting.md:3018`). There is no `syscore/accounting.py` (`ls` fails; `git grep "syscore.accounting"` finds only this doc line). The function is `systems/accounts/curves/account_curve_analysis.py:16` (`account_t_test`). VERIFIED (minor, import path).

### 14.4 Relevance to later phases (identified only)

- Phase 17 (degrees of freedom): every §14.1 "configurable component" is a degree of freedom; the only in-repo comparison statistic found is the t-test (no multiple-testing control found).
- Phase 18 (testing): the precedence code carries a doctest (`fill_config_dict_with_defaults.py:3-4`); not run in this phase.

### 14.5 Experiments

NOT TESTED — REASON: every Phase 13 item was answered from the configuration code and docs (spec §22). No run was needed.

### 14.6 Phase 13 change log (explicit)

| Item | Change | Basis |
|---|---|---|
| CSV `last_phase` | → 13 for C04 (config) and C05 (sim data: instrument representation) | §14.1 |
| CSV other fields | **unchanged**. C04 `impl_evidence` stays INFERRED and `divergence` stays UNKNOWN: this phase read the Config code directly, but U5 forbids an INFERRED → VERIFIED upgrade on reading, and DV14 concerns `account_t_test`'s documented path (an accounts/reporting item), not the Config component | U5; operator instructions |
| Divergence register | DV14 added | §14.3 |
| Earlier sections | not edited; no conflict found | — |

## 15. Static Causality / Look-Ahead Audit

**Phase 14 status: COMPLETE** (session 6). Spec §39. All citations are `@ 8958c49`. The evidence is static source reading, plus one synthetic scratch check (EXP-04, §15.6) run only because PF-14 depends on a library labelling convention that the repository source alone does not settle.

**Evidence discipline.**
- **Categories used** (spec §39): `NO ISSUE IDENTIFIED` / `POSSIBLE ISSUE` / `CONFIRMED ISSUE` / `UNVERIFIED`.
  - **CONFIRMED ISSUE** here means: the cited code makes a value that becomes known only *after* T an input to a quantity stamped T. It is a statement about the *mechanism* (from code, or TESTED for PF-14). It says nothing about the size of the effect, which is not measured anywhere in this audit (Phase 15).
  - **NO ISSUE IDENTIFIED** means that no post-T input was found in the code paths read. It is **not** "verified causal" (spec §14): no empirical causality test (Phase 15) has been run, and the reading is limited to the files cited.
  - **Scope** is stated for every item: *default* (the shipped `defaults.yaml` + the chapter-15 system) or *conditional* (only when a non-default switch, stage or system is used).
- **Timing convention** (SC11, §8): a value stamped *t* on the 1B index is known at the close of *t*. A position "established at T" is the position decided at the close of T; with `delayfill=True` it is filled at the T+1 price.
- **U5** applies. No INFERRED row is upgraded; R03–R07 stay INFERRED.

**Source read this phase** (on top of Phases 3–12 and §10): `sysquant/estimators/forecast_scalar.py` (whole); `syscore/pandas/strategy_functions.py:164-176`; `sysquant/fitting_dates.py:50-160` (grep + `_in_sample_dates`); `sysquant/estimators/stdev_estimator.py:30-70`; `systems/provided/dynamic_small_system_optimise/optimised_positions_stage.py:185-265`; `systems/portfolio.py:1119-1225`; `systems/accounts/account_forecast.py:125-148`; `systems/accounts/account_with_multiplier.py:136-159`; `syscore/capital.py` (whole); `systems/basesystem.py:150-275,285-390`; `sysdata/config/defaults.yaml:108-145,345-395`; `systems/accounts/pandl_calculators/pandl_SR_cost.py:108-135`; `systems/provided/rules/breakout.py:15-45`; `systems/provided/futures_chapter15/futuresconfig.yaml` (parameter lines); `docs/backtesting.md:215-235,3305-3360`.

**Look-ahead pattern search** (supports the absence statements below): `git grep` over `systems/ sysquant/ syscore/ sysdata/sim/` (tests excluded) for `shift(-`, `.bfill`, `backfill`, `center=True`, `fillna(method='bfill'|'backfill')`. Hits (all accounted for in §15.2–§15.3): `forecast_scalar.py:13,47-48` (PF-1); `stdev_estimator.py:63` (PF-7); `pandl_SR_cost.py:118` (§15.3 N8); `portfolio.py:1201` (PF-15); `account_forecast.py:144` (§15.3 N8); `vol.py:26,77-79,112-118,128,177-179` (vol `backfill` parameter, default False, not set in `defaults.yaml:111-120`); `account_curve.py:326` (`center=True` in the `rolling_ann_std` *report statistic* only); `full_merge_with_replacement.py:193` (row-wise `bfill(axis=1)` across columns, not across time). No `shift(-n)` was found. Whole-series aggregates in `systems/provided/rules/*.py` (grep for `.mean()`, `.std()`, `.max()`, `.min()`, `.median()`, `iloc[-1]`, `quantile(` outside `rolling`/`ewm`/`expanding`): only `breakout.py:25-30`, which are rolling (`price.rolling(lookback).max()/min()`). Absence beyond these patterns is UNVERIFIED.

### 15.1 Central question

> *If a position is established at time T, does any calculation determining it use information that becomes available only after T?*

| Configuration | Answer | Classification |
|---|---|---|
| **Default classic backtest** (chapter-15 system: fixed scalars, weights, FDM, IDM; `delayfill=True`; cash costs; `fixed_capital`; risk overlay off; daily data) | **For the position:** no post-T input was found. Rules see data ≤ T (SC11; pattern search above); vol at T uses returns ≤ T (Q1); scaling, caps, weights, FDM and IDM are fixed constants; sizing uses price, vol and FX ≤ T (reindex **ffill**, never bfill); the buffered path P06 depends only on rows ≤ T; the fill is at T+1. **For the reported P&L:** the cash cost of every historical fill is multiplied by `vol(t)/vol(last sample date)` (PF-2), so the *net* P&L at T uses the last sample date. The position is not affected in this configuration because costs never feed positions (§13.4) | Position: **NO ISSUE IDENTIFIED** (static; not verified causal). Net P&L / costs: **CONFIRMED ISSUE** (PF-2, default ON). Caveats: the provenance of the shipped fixed parameters is **UNVERIFIED** (§15.3 N9); roll / back-adjustment construction is **UNVERIFIED** (PF-8, D01, Phase 10 on hold) |
| **Estimated classic backtest** (any `use_*_estimates: True`; the "estimated system for chapter 15") | Yes, post-T inputs reach positions through: the forecast-scalar backfill (PF-1); end-of-sample SR cost per trade and full-sample turnover in the net returns used by the forecast-weight optimiser (PF-3/PF-4); the end-anchored cost deflator inside the subsystem P&L that feeds instrument weights and the IDM (PF-2 via F2/F3); a fit-period grid placed from the last sample date (PF-11); and the documented `in_sample` date method when chosen (§15.3 N7) | **CONFIRMED ISSUE** (PF-1, PF-3, PF-4, PF-2-via-estimates, N7); **POSSIBLE ISSUE** (PF-11) |
| **Other non-default paths** | Compounding (`full`/`half`) carries PF-2 into positions (PF-6); the risk overlay's shocked-vol backfill (PF-7); P09 end-of-sample cost inputs (PF-13); hourly configurations (PF-14, TESTED mechanism); speed limit on (PF-3/PF-4) | see §15.2 |
| **Production (live decision at T = today)** | The live run computes the whole history up to *now* and uses only the last row (PF-9). At that row every "end-of-sample" quantity is *today's* value (for example the deflator at the last row is `vol(T)/vol(T) = 1`; P09 "final price" = today's price), and no data after T exists. The end-anchored issues above are therefore **backtest-only**. They do shape the *historical* estimates (weights, IDM) that the live system inherits when estimation is on | Live decision: **NO ISSUE IDENTIFIED** (static) |

### 15.2 Pre-flag classification (PF-1…PF-12 from §8.4; PF-13 from §12.5; PF-14 from §10.5; PF-15 new)

| PF | Item | Mechanism (post-T input?) | Scope / default active? | Classification | Evidence |
|---|---|---|---|---|---|
| PF-1 | Forecast-scalar backfill | `scaling_factor.bfill()` gives rows before `min_periods` (500) the first estimate, which is built from rows up to 500. Rows after that use `rolling(250000).mean()` of rows ≤ *t* (same-row inclusion is data at *t*, not after *t*). Default `backfill: True` whenever the scalar is estimated | Conditional: `use_forecast_scale_estimates: True` (default False). DOCUMENTED as "strictly speaking this is cheating" (`backtesting.md:2451`); source comment "SLIGHTLY CHEATING" | **CONFIRMED ISSUE** (warm-up rows only) | `forecast_scalar.py:13,44-48`; `defaults.yaml:131-139` |
| PF-2 | Cash-cost vol deflator | `cost_scalar = vol_180(t) / vol_180.iloc[-1]`: every historical cost uses the last sample row | **Default ON** (`vol_normalise_currency_costs: True`). Affects net P&L (default); reaches positions only via estimated instrument weights / IDM (F2/F3), compounding (PF-6) or P09 (PF-13) | **CONFIRMED ISSUE** for backtest costs / net P&L; position impact conditional (see those rows) | `strategy_functions.py:164-172`; `pandl_cash_costs.py:191-225` |
| PF-3 | SR cost per trade | cost of one block at the **last-year** average price ÷ last-year average vol × point value | Conditional: SR-cost P&L (`use_SR_costs`, default False); **always** used in forecast-weight estimation and the speed limit when those are on (both default off) | **CONFIRMED ISSUE** (conditional) | `account_costs.py:295-345`; §8 Q13 |
| PF-4 | Full-sample turnover | turnover = `256 × mean|Δ(x)|` over the **whole** sample; × PF-3 → a constant cost subtracted from every fit period's returns and used for rule exclusion | Conditional: forecast-weight estimation (default off) or speed limit (999/9999, effectively off) | **CONFIRMED ISSUE** (conditional) | `strategy_functions.py:11-33`; `pre_processing.py:155-200`; `forecast_combine.py:735-864` |
| PF-5 | Inclusive `[fit_start:fit_end]` slices | includes at most the row stamped exactly `period_start`. That row is known at the close of `period_start`, which is when the new estimate first applies; nothing after `period_start` is included | Cleaning is on by default for the DM correlations (estimation itself off) | **NO ISSUE IDENTIFIED** (same-timestamp information, available at T under SC11) | §8 O3; `correlations.py:115-117`; `correlation_estimator.py:59` |
| PF-6 | Capital multiplier (unshifted for positions) | the multiplier at *t* includes the portfolio % P&L at *t*, which is known at the close of *t* (`delayfill` positions × Δprice ≤ *t*). Timing alone uses no post-T data. **However**, the multiplier is built from `accounts.portfolio().percent`, a *net* curve, so its costs carry PF-2 into positions | Conditional: `full_compounding` / `half_compounding` (default `fixed_capital`) | Timing: **NO ISSUE IDENTIFIED**. Via costs: **CONFIRMED ISSUE** (inherits PF-2, conditional) | `syscore/capital.py:19-46`; `account_with_multiplier.py:108-159`; `portfolio.py:93-97` |
| PF-7 | Shocked-vol backfill; pre-index lookups | `shocked.bfill()` fills rows before `min_periods = 3` from row 3; `get_stdev_on_date` uses the **first** row for any date before the index | Conditional: risk overlay configured (default off) | **CONFIRMED ISSUE** (limited to the first two rows and pre-index dates) | `stdev_estimator.py:42-66` |
| PF-8 | Carry / roll data | which contract is PRICE/CARRY historically and the back-adjustment are built outside the System (D01). Not read (Phase 10 on hold) | Default (carry rules; back-adjusted prices for all rules) | **UNVERIFIED** | D01; §8 Q15. Note (INFERRED): provided price rules use differences or rolling ranges (`ewmac`, `breakout.py:25-37`, `accel.py:8`), in which a constant additive back-adjustment offset cancels; this does not settle roll-date effects or contract selection |
| PF-9 | Production full recalculation | each run recomputes all history (and the O2 grid shifts); only the last row is used. No post-T data exists at the live decision | Production | **NO ISSUE IDENTIFIED** (look-ahead). The reproducibility property (restated history) is recorded, not a causality finding | `run_system_classic.py:52-200` |
| PF-10 | No age check on stored optimal positions | a stale position uses *older* information, not future information | Production | **NO ISSUE IDENTIFIED** (look-ahead). Whether a staleness check exists elsewhere, and the run scheduling (G8), stay **UNVERIFIED** | §8 Q20; G8 |
| PF-11 | Fit-period grid anchored to the sample end | `pd.date_range(end_date, start_date, freq="-365D")`: *which* dates are refit dates depends on the last sample date. The data used at each refit is still `< period_start`; no post-T price or return enters an estimate | Conditional: any estimation on | **POSSIBLE ISSUE** (post-T calendar information places the refits; no post-T market data found; effect not established) | `fitting_dates.py:157-175`; §8 O2 |
| PF-12 | Instrument universe | (a) `remove_short_history` uses the full-history length. No in-repo caller passes `remove_short_history=True` (grep of `*.py`: only defaults `False` at `basesystem.py:158,187,231,263`). (b) The universe, `bad_markets` and `trading_restrictions` come from config lists written with today's knowledge (the defaults comment says "Run interactive controls to get a list of suggested markets here") and apply to the whole history; pooled estimators and asset-class medians use that ex-post universe at same-date values | (a) not reachable from repo code with default arguments; (b) default (config-driven universe) | (a) **CONFIRMED ISSUE** if enabled by a caller (conditional; no in-repo caller found). (b) **POSSIBLE ISSUE** (ex-post selection; no post-T market data enters the code) | `basesystem.py:150-275,373-390`; `defaults.yaml:345-395` |
| PF-13 | P09 cost inputs | cost per contract = cost at the **final** raw price × **final** FX × current contract value × deflator(t) (PF-2 denominator); the deflator's warm-up NaN → 10000.0 | Conditional: dynamic-optimisation system (P09) | **CONFIRMED ISSUE** (conditional) | `optimised_positions_stage.py:188-262` |
| PF-14 (new, Phase 9) | Daily → hourly alignment | daily series are labelled 00:00 of day *t* but hold day *t*'s last (23:00) value; `reindex(..., method="ffill")` onto an hourly forecast index gives every hourly bar of day *t* (e.g. 10:00) that day's close-based value: the vol scalar (`positionsizing.py:126`), and likewise weights, FDM and IDM series | Conditional: hourly rules / hourly positions (e.g. `hourly_with_order_simulator.yaml`); daily-only systems are unaffected | **CONFIRMED ISSUE** (mechanism TESTED, EXP-04, synthetic data) | `sim_data.py:98-142`; `frequency.py:45-92,169-170`; `positionsizing.py:126`; EXP-04 |
| PF-15 (new) | Per-contract value backfill | `get_per_contract_value_as_proportion_of_capital_df` ffills then `bfill()`s (source comment "slight cheating"): before an instrument's first value, its first *later* value is used | Conditional: P09 (`optimised_positions_stage.py:44,327`) | **POSSIBLE ISSUE** (post-T values enter only for rows before an instrument's data starts; whether they change any P09 position was not established) | `portfolio.py:1180-1203` |

### 15.3 Spec §39 inspection list (items not already covered by a PF)

| # | Spec item | Finding | Classification | Evidence |
|---|---|---|---|---|
| N1 | Future prices | Rules receive system-method data ≤ *t* and are called once on the whole history; causality inside a rule is the rule's responsibility (SC11). Provided rules use `rolling`, `ewm` and positive `shift(n)` only (pattern search above). Cross-sectional medians use same-date values (`rawdata.py:351,664`); normalised returns use vol `shift(1)` (`rawdata.py:300`) | **NO ISSUE IDENTIFIED** (provided rules, searched patterns; not every rule line-read). A user rule is not checked by the framework | SC11; `rules/*.py`; `rawdata.py:300,351,664` |
| N2 | Same-day close leakage (daily path) | The forecast at close *t* fills at the *t+1* price with `delayfill=True` (all accounts callers default to it; the base-class default `False` at `pandl_calculation.py:17` is overridden by every caller found by `grep delayfill=False`). With `delayfill=False`, the fill would be at the same close that produced the signal: an execution-realism assumption, not post-T information | **NO ISSUE IDENTIFIED** (default) | `pandl_calculation.py:150-159,223-235`; §10.1 |
| N3 | Same-day close leakage (mixed frequency) | = PF-14 | CONFIRMED ISSUE (conditional) | §15.2 |
| N4 | Volatility leakage | vol at *t* uses returns ≤ *t*; `backfill` default False and not set in `defaults.yaml`; the slow component has no `min_periods` (a warm-up bias, not look-ahead) | **NO ISSUE IDENTIFIED** | `vol.py:121-181`; `defaults.yaml:111-120`; §8 Q1 |
| N5 | Correlation leakage | exponential estimates use rows strictly `< fit_end = period_start`; cleaning uses `[fit_start:fit_end]` for presence only (PF-5) | **NO ISSUE IDENTIFIED** at the date level (plus PF-11 POSSIBLE) | §8 O1/O3/O8 |
| N6 | Weight / FDM / IDM leakage | raw weights indexed at `period_start`, fitted on data before it; smoothed forward with EWM 125; FDM/IDM use weights ≤ `period_start`; 1/N before the first fit. Post-T information enters only through the *inputs* (PF-2/3/4, PF-11) | Date level: **NO ISSUE IDENTIFIED**; inputs: see PF rows | §8 Q6–Q11 |
| N7 | Full-sample estimation (`in_sample`) | `date_method: in_sample` produces one fit period with `fit_start = period_start = start`, `fit_end = end`: estimates from the whole sample apply from the first date. DOCUMENTED as an option and as a speed tip (`backtesting.md:3311,3359`) | Conditional (defaults use `expanding`, and `rolling` for risk correlations, `defaults.yaml:156,192,241,268,315`) | **CONFIRMED ISSUE** when chosen (by design) | `fitting_dates.py:50,110-112,153-154` |
| N8 | Warm-up / backfill elsewhere | (i) SR-cost P&L: the annualised SR cost is `bfill`ed during warm-up where a position exists (P&L only; `use_SR_costs` default False). (ii) Weighted per-rule P&L attribution (`_unnormalised_weight_for_forecast_and_instrument`) `bfill`s IDM/FDM/weights (reporting only, `account_trading_rules.py`). (iii) The forecast-scalar and shocked-vol backfills (PF-1, PF-7) | (i) **CONFIRMED ISSUE** (conditional; P&L only). (ii) **CONFIRMED ISSUE** (reporting only; no position effect). | `pandl_SR_cost.py:108-135`; `account_forecast.py:132-148` |
| N9 | OOS contamination of shipped fixed parameters | The default system's fixed forecast scalars, weights, FDM (1.31) and IDM are those "defined in chapter 15 of my book" (`backtesting.md:217`; `futuresconfig.yaml:18-90`). How and on what data period they were derived is not stated in the repository (an external book is not repository evidence, spec §6) | Default | **UNVERIFIED** | `futuresconfig.yaml`; `backtesting.md:215-235` |
| N10 | OOS contamination via protected / stale cache | Protected estimates survive `delete_all_items()` and config is not in the cache key (§3). Re-using a System after changing data or config can reuse estimates from another run. This is a research-hygiene property, not a post-T data path in a fresh System | **POSSIBLE ISSUE** (conditional on user workflow; DOCUMENTED warning `backtesting.md:1590-1609`) | §3 (i)–(iii) |
| N11 | Execution timing | = N2 (backtest). Live: order generation reads stored edges later (G8 UNVERIFIED); stale, not future | **NO ISSUE IDENTIFIED** | §9.5 |
| N12 | Cost timing | costs are booked at fill dates (*t+1*); roll pseudo-fills are priced with `get_row_of_series_before_date` and sized by the mean \|position\| over the *preceding* interval. The only post-T input is the deflator (PF-2) | Timing: **NO ISSUE IDENTIFIED**; deflator: PF-2 | `pandl_cash_costs.py:121-185` |
| N13 | Roll / back-adjustment effects | = PF-8 | **UNVERIFIED** | D01 |
| N14 | Order-simulator limit fills (§10.4) | the limit is set at the current price and filled only if the *next* price is strictly better; the decision uses data ≤ *t*, the fill is evaluated at *t+1* | **NO ISSUE IDENTIFIED** (look-ahead). The gross-P&L/fill-price observation O-P9-1 is an accounting matter, not look-ahead | `hourly_limit_orders.py:36-65`; `fills_and_orders.py:64-88` |

### 15.4 Summary of classifications

- **CONFIRMED ISSUE (default configuration):** PF-2 (cost deflator → backtest costs and net P&L; not positions).
- **CONFIRMED ISSUE (conditional, non-default):** PF-1, PF-3, PF-4, PF-6 (via PF-2), PF-7, PF-12(a), PF-13, PF-14 (TESTED mechanism), N7, N8(i), N8(ii) (reporting only).
- **POSSIBLE ISSUE:** PF-11, PF-12(b), PF-15, N10.
- **NO ISSUE IDENTIFIED:** PF-5, PF-6 (timing), PF-9, PF-10, N1, N2, N4, N5, N6 (date level), N11, N12 (timing), N14.
- **UNVERIFIED:** PF-8 / N13 (roll and back-adjustment, D01; Phase 10 on hold), N9 (provenance of shipped fixed parameters), G8 (live scheduling / staleness).
- **Not verified causal.** No item is labelled causal-verified. "NO ISSUE IDENTIFIED" rests on static reading of the cited paths and the pattern search; Phase 15 (optional, empirical) has not run.

### 15.5 Documentation / implementation items

No new DV or UD item. PF-1 and N7 are DOCUMENTED (`backtesting.md:2451,3311,3359`). The PF-2 end anchor is documented only as "normally standardised for historic volatility" (`backtesting.md:3038`, §13.2); the use of the *final* sample value is not stated there (undocumented detail, already visible in §13.2; not added to the register because §13.2 already records it with its evidence).

### 15.6 Experiments

**EXP-04 (PF-14).** Spec §22 items, stated before running:
1. *Question:* does the repository's daily resample label day *t*'s last (23:00) price at 00:00 of day *t*, so that the `reindex(..., method="ffill")` used at `positionsizing.py:126` hands it to hourly bars of day *t* before the close?
2. *Why static reading is not enough:* the label position is a pandas behaviour (`resample("1B").last()`), not repository code; the repository source alone does not settle it.
3. *Smallest experiment:* a synthetic 3-day, 9-row series (10:00, 15:00, 23:00 each day) passed through the repository's own `resample_prices_to_business_day_index` and `get_intraday_pdf_at_frequency`, then aligned with `reindex(method="ffill")`. No repository data, no network, scratch venv, `HOME` under `scaffolding/`.
4. *Expected evidence:* daily rows labelled `YYYY-MM-DD 00:00` holding the 23:00 value; hourly rows of the same day seeing that value.
5. *Stopping condition:* one run; the result is recorded whatever it shows.

*Result:* daily labels `2024-01-02/03/04` (00:00) hold 109/209/309 (the 23:00 values); the hourly bars at 10:00 and 15:00 of each day see 109/209/309 while the hourly prices are 101/102, 201/202, 301/302. **TESTED: the mechanism holds.** Script `scaffolding/experiments/exp04_daily_label_alignment.py`; output `scaffolding/experiments/exp04_output.txt`. `audit/repo` stayed clean.

NOT TESTED — REASON: every other classification was settled statically (spec §22). The *size* of any CONFIRMED ISSUE (e.g. how much PF-2 changes historical costs, or PF-1 changes early positions) is a Phase 15 question (optional; operator decision).

### 15.7 Phase 14 change log (explicit)

| Item | Change | Basis |
|---|---|---|
| CSV `last_phase` | → 14 for the 26 rows whose timing is classified here: A01, A03, A04, A06, A08, R01–R11, P01, P04, P07, P09, D01, E01, E02, E03, E04, C01 | §15.1–§15.3 |
| CSV other fields | **unchanged**. R03–R07 stay INFERRED (U5); D01 stays UNVERIFIED (PF-8 UNVERIFIED); E05 stays UNVERIFIED; E06 unchanged; transfer labels `NOT YET ASSESSED`. No evidence value is changed by a causality classification | U5; operator instructions |
| Pre-flags | PF-1…PF-14 classified; PF-15 added and classified | §15.2 |
| Experiments | EXP-04 added (TESTED) | §15.6 |
| Earlier sections | not edited; no conflict found (§3's INFERRED note on `remove_short_history` is consistent with PF-12(a); §8's Q-rows are consistent with the classifications) | — |

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
| PF-11 end-anchored fit grid | non-default (any estimation; tested for forecast weights) | POSSIBLE ISSUE | EXP-08 C + control B, EXP-08b | yes | yes | yes | yes | **POSSIBLE ISSUE** (unchanged from §15; interim relabel reverted, §16.12). Sample-end → refit-date dependency: TESTED, L1–L4, design property. Future market data entering estimates: NO ISSUE IDENTIFIED (control B) |
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
  - PF-11: §15.2 recorded **POSSIBLE ISSUE** ("post-T calendar information places the refits; no post-T market data found; effect not established"). Phase 15 evidence, reported as three separate lines:
    - **Sample-end → refit-date dependency:** TESTED, **L1–L4**. It is a **design property**: the refit calendar depends on the sample end date (`pd.date_range(end_date, start_date, freq="-365D")`). Removing post-C data moves the refit dates and so changes weights, forecasts, positions and P&L at dates ≤ C (arm C, EXP-08b).
    - **Future market data entering estimates:** **NO ISSUE IDENTIFIED**. With the refit dates held fixed (control B), removing post-C data leaves every value ≤ C unchanged (0 differing rows). Every estimate uses data before its own `period_start`.
    - **Causality label:** **POSSIBLE ISSUE**, unchanged from §15. The test separates a design property from future-information leakage (spec §40) and shows no leakage; it does not establish the sample-end calendar dependence as future-information leakage, so no upgrade is made. An interim relabel to CONFIRMED ISSUE ONLY WHEN NON-DEFAULT OPTION ENABLED (commit `a5dd7b9`) was reverted by operator-authorised correction; its text is kept verbatim in §16.12.
    - Scope: tested for forecast weights only. Instrument weights, FDM and IDM use the same grid code (§8 O2) but were not run (INFERRED to behave alike).

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
- **Classification:** look-ahead (N14): **NO ISSUE IDENTIFIED**, unchanged: the fill decision uses the price at the fill row, which is when the fill is evaluated. O-P9-1: the accounting effect is **TESTED** (L4, gross P&L; positions unaffected). The −161,390.62 USD gap is an accounting-valuation effect: marking fills at the simulator's fill-row price instead of the fill price. It is not evidence of future information. O-P9-2: **TESTED** (costs). Both are recorded without judgement on intent, for this example, instrument and period only. O-P9-3 is not tested (§16.9).

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
| PF-11 | POSSIBLE ISSUE | EXP-08 B/C, 08b. Sample-end → refit-date dependency: TESTED, L1–L4, design property (refit calendar depends on sample end date). Future market data entering estimates: NO ISSUE IDENTIFIED (fixed-refit-date control B: 0 differences) | **POSSIBLE ISSUE**, unchanged (the interim CONFIRMED relabel was reverted; §16.12) |
| PF-15 | POSSIBLE ISSUE | EXP-10: L1 only (values on 2,573–10,801 pre-start rows); 0 position / P&L differences | **changed → NO ISSUE IDENTIFIED** for positions and P&L (TESTED; L1 dependence remains) |
| O-P11-1 | effect INFERRED (§12.2) | EXP-09: L1–L4 | effect TESTED; causality NO ISSUE IDENTIFIED |
| O-P9-1 / O-P9-2 | effects INFERRED / recorded (§10.4) | EXP-11 | effects TESTED; N14 look-ahead NO ISSUE IDENTIFIED unchanged |

### 16.11 Phase 15 change log (explicit)

- Report: this section (§16) written; §15 not edited (supersessions in §16.10); Executive Summary bullets 11, 17 and 20 and the status line updated.
- CSV: `last_phase` → 15 on the six rows whose findings were tested: E02_COST_MODEL (PF-2), R01_FORECAST_SCALAR_EST (PF-1), R05_FORECAST_WEIGHT_OPT (PF-3/PF-4, PF-11, O-P11-1), R08_FITTING_DATES (PF-11), R09_TURNOVER_SR_COST (PF-3/PF-4), P09_DYNAMIC_OPTIMISATION (PF-15). No evidence value changed (U5: R03–R07 stay INFERRED; experiments test effects, not the components' implementation labels). No row added (the order simulator stays outside the inventory, DISC-3).
- Progress file: phase table, empirical tests (EXP-06…EXP-11), estimation flags per test, next task, session log, usage UNRECORDED.

### 16.12 Phase 15 correction (session 8, operator-authorised; no new experiments)

- **Scope.** The PF-11 causality label is reverted to POSSIBLE ISSUE, with its evidence reported as separate lines (§16.2, §16.5, §16.10, Executive Summary bullet 11, progress file). One clarifying sentence is added for O-P9-1 (§16.8). The cutoff-replacement limitation is recorded in the progress file. No other finding changed and no experiment was run.
- **Reason (PF-11).** Spec §40 requires Phase 15 to distinguish methodological design from future-information leakage. EXP-08 shows a design property: refit dates depend on the sample end date. Control B shows no future market data enters any estimate. The interim upgrade read the central question's "information after T" to include the calendar alone, which overstated what the test established.
- **Original §15 text (unchanged, in §15.2):** PF-11 — **POSSIBLE ISSUE** (post-T calendar information places the refits; no post-T market data found; effect not established).
- **Interim §16 text (commit `a5dd7b9`, superseded), kept verbatim:**
  - §16.2 row: `| PF-11 end-anchored fit grid | non-default (any estimation; tested for forecast weights) | POSSIBLE ISSUE | EXP-08 C + control B, EXP-08b | yes | yes | yes | yes | **CONFIRMED ISSUE ONLY WHEN NON-DEFAULT OPTION ENABLED** — TESTED; the post-T input is the sample end *date* only (no post-T price or return enters any estimate) |`
  - §16.5 bullet: `- PF-11: §15.2 recorded **POSSIBLE ISSUE** ("post-T calendar information places the refits; no post-T market data found; effect not established"). Empirically, removing post-C data changes weights, forecasts, positions and P&L at dates ≤ C (C), while holding the grid fixed removes every difference (B). The position at T therefore depends on the sample end date, which is information after T; B shows it is the only such input once costs are removed. Reclassified to **CONFIRMED ISSUE ONLY WHEN NON-DEFAULT OPTION ENABLED**, qualified: the post-T information is the refit *calendar* only; every estimate still uses data before its own `period_start`. Tested for forecast weights only; instrument weights, FDM and IDM use the same grid code (§8 O2) but were not run (INFERRED to behave alike).`
  - §16.10 row: `| PF-11 | POSSIBLE ISSUE | EXP-08 B/C, 08b: L1–L4 when the grid moves; zero when it does not | **changed → CONFIRMED ISSUE ONLY WHEN NON-DEFAULT OPTION ENABLED** (calendar-only post-T input) |`
  - Executive Summary bullet 11 sentence: `**PF-11 POSSIBLE → CONFIRMED ISSUE ONLY WHEN NON-DEFAULT OPTION ENABLED**; the post-T input is the sample end *date* only.`

## 17. Position / Lag / P&L Timing

Phase 16 status: COMPLETE (session 8; operator-authorised Phase 16 only; Phases 17–19 not started). One trace script (EXP-12) plus one single-date check of the roll-day price source (EXP-12b), both scratch-only. `audit/repo` stayed at `8958c49`, clean. Results apply to the traced sample only (spec §40: "Do not generalize beyond evidence").

### 17.1 Sample and method

- **System.** The shipped default: `futures_system()` + `futuresconfig.yaml`, all estimation OFF, `delayfill=True`, `roundpositions=True`, cash costs, fixed capital. Data: the shipped CSVs. Instrument: **US10** (value per point 1,000 USD, FX 1.0; quarterly roll).
- **Date-selection rules, stated before running** (script header; following limitation L-P15-1):
  - *Ordinary:* the first business day in 2023 on which the rounded buffered position changes and which is ≥ 5 business days from any PRICE_CONTRACT change → **2023-02-28**.
  - *Roll:* the first business day in 2023 on which the daily PRICE_CONTRACT changes → **2023-02-09** (20230300 → 20230600).
  - *Boundary:* the most recent available date → **2024-03-28**.
  - The fallback year (2022) was not needed.
- **Identity checked on every traced row.** `gross P&L(r) = pos_used(r−1) × (P(r) − P(r−1)) × value_per_point × fx(r)`, where `pos_used` is the position after the `delayfill` shift. This is the form of `calculate_pandl` (`pandl_calculation.py:223-235`). All 10 traced rows match to the cent.
- Scripts: `scaffolding/experiments/exp12_timing_trace.py` (output `exp12_output.txt`) and `exp12b_roll_day_source.py` (`exp12b_output.txt`).

### 17.2 Trace tables

**A. Ordinary date — decision at t = 2023-02-28**

| Step | Timestamp | Value / evidence |
|---|---|---|
| Market data | 9 raw rows on 2023-02-28, 14:30 → 23:00 | the 23:00 row (113.671875) is the day's last value |
| Daily price | label 2023-02-28 00:00 | 113.671875 = the 23:00 value (the label precedes the data time; consistent in a daily-only system, cf. EXP-04) |
| Signal / forecast | row t | combined forecast −11.0438 (t−1: −10.6155), from daily prices ≤ t |
| Position available | row t (after close t) | notional −1.6946; buffered, rounded −2 (t−1: −1): a trade is decided at t |
| Lag applied | one row (`delayfill` → `positions.shift(1)`) | `pos_used` = −2 first on row 2023-03-01 |
| Fill | row t+1 = 2023-03-01 | inferred fill −1 @ **113.140625** = the daily price of t+1 (close of t+1) |
| Return / P&L price | daily adjusted close | row 2023-03-01: +531.25 = −1 × (113.140625 − 113.671875) × 1000 (old position); row 2023-03-02: +906.25 = −2 × (112.6875 − 113.140625) × 1000 (first return on the new position) |
| Same-day exposure | — | **none**: the new position earns first from close t+1 to close t+2 |
| Next-bar convention | — | decision at close t → fill at close t+1 at price(t+1) → exposure from close t+1 |

**B. Roll-related date — t = 2023-02-09 (US10 20230300 → 20230600)**

| Step | Timestamp | Value / evidence |
|---|---|---|
| Market data | 10 raw adjusted rows 14:30 → 23:00. In the multiple prices, the old contract's last row is 21:00:00 and the new contract's first is **21:00:01** (an intraday roll) | multiple prices 23:00: 2023-02-08 PRICE 113.640625 (20230300); 2023-02-09 PRICE 113.734375 (20230600) |
| Daily price | label 2023-02-09 00:00 | 115.859375 (back-adjusted) |
| Signal / forecast | row t | −5.9176 (t−1: −5.6115) |
| Position available | row t | notional −0.7777; buffered, rounded −1 (unchanged): no trade decided |
| Lag applied | one row | `pos_used` −1 on 2023-02-08…02-13 |
| Fill | — | **none**: the backtest holds a contract count on a continuous adjusted series, so no roll trade is inferred |
| Return / P&L price | adjusted daily close | row 2023-02-09: +468.75 = −1 × (115.859375 − 116.328125) × 1000. The adjusted move −0.468750 = the old contract's move from the 02-08 close to the last pre-roll row (113.640625 → 113.171875) + the new contract's move from the roll row to the close (113.734375 → 113.734375 = 0) (EXP-12b). The shipped adjusted CSV equals the repo stitcher's output from the shipped multiple prices on both days. The raw cross-contract PRICE jump (+0.09375) does not enter P&L |
| Roll cost | pseudo-fill dates | 2023 pseudo-fill dates 02-15, 05-17, 08-16, 11-15 vs actual PRICE_CONTRACT changes 02-09, 05-23, 08-21, 11-20: the roll day is **not** a cost date (offset 4–6 days in 2023; mechanism in Card 12 / §13) |
| Same-day exposure | — | none (position unchanged across the roll) |
| Next-bar convention | — | as A; the roll itself creates no fill or lag event |

**C. Boundary — most recent date t = 2024-03-28**

| Step | Timestamp | Value / evidence |
|---|---|---|
| Market data | 9 raw rows 13:30 → 23:00 | 23:00 value 110.71875 |
| Daily price | label 2024-03-28 00:00 | 110.71875 |
| Signal / forecast | row t | −8.7169 (t−1: −8.7192) |
| Position available | row t | notional −1.6471; buffered, rounded −1 (inside the buffer, unchanged) |
| Lag applied | one row | there is **no row t+1**, so the position decided at t is never filled or held inside the sample |
| Fill | — | none |
| Return / P&L price | row t | +156.25 = −1 × (110.71875 − 110.875) × 1000, earned by the position decided at 2024-03-26 |
| Same-day exposure | — | none |
| Next-bar convention | — | the decision at the last row has no simulated fill. In production this last row is the one used as the live decision (§9.5, PF-9), filled outside the backtest |

### 17.3 Implemented convention (traced sample)

For the traced rows, a position computed from data up to and including the close of day t (daily label t) is shifted one row by `delayfill`. It is filled at the close price of the next row (t+1), and earns its first return over (t+1, t+2]. The second `shift(1)` inside `calculate_pandl` is the ordinary "previous position × this row's price change" form; it adds no further lag. There is no same-day exposure and no intra-bar fill price; one price per row is used for fills, P&L and costs (§10.6 item 2).

### 17.4 Documented vs implemented

| Item | Documented | Implemented (traced) | Status |
|---|---|---|---|
| Fill timing | "`delayfill`: Assume we trade at the next days closing price. Always defaults to True (more conservative)" (`docs/backtesting.md:2738`) | fill at the close of row t+1 at price(t+1) (trace A) | **consistent**. The base class `pandlCalculation` default is `delayfill=False` (`pandl_calculation.py:17`), but every accounts caller passes True (§15 N2); consistent for the accounts path traced |
| Lag parameter docstring | "Lag fills by one day" (`account_instruments.py` docstring) | one *row*; for daily data, one business day | consistent for the daily path traced |
| Roll handling | back-adjusted (Panama) prices (§11.4) | P&L on the roll day = the old contract's pre-roll move + the new contract's post-roll move (trace B) | consistent with §11.4 / EXP-05 |
| Roll costs | no description of the cash-method roll-cost placement found in `docs/*.md` (searched: "roll cost", "rolling cost", "cost of rolling", "holding cost", "multiply_roll_costs"; absence UNVERIFIED beyond these terms) | pseudo-fills at equally spaced dates, not on actual roll days (trace B) | implementation recorded (Card 12, §13); no documentation to compare against in the searched terms |

**No new documentation/implementation divergence** was found in the traced sample.

### 17.5 Observations (traced sample only)

- **O-P16-1:** the shipped US10 multiple prices roll intraday (21:00:00 → 21:00:01 on 2023-02-09). The adjusted daily move on the roll day therefore combines two contracts' moves, split at the roll time. A whole-day new-contract comparison (−0.453125) is not the stitched quantity; the stitched value (−0.468750) is reproduced exactly by the repo's own stitcher (EXP-12b).
- **O-P16-2:** in 2023, cash roll costs for US10 are booked 4–6 days away from the actual roll days, before or after. The backtest registers no roll trade on the roll day itself.
  - *Status (formalised in Phase 17 at operator request):* **report-only prose; not a CSV row.** Reason: the findings CSV is a component inventory (spec §32 schema: one row per framework component, no finding rows), held at 41 rows by operator decision. This behaviour belongs to the existing row **E02_COST_MODEL**, whose mechanism is already recorded in §6 Card 12 and §13. Evidence category: **VERIFIED** (code, `pandl_cash_costs.py:111-160`, `syscore/dateutils.py:674-690`; observed on the traced sample, EXP-12). Its effect on P&L was not measured and is not investigated further.
- **O-P16-3:** the position decided on the final row is never filled in the backtest. The last P&L row belongs to a position decided two rows earlier.

### 17.6 Limits

- Three dates on one instrument in the default daily configuration. Hourly systems (PF-14), the order simulator (§10.4, EXP-11), compounding (PF-6) and P09 were not traced.
- The warm-up boundary (first valid position) was not traced; the most recent date was chosen as the boundary.

### 17.7 Phase 16 change log (explicit)

- Report: this section (§17) written. Status line and Executive Summary bullet 12 updated (sentence added; bullet count unchanged).
- CSV: `last_phase` → 16 on the four rows traced: E01_BACKTEST_PANDL (fill/P&L identity), P06_BUFFERED_POSITION_SIM (position path), E02_COST_MODEL (roll pseudo-fill dates), D01_PRICE_ROLL_DATA (roll-day adjusted price). No evidence value changed; no row added.
- Progress file: phase table, next task, empirical tests (EXP-12, EXP-12b), session log, usage line.

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

## 19. Testing / Validation Infrastructure

Phase 18 status: COMPLETE (session 8; operator-authorised Phase 18 only; Phase 19 not started). Inventory of the repository's own tests, plus one run of the existing suites. No test was written and no audited file was modified. To avoid writing into the audited clone (for example, `test_cache` pickles to the tracked `systems/tests/tempcachefile.pck`), the suites ran in a disposable copy of `audit/repo` at the same commit (`scaffolding/home/p18repo`, git-ignored), placed first on `PYTHONPATH`; imports were verified to resolve to the copy. `audit/repo` stayed at `8958c49`, clean.

### 19.1 Test configuration and runs

- **Configuration:**
  - `pyproject.toml` `[tool.pytest.ini_options]`: `--doctest-modules`. `testpaths` = `syscore/pandas`, `syscore/tests`, `sysdata/config`, `sysdata/tests`, `sysinit/futures/tests`, `systems/tests`, `sysobjects/production`, `sysobjects/tests`, `sysquant/optimisation`, `sysquant/tests`, `sysbrokers/IB/tests`, `tests`.
  - Commented out, and therefore **not run**: `syscore`, `sysdata`, `sysdata/sim`, `sysquant/estimators`, `systems`, `systems/accounts`, `systems/provided`, `systems/provided/futures_chapter15`.
  - `tests/conftest.py` skips `@pytest.mark.slow` tests unless `--runslow` is given.
  - CI workflows (`.github/workflows/quick-test.yml`, `slow-test.yml`) run `pytest` and `pytest --runslow`. CI run history was not inspected.
- **Run 1 — quick suite** (`pytest`, repo config; `scaffolding/phase18/pytest_quick_outcomes.txt`): **101 passed, 40 skipped, 3 xfailed** in 46 s. Skipped: 29 Windows-only (`test_fileutils`) and 11 slow (`test_examples`). The 3 xfails are `test_fileutils` path-resolution cases marked "Cannot work with old or new implementation".
- **Run 2 — slow suite** (`pytest --runslow tests/test_examples.py`; `pytest_slow_outcomes.txt`): **17 passed** in 228 s.
- **Collection audit** (`--collect-only` per file; `test_file_collection.txt`): number of test functions defined vs collected.

| File | Defined | Collected | In `testpaths` | Why not collected |
|---|---|---|---|---|
| `systems/tests/test_cache.py` | 11 | 0 | Y | class decorated `@unittest.SkipTest` |
| `systems/tests/test_forecast_combine.py` | 11 | 0 | Y | class decorated `@unittest.SkipTest` |
| `systems/tests/test_portfolio.py` | 9 | 0 | Y | every test decorated `@unittest.SkipTest` |
| `systems/tests/test_position_sizing.py` | 10 | 1 | Y | 9 decorated `@unittest.SkipTest` |
| `systems/tests/test_rawdata.py` | 5 | 0 | Y | decorated `@unittest.SkipTest` |
| `systems/tests/test_forecasts.py` | 5 | 2 | Y | 3 decorated `@unittest.SkipTest` |
| `systems/tests/test_forecast_scale_cap.py` | 5 | 1 | Y | 4 decorated `@unittest.SkipTest` |
| `systems/tests/test_base_systems.py` | 1 | 0 | Y | decorated `@unittest.SkipTest` |
| `syscore/tests/test_correlation.py` | 8 | 0 | Y | decorated `@unittest.SkipTest` |
| `syscore/tests/test_algos.py` | 5 | 2 | Y | 3 decorated `@ut.SkipTest` |
| `syscore/tests/test_pdutils.py` | 1 | 0 | Y | decorated `@unittest.SkipTest` |
| `tests/test_static.py` (flake8) | 1 | 0 | Y | decorated `@unittest.SkipTest` |
| `systems/accounts/tests/test_accounts.py` | 5 | 0 | **N** | **collection error**: `AttributeError: module 'datetime' has no attribute 'strptime'` (cause in O-P18-3); the class is also `@pytest.mark.skip` |
| `sysquant/estimators/tests/test_mean_estimator.py` | 1 | 1 | N | not in `testpaths` (never run by the configured suite) |
| `sysexecution/tests/test_trade_qty.py`, `syslogging/tests/logging_tests.py`, `sysdata/mongodb/tests/test_mongodb.py`, `sysproduction/tests/test_controls.py` | — | 3 / 12 / 1 / 0 | N | not in `testpaths`; the mongodb test needs a database (not run: safety) |

- **O-P18-1 (silent non-collection):** `@unittest.SkipTest` is an exception class, not a skip decorator. Used as a decorator it replaces the test with an exception instance, which pytest does not collect. **66 defined tests** in `testpaths` files are therefore neither run nor reported as skipped (sum of the "decorated" rows above) (the skip count above covers only the Windows and slow tests). VERIFIED (collection output vs `def test` counts).
- **O-P18-3 (cause of the `test_accounts` collection error; confirmed at P1B close):** the error comes from the repository's own import chain, not from this environment. `sysdata/sim/csv_futures_sim_test_data.py` does `from datetime import datetime` (line 2) and then `from syslogging.logger import *` (line 16). The star import re-exports the *module* `datetime`: `syslogdiag/pst_logger.py:1` has `import datetime`, which reaches `syslogging/logger.py` through `syslogging/adapter.py:3 from syslogdiag.pst_logger import *` and `syslogging/logger.py:7 from syslogging.adapter import *`. None of these modules defines `__all__`. That rebinds `datetime` to the module, so line 30 `datetime.strptime(...)` fails. Evidence: **VERIFIED** on this environment (Python 3.11.15, pandas 2.1.3), by source reading of the chain and a runtime check that `syslogging.logger.datetime` is the `datetime` module. The mechanism (star-import re-export of module-level names without `__all__`; the `datetime` module has no `strptime`) is Python-language behaviour, so the failure is **INFERRED** to reproduce on other Python 3 versions (not run). It is a property of the repository's code at `8958c49`, not of this audit's environment.
- **O-P18-2 (assertion-free end-to-end tests):** `tests/test_examples.py` has **zero `assert` statements** (`grep -c assert` = 0). All 17 tests build systems (fixed and estimated forecast scalars, forecast weights/FDM, instrument weights/IDM, costs, risk overlay, config import, chapter-15 prebaked system) and print results. They pass if nothing raises. The two `sysinit` roll-calendar tests likewise contain no assertions (they pass if building or checking the calendar does not raise).

### 19.2 Coverage inventory by area

"Runs in suite" = executed by `pytest` with the repository's configuration (quick, or `--runslow` for slow).

| Area | Tests that run and assert | Tests that exist but do not run | What the running tests prove | What they do not prove |
|---|---|---|---|---|
| Forecasts | `test_forecasts` (2: rule-spec parsing, rule init); `test_forecast_scale_cap::test_get_forecast_cap`; doctest `replace_all_zeros_with_nan` | 3 in `test_forecasts`, 4 in `test_forecast_scale_cap` (incl. raw-forecast value), 11 in `test_forecast_combine` | rule specs parse; the cap value is read; zeros become NaN | forecast values, scaling, combination, the zero→NaN→ffill consequence (EXP-01), or timing |
| Volatility | `test_algos` (2: `robust_vol_calc` min_period, min_value) | 3 in `test_algos`; price-vol tests in `test_position_sizing` | `robust_vol_calc` honours min periods and floor | the **default** `mixed_vol_calc` (not tested), vol values, or look-back causality |
| Weights | `test_mp_optimise_over_time` (multiprocess weights == single-process; pickled attributes include `_pooled_length`); doctests `clean_list_of_weights`, `weights_sum_to_one`; slow smoke (estimated weights) | 9 in `test_portfolio` | parallel and serial optimisation agree; the cleaning arithmetic; weights sum to one | that weights are correct, fitted causally, or stable; the optimiser numerics (§12); the refit grid (PF-11); cost inputs (PF-3/PF-4) |
| Correlations | doctest `get_avg_corr` | 8 in `test_correlation` | average-correlation arithmetic | correlation estimates, windows, pooling or causality |
| FDM | none asserting; slow smoke estimates FDM | FDM tests inside `test_forecast_combine` | the estimated-FDM path runs without error | any FDM value or its causality |
| IDM | none asserting; slow smoke estimates IDM | IDM tests inside `test_portfolio` | the estimated-IDM path runs without error | any IDM value or its causality |
| Buffering | none (`buffering.py` has no doctests; no buffer test collected) | — | nothing | buffer edges, trade-to-edge, the path-dependent position (P06) |
| Costs | `sysquant/tests/test_returns` (4: SR-cost adjustment reduces returns by the analytic amount; zero cost leaves returns unchanged); slow smoke `test_simple_system_costs` | `systems/accounts/tests/test_accounts.py` (per-trade, percentage and rule SR-cost values) — outside `testpaths`, skip-marked, and fails at import; `account_costs.py` doctests (outside `testpaths`) | applying a given SR cost to returns is arithmetically right | the cost values, the cash-cost model, the vol deflator (PF-2), end-anchored SR cost (PF-3), turnover (PF-4), roll pseudo-fills |
| Data | doctests in `syscore/pandas` (merge, frequency, find_data, pdutils); data loading is exercised only inside the smoke tests | 5 in `test_rawdata`; `sysdata/sim` doctests (outside `testpaths`) | pandas utility behaviour, including `get_intraday_pdf_at_frequency` and `closing_date_rows_in_pd_object` | shipped CSV content, provenance (§11.7), adjusted/multiple consistency |
| Rolls | `sysinit` `test_build_roll_calendar`, `test_check_saved_roll_calendar` (no asserts; sample AUD data) | — | building and checking a roll calendar from sample prices does not raise | roll-date correctness, Panama stitching (EXP-05 is the audit's own check), the live roll process |
| Simulation | slow and quick `test_examples` smoke (17), no asserts | `test_base_systems` (1), `test_cache` (11) | the example and chapter-15 systems build and run to a Sharpe ratio without exceptions under pandas 2.1.3 | any numerical result; P&L correctness; cache semantics (EXP-02 is the audit's own check) |
| Configuration | `sysdata/tests/test_config` (12: dict/str/list init, defaults, private/control/trading-hours dirs and bad dirs); doctests in `configdata.py`, `fill_config_dict_with_defaults.py`, `defaults.py` | — | config loading and precedence mechanics, including custom and bad private directories | that config values are sensible; the `None`-cannot-override rule (O-P13-3) is not asserted |
| Live behaviour | `sysbrokers/IB/tests` (3: combo-contract lookup); doctest `apply_position_limit_to_single_leg_trade` | `sysexecution/tests/test_trade_qty` (3), `syslogging` (12), `sysproduction/tests` (0), `sysdata/mongodb` (needs a DB) — all outside `testpaths` | IB combo lookup picks the right leg; position-limit arithmetic for one leg | order generation, stack handling, reconciliation, the production run cycle |
| Reproducibility | `test_mp_optimise_over_time` (identical weights across process modes) | `test_cache` pickling tests | determinism of the weight optimiser across execution modes | run-to-run determinism of a full system, or config/code versioning (none exists, §14) |
| Timing | frequency and `find_data` doctests (e.g. `get_row_of_series_before_date`) | `pandl_calculation.py` has no doctests; `test_accounts` broken | the helper functions' index arithmetic | `delayfill`, the fill price, the P&L lag, or next-bar semantics (Phase 16's EXP-12 trace is the only check) |

### 19.3 Coverage of the Phase 14/15 causality findings

"Would the repository's own suite catch it?" means: would any test that runs under the repository's configuration fail if the behaviour changed (either removed or made worse)?

| Finding | Relevant existing tests | Would the suite catch a regression? | Why |
|---|---|---|---|
| **PF-1** forecast-scalar backfill | `test_examples::test_simple_system_trading_rules_estimated` runs an estimated scalar (unpooled) and prints its tail; `forecast_scalar.py` has no doctest | **No: invisible to existing tests** | nothing asserts the scalar's values, the warm-up rows or the `backfill` behaviour; the smoke test fails only on an exception |
| **PF-2** end-anchored cost deflator | none on `calculate_cost_deflator` (`strategy_functions.py:164-172`, no doctest); `test_simple_system_costs` is a smoke test | **No: invisible** | no test asserts costs, their scaling or their anchor |
| **PF-3/PF-4** SR cost per trade × full-sample turnover | `test_accounts` asserts SR cost per trade and rule SR cost values, but it is skip-marked, outside `testpaths` and fails at import; `test_returns` checks only the arithmetic of subtracting a given SR cost | **No: invisible** | the only value-level cost assertions never run, and even if repaired they are value snapshots on full data, not a truncation/causality check |
| **PF-11** end-anchored refit grid | `test_mp_optimise_over_time` compares two runs on the same data; `fitting_dates.py` has no tests | **No: invisible** | both compared runs share the same end date; no test varies the sample end or checks refit dates |
| **PF-15** per-contract value bfill (P09) | none (`portfolio.py` doctests are outside `testpaths`; no P09 test found: `git grep dynamic_small_system_optimise` in test files returns nothing) | **No: invisible** | no test runs P09 at all |

All five are detectable only by ad hoc experiments of the Phase 15 kind (EXP-06…EXP-10). None of the existing tests is a truncation or future-data test.

### 19.4 What important tests prove vs. do not prove

- **`tests/test_examples.py` (17 smoke tests):** prove that the provided example and chapter-15 systems, with estimation on and off, build and run end to end without exceptions on the shipped data under this environment. They do not prove any number is correct, and they do not detect look-ahead, cost or timing regressions. A passing run is not evidence of methodological validity.
- **`sysdata/tests/test_config.py` (12):** prove config loading and directory precedence behave as asserted. They do not prove that any parameter value is appropriate.
- **`sysquant/tests/test_returns.py` (4):** prove that SR-cost adjustment of a returns frame matches the analytic expectation. They do not prove the SR cost itself is computed correctly or causally.
- **`systems/tests/test_mp_optimise_over_time.py` (2):** prove parallel and serial weight optimisation give identical weights, and that pooled-length metadata survives pickling. They do not prove the weights are right or fitted without future information.
- **`syscore/tests/test_algos.py` (2 running):** prove `robust_vol_calc` minimum-period and floor behaviour. They do not cover the default vol function (`mixed_vol_calc`).
- **`syscore/pandas` doctests (frequency, merge, find_data):** prove the documented examples of index and merge helpers. They do not prove the system-level timing convention (§17) or the mixed-frequency alignment consequence (PF-14).
- **Collection itself:** a green suite here does not mean the defined tests pass. 66 are silently never run (O-P18-1), and the only cost-value test cannot be imported.

### 19.5 Phase 18 change log (explicit)

- Report: this section (§19). Status line and Executive Summary bullet 17 updated (bullet count unchanged).
- Evidence files (committed): `scaffolding/phase18/pytest_quick_outcomes.txt`, `pytest_slow_outcomes.txt`, `test_file_collection.txt`. The test-run copy lives in git-ignored scratch.
- CSV: `last_phase` → 18 on the rows whose test coverage is assessed as a component here: C03_CACHE (cache tests dropped), R01_FORECAST_SCALAR_EST (PF-1), R08_FITTING_DATES (PF-11), R09_TURNOVER_SR_COST (PF-3/PF-4), E02_COST_MODEL (PF-2; `test_accounts`), P09_DYNAMIC_OPTIMISATION (PF-15). No evidence value changed; no row added.
- Progress file: phase table, next task, empirical tests (TEST-RUN-1/2), session log, usage UNRECORDED.
- P1B close addendum: O-P18-3 added (cause of the `test_accounts` collection error) and the §19.1 table row annotated. No other §19 content changed.

## 20. Live / Production Architecture

**Phase 19 — SKIPPED — RESOURCE PRIORITY. Static review of the research-to-live connection, broker integration, order generation, position reconciliation, account state, persistence, restart behavior, monitoring, logging, overrides, limits, and error handling was not performed. This is a known gap, not a finding of NO ISSUE IDENTIFIED.**

Operator decision (session 8, P1B close) under spec §40's resource-priority allowance: Phase 19 is optional and first to cut. No Phase 19 inspection was done. Earlier phases' entry-level live facts remain as recorded (§2; §9.5; §13.5 research/live table; Executive Summary items 14–15; PF-9/PF-10; G8; E05 UNVERIFIED) and are not extended here.

## 21. Swing Transfer Analysis (Phase 20)

**Definitions in force (spec §5).** Swing = multi-day holding periods, decisions made no more frequently than once per trading day, using daily-or-slower decision data; execution may use finer data.

### 21.1 General finding

The audited default configuration already operates at exactly this cadence: forecasts are generated once per day from daily bars (SC4, SC12 — VERIFIED), positions are decided at most once per day, and execution fills at the next daily close (SC11, Phase 16 trace — VERIFIED). Swing trading, as defined for this audit, is not a different frequency from what pysystemtrade already does by default — it is what pysystemtrade already does by default. Consequently, for the great majority of components, the swing-transfer question reduces to "does anything about this component depend on a frequency *faster* than daily?" — and the answer is almost uniformly no. This is reflected in the table below: most rows carry **CONCEPTUALLY PORTABLE — UNTESTED** rather than a stronger label, because "untested" is doing real work here — no swing-specific empirical run was performed in this audit (P0/P1 tested causality and timing, not swing performance), so the correct claim is "the mechanism does not appear frequency-blocked for swing," not "swing use is validated."

Three categories of exception exist and are treated separately below the table: (a) components whose *own* audit depth was insufficient to respond responsibly (P09, E05); (b) the alpha-specific components themselves (A03, A07), which sit outside the "framework minus alpha" question this phase asks; (c) none of the remaining components showed a swing-blocking assumption in the evidence gathered.

### 21.2 Component-by-component table

Columns: Principle (what the component is *for*, independent of implementation) · Implementation (brief) · Assumption tested against swing cadence · Evidence · Transfer status. "Assumption survives" is stated inline in the Assumption column rather than as a separate column, per spec §44.

| Component | Principle | Implementation (brief) | Assumption vs. swing cadence | Evidence | Transfer status |
| --- | --- | --- | --- | --- | --- |
| SC — Signal Contract | A forecast is a signed, continuous, daily-or-slower series | SC1–SC16 (§5) | A daily-or-slower signal is exactly what the contract already specifies (SC12) | VERIFIED (§5) | CONCEPTUALLY PORTABLE — UNTESTED |
| C01 System / C02 Stage | Compose a pipeline of named, cacheable calculation stages | `System`/`SystemStage` (`systems/basesystem.py`, `systems/stage.py`) | No reference to bar frequency anywhere in the container pattern | VERIFIED | CONCEPTUALLY PORTABLE — UNTESTED |
| C03 Cache | Memoise whole-history pure-function results | `systemCache` decorators (`systems/system_cache.py`) | Whole-history recompute per call is cheap at daily-bar row counts (thousands of rows) | VERIFIED (row-count reasoning) | CONCEPTUALLY PORTABLE — UNTESTED |
| C04 Config | Parameter store, independent of frequency | `Config`/`defaults.yaml` | Genuinely frequency-agnostic; only the *values* would differ | VERIFIED | CONCEPTUALLY PORTABLE — UNTESTED |
| C05 SimData | Supply price/vol/carry data to stages | `simData`/`futures_sim_data.py` | Default path already resamples to daily (`1B`); swing needs nothing finer | INFERRED | CONCEPTUALLY PORTABLE — UNTESTED |
| D01 Price/roll data | Continuous, back-adjusted futures series | adjusted/multiple prices, roll calendars | Built and validated at daily granularity, which is swing's native granularity | VERIFIED | CONCEPTUALLY PORTABLE — UNTESTED |
| A01/A02 TradingRule / Rules stage | Generic call shape for any signal | `f(*data, **kwargs) -> pd.Series` (SC1–SC5) | Vectorised whole-history evaluation is what a daily swing rule already looks like | VERIFIED | CONCEPTUALLY PORTABLE — UNTESTED |
| A03 Provided rules | Trend/carry/breakout signal generation | EWMAC/carry/breakout in `systems/provided/rules/*.py` | **Out of scope as "framework machinery"** — this is the alpha being replaced under the audit's central question. As shipped, parameters are explicitly day-denominated (`ewmac.py`: *"Assumes that 'price' is daily data"*, *"Lookback for fast in days"* — VERIFIED by direct reading). At swing cadence this is already the native unit, so no redesign is implied | VERIFIED (docstring, confirmed this session) | CONCEPTUALLY PORTABLE — UNTESTED *(caveat: alpha-specific, see §21.3)* |
| A04 Forecast scaling | Normalise forecast magnitude to a fixed average | `get_scaled_forecast`; expanding-mean scalar or fixed | Mean-abs scaling is meaningful for a continuous daily signal (SC7) | VERIFIED | CONCEPTUALLY PORTABLE — UNTESTED |
| A05 Forecast cap | Bound extreme conviction | `clip(±20)` | A daily signal's tails are what the cap was calibrated against | VERIFIED | CONCEPTUALLY PORTABLE — UNTESTED |
| A06 Forecast combination | Blend multiple signals into one | weighted sum after ffill, resampled to `1B` (`forecast_combine.py:258-260`, comment: *"Remap to business day frequency so the smoothing makes sense"* — VERIFIED, confirmed this session) | The `1B` resample is a no-op at daily cadence — swing decisions already land on business days | VERIFIED | CONCEPTUALLY PORTABLE — UNTESTED |
| A07 Forecast mapping | Non-linear response curve on the forecast | `map_forecast_value` | Assumes a roughly Gaussian daily forecast distribution (documented, not verified statistically here) | HYPOTHESIS (unchanged from §5 SC8) | CONCEPTUALLY PORTABLE — UNTESTED |
| A08 FDM application | Scale up combined forecast for imperfect correlation | scalar multiply, capped 2.5 | Correlation-based risk-shrinkage logic has no frequency term itself | VERIFIED | CONCEPTUALLY PORTABLE — UNTESTED |
| R01 Forecast-scalar estimation | Estimate the scaling constant from history | expanding mean of cross-sectional median \|forecast\| | Expanding-window statistics are frequency-general; PF-1's backfill effect is confined to pooled warm-up, not a frequency effect | TESTED (PF-1, Phase 15) | CONCEPTUALLY PORTABLE — UNTESTED |
| R02 Vol estimation | Estimate risk per unit position | 35-day EWM blended 30% with a 10-year slow vol | Both windows are denominated in calendar days; at swing (daily decisions) they apply exactly as designed | VERIFIED | CONCEPTUALLY PORTABLE — UNTESTED |
| R03 Forecast-correlation estimation | Estimate how forecasts co-move | weekly-resampled, pooled/stacked correlation | Weekly resampling of a daily signal is a design choice already compatible with swing | INFERRED | CONCEPTUALLY PORTABLE — UNTESTED |
| R04 FDM estimation | Calibrate the diversification multiplier | `1/√(wᵀCw)`, capped 2.5, EWM125 | Depends on R03; no additional frequency assumption | INFERRED | CONCEPTUALLY PORTABLE — UNTESTED |
| R05/R06 Weight optimisation | Fit forecast/instrument weights | Markowitz variants + handcraft, refit periodically (R08) | 365-day refit periods match a swing system's natural recalibration cadence | INFERRED | CONCEPTUALLY PORTABLE — UNTESTED |
| R07 Instrument-corr/IDM estimation | Estimate diversification across instruments | weekly correlation of subsystem returns | Same reasoning as R03 | INFERRED | CONCEPTUALLY PORTABLE — UNTESTED |
| R08 Fitting dates | Generate refit period boundaries | expanding/rolling/in-sample date windows | Pure calendar arithmetic; no bar-frequency reference at all | VERIFIED | CONCEPTUALLY PORTABLE — UNTESTED |
| R09 Turnover/SR cost | Estimate trading activity and its cost | `\|Δ(forecast/10)\|` on a `.resample("1B")`, ×`BUSINESS_DAYS_IN_YEAR` (=256, `syscore/dateutils.py:26` — VERIFIED, confirmed this session) | `1B` resample of a daily decision series changes nothing | VERIFIED | CONCEPTUALLY PORTABLE — UNTESTED |
| R10 Forecast P&L proxy | Approximate the P&L a forecast alone would earn | forecast/10 × average position, delayed fill | Same daily assumptions as E01, already swing-native | VERIFIED | CONCEPTUALLY PORTABLE — UNTESTED |
| R11 Cost-ceiling speed limit | Drop rules whose estimated cost is too high | SR-cost threshold (defaults off: 999/9999) | Depends on R09; inherits its swing-compatibility | VERIFIED | CONCEPTUALLY PORTABLE — UNTESTED |
| P01 Position sizing | Size positions to a risk target | `capital × %target/√256 / (point value × vol × fx) × f/10` | √256 annualisation is a daily-vol convention already appropriate at swing cadence | VERIFIED | CONCEPTUALLY PORTABLE — UNTESTED |
| P02 Instrument-weight application | Allocate risk across instruments | scalar multiply, EWM125 smoothing | Smoothing window denominated in daily periods, swing-native | VERIFIED | CONCEPTUALLY PORTABLE — UNTESTED |
| P03 IDM application | Scale up for cross-instrument diversification | scalar multiply | Depends on R07; no independent frequency assumption | VERIFIED | CONCEPTUALLY PORTABLE — UNTESTED |
| P04 Risk overlay | Portfolio-level leverage/risk scalar | scalar in \[0,1\] on positions, off by default | Generic risk-scalar concept; **evidence is thinner here** — undocumented (`doc_status = NOT_DOCUMENTED`) and not deeply exercised beyond existence | VERIFIED (existence/mechanism only) | CONCEPTUALLY PORTABLE — UNTESTED |
| P05/P06 Buffering | Avoid over-trading around a noisy target | width = 0.1 × \|avg position at forecast 10\|; path-dependent apply loop | A daily-vol-scaled buffer width is exactly what a swing system's own target already is | VERIFIED | CONCEPTUALLY PORTABLE — UNTESTED |
| P07 Capital multiplier | Scale positions to available capital | fixed or compounding | Frequency-agnostic arithmetic | VERIFIED | CONCEPTUALLY PORTABLE — UNTESTED |
| P08 Long-only constraint | Zero out negative positions where required | per-instrument floor at 0 | Frequency-agnostic constraint | VERIFIED | CONCEPTUALLY PORTABLE — UNTESTED |
| P09 Dynamic optimisation | Alternative integer-position construction | greedy per-date search vs. classic notional | **Own internals were only partially read (§12.4); deep review was explicitly deferred as PARTIALLY AUDITED — RESOURCE PRIORITY** | UNVERIFIED (depth) | TRANSFER NOT JUSTIFIED — insufficient audit depth |
| E01 Backtest P&L | Simulate fills and returns | next-close fill, `delayfill` shift(1) | This *is* the swing execution model as defined (decide at close t, fill close t+1, hold days) | VERIFIED (Phase 16 trace) | CONCEPTUALLY PORTABLE — UNTESTED |
| E02 Cost model | Charge trading costs | linear per-fill cost + roll pseudo-fills + end-of-sample deflator | A swing system trades occasionally; a per-fill linear cost model is the right granularity | VERIFIED | CONCEPTUALLY PORTABLE — UNTESTED |
| E03 Production runner | Re-run the system daily, act on the last row | re-run full `System`, read `buffers.iloc[-1]` | Exactly a swing production loop by construction | VERIFIED | CONCEPTUALLY PORTABLE — UNTESTED |
| E04 Order generation | Trade toward the target when outside the buffer | round to buffer edge | Daily decision → daily order generation, swing-native | VERIFIED | CONCEPTUALLY PORTABLE — UNTESTED |
| E05 Order stacks / broker | Route and manage live orders | `sysexecution`/`sysbrokers` | **Not deeply audited — Phase 19 (the phase that would cover this) was explicitly SKIPPED — RESOURCE PRIORITY** | UNVERIFIED | TRANSFER NOT JUSTIFIED — insufficient evidence |
| E06 Overrides/limits | Apply position/trade caps after generation | `override`/`position_limits`/`trade_limits` | Frequency-agnostic control layer | VERIFIED | CONCEPTUALLY PORTABLE — UNTESTED |

### 21.3 Exceptions requiring their own reasoning

- **A03 (provided rules) and A07 (forecast mapping)** are alpha-specific or thin-evidence items sitting outside the main "framework minus alpha" question. A03's day-denominated parameters need no change at swing cadence (evidence: VERIFIED docstring, confirmed this session), but note this is a statement about *parameter units matching*, not an endorsement of the rules themselves — the master spec's Central Research Question treats A03 as the thing being replaced, not the thing being transferred. A07 remains HYPOTHESIS-level (§5 SC8) because the Gaussian-forecast assumption behind the mapping was never statistically tested against real forecast distributions in this audit.
- **P09 and E05** are labelled TRANSFER NOT JUSTIFIED for a reason distinct from every other row: it is not that evidence points against transfer, but that the audit itself did not go deep enough to respond responsibly. This is the correct application of the label's definition (spec §43: "available evidence is insufficient to justify transfer") and should not be read as "swing transfer of these components fails" — it should be read as "this audit cannot tell you."

---

## 22. Intraday Transfer Analysis (Phase 21)

**Definitions in force (spec §5).** Intraday = positions normally opened and closed within a trading session, decisions made on sub-daily data (1–5 minute bars or ticks for liquid futures such as ES/NQ/YM).

Unlike swing, intraday is a genuine frequency change from everything the audited default configuration does. Every daily-denominated constant, resample, or window identified across P0/P1 becomes a live question here. Per spec §45, findings are separated into four buckets (A–D) and the specific mechanisms it names are inspected explicitly within them, rather than repeating the swing table's per-row format.

### 22.A Timeframe-independent principles

These components carry no daily-specific assumption in their own logic — the assumption, if any, lives entirely in what feeds them.

| Component | Principle | Why it is frequency-independent | Evidence |
| --- | --- | --- | --- |
| C01/C02 (System/Stage) | Pipeline-of-stages container | No reference to bar size anywhere in the pattern | VERIFIED |
| C04 (Config) | Parameter store | Values change; the mechanism does not | VERIFIED |
| R08 (Fitting dates) | Generate refit-period boundaries | Pure calendar-window arithmetic — the one estimation mechanism with no embedded frequency constant found anywhere in the audit | VERIFIED |
| P04 (Risk overlay) | Portfolio leverage/risk scalar in \[0,1\] | Operates on already-computed positions; no window or annualisation constant in the mechanism itself | VERIFIED (existence); undocumented beyond that |
| P07 (Capital multiplier) | Scale by available capital | Arithmetic scaling, no time constant | VERIFIED |
| P08 (Long-only) | Floor negative positions at 0 | A constraint, not a calculation | VERIFIED |
| E06 (Overrides/limits) | Post-hoc position/trade caps | Applied after position generation regardless of how positions were generated | VERIFIED |

**Transfer status for this group: CONCEPTUALLY PORTABLE — UNTESTED.** "Untested" still applies — no intraday run was performed — but no redesign is implied by anything found in the audit.

### 22.B Daily-frequency assumptions (structural, not incremental)

These are cases where the label DAILY-DEPENDENT applies because the assumption is load-bearing throughout the component, not confined to a constant that could be swapped out.

| Item | Principle at stake | What is daily-dependent | Evidence |
| --- | --- | --- | --- |
| A03 (provided rules, as shipped) | Trend/carry signal generation | EWMAC's own docstring: *"Assumes that 'price' is daily data,"* lookbacks specified *"in days"* (`systems/provided/rules/ewmac.py`) | VERIFIED, confirmed this session |
| E01 (backtest P&L) | Simulate fills and P&L | Single fill at the *next daily close*; §13.6 item 4 already records "no partial fills, queue position, intrabar sequencing or latency in the backtest" (VERIFIED). This is not a parameter to retune — it is a different kind of P&L engine (see §22.C for the repository's own partial alternative) | VERIFIED (`pandl_calculation.py:223-235`; Phase 16 trace) |
| E03 (production runner) | Generate today's decision from the whole system | Re-runs an entire whole-history `System` once per day and reads the last row (SC4). A 1–5 minute production cadence is a different computational pattern, not a faster version of this one | VERIFIED |
| **Market impact / cost curve (gap, not a component)** | Cost should scale with trade size and liquidity | §13.6 item 2: *"no market impact and no cost curve... cost per contract is independent of trade size, time of day and liquidity"* (VERIFIED formula). At the trade sizes and frequencies swing/position trading implies, ignoring impact is a safe simplification; at intraday frequency and size it stops being safe. There is no partial mechanism to redesign — this would need to be built from nothing | VERIFIED (absence within search scope; UNVERIFIED beyond it) |
| **Stops / targets / intrabar exits (gap, not a component)** | Risk-manage a position within its holding period | SC14 (VERIFIED): *"no channel for entry/exit events, stops, targets, holding-period logic or order types"* anywhere in the audited framework. This is the single most consequential gap for intraday use, because stop/target logic is close to a baseline requirement for intraday risk management | VERIFIED |

### 22.C Potentially portable, requires redesign

The largest bucket. Each row names the specific redesign the evidence points to — not a vague "needs work."

| Component / mechanism | Principle (portable) | Concrete redesign implied | Evidence |
| --- | --- | --- | --- |
| C03 (Cache) | Memoise pure-function history | Whole-history recompute-per-call is a fundamentally different cost at 1–5 min bars over years of data than at daily bars; per-argument cache keying was already found broken at the base-system level (UD2, TESTED) | INFERRED (scale reasoning) + VERIFIED (UD2) |
| C05 (SimData) / D01 (price/roll data) | Supply price data to stages | Default path resamples to daily; a documented, partially-built sub-daily path already exists (see below) but is not the default | INFERRED |
| A01/A02 (TradingRule / Rules stage) | Generic per-instrument signal call | SC4 (vectorised whole-history) and SC9 (zero-as-missing, TESTED in EXP-01 to silently corrupt intended-flat periods) both need redesign for an event-driven, stateful intraday rule | VERIFIED / TESTED |
| A04–A06, A08 (scaling, cap, combination, FDM application) | Normalise and blend forecasts | A06 in particular: ffill-holds the last non-zero forecast through what should be a flat period — EXP-01 measured this holding a constant +10 forecast across 3,505 intended-flat bars; the `1B` resample in combination is an explicit daily-frequency step (`forecast_combine.py:258-260`, comment confirmed this session) | TESTED (EXP-01) / VERIFIED |
| R01–R07, R09–R11 (estimation and cost-ceiling machinery) | Estimate scaling, correlation, weights, turnover from history | The repository's **own source code warns against this at high frequency**: the stacking function used for pooled correlation estimation carries the comment *"WON'T WORK WITH HIGH FREQUENCY DATA"* (`syscore/pandas/list_of_df.py`, confirmed this session — DOCUMENTED, in-source). R09's turnover measure additionally resamples to `1B` before differencing, which would discard almost all intraday trading activity if applied unmodified | DOCUMENTED (in-source) + VERIFIED |
| P01–P03, P05–P06 (position sizing, weight/IDM application, buffering) | Size and smooth positions to a risk target | √256 annualisation (`syscore/dateutils.py:26`, confirmed this session) and the buffer-width formula (0.1 × avg daily position) are both daily-vol conventions; the *principle* — size inversely to volatility, trade only when the deviation exceeds a threshold — is genuinely frequency-general and is arguably the most portable idea in the whole framework once re-derived for the native bar frequency | VERIFIED |
| E02 (cost model) | Charge configured trading costs | §13.6 items 2–3 (VERIFIED): linear, size-independent, time-of-day-independent, constant-spread-per-instrument. The *charge a cost per fill* principle is portable; the specific linear/constant model is not | VERIFIED |
| E04 (order generation) | Trade toward target when outside a buffer | The CSV's own Case-B note already flags "no event/exit channel" (VERIFIED); a stop/target/event channel would need to be added, not tuned | VERIFIED |
| **Fill uncertainty / partial fills / intrabar sequencing (gap, with a partial answer in-repo)** | Model realistic execution | The default vectorised path has none of this (§13.6 item 4). However, the repository already contains a non-default `AccountWithOrderSimulator` with hourly market/limit variants (UD5, VERIFIED) that replaces the vectorised fill inference with a per-row order/fill loop. Phase 15's O-P9-1 test already used this path and found a large, systematic accounting gap (+31,516 USD framework-reported gross vs. −129,875 USD valuing the same 1,843 fills at their own fill prices) — not evidence of look-ahead, but evidence that this alternative path's own accounting needs to be understood and reconciled before it could be trusted as an intraday fill model | VERIFIED (existence) + TESTED (O-P9-1 accounting gap) |
| **State requirements for path-dependent logic (gap, with existing patterns in-repo)** | Support state that depends on the position's own history (entry price, elapsed time, a trailing stop) | SC4/SC5 make the default rule-evaluation path stateless. But the framework already contains two working stateful, path-dependent loops — P06's buffered-position application and P09's per-date greedy search — demonstrating the architecture *can* support this pattern; neither is currently wired to anything resembling an intraday state need | VERIFIED (existence of P06, P09 as stateful precedent) |

### 22.D Transfer not justified

| Item | Why evidence is insufficient | Evidence |
| --- | --- | --- |
| P09 (dynamic optimisation) | Internals only partially read (§12.4); deep review explicitly deferred | UNVERIFIED (depth) |
| E05 (order stacks / broker) | Phase 19, which would establish latency, fill handling, and reconciliation behaviour, was explicitly SKIPPED — RESOURCE PRIORITY | UNVERIFIED |
| **Latency (cross-cutting)** | Depends entirely on E05 internals, which are unaudited | UNVERIFIED |
| A07 (forecast mapping) | The Gaussian-forecast assumption behind it was never tested against actual forecast distributions, daily or otherwise | HYPOTHESIS |

### 22.5 Explicit coverage of the §45 mechanism list

For traceability against the master spec's named inspection list: **volatility targeting** → §22.C (P01, R02); **forecast scaling** → §22.C (A04); **forecast combination** → §22.C (A06, TESTED break); **correlation/diversification** → §22.C (R03/R04/R07, DOCUMENTED in-source warning); **signal vs. position sizing** → §22.A/§22.C split (the sizing *formula* is §22.C, the *signal contract itself* is §21/§22.B via SC9); **buffering** → §22.C (P05/P06); **transaction costs, spread, slippage** → §22.C (E02); **market impact** → §22.B (no mechanism exists to redesign); **latency, fill uncertainty, intrabar sequencing, partial fills** → §22.C/§22.D split (a partial in-repo answer exists via the order simulator, but its own accounting needs reconciliation, and latency specifically depends on unaudited E05); **stops, targets** → §22.B (structural gap, SC14); **state requirements** → §22.C (existing P06/P09 precedent, not currently applied to this need).

No replacement system is designed here, per spec §45.

---

## 23. Swing Operational Readiness (Phase 22)

**Scope and evidence basis (spec §46).** This section separates two questions for each item:
- **Research / reference usability:** can the audited machinery be read, run and relied on as a research reference at swing cadence (spec §5: decisions at most once per trading day, on daily-or-slower data)?
- **Live operational requirements:** what running a swing system live would need from this area, and what the audit established about pysystemtrade's live code for it.

It makes no adoption recommendation (spec §46) and ranks nothing. P2 is synthesis over the audit files (spec §41). Most rows cite earlier sections.

**The Phase 19 gap governs the live half of this section.** Phase 19 (live / production architecture) was SKIPPED — RESOURCE PRIORITY (§20). The only live-side facts established are:
- the production flow edges L1–L5 up to broker-order creation (§9.5);
- the E03/E04 card (Card 16), E06 overrides and limits (§7.10);
- the research/live consistency table (§13.5).

Everything else on the live side is **UNVERIFIED**. Where a live column below says "UNVERIFIED", it means *not examined*. It does **not** mean a problem was found, and it is not NO ISSUE IDENTIFIED.

**Session 9 targeted listing (the only repository access for this section).** Several spec §46 items (margin, micro contracts, capital, storage, monitoring, deployment) were never examined in P0/P1. For those, one read-only step was run in the pinned clone `audit/repo` @ `8958c49` (clean before and after):
- a `git ls-files` listing of file names;
- a row count of the shipped `data/futures/csvconfig/instrumentconfig.csv` and of the shipped price directories.

No source file was opened and nothing was executed. Findings from it are labelled **VERIFIED (listing)**: they establish that a file with that name exists, and **nothing about its behaviour** (spec §16: names are not evidence of behaviour).

### 23.1 Item-by-item

| Item | Research / reference usability (swing) | Live operational requirement and what is known | Evidence | Not assessable in this audit |
|---|---|---|---|---|
| **Data** | The default sim data is the shipped CSVs (`csvFuturesSimData`). 252 instruments have both adjusted and multiple prices, and all 252 have a row in the instrument config. The decision series is `daily_prices` = `resample("1B").last()` of the back-adjusted price, which is swing's native granularity (§21.1). Stored rows have irregular timestamps; hourly access exists but is not the default. | Production reads its full history from a database through a sim-data wrapper (L1), fed by the daily updaters `update_historical_prices`, `update_multiple_adjusted_prices` and `update_fx_prices`. Those updaters are listed, not read. | §11.1; §2; §9.5 L1 VERIFIED. Counts: VERIFIED (listing, session 9) | How the shipped historical CSVs were built (§11.7, UNVERIFIED). Production updater internals and data-quality checks (not read). The shipped data was last changed in commit `44208025` (2024-05-01, §11.7); how far each file's history extends was not checked |
| **Contracts** | Instrument metadata (`Pointsize`, `Currency`, cost fields) is **one static row per instrument with no date dimension**. Edits apply to all history, e.g. the SGX multiplier change 10 → 2 (§11.8). Expiry is approximated from the contract date plus a static `ExpiryOffset`. | Live contract resolution goes through the production DB and IB contract code (`sysbrokers/IB/ib_contracts.py` and related; listing only). | §11.8 VERIFIED; §11.9 POSSIBLE ISSUE (retrospective metadata) | Live contract selection and expiry handling (Phase 19 skipped); effect of metadata edits on rounding and costs (INFERRED only, §11.8) |
| **Rolls** | Two mechanisms (§11.2). **R1 (research):** static offsets plus full-dataset price *availability*; roll dates are POSSIBLE ISSUE (§11.10(c)). Shipped calendars were backed out of the shipped multiple prices, so pre-calendar contract selection cannot be reproduced from shipped inputs (e.g. SOFR prices from 1984, calendar from 2020). **Panama** back-adjustment mutates earlier *levels* but not earlier *differences* (EXP-05, TESTED). In the backtest, roll costs are pseudo-fills on equally spaced dates, not actual roll days (O-P16-2, §17.5). | **R2 (live):** a roll-status process with volume/expiry parameters and operator confirmation by default; adjusted prices are re-stitched at the roll. Research R1 and live R2 differ, so research roll dates need not match live ones (INFERRED, not compared on data). A swing position held for days spans roll dates more often than an intraday one, so both mechanisms apply to it (INFERRED from the definitions). | §11.2–§11.4, §11.9–§11.10; EXP-05 TESTED; §17.5 VERIFIED | R2 trigger internals (UNVERIFIED, §11.2). Effect size of availability-based roll dating (raw contract prices not shipped, §11.12). Actual live roll orders (`sysexecution/stack_handler/roll_orders.py`, listing only, §13.5) |
| **Carry** | Carry = annualised roll yield from the `PRICE`/`CARRY` columns; the value at *t* uses only prices at *t* (NO ISSUE IDENTIFIED, §11.10(b)). The carry contract per date comes from R1 or from the shipped multiple prices. Carry rules are in the default chapter-15 config, so carry reaches positions. | Production carry uses the same `rawdata` code over production multiple prices (INFERRED from L1: the same System is re-run; the production multiple-price updater was not read). | §11.5 VERIFIED; §9.5 L1 | Live multiple-price construction (updater not read) |
| **FX** | Spot FX from `fx_prices_csv` (12 shipped files) or the DB; aligned by `reindex(..., ffill)`; no backward fill found in the FX path (NO ISSUE IDENTIFIED). | Live FX is updated by `update_fx_prices` (listed, not read) and consumed through the same System code (INFERRED from L1). | §11.6 VERIFIED; file count VERIFIED (listing) | FX updater internals; IB FX client (`sysbrokers/IB/ib_Fx_prices_data.py`, listing only) |
| **Broker integration** | Not a research concern: the backtest is broker-free (E01 simulated fills). | The only broker integration present is IB via `ib_async` (`sysbrokers/IB/*`). What is VERIFIED is the path up to broker-order creation: L3 order generation (trade to `round(edge)`), L4 overrides and position limits, L5 contract orders and trade limits. **E05 (stacks, algos, IB client) is UNVERIFIED.** The docs' statement that there is no live trading system is stale (DV2). | §9.5 L1–L5 VERIFIED; §6.3 E05 UNVERIFIED; §20 | Order routing, algos, fill handling, partial fills, position reconciliation, error handling and restart behaviour (Phase 19 skipped). No broker connection was made (spec §10) |
| **Instrument universe** | The shipped instrument config has **586 rows** in 14 asset classes (Equity 151, FX 91, Bond 82, Sector 61, SingleStock 54, Ags 44, Metals 38, OilGas 30, Housing 13, STIR 9, Vol 6, Weather 4, Other 2, CommodityIndex 1). **252** of them have shipped prices (Equity 57, FX 43, Ags 36, Bond 34, Sector 34, Metals 21, OilGas 20, Vol 4, Housing 2, Other 1). The default chapter-15 system trades **6** (CORN, EUROSTX, MXP, SOFR, US10, V2X). The universe resolves config weights → `config.instruments` → all data, minus exclusion lists written with current knowledge and applied to all history (PF-12(b), POSSIBLE ISSUE). | Production universe comes from the strategy config and production DB. Reports named `duplicate_market_report`, `remove_markets_report` and `liquidity_report` exist (listing only). | §3; §14.1; §15 PF-12; counts VERIFIED (listing, session 9) | Live universe maintenance, and what those reports compute (not read) |
| **Diversification** | Instrument weights (P02) and the IDM (P03) are fixed in config by default; estimation (R06/R07) is opt-in, using weekly correlations of subsystem returns with `fit_end = period_start` (Card 11). The FDM is capped at 2.5. The pooled-stacking warning (DOCUMENTED in-source) concerns high-frequency data, not daily (§22.C). With 6 default instruments, how much diversification is achievable is a property of the chosen universe, which this audit did not measure. | Live re-runs the same System, so live weights and IDM equal the research values at the last row (E03, VERIFIED). | Cards 10–11 VERIFIED; §21.2 | Diversification achieved for any real account size or universe (not measured; performance claims excluded by spec §54) |
| **Capital** | Sizing uses `notional_trading_capital` (default 1e6) and `percentage_vol_target` 16. The backtest default is **fixed** capital (`fixed_capital`); compounding variants are opt-in. Positions use the unshifted capital multiplier while account capital is shifted (O4/PF-6). | Production injects **current** capital as the notional constant (L1; `production_capital_method: full`), so research and live scale capital in different places (O5/P8-O5). Capital-update and allocation code exists: `update_total_capital`, `update_strategy_capital`, `interactive_update_capital_manual`, `sysbrokers/IB/ib_capital_data.py`, a `minimum_capital_report` (listing only). | Card 9; §8 O4/O5; §9.5 L1, P8-O5 VERIFIED; listing VERIFIED (listing) | How live total and strategy capital are computed and allocated; what the minimum-capital report computes (not read) |
| **Margin** | **No margin, cash-balance or financing model was found in the backtest** (searched `systems/` for `margin`; absence UNVERIFIED beyond the searched terms, §10.2). Positions are sized by volatility only. | Production margin storage exists: `sysdata/production/margin.py`, `sysdata/mongodb/mongo_margin.py` (listing only). What is stored, where it comes from and whether it constrains positions or orders: **UNVERIFIED**. | §10.2, §10.6 item 7; listing VERIFIED (listing) | Any margin constraint on live positions; margin-to-capital relationships (not read; broker data unavailable, spec §10) |
| **Micro contracts** | Micro contracts are present as ordinary instrument rows with their own metadata: 23 instrument codes contain "micro" and 12 have shipped prices (AUD, CAD, CHF, EUR, GBP FX micros; SP500, NASDAQ; GOLD, COPPER, CRUDE_W, GASOILINE; ETHER). Contract size enters sizing through `Pointsize`, so a smaller contract gives proportionally more contracts for the same notional risk before rounding (§11.8, INFERRED). Integer rounding happens in P06 and E04 (`round`). P09 (dynamic optimisation, the integer-contract alternative) is TRANSFER NOT JUSTIFIED for depth reasons (§21.3). | A `sysinit/futures/clone_large_to_small_contracts.py` tool exists (listing only). | §11.8; §7.9 rounding; §12.4; counts VERIFIED (listing, session 9) | Any micro-specific code path (no file-name hit beyond the one above; code not searched). Rounding effects at small account sizes (not tested) |
| **Leverage** | No margin model, so leverage is not constrained by margin in the backtest (§10.2). Leverage-related controls: FDM/IDM `dm_max` 2.5 (Cards 8, 10), and the risk overlay's `max_risk_leverage` limit (P04, **OFF by default**, undocumented in `docs/`). | Live applies the risk overlay only if configured (same System). E06 position limits and overrides cap positions downstream (VERIFIED). Broker leverage limits: UNVERIFIED (E05). | Cards 8, 10, 15; §7.10 VERIFIED | Broker-imposed leverage or margin calls (Phase 19 skipped) |
| **Storage** | Research reads shipped CSVs by default. Storage back-ends exist for CSV, Parquet, MongoDB and Arctic (`sysdata/{csv,parquet,mongodb,arctic}`). Estimated parameters live only in the cache unless exported; the export writes last values (O-P13-1). | Production stores a pickled backtest state and the merged config per run, deleted after `backtest_max_age: 30` days (§14.1). Backup tooling exists: `run_backups`, `backup_db_to_csv`, `backup_mongo_data_as_dump`, `backup_parquet_data_to_remote`, `backup_state_files`, `backup_arctic_to_parquet` (listing only). No config or code versioning found (§14.1; absence UNVERIFIED beyond the searched terms). | §2; §14.1 VERIFIED; listing VERIFIED (listing) | Parquet/Mongo read/write paths (not read, §11.11); backup completeness and restore behaviour (not read) |
| **Computation** | The engine recomputes the whole history per System (no incremental path, §10.6 item 1). At swing cadence that is one recompute per decision day. Recorded runtimes in this audit: the 17 slow example tests took 228 s together (TEST-RUN-2); a P09 run on the six-instrument chapter-15 system took about 3 min (EXP-10). | Production re-runs the full System every run and uses only the last row (PF-9, E03 VERIFIED). | §10.6; §19; §16.7; progress file | Runtime and memory for a production-size universe (not measured). No performance claim is made (spec §54) |
| **Monitoring** | Not a research concern. | Monitoring code exists: `syscontrol/monitor.py`, `report_process_status.py`, `list_running_pids.py`, reporting modules (`risk_report`, `reconcile_report`, `market_monitor_report`, `instrument_risk_report`, `status_report` and others), and a doc `docs/dashboard_and_monitor.md` (listing only). These were classified Tier 3 (not inventoried, §6.2). **No age check on stored optimal positions was observed** in the files searched (PF-10; G8, UNVERIFIED elsewhere). | §6.2; §9.5 L2–L3; listing VERIFIED (listing) | What is monitored, alerting, reconciliation behaviour (Phase 19 skipped; Tier 3) |
| **Deployment** | Not a research concern. Backtests run from Python factory functions (e.g. `futures_system()`). | Production runs `sysproduction/run_*.py` processes under `syscontrol` scheduling (`control_config.yaml`, `timer_functions.py`, `run_process.py`), with a shipped `sysproduction/linux/crontab` and wrapper scripts (listing only). Production needs a private config (`private_config.yaml`, absent in the audit), a database and an IB gateway, none of which were available or used (spec §10). | §2 entry points; §3 live implications; listing VERIFIED (listing) | Scheduling order of `run_systems` vs `run_strategy_order_generator` (G8, UNVERIFIED); restart and failure handling (Phase 19 skipped) |

### 23.2 What this section can and cannot support

- **Research / reference usability at swing cadence is the better-evidenced half.** The data, contract, roll, carry and FX machinery was read in Phase 10 (§11, D01 VERIFIED for in-repo code). Its known limits are specific and recorded:
  - retrospective static metadata (POSSIBLE ISSUE);
  - availability-based research roll dates (POSSIBLE ISSUE);
  - shipped-history construction (UNVERIFIED);
  - no margin or financing model (absence UNVERIFIED beyond the searched terms);
  - the end-anchored cost deflator (PF-2, CONFIRMED ISSUE, costs and net P&L only, TESTED).
- **Live operational readiness is mostly not assessable from this audit.** Of the 16 spec §46 items, the live side of margin, monitoring and deployment rests on file listings only. For broker integration, the research-to-live flow up to broker-order creation is VERIFIED (§9.5 L1–L5); only E05's internals onward (order stacks, algos, IB client) are unaudited (Phase 19 skipped). The live side of every other item depends on production code that Phase 19 would have read.
  - Established live facts: the research-to-live flow up to broker-order creation (§9.5 L1–L5), trade-to-edge hard-coding (DV3), the capital-scaling difference (O5/P8-O5), E06 overrides and limits, and the absence of an observed age check on stored positions (PF-10).
  - Beyond those, this audit supports **no** statement that live operation at swing cadence works, or that it does not.
- **Nothing here is a recommendation.** Readiness is described, not judged; items are not ranked (spec §43, §46, §54).

### 23.3 Phase 22 change log (explicit)

- No CSV field changed. `last_phase` unchanged on every row (P2 is synthesis, as for Deliverable 1).
- New evidence this section: the session 9 file listing and data-file counts above, all VERIFIED (listing). No behaviour claim is based on them.
- No new DV/UD entries.

---

## 24. Master Inventory Views (Phase 23)

Generated from `pysystemtrade_framework_inventory.csv` (41 rows + the Signal Contract row) at commit `86fcd72`.

### 24.1 Alpha-independent framework

Every row with `alpha_specific = N` (i.e., every row except A03). This is the entire audited inventory minus the one component that *is* the signal:

SC, C01–C05, D01, A01–A02, A04–A08, R01–R11, P01–P09, E01–E06 — **40 of 41 components**.

**Case A / Case B recap (full reasoning already in §4/§5; not re-derived here):** under Case A (replacement signal satisfies the Signal Contract), all 40 of these components have survives_if_contract_met = Y in the CSV, including P09 (set in session 5, Phases 11–12, per §13.9). P09's own audit depth remains limited (see §21.3's TRANSFER NOT JUSTIFIED verdict), but that is a separate question from its Case A survival value. Under Case B (replacement violates the contract), per the CSV (survives_if_contract_violated):
- Y (14): C01, C02, C04, C05, D01, R02, R08, P02, P04, P07, P08, E02, E05, E06.
- PARTIAL (25): C03, A01, A02, A04-A08, R01, R03-R07, R09-R11, P01, P03, P05, P06, P09, E01, E03, E04.
- N (2): SC (violated by definition), A03 (inapplicable).

The partial set changes because exact zeros are erased and the prior forecast is held through intended-flat periods (SC9/SC10, TESTED by EXP-01); whole-history, stateless evaluation gives no feedback of position or fills to the rule (SC4/SC5); and there is no channel for entry/exit events, stops or targets (SC14).

### 24.2 Research / estimation framework

R01 (forecast-scalar estimation) · R02 (volatility) · R03 (forecast correlation) · R04 (FDM estimation) · R05 (forecast-weight optimisation) · R06 (instrument-weight optimisation) · R07 (instrument correlation / IDM estimation) · R08 (fitting dates) · R09 (turnover / SR-cost) · R10 (forecast P&L proxy) · R11 (cost-ceiling speed limit).

All eleven default to CONCEPTUALLY PORTABLE — UNTESTED at swing. At intraday, ten of eleven are POTENTIALLY PORTABLE — REQUIRES REDESIGN, with R08 the sole exception (CONCEPTUALLY PORTABLE — UNTESTED, being pure calendar arithmetic with no frequency term). This is the layer where the repository's own documentation most directly warns against high-frequency use (the stacking-function comment underlying R03/R04/R05/R06/R07).

### 24.3 Portfolio / risk framework

P01 (position sizing) · P02 (instrument-weight application) · P03 (IDM application) · P04 (risk overlay) · P05/P06 (buffering) · P07 (capital multiplier) · P08 (long-only) · P09 (dynamic optimisation).

Seven of nine are CONCEPTUALLY PORTABLE — UNTESTED for swing and either CONCEPTUALLY PORTABLE — UNTESTED (P04, P07, P08 — no embedded frequency constant) or POTENTIALLY PORTABLE — REQUIRES REDESIGN (P01, P02/P03, P05/P06 — daily-vol-denominated constants) for intraday. P09 is TRANSFER NOT JUSTIFIED at both frequencies, for audit-depth reasons rather than evidence against it.

### 24.4 Execution framework

E01 (backtest P&L) · E02 (cost model) · E03 (production runner) · E04 (order generation) · E05 (order stacks/broker) · E06 (overrides/limits).

This layer shows the sharpest swing/intraday split in the whole inventory: every row is CONCEPTUALLY PORTABLE — UNTESTED for swing (the default execution model *is* a swing execution model), but E01 and E03 become DAILY-DEPENDENT at intraday specifically because their daily assumption is structural rather than parametric (§22.B). E02 and E04 are POTENTIALLY PORTABLE — REQUIRES REDESIGN. E05 is TRANSFER NOT JUSTIFIED for depth reasons (Phase 19 skipped).

### 24.5 Swing transfer view (grouped by label)

| Label | Count | Components |
| --- | --- | --- |
| CONCEPTUALLY PORTABLE — UNTESTED | 39 | SC, C01–C05, D01, A01–A08, R01–R11, P01–P08, E01–E04, E06 |
| POTENTIALLY PORTABLE — REQUIRES REDESIGN | 0 | — |
| DAILY-DEPENDENT | 0 | — |
| TRANSFER NOT JUSTIFIED | 2 | P09, E05 |

### 24.6 Intraday transfer view (grouped by label)

| Label | Count | Components |
|---|---|---|
| CONCEPTUALLY PORTABLE — UNTESTED | 8 | C01, C02, C04, R08, P04, P07, P08, E06 |
| POTENTIALLY PORTABLE — REQUIRES REDESIGN | 27 | SC, C03, C05, D01, A01, A02, A04, A05, A06, A08, R01–R07, R09–R11, P01–P03, P05, P06, E02, E04 |
| DAILY-DEPENDENT | 3 | A03, E01, E03 |
| TRANSFER NOT JUSTIFIED | 3 | P09, E05, A07 |

---

## 25. Swing vs Intraday Transfer Matrix (Phase 24)

Full matrix, all 41 inventory rows plus the Signal Contract. "What breaks" is left blank where nothing does. No ranking is implied by row order (CSV order preserved).

| Component | Current Implementation | Underlying Principle | Swing Transfer | Intraday Transfer | What Breaks | Evidence Needed |
| --- | --- | --- | --- | --- | --- | --- |
| SC Signal Contract | SC1–SC16 (§5) | A forecast is a signed, continuous series known at t | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | Zero-as-missing (SC9) and whole-history evaluation (SC4) both assume a non-event-driven, daily-or-slower signal | An intraday-native contract definition and a test signal built against it |
| C01 System | `basesystem.py` | Compose named calculation stages | CONCEPTUALLY PORTABLE — UNTESTED | CONCEPTUALLY PORTABLE — UNTESTED | — | Nothing beyond what feeds it |
| C02 Stage | `stage.py` | A named unit of calculation within a System | CONCEPTUALLY PORTABLE — UNTESTED | CONCEPTUALLY PORTABLE — UNTESTED | — | Nothing beyond what feeds it |
| C03 Cache | `system_cache.py` | Memoise pure-function results | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | Whole-history recompute cost at 1–5min row counts; UD2's broken argument-keying | Cache-cost measurement at intraday row counts |
| C04 Config | `configdata.py`/`defaults.yaml` | Parameter store | CONCEPTUALLY PORTABLE — UNTESTED | CONCEPTUALLY PORTABLE — UNTESTED | — | New parameter values only |
| C05 SimData | `sim_data.py`/`futures_sim_data.py` | Supply price/vol/carry data | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | Default path resamples to daily | A working sub-daily data path through the same stages |
| D01 Price/roll data | adjusted/multiple prices, roll calendars | Continuous back-adjusted futures series | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | Roll dating and back-adjustment validated at daily granularity only | Bar-level validation of roll/back-adjustment logic |
| A01 TradingRule | `trading_rules.py` | Generic per-instrument signal call | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | SC4 (vectorised) / SC9 (zero=missing, TESTED) | An event-driven, stateful call variant |
| A02 Rules stage | `forecasting.py` | Invoke rules per instrument, coerce to Series | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | Same as A01 | Same as A01 |
| A03 Provided rules | EWMAC/carry/breakout | Trend/carry signal generation | CONCEPTUALLY PORTABLE — UNTESTED *(alpha, out of scope)* | DAILY-DEPENDENT | Docstring-verified day-denominated lookbacks | Not applicable — this is the signal being replaced |
| A04 Forecast scaling | `forecast_scale_cap.py` | Normalise forecast magnitude | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | Mean-abs scalar estimated on non-zero bars only | Behaviour under a sparse/event signal |
| A05 Forecast cap | `forecast_scale_cap.py` | Bound extreme conviction | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | Cap becomes trivial or distortive for a fixed-size signal | Cap behaviour under non-continuous forecasts |
| A06 Forecast combination | `forecast_combine.py` | Blend multiple signals | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | Ffill holds last non-zero forecast (TESTED, EXP-01); `1B` resample is explicit | An exit-aware combination step |
| A07 Forecast mapping | `forecast_mapping.py` | Non-linear response curve | CONCEPTUALLY PORTABLE — UNTESTED | TRANSFER NOT JUSTIFIED | Gaussian assumption untested at any frequency | A statistical test of forecast distribution shape |
| A08 FDM application | `forecast_combine.py` | Scale for imperfect forecast correlation | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | Depends on R03/R04 | Same as R03/R04 |
| R01 Forecast-scalar est. | `forecast_scalar.py` | Estimate the scaling constant | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | Estimated on non-zero bars only; interacts with SC9 | Behaviour under sparse signals |
| R02 Vol estimation | `rawdata.py`/`vol.py` | Estimate risk per unit position | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | 35-day/10-year windows are calendar-day-denominated | Re-derived windows and validation at bar frequency |
| R03 Forecast-corr est. | `pooled_correlation.py` | Estimate forecast co-movement | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | In-source warning: stacking method won't work with high-frequency data (DOCUMENTED) | A pooling method that survives high-frequency data |
| R04 FDM estimation | `diversification_multipliers.py` | Calibrate diversification multiplier | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | Depends on R03 | Same as R03 |
| R05 Forecast-weight opt. | `sysquant/optimisation/*` | Fit forecast weights | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | P&L proxy (R10) and correlation inputs (R03) both assume daily | Redesigned P&L proxy and correlation basis |
| R06 Instrument-weight opt. | `portfolio.py` | Fit instrument weights | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | Depends on R07 | Same as R07 |
| R07 Instrument-corr/IDM est. | `correlation_over_time.py` | Estimate cross-instrument diversification | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | Same in-source high-frequency warning applies (subsystem returns pooled the same way) | Same as R03 |
| R08 Fitting dates | `fitting_dates.py` | Generate refit-period boundaries | CONCEPTUALLY PORTABLE — UNTESTED | CONCEPTUALLY PORTABLE — UNTESTED | — | None identified |
| R09 Turnover/SR cost | `strategy_functions.py`/`account_costs.py` | Estimate trading activity and its cost | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | `.resample("1B")` before differencing (VERIFIED) would discard intraday activity | A turnover measure at native bar frequency |
| R10 Forecast P&L proxy | `account_forecast.py` | Approximate forecast-only P&L | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | Same daily assumptions as E01 | Same as E01 |
| R11 Cost-ceiling speed limit | `forecast_combine.py` | Drop rules whose cost is too high | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | Inherits R09 | Same as R09 |
| P01 Position sizing | `positionsizing.py` | Size to a risk target | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | √256 annualisation constant (VERIFIED) | Re-derived annualisation and vol estimator |
| P02 Instrument-weight appl. | `portfolio.py` | Allocate risk across instruments | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | EWM125 smoothing window; depends on R06 | Same as R06 |
| P03 IDM application | `portfolio.py` | Scale for cross-instrument diversification | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | Depends on R07 | Same as R07 |
| P04 Risk overlay | `risk_overlay.py` | Portfolio leverage/risk scalar | CONCEPTUALLY PORTABLE — UNTESTED | CONCEPTUALLY PORTABLE — UNTESTED | — (evidence thinner: undocumented) | Deeper reading of an undocumented, off-by-default module |
| P05 Buffer calc | `buffering.py` | Avoid over-trading around a noisy target | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | Width tied to daily-vol-scaled average position | A buffer width tied to intrabar noise, not daily vol |
| P06 Buffered position sim | `account_buffering_system.py` | Apply the buffer path-dependently | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | Holds last position on NaN inputs; static width | Behaviour under frequent target jumps |
| P07 Capital multiplier | `account_with_multiplier.py` | Scale by available capital | CONCEPTUALLY PORTABLE — UNTESTED | CONCEPTUALLY PORTABLE — UNTESTED | — | None identified |
| P08 Long-only | `positionsizing.py` | Floor negative positions at 0 | CONCEPTUALLY PORTABLE — UNTESTED | CONCEPTUALLY PORTABLE — UNTESTED | — | None identified |
| P09 Dynamic optimisation | `dynamic_small_system_optimise/*` | Integer-position construction, alternative to classic | TRANSFER NOT JUSTIFIED | TRANSFER NOT JUSTIFIED | Own internals only partially read | A full read of the remaining P09 internals |
| E01 Backtest P&L | `pandl_calculation.py` | Simulate fills and returns | CONCEPTUALLY PORTABLE — UNTESTED | DAILY-DEPENDENT | Single fill at next daily close; no intrabar fills, stops, or targets | A genuinely different fill-simulation engine |
| E02 Cost model | `pandl_cash_costs.py`/`pandl_SR_cost.py` | Charge trading costs | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | Linear, size- and time-independent, constant spread | A size/liquidity/time-of-day-aware cost model |
| E03 Prod. system runner | `run_system_classic.py` | Re-run system daily, act on last row | CONCEPTUALLY PORTABLE — UNTESTED | DAILY-DEPENDENT | Whole-history re-run per decision (SC4) | A materially different production architecture, not a faster version of this one |
| E04 Order generation | `classic_buffered_positions.py` | Trade to buffer edge | CONCEPTUALLY PORTABLE — UNTESTED | POTENTIALLY PORTABLE — REQUIRES REDESIGN | No event/exit channel | A stop/target/event order-generation path |
| E05 Order stacks/broker | `sysexecution/*`, `sysbrokers/IB/*` | Route and manage live orders | TRANSFER NOT JUSTIFIED | TRANSFER NOT JUSTIFIED | Unaudited (Phase 19 skipped) | The Phase 19 review that was skipped |
| E06 Overrides/limits | `override.py`/`position_limits.py`/`trade_limits.py` | Post-hoc position/trade caps | CONCEPTUALLY PORTABLE — UNTESTED | CONCEPTUALLY PORTABLE — UNTESTED | — | None identified |

---

## 26. Final Research Framework Synthesis (Phase 25)

**Basis.** This section is synthesis only (spec §41, §49). It draws on §2–§22 and §24–§25 and on the canonical CSV. It adds no new evidence and reads no source. Each answer carries the evidence tag of the finding it rests on. Where the CSV and earlier report text differ, **the CSV is used** and the difference is named (26.3). Nothing below is a recommendation, and no component is ranked (spec §43, §54).

### 26.1 Structured answers (spec §49)

**1. What is the actual conceptual architecture?**
- A `System` is a container of named `SystemStage` objects plus one `simData` and one `Config`. Stages compute **whole-history pandas series on demand**: a lazy, pull-based tree memoised in a per-System cache. There is no clock or event loop. VERIFIED (§3; §10.1).
- The default pipeline is rawdata → rules → forecast scale/cap → forecast combination (FDM, then a combined cap or mapping) → position sizing → portfolio (instrument weights, IDM, optional risk overlay, buffer edges) → accounts (buffered position path, P&L, costs). VERIFIED (§9.1, Executive Summary 2).
- Research estimators (scalars, correlations, weights, FDM, IDM, turnover and SR cost) are opt-in feedback edges into that pipeline, all OFF by default except volatility. VERIFIED (§9.4; Executive Summary 10).
- Live operation re-runs the same System each run, stores the last row's buffer edges, and generates orders from them through overrides and limits to the order stacks and broker. VERIFIED up to broker-order creation (§9.5 L1–L5); the stacks and broker (E05) are UNVERIFIED.

**2. What is the alpha framework?**
- Eight ALPHA-layer rows (A01–A08). Only **A03** (the provided rules) is alpha-specific. The others (the rule wrapper and Rules stage, scaling, cap, combination, mapping, FDM application) sit in the alpha pipeline but are signal-agnostic machinery. VERIFIED (CSV `alpha_specific`; §4).
- The interface they share is the **Signal Contract** (§5, SC1–SC16): a signed, continuous, daily `pd.Series` per (instrument, rule variation), evaluated over the whole history, scaled to average |10| and capped at ±20. Position is linear in the forecast. Exact zeros become NaN and are forward-filled (SC9, TESTED by EXP-01).

**3. What is the research / estimation framework?**
- Eleven RESEARCH rows (R01–R11): forecast-scalar, volatility, forecast-correlation, FDM, forecast-weight, instrument-weight and instrument-correlation/IDM estimation; fitting dates; turnover and SR cost; the forecast P&L proxy; the cost-ceiling speed limit. VERIFIED (CSV; §6).
- Every estimation switch defaults OFF except volatility (R02). VERIFIED (Executive Summary 10).
- Fit windows end at `period_start` (R08), and default estimators are exponential, taking rows strictly before `period_start`. No causal violation was identified at the date-window level. VERIFIED (§8; §15).
- The known exceptions are recorded, not resolved:
  - PF-1 scalar backfill, and PF-3/PF-4 end-of-sample SR cost × full-sample turnover: CONFIRMED ISSUE ONLY WHEN NON-DEFAULT OPTION ENABLED, TESTED (§16);
  - PF-11 end-anchored fit grid: POSSIBLE ISSUE (§16.12);
  - PF-2, the end-anchored cost deflator: CONFIRMED ISSUE with default ON, and TESTED as affecting costs and net P&L only in the default system (§16.3).
- `impl_evidence` for R03–R07 stays INFERRED under U5.

**4. What is the portfolio / risk framework?**
- Nine PORTFOLIO_RISK rows (P01–P09): vol-targeted position sizing (√256 annualisation), instrument-weight and IDM application, an optional risk overlay (OFF by default, undocumented), buffer edges and the path-dependent buffered position (P06, the only path-dependent step in the default backtest), a capital multiplier (fixed by default), a long-only constraint, and dynamic optimisation (P09, an alternative, not default). VERIFIED (§6; §12), except P09, which is PARTIALLY AUDITED — RESOURCE PRIORITY (§12.4).

**5. What is the execution framework?**
- Six EXECUTION rows. **Simulated:** E01 infers fills from position changes, with a decision at close t filled at close t+1 (TESTED by the Phase 16 trace, §17); E02 is a linear cost model with roll pseudo-fills and an end-anchored deflator. **Live:** E03 re-runs the System and stores `iloc[-1]` edges; E04 trades to `round(edge)` (trade-to-edge hard-coded, DV3); E06 overrides and limits apply downstream with no backtest equivalent. VERIFIED.
- E05 (order stacks, algos, IB broker) is **UNVERIFIED**: Phase 19 was SKIPPED — RESOURCE PRIORITY (§20).
- An alternative accounts stage, the order simulator (UD5, §10.4), replaces fill inference with a per-row order/fill loop. It is not an inventory row (DISC-3). VERIFIED (code); accounting effect TESTED (EXP-11, §16.8).

**6. What survives complete replacement of the signal when the replacement satisfies the Signal Contract (Case A)?**
- Per the CSV (`survives_if_contract_met`): **40 of 41 rows = Y**. The one exception is **A03 = N**: the provided rules are the signal being replaced, so they become inapplicable rather than broken.
- Evidence status: `swap_evidence` is INFERRED for every row except A06 (TESTED) and A07 (HYPOTHESIS). The finding is counterfactual (spec §13) and was not tested by running a replacement signal.
- Survival means the mechanism still runs as designed. It says nothing about whether parameter values fit the new signal; those must be re-fixed or re-estimated (§5 Case A).

**7. What fails or changes when the replacement violates the Signal Contract (Case B)?**
Per the CSV (`survives_if_contract_violated`):
- **Y (14):** C01, C02, C04, C05, D01, R02, R08, P02, P04, P07, P08, E02, E05, E06.
- **PARTIAL (25):** C03, A01, A02, A04–A08, R01, R03–R07, R09–R11, P01, P03, P05, P06, P09, E01, E03, E04.
- **N (2):** SC (violated by definition) and A03 (inapplicable).

Why the partial set changes (§5 Case B):
- exact zeros are erased and the prior forecast is held through intended-flat periods (SC9/SC10, TESTED by EXP-01);
- whole-history, stateless evaluation gives no feedback of position or fills to the rule (SC4/SC5, VERIFIED);
- sparse signals are scaled on active bars only, and turnover and costs are understated on held series (INFERRED);
- there is no channel for entry/exit events, stops or targets (SC14, VERIFIED).

`swap_evidence` as in item 6.

**8. What is daily / position-trading dependent?**
- Rows labelled **DAILY-DEPENDENT** for intraday (§24.6, CSV): **A03** (day-denominated rule parameters), **E01** (single fill at the next daily close) and **E03** (whole-history re-run per decision). VERIFIED.
- Daily conventions that are *parametric* rather than structural run through most other rows: business-day resampling of prices, weights and turnover (SC12); √256 annualisation; the 35-day / 10-year vol windows; the buffer width as a daily-vol quantity; the 256-day turnover annualisation. These sit in the 27 POTENTIALLY PORTABLE — REQUIRES REDESIGN rows. VERIFIED (§13.6; §10.6; §22.C).
- Two structural gaps are not inventory rows (§22.B): **no market-impact or cost-curve model** (absence UNVERIFIED beyond the searched terms) and **no stop/target/intrabar-exit channel** (SC14, VERIFIED).

**9. Which principles are conceptually portable to swing futures?**
- **39 of 41 rows** are CONCEPTUALLY PORTABLE — UNTESTED at swing (§24.5; CSV). The general reason: the audited default already decides once per day on daily bars and fills at the next daily close, which is the swing cadence as defined in spec §5 (§21.1, VERIFIED).
- **UNTESTED** is load-bearing: no swing-specific run was made in this audit.
- **P09 and E05** are TRANSFER NOT JUSTIFIED because the audit did not examine them deeply enough (§21.3). That is a statement about audit depth, not evidence against transfer.

**10. Which principles are potentially portable to intraday futures?**
- **CONCEPTUALLY PORTABLE — UNTESTED (8):** C01, C02, C04, R08, P04, P07, P08, E06. Their logic has no embedded bar-frequency constant (§22.A, VERIFIED).
- **POTENTIALLY PORTABLE — REQUIRES REDESIGN (27; see item 11).** The underlying principles may transfer: size inversely to volatility, normalise and blend forecasts, diversify by correlation, trade only outside a threshold, charge a cost per fill. Their implementations would not transfer as written (§22.C). HYPOTHESIS for the principle; VERIFIED for the implementation constraints.

**11. Which implementations require redesign for intraday frequency?**
- **The 27 rows labelled POTENTIALLY PORTABLE — REQUIRES REDESIGN:** SC, C03, C05, D01, A01, A02, A04, A05, A06, A08, R01–R07, R09–R11, P01–P03, P05, P06, E02, E04 (§24.6; CSV).
- The specific redesigns are named in §22.C and the §25 "Evidence Needed" column. Examples:
  - a turnover measure not resampled to `1B` (R09, VERIFIED);
  - a pooling method that survives high-frequency data, since the stacking function carries an in-source warning (R03/R04/R07, DOCUMENTED);
  - re-derived annualisation and vol windows (P01/R02, VERIFIED);
  - an exit-aware combination step (A06, TESTED break);
  - a size-, liquidity- and time-of-day-aware cost model (E02, VERIFIED).
- No replacement is designed here (spec §45).

**12. Which assumptions are most important?**
The criterion is **breadth of dependence**: how many inventory rows change status if the assumption fails, per §5 Case B, §22 and §25, and whether the effect has been TESTED. The list is unordered. The criterion identifies these assumptions, and no importance order among them is claimed.
- **Zero means missing, then forward-filled** (SC9/SC10). It reaches every forecast-processing row, and its effect is TESTED (EXP-01).
- **Whole-history, stateless, vectorised evaluation** (SC4/SC5). It underlies the cache, rules, production runner and the absence of state feedback. VERIFIED.
- **Business-day frequency in all calibration statistics** (SC12). It reaches sizing, turnover, costs, weights and combination. VERIFIED.
- **Forecasts, not orders or events** (SC14). There is no entry/exit, stop or target channel anywhere downstream. VERIFIED.
- **A single price per bar, with a fill at the next bar** (E01; §13.6 item 4). It defines backtest execution. TESTED (Phase 16 trace).
- **Cost linearity and a constant spread per instrument** (E02; §13.6 items 2–3). VERIFIED formula; absence of impact modelling UNVERIFIED beyond the searched terms.
- **End-of-sample anchors in cost and estimation quantities** (PF-2 by default; PF-1, PF-3/PF-4 and PF-11 when estimation is on). TESTED (§16).
- **Static, current instrument metadata applied to all history, and research roll dates chosen by data availability** (§11.8–§11.10). VERIFIED mechanism; POSSIBLE ISSUE.

**13. Which assumptions should not be transferred blindly?**
Each of these is recorded with evidence showing the assumption holds only under conditions a new setting may not meet. The list is unordered.
- **Zero = missing.** A replacement signal that uses 0 for flat is silently held at its previous value. TESTED (EXP-01).
- **Business-day constants:** √256, `1B` resampling, 256-day turnover annualisation, a 35-day vol span, 0.1 × average position buffers. Correct only for a daily decision index. VERIFIED.
- **Pooled correlation by stacking with microsecond offsets.** The source warns it will not work with high-frequency data. DOCUMENTED (in-source).
- **Next-close single-price fills.** They rule out partial fills, queue position, latency and intrabar sequencing. VERIFIED.
- **The order simulator's gross P&L at bar prices.** For the provided hourly limit-order example, +31,516 USD against −129,875 USD at fill prices. TESTED (EXP-11). It is not look-ahead, but it is not a validated intraday fill model either.
- **Linear, size-independent costs with one spread per instrument for all history.** VERIFIED.
- **End-anchored quantities** (PF-2 by default; PF-1/PF-3/PF-4 with estimation). TESTED.
- **Research roll dating (R1) versus live roll decisions (R2).** Different mechanisms, not compared on data. INFERRED.
- **Shipped fixed parameters whose derivation is not in the repository** (N9). UNVERIFIED.
- **Capital scaling that differs between backtest (fixed multiplier) and live (current capital as notional).** VERIFIED (O5/P8-O5).
- **Trade-to-edge hard-coded live, while the backtest honours the config.** VERIFIED (DV3).
- **Anything in E05 or P09.** Not examined deeply enough to transfer (TRANSFER NOT JUSTIFIED, audit depth).

### 26.2 Framework layer summary (spec §49)

Column sources:
- **Problem Solved** and **Failure Mode Prevented** come from the Tier 1 cards (§6.4) where a card exists. For Tier 2 rows without a card they come from the §6.3 notes and are marked *(INFERRED from note)*; "—" means none is recorded.
- **Alpha-Specific?** is the CSV `alpha_specific` field.
- **Portfolio-Level?** records whether the component operates across instruments (Y) or per instrument (N). "infra" means cross-layer infrastructure; "both" means it has per-instrument and portfolio variants.
- **Transferable Principle?** gives the CSV swing / intraday labels. These are classifications, not recommendations (spec §43).
- **Evidence** is the CSV `impl_evidence` plus the report section.

Label abbreviations in this table: CP-U = CONCEPTUALLY PORTABLE — UNTESTED; PP-RR = POTENTIALLY PORTABLE — REQUIRES REDESIGN; DD = DAILY-DEPENDENT; TNJ = TRANSFER NOT JUSTIFIED.

| Framework Layer | Problem Solved | Failure Mode Prevented | Alpha-Specific? | Portfolio-Level? | Transferable Principle? | Evidence |
|---|---|---|---|---|---|---|
| Signal Contract (SC) | Defines what a rule must return for downstream stages to work as designed | — (an interface, not a mechanism) | N | infra | Swing CP-U; intraday PP-RR | VERIFIED; §5 |
| System + Stage (C01, C02) | A uniform container binding stages, data and config, with a shared namespace and one cache | Ad-hoc wiring | N | infra | Swing CP-U; intraday CP-U | VERIFIED; Card 2 |
| Cache (C03) | Avoids recomputing whole-history series and estimates | Repeated slow estimation; inconsistent recomputation within one System | N | infra | Swing CP-U; intraday PP-RR | VERIFIED; Card 1 |
| Config (C04) | Parameter store with layered defaults | — | N | infra | Swing CP-U; intraday CP-U | INFERRED; §6.3, §14 |
| SimData (C05) | Supplies price, vol, carry and FX series to stages *(INFERRED from note)* | — | N | infra | Swing CP-U; intraday PP-RR | VERIFIED; §6.3, §11.1 |
| Price / roll data (D01) | Continuous back-adjusted series, multiple prices and roll calendars *(INFERRED from note)* | — | N | infra | Swing CP-U; intraday PP-RR | VERIFIED; §11 |
| Trading-rule interface (A01, A02) | Any function over system data becomes a named rule variation producing a raw forecast | Rule-specific plumbing in downstream stages | N | N | Swing CP-U; intraday PP-RR | VERIFIED; Card 3 |
| Provided rules (A03) | Trend, carry, breakout and other signal generators *(INFERRED from note)* | — | **Y** | N | Swing CP-U (alpha; out of scope, §21.3); intraday DD | VERIFIED; §6.3 |
| Forecast scaling + scalar estimation (A04, R01) | A common scale across rules (average \|10\|) | Rules with different natural units dominating combination or sizing | N | N | Swing CP-U; intraday PP-RR (both) | VERIFIED; Card 4 |
| Forecast cap (A05) | Limits the influence of extreme forecasts | Outsized positions from outliers or scalar mis-estimation | N | N | Swing CP-U; intraday PP-RR | VERIFIED; Card 5 |
| Forecast combination (A06) | Blends rule variations into one instrument forecast | Reliance on a single rule; weight jumps; weight on rules without history | N | N | Swing CP-U; intraday PP-RR | VERIFIED; Card 6 |
| Forecast mapping (A07) | Optional non-linear response curve on the combined forecast *(INFERRED from note)* | — | N | N | Swing CP-U; intraday TNJ | INFERRED; §6.3 |
| FDM application + estimation (A08, R04, R03) | Restores average \|forecast\| lost to averaging imperfectly correlated forecasts | Systematic under-sizing from diversification across rules | N | N | Swing CP-U; intraday PP-RR (all three) | A08 VERIFIED; R03/R04 INFERRED; Card 8 |
| Volatility estimation (R02) | Price-difference vol for rule normalisation and sizing | Positions that ignore changing risk; jumps from short-window vol; division by zero | N | N | Swing CP-U; intraday PP-RR | VERIFIED; Card 7 |
| Forecast-weight optimisation (R05) + P&L proxy (R10) | Fits forecast weights on forecast P&L *(INFERRED from note)* | — | N | N | Swing CP-U; intraday PP-RR (both) | R05 INFERRED; R10 VERIFIED; §6.3, §12 |
| Fitting dates (R08) | Builds fit and apply windows with `fit_end = period_start` *(INFERRED from note)* | Using data from the period an estimate is applied to *(INFERRED from note)* | N | infra | Swing CP-U; intraday CP-U | VERIFIED; §6.3 |
| Turnover / SR cost + speed limit (R09, R11) | Excludes rule variations whose expected cost in SR units exceeds a ceiling | Allocating to fast rules whose costs consume their expected return | N | N | Swing CP-U; intraday PP-RR (both) | VERIFIED; Card 14 |
| Position sizing (P01) | Converts a forecast into contracts so forecast 10 = the annual cash-vol target for the subsystem | Positions whose risk varies with instrument vol, contract size or FX | N | N | Swing CP-U; intraday PP-RR | VERIFIED; Card 9 |
| Instrument weights + IDM (P02, P03, R06, R07) | Allocates the risk budget across instruments; restores the portfolio vol target lost to diversification | Concentration; portfolio vol below target | N | Y | Swing CP-U; intraday PP-RR (all four) | P02/P03 VERIFIED; R06/R07 INFERRED; Cards 10–11 |
| Risk overlay (P04) | Portfolio-wide multiplier in [0, 1] when estimated risk, shocked risk, absolute risk or leverage exceed limits | "Expected risk that is too high; weird correlation shocks combined with extreme positions; jumpy volatility" (docstring) | N | Y | Swing CP-U; intraday CP-U | VERIFIED (OFF by default; NOT_DOCUMENTED); Card 15 |
| Buffering (P05, P06) | A no-trade zone around the optimal position | Trading on small changes in the optimal position (cost drag) | N | both | Swing CP-U; intraday PP-RR (both) | VERIFIED; Card 12 |
| Capital multiplier (P07) | Scales notional positions to actual positions *(INFERRED from note)* | — | N | Y | Swing CP-U; intraday CP-U | VERIFIED; §6.3, §8 |
| Long-only (P08) | Sets negative positions to 0 for listed instruments *(INFERRED from note)* | — | N | N | Swing CP-U; intraday CP-U | VERIFIED; §6.3 |
| Dynamic optimisation (P09) | Integer-contract portfolio construction as an alternative to classic *(INFERRED from note)* | — | N | Y | Swing TNJ; intraday TNJ | VERIFIED (core only; PARTIALLY AUDITED); §12.4 |
| Backtest P&L (E01) | Simulated fills and returns from a position series *(INFERRED from note)* | — | N | N | Swing CP-U; intraday DD | VERIFIED; §6.3, §17 |
| Cost model (E02) | Deducts trading and roll costs; expresses costs in SR units | Overstated net performance; selecting rules too expensive to trade | N | N | Swing CP-U; intraday PP-RR | VERIFIED; Card 13 |
| Production runner + order generation (E03, E04) | Turns the latest backtest output into position bands, then orders given actual positions | Trading within the buffer; research/live calculation divergence | N | N | Swing CP-U; intraday E03 DD, E04 PP-RR | VERIFIED; Card 16 |
| Order stacks / broker (E05) | Routes and manages live orders *(INFERRED from note)* | — | N | infra | Swing TNJ; intraday TNJ | **UNVERIFIED**; §6.3, §20 |
| Overrides / limits (E06) | Post-generation position and trade caps, and discretionary overrides *(INFERRED from note)* | — | N | both | Swing CP-U; intraday CP-U | VERIFIED; §6.3, §7.10 |

Row coverage: the 29 table rows cover all 41 CSV rows (SC; C01–C05; D01; A01–A08; R01–R11; P01–P09; E01–E06). Where rows are grouped, every grouped ID carries the same labels for that column except where the cell says otherwise (E03/E04).

### 26.3 Differences between the CSV and earlier report text (corrected in the P2 Deliverable 2 review)

**The CSV is canonical for component fields** (spec §32). The Deliverable 2 recount found earlier text that differed from it. Both corrections are now applied:
- **Correction A, §24.1 recap** (a transcription error in Deliverable 1 against CSV data that was already correct): the Case A sentence now records P09 as Y in the CSV, and the Case B recap now lists the CSV's Y (14) / PARTIAL (25) / N (2) sets. Logged in `audit_progress.md` (session 9).
- **Correction B, §5 Case A/B tables** (documentation lag since session 5): the P09 rows now read Y and PARTIAL, as set in the CSV in session 5 (§13.9). Recorded as **DISC-4** in the divergence register.

§24.1's count "40 of 41 components" was already correct against `alpha_specific` (40 N, 1 Y).

## 27. Open Questions / Evidence Gaps / Stage-2 Comparison Questions

**Phase 26 (spec §50).** This section has three parts:
- 27.1 classifies every unresolved evidence item recorded in the audit into the six spec §50 categories;
- 27.2 points to the running issue lists;
- 27.3 lists neutral questions that could later be asked of another futures research architecture, generated from the inventory.

It guesses nothing and answers none of the 27.3 questions. The documentation / implementation divergence register below is unchanged.

### 27.1 Evidence gaps, classified (spec §50)

Each item is listed once, under the category that best describes *why* it is unresolved. "Source" is where the audit records it.

| Category | Item | What is unresolved | Source |
|---|---|---|---|
| **Unavailable source** | Shipped historical CSV construction | How the shipped multiple and adjusted prices were built before the shipped roll calendars begin. Described as author-built; the method is outside the repository | §11.7; §11.10(d); PF-8(d) |
| Unavailable source | Shipped fixed-parameter provenance (N9) | Method and data period behind the fixed parameters in `futuresconfig.yaml` | §15 N9; G12 |
| **Unavailable data** | Availability-based roll dating (R1) effect size | Re-building calendars needs raw per-contract prices, which are not shipped | §11.12; G11 (Phase 10) |
| **Unavailable dependency** | Live order stacks, algos, IB client (E05) at run time | Needs an IB gateway and a production database; excluded by the safety rules (spec §10), and not read statically either (Phase 19 skipped) | §6.3 E05; §20; G4 |
| Unavailable dependency | Live roll-status decision (R2) at run time | Needs production price and volume data; the trigger internals were also not read | §11.2 |
| Unavailable dependency | Production scheduling behaviour (G8) | The order of `run_systems` vs `run_strategy_order_generator`, and any staleness check on stored positions; needs the production scheduler and config | G8; PF-10 |
| Unavailable dependency | Production margin and capital data | What `sysdata/production/margin.py` / `mongo_margin.py` store, and how live capital is computed (listing only) | §23.1 |
| **Untestable implementation** | PF-12(b) ex-post universe selection | Exclusion lists written with current knowledge are applied to all history. A truncation test cannot isolate this; it is not a data path | §16.9 |
| Untestable implementation | N10 protected / stale cache | A user-workflow property, not a data path | §16.9 |
| **Insufficient evidence** | Phase 19 scope | Research-to-live connection, broker integration, reconciliation, account state, persistence, restart, monitoring, logging, error handling: **SKIPPED — RESOURCE PRIORITY**. A known gap, not NO ISSUE IDENTIFIED | §20 |
| Insufficient evidence | P09 remaining internals | Constraint set-up, data preparation, accounts and live-strategy internals not read (PARTIALLY AUDITED — RESOURCE PRIORITY) | §12.4; U4 |
| Insufficient evidence | A07 forecast mapping | The Gaussian-forecast assumption was never tested against actual forecast distributions; mapping parameters not read | §6.3 A07; §22.D |
| Insufficient evidence | Market impact / cost curve absence | The absence rests on name-based searches; UNVERIFIED beyond the searched terms | §13.2; G10 |
| Insufficient evidence | Live commission feedback | No automatic feedback from broker commissions into configured costs was observed; limited search | §13.5; G10 |
| Insufficient evidence | Margin / financing absence in the backtest | Searched `systems/` for `margin` and related terms only | §10.2 |
| Insufficient evidence | Config / code versioning absence | Searched a fixed term list only | §14.1 |
| Insufficient evidence | Parquet / Mongo storage paths | Not read | §11.11 |
| Insufficient evidence | Findings classified but not run in Phase 15 | PF-2 via estimated weights / IDM; PF-6; PF-7; PF-13; PF-14 effect size; N8; the greedy `False` maximum (G7 candidate) | §16.9 |
| Insufficient evidence | Metadata-edit effect | The effect on rounding, per-block commissions and live execution is formula-level INFERRED only | §11.8; §11.12 |
| Insufficient evidence | Timing trace coverage | Three dates, one instrument, daily default only. Hourly systems, order simulator, compounding, P09 and the warm-up boundary were not traced | §17.6 |
| Insufficient evidence | Hourly data in the bundled CSVs | Whether the bundled data contains intraday rows for the hourly path was not checked as a general property | G11 (Phase 9) |
| Insufficient evidence | Documentation coverage of production | The production docs were not read (Phase 19 skipped), so live-side documentation divergences are unassessed | Card 16; §20 |
| Insufficient evidence | Order simulator as a component | Not an inventory row (DISC-3). Its own accounting (O-P9-1) is TESTED only for the provided hourly limit-order example | §10.4; §16.8 |
| **Unresolved code ambiguity** | O-P9-1 | Whether gross P&L at bar prices rather than fill prices is intended; not documented | §10.4; §16.8 |
| Unresolved code ambiguity | O-P9-2 | Why the limit-fill slippage flag is `False` for buys and `True` for sells; intent not documented | §10.4 |
| Unresolved code ambiguity | O-P9-3 | Hourly use of a rule docstring-labelled for daily data; lookbacks then count hours | §10.4 |
| Unresolved code ambiguity | UD3 | Downstream numeric treatment of `minimum_position_limit` returning `False` | §12.3; register UD3 |
| Unresolved code ambiguity | §3 (v) | The instrument-code match takes the last matching positional argument, while the docstring says the first | §3 |
| Unresolved code ambiguity | SC5 edge | Any stage method could in principle be named as rule data, which could feed state back into rules (INFERRED) | §5 SC5 |
| Unresolved code ambiguity | R1 vs R2 roll consistency | Research and live roll mechanisms differ and were not compared on data (INFERRED) | §11.2 |

Not in this table: operational items that are not evidence about pysystemtrade. U2, usage/cost not recorded, is kept in `audit_progress.md`.

### 27.2 Running issue lists

Unresolved issues U1–U7, evidence gaps G1–G12 and limitation L-P15-1 are maintained in `audit_progress.md` and are authoritative there. 27.1 classifies their content; it does not replace those lists.

### 27.3 Future comparison questions (neutral; not answered)

These questions come from the verified inventory (spec §50). They are for a later comparison against another futures research architecture. No other system was inspected, and nothing here implies an expected answer or a preference.

**27.3.1 Standard questions, to ask for every inventory component.** For each of SC, C01–C05, D01, A01–A08, R01–R11, P01–P09 and E01–E06 (41 rows):
1. Does the architecture have an equivalent of this component?
2. Where does it live (module, layer, process)?
3. Is it separated from alpha generation?
4. Is it fixed, estimated or optimised, and how is it estimated?
5. When does the estimate become available relative to the data it is applied to?
6. Is its behaviour documented, and does the documentation match the implementation?
7. Is it covered by tests that would detect a change in its output?

**27.3.2 Component-specific questions, from verified findings.**

*Signal interface (SC, A01, A02)*
- What object and type must a signal return, and is that stated in documentation?
- How is an exact zero signal value interpreted: as flat, missing or held?
- Is a signal evaluated over the whole history at once or bar by bar, and can it receive its own position, fills or entry price?
- Is there a channel for entry/exit events, stops, targets or order types, separate from a continuous forecast?
- At what frequency are signals assumed to arrive, and where is that assumption encoded?

*Infrastructure (C01–C05, D01)*
- How are calculation stages composed, and are their dependencies declared or implicit?
- What is cached, what is the cache key, and do config or data changes invalidate it?
- How are configuration layers merged, and can a null value override a default?
- Are configuration and code versions recorded with each result?
- How are continuous futures series constructed (method of back-adjustment), and do later rolls change earlier values?
- How are roll dates chosen for research data, and is that the same mechanism as live rolls?
- Is instrument metadata (contract size, costs) versioned by date or applied to all history?

*Forecast processing (A04–A08, R01, R03–R05)*
- How are signals from different rules put on a common scale, and on which observations is the scale estimated?
- Is the scale estimate backfilled before enough data exists?
- How are missing values handled when signals are combined?
- How are combination weights estimated, on what return proxy, and at what refit frequency?
- How is diversification across signals measured, and is there a cap on the resulting multiplier?
- Is any non-linear mapping applied, and what distributional assumption does it make?

*Estimation framework (R02, R06–R11)*
- How is volatility estimated (windows, blending, floors), and in what time unit are the windows expressed?
- How are correlations estimated, and are instruments pooled? If pooled, how are rows aligned?
- Do fit windows end strictly before the period an estimate is applied to?
- Is the refit calendar anchored to the sample start, the sample end or fixed dates?
- How is turnover measured, and on what resampling?
- Are costs used in rule selection or weighting, and are any cost inputs taken from the end of the sample?

*Portfolio and risk (P01–P09)*
- How is a signal converted into a position (risk target, annualisation convention)?
- How are instrument weights and a cross-instrument diversification multiplier set?
- Is there a portfolio-level risk or leverage overlay, and is it on by default?
- Is there a no-trade buffer, how is its width set, and does the width depend on costs?
- How is capital scaled over time (fixed or compounding), and is the timing of capital consistent with positions?
- How are integer contract constraints handled for small accounts?

*Execution (E01–E06)*
- How are backtest fills simulated: at which price, with what delay, and with partial fills?
- How are trading costs modelled (spread, commission, impact), and are they size- or time-dependent?
- How are roll costs modelled: on actual roll dates or on modelled events?
- How does the live process derive today's target from research code, and is the stored target checked for age?
- Does live order generation follow the same buffer rule as the backtest?
- What overrides, position limits and trade limits exist, and do they have backtest equivalents?
- How are orders routed, filled, reconciled and recovered after failure?
- Is there an alternative event-driven or order-level simulator, and how does it value fills?

*Validation (cross-cutting, from §16–§19)*
- Which look-ahead or end-of-sample dependencies does the architecture's own test suite detect?
- Are end-to-end tests asserting outputs, or only that code runs?
- What safeguards exist against data snooping, repeated experimentation and multiple testing?

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
| DV14 | "The function `from syscore.accounting import account_t_test` can be used for this purpose" (`docs/backtesting.md:3018`) | There is no `syscore/accounting.py`; `git grep syscore.accounting` finds only this doc line. The function is `account_t_test` in `systems/accounts/curves/account_curve_analysis.py:16` (Phase 13, §14.3) | VERIFIED (minor, import path) |
| UD1 | (undocumented) | Zeros → NaN → ffill (SC9) | TESTED (EXP-01) |
| UD2 | (undocumented) | base_system_cache ignores arguments | TESTED (EXP-02) |
| UD3 | (undocumented) | `positionLimit.minimum_position_limit` returns `other.no_limit` (a bool, `False`) when the instrument has no limit but the instrument-strategy does; reaches only the dynamic-optimised live strategy's maximum-position input (`controls.py:578-592`; `dynamic_optimised_positions.py:289-322`). Downstream numeric treatment INFERRED | VERIFIED (return value) |
| UD4 | (undocumented) | Commission = **max**(per-block × \|qty\|, per-trade, percentage × value), not a sum (`instruments.py:365-373`); the docs list the three types without the combination rule (searched the `backtesting.md` costs section and `instruments.md` for max/maximum/largest) | VERIFIED |
| UD5 | (undocumented) | The order-simulator accounts stage `AccountWithOrderSimulator` and its hourly market/limit variants (`systems/accounts/order_simulator/*`; examples `systems/provided/example/{daily,hourly}_with_order_simulation*`) replace vectorised fill inference with a per-row order/fill loop and bypass buffering. `docs/*.md` searched for `order simulat`, `order_simulat`, `vectorised`, `vectorized`, `event.driven`, `event driven`: no hits (Phase 9, §10.4) | VERIFIED |
| DISC-4 | §5's Case A/B tables (Phase 4) recorded P09 as UNKNOWN / Not audited | Phase 11 (§12.4) read P09's core and the CSV was updated accordingly in session 5 (survives_if_contract_met = Y, survives_if_contract_violated = PARTIAL, §13.9), but §5's text was never back-ported | Found during P2 Deliverable 2 review (§26.3); §5 corrected |
