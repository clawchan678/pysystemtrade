# audit_progress.md — AUTHORITATIVE RESUME STATE

## Identity / provenance

| Field | Value |
|---|---|
| Workspace path | `/home/user/pysystemtrade/audit/` (inside the persistence repo checkout, see Persistence) |
| Repository URL (audit target) | https://github.com/pst-group/pysystemtrade |
| Verified repository identity | README @ 8958c49 says: "pysystemtrade ... open source version of Rob Carver's own backtesting and trading engine"; History: "In January 2026 Rob moved pysystemtrade to a new github 'organisation', pst-group ... owned by Andy and Rob." `pyproject.toml` Homepage = https://github.com/pst-group/pysystemtrade. Matches the intended target. |
| Default branch (reported by Git) | `develop` (`git ls-remote --symref https://github.com/pst-group/pysystemtrade HEAD` → `ref: refs/heads/develop`; clone `refs/remotes/origin/HEAD` → `origin/develop`) |
| Audited branch | `develop` |
| **Pinned commit (HEAD SHA)** | **`8958c49c38b1e4a8c07f0e4375d5e9cb68a087f7`** (commit date 2026-09-21 11:55:15 +0100, "Merge pull request #1634 ...") |
| Release / tag | `git describe` → `1.8.2-344-g8958c49c` (344 commits after tag `1.8.2`); `pyproject.toml` version = `1.8.2` |
| Audit date | 2026-09-24 (session start ~10:18 UTC) |
| Python | 3.11.15 (scratch venv) |
| Documentation versions | Last commit touching each doc: backtesting.md 2026-03-28; production.md 2026-09-18; data.md 2026-02-05; introduction.md 2025-04-05; IB.md 2026-04-01; installation.md 2026-03-04 |
| Model used | Session configured for claude-opus-5-5 (operator: confirm) |

### Provenance notes / discrepancies (recorded, not silently reconciled)

1. The session working directory is a clone of the fork `clawchan678/pysystemtrade` at branch `claude/jolly-galileo-jv9j4g`. The fork's HEAD is **identical** to upstream `develop` HEAD (`8958c49`). The audit reads **only** the fresh scratch clone of `pst-group/pysystemtrade` at `audit/repo/` (pinned). The fork checkout serves solely as the **persistence repository** (Mode B) for the three audit files. It is never modified outside `audit/`.
2. `PYSYSTEMTRADE_AUDIT_MASTER.md` and `CLAUDE.md` were absent at session 1 start. **Resolved in session 2 (Phase 5):** on the operator's explicit instruction, Claude Code wrote both files into `audit/`. `PYSYSTEMTRADE_AUDIT_MASTER.md` is a verbatim copy of the specification text supplied in the session-1 prompt (sections 0–56). `CLAUDE.md` is the §26 text. This overrides the §7 "Claude Code must NOT create the master specification" rule by operator authority. **Session 2 persistence check:** the operator uploaded the original `PYSYSTEMTRADE_AUDIT_MASTER.md` and `CLAUDE.md`. `diff` showed them byte-identical to the workspace copies. The workspace files were then overwritten with the uploaded originals (no content change), so they now come directly from the operator.
3. No operator-specified branch conflicts with the reported default branch.

## Persistence mode

MODE B (web / non-persistent Claude environment). Persistent storage = git branch `claude/jolly-galileo-jv9j4g` of `clawchan678/pysystemtrade`, directory `audit/`. `audit/repo/`, `audit/venv/`, `audit/scaffolding/home/`, `audit/scaffolding/pipcache/` are gitignored. The scratch clone must be re-created in a new session (`git clone https://github.com/pst-group/pysystemtrade audit/repo && git -C audit/repo checkout 8958c49c38b1e4a8c07f0e4375d5e9cb68a087f7`).

## Environment status

- Status: **USABLE** after setup attempt 1 of 2 (no second attempt needed).
- venv: `audit/venv` (python3 -m venv). Installed: pandas 2.1.3, numpy 1.26.4 (**pinned <2 by auditor**; pyproject allows `>=1.24.0`), scipy 1.17.1, statsmodels 0.14.0, scikit-learn 1.9.1, pyarrow 19.0.1, PyYAML 6.0.1, matplotlib 3.11.2, pymongo 3.11.3, ib_async 2.1.0, pytest 9.1.1, Flask, PyPDF2, psutil 7.2.1, pytz 2023.3. The repo is installed editable with `--no-deps --no-build-isolation`.
- Environment variables for scratch execution: `HOME=/home/user/pysystemtrade/audit/scaffolding/home`, `PIP_CACHE_DIR=/home/user/pysystemtrade/audit/scaffolding/pipcache`, `PYTHONDONTWRITEBYTECODE=1`. Execution cwd = `audit/repo`. No MongoDB, no IB gateway, no private config (the framework logs "Private configuration ... missing ... no problem if running in sim mode").
- Session 6: scratch clone and venv recreated in **setup attempt 1 of 2** with the recorded commands and environment variables (succeeded: Python 3.11, pandas 2.1.3, numpy 1.26.4; clone `8958c49`, clean).
- Recreate: `python3 -m venv audit/venv && audit/venv/bin/pip install 'pandas==2.1.3' 'PyYAML==6.0.1' 'numpy<2' scipy matplotlib 'statsmodels==0.14.0' 'scikit-learn>1.3.0' 'pytz==2023.3' 'pyarrow>=16,<20' 'pymongo==3.11.3' 'psutil==7.2.1' 'ib_async>=2,<3' Flask PyPDF2 pytest && audit/venv/bin/pip install --no-deps --no-build-isolation -e audit/repo`

## Stage / phase status

| Phase | Status |
|---|---|
| P0 Phase 1 — Provenance & environment | COMPLETE |
| P0 Phase 2 — Repository architecture | COMPLETE (targeted; see report §2) |
| P0 Phase 3 — System / Stage / Caching | COMPLETE (report §3) |
| P0 Phase 4 — Four-layer decomposition + Signal Contract + Case A/B | COMPLETE — **APPROVED by operator** (session 2), incl. the three classification decisions (see U3) |
| P0 Phase 5 — Master inventory (tiers + Tier 1 cards) | COMPLETE (report §6; 16 cards / 26 IDs + SC + 13 Tier 2 = 40; evidence-change log §6.5) |
| P0 Phase 6 — pysystemtrade-specific framework concepts | COMPLETE — **APPROVED by operator** (session 2) (report §7; 10 concepts; E06 added; DV10) |
| P0 Phase 7 — State and estimation | COMPLETE (session 3; report §8: 20-quantity table, per-quantity assessment, O1–O12, PF-1…PF-12, change log §8.6) — **APPROVED by operator** (session 5 instructions) |
| P0 Phase 8 — Dependency / information flow | COMPLETE — **APPROVED by operator**; DISC-1/DISC-2 accepted and corrected in session 5 (session 4; report §9: corrected flow, spec-chain corrections, D1–D18, F1–F5, L1–L5, P8-O1…O5, DISC-1/2, DV11/DV12) |
| **P0 (Phases 1–8)** | **COMPLETE — P0 STOP** (all phases approved) |
| P1A Phase 11 — Forecast / weight / portfolio methodology | COMPLETE — **APPROVED by operator** (session 5; report §12: G1 and G7 closed, P09 core read (PARTIALLY AUDITED — RESOURCE PRIORITY), O-P11-1…4, PF-13 candidate) |
| P1A Phase 12 — Cost / turnover / buffering / speed limits | COMPLETE — **APPROVED by operator**, including both consistency-check updates and the P09 reclassification (session 5; report §13: cost components, turnover controls, cost influence, research/live table, intraday-sensitive assumptions, DV13/UD4) |
| P1A Phase 9 — Simulation / backtest architecture | COMPLETE (session 6; report §10: end-to-end trace, §39 dimensions, classification, order simulator UD5, PF-14 candidate, DISC-3) |
| P1A Phase 14 — Static causality / look-ahead | COMPLETE (session 6; report §15: central question answered per configuration; PF-1…PF-15 and N1–N14 classified; EXP-04 TESTED) |
| P1A Phase 13 — Configuration / experiment infrastructure | COMPLETE (targeted; session 6; report §14: §39 items, precedence, versioning absence, O-P13-1…3, DV14) |
| P1A Phase 10 — Data / contract / roll architecture | COMPLETE (session 7; report §11: data sources, two roll mechanisms R1/R2, multiple-price builder, Panama back-adjustment + EXP-05, carry, FX, shipped-data provenance, metadata, mutation table, PF-8 → POSSIBLE ISSUE, D01 → VERIFIED) |
| **P1A (Phases 9–14)** | **COMPLETE — P1A STOP** (Phase 10 awaiting operator review) |
| P1B Phase 15 — Empirical causality | COMPLETE (session 8, operator-authorised Phase 15 only; report §16: EXP-06…EXP-11 + EXP-08b; PF-2/PF-1/PF-3/PF-4/O-P11-1/O-P9-1/O-P9-2 effects TESTED; PF-11 → CONFIRMED ISSUE ONLY WHEN NON-DEFAULT OPTION ENABLED; PF-15 → NO ISSUE IDENTIFIED for positions/P&L) — **STOPPED BEFORE PHASE 16** |
| P1B Phases 16–19, P2 | NOT STARTED |

**Current phase:** P1B Phase 15 COMPLETE — **STOPPED BEFORE PHASE 16** (session 8). Phases 16–19 not started.

**Exact next task:** **STOP. Await operator authorization** after Phase 15 (report §16). Do not start Phase 16 (or 17–19) without explicit operator approval.

## Unresolved issues

- U1: RESOLVED (session 2). Spec files added to `audit/` on operator instruction (provenance note 2).
- U2: OPEN. The operator's approval message contained the literal placeholder "[INSERT ACTUAL USAGE/COST HERE]" and no figure. Usage/cost through the Phase 4 gate is therefore still **not recorded**. Claude Code cannot see account-level cost and will not estimate it.
- U3: RESOLVED (operator decision, session 2). A08 FDM application = ALPHA; R04 FDM estimation = RESEARCH. P06 buffered position = PORTFOLIO_RISK, with the caveat that the code lives in `systems/accounts/*`. E01 backtest P&L = EXECUTION, qualified as *simulated* execution, distinct from live order generation and broker execution (E03–E05). Caveats preserved in report §6.1 and Cards 8/12/16.
- U4: `systems/provided/dynamic_small_system_optimise` (an alternative portfolio construction path) has been classified only. It is PARTIALLY AUDITED.

- U5: **RESOLVED** (operator ruling, session 2). §12 is applied literally: direct source inspection does not justify an INFERRED → VERIFIED upgrade. R04 and R07 `impl_evidence` were reverted to **INFERRED** in the CSV, report cards 8 and 11, the §6.5 log, and the Executive Summary. The underlying observations and their provenance are kept. P04/E02 (UNVERIFIED → VERIFIED) are unaffected.
- U7: RESOLVED (operator decision, session 2). The E06_PROD_OVERRIDES_LIMITS row stays in the inventory as Tier 2 / VERIFIED (41 rows). It changes only if the audit itself establishes a reason.
- U6: RESOLVED (session 2 check). The Tier 1 ID count was misstated as 27 in the report and progress file; the correct count is 26 (26 + SC + 13 Tier 2 = 40). Card 6 stated A06 `swap_evidence` as INFERRED while the CSV holds TESTED (Phase 4, approved); the card text was aligned to the CSV, and no evidence value was changed.

## Evidence gaps

- G1: **CLOSED in Phase 11** at code level (report §12.2: optimiser numerics, equalisation, SR tilt, cleaning, pooled correlation). Classification is unchanged: R03/R05/R06 INFERRED (U5). History: PARTLY ADDRESSED in Phases 5 and 7 (Phase 7: cleaning path and `< fit_end` selection in the mean/stdev estimators read; remaining: per-method optimiser numerics, Phase 11). The DM formula and correlation sampling were read directly (observations in Cards 8/11). Their classification stays INFERRED per §12 (U5). Still open: optimiser internals (`sysquant/optimisation/*`), pooled forecast correlation, and the correlation `cleaning` path (Phases 6/11/14).
- G2: **CLOSED in Phase 7** (`calc_portfolio_risk_series` and `seriesOfStdevEstimates.shocked()` read, report §8.3 O7/O9). Previously PARTLY CLOSED: The overlay formula and default-off wiring are VERIFIED. `calc_portfolio_risk_series` and `seriesOfStdevEstimates.shocked()` are not read.
- G3: **CLOSED in Phase 7** (`pandl_SR_cost.py` read, report §8.3 O10). Previously PARTLY CLOSED: Cash-cost model and SR cost per trade VERIFIED. `pandl_SR_cost.py` not read (Phase 12).
- G6: **D01 addressed in Phase 10** (report §11.11; CSV D01 impl_evidence UNVERIFIED → VERIFIED, logged §11.13). Still UNVERIFIED: shipped historical CSV construction, live roll-status (R2) trigger internals, Parquet/Mongo paths. Earlier: **P09 core read in Phase 11** (report §12.4; CSV P09 impl_evidence → VERIFIED, logged §13.9); remaining P09 files are PARTIALLY AUDITED — RESOURCE PRIORITY. D01 is still UNVERIFIED. History: **P07 closed in Phase 7** (code read; CSV impl_evidence UNVERIFIED → VERIFIED, logged in report §8.6). D01 data/roll construction and P09 dynamic optimisation remain UNVERIFIED (P09's greedy integer search and speed control were confirmed to exist in Phase 6; still PARTIALLY AUDITED).
- G7: **CLOSED in Phase 11** (report §12.3; UD3). The only call site feeds the dynamic-optimised live strategy's maximum positions. History: (Phase 6) `positionLimit.minimum_position_limit` returns a bool when `self.no_limit` (`position_limits.py:21-28`); call-site effect still UNVERIFIED. **Phase 7:** the correlation `cleaning` path was read (report §8.3 O8): it fills from the same matrix's average or 0.99, with must-haves from `[fit_start:fit_end]`. No use of data after `fit_end` was observed; R03/R07 stay INFERRED (U5).
- G8 (Phase 7): production scheduling (`syscontrol`) of `run_systems` vs `run_strategy_order_generator`, and any age/staleness check on stored optimal positions, is UNVERIFIED. Searched `sysexecution/`, `sysproduction/strategy_code/`, `run_strategy_order_generator.py`, `sysproduction/data/optimal_positions.py` for `stale|too old|max_age|days_old`; "stale" there means config-listed instruments or strategies only.
- G4: Production and execution (sysexecution, sysbrokers, sysproduction) were mapped only at the entry-point level (Phase 19 optional). **Phase 8:** §9.5 L1–L5 traced the production flow down to broker-order creation. Stacks, algos and IB internals (E05) are still UNVERIFIED.
- G10 (Phase 12): the market-impact and cost-curve absences rest on name-based repo searches (report §13.2), so they are UNVERIFIED beyond the searched terms. Automatic feedback from live commission reports into configured costs: not observed (limited search).
- G9 (Phase 8): no new gap was opened. The §9 edges touching E05, D01, P09 and G8 are marked in place and not filled. DISC-1/DISC-2 (§9.7) await the operator's decision on whether to correct §2, Card 12 and §8.1 Q17.
- G11 (Phase 9): the order-simulator effects (O-P9-1 gross P&L at bar prices, O-P9-2 limit-fill slippage flags) are INFERRED, not tested; whether the bundled csv data contains intraday rows for the hourly path was not checked (UNVERIFIED).
- G12 (Phase 14): the derivation (method and data period) of the shipped fixed parameters in `futuresconfig.yaml` is not stated in the repository (N9, UNVERIFIED); PF-8 (roll/back-adjustment) stays UNVERIFIED pending the Phase 10 decision.
- G5: The P&L fill-timing reading (`delayfill`) is static only (Phase 16 will trace it empirically).

- G11 (Phase 10): the effect size of availability-based roll dating (R1) on real data cannot be tested from shipped data (raw contract prices are not shipped): UNVERIFIED. User-written rules that consume adjusted-price *levels* are not covered by the PF-8(a) verdict.

## Empirical tests

| ID | Question | Script | Result | Status |
|---|---|---|---|---|
| EXP-01 | Does an exact-zero raw forecast propagate as zero, or as NaN that is then forward-filled? | `scaffolding/experiments/exp01_zero_forecast.py` (SOFR, csv sim data, fixed scalar 1, single rule weight 1, FDM 1) | Rule output 3505 zeros of 10440 rows. Raw forecast: 0 zeros, 3505 NaN. Capped: 3505 NaN. Combined forecast: 0 zeros, 0 NaN, unique values {10.0}. Subsystem position: 0 zeros, 10430 non-zero, 10 NaN (vol warm-up). **Exact zeros become NaN and are forward-filled, so the prior non-zero forecast is held.** | TESTED |
| EXP-02 | Does `base_system_cache` key `System.get_instrument_list` on its arguments? | `scaffolding/experiments/exp02_base_cache_args.py` | Same system: default call → [CORN,SOFR,US10]; later call with `force_to_passed_list=["SOFR"]` → [CORN,SOFR,US10] (cached). Fresh system → ["SOFR"]. One cache ref, keyed with no arguments. **Arguments are ignored in base-system cache keys.** | TESTED |
| EXP-03 | Can a rule return a Tx1 DataFrame, as the docs state? | inline: `pd.Series(<Tx1 DataFrame>)` under pandas 2.1.3 | `ValueError: The truth value of a DataFrame is ambiguous` at the `pd.Series(result)` coercion step. End-to-end failure through `Rules.get_raw_forecast` is INFERRED, not run. | TESTED (coercion step only) |

| EXP-04 | (Phase 14, PF-14) Does the daily resample label day *t*'s 23:00 price at 00:00 of day *t*, so that `reindex(ffill)` onto an hourly index exposes it to earlier hours of day *t*? | `scaffolding/experiments/exp04_daily_label_alignment.py` (synthetic 9-row series; repo's own `resample_prices_to_business_day_index` and `get_intraday_pdf_at_frequency`); output `exp04_output.txt` | Daily labels 00:00 hold 109/209/309 (the 23:00 values); hourly bars at 10:00/15:00 see 109/209/309 while hourly prices are 101/102, 201/202, 301/302. **Mechanism holds.** `audit/repo` stayed clean | TESTED |
| EXP-05 | Does a later roll change earlier Panama-adjusted values and differences? | `scaffolding/experiments/exp05_panama_mutation.py` (synthetic 12-day multiple prices, framework stitcher; history before vs after a second roll) | Every earlier level shifted by the constant 8 (= day-10 FORWARD − PRICE). All earlier one-day differences unchanged. The roll-day difference = the new contract's own move. | TESTED (mechanism, synthetic) |
| EXP-06 | (Phase 15, PF-2, **default**) Does removing post-C data change forecasts, positions, gross, costs or net P&L at dates ≤ C? | `scaffolding/experiments/exp06_pf2_cost_deflator.py`; output `exp06_output.txt` (chapter-15 system, shipped CSVs, C ∈ {2016-12-30, 2019-12-31}; 2009-12-31 pre-declared but could not run: EUROSTX has no data then; control `vol_normalise_currency_costs=False`) | Forecasts, positions, gross: 0 differing rows. Costs: one constant factor per instrument (0.66–1.98). Portfolio costs ≤ C: ratio 0.9961 (2016), 0.9326 (2019); net SR 0.4911/0.4911, 0.4856/0.4843. Control: 0 differences. **L4 only (costs, net P&L).** | TESTED |
| EXP-07 | (PF-1, non-default scalar estimation) Which rows get the backfilled scalar, and what changes? | `exp07_pf1_scalar_backfill.py`; `exp07_output.txt` (backfill True vs False; control truncation 2019-12-31) | CORN only, 509 rows 1972-10-18…1974-09-30. Forecasts on 499 rows, positions on 502; on the differing rows gross is 419,295 vs −2,187.50. Full-sample net SR 0.4919 vs 0.4146. Control: 0 position differences; the only scalar difference is on the boundary row (~1e-8). **L1–L4, warm-up only.** | TESTED |
| EXP-08 | (PF-3/PF-4, PF-11, non-default forecast-weight estimation) Grid-aligned truncation (C_A 2017-03-31), with and without optimiser costs; grid-moving truncation (2019-12-31) without costs | `exp08_pf3_pf4_pf11_forecast_weights.py`, `exp08_output.txt`; breakdown `exp08b_pf11_breakdown.py`, `exp08b_output.txt` (PF-2 off in all arms) | A (PF-3/PF-4): raw weights differ in 43/44 periods (max 0.16); positions differ (CORN 5,415 rows, max 5); net ≤ C +1.0%; net SR 0.5794 vs 0.5726. B (control): **0 differences everywhere**. C (PF-11): weights differ (to 0.2251 after 2000; 0.51 in 1975); positions differ (MXP max 7, CORN 64 in 1975, 4 after 2000); net SR 0.5617 vs 0.5484. **L1–L4.** | TESTED |
| EXP-09 | (O-P11-1, non-default) Effect of counting stacked pooled rows as years in the handcraft SR tilt | `exp09_op11_1_years_of_data.py`, `exp09_output.txt` (in-process patch in script only: data_length / pooled_length) | Last fit: 303.7 vs 50.6 years. Raw weights differ in 50/51 periods (max 0.245). Positions differ (CORN 4,366 rows, max 9). Net SR 0.5677 vs 0.5647. **L1–L4; not look-ahead.** | TESTED |
| EXP-10 | (PF-15, non-default P09) Do the bfilled per-contract values reach any P09 position or P&L? | `exp10_pf15_per_contract_bfill.py`, `exp10_output.txt` (P09 stage list on chapter-15 system + shipped CSVs; variant: bfilled rows × 2, in-process patch in script only; about 3 min per run) | Values changed on 2,573–10,801 pre-start rows (five instruments). Positions, gross, costs and net: **0 differing rows**. **L1 only.** | TESTED |
| EXP-11 | (O-P9-1/O-P9-2, non-default order simulator) Gross P&L at simulator prices vs at fill prices for hourly limit orders; cost by side | `exp11_op9_limit_fill_accounting.py`, `exp11_output.txt` (provided hourly example, `use_limit_orders=True`, shipped CSVs, US10) | 1,843 fills. Framework gross 31,515.62 USD (identity reproduced exactly); at fill prices −129,875.00; gap −161,390.62. All fills are adverse to the fill-row price. Buys: slippage flag 0/919, 1.67 USD/contract. Sells: 924/924, 9.67 USD/contract. **Not look-ahead.** | TESTED |

## Estimation flags (defaults in `sysdata/config/defaults.yaml` @ 8958c49)

use_forecast_scale_estimates: False (l.131) · use_forecast_div_mult_estimates: False (l.150) · use_forecast_weight_estimates: False (l.171) · use_instrument_div_mult_estimates: False (l.236) · use_instrument_weight_estimates: False (l.256) · use_SR_costs: False (l.300) · buffer_method: forecast (l.296) · capital_multiplier func: syscore.capital.fixed_capital (l.226) · production_capital_method: 'full' (l.74) · vol_normalise_currency_costs: True (l.301). EXP-01/02 ran with all estimation OFF (fixed values).


**Phase 15 flags per experiment (ON / OFF; anything not listed = shipped chapter-15 config + defaults):**
- EXP-06: all estimation OFF. `vol_normalise_currency_costs` ON (baseline) / OFF (control). `use_SR_costs` OFF. Capital `fixed_capital`.
- EXP-07: `use_forecast_scale_estimates` ON (pooled, min_periods 500); `forecast_scalar_estimate.backfill` ON (baseline) / OFF (variant). Other estimation OFF. `vol_normalise_currency_costs` ON.
- EXP-08 / 08b: `use_forecast_weight_estimates` ON (handcraft, pooled gross, pooled turnover, expanding, weekly); `forecast_weight_estimate.cost_multiplier` 2.0 (arm A) / 0.0 (arms B, C). Other estimation OFF. `vol_normalise_currency_costs` OFF in every arm.
- EXP-09: `use_forecast_weight_estimates` ON (defaults, cost_multiplier 2.0). Other estimation OFF. `vol_normalise_currency_costs` ON.
- EXP-10: all estimation OFF. P09 ON (dynamic optimisation stages; `small_system` defaults). `vol_normalise_currency_costs` ON.
- EXP-11: all estimation OFF (the example's fixed values). Order simulator ON (hourly limit orders). `buffer_method: none` (example config). `vol_normalise_currency_costs` ON.
## Scratch modifications

- `audit/repo`: editable install (`pip install -e`). Build metadata and a few `__pycache__` directories were created inside the scratch clone during setup and imports; `git status` in the clone remains clean (they are ignored by the repo's `.gitignore`). No source file was modified.
- No user-owned checkout was touched. The fork checkout at `/home/user/pysystemtrade` is modified only under `audit/`.

## Important findings (P0 so far)

See report §3–§5, §8 and the Executive Summary. Key items: F1 zero→NaN→ffill (EXP-01); F2 base-cache argument blindness (EXP-02); F3 cache keys exclude config/data (DOCUMENTED + VERIFIED); F4 the forecast scalar backfills its first estimate (`backfill=True` default, comment "SLIGHTLY CHEATING"); F5 production hard-codes trade-to-edge; F6 docs "Tx1 dataframe" vs `pd.Series` coercion (EXP-03). **Phase 5:** F7 cost vol deflator and SR cost per trade are anchored to the end of the sample (pre-flag for Phase 14); F8 risk overlay is OFF by default and not documented in `docs/`; F9 the speed limit uses a full-sample turnover and is effectively OFF by default; F10 DV7 (documented default vol function and floor differ from the configured default), DV8/DV9 (config-key names). **Phase 6:** F11 DV10 (docs "five" optimisation methods vs four registered; bootstrap not implemented); F12 handcrafting = fixed binary clustering with a 0.5/0.5 split × sub-portfolio DM and an SR tilt that depends on years of data; F13 pooled estimators stack instruments with microsecond offsets, and the code warns this is unsuitable for high-frequency data; F14 FDM correlations use weekly forecast *levels*, the IDM uses weekly subsystem *returns*; F15 integer handling uses round (backtest/live buffers) vs floor (overrides); F16 overrides, position limits and trade limits exist only in production, downstream of the System. **Phase 7 (report §8):**
- F17: every default estimator is exponential and ignores `fit_start`, so `rolling`/`rollyears` has no effect there. `rollyears` counts periods (O1).
- F18: the fit-period grid is anchored to the sample end, so historic periods shift when data is added (O2/PF-11).
- F19: inclusive `[fit_start:fit_end]` slices (cleaning, non-exponential estimators) vs strict `<` in the exponential path (O3/PF-5).
- F20: positions use the unshifted capital multiplier while account capital is `shift(1)` (O4/PF-6).
- F21: the backtest capital default is `fixed` while the production default is `full` (O5).
- F22: `ewm(n)` in the carry and turnover code means com, not span (O6).
- F23: the forecast-scalar backfill **is** documented (`backtesting.md:2451`), which corrects §7.3 and Card 4 (O11).
- F24: production re-estimates all history every run, stores notional edges stamped `now()`, and no age check on them was observed (O12/PF-9/PF-10).

**Phase 8 (report §9):**
- F25: the spec §38 chain is corrected in §9.2. Vol feeds both the rules and sizing; zeros → NaN; FDM → combined cap or mapping (mapping *replaces* the cap, P8-O4); the risk overlay comes after the IDM; buffering is split across the portfolio stage (edges) and accounts or live order generation (path); costs sit only in accounts; the capital multiplier applies to backtest positions only.
- F26: the research feedback loops F1–F5 have no circular dependency (INFERRED). Forecast weights use SR costs only; instrument weights and the IDM use cash-cost subsystem P&L, including the end-anchored deflator PF-2 (P8-O2).
- F27: subsystem-level buffers (no weight or IDM) drive the research P&L for R06/R07, while portfolio-level buffers drive instrument P&L (P8-O1).
- F28: the sizing risk unit is price-unit vol × point value; the raw-price denominator cancels (P8-O3, INFERRED).
- F29: DV11/DV12 (doc wiring and example method names). DISC-1/DISC-2 raise earlier-section statements about "the only loop" for the operator (**corrected in session 5**).

**Phases 11–12 (report §12–§13):**
- F30: the Markowitz core is max-SR SLSQP (long-only, weights sum to 1, tol 1e-5). Vol/SR equalisation leaves only correlation to drive the weights when both are on.
- F31: handcraft applies the parametric SR tilt (hard-coded avg SR 0.5, std 0.15, CDF points 0.2–0.8) only at the top level. Its `years_of_data` counts stacked pooled rows (O-P11-1, effect INFERRED).
- F32: G7 is closed. `minimum_position_limit` → `False` reaches the dynamic-optimised live strategy only (UD3).
- F33: P09 is a per-date greedy integer optimiser (TE + shadow cost, TE buffer), a sequential path-dependent loop, with end-anchored cost inputs (PF-13 candidate).
- F34: cost = linear spread + max(commissions) (UD4); no market-impact or cost-curve model found (search recorded; absence UNVERIFIED beyond the terms); roll pseudo-fills × 0.5; buffer width not cost-dependent. In the default configuration costs affect P&L only.
- F35: research/live cost consistency. The backtest uses one configured spread per instrument for all history (× deflator); live reports sampled and realised spreads and allows interactive update. DV13 (the documented `Slippage` column is absent).
- F36: §13.6 lists the assumptions that may change materially for intraday trading (identified only).
- The SR-cost P&L is a smooth charge on the average position, built from full-sample turnover × end-anchored SR cost (O10).

**Phase 9 (report §10):**
- F37: the engine is vectorised, whole-history, daily-bar, lazy and memoised; there is no clock or event loop. Fills are inferred from position changes at one price per row; gross P&L = `positions.shift(1) × Δprice` after the `delayfill` shift; reporting sums into BDay bins. No cash, margin or financing state (absence UNVERIFIED beyond the searched terms).
- F38: an undocumented alternative accounts stage (the order simulator, UD5) runs a per-row order/fill loop (market or hourly limit orders), bypasses buffering, and computes gross P&L against bar prices rather than fill prices (O-P9-1, INFERRED effect). Not inventoried (41 rows kept); DISC-3 raised.
- F39: in hourly configurations, daily series labelled 00:00 of day *t* (holding day-*t* closing data) are ffilled onto that day's hourly bars (PF-14 candidate, classified in §15).

**Phase 14 (report §15):**
- F40: default classic backtest: no post-T input to the *position* was identified (NO ISSUE IDENTIFIED, static, not verified causal); the end-anchored cost deflator makes backtest *costs / net P&L* use the last sample date (PF-2, CONFIRMED ISSUE, default ON). Shipped fixed-parameter provenance (N9) and roll/back-adjustment (PF-8) are UNVERIFIED.
- F41: with estimation on, post-T inputs reach positions (PF-1 backfill, PF-3/PF-4 end-of-sample SR cost × full-sample turnover, PF-2 via instrument weights/IDM, `in_sample` date method N7: CONFIRMED ISSUE, conditional; PF-11 grid placement: POSSIBLE ISSUE).
- F42: non-default paths: compounding carries PF-2 (PF-6), shocked-vol backfill (PF-7), P09 final-price costs (PF-13), hourly daily→hourly ffill (PF-14, TESTED by EXP-04): CONFIRMED ISSUE, conditional; per-contract value bfill (PF-15): POSSIBLE ISSUE. Live decisions at T: NO ISSUE IDENTIFIED (end anchors equal today).

**Phase 13 (report §14):**
- F43: configuration is layered YAML (backtest config or list, with `base_config`) > `private_config.yaml` (outside the repo, `PYSYS_PRIVATE_CONFIG_DIR`) > `defaults.yaml`, merged recursively; `None` cannot override a default (O-P13-3); functions are named by dotted strings. No config/code versioning, content hash or git stamp was found (absence UNVERIFIED beyond the searched terms); production saves a pickled state plus the merged config per run (30-day retention).
- F44: estimated parameters exist only in the cache unless exported; the export writes last values (O-P13-1), which the docs suggest merging into simulated configs. Comparison tools: account curves, `t_test`, `account_t_test` (DV14: documented import path wrong). No experiment registry or multiple-testing control found.

**Phase 15 (report §16):**
- F45: PF-2 is TESTED at L4 only in the default system: costs and net P&L change; forecasts, positions and gross do not. That also supports the default-position NO ISSUE IDENTIFIED answer at two cutoffs. PF-1 and PF-3/PF-4 are TESTED at L1–L4 (non-default). PF-11 moves from POSSIBLE to CONFIRMED ISSUE ONLY WHEN NON-DEFAULT OPTION ENABLED; its post-T input is the sample end date only, since the grid-aligned control has zero differences. PF-15 moves from POSSIBLE to NO ISSUE IDENTIFIED for positions and P&L (L1 only).
- F46: O-P11-1 changes weights, positions and P&L (303.7 vs 50.6 years at the last fit) and is not look-ahead. O-P9-1: for the provided hourly limit-order example on US10, the framework's gross is +31,516 USD against −129,875 at fill prices. O-P9-2: only sells pay slippage.

## Optional-phase status

Phase 10: COMPLETE (session 7; this line said ON HOLD until session 8, and was corrected here as a stale status). Phase 15: **COMPLETE** (session 8, operator-authorised; report §16; EXP-06…EXP-11). Earlier EXP-01…05 are contract, caching and mechanism checks, not Phase 15 tests. Phase 19: not started.

## Operator-reported usage / cost

- P0 through the Phase 4 gate: **NOT RECORDED.** The operator's message contained the literal placeholder "[INSERT ACTUAL USAGE/COST HERE]"; the operator should supply the actual figure.
- Phase 5 (session 2): not recorded (operator to supply).
- Phase 6 (session 2): not recorded (operator to supply).
- Phase 7 (session 3): **UNRECORDED**. Claude Code cannot see account-level usage and has not estimated it; the operator will supply the figure. Budget plan (spec §18): P0 35%, P1A 40%, P1B 15%, reserve 10%.
- Phase 8 (session 4): **UNRECORDED** (not estimated).
- Phase 11-12 (session 5): **UNRECORDED**
- Phases 9/14/13 (session 6): **UNRECORDED** (the operator separately cited ≈ $8.56 for that session in the session 7 instructions, as an approximate platform figure; it is recorded here as quoted, not derived)
- Phase 10 (session 7): **UNRECORDED**
- Phase 15 (session 8): **UNRECORDED** (not estimated)
- Operator-reported REMAINING Claude Code credit balance at session 5 start: $66 (reported by the operator in the session 5 instructions). This is a remaining balance, NOT a consumed-cost figure and NOT audit usage/cost; no consumed figure is derived from it.
- Operator-reported REMAINING Claude Code credit balance: $81 (reported in session 2, 2026-09-24). This is a remaining balance, NOT a consumed-cost figure and NOT audit usage/cost. Consumed usage/cost for Phases 1–6 remains UNRECORDED (no reliable figure available; not to be estimated).

## Session log

- Session 8 (Phase 15, operator-authorised; Phase 15 only). Start checks passed: branch head `3f65eef`, clean; clone `8958c49` clean; 134/134 checks; the existing venv was reused, with no setup attempt consumed. Ran EXP-06…EXP-11 plus the EXP-08b breakdown in scratch. Truncated CSV copies are under `scaffolding/home/p15data/` (git-ignored). Two variants use in-process patches inside the scripts only (EXP-09, EXP-10); no repository file was modified. Report §16 written; §15 not edited (supersessions in §16.10). Executive Summary bullets 11, 17, 18 and 20 and the status line updated. CSV: `last_phase` → 15 on E02, R01, R05, R08, R09, P09; nothing else. The stale "Phase 10: ON HOLD" optional-phase line was corrected. `check_consistency.py` updated for Phase 15. **STOPPED BEFORE PHASE 16.**
- Session 7 (Phase 10, in the original container): operator approved Phase 10 after seeing the session-6 spend. Start checks passed (branch head `1df7ece`; clone `8958c49` clean, before and after; 127/127 checks before work; the existing venv was reused, no setup attempt consumed). Phase 10 completed (report §11). EXP-05 run (synthetic). CSV: D01 impl_evidence → VERIFIED; `last_phase` → 10 on C05, D01. PF-8 superseded (§11.10); D01 resolved (§11.11). **P1A STOP.**

- Session 1 (2026-09-24): Phases 1–4; commit `bae290c`. The first push was blocked until the Claude GitHub App was installed on the fork, then succeeded.
- Session 3 (2026-09-24): fresh session. Scratch clone recreated and pinned (`8958c49` verified before and after). Venv recreated in setup attempt 1 of 2 (recorded command, succeeded; Python 3.11.15, pandas 2.1.3, numpy 1.26.4). Phase 7 completed (report §8). CSV: P07 impl_evidence UNVERIFIED → VERIFIED; `last_phase` → 7 on 26 rows. Report-text corrections to §7.3 and Card 4 (backfill documented). `check_consistency.py` expectations updated for Phase 7. No experiments were run; one pandas signature check. Stopped before Phase 8.
- Post-session-5 (operator): Phases 11–12 approved (commit `742c541`), including both check updates and the P09 reclassification. Next: Phase 9, then 14, then 13, in a fresh session (§27). The Phase 10 decision is held until actual spend from 9/14/13 is known.
- Session 5: operator approved Phases 7–8 and accepted DISC-1/DISC-2. Start checks passed (branch head `4d3e97f`; clone `8958c49` clean, before and after; spec and CLAUDE.md byte-identical to the operator originals; the existing venv was reused with no setup attempt consumed; 89/89 checks before work). Phases 11 and 12 completed (report §12–§13). DISC text corrections in §2, Card 12, §8.1 Q17 (logged §13.9). CSV: P09 fields (logged); `last_phase` → 11/12. DV13, UD3, UD4 added; PF-13 candidate. `check_consistency.py` updated. **Intermediate stop (operator-chosen), not the P1A stop.**
- Session 4 (2026-09-24): fresh-session start procedure followed (branch head `a3efc5d` with `d5f094f` in history verified). The scratch clone at `audit/repo` and the venv were already present in this container; both were verified rather than recreated (`8958c49` and a clean tree, before and after; `import systems.basesystem` OK; no setup attempt consumed). Phase 8 completed (report §9). CSV: `last_phase` → 8 on 35 rows; no other field changed. DV11/DV12 added. DISC-1/DISC-2 raised. `check_consistency.py` updated for P0 end. **P0 STOP.**
- Session 2: Phase 4 approved; spec files added; Phase 5 completed; persistence check (26-ID count, Card 6); U5 revert; Phase 5 approved; Phase 6 completed and approved (E06 kept). SHA re-verified `8958c49`. Phase 7 handed to a fresh session.

- Session 6 (2026-09-24): fresh session. Start checks passed (branch head `2a588ab`; 101/101 consistency checks before any change). Scratch clone and venv recreated in setup attempt 1 of 2 (clone `8958c49`, clean). Phase 9 completed (report §10; commit recorded in the next log line). CSV: `last_phase` → 9 on C01, C02, C03, C05, E01; nothing else. UD5, PF-14 candidate and DISC-3 added. Phase 9 commit `820e157`. Phase 14 completed (report §15): PF-1…PF-15 and N1–N14 classified; EXP-04 run (synthetic, scratch-only, TESTED). CSV: `last_phase` → 14 on 26 rows (logged §15.7); nothing else. Phase 14 commit `fc7be98`. Phase 13 completed (report §14, targeted); CSV `last_phase` → 13 on C04, C05; DV14 added. Executive Summary merged (still 20 bullets), status line and next task updated. `audit/repo` verified at `8958c49`, clean, before and after. **Stopped for the operator's Phase 10 decision** (not the P1A stop).

## Safety log

No live trades, broker connections, production databases, or credentials were used. The only network access was `git clone` / `git ls-remote` of the public repo and PyPI installs.
