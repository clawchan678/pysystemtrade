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
| P0 Phase 7 — State and estimation | COMPLETE (session 3; report §8: 20-quantity table, per-quantity assessment, O1–O12, PF-1…PF-12, change log §8.6) — awaiting operator review |
| P0 Phase 8 — Dependency / information flow | COMPLETE (session 4; report §9: corrected flow, spec-chain corrections, D1–D18, F1–F5, L1–L5, P8-O1…O5, DISC-1/2, DV11/DV12) |
| **P0 (Phases 1–8)** | **COMPLETE — P0 STOP** (Phase 7 and Phase 8 awaiting operator review) |
| P1A, P1B, P2 | NOT STARTED |

**Current phase:** P0 complete (P0 STOP, session 4). Next stage: **P1A**, not started; waiting for the operator to review Phases 7–8 and approve P1A.

**Exact next task:** After operator approval, begin **P1A — Core methodology** (spec §39). Work in the spec's priority order and write the matching report sections:
1. **Phase 11 — Forecast / weight / portfolio methodology** (report §12), HIGH PRIORITY. For forecast generation, scaling, caps, combination, FDM, position sizing, vol targeting, instrument weights, IDM, correlations and portfolio construction, record the formula, inputs, assumptions, estimation method, update frequency, rationale, documented vs implemented behaviour, and evidence. Trace forecast → risk → position, building on Cards 3–12 and §9. Open G1 remainder: per-method optimiser numerics (`sysquant/optimisation/shared.py`, `SR_adjustment.py`, shrinkage/one_period). U5 applies: R03–R07 stay INFERRED.
2. **Phase 12 — Cost / turnover / buffering / speed limits** (report §13), HIGH PRIORITY. Trace forecast/rule → desired position → turnover → transaction cost → portfolio decision. Cover commissions, spread, slippage, market impact, instrument cost data, cost influence, speed limits, buffering, turnover control and research/live consistency, building on Cards 12–14, §9 D8/D14–D18/F1–F4, and P8-O1/O2.
3. **Phase 9 — Simulation / backtest architecture** (report §10). Classify the architecture (vectorised, daily-bar, stateful loops per DISC-1/2).
4. **Phase 14 — Static causality / look-ahead** (report §15). Classify PF-1…PF-12 as NO ISSUE IDENTIFIED / POSSIBLE ISSUE / CONFIRMED ISSUE / UNVERIFIED.
5. Then Phase 13 (configuration, targeted) and Phase 10 (data/roll; the first phase to cut under budget pressure).

Then the **P1A STOP** (spec §39). Do not start P1B.

## Unresolved issues

- U1: RESOLVED (session 2). Spec files added to `audit/` on operator instruction (provenance note 2).
- U2: OPEN. The operator's approval message contained the literal placeholder "[INSERT ACTUAL USAGE/COST HERE]" and no figure. Usage/cost through the Phase 4 gate is therefore still **not recorded**. Claude Code cannot see account-level cost and will not estimate it.
- U3: RESOLVED (operator decision, session 2). A08 FDM application = ALPHA; R04 FDM estimation = RESEARCH. P06 buffered position = PORTFOLIO_RISK, with the caveat that the code lives in `systems/accounts/*`. E01 backtest P&L = EXECUTION, qualified as *simulated* execution, distinct from live order generation and broker execution (E03–E05). Caveats preserved in report §6.1 and Cards 8/12/16.
- U4: `systems/provided/dynamic_small_system_optimise` (an alternative portfolio construction path) has been classified only. It is PARTIALLY AUDITED.

- U5: **RESOLVED** (operator ruling, session 2). §12 is applied literally: direct source inspection does not justify an INFERRED → VERIFIED upgrade. R04 and R07 `impl_evidence` were reverted to **INFERRED** in the CSV, report cards 8 and 11, the §6.5 log, and the Executive Summary. The underlying observations and their provenance are kept. P04/E02 (UNVERIFIED → VERIFIED) are unaffected.
- U7: RESOLVED (operator decision, session 2). The E06_PROD_OVERRIDES_LIMITS row stays in the inventory as Tier 2 / VERIFIED (41 rows). It changes only if the audit itself establishes a reason.
- U6: RESOLVED (session 2 check). The Tier 1 ID count was misstated as 27 in the report and progress file; the correct count is 26 (26 + SC + 13 Tier 2 = 40). Card 6 stated A06 `swap_evidence` as INFERRED while the CSV holds TESTED (Phase 4, approved); the card text was aligned to the CSV, and no evidence value was changed.

## Evidence gaps

- G1: PARTLY ADDRESSED in Phases 5 and 7 (Phase 7: cleaning path and `< fit_end` selection in the mean/stdev estimators read; remaining: per-method optimiser numerics, Phase 11). The DM formula and correlation sampling were read directly (observations in Cards 8/11). Their classification stays INFERRED per §12 (U5). Still open: optimiser internals (`sysquant/optimisation/*`), pooled forecast correlation, and the correlation `cleaning` path (Phases 6/11/14).
- G2: **CLOSED in Phase 7** (`calc_portfolio_risk_series` and `seriesOfStdevEstimates.shocked()` read, report §8.3 O7/O9). Previously PARTLY CLOSED: The overlay formula and default-off wiring are VERIFIED. `calc_portfolio_risk_series` and `seriesOfStdevEstimates.shocked()` are not read.
- G3: **CLOSED in Phase 7** (`pandl_SR_cost.py` read, report §8.3 O10). Previously PARTLY CLOSED: Cash-cost model and SR cost per trade VERIFIED. `pandl_SR_cost.py` not read (Phase 12).
- G6: **P07 closed in Phase 7** (code read; CSV impl_evidence UNVERIFIED → VERIFIED, logged in report §8.6). D01 data/roll construction and P09 dynamic optimisation remain UNVERIFIED (P09's greedy integer search and speed control were confirmed to exist in Phase 6; still PARTIALLY AUDITED).
- G7 (Phase 6): `positionLimit.minimum_position_limit` returns a bool when `self.no_limit` (`position_limits.py:21-28`); call-site effect still UNVERIFIED. **Phase 7:** the correlation `cleaning` path was read (report §8.3 O8): it fills from the same matrix's average or 0.99, with must-haves from `[fit_start:fit_end]`. No use of data after `fit_end` was observed; R03/R07 stay INFERRED (U5).
- G8 (Phase 7): production scheduling (`syscontrol`) of `run_systems` vs `run_strategy_order_generator`, and any age/staleness check on stored optimal positions, is UNVERIFIED. Searched `sysexecution/`, `sysproduction/strategy_code/`, `run_strategy_order_generator.py`, `sysproduction/data/optimal_positions.py` for `stale|too old|max_age|days_old`; "stale" there means config-listed instruments or strategies only.
- G4: Production and execution (sysexecution, sysbrokers, sysproduction) were mapped only at the entry-point level (Phase 19 optional). **Phase 8:** §9.5 L1–L5 traced the production flow down to broker-order creation. Stacks, algos and IB internals (E05) are still UNVERIFIED.
- G9 (Phase 8): no new gap was opened. The §9 edges touching E05, D01, P09 and G8 are marked in place and not filled. DISC-1/DISC-2 (§9.7) await the operator's decision on whether to correct §2, Card 12 and §8.1 Q17.
- G5: The P&L fill-timing reading (`delayfill`) is static only (Phase 16 will trace it empirically).

## Empirical tests

| ID | Question | Script | Result | Status |
|---|---|---|---|---|
| EXP-01 | Does an exact-zero raw forecast propagate as zero, or as NaN that is then forward-filled? | `scaffolding/experiments/exp01_zero_forecast.py` (SOFR, csv sim data, fixed scalar 1, single rule weight 1, FDM 1) | Rule output 3505 zeros of 10440 rows. Raw forecast: 0 zeros, 3505 NaN. Capped: 3505 NaN. Combined forecast: 0 zeros, 0 NaN, unique values {10.0}. Subsystem position: 0 zeros, 10430 non-zero, 10 NaN (vol warm-up). **Exact zeros become NaN and are forward-filled, so the prior non-zero forecast is held.** | TESTED |
| EXP-02 | Does `base_system_cache` key `System.get_instrument_list` on its arguments? | `scaffolding/experiments/exp02_base_cache_args.py` | Same system: default call → [CORN,SOFR,US10]; later call with `force_to_passed_list=["SOFR"]` → [CORN,SOFR,US10] (cached). Fresh system → ["SOFR"]. One cache ref, keyed with no arguments. **Arguments are ignored in base-system cache keys.** | TESTED |
| EXP-03 | Can a rule return a Tx1 DataFrame, as the docs state? | inline: `pd.Series(<Tx1 DataFrame>)` under pandas 2.1.3 | `ValueError: The truth value of a DataFrame is ambiguous` at the `pd.Series(result)` coercion step. End-to-end failure through `Rules.get_raw_forecast` is INFERRED, not run. | TESTED (coercion step only) |

## Estimation flags (defaults in `sysdata/config/defaults.yaml` @ 8958c49)

use_forecast_scale_estimates: False (l.131) · use_forecast_div_mult_estimates: False (l.150) · use_forecast_weight_estimates: False (l.171) · use_instrument_div_mult_estimates: False (l.236) · use_instrument_weight_estimates: False (l.256) · use_SR_costs: False (l.300) · buffer_method: forecast (l.296) · capital_multiplier func: syscore.capital.fixed_capital (l.226) · production_capital_method: 'full' (l.74) · vol_normalise_currency_costs: True (l.301). EXP-01/02 ran with all estimation OFF (fixed values).

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
- F29: DV11/DV12 (doc wiring and example method names). DISC-1/DISC-2 raise earlier-section statements about "the only loop" for the operator.
- The SR-cost P&L is a smooth charge on the average position, built from full-sample turnover × end-anchored SR cost (O10).

## Optional-phase status

Phase 10: not started. Phase 15: not started (Phases 7–8 ran no experiments; the Phase 8 flow trace was NOT TESTED because static reading was sufficient, §9.8) (EXP-01/02 are Signal-Contract/Stage checks, not causality tests). Phase 19: not started.

## Operator-reported usage / cost

- P0 through the Phase 4 gate: **NOT RECORDED.** The operator's message contained the literal placeholder "[INSERT ACTUAL USAGE/COST HERE]"; the operator should supply the actual figure.
- Phase 5 (session 2): not recorded (operator to supply).
- Phase 6 (session 2): not recorded (operator to supply).
- Phase 7 (session 3): **UNRECORDED**. Claude Code cannot see account-level usage and has not estimated it; the operator will supply the figure. Budget plan (spec §18): P0 35%, P1A 40%, P1B 15%, reserve 10%.
- Phase 8 (session 4): **UNRECORDED** (not estimated).
- Operator-reported REMAINING Claude Code credit balance: $81 (reported in session 2, 2026-09-24). This is a remaining balance, NOT a consumed-cost figure and NOT audit usage/cost. Consumed usage/cost for Phases 1–6 remains UNRECORDED (no reliable figure available; not to be estimated).

## Session log

- Session 1 (2026-09-24): Phases 1–4; commit `bae290c`. The first push was blocked until the Claude GitHub App was installed on the fork, then succeeded.
- Session 3 (2026-09-24): fresh session. Scratch clone recreated and pinned (`8958c49` verified before and after). Venv recreated in setup attempt 1 of 2 (recorded command, succeeded; Python 3.11.15, pandas 2.1.3, numpy 1.26.4). Phase 7 completed (report §8). CSV: P07 impl_evidence UNVERIFIED → VERIFIED; `last_phase` → 7 on 26 rows. Report-text corrections to §7.3 and Card 4 (backfill documented). `check_consistency.py` expectations updated for Phase 7. No experiments were run; one pandas signature check. Stopped before Phase 8.
- Session 4 (2026-09-24): fresh-session start procedure followed (branch head `a3efc5d` with `d5f094f` in history verified). The scratch clone at `audit/repo` and the venv were already present in this container; both were verified rather than recreated (`8958c49` and a clean tree, before and after; `import systems.basesystem` OK; no setup attempt consumed). Phase 8 completed (report §9). CSV: `last_phase` → 8 on 35 rows; no other field changed. DV11/DV12 added. DISC-1/DISC-2 raised. `check_consistency.py` updated for P0 end. **P0 STOP.**
- Session 2: Phase 4 approved; spec files added; Phase 5 completed; persistence check (26-ID count, Card 6); U5 revert; Phase 5 approved; Phase 6 completed and approved (E06 kept). SHA re-verified `8958c49`. Phase 7 handed to a fresh session.

## Safety log

No live trades, broker connections, production databases, or credentials were used. The only network access was `git clone` / `git ls-remote` of the public repo and PyPI installs.
