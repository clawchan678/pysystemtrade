# EXP-08b (Phase 15, PF-11 breakdown of EXP-08 arm C). Same two runs as EXP-08 C
# (cost_multiplier 0.0, vol_normalise_currency_costs False, forecast weights estimated;
# full data vs data truncated at 2019-12-31). Question: WHERE in time do the weight and
# position differences occur (first fitted years vs later), so that maxima are not
# misread? Descriptive only; no new parameter or cutoff.
import pandas as pd, numpy as np
from p15_common import build_system, INSTRUMENTS
from exp08_pf3_pf4_pf11_forecast_weights import cfg, C_M

C = pd.Timestamp(C_M) + pd.Timedelta(hours=23, minutes=59)
X = build_system(None, cfg(0.0))
Y = build_system(C_M, cfg(0.0))
starts_x = [p.period_start for p in X.combForecast.calculation_of_raw_estimated_monthly_forecast_weights("CORN").fit_dates]
starts_y = [p.period_start for p in Y.combForecast.calculation_of_raw_estimated_monthly_forecast_weights("CORN").fit_dates]
print("first three period starts X:", [str(s.date()) for s in starts_x[:3]], " Y:", [str(s.date()) for s in starts_y[:3]])
bins = [pd.Timestamp("1900-01-01"), pd.Timestamp("1980-01-01"), pd.Timestamp("2000-01-01"), C]
for ins in INSTRUMENTS:
    wx, wy = X.combForecast.get_forecast_weights(ins)[:C].align(Y.combForecast.get_forecast_weights(ins)[:C], join="inner")
    dw = (wx - wy).abs().max(axis=1)
    px, py = X.accounts.get_buffered_position(ins, roundpositions=True)[:C].align(
        Y.accounts.get_buffered_position(ins, roundpositions=True)[:C], join="inner")
    dp = (px - py).abs()
    print(f"{ins}: max weight diff {dw.max():.4f} on {dw.idxmax().date()}; max position diff {dp.max():.0f} on {dp.idxmax().date()}")
    for a, b in zip(bins[:-1], bins[1:]):
        sw, sp = dw[(dw.index >= a) & (dw.index < b)], dp[(dp.index >= a) & (dp.index < b)]
        if len(sw):
            print(f"   {a.year}-{b.year if b != C else 'C'}: weight maxabs={sw.max():.4f}, "
                  f"position rows differing={int((sp > 0).sum())}/{len(sp)}, position maxabs={sp.max():.0f}")
