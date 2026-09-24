# EXP-12 (Phase 16). Position / lag / P&L timing trace. Scratch only; no repository change.
# System: shipped default chapter-15 system (futures_system(), futuresconfig.yaml, all estimation
#   OFF, delayfill=True, cash costs, fixed capital) on the shipped CSVs. Instrument: US10.
# Date-selection rules, stated BEFORE running (lesson L-P15-1):
#   ORDINARY: the first business day in 2023 on which the rounded buffered position changes and
#             which is at least 5 business days away from any PRICE_CONTRACT change.
#   ROLL:     the first business day in 2023 on which the daily PRICE_CONTRACT changes.
#   BOUNDARY: the last available date (most recent row of the daily price series).
#   Fallback (not needed if the above exist): the same rules applied to 2022.
# For each decision date t: raw rows of day t, daily label/value, forecast, position, the
#   delayed position used by the P&L, the inferred fill (date, price), and the P&L rows t+1, t+2,
#   checked against the identity pnl(r) = pos_used(r-1) * (P(r) - P(r-1)) * value_per_point * fx(r).
import pandas as pd, numpy as np
from p15_common import build_system

INS = "US10"
s = build_system()
raw = s.data.get_raw_price(INS)
P = s.rawdata.get_daily_prices(INS)
mult = s.data.get_multiple_prices(INS)
pc_daily = mult.PRICE_CONTRACT.groupby(mult.index.normalize()).last()
fc = s.combForecast.get_combined_forecast(INS)
notional = s.portfolio.get_notional_position(INS)
buf = s.accounts.get_buffered_position(INS, roundpositions=True)
acc = s.accounts.pandl_for_instrument(INS)
calc = acc.pandl_calculator_with_costs
pos_used = calc.positions
price = calc.price
vpp = calc.value_per_point
fx = calc.fx.reindex(price.index).ffill()
gross = calc.pandl_in_base_currency() if hasattr(calc, "pandl_in_base_currency") else None
fills = [f for f in calc.fills if f.qty != 0]
fills_by_date = {pd.Timestamp(f.date): f for f in fills}
idx = P.index

roll_days = pc_daily.index[pc_daily.ne(pc_daily.shift(1)) & pc_daily.shift(1).notna()]


def near_roll(d, n=5):
    i = idx.get_indexer([d])[0]
    lo, hi = idx[max(i - n, 0)], idx[min(i + n, len(idx) - 1)]
    return any((r >= lo) and (r <= hi) for r in roll_days)


def pick(year):
    yr = buf[(buf.index.year == year)]
    changes = yr.index[yr.diff().fillna(0) != 0]
    ordinary = next((d for d in changes if not near_roll(d)), None)
    roll = next((d for d in roll_days if d.year == year), None)
    return ordinary, roll


ordinary, roll = pick(2023)
if ordinary is None or roll is None:
    ordinary, roll = pick(2022)
boundary = idx[-1]
print(f"Selected (rule-based): ordinary={ordinary.date()} roll={roll.date()} boundary={boundary.date()}")
print(f"value_per_point={vpp}; fx(USD)={fx.iloc[-1]}; delayfill={calc.delayfill}; roundpositions={calc.roundpositions}")


def row(series, d):
    return series.get(d, np.nan)


def trace(name, t):
    print(f"\n=== {name}: decision date t = {t.date()} ===")
    day = raw[(raw.index >= t) & (raw.index < t + pd.Timedelta(days=1))]
    print(f"raw rows on calendar day t: {len(day)}; first {day.index[0] if len(day) else '-'}; "
          f"last {day.index[-1] if len(day) else '-'} = {day.iloc[-1] if len(day) else float('nan')}")
    print(f"daily price label {t} value {row(P, t)} (equals last raw value of day t: {len(day) and np.isclose(row(P, t), day.iloc[-1])})")
    i = idx.get_indexer([t])[0]
    nxt = [idx[k] for k in (i + 1, i + 2) if k < len(idx)]
    print(f"combined forecast at t: {row(fc, t):.4f} (t-1: {row(fc, idx[i-1]):.4f})")
    print(f"notional position at t: {row(notional, t):.4f}; buffered rounded position at t: {row(buf, t)} (t-1: {row(buf, idx[i-1])})")
    for d in [idx[i - 1], t] + nxt:
        f = fills_by_date.get(d)
        pr = row(price, d); pprev = row(price, idx[idx.get_indexer([d])[0] - 1])
        pu = row(pos_used, d); pu_prev = row(pos_used, idx[idx.get_indexer([d])[0] - 1])
        pnl_id = pu_prev * (pr - pprev) * vpp * row(fx, d)
        g = row(gross, d) if gross is not None else np.nan
        print(f"  row {d.date()}: price {pr:.6f} | pos_used {pu} | fill {'-' if f is None else f'{f.qty:+.0f} @ {f.price:.6f}'} "
              f"| gross P&L {g:.2f} | identity {pnl_id:.2f}")
    if not nxt:
        print("  no row after t: the position decided at t is never filled or held inside the sample")


trace("ORDINARY", ordinary)

print(f"\n=== ROLL: PRICE_CONTRACT change on {roll.date()} ===")
i = idx.get_indexer([roll])[0]
prev = idx[i - 1]
m_prev = mult[mult.index.normalize() == prev].iloc[-1]
m_roll = mult[mult.index.normalize() == roll].iloc[-1]
print(f"multiple prices {prev.date()}: PRICE {m_prev.PRICE} ({m_prev.PRICE_CONTRACT}), FORWARD {m_prev.FORWARD} ({m_prev.FORWARD_CONTRACT})")
print(f"multiple prices {roll.date()}: PRICE {m_roll.PRICE} ({m_roll.PRICE_CONTRACT}), FORWARD {m_roll.FORWARD} ({m_roll.FORWARD_CONTRACT})")
print(f"adjusted price diff on roll day: {row(P, roll) - row(P, prev):.6f}; whole-day new-contract move "
      f"(PRICE@roll close - FORWARD@prev close; NOT the stitched move when the roll is intraday, see exp12b): {m_roll.PRICE - m_prev.FORWARD:.6f}; "
      f"raw PRICE jump across contracts: {m_roll.PRICE - m_prev.PRICE:.6f}")
trace("ROLL", roll)
pseudo = [f for f in calc.pseudo_fills_from_holding if pd.Timestamp(f.date).year == roll.year]
pdates = sorted({pd.Timestamp(f.date).date() for f in pseudo})
print(f"roll-cost pseudo-fill dates in {roll.year}: {pdates}; roll day among them: {roll.date() in pdates}")
print(f"actual PRICE_CONTRACT change days in {roll.year}: {[d.date() for d in roll_days if d.year == roll.year]}")

trace("BOUNDARY (most recent date)", boundary)
