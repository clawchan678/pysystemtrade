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
| `systems/accounts/tests/test_accounts.py` | 5 | 0 | **N** | **collection error**: `AttributeError: module 'datetime' has no attribute 'strptime'`; the class is also `@pytest.mark.skip` |
| `sysquant/estimators/tests/test_mean_estimator.py` | 1 | 1 | N | not in `testpaths` (never run by the configured suite) |
| `sysexecution/tests/test_trade_qty.py`, `syslogging/tests/logging_tests.py`, `sysdata/mongodb/tests/test_mongodb.py`, `sysproduction/tests/test_controls.py` | — | 3 / 12 / 1 / 0 | N | not in `testpaths`; the mongodb test needs a database (not run: safety) |

- **O-P18-1 (silent non-collection):** `@unittest.SkipTest` is an exception class, not a skip decorator. Used as a decorator it replaces the test with an exception instance, which pytest does not collect. **66 defined tests** in `testpaths` files are therefore neither run nor reported as skipped (sum of the "decorated" rows above) (the skip count above covers only the Windows and slow tests). VERIFIED (collection output vs `def test` counts).
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
