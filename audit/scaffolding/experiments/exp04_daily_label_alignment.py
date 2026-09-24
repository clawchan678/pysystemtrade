# EXP-04 (Phase 14, PF-14). Scratch-only, synthetic data, no repo data, no network.
# Question: does the repo's daily resample label day t's last (23:00) price at 00:00 of day t,
# so that the positionsizing-style reindex(ffill) onto an hourly index hands that value
# to hourly bars of day t that precede the 23:00 close?
import pandas as pd
from syscore.pandas.frequency import (
    resample_prices_to_business_day_index,   # used by simData.daily_prices (sim_data.py:125)
    get_intraday_pdf_at_frequency,           # used by simData.hourly_prices (sim_data.py:140)
)
idx = []
vals = []
for d, base in (("2024-01-02", 100.0), ("2024-01-03", 200.0), ("2024-01-04", 300.0)):
    for h, add in ((10, 1.0), (15, 2.0), (23, 9.0)):   # 23:00 = notional close row
        idx.append(pd.Timestamp(d) + pd.Timedelta(hours=h)); vals.append(base + add)
raw = pd.Series(vals, index=pd.DatetimeIndex(idx))
daily = resample_prices_to_business_day_index(raw)
hourly = get_intraday_pdf_at_frequency(raw)
aligned = daily.reindex(hourly.index, method="ffill")   # as positionsizing.py:126
print("raw:\n", raw, "\n\ndaily (1B last):\n", daily, "\n\nhourly:\n", hourly)
print("\ndaily value ffilled onto hourly index:\n", pd.concat([hourly, aligned], axis=1, keys=["hourly_price", "daily_value_seen"]))
