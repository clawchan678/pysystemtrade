# EXP-05 (Phase 10): Does a LATER roll change EARLIER Panama-adjusted values, and do earlier
# price DIFFERENCES change? Synthetic multiple prices; uses the framework's own stitcher.
import pandas as pd, numpy as np
from sysobjects.multiple_prices import futuresMultiplePrices
from sysobjects.adjusted_prices import futuresAdjustedPrices
idx = pd.bdate_range("2020-01-01", periods=12)
# contract A held days 0-5, roll to B on day 6 ; B held days 6-11, roll to C on day 11 (only in "full")
price = [100,101,102,101,103,104, 110,111,112,111,113, 120]
pc    = ["A"]*6 + ["B"]*5 + ["C"]
fwd   = [109,110,111,110,112,113, 118,119,120,119,121, 130]
fc    = ["B"]*6 + ["C"]*5 + ["D"]
def mp(n):
    d = pd.DataFrame(dict(PRICE=price[:n], PRICE_CONTRACT=pc[:n], FORWARD=fwd[:n], FORWARD_CONTRACT=fc[:n],
                          CARRY=fwd[:n], CARRY_CONTRACT=fc[:n]), index=idx[:n])
    return futuresMultiplePrices(d)
trunc = futuresAdjustedPrices.stitch_multiple_prices(mp(11))   # history known at day 10 (no 2nd roll yet)
full  = futuresAdjustedPrices.stitch_multiple_prices(mp(12))   # history after the 2nd roll on day 11
common = trunc.index
lvl = (full[common] - trunc).round(10)
dif = (full[common].diff() - trunc.diff()).round(10)
print("level change on days 0-10 after later roll (unique):", sorted(lvl.unique()))
print("difference change on days 1-10 (unique):", sorted(dif.dropna().unique()))
print("roll-day diff (day 6) full:", full.diff().iloc[6], " = B(day6)-B_fwd(day5):", price[6]-fwd[5])
