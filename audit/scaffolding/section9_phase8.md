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

| # | Location | Statement | Finding | Evidence |
|---|---|---|---|---|
| DISC-1 | §2 "Engines" | "the only per-period loop is the buffer application" (labelled INFERRED) | Other per-period loops exist: `half_compounding` (a sequential capital loop, `syscore/capital.py:34-46`), the risk-series date loop (`portfolio_risk.py:30-58`, §8 O9), and per-fit-period loops in the optimiser and DM (`optimise_over_time.py:54-77`; `diversification_multipliers.py:44-60`) | VERIFIED (code) |
| DISC-2 | Card 12 "State"; §8.1 Q17 | P06 is "the only path-dependent loop" / "the only stateful loop in the backtest" | `half_compounding` is also a sequential, path-dependent loop (the multiplier is capped at 1.0 and depends on prior values). It is not the default (`fixed_capital`), and §8.1 Q18 itself describes it as a sequential loop, so §8 is internally inconsistent on this point | `syscore/capital.py:34-46` VERIFIED |

### 9.8 Experiments

NOT TESTED — REASON: every §9 edge was settled by static reading of the call sites cited (spec §22: static first). No end-to-end numerical flow trace was run. The empirical position → lag → fill → P&L trace belongs to Phase 16, and causal testing to Phase 15.

### 9.9 Phase 8 change log (explicit)

| Item | Change | Basis |
|---|---|---|
| CSV `last_phase` | → 8 for rows that appear as nodes in §9.3–§9.5: C05, D01, A01, A02, A04, A05, A06, A07, A08, R01–R11, P01–P08, E01–E06 | Traced in Phase 8 |
| CSV other fields | **unchanged** (including `alpha_specific`, `impl_evidence`; R03–R07 stay INFERRED; D01/P09/E05 stay UNVERIFIED; E06 unchanged) | U5; operator instructions |
| Divergence register | DV11, DV12 added (docs), see register | §9 reading of `docs/backtesting.md` |
| Earlier sections | not edited; DISC-1, DISC-2 raised for the operator | §9.7 |
