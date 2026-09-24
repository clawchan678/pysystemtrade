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
