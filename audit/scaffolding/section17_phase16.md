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
- **O-P16-3:** the position decided on the final row is never filled in the backtest. The last P&L row belongs to a position decided two rows earlier.

### 17.6 Limits

- Three dates on one instrument in the default daily configuration. Hourly systems (PF-14), the order simulator (§10.4, EXP-11), compounding (PF-6) and P09 were not traced.
- The warm-up boundary (first valid position) was not traced; the most recent date was chosen as the boundary.

### 17.7 Phase 16 change log (explicit)

- Report: this section (§17) written. Status line and Executive Summary bullet 12 updated (sentence added; bullet count unchanged).
- CSV: `last_phase` → 16 on the four rows traced: E01_BACKTEST_PANDL (fill/P&L identity), P06_BUFFERED_POSITION_SIM (position path), E02_COST_MODEL (roll pseudo-fill dates), D01_PRICE_ROLL_DATA (roll-day adjusted price). No evidence value changed; no row added.
- Progress file: phase table, next task, empirical tests (EXP-12, EXP-12b), session log, usage line.
