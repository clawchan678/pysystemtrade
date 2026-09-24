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
