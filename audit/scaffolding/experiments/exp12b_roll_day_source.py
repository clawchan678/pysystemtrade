# EXP-12b (Phase 16, roll-date trace only). Where does the roll-day P&L price move come from?
# Compares, for US10 on the traced roll day 2023-02-09: (i) the shipped adjusted CSV (used by the
# backtest P&L), (ii) the repo's own Panama stitcher applied to the shipped multiple-prices CSV,
# and the multiple-price rows around the roll (intraday). One date; no other change.
import pandas as pd
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from sysobjects.adjusted_prices import futuresAdjustedPrices
d = csvFuturesSimData()
mult = d.get_multiple_prices("US10")
shipped = d.get_backadjusted_futures_price("US10")
restitched = futuresAdjustedPrices.stitch_multiple_prices(mult)
win = (mult.index >= "2023-02-08") & (mult.index < "2023-02-10")
print(mult[win][["PRICE", "PRICE_CONTRACT", "FORWARD", "FORWARD_CONTRACT"]].to_string())
def daily(x): return x.groupby(x.index.normalize()).last()
S, T = daily(shipped), daily(restitched)
a, b = pd.Timestamp("2023-02-08"), pd.Timestamp("2023-02-09")
for lab, x in [("shipped adjusted", S), ("restitched from shipped multiple", T)]:
    print(f"{lab}: 2023-02-08 {x[a]:.6f}  2023-02-09 {x[b]:.6f}  diff {x[b]-x[a]:.6f}")
m = mult
old_leg = m.PRICE[(m.index > "2023-02-09") & (m.PRICE_CONTRACT == "20230300")].iloc[-1] - m.PRICE[m.index.normalize() == a].iloc[-1]
new_leg = m.PRICE[m.index.normalize() == b].iloc[-1] - m.PRICE[(m.index.normalize() == b) & (m.PRICE_CONTRACT == "20230600")].iloc[0]
print(f"old contract move prev close -> last pre-roll row: {old_leg:.6f}; new contract move roll row -> close: {new_leg:.6f}; sum {old_leg+new_leg:.6f}")
