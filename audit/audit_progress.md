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
| P0 Phases 6–8 | NOT STARTED |
| P1A, P1B, P2 | NOT STARTED |

**Current phase:** P0 — Phase 5 complete; Phase 6 next.

**Exact next task:** Begin **Phase 6 — pysystemtrade-specific framework concepts** (spec §36), writing report §7. For each concept record existence, location, function, documented vs implemented behaviour, assumptions, evidence and tier: (1) handcrafted vs optimised weights: read `sysquant/optimisation/{generic_optimiser,portfolio_optimiser,full_handcrafting,optimise_over_time}.py` (closes the R05/R06 part of G1); (2) pooling across instruments (forecast scalar, forecast correlations `sysquant/estimators/pooled_correlation.py`, costs/turnover, gross returns); (3) forecast scalar/target/cap (cite Cards 4–5); (4) FDM; (5) IDM (cite Cards 8/10); (6) vol and long-run blending (Card 7, DV7); (7) cost-based speed limits (Card 14); (8) buffering (Card 12); (9) integer/lumpy position handling (rounding in `apply_buffer`, `roundpositions`, production `round()`, `dynamic_small_system_optimise`); (10) production overrides and limits (search `sysproduction/data` and `sysobjects/production` for override and position-limit code). Then Phase 7 (report §8, state/estimation table) and Phase 8 (report §9, dependency flow), then the **P0 STOP** (spec §38/§53).

## Unresolved issues

- U1: RESOLVED (session 2). Spec files added to `audit/` on operator instruction (provenance note 2).
- U2: OPEN. The operator's approval message contained the literal placeholder "[INSERT ACTUAL USAGE/COST HERE]" and no figure. Usage/cost through the Phase 4 gate is therefore still **not recorded**. Claude Code cannot see account-level cost and will not estimate it.
- U3: RESOLVED (operator decision, session 2). A08 FDM application = ALPHA; R04 FDM estimation = RESEARCH. P06 buffered position = PORTFOLIO_RISK, with the caveat that the code lives in `systems/accounts/*`. E01 backtest P&L = EXECUTION, qualified as *simulated* execution, distinct from live order generation and broker execution (E03–E05). Caveats preserved in report §6.1 and Cards 8/12/16.
- U4: `systems/provided/dynamic_small_system_optimise` (an alternative portfolio construction path) has been classified only. It is PARTIALLY AUDITED.

- U5: OPEN (operator decision). Spec §12 says "Never upgrade ... INFERRED → VERIFIED". Phase 5 changed `impl_evidence` for R04 and R07 from INFERRED to VERIFIED after reading their source directly (logged in report §6.5, not silent). If §12 is read literally as covering fresh direct inspection, these two should be reverted to INFERRED. P04/E02 moved from UNVERIFIED, which §12 does not prohibit. Left unchanged pending the operator's ruling.
- U6: RESOLVED (session 2 check). The Tier 1 ID count was misstated as 27 in the report and progress file; the correct count is 26 (26 + SC + 13 Tier 2 = 40). Card 6 stated A06 `swap_evidence` as INFERRED while the CSV holds TESTED (Phase 4, approved); the card text was aligned to the CSV, and no evidence value was changed.

## Evidence gaps

- G1: PARTLY CLOSED in Phase 5. The DM formula and correlation sampling are now VERIFIED. Still open: optimiser internals (`sysquant/optimisation/*`), pooled forecast correlation, and the correlation `cleaning` path (Phases 6/11/14).
- G2: PARTLY CLOSED. The overlay formula and default-off wiring are VERIFIED. `calc_portfolio_risk_series` and `seriesOfStdevEstimates.shocked()` are not read.
- G3: PARTLY CLOSED. Cash-cost model and SR cost per trade VERIFIED. `pandl_SR_cost.py` not read (Phase 12).
- G6 (new): D01 data/roll construction, P07 compounding capital variants and P09 dynamic optimisation remain UNVERIFIED.
- G4: Production and execution (sysexecution, sysbrokers, sysproduction) were mapped only at the entry-point level (Phase 19 optional).
- G5: The P&L fill-timing reading (`delayfill`) is static only (Phase 16 will trace it empirically).

## Empirical tests

| ID | Question | Script | Result | Status |
|---|---|---|---|---|
| EXP-01 | Does an exact-zero raw forecast propagate as zero, or as NaN that is then forward-filled? | `scaffolding/experiments/exp01_zero_forecast.py` (SOFR, csv sim data, fixed scalar 1, single rule weight 1, FDM 1) | Rule output 3505 zeros of 10440 rows. Raw forecast: 0 zeros, 3505 NaN. Capped: 3505 NaN. Combined forecast: 0 zeros, 0 NaN, unique values {10.0}. Subsystem position: 0 zeros, 10430 non-zero, 10 NaN (vol warm-up). **Exact zeros become NaN and are forward-filled, so the prior non-zero forecast is held.** | TESTED |
| EXP-02 | Does `base_system_cache` key `System.get_instrument_list` on its arguments? | `scaffolding/experiments/exp02_base_cache_args.py` | Same system: default call → [CORN,SOFR,US10]; later call with `force_to_passed_list=["SOFR"]` → [CORN,SOFR,US10] (cached). Fresh system → ["SOFR"]. One cache ref, keyed with no arguments. **Arguments are ignored in base-system cache keys.** | TESTED |
| EXP-03 | Can a rule return a Tx1 DataFrame, as the docs state? | inline: `pd.Series(<Tx1 DataFrame>)` under pandas 2.1.3 | `ValueError: The truth value of a DataFrame is ambiguous` at the `pd.Series(result)` coercion step. End-to-end failure through `Rules.get_raw_forecast` is INFERRED, not run. | TESTED (coercion step only) |

## Estimation flags (defaults in `sysdata/config/defaults.yaml` @ 8958c49)

use_forecast_scale_estimates: False (l.131) · use_forecast_div_mult_estimates: False (l.150) · use_forecast_weight_estimates: False (l.171) · use_instrument_div_mult_estimates: False (l.236) · use_instrument_weight_estimates: False (l.256) · use_SR_costs: False (l.300) · buffer_method: forecast (l.296). EXP-01/02 ran with all estimation OFF (fixed values).

## Scratch modifications

- `audit/repo`: editable install (`pip install -e`). Build metadata and a few `__pycache__` directories were created inside the scratch clone during setup and imports; `git status` in the clone remains clean (they are ignored by the repo's `.gitignore`). No source file was modified.
- No user-owned checkout was touched. The fork checkout at `/home/user/pysystemtrade` is modified only under `audit/`.

## Important findings (P0 so far)

See report §3–§5 and the Executive Summary. Key items: F1 zero→NaN→ffill (EXP-01); F2 base-cache argument blindness (EXP-02); F3 cache keys exclude config/data (DOCUMENTED + VERIFIED); F4 the forecast scalar backfills its first estimate (`backfill=True` default, comment "SLIGHTLY CHEATING"); F5 production hard-codes trade-to-edge; F6 docs "Tx1 dataframe" vs `pd.Series` coercion (EXP-03). **Phase 5:** F7 cost vol deflator and SR cost per trade are anchored to the end of the sample (pre-flag for Phase 14); F8 risk overlay is OFF by default and not documented in `docs/`; F9 the speed limit uses a full-sample turnover and is effectively OFF by default; F10 DV7 (documented default vol function and floor differ from the configured default), DV8/DV9 (config-key names).

## Optional-phase status

Phase 10: not started. Phase 15: not started (EXP-01/02 are Signal-Contract/Stage checks, not causality tests). Phase 19: not started.

## Operator-reported usage / cost

- P0 through the Phase 4 gate: **NOT RECORDED.** The operator's message contained the literal placeholder "[INSERT ACTUAL USAGE/COST HERE]"; the operator should supply the actual figure.
- Phase 5 (session 2): not recorded (operator to supply). Budget plan (spec §18): P0 35%, P1A 40%, P1B 15%, reserve 10%.

## Session log

- Session 1 (2026-09-24): Phases 1–4; commit `bae290c`. The first push was blocked until the Claude GitHub App was installed on the fork, then succeeded.
- Session 2: Phase 4 approved; spec files added; Phase 5 completed. SHA re-verified `8958c49`.

## Safety log

No live trades, broker connections, production databases, or credentials were used. The only network access was `git clone` / `git ls-remote` of the public repo and PyPI installs.
