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
2. **The operator-supplied `PYSYSTEMTRADE_AUDIT_MASTER.md` and `CLAUDE.md` were NOT present on disk** at session start. The master specification was supplied in the session prompt. Per spec §7, Claude Code did not create the master spec. **Operator action required:** place `PYSYSTEMTRADE_AUDIT_MASTER.md` and `CLAUDE.md` in the workspace (or keep supplying the spec in the prompt) before the next session.
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
| P0 Phase 4 — Four-layer decomposition + Signal Contract + Case A/B | COMPLETE — **AWAITING OPERATOR REVIEW (hard gate, spec §34)** |
| P0 Phases 5–8 | NOT STARTED (blocked on Phase 4 approval) |
| P1A, P1B, P2 | NOT STARTED |

**Current phase:** Phase 4 review gate (STOPPED).

**Exact next task:** After the operator explicitly approves the Phase 4 output: begin **Phase 5 — Master Inventory**. Assign tiers to all 40 CSV rows (Tier 1 candidates are already listed in report §6). Write FULL COMPONENT CARDS (spec §29) for the Tier 1 components into report §6, in this order: C03 cache, C01/C02 System/Stage, A01/A02 rule interface, A04 scaling, A05 cap, A06 combination, R02 vol, A08/R04 FDM, P01 position sizing, P02/P03 instrument weights and IDM, R07 correlations, P05/P06 buffering, E02 costs, R11 speed limit, P04 risk overlay, E04 order generation. Before Phase 5, apply any corrections the operator requests to the §4/§5 classification.

## Unresolved issues

- U1: Master spec and CLAUDE.md are absent on disk (see provenance note 2).
- U2: Operator-reported usage/cost for P0 (Phases 1–4) is not yet recorded. Claude Code cannot see account-level cost.
- U3: Layer classification uncertainty. FDM is split into application (ALPHA pipeline position) and estimation (RESEARCH). Buffered-position simulation lives in the Accounts stage and is labelled PORTFOLIO_RISK. Backtest P&L/fill simulation is labelled EXECUTION (simulated). Operator to confirm.
- U4: `systems/provided/dynamic_small_system_optimise` (an alternative portfolio construction path) has been classified only. It is PARTIALLY AUDITED.

## Evidence gaps

- G1: Instrument-weight and IDM estimation internals (`sysquant/optimisation/*`, `sysquant/estimators/diversification_multipliers.py`, `correlation_over_time.py`) were classified from call sites and defaults only. They are not deep-read yet (Phase 6/7/11).
- G2: Risk overlay (`systems/risk_overlay.py`) was classified only.
- G3: Cost model internals (`pandl_cash_costs.py`, `pandl_SR_cost.py`, `sysobjects/instruments.py:instrumentCosts`) were classified only (Phase 12).
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

See report §3–§5 and the Executive Summary. Key items: F1 zero→NaN→ffill (EXP-01); F2 base-cache argument blindness (EXP-02); F3 cache keys exclude config/data (DOCUMENTED + VERIFIED); F4 the forecast scalar backfills its first estimate (`backfill=True` default, comment "SLIGHTLY CHEATING"); F5 production hard-codes trade-to-edge; F6 docs "Tx1 dataframe" vs `pd.Series` coercion (EXP-03).

## Optional-phase status

Phase 10: not started. Phase 15: not started (EXP-01/02 are Signal-Contract/Stage checks, not causality tests). Phase 19: not started.

## Operator-reported usage / cost

- P0 through the Phase 4 gate: **NOT YET REPORTED** (operator to fill in). Budget plan (spec §18): P0 35%, P1A 40%, P1B 15%, reserve 10%.

## Safety log

No live trades, broker connections, production databases, or credentials were used. The only network access was `git clone` / `git ls-remote` of the public repo and PyPI installs.
