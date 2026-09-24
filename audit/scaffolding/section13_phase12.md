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
